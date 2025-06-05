#!/bin/bash

# setup.sh
# Quick setup script for the Visual Learning App project.
# Automates creating a virtual environment and installing dependencies.

# Exit immediately if a command exits with a non-zero status.
set -e

echo "🚀 Starting VisualMathAi project setup..."

# --- Step 1: Create .env file ---
echo "📄 Checking for .env file..."
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "   .env file not found. Copying .env.example to .env"
        cp .env.example .env
        echo "   Please edit the .env file to add your API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)."
        # Open .env for editing (optional, depends on user's OS/pref)
        # Example for macOS/Linux: open .env || nano .env
    else
        echo "Error: .env.example not found. Cannot create .env file."
        exit 1
    fi
else
    echo "   .env file already exists. Skipping creation."
fi

# --- Step 2: Create Python Virtual Environment ---
echo "🐍 Setting up Python virtual environment..."
if [ -d "venv" ]; then
    echo "   Virtual environment 'venv' already exists. Skipping creation."
else
    # Check if python3 is available
    if command -v python3 &>/dev/null; then
        python3 -m venv venv
        echo "   Virtual environment 'venv' created."
    elif command -v python &>/dev/null; then
        # Fallback to 'python' if 'python3' is not the default
        python -m venv venv
         echo "   Virtual environment 'venv' created using 'python'."
    else
        echo "Error: python3 or python command not found. Please install Python 3.8+."
        exit 1
    fi
fi

# --- Step 3: Activate Virtual Environment and Install Dependencies ---
echo "📦 Activating virtual environment and installing dependencies..."
source venv/bin/activate

# Ensure pip is up-to-date inside the venv
pip install --upgrade pip

# Install dependencies from requirements.txt
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "   Python dependencies installed from requirements.txt."
else
    echo "Error: requirements.txt not found."
    exit 1
fi

# --- Step 4: Create runtime directories ---
echo "📁 Creating runtime directories..."
mkdir -p runtime/cache/manim
mkdir -p runtime/cache/generated_assets/html
mkdir -p runtime/sandbox/temp
echo "   Runtime directories created."

# --- Step 5: Final Instructions ---
echo ""
echo "✨ Setup complete!"
echo "You can now activate the virtual environment in your terminal:"
echo "source venv/bin/activate"
echo ""
echo "Then you can run the application:"
echo "python app/gradio_app.py"
echo ""
echo "Note: Manim requires additional system dependencies (like LaTeX and FFmpeg) not included in Python packages. Please ensure these are installed on your system if you encounter errors with Manim rendering."

# Deactivate the venv used *within* the script (does not affect the user's shell)
deactivate