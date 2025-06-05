import asyncio 
from typing import Dict, Any, Optional, Union
from backend.context.memory import SQLiteContextStorage, initialize_context_storage
from backend.models.context import LearningContext, ContextMessage, UIState, VisualizationSpec, create_session_id

# Import datetime for timestamps if not already handled by Pydantic defaults
from datetime import datetime

class ContextProtocol:
    """
    Manages the stateful context for learning sessions, abstracting the storage layer.
    Provides methods to get, update, and add information to a session's context.
    """
    def __init__(self, storage_backend: str = "sqlite"):
        """
        Initializes the ContextProtocol with a specific storage backend.

        Args:
            storage_backend: The name of the storage backend to use ('sqlite', 'memory', etc.).
        """
        # Initialize the chosen storage backend
        if storage_backend == "sqlite":
            self._storage = SQLiteContextStorage()
            self._storage_backend_name = "sqlite"
        # elif storage_backend == "redis":
        #     self._storage = RedisContextStorage(...) # Placeholder for Redis
        #     self._storage_backend_name = "redis"
        else:
            # Fallback to a simple in-memory dictionary if no valid backend specified
            print(f"Warning: Unknown or unsupported storage backend '{storage_backend}'. Using in-memory.")
            self._storage_backend_name = "memory"
            class InMemoryStorage: # Define a simple in-memory adapter implementing the storage interface
                 def __init__(self):
                     self._contexts: Dict[str, LearningContext] = {}
                 async def load_context(self, session_id: str) -> Optional[LearningContext]:
                     # Simulate async I/O delay
                     await asyncio.sleep(0.001)
                     return self._contexts.get(session_id)
                 async def save_context(self, context: LearningContext):
                     # Simulate async I/O delay
                     await asyncio.sleep(0.001)
                     # Create a copy to avoid issues if the original object is modified elsewhere
                     self._contexts[context.session_id] = context.model_copy(deep=True)
                 async def delete_context(self, session_id: str):
                     # Simulate async I/O delay
                     await asyncio.sleep(0.001)
                     self._contexts.pop(session_id, None)
                 # Add dummy init_db if storage requires it, or handle in protocol init
                 async def _init_db(self):
                     print("In-memory storage needs no DB initialization.")


            self._storage = InMemoryStorage()

        print(f"ContextProtocol initialized using '{self._storage_backend_name}' storage backend.")


    async def get_context(self, session_id: str) -> LearningContext:
        """
        Retrieves a context for a session from storage. If not found, creates a new one
        and saves it before returning.

        Args:
            session_id: The unique identifier for the session.

        Returns:
            The LearningContext object for the session.
        """
        context = await self._storage.load_context(session_id)
        if context is None:
            # If context not found in storage, create a new one
            # Use the create_session_id default factory from the model if session_id is None,
            # but typically get_context is called *with* a session_id provided by the UI/session management.
            # Let's assume session_id is always provided here.
            new_context = LearningContext(session_id=session_id)
            await self._storage.save_context(new_context) # Save the newly created context
            print(f"Created and saved new context for session: {session_id}")
            return new_context
        # print(f"Retrieved context for session: {session_id}") # Optional: verbose logging
        return context


    async def update_context(self, session_id: str, updates: Dict[str, Any]) -> LearningContext:
        """
        Updates the context with new information based on a dictionary of updates
        and persists the changes. Handles merging into nested Pydantic models.

        Args:
            session_id: The unique identifier for the session.
            updates: A dictionary containing fields to update. Can include nested
                     structure matching the LearningContext model (e.g., {'ui_state': {'variables': {'a': 5}}}).

        Returns:
            The updated LearningContext object.
        """
        context = await self.get_context(session_id) # Load existing context

        # Apply updates using Pydantic's update capabilities for safety and structure
        # A simple way is to dump to dict, apply updates, then validate back to Pydantic.
        context_dict = context.model_dump() # Get dictionary representation

        # Use a simple recursive update function or similar logic for nested dicts
        # Pydantic v2's model_copy(update=...) is cleaner if applicable, but needs careful use.
        # Let's use a deep merge for simplicity, but acknowledge Pydantic methods might be better.
        def deep_update(source_dict, updates_dict):
            for key, value in updates_dict.items():
                if isinstance(value, dict) and key in source_dict and isinstance(source_dict[key], dict):
                    # Recursively update if both are dictionaries
                    source_dict[key] = deep_update(source_dict[key], value)
                # elif isinstance(value, list) and key in source_dict and isinstance(source_dict[key], list):
                #     # Decide how to handle lists: replace, extend, merge? Replace for now.
                #     source_dict[key] = value
                else:
                    # Otherwise, set or overwrite the value
                    source_dict[key] = value
            return source_dict

        updated_dict_data = deep_update(context_dict, updates)

        # Create a new Pydantic instance from the updated dictionary data
        # This handles validation and potential type casting from dict values
        try:
            updated_context = LearningContext(**updated_dict_data)
            updated_context.updated_at = datetime.now() # Ensure updated_at is current
        except Exception as e:
             print(f"Error validating updated context data for session {session_id}: {e}")
             # Depending on requirements, you might raise an error or return the original context
             raise ValueError(f"Invalid update data provided: {e}") from e


        # Save the updated context
        await self._storage.save_context(updated_context)
        # print(f"Context updated and saved for session: {session_id}") # Optional: verbose logging
        return updated_context


    async def add_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> LearningContext:
        """
        Adds a message to the context's message history and persists it.

        Args:
            session_id: The unique identifier for the session.
            role: The role of the message sender ("user", "assistant", etc.).
            content: The message content.
            metadata: Optional metadata for the message.

        Returns:
            The updated LearningContext object.
        """
        context = await self.get_context(session_id) # Load existing context
        context.add_message(role=role, content=content, metadata=metadata) # Add message using Pydantic model method
        await self._storage.save_context(context) # Save the modified context object
        # print(f"Message added and context saved for session: {session_id}") # Optional: verbose logging
        return context

    async def update_ui_variables(self, session_id: str, variables: Dict[str, Any]) -> LearningContext:
        """
        Updates UI variables within the context's ui_state and persists the change.

        Args:
            session_id: The unique identifier for the session.
            variables: A dictionary of variable key-value pairs to update in ui_state.variables.

        Returns:
            The updated LearningContext object.
        """
        context = await self.get_context(session_id) # Load existing context
        context.update_ui_variables(variables) # Update variables using Pydantic model method
        await self._storage.save_context(context) # Save the modified context object
        # print(f"UI variables updated and context saved for session: {session_id} -> {context.ui_state.variables}") # Optional: verbose logging
        return context

    async def delete_context(self, session_id: str):
        """
        Deletes a context from storage.

        Args:
            session_id: The unique identifier for the session to delete.
        """
        await self._storage.delete_context(session_id)
        print(f"Context deleted for session: {session_id}")


