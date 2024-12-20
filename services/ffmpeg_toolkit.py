import os
import ffmpeg
import requests
from services.file_management import download_file
import logging

# Set the default local storage directory
STORAGE_PATH = "/tmp/"
logger = logging.getLogger(__name__)

def process_conversion(media_url, job_id, bitrate='128k', webhook_url=None):
    """Convert media to MP3 format with specified bitrate."""
    input_filename = download_file(media_url, os.path.join(STORAGE_PATH, f"{job_id}_input"))
    output_filename = f"{job_id}.mp3"
    output_path = os.path.join(STORAGE_PATH, output_filename)

    try:
        # Convert media file to MP3 with specified bitrate
        (
            ffmpeg
            .input(input_filename)
            .output(output_path, acodec='libmp3lame', audio_bitrate=bitrate)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        os.remove(input_filename)
        print(f"Conversion successful: {output_path} with bitrate {bitrate}")

        # Ensure the output file exists locally before attempting upload
        if not os.path.exists(output_path):
            raise FileNotFoundError(f"Output file {output_path} does not exist after conversion.")

        return output_path

    except Exception as e:
        print(f"Conversion failed: {str(e)}")
        raise

def process_video_combination(media_urls, job_id, webhook_url=None):
    """Combine multiple videos into one."""
    input_files = []
    output_filename = f"{job_id}.mp4"
    output_path = os.path.join(STORAGE_PATH, output_filename)

    try:
        # Download all media files
        for i, media_item in enumerate(media_urls):
            url = media_item['video_url']
            input_filename = download_file(url, os.path.join(STORAGE_PATH, f"{job_id}_input_{i}"))
            input_files.append(input_filename)

        # Generate an absolute path concat list file for FFmpeg
        concat_file_path = os.path.join(STORAGE_PATH, f"{job_id}_concat_list.txt")
        with open(concat_file_path, 'w') as concat_file:
            for input_file in input_files:
                # Write absolute paths to the concat list
                concat_file.write(f"file '{os.path.abspath(input_file)}'\n")

        # Use the concat demuxer to concatenate the videos
        (
            ffmpeg.input(concat_file_path, format='concat', safe=0).
                output(output_path, c='copy').
                run(overwrite_output=True)
        )

        # Clean up input files
        for f in input_files:
            os.remove(f)
            
        os.remove(concat_file_path)  # Remove the concat list file after the operation

        print(f"Video combination successful: {output_path}")

        # Check if the output file exists locally before upload
        if not os.path.exists(output_path):
            raise FileNotFoundError(f"Output file {output_path} does not exist after combination.")

        return output_path
    except Exception as e:
        print(f"Video combination failed: {str(e)}")
        raise 

def process_audio_combination(media_urls, job_id, webhook_url=None):
    """Combine multiple audio files into one."""
    input_files = []
    output_filename = f"{job_id}.mp3"
    output_path = os.path.join(STORAGE_PATH, output_filename)

    try:
        # Download all media files
        for i, media_item in enumerate(media_urls):
            url = media_item.audio_url
            input_filename = download_file(url, os.path.join(STORAGE_PATH, f"{job_id}_input_{i}"))
            input_files.append(input_filename)

        # Generate an absolute path concat list file for FFmpeg
        concat_file_path = os.path.join(STORAGE_PATH, f"{job_id}_concat_list.txt")
        with open(concat_file_path, 'w') as concat_file:
            for input_file in input_files:
                # Write absolute paths to the concat list
                concat_file.write(f"file '{os.path.abspath(input_file)}'\n")

        # Use the concat demuxer to concatenate the audio files
        (
            ffmpeg.input(concat_file_path, format='concat', safe=0)
            .output(output_path, acodec='libmp3lame', audio_bitrate='192k')
            .run(overwrite_output=True)
        )

        # Clean up input files
        for f in input_files:
            os.remove(f)
            
        os.remove(concat_file_path)  # Remove the concat list file after the operation

        print(f"Audio combination successful: {output_path}")

        # Check if the output file exists locally before upload
        if not os.path.exists(output_path):
            raise FileNotFoundError(f"Output file {output_path} does not exist after combination.")

        return output_path
    except Exception as e:
        print(f"Audio combination failed: {str(e)}")
        raise

def crop_audio(input_file: str, output_file: str, start_time: str, end_time: str) -> bool:
    """
    Crop audio file using start and end timestamps.
    
    Args:
        input_file (str): Path to input audio file
        output_file (str): Path to save output audio file
        start_time (str): Start time in format HH:MM:SS or MM:SS
        end_time (str): End time in format HH:MM:SS or MM:SS
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        import ffmpeg
        
        # Convert time format if needed (MM:SS to HH:MM:SS)
        if len(start_time.split(':')) == 2:
            start_time = f"00:{start_time}"
        if len(end_time.split(':')) == 2:
            end_time = f"00:{end_time}"
            
        # Build ffmpeg command
        stream = ffmpeg.input(input_file, ss=start_time, t=end_time)
        stream = ffmpeg.output(stream, output_file, acodec='copy')
        
        # Run the command
        ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
        
        return True
        
    except Exception as e:
        logger.error(f"Error cropping audio: {str(e)}")
        return False