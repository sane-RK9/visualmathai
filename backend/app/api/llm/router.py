from abc import ABC, abstractmethod
from typing import Dict, Any, List

class LLMProvider(ABC):
    @abstractmethod
    async def generate_response(self, messages: List[Dict], context: LearningContext) -> str:
        pass
    
    @abstractmethod
    async def generate_code(self, prompt: str, language: str) -> Dict[str, str]:
        pass

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    async def generate_response(self, messages: List[Dict], context: LearningContext) -> str:
        # Enhanced prompt with context awareness
        system_prompt = f"""
        You are an interactive learning assistant. Generate educational visualizations.
        Current topic: {context.current_topic}
        UI State: {context.ui_state.variables}
        Learning objectives: {context.learning_objectives}
        
        When generating visualizations:
        1. Create interactive HTML/JS code with sliders and controls
        2. Explain concepts step-by-step
        3. Suggest follow-up explorations
        4. Consider the current UI state and variables
        """
        
        response = await self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": system_prompt}] + messages,
            temperature=0.7
        )
        return response.choices[0].message.content

class LLMRouter:
    def __init__(self):
        self.providers = {
            "openai": OpenAIProvider(os.getenv("OPENAI_API_KEY")),
            "claude": ClaudeProvider(os.getenv("ANTHROPIC_API_KEY")),
            "local": LocalLLMProvider(os.getenv("LOCAL_LLM_URL"))
        }
    
    async def route_request(self, provider: str, request_type: str, **kwargs):
        if provider not in self.providers:
            raise ValueError(f"Unknown provider: {provider}")
        
        provider_instance = self.providers[provider]
        
        if request_type == "chat":
            return await provider_instance.generate_response(**kwargs)
        elif request_type == "code":
            return await provider_instance.generate_code(**kwargs)