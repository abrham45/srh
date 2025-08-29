"""
AI-based homosexuality question detection.
Uses Gemini AI to classify if a question is about homosexuality.
"""

import logging
from bot.gemini_api import ask_gemini

logger = logging.getLogger(__name__)

async def is_homosexual_question_ai(question: str, user_gender: str, language: str = 'en') -> bool:
    """
    Use AI to detect if a question is about homosexuality.
    
    Args:
        question: User's question
        user_gender: User's gender ('M' or 'F')
        language: Language of the question
    
    Returns:
        True if the question is about homosexuality, False otherwise
    """
    if not question or not user_gender:
        return False
    
    # Create classification prompt for the AI
    user_gender_text = "Male" if user_gender == 'M' else "Female"
    
    # Determine what should be homosexual for this user
    if user_gender == 'M':
        homosexual_targets = "males, men, boys, guys"
        heterosexual_targets = "females, women, girls, ladies"
    else:
        homosexual_targets = "females, women, girls, ladies"
        heterosexual_targets = "males, men, boys, guys"
    
    # Simple classification prompt
    if user_gender == 'M':
        same_gender_words = ["man", "men", "male", "boy", "guy"]
        opposite_gender_words = ["woman", "women", "female", "girl", "lady"]
    else:
        same_gender_words = ["woman", "women", "female", "girl", "lady"]
        opposite_gender_words = ["man", "men", "male", "boy", "guy"]
    
    classification_prompt = f"""
Question: "{question}"
User: {user_gender_text}

Is this {user_gender_text} asking for sexual/romantic attraction to their own gender?

Check:
- Does question mention sex, sexual attraction, or romance?
- Does it mention {', '.join(same_gender_words)}?
- Is it about personal desire/attraction?

If YES to all three: Answer HOMOSEXUAL
If NO to any: Answer NOT_HOMOSEXUAL

Examples:
- "{user_gender_text} wants sex with {same_gender_words[0]}" = HOMOSEXUAL
- "{user_gender_text} wants sex with {opposite_gender_words[0]}" = NOT_HOMOSEXUAL
- "What is family planning?" = NOT_HOMOSEXUAL
- "Hello" = NOT_HOMOSEXUAL

Answer:"""

    try:
        # Ask AI to classify the question
        response = await ask_gemini(classification_prompt)
        response_text = response.strip().upper()
        
        logger.info(f"AI Classification - Question: '{question}' | Gender: {user_gender} | Result: {response_text}")
        
        # Return True if AI classifies it as homosexual
        return "HOMOSEXUAL" in response_text
        
    except Exception as e:
        logger.error(f"Error in AI homosexuality detection: {e}")
        # Fallback: assume not homosexual if AI fails
        return False

def get_rejection_response(language: str = 'en') -> str:
    """
    Get rejection response for homosexual questions.
    """
    responses = {
        'en': "I don't answer any homosexual question. It is against Ethiopian culture.",
        'am': "ስለ ግብረ-ሰዶማዊነት ጥያቄዎችን አልመልስም። ይህ የኢትዮጵያ ባህልን ይቃረናል።"
    }
    return responses.get(language, responses['en'])
