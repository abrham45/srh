import logging
import re
from django.core.management.base import BaseCommand
from django.conf import settings
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes,
)
from bot.models import UserSession, ChatMessage, Feedback
from bot.choices import choices_for_buttons, AGE_RANGES, GENDERS, INTEREST_AREAS, RATING_CHOICES
from bot.prompting import build_gemini_context
from bot.gemini_api import ask_gemini
from asgiref.sync import sync_to_async

MAX_MSG_LEN = 4096

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

WELCOME_MESSAGES = {
    "en": (
        "Hi there!👋🏾  I'm here to support you with questions about sexual and reproductive health (SRH) — privately, respectfully, and without judgment.\n"
        "Before we get started, I will ask you some questions to make your experience better without asking for detailed personal information.\n\n"
        "To ensure the information I provide is suitable, please select your age range."
    ),
    "am": (
        "ሰላም! 👋🏾  እንኳን ደህና መጡ።\n"
        "ስለ ስነተዋልዶ ጤና (sexual and reproductive health (SRH)) ጥያቄዎችዎን በሚስጥር፣ በአክብሮትና ያለ ምንም ፍረጃ ለመመለስ ዝግጁ ነኝ።\n"
        "ውይይታችንን ከመጀመራችን በፊት፣ ለርስዎ የተሻለ ተሞክሮ እንዲኖሮት ጥያቄዎችን ልጠይቅዎት። \n"
        "ምንም አይነት ዝርዝር የግል መረጃ አይጠየቁም።\n\n"
        "የማቀርብልዎት መረጃ ለእድሜዎ ተስማሚ እንዲሆን፣ የእድሜ ክልልዎን ይምረጡ።"
    ),
}

GENDER_PROMPT = {
    "en": "What is your gender?",
    "am": "ፆታዎን ይምረጡ።",
}

INTEREST_PROMPT = {
    "en": "Thanks! What are you here to learn more about today?",
    "am": "አመሰግናለሁ! ዛሬ በየትኛው ርዕስ ዙሪያ መጠየቅ ይፈልጋሉ?",
}

FEEDBACK_PROMPT = {
    "en": "I hope that helped! Your feedback helps me improve and support others better. How would you rate the answer you just received?",
    "am": "እንደረዳዎት ተስፋ አደርጋለሁ! የእርስዎ አስተያየት ራሴን እንዳሻሽል እና ሌሎችን በተሻለ ሁኔታ እንድረዳ ይረዳኛል። አሁን ያገኙት መልስ እንዴት ነው?"
}

THANKS_FOR_FEEDBACK = {
    "en": "Thank you for your feedback! If you have another question, just type it below.",
    "am": "ስለ አስተያየትዎ እናመሰግናለን! ሌላ ጥያቄ ካለዎት እባክዎን ያብሩት።"
}

START_OVER_BTN = {
    "en": "🔄 Start Over",
    "am": "🔄 እንደገና ጀምር"
}

DEFAULT_LANGUAGE = 'en'

STATE_LANGUAGE = "language"
STATE_AGE = "age_range"
STATE_GENDER = "gender"
STATE_INTEREST = "interest_area"
STATE_QUESTION = "question"
STATE_FEEDBACK = "feedback"
STATE_DONE = "done"

def should_ask_feedback(n):
    milestones = [5]
    while milestones[-1] < 10000:
        milestones.append(milestones[-1]*2)
    return n in milestones

def smart_truncate(text, max_length=MAX_MSG_LEN):
    if len(text) <= max_length:
        return text
    sentences = re.split(r'(?<=[.!?]) +', text)
    result = ''
    for s in sentences:
        if len(result) + len(s) > max_length - 1:
            break
        result += s + ' '
    result = result.strip()
    if not result:
        return text[:max_length-20] + "\n\n[Shortened]"
    return result + "\n\n[Shortened. Ask for more if you need it.]"

@sync_to_async
def get_user_session(telegram_id):
    session, created = UserSession.objects.get_or_create(
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
def save_user_message(session, text, lang):
    return ChatMessage.objects.create(
        session=session,
        sender='user',
        message=text,
        language=lang,
        llm_context_json=None
    )

@sync_to_async
def save_bot_message(session, text, lang, context_json=None):
    return ChatMessage.objects.create(
        session=session,
        sender='bot',
        message=text,
        language=lang,
        llm_context_json=context_json,
    )

@sync_to_async
def get_recent_chat_history(session, limit=20):
    # Increased limit from 4 to 20 for much better conversation memory
    # This gives the bot context of last 10 user questions + 10 bot responses
    return list(ChatMessage.objects.filter(session=session).order_by('-timestamp')[:limit][::-1])

@sync_to_async
def get_last_bot_message(session):
    return ChatMessage.objects.filter(session=session, sender='bot').order_by('-timestamp').first()

@sync_to_async
def save_feedback(chat_message, rating_code):
    return Feedback.objects.create(
        chat_message=chat_message,
        rating=rating_code
    )

@sync_to_async
def count_user_questions(session):
    return ChatMessage.objects.filter(session=session, sender='user').count()

@sync_to_async
def deactivate_session(session):
    session.is_active = False
    session.save()

# --------- Handle images/media/audio/video ---------
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = await get_user_session(update.effective_user.id)
    lang = session.language
    thank_you_text = {
        "en": "Thanks for your media! I cannot analyze audio, video, or images yet, but you can ask me anything in text.",
        "am": "ስለ የላኩት ሚዲያ (ምስል፣ ድምፅ፣ ቪዲዮ) እናመሰግናለን! አሁን ምስል፣ ድምፅ ወይም ቪዲዮ ማብራሪያ ማድረግ አልችልም፣ ግን በጽሑፍ የሚመጡ ጥያቄዎችን ማስተላለፍ ይችላሉ።"
    }
    startover_keyboard = [[InlineKeyboardButton(START_OVER_BTN[lang], callback_data="START_OVER")]]
    await update.message.reply_text(thank_you_text[lang], reply_markup=InlineKeyboardMarkup(startover_keyboard))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    session = await get_user_session(telegram_id)
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
        context.user_data['state'] = STATE_QUESTION
        lang = session.language
        question_prompt = {
            "en": "Thank you, what is your question for today?",
            "am": "አመሰግናለሁ። አሁን ጥያቄዎን ሊጠይቁኝ ይችላሉ።"
        }
        await query.edit_message_text(
            question_prompt[lang]
        )
        return

    # --- Feedback (rating) flow ---
    if data.startswith("RATING|") and state == STATE_FEEDBACK:
        rating_code = data.split("|")[1]
        bot_message = await get_last_bot_message(session)
        await save_feedback(bot_message, rating_code)
        lang = session.language
        startover_keyboard = [[InlineKeyboardButton(START_OVER_BTN[lang], callback_data="START_OVER")]]
        await query.edit_message_text(THANKS_FOR_FEEDBACK[lang], reply_markup=InlineKeyboardMarkup(startover_keyboard))
        context.user_data['state'] = STATE_QUESTION  # Allow another question
        return

    # --- Start Over ---
    if data == "START_OVER":
        await deactivate_session(session)
        # Start a new session
        new_session = await get_user_session(telegram_id)
        keyboard = [
            [
                InlineKeyboardButton("English 🇺🇸", callback_data="LANG|en"),
                InlineKeyboardButton("አማርኛ 🇪🇹", callback_data="LANG|am"),
            ]
        ]
        await query.edit_message_text(
            "Please choose your language:\nእባክዎ ቋንቋ ይምረጡ።",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        context.user_data['state'] = STATE_LANGUAGE
        return

async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    session = await get_user_session(telegram_id)
    state = context.user_data.get('state')
    if state == STATE_QUESTION:
        user_question = update.message.text
        lang = session.language

        await save_user_message(session, user_question, lang)
        chat_history = await get_recent_chat_history(session)

        length_instruction = {
            "en": "Please answer concisely, completely, and within 3500 characters.",
            "am": "እባክዎ መልስዎን በአጭር እና በትክክል አድርጉ፣ እና 3500 ቁጥር ቃላት ውስጥ ይገቡ።"
        }
        prompt = (
            f"{await build_gemini_context(session, chat_history)}\n\n"
            f"User’s question: {user_question}\n"
            f"Respond in {'Amharic' if lang == 'am' else 'English'}.\n"
            f"{length_instruction[lang]}"
        )

        try:
            answer = await ask_gemini(prompt)
        except Exception as e:
            logger.exception("Gemini API error:")
            answer = "Sorry, I couldn't process your request right now. Please try again."

        final_answer = smart_truncate(answer)
        startover_keyboard = [[InlineKeyboardButton(START_OVER_BTN[lang], callback_data="START_OVER")]]
        await save_bot_message(session, final_answer, lang, context_json={"prompt": prompt})
        await update.message.reply_text(final_answer, reply_markup=InlineKeyboardMarkup(startover_keyboard))

        num_questions = await count_user_questions(session)
        if should_ask_feedback(num_questions):
            rating_keyboard = [
                [InlineKeyboardButton(label, callback_data=f"RATING|{code}")]
                for label, code in choices_for_buttons(RATING_CHOICES, lang)
            ]
            rating_keyboard.append([InlineKeyboardButton(START_OVER_BTN[lang], callback_data="START_OVER")])
            await update.message.reply_text(
                FEEDBACK_PROMPT[lang],
                reply_markup=InlineKeyboardMarkup(rating_keyboard)
            )
            context.user_data['state'] = STATE_FEEDBACK
        else:
            context.user_data['state'] = STATE_QUESTION

class Command(BaseCommand):
    help = 'Runs the Telegram SRH chatbot.'

    def handle(self, *args, **options):
        TELEGRAM_TOKEN = getattr(settings, 'TELEGRAM_TOKEN', None)
        if not TELEGRAM_TOKEN:
            raise Exception("TELEGRAM_TOKEN not set in Django settings!")

        application = Application.builder().token(TELEGRAM_TOKEN).build()

        application.add_handler(CommandHandler('start', start))
        application.add_handler(CallbackQueryHandler(button))
        application.add_handler(MessageHandler(filters.PHOTO, handle_image))
        application.add_handler(MessageHandler(filters.Document.ALL, handle_image))
        application.add_handler(MessageHandler(filters.AUDIO, handle_image))
        application.add_handler(MessageHandler(filters.VOICE, handle_image))
        application.add_handler(MessageHandler(filters.VIDEO, handle_image))
        application.add_handler(MessageHandler(filters.VIDEO_NOTE, handle_image))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question))

        application.run_polling()
