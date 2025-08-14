from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
import logging
from typing import Optional
from ..modules.tts_engine import TTSEngine
from ..config.settings import Settings

logger = logging.getLogger(__name__)

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "default"
    speed: Optional[float] = 1.0
    volume: Optional[float] = 0.8

class WebhookService:
    def __init__(self, tts_engine: TTSEngine, settings: Settings, hc3_listener=None):
        self.app = FastAPI(title="Media Center Webhook Service")
        self.tts_engine = tts_engine
        self.settings = settings
        self.hc3_listener = hc3_listener
        self.setup_routes()
        
    def setup_routes(self):
        """Setup API endpoints"""
        
        @self.app.post("/tts")
        async def text_to_speech(request: TTSRequest):
            """API endpoint to receive text and convert to speech"""
            try:
                if not request.text or request.text.strip() == "":
                    raise HTTPException(status_code=400, detail="Text cannot be empty")
                
                logger.info(f"Received TTS request: {request.text}")
                
                # Convert text to speech and play
                await self.tts_engine.speak(
                    text=request.text,
                    voice=request.voice,
                    speed=request.speed,
                    volume=request.volume
                )
                
                return {"status": "success", "message": "Text converted to speech successfully"}
                
            except Exception as e:
                logger.error(f"Error in TTS request: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {"status": "healthy", "service": "webhook_service"}
        
        @self.app.post("/hc3/command")
        async def hc3_command(command: dict):
            """API endpoint to receive commands from HC3"""
            try:
                logger.info(f"Received HC3 command: {command}")
                
                if self.hc3_listener:
                    await self.hc3_listener.handle_command(command)
                    return {"status": "success", "message": "Command processed"}
                else:
                    raise HTTPException(status_code=503, detail="HC3 listener not available")
                    
            except Exception as e:
                logger.error(f"Error processing HC3 command: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/status")
        async def service_status():
            """Service status"""
            return {
                "service": "webhook_service",
                "tts_engine": "available" if self.tts_engine else "unavailable",
                "hc3_listener": "available" if self.hc3_listener else "unavailable",
                "endpoints": ["/tts", "/hc3/command", "/health", "/status"]
            }
    
    async def start(self, host: str = "0.0.0.0", port: int = 8000):
        """Start webhook service"""
        try:
            import uvicorn
            logger.info(f"Starting webhook service on {host}:{port}")
            
            config = uvicorn.Config(
                app=self.app,
                host=host,
                port=port,
                log_level="info"
            )
            server = uvicorn.Server(config)
            await server.serve()
            
        except Exception as e:
            logger.error(f"Error starting webhook service: {e}")
            raise
    
    def stop(self):
        """Stop webhook service"""
        logger.info("Webhook service stopped")