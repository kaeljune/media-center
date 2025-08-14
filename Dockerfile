# Multi-stage build cho Media Center
FROM python:3.9-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Audio tools
    mpg123 \
    alsa-utils \
    pulseaudio \
    sox \
    ffmpeg \
    # TTS engines
    espeak \
    espeak-data \
    festival \
    # Video player
    mpv \
    # Network tools
    curl \
    wget \
    # Build tools
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Install yt-dlp (latest version)
RUN curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp \
    && chmod a+rx /usr/local/bin/yt-dlp

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mediacenter/ ./mediacenter/
COPY stylish-tts/ ./stylish-tts/
COPY setup_stylish_tts.sh .
COPY main.py .

# Setup Stylish-TTS
RUN chmod +x setup_stylish_tts.sh && ./setup_stylish_tts.sh

# Create necessary directories
RUN mkdir -p \
    audio/music \
    audio/playlists \
    audio/tts_cache \
    audio/youtube_cache \
    logs \
    config

# Copy default configuration and playlists
COPY audio/playlists/ ./audio/playlists/

# Create non-root user for security
RUN useradd -m -u 1000 mediacenter && \
    chown -R mediacenter:mediacenter /app

USER mediacenter

# Expose ports
EXPOSE 8000 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "main.py"]