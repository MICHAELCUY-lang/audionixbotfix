import logging
import os
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
from services.lyrics_service import get_lyrics_as_text
from services.trending_service import get_trending_formatted
from services.notification_service import (
    subscribe_to_artist, unsubscribe_from_artist, 
    get_user_subscriptions, toggle_notifications
)

# Setup logging
logger = logging.getLogger(__name__)

# States for subscription conversation
SUBSCRIBING = 4  # Matches the state in bot.py

def lyrics_command(update: Update, context: CallbackContext) -> None:
    """Handle the /lyrics command."""
    update.message.reply_text(
        "Please send me the song title and artist name in the format: 'Song Title - Artist Name'"
    )
    return

def lyrics_search(update: Update, context: CallbackContext) -> None:
    """Search for lyrics based on the provided song info."""
    query = update.message.text
    
    # Split query into title and artist (if provided in the format "Title - Artist")
    parts = query.split('-')
    title = parts[0].strip()
    artist = parts[1].strip() if len(parts) > 1 else None
    
    # Send a status message
    status_message = update.message.reply_text(f"Searching for lyrics of '{title}'{f' by {artist}' if artist else ''}...")
    
    try:
        # Get lyrics using Genius API
        lyrics = get_lyrics_as_text(title, artist)
        
        if lyrics and len(lyrics) > 0:
            # Break up the lyrics into 4000-character chunks if needed (Telegram message limit)
            if len(lyrics) > 4000:
                chunks = [lyrics[i:i+4000] for i in range(0, len(lyrics), 4000)]
                
                # Send first chunk with header
                first_chunk = chunks[0]
                header = f"🎵 *Lyrics for '{title}'*"
                header += f" *by {artist}*" if artist else ""
                header += "\n\n"
                
                context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=status_message.message_id
                )
                
                update.message.reply_text(
                    header + first_chunk,
                    parse_mode='Markdown'
                )
                
                # Send remaining chunks
                for chunk in chunks[1:]:
                    update.message.reply_text(chunk)
            else:
                # Send all lyrics in one message
                header = f"🎵 *Lyrics for '{title}'*"
                header += f" *by {artist}*" if artist else ""
                header += "\n\n"
                
                context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=status_message.message_id
                )
                
                update.message.reply_text(
                    header + lyrics,
                    parse_mode='Markdown'
                )
        else:
            status_message.edit_text(
                f"❌ Sorry, couldn't find lyrics for '{title}'{f' by {artist}' if artist else ''}.\n"
                "Please try again with a different song or check your spelling."
            )
    except Exception as e:
        logger.error(f"Lyrics error: {e}")
        status_message.edit_text(
            f"❌ Error searching for lyrics: {str(e)}\n"
            "Please try again or try a different song."
        )

def trending_command(update: Update, context: CallbackContext) -> None:
    """Handle the /trending command and show trending songs."""
    # Send a status message
    status_message = update.message.reply_text("Fetching trending songs from Spotify and YouTube...")
    
    try:
        # Get trending songs formatted text
        trending_text = get_trending_formatted()
        
        if trending_text:
            context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=status_message.message_id
            )
            
            update.message.reply_text(
                trending_text,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        else:
            status_message.edit_text(
                "❌ Sorry, couldn't retrieve trending songs at the moment.\n"
                "Please try again later."
            )
    except Exception as e:
        logger.error(f"Trending error: {e}")
        status_message.edit_text(
            f"❌ Error fetching trending songs: {str(e)}\n"
            "Please try again later."
        )

def subscribe_command(update: Update, context: CallbackContext) -> int:
    """Handle the /subscribe command."""
    keyboard = [
        [
            InlineKeyboardButton("Subscribe to Artist", callback_data="subscribe_artist"),
            InlineKeyboardButton("Manage Subscriptions", callback_data="manage_subscriptions")
        ],
        [
            InlineKeyboardButton("Toggle Notifications", callback_data="toggle_notifications")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "Artist Subscription Manager\n\n"
        "Get notified when your favorite artists release new music!\n\n"
        "What would you like to do?", 
        reply_markup=reply_markup
    )
    return SUBSCRIBING

def subscribe_menu_callback(update: Update, context: CallbackContext) -> int:
    """Handle subscription menu callbacks."""
    query = update.callback_query
    query.answer()
    
    action = query.data
    
    if action == "subscribe_artist":
        query.edit_message_text(
            "Please send me the artist name you want to subscribe to."
        )
        # Set state for the next handler
        context.user_data['subscribe_action'] = 'artist_name'
        return SUBSCRIBING
    
    elif action == "manage_subscriptions":
        # Get user's subscriptions
        telegram_id = str(update.effective_user.id)
        subscriptions = get_user_subscriptions(telegram_id)
        
        if not subscriptions:
            query.edit_message_text(
                "You don't have any artist subscriptions yet.\n\n"
                "Use /subscribe and select 'Subscribe to Artist' to add some!"
            )
            return ConversationHandler.END
        
        # Create keyboard with subscriptions
        keyboard = []
        for sub in subscriptions:
            keyboard.append([
                InlineKeyboardButton(
                    f"❌ {sub['artist_name']} ({sub['platform'].capitalize()})",
                    callback_data=f"unsub_{sub['id']}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("Done", callback_data="sub_done")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            "Your Artist Subscriptions\n\n"
            "Click on an artist to unsubscribe:",
            reply_markup=reply_markup
        )
        return SUBSCRIBING
    
    elif action == "toggle_notifications":
        telegram_id = str(update.effective_user.id)
        # Toggle notifications
        enabled = toggle_notifications(telegram_id, None)  # Toggle current state
        
        state = "ENABLED" if enabled else "DISABLED"
        query.edit_message_text(
            f"Notifications are now {state}.\n\n"
            f"You will {'now receive' if enabled else 'no longer receive'} "
            "notifications about new releases from your subscribed artists."
        )
        return ConversationHandler.END
    
    return SUBSCRIBING

def handle_artist_subscribe(update: Update, context: CallbackContext) -> int:
    """Handle artist name input for subscription."""
    artist_name = update.message.text.strip()
    
    if not artist_name:
        update.message.reply_text(
            "Please provide a valid artist name."
        )
        return SUBSCRIBING
    
    # Ask user to select platform
    keyboard = [
        [
            InlineKeyboardButton("Spotify", callback_data=f"sub_platform_spotify_{artist_name}"),
            InlineKeyboardButton("YouTube", callback_data=f"sub_platform_youtube_{artist_name}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        f"Which platform would you like to subscribe to '{artist_name}' on?",
        reply_markup=reply_markup
    )
    return SUBSCRIBING

def handle_platform_selection(update: Update, context: CallbackContext) -> int:
    """Handle platform selection for artist subscription."""
    query = update.callback_query
    query.answer()
    
    # Parse data in format "sub_platform_PLATFORM_ARTIST"
    parts = query.data.split('_', 3)
    platform = parts[2]
    artist_name = parts[3]
    
    telegram_id = str(update.effective_user.id)
    
    # Update status
    query.edit_message_text(f"Searching for '{artist_name}' on {platform.capitalize()}...")
    
    # Search for artist and subscribe
    try:
        # This would typically search the platform API for the artist ID
        # For now, we'll just use a simple artist ID
        artist_id = f"artist_{platform}_{artist_name.lower().replace(' ', '')}"
        
        # Subscribe to the artist
        success = subscribe_to_artist(telegram_id, artist_name, artist_id, platform)
        
        if success:
            query.edit_message_text(
                f"✅ You are now subscribed to {artist_name} on {platform.capitalize()}!\n\n"
                "You'll receive notifications when they release new music."
            )
        else:
            query.edit_message_text(
                f"❌ Failed to subscribe to {artist_name}.\n"
                "You might already be subscribed to this artist, or there was an error."
            )
    except Exception as e:
        logger.error(f"Subscription error: {e}")
        query.edit_message_text(
            f"❌ Error subscribing to {artist_name}: {str(e)}\n"
            "Please try again later."
        )
    
    return ConversationHandler.END

def handle_unsubscribe(update: Update, context: CallbackContext) -> int:
    """Handle unsubscribe callbacks."""
    query = update.callback_query
    query.answer()
    
    # Parse data in format "unsub_ID"
    parts = query.data.split('_')
    subscription_id = int(parts[1])
    
    telegram_id = str(update.effective_user.id)
    
    # Unsubscribe from the artist
    success = unsubscribe_from_artist(telegram_id, subscription_id)
    
    if success:
        # Get updated subscriptions
        subscriptions = get_user_subscriptions(telegram_id)
        
        if not subscriptions:
            query.edit_message_text(
                "You've unsubscribed from all artists.\n\n"
                "Use /subscribe and select 'Subscribe to Artist' to add some!"
            )
            return ConversationHandler.END
        
        # Create keyboard with remaining subscriptions
        keyboard = []
        for sub in subscriptions:
            keyboard.append([
                InlineKeyboardButton(
                    f"❌ {sub['artist_name']} ({sub['platform'].capitalize()})",
                    callback_data=f"unsub_{sub['id']}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("Done", callback_data="sub_done")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            "Artist unsubscribed successfully.\n\n"
            "Your Artist Subscriptions:\n"
            "Click on an artist to unsubscribe:",
            reply_markup=reply_markup
        )
        return SUBSCRIBING
    else:
        query.edit_message_text(
            "❌ Failed to unsubscribe.\n"
            "Please try again later."
        )
        return ConversationHandler.END