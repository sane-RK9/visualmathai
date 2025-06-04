# Visual Learning App

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