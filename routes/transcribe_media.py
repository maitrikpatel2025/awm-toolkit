from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from app_utils import TranscribeRequest, verify_api_key, queue_task
from services.transcription import process_transcription
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/transcribe-media",
    summary="Transcribe media file",
    description="Convert media file to transcript, SRT, VTT, or ASS format",
    response_description="Transcription result or job status",
    tags=["Transcription"])
@queue_task()
async def transcribe_media(
    request: Request,
    transcribe_request: TranscribeRequest,
    api_key: str = Depends(verify_api_key)
):
    logger.info(f"Received transcription request for {transcribe_request.media_url}")
    
    result = await run_in_threadpool(
        process_transcription,
        str(transcribe_request.media_url),
        transcribe_request.output.value,
        transcribe_request.max_chars
    )
    return result, "/transcribe-media", 200