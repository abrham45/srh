import asyncio
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from bot.models import UserSession, ChatMessage, Feedback
from bot.choices import choices_for_buttons, RATING_CHOICES
from bot.handlers.utils import should_ask_feedback, smart_truncate
from bot.prompting import build_gemini_context
from bot.gemini_api import ask_gemini
from bot.intent_classification import perform_intent_classification
from bot.emotion_detection import perform_emotion_detection
from bot.risk_assessment import perform_risk_assessment
from bot.myth_detection import perform_myth_detection
from bot.homosexuality_filter import should_reject_question

logger = logging.getLogger(__name__)

# Configuration constants
CHAT_HISTORY_LIMIT = 20  # Number of recent messages to include in context (10 user + 10 bot)
# Increased from 4 to 20 for much better conversation memory
# This allows the bot to remember and reference much more context

STATE_QUESTION = "question"
STATE_FEEDBACK = "feedback"
STATE_LANGUAGE = "language"
STATE_LANGUAGE_CHANGE = "language_change"
STATE_FAQ_SECTION = "faq_section"
STATE_FAQ_QUESTION = "faq_question"

START_OVER_BTN = {"en": "⚙️ Settings", "am": "⚙️ ቅንብር"}
NEW_CHAT_BTN = {"en": "✨ Start New Chat", "am": "✨ አዲስ ውይይት ጀምር"}
FAQ_BTN = {"en": "💭 FAQ & Help", "am": "💭 ተደጋጋሚ ጥያቄዎች"}
HELP_BTN = {"en": "💭 FAQ & Help", "am": "💭 ተደጋጋሚ ጥያቄዎች"}
END_CHAT_BTN = {"en": "🚪 Exit Chat", "am": "🚪 ውይይት ውጣ"}
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
FEEDBACK_PROMPT = {
    "en": "I hope that helped! Your feedback helps me improve and support others better. In order to continue please provide us with feedback. How would you rate the answer you just received?",
    "am": "እንደረዳዎት ተስፋ አደርጋለሁ! የእርስዎ አስተያየት ራሴን እንዳሻሽል እና ሌሎችን በተሻለ ሁኔታ እንድረዳ ይረዳኛል። ለመቀጠል እባክዎን አስተያየትዎን ይስጡን። አሁን ያገኙት መልስ እንዴት ነው?"
}
THANKS_FOR_FEEDBACK = {
    "en": "Thank you for your feedback! If you have another question, just type it below.",
    "am": "ስለ አስተያየትዎ እናመሰግናለን! ሌላ ጥያቄ ካለዎት እባክዎን"
}

HELP_BTNS = ["❓ Help", "❓ እርዳታ"]
NEW_CHAT_BTNS = ["✨ Start New Chat", "✨ አዲስ ውይይት ጀምር"]
FAQ_BTNS = ["💭 FAQ & Help", "💭 ተደጋጋሚ ጥያቄዎች"]
END_CHAT_BTNS = ["🚪 Exit Chat", "🚪 ውይይት ውጣ"]

# FAQ Categories (for internal organization only)
FAQ_CATEGORIES = ["pregnancy", "menstruation", "contraception", "sti", "puberty", "relationships"]

# FAQ Data based on the spreadsheet
FAQ_DATA = {
    "pregnancy": {
        "en": [
            ("Can a girl get pregnant the first time she has sex?", "Yes. Pregnancy can happen any time a male's sperm meets a female's egg—even during the first time a girl has sex."),
            ("Can you get pregnant during your period?", "Yes, though it's less likely. Sperm can live inside the body for up to 5 days, and some women have shorter cycles, making pregnancy possible."),
            ("How can I tell if I'm pregnant without a test?", "Some common signs include missed periods, nausea, breast tenderness, and tiredness. However, only a pregnancy test can confirm for sure."),
            ("What are safe ways to avoid pregnancy?", "Family planning methods include natural tracking of your cycle, condoms, implants, and other methods provided by health professionals. Visit a clinic to learn what's available in your area."),
            ("Is it dangerous for a teenager to get pregnant?", "Yes, early pregnancies can be risky for both mother and baby. It's important to delay pregnancy until the body is more mature and there is enough support.")
        ],
        "am": [
            ("አንዲት ሴት ለመጀመሪያ ጊዜ ወሲብ ስትፈጽም ማርገዝ ትችላለች?", "አዎ፣ የወንድ የዘር ፍሬ ከሴት እንቁላል ጋር በሚገናኝበት ጊዜ ሁሉ እርግዝና ሊከሰት ይችላል—ሴት ልጅ ለመጀመሪያ ጊዜ ወሲብ ስትፈጽም ቢሆን።"),
            ("በወር አበባ ወቅት እርጉዝ መሆን ይቻላል?", "ያነሰ እድል ቢሆንም አዎ ሊሆን ይችላል። የወንድ የዘር ፍሬ በሰውነት ውስጥ እስከ 5 ቀናት ሊቆይ ይችላል፣ እናም አንዳንድ ሴቶች ደግሞ አጭር የወር አበባ ዑደት አላቸው፣ ይህም እርግዝናን ያስከትላል።"),
            ("ያለ ምርመራ እርጉዝ መሆኔን እንዴት ማወቅ እችላለሁ?", "አንዳንድ የተለመዱ ምልክቶች ያመለጡ የወር አበባዎች፣ ማቅለሽለሽ፣ የጡት መጠንከር እና ድካም ያካትታሉ። ሆኖም፣ የእርግዝና ምርመራ ብቻ ነው በእርግጠኝነት ማረጋገጥ የሚችለው።"),
            ("እርግዝና አንዳይፈጠር የሚያደርጉ ጥሩ መንገዶች ምንድን ናቸው?", "የቤተሰብ እቅድ ዘዴዎች የወር አበባ ዑደትዎን መከታተል፣ ኮንዶምን፣ መከላከያዎችን እና በጤና ባለሙያዎች የሚሰጡ ሌሎች ዘዴዎችን መጠቀምን ያካትታሉ። በአካባቢዎ ያለውን ለማወቅ አቅራቢያዎ ያለን ክሊኒክ ይጎብኙ።"),
            ("በአሥራዎቹ ዕድሜ ላይ ለምትገኝ ልጅ እርጉዝ መሆን አደገኛ ነው?", "አዎን፣ በልጀነት የሚፈጠር እርግዝና ለእናትም ሆነ ለሕፃን አደገኛ ሊሆን ይችላል። ሰውነት የበለጠ እስኪበስል እና በቂ ድጋፍ እስኪኖር ድረስ እርግዝናን ማዘግየት አስፈላጊ ነው።")
        ]
    },
    "menstruation": {
        "en": [
            ("Is it normal to miss a period sometimes?", "Yes, especially in the first few years after periods start. Stress, illness, or changes in weight can also affect your cycle. If you miss your period for more than 2 months, consider speaking to a health professional."),
            ("How much bleeding is normal during a period?", "Most people lose about 2-3 tablespoons of blood during their entire period. Heavy bleeding that soaks through a pad or tampon every hour for several hours needs medical attention."),
            ("Can I exercise during my period?", "Yes! Exercise can actually help reduce cramps and improve your mood during your period. Just use the protection you're comfortable with."),
            ("Why do I get cramps during my period?", "Cramps happen because your uterus contracts to shed its lining. This is normal, but severe pain that interferes with daily activities should be discussed with a healthcare provider.")
        ],
        "am": [
            ("አንዳንድ ጊዜ የወር አበባ መዘግየት ተለመደ ነው?", "አዎ፣ በተለይ የወር አበባ ከተጀመረ በኋላ በመጀመሪያዎቹ ዓመታት። ጭንቀት፣ ህመም ወይም የክብደት ለውጦች የወር አበባ ዑደትዎን ሊጎዱ ይችላሉ። የወር አበባዎትን ከ2 ወር በላይ ካመለጥዎት፣ ከጤና ባለሙያ ጋር ማናገር ያስቡበት።"),
            ("በወር አበባ ወቅት ምን ያህል ደም መፍሰስ የተለመደ ነው?", "አብዛኞቹ ሰዎች በጠቅላላ የወር አበባ ወቅት ወደ 2-3 የሻይ ማንኪያ ያህል ደም ያጣሉ። በየሰዓቱ ለብዙ ሰዓታት ወጣቶችን ወይም ታምፖንን የሚነከር ከባድ ደም መፍሰስ የሕክምና እንክብካቤ ያስፈልገዋል።"),
            ("በወር አበባ ወቅት የአካል ብቃት እንቅስቃሴ ማድረግ እችላለሁ?", "አዎ! የአካል ብቃት እንቅስቃሴ በሳቅታ ወቅት ደረትን ሊቀንስ እና ስሜትዎን ሊያሻሽል ይችላል። የሚመቸዎትን ጥበቃ ብቻ ይጠቀሙ።"),
            ("በወር አበባ ወቅት ለምን ሆዴ ይቆጣል?", "የሆድ ቁርጠት የሚከሰተው ማህፀንዎ በደሙ ውስጥ ያለውን ሽፋን ለማስወገድ በሚያሸማቅቅበት ጊዜ ነው። ይህ የተለመደ ነው፣ ነገር ግን ዕለታዊ እንቅስቃሴዎችን የሚያደናቅፍ ከባድ ህመም ከጤና አጠባበቅ አቅራቢ ጋር መወያየት አለበት።")
        ]
    },
    "contraception": {
        "en": [
            ("What contraceptive methods are available?", "There are many options including condoms, birth control pills, implants, IUDs, and injectable contraceptives. Consult a healthcare provider to find what's best for you."),
            ("Are condoms effective?", "Yes, when used correctly, condoms are about 98% effective at preventing pregnancy and also protect against STIs."),
            ("Can I use emergency contraception?", "Emergency contraception can be used up to 72-120 hours after unprotected sex, depending on the type. The sooner it's taken, the more effective it is.")
        ],
        "am": [
            ("ምን ዓይነት የወሊድ መከላከያ ዘዴዎች አሉ?", "ኮንዶም፣ የወሊድ መከላከያ ክኒኖች፣ ወተትተክዎች፣ IUDs እና የመርፌ መከላከያዎችን ጨምሮ ብዙ አማራጮች አሉ። ለእርስዎ ምን እንደሚሻል ለማወቅ ከጤና አጠባበቅ አቅራቢ ጋር ይመክሩ።"),
            ("ኮንዶሞች ውጤታማ ናቸው?", "አዎ፣ በትክክል ሲጠቀሙ፣ ኮንዶሞች እርግዝናን ከመከላከል ከ98% ውጤታማ ናቸው እናም ከSTIs ይጠብቁዎታል።"),
            ("ድንገተኛ መከላከያ መጠቀም እችላለሁ?", "ድንገተኛ መከላከያ ከጥበቃ ያለ ወሲብ በኋላ እስከ 72-120 ሰዓታት ሊጠቀሙ ይችላሉ፣ አይነቱን በመወሰን። በፍጥነት ሲወሰድ የበለጠ ውጤታማ ነው።")
        ]
    },
    "sti": {
        "en": [
            ("How can I protect myself from STIs?", "Use condoms consistently, limit sexual partners, get regular testing, and communicate openly with partners about sexual health."),
            ("What are common STI symptoms?", "Symptoms can include unusual discharge, burning during urination, genital sores, or itching. However, many STIs have no symptoms, so regular testing is important."),
            ("Can STIs be treated?", "Many STIs can be cured with proper treatment, especially bacterial infections. Viral infections can be managed with medication.")
        ],
        "am": [
            ("ከSTIs እንዴት መጠበቅ እችላለሁ?", "ኮንዶሞችን በማያቋርጥ ይጠቀሙ፣ የወሲብ አጋሮችን ይገድቡ፣ መደበኛ ምርመራ ያድርጉ፣ እና ስለ ጾታዊ ጤና ከአጋሮች ጋር በግልጽ ይነጋገሩ።"),
            ("የተለመዱ የSTI ምልክቶች ምንድን ናቸው?", "ምልክቶች ያልተለመደ ፈሳሽ፣ ሽንት ወቅት መቃጠል፣ የወሊድ አካላት ቁስሎች ወይም ማሳከክን ሊያካትቱ ይችላሉ። ሆኖም፣ ብዙ STIs ምንም ምልክት የላቸውም፣ ስለዚህ መደበኛ ምርመራ አስፈላጊ ነው።"),
            ("STIs ሊታከሙ ይችላሉ?", "ብዙ STIs በትክክለኛ ሕክምና ሊፈወሱ ይችላሉ፣ በተለይ የባክቴሪያ ኢንፌክሽኖች። የቫይረስ ኢንፌክሽኖች በመድኃኒት ሊተዳደሩ ይችላሉ።")
        ]
    },
    "puberty": {
        "en": [
            ("When does puberty start?", "Puberty typically begins between ages 8-13 for girls and 9-14 for boys, but timing varies widely and is normal."),
            ("What changes happen during puberty?", "Physical changes include growth spurts, voice changes, development of sexual characteristics, and emotional changes."),
            ("Is irregular periods normal during puberty?", "Yes, it's very common for periods to be irregular for the first few years after they start.")
        ],
        "am": [
            ("የአካል እድገት መቼ ይጀመራል?", "የአካል እድገት በተለምዶ ለሴት ልጆች በ8-13 እድመ እና ለወንድ ልጆች በ9-14 እድሜ ይጀመራል፣ ነገር ግን ጊዜው በሰፊው ይለያያል እና የተለመደ ነው።"),
            ("በአካል እድገት ወቅት ምን ለውጦች ይከሰታሉ?", "አካላዊ ለውጦች ፈጣን እድገት፣ የድምፅ ለውጦች፣ የወሲብ ባህሪያት እድገት እና ስሜታዊ ለውጦችን ያካትታሉ።"),
            ("በአካል እድገት ወቅት መደበኛ ያልሆነ የወር አበባ የተለመደ ነው?", "አዎ፣ የወር አበባ ከተጀመረ በኋላ ለመጀመሪያዎቹ ጥቂት ዓመታት መደበኛ ያልሆነ መሆን በጣም የተለመደ ነው።")
        ]
    },
    "relationships": {
        "en": [
            ("How do I know if I'm ready for a relationship?", "You should feel emotionally mature, able to communicate well, and understand the responsibilities that come with relationships."),
            ("What is consent?", "Consent means freely agreeing to sexual activity. It must be clear, ongoing, and can be withdrawn at any time."),
            ("How can I communicate better with my partner?", "Practice active listening, express your feelings honestly, respect boundaries, and discuss important topics openly.")
        ],
        "am": [
            ("ለግንኙነት ዝግጁ መሆኔን እንዴት ማወቅ እችላለሁ?", "ስሜታዊ በብስለት መሰማት፣ በደንብ መገናኘት እና ከግንኙነቶች ጋር የሚመጡ ሃላፊነቶችን መረዳት አለብዎት።"),
            ("ፈቃድ ምንድን ነው?", "ፈቃድ ማለት ለወሲብ እንቅስቃሴ በነፃ መስማማት ማለት ነው። ግልጽ፣ ቀጣይ መሆን አለበት፣ እና በማንኛውም ጊዜ ሊወሰድ ይችላል።"),
            ("ከአጋሬ ጋር በተሻለ ሁኔታ እንዴት መገናኘት እችላለሁ?", "ንቁ ማዳመጥን ይለማመዱ፣ ስሜቶቻችሁን በታማኝነት ይግለጹ፣ ወሰኖችን ያክብሩ፣ እና አስፈላጊ ርዕሶችን በግልጽ ይወያዩ።")
        ]
    }
}

@sync_to_async
def get_user_session(telegram_id):
    # Simple get_or_create without select_for_update to avoid transaction issues
    # The concurrent processing at the application level handles race conditions
    session, _ = UserSession.objects.get_or_create(
        telegram_user_id=telegram_id, 
        is_active=True,
        defaults={'language': 'en'}  # Set default language if creating new session
    )
    return session

async def show_faq_sections(update, context, lang):
    """Show FAQ section selection"""
    sections_msg = {
        "en": "📋 **FAQ - Choose a Topic**\n\nPlease select the topic you'd like to learn about:",
        "am": "📋 **ተደጋጋሚ ጥያቄዎች - ርዕስ ይምረጡ**\n\nመማር የሚፈልጉትን ርዕስ ይምረጡ:"
    }
    
    # Create inline keyboard for sections
    keyboard = []
    section_titles = {
        "pregnancy": {"en": "🤱 Pregnancy & Family Planning", "am": "🤱 እርግዝና እና የቤተሰብ እቅድ"},
        "menstruation": {"en": "🩸 Menstruation (Periods)", "am": "🩸 የወር አበባ"},
        "contraception": {"en": "🛡️ Contraception & Birth Control", "am": "🛡️ ወሊድ መከላከያ"},
        "sti": {"en": "🦠 STIs & Sexual Health", "am": "🦠 ጾታዊ ተላላፊ በሽታዎች"},
        "puberty": {"en": "🌱 Puberty & Development", "am": "🌱 የአካል እድገት"},
        "relationships": {"en": "💕 Relationships & Sexuality", "am": "💕 የፍቅር ግንኙነት"}
    }
    
    for section_id in FAQ_CATEGORIES:
        if section_id in section_titles:
            section_name = section_titles[section_id][lang]
            keyboard.append([InlineKeyboardButton(section_name, callback_data=f"FAQ_SECTION|{section_id}")])
    
    # Add back to menu button
    back_text = {"en": "🔙 Back to Menu", "am": "🔙 ወደ ማውጫ ተመለስ"}
    keyboard.append([InlineKeyboardButton(back_text[lang], callback_data="FAQ_BACK_TO_MENU")])
    
    await update.message.reply_text(
        sections_msg[lang],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    context.user_data['state'] = STATE_FAQ_SECTION



async def show_section_qa(update, context, section_id, lang):
    """Show all Q&A pairs for a section"""
    if section_id not in FAQ_DATA:
        await update.callback_query.edit_message_text("❌ Section not found. Please try again.")
        return
    
    # Get section title
    section_titles = {
        "pregnancy": {"en": "🤱 Pregnancy & Family Planning", "am": "🤱 እርግዝና እና የቤተሰብ እቅድ"},
        "menstruation": {"en": "🩸 Menstruation (Periods)", "am": "🩸 የወር አበባ"},
        "contraception": {"en": "🛡️ Contraception & Birth Control", "am": "🛡️ ወሊድ መከላከያ"},
        "sti": {"en": "🦠 STIs & Sexual Health", "am": "🦠 ጾታዊ ተላላፊ በሽታዎች"},
        "puberty": {"en": "🌱 Puberty & Development", "am": "🌱 የአካል እድገት"},
        "relationships": {"en": "💕 Relationships & Sexuality", "am": "💕 የፍቅር ግንኙነት"}
    }
    
    section_name = section_titles.get(section_id, {}).get(lang, "FAQ")
    
    # Build message with all Q&A pairs
    qa_msg = f"📋 **{section_name}**\n\n"
    
    questions = FAQ_DATA[section_id][lang]
    for i, (question, answer) in enumerate(questions, 1):
        qa_msg += f"**{i}. {question}**\n\n✅ {answer}\n\n{'─' * 30}\n\n"
    
    # Create navigation
    keyboard = []
    back_to_topics_text = {"en": "🔙 Back to Topics", "am": "🔙 ወደ ርዕሶች ተመለስ"}
    back_to_menu_text = {"en": "🏠 Main Menu", "am": "🏠 ዋና ማውጫ"}
    
    keyboard.append([InlineKeyboardButton(back_to_topics_text[lang], callback_data="FAQ_BACK_TO_SECTIONS")])
    keyboard.append([InlineKeyboardButton(back_to_menu_text[lang], callback_data="FAQ_BACK_TO_MENU")])
    
    await update.callback_query.edit_message_text(
        qa_msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_faq_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle FAQ callback queries"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    session = await get_user_session(telegram_id)
    lang = session.language
    data = query.data
    
    if data == "FAQ_BACK_TO_MENU":
        # Go back to main menu
        menu_msg = {"en": "Back to main menu:", "am": "ወደ ዋናው ማውጫ:"}
        await query.edit_message_text(menu_msg[lang])
        await context.bot.send_message(
            chat_id=telegram_id,
            text="....",
            reply_markup=ReplyKeyboardMarkup(MENU_BTNS[lang], resize_keyboard=True, one_time_keyboard=False)
        )
        context.user_data['state'] = STATE_QUESTION
        return
    
    elif data == "FAQ_BACK_TO_SECTIONS":
        # Show sections again
        await show_faq_sections_callback(query, context, lang)
        return
    
    elif data.startswith("FAQ_SECTION|"):
        # Show Q&A pairs for selected section
        section_id = data.split("|")[1]
        await show_section_qa(update, context, section_id, lang)
        return

async def show_faq_sections_callback(query, context, lang):
    """Show FAQ sections for callback"""
    sections_msg = {
        "en": "📋 **FAQ - Choose a Topic**\n\nPlease select the topic you'd like to learn about:",
        "am": "📋 **ተደጋጋሚ ጥያቄዎች - ርዕስ ይምረጡ**\n\nመማር የሚፈልጉትን ርዕስ ይምረጡ:"
    }
    
    # Create inline keyboard for sections
    keyboard = []
    section_titles = {
        "pregnancy": {"en": "🤱 Pregnancy & Family Planning", "am": "🤱 እርግዝና እና የቤተሰብ እቅድ"},
        "menstruation": {"en": "🩸 Menstruation (Periods)", "am": "🩸 የወር አበባ"},
        "contraception": {"en": "🛡️ Contraception & Birth Control", "am": "🛡️ ወሊድ መከላከያ"},
        "sti": {"en": "🦠 STIs & Sexual Health", "am": "🦠 ጾታዊ ተላላፊ በሽታዎች"},
        "puberty": {"en": "🌱 Puberty & Development", "am": "🌱 የአካል እድገት"},
        "relationships": {"en": "💕 Relationships & Sexuality", "am": "💕 የፍቅር ግንኙነት"}
    }
    
    for section_id in FAQ_CATEGORIES:
        if section_id in section_titles:
            section_name = section_titles[section_id][lang]
            keyboard.append([InlineKeyboardButton(section_name, callback_data=f"FAQ_SECTION|{section_id}")])
    
    # Add back to menu button
    back_text = {"en": "🔙 Back to Menu", "am": "🔙 ወደ ማውጫ ተመለስ"}
    keyboard.append([InlineKeyboardButton(back_text[lang], callback_data="FAQ_BACK_TO_MENU")])
    
    await query.edit_message_text(
        sections_msg[lang],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    context.user_data['state'] = STATE_FAQ_SECTION

@sync_to_async
def save_user_message(session, text, lang):
    return ChatMessage.objects.create(
        session=session, sender='user', message=text, language=lang, llm_context_json=None
    )

@sync_to_async
def save_bot_message(session, text, lang, context_json=None):
    return ChatMessage.objects.create(
        session=session, sender='bot', message=text, language=lang, llm_context_json=context_json
    )

@sync_to_async
def get_recent_chat_history(session, limit=CHAT_HISTORY_LIMIT):
    # Use select_related to optimize database queries
    # Increased limit from 4 to 20 for much better conversation memory
    # This gives the bot context of last 10 user questions + 10 bot responses
    return list(ChatMessage.objects.filter(session=session)
                .select_related('session')
                .order_by('-timestamp')[:limit][::-1])

@sync_to_async
def get_last_bot_message(session):
    return ChatMessage.objects.filter(session=session, sender='bot').order_by('-timestamp').first()

@sync_to_async
def save_feedback(chat_message, rating_code):
    return Feedback.objects.create(chat_message=chat_message, rating=rating_code)

@sync_to_async
def count_user_questions(session):
    return ChatMessage.objects.filter(session=session, sender='user').count()

@sync_to_async
def get_user_session_with_stats(telegram_id):
    """
    Optimized function to get user session and question count in one query.
    Reduces database calls for concurrent users.
    """
    from django.db.models import Count, Q
    
    session, created = UserSession.objects.get_or_create(
        telegram_user_id=telegram_id, 
        is_active=True,
        defaults={'language': 'en'}
    )
    
    # Get question count separately
    question_count = ChatMessage.objects.filter(
        session=session, 
        sender='user'
    ).count()
    
    return session, question_count, created

@sync_to_async
def deactivate_session(session):
    session.is_active = False
    session.save()

@sync_to_async
def clear_chat_history(session):
    """Clear all chat messages for a session while keeping user profile"""
    ChatMessage.objects.filter(session=session).delete()

@sync_to_async  
def set_language(session, lang):
    """Update session language"""
    session.language = lang
    session.save()

async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    session = await get_user_session(telegram_id)
    lang = session.language
    state = context.user_data.get('state')
    user_input = update.message.text.strip()

    # --- Check if user is in feedback state ---
    if state == STATE_FEEDBACK:
        # User must provide feedback before continuing - show feedback options again
        rating_keyboard = [
            [InlineKeyboardButton(label, callback_data=f"RATING|{code}")]
            for label, code in choices_for_buttons(RATING_CHOICES, lang)
        ]
        rating_keyboard.append([InlineKeyboardButton(START_OVER_BTN[lang], callback_data="FEEDBACK_SETTINGS")])
        await update.message.reply_text(
            FEEDBACK_PROMPT[lang],
            reply_markup=InlineKeyboardMarkup(rating_keyboard)
        )
        return

    # --- Settings via menu ---
    if user_input in [START_OVER_BTN["en"], START_OVER_BTN["am"]]:
        # Don't deactivate session - just show language change options
        keyboard = [
            [
                InlineKeyboardButton("English 🇺🇸", callback_data="LANG_CHANGE|en"),
                InlineKeyboardButton("አማርኛ 🇪🇹", callback_data="LANG_CHANGE|am"),
            ]
        ]
        settings_msg = {
            "en": "⚙️ Choose your preferred language:\n\nNote: This will change the language for all future responses.",
            "am": "⚙️ የሚፈልጉትን ቋንቋ ይምረጡ:\n\nማስታወሻ: ይህ ለወደፊቱ ሁሉም ምላሾች ቋንቋ ይቀይራል።"
        }
        await update.message.reply_text(
            settings_msg[lang],
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await update.message.reply_text("", reply_markup=ReplyKeyboardRemove())
        context.user_data['state'] = STATE_LANGUAGE_CHANGE
        return

    # --- Help via menu ---
    if user_input in HELP_BTNS:
        help_msg = {
            "en": (
                "👋 This is an SRH help bot. Type your question or choose an option from the menu.\n\n"
                "Use 'Settings' to change your profile, or 'End Chat' to clear your data."
            ),
            "am": (
                "👋 ይህ የSRH እርዳታ ቦት ነው። ጥያቄዎን ያብሩ ወይም ከማውጫው ውስጥ ይምረጡ።\n\n"
                "'ቅንብር' የሚለውን መገለጫዎን ለመቀየር፣ 'ውይይት ያቁሙ' የሚለውን ውሂብዎን ለመሰረዝ ይጠቀሙ።"
            )
        }
        await update.message.reply_text(
            help_msg[lang],
            reply_markup=ReplyKeyboardMarkup(MENU_BTNS[lang], resize_keyboard=True, one_time_keyboard=False)
        )
        return

    # --- New Chat via menu ---
    if user_input in NEW_CHAT_BTNS:
        # Clear only the chat history but keep user profile
        await clear_chat_history(session)
        new_chat_msg = {
            "en": "💬 Starting a new conversation! Your profile settings are preserved. What would you like to ask?",
            "am": "💬 አዲስ ውይይት ጀምረናል! የእርስዎ መገለጫ ቅንብሮች ተጠብቀዋል። ምን መጠየቅ ይፈልጋሉ?"
        }
        await update.message.reply_text(
            new_chat_msg[lang],
            reply_markup=ReplyKeyboardMarkup(MENU_BTNS[lang], resize_keyboard=True, one_time_keyboard=False)
        )
        context.user_data['state'] = STATE_QUESTION
        return

    # --- FAQ via menu ---
    if user_input in FAQ_BTNS:
        await show_faq_sections(update, context, session.language)
        return

    # --- End Chat via menu ---
    if user_input in END_CHAT_BTNS:
        await deactivate_session(session)
        end_msg = {
            "en": "✅ Your chat session has ended and your data was cleared. Type /start to begin again!",
            "am": "✅ ውይይትዎ ተዘግቷል። መጀመሪያ ለማድረግ /start ይጻፉ!"
        }
        await update.message.reply_text(
            end_msg[lang],
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data['state'] = STATE_LANGUAGE
        return

    # --- Normal Q&A flow ---
    if state == STATE_QUESTION:
        user_question = user_input
        
        # Check if question is about homosexuality and reject if so
        should_reject, rejection_message = should_reject_question(user_question, lang)
        if should_reject:
            await update.message.reply_text(
                rejection_message,
                reply_markup=ReplyKeyboardMarkup(MENU_BTNS[lang], resize_keyboard=True, one_time_keyboard=False)
            )
            return
        
        try:
            # Save user message and get chat history concurrently
            user_msg_task = save_user_message(session, user_question, lang)
            chat_history_task = get_recent_chat_history(session)
            
            # Wait for both operations to complete
            await user_msg_task
            chat_history = await chat_history_task

            # Language-specific instructions
            if lang == 'am':
                length_instruction = "እባክዎ መልስዎን በአጭር እና በትክክል በአማርኛ ብቻ ይመልሱ። በ3500 ቁምፊ ውስጥ ይገቡ።"
                question_label = "የተጠቃሚ ጥያቄ"
                language_instruction = (
                    "በአማርኛ ቋንቋ ብቻ ይመልሱ። ምንም እንግሊዝኛ ቃላት ወይም ሐረጎች አይጠቀሙ። "
                    "የአማርኛ ፊደላትን ብቻ ይጠቀሙ። "
                    "ተጠቃሚው አማርኛ ተናጋሪ ነው እና በአማርኛ ብቻ ይረዳል።"
                )
            else:
                length_instruction = "Please answer concisely, completely, and within 3500 characters."
                question_label = "User's question"
                language_instruction = (
                    "Respond ONLY in English. Do not use any Amharic words or phrases. "
                    "Use only English alphabet and words. "
                    "The user is an English speaker and understands only English."
                )

            # Safety reminders
            medication_safety = {
                'en': "⚠️ MEDICATION SAFETY: As SRH expert consultant, explain medications educationally but always add 'but before taking any medication, you need a doctor's prescription.'",
                'am': "⚠️ የመድኃኒት ደህንነት: እንደ SRH ባለሙያ አማካሪ ስለ መድኃኒቶች ትምህርታዊ ያብራሩ ነገር ግን ሁልጊዜ 'ግን ማንኛውንም መድኃኒት ከመውሰድዎ በፊት የሐኪም ዶክተር ትዕዛዝ ያስፈልግዎታል' ብለው ያክሉ።"
            }
            
            scope_reminder = {
                'en': "⚠️ SCOPE: Only answer SRH-related questions. Politely redirect non-SRH questions.",
                'am': "⚠️ ወሰን: ስለ ስነተዋልዶ ጤና ጥያቄዎች ብቻ ይመልሱ። ሌሎች ጥያቄዎችን በአክብሮት ይሳሳቱ።"
            }
            
            response_guidelines = {
                'en': "⚠️ CONTEXTUAL ENGAGEMENT: Keep answers moderate length (4-5 sentences), supportive and encouraging. Continue the conversation naturally without unnecessary greetings. End with ONE simple, relevant question based on context to keep conversation engaging. Never ask multiple questions - only ONE question per response.",
                'am': "⚠️ ባውድ ላይ የተመሰረተ መሳተፍ: መልሶችን መጠነኛ ርዝመት (4-5 ዓረፍተ ነገር)፣ ድጋፋዊ እና አበረታች ያድርጉ። ቀጣይ ውይይት ሲሆን ሰላምታ አይድገሙ። በአውድ ላይ በመመስረት ንግግሩን አሳታፊ ለማድረግ አንድ ቀላል እና ተዛማጅ ጥያቄ በመጨረስ ያጠናቅቁ። ብዙ ጥያቄዎችን አይጠይቁ - በአንድ ምላሽ ውስጥ አንድ ጥያቄ ብቻ።"
            }
            
            ethiopian_context = {
                'en': "⚠️ ETHIOPIAN CONTEXT: You are operating in Ethiopia. Consider Ethiopian culture, healthcare system (health posts, health centers, hospitals), and conservative values. Recommend local Ethiopian health facilities when professional help is needed. For questions about homosexuality, respect Ethiopian conservative cultural and religious values without promoting such behaviors.",
                'am': "⚠️ የኢትዮጵያ አውድ: እርስዎ በኢትዮጵያ ውስጥ እየሰሩ ነዎት። የኢትዮጵያን ባህል፣ የጤና ሲስተም (ጤና ጣቢያዎች፣ ጤና ኬላዎች፣ ሆስፒታሎች)፣ እና ወግ አጥባቂ እሴቶችን ግምት ውስጥ ያስገቡ። የፕሮፌሽናል እርዳታ ሲያስፈልግ የኢትዮጵያ የጤና ተቋማትን ይምከሩ። ስለ ግብረ-ሰዶማዊነት ጥያቄዎች ላይ የኢትዮጵያን ወግ አጥባቂ ባህላዊ እና ሃይማኖታዊ እሴቶችን ያከብሩ።"
            }
                
            prompt = (
                f"{await build_gemini_context(session, chat_history)}\n\n"
                f"{question_label}: {user_question}\n\n"
                f"MEDICATION SAFETY: {medication_safety[lang]}\n"
                f"QUESTION SCOPE: {scope_reminder[lang]}\n"
                f"ETHIOPIAN CONTEXT: {ethiopian_context[lang]}\n"
                f"CONTEXTUAL ENGAGEMENT: {response_guidelines[lang]}\n"
                f"LANGUAGE REQUIREMENT: {language_instruction}\n"
                f"RESPONSE INSTRUCTION: {length_instruction}"
            )

            # Get AI response (this includes its own error handling now)
            answer = await ask_gemini(prompt)
            
            final_answer = smart_truncate(answer)
            
            # Save bot message and count questions concurrently
            save_msg_task = save_bot_message(session, final_answer, lang, context_json={"prompt": prompt})
            count_task = count_user_questions(session)
            
            # Send response to user immediately (don't wait for DB operations)
            await update.message.reply_text(
                final_answer,
                reply_markup=ReplyKeyboardMarkup(MENU_BTNS[lang], resize_keyboard=True, one_time_keyboard=False)
            )
            
            # Now wait for DB operations to complete
            await save_msg_task
            num_questions = await count_task
            
            # Perform intent classification at 5th, 10th, 20th, 40th, 80th... conversations (runs in background)
            try:
                classification_task = perform_intent_classification(session, lang)
                # Don't await this to avoid blocking the user response
                asyncio.create_task(classification_task)
                logger.debug(f"Started intent classification task for session {session.id}")
            except Exception as e:
                logger.warning(f"Failed to start intent classification: {e}")
            
            # Perform emotion detection at 5th, 20th, 80th, 320th... conversations (runs in background)
            try:
                emotion_task = perform_emotion_detection(session, lang)
                # Don't await this to avoid blocking the user response
                asyncio.create_task(emotion_task)
                logger.debug(f"Started emotion detection task for session {session.id}")
            except Exception as e:
                logger.warning(f"Failed to start emotion detection: {e}")
            
            # Perform risk assessment at 3rd, 6th, 12th, 24th, 48th... conversations (runs in background)
            try:
                risk_task = perform_risk_assessment(session, num_questions)
                # Don't await this to avoid blocking the user response
                asyncio.create_task(risk_task)
                logger.debug(f"Started risk assessment task for session {session.id}")
            except Exception as e:
                logger.warning(f"Failed to start risk assessment: {e}")
            
            # Perform myth detection every 2 messages starting from 2nd (runs in background)
            try:
                myth_task = perform_myth_detection(session, num_questions)
                # Don't await this to avoid blocking the user response
                asyncio.create_task(myth_task)
                logger.debug(f"Started myth detection task for session {session.id}")
            except Exception as e:
                logger.warning(f"Failed to start myth detection: {e}")
            
            if should_ask_feedback(num_questions):
                rating_keyboard = [
                    [InlineKeyboardButton(label, callback_data=f"RATING|{code}")]
                    for label, code in choices_for_buttons(RATING_CHOICES, lang)
                ]
                rating_keyboard.append([InlineKeyboardButton(START_OVER_BTN[lang], callback_data="FEEDBACK_SETTINGS")])
                await update.message.reply_text(
                    FEEDBACK_PROMPT[lang],
                    reply_markup=InlineKeyboardMarkup(rating_keyboard)
                )
                context.user_data['state'] = STATE_FEEDBACK
            else:
                context.user_data['state'] = STATE_QUESTION
                
        except Exception as e:
            # Enhanced error handling for concurrent scenarios
            logger.error(f"Error processing question for user {telegram_id}: {e}")
            
            # Language-specific error messages
            if lang == 'am':
                error_msg = "ይቅርታ፣ አሁን ጥያቄዎን መመለስ አልቻልኩም። እባክዎ እንደገና ይሞክሩ።"
            else:
                error_msg = "Sorry, I couldn't process your request right now. Please try again."
            
            await update.message.reply_text(
                error_msg,
                reply_markup=ReplyKeyboardMarkup(MENU_BTNS[lang], resize_keyboard=True, one_time_keyboard=False)
            )

async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    telegram_id = query.from_user.id
    session = await get_user_session(telegram_id)
    lang = session.language

    if query.data.startswith("RATING|"):
        rating_code = query.data.split("|")[1]
        last_bot_message = await get_last_bot_message(session)
        if last_bot_message:
            await save_feedback(last_bot_message, rating_code)
        # Create a combined message with feedback thanks and menu
        menu_text = {
            "en": f"{THANKS_FOR_FEEDBACK['en']}\n\nYou can continue asking questions below:",
            "am": f"{THANKS_FOR_FEEDBACK['am']}\n\nከዚህ በታች ጥያቄዎችን መቀጠል ይችላሉ፡"
        }
        await query.edit_message_text(
            menu_text[lang]
        )
        # Show menu keyboard in a separate message
        await context.bot.send_message(
            chat_id=telegram_id,
            text="💬",  # Use an emoji instead of empty text
            reply_markup=ReplyKeyboardMarkup(MENU_BTNS[lang], resize_keyboard=True, one_time_keyboard=False)
        )
        context.user_data['state'] = STATE_QUESTION
        return
    
    elif query.data == "FEEDBACK_SETTINGS":
        # Handle the Settings button from feedback
        keyboard = [
            [
                InlineKeyboardButton("English 🇺🇸", callback_data="LANG_CHANGE|en"),
                InlineKeyboardButton("አማርኛ 🇪🇹", callback_data="LANG_CHANGE|am"),
            ]
        ]
        settings_msg = {
            "en": "⚙️ Choose your preferred language:\n\nNote: This will change the language for all future responses.",
            "am": "⚙️ የሚፈልጉትን ቋንቋ ይምረጡ:\n\nማስታወሻ: ይህ ለወደፊቱ ሁሉም ምላሾች ቋንቋ ይቀይራል።"
        }
        await query.edit_message_text(
            settings_msg[lang],
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data['state'] = STATE_LANGUAGE_CHANGE
        return

async def handle_language_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language change from Settings menu"""
    query = update.callback_query
    await query.answer()
    telegram_id = query.from_user.id
    session = await get_user_session(telegram_id)
    
    if query.data.startswith("LANG_CHANGE|"):
        new_lang = query.data.split("|")[1]
        old_lang = session.language
        
        # Update session language while preserving all other profile data
        await set_language(session, new_lang)
        
        # Confirmation message in the NEW language
        confirmation_msg = {
            "en": f"✅ Language changed to English!\n\nYour profile settings (age, gender, interests) have been preserved. You can continue chatting normally.",
            "am": f"✅ ቋንቋ ወደ አማርኛ ተቀይሯል!\n\nየእርስዎ መገለጫ ቅንብሮች (እድሜ፣ ጾታ፣ ፍላጎቶች) ተጠብቀዋል። በመደበኛ ሁኔታ ማውራት መቀጠል ይችላሉ።"
        }
        
        await query.edit_message_text(confirmation_msg[new_lang])
        
        # Show menu in the NEW language
        await context.bot.send_message(
            chat_id=telegram_id,
            text="....",
            reply_markup=ReplyKeyboardMarkup(MENU_BTNS[new_lang], resize_keyboard=True, one_time_keyboard=False)
        )
        context.user_data['state'] = STATE_QUESTION
