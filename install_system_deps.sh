#!/bin/bash

# Script cài đặt system dependencies cho Jetson Nano
echo "Installing system dependencies for Media Center on Jetson Nano..."

# Update package list
sudo apt-get update

# Audio players và codecs
echo "Installing audio players and codecs..."
sudo apt-get install -y \
    mpg123 \
    alsa-utils \
    pulseaudio \
    pulseaudio-utils \
    sox \
    ffmpeg

# Text-to-Speech engines
echo "Installing TTS engines..."
sudo apt-get install -y \
    espeak \
    espeak-data \
    festival \
    festival-freebsoft-utils

# Video player cho YouTube (optional)
echo "Installing video player..."
sudo apt-get install -y mpv

# Python development tools
echo "Installing Python development tools..."
sudo apt-get install -y \
    python3-dev \
    python3-pip \
    python3-venv

# Optional: GPU acceleration for video
echo "Installing GPU acceleration libraries..."
sudo apt-get install -y \
    nvidia-l4t-multimedia \
    nvidia-l4t-multimedia-utils

echo "System dependencies installation completed!"
echo ""
echo "Next steps:"
echo "1. pip install -r requirements.txt"
echo "2. Test audio: speaker-test -t wav -c 2"
echo "3. Test TTS: espeak 'Hello World'"
echo "4. Test yt-dlp: yt-dlp --version"