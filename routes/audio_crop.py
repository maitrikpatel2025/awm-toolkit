from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from app_utils import verify_api_key, queue_task
from models.audio_crop import AudioCropRequest
from services.audio_croping import process_audio_crop
from services.cloud_storage import upload_file
import logging
import os

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/crop-audio",
    summary="Crop audio file",
    description="Crop an audio file using start and end timestamps. Supports MP3, WAV, and other audio formats.",
    response_description="URL to the cropped audio file",
    tags=["Audio Processing"])
@queue_task()
async def crop_audio_file(
    request: Request,
    crop_request: AudioCropRequest,
    api_key: str = Depends(verify_api_key)
):
    job_id = request.state.job_id
    logger.info(f"Job {job_id}: Received audio crop request for {crop_request.media_url}")
    
    try:
        # Process the audio crop
        result = await run_in_threadpool(
            process_audio_crop,
            str(crop_request.media_url),
            crop_request.start_time,
            crop_request.end_time
        )
        logger.info(f"Job {job_id}: Audio crop process completed successfully")

        # Upload to cloud storage
        cloud_url = await run_in_threadpool(upload_file, result)
        
        # Clean up the temporary file after uploading
        if result and os.path.exists(result):
            os.remove(result)
            
        return cloud_url, "/crop-audio", 200
        
    except Exception as e:
        logger.error(f"Job {job_id}: Error during audio cropping process - {str(e)}")
        return str(e), "/crop-audio", 500