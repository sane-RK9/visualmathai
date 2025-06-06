import plotly.graph_objects as go
import numpy as np
from typing import Dict, Any
from asteval import Interpreter 
from backend.app.models.context import VisualizationSpec

class PlotlyGenerator:
    """
    Generates Plotly figures from a structured specification.
    """
    def __init__(self):
        print("PlotlyGenerator initialized.")
        # Create a safe interpreter for evaluating math expressions
        self.safe_interpreter = Interpreter()
        # Add common math functions and constants to the interpreter's symbol table
        self.safe_interpreter.symtable['np'] = np
        self.safe_interpreter.symtable['math'] = __import__('math')


    async def generate_plotly_visualization(self, spec: VisualizationSpec) -> go.Figure:
        """
        Generates a Plotly figure based on a 'plotly' visualization spec.

        Args:
            spec: A VisualizationSpec Pydantic object with type='plotly'.

        Returns:
            A plotly.graph_objects.Figure object, which can be directly used by gr.Plot.
        """
        if spec.type != "plotly":
            raise ValueError("Spec type must be 'plotly' for this generator.")

        content = spec.content

        # --- Primary Method: Use a pre-defined figure dictionary from the LLM ---
        figure_dict = content.get("figure")
        if figure_dict and isinstance(figure_dict, dict):
            print("Generating Plotly figure from 'figure' dictionary in spec.")
            try:
                # Create a figure directly from the dictionary provided by the LLM
                fig = go.Figure(figure_dict)
                # Ensure the title is set from the main explanation for consistency
                fig.update_layout(title_text=spec.explanation, title_x=0.5)
                return fig
            except Exception as e:
                error_message = f"Error creating Plotly figure from spec data: {e}"
                print(error_message)
                return self._create_error_figure(error_message)


        # --- Fallback Method: Generate from a function expression ---
        function_expr = content.get("function_expr")
        if function_expr:
            print(f"Attempting to generate Plotly figure from 'function_expr': {function_expr}")
            try:
                # Get parameters and their default values from the spec
                parameters = content.get("parameters", {})
                for param_name, config in parameters.items():
                    # Add parameter default values to the interpreter's symbol table
                    self.safe_interpreter.symtable[param_name] = config.get("default", 0)

                # Generate x values
                x_values = np.linspace(-10, 10, 400)
                self.safe_interpreter.symtable['x'] = x_values

                # Safely evaluate the expression
                y_values = self.safe_interpreter.eval(function_expr)

                # Create the plot
                fig = go.Figure(data=go.Scatter(x=x_values, y=y_values, mode='lines', name=function_expr))
                fig.update_layout(
                    title_text=spec.explanation,
                    title_x=0.5,
                    xaxis_title="x",
                    yaxis_title="y"
                )
                return fig

            except Exception as e:
                error_message = f"Error evaluating function expression '{function_expr}': {e}"
                print(error_message)
                return self._create_error_figure(error_message)


        # --- Failure Case ---
        # If neither 'figure' nor 'function_expr' is provided or valid
        error_message = "Plotly spec is missing valid 'figure' data or a 'function_expr'."
        print(error_message)
        return self._create_error_figure(error_message)


    def _create_error_figure(self, error_message: str) -> go.Figure:
        """Creates an empty Plotly figure with an error message annotation."""
        fig = go.Figure()
        fig.update_layout(
            title_text="Plot Generation Error",
            xaxis={'visible': False},
            yaxis={'visible': False},
            annotations=[{
                'text': f"Could not generate plot:<br>{error_message[:200]}...",
                'xref': 'paper',
                'yref': 'paper',
                'showarrow': False,
                'font': {'size': 14, 'color': 'red'}
            }]
        )
        return fig