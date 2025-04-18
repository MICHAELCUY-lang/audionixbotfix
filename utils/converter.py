import os
import logging
import tempfile
import subprocess

# Configure logging
logger = logging.getLogger(__name__)

def convert_mp3_to_mp4(mp3_path):
    """
    Convert an MP3 file to MP4 using ffmpeg.
    
    Args:
        mp3_path (str): Path to the MP3 file.
    
    Returns:
        str: Path to the converted MP4 file.
    """
    try:
        # Create a temporary output file
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            output_path = temp_file.name
        
        # Get audio duration using ffprobe
        duration_cmd = [
            'ffprobe', 
            '-v', 'error', 
            '-show_entries', 'format=duration', 
            '-of', 'default=noprint_wrappers=1:nokey=1', 
            mp3_path
        ]
        
        try:
            # Get the duration of the audio file
            audio_duration = float(subprocess.check_output(duration_cmd).decode('utf-8').strip())
            logger.info(f"Detected audio duration: {audio_duration} seconds")
        except Exception as e:
            logger.warning(f"Could not determine audio duration: {e}, using default color source")
            audio_duration = 36000  # Use a very large default (10 hours)
        
        # Create a command to use ffmpeg for conversion
        # Generate a solid color video with the audio for the full duration
        command = [
            'ffmpeg',
            '-y',  # Overwrite output file if it exists
            '-f', 'lavfi',  # Use lavfi input format
            '-i', f'color=c=blue:s=1280x720:d={audio_duration}',  # Create blue background for full duration
            '-i', mp3_path,  # Input audio file
            '-shortest',  # End when the shortest input stream ends
            '-c:v', 'libx264',  # Video codec
            '-tune', 'stillimage',  # Optimize for still image
            '-c:a', 'aac',  # Audio codec
            '-b:a', '192k',  # Audio bitrate
            '-pix_fmt', 'yuv420p',  # Pixel format
            output_path  # Output file
        ]
        
        # Run the command
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logger.error(f"FFmpeg error: {stderr.decode()}")
            raise Exception(f"FFmpeg conversion failed with code {process.returncode}")
        
        return output_path
    
    except Exception as e:
        logger.error(f"Error converting MP3 to MP4: {e}")
        raise

def convert_mp4_to_mp3(mp4_path):
    """
    Convert an MP4 file to MP3 using ffmpeg.
    
    Args:
        mp4_path (str): Path to the MP4 file.
    
    Returns:
        str: Path to the converted MP3 file.
    """
    try:
        # Create a temporary output file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            output_path = temp_file.name
        
        # Use ffmpeg to extract audio from video
        command = [
            'ffmpeg',
            '-y',  # Overwrite output file if it exists
            '-i', mp4_path,  # Input video file
            '-vn',  # No video
            '-ar', '44100',  # Audio sample rate
            '-ac', '2',  # Audio channels
            '-b:a', '192k',  # Audio bitrate
            '-f', 'mp3',  # Output format
            output_path  # Output file
        ]
        
        # Run the command
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logger.error(f"FFmpeg error: {stderr.decode()}")
            raise Exception(f"FFmpeg conversion failed with code {process.returncode}")
        
        return output_path
    
    except Exception as e:
        logger.error(f"Error converting MP4 to MP3: {e}")
        raise
