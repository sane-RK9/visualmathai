import os
from typing import Dict, Any, List, Union
from .router import LLMProvider
from backend.models.context import LearningContext, ContextMessage, VisualizationSpec
import openai
import json
import re # To extract JSON from text

class OpenAIProvider(LLMProvider):
    def __init__(self):
        # API key loaded from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
             raise ValueError("OPENAI_API_KEY environment variable not set.")
        self.client = openai.OpenAI(api_key=api_key)
        # Define the LLM model to use
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini") # Use a capable model for JSON
        print(f"OpenAIProvider initialized with model: {self.model}")

    async def generate_response(self, messages: List[Dict], context: LearningContext) -> Union[str, VisualizationSpec]:
        """
        Generates a response. Tries to generate a structured VisualizationSpec
        if the user's prompt requests a visualization.
        """
        # Create enhanced system prompt with context and instruction for structured output
        system_prompt = f"""
You are an interactive educational assistant called 'VisualLearner'. Your primary goal is to help users understand concepts through explanations and dynamic visualizations.

**Current State:**
- Session ID: {context.session_id}
- Current Topic: {context.current_topic if context.current_topic else 'Not specified'}
- UI Variables: {json.dumps(context.ui_state.variables)}

**Instructions:**
1.  Always provide a clear, concise explanation of the concept or answer the user's question in standard markdown text first.
2.  If the user asks to "visualize", "show a graph", "animate", "plot", "model", "simulate", etc., attempt to generate a structured visualization specification in JSON format. Place the JSON *after* your explanation, enclosed in ```json ... ``` block.
3.  The JSON must conform to the `VisualizationSpec` structure:
    ```json
    {{
      "type": "string", // Choose one: "plotly", "manim", "interactive_js", "text_explanation"
      "explanation": "string", // Repeat or elaborate on the explanation text here
      "content": {{ // Details specific to the type
        // If type is "plotly": {{ "data": [{{...}}], "layout": {{...}} }} (standard Plotly figure dict)
        // If type is "manim": {{ "scene_code": "string" }} (Python Manim code string)
        // If type is "interactive_js": {{ "html": "string", "javascript": "string", "css": "string", "parameters": {{...}} }} (HTML for controls/canvas, JS logic, optional CSS, parameter specs for interactive controls)
        // If type is "text_explanation": {{}} // Content is empty, only explanation is provided
      }}
    }}

    ```
4.  If a visualization is not appropriate or cannot be generated, provide only a text explanation and set the JSON `type` to `"text_explanation"` with empty content.
5.  Use the `interactive_js` type for simple parameterized graphs (like sin(x+a), quadratic equations) that can be drawn on a 2D canvas with sliders.
6.  Use the `plotly` type for static or more complex 2D/3D plots that Plotly supports.
7.  Use the `manim` type for animations or more formal mathematical demonstrations.
8.  Ensure the `explanation` field in the JSON matches the explanation provided outside the JSON block.
9.  Always keep your responses helpful, educational, and friendly.

**Example JSON Structure for sin(x+a) Interactive JS:**
```json
{{
  "type": "interactive_js",
  "explanation": "Let's visualize the sine wave $y = \sin(x+a)$ where $a$ is the phase shift.",
  "content": {{
    "function_expr": "Math.sin(x + a)",
    "parameters": {{
      "a": {{"min": 0, "max": 6.28, "default": 0, "step": 0.1, "label": "Phase Shift (a)"}}
    }}
  }}
}}```
        """
        
        # Prepare the messages for the OpenAI API
        openai_messages = [
            {"role": "system", "content": system_prompt},
            *messages  # Include user and assistant messages
        ]

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                max_tokens=1500,  # Adjust as needed
                temperature=0.7,  # Adjust for creativity vs. accuracy
            )
            
            # Extract the content from the response
            content = response.choices[0].message.content.strip()
            
            # Try to extract JSON from the response using regex
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                json_content = json_match.group(1).strip()
                visualization_spec = VisualizationSpec.model_validate_json(json_content)
                return visualization_spec
            
            # If no JSON found, return the plain text response
            return content
        
        except Exception as e:
            print(f"Error generating response: {e}")
            return str(e)