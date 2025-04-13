#!/usr/bin/env python3
"""
Script to run the bot continuously, restarting it if it crashes.
"""

import os
import sys
import time
import logging
import subprocess
import signal
import datetime

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot_runner.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BotRunner")

# Constants
MAX_RESTARTS_PER_HOUR = 5
COOLDOWN_PERIOD = 3600  # 1 hour in seconds
BOT_SCRIPT = "main.py"

# Global variables for tracking restarts
restart_count = 0
last_restart_time = datetime.datetime.now()

def run_bot():
    """Run the bot process and return the process object."""
    logger.info("Starting bot process...")
    
    # Use Python from the environment
    cmd = [sys.executable, BOT_SCRIPT]
    
    # Start the process with logging
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1  # Line buffered
    )
    
    logger.info(f"Bot process started with PID: {process.pid}")
    return process

def log_output(process):
    """Log the output from the bot process."""
    for line in iter(process.stdout.readline, ""):
        if line:
            print(line.rstrip())
            sys.stdout.flush()  # Ensure output is displayed immediately
    
    # If we get here, the process has ended
    return_code = process.wait()
    logger.info(f"Bot process ended with return code: {return_code}")
    return return_code

def handle_sigterm(signum, frame):
    """Handle SIGTERM signal gracefully."""
    logger.info("Received SIGTERM signal. Shutting down...")
    sys.exit(0)

def main():
    """Main function to run the bot continuously."""
    global restart_count, last_restart_time
    
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGTERM, handle_sigterm)
    
    logger.info("Bot runner started")
    
    while True:
        try:
            # Check if we're restarting too frequently
            current_time = datetime.datetime.now()
            time_diff = (current_time - last_restart_time).total_seconds()
            
            if time_diff < COOLDOWN_PERIOD and restart_count >= MAX_RESTARTS_PER_HOUR:
                cooldown_remaining = COOLDOWN_PERIOD - time_diff
                logger.warning(
                    f"Too many restarts ({restart_count}) within the past hour. "
                    f"Cooling down for {cooldown_remaining:.1f} seconds..."
                )
                time.sleep(min(300, cooldown_remaining))  # Sleep at most 5 minutes
                continue
            
            # Reset restart count if more than an hour has passed
            if time_diff >= COOLDOWN_PERIOD:
                restart_count = 0
                last_restart_time = current_time
            
            # Start the bot
            process = run_bot()
            
            # Monitor the bot and get exit code
            return_code = log_output(process)
            
            # Handle different exit codes
            if return_code == 0:
                logger.info("Bot exited normally. Restarting in 5 seconds...")
                time.sleep(5)
            else:
                # Bot crashed, increment restart count
                restart_count += 1
                last_restart_time = datetime.datetime.now()
                
                logger.error(f"Bot crashed with exit code {return_code}. Restarting in 10 seconds...")
                time.sleep(10)
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt. Shutting down...")
            break
        except Exception as e:
            logger.error(f"Error in runner: {e}")
            time.sleep(30)  # Sleep for 30 seconds before trying again

if __name__ == "__main__":
    main()