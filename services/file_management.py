import os
import uuid
import requests
from urllib.parse import urlparse, parse_qs

def download_file(url: str, base_path: str) -> str:
    """Download file from URL and return local path"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(base_path, exist_ok=True)
        
        # Get file extension from URL
        parsed_url = urlparse(url)
        file_ext = os.path.splitext(parsed_url.path)[1]
        if not file_ext:
            file_ext = '.mp4' if 'video' in url else '.jpg'
            
        # Create output path
        output_path = os.path.join(base_path, f"file{file_ext}")
        
        # Download file
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        return output_path
        
    except Exception as e:
        logger.error(f"File download failed: {str(e)}")
        raise Exception(f"File download failed: {str(e)}")


def delete_old_files():
    now = time.time()
    for filename in os.listdir(STORAGE_PATH):
        file_path = os.path.join(STORAGE_PATH, filename)
        if os.path.isfile(file_path) and os.stat(file_path).st_mtime < now - 3600:
            os.remove(file_path)
