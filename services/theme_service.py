import logging
import os
import json
from sqlalchemy.exc import SQLAlchemyError
from database import db
from models import UserTheme

# Configure logging
logger = logging.getLogger(__name__)

# Define preset themes
PRESET_THEMES = {
    "default": {
        "name": "Default",
        "primary_color": "#0088CC",  # Telegram Blue
        "secondary_color": "#FFFFFF",
        "accent_color": "#27AE60",
        "font_style": "default",
        "emoji_set": "default",
        "description": "The default Telegram-style theme"
    },
    "dark": {
        "name": "Dark Mode",
        "primary_color": "#1E1E1E",
        "secondary_color": "#333333",
        "accent_color": "#7289DA",
        "font_style": "monospace",
        "emoji_set": "minimal",
        "description": "A sleek dark theme for night-time browsing"
    },
    "music": {
        "name": "Music Lover",
        "primary_color": "#E91E63",  # Pink
        "secondary_color": "#F8BBD0",
        "accent_color": "#9C27B0",
        "font_style": "rounded",
        "emoji_set": "music",
        "description": "Vibrant theme for music enthusiasts"
    },
    "forest": {
        "name": "Forest",
        "primary_color": "#2E7D32",  # Green
        "secondary_color": "#C8E6C9",
        "accent_color": "#FFC107",
        "font_style": "serif",
        "emoji_set": "nature",
        "description": "A calming nature-inspired theme"
    },
    "ocean": {
        "name": "Ocean",
        "primary_color": "#0277BD",  # Blue
        "secondary_color": "#B3E5FC",
        "accent_color": "#00BCD4",
        "font_style": "default",
        "emoji_set": "sea",
        "description": "Cool ocean vibes"
    }
}

# Emoji sets
EMOJI_SETS = {
    "default": {
        "music": "🎵",
        "search": "🔍",
        "download": "⬇️",
        "convert": "🔄",
        "lyrics": "📝",
        "trending": "📈",
        "recommend": "👍",
        "settings": "⚙️",
        "theme": "🎨",
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
        "info": "ℹ️"
    },
    "minimal": {
        "music": "♪",
        "search": "→",
        "download": "↓",
        "convert": "⇄",
        "lyrics": "✎",
        "trending": "↑",
        "recommend": "+",
        "settings": "◎",
        "theme": "◇",
        "success": "✓",
        "error": "×",
        "warning": "!",
        "info": "i"
    },
    "music": {
        "music": "🎧",
        "search": "🔍",
        "download": "📥",
        "convert": "🔁",
        "lyrics": "🎤",
        "trending": "🔥",
        "recommend": "🎯",
        "settings": "🎛️",
        "theme": "🎨",
        "success": "🎶",
        "error": "📛",
        "warning": "⚠️",
        "info": "💡"
    },
    "nature": {
        "music": "🍃",
        "search": "🔍",
        "download": "🌱",
        "convert": "🌿",
        "lyrics": "🌷",
        "trending": "☀️",
        "recommend": "🌟",
        "settings": "🌳",
        "theme": "🌈",
        "success": "🌺",
        "error": "🍂",
        "warning": "🌩️",
        "info": "💧"
    },
    "sea": {
        "music": "🐠",
        "search": "🔍",
        "download": "🌊",
        "convert": "🐙",
        "lyrics": "🐚",
        "trending": "🐬",
        "recommend": "⭐",
        "settings": "🧜‍♀️",
        "theme": "🐳",
        "success": "🐋",
        "error": "🦀",
        "warning": "🦑",
        "info": "🐟"
    }
}

def get_user_theme(telegram_id):
    """
    Get the theme settings for a user.
    
    Args:
        telegram_id (str): The user's Telegram ID.
    
    Returns:
        dict: The user's theme settings.
    """
    try:
        # Check if user has a theme
        user_theme = UserTheme.query.filter_by(telegram_id=telegram_id).first()
        
        if not user_theme:
            # Create a default theme for the user
            user_theme = UserTheme(
                telegram_id=telegram_id,
                theme_name="default"
            )
            db.session.add(user_theme)
            db.session.commit()
            logger.info(f"Created default theme for user {telegram_id}")
        
        # Build theme dictionary
        theme = {
            "id": user_theme.id,
            "theme_name": user_theme.theme_name,
            "primary_color": user_theme.primary_color,
            "secondary_color": user_theme.secondary_color,
            "accent_color": user_theme.accent_color,
            "font_style": user_theme.font_style,
            "emoji_set": user_theme.emoji_set
        }
        
        return theme
    
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting user theme: {e}")
        # Return default theme if there's an error
        return PRESET_THEMES["default"]

def set_user_theme(telegram_id, theme_name):
    """
    Set a preset theme for a user.
    
    Args:
        telegram_id (str): The user's Telegram ID.
        theme_name (str): The name of the preset theme.
    
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        if theme_name not in PRESET_THEMES:
            logger.error(f"Theme {theme_name} not found")
            return False
        
        preset = PRESET_THEMES[theme_name]
        
        # Get or create user theme
        user_theme = UserTheme.query.filter_by(telegram_id=telegram_id).first()
        
        if not user_theme:
            user_theme = UserTheme(telegram_id=telegram_id)
            db.session.add(user_theme)
        
        # Update with preset values
        user_theme.theme_name = theme_name
        user_theme.primary_color = preset["primary_color"]
        user_theme.secondary_color = preset["secondary_color"]
        user_theme.accent_color = preset["accent_color"]
        user_theme.font_style = preset["font_style"]
        user_theme.emoji_set = preset["emoji_set"]
        
        db.session.commit()
        logger.info(f"Set theme {theme_name} for user {telegram_id}")
        return True
    
    except SQLAlchemyError as e:
        logger.error(f"Database error when setting user theme: {e}")
        db.session.rollback()
        return False

def update_user_theme_settings(telegram_id, settings):
    """
    Update specific theme settings for a user.
    
    Args:
        telegram_id (str): The user's Telegram ID.
        settings (dict): Dictionary of settings to update.
    
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        # Get or create user theme
        user_theme = UserTheme.query.filter_by(telegram_id=telegram_id).first()
        
        if not user_theme:
            user_theme = UserTheme(telegram_id=telegram_id)
            db.session.add(user_theme)
            user_theme.theme_name = "custom"
        elif "theme_name" in settings:
            # If changing specific settings, mark as custom theme
            user_theme.theme_name = "custom"
        
        # Update settings
        if "primary_color" in settings:
            user_theme.primary_color = settings["primary_color"]
        if "secondary_color" in settings:
            user_theme.secondary_color = settings["secondary_color"]
        if "accent_color" in settings:
            user_theme.accent_color = settings["accent_color"]
        if "font_style" in settings:
            user_theme.font_style = settings["font_style"]
        if "emoji_set" in settings:
            user_theme.emoji_set = settings["emoji_set"]
        
        db.session.commit()
        logger.info(f"Updated theme settings for user {telegram_id}")
        return True
    
    except SQLAlchemyError as e:
        logger.error(f"Database error when updating user theme: {e}")
        db.session.rollback()
        return False

def get_preset_themes():
    """
    Get a list of all preset themes.
    
    Returns:
        dict: Dictionary of preset themes.
    """
    return PRESET_THEMES

def get_emoji(emoji_name, telegram_id=None):
    """
    Get an emoji based on the user's selected emoji set.
    
    Args:
        emoji_name (str): The name of the emoji.
        telegram_id (str, optional): The user's Telegram ID. If not provided, uses default emoji set.
    
    Returns:
        str: The emoji character.
    """
    try:
        emoji_set = "default"
        
        if telegram_id:
            user_theme = UserTheme.query.filter_by(telegram_id=telegram_id).first()
            if user_theme:
                emoji_set = user_theme.emoji_set
        
        if emoji_set in EMOJI_SETS and emoji_name in EMOJI_SETS[emoji_set]:
            return EMOJI_SETS[emoji_set][emoji_name]
        
        # Fall back to default emoji set
        if emoji_name in EMOJI_SETS["default"]:
            return EMOJI_SETS["default"][emoji_name]
        
        # Final fallback
        return "•"
    
    except Exception as e:
        logger.error(f"Error getting emoji: {e}")
        return "•"

def format_message_with_theme(message, telegram_id=None):
    """
    Format a message with themed emojis based on the user's theme.
    
    Args:
        message (str): The message to format.
        telegram_id (str, optional): The user's Telegram ID.
    
    Returns:
        str: The formatted message.
    """
    try:
        # Replace emoji placeholders with actual emojis
        formatted_message = message
        
        # Look for {emoji:name} patterns and replace them
        import re
        emoji_pattern = r'\{emoji:([\w]+)\}'
        
        def replace_emoji(match):
            emoji_name = match.group(1)
            return get_emoji(emoji_name, telegram_id)
        
        formatted_message = re.sub(emoji_pattern, replace_emoji, formatted_message)
        
        return formatted_message
    
    except Exception as e:
        logger.error(f"Error formatting message with theme: {e}")
        return message  # Return original message if there's an error