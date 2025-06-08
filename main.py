import gradio as gr
import httpx 
import uuid
import json
import os

# --- Configuration ---
# The Gradio app reads the backend's URL from an environment variable.
# This makes it flexible for both local development and deployment.
# In docker-compose, this is set to 'http://backend:8000'.
# For local testing without Docker, it defaults to 'http://127.0.0.1:8000'.
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
API_PREFIX = "/api/v1" 

# --- API Client Function ---
async def send_request_to_backend(session_id: str, message: str) -> dict:
    """
    Sends the user's message to the FastAPI backend and returns the parsed JSON response.
    This function handles all communication with the backend.
    """
    api_url = f"{BACKEND_URL}{API_PREFIX}/chat/{session_id}"
    payload = {"message": message, "provider": "openai"}  # The provider could be a UI option later

    print(f"Frontend: Sending request to {api_url}")
    try:
        # Set a generous timeout to allow for LLM and rendering latency.
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(api_url, json=payload)
            # This will raise an exception for HTTP error codes (4xx or 5xx).
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        # Handle API errors returned from the backend (e.g., 500 Internal Server Error)
        try:
            error_detail = e.response.json().get("detail", e.response.text)
        except json.JSONDecodeError:
            error_detail = e.response.text
        print(f"API Error: {e.response.status_code} - {error_detail}")
        return {"error": f"Backend API Error ({e.response.status_code}): {error_detail}"}
    except httpx.RequestError as e:
        # Handle network-level errors (e.g., cannot connect to the backend)
        error_msg = f"Network Error: Unable to connect to backend at {api_url}. Is the backend server running?"
        print(f"{error_msg} Details: {e}")
        return {"error": error_msg}
    except Exception as e:
        print(f"An unexpected error occurred in the API client: {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

# --- Gradio UI and Event Handlers ---

async def handle_user_input(user_message: str, history: list, session_id: str):
    """
    The main Gradio event handler. It's triggered by user actions.
    It calls the backend and then yields updates for the UI components.
    """
    if not user_message.strip():
        # Do nothing if the input is empty
        return

    # Append user message to the UI immediately for a responsive feel
    history.append([user_message, None])
    # Yield the history to update the chatbot with the user's message
    yield history, gr.update(), gr.update(), gr.update(), gr.update()

    # Call our API client function to get the response from the backend
    response_data = await send_request_to_backend(session_id, user_message)
    
    # Check for an error in the response
    if "error" in response_data:
        history[-1][1] = f"⚠️ **Error:** {response_data['error']}"
        yield history, gr.update(), gr.update(), gr.update(), gr.update()
        return

    # Process the successful response from the backend
    explanation = response_data.get("explanation", "*No explanation provided.*")
    visualization = response_data.get("visualization") # This can be None

    # Update the chatbot with the final text explanation from the assistant
    history[-1][1] = explanation
    
    # Prepare updates for the visualization components
    html_update = gr.HTML(visible=False)
    plot_update = gr.Plot(visible=False)
    video_update = gr.Video(visible=False)
    
    if visualization:
        viz_type = visualization.get("type")
        if viz_type == "html":
            # Construct the full URL to the static asset served by the backend
            iframe_url = BACKEND_URL + visualization.get("url", "")
            html_update = gr.HTML(
                value=f'<iframe src="{iframe_url}" width="100%" height="400px" sandbox="allow-scripts allow-same-origin allow-forms"></iframe>',
                visible=True
            )
        elif viz_type == "plotly":
            # The backend sends the figure as a JSON string, so we parse it
            figure_json = json.loads(visualization.get("figure", "{}"))
            plot_update = gr.Plot(value=figure_json, visible=True)
        elif viz_type == "video":
            # Construct the full URL to the video served by the backend
            video_url = BACKEND_URL + visualization.get("url", "")
            video_update = gr.Video(value=video_url, visible=True)

    # Yield the final state with all updates
    yield history, html_update, plot_update, video_update, session_id

def create_interface():
    """Creates and configures the Gradio Blocks interface."""
    with gr.Blocks(title="VisualMathAI", theme=gr.themes.Soft(), css=".gradio-container { max-width: 1200px !important; margin: auto; }") as app:
        gr.Markdown("# 🧠 VisualMathAI")
        gr.Markdown("An interactive AI assistant for visual learning. Ask a question or request a visualization below.")

        # This state object holds the unique session ID for the browser tab.
        session_id_state = gr.State(value=str(uuid.uuid4()))

        chatbot = gr.Chatbot(label="Conversation", height=500, bubble_full_width=False)
        message_input = gr.Textbox(placeholder="e.g., 'What is a Fourier Transform?' or 'Plot the function y = x^3 - 2*x'", label="Your Message")
        
        with gr.Row():
            send_btn = gr.Button("Send", variant="primary")
            clear_btn = gr.Button("Clear Chat")
            
        with gr.Accordion("🔬 Visualization Output", open=True):
            html_visualization = gr.HTML(visible=False)
            plotly_visualization = gr.Plot(visible=False)
            video_visualization = gr.Video(visible=False)
        
        # Define the outputs for the event handler IN ORDER
        outputs = [
            chatbot,
            html_visualization,
            plotly_visualization,
            video_visualization,
            session_id_state
        ]
        
        # Wire up events
        send_btn.click(
            fn=handle_user_input,
            inputs=[message_input, chatbot, session_id_state],
            outputs=outputs
        ).then(lambda: "", outputs=message_input) # Clear input after send

        message_input.submit(
            fn=handle_user_input,
            inputs=[message_input, chatbot, session_id_state],
            outputs=outputs
        ).then(lambda: "", outputs=message_input)

        def clear_chat_handler():
            # Simply clear the UI and generate a new session ID for a fresh start
            new_session_id = str(uuid.uuid4())
            return [], gr.HTML(visible=False), gr.Plot(visible=False), gr.Video(visible=False), new_session_id

        clear_btn.click(fn=clear_chat_handler, outputs=outputs)
    return app

# --- Entry Point ---
if __name__ == "__main__":
    interface = create_interface()
    # Launch on 0.0.0.0 to be accessible within a Docker container.
    # The port 7860 is what we expose in docker-compose.yml.
    interface.launch(server_name="0.0.0.0", server_port=7860)