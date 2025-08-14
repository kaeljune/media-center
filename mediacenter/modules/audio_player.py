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
        """Phát một bài nhạc cụ thể"""
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
        """Phát một playlist"""
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
        """Tìm kiếm và phát nhạc từ YouTube"""
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
        """Phát nhạc từ YouTube URL"""
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
        """Phát YouTube playlist"""
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
        """Dừng phát nhạc"""
        # Dừng local player
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
        
        # Dừng YouTube player
        await self.youtube_player.stop()
        self.is_playing = False
    
    async def pause(self):
        """Tạm dừng phát nhạc"""
        if self.current_process and self.is_playing:
            try:
                self.current_process.send_signal(subprocess.signal.SIGSTOP)
                self.is_playing = False
                logger.info("Music paused")
            except Exception as e:
                logger.error(f"Error pausing music: {e}")
    
    async def resume(self):
        """Tiếp tục phát nhạc"""
        if self.current_process and not self.is_playing:
            try:
                self.current_process.send_signal(subprocess.signal.SIGCONT)
                self.is_playing = True
                logger.info("Music resumed")
            except Exception as e:
                logger.error(f"Error resuming music: {e}")
    
    async def next_song(self):
        """Chuyển sang bài tiếp theo"""
        if self.current_playlist:
            self.current_index = (self.current_index + 1) % len(self.current_playlist)
            await self._play_current_song()
    
    async def previous_song(self):
        """Chuyển về bài trước"""
        if self.current_playlist:
            self.current_index = (self.current_index - 1) % len(self.current_playlist)
            await self._play_current_song()
    
    async def set_volume(self, volume: int):
        """Điều chỉnh âm lượng (0-100)"""
        self.volume = max(0, min(100, volume))
        logger.info(f"Volume set to: {self.volume}")
    
    def toggle_shuffle(self):
        """Bật/tắt chế độ shuffle"""
        self.shuffle_mode = not self.shuffle_mode
        logger.info(f"Shuffle mode: {'ON' if self.shuffle_mode else 'OFF'}")
    
    def toggle_repeat(self):
        """Bật/tắt chế độ repeat"""
        self.repeat_mode = not self.repeat_mode
        logger.info(f"Repeat mode: {'ON' if self.repeat_mode else 'OFF'}")
    
    def get_status(self) -> Dict[str, Any]:
        """Lấy trạng thái hiện tại của player"""
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
        """Tìm file nhạc theo tên"""
        for ext in ['.mp3', '.wav', '.flac', '.ogg', '.m4a']:
            song_path = self.music_dir / f"{song_name}{ext}"
            if song_path.exists():
                return song_path
                
        # Tìm kiếm không phân biệt hoa thường
        for file_path in self.music_dir.rglob("*"):
            if file_path.is_file() and song_name.lower() in file_path.stem.lower():
                return file_path
                
        return None
    
    def _load_playlist(self, playlist_name: str) -> List[str]:
        """Load playlist từ file JSON"""
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
        """Phát file nhạc sử dụng mpg123 hoặc aplay"""
        try:
            # Thử sử dụng mpg123 cho MP3
            if file_path.suffix.lower() == '.mp3':
                cmd = ['mpg123', '-q', str(file_path)]
            else:
                # Sử dụng aplay cho các format khác
                cmd = ['aplay', str(file_path)]
                
            self.current_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            self.is_playing = True
            
            # Chờ process kết thúc
            await self.current_process.wait()
            
            # Nếu đang phát playlist và bài hát kết thúc tự nhiên
            if self.is_playing and self.current_playlist:
                await self._handle_song_finished()
                
        except Exception as e:
            logger.error(f"Error playing file {file_path}: {e}")
            self.is_playing = False
    
    async def _play_current_song(self):
        """Phát bài nhạc hiện tại trong playlist"""
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
        """Xử lý khi một bài nhạc kết thúc"""
        if self.repeat_mode and len(self.current_playlist) == 1:
            # Lặp lại bài hiện tại
            await self._play_current_song()
        elif self.current_index < len(self.current_playlist) - 1:
            # Chuyển sang bài tiếp theo
            await self.next_song()
        elif self.repeat_mode:
            # Lặp lại playlist
            self.current_index = 0
            await self._play_current_song()
        else:
            # Kết thúc playlist
            self.is_playing = False
            logger.info("Playlist finished")