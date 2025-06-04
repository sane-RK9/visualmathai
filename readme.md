## VisualMathAi

An interactive web application powered by Large Language Models to create dynamic, visual explanations of concepts. Ask questions, explore topics, and interact with generated visualizations like graphs, simulations, or animations.

This project is designed with deployment on platforms like Hugging Face Spaces in mind, leveraging Gradio for the user interface.

## ✨ Features

*   **LLM Interaction:** Chat with an AI assistant powered by models like OpenAI GPT, Anthropic Claude, or local LLMs.
*   **Dynamic Visualizations:** Request the AI to generate interactive graphs, plots, or animations based on your queries.
*   **Interactive Controls:** Manipulate parameters using sliders and inputs in real-time to understand concepts dynamically.
*   **Multi-Modal Output:** Supports generating interactive JavaScript visualizations, Plotly plots, and Manim animations.
*   **Stateful Context:** The application remembers your conversation history and the state of visualizations, allowing for follow-up questions and manipulations.
*   **Safe Code Execution:** Generated code is handled securely to prevent risks.

## 🏗️ Architecture

The application follows a layered architecture, with the core logic centered around the user's interaction context.

```
┌─────────────────────────────────────────────────────────────────┐
│                           Gradio App                              │
│  (UI Definition, Function Handlers, Maps Logic Output to Gradio  │
│   Components)                                                   │
└─────────────┬───────────────────────────────────────────────────┘
              │ Direct Python Calls
┌─────────────┼───────────────────────────────────────────────────┐
│                      Backend Logic Modules                      │
│  (LLM Integration, Context Management, Rendering Logic, Cache,  │
│   Sandbox)                                                      │
└───────────────────────────┬─────────────────────────────────────┘
                            │ (Optional) External Service Call
              ┌─────────────┴─────────────┐
              │    (e.g., Dedicated Manim │
              │       Rendering Service)  │
              └───────────────────────────┘
```

*   **Gradio App:** Handles the user interface, takes user input, triggers backend logic functions, and displays the results using Gradio components (`gr.Textbox` for chat, `gr.HTML` for interactive JS, `gr.Plot`, `gr.Video`).
*   **Backend Logic Modules:** A collection of Python modules containing the core intelligence:
    *   **LLM:** Communicates with various LLM providers, crafts prompts with context, and processes responses, potentially generating structured specifications for visualizations.
    *   **Context:** Manages the state for each user session, including conversation history, UI variable values, and references to generated outputs.
    *   **Render:** Contains logic to translate LLM specifications into concrete visualization outputs (e.g., generates HTML/JS code snippets, prepares data for Plotly, constructs Manim scene commands).
    *   **Cache:** Stores results of expensive operations (like Manim renders) to improve performance.
    *   **Sandbox:** Provides a safe environment for executing generated code snippets.

## 📁 Project Structure

```
visual-learning-app-gradio/
├── app/                         # Main Gradio application script(s)
├── backend_logic/               # Modular Python code for core logic (LLM, Context, Render)
├── runtime/                     # Directories for cached outputs and sandbox files
├── scripts/                     # Helper scripts (e.g., Manim templates)
├── config/                      # Configuration files (e.g., Docker)
├── .env.example                 # Example environment variables
├── README.md
├── requirements.txt             # Python dependencies
└── docker-compose.yml           # (Optional) For local development
```

## 🚀 Quick Start

Follow these steps to get the application running locally.

### Prerequisites

*   Python 3.8+
*   `pip` package manager
*   Optional: Docker and Docker Compose

### 1. Clone the Repository

```bash
git clone <repository_url>
cd visual-learning-app-gradio
```

### 2. Set up Environment Variables

Create a `.env` file in the root directory by copying the example:

```bash
cp .env.example .env
```

Edit the `.env` file to add your API keys (e.g., `OPENAI_API_KEY`) and configure other settings as needed.

### 3. Install Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

### 4. Run the Application

Run the main Gradio application script:

```bash
python app/gradio_app.py
```

The application will start, and you will typically see a local URL (e.g., `http://127.0.0.1:7860`) where you can access the interface in your web browser.

### Running with Docker (Optional)

If you have Docker and Docker Compose installed, you can build and run the application using the provided `docker-compose.yml`:

```bash
docker-compose up --build
```

This will build the necessary images and start the services. Access the application via the port configured in your Nginx or service definition (commonly `http://localhost`).

## ⚙️ Configuration

Application settings are managed via environment variables loaded from the `.env` file using the `backend_logic.core.config` module. Refer to `.env.example` for available variables.

## ☁️ Deployment on Hugging Face Spaces

This application is designed for easy deployment on Hugging Face Spaces. Simply push your code to a new Space configured with the "Gradio" SDK. Ensure your `requirements.txt` is correct and your `.env` secrets are added via the Spaces settings. The `app/gradio_app.py` script will be automatically detected and run by the Gradio SDK.

## 🛡️ Security Considerations

Generated code (especially JavaScript for interactive visualizations) is a potential security risk. The `backend_logic.sandbox` module and the frontend's handling of generated code should prioritize safety. Displaying generated HTML/JS within a sandboxed `<iframe>` is the recommended approach to isolate potential malicious code from the main application.

## ⏭️ Future Enhancements

*   **Session Persistence:** Implement database integration (e.g., SQLite, PostgreSQL, Redis) in `backend_logic.context` to save and restore user sessions and history.
*   **Edit Mode:** Allow users to view and modify the LLM-generated code before execution.
*   **Export Functionality:** Add options to export visualizations (e.g., save plots, download Manim videos).
*   **Advanced Rendering:** Integrate more sophisticated rendering libraries or custom visualization components.
*   **User Authentication:** Implement user accounts to manage personal histories and settings.
*   **Streaming LLM Output:** Integrate Gradio's streaming features for real-time LLM response generation.

##🤝 Contributing

We welcome contributions! Please see the contributing guidelines.

## 📄 License

This project is licensed under the MIT License - see the LICENSE.md file for details.

## 🙏 Acknowledgments

*   Hugging Face and Gradio for the excellent platform and tools.
*   The developers of Manim, Plotly, and other visualization libraries.
*   The researchers and engineers behind the powerful Large Language Models.

