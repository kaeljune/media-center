import asyncio
import hashlib
import os
import logging
from pathlib import Path
from typing import Optional
import subprocess

logger = logging.getLogger(__name__)

class TTSEngine:
    def __init__(self, cache_dir: str, default_voice: str = "default"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_voice = default_voice
        self.current_process = None
        
    async def speak(self, text: str, voice: Optional[str] = None, speed: float = 1.0, volume: float = 0.8):
        """Chuyển text thành speech và phát ra loa"""
        try:
            if not text or text.strip() == "":
                logger.warning("Empty text provided for TTS")
                return False
                
            # Sử dụng voice mặc định nếu không được chỉ định
            if not voice:
                voice = self.default_voice
                
            # Tạo cache key từ text và các tham số
            cache_key = self._generate_cache_key(text, voice, speed)
            cache_file = self.cache_dir / f"{cache_key}.wav"
            
            # Kiểm tra cache
            if not cache_file.exists():
                logger.info(f"Generating TTS for: {text[:50]}...")
                success = await self._generate_tts(text, voice, speed, cache_file)
                if not success:
                    logger.error("Failed to generate TTS")
                    return False
            else:
                logger.info("Using cached TTS file")
            
            # Phát file audio
            await self._play_audio(cache_file, volume)
            return True
            
        except Exception as e:
            logger.error(f"Error in TTS speak: {e}")
            return False
    
    async def stop(self):
        """Dừng phát TTS hiện tại"""
        if self.current_process:
            try:
                self.current_process.terminate()
                await asyncio.sleep(0.5)
                if self.current_process.poll() is None:
                    self.current_process.kill()
                self.current_process = None
                logger.info("TTS stopped")
            except Exception as e:
                logger.error(f"Error stopping TTS: {e}")
    
    def clear_cache(self):
        """Xóa cache TTS"""
        try:
            for cache_file in self.cache_dir.glob("*.wav"):
                cache_file.unlink()
            logger.info("TTS cache cleared")
        except Exception as e:
            logger.error(f"Error clearing TTS cache: {e}")
    
    def get_cache_size(self) -> int:
        """Lấy kích thước cache (số file)"""
        return len(list(self.cache_dir.glob("*.wav")))
    
    def _generate_cache_key(self, text: str, voice: str, speed: float) -> str:
        """Tạo cache key từ text và tham số"""
        content = f"{text}_{voice}_{speed}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    async def _generate_tts(self, text: str, voice: str, speed: float, output_file: Path) -> bool:
        """Tạo file TTS sử dụng espeak hoặc festival"""
        try:
            # Thử sử dụng espeak trước
            cmd = [
                'espeak',
                '-s', str(int(175 * speed)),  # Tốc độ (words per minute)
                '-a', '100',  # Amplitude
                '-w', str(output_file),  # Output file
                text
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and output_file.exists():
                logger.info("TTS generated successfully with espeak")
                return True
            else:
                logger.warning("espeak failed, trying festival")
                return await self._generate_tts_festival(text, output_file)
                
        except FileNotFoundError:
            logger.warning("espeak not found, trying festival")
            return await self._generate_tts_festival(text, output_file)
        except Exception as e:
            logger.error(f"Error generating TTS with espeak: {e}")
            return await self._generate_tts_festival(text, output_file)
    
    async def _generate_tts_festival(self, text: str, output_file: Path) -> bool:
        """Tạo file TTS sử dụng festival"""
        try:
            # Tạo temporary text file
            temp_text_file = self.cache_dir / "temp_tts.txt"
            with open(temp_text_file, 'w', encoding='utf-8') as f:
                f.write(text)
            
            cmd = [
                'festival',
                '--tts',
                str(temp_text_file)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Cleanup temp file
            if temp_text_file.exists():
                temp_text_file.unlink()
            
            if process.returncode == 0:
                logger.info("TTS generated successfully with festival")
                return True
            else:
                logger.error("Festival TTS generation failed")
                return False
                
        except FileNotFoundError:
            logger.error("Neither espeak nor festival found. Please install TTS engine.")
            return False
        except Exception as e:
            logger.error(f"Error generating TTS with festival: {e}")
            return False
    
    async def _play_audio(self, audio_file: Path, volume: float):
        """Phát file audio"""
        try:
            # Điều chỉnh volume (0.0 - 1.0)
            volume_percent = int(volume * 100)
            
            # Thử sử dụng aplay
            cmd = ['aplay', str(audio_file)]
            
            self.current_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await self.current_process.wait()
            
            if self.current_process.returncode == 0:
                logger.info("TTS audio played successfully")
            else:
                # Fallback to other audio players
                await self._play_audio_fallback(audio_file)
                
        except FileNotFoundError:
            await self._play_audio_fallback(audio_file)
        except Exception as e:
            logger.error(f"Error playing TTS audio: {e}")
    
    async def _play_audio_fallback(self, audio_file: Path):
        """Fallback audio player methods"""
        players = ['mpg123', 'sox', 'paplay']
        
        for player in players:
            try:
                if player == 'mpg123':
                    cmd = [player, '-q', str(audio_file)]
                elif player == 'sox':
                    cmd = [player, str(audio_file), '-d']
                elif player == 'paplay':
                    cmd = [player, str(audio_file)]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                await process.wait()
                
                if process.returncode == 0:
                    logger.info(f"TTS audio played successfully with {player}")
                    return
                    
            except FileNotFoundError:
                continue
            except Exception as e:
                logger.warning(f"Failed to play with {player}: {e}")
                continue
        
        logger.error("No suitable audio player found for TTS")