from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from datetime import datetime

class ContextMessage(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

class UIState(BaseModel):
    variables: Dict[str, Any] = {}
    active_components: List[str] = []
    last_render_id: Optional[str] = None
    viewport: Dict[str, float] = {"width": 800, "height": 600}

class LearningContext(BaseModel):
    session_id: str
    messages: List[ContextMessage] = []
    ui_state: UIState = UIState()
    current_topic: Optional[str] = None
    learning_objectives: List[str] = []
    generated_code: Dict[str, str] = {}  # {"js": "...", "html": "...", "python": "..."}
    render_history: List[str] = []


