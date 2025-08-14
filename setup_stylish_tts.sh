#!/bin/bash

# Setup script for Stylish-TTS integration
# This script installs dependencies and configures Stylish-TTS for the media center

echo "Setting up Stylish-TTS for Media Center..."

# Check if we're in a container
if [ -f /.dockerenv ]; then
    echo "Running inside Docker container"
    IN_CONTAINER=true
else
    echo "Running on host system"
    IN_CONTAINER=false
fi

# Install Python dependencies for Stylish-TTS
echo "Installing Python dependencies..."
pip install --no-cache-dir \
    torch \
    torchaudio \
    pydub \
    onnx \
    onnxruntime \
    scipy \
    numpy \
    misaki \
    git+https://github.com/CodeLinkIO/Vietnamese-text-normalization.git@main

# Install stylish-tts library in development mode
if [ -d "./stylish-tts/lib" ]; then
    echo "Installing stylish-tts library..."
    pip install -e ./stylish-tts/lib/
else
    echo "Error: stylish-tts/lib directory not found!"
    exit 1
fi

# Verify installation
echo "Verifying Stylish-TTS installation..."
python3 -c "
try:
    from stylish_lib.config_loader import ModelConfig
    from stylish_lib.text_utils import TextCleaner
    from misaki import vi
    from vi_cleaner.vi_cleaner import ViCleaner
    import onnxruntime as ort
    print('✓ All Stylish-TTS dependencies installed successfully')
except ImportError as e:
    print(f'✗ Import error: {e}')
    exit(1)
"

# Check if ONNX model exists
if [ -f "./stylish-tts/stylish_1.onnx" ]; then
    echo "✓ Stylish-TTS ONNX model found"
else
    echo "⚠ Warning: Stylish-TTS ONNX model not found at ./stylish-tts/stylish_1.onnx"
    echo "  Please ensure the trained model is in the correct location"
fi

echo "✓ Stylish-TTS setup completed successfully!"
echo ""
echo "The media center will now use Stylish-TTS for Vietnamese text-to-speech."
echo "You can test it by sending a POST request to /tts endpoint with Vietnamese text."