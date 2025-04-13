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
from utils.converter import convert_mp3_to_mp4, convert_mp4_to_mp3
from utils.downloader import clean_filename

# States for conversation
SEARCHING, DOWNLOADING, CONVERTING, FORMAT_SELECTION = range(4)

# Callback data
YOUTUBE = 'youtube'
SPOTIFY = 'spotify'
CONVERT = 'convert'
MP3_TO_MP4 = 'mp3_to_mp4'
MP4_TO_MP3 = 'mp4_to_mp3'

logger = logging.getLogger(__name__)

def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    update.message.reply_html(
        f"Hi <a href='tg://user?id={user.id}'>{user.first_name}</a>! I'm your Music Bot.\n\n"
        "Here's what I can do for you:\n"
        "- Search and download music from YouTube and Spotify\n"
        "- Convert MP3 to MP4 and vice versa\n\n"
        "Commands:\n"
        "/search - Search for music\n"
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
        "/convert - Convert between MP3 and MP4\n"
        "/help - Show this help message\n\n"
        "*How to use:*\n"
        "1. Use /search to find music\n"
        "2. Select the platform (YouTube/Spotify)\n"
        "3. Enter your search query\n"
        "4. Select a song from the results\n\n"
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
        keyboard.append([InlineKeyboardButton(f"{result['title']} - {result['artist']}", callback_data=str(i))])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Select a song to download:", reply_markup=reply_markup)
    
    return DOWNLOADING

def download_callback(update: Update, context: CallbackContext) -> int:
    """Handle download selection callback."""
    query = update.callback_query
    query.answer()
    
    # Get selected song index
    selected_index = int(query.data)
    results = context.user_data.get('search_results', [])
    
    if 0 <= selected_index < len(results):
        selected_song = results[selected_index]
        platform = context.user_data.get('platform')
        
        query.edit_message_text(f"Downloading: {selected_song['title']} - {selected_song['artist']}...")
        
        try:
            filepath = None
            if platform == YOUTUBE:
                filepath = context.dispatcher.run_async(
                    download_from_youtube, selected_song['id']
                ).result()
            elif platform == SPOTIFY:
                filepath = context.dispatcher.run_async(
                    download_from_spotify, selected_song['id']
                ).result()
            
            if filepath:
                # Send the file
                safe_filename = clean_filename(f"{selected_song['title']} - {selected_song['artist']}")
                with open(filepath, 'rb') as audio_file:
                    context.bot.send_audio(
                        chat_id=update.effective_chat.id,
                        audio=audio_file,
                        title=selected_song['title'],
                        performer=selected_song['artist'],
                        filename=f"{safe_filename}.mp3"
                    )
                
                # Clean up the file
                if os.path.exists(filepath):
                    os.remove(filepath)
                
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Download completed! Enjoy your music! 🎵"
                )
            else:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Sorry, I couldn't download this song. Please try another one."
                )
        except Exception as e:
            logger.error(f"Download error: {e}")
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Error during download: {str(e)}"
            )
    else:
        query.edit_message_text("Invalid selection. Please try searching again.")
    
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
                CallbackQueryHandler(download_callback)
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
    
    # Add fallback message handler
    dispatcher.add_handler(
        MessageHandler(
            Filters.text & ~Filters.command,
            lambda update, context: update.message.reply_text(
                "I didn't understand that. Try using /help to see available commands."
            )
        )
    )