import os
import io
import tempfile
import logging
import numpy as np
import matplotlib.pyplot as plt
import librosa
import librosa.display
from pydub import AudioSegment

# Configure logging
logger = logging.getLogger(__name__)

def generate_waveform_image(audio_path, output_path=None, duration=30):
    """
    Generate a waveform image from an audio file.
    
    Args:
        audio_path (str): Path to the audio file.
        output_path (str, optional): Path to save the output image. If None, a temp file is created.
        duration (int, optional): Duration in seconds to use for the preview. Defaults to 30 seconds.
    
    Returns:
        str: Path to the generated waveform image.
    """
    try:
        # Create output path if not provided
        if output_path is None:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                output_path = temp_file.name
        
        # Load audio file
        y, sr = librosa.load(audio_path, duration=duration)
        
        # Create figure
        plt.figure(figsize=(10, 3))
        plt.axis('off')  # Hide axes
        
        # Generate waveform
        librosa.display.waveshow(y, sr=sr, alpha=0.6)
        plt.title('Waveform Preview')
        plt.tight_layout()
        
        # Save figure
        plt.savefig(output_path, dpi=100, bbox_inches='tight', pad_inches=0.1)
        plt.close()
        
        return output_path
    
    except Exception as e:
        logger.error(f"Error generating waveform: {e}")
        if output_path and os.path.exists(output_path):
            os.remove(output_path)
        return None

def create_audio_preview(audio_path, output_path=None, duration=30):
    """
    Create a shorter preview of the audio file.
    
    Args:
        audio_path (str): Path to the audio file.
        output_path (str, optional): Path to save the output audio. If None, a temp file is created.
        duration (int, optional): Duration in seconds for the preview. Defaults to 30 seconds.
    
    Returns:
        str: Path to the generated audio preview.
    """
    try:
        # Create output path if not provided
        if output_path is None:
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                output_path = temp_file.name
        
        # Load audio using pydub
        audio = AudioSegment.from_file(audio_path)
        
        # Get total duration in milliseconds
        total_duration = len(audio)
        preview_duration = min(duration * 1000, total_duration)
        
        # Take up to 'duration' seconds from the middle of the song
        middle_point = total_duration // 2
        start_time = max(0, middle_point - preview_duration // 2)
        end_time = min(total_duration, start_time + preview_duration)
        
        # Extract the preview segment
        preview = audio[start_time:end_time]
        
        # Export to output path
        preview.export(output_path, format="mp3")
        
        return output_path
    
    except Exception as e:
        logger.error(f"Error creating audio preview: {e}")
        if output_path and os.path.exists(output_path):
            os.remove(output_path)
        return None

def generate_preview_bundle(audio_path, image_path=None, audio_preview_path=None, duration=30):
    """
    Generate both a waveform image and audio preview for a given audio file.
    
    Args:
        audio_path (str): Path to the audio file.
        image_path (str, optional): Path to save the waveform image.
        audio_preview_path (str, optional): Path to save the audio preview.
        duration (int, optional): Duration in seconds for the preview. Defaults to 30 seconds.
    
    Returns:
        tuple: (image_path, audio_preview_path) or (None, None) if failed.
    """
    try:
        # Generate audio preview
        preview_path = create_audio_preview(audio_path, audio_preview_path, duration)
        if not preview_path:
            return None, None
        
        # Generate waveform from the preview (more efficient than using the full file)
        waveform_path = generate_waveform_image(preview_path, image_path, duration)
        if not waveform_path:
            if os.path.exists(preview_path):
                os.remove(preview_path)
            return None, None
        
        return waveform_path, preview_path
    
    except Exception as e:
        logger.error(f"Error generating preview bundle: {e}")
        return None, None