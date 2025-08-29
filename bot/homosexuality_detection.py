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
    
    # Simple prompt - just ask Gemini directly
    user_gender_text = "Male" if user_gender == 'M' else "Female"
    
    classification_prompt = f"""
User is {user_gender_text}.
Question: "{question}"

Is this question about homosexuality? Answer only YES or NO.

YES = Question is about same-gender attraction, relationships, or sexual activity
NO = Everything else (opposite-gender, health topics, general conversation, etc.)

Answer:"""

    try:
        # Ask AI to classify the question
        response = await ask_gemini(classification_prompt)
        response_text = response.strip().upper()
        
        logger.info(f"AI Classification - Question: '{question}' | Gender: {user_gender} | Result: {response_text}")
        
        # Return True if AI says YES
        return "YES" in response_text
        
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
