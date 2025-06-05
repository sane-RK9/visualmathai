from abc import ABC, abstractmethod
from typing import Dict, Any, List, Union
import os 
from backend.models.context import LearningContext, VisualizationSpec
# Import the concrete provider classes
from .openai_client import OpenAIProvider
from .claude_client import ClaudeProvider


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate_response(self, messages: List[Dict], context: LearningContext) -> Union[str, VisualizationSpec]:
        """
        Generates a response from the LLM. Can return a simple string (chat response)
        or a structured VisualizationSpec if the request implies a visualization.
        Messages should be formatted appropriate for the specific LLM API.
        """
        pass

    # Removed the generate_code abstract method, as the LLM is now expected
    # to return a structured spec via generate_response.
    # If specific providers have helper methods, they can implement them,
    # but it's not part of the required interface for the router.


class LLMRouter:
    """Routes LLM requests to the appropriate provider."""

    def __init__(self):
        """Initializes available LLM providers."""
        self.providers: Dict[str, LLMProvider] = {}

        # Initialize providers based on availability/config
        # Providers should handle their own API key checking
        try:
            self.providers["claude"] = ClaudeProvider()
            print("Initialized ClaudeProvider.")
        except ValueError as e:
             print(f"ClaudeProvider not initialized: {e}")

        try:
            self.providers["openai"] = OpenAIProvider()
            print("Initialized OpenAIProvider.")
        except ValueError as e:
            print(f"OpenAIProvider not initialized: {e}")

        if not self.providers:
            print("Warning: No LLM providers were successfully initialized!")


    async def route_request(self, provider_name: str, messages: List[Dict], context: LearningContext) -> Union[str, VisualizationSpec]:
        """
        Routes a request to the specified LLM provider.

        Args:
            provider_name: The name of the LLM provider to use (e.g., "openai", "claude").
            messages: The list of message history for the LLM (in a format compatible
                      with the provider, though provider methods might adapt).
            context: The current LearningContext for the session.

        Returns:
            A string (chat response) or a VisualizationSpec object.

        Raises:
            ValueError: If the requested provider is not available.
            Exception: Propagates exceptions from the LLM provider's generate_response method.
        """
        provider = self.providers.get(provider_name.lower())
        if not provider:
            # Fallback if the requested provider isn't available but others are
            if self.providers:
                 default_provider_name = list(self.providers.keys())[0]
                 print(f"Warning: Provider '{provider_name}' not found. Using default: '{default_provider_name}'.")
                 provider = self.providers[default_provider_name]
            else:
                raise ValueError(f"No LLM providers are available. Cannot route request for '{provider_name}'.")

        # Call the single generate_response method
        return await provider.generate_response(messages=messages, context=context)

    # No need for a separate route_code method anymore, as generate_response
    # handles both chat and structured spec output.