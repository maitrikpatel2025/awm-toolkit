import os
import uuid
import requests
import mimetypes
from urllib.parse import urlparse, parse_qs

def download_file(url, storage_path="/tmp/"):
    # Parse the URL to extract the file ID from the query parameters
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    
    # Generate a unique file ID
    file_id = str(uuid.uuid4())
    
    # Ensure the storage directory exists
    if not os.path.exists(storage_path):
        os.makedirs(storage_path)
    
    # Download the file headers first to check content type
    response = requests.head(url, allow_redirects=True)
    content_type = response.headers.get('content-type', '')
    
    # Try to get extension from content type
    extension = mimetypes.guess_extension(content_type)
    
    # If no extension found from content type, try to get it from URL
    if not extension:
        url_path = parsed_url.path
        _, url_extension = os.path.splitext(url_path)
        extension = url_extension if url_extension else '.tmp'
    
    # Clean up the extension (remove dot if present)
    extension = extension.lstrip('.').lower()
    
    # Map common content types to extensions
    extension_map = {
        'image/jpeg': 'jpg',
        'image/png': 'png',
        'image/webp': 'webp',
        'video/mp4': 'mp4',
        'video/quicktime': 'mov',
        'audio/mpeg': 'mp3',
        'audio/wav': 'wav',
        'audio/x-wav': 'wav',
        'application/x-subrip': 'srt',
        'text/vtt': 'vtt'
    }
    
    # Use mapped extension if available
    if content_type in extension_map:
        extension = extension_map[content_type]
    
    # Construct the local filename
    local_filename = os.path.join(storage_path, f"{file_id}.{extension}")
    
    # Download the file
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    with open(local_filename, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    return local_filename


def delete_old_files():
    now = time.time()
    for filename in os.listdir(STORAGE_PATH):
        file_path = os.path.join(STORAGE_PATH, filename)
        if os.path.isfile(file_path) and os.stat(file_path).st_mtime < now - 3600:
            os.remove(file_path)