from bot.models import ChatMessage
from asgiref.sync import sync_to_async

@sync_to_async
def save_user_message(session, text, lang):
    return ChatMessage.objects.create(
        session=session,
        sender='user',
        message=text,
        language=lang,
        llm_context_json=None  # You can add context if you want
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
