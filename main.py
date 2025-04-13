import logging
import os
from telegram.ext import Updater
from bot import setup_bot

# Set environment variables directly if they're not set
# These would normally be read from .env file
if not os.environ.get("TELEGRAM_TOKEN"):
    os.environ["TELEGRAM_TOKEN"] = "8166423286:AAGkFu7rCr8etPwruo9OdbAXL9zE_PxFM0k"
if not os.environ.get("YOUTUBE_API_KEY"):
    os.environ["YOUTUBE_API_KEY"] = "AIzaSyB59tvqGw1VbuhDEoGltDFRMfoJWoL20CQ"
if not os.environ.get("SPOTIFY_CLIENT_ID"):
    os.environ["SPOTIFY_CLIENT_ID"] = "f8b64136c2b84dfe8a87792f371a0fef"
if not os.environ.get("SPOTIFY_CLIENT_SECRET"):
    os.environ["SPOTIFY_CLIENT_SECRET"] = "a22e0a461f9b4cc580352f7843310d88"

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

def main():
    """Start the bot."""
    # Get the token from environment variable
    token = os.environ.get("TELEGRAM_TOKEN")
    
    if not token:
        logger.error("No Telegram token found! Please set the TELEGRAM_TOKEN environment variable.")
        return
    
    # Create the Updater and pass it your bot's token
    updater = Updater(token)
    
    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher
    
    # Setup bot handlers
    setup_bot(dispatcher)
    
    # Start the Bot
    logger.info("Starting bot with token %s...", token[:5] + "..." + token[-5:])
    updater.start_polling()
    
    logger.info("Bot is up and running! Use your Telegram client to interact with it.")
    logger.info("Press Ctrl+C to stop the bot.")
    
    # Run the bot until you press Ctrl-C
    updater.idle()

if __name__ == '__main__':
    main()
