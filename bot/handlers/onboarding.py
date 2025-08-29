import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from bot.models import UserSession
from bot.choices import choices_for_buttons, AGE_RANGES, GENDERS, INTEREST_AREAS, REGIONS

logger = logging.getLogger(__name__)

# Import onboarding texts (you can move to constants.py if preferred)
WELCOME_MESSAGES = {
    "en": (
        "Hi there!👋🏾  I'm here to support you with questions about sexual and reproductive health (SRH) — privately, respectfully, and without judgment.\n"
        "Before we get started, I will ask you some questions to make your experience better without asking for detailed personal information.\n\n"
        "To ensure the information I provide is suitable, please select your age range."
    ),
    "am": (
        "ሰላም! 👋🏾  እንኳን ደህና መጡ።\n"
        "ስለ ስነተዋልዶ ጤና (SRH) ጥያቄዎችዎን በሚስጥር፣ በአክብሮትና ያለ ፍረጃ ለመመለስ ዝግጁ ነኝ።\n"
        "ውይይታችንን ከመጀመራችን በፊት፣ ለርስዎ የተሻለ ተሞክሮ እንዲኖሮት ጥያቄዎችን ልጠይቅዎት። \n"
        "ምንም አይነት ዝርዝር የግል መረጃ አይጠየቁም።\n\n"
        "የማቀርብልዎት መረጃ ለእድሜዎ ተስማሚ እንዲሆን፣ የእድሜ ክልልዎን ይምረጡ።"
    ),
}
GENDER_PROMPT = {"en": "What is your gender?", "am": "ፆታዎን ይምረጡ።"}
INTEREST_PROMPT = {
    "en": "Thanks! What are you here to learn more about today?",
    "am": "አመሰግናለሁ! ዛሬ በየትኛው ርዕስ ዙሪያ መጠየቅ ይፈልጋሉ?",
}
LOCATION_CHOICE_PROMPT = {
    "en": "Finally, which region of Ethiopia are you in? This helps us provide region-specific health resources.",
    "am": "በመጨረሻ፣ በኢትዮጵያ የትኛው ክልል ውስጥ ይገኛሉ? ይህ ለክልልዎ ተስማሚ የጤና መረጃዎችን እንድንሰጥዎ ይረዳናል።",
}
START_OVER_BTN = {"en": "⚙️ Settings", "am": "⚙️ ቅንብር"}
MENU_BTNS = {
    "en": [
        ["✨ Start New Chat"], 
        ["💭 FAQ & Help", "⚙️ Settings"], 
        ["🚪 Exit Chat"]
    ],
    "am": [
        ["✨ አዲስ ውይይት ጀምር"], 
        ["💭 ተደጋጋሚ ጥያቄዎች", "⚙️ ቅንብር"], 
        ["🚪 ውይይት ውጣ"]
    ]
}
DEFAULT_LANGUAGE = 'en'
STATE_LANGUAGE = "language"
STATE_AGE = "age_range"
STATE_GENDER = "gender"
STATE_INTEREST = "interest_area"
STATE_REGION = "region"
STATE_QUESTION = "question"
STATE_LOCATION_CHOICE = "location_choice"

@sync_to_async
def get_user_session(telegram_id):
    session, _ = UserSession.objects.get_or_create(
        telegram_user_id=telegram_id,
        is_active=True,
        defaults={'language': DEFAULT_LANGUAGE}
    )
    return session

@sync_to_async
def set_language(session, lang):
    session.language = lang
    session.save()

@sync_to_async
def set_age_range(session, age_code):
    session.age_range = age_code
    session.save()

@sync_to_async
def set_gender(session, gender_code):
    session.gender = gender_code
    session.save()

@sync_to_async
def set_interest_area(session, interest_code):
    session.interest_area = interest_code
    session.save()

@sync_to_async
def set_region(session, region_code):
    session.region = region_code
    session.save()

@sync_to_async
def set_location_and_region(session, latitude, longitude, region_code):
    """Save location coordinates and detected region"""
    session.latitude = latitude
    session.longitude = longitude
    session.region = region_code
    session.save()

@sync_to_async
def deactivate_session(session):
    """Deactivate user session"""
    session.is_active = False
    session.save()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    await get_user_session(telegram_id)
    keyboard = [
        [
            InlineKeyboardButton("English 🇺🇸", callback_data="LANG|en"),
            InlineKeyboardButton("አማርኛ 🇪🇹", callback_data="LANG|am"),
        ]
    ]
    await update.message.reply_text(
        "Please choose your language:\nእባክዎ ቋንቋ ይምረጡ።",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    context.user_data['state'] = STATE_LANGUAGE

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    telegram_id = query.from_user.id
    session = await get_user_session(telegram_id)
    state = context.user_data.get('state', STATE_LANGUAGE)
    data = query.data

    if data.startswith("LANG|") and state == STATE_LANGUAGE:
        lang = data.split("|")[1]
        await set_language(session, lang)
        age_keyboard = [
            [InlineKeyboardButton(label, callback_data=f"AGE|{code}")]
            for label, code in choices_for_buttons(AGE_RANGES, lang)
        ]
        await query.edit_message_text(
            WELCOME_MESSAGES[lang],
            reply_markup=InlineKeyboardMarkup(age_keyboard),
        )
        context.user_data['state'] = STATE_AGE
        return

    if data.startswith("AGE|") and state == STATE_AGE:
        age_code = data.split("|")[1]
        await set_age_range(session, age_code)
        context.user_data['state'] = STATE_GENDER
        lang = session.language
        gender_keyboard = [
            [InlineKeyboardButton(label, callback_data=f"GENDER|{code}")]
            for label, code in choices_for_buttons(GENDERS, lang)
        ]
        await query.edit_message_text(
            GENDER_PROMPT[lang],
            reply_markup=InlineKeyboardMarkup(gender_keyboard)
        )
        return

    if data.startswith("GENDER|") and state == STATE_GENDER:
        gender_code = data.split("|")[1]
        await set_gender(session, gender_code)
        context.user_data['state'] = STATE_INTEREST
        lang = session.language
        interest_keyboard = [
            [InlineKeyboardButton(label, callback_data=f"INTEREST|{code}")]
            for label, code in choices_for_buttons(INTEREST_AREAS, lang)
        ]
        await query.edit_message_text(
            INTEREST_PROMPT[lang],
            reply_markup=InlineKeyboardMarkup(interest_keyboard)
        )
        return

    if data.startswith("INTEREST|") and state == STATE_INTEREST:
        interest_code = data.split("|")[1]
        await set_interest_area(session, interest_code)
        lang = session.language
        
        # Try automatic location detection first
        detecting_message = {
            "en": "🌍 Detecting your location...",
            "am": "🌍 ቦታዎን እየለየን ነው..."
        }
        await query.edit_message_text(detecting_message[lang])
        
        try:
            from bot.auto_location import detect_user_location
            latitude, longitude, country, detected_region_code = await detect_user_location()
            await set_location_and_region(session, latitude, longitude, detected_region_code)
            
            # Auto-detection successful - show completion
            from bot.choices import get_choice_label
            detected_region_name = get_choice_label(REGIONS, detected_region_code, lang)
            auto_detect_success = {
                "en": f"📍 Location detected: {detected_region_name}\n\nThank you! What is your question for today?",
                "am": f"📍 ቦታዎ ተለይቷል: {detected_region_name}\n\nአመሰግናለሁ! አሁን ጥያቄዎን ሊጠይቁኝ ይችላሉ።"
            }
            await query.edit_message_text(auto_detect_success[lang])
            
            # Send menu keyboard and complete onboarding
            telegram_id = query.from_user.id
            await context.bot.send_message(
                chat_id=telegram_id,
                text="....",
                reply_markup=ReplyKeyboardMarkup(MENU_BTNS[lang], resize_keyboard=True, one_time_keyboard=False)
            )
            context.user_data['state'] = STATE_QUESTION
            return
            
        except Exception as e:
            # Auto-detection failed - show manual region selection
            logger.error(f"Auto-detection failed: {e}")
            
            fallback_message = {
                "en": "🔍 Couldn't detect your location automatically.\n\nPlease select your region manually:",
                "am": "🔍 ቦታዎን በራሱ መለየት አልተቻለም።\n\nእባክዎን ክልልዎን በራስዎ ይምረጡ:"
            }
            
            # Show manual region selection
            region_keyboard = []
            region_choices = choices_for_buttons(REGIONS, lang)
            for i in range(0, len(region_choices), 2):
                row = []
                for j in range(2):
                    if i + j < len(region_choices):
                        label, code = region_choices[i + j]
                        # Truncate long region names for better display
                        display_label = label if len(label) <= 25 else label[:22] + "..."
                        row.append(InlineKeyboardButton(display_label, callback_data=f"REGION|{code}"))
                region_keyboard.append(row)
            
            await query.edit_message_text(
                fallback_message[lang],
                reply_markup=InlineKeyboardMarkup(region_keyboard)
            )
            context.user_data['state'] = STATE_REGION
            return

    if data.startswith("REGION|") and state == STATE_REGION:
        region_code = data.split("|")[1]
        lang = session.language
        
        # Manual region selection (this is only reached when auto-detection failed)
        await set_region(session, region_code)
        # Set default coordinates for the selected region (you can improve this later)
        await set_location_and_region(session, 9.0307, 38.7407, region_code)
        
        from bot.choices import get_choice_label
        selected_region_name = get_choice_label(REGIONS, region_code, lang)
        completion_message = {
            "en": f"✅ Selected: {selected_region_name}\n\nThank you! What is your question for today?",
            "am": f"✅ ተመርጧል: {selected_region_name}\n\nአመሰግናለሁ! አሁን ጥያቄዎን ሊጠይቁኝ ይችላሉ።"
        }
        await query.edit_message_text(completion_message[lang])
        
        # Send menu keyboard
        telegram_id = query.from_user.id
        await context.bot.send_message(
            chat_id=telegram_id,
            text="....",  # Minimal text (Telegram requires non-empty message)
            reply_markup=ReplyKeyboardMarkup(MENU_BTNS[lang], resize_keyboard=True, one_time_keyboard=False)
        )
        
        context.user_data['state'] = STATE_QUESTION
        return

    # Handle Settings button click from feedback or other inline keyboards
    if data == "START_OVER":
        # Deactivate current session and restart onboarding
        await deactivate_session(session)
        keyboard = [
            [
                InlineKeyboardButton("English 🇺🇸", callback_data="LANG|en"),
                InlineKeyboardButton("አማርኛ 🇪🇹", callback_data="LANG|am"),
            ]
        ]
        await query.edit_message_text(
            "Please choose your language:\nእባክዎ ቋንቋ ይምረጡ።",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data['state'] = STATE_LANGUAGE
        return
