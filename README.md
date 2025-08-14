# Media Center for Jetson Nano

A Media Center system designed to run on Jetson Nano with the following features:

- **HC3 Command Listener**: Receives commands from HC3 to play music/playlists
- **Webhook TTS Service**: Webhook API for text-to-speech conversion
- **Audio Player**: Music playback management with playlist support
- **Text-to-Speech**: Text to voice conversion

## Project Structure

```
mediacenter-jetson/
├── mediacenter/
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py          # System configuration
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── audio_player.py      # Audio player module
│   │   └── tts_engine.py        # Text-to-speech module
│   ├── services/
│   │   ├── __init__.py
│   │   ├── hc3_listener.py      # HC3 listener service
│   │   └── webhook_service.py   # Webhook API service
│   └── __init__.py
├── audio/
│   ├── music/                   # Music directory
│   ├── playlists/               # Playlist JSON directory
│   └── tts_cache/               # TTS cache files
├── logs/                        # Log directory
├── main.py                      # Main application
├── requirements.txt             # Dependencies
└── README.md                    # This document
```

## Installation

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Install system dependencies (for Jetson Nano)

```bash
# Audio players
sudo apt-get install mpg123 alsa-utils

# Text-to-Speech engines
sudo apt-get install espeak espeak-data festival

# Optional: SoX for audio processing
sudo apt-get install sox
```

### 3. Configure audio output

```bash
# Check audio devices
aplay -l

# Set default audio output (if needed)
# Edit /home/user/.asoundrc or /etc/asound.conf
```

## Usage

### Start Media Center

```bash
python main.py
```

### API Endpoints

#### 1. Text-to-Speech Webhook

**POST** `http://jetson-ip:8000/tts`

```json
{
  "text": "Hello, this is a notification from the system",
  "voice": "default",
  "speed": 1.0,
  "volume": 0.8
}
```

#### 2. Health Check

**GET** `http://jetson-ip:8000/health`

#### 3. Service Status

**GET** `http://jetson-ip:8000/status`

### HC3 Commands

The service will listen for commands from HC3 with the following format:

```json
{
  "type": "play_music",
  "song_name": "song.mp3"
}
```

```json
{
  "type": "play_playlist", 
  "playlist_name": "playlist1"
}
```

```json
{
  "type": "stop_music"
}
```

```json
{
  "type": "volume",
  "volume": 75
}
```

## Configuration

Configuration file will be automatically created at `config.json`. Main parameters:

```json
{
  "audio": {
    "music_dir": "./audio/music",
    "playlists_dir": "./audio/playlists",
    "default_volume": 50
  },
  "webhook": {
    "host": "0.0.0.0",
    "port": 8000
  },
  "hc3": {
    "enabled": true,
    "port": 8001
  },
  "tts": {
    "engine": "espeak",
    "default_voice": "default",
    "cache_enabled": true
  }
}
```

## Playlist Management

Create JSON files in the `audio/playlists/` directory:

**playlist1.json**:
```json
{
  "name": "Playlist 1",
  "songs": [
    "song_1",
    "song_2", 
    "song_3"
  ]
}
```

## Logging

Logs are written to:
- File: `logs/mediacenter.log`
- Console output

## Docker Deployment (Recommended)

### Run on Jetson Nano

```bash
# Build for ARM64
./build.sh -p linux/arm64

# Deploy
./deploy.sh --build up
```

### Run on macOS/x86_64

```bash
# Build for AMD64
./build.sh -p linux/amd64

# Deploy
./deploy.sh --build up
```

### Useful Docker commands

```bash
# View logs
./deploy.sh logs

# Check status
./deploy.sh status

# Stop services
./deploy.sh down

# Restart
./deploy.sh restart
```

### Simple Docker Compose

```bash
# Start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## Run as Service (Systemd) - Without Docker

Create file `/etc/systemd/system/mediacenter.service`:

```ini
[Unit]
Description=Media Center Service
After=network.target

[Service]
Type=simple
User=jetson
WorkingDirectory=/path/to/mediacenter-jetson
ExecStart=/usr/bin/python3 /path/to/mediacenter-jetson/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable service:

```bash
sudo systemctl enable mediacenter
sudo systemctl start mediacenter
sudo systemctl status mediacenter
```

## Troubleshooting

### Audio playback issues

1. Check audio device: `aplay -l`
2. Test audio: `speaker-test -t wav -c 2`
3. Check volume: `alsamixer`

### TTS not working

1. Test espeak: `espeak "test"`
2. Install festival: `sudo apt-get install festival`

### Module import errors

Run from the project root directory and ensure Python path is correct.

## Development

The project is designed to be modular for easy extension:

- Add audio effects in `modules/`
- Add other communication protocols in `services/`
- Add new configurations in `config/settings.py`
- Add new API endpoints in `webhook_service.py`