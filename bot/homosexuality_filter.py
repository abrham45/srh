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

def detect_homosexuality_question(text: str, language: str = 'en', user_gender: str = None) -> Tuple[bool, str]:
    """
    Detect if a question is about homosexuality.
    
    Args:
        text: User input text
        language: Language of the text ('en' or 'am')
        user_gender: User's gender ('M' for Male, 'F' for Female)
    
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
    
    # Gender-aware detection
    if user_gender:
        is_homosexual, reason = detect_same_gender_attraction(text, language, user_gender)
        if is_homosexual:
            return True, reason
    else:
        # Fallback: detect general same-gender expressions when gender is unknown
        logger.warning(f"No user gender available for homosexuality detection, using fallback patterns")
        is_homosexual, reason = detect_general_same_gender_expressions(text, language)
        if is_homosexual:
            return True, reason
    
    return False, ""

def detect_general_same_gender_expressions(text: str, language: str) -> Tuple[bool, str]:
    """
    Fallback detection for same-gender expressions when user gender is unknown.
    Uses more general patterns that don't require gender context.
    """
    text_lower = text.lower()
    
    if language == 'en':
        # General same-gender patterns (more cautious)
        fallback_patterns = [
            r'\b(man|men)\s+(with|and|having\s+sex\s+with)\s+(man|men)\b',
            r'\b(woman|women)\s+(with|and|having\s+sex\s+with)\s+(woman|women)\b',
            r'\bsex\s+with\s+(same|another)\s+(man|woman|gender)\b',
            r'\bhomosexual\s+(sex|activity|behavior|relationship)\b',
            r'\bgay\s+(sex|relationship|couple|partner)\b',
            r'\blesbian\s+(sex|relationship|couple|partner)\b',
            # More suspicious patterns when gender is unknown
            r'\bi\s+(want|need)\s+(to\s+)?have\s+sex\s+with\s+(man|men)\b.*\b(too|also|as\s+well)\b',
            r'\bi\s+(want|need)\s+(to\s+)?have\s+sex\s+with\s+(woman|women)\b.*\b(too|also|as\s+well)\b',
            r'\bsame\s+(sex|gender)\s+(attraction|desire|love|relationship)\b',
            r'\bhomosexual\s+(desire|urge|feeling|thought)\b'
        ]
        
        for pattern in fallback_patterns:
            if re.search(pattern, text_lower):
                logger.info(f"General same-gender pattern detected: '{pattern}' in text")
                return True, f"fallback_pattern: {pattern}"
    
    elif language == 'am':
        # Amharic fallback patterns
        fallback_patterns_am = [
            r'\bወንድ\s+ከ\s*ወንድ\s+ጋር\s+(ወሲብ|ግንኙነት)\b',
            r'\bሴት\s+ከ\s*ሴት\s+ጋር\s+(ወሲብ|ግንኙነት)\b',
            r'\bተመሳሳይ\s+ጾታ\s+(ወሲብ|ግንኙነት)\b',
            r'\bግብረሰዶማዊ\s+(ወሲብ|ግንኙነት|ስሜት)\b'
        ]
        
        for pattern in fallback_patterns_am:
            if re.search(pattern, text_lower):
                logger.info(f"General same-gender pattern detected (Amharic): '{pattern}' in text")
                return True, f"fallback_pattern_am: {pattern}"
    
    return False, ""

def detect_same_gender_attraction(text: str, language: str, user_gender: str) -> Tuple[bool, str]:
    """
    Detect same-gender attraction based on user's gender and their statements.
    
    Args:
        text: User input text
        language: Language of the text
        user_gender: User's gender ('M' for Male, 'F' for Female)
    
    Returns:
        Tuple of (is_same_gender_attraction, detection_reason)
    """
    text_lower = text.lower()
    
    if language == 'en':
        if user_gender == 'M':  # Male user
            # Male expressing attraction/activity with males
            male_patterns = [
                r'\bi\s+(want|like|love|am\s+attracted\s+to)\s+.*\b(men|man|male|boy|boys|guy|guys)\b',
                r'\bhave\s+sex\s+with\s+(men|man|male|boy|boys|guy|guys)\b',
                r'\bsex\s+with\s+(men|man|male|boy|boys|guy|guys)\b',
                r'\b(date|dating|kiss|kissing)\s+(men|man|male|boy|boys|guy|guys)\b',
                r'\b(attracted|attraction)\s+to\s+(men|man|male|boy|boys|guy|guys)\b',
                r'\bmy\s+(boyfriend|partner)\s+is\s+(male|man|boy)\b'
            ]
            for pattern in male_patterns:
                if re.search(pattern, text_lower):
                    logger.info(f"Male-male attraction detected: '{pattern}' in text")
                    return True, f"male_attraction: {pattern}"
                    
        elif user_gender == 'F':  # Female user
            # Female expressing attraction/activity with females
            female_patterns = [
                r'\bi\s+(want|like|love|am\s+attracted\s+to)\s+.*\b(women|woman|female|girl|girls|lady|ladies)\b',
                r'\bhave\s+sex\s+with\s+(women|woman|female|girl|girls|lady|ladies)\b',
                r'\bsex\s+with\s+(women|woman|female|girl|girls|lady|ladies)\b',
                r'\b(date|dating|kiss|kissing)\s+(women|woman|female|girl|girls|lady|ladies)\b',
                r'\b(attracted|attraction)\s+to\s+(women|woman|female|girl|girls|lady|ladies)\b',
                r'\bmy\s+(girlfriend|partner)\s+is\s+(female|woman|girl)\b'
            ]
            for pattern in female_patterns:
                if re.search(pattern, text_lower):
                    logger.info(f"Female-female attraction detected: '{pattern}' in text")
                    return True, f"female_attraction: {pattern}"
    
    elif language == 'am':
        if user_gender == 'M':  # Male user
            # Male expressing attraction/activity with males in Amharic
            male_patterns_am = [
                r'\bወንድ\s+.*\s+(መውደድ|ፍቅር|ወሲብ)\b',
                r'\bወንዶች\s+.*\s+(መውደድ|ፍቅር|ወሲብ)\b',
                r'\bከ\s*ወንድ\s+ጋር\s+(ወሲብ|ፍቅር|ግንኙነት)\b',
                r'\bወንድ\s+ከ\s*ወንድ\s+ጋር\b',
                r'\bእኔ\s+.*\s+ወንድ\s+.*\s+(እወዳለሁ|እፈልጋለሁ)\b',
                r'\bወንድ\s+(እወዳለሁ|እፈልጋለሁ|መውደድ)\b',
                r'\bወንዶች\s+(እወዳለሁ|እፈልጋለሁ|መውደድ)\b'
            ]
            for pattern in male_patterns_am:
                if re.search(pattern, text_lower):
                    logger.info(f"Male-male attraction detected (Amharic): '{pattern}' in text")
                    return True, f"male_attraction_am: {pattern}"
                    
        elif user_gender == 'F':  # Female user
            # Female expressing attraction/activity with females in Amharic
            female_patterns_am = [
                r'\bሴት\s+.*\s+(መውደድ|ፍቅር|ወሲብ)\b',
                r'\bሴቶች\s+.*\s+(መውደድ|ፍቅር|ወሲብ)\b',
                r'\bከ\s*ሴት\s+ጋር\s+(ወሲብ|ፍቅር|ግንኙነት)\b',
                r'\bሴት\s+ከ\s*ሴት\s+ጋር\b',
                r'\bእኔ\s+.*\s+ሴት\s+.*\s+(እወዳለሁ|እፈልጋለሁ)\b',
                r'\bሴት\s+(እወዳለሁ|እፈልጋለሁ|መውደድ)\b',
                r'\bሴቶች\s+(እወዳለሁ|እፈልጋለሁ|መውደድ)\b'
            ]
            for pattern in female_patterns_am:
                if re.search(pattern, text_lower):
                    logger.info(f"Female-female attraction detected (Amharic): '{pattern}' in text")
                    return True, f"female_attraction_am: {pattern}"
    
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

def should_reject_question(text: str, language: str = 'en', user_gender: str = None) -> Tuple[bool, str]:
    """
    Main function to check if a question should be rejected due to homosexuality content.
    
    Args:
        text: User input text
        language: Language of the text
        user_gender: User's gender ('M' for Male, 'F' for Female)
    
    Returns:
        Tuple of (should_reject, rejection_message)
    """
    is_homosexuality, reason = detect_homosexuality_question(text, language, user_gender)
    
    if is_homosexuality:
        rejection_message = get_homosexuality_rejection_response(language)
        logger.info(f"Rejecting homosexuality question. Reason: {reason}")
        return True, rejection_message
    
    return False, ""
