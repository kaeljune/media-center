import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

class Settings:
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "config.json"
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration từ file hoặc tạo config mặc định"""
        config_path = Path(self.config_file)
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
                return self._get_default_config()
        else:
            config = self._get_default_config()
            self.save_config()
            return config
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Cấu hình mặc định"""
        return {
            "audio": {
                "music_dir": "./audio/music",
                "playlists_dir": "./audio/playlists", 
                "tts_cache_dir": "./audio/tts_cache",
                "default_volume": 50,
                "supported_formats": [".mp3", ".wav", ".flac", ".ogg", ".m4a"]
            },
            "hc3": {
                "enabled": True,
                "host": "0.0.0.0",
                "port": 8001,
                "timeout": 30
            },
            "webhook": {
                "enabled": True,
                "host": "0.0.0.0",
                "port": 8000,
                "timeout": 60
            },
            "tts": {
                "engine": "espeak",
                "default_voice": "default",
                "default_speed": 1.0,
                "default_volume": 0.8,
                "cache_enabled": True,
                "max_cache_files": 1000
            },
            "logging": {
                "level": "INFO",
                "file": "./logs/mediacenter.log",
                "max_size": "10MB",
                "backup_count": 5,
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "security": {
                "api_keys": [],
                "allowed_ips": ["127.0.0.1", "localhost"],
                "enable_auth": False
            }
        }
    
    def save_config(self):
        """Lưu cấu hình ra file"""
        try:
            config_path = Path(self.config_file)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Lấy giá trị config theo key (hỗ trợ nested key với dấu chấm)"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
    
    def set(self, key: str, value: Any):
        """Set giá trị config theo key (hỗ trợ nested key với dấu chấm)"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
            
        config[keys[-1]] = value
        self.save_config()
    
    # Các property để truy cập nhanh các cấu hình thường dùng
    @property
    def music_dir(self) -> str:
        return self.get('audio.music_dir', './audio/music')
    
    @property
    def playlists_dir(self) -> str:
        return self.get('audio.playlists_dir', './audio/playlists')
    
    @property
    def tts_cache_dir(self) -> str:
        return self.get('audio.tts_cache_dir', './audio/tts_cache')
    
    @property
    def webhook_host(self) -> str:
        return self.get('webhook.host', '0.0.0.0')
    
    @property
    def webhook_port(self) -> int:
        return self.get('webhook.port', 8000)
    
    @property
    def hc3_host(self) -> str:
        return self.get('hc3.host', '0.0.0.0')
    
    @property
    def hc3_port(self) -> int:
        return self.get('hc3.port', 8001)
    
    @property
    def log_level(self) -> str:
        return self.get('logging.level', 'INFO')
    
    @property
    def log_file(self) -> str:
        return self.get('logging.file', './logs/mediacenter.log')
    
    @property
    def tts_engine(self) -> str:
        return self.get('tts.engine', 'espeak')
    
    @property
    def default_volume(self) -> int:
        return self.get('audio.default_volume', 50)
    
    def create_directories(self):
        """Tạo các thư mục cần thiết"""
        directories = [
            self.music_dir,
            self.playlists_dir,
            self.tts_cache_dir,
            os.path.dirname(self.log_file)
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)