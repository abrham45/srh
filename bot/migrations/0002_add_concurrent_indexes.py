# Generated migration for concurrent user optimization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0001_initial'),
    ]

    operations = [
        # Add database indexes for better concurrent performance
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_usersession_telegram_active ON bot_usersession(telegram_user_id, is_active);",
            reverse_sql="DROP INDEX IF EXISTS idx_usersession_telegram_active;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_chatmessage_session_sender ON bot_chatmessage(session_id, sender);",
            reverse_sql="DROP INDEX IF EXISTS idx_chatmessage_session_sender;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_chatmessage_session_timestamp ON bot_chatmessage(session_id, timestamp DESC);",
            reverse_sql="DROP INDEX IF EXISTS idx_chatmessage_session_timestamp;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_feedback_chatmessage ON bot_feedback(chat_message_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_feedback_chatmessage;"
        ),
    ]
