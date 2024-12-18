from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from app_utils import  verify_api_key, queue_task
from models.transcribe_request import TranscribeRequest
from services.transcription import process_transcription
from services.cloud_storage import upload_file
import logging
import os

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/transcribe-media",
    summary="Transcribe media file",
    description="Convert media file to transcript, SRT, VTT, or ASS format",
    response_description="Transcription result or job status",
    tags=["Transcription"])
@queue_task(bypass_queue=False)
async def transcribe_media(
    request: Request,
    transcribe_request: TranscribeRequest,
    api_key: str = Depends(verify_api_key)
):
    job_id = request.state.job_id
    logger.info(f"Job {job_id}: Received transcription request for {transcribe_request.media_url}")
    
    try:
        result = await run_in_threadpool(
            process_transcription,
            str(transcribe_request.media_url),
            transcribe_request.output.value,
            transcribe_request.max_chars
        )
        logger.info(f"Job {job_id}: Transcription process completed successfully")

        # Handle file uploads for subtitle formats
        if transcribe_request.output.value in ['srt', 'vtt', 'ass']:
            cloud_url = await run_in_threadpool(upload_file, result)
            os.remove(result)  # Remove the temporary file after uploading
            return cloud_url, "/transcribe-media", 200
        
        return result, "/transcribe-media", 200
        
    except Exception as e:
        logger.error(f"Job {job_id}: Error during transcription process - {str(e)}")
        return str(e), "/transcribe-media", 500