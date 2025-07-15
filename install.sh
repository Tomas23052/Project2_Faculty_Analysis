#!/bin/bash

# IPT Faculty Performance Assessment System Installation Script
echo "🚀 IPT Faculty Performance Assessment System"
echo "============================================="

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check Python version
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "🐍 Python version: $python_version"

# Check if virtual environment already exists
if [ -d "venv" ]; then
    echo "✅ Virtual environment already exists"
else
    echo "🔧 Creating virtual environment..."
    python3 -m venv venv
    
    if [ $? -eq 0 ]; then
        echo "✅ Virtual environment created successfully"
    else
        echo "❌ Failed to create virtual environment"
        echo "Please install python3-venv: sudo apt install python3-venv"
        exit 1
    fi
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📚 Installing requirements..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Requirements installed successfully"
else
    echo "❌ Failed to install requirements"
    exit 1
fi

# Create necessary directories
echo "📂 Creating project directories..."
mkdir -p data/raw
mkdir -p notebooks

# Run setup verification
echo "🧪 Running setup verification..."
python setup.py

echo ""
echo "🎉 Installation completed successfully!"
echo ""
echo "To use the project:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Place IPT HR PDF files in data/raw/ directory"
echo "3. Run data collection: python src/collect_all_data.py"
echo "4. Launch dashboard: streamlit run src/dashboard.py"
echo ""
echo "To deactivate virtual environment later: deactivate"
