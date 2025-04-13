import os
import logging
import time
import threading
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

def keep_alive():
    """Keep the application alive by pinging it periodically."""
    while True:
        try:
            # Get the app URL from environment variables or use a default
            app_url = os.environ.get("REPLIT_URL", "https://localhost:5000")
            
            # Send a request to the app every 5 minutes
            if app_url and app_url != "https://localhost:5000":
                import requests
                response = requests.get(app_url)
                logger.info(f"Keep-alive ping sent. Status: {response.status_code}")
            
            # Sleep for 5 minutes
            time.sleep(300)  # 5 minutes = 300 seconds
        except Exception as e:
            logger.error(f"Error in keep-alive thread: {e}")
            time.sleep(60)  # Wait a minute and try again

def error_handler(update, context):
    """Log Errors caused by Updates."""
    try:
        logger.error(f"Update {update} caused error {context.error}")
        
        # Try to notify admin if possible
        admin_id = os.environ.get("ADMIN_TELEGRAM_ID")
        if admin_id:
            try:
                context.bot.send_message(
                    chat_id=admin_id, 
                    text=f"⚠️ Bot error: {context.error}"
                )
            except Exception as e:
                logger.error(f"Could not notify admin: {e}")
    except Exception as e:
        logger.error(f"Error in error handler: {e}")

def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token
    token = os.environ.get("TELEGRAM_TOKEN", "8166423286:AAGkFu7rCr8etPwruo9OdbAXL9zE_PxFM0k")
    
    # Start the keep-alive thread
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    logger.info("Keep-alive thread started")
    
    # Print information about the bot setup
    logger.info("Initializing bot...")
    logger.info("Make sure your bot's privacy mode is DISABLED to work in groups")
    logger.info("You can disable privacy mode by messaging @BotFather and using /setprivacy")
    
    max_retries = 10
    retry_delay = 30  # seconds
    
    for attempt in range(1, max_retries + 1):
        try:
            # Setup bot
            updater = Updater(token)
            
            # Get the dispatcher to register handlers
            dispatcher = updater.dispatcher
            
            # Add error handler
            dispatcher.add_error_handler(error_handler)
            
            # Setup bot handlers
            bot.setup_bot(dispatcher)
            
            # Initialize services
            initialize_genius()
            initialize_api_clients()
            # initialize_notification_service(updater.bot, app.app_context)  # Disabled subscription service
            
            # Log that the bot is starting
            logger.info("Starting bot with token %s...", token[:8] + "..." + token[-5:])
            
            # Start the Bot
            updater.start_polling(drop_pending_updates=True)
            
            # Run the bot until you press Ctrl-C
            logger.info("Bot is up and running! Use your Telegram client to interact with it.")
            logger.info("Press Ctrl+C to stop the bot.")
            logger.info("\nIMPORTANT:")
            logger.info("1. Make sure bot's privacy mode is DISABLED via BotFather")
            logger.info("2. Add the bot as an ADMIN in large groups")
            logger.info("3. Use /status command to check bot's status in groups")
            logger.info("4. Commands in groups must start with / (slash)")
            
            # Set up automatic reconnection if connection is lost
            updater.idle()
            
            # If we get here, the bot was stopped gracefully
            logger.info("Bot was stopped gracefully")
            break
            
        except Exception as e:
            logger.error(f"Error starting bot (attempt {attempt}/{max_retries}): {e}")
            
            if attempt < max_retries:
                # Wait before retrying
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                # Increase retry delay for next attempt (exponential backoff)
                retry_delay = min(retry_delay * 1.5, 300)  # Maximum 5 minutes
            else:
                logger.error("Maximum retry attempts reached. Giving up.")
                # Try to notify admin
                admin_id = os.environ.get("ADMIN_TELEGRAM_ID")
                if admin_id:
                    try:
                        import requests
                        requests.post(
                            f"https://api.telegram.org/bot{token}/sendMessage",
                            json={
                                "chat_id": admin_id,
                                "text": f"⚠️ Bot failed to start after {attempt} attempts. Please check logs."
                            }
                        )
                    except Exception as notify_err:
                        logger.error(f"Could not notify admin: {notify_err}")
                break

# Initialize database tables within the app context
with app.app_context():
    # Import models here to avoid circular imports
    from models import User, ArtistSubscription, SearchHistory, TrendingSong, UserTheme  # noqa: F401
    
    # Create tables if they don't exist
    db.create_all()

if __name__ == '__main__':
    main()