from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Visual Learning API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# LLM Interaction
@app.post("/api/chat/{session_id}")
async def chat_with_llm(session_id: str, request: ChatRequest):
    context = await context_protocol.get_context(session_id)
    await context_protocol.add_message(session_id, "user", request.message)
    
    # Route to appropriate LLM
    response = await llm_router.route_request(
        provider=request.provider,
        request_type="chat",
        messages=[{"role": msg.role, "content": msg.content} for msg in context.messages],
        context=context
    )
    
    await context_protocol.add_message(session_id, "assistant", response)
    return {"response": response}

# Generate Interactive Component
@app.post("/api/generate/{session_id}")
async def generate_visualization(session_id: str, request: GenerateRequest):
    context = await context_protocol.get_context(session_id)
    
    if request.type == "interactive":
        js_gen = InteractiveJSGenerator()
        code = await js_gen.generate_interactive_visualization(
            function_expr=request.function,
            parameters=request.parameters
        )
    elif request.type == "manim":
        manim_renderer = ManimRenderer()
        video_path = await manim_renderer.render_scene(request.scene_code)
        return {"video_url": f"/static/{video_path}"}
    
    # Update context with generated code
    await context_protocol.update_context(session_id, {
        "generated_code": code,
        "last_render_id": f"render_{datetime.now().timestamp()}"
    })
    
    return {"code": code, "session_context": context}

# WebSocket for real-time updates
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data["type"] == "variable_update":
                # Update UI state in real-time
                await context_protocol.update_context(session_id, {
                    "ui_state": {"variables": message_data["variables"]}
                })
                
                # Broadcast to other connected clients
                await websocket.send_text(json.dumps({
                    "type": "state_sync",
                    "variables": message_data["variables"]
                }))
                
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()