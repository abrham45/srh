"""
Homosexuality question detection and filtering.
Detects questions about homosexuality and provides appropriate rejections.
"""

import logging
import re
from typing import Tuple

logger = logging.getLogger(__name__)

# Keywords and patterns to detect homosexuality questions
HOMOSEXUALITY_KEYWORDS = {
    'en': [
        'homosexual', 'homosexuality', 'gay', 'lesbian', 'lgbtq', 'lgbt', 
        'same-sex', 'same sex', 'queer', 'bisexual', 'transgender', 'trans',
        'pride', 'rainbow flag', 'coming out', 'sexual orientation',
        'gender identity', 'non-binary', 'pansexual', 'asexual'
    ],
    'am': [
        'ግብረ-ሰዶማዊነት', 'ግብረሰዶማዊነት', 'ግብረ ሰዶማዊነት', 'ሰዶማዊነት',
        'ወንድ ከወንድ', 'ሴት ከሴት', 'ተመሳሳይ ጾታ', 'የተመሳሳይ ጾታ',
        'ግብረሰዶማዊ', 'ግብረ-ሰዶማዊ', 'ወንድ ጋር ወንድ', 'ሴት ጋር ሴት'
    ]
}

# Pattern-based detection (more flexible)
HOMOSEXUALITY_PATTERNS = {
    'en': [
        r'\b(man|men)\s+(with|and|love|loves|loving)\s+(man|men)\b',
        r'\b(woman|women)\s+(with|and|love|loves|loving)\s+(woman|women)\b',
        r'\b(boy|boys)\s+(with|and|love|loves|loving)\s+(boy|boys)\b',
        r'\b(girl|girls)\s+(with|and|love|loves|loving)\s+(girl|girls)\b',
        r'\bmale\s+(with|and|love|loves|loving)\s+male\b',
        r'\bfemale\s+(with|and|love|loves|loving)\s+female\b',
        r'\bcan\s+(men|man)\s+(love|date|marry)\s+(men|man)\b',
        r'\bcan\s+(women|woman)\s+(love|date|marry)\s+(women|woman)\b',
        r'\bi\s+am\s+(gay|lesbian|bisexual|trans)\b',
        r'\bmy\s+(boyfriend|girlfriend)\s+is\s+(gay|lesbian)\b',
        r'\battracted\s+to\s+(same|men|women)\b.*\b(as|like)\s+me\b'
    ],
    'am': [
        r'\bወንድ\s+(ከ|ጋር|እና)\s+ወንድ\b',
        r'\bሴት\s+(ከ|ጋር|እና)\s+ሴት\b',
        r'\bወንዶች\s+(ከ|ጋር|እና)\s+ወንዶች\b',
        r'\bሴቶች\s+(ከ|ጋር|እና)\s+ሴቶች\b',
        r'\bእኔ\s+.*\s+(ግብረሰዶማዊ|ግብረ-ሰዶማዊ)\b',
        r'\bወንድ\s+.*\s+ወንድ\s+.*\s+(ፍቅር|ወሲብ|ግንኙነት)\b',
        r'\bሴት\s+.*\s+ሴት\s+.*\s+(ፍቅር|ወሲብ|ግንኙነት)\b'
    ]
}

def detect_homosexuality_question(text: str, language: str = 'en') -> Tuple[bool, str]:
    """
    Detect if a question is about homosexuality.
    
    Args:
        text: User input text
        language: Language of the text ('en' or 'am')
    
    Returns:
        Tuple of (is_homosexuality_question, detection_reason)
    """
    if not text:
        return False, ""
    
    text_lower = text.lower()
    
    # Check keywords
    keywords = HOMOSEXUALITY_KEYWORDS.get(language, [])
    for keyword in keywords:
        if keyword.lower() in text_lower:
            logger.info(f"Homosexuality keyword detected: '{keyword}' in text")
            return True, f"keyword: {keyword}"
    
    # Check patterns
    patterns = HOMOSEXUALITY_PATTERNS.get(language, [])
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            logger.info(f"Homosexuality pattern detected: '{pattern}' in text")
            return True, f"pattern: {pattern}"
    
    return False, ""

def get_homosexuality_rejection_response(language: str = 'en') -> str:
    """
    Get appropriate rejection response for homosexuality questions.
    
    Args:
        language: Response language ('en' or 'am')
    
    Returns:
        Rejection message
    """
    responses = {
        'en': (
            "I cannot answer questions about homosexuality. "
            "I'm designed to provide information about traditional sexual and reproductive health topics "
            "within Ethiopian cultural and religious values. "
            "If you have questions about family planning, marriage, or other traditional health topics, "
            "I'm here to help with those."
        ),
        'am': (
            "ስለ ግብረ-ሰዶማዊነት ጥያቄዎችን መመለስ አልችልም። "
            "እኔ በኢትዮጵያ ባህላዊ እና ሃይማኖታዊ እሴቶች ውስጥ ስለ ባህላዊ ስነተዋልዶ ጤና ርዕሶች "
            "መረጃ ለመስጠት የተዘጋጀሁ ነኝ። "
            "ስለ የቤተሰብ እቅድ፣ ጋብቻ፣ ወይም ሌሎች ባህላዊ የጤና ርዕሶች ጥያቄዎች ካለዎት፣ "
            "እነዚያን ለመርዳት እዚህ ነኝ።"
        )
    }
    
    return responses.get(language, responses['en'])

def should_reject_question(text: str, language: str = 'en') -> Tuple[bool, str]:
    """
    Main function to check if a question should be rejected due to homosexuality content.
    
    Args:
        text: User input text
        language: Language of the text
    
    Returns:
        Tuple of (should_reject, rejection_message)
    """
    is_homosexuality, reason = detect_homosexuality_question(text, language)
    
    if is_homosexuality:
        rejection_message = get_homosexuality_rejection_response(language)
        logger.info(f"Rejecting homosexuality question. Reason: {reason}")
        return True, rejection_message
    
    return False, ""
