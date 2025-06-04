# backend/app/api/render/js_generator.py
class InteractiveJSGenerator:
    def __init__(self):
        self.templates = {
            "slider_control": """
            <div class="control-group">
                <label for="{var_name}">{label}: <span id="{var_name}_value">{default_value}</span></label>
                <input type="range" id="{var_name}" min="{min_val}" max="{max_val}" 
                       step="{step}" value="{default_value}" 
                       oninput="update{var_name}(this.value)">
            </div>
            """,
            "canvas_setup": """
            <canvas id="visualization" width="800" height="600"></canvas>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
            """,
            "math_function": """
            function {function_name}(x, {parameters}) {{
                return {expression};
            }}
            
            function update{parameter}(value) {{
                {parameter} = parseFloat(value);
                document.getElementById('{parameter}_value').textContent = value;
                redraw();
            }}
            """
        }
    
    async def generate_interactive_visualization(self, 
                                              function_expr: str, 
                                              parameters: Dict[str, Dict],
                                              canvas_type: str = "2d") -> Dict[str, str]:
        html_parts = []
        js_parts = []
        css_parts = []
        
        # Generate parameter controls
        for param_name, param_config in parameters.items():
            html_parts.append(
                self.templates["slider_control"].format(
                    var_name=param_name,
                    label=param_config.get("label", param_name),
                    default_value=param_config.get("default", 0),
                    min_val=param_config.get("min", -10),
                    max_val=param_config.get("max", 10),
                    step=param_config.get("step", 0.1)
                )
            )
        
        # Generate visualization code
        if canvas_type == "2d":
            js_parts.append(self._generate_2d_plot(function_expr, parameters))
        elif canvas_type == "3d":
            js_parts.append(self._generate_3d_plot(function_expr, parameters))
        
        return {
            "html": "\n".join(html_parts),
            "javascript": "\n".join(js_parts),
            "css": "\n".join(css_parts)
        }
