from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import json
import asyncio
import hashlib
from datetime import datetime
import openai
import os

app = FastAPI(title="Visual Learning API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for served content
app.mount("/static", StaticFiles(directory="runtime/cache"), name="static")

# Pydantic Models
class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[datetime] = None

class GenerateVisualizationRequest(BaseModel):
    prompt: str
    visualization_type: str = "interactive"  # "interactive", "manim", "plotly"
    parameters: Dict[str, Any] = {}
    provider: str = "openai"  # "openai", "claude", "local"

class ContextUpdate(BaseModel):
    variables: Dict[str, Any] = {}
    ui_state: Dict[str, Any] = {}

# In-memory storage (replace with Redis/DB in production)
class ContextManager:
    def __init__(self):
        self.contexts: Dict[str, Dict] = {}
        self.connections: Dict[str, List[WebSocket]] = {}
    
    def get_context(self, session_id: str) -> Dict:
        if session_id not in self.contexts:
            self.contexts[session_id] = {
                "session_id": session_id,
                "messages": [],
                "variables": {},
                "generated_code": {},
                "last_render": None,
                "created_at": datetime.now()
            }
        return self.contexts[session_id]
    
    def add_message(self, session_id: str, role: str, content: str):
        context = self.get_context(session_id)
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        context["messages"].append(message)
        return context
    
    def update_variables(self, session_id: str, variables: Dict[str, Any]):
        context = self.get_context(session_id)
        context["variables"].update(variables)
        return context
    
    async def broadcast_to_session(self, session_id: str, message: Dict):
        if session_id in self.connections:
            disconnected = []
            for websocket in self.connections[session_id]:
                try:
                    await websocket.send_text(json.dumps(message))
                except:
                    disconnected.append(websocket)
            
            # Clean up disconnected clients
            for ws in disconnected:
                self.connections[session_id].remove(ws)

context_manager = ContextManager()

# LLM Integration
class LLMProvider:
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    async def generate_response(self, messages: List[Dict], context: Dict) -> str:
        # Create enhanced system prompt with context
        system_prompt = f"""
You are an interactive educational assistant that creates visualizations and explanations.

Current Context:
- Session Variables: {context.get('variables', {})}
- Previous Interactions: {len(context.get('messages', []))} messages

When generating visualizations:
1. Create interactive HTML/JavaScript code with controls (sliders, buttons, inputs)
2. Use mathematical functions that can be parameterized
3. Provide clear explanations of concepts
4. Return code in a structured format

For interactive visualizations, return JSON with:
{{
    "explanation": "Clear explanation of the concept",
    "html": "HTML for controls and canvas",
    "javascript": "JavaScript for interactivity and rendering",
    "css": "Optional CSS for styling",
    "parameters": {{"param_name": {{"min": 0, "max": 10, "default": 1, "step": 0.1}}}},
    "functions": ["function_name(x, param1, param2) = expression"]
}}
"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    *messages
                ],
                temperature=0.7,
                max_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating response: {str(e)}"

llm_provider = LLMProvider()

# Interactive Code Generator
class InteractiveCodeGenerator:
    def __init__(self):
        self.templates = {
            "math_visualization": """
<!DOCTYPE html>
<html>
<head>
    <style>
        .controls { margin: 20px 0; }
        .control-group { margin: 10px 0; }
        .control-group label { display: inline-block; width: 150px; }
        .control-group input[type="range"] { width: 200px; }
        .value-display { font-weight: bold; color: #007bff; }
        canvas { border: 1px solid #ccc; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="controls">
        {controls}
    </div>
    <canvas id="canvas" width="800" height="400"></canvas>
    
    <script>
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        
        // Variables
        {variable_declarations}
        
        // Mathematical function
        {math_function}
        
        // Update functions
        {update_functions}
        
        // Drawing function
        function draw() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // Draw axes
            ctx.strokeStyle = '#ddd';
            ctx.lineWidth = 1;
            
            // X-axis
            ctx.beginPath();
            ctx.moveTo(0, canvas.height / 2);
            ctx.lineTo(canvas.width, canvas.height / 2);
            ctx.stroke();
            
            // Y-axis
            ctx.beginPath();
            ctx.moveTo(canvas.width / 2, 0);
            ctx.lineTo(canvas.width / 2, canvas.height);
            ctx.stroke();
            
            // Draw function
            ctx.strokeStyle = '#007bff';
            ctx.lineWidth = 2;
            ctx.beginPath();
            
            const xScale = canvas.width / 20; // -10 to 10
            const yScale = canvas.height / 20; // -10 to 10
            const xOffset = canvas.width / 2;
            const yOffset = canvas.height / 2;
            
            let firstPoint = true;
            for (let x = -10; x <= 10; x += 0.1) {{
                const y = {function_call};
                const canvasX = x * xScale + xOffset;
                const canvasY = yOffset - y * yScale;
                
                if (firstPoint) {{
                    ctx.moveTo(canvasX, canvasY);
                    firstPoint = false;
                }} else {{
                    ctx.lineTo(canvasX, canvasY);
                }}
            }}
            ctx.stroke();
            
            // Draw grid labels
            ctx.fillStyle = '#666';
            ctx.font = '12px Arial';
            for (let i = -10; i <= 10; i += 2) {{
                if (i !== 0) {{
                    // X-axis labels
                    ctx.fillText(i.toString(), i * xScale + xOffset - 5, yOffset + 15);
                    // Y-axis labels
                    ctx.fillText(i.toString(), xOffset + 5, yOffset - i * yScale + 3);
                }}
            }}
        }}
        
        // Initial draw
        draw();
        
        // Send updates to parent if in iframe
        function notifyParent(variable, value) {{
            if (window.parent && window.parent.updateReactState) {{
                window.parent.updateReactState(variable, value);
            }}
        }}
    </script>
</body>
</html>
"""
        }
    
    def generate_math_visualization(self, function_expr: str, parameters: Dict) -> str:
        controls = []
        variable_declarations = []
        update_functions = []
        
        for param_name, config in parameters.items():
            # Generate slider control
            controls.append(f"""
            <div class="control-group">
                <label for="{param_name}">{config.get('label', param_name)}: 
                    <span id="{param_name}_value" class="value-display">{config['default']}</span>
                </label>
                <input type="range" id="{param_name}" 
                       min="{config['min']}" max="{config['max']}" 
                       step="{config['step']}" value="{config['default']}"
                       oninput="update_{param_name}(this.value)">
            </div>
            """)
            
            # Generate variable declaration
            variable_declarations.append(f"let {param_name} = {config['default']};")
            
            # Generate update function
            update_functions.append(f"""
            function update_{param_name}(value) {{
                {param_name} = parseFloat(value);
                document.getElementById('{param_name}_value').textContent = value;
                draw();
                notifyParent('{param_name}', value);
            }}
            """)
        
        return self.templates["math_visualization"].format(
            controls="\n".join(controls),
            variable_declarations="\n        ".join(variable_declarations),
            math_function=f"function mathFunction(x) {{ return {function_expr}; }}",
            update_functions="\n        ".join(update_functions),
            function_call=f"mathFunction(x)"
        )

code_generator = InteractiveCodeGenerator()

# API Routes
@app.get("/")
async def root():
    return {"message": "Visual Learning API is running"}

@app.get("/api/context/{session_id}")
async def get_context(session_id: str):
    context = context_manager.get_context(session_id)
    return context

@app.post("/api/chat/{session_id}")
async def chat_with_llm(session_id: str, message: ChatMessage):
    # Add user message to context
    context = context_manager.add_message(session_id, message.role, message.content)
    
    # Generate LLM response
    messages = [{"role": msg["role"], "content": msg["content"]} 
                for msg in context["messages"]]
    
    response_content = await llm_provider.generate_response(messages, context)
    
    # Add assistant response to context
    context_manager.add_message(session_id, "assistant", response_content)
    
    # Broadcast to connected clients
    await context_manager.broadcast_to_session(session_id, {
        "type": "new_message",
        "message": {
            "role": "assistant",
            "content": response_content,
            "timestamp": datetime.now().isoformat()
        }
    })
    
    return {"response": response_content, "context": context}

@app.post("/api/generate/{session_id}")
async def generate_visualization(session_id: str, request: GenerateVisualizationRequest):
    context = context_manager.get_context(session_id)
    
    if request.visualization_type == "interactive":
        # Parse the request to extract function and parameters
        # This is a simplified example - you'd want more sophisticated parsing
        
        # Example: "visualize sin(x * a) where a can vary from 0 to 5"
        if "sin" in request.prompt.lower():
            function_expr = "Math.sin(x * a)"
            parameters = {
                "a": {"min": 0, "max": 5, "default": 1, "step": 0.1, "label": "Frequency"}
            }
        elif "cos" in request.prompt.lower():
            function_expr = "Math.cos(x * a + b)"
            parameters = {
                "a": {"min": 0, "max": 5, "default": 1, "step": 0.1, "label": "Frequency"},
                "b": {"min": 0, "max": 6.28, "default": 0, "step": 0.1, "label": "Phase"}
            }
        else:
            # Default quadratic
            function_expr = "a * x * x + b * x + c"
            parameters = {
                "a": {"min": -2, "max": 2, "default": 1, "step": 0.1, "label": "a (x²)"},
                "b": {"min": -5, "max": 5, "default": 0, "step": 0.1, "label": "b (x)"},
                "c": {"min": -5, "max": 5, "default": 0, "step": 0.1, "label": "c (constant)"}
            }
        
        # Generate the interactive HTML
        html_code = code_generator.generate_math_visualization(function_expr, parameters)
        
        # Store in context
        context["generated_code"] = {
            "html": html_code,
            "function": function_expr,
            "parameters": parameters,
            "type": "interactive"
        }
        context["last_render"] = datetime.now().isoformat()
        
        # Broadcast to connected clients
        await context_manager.broadcast_to_session(session_id, {
            "type": "new_visualization",
            "code": context["generated_code"]
        })
        
        return {
            "success": True,
            "code": context["generated_code"],
            "session_id": session_id
        }
    
    else:
        return {"error": "Visualization type not supported yet"}

@app.post("/api/context/{session_id}/update")
async def update_context(session_id: str, update: ContextUpdate):
    context = context_manager.update_variables(session_id, update.variables)
    
    # Broadcast variable updates to connected clients
    await context_manager.broadcast_to_session(session_id, {
        "type": "variables_updated",
        "variables": update.variables
    })
    
    return {"success": True, "context": context}

# WebSocket endpoint for real-time updates
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    # Add to connections
    if session_id not in context_manager.connections:
        context_manager.connections[session_id] = []
    context_manager.connections[session_id].append(websocket)
    
    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "variable_update":
                # Update context and broadcast to other clients
                context_manager.update_variables(session_id, message["variables"])
                
                # Broadcast to all other clients in the session
                for ws in context_manager.connections[session_id]:
                    if ws != websocket:
                        try:
                            await ws.send_text(json.dumps({
                                "type": "sync_variables",
                                "variables": message["variables"]
                            }))
                        except:
                            pass
            
            elif message["type"] == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
                
    except WebSocketDisconnect:
        # Remove from connections
        if session_id in context_manager.connections:
            context_manager.connections[session_id].remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Clean up
        if session_id in context_manager.connections:
            try:
                context_manager.connections[session_id].remove(websocket)
            except ValueError:
                pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)