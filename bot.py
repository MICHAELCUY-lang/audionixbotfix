import logging
import os
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, MessageHandler,
    Filters, CallbackQueryHandler, ConversationHandler, CallbackContext
)
from services.youtube_service import search_youtube, download_from_youtube
from services.spotify_service import search_spotify, download_from_spotify
from services.lyrics_service import search_lyrics, get_lyrics_as_text, get_lyrics_as_file
from services.trending_service import get_trending_formatted
from services.notification_service import (
    subscribe_to_artist, unsubscribe_from_artist, 
    get_user_subscriptions, toggle_notifications
)
from utils.converter import convert_mp3_to_mp4, convert_mp4_to_mp3
from utils.downloader import clean_filename
from utils.waveform import generate_preview_bundle

# States for conversation
SEARCHING, DOWNLOADING, CONVERTING, FORMAT_SELECTION, SUBSCRIBING = range(5)

# Callback data
YOUTUBE = 'youtube'
SPOTIFY = 'spotify'
CONVERT = 'convert'
MP3_TO_MP4 = 'mp3_to_mp4'
MP4_TO_MP3 = 'mp4_to_mp3'

# Social media sharing platforms
SHARE_TWITTER = 'share_twitter'
SHARE_FACEBOOK = 'share_facebook'
SHARE_WHATSAPP = 'share_whatsapp'
SHARE_TELEGRAM = 'share_telegram'
SHARE_MORE = 'share_more'

# Preview action
PREVIEW = 'preview'
DOWNLOAD = 'download'

# Group mode handling - Check if command is in a group and handle accordingly
def is_group_message(update):
    """Check if the message is from a group chat."""
    return update.effective_chat.type in ["group", "supergroup"]

def handle_group_command(update, context, command_function):
    """
    Special handler for commands in groups. Ensures the bot processes
    commands properly in group environments.
    """
    if is_group_message(update):
        # Log that we received a command in a group
        logger.info(f"Received command in group: {update.effective_chat.title}")
        
        # Process all commands in groups (more permissive approach)
        return command_function(update, context)
    else:
        # Process normally in private chats
        return command_function(update, context)
PREVIEW_DURATION = 30  # seconds for preview

logger = logging.getLogger(__name__)

def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    update.message.reply_html(
        f"Hi <a href='tg://user?id={user.id}'>{user.first_name}</a>! I'm your Music Bot.\n\n"
        "Here's what I can do for you:\n"
        "- Search and download music from YouTube and Spotify\n"
        "- Preview songs with visual waveform display\n"
        "- Show song lyrics\n"
        "- Display trending songs\n"
        "- Notify about new releases from your favorite artists\n"
        "- Share songs via social media with one click\n"
        "- Convert MP3 to MP4 and vice versa\n\n"
        "Commands:\n"
        "/search - Search for music\n"
        "/lyrics - Find lyrics for a song\n"
        "/trending - Show trending songs\n"
        "/subscribe - Get notified of new releases\n"
        "/convert - Convert between MP3 and MP4\n"
        "/help - Get help\n"
    )

def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text(
        "🎵 *Music Bot Help* 🎵\n\n"
        "*Commands:*\n"
        "/start - Start the bot\n"
        "/search - Search for music on YouTube or Spotify\n"
        "/lyrics - Find lyrics for a song\n"
        "/trending - Show trending songs\n"
        "/subscribe - Get notified of new releases\n"
        "/convert - Convert between MP3 and MP4\n"
        "/help - Show this help message\n\n"
        "*How to use:*\n"
        "1. Use /search to find music\n"
        "2. Select the platform (YouTube/Spotify)\n"
        "3. Enter your search query\n"
        "4. Select a song from the results\n"
        "5. Choose to preview the song or download it\n"
        "6. After download, you can share the song to social media\n\n"
        "*Preview Feature:*\n"
        "- Get a 30-second audio preview of the song\n"
        "- View the audio waveform visualization\n"
        "- Perfect for deciding if you want the full song\n\n"
        "*Lyrics Feature:*\n"
        "- Get lyrics for your favorite songs\n"
        "- Simply use /lyrics and follow the instructions\n\n"
        "*Trending Feature:*\n"
        "- See what songs are trending on YouTube and Spotify\n"
        "- Simply use /trending to get the latest charts\n\n"
        "*Artist Notifications:*\n"
        "- Get notified when your favorite artists release new music\n"
        "- Use /subscribe to manage your artist subscriptions\n\n"
        "*Sharing:*\n"
        "After downloading a song, you'll see sharing buttons for:\n"
        "- Twitter\n"
        "- Facebook\n"
        "- WhatsApp\n"
        "- Telegram\n\n"
        "For conversion, use /convert and follow the instructions.",
        parse_mode='Markdown'
    )

def search_command(update: Update, context: CallbackContext) -> int:
    """Handle the /search command."""
    keyboard = [
        [
            InlineKeyboardButton("YouTube", callback_data=YOUTUBE),
            InlineKeyboardButton("Spotify", callback_data=SPOTIFY),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "Where would you like to search for music?", 
        reply_markup=reply_markup
    )
    return SEARCHING

def platform_callback(update: Update, context: CallbackContext) -> int:
    """Handle platform selection callback."""
    query = update.callback_query
    query.answer()
    
    # Save the selected platform
    context.user_data['platform'] = query.data
    
    query.edit_message_text(
        f"You selected {query.data.capitalize()}. "
        "Please enter your search query:"
    )
    return DOWNLOADING

def search_query(update: Update, context: CallbackContext) -> int:
    """Handle search query and return results."""
    query_text = update.message.text
    platform = context.user_data.get('platform')
    
    # Show searching message
    message = update.message.reply_text(f"Searching for '{query_text}' on {platform.capitalize()}...")
    
    # Search based on platform
    results = []
    if platform == YOUTUBE:
        results = context.dispatcher.run_async(
            search_youtube, query_text
        ).result()
        if not results:
            update.message.reply_text("No results found on YouTube. Please try again.")
            return ConversationHandler.END
    elif platform == SPOTIFY:
        results = context.dispatcher.run_async(
            search_spotify, query_text
        ).result()
        if not results:
            update.message.reply_text("No results found on Spotify. Please try again.")
            return ConversationHandler.END
    
    # Store results for later use
    context.user_data['search_results'] = results
    
    # Create keyboard with results
    keyboard = []
    for i, result in enumerate(results[:5]):  # Limit to 5 results
        keyboard.append([
            InlineKeyboardButton(
                f"{result['title']} - {result['artist']}", 
                callback_data=f"{i}"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Select a song:", reply_markup=reply_markup)
    
    return DOWNLOADING

def generate_share_links(title, artist, platform, track_id):
    """
    Generate sharing links for different social media platforms.
    
    Args:
        title (str): The title of the track.
        artist (str): The artist name.
        platform (str): The platform (youtube or spotify).
        track_id (str): The track ID on the platform.
    
    Returns:
        dict: A dictionary of sharing links for different platforms.
    """
    # Create text to share
    share_text = f"🎵 Listening to {title} by {artist}"
    
    # Create links for direct access to the track
    direct_url = ""
    if platform == YOUTUBE:
        direct_url = f"https://www.youtube.com/watch?v={track_id}"
    elif platform == SPOTIFY:
        direct_url = f"https://open.spotify.com/track/{track_id}"
    
    # Generate sharing links
    encoded_text = share_text.replace(" ", "%20")
    encoded_url = direct_url.replace(":", "%3A").replace("/", "%2F")
    
    links = {
        'twitter': f"https://twitter.com/intent/tweet?text={encoded_text}&url={encoded_url}",
        'facebook': f"https://www.facebook.com/sharer/sharer.php?u={encoded_url}",
        'whatsapp': f"https://wa.me/?text={encoded_text}%20{encoded_url}",
        'telegram': f"https://t.me/share/url?url={encoded_url}&text={encoded_text}",
        'direct': direct_url
    }
    
    return links

def share_callback(update: Update, context: CallbackContext) -> None:
    """Handle sharing callbacks."""
    query = update.callback_query
    query.answer()
    
    # Get callback data in format "share_platform:index"
    callback_parts = query.data.split(':')
    if len(callback_parts) != 2:
        query.edit_message_text("Invalid sharing option. Please try again.")
        return
    
    share_platform = callback_parts[0]
    track_index = int(callback_parts[1])
    
    # Get the track information
    results = context.user_data.get('search_results', [])
    if 0 <= track_index < len(results):
        selected_song = results[track_index]
        platform = context.user_data.get('platform')
        
        # Generate sharing links
        share_links = generate_share_links(
            selected_song['title'], 
            selected_song['artist'], 
            platform, 
            selected_song['id']
        )
        
        # Send appropriate link based on sharing platform
        if share_platform == SHARE_TWITTER:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Share on Twitter: {share_links['twitter']}"
            )
        elif share_platform == SHARE_FACEBOOK:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Share on Facebook: {share_links['facebook']}"
            )
        elif share_platform == SHARE_WHATSAPP:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Share on WhatsApp: {share_links['whatsapp']}"
            )
        elif share_platform == SHARE_TELEGRAM:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Share on Telegram: {share_links['telegram']}"
            )
        elif share_platform == SHARE_MORE:
            # Send all sharing options
            share_message = f"Share '{selected_song['title']}' by {selected_song['artist']}:\n\n"
            share_message += f"🐦 Twitter: {share_links['twitter']}\n\n"
            share_message += f"📘 Facebook: {share_links['facebook']}\n\n"
            share_message += f"📱 WhatsApp: {share_links['whatsapp']}\n\n"
            share_message += f"📢 Telegram: {share_links['telegram']}\n\n"
            share_message += f"🔗 Direct link: {share_links['direct']}"
            
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=share_message,
                disable_web_page_preview=True
            )
    else:
        query.edit_message_text("Track information not found. Please try searching again.")

def show_share_options(update: Update, context: CallbackContext, track_index) -> None:
    """Show sharing options for a track."""
    results = context.user_data.get('search_results', [])
    if 0 <= track_index < len(results):
        selected_song = results[track_index]
        
        # Create sharing keyboard
        keyboard = [
            [
                InlineKeyboardButton("Twitter", callback_data=f"{SHARE_TWITTER}:{track_index}"),
                InlineKeyboardButton("Facebook", callback_data=f"{SHARE_FACEBOOK}:{track_index}")
            ],
            [
                InlineKeyboardButton("WhatsApp", callback_data=f"{SHARE_WHATSAPP}:{track_index}"),
                InlineKeyboardButton("Telegram", callback_data=f"{SHARE_TELEGRAM}:{track_index}")
            ],
            [
                InlineKeyboardButton("More options", callback_data=f"{SHARE_MORE}:{track_index}")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Share '{selected_song['title']}' by {selected_song['artist']}:",
            reply_markup=reply_markup
        )
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Track information not found. Please try searching again."
        )

def song_options_callback(update: Update, context: CallbackContext) -> int:
    """Handle song selection and show options (Preview/Download)."""
    query = update.callback_query
    query.answer()
    
    # Get selected song index
    selected_index = int(query.data)
    results = context.user_data.get('search_results', [])
    
    if 0 <= selected_index < len(results):
        selected_song = results[selected_index]
        
        # Store selected index for later use
        context.user_data['selected_song_index'] = selected_index
        
        # Create keyboard with action options
        keyboard = [
            [
                InlineKeyboardButton("▶️ Preview (30s with waveform)", callback_data=f"{PREVIEW}:{selected_index}"),
            ],
            [
                InlineKeyboardButton("⬇️ Download Full Song", callback_data=f"{DOWNLOAD}:{selected_index}"),
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            f"Selected: {selected_song['title']} - {selected_song['artist']}\n\n"
            f"What would you like to do?",
            reply_markup=reply_markup
        )
        
        return DOWNLOADING
    else:
        query.edit_message_text("Invalid selection. Please try searching again.")
        return ConversationHandler.END

def preview_song(update: Update, context: CallbackContext, track_index) -> None:
    """Generate and send a 30-second preview with waveform visualization."""
    query = update.callback_query
    results = context.user_data.get('search_results', [])
    
    if 0 <= track_index < len(results):
        selected_song = results[track_index]
        platform = context.user_data.get('platform')
        
        # Update status
        status_message = context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Generating preview for '{selected_song['title']}' by {selected_song['artist']}..."
        )
        
        try:
            # Download the full song first
            filepath = None
            if platform == YOUTUBE:
                filepath = context.dispatcher.run_async(
                    download_from_youtube, 
                    selected_song['id'],
                    context.bot,
                    update.effective_chat.id,
                    status_message
                ).result()
            elif platform == SPOTIFY:
                status_message.edit_text(f"Finding '{selected_song['title']}' by {selected_song['artist']} on YouTube...")
                filepath = context.dispatcher.run_async(
                    download_from_spotify, 
                    selected_song['id'],
                    context.bot,
                    update.effective_chat.id,
                    status_message
                ).result()
            
            if filepath:
                # Update status
                status_message.edit_text(f"Creating waveform visualization for '{selected_song['title']}'...")
                
                # Generate preview and waveform
                waveform_path, preview_path = context.dispatcher.run_async(
                    generate_preview_bundle,
                    filepath,
                    duration=PREVIEW_DURATION
                ).result()
                
                # Clean up the original file
                if os.path.exists(filepath):
                    os.remove(filepath)
                
                if waveform_path and preview_path:
                    # First send the waveform image
                    with open(waveform_path, 'rb') as img_file:
                        context.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=img_file,
                            caption=f"Waveform visualization for '{selected_song['title']}' by {selected_song['artist']}"
                        )
                    
                    # Then send the audio preview
                    with open(preview_path, 'rb') as audio_file:
                        context.bot.send_audio(
                            chat_id=update.effective_chat.id,
                            audio=audio_file,
                            title=f"{selected_song['title']} (Preview)",
                            performer=selected_song['artist'],
                            caption=f"▶️ 30-second preview of '{selected_song['title']}' by {selected_song['artist']}"
                        )
                    
                    # Clean up temporary files
                    if os.path.exists(waveform_path):
                        os.remove(waveform_path)
                    if os.path.exists(preview_path):
                        os.remove(preview_path)
                    
                    # Show download option
                    keyboard = [
                        [
                            InlineKeyboardButton(
                                "⬇️ Download Full Song", 
                                callback_data=f"{DOWNLOAD}:{track_index}"
                            )
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"Enjoyed the preview? Download the full song!",
                        reply_markup=reply_markup
                    )
                    
                    # Delete the status message
                    context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=status_message.message_id
                    )
                else:
                    status_message.edit_text("❌ Failed to generate preview.")
            else:
                status_message.edit_text("❌ Failed to download song for preview.")
                
        except Exception as e:
            logger.error(f"Preview error: {e}")
            try:
                status_message.edit_text(f"❌ Error creating preview: {str(e)}")
            except Exception:
                pass
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Invalid track selection. Please try searching again."
        )

def song_action_callback(update: Update, context: CallbackContext) -> int:
    """Handle Preview/Download actions for a selected song."""
    query = update.callback_query
    query.answer()
    
    # Get callback data in format "action:index"
    callback_parts = query.data.split(':')
    if len(callback_parts) != 2:
        query.edit_message_text("Invalid selection. Please try searching again.")
        return ConversationHandler.END
    
    action = callback_parts[0]
    track_index = int(callback_parts[1])
    
    # Handle different actions
    if action == PREVIEW:
        # Generate and send preview
        preview_song(update, context, track_index)
        return DOWNLOADING
    elif action == DOWNLOAD:
        # Download full song
        return download_song(update, context, track_index)
    else:
        query.edit_message_text("Invalid action. Please try searching again.")
        return ConversationHandler.END

def download_song(update: Update, context: CallbackContext, track_index) -> int:
    """Handle full song download."""
    query = update.callback_query
    results = context.user_data.get('search_results', [])
    
    if 0 <= track_index < len(results):
        selected_song = results[track_index]
        platform = context.user_data.get('platform')
        
        # Send initial status message that will be updated with progress
        status_message = context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Preparing to download: {selected_song['title']} - {selected_song['artist']}..."
        )
        
        # Update the original message if it exists
        try:
            query.edit_message_text(f"Downloading song: {selected_song['title']} - {selected_song['artist']}")
        except Exception:
            pass  # Ignore if we can't edit the message
        
        try:
            filepath = None
            if platform == YOUTUBE:
                # Use download with progress updates
                filepath = context.dispatcher.run_async(
                    download_from_youtube, 
                    selected_song['id'],
                    context.bot,  # Pass bot for progress updates
                    update.effective_chat.id,  # Pass chat_id
                    status_message  # Pass initial status message
                ).result()
            elif platform == SPOTIFY:
                # Update status message for Spotify
                status_message.edit_text(f"Finding and downloading {selected_song['title']} - {selected_song['artist']} from Spotify via YouTube...")
                
                # Download from Spotify (which uses YouTube internally)
                filepath = context.dispatcher.run_async(
                    download_from_spotify, 
                    selected_song['id'],
                    context.bot,
                    update.effective_chat.id,
                    status_message
                ).result()
            
            if filepath:
                # Update status
                status_message.edit_text("Download complete! Sending file to you...")
                
                # Send the file
                safe_filename = clean_filename(f"{selected_song['title']} - {selected_song['artist']}")
                with open(filepath, 'rb') as audio_file:
                    context.bot.send_audio(
                        chat_id=update.effective_chat.id,
                        audio=audio_file,
                        title=selected_song['title'],
                        performer=selected_song['artist'],
                        filename=f"{safe_filename}.mp3",
                        caption=f"🎵 {selected_song['title']} - {selected_song['artist']}"
                    )
                
                # Clean up the file
                if os.path.exists(filepath):
                    os.remove(filepath)
                
                # Final success message
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="✅ Download completed! Enjoy your music! 🎵"
                )
                
                # Show sharing options after successful download
                show_share_options(update, context, track_index)
                
            else:
                # Update status for failure
                status_message.edit_text("❌ Download failed.")
                
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Sorry, I couldn't download this song. Please try another one."
                )
        except Exception as e:
            logger.error(f"Download error: {e}")
            
            # Update status for error
            try:
                status_message.edit_text("❌ Download error.")
            except Exception:
                pass  # Ignore if we can't edit the message
                
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Error during download: {str(e)}"
            )
    else:
        try:
            query.edit_message_text("Invalid selection. Please try searching again.")
        except Exception:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Invalid selection. Please try searching again."
            )
    
    return ConversationHandler.END

def convert_command(update: Update, context: CallbackContext) -> int:
    """Handle the /convert command."""
    keyboard = [
        [
            InlineKeyboardButton("MP3 to MP4", callback_data=MP3_TO_MP4),
            InlineKeyboardButton("MP4 to MP3", callback_data=MP4_TO_MP3),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "What conversion would you like to perform?", 
        reply_markup=reply_markup
    )
    return FORMAT_SELECTION

def format_selection_callback(update: Update, context: CallbackContext) -> int:
    """Handle format selection callback."""
    query = update.callback_query
    query.answer()
    
    # Save the selected conversion type
    context.user_data['conversion_type'] = query.data
    
    if query.data == MP3_TO_MP4:
        query.edit_message_text(
            "Please send me the MP3 file you want to convert to MP4."
        )
    else:  # MP4_TO_MP3
        query.edit_message_text(
            "Please send me the MP4 file you want to convert to MP3."
        )
    
    return CONVERTING

def handle_file_for_conversion(update: Update, context: CallbackContext) -> int:
    """Handle the file sent for conversion."""
    conversion_type = context.user_data.get('conversion_type')
    
    # Check if there's a document or audio in the message
    file = None
    if update.message.document:
        file = update.message.document
    elif update.message.audio:
        file = update.message.audio
    elif update.message.video:
        file = update.message.video
    
    if not file:
        update.message.reply_text(
            "Please send a valid file for conversion."
        )
        return ConversationHandler.END
    
    # Download the file
    update.message.reply_text("Downloading your file...")
    file_info = context.bot.get_file(file.file_id)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.file_name)[1] if hasattr(file, 'file_name') else '.mp3') as temp_file:
        input_file = temp_file.name
    
    file_info.download(input_file)
    
    # Convert the file
    update.message.reply_text("Converting your file...")
    
    try:
        output_file = None
        if conversion_type == MP3_TO_MP4:
            output_file = context.dispatcher.run_async(
                convert_mp3_to_mp4, input_file
            ).result()
            
            # Send the converted file
            with open(output_file, 'rb') as video_file:
                context.bot.send_video(
                    chat_id=update.effective_chat.id,
                    video=video_file,
                    caption="Here's your converted MP4 file!"
                )
        
        elif conversion_type == MP4_TO_MP3:
            output_file = context.dispatcher.run_async(
                convert_mp4_to_mp3, input_file
            ).result()
            
            # Send the converted file
            with open(output_file, 'rb') as audio_file:
                context.bot.send_audio(
                    chat_id=update.effective_chat.id,
                    audio=audio_file,
                    caption="Here's your converted MP3 file!"
                )
        
        # Clean up temporary files
        if os.path.exists(input_file):
            os.remove(input_file)
        if output_file and os.path.exists(output_file):
            os.remove(output_file)
            
        update.message.reply_text("Conversion completed successfully! 🎵")
        
    except Exception as e:
        logger.error(f"Conversion error: {e}")
        update.message.reply_text(
            f"Sorry, I encountered an error during conversion: {str(e)}"
        )
        # Clean up temporary files on error
        if os.path.exists(input_file):
            os.remove(input_file)
    
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    """Cancel and end the conversation."""
    update.message.reply_text(
        "Operation cancelled. What would you like to do next?"
    )
    return ConversationHandler.END

def setup_bot(dispatcher):
    """Setup bot handlers."""
    # Import command handlers from bot_commands.py
    from bot_commands import (
        lyrics_command, lyrics_search, trending_command, 
        recommend_command, recommend_callback
    )
    
    # Basic command handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    
    # Search conversation handler
    search_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("search", search_command)],
        states={
            SEARCHING: [CallbackQueryHandler(platform_callback)],
            DOWNLOADING: [
                MessageHandler(Filters.text & ~Filters.command, search_query),
                CallbackQueryHandler(song_options_callback, pattern=r'^\d+$'),
                CallbackQueryHandler(song_action_callback, pattern=f'^({PREVIEW}|{DOWNLOAD}):\\d+$')
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    dispatcher.add_handler(search_conv_handler)
    
    # Convert conversation handler
    convert_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("convert", convert_command)],
        states={
            FORMAT_SELECTION: [CallbackQueryHandler(format_selection_callback)],
            CONVERTING: [
                MessageHandler(
                    Filters.audio | Filters.document | Filters.video,
                    handle_file_for_conversion
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    dispatcher.add_handler(convert_conv_handler)
    
    # Add recommendation handlers
    dispatcher.add_handler(CommandHandler("recommend", recommend_command))
    
    # Add recommendation callback handler
    dispatcher.add_handler(
        CallbackQueryHandler(
            recommend_callback,
            pattern=r'^genre_|^custom_rec$'
        )
    )
    
    # Add trending handler
    dispatcher.add_handler(CommandHandler("trending", trending_command))
    
    # Add lyrics handlers
    dispatcher.add_handler(CommandHandler("lyrics", lyrics_command))
    dispatcher.add_handler(MessageHandler(
        Filters.regex(r'^.+( - ).+$') & 
        Filters.update.message & 
        ~Filters.command, 
        lyrics_search
    ))
    
    # Add social media sharing handlers
    dispatcher.add_handler(
        CallbackQueryHandler(
            share_callback,
            pattern=f'^({SHARE_TWITTER}|{SHARE_FACEBOOK}|{SHARE_WHATSAPP}|{SHARE_TELEGRAM}|{SHARE_MORE}):'
        )
    )
    
    # Add fallback message handler - MUST BE LAST
    dispatcher.add_handler(
        MessageHandler(
            Filters.text & ~Filters.command,
            lambda update, context: update.message.reply_text(
                "I didn't understand that. Try using /help to see available commands."
            )
        )
    )