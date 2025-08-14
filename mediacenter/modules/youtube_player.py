import asyncio
import subprocess
import logging
import re
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
import json

logger = logging.getLogger(__name__)

class YouTubePlayer:
    def __init__(self, cache_dir: str = "./audio/youtube_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.current_process = None
        self.is_playing = False
        self.volume = 50
        
    async def play_youtube_url(self, url: str, audio_only: bool = True):
        """Play music from YouTube URL"""
        try:
            if not self._is_valid_youtube_url(url):
                logger.error(f"Invalid YouTube URL: {url}")
                return False
                
            await self.stop()
            
            if audio_only:
                # Audio only, save bandwidth
                cmd = [
                    'yt-dlp',
                    '--extract-audio',
                    '--audio-format', 'mp3',
                    '--output', '-',
                    url
                ]
                
                # Pipe to audio player
                yt_process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                # Play with mpg123
                play_cmd = ['mpg123', '-q', '-']
                self.current_process = await asyncio.create_subprocess_exec(
                    *play_cmd,
                    stdin=yt_process.stdout,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                self.is_playing = True
                await self.current_process.wait()
                await yt_process.wait()
                
            else:
                # Play video (requires display)
                cmd = [
                    'yt-dlp',
                    '--format', 'best[height<=480]',  # Limit quality for Jetson
                    '--output', '-',
                    url
                ]
                
                yt_process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                # Play with mpv
                play_cmd = ['mpv', '--vo=gpu', '--hwdec=auto', '-']
                self.current_process = await asyncio.create_subprocess_exec(
                    *play_cmd,
                    stdin=yt_process.stdout,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                self.is_playing = True
                await self.current_process.wait()
                await yt_process.wait()
                
            logger.info(f"Successfully played YouTube content: {url}")
            return True
            
        except Exception as e:
            logger.error(f"Error playing YouTube URL {url}: {e}")
            return False
    
    async def search_and_play(self, query: str, audio_only: bool = True):
        """Search and play music from YouTube"""
        try:
            # Check if running on macOS (has environment variable AUDIO_OUTPUT=host)
            if os.environ.get('AUDIO_OUTPUT') == 'host':
                return await self._play_on_macos_host(query, 'youtube_search')
            
            # Fallback to container method
            return await self._search_and_play_in_container(query, audio_only)
                
        except Exception as e:
            logger.error(f"Error searching YouTube for '{query}': {e}")
            return False
    
    async def _search_and_play_in_container(self, query: str, audio_only: bool = True):
        """Legacy method to play in container"""
        try:
            # Search for first video
            search_cmd = [
                'yt-dlp',
                '--get-url',
                '--get-title',
                f'ytsearch1:{query}'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *search_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                lines = stdout.decode().strip().split('\n')
                if len(lines) >= 2:
                    title = lines[0]
                    url = lines[1]
                    
                    logger.info(f"Found: {title}")
                    logger.info(f"URL: {url}")
                    
                    return await self.play_youtube_url(url, audio_only)
                else:
                    logger.error(f"No results found for: {query}")
                    return False
            else:
                logger.error(f"Search failed: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Error searching YouTube for '{query}': {e}")
            return False
    
    async def _play_on_macos_host(self, param: str, command_type: str):
        """Call script on macOS host to play audio"""
        try:
            # Script path in container (mounted from host)
            script_path = "/app/play_audio_macos.sh"
            
            # Run script on host through reverse docker exec
            cmd = ['sh', '-c', f'echo "{param}" > /tmp/mediacenter_request && echo "{command_type}" > /tmp/mediacenter_command']
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.wait()
            
            # Create signal file for host script to read
            with open('/tmp/mediacenter_request', 'w') as f:
                f.write(param)
            with open('/tmp/mediacenter_command', 'w') as f:
                f.write(command_type)
                
            logger.info(f"Created request for macOS host: {command_type} - {param}")
            return True
            
        except Exception as e:
            logger.error(f"Error calling macOS host script: {e}")
            return False
    
    async def play_youtube_playlist(self, playlist_url: str, audio_only: bool = True, shuffle: bool = False):
        """Play YouTube playlist"""
        try:
            if not self._is_valid_youtube_playlist_url(playlist_url):
                logger.error(f"Invalid YouTube playlist URL: {playlist_url}")
                return False
                
            # Get list of videos in playlist
            list_cmd = [
                'yt-dlp',
                '--get-url',
                '--get-title',
                '--playlist-items', '1-20',  # Limit to first 20 videos
                playlist_url
            ]
            
            if shuffle:
                list_cmd.extend(['--playlist-random'])
                
            process = await asyncio.create_subprocess_exec(
                *list_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                lines = stdout.decode().strip().split('\n')
                
                # Parse title and URL pairs
                videos = []
                for i in range(0, len(lines), 2):
                    if i + 1 < len(lines):
                        title = lines[i]
                        url = lines[i + 1]
                        videos.append({'title': title, 'url': url})
                
                logger.info(f"Found {len(videos)} videos in playlist")
                
                # Play each video
                for video in videos:
                    if not self.is_playing:  # Might be stopped
                        break
                        
                    logger.info(f"Playing: {video['title']}")
                    await self.play_youtube_url(video['url'], audio_only)
                    
                return True
            else:
                logger.error(f"Failed to get playlist: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Error playing YouTube playlist {playlist_url}: {e}")
            return False
    
    async def download_and_cache(self, url: str, filename: Optional[str] = None) -> Optional[Path]:
        """Download and cache YouTube audio for offline playback"""
        try:
            if not filename:
                # Create filename from video title
                info_cmd = ['yt-dlp', '--get-title', url]
                process = await asyncio.create_subprocess_exec(
                    *info_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await process.communicate()
                title = stdout.decode().strip()
                
                # Clean filename
                filename = re.sub(r'[^\w\s-]', '', title).strip()
                filename = re.sub(r'[-\s]+', '-', filename)
                
            cache_file = self.cache_dir / f"{filename}.mp3"
            
            # Check cache
            if cache_file.exists():
                logger.info(f"Using cached file: {cache_file}")
                return cache_file
                
            # Download
            download_cmd = [
                'yt-dlp',
                '--extract-audio',
                '--audio-format', 'mp3',
                '--output', str(cache_file.with_suffix('')),  # yt-dlp will add .mp3
                url
            ]
            
            process = await asyncio.create_subprocess_exec(
                *download_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.wait()
            
            if process.returncode == 0 and cache_file.exists():
                logger.info(f"Downloaded and cached: {cache_file}")
                return cache_file
            else:
                logger.error(f"Failed to download: {url}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            return None
    
    async def stop(self):
        """Stop YouTube playback"""
        if self.current_process:
            try:
                self.current_process.terminate()
                await asyncio.sleep(1)
                if self.current_process.poll() is None:
                    self.current_process.kill()
                self.current_process = None
                self.is_playing = False
                logger.info("YouTube playback stopped")
            except Exception as e:
                logger.error(f"Error stopping YouTube playback: {e}")
    
    def _is_valid_youtube_url(self, url: str) -> bool:
        """Check if YouTube URL is valid"""
        youtube_patterns = [
            r'youtube\.com/watch\?v=',
            r'youtu\.be/',
            r'youtube\.com/embed/',
            r'music\.youtube\.com/watch\?v='
        ]
        return any(re.search(pattern, url) for pattern in youtube_patterns)
    
    def _is_valid_youtube_playlist_url(self, url: str) -> bool:
        """Check if YouTube playlist URL is valid"""
        playlist_patterns = [
            r'youtube\.com/playlist\?list=',
            r'youtube\.com/watch\?.*list=',
            r'music\.youtube\.com/playlist\?list='
        ]
        return any(re.search(pattern, url) for pattern in playlist_patterns)
    
    def clear_cache(self):
        """Clear YouTube cache"""
        try:
            for cache_file in self.cache_dir.glob("*.mp3"):
                cache_file.unlink()
            logger.info("YouTube cache cleared")
        except Exception as e:
            logger.error(f"Error clearing YouTube cache: {e}")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache information"""
        cache_files = list(self.cache_dir.glob("*.mp3"))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            "cache_count": len(cache_files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "cache_dir": str(self.cache_dir)
        }