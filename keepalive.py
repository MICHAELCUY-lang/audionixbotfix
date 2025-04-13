import logging
import threading
import time
import requests
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global variables
KEEP_ALIVE_INTERVAL = 5 * 60  # 5 minutes
last_restart_time = datetime.now()
restart_count = 0
MAX_RESTARTS_PER_HOUR = 5

def keep_alive():
    """
    Function to keep the bot alive by periodically sending requests to itself.
    This prevents the server from going to sleep.
    """
    while True:
        try:
            # Get the REPL's URL
            repl_url = os.environ.get("REPLIT_URL")
            if repl_url:
                # Ping the app to keep it alive
                response = requests.get(repl_url)
                logger.info(f"Keep-alive ping sent. Status: {response.status_code}")
            else:
                logger.warning("REPLIT_URL environment variable not set")
            
            # Sleep for the specified interval
            time.sleep(KEEP_ALIVE_INTERVAL)
        except Exception as e:
            logger.error(f"Error in keep_alive function: {e}")
            time.sleep(60)  # Sleep for a minute before retrying

def should_restart():
    """
    Determine whether the bot should restart based on restart frequency.
    Prevents excessive restarts that might get the bot rate-limited.
    
    Returns:
        bool: True if the bot should restart, False otherwise.
    """
    global last_restart_time, restart_count
    
    current_time = datetime.now()
    time_diff = (current_time - last_restart_time).total_seconds() / 3600  # in hours
    
    if time_diff < 1 and restart_count >= MAX_RESTARTS_PER_HOUR:
        logger.warning(f"Too many restarts in the past hour ({restart_count}). Waiting...")
        return False
    
    if time_diff >= 1:
        # Reset counter if an hour has passed
        restart_count = 0
        last_restart_time = current_time
    
    restart_count += 1
    return True

def start_keep_alive_thread():
    """
    Start a separate thread for the keep-alive functionality.
    """
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    logger.info("Keep-alive thread started")
    return keep_alive_thread