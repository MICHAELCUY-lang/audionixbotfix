import os
import logging
import random
from datetime import datetime
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

def initialize_clients():
    """Initialize API clients."""
    global spotify, youtube
    
    # Initialize Spotify client
    if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
        spotify_auth = SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET
        )
        spotify = spotipy.Spotify(auth_manager=spotify_auth)
    else:
        logger.warning("Spotify credentials not found. Recommendations will be limited.")
    
    # Initialize YouTube client
    if YOUTUBE_API_KEY:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    else:
        logger.warning("YouTube API key not found. Recommendations will be limited.")

def get_recommendations_by_genre(genre, limit=5):
    """
    Get music recommendations based on genre.
    
    Args:
        genre (str): The genre to get recommendations for.
        limit (int): Maximum number of recommendations to return.
    
    Returns:
        list: List of recommended tracks with title, artist, and platform info.
    """
    if not spotify:
        logger.warning("Spotify client not initialized. Cannot get recommendations.")
        return []
    
    try:
        # Get recommendations from Spotify based on genre seed
        results = spotify.recommendations(seed_genres=[genre], limit=limit)
        
        recommendations = []
        for track in results['tracks']:
            recommendations.append({
                'title': track['name'],
                'artist': track['artists'][0]['name'],
                'platform': 'spotify',
                'track_id': track['id'],
                'preview_url': track['preview_url'],
                'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None
            })
        
        return recommendations
    
    except Exception as e:
        logger.error(f"Error getting recommendations by genre: {e}")
        return []

def get_recommendations_by_artist(artist_name, limit=5):
    """
    Get music recommendations based on an artist.
    
    Args:
        artist_name (str): The name of the artist to get recommendations for.
        limit (int): Maximum number of recommendations to return.
    
    Returns:
        list: List of recommended tracks with title, artist, and platform info.
    """
    if not spotify:
        logger.warning("Spotify client not initialized. Cannot get recommendations.")
        return []
    
    try:
        # Search for the artist first
        artist_results = spotify.search(q=f'artist:{artist_name}', type='artist', limit=1)
        
        if not artist_results['artists']['items']:
            return []
        
        artist_id = artist_results['artists']['items'][0]['id']
        
        # Get artist's top tracks
        top_tracks = spotify.artist_top_tracks(artist_id)
        
        recommendations = []
        for track in top_tracks['tracks'][:limit]:
            recommendations.append({
                'title': track['name'],
                'artist': track['artists'][0]['name'],
                'platform': 'spotify',
                'track_id': track['id'],
                'preview_url': track['preview_url'],
                'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None
            })
        
        # Get related artists and their top tracks
        related_artists = spotify.artist_related_artists(artist_id)
        
        for related_artist in related_artists['artists'][:3]:
            related_top_tracks = spotify.artist_top_tracks(related_artist['id'])
            
            if related_top_tracks['tracks']:
                # Add one top track from each related artist
                track = related_top_tracks['tracks'][0]
                recommendations.append({
                    'title': track['name'],
                    'artist': related_artist['name'],
                    'platform': 'spotify',
                    'track_id': track['id'],
                    'preview_url': track['preview_url'],
                    'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None
                })
        
        # Limit the total recommendations
        return recommendations[:limit]
    
    except Exception as e:
        logger.error(f"Error getting recommendations by artist: {e}")
        return []

def get_recommendations_by_track(track_name, artist_name=None, limit=5):
    """
    Get music recommendations based on a track.
    
    Args:
        track_name (str): The name of the track to get recommendations for.
        artist_name (str, optional): The artist name to refine the search.
        limit (int): Maximum number of recommendations to return.
    
    Returns:
        list: List of recommended tracks with title, artist, and platform info.
    """
    if not spotify:
        logger.warning("Spotify client not initialized. Cannot get recommendations.")
        return []
    
    try:
        # Search for the track
        query = f'track:{track_name}'
        if artist_name:
            query += f' artist:{artist_name}'
        
        track_results = spotify.search(q=query, type='track', limit=1)
        
        if not track_results['tracks']['items']:
            return []
        
        track_id = track_results['tracks']['items'][0]['id']
        
        # Get track features
        track_features = spotify.audio_features(track_id)[0]
        
        # Get recommendations based on seed track and audio features
        results = spotify.recommendations(
            seed_tracks=[track_id],
            target_energy=track_features['energy'],
            target_danceability=track_features['danceability'],
            target_valence=track_features['valence'],  # musical positiveness
            limit=limit
        )
        
        recommendations = []
        for track in results['tracks']:
            # Skip the original track if it appears in recommendations
            if track['id'] == track_id:
                continue
                
            recommendations.append({
                'title': track['name'],
                'artist': track['artists'][0]['name'],
                'platform': 'spotify',
                'track_id': track['id'],
                'preview_url': track['preview_url'],
                'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None
            })
        
        return recommendations
    
    except Exception as e:
        logger.error(f"Error getting recommendations by track: {e}")
        return []

def get_youtube_recommendations(query, limit=5):
    """
    Get YouTube music video recommendations based on a search query.
    
    Args:
        query (str): The search query.
        limit (int): Maximum number of recommendations to return.
    
    Returns:
        list: List of recommended videos with title, artist, and platform info.
    """
    if not youtube:
        logger.warning("YouTube client not initialized. Cannot get recommendations.")
        return []
    
    try:
        # Search for music videos
        search_response = youtube.search().list(
            q=query + " music",
            part="snippet",
            maxResults=limit,
            type="video",
            videoCategoryId="10"  # Music category
        ).execute()
        
        recommendations = []
        for item in search_response.get('items', []):
            # Extract artist name from video title if possible
            title = item['snippet']['title']
            artist = ""
            
            # Try to separate artist from title (common format: "Artist - Title")
            if " - " in title:
                parts = title.split(" - ", 1)
                artist = parts[0].strip()
                title = parts[1].strip()
            else:
                # Use channel title as artist name
                artist = item['snippet']['channelTitle']
            
            recommendations.append({
                'title': title,
                'artist': artist,
                'platform': 'youtube',
                'track_id': item['id']['videoId'],
                'thumbnail': item['snippet']['thumbnails']['high']['url'] if 'high' in item['snippet']['thumbnails'] else item['snippet']['thumbnails']['default']['url']
            })
        
        return recommendations
    
    except Exception as e:
        logger.error(f"Error getting YouTube recommendations: {e}")
        return []

def get_popular_genres():
    """
    Get a list of popular music genres for recommendations.
    
    Returns:
        list: List of genre names.
    """
    # List of popular genres supported by Spotify's recommendation API
    genres = [
        "pop", "rock", "hip-hop", "rap", "electronic", "dance", 
        "r-n-b", "indie", "classical", "jazz", "metal", "punk",
        "soul", "blues", "reggae", "country", "folk", "latin",
        "edm", "ambient", "trap", "disco", "house"
    ]
    
    return genres

def get_mixed_recommendations(query=None, limit=5):
    """
    Get mixed recommendations from Spotify and YouTube.
    
    Args:
        query (str, optional): Search query for recommendations. If None, random genres will be used.
        limit (int): Maximum number of recommendations to return per platform.
    
    Returns:
        dict: Dictionary with lists of recommended tracks by platform.
    """
    recommendations = {
        'spotify': [],
        'youtube': []
    }
    
    try:
        # If no query provided, use random genres
        if not query:
            genres = get_popular_genres()
            random_genre = random.choice(genres)
            
            # Get Spotify recommendations by genre
            recommendations['spotify'] = get_recommendations_by_genre(random_genre, limit)
            
            # Get YouTube recommendations with the genre as query
            recommendations['youtube'] = get_youtube_recommendations(random_genre, limit)
        else:
            # Parse query to check if it's in "track - artist" format
            if " - " in query:
                track, artist = query.split(" - ", 1)
                recommendations['spotify'] = get_recommendations_by_track(track, artist, limit)
            else:
                # Try both track and artist recommendations
                track_recs = get_recommendations_by_track(query, limit=limit)
                artist_recs = get_recommendations_by_artist(query, limit=limit)
                
                # Use whichever returned more results, or combine them
                if len(track_recs) >= len(artist_recs):
                    recommendations['spotify'] = track_recs
                else:
                    recommendations['spotify'] = artist_recs
            
            # Get YouTube recommendations with the same query
            recommendations['youtube'] = get_youtube_recommendations(query, limit)
    
    except Exception as e:
        logger.error(f"Error getting mixed recommendations: {e}")
    
    return recommendations

def save_recommendation_history(telegram_id, query, platform=None):
    """
    Save a recommendation query to history.
    
    Args:
        telegram_id (str): The Telegram ID of the user.
        query (str): The recommendation query.
        platform (str, optional): The platform (spotify or youtube).
    """
    try:
        from database import app
        with app.app_context():
            from models import User, SearchHistory
            
            # Get or create user
            user = User.query.filter_by(telegram_id=telegram_id).first()
            if not user:
                user = User(telegram_id=telegram_id)
                app.db.session.add(user)
                app.db.session.commit()
            
            # Save recommendation as search history
            history = SearchHistory(
                user_id=user.id,
                query=query,
                platform=platform or "mixed",
                timestamp=datetime.utcnow()
            )
            
            app.db.session.add(history)
            app.db.session.commit()
            
    except Exception as e:
        logger.error(f"Error saving recommendation history: {e}")