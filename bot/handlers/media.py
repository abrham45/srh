from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from bot.models import UserSession

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

@sync_to_async
def get_user_session(telegram_id):
    session, _ = UserSession.objects.get_or_create(telegram_user_id=telegram_id, is_active=True)
    return session

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = await get_user_session(update.effective_user.id)
    lang = session.language
    thank_you_text = {
        "en": "Thanks for your media! I cannot analyze audio, video, or images yet, but you can ask me anything in text.",
        "am": "ስለ የላኩት ሚዲያ (ምስል፣ ድምፅ፣ ቪዲዮ) እናመሰግናለን! አሁን ምስል፣ ድምፅ ወይም ቪዲዮ ማብራሪያ ማድረግ አልችልም፣ ግን በጽሑፍ የሚመጡ ጥያቄዎችን ማስተላለፍ ይችላሉ።"
    }
    await update.message.reply_text(
        thank_you_text[lang],
        reply_markup=ReplyKeyboardMarkup(MENU_BTNS[lang], resize_keyboard=True, one_time_keyboard=False)
    )
