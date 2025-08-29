"""
Simple homosexuality question detection.
Detects questions about homosexuality using user gender and question content.
"""

import logging
import re
from typing import Tuple

logger = logging.getLogger(__name__)

def is_homosexual_question(text: str, user_gender: str, language: str = 'en') -> bool:
    """
    Simple detection: Check if user is asking about same-gender topics.
    
    Args:
        text: User input text
        user_gender: User's gender ('M' for Male, 'F' for Female)
        language: Language of the text ('en' or 'am')
    
    Returns:
        True if homosexual question, False otherwise
    """
    if not text or not user_gender:
        return False
    
    text_lower = text.lower()
    
    # Basic homosexuality keywords (always detected regardless of gender)
    homo_keywords = {
        'en': ['homosexual', 'homosexuality', 'gay', 'lesbian', 'lgbt', 'lgbtq', 'same-sex', 'queer'],
        'am': ['ግብረ-ሰዶማዊነት', 'ግብረሰዶማዊነት', 'ግብረ ሰዶማዊነት']
    }
    
    keywords = homo_keywords.get(language, [])
    for keyword in keywords:
        if keyword.lower() in text_lower:
            return True
    
    # Gender-specific detection
    if language == 'en':
        if user_gender == 'M':  # Male asking about males
            male_patterns = [
                r'\bi\s+(want|love|like|am\s+attracted\s+to)\s+(a\s+)?(man|men|male|boy|guy)',
                r'\bi\s+(want\s+to\s+)?have\s+sex\s+with\s+(a\s+)?(man|men|male|boy|guy)',
                r'\bi\s+(want\s+to\s+)?date\s+(a\s+)?(man|men|male|boy|guy)',
                r'\bi\s+(want\s+to\s+)?have\s+(male|man|men)\s+(sex|intercourse)'
            ]
            for pattern in male_patterns:
                if re.search(pattern, text_lower):
                    return True
                    
        elif user_gender == 'F':  # Female asking about females
            female_patterns = [
                r'\bi\s+(want|love|like|am\s+attracted\s+to)\s+(a\s+)?(woman|women|female|girl|lady)',
                r'\bi\s+(want\s+to\s+)?have\s+sex\s+with\s+(a\s+)?(woman|women|female|girl|lady)',
                r'\bi\s+(want\s+to\s+)?date\s+(a\s+)?(woman|women|female|girl|lady)',
                r'\bi\s+(want\s+to\s+)?have\s+(female|woman|women)\s+(sex|intercourse)'
            ]
            for pattern in female_patterns:
                if re.search(pattern, text_lower):
                    return True
    
    elif language == 'am':
        if user_gender == 'M':  # Male asking about males in Amharic
            if re.search(r'\bወንድ.*(እወዳለሁ|ወሲብ|ግንኙነት|ፍቅር)', text_lower):
                return True
        elif user_gender == 'F':  # Female asking about females in Amharic
            if re.search(r'\bሴት.*(እወዳለሁ|ወሲብ|ግንኙነት|ፍቅር)', text_lower):
                return True
    
    return False

def get_rejection_response(language: str = 'en') -> str:
    """
    Get simple rejection response.
    """
    responses = {
        'en': "I don't answer any homosexual question. It is against Ethiopian culture.",
        'am': "ስለ ግብረ-ሰዶማዊነት ጥያቄዎችን አልመልስም። ይህ የኢትዮጵያ ባህልን ይቃረናል።"
    }
    return responses.get(language, responses['en'])