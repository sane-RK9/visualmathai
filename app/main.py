import gradio as gr
import os
import asyncio # Needed for running async initialization
import traceback # For detailed error logging
# Import the core backend logic components
from backend.context.protocol import ContextProtocol, initialize_context_storage
from backend.llm.router import LLMRouter
from backend.models.context import LearningContext, ContextMessage, VisualizationSpec, create_session_id
from backend.render.js_generator import InteractiveJSGenerator
from backend.render.manim_engine import ManimRenderer
from backend.render.plotly_generator import PlotlyGenerator
# from backend_logic.sandbox.executor import SafeCodeExecutor # Import when implemented

# --- Global Backend Logic Instances ---
# These will be initialized once at application startup
context_protocol: ContextProtocol = None
llm_router: LLMRouter = None
js_generator: InteractiveJSGenerator = None
manim_renderer: ManimRenderer = None
plotly_generator: PlotlyGenerator = None
# safe_executor: SafeCodeExecutor = None # Initialize when implemented

# --- Asynchronous Initialization Function ---
async def initialize_backend():
    """Initializes all backend components, including async ones like database."""
    print("Initializing backend components...")
    # Initialize context storage (e.g., SQLite DB)
    await initialize_context_storage()

    # Initialize protocol and renderers
    global context_protocol, llm_router, js_generator, manim_renderer, plotly_generator # Declare globals
    context_protocol = ContextProtocol(storage_backend="sqlite") # Use sqlite persistence
    llm_router = LLMRouter()
    js_generator = InteractiveJSGenerator()
    manim_renderer = ManimRenderer()
    plotly_generator = PlotlyGenerator()
    # safe_executor = SafeCodeExecutor() # Initialize sandbox executor

    print("Backend components initialized.")

# --- Gradio Interaction Function ---

async def handle_user_input(user_message: str, history: list, session_id: str):
    """
    Handles user input, interacts with LLM and renderers, updates context,
    and returns outputs for the Gradio UI.
    """
    if not user_message:
        return history, gr.Markdown(visible=False, value=""), gr.HTML(visible=False, value=""), gr.Plot(visible=False, value=None), gr.Video(visible=False, value=None)

    if not session_id:
        session_id = create_session_id()
        print(f"New session created: {session_id}")

    # 1. Get current context
    try:
        context = await context_protocol.get_context(session_id)
    except Exception as e:
        error_msg = f"Error loading context for session {session_id}: {e}"
        print(error_msg)
        # Update history with error
        history.append([user_message, error_msg])
        return history, gr.Markdown(visible=True, value=error_msg), gr.HTML(visible=False, value=""), gr.Plot(visible=False, value=None), gr.Video(visible=False, value=None)


    # 2. Add user message to context
    # We add the user message to history *before* calling LLM so it appears immediately
    # Then add to backend context for persistence and LLM
    history.append([user_message, None]) # Add user message immediately to Gradio history
    await context_protocol.add_message(session_id, "user", user_message)


    # 3. Call LLM
    # Prepare messages for LLM (using messages from context)
    # Convert ContextMessage Pydantic objects to dicts for LLM provider
    llm_messages = [{"role": msg.role, "content": msg.content} for msg in context.messages]

    # Get response from LLM (this might be text or a VisualizationSpec)
    llm_output = None # Initialize llm_output outside try block
    try:
        llm_output = await llm_router.route_request(
            provider_name="openai", # Or "claude", "local" - could be a UI parameter
            messages=llm_messages,
            context=context # Pass the full context object
        )
    except ValueError as e:
         # Handle specific errors like unknown provider
         error_msg = f"LLM Configuration Error: {e}"
         print(error_msg)
         history[-1][1] = error_msg # Update last assistant message placeholder
         # Return components to update
         return history, gr.Markdown(visible=True, value=error_msg), gr.HTML(visible=False, value=""), gr.Plot(visible=False, value=None), gr.Video(visible=False, value=None)
    except Exception as e:
        error_msg = f"Error during LLM request: {e}\n{traceback.format_exc()}" # Include traceback
        print(error_msg)
        history[-1][1] = error_msg # Update last assistant message placeholder
        # Return components to update
        return history, gr.Markdown(visible=True, value=error_msg), gr.HTML(visible=False, value=""), gr.Plot(visible=False, value=None), gr.Video(visible=False, value=None)


    # --- Process LLM Output ---
    explanation_text = ""
    visualization_output_details = None # Store details about the viz output (type, content)
    viz_spec = None # Store the received spec if any

    if isinstance(llm_output, VisualizationSpec):
        viz_spec = llm_output
        explanation_text = viz_spec.explanation # Use explanation from the spec

        try:
            # Determine which renderer to use based on the spec type
            if viz_spec.type == "interactive_js":
                # Generate HTML/JS and get the path to the file
                render_result = await js_generator.generate_interactive_visualization(viz_spec)
                # render_result is expected to be {"html_path": "..."}
                visualization_output_details = {"type": "html", "content": render_result.get("html_path")}
                print(f"Generated interactive JS visualization file: {visualization_output_details['content']}")

            elif viz_spec.type == "plotly":
                # Generate Plotly figure object
                render_result = await plotly_generator.generate_plotly_visualization(viz_spec)
                # render_result is a plotly.graph_objects.Figure
                visualization_output_details = {"type": "plotly", "content": render_result}
                print("Generated Plotly visualization object.")

            elif viz_spec.type == "manim":
                 # Generate Manim video and get the path to the file
                 # The spec.content for Manim is expected to have {"scene_code": "..."}
                 render_result_path = await manim_renderer.render_scene(viz_spec.content)
                 # render_result_path is expected to be the path relative to runtime/cache
                 visualization_output_details = {"type": "video", "content": f"/static/{render_result_path}"} # Prepend /static for Gradio serving
                 print(f"Generated Manim video path: {visualization_output_details['content']}")

            elif viz_spec.type == "text_explanation":
                 # No visualization needed, just text
                 explanation_text = viz_spec.explanation
                 visualization_output_details = None
                 print("LLM requested text explanation only.")

            else:
                 # Handle unknown visualization types returned by LLM
                 explanation_text = f"LLM requested unknown visualization type: {viz_spec.type}.\n\n" + explanation_text
                 visualization_output_details = None
                 print(f"LLM returned unknown visualization type: {viz_spec.type}")

        except Exception as e:
            # Handle errors during the rendering process
            error_msg = f"Error generating visualization ({viz_spec.type}): {e}\n{traceback.format_exc()}"
            print(error_msg)
            explanation_text = f"An error occurred while creating the visualization: {e}\n\n" + explanation_text # Prepend error to explanation
            visualization_output_details = None # Ensure no partial visualization is shown


        # Update context with the assistant's explanation and visualization details
        # Add the explanation as an assistant message
        await context_protocol.add_message(session_id, "assistant", explanation_text)

        # Update context with the spec and render output
        await context_protocol.update_context(session_id, {
             "last_visualization_spec": viz_spec, # Store the Pydantic spec object
             "last_render_output": visualization_output_details.get('content') if visualization_output_details else None # Store the path/figure/etc.
        })

    else: # LLM returned plain text (not a VisualizationSpec instance)
        explanation_text = llm_output
        visualization_output_details = None
        # Create a basic text_explanation spec for context history
        viz_spec = VisualizationSpec(type="text_explanation", explanation=explanation_text)

        # Add assistant message to context
        await context_protocol.add_message(session_id, "assistant", explanation_text)
        await context_protocol.update_context(session_id, {
            "last_visualization_spec": viz_spec,
            "last_render_output": None
        })


    # --- Update Gradio UI Components ---

    # Update the last assistant message in Gradio history with the final explanation text
    history[-1][1] = explanation_text

    # Prepare components to update based on visualization_output_details
    explanation_comp_update = gr.Markdown(value=explanation_text, visible=True)
    html_comp_update = gr.HTML(value="", visible=False)
    plot_comp_update = gr.Plot(value=None, visible=False)
    video_comp_update = gr.Video(value=None, visible=False)


    if visualization_output_details:
        viz_type = visualization_output_details["type"]
        viz_content = visualization_output_details["content"]

        if viz_type == "html":
            # Embed the generated HTML file in an iframe
            # The src must be relative to the Gradio app's root or static files mount point
            # Assumes 'runtime/cache' is mounted at '/static'
            if viz_content: # Check if html_path was generated
                 html_comp_update = gr.HTML(value=f'<iframe src="{viz_content}" width="100%" height="400px" sandbox="allow-scripts allow-same-origin allow-forms"></iframe>', visible=True)
            else:
                 # Handle case where JS generation failed but no exception was raised
                 explanation_comp_update.value += "\n\n*Error: Could not generate interactive HTML.*"

        elif viz_type == "plotly":
            # Gradio Plot component directly accepts a Plotly figure object
            if viz_content: # Check if figure object was created
                 plot_comp_update = gr.Plot(value=viz_content, visible=True)
            else:
                 explanation_comp_update.value += "\n\n*Error: Could not generate Plotly figure.*"


        elif viz_type == "video":
            # Gradio Video component accepts a file path or URL
            # Use the static URL path determined during rendering
            if viz_content: # Check if video path was returned
                video_comp_update = gr.Video(value=viz_content, visible=True)
            else:
                 explanation_comp_update.value += "\n\n*Error: Could not generate video.*"


    # Return the updated components.
    # The order MUST match the order in the .change() or .click() output list.
    return history, explanation_comp_update, html_comp_update, plot_comp_update, video_comp_update, session_id


# --- Gradio Interface Layout ---

def create_interface():
    """Creates the Gradio Blocks interface."""
    # Use a state object to hold the session ID.
    # Initial value is generated when the Gradio state component is created.
    # We will pass this state component to the handler function.

    with gr.Blocks(
        title="Visual Learning App",
        theme=gr.themes.Soft(), # Use a pleasant theme
        css="""
        .gradio-container {
            max-width: 1200px;
            margin: auto;
            padding: 20px;
        }
        .chat-container {
            height: 500px; /* Make chatbot height predictable */
        }
        #chatbot {
            height: 400px !important; /* Ensure chatbot has fixed height */
            overflow-y: auto !important; /* Add scroll if needed */
        }
        .gr-plot {
            height: 400px !important; /* Give plot a standard height */
        }
         .gr-video {
            max-height: 400px; /* Limit video height */
            width: 100%; /* Make video responsive */
         }
        iframe {
            width: 100%;
            height: 400px; /* Give iframe a standard height */
            border: none; /* Remove default iframe border */
        }
        .explanation-box {
            margin-top: 15px;
            padding: 15px;
            border: 1px solid #e0e0e0;
            border-radius: 5px;
            background-color: #f9f9f9;
        }
        """
    ) as visual_learning_app:

        gr.Markdown("# ✨ Visual Learning App")
        gr.Markdown("Ask questions and visualize concepts using AI.")

        # Use gr.State to manage the session ID across interactions
        # The value will be passed to the handler function and returned.
        # We initialize it with a new ID using lambda
        session_id_state = gr.State(value=create_session_id)

        # Chat history display
        chatbot = gr.Chatbot(
            value=[], # Initialize with empty history
            height=400,
            label="Conversation",
            show_label=True,
            container=True,
            bubble_full_width=False,
            elem_id="chatbot" # Add ID for CSS
        )

        # Input area
        with gr.Row():
            with gr.Column(scale=4):
                message_input = gr.Textbox(
                    placeholder="Ask me anything or request a mathematical visualization (e.g., 'Plot sin(x) from -pi to pi' or 'What is linear regression?')...",
                    label="Message",
                    lines=2,
                    container=False # Use container=False as it's in a Row/Column already
                )

            with gr.Column(scale=1):
                # File upload is removed for simplicity in this direct integration,
                # as handling file content passing to LLM is complex.
                # If needed, this would require reading file content in Gradio handler
                # and passing it to LLM via messages/tools/etc.
                # file_upload = gr.File(label="Attach Files", file_count="multiple")
                send_btn = gr.Button("Send", variant="primary", scale=1)

        # Clear chat button
        clear_btn = gr.Button("Clear Chat")

        # Output area for explanation (Markdown) and Visualization (various components)
        # Use variables to control visibility dynamically
        explanation_visible = gr.Variable(False) # Will be set True when explanation is available
        html_viz_visible = gr.Variable(False)
        plot_viz_visible = gr.Variable(False)
        video_viz_visible = gr.Variable(False)

        # Explanation output area
        explanation_output = gr.Markdown(visible=explanation_visible, elem_classes="explanation-box")

        # Visualization output area - Use a column to stack potential visualization outputs
        # Only one should be made visible at a time by the handler function.
        with gr.Column(visible=True) as visualization_output_area:
             # gr.HTML to display interactive JS visualizations (embedded in an iframe)
             html_visualization = gr.HTML(visible=html_viz_visible)

             # gr.Plot for Plotly visualizations
             plotly_visualization = gr.Plot(visible=plot_viz_visible)

             # gr.Video for Manim animations
             video_visualization = gr.Video(visible=video_viz_visible)

             # Add other potential output components here (e.g., gr.DataFrame for tables)


        # --- Event Handlers ---

        # Define the outputs that the handle_user_input function will return IN ORDER
        output_components = [
            chatbot,             # Updated history
            explanation_output,  # Updated explanation text and visibility (will be True if text exists)
            html_visualization,  # Updated HTML content and visibility
            plotly_visualization,# Updated Plotly figure and visibility
            video_visualization, # Updated Video path and visibility
            session_id_state     # Ensure session ID state is returned (optional, but good practice)
        ]

        # When the send button is clicked
        send_btn.click(
            fn=handle_user_input,
            inputs=[message_input, chatbot, session_id_state],
            outputs=output_components
        )

        # When the user presses Enter in the textbox
        message_input.submit(
            fn=handle_user_input,
            inputs=[message_input, chatbot, session_id_state],
            outputs=output_components
        )

        # Clear chat functionality
        # This clears the Gradio chatbot history and resets the session context
        async def clear_chat_handler(session_id):
             print(f"Clearing session: {session_id}")
             if session_id:
                 try:
                     await context_protocol.delete_context(session_id)
                 except Exception as e:
                     print(f"Error deleting session context: {e}")
             # Return empty history and a *new* session ID
             new_session_id = create_session_id()
             print(f"New session created after clear: {new_session_id}")

             # Also hide visualization components
             return [], gr.Markdown(visible=False, value=""), gr.HTML(visible=False, value=""), gr.Plot(visible=False, value=None), gr.Video(visible=False, value=None), new_session_id

        clear_btn.click(
            fn=clear_chat_handler,
            inputs=[session_id_state], # Need the current session ID to delete
            outputs=[chatbot, explanation_output, html_visualization, plotly_visualization, video_visualization, session_id_state]
        )

    return visual_learning_app

# --- Application Startup ---

# We need to run the async initialization before launching the Gradio app.
# Gradio's launch function runs the app loop, so we need an entry point
# that handles the async setup first.

async def main():
    """Main function to initialize backend and launch Gradio."""
    await initialize_backend()
    interface = create_interface()

    # Define static file serving.
    # In HF Spaces, you might configure this via the Space settings,
    # mapping a directory (like runtime/cache) to /static.
    # For local development, use the static_files parameter in launch.
    static_dir = Path("runtime/cache")
    static_dir.mkdir(parents=True, exist_ok=True) # Ensure static cache directory exists

    # Manim and HTML generators save files inside runtime/cache/manim/ and runtime/cache/generated_assets/
    # These should be served under /static/manim and /static/generated_assets respectively.
    # The renderers return paths relative to runtime/cache, like "manim/video.mp4" or "generated_assets/html/viz.html".
    # When constructing the URL in handle_user_input, we prepend "/static/".

    print(f"Serving static files from {static_dir} under the /static/ route.")

    interface.launch(
        server_name="0.0.0.0", # Listen on all interfaces
        server_port=7860,     # Default Gradio port
        share=False,          # Set to True to get a shareable link
        debug=True,           # Set to False for production
        # Configure static file serving for local testing
        static_files={"/static": str(static_dir)}
    )

# --- Entry Point ---
if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())