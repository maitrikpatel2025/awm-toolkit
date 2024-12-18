from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Request
from models.background_removal import BackgroundRemovalRequest
from fastapi.concurrency import run_in_threadpool
from services.background_removing import process_background_removal
from app_utils import verify_api_key, queue_task
from services.cloud_storage import upload_file
import os
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/remove-background",
    summary="Remove background from image using AI",
    description="Uses AI to remove the background from the uploaded image",
    response_description="remove the background",
    tags=["Background Removal"])
@queue_task()
async def remove_background(
    request: Request,
    background_removal_request: BackgroundRemovalRequest,
    api_key: str = Depends(verify_api_key)
):
    job_id = request.state.job_id
    logger.info(f"Job {job_id}: Received background removal request for {background_removal_request.media_url}")
    
    try:
        result = await run_in_threadpool(
            process_background_removal,
            str(background_removal_request.media_url),
            background_removal_request.output_format.value,
            background_removal_request.webhook_url
        )
        logger.info(f"Job {job_id}: Background removal process completed successfully")

        cloud_url = await run_in_threadpool(upload_file, result)
        if os.path.exists(result):
            os.remove(result)
            logger.info(f"Job {job_id}: Cleaned up local file {result}")

        return cloud_url, "/remove-background", 200
        
    except Exception as e:
        logger.error(f"Job {job_id}: Error during background removal process - {str(e)}")
        return str(e), "/remove-background", 500