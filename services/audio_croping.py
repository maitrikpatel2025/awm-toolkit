import os
import logging
import ffmpeg
from pathlib import Path
from services.file_management import download_file
import uuid

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Set the default local storage directory
STORAGE_PATH = "/tmp/"

def process_audio_crop(media_url: str, start_time: str, end_time: str, language=None):
    """
    Process audio cropping with proper logging and file management.
    
    Args:
        media_url (str): URL of the input audio file
        start_time (str): Start time in format HH:MM:SS or MM:SS
        end_time (str): End time in format HH:MM:SS or MM:SS
        language (str, optional): Language code (not used, kept for consistency)
        
    Returns:
        str: Path to the cropped audio file
        
    Raises:
        Exception: If cropping fails
    """
    logger.info(f"Starting audio crop for media URL: {media_url}")
    logger.info(f"Time range: {start_time} to {end_time}")
    
    input_filename = None
    output_filename = None
    
    try:
        # Download the input file
        input_filename = download_file(media_url, STORAGE_PATH)
        logger.info(f"Downloaded media to local file: {input_filename}")

        try:
            # Determine input file extension
            input_ext = os.path.splitext(input_filename)[1]
            if not input_ext:
                input_ext = '.mp3'  # Default to mp3 if no extension
                
            # Generate unique output filename
            output_filename = os.path.join(STORAGE_PATH, f"{uuid.uuid4()}{input_ext}")
            
            # Convert time format if needed (MM:SS to HH:MM:SS)
            start_time = _normalize_timestamp(start_time)
            end_time = _normalize_timestamp(end_time)
            
            # Calculate duration
            duration = _calculate_duration(end_time, start_time)
            logger.info(f"Calculated duration: {duration} seconds")
            
            # Check if input file is accessible and valid
            if not os.path.exists(input_filename) or os.path.getsize(input_filename) == 0:
                raise ValueError("Input file does not exist or is empty")
            
            # Build and run ffmpeg command
            stream = ffmpeg.input(input_filename, ss=start_time)
            stream = ffmpeg.output(stream, output_filename, t=duration, acodec='copy')
            ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
            
            # Verify output file
            if not os.path.exists(output_filename) or os.path.getsize(output_filename) == 0:
                raise Exception("Failed to generate cropped audio file")
                
            logger.info(f"Audio crop completed successfully: {output_filename}")
            
            # Clean up input file
            os.remove(input_filename)
            logger.info(f"Removed input file: {input_filename}")
            
            return output_filename
            
        except Exception as e:
            logger.error(f"Audio cropping failed: {str(e)}")
            if input_filename and os.path.exists(input_filename):
                os.remove(input_filename)
            if output_filename and os.path.exists(output_filename):
                os.remove(output_filename)
            raise
            
    except Exception as e:
        logger.error(f"Audio cropping failed: {str(e)}")
        if input_filename and os.path.exists(input_filename):
            os.remove(input_filename)
        if output_filename and os.path.exists(output_filename):
            os.remove(output_filename)
        raise

def _normalize_timestamp(timestamp: str) -> str:
    """
    Normalize timestamp to HH:MM:SS format.
    
    Args:
        timestamp (str): Time in format HH:MM:SS or MM:SS
        
    Returns:
        str: Normalized timestamp in HH:MM:SS format
    """
    parts = timestamp.split(':')
    if len(parts) == 2:
        return f"00:{timestamp}"
    return timestamp

def _calculate_duration(end_time: str, start_time: str) -> str:
    """
    Calculate duration between two timestamps.
    
    Args:
        end_time (str): End time in HH:MM:SS format
        start_time (str): Start time in HH:MM:SS format
        
    Returns:
        str: Duration in seconds
        
    Raises:
        ValueError: If end time is before start time
    """
    def time_to_seconds(time_str):
        h, m, s = map(int, time_str.split(':'))
        return h * 3600 + m * 60 + s
        
    end_seconds = time_to_seconds(end_time)
    start_seconds = time_to_seconds(start_time)
    duration = end_seconds - start_seconds
    
    if duration <= 0:
        raise ValueError("End time must be after start time")
        
    return str(duration)