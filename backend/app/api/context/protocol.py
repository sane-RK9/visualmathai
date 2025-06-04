class ContextProtocol:
    def __init__(self, storage_backend="memory"):
        self.contexts: Dict[str, LearningContext] = {}
    
    async def get_context(self, session_id: str) -> LearningContext:
        if session_id not in self.contexts:
            self.contexts[session_id] = LearningContext(session_id=session_id)
        return self.contexts[session_id]
    
    async def update_context(self, session_id: str, updates: Dict[str, Any]):
        context = await self.get_context(session_id)
        # Update context with new information
        return context
    
    async def add_message(self, session_id: str, role: str, content: str):
        context = await self.get_context(session_id)
        message = ContextMessage(
            role=role,
            content=content,
            timestamp=datetime.now()
        )
        context.messages.append(message)
        return context