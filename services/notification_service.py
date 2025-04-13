import os
import logging
from datetime import datetime, timedelta
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from googleapiclient.discovery import build
from apscheduler.schedulers.background import BackgroundScheduler

# Setup logging
logger = logging.getLogger(__name__)

# API credentials
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID", "f8b64136c2b84dfe8a87792f371a0fef")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "a22e0a461f9b4cc580352f7843310d88")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "AIzaSyB59tvqGw1VbuhDEoGltDFRMfoJWoL20CQ")

# Initialize API clients
spotify = None
youtube = None
scheduler = None
bot_instance = None
db_context = None

def initialize_notification_service(bot, app_context):
    """
    Initialize the notification service.
    
    Args:
        bot: The Telegram bot instance.
        app_context: The Flask app context for database operations.
    """
    global bot_instance, db_context, scheduler, spotify, youtube
    
    bot_instance = bot
    db_context = app_context
    
    # Initialize Spotify client
    if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
        spotify_auth = SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET
        )
        spotify = spotipy.Spotify(auth_manager=spotify_auth)
    else:
        logger.warning("Spotify credentials not found. New release notifications will be limited.")
    
    # Initialize YouTube client
    if YOUTUBE_API_KEY:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    else:
        logger.warning("YouTube API key not found. New release notifications will be limited.")
    
    # Initialize scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_for_new_releases, 'interval', hours=12)
    scheduler.start()
    
    logger.info("Notification service initialized.")

def check_for_new_releases():
    """Check for new releases from artists users are subscribed to."""
    if not db_context:
        logger.error("Database context not initialized. Cannot check for new releases.")
        return
    
    with db_context():
        from models import User, ArtistSubscription
        
        # Get all active subscriptions
        subscriptions = ArtistSubscription.query.all()
        
        for subscription in subscriptions:
            user = User.query.get(subscription.user_id)
            
            if not user or not user.notifications_enabled:
                continue
            
            # Check for new releases based on platform
            if subscription.platform == 'spotify':
                check_spotify_new_releases(subscription, user)
            elif subscription.platform == 'youtube':
                check_youtube_new_releases(subscription, user)

def check_spotify_new_releases(subscription, user):
    """
    Check for new releases from a Spotify artist.
    
    Args:
        subscription: The ArtistSubscription object.
        user: The User object.
    """
    if not spotify:
        logger.warning("Spotify client not initialized. Cannot check for new releases.")
        return
    
    try:
        # Get artist's albums
        results = spotify.artist_albums(subscription.artist_id, album_type='album,single', limit=5)
        albums = results['items']
        
        # Check if there's any new album since last check
        for album in albums:
            # Check if this is a new release
            release_date = datetime.strptime(album['release_date'], '%Y-%m-%d')
            
            if (release_date > subscription.last_checked and 
                album['id'] != subscription.last_release_id):
                
                # We found a new release, send notification
                send_new_release_notification(
                    user.telegram_id,
                    subscription.artist_name,
                    album['name'],
                    'album',
                    release_date,
                    f"https://open.spotify.com/album/{album['id']}",
                    'spotify'
                )
                
                # Update subscription with latest release
                with db_context():
                    from models import ArtistSubscription
                    sub = ArtistSubscription.query.get(subscription.id)
                    sub.last_release_id = album['id']
                    sub.last_checked = datetime.utcnow()
                    db_context.session.commit()
                
                # Only notify about the most recent release
                break
        
    except Exception as e:
        logger.error(f"Error checking Spotify new releases: {e}")

def check_youtube_new_releases(subscription, user):
    """
    Check for new uploads from a YouTube channel.
    
    Args:
        subscription: The ArtistSubscription object.
        user: The User object.
    """
    if not youtube:
        logger.warning("YouTube client not initialized. Cannot check for new releases.")
        return
    
    try:
        # Get channel's latest videos
        request = youtube.search().list(
            part="snippet",
            channelId=subscription.artist_id,
            maxResults=5,
            order="date",
            type="video"
        )
        response = request.execute()
        
        if 'items' in response and response['items']:
            latest_video = response['items'][0]
            video_id = latest_video['id']['videoId']
            
            # Check if this is a new video
            publish_time = datetime.strptime(
                latest_video['snippet']['publishedAt'], 
                '%Y-%m-%dT%H:%M:%SZ'
            )
            
            if (publish_time > subscription.last_checked and 
                video_id != subscription.last_release_id):
                
                # We found a new release, send notification
                send_new_release_notification(
                    user.telegram_id,
                    subscription.artist_name,
                    latest_video['snippet']['title'],
                    'video',
                    publish_time,
                    f"https://www.youtube.com/watch?v={video_id}",
                    'youtube'
                )
                
                # Update subscription with latest release
                with db_context():
                    from models import ArtistSubscription
                    sub = ArtistSubscription.query.get(subscription.id)
                    sub.last_release_id = video_id
                    sub.last_checked = datetime.utcnow()
                    db_context.session.commit()
        
    except Exception as e:
        logger.error(f"Error checking YouTube new releases: {e}")

def send_new_release_notification(telegram_id, artist_name, release_name, release_type, release_date, url, platform):
    """
    Send a notification about a new release to a user.
    
    Args:
        telegram_id: The Telegram ID of the user.
        artist_name: The name of the artist.
        release_name: The name of the release (album, single, video, etc.)
        release_type: The type of release (album, single, video, etc.)
        release_date: The release date.
        url: The URL to the release.
        platform: The platform (spotify or youtube).
    """
    if not bot_instance:
        logger.error("Bot instance not initialized. Cannot send notification.")
        return
    
    # Create the notification message
    if platform == 'spotify':
        emoji = "🎵"
        platform_name = "Spotify"
    else:  # youtube
        emoji = "📺"
        platform_name = "YouTube"
    
    # Format release date
    release_date_str = release_date.strftime("%Y-%m-%d")
    
    message = (
        f"{emoji} *NEW RELEASE ALERT!* {emoji}\n\n"
        f"Artist: *{artist_name}*\n"
        f"New {release_type}: *{release_name}*\n"
        f"Released on: {release_date_str}\n"
        f"Platform: {platform_name}\n\n"
        f"[Listen Now]({url})"
    )
    
    try:
        bot_instance.send_message(
            chat_id=telegram_id,
            text=message,
            parse_mode='Markdown',
            disable_web_page_preview=False
        )
        logger.info(f"Sent new release notification to {telegram_id} for {artist_name}")
    except Exception as e:
        logger.error(f"Error sending notification: {e}")

def subscribe_to_artist(telegram_id, artist_name, artist_id, platform):
    """
    Subscribe a user to an artist's new releases.
    
    Args:
        telegram_id: The Telegram ID of the user.
        artist_name: The name of the artist.
        artist_id: The ID of the artist on the platform.
        platform: The platform (spotify or youtube).
    
    Returns:
        bool: True if subscription was successful, False otherwise.
    """
    if not db_context:
        logger.error("Database context not initialized. Cannot subscribe to artist.")
        return False
    
    try:
        with db_context():
            from models import User, ArtistSubscription
            
            # Get or create user
            user = User.query.filter_by(telegram_id=telegram_id).first()
            
            if not user:
                user = User(telegram_id=telegram_id)
                db_context.session.add(user)
                db_context.session.commit()
            
            # Check if subscription already exists
            existing_sub = ArtistSubscription.query.filter_by(
                user_id=user.id,
                artist_id=artist_id,
                platform=platform
            ).first()
            
            if existing_sub:
                return False  # Already subscribed
            
            # Create new subscription
            subscription = ArtistSubscription(
                user_id=user.id,
                artist_name=artist_name,
                artist_id=artist_id,
                platform=platform,
                last_checked=datetime.utcnow()
            )
            
            db_context.session.add(subscription)
            db_context.session.commit()
            
            return True
        
    except Exception as e:
        logger.error(f"Error subscribing to artist: {e}")
        return False

def unsubscribe_from_artist(telegram_id, subscription_id):
    """
    Unsubscribe a user from an artist's new releases.
    
    Args:
        telegram_id: The Telegram ID of the user.
        subscription_id: The ID of the subscription to remove.
    
    Returns:
        bool: True if unsubscription was successful, False otherwise.
    """
    if not db_context:
        logger.error("Database context not initialized. Cannot unsubscribe from artist.")
        return False
    
    try:
        with db_context():
            from models import User, ArtistSubscription
            
            # Get user
            user = User.query.filter_by(telegram_id=telegram_id).first()
            
            if not user:
                return False  # User not found
            
            # Get subscription
            subscription = ArtistSubscription.query.filter_by(
                id=subscription_id,
                user_id=user.id
            ).first()
            
            if not subscription:
                return False  # Subscription not found
            
            # Delete subscription
            db_context.session.delete(subscription)
            db_context.session.commit()
            
            return True
        
    except Exception as e:
        logger.error(f"Error unsubscribing from artist: {e}")
        return False

def get_user_subscriptions(telegram_id):
    """
    Get all subscriptions for a user.
    
    Args:
        telegram_id: The Telegram ID of the user.
    
    Returns:
        list: List of subscription dictionaries.
    """
    if not db_context:
        logger.error("Database context not initialized. Cannot get user subscriptions.")
        return []
    
    try:
        with db_context():
            from models import User, ArtistSubscription
            
            # Get user
            user = User.query.filter_by(telegram_id=telegram_id).first()
            
            if not user:
                return []  # User not found
            
            # Get subscriptions
            subscriptions = ArtistSubscription.query.filter_by(user_id=user.id).all()
            
            result = []
            for sub in subscriptions:
                result.append({
                    'id': sub.id,
                    'artist_name': sub.artist_name,
                    'platform': sub.platform,
                    'created_at': sub.created_at
                })
            
            return result
        
    except Exception as e:
        logger.error(f"Error getting user subscriptions: {e}")
        return []

def toggle_notifications(telegram_id, enabled):
    """
    Enable or disable notifications for a user.
    
    Args:
        telegram_id: The Telegram ID of the user.
        enabled: Boolean indicating whether notifications should be enabled.
    
    Returns:
        bool: True if toggle was successful, False otherwise.
    """
    if not db_context:
        logger.error("Database context not initialized. Cannot toggle notifications.")
        return False
    
    try:
        with db_context():
            from models import User
            
            # Get or create user
            user = User.query.filter_by(telegram_id=telegram_id).first()
            
            if not user:
                user = User(telegram_id=telegram_id, notifications_enabled=enabled)
                db_context.session.add(user)
            else:
                user.notifications_enabled = enabled
            
            db_context.session.commit()
            
            return True
        
    except Exception as e:
        logger.error(f"Error toggling notifications: {e}")
        return False