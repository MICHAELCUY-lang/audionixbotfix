import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import CallbackContext

from services.theme_service import (
    get_user_theme, 
    set_user_theme, 
    update_user_theme_settings, 
    get_preset_themes,
    get_emoji,
    format_message_with_theme
)

# Configure logging
logger = logging.getLogger(__name__)

# Callback data patterns
THEME_SELECT = 'theme_select'
THEME_CUSTOM = 'theme_custom'
THEME_COLOR = 'theme_color'
THEME_EMOJI = 'theme_emoji'
THEME_FONT = 'theme_font'

def theme_command(update: Update, context: CallbackContext) -> None:
    """Handle the /theme command to show and set themes."""
    user = update.effective_user
    telegram_id = str(user.id)
    
    # Get current user theme
    current_theme = get_user_theme(telegram_id)
    preset_themes = get_preset_themes()
    
    # Create keyboard with theme options
    keyboard = []
    
    # Add preset theme buttons
    for theme_id, theme in preset_themes.items():
        # Mark the current theme with an asterisk
        theme_label = f"🎨 {theme['name']}"
        if current_theme['theme_name'] == theme_id:
            theme_label += " ✓"
            
        keyboard.append([
            InlineKeyboardButton(
                theme_label, 
                callback_data=f"{THEME_SELECT}:{theme_id}"
            )
        ])
    
    # Add custom theme options
    keyboard.append([
        InlineKeyboardButton(
            "🎭 Customize Colors", 
            callback_data=f"{THEME_CUSTOM}:colors"
        )
    ])
    
    keyboard.append([
        InlineKeyboardButton(
            "😀 Change Emoji Set", 
            callback_data=f"{THEME_EMOJI}:select"
        )
    ])
    
    keyboard.append([
        InlineKeyboardButton(
            "🔤 Change Font Style", 
            callback_data=f"{THEME_FONT}:select"
        )
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Create a themed message
    current_theme_info = preset_themes.get(current_theme['theme_name'], {"name": "Custom", "description": "Your customized theme"})
    
    message = format_message_with_theme(
        "{emoji:theme} *Customize Your Bot Interface*\n\n"
        f"Current Theme: *{current_theme_info['name']}*\n"
        f"{current_theme_info['description']}\n\n"
        "{emoji:info} Choose a theme or customize your own:",
        telegram_id
    )
    
    update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

def theme_callback(update: Update, context: CallbackContext) -> None:
    """Handle theme selection callbacks."""
    query = update.callback_query
    query.answer()
    
    user = update.effective_user
    telegram_id = str(user.id)
    
    # Parse callback data
    callback_parts = query.data.split(':')
    if len(callback_parts) != 2:
        query.edit_message_text("Invalid theme option. Please try again.")
        return
    
    action = callback_parts[0]
    param = callback_parts[1]
    
    if action == THEME_SELECT:
        # Set preset theme
        if set_user_theme(telegram_id, param):
            preset_themes = get_preset_themes()
            theme_info = preset_themes.get(param, {"name": "Unknown"})
            
            message = format_message_with_theme(
                "{emoji:success} Theme changed to *" + theme_info['name'] + "*\n\n"
                "Your bot interface will now use this theme for all interactions.",
                telegram_id
            )
            
            query.edit_message_text(
                message,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            query.edit_message_text(
                format_message_with_theme(
                    "{emoji:error} Sorry, there was a problem setting your theme.",
                    telegram_id
                )
            )
    
    elif action == THEME_CUSTOM:
        # Show color customization options
        show_color_options(update, context, telegram_id)
    
    elif action == THEME_COLOR:
        # Handle color selection
        handle_color_selection(update, context, telegram_id, param)
    
    elif action == THEME_EMOJI:
        # Show emoji set options
        show_emoji_options(update, context, telegram_id)
    
    elif action == THEME_FONT:
        # Show font style options
        show_font_options(update, context, telegram_id)
    
    else:
        query.edit_message_text(
            format_message_with_theme(
                "{emoji:error} Unknown theme option. Please try again.",
                telegram_id
            )
        )

def show_color_options(update: Update, context: CallbackContext, telegram_id: str) -> None:
    """Show color customization options."""
    query = update.callback_query
    
    # Get current theme
    current_theme = get_user_theme(telegram_id)
    
    # Create keyboard with color options
    keyboard = [
        [
            InlineKeyboardButton(
                "🔵 Primary Color", 
                callback_data=f"{THEME_COLOR}:primary"
            )
        ],
        [
            InlineKeyboardButton(
                "⚪ Background Color", 
                callback_data=f"{THEME_COLOR}:secondary"
            )
        ],
        [
            InlineKeyboardButton(
                "🟢 Accent Color", 
                callback_data=f"{THEME_COLOR}:accent"
            )
        ],
        [
            InlineKeyboardButton(
                "← Back to Themes", 
                callback_data=f"{THEME_SELECT}:back"
            )
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = format_message_with_theme(
        "{emoji:theme} *Color Customization*\n\n"
        "Choose which color to customize:\n\n"
        f"• Primary: `{current_theme['primary_color']}`\n"
        f"• Background: `{current_theme['secondary_color']}`\n"
        f"• Accent: `{current_theme['accent_color']}`\n\n"
        "{emoji:info} Select an option:",
        telegram_id
    )
    
    query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

def handle_color_selection(update: Update, context: CallbackContext, telegram_id: str, color_type: str) -> None:
    """Handle color selection."""
    query = update.callback_query
    
    if color_type == "back":
        # Return to main theme menu
        theme_command(update, context)
        return
    
    # Predefined color options
    color_options = {
        "primary": [
            {"name": "Blue", "value": "#0088CC"},
            {"name": "Red", "value": "#E91E63"},
            {"name": "Green", "value": "#2E7D32"},
            {"name": "Purple", "value": "#9C27B0"},
            {"name": "Orange", "value": "#FF9800"},
            {"name": "Black", "value": "#1E1E1E"}
        ],
        "secondary": [
            {"name": "White", "value": "#FFFFFF"},
            {"name": "Light Gray", "value": "#F5F5F5"},
            {"name": "Dark Gray", "value": "#333333"},
            {"name": "Light Blue", "value": "#E3F2FD"},
            {"name": "Light Pink", "value": "#FCE4EC"},
            {"name": "Light Green", "value": "#E8F5E9"}
        ],
        "accent": [
            {"name": "Cyan", "value": "#00BCD4"},
            {"name": "Amber", "value": "#FFC107"},
            {"name": "Lime", "value": "#CDDC39"},
            {"name": "Teal", "value": "#009688"},
            {"name": "Pink", "value": "#FF4081"},
            {"name": "Deep Purple", "value": "#673AB7"}
        ]
    }
    
    # Create keyboard with color options
    keyboard = []
    
    if color_type in color_options:
        for color in color_options[color_type]:
            keyboard.append([
                InlineKeyboardButton(
                    f"{color['name']} ({color['value']})", 
                    callback_data=f"theme_set:{color_type}:{color['value']}"
                )
            ])
    
    keyboard.append([
        InlineKeyboardButton(
            "← Back to Colors", 
            callback_data=f"{THEME_CUSTOM}:colors"
        )
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    color_type_names = {
        "primary": "Primary",
        "secondary": "Background",
        "accent": "Accent"
    }
    
    message = format_message_with_theme(
        f"{{emoji:theme}} *Select {color_type_names.get(color_type, color_type)} Color*\n\n"
        "Choose from the following options:",
        telegram_id
    )
    
    query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

def show_emoji_options(update: Update, context: CallbackContext, telegram_id: str) -> None:
    """Show emoji set options."""
    query = update.callback_query
    
    # Emoji set options
    emoji_sets = [
        {"id": "default", "name": "Default", "sample": "🎵 🔍 ⬇️ 📝"},
        {"id": "minimal", "name": "Minimal", "sample": "♪ → ↓ ✎"},
        {"id": "music", "name": "Music", "sample": "🎧 🔍 📥 🎤"},
        {"id": "nature", "name": "Nature", "sample": "🍃 🔍 🌱 🌷"},
        {"id": "sea", "name": "Ocean", "sample": "🐠 🔍 🌊 🐚"}
    ]
    
    # Create keyboard with emoji set options
    keyboard = []
    
    current_theme = get_user_theme(telegram_id)
    
    for emoji_set in emoji_sets:
        # Mark current emoji set
        set_label = f"{emoji_set['name']} {emoji_set['sample']}"
        if current_theme['emoji_set'] == emoji_set['id']:
            set_label += " ✓"
            
        keyboard.append([
            InlineKeyboardButton(
                set_label, 
                callback_data=f"theme_set:emoji_set:{emoji_set['id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            "← Back to Themes", 
            callback_data=f"{THEME_SELECT}:back"
        )
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = format_message_with_theme(
        "{emoji:theme} *Emoji Set Selection*\n\n"
        "Choose an emoji set to use throughout the bot interface:\n\n"
        "{emoji:info} Current set: *" + current_theme['emoji_set'] + "*",
        telegram_id
    )
    
    query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

def show_font_options(update: Update, context: CallbackContext, telegram_id: str) -> None:
    """Show font style options."""
    query = update.callback_query
    
    # Font style options
    font_styles = [
        {"id": "default", "name": "Default", "description": "Standard Telegram font"},
        {"id": "monospace", "name": "Monospace", "description": "Fixed-width technical font"},
        {"id": "serif", "name": "Serif", "description": "Classic styled font with serifs"},
        {"id": "rounded", "name": "Rounded", "description": "Modern font with rounded edges"}
    ]
    
    # Create keyboard with font style options
    keyboard = []
    
    current_theme = get_user_theme(telegram_id)
    
    for font_style in font_styles:
        # Mark current font style
        style_label = font_style['name']
        if current_theme['font_style'] == font_style['id']:
            style_label += " ✓"
            
        keyboard.append([
            InlineKeyboardButton(
                style_label, 
                callback_data=f"theme_set:font_style:{font_style['id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            "← Back to Themes", 
            callback_data=f"{THEME_SELECT}:back"
        )
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Font style preview
    font_preview = {
        "default": "Regular text",
        "monospace": "`Monospace text`",
        "serif": "*Serif text* (simulated with bold)",
        "rounded": "_Rounded text_ (simulated with italic)"
    }
    
    preview = font_preview.get(current_theme['font_style'], "Text preview")
    
    message = format_message_with_theme(
        "{emoji:theme} *Font Style Selection*\n\n"
        "Choose a font style to use throughout the bot interface:\n\n"
        "{emoji:info} Current style: *" + current_theme['font_style'] + "*\n\n"
        f"Preview: {preview}",
        telegram_id
    )
    
    query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

def theme_set_callback(update: Update, context: CallbackContext) -> None:
    """Handle theme setting callbacks."""
    query = update.callback_query
    query.answer()
    
    user = update.effective_user
    telegram_id = str(user.id)
    
    # Parse callback data
    callback_parts = query.data.split(':')
    if len(callback_parts) != 3:
        query.edit_message_text("Invalid setting option. Please try again.")
        return
    
    setting_type = callback_parts[1]
    setting_value = callback_parts[2]
    
    # Update the specific setting
    settings = {setting_type: setting_value}
    
    if update_user_theme_settings(telegram_id, settings):
        message = format_message_with_theme(
            "{emoji:success} Theme setting updated!\n\n"
            f"Changed *{setting_type}* to *{setting_value}*",
            telegram_id
        )
        
        # Return to appropriate screen based on setting type
        if setting_type in ["primary_color", "secondary_color", "accent_color"]:
            show_color_options(update, context, telegram_id)
        elif setting_type == "emoji_set":
            show_emoji_options(update, context, telegram_id)
        elif setting_type == "font_style":
            show_font_options(update, context, telegram_id)
        else:
            theme_command(update, context)
    else:
        query.edit_message_text(
            format_message_with_theme(
                "{emoji:error} Sorry, there was a problem updating your theme setting.",
                telegram_id
            )
        )