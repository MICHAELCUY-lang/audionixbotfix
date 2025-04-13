import logging
import os
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
from services.lyrics_service import get_lyrics_as_text
from services.trending_service import get_trending_formatted
from services.recommendation_service import (
    get_mixed_recommendations, get_recommendations_by_genre,
    get_recommendations_by_artist, get_recommendations_by_track,
    get_popular_genres, save_recommendation_history, initialize_clients
)

# Setup logging
logger = logging.getLogger(__name__)

# Initialize recommendation service
initialize_clients()

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
    parts = query.split(" - ", 1)
    if len(parts) == 2:
        title, artist = parts
        title = title.strip()
        artist = artist.strip()
    else:
        title = query
        artist = None
    
    # Send a "searching" message
    status_message = update.message.reply_text(
        f"🔎 Searching for lyrics of '{title}'{' by ' + artist if artist else ''}..."
    )
    
    # Get the lyrics
    lyrics = get_lyrics_as_text(title, artist)
    
    # Update the message with the lyrics or error
    if lyrics and "Could not find lyrics" not in lyrics:
        # If lyrics are too long, split them into multiple messages
        if len(lyrics) > 4000:
            status_message.edit_text("📝 Found lyrics! Sending in multiple parts due to length...")
            
            # Split lyrics into chunks of 4000 characters
            chunks = [lyrics[i:i+4000] for i in range(0, len(lyrics), 4000)]
            
            for i, chunk in enumerate(chunks):
                update.message.reply_text(
                    f"📝 *Lyrics* (Part {i+1}/{len(chunks)}): \n\n{chunk}",
                    parse_mode='Markdown'
                )
        else:
            status_message.edit_text(
                f"📝 *Lyrics*: \n\n{lyrics}",
                parse_mode='Markdown'
            )
    else:
        status_message.edit_text(
            f"❌ Sorry, I couldn't find lyrics for '{title}'{' by ' + artist if artist else ''}. "
            "Please check the spelling or try another song."
        )

def trending_command(update: Update, context: CallbackContext) -> None:
    """Handle the /trending command and show trending songs."""
    # Send a "loading" message
    status_message = update.message.reply_text(
        "🔍 Fetching the latest trending songs... Please wait!"
    )
    
    # Get the trending songs formatted text
    trending_text = get_trending_formatted()
    
    # Update the message with the trending songs
    status_message.edit_text(
        trending_text,
        parse_mode='Markdown',
        disable_web_page_preview=True
    )

def recommend_command(update: Update, context: CallbackContext) -> None:
    """Handle the /recommend command and provide music recommendations."""
    # Check if there are arguments (query or genre)
    query = " ".join(context.args) if context.args else None
    
    if not query:
        # No query provided, show genre options
        genres = get_popular_genres()
        
        # Create keyboard with genre buttons
        keyboard = []
        row = []
        for i, genre in enumerate(genres):
            # Format genre name for display (capitalize, replace hyphens)
            display_name = genre.replace('-', ' ').title()
            
            # Add button to current row
            row.append(InlineKeyboardButton(display_name, callback_data=f"genre_{genre}"))
            
            # Start a new row every 3 buttons
            if (i + 1) % 3 == 0 or i == len(genres) - 1:
                keyboard.append(row)
                row = []
        
        # Add a button for custom recommendation
        keyboard.append([InlineKeyboardButton("Custom Recommendation", callback_data="custom_rec")])
        
        # Send message with genre options
        update.message.reply_text(
            "🎵 What kind of music would you like me to recommend? Choose a genre or request a custom recommendation:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        # Query provided, get recommendations directly
        send_recommendations(update, context, query)

def recommend_callback(update: Update, context: CallbackContext) -> None:
    """Handle recommendation callback queries."""
    query = update.callback_query
    query.answer()
    
    data = query.data
    
    if data == "custom_rec":
        # User wants custom recommendation
        query.edit_message_text(
            "🎵 Please send me an artist name, song title, or both (in format 'Song - Artist') "
            "for personalized recommendations!"
        )
    elif data.startswith("genre_"):
        # User selected a genre
        genre = data.split("_", 1)[1]
        
        # Format genre name for display
        display_name = genre.replace('-', ' ').title()
        
        # Get recommendations for this genre
        query.edit_message_text(f"🔍 Finding the best {display_name} recommendations for you...")
        
        # Get and send recommendations
        send_recommendations(update, context, genre, is_callback=True)
    else:
        # Unknown callback data
        query.edit_message_text("Sorry, I couldn't process that. Please try again.")

def send_recommendations(update: Update, context: CallbackContext, query, is_callback=False) -> None:
    """Send music recommendations based on the query."""
    # Get mixed recommendations
    recommendations = get_mixed_recommendations(query)
    
    # Save to history if it's not a callback (direct command)
    if not is_callback:
        user_id = update.message.from_user.id
        save_recommendation_history(str(user_id), query)
    
    # Create the message
    message = f"🎵 *Music Recommendations for '{query}'* 🎵\n\n"
    
    # Add Spotify recommendations
    if recommendations['spotify']:
        message += "*🎧 From Spotify:*\n"
        for i, track in enumerate(recommendations['spotify']):
            message += f"{i+1}. {track['title']} - {track['artist']}\n"
        message += "\n"
    
    # Add YouTube recommendations
    if recommendations['youtube']:
        message += "*📺 From YouTube:*\n"
        for i, video in enumerate(recommendations['youtube']):
            message += f"{i+1}. {video['title']} - {video['artist']}\n"
        message += "\n"
    
    # Add a note if no recommendations were found
    if not recommendations['spotify'] and not recommendations['youtube']:
        message += "Sorry, I couldn't find any recommendations for this query. Please try something else."
    
    # Send the message
    if is_callback:
        update.callback_query.edit_message_text(
            message,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
    else:
        update.message.reply_text(
            message,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )