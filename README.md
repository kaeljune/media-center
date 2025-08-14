# Media Center for Jetson Nano

Hệ thống Media Center được thiết kế để chạy trên Jetson Nano với các tính năng:

- **HC3 Command Listener**: Nhận lệnh từ HC3 để phát nhạc/playlist
- **Webhook TTS Service**: API webhook để chuyển text thành speech
- **Audio Player**: Quản lý phát nhạc với hỗ trợ playlist
- **Text-to-Speech**: Chuyển đổi text thành giọng nói

## Cấu trúc dự án

```
mediacenter-jetson/
├── mediacenter/
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py          # Cấu hình hệ thống
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── audio_player.py      # Module phát nhạc
│   │   └── tts_engine.py        # Module text-to-speech
│   ├── services/
│   │   ├── __init__.py
│   │   ├── hc3_listener.py      # Service lắng nghe HC3
│   │   └── webhook_service.py   # Webhook API service
│   └── __init__.py
├── audio/
│   ├── music/                   # Thư mục chứa nhạc
│   ├── playlists/               # Thư mục chứa playlist JSON
│   └── tts_cache/               # Cache file TTS
├── logs/                        # Thư mục log
├── main.py                      # Application chính
├── requirements.txt             # Dependencies
└── README.md                    # Tài liệu này
```

## Cài đặt

### 1. Cài đặt Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Cài đặt system dependencies (cho Jetson Nano)

```bash
# Audio players
sudo apt-get install mpg123 alsa-utils

# Text-to-Speech engines
sudo apt-get install espeak espeak-data festival

# Optional: SoX for audio processing
sudo apt-get install sox
```

### 3. Cấu hình audio output

```bash
# Kiểm tra audio devices
aplay -l

# Set default audio output (nếu cần)
# Chỉnh sửa /home/user/.asoundrc hoặc /etc/asound.conf
```

## Sử dụng

### Khởi động Media Center

```bash
python main.py
```

### API Endpoints

#### 1. Text-to-Speech Webhook

**POST** `http://jetson-ip:8000/tts`

```json
{
  "text": "Xin chào, đây là thông báo từ hệ thống",
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

Service sẽ lắng nghe các lệnh từ HC3 với format:

```json
{
  "type": "play_music",
  "song_name": "bai_hat.mp3"
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

## Cấu hình

File cấu hình sẽ được tạo tự động tại `config.json`. Các thông số chính:

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

## Quản lý Playlist

Tạo file JSON trong thư mục `audio/playlists/`:

**playlist1.json**:
```json
{
  "name": "Playlist 1",
  "songs": [
    "bai_hat_1",
    "bai_hat_2", 
    "bai_hat_3"
  ]
}
```

## Logging

Logs được ghi vào:
- File: `logs/mediacenter.log`
- Console output

## Docker Deployment (Khuyến nghị)

### Chạy trên Jetson Nano

```bash
# Build cho ARM64
./build.sh -p linux/arm64

# Deploy
./deploy.sh --build up
```

### Chạy trên macOS/x86_64

```bash
# Build cho AMD64
./build.sh -p linux/amd64

# Deploy
./deploy.sh --build up
```

### Các lệnh Docker hữu ích

```bash
# Xem logs
./deploy.sh logs

# Kiểm tra trạng thái
./deploy.sh status

# Dừng services
./deploy.sh down

# Restart
./deploy.sh restart
```

### Docker Compose đơn giản

```bash
# Khởi động
docker-compose up -d

# Xem logs
docker-compose logs -f

# Dừng
docker-compose down
```

## Chạy như Service (Systemd) - Không dùng Docker

Tạo file `/etc/systemd/system/mediacenter.service`:

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

Kích hoạt service:

```bash
sudo systemctl enable mediacenter
sudo systemctl start mediacenter
sudo systemctl status mediacenter
```

## Troubleshooting

### Lỗi audio không phát được

1. Kiểm tra audio device: `aplay -l`
2. Test audio: `speaker-test -t wav -c 2`
3. Kiểm tra volume: `alsamixer`

### Lỗi TTS không hoạt động

1. Kiểm tra espeak: `espeak "test"`
2. Cài đặt festival: `sudo apt-get install festival`

### Lỗi import module

Chạy từ thư mục gốc của project và đảm bảo Python path đúng.

## Phát triển thêm

Dự án được thiết kế modular để dễ dàng mở rộng:

- Thêm audio effects trong `modules/`
- Thêm protocol communication khác trong `services/`
- Thêm cấu hình mới trong `config/settings.py`
- Thêm API endpoints mới trong `webhook_service.py`