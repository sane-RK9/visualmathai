import modal
import asyncio
from typing import Dict, Any, List, Union

# --- Modal App Definition ---
# We define a single app object. Other Modal runner files can look this up
# This approach keeps all our backend functions under one logical application.
app = modal.App(
    name="VisualMathAi-backend"
)

# --- Remote Function Definition ---
# This decorator turns the Python function into a serverless function on Modal.
@app.function(
    secrets=[modal.Secret.from_dotenv()],
    
    pip_install=["openai", "anthropic", "pydantic"],
    
    # Set resource limits and timeouts.
    timeout=120,  # Allow up to 2 minutes for an LLM response.
    cpu=1,        # This function is not CPU-intensive.
    memory=1024,  # Request 1GB of memory.
    
    # Keep the container warm for a few minutes to reduce cold start latency.
    keep_warm=1,
    
    # Allow multiple concurrent calls to this function.
    allow_concurrent_inputs=10,
)
def generate_llm_response(provider_name: str, messages: List[Dict], context_dict: Dict) -> Union[str, Dict]:
    """
    Runs LLM inference securely on Modal's infrastructure.

    This function is called remotely from the FastAPI backend. It initializes the
    appropriate LLM client inside the secure Modal environment (where API keys
    are present) and returns the generated response.

    Args:
        provider_name: The name of the LLM provider to use (e.g., "openai", "claude").
        messages: The chat history, formatted as a list of dictionaries.
        context_dict: The current LearningContext, serialized as a dictionary.

    Returns:
        The LLM's response, which can be either a plain string or a dictionary
        representing a serialized VisualizationSpec.
    """
    # This code runs *inside the Modal container*.
    print(f"Modal function started for provider: {provider_name}")

    # --- Re-import and Re-create Objects Inside the Remote Environment ---
    from backend.app.api.llm.router import LLMRouter as InternalLLMRouter
    from backend.app.models.context import LearningContext, VisualizationSpec

    # The LLMRouter and its providers are initialized here, inside the Modal container.
    try:
        llm_router = InternalLLMRouter()
    except Exception as e:
        # Handle initialization errors (e.g., missing dependencies in pip_install)
        print(f"Error initializing LLM router on Modal: {e}")
        raise

    # Re-create the Pydantic model from the dictionary passed over the network.
    try:
        context = LearningContext(**context_dict)
    except Exception as e:
        print(f"Error validating context data on Modal: {e}")
        raise ValueError(f"Invalid context data received: {e}") from e

    # --- Execute the Core Logic ---
    # Since the Modal function entrypoint is synchronous but our `route_request`
    # is async, we use `asyncio.run` to execute it. 
    async def _run_async_logic():
        return await llm_router.route_request(
            provider_name=provider_name,
            messages=messages,
            context=context
        )

    try:
        result = asyncio.run(_run_async_logic())
    except Exception as e:
        # Catch errors from the LLM provider API calls
        print(f"Error during LLM API call on Modal: {e}")
        raise
        
    print("Modal function finished successfully.")

    # --- Serialize the Return Value ---
    # If the result is a Pydantic model (VisualizationSpec), we must convert it
    # to a dictionary before returning it, as Modal needs to serialize the output.
    if isinstance(result, VisualizationSpec):
        return result.model_dump()

    return result