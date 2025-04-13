import os
import re
import logging

# Configure logging
logger = logging.getLogger(__name__)

def clean_filename(filename):
    """
    Clean a filename to make it safe for file systems.
    
    Args:
        filename (str): The filename to clean.
    
    Returns:
        str: A cleaned filename.
    """
    # Replace invalid characters with underscores
    cleaned = re.sub(r'[\\/*?:"<>|]', "_", filename)
    # Remove leading/trailing spaces and periods
    cleaned = cleaned.strip(". ")
    # Ensure the filename is not too long
    if len(cleaned) > 200:
        cleaned = cleaned[:200]
    return cleaned

def get_download_path(filename, extension="mp3"):
    """
    Generate a download path for a file.
    
    Args:
        filename (str): The base filename.
        extension (str, optional): The file extension. Defaults to "mp3".
    
    Returns:
        str: A path to save the downloaded file.
    """
    # Ensure the downloads directory exists
    os.makedirs("downloads", exist_ok=True)
    
    # Clean the filename
    clean_name = clean_filename(filename)
    
    # Generate the full path
    download_path = os.path.join("downloads", f"{clean_name}.{extension}")
    
    return download_path
