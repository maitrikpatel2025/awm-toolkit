from fastapi import FastAPI
from fastapi.security import HTTPBearer
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Media Processing API",
    description="API for processing media files including transcription, conversion, and more",
    version="1.0.0"
)

# Define security scheme
security = HTTPBearer()

# Import and register routers
from routes import authenticate, transcribe_media, combine_audios, background_removal, audio_crop, user_routes

app.include_router(user_routes.router)
app.include_router(authenticate.router)
app.include_router(transcribe_media.router)
app.include_router(combine_audios.router)
app.include_router(background_removal.router)
app.include_router(audio_crop.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)