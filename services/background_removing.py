import os
import logging
import uuid
from rembg import remove
from PIL import Image
from services.file_management import download_file

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Set the default local storage directory
STORAGE_PATH = "/tmp/"

def process_background_removal(media_url, output_format='png', webhook_url=None):
    logger.info(f"Starting background removal for media URL: {media_url} with output format: {output_format}")
    input_filename = None
    try:
        # Download the file
        input_filename = download_file(media_url, os.path.join(STORAGE_PATH, 'input_media'))
        logger.info(f"Downloaded media to local file: {input_filename}")

        # Check if file is accessible and valid
        if not os.path.exists(input_filename) or os.path.getsize(input_filename) == 0:
            raise ValueError("Input file does not exist or is empty.")

        # Process the image
        input_image = Image.open(input_filename)
        output_image = remove(input_image)
        logger.info("Background removal completed")

        # Save the processed image
        output_filename = os.path.join(STORAGE_PATH, f"{uuid.uuid4()}.{output_format}")
        output_image.save(output_filename, format=output_format.upper())
        logger.info(f"Saved processed image to: {output_filename}")

        # Clean up input file
        os.remove(input_filename)
        logger.info(f"Removed input file: {input_filename}")

        return output_filename

    except Exception as e:
        logger.error(f"Background removal failed: {str(e)}")
        if input_filename and os.path.exists(input_filename):
            os.remove(input_filename)
        raise