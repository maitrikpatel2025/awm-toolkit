from fastapi import Header, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, Callable
from pydantic import BaseModel, HttpUrl
from enum import Enum
from queue import Queue
import threading
import uuid
import os
import time
from services.webhook import send_webhook
from version import BUILD_NUMBER
from functools import wraps
import asyncio

# Pydantic base models
class OutputType(str, Enum):
    transcript = "transcript"
    srt = "srt"
    vtt = "vtt"
    ass = "ass"

class TranscribeRequest(BaseModel):
    media_url: HttpUrl
    output: Optional[OutputType] = OutputType.transcript
    webhook_url: Optional[HttpUrl] = None
    max_chars: Optional[int] = 56
    id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "media_url": "https://example.com/media.mp4",
                "output": "transcript",
                "webhook_url": "https://example.com/webhook",
                "max_chars": 56,
                "id": "123"
            }
        }

# Authentication dependency
async def verify_api_key(x_api_key: str = Header(..., description="API Key for authentication")):
    if x_api_key != os.environ.get('API_KEY'):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return x_api_key

# Queue setup
task_queue = Queue()
queue_id = id(task_queue)
MAX_QUEUE_LENGTH = int(os.environ.get('MAX_QUEUE_LENGTH', 0))

def process_queue():
    """Process tasks from the queue in a separate thread"""
    async def process_task(job_id, data, task_func, queue_start_time):
        queue_time = time.time() - queue_start_time
        run_start_time = time.time()
        pid = os.getpid()
        
        try:
            # Execute the task function
            response = await task_func()
            run_time = time.time() - run_start_time
            total_time = time.time() - queue_start_time

            response_data = {
                "endpoint": response[1],
                "code": response[2],
                "id": data.get("id"),
                "job_id": job_id,
                "response": response[0] if response[2] == 200 else None,
                "message": "success" if response[2] == 200 else response[0],
                "pid": pid,
                "queue_id": queue_id,
                "run_time": round(run_time, 3),
                "queue_time": round(queue_time, 3),
                "total_time": round(total_time, 3),
                "queue_length": task_queue.qsize(),
                "build_number": BUILD_NUMBER
            }

            if data.get("webhook_url"):
                await send_webhook(str(data["webhook_url"]), response_data)

        except Exception as e:
            error_response = {
                "code": 500,
                "id": data.get("id"),
                "job_id": job_id,
                "message": str(e),
                "pid": pid,
                "queue_id": queue_id,
                "queue_length": task_queue.qsize(),
                "build_number": BUILD_NUMBER
            }
            
            if data.get("webhook_url"):
                await send_webhook(str(data["webhook_url"]), error_response)

    while True:
        job_id, data, task_func, queue_start_time = task_queue.get()
        # Create event loop for async processing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(process_task(job_id, data, task_func, queue_start_time))
        task_queue.task_done()

# Start the queue processing thread
threading.Thread(target=process_queue, daemon=True).start()

def queue_task(bypass_queue: bool = False):
    """Decorator to handle task queueing"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            job_id = str(uuid.uuid4())
            data = kwargs.get('transcribe_request').dict() if 'transcribe_request' in kwargs else {}
            pid = os.getpid()
            start_time = time.time()

            if bypass_queue or not data.get('webhook_url'):
                try:
                    response = await func(request, *args, **kwargs)
                    run_time = time.time() - start_time
                    return JSONResponse(
                        status_code=response[2],
                        content={
                            "endpoint": response[1],
                            "code": response[2],
                            "id": data.get("id"),
                            "job_id": job_id,
                            "response": response[0] if response[2] == 200 else None,
                            "message": "success" if response[2] == 200 else response[0],
                            "run_time": round(run_time, 3),
                            "queue_time": 0,
                            "total_time": round(run_time, 3),
                            "pid": pid,
                            "queue_id": queue_id,
                            "queue_length": task_queue.qsize(),
                            "build_number": BUILD_NUMBER
                        }
                    )
                except Exception as e:
                    return JSONResponse(
                        status_code=500,
                        content={
                            "code": 500,
                            "message": str(e),
                            "job_id": job_id,
                            "pid": pid,
                            "queue_id": queue_id,
                            "queue_length": task_queue.qsize(),
                            "build_number": BUILD_NUMBER
                        }
                    )
            else:
                if MAX_QUEUE_LENGTH > 0 and task_queue.qsize() >= MAX_QUEUE_LENGTH:
                    return JSONResponse(
                        status_code=429,
                        content={
                            "code": 429,
                            "id": data.get("id"),
                            "job_id": job_id,
                            "message": f"MAX_QUEUE_LENGTH ({MAX_QUEUE_LENGTH}) reached",
                            "pid": pid,
                            "queue_id": queue_id,
                            "queue_length": task_queue.qsize(),
                            "build_number": BUILD_NUMBER
                        }
                    )
                
                task_queue.put((job_id, data, lambda: func(request, *args, **kwargs), start_time))
                
                return JSONResponse(
                    status_code=202,
                    content={
                        "code": 202,
                        "id": data.get("id"),
                        "job_id": job_id,
                        "message": "processing",
                        "pid": pid,
                        "queue_id": queue_id,
                        "max_queue_length": MAX_QUEUE_LENGTH if MAX_QUEUE_LENGTH > 0 else "unlimited",
                        "queue_length": task_queue.qsize(),
                        "build_number": BUILD_NUMBER
                    }
                )
        return wrapper
    return decorator