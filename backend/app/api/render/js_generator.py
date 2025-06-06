import json
from typing import Dict, Any
from pathlib import Path
import hashlib
from backend.models.context import VisualizationSpec

class InteractiveJSGenerator:
    """
    Generates a self-contained, interactive HTML/JS visualization based on a structured spec.
    The output is an HTML file that can be embedded in an iframe.
    """
    def __init__(self):
        # Define a comprehensive base template for the HTML file.
        # This template includes placeholders for injecting controls, variables, and functions.
        self.base_html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Interactive Visualization</title>
    <style>
        /* Basic styling for a clean look within an iframe */
        body {{ 
            margin: 0; 
            padding: 10px; 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            display: flex; 
            flex-direction: column; 
            align-items: center; 
            height: 100vh;
            box-sizing: border-box;
            background-color: #f9f9f9;
        }}
        .controls {{ 
            margin-bottom: 10px; 
            display: flex; 
            flex-wrap: wrap; 
            justify-content: center; 
            gap: 15px; 
            padding: 8px; 
            background-color: #f0f0f0; 
            border-radius: 8px;
            width: 100%;
            box-sizing: border-box;
        }}
        .control-group {{ 
            display: flex; 
            align-items: center; 
            gap: 8px; 
        }}
        .control-group label {{ 
            font-weight: 500; 
            font-size: 14px;
        }}
        .value-display {{ 
            min-width: 40px; 
            text-align: center; 
            font-weight: normal; 
            font-family: monospace;
            background-color: white;
            padding: 2px 4px;
            border-radius: 4px;
            border: 1px solid #ddd;
        }}
        canvas {{ 
            border: 1px solid #ccc; 
            background-color: white; 
            width: 100%;
            flex-grow: 1; /* Allow canvas to take remaining space */
            box-sizing: border-box;
        }}
    </style>
</head>
<body>
    <div class="controls">
        {controls_html}
    </div>
    <canvas id="visualization-canvas"></canvas>

    <script>
        const canvas = document.getElementById('visualization-canvas');
        const ctx = canvas.getContext('2d');

        // --- Injected State and Parameters ---
        {variable_declarations}

        // --- Injected Mathematical Function ---
        {math_function_js}

        // --- Injected Parameter Update Functions ---
        {update_functions_js}
        
        // --- Core Drawing and Resize Logic ---
        function resizeCanvas() {{
            // Resize canvas to fit its container's displayed size
            const dpr = window.devicePixelRatio || 1;
            const rect = canvas.getBoundingClientRect();
            canvas.width = rect.width * dpr;
            canvas.height = rect.height * dpr;
            ctx.scale(dpr, dpr);
            // Redraw after resizing
            draw();
        }}

        function draw() {{
            if (!canvas || !ctx) return;
            const width = canvas.clientWidth;
            const height = canvas.clientHeight;
            ctx.clearRect(0, 0, width, height);

            // Define the plot range (can be made dynamic later)
            const xMin = -10, xMax = 10;
            const yMin = -10, yMax = 10;
            const xRange = xMax - xMin;
            const yRange = yMax - yMin;

            const xScale = width / xRange;
            const yScale = height / yRange;
            const xOffset = -xMin * xScale;
            const yOffset = yMax * yScale;

            // Draw axes
            ctx.strokeStyle = '#ccc';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(0, yOffset); ctx.lineTo(width, yOffset); // X-axis
            ctx.moveTo(xOffset, 0); ctx.lineTo(xOffset, height); // Y-axis
            ctx.stroke();
            
            // Draw grid lines (optional)
            ctx.strokeStyle = '#eee';
            for (let i = Math.floor(xMin); i <= Math.ceil(xMax); i++) {{
                if (i === 0) continue;
                const gridX = xOffset + i * xScale;
                ctx.beginPath(); ctx.moveTo(gridX, 0); ctx.lineTo(gridX, height); ctx.stroke();
            }}
            for (let i = Math.floor(yMin); i <= Math.ceil(yMax); i++) {{
                if (i === 0) continue;
                const gridY = yOffset - i * yScale;
                ctx.beginPath(); ctx.moveTo(0, gridY); ctx.lineTo(width, gridY); ctx.stroke();
            }}

            // Draw function graph
            ctx.strokeStyle = '#007bff';
            ctx.lineWidth = 2;
            ctx.beginPath();

            let lastValidY = null;
            for (let px = 0; px < width; px++) {{
                const x = (px - xOffset) / xScale;
                const y = mathFunction(x, {parameter_names_list}); // Pass parameters
                
                if (isFinite(y)) {{
                    const py = yOffset - y * yScale;
                    // If the last point was not valid, move to this new point to start a new line segment
                    if (lastValidY === null) {{
                        ctx.moveTo(px, py);
                    }} else {{
                        ctx.lineTo(px, py);
                    }}
                    lastValidY = py;
                }} else {{
                    // Current point is invalid (e.g., tan(pi/2)), reset last valid point
                    lastValidY = null;
                }}
            }}
            ctx.stroke();
        }}
        
        // --- Communication with Parent Frame ---
        function notifyParent(variable, value) {{
            // Use postMessage for secure cross-origin communication
            if (window.parent) {{
                window.parent.postMessage({{ 
                    type: 'iframe_variable_update', 
                    variable: variable, 
                    value: value 
                }}, '*'); // Replace '*' with target origin in production for security
            }}
        }}

        // --- Initialization ---
        window.addEventListener('resize', resizeCanvas);
        // Initial call
        resizeCanvas();

    </script>
</body>
</html>
"""
        print("InteractiveJSGenerator initialized with updated templates.")

    async def generate_interactive_visualization(self, spec: VisualizationSpec) -> Dict[str, str]:
        """
        Generates a self-contained interactive HTML visualization from a spec.

        Args:
            spec: A VisualizationSpec Pydantic object with type='interactive_js'.

        Returns:
            A dictionary containing the path to the generated HTML file,
            relative to the static mount point. E.g., {'html_path': 'generated_assets/html/viz_hash.html'}
        """
        if spec.type != "interactive_js":
            raise ValueError("Spec type must be 'interactive_js' for this generator.")

        content = spec.content
        function_expr = content.get("function_expr")
        parameters = content.get("parameters", {}) # Dict[param_name, config]

        if not function_expr:
             raise ValueError("Interactive JS spec is missing the required 'function_expr' in its content.")

        # --- Generate HTML and JS parts from the spec ---
        controls_html_parts = []
        variable_declarations = []
        update_functions_js_parts = []
        parameter_names_list = list(parameters.keys())

        for param_name, config in parameters.items():
            # Generate slider control HTML
            controls_html_parts.append(f"""
            <div class="control-group">
                <label for="{param_name}">{config.get('label', param_name)}:</label>
                <input type="range" id="{param_name}" min="{config.get('min', -10)}" max="{config.get('max', 10)}"
                       step="{config.get('step', 0.1)}" value="{config.get('default', 0)}"
                       oninput="update_{param_name}(this.value)">
                <span id="{param_name}_value" class="value-display">{config.get('default', 0)}</span>
            </div>
            """)
            
            # Generate JavaScript variable declaration for the parameter
            variable_declarations.append(f"let {param_name} = {config.get('default', 0)};")
            
            # Generate the update function for this parameter
            update_functions_js_parts.append(f"""
            function update_{param_name}(value) {{
                {param_name} = parseFloat(value);
                document.getElementById('{param_name}_value').textContent = value;
                draw(); // Redraw the visualization on change
                notifyParent('{param_name}', {param_name}); // Notify the parent Gradio app
            }}
            """)

        # --- Generate the core mathematical function using the safer Function constructor ---
        # This prevents it from accessing the local scope, which is safer than direct eval().
        # We assume the expression uses standard Math object properties (e.g., Math.sin, Math.cos).
        # We also pass the parameter names as arguments to the function.
        parameter_names_str = ", ".join(parameter_names_list)
        # The body of the function simply returns the expression.
        # This is where you would add sanitization if needed.
        # For now, we trust the LLM to provide a valid JS math expression.
        math_function_js = f"""
        const mathFunction = new Function('x', '{parameter_names_str}', `"use strict"; return ${function_expr};`);
        """

        # --- Assemble the final HTML file content ---
        full_html = self.base_html_template.format(
            controls_html="\n".join(controls_html_parts),
            variable_declarations="\n        ".join(variable_declarations),
            math_function_js=math_function_js,
            update_functions_js="\n        ".join(update_functions_js_parts),
            parameter_names_list=parameter_names_str # Pass this to the draw function call
        )

        # --- Save the HTML to a file and return its path ---
        temp_dir = Path("runtime/cache/generated_assets/html")
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Create a unique filename based on the hash of the generated content
        file_hash = hashlib.md5(full_html.encode()).hexdigest()
        file_path = temp_dir / f"viz_{file_hash}.html"

        # Write to file only if it doesn't already exist (caching)
        if not file_path.exists():
             file_path.write_text(full_html, encoding='utf-8')
             print(f"Generated and saved new interactive HTML to: {file_path}")
        else:
             print(f"Interactive HTML found in cache: {file_path}")

        # The Gradio app will serve the `runtime/cache` directory at `/static`.
        # Return the path relative to that mount point.
        relative_path = Path("generated_assets/html") / file_path.name

        return {"html_path": str(relative_path)}