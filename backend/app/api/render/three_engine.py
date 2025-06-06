import hashlib
from pathlib import Path
from typing import Dict, Any
from backend.models.context import VisualizationSpec

class ThreeJSGenerator:
    """
    Generates a self-contained, interactive 3D scene using Three.js.
    The output is an HTML file that can be embedded in an iframe.
    """
    def __init__(self):
        # This includes the library, a basic scene setup, and an animation loop.
        self.base_html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>3D Visualization</title>
    <style>
        body {{ margin: 0; overflow: hidden; }}
        canvas {{ display: block; width: 100%; height: 100%; }}
    </style>
</head>
<body>
    <!-- Import Three.js and OrbitControls -->
    <script type="importmap">
    {{
        "imports": {{
            "three": "https://unpkg.com/three@0.160.0/build/three.module.js",
            "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/"
        }}
    }}
    </script>

    <script type="module">
        import * as THREE from 'three';
        import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';

        // --- Basic Scene Setup ---
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0xf0f0f0);

        const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        camera.position.z = 5;

        const renderer = new THREE.WebGLRenderer({{ antialias: true }});
        renderer.setSize(window.innerWidth, window.innerHeight);
        document.body.appendChild(renderer.domElement);

        // --- Controls ---
        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true; // an animation loop is required when either damping or auto-rotation are enabled
        controls.dampingFactor = 0.05;
        controls.screenSpacePanning = false;
        controls.minDistance = 1;
        controls.maxDistance = 50;

        // --- Lighting ---
        const ambientLight = new THREE.AmbientLight(0x404040, 2); // soft white light
        scene.add(ambientLight);
        const directionalLight = new THREE.DirectionalLight(0xffffff, 1.5);
        directionalLight.position.set(1, 1, 1);
        scene.add(directionalLight);
        
        // --- Axes Helper ---
        const axesHelper = new THREE.AxesHelper(5);
        scene.add(axesHelper);

        // --- LLM GENERATED SCENE SETUP CODE START ---
        // This is where the LLM's custom JavaScript code will be injected.
        // It should add objects to the 'scene' and can define animation logic.
        {injected_scene_code}
        // --- LLM GENERATED SCENE SETUP CODE END ---
        
        // --- Animation Loop ---
        function animate() {{
            requestAnimationFrame(animate);

            // Update controls
            controls.update();

            // --- LLM GENERATED ANIMATION CODE START ---
            // Optional: LLM can provide code to be run inside the animation loop.
            {injected_animation_code}
            // --- LLM GENERATED ANIMATION CODE END ---

            renderer.render(scene, camera);
        }}

        // --- Handle window resizing ---
        window.addEventListener('resize', () => {{
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }});
        
        // Start the animation loop
        animate();
    </script>
</body>
</html>
"""
        print("ThreeJSGenerator initialized.")

    async def generate_3d_visualization(self, spec: VisualizationSpec) -> Dict[str, str]:
        """
        Generates a self-contained 3D visualization from a spec.

        Args:
            spec: A VisualizationSpec Pydantic object with type='three_js'.

        Returns:
            A dictionary containing the path to the generated HTML file.
        """
        if spec.type != "three_js":
            raise ValueError("Spec type must be 'three_js' for this generator.")

        content = spec.content
        # The LLM should provide the JS code to set up the scene's objects
        scene_setup_code = content.get("scene_setup_code", "// No scene setup code provided.")
        # The LLM can also provide code for the animation loop
        animation_code = content.get("animation_code", "// No custom animation code provided.")

        # --- Assemble the final HTML file content ---
        full_html = self.base_html_template.format(
            injected_scene_code=scene_setup_code,
            injected_animation_code=animation_code
        )

        # --- Save the HTML to a file and return its path ---
        temp_dir = Path("runtime/cache/generated_assets/html")
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Create a unique filename based on the hash of the generated content
        file_hash = hashlib.md5(full_html.encode()).hexdigest()
        file_path = temp_dir / f"viz_3d_{file_hash}.html"

        # Write to file only if it doesn't already exist (caching)
        if not file_path.exists():
             file_path.write_text(full_html, encoding='utf-8')
             print(f"Generated and saved new 3D HTML to: {file_path}")
        else:
             print(f"3D HTML found in cache: {file_path}")

        # Return the path relative to the static mount point (`runtime/cache`)
        relative_path = Path("generated_assets/html") / file_path.name

        return {"html_path": str(relative_path)}