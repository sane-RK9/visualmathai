import modal
from pathlib import Path
import time

dockerfile_path =  Path("../config/docker/DockerFile.manim")

# --- Define the Modal App and Docker Image ---
# We define a custom Docker image to ensure Manim and its dependencies (like FFmpeg) are installed.
# This image will be built once and reused for fast cold starts.
manim_image = modal.Image.from_dockerfile(dockerfile_path) 

app = modal.App(
    name="ViualMathAi-backend",
    image=manim_image
)

# --- Define the Modal Function ---
@app.function(
    timeout=300, # Allow up to 5 minutes for rendering
    cpu=2, # Request 2 CPUs for the rendering task
    memory=4096, # Request 4GB of memory
    # You could also add a GPU if using a GPU-accelerated Manim renderer
)
def render_manim_scene(scene_code: str) -> bytes:
    """
    Renders a Manim scene inside a secure, ephemeral Modal Sandbox.

    Args:
        scene_code: A string containing the Python code for the Manim scene's construct() method.

    Returns:
        The raw bytes of the rendered MP4 video file.
    """
    start_time = time.time()
    
    # Base template for the Manim script
    base_scene_template = f"""
from manim import *
import numpy as np

class GeneratedScene(Scene):
    def construct(self):
{scene_code}
"""
    # Create a temporary directory inside the sandbox for all files
    # This directory is automatically cleaned up when the sandbox terminates.
    sandbox_workdir = Path("/tmp/manim_run")
    
    # Create a Modal Sandbox to run the Manim rendering process.
    # We mount our workdir to it.
    sandbox = modal.Sandbox.create(
        "bash", # Start a bash shell
        mounts=[modal.Mount.from_local_dir(".", remote_path="/root")] # Mount local code if needed
    )
    
    # Start the sandbox
    sandbox.start()
    print("Modal Sandbox started.")

    # Create the workdir inside the running sandbox
    sandbox.exec(f"mkdir -p {sandbox_workdir}")

    # Write the full scene code to a file inside the sandbox
    scene_file_path = sandbox_workdir / "scene.py"
    sandbox.exec(f"touch {scene_file_path}") # Create the file
    # Use a 'here document' to safely write the multiline string to the file
    write_proc = sandbox.run_in_sandbox("bash", "-c", f"cat > {scene_file_path}")
    write_proc.stdin.write(base_scene_template.encode("utf-8"))
    write_proc.stdin.close()
    
    print(f"Manim script written to {scene_file_path} inside sandbox.")
    
    # Construct the Manim command
    output_filename = "output.mp4"
    output_file_path = sandbox_workdir / output_filename
    
    cmd = [
        "manim",
        str(scene_file_path),
        "GeneratedScene",
        "--renderer=opengl",
        "--quality=m", # Medium quality
        "--format=mp4",
        "--output_file", str(output_file_path),
        "--progress_bar=none",
        "--quiet"
    ]

    print(f"Executing Manim command in sandbox: {' '.join(cmd)}")
    
    # Execute the Manim command inside the sandbox
    manim_proc = sandbox.exec(*cmd)
    
    if manim_proc.returncode != 0:
        stderr = manim_proc.stderr.read().decode("utf-8")
        print(f"Manim render failed with stderr:\n{stderr}")
        raise Exception(f"Manim render failed: {stderr[:500]}...")

    print("Manim render successful.")

    # Read the rendered video file from the sandbox
    video_bytes = sandbox.get_file(output_file_path)

    # Terminate the sandbox to release resources
    sandbox.terminate()
    
    end_time = time.time()
    print(f"Manim rendering completed in {end_time - start_time:.2f} seconds.")
    
    return video_bytes