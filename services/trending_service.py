import os
import logging
import requests
import json
from datetime import datetime
from bs4 import BeautifulSoup
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from googleapiclient.discovery import build

# Setup logging
logger = logging.getLogger(__name__)

# API credentials
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID", "f8b64136c2b84dfe8a87792f371a0fef")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "a22e0a461f9b4cc580352f7843310d88")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "AIzaSyB59tvqGw1VbuhDEoGltDFRMfoJWoL20CQ")

# Initialize API clients
spotify = None
youtube = None

def initialize_api_clients():
    """Initialize API clients for Spotify and YouTube."""
    global spotify, youtube
    
    # Initialize Spotify client
    if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
        spotify_auth = SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET
        )
        spotify = spotipy.Spotify(auth_manager=spotify_auth)
    else:
        logger.warning("Spotify credentials not found. Trending functionality will be limited.")
    
    # Initialize YouTube client
    if YOUTUBE_API_KEY:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    else:
        logger.warning("YouTube API key not found. Trending functionality will be limited.")

def get_spotify_trending(limit=10):
    """
    Get trending songs from Spotify.
    
    Args:
        limit (int): Maximum number of songs to return.
    
    Returns:
        list: List of trending songs with title, artist, and track_id.
    """
    if not spotify:
        initialize_api_clients()
        if not spotify:
            logger.error("Failed to initialize Spotify client.")
            return []
    
    try:
        # Get the Global Top 50 playlist
        playlist_id = '37i9dQZEVXbMDoHDwVN2tF'
        
        # Fetch the playlist tracks
        results = spotify.playlist_tracks(playlist_id, limit=limit)
        
        trending_songs = []
        
        for i, item in enumerate(results['items']):
            track = item['track']
            
            # Extract track information
            song_info = {
                'rank': i + 1,
                'title': track['name'],
                'artist': track['artists'][0]['name'],
                'track_id': track['id'],
                'platform': 'spotify',
                'album': track['album']['name'],
                'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None,
                'popularity': track['popularity']
            }
            
            trending_songs.append(song_info)
        
        return trending_songs
    
    except Exception as e:
        logger.error(f"Error getting Spotify trends: {e}")
        return []

def get_youtube_trending(limit=10):
    """
    Get trending music videos from YouTube.
    
    Args:
        limit (int): Maximum number of videos to return.
    
    Returns:
        list: List of trending songs with title, artist, and track_id.
    """
    if not youtube:
        initialize_api_clients()
        if not youtube:
            logger.error("Failed to initialize YouTube client.")
            return []
    
    try:
        # Get trending music videos
        request = youtube.videos().list(
            part="snippet,statistics",
            chart="mostPopular",
            regionCode="US",
            videoCategoryId="10",  # Music category
            maxResults=limit
        )
        response = request.execute()
        
        trending_songs = []
        
        for i, item in enumerate(response['items']):
            # Extract video information
            title = item['snippet']['title']
            
            # Try to extract artist from title (this is a simple approximation)
            title_parts = title.split(' - ')
            artist = title_parts[0] if len(title_parts) > 1 else "Unknown Artist"
            song_title = title_parts[1] if len(title_parts) > 1 else title
            
            song_info = {
                'rank': i + 1,
                'title': song_title,
                'artist': artist,
                'track_id': item['id'],
                'platform': 'youtube',
                'views': item['statistics'].get('viewCount', 0),
                'thumbnail': item['snippet']['thumbnails']['high']['url'],
                'channel': item['snippet']['channelTitle']
            }
            
            trending_songs.append(song_info)
        
        return trending_songs
    
    except Exception as e:
        logger.error(f"Error getting YouTube trends: {e}")
        return []

def get_all_trending(limit=5):
    """
    Get trending songs from all platforms.
    
    Args:
        limit (int): Maximum number of songs to return per platform.
    
    Returns:
        dict: Dictionary with lists of trending songs by platform.
    """
    spotify_trending = get_spotify_trending(limit)
    youtube_trending = get_youtube_trending(limit)
    
    return {
        'spotify': spotify_trending,
        'youtube': youtube_trending
    }

def get_trending_formatted():
    """
    Get formatted text of trending songs for display in Telegram.
    
    Returns:
        str: Formatted trending songs text.
    """
    trends = get_all_trending(5)
    
    if not trends['spotify'] and not trends['youtube']:
        return "⚠️ Failed to fetch trending songs. Please try again later."
    
    message = "🔥 *TRENDING SONGS* 🔥\n\n"
    
    # Add Spotify trends
    if trends['spotify']:
        message += "📊 *Spotify Global Top 5*\n"
        for song in trends['spotify']:
            message += f"{song['rank']}. *{song['title']}* - {song['artist']}\n"
        message += "\n"
    
    # Add YouTube trends
    if trends['youtube']:
        message += "📺 *YouTube Music Trending*\n"
        for song in trends['youtube']:
            message += f"{song['rank']}. *{song['title']}* - {song['artist']}\n"
    
    message += "\nUse /search to download any of these songs!"
    
    return message