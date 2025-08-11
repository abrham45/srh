import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters,
)

# Import modularized handlers
from bot.handlers.onboarding import start, button
from bot.handlers.conversation import handle_question, handle_feedback, handle_language_change, handle_faq_callback
from bot.handlers.media import handle_image

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs the Telegram SRH chatbot.'

    def handle(self, *args, **options):
        TELEGRAM_TOKEN = getattr(settings, 'TELEGRAM_TOKEN', None)
        if not TELEGRAM_TOKEN:
            raise Exception("TELEGRAM_TOKEN not set in Django settings!")

        # Enable concurrent processing for multiple users
        application = Application.builder().token(TELEGRAM_TOKEN).concurrent_updates(50).build()

        # Register handlers
        application.add_handler(CommandHandler('start', start))

        # 1. Feedback handler - register FIRST for InlineKeyboard feedback responses!
        application.add_handler(CallbackQueryHandler(handle_feedback, pattern=r"^(RATING\|.*|FEEDBACK_SETTINGS)$"))

        # 2. FAQ handler - for FAQ navigation
        application.add_handler(CallbackQueryHandler(handle_faq_callback, pattern=r"^FAQ_"))

        # 3. Language change handler - for settings language changes
        application.add_handler(CallbackQueryHandler(handle_language_change, pattern=r"^LANG_CHANGE\|"))

        # 4. Main button handler for onboarding & in-convo navigation
        application.add_handler(CallbackQueryHandler(button))

        # 5. Media handlers (photo, video, doc, audio, etc.)
        application.add_handler(MessageHandler(filters.PHOTO, handle_image))
        application.add_handler(MessageHandler(filters.Document.ALL, handle_image))
        application.add_handler(MessageHandler(filters.AUDIO, handle_image))
        application.add_handler(MessageHandler(filters.VOICE, handle_image))
        application.add_handler(MessageHandler(filters.VIDEO, handle_image))
        application.add_handler(MessageHandler(filters.VIDEO_NOTE, handle_image))

        # 6. Main Q&A handler (must be last to avoid hijacking other types)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question))

        application.run_polling()
