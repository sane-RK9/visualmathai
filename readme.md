# VisualMathAI

An advanced, interactive web application that combines a conversational AI with dynamic visualization capabilities. Users can explore complex mathematical and scientific concepts by asking questions and requesting the AI to generate on-the-fly graphs, animations, and interactive diagrams.

The project features a sophisticated three-tier architecture: a lightweight Gradio frontend, a robust FastAPI backend for application logic, and a scalable Modal cloud backend for secure, resource-intensive tasks like LLM inference and Manim rendering.

## ✨ Features

*   **Conversational AI Interface:** Chat with an AI assistant powered by state-of-the-art models from OpenAI or Anthropic.
*   **On-Demand Visualization:** Request the AI to generate a variety of visual aids based on your prompts.
*   **Multi-Modal Output:**
    *   **Interactive JS:** Dynamic charts with real-time controls (sliders, inputs).
    *   **Plotly:** High-quality static and interactive 2D/3D plots.
    *   **Manim:** Broadcast-quality mathematical animations rendered as videos.
*   **Persistent Sessions:** Conversation history and context are saved, allowing for follow-up questions and multi-turn interactions.
*   **Scalable & Secure Backend:** Heavy tasks are offloaded to a serverless cloud backend (Modal), ensuring the application remains responsive and secure. Sandboxed execution for rendering protects the system.

## 🏗️ Architecture

The application is built on a modern, distributed three-tier architecture for scalability, security, and clear separation of concerns.

```
┌──────────────────────────┐       ┌───────────────────────────────┐       ┌──────────────────────────────────┐
│  Gradio Frontend Client  │       │   FastAPI Backend Server      │       │     Modal Serverless Backend     │
│  (main.py)               ├─HTTP─►│   (backend/)                  ├─RPC──►│       (modal_runners/)           │
│                          │       │                               │       │                                  │
│ - Renders UI             │       │ - Manages Context (SQLite)    │       │ - Runs LLM Inference (on GPU)    │
│ - Sends User Input       │       │ - Orchestrates Calls to Modal │       │ - Renders Manim (Sandboxed)      │
│ - Displays Visuals       │       │ - Serves Static Assets        │       │                                  │
└──────────────────────────┘       └───────────────────────────────┘       └──────────────────────────────────┘
```

1.  **Gradio Frontend (`main.py`):** A lightweight client application that provides the user interface. It makes HTTP API calls to the FastAPI backend and is responsible for rendering the final text and visualizations.
2.  **FastAPI Backend (`backend/`):** The central application server. It exposes a REST API, manages session state and context using a SQLite database, and acts as an orchestrator. It does **not** perform heavy computations itself; instead, it calls the Modal backend.
3.  **Modal Serverless Backend (`modal_runners/`):** A set of powerful, ephemeral cloud functions for resource-intensive tasks.
    *   **LLM Inference:** An endpoint that securely handles API calls to OpenAI/Anthropic, keeping API keys out of the main backend server. Can be deployed on GPUs for large local models.
    *   **Manim Rendering:** A sandboxed endpoint that takes Manim scene code, renders it in a secure container with all necessary dependencies (LaTeX, FFmpeg), and returns the resulting video.

## 📁 Project Structure

```
visual-learning-app/
├── main.py                 # Gradio Frontend Client application
├── requirements.txt        # Dependencies for the Gradio Frontend (gradio, httpx)
│
├── backend/                # FastAPI Backend Server application
│   ├── app/                # Main source code for the backend
│   │   ├── api/            # API endpoint logic and business logic modules
│   │   ├── core/           # Core components like configuration
│   │   ├── models/         # Pydantic data models
│   │   └── main.py         # FastAPI app entry point
│   └── requirements.txt    # Dependencies for the Backend (fastapi, modal, etc.)
│
├── modal_runners/          # Code for functions deployed to Modal
│   ├── manim_runner.py     # Defines the remote Manim rendering function
│   └── llm_inference.py    # Defines the remote LLM inference function
│
├── config/                 # Deployment configurations
│   ├── docker/
│   └── nginx/
│
├── runtime/                # Directory for runtime-generated files (cache, db)
│
├── .env                    # Local environment variables (API keys)
├── README.md
└── setup.sh                # Automated setup script
```

## 🚀 Getting Started

This project involves three main components: the Gradio Frontend, the FastAPI Backend, and the Modal Backend.

### Prerequisites

*   Python 3.9+
*   [Modal CLI](https://modal.com/docs/guide/local-development#installing-the-`modal`-cli) installed and configured (`modal token new`).
*   Manim system dependencies (for local testing, if desired): [FFmpeg and LaTeX](https://docs.manim.community/en/stable/installation.html).
*   An active `.env` file with API keys (see next step).

### Local Development Setup

Follow these steps to run the full application locally.

**1. Initial Setup**

First, clone the repository and run the setup script. This will prepare your environment variables and install Python dependencies for both frontend and backend.

```bash
git clone <repository_url>
cd visual-learning-app
./setup.sh
```
After running, **edit the newly created `.env` file** to add your `OPENAI_API_KEY` and/or `ANTHROPIC_API_KEY`.

**2. Deploy the Modal Backend**

The resource-intensive parts of the application run on Modal's serverless platform. Deploy them with a single command:

```bash
# This command deploys all functions defined in the modal_runners directory.
# It will build a custom Docker image with Manim on the first run.
modal deploy modal_runners/llm_inference.py
```
*(Note: Since both runner files look up the same app name, deploying one should be sufficient to register all functions under that app.)*

**3. Run the FastAPI Backend Server**

In a new terminal, navigate to the `backend` directory, activate the virtual environment, and start the Uvicorn server.

```bash
# Terminal 1: FastAPI Backend
cd backend/
source ../venv/bin/activate  # Activate the shared venv from the root
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**4. Run the Gradio Frontend Client**

Finally, in another terminal, start the Gradio UI.

```bash
# Terminal 2: Gradio Frontend
source venv/bin/activate  # Activate the venv in the root directory
python main.py
```

You can now access the Gradio interface at `http://127.0.0.1:7860` (or the URL provided by Gradio).

## ☁️ Deployment

*   **Modal:** The backend functions are deployed via the `modal deploy` command.
*   **FastAPI Backend & Gradio Frontend:** These can be deployed as standard web applications using Docker, cloud services like Google Cloud Run, AWS App Runner, or on a VM behind an Nginx reverse proxy. The provided `Dockerfile.backend` and `docker-compose.yml` can be used as a starting point.

## 🛡️ Security

*   **API Keys:** Handled securely using Modal Secrets. Keys in the local `.env` file are only used for `modal deploy` and are not stored in the FastAPI backend or the Gradio client.
*   **Code Execution:** Manim code is executed within a `modal.Sandbox`, an isolated, secure container, preventing it from accessing the host system.
*   **Web Security:** Standard security practices like CORS configuration are applied in the FastAPI backend.

## ⏭️ Future Enhancements

*   **Streaming LLM Output:** Implement WebSocket support between the FastAPI backend and Gradio frontend to stream LLM responses in real-time.
*   **User Authentication:** Add an authentication layer to manage user-specific session histories.
*   **Advanced Caching:** Implement a Redis cache for LLM responses and other frequently accessed data to reduce latency and cost.
*   **Edit & Rerun:** Allow users to view and edit the generated Manim/JS code and rerun the visualization.

## 🤝 Contributing

We welcome contributions! Please fork the repository and submit a pull request with your changes. (TODO: Add a `CONTRIBUTING.md` file with detailed guidelines).

## 📄 License

This project is licensed under the MIT License - see the `LICENSE.md` file for details.
