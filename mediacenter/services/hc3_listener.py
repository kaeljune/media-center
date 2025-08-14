import asyncio
import json
import logging
from typing import Dict, Any
from ..modules.audio_player import AudioPlayer
from ..config.settings import Settings

logger = logging.getLogger(__name__)

class HC3CommandListener:
    def __init__(self, audio_player: AudioPlayer, settings: Settings):
        self.audio_player = audio_player
        self.settings = settings
        self.running = False
        
    async def start(self):
        """Start service to listen for commands from HC3"""
        self.running = True
        logger.info("HC3 Command Listener started")
        
        while self.running:
            try:
                await self._listen_for_commands()
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error in HC3 listener: {e}")
                await asyncio.sleep(5)
    
    def stop(self):
        """Stop service"""
        self.running = False
        logger.info("HC3 Command Listener stopped")
    
    async def _listen_for_commands(self):
        """Listen and process commands from HC3"""
        pass
    
    async def handle_command(self, command: Dict[str, Any]):
        """Process commands from HC3"""
        try:
            command_type = command.get('type')
            
            if command_type == 'play_music':
                await self._handle_play_music(command)
            elif command_type == 'stop_music':
                await self._handle_stop_music()
            elif command_type == 'play_playlist':
                await self._handle_play_playlist(command)
            elif command_type == 'play_youtube_search':
                await self._handle_play_youtube_search(command)
            elif command_type == 'play_youtube_url':
                await self._handle_play_youtube_url(command)
            elif command_type == 'play_youtube_playlist':
                await self._handle_play_youtube_playlist(command)
            elif command_type == 'volume':
                await self._handle_volume(command)
            else:
                logger.warning(f"Unknown command type: {command_type}")
                
        except Exception as e:
            logger.error(f"Error handling command: {e}")
    
    async def _handle_play_music(self, command: Dict[str, Any]):
        """Play a specific song"""
        song_name = command.get('song_name')
        if song_name:
            await self.audio_player.play_song(song_name)
            logger.info(f"Playing song: {song_name}")
    
    async def _handle_stop_music(self):
        """Stop playing music"""
        await self.audio_player.stop()
        logger.info("Music stopped")
    
    async def _handle_play_playlist(self, command: Dict[str, Any]):
        """Play playlist"""
        playlist_name = command.get('playlist_name')
        if playlist_name:
            await self.audio_player.play_playlist(playlist_name)
            logger.info(f"Playing playlist: {playlist_name}")
    
    async def _handle_play_youtube_search(self, command: Dict[str, Any]):
        """Search and play music from YouTube"""
        query = command.get('query')
        audio_only = command.get('audio_only', True)
        if query:
            await self.audio_player.play_youtube_search(query, audio_only)
            logger.info(f"Playing YouTube search: {query}")
    
    async def _handle_play_youtube_url(self, command: Dict[str, Any]):
        """Play music from YouTube URL"""
        url = command.get('url')
        audio_only = command.get('audio_only', True)
        if url:
            await self.audio_player.play_youtube_url(url, audio_only)
            logger.info(f"Playing YouTube URL: {url}")
    
    async def _handle_play_youtube_playlist(self, command: Dict[str, Any]):
        """Play YouTube playlist"""
        playlist_url = command.get('playlist_url')
        audio_only = command.get('audio_only', True)
        shuffle = command.get('shuffle', False)
        if playlist_url:
            await self.audio_player.play_youtube_playlist(playlist_url, audio_only, shuffle)
            logger.info(f"Playing YouTube playlist: {playlist_url}")

    async def _handle_volume(self, command: Dict[str, Any]):
        """Adjust volume"""
        volume = command.get('volume', 50)
        await self.audio_player.set_volume(volume)
        logger.info(f"Volume set to: {volume}")