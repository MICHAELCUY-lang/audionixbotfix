import os
import logging
import tempfile
import lyricsgenius

# Setup logging
logger = logging.getLogger(__name__)

# Initialize the Genius API client
GENIUS_ACCESS_TOKEN = os.environ.get("GENIUS_ACCESS_TOKEN")
genius = None

def initialize_genius():
    """Initialize the Genius API client with the access token."""
    global genius
    if GENIUS_ACCESS_TOKEN:
        genius = lyricsgenius.Genius(GENIUS_ACCESS_TOKEN)
        # Turn off status messages
        genius.verbose = False
        # Remove section headers like [Chorus], [Verse], etc. from lyrics
        genius.remove_section_headers = True
        return True
    else:
        logger.warning("GENIUS_ACCESS_TOKEN not found. Lyrics functionality will be limited.")
        return False

def search_lyrics(song_title, artist_name=None):
    """
    Search for lyrics of a song.
    
    Args:
        song_title (str): The title of the song.
        artist_name (str, optional): The name of the artist. Helps with accuracy.
    
    Returns:
        dict: Dictionary containing lyrics information, or None if not found.
    """
    if not genius and not initialize_genius():
        logger.warning("Genius API not initialized. Cannot fetch lyrics.")
        return None
    
    try:
        # Search for the song
        if artist_name:
            search_term = f"{song_title} {artist_name}"
            song = genius.search_song(song_title, artist_name)
        else:
            search_term = song_title
            song = genius.search_song(song_title)
        
        if not song:
            logger.info(f"No lyrics found for: {search_term}")
            return None
        
        # Create result dictionary
        result = {
            'title': song.title,
            'artist': song.artist,
            'lyrics': song.lyrics,
            'url': song.url,
            'album': song.album,
            'featured_artists': song.featured_artists,
            'song_art_image_url': song.song_art_image_url
        }
        
        return result
    
    except Exception as e:
        logger.error(f"Error searching for lyrics: {e}")
        return None

def get_lyrics_as_text(song_title, artist_name=None):
    """
    Get just the lyrics text of a song.
    
    Args:
        song_title (str): The title of the song.
        artist_name (str, optional): The name of the artist. Helps with accuracy.
    
    Returns:
        str: The lyrics text, or an error message if not found.
    """
    lyrics_data = search_lyrics(song_title, artist_name)
    
    if lyrics_data and 'lyrics' in lyrics_data:
        return lyrics_data['lyrics']
    else:
        return f"No lyrics found for '{song_title}'"

def get_lyrics_as_file(song_title, artist_name=None):
    """
    Get lyrics as a text file.
    
    Args:
        song_title (str): The title of the song.
        artist_name (str, optional): The name of the artist. Helps with accuracy.
    
    Returns:
        str: Path to the text file containing lyrics, or None if not found.
    """
    lyrics_data = search_lyrics(song_title, artist_name)
    
    if not lyrics_data or 'lyrics' not in lyrics_data:
        return None
    
    try:
        # Create a temp file for the lyrics
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as temp_file:
            file_path = temp_file.name
            
            # Write lyrics with some formatting
            temp_file.write(f"{lyrics_data['title']} - {lyrics_data['artist']}\n\n")
            temp_file.write(f"Album: {lyrics_data['album'] or 'Unknown'}\n")
            if lyrics_data['featured_artists']:
                temp_file.write(f"Featuring: {', '.join(lyrics_data['featured_artists'])}\n")
            temp_file.write(f"Source: {lyrics_data['url']}\n\n")
            temp_file.write(lyrics_data['lyrics'])
            
        return file_path
        
    except Exception as e:
        logger.error(f"Error creating lyrics file: {e}")
        return None