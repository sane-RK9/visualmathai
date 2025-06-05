import os
import json
import re # To extract JSON from text
from typing import Dict, Any, List, Union
from backend.llm.router import LLMProvider
from backend.models.context import LearningContext, ContextMessage, VisualizationSpec
import anthropic

class ClaudeProvider(LLMProvider):
    def __init__(self):
        # API key loaded from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
             # Allow initialization even without key, but raise error on use
             print("Warning: ANTHROPIC_API_KEY environment variable not set. ClaudeProvider will not work.")
             self.client = None
        else:
            self.client = anthropic.Anthropic(api_key=api_key)

        # Define the LLM model to use
        # Choose a suitable Claude model, e.g., claude-3-opus-20240229, claude-3-sonnet-20240229, claude-3-haiku-20240307
        # Haiku is fastest/cheapest, Opus is strongest, Sonnet is a good balance.
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-4-haiku-20250507")  
        if self.client:
            print(f"ClaudeProvider initialized with model: {self.model}")


    async def generate_response(self, messages: List[Dict], context: LearningContext) -> Union[str, VisualizationSpec]:
        """
        Generates a response using Anthropic Claude. Tries to generate a structured
        VisualizationSpec if the user's prompt requests a visualization.
        """
        if not self.client:
             return "Claude provider is not configured (ANTHROPIC_API_KEY not set)."

        # Construct the system prompt - similar structure to OpenAI prompt
        # emphasizing structured output and context awareness.
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
"""

        # Format messages for Anthropic API.
        # Anthropic Messages API expects alternating 'user' and 'assistant' roles.
        # The system prompt is a separate parameter.
        # Ensure the last message is from the user.
        anthropic_messages = []
        for msg_dict in messages:
            # Basic validation/conversion for Anthropic roles
            role = msg_dict.get("role")
            content = msg_dict.get("content")
            if role in ["user", "assistant"] and content is not None:
                 anthropic_messages.append({"role": role, "content": content})
            # System messages from history are handled by the main system prompt

        # Ensure the message list is not empty and ends with a user message
        if not anthropic_messages or anthropic_messages[-1]["role"] != "user":
             print("Warning: Message history is not in expected format for Anthropic (empty or doesn't end with user).")
             # Attempt to recover by just using the last user message if available
             last_user_message = next((m for m in reversed(messages) if m.get("role") == "user"), None)
             if last_user_message:
                  anthropic_messages = [{"role": "user", "content": last_user_message["content"]}]
             else:
                 return "Could not format messages for the LLM."


        try:
            print(f"Calling Claude model: {self.model}")
            # Use the async client method
            response = await self.client.messages.create(
                model=self.model,
                system=system_prompt, # System prompt as a separate parameter
                messages=anthropic_messages,
                max_tokens=2500, # Allow enough tokens
                temperature=0.7
            )

            # The response content is a list of content blocks
            response_content = "".join(block.text for block in response.content if block.type == 'text')
            print(f"Received Claude response (partial):\n{response_content[:500]}...")


            # Attempt to parse JSON from the response using the same regex
            json_match = re.search(r'```json\s*(.*?)\s*```', response_content, re.DOTALL)

            if json_match:
                json_string = json_match.group(1)
                try:
                    spec_data = json.loads(json_string)
                    # Validate against Pydantic model
                    visualization_spec = VisualizationSpec(**spec_data)
                    # You might want to clean the raw response content to remove the JSON block
                    # before using it as the primary text explanation, or rely solely
                    # on the explanation field within the JSON. Let's clean the raw text.
                    text_explanation = re.sub(r'```json\s*.*?```', '', response_content, flags=re.DOTALL).strip()
                    # Use the cleaned text explanation
                    visualization_spec.explanation = text_explanation

                    return visualization_spec

                except json.JSONDecodeError as e:
                    print(f"Warning: Claude returned invalid JSON: {e}\nContent: {json_string}")
                    # Fallback to returning just the text response if JSON is invalid
                    return response_content
                except Exception as e:
                    print(f"Warning: Failed to parse Claude JSON response into spec: {e}\nContent: {json_string}")
                     # Fallback to returning just the text response if validation fails
                    return response_content
            else:
                # No JSON block found, return plain text response
                print("No JSON block found in Claude response, returning text.")
                return response_content

        except anthropic.APIConnectionError as e:
            print(f"Claude API connection error: {e}")
            return f"An API connection error occurred with Claude: {e}"
        except anthropic.RateLimitError as e:
             print(f"Claude Rate limit error: {e}")
             return "You've hit the rate limit for the Claude API. Please try again later."
        except anthropic.AuthenticationError as e:
             print(f"Claude Authentication error: {e}")
             return "Authentication failed for the Claude API. Check your API key."
        except anthropic.APIStatusError as e:
            print(f"Claude API status error {e.status_code}: {e.response}")
            return f"An API error occurred with Claude (Status {e.status_code})."
        except Exception as e:
            print(f"An unexpected error occurred during Claude call: {e}")
            return f"An unexpected error occurred: {e}"