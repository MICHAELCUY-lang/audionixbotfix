import os
import logging
from telegram.ext import Updater
import bot
from database import app, db
# from services.notification_service import initialize_notification_service
from services.lyrics_service import initialize_genius
from services.trending_service import initialize_api_clients

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token
    token = os.environ.get("TELEGRAM_TOKEN", "8166423286:AAGkFu7rCr8etPwruo9OdbAXL9zE_PxFM0k")
    
    # Print information about the bot setup
    logger.info("Initializing bot...")
    logger.info("Make sure your bot's privacy mode is DISABLED to work in groups")
    logger.info("You can disable privacy mode by messaging @BotFather and using /setprivacy")
    
    # Setup persistence
    updater = Updater(token)
    
    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher
    
    # Setup bot handlers
    bot.setup_bot(dispatcher)
    
    # Initialize services
    initialize_genius()
    initialize_api_clients()
    # initialize_notification_service(updater.bot, app.app_context)  # Disabled subscription service
    
    # Log that the bot is starting
    logger.info("Starting bot with token %s...", token[:8] + "..." + token[-5:])
    
    # Start the Bot
    updater.start_polling()
    
    # Run the bot until you press Ctrl-C
    logger.info("Bot is up and running! Use your Telegram client to interact with it.")
    logger.info("Press Ctrl+C to stop the bot.")
    logger.info("\nIMPORTANT:")
    logger.info("1. Make sure bot's privacy mode is DISABLED via BotFather")
    logger.info("2. Add the bot as an ADMIN in large groups")
    logger.info("3. Use /status command to check bot's status in groups")
    logger.info("4. Commands in groups must start with / (slash)")
    updater.idle()

# Initialize database tables within the app context
with app.app_context():
    # Import models here to avoid circular imports
    from models import User, ArtistSubscription, SearchHistory, TrendingSong  # noqa: F401
    
    # Create tables if they don't exist
    db.create_all()

if __name__ == '__main__':
    main()