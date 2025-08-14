#!/usr/bin/env python3
import asyncio
import logging
import signal
import sys
from pathlib import Path

from mediacenter.config.settings import Settings
from mediacenter.modules.audio_player import AudioPlayer
from mediacenter.modules.tts_engine import TTSEngine
from mediacenter.services.hc3_listener import HC3CommandListener
from mediacenter.services.webhook_service import WebhookService

class MediaCenterApp:
    def __init__(self):
        self.settings = Settings()
        self.audio_player = None
        self.tts_engine = None
        self.hc3_listener = None
        self.webhook_service = None
        self.running = False
        
        # Setup logging
        self._setup_logging()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _setup_logging(self):
        """Setup logging"""
        # Create logs directory if it doesn't exist
        log_dir = Path(self.settings.log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, self.settings.log_level),
            format=self.settings.get('logging.format'),
            handlers=[
                logging.FileHandler(self.settings.log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        
    def _signal_handler(self, signum, frame):
        """Handle stop signal"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        
    async def initialize(self):
        """Initialize components"""
        try:
            self.logger.info("Initializing Media Center...")
            
            # Create necessary directories
            self.settings.create_directories()
            
            # Initialize audio player
            self.audio_player = AudioPlayer(
                music_dir=self.settings.music_dir,
                playlists_dir=self.settings.playlists_dir
            )
            self.audio_player.set_volume(self.settings.default_volume)
            
            # Initialize TTS engine
            self.tts_engine = TTSEngine(
                cache_dir=self.settings.tts_cache_dir,
                default_voice=self.settings.get('tts.default_voice', 'default')
            )
            
            # Initialize HC3 listener
            self.hc3_listener = HC3CommandListener(
                audio_player=self.audio_player,
                settings=self.settings
            )
            
            # Initialize webhook service
            self.webhook_service = WebhookService(
                tts_engine=self.tts_engine,
                settings=self.settings,
                hc3_listener=self.hc3_listener
            )
            
            self.logger.info("Media Center initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing Media Center: {e}")
            raise
            
    async def start(self):
        """Start all services"""
        try:
            self.running = True
            self.logger.info("Starting Media Center services...")
            
            # Create tasks for all services
            tasks = []
            
            # Start webhook service
            if self.settings.get('webhook.enabled', True):
                webhook_task = asyncio.create_task(
                    self.webhook_service.start(
                        host=self.settings.webhook_host,
                        port=self.settings.webhook_port
                    )
                )
                tasks.append(webhook_task)
                self.logger.info(f"Webhook service starting on {self.settings.webhook_host}:{self.settings.webhook_port}")
            
            # Start HC3 listener
            if self.settings.get('hc3.enabled', True):
                hc3_task = asyncio.create_task(self.hc3_listener.start())
                tasks.append(hc3_task)
                self.logger.info("HC3 listener service started")
            
            # Wait for all tasks to complete or error
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            else:
                self.logger.warning("No services enabled")
                
        except Exception as e:
            self.logger.error(f"Error starting services: {e}")
            raise
        finally:
            await self.stop()
            
    async def stop(self):
        """Stop all services"""
        try:
            self.logger.info("Stopping Media Center services...")
            
            if self.hc3_listener:
                self.hc3_listener.stop()
                
            if self.webhook_service:
                self.webhook_service.stop()
                
            if self.audio_player:
                await self.audio_player.stop()
                
            if self.tts_engine:
                await self.tts_engine.stop()
                
            self.logger.info("Media Center stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping Media Center: {e}")

async def main():
    """Main function"""
    app = MediaCenterApp()
    
    try:
        await app.initialize()
        await app.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBye!")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)