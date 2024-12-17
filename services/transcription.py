import os
import whisper
import srt
from datetime import timedelta
from whisper.utils import WriteSRT, WriteVTT
from services.file_management import download_file
import logging
import uuid

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Set the default local storage directory
STORAGE_PATH = "../test_data"
def process_transcription(media_url, output_type, max_chars=56, language=None):
    logger.info(f"Starting transcription for media URL: {media_url} with output type: {output_type}")
    input_filename = None
    try:
        input_filename = download_file(media_url, os.path.join(STORAGE_PATH, 'input_media'))
        logger.info(f"Downloaded media to local file: {input_filename}")

        try:
            model = whisper.load_model("base")
            logger.info("Loaded Whisper model")

            # Check if file is accessible and valid (optional)
            if not os.path.exists(input_filename) or os.path.getsize(input_filename) == 0:
                raise ValueError("Input file does not exist or is empty.")

            # Transcribe
            result = model.transcribe(input_filename, language=language)
            logger.info("Transcription completed")

            if output_type == 'transcript':
                output = result['text']
                logger.info("Generated transcript output")
            elif output_type in ['srt', 'vtt']:
                srt_subtitles = []
                for i, segment in enumerate(result['segments'], start=1):
                    start = timedelta(seconds=segment['start'])
                    end = timedelta(seconds=segment['end'])
                    text = segment['text'].strip()
                    srt_subtitles.append(srt.Subtitle(i, start, end, text))
                
                output_content = srt.compose(srt_subtitles)
                output_filename = os.path.join(STORAGE_PATH, f"{uuid.uuid4()}.{output_type}")
                with open(output_filename, 'w') as f:
                    f.write(output_content)
                output = output_filename
                logger.info(f"Generated {output_type.upper()} output: {output}")

            else:
                raise ValueError("Invalid output type. Must be 'transcript', 'srt', or 'vtt'.")

            os.remove(input_filename)
            logger.info(f"Removed local file: {input_filename}")
            logger.info(f"Transcription successful, output type: {output_type}")
            return output
        except Exception as e:
            logger.error(f"Transcription failed: {str(e)}")
            if input_filename and os.path.exists(input_filename):
                os.remove(input_filename)
            raise
    except Exception as e:
        logger.error(f"Transcription failed: {str(e)}")
        if input_filename and os.path.exists(input_filename):
            os.remove(input_filename)
        raise


def generate_ass_subtitle(result, max_chars):
    """Generate ASS subtitle content with highlighted current words, showing one line at a time."""
    logger.info("Generate ASS subtitle content with highlighted current words")
    # ASS file header
    ass_content = ""

    # Helper function to format time
    def format_time(t):
        hours = int(t // 3600)
        minutes = int((t % 3600) // 60)
        seconds = int(t % 60)
        centiseconds = int(round((t - int(t)) * 100))
        return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"

    max_chars_per_line = max_chars  # Maximum characters per line

    # Process each segment
    for segment in result['segments']:
        words = segment.get('words', [])
        if not words:
            continue  # Skip if no word-level timestamps

        # Group words into lines
        lines = []
        current_line = []
        current_line_length = 0
        for word_info in words:
            word_length = len(word_info['word']) + 1  # +1 for space
            if current_line_length + word_length > max_chars_per_line:
                lines.append(current_line)
                current_line = [word_info]
                current_line_length = word_length
            else:
                current_line.append(word_info)
                current_line_length += word_length
        if current_line:
            lines.append(current_line)

        # Generate events for each line
        for line in lines:
            line_start_time = line[0]['start']
            line_end_time = line[-1]['end']

            # Generate events for highlighting each word
            for i, word_info in enumerate(line):
                start_time = word_info['start']
                end_time = word_info['end']
                current_word = word_info['word']

                # Build the line text with highlighted current word
                caption_parts = []
                for w in line:
                    word_text = w['word']
                    if w == word_info:
                        # Highlight current word
                        caption_parts.append(r'{\c&H00FFFF&}' + word_text)
                    else:
                        # Default color
                        caption_parts.append(r'{\c&HFFFFFF&}' + word_text)
                caption_with_highlight = ' '.join(caption_parts)

                # Format times
                start = format_time(start_time)
                # End the dialogue event when the next word starts or at the end of the line
                if i + 1 < len(line):
                    end_time = line[i + 1]['start']
                else:
                    end_time = line_end_time
                end = format_time(end_time)

                # Add the dialogue line
                ass_content += f"Dialogue: 0,{start},{end},Default,,0,0,0,,{caption_with_highlight}\n"

    return ass_content