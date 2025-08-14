import asyncio
import hashlib
import os
import logging
from pathlib import Path
from typing import Optional
import subprocess
import tempfile
import sys
import torch
import numpy as np
import onnxruntime as ort
from scipy.io.wavfile import write
from pydub import AudioSegment
import onnx
import re

# Add stylish-tts lib to path
sys.path.append(str(Path(__file__).parent.parent.parent / "stylish-tts" / "lib"))
sys.path.append(str(Path(__file__).parent.parent.parent / "stylish-tts"))

from stylish_lib.config_loader import ModelConfig
from stylish_lib.text_utils import TextCleaner
from misaki import vi
from vi_cleaner.vi_cleaner import ViCleaner

logger = logging.getLogger(__name__)

class TTSEngine:
    def __init__(self, cache_dir: str, default_voice: str = "default"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_voice = default_voice
        self.current_process = None
        
        # Stylish-TTS setup
        self.onnx_model_path = Path(__file__).parent.parent.parent / "stylish-tts" / "stylish_1.onnx"
        self.g2p = vi.VIG2P()
        self.tone_arrow = {
            "1": "",
            "2": "↘",
            "3": "→",
            "4": "⤺",
            "5": "↗",
            "6": "↓",
        }
        self.model_config = None
        self.text_cleaner = None
        self.session = None
        
        # Initialize Stylish-TTS model
        self._init_stylish_tts()
        
    async def speak(self, text: str, voice: Optional[str] = None, speed: float = 1.0, volume: float = 0.8):
        """Convert text to speech and play through speakers"""
        try:
            if not text or text.strip() == "":
                logger.warning("Empty text provided for TTS")
                return False
                
            # Use default voice if not specified
            if not voice:
                voice = self.default_voice
                
            # Create cache key from text and parameters
            cache_key = self._generate_cache_key(text, voice, speed)
            cache_file = self.cache_dir / f"{cache_key}.wav"
            
            # Check cache
            if not cache_file.exists():
                logger.info(f"Generating TTS for: {text[:50]}...")
                success = await self._generate_tts(text, voice, speed, cache_file)
                if not success:
                    logger.error("Failed to generate TTS")
                    return False
            else:
                logger.info("Using cached TTS file")
            
            # Play audio file
            await self._play_audio(cache_file, volume)
            return True
            
        except Exception as e:
            logger.error(f"Error in TTS speak: {e}")
            return False
    
    async def stop(self):
        """Stop current TTS playback"""
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
        """Clear TTS cache"""
        try:
            for cache_file in self.cache_dir.glob("*.wav"):
                cache_file.unlink()
            logger.info("TTS cache cleared")
        except Exception as e:
            logger.error(f"Error clearing TTS cache: {e}")
    
    def get_cache_size(self) -> int:
        """Get cache size (number of files)"""
        return len(list(self.cache_dir.glob("*.wav")))
    
    def _generate_cache_key(self, text: str, voice: str, speed: float) -> str:
        """Create cache key from text and parameters"""
        content = f"{text}_{voice}_{speed}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _init_stylish_tts(self):
        """Initialize Stylish-TTS model"""
        try:
            if not self.onnx_model_path.exists():
                logger.error(f"ONNX model not found at {self.onnx_model_path}")
                return
                
            # Load model config from ONNX metadata
            model_config_str = self._read_meta_data_onnx(str(self.onnx_model_path), "model_config")
            if not model_config_str:
                logger.error("No model_config found in ONNX metadata")
                return
                
            self.model_config = ModelConfig.model_validate_json(model_config_str)
            self.text_cleaner = TextCleaner(self.model_config.symbol)
            
            # Initialize ONNX session
            self.session = ort.InferenceSession(
                str(self.onnx_model_path),
                providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
            )
            
            logger.info("Stylish-TTS model initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Stylish-TTS: {e}")
            
    def _read_meta_data_onnx(self, filename, key):
        """Read metadata from ONNX model"""
        try:
            model = onnx.load(filename)
            for prop in model.metadata_props:
                if prop.key == key:
                    return prop.value
        except Exception as e:
            logger.error(f"Error reading ONNX metadata: {e}")
        return None
        
    def _arrowize(self, ipa: str) -> str:
        """Convert tone numbers to arrows"""
        return re.sub(r"[1-6]", lambda m: self.tone_arrow[m.group()], ipa)
        
    def _split_text_into_chunks(self, text, max_sentences=2):
        """Split text into manageable chunks"""
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        return [' '.join(sentences[i:i + max_sentences]) for i in range(0, len(sentences), max_sentences)]
        
    def _split_text_with_pause(self, text):
        """Handle pause tags in text"""
        parts = re.split(r'(<pause\s+\d+>)', text)
        result = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if part.startswith("<pause"):
                match = re.match(r'<pause\s+(\d+)>', part)
                if match:
                    pause_duration = int(match.group(1))
                    result.append(("pause", pause_duration))
            else:
                result.append(("text", part))
        return result
        
    def _synthesize_chunk(self, text_input):
        """Synthesize a single chunk of text"""
        try:
            cleaner = ViCleaner(text_input)
            normalized_text = cleaner.clean()
            ipa_num, _ = self.g2p(normalized_text)
            ipa_arrow = self._arrowize(ipa_num)

            tokens = torch.tensor(self.text_cleaner(ipa_arrow)).unsqueeze(0)
            texts = torch.zeros([1, tokens.shape[1] + 2], dtype=int)
            texts[0][1 : tokens.shape[1] + 1] = tokens
            text_lengths = torch.zeros([1], dtype=int)
            text_lengths[0] = tokens.shape[1] + 2

            outputs = self.session.run(
                None,
                {
                    "texts": texts.cpu().numpy(),
                    "text_lengths": text_lengths.cpu().numpy(),
                },
            )
            samples = np.multiply(outputs[0], 32768).astype(np.int16)
            return samples
            
        except Exception as e:
            logger.error(f"Error synthesizing chunk: {e}")
            return None

    async def _generate_tts(self, text: str, voice: str, speed: float, output_file: Path) -> bool:
        """Create TTS file using Stylish-TTS"""
        try:
            if not self.session or not self.text_cleaner:
                logger.error("Stylish-TTS not properly initialized")
                return False
                
            logger.info(f"Generating TTS with Stylish-TTS for: {text[:50]}...")
            
            # Process text with pause handling
            parts = self._split_text_with_pause(text)
            full_audio = AudioSegment.empty()
            
            for part_type, content in parts:
                if part_type == "text":
                    chunks = self._split_text_into_chunks(content, max_sentences=2)
                    for chunk in chunks:
                        if chunk.strip() == "":
                            continue
                        logger.debug(f"Synthesizing chunk: {chunk}")
                        samples = self._synthesize_chunk(chunk)
                        if samples is not None:
                            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
                                write(tmpfile.name, 24000, samples)
                                audio = AudioSegment.from_wav(tmpfile.name)
                                full_audio += audio
                                os.remove(tmpfile.name)
                elif part_type == "pause":
                    logger.debug(f"Adding pause: {content}ms")
                    pause_audio = AudioSegment.silent(duration=content)
                    full_audio += pause_audio
            
            # Export final audio
            full_audio.export(str(output_file), format="wav")
            logger.info("TTS generated successfully with Stylish-TTS")
            return True
            
        except Exception as e:
            logger.error(f"Error generating TTS with Stylish-TTS: {e}")
            return False
    
    async def _play_audio(self, audio_file: Path, volume: float):
        """Play audio file"""
        try:
            # Adjust volume (0.0 - 1.0)
            volume_percent = int(volume * 100)
            
            # Try using aplay
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