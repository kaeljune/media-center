import asyncio
import json
import os
import random
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
import subprocess
from .youtube_player import YouTubePlayer

logger = logging.getLogger(__name__)

class AudioPlayer:
    def __init__(self, music_dir: str, playlists_dir: str, youtube_cache_dir: str = "./audio/youtube_cache"):
        self.music_dir = Path(music_dir)
        self.playlists_dir = Path(playlists_dir)
        self.current_process = None
        self.current_playlist = []
        self.current_index = 0
        self.is_playing = False
        self.volume = 50
        self.repeat_mode = False
        self.shuffle_mode = False
        
        # YouTube player
        self.youtube_player = YouTubePlayer(youtube_cache_dir)
        
    async def play_song(self, song_name: str):
        """Play a specific song"""
        try:
            song_path = self._find_song(song_name)
            if not song_path:
                logger.error(f"Song not found: {song_name}")
                return False
                
            await self.stop()
            await self._play_file(song_path)
            logger.info(f"Playing song: {song_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error playing song {song_name}: {e}")
            return False
    
    async def play_playlist(self, playlist_name: str):
        """Play a playlist"""
        try:
            playlist = self._load_playlist(playlist_name)
            if not playlist:
                logger.error(f"Playlist not found: {playlist_name}")
                return False
                
            self.current_playlist = playlist
            self.current_index = 0
            
            if self.shuffle_mode:
                random.shuffle(self.current_playlist)
                
            await self._play_current_song()
            logger.info(f"Playing playlist: {playlist_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error playing playlist {playlist_name}: {e}")
            return False
    
    async def play_youtube_search(self, query: str, audio_only: bool = True):
        """Search and play music from YouTube"""
        try:
            await self.stop()
            success = await self.youtube_player.search_and_play(query, audio_only)
            if success:
                self.is_playing = True
                logger.info(f"Playing YouTube search: {query}")
            return success
        except Exception as e:
            logger.error(f"Error playing YouTube search '{query}': {e}")
            return False
    
    async def play_youtube_url(self, url: str, audio_only: bool = True):
        """Play music from YouTube URL"""
        try:
            await self.stop()
            success = await self.youtube_player.play_youtube_url(url, audio_only)
            if success:
                self.is_playing = True
                logger.info(f"Playing YouTube URL: {url}")
            return success
        except Exception as e:
            logger.error(f"Error playing YouTube URL '{url}': {e}")
            return False
    
    async def play_youtube_playlist(self, playlist_url: str, audio_only: bool = True, shuffle: bool = False):
        """Play YouTube playlist"""
        try:
            await self.stop()
            success = await self.youtube_player.play_youtube_playlist(playlist_url, audio_only, shuffle)
            if success:
                self.is_playing = True
                logger.info(f"Playing YouTube playlist: {playlist_url}")
            return success
        except Exception as e:
            logger.error(f"Error playing YouTube playlist '{playlist_url}': {e}")
            return False

    async def stop(self):
        """Stop playing music"""
        # Stop local player
        if self.current_process:
            try:
                self.current_process.terminate()
                await asyncio.sleep(0.5)
                if self.current_process.poll() is None:
                    self.current_process.kill()
                self.current_process = None
                self.is_playing = False
                logger.info("Music stopped")
            except Exception as e:
                logger.error(f"Error stopping music: {e}")
        
        # Stop YouTube player
        await self.youtube_player.stop()
        self.is_playing = False
    
    async def pause(self):
        """Pause music playback"""
        if self.current_process and self.is_playing:
            try:
                self.current_process.send_signal(subprocess.signal.SIGSTOP)
                self.is_playing = False
                logger.info("Music paused")
            except Exception as e:
                logger.error(f"Error pausing music: {e}")
    
    async def resume(self):
        """Resume music playback"""
        if self.current_process and not self.is_playing:
            try:
                self.current_process.send_signal(subprocess.signal.SIGCONT)
                self.is_playing = True
                logger.info("Music resumed")
            except Exception as e:
                logger.error(f"Error resuming music: {e}")
    
    async def next_song(self):
        """Skip to next song"""
        if self.current_playlist:
            self.current_index = (self.current_index + 1) % len(self.current_playlist)
            await self._play_current_song()
    
    async def previous_song(self):
        """Go back to previous song"""
        if self.current_playlist:
            self.current_index = (self.current_index - 1) % len(self.current_playlist)
            await self._play_current_song()
    
    async def set_volume(self, volume: int):
        """Adjust volume (0-100)"""
        self.volume = max(0, min(100, volume))
        logger.info(f"Volume set to: {self.volume}")
    
    def toggle_shuffle(self):
        """Toggle shuffle mode"""
        self.shuffle_mode = not self.shuffle_mode
        logger.info(f"Shuffle mode: {'ON' if self.shuffle_mode else 'OFF'}")
    
    def toggle_repeat(self):
        """Toggle repeat mode"""
        self.repeat_mode = not self.repeat_mode
        logger.info(f"Repeat mode: {'ON' if self.repeat_mode else 'OFF'}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current player status"""
        current_song = None
        if self.current_playlist and 0 <= self.current_index < len(self.current_playlist):
            current_song = self.current_playlist[self.current_index]
            
        return {
            "is_playing": self.is_playing,
            "current_song": current_song,
            "volume": self.volume,
            "shuffle_mode": self.shuffle_mode,
            "repeat_mode": self.repeat_mode,
            "playlist_length": len(self.current_playlist),
            "current_index": self.current_index
        }
    
    def _find_song(self, song_name: str) -> Optional[Path]:
        """Find music file by name"""
        for ext in ['.mp3', '.wav', '.flac', '.ogg', '.m4a']:
            song_path = self.music_dir / f"{song_name}{ext}"
            if song_path.exists():
                return song_path
                
        # Case-insensitive search
        for file_path in self.music_dir.rglob("*"):
            if file_path.is_file() and song_name.lower() in file_path.stem.lower():
                return file_path
                
        return None
    
    def _load_playlist(self, playlist_name: str) -> List[str]:
        """Load playlist from JSON file"""
        playlist_path = self.playlists_dir / f"{playlist_name}.json"
        if not playlist_path.exists():
            return []
            
        try:
            with open(playlist_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('songs', [])
        except Exception as e:
            logger.error(f"Error loading playlist {playlist_name}: {e}")
            return []
    
    async def _play_file(self, file_path: Path):
        """Play music file using mpg123 or aplay"""
        try:
            # Try using mpg123 for MP3
            if file_path.suffix.lower() == '.mp3':
                cmd = ['mpg123', '-q', str(file_path)]
            else:
                # Use aplay for other formats
                cmd = ['aplay', str(file_path)]
                
            self.current_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            self.is_playing = True
            
            # Wait for process to finish
            await self.current_process.wait()
            
            # If playing playlist and song ends naturally
            if self.is_playing and self.current_playlist:
                await self._handle_song_finished()
                
        except Exception as e:
            logger.error(f"Error playing file {file_path}: {e}")
            self.is_playing = False
    
    async def _play_current_song(self):
        """Play current song in playlist"""
        if not self.current_playlist or self.current_index >= len(self.current_playlist):
            return
            
        song_name = self.current_playlist[self.current_index]
        song_path = self._find_song(song_name)
        
        if song_path:
            await self.stop()
            await self._play_file(song_path)
        else:
            logger.error(f"Song not found in playlist: {song_name}")
            await self.next_song()
    
    async def _handle_song_finished(self):
        """Handle when a song finishes"""
        if self.repeat_mode and len(self.current_playlist) == 1:
            # Repeat current song
            await self._play_current_song()
        elif self.current_index < len(self.current_playlist) - 1:
            # Move to next song
            await self.next_song()
        elif self.repeat_mode:
            # Repeat playlist
            self.current_index = 0
            await self._play_current_song()
        else:
            # End playlist
            self.is_playing = False
            logger.info("Playlist finished")