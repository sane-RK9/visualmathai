from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
from backend.app.main import router as api_router
from backend.app.api.context.memory import initialize_context_storage

# --- FastAPI App Initialization ---
# Create the main FastAPI application instance.
# Documentation URLs can be customized or disabled for production.
app = FastAPI(
    title="Visual Learning Backend API",
    description="Provides services for LLM interaction, context management, and visualization rendering.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# --- Middleware Configuration ---
# Configure Cross-Origin Resource Sharing (CORS) to allow requests from the Gradio frontend.
# For development, allowing all origins ("*") is convenient.
# For production, you should restrict this to the specific domain of your frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your frontend's URL in production
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# --- Static File Serving ---
# Create the directory for static files if it doesn't exist.
static_dir = Path("runtime/cache")
static_dir.mkdir(parents=True, exist_ok=True)

# Mount the 'runtime/cache' directory to be served at the '/static' URL path.
# This allows the frontend to access generated files like Manim videos and interactive HTML.
# For example, a file at 'runtime/cache/manim/video.mp4' will be accessible at
# 'http://<backend_url>/static/manim/video.mp4'.
app.mount("/static", StaticFiles(directory=static_dir), name="static")
print(f"Serving static files from '{static_dir.resolve()}' at the '/static' route.")

# --- Application Lifecycle Events ---
@app.on_event("startup")
async def startup_event():
    """
    This function runs once when the FastAPI application starts.
    It's the ideal place for initialization tasks.
    """
    print("FastAPI application starting up...")
    try:
        # Initialize the SQLite database and create necessary tables.
        # This ensures the database is ready before handling any requests.
        await initialize_context_storage()
        print("Database context storage initialized successfully.")
    except Exception as e:
        print(f"Error during startup initialization: {e}")
        # Depending on the severity, you might want to exit the application here.

@app.on_event("shutdown")
def shutdown_event():
    """
    This function runs once when the FastAPI application shuts down.
    Useful for cleanup tasks like closing database connection pools.
    """
    print("FastAPI application shutting down.")
    # Add any cleanup logic here (e.g., closing database connection pools).


# --- API Router Inclusion ---
# Include the main API router from `backend.app.api.main`.
# All endpoints defined in that router will be added to the application
# with the prefix specified here (e.g., "/api/v1").
app.include_router(api_router, prefix="/api")
print("API router included at prefix '/api'.")

# --- Root Endpoint ---
# A simple health check endpoint to confirm the server is running.
@app.get("/", tags=["Health Check"])
async def read_root():
    """
    Root endpoint for health checks.
    """
    return {
        "status": "ok",
        "message": "Welcome to the Visual Learning Backend API!",
        "docs": "/docs"
    }

# Note: The Uvicorn server to run this app is typically managed by a separate
# script or command, not started from within this file.
# For example, you would run: `uvicorn backend.app.main:app --reload`