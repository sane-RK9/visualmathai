import modal
import hashlib
from pathlib import Path
from typing import Dict, Any
from backend.app.models.context import VisualizationSpec

try:
    render_manim_scene_modal = modal.Function.lookup(
        "ViualMathAi-backend-backend", "render_manim_scene"
    )
    MODAL_AVAILABLE = True
    print("Successfully connected to Modal function 'render_manim_scene'.")
except modal.exception.NotFoundError:
    render_manim_scene_modal = None
    MODAL_AVAILABLE = False
    print("Warning: Modal function 'render_manim_scene' not found. "
          "Ensure the Modal app is deployed by running 'modal deploy modal_runners/manim_runner.py'. "
          "Manim rendering will be disabled.")

class ManimRenderer:
    """
    Client for the Modal-based sandboxed Manim rendering service.
    
    This class's responsibility is to:
    1. Check a local cache for previously rendered videos.
    2. If not cached, call the remote Modal function to perform the rendering.
    3. Receive the video bytes from Modal.
    4. Save the video to the local cache.
    5. Return a relative path suitable for the Gradio UI.
    """
    def __init__(self, output_dir: str = "runtime/cache/manim"):
        """
        Initializes the ManimRenderer client.

        Args:
            output_dir: The local directory to cache rendered videos.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        print(f"ManimRenderer (Modal Client) initialized. Local cache: {self.output_dir}")
        if not MODAL_AVAILABLE:
            print("ManimRenderer is in a non-functional state as the Modal backend is not available.")

    async def render_scene(self, spec: VisualizationSpec) -> str:
        """
        Calls the remote Modal function to render a Manim scene, leveraging a local cache.

        Args:
            spec: A VisualizationSpec Pydantic object with type='manim'.
                  The spec.content is expected to contain a 'scene_code' string.

        Returns:
            The path to the saved video file, relative to the static mount point
            (e.g., "manim/GeneratedScene_hash.mp4").

        Raises:
            ValueError: If the spec is invalid.
            RuntimeError: If the Modal backend is not available.
            Exception: If the remote rendering process on Modal fails.
        """
        if not MODAL_AVAILABLE:
            raise RuntimeError("Manim rendering is disabled because the Modal backend is not deployed or available.")
            
        if spec.type != "manim":
            raise ValueError("Spec type must be 'manim' for this generator.")

        scene_code = spec.content.get("scene_code")
        if not scene_code or not isinstance(scene_code, str) or not scene_code.strip():
            raise ValueError("Manim spec is missing valid 'scene_code' in its content.")

        # --- Local Cache Check ---
        # Generate a unique filename based on a hash of the scene code.
        # This allows us to avoid re-rendering identical scenes.
        content_hash = hashlib.md5(scene_code.encode('utf-8')).hexdigest()
        # The scene name is fixed in the Modal runner template
        scene_name = "GeneratedScene"
        output_filename = f"{scene_name}_{content_hash}.mp4"
        local_cache_path = self.output_dir / output_filename

        if local_cache_path.exists():
            print(f"Manim video found in local cache: {local_cache_path}")
            # Return path relative to the `runtime/cache` directory
            return str(Path("manim") / local_cache_path.name)

        # --- Remote Rendering Call ---
        try:
            print("Calling remote Modal function for Manim rendering...")
            
            # .remote.aio() is the non-blocking, async version of the call.
            video_bytes = await render_manim_scene_modal.remote.aio(scene_code)
            
            if not video_bytes:
                raise Exception("Modal function returned empty video data.")

            # --- Save to Local Cache ---
            # Save the received video bytes to our local cache for future requests.
            with open(local_cache_path, "wb") as f:
                f.write(video_bytes)
            
            print(f"Manim video received from Modal and saved to local cache: {local_cache_path}")
            
            # --- Return Relative Path ---
            # The path should be relative to `runtime/cache` for the Gradio static server.
            relative_path = Path("manim") / local_cache_path.name
            return str(relative_path)

        except modal.exception.RemoteError as e:
            # This error specifically catches exceptions raised *within* the remote Modal function.
            print(f"Error from remote Manim renderer: {e}")
            # Propagate a user-friendly error message.
            raise Exception(f"Failed to render Manim video remotely. The scene code may contain an error. Details: {e}")
        except Exception as e:
            # Catch other potential errors (network issues, etc.)
            print(f"An unexpected error occurred while calling the Modal Manim renderer: {e}")
            raise