import os
import re
import logging
import telegram

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

class DownloadProgressHook:
    """
    A progress hook for yt-dlp that reports download progress to the user.
    """
    def __init__(self, bot, chat_id, status_message=None):
        """
        Initialize the hook.
        
        Args:
            bot: The Telegram bot instance
            chat_id: The chat ID to send progress updates to
            status_message: Optional message object to edit for progress updates
        """
        self.bot = bot
        self.chat_id = chat_id
        self.status_message = status_message
        self.last_percentage = -1
        self.download_speed = "0 KiB/s"
        self.eta = "Unknown"
        self.downloaded_bytes = 0
        self.total_bytes = 0
        
    def __call__(self, d):
        """
        Called by yt-dlp with download progress updates.
        
        Args:
            d: The progress information dictionary from yt-dlp
        """
        if d['status'] == 'downloading':
            # Extract progress information
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded_bytes = d.get('downloaded_bytes', 0)
            
            if total_bytes > 0:
                self.total_bytes = total_bytes
                self.downloaded_bytes = downloaded_bytes
                
                # Calculate percentage
                percentage = int(downloaded_bytes / total_bytes * 100)
                
                # Only update if percentage has changed significantly (every 5%)
                if percentage >= self.last_percentage + 5 or percentage == 100:
                    # Get download speed and ETA
                    self.download_speed = d.get('speed', 0)
                    if self.download_speed:
                        self.download_speed = f"{self.download_speed/1024:.1f} KiB/s"
                    else:
                        self.download_speed = "Unknown"
                        
                    self.eta = d.get('eta', 'Unknown')
                    if isinstance(self.eta, (int, float)):
                        minutes, seconds = divmod(self.eta, 60)
                        self.eta = f"{int(minutes)}:{int(seconds):02d}"
                    
                    # Create progress bar
                    progress_bar = self._create_progress_bar(percentage)
                    
                    # Create message text
                    message_text = (
                        f"Downloading: {percentage}%\n"
                        f"{progress_bar}\n"
                        f"Speed: {self.download_speed} | ETA: {self.eta}"
                    )
                    
                    # Update message
                    self._update_progress(message_text)
                    
                    self.last_percentage = percentage
                    
        elif d['status'] == 'finished':
            # Download is complete
            message_text = "Download complete! Processing file..."
            self._update_progress(message_text)
            
        elif d['status'] == 'error':
            # An error occurred
            message_text = f"Error during download: {d.get('error', 'Unknown error')}"
            self._update_progress(message_text)
    
    def _create_progress_bar(self, percentage, length=20):
        """
        Create a text-based progress bar.
        
        Args:
            percentage: The current percentage (0-100)
            length: The length of the progress bar in characters
            
        Returns:
            str: A text progress bar
        """
        filled_length = int(length * percentage // 100)
        bar = '█' * filled_length + '░' * (length - filled_length)
        return f"[{bar}]"
    
    def _update_progress(self, text):
        """
        Update the progress message.
        
        Args:
            text: The text to display
        """
        try:
            if self.status_message:
                # Edit existing message
                self.bot.edit_message_text(
                    chat_id=self.chat_id,
                    message_id=self.status_message.message_id,
                    text=text
                )
            else:
                # Send new message
                self.status_message = self.bot.send_message(
                    chat_id=self.chat_id,
                    text=text
                )
        except telegram.error.TelegramError as e:
            # Ignore "message not modified" errors
            if "message is not modified" not in str(e).lower():
                logger.error(f"Telegram error updating progress: {e}")
            
class ConversionProgressHook:
    """
    A progress hook for ffmpeg conversions that reports progress to the user.
    """
    def __init__(self, bot, chat_id, status_message=None):
        """
        Initialize the hook.
        
        Args:
            bot: The Telegram bot instance
            chat_id: The chat ID to send progress updates to
            status_message: Optional message object to edit for progress updates
        """
        self.bot = bot
        self.chat_id = chat_id
        self.status_message = status_message
        self.last_percentage = -1
        
    def update_progress(self, percentage, message=None):
        """
        Update the conversion progress.
        
        Args:
            percentage: The current percentage (0-100)
            message: Optional additional message
        """
        if percentage >= self.last_percentage + 10 or percentage == 100:
            # Create progress bar
            progress_bar = self._create_progress_bar(percentage)
            
            # Create message text
            if message:
                message_text = (
                    f"Converting: {percentage}%\n"
                    f"{progress_bar}\n"
                    f"{message}"
                )
            else:
                message_text = (
                    f"Converting: {percentage}%\n"
                    f"{progress_bar}"
                )
            
            # Update message
            self._update_progress(message_text)
            
            self.last_percentage = percentage
    
    def _create_progress_bar(self, percentage, length=20):
        """
        Create a text-based progress bar.
        
        Args:
            percentage: The current percentage (0-100)
            length: The length of the progress bar in characters
            
        Returns:
            str: A text progress bar
        """
        filled_length = int(length * percentage // 100)
        bar = '█' * filled_length + '░' * (length - filled_length)
        return f"[{bar}]"
    
    def _update_progress(self, text):
        """
        Update the progress message.
        
        Args:
            text: The text to display
        """
        try:
            if self.status_message:
                # Edit existing message
                self.bot.edit_message_text(
                    chat_id=self.chat_id,
                    message_id=self.status_message.message_id,
                    text=text
                )
            else:
                # Send new message
                self.status_message = self.bot.send_message(
                    chat_id=self.chat_id,
                    text=text
                )
        except telegram.error.TelegramError as e:
            # Ignore "message not modified" errors
            if "message is not modified" not in str(e).lower():
                logger.error(f"Telegram error updating progress: {e}")
