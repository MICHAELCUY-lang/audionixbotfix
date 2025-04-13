import os
import logging
import tempfile
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp
from utils.downloader import clean_filename, DownloadProgressHook
from services.youtube_service import search_youtube, download_from_youtube

# Configure logging
logger = logging.getLogger(__name__)

# Set Spotify credentials if not already set
if not os.environ.get("SPOTIFY_CLIENT_ID"):
    os.environ["SPOTIFY_CLIENT_ID"] = "f8b64136c2b84dfe8a87792f371a0fef"
if not os.environ.get("SPOTIFY_CLIENT_SECRET"):
    os.environ["SPOTIFY_CLIENT_SECRET"] = "a22e0a461f9b4cc580352f7843310d88"

# Get Spotify credentials from environment variables
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")

# Initialize Spotify client
try:
    spotify = spotipy.Spotify(
        client_credentials_manager=SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET
        )
    )
except Exception as e:
    logger.error(f"Error initializing Spotify client: {e}")
    spotify = None

def search_spotify(query, max_results=5):
    """
    Search for tracks on Spotify.
    
    Args:
        query (str): The search query.
        max_results (int, optional): Maximum number of results to return. Defaults to 5.
    
    Returns:
        list: List of dictionaries containing track information.
    """
    if not spotify:
        logger.error("Spotify client is not initialized")
        return []
    
    try:
        # Search Spotify for tracks
        results = spotify.search(q=query, limit=max_results, type='track')
        
        # Process search results
        tracks = []
        for item in results['tracks']['items']:
            artist_names = ', '.join([artist['name'] for artist in item['artists']])
            tracks.append({
                'id': item['id'],
                'title': item['name'],
                'artist': artist_names,
                'album': item['album']['name'],
                'thumbnail': item['album']['images'][0]['url'] if item['album']['images'] else None,
                'platform': 'spotify'
            })
        
        return tracks
    
    except Exception as e:
        logger.error(f"Error searching Spotify: {e}")
        return []

def download_from_spotify(track_id, bot=None, chat_id=None, status_message=None, progress_callback=None):
    """
    Download a track from Spotify (via YouTube).
    
    Args:
        track_id (str): The Spotify track ID.
        bot: The Telegram bot instance for progress updates
        chat_id: The chat ID to send progress updates to
        status_message: Message object to update with progress
        progress_callback (callable, optional): Legacy callback function for progress updates.
    
    Returns:
        str: Path to the downloaded file, or None if download failed.
    """
    if not spotify:
        logger.error("Spotify client is not initialized")
        return None
    
    try:
        # Update status message if we have bot and chat_id
        if bot and chat_id and status_message:
            status_message.edit_text("Getting track information from Spotify...")
        # Otherwise use legacy progress callback
        elif progress_callback:
            progress_callback(0, "Getting track information from Spotify...")
        
        # Get track information from Spotify
        track = spotify.track(track_id)
        
        if not track:
            logger.error(f"Track with ID {track_id} not found on Spotify")
            if bot and chat_id and status_message:
                status_message.edit_text("❌ Track not found on Spotify")
            return None
        
        # Update progress for YouTube search
        if bot and chat_id and status_message:
            status_message.edit_text(f"Looking for '{track['name']}' on YouTube...")
        elif progress_callback:
            progress_callback(10, "Looking for track on YouTube...")
        
        # Create search query for YouTube
        artist_names = ', '.join([artist['name'] for artist in track['artists']])
        search_query = f"{track['name']} {artist_names}"
        
        # Search for the track on YouTube
        youtube_results = search_youtube(search_query, max_results=1)
        
        if not youtube_results:
            logger.error(f"No YouTube results found for Spotify track: {search_query}")
            if bot and chat_id and status_message:
                status_message.edit_text(f"❌ Could not find '{track['name']}' by {artist_names} on YouTube")
            return None
        
        # Update progress for YouTube download
        if bot and chat_id and status_message:
            status_message.edit_text(f"Found '{track['name']}' by {artist_names} on YouTube. Starting download...")
        elif progress_callback:
            progress_callback(20, "Starting download from YouTube...")
        
        # If we have bot integration, use it
        if bot and chat_id:
            return download_from_youtube(
                youtube_results[0]['id'],
                bot,
                chat_id,
                status_message
            )
        # Otherwise use legacy progress callback
        elif progress_callback:
            # Create a nested progress callback to scale percentages
            def youtube_progress(percent):
                # Scale the progress from 20% to 100%
                scaled_percent = 20 + (percent * 0.8)  # 20% to 100%
                progress_callback(round(scaled_percent), "Downloading and processing audio...")
                
            return download_from_youtube(
                youtube_results[0]['id'], 
                progress_callback=youtube_progress
            )
        # No progress updates
        else:
            return download_from_youtube(youtube_results[0]['id'])
    
    except Exception as e:
        logger.error(f"Error downloading from Spotify: {e}")
        if bot and chat_id and status_message:
            try:
                status_message.edit_text(f"❌ Error downloading from Spotify: {str(e)}")
            except Exception:
                pass  # Ignore if we can't edit the message
        return None
