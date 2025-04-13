import os
import logging
import tempfile
from googleapiclient.discovery import build
import yt_dlp
from utils.downloader import clean_filename, DownloadProgressHook

# Configure logging
logger = logging.getLogger(__name__)

# Set YouTube API Key if not already set
if not os.environ.get("YOUTUBE_API_KEY"):
    os.environ["YOUTUBE_API_KEY"] = "AIzaSyB59tvqGw1VbuhDEoGltDFRMfoJWoL20CQ"

# Get API key from environment variables
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")

# Create YouTube API client
try:
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
except Exception as e:
    logger.error(f"Error initializing YouTube API client: {e}")
    youtube = None

def search_youtube(query, max_results=5):
    """
    Search for videos on YouTube.
    
    Args:
        query (str): The search query.
        max_results (int, optional): Maximum number of results to return. Defaults to 5.
    
    Returns:
        list: List of dictionaries containing video information.
    """
    if not youtube:
        logger.error("YouTube API client is not initialized")
        return []
        
    try:
        # Call the search.list method to retrieve search results
        search_response = youtube.search().list(
            q=query,
            part='id,snippet',
            maxResults=max_results,
            type='video'
        ).execute()
        
        # Process search results
        videos = []
        for search_result in search_response.get('items', []):
            if search_result['id']['kind'] == 'youtube#video':
                videos.append({
                    'id': search_result['id']['videoId'],
                    'title': search_result['snippet']['title'],
                    'artist': search_result['snippet']['channelTitle'],
                    'thumbnail': search_result['snippet']['thumbnails']['default']['url'],
                    'platform': 'youtube'
                })
        
        return videos
    
    except Exception as e:
        logger.error(f"Error searching YouTube: {e}")
        return []

def download_from_youtube(video_id, bot=None, chat_id=None, status_message=None, progress_callback=None):
    """
    Download a video from YouTube as MP3.
    
    Args:
        video_id (str): The YouTube video ID.
        bot: The Telegram bot instance, optional for progress updates
        chat_id: The chat ID to send progress updates to, optional
        status_message: Optional message object to edit for progress updates
        progress_callback (callable, optional): A callback function to report progress.
            It will be called with the current progress percentage.
    
    Returns:
        str: Path to the downloaded file, or None if download failed.
    """
    if not video_id:
        logger.error("No video ID provided for download")
        return None
        
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    try:
        # Create temporary file with appropriate extension
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            output_path = temp_file.name
        
        # Set up progress hooks
        progress_hooks = []
        
        # Use DownloadProgressHook if bot and chat_id are provided
        if bot and chat_id:
            progress_hooks.append(DownloadProgressHook(bot, chat_id, status_message))
        # Otherwise, use the simple progress callback if provided
        elif progress_callback:
            def simple_progress_hook(d):
                if d['status'] == 'downloading':
                    if 'total_bytes' in d and d['total_bytes'] > 0:
                        percent = d['downloaded_bytes'] / d['total_bytes'] * 100
                    elif 'total_bytes_estimate' in d and d['total_bytes_estimate'] > 0:
                        percent = d['downloaded_bytes'] / d['total_bytes_estimate'] * 100
                    else:
                        percent = 0
                    
                    # Report progress
                    progress_callback(round(percent))
                
                elif d['status'] == 'finished':
                    progress_callback(100)
            
            progress_hooks.append(simple_progress_hook)
        
        # Set up yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': output_path[:-4],  # Remove the .mp3 extension as yt-dlp adds it
            'quiet': not progress_hooks,  # Only be quiet if no progress hooks
            'no_warnings': True,
        }
        
        # Add progress hooks if available
        if progress_hooks:
            ydl_opts['progress_hooks'] = progress_hooks
        
        # Download the audio
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        # The actual output file has .mp3 extension added by yt-dlp
        actual_output_path = f"{output_path[:-4]}.mp3"
        
        # Verify the file exists
        if os.path.exists(actual_output_path):
            return actual_output_path
        else:
            logger.error(f"Expected output file not found: {actual_output_path}")
            return None
    
    except Exception as e:
        logger.error(f"Error downloading from YouTube: {e}")
        # Clean up any temporary files
        if 'output_path' in locals():
            if os.path.exists(output_path):
                os.remove(output_path)
        if 'actual_output_path' in locals():
            if os.path.exists(actual_output_path):
                os.remove(actual_output_path)
        return None
