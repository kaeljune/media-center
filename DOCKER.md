# Docker Deployment Guide

## Tổng quan

Media Center được đóng gói thành Docker container để dễ dàng triển khai trên:
- **Jetson Nano** (ARM64)
- **macOS** (AMD64)
- **Linux x86_64** (AMD64)

## Quick Start

### 1. Trên macOS (Development/Testing)

```bash
# Clone repository
git clone <repo-url>
cd mediacenter-jetson

# Build và chạy
./deploy.sh --build up

# Kiểm tra
curl http://localhost:8000/health
```

### 2. Trên Jetson Nano (Production)

```bash
# Clone repository
git clone <repo-url>
cd mediacenter-jetson

# Build cho ARM64
./build.sh -p linux/arm64

# Chạy với audio device access
./deploy.sh up

# Kiểm tra audio
docker exec -it mediacenter speaker-test -t wav -c 2
```

## Build Options

### Build cho platform cụ thể

```bash
# Cho Jetson Nano (ARM64)
./build.sh -p linux/arm64

# Cho macOS/Linux (AMD64)  
./build.sh -p linux/amd64

# Multi-platform build
docker buildx build --platform linux/amd64,linux/arm64 -t mediacenter:latest .
```

### Build với tên image tùy chỉnh

```bash
# Build với registry
./build.sh -n myregistry.com/mediacenter -t v1.0.0

# Build và push
./build.sh -n myregistry.com/mediacenter --push
```

## Configuration

### Environment Variables

```bash
# docker-compose.override.yml
services:
  mediacenter:
    environment:
      - LOG_LEVEL=DEBUG
      - WEBHOOK_PORT=8000
      - HC3_PORT=8001
      - TTS_ENGINE=espeak
```

### Volume Mounts

```yaml
volumes:
  # Persistent data
  - ./audio:/app/audio
  - ./logs:/app/logs
  - ./config:/app/config
  
  # Audio devices (Linux only)
  - /dev/snd:/dev/snd
```

### Audio Configuration

#### Linux/Jetson Nano
```bash
# Check audio devices
docker exec -it mediacenter aplay -l

# Test audio output
docker exec -it mediacenter speaker-test -t wav
```

#### macOS
```bash
# Audio sẽ output ra host system
# Không cần mount /dev/snd
```

## Service Commands

### Deploy Script

```bash
# Start services
./deploy.sh up

# Start with build
./deploy.sh --build up

# Stop services
./deploy.sh down

# Restart
./deploy.sh restart

# Show logs
./deploy.sh logs

# Check status
./deploy.sh status
```

### Manual Docker Commands

```bash
# Build
docker build -t mediacenter .

# Run single container
docker run -d \
  --name mediacenter \
  -p 8000:8000 \
  -p 8001:8001 \
  -v $(pwd)/audio:/app/audio \
  -v $(pwd)/logs:/app/logs \
  --device /dev/snd \
  mediacenter

# Check logs
docker logs -f mediacenter

# Execute commands
docker exec -it mediacenter bash
```

## API Testing

### Health Check
```bash
curl http://localhost:8000/health
```

### Text-to-Speech
```bash
curl -X POST http://localhost:8000/tts \
  -H 'Content-Type: application/json' \
  -d '{"text":"Hello from Docker container"}'
```

### YouTube Music
```bash
curl -X POST http://localhost:8000/hc3/command \
  -H 'Content-Type: application/json' \
  -d '{"type":"play_youtube_search","query":"relaxing music"}'
```

### HC3 Commands
```bash
# Play local music
curl -X POST http://localhost:8000/hc3/command \
  -H 'Content-Type: application/json' \
  -d '{"type":"play_music","song_name":"test_song"}'

# Stop music
curl -X POST http://localhost:8000/hc3/command \
  -H 'Content-Type: application/json' \
  -d '{"type":"stop_music"}'
```

## Troubleshooting

### Audio Issues

#### Jetson Nano
```bash
# Check audio devices in container
docker exec -it mediacenter aplay -l

# Check ALSA configuration
docker exec -it mediacenter cat /proc/asound/cards

# Test audio
docker exec -it mediacenter espeak "Audio test"
```

#### macOS
```bash
# Audio sẽ sử dụng host system
# Kiểm tra volume macOS

# Test TTS
curl -X POST http://localhost:8000/tts \
  -H 'Content-Type: application/json' \
  -d '{"text":"macOS audio test"}'
```

### Container Issues

```bash
# Check container status
docker ps

# Check container logs
docker logs mediacenter

# Check resource usage
docker stats mediacenter

# Restart container
docker restart mediacenter
```

### Network Issues

```bash
# Check port binding
docker port mediacenter

# Check container network
docker inspect mediacenter | grep IPAddress

# Test connectivity
curl -v http://localhost:8000/health
```

### Build Issues

```bash
# Clean build
docker system prune -a

# Check build context
docker build --no-cache .

# Multi-stage build debug
docker build --target base .
```

## Production Deployment

### Jetson Nano Production

```bash
# Create systemd service
sudo tee /etc/systemd/system/mediacenter.service << EOF
[Unit]
Description=Media Center Docker
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/mediacenter
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
ExecReload=/usr/bin/docker-compose restart

[Install]
WantedBy=multi-user.target
EOF

# Enable service
sudo systemctl enable mediacenter
sudo systemctl start mediacenter
```

### Resource Limits

```yaml
# docker-compose.yml
services:
  mediacenter:
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '1.0'
        reservations:
          memory: 256M
          cpus: '0.5'
```

### Logging

```yaml
services:
  mediacenter:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## Security

### Non-root User
Container chạy với user `mediacenter` (UID 1000) thay vì root.

### Capabilities
Chỉ sử dụng capabilities cần thiết:
```yaml
cap_add:
  - SYS_ADMIN  # Cho audio device access
```

### Network Security
```yaml
networks:
  mediacenter-net:
    driver: bridge
    internal: false  # Allow internet access for YouTube
```

## Monitoring

### Health Checks
```bash
# Container health
docker inspect mediacenter | grep Health

# Service health
curl http://localhost:8000/health
```

### Metrics
```bash
# Resource usage
docker stats mediacenter

# Logs
docker logs --tail 100 mediacenter
```