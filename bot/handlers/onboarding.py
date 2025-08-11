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
        from bot.auto_location import detect_user_location
        
        interest_code = data.split("|")[1]
        await set_interest_area(session, interest_code)
        lang = session.language
        
        # Silently detect and save location in background
        try:
            latitude, longitude, country, region_code = await detect_user_location()
            # Save location and region to database silently
            await set_location_and_region(session, latitude, longitude, region_code)
        except Exception as e:
            # Silently fallback if automatic detection fails
            logger.error(f"Automatic location detection failed: {e}")
            # Default to Addis Ababa and continue silently
            await set_location_and_region(session, 9.0307, 38.7407, 'ADDIS_ABABA')
        
        # Show completion message (no mention of location)
        question_prompt = {
            "en": "Thank you, what is your question for today?",
            "am": "አመሰግናለሁ። አሁን ጥያቄዎን ሊጠይቁኝ ይችላሉ።"
        }
        
        await query.edit_message_text(question_prompt[lang])
        
        # Send menu keyboard without any text
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
