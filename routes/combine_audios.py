from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from app_utils import  verify_api_key, queue_task, current_user_id
from models.combine_audio_request import CombineAudioRequest
from services.ffmpeg_toolkit import process_audio_combination
from services.cloud_storage import upload_file
import logging
import os

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/combine-audios", 
    summary="Combine audio files",
    description="Combine audio files into a single file",
    response_description="Combined audio file",
    tags=["Audio"])
@queue_task()
async def combine_audios(
    request: Request,
    combine_audio_request: CombineAudioRequest,
    api_key: str = Depends(verify_api_key)
):
    job_id = request.state.job_id

    logger.info(f"Job {job_id}: Received combine-audios request for {len(combine_audio_request.audio_urls)} audio files")
    
    try:
        output_file = await run_in_threadpool(
            process_audio_combination,
            combine_audio_request.audio_urls,
            job_id
        )
        logger.info(f"Job {job_id}: Audio combination process completed successfully")

        cloud_url = await run_in_threadpool(upload_file, output_file)
        logger.info(f"Job {job_id}: Combined audio uploaded to cloud storage: {cloud_url}")

        # Clean up the local file after successful upload
        if os.path.exists(output_file):
            os.remove(output_file)
            logger.info(f"Job {job_id}: Cleaned up local file {output_file}")

        return cloud_url, "/combine-audios", 200

    except Exception as e:
        logger.error(f"Job {job_id}: Error during audio combination process - {str(e)}")
        return str(e), "/combine-audios", 500