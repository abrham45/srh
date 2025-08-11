import json
import logging
from typing import List, Dict, Tuple, Optional
from asgiref.sync import sync_to_async
from bot.models import ChatMessage, Emotion, EMOTION_CHOICES, EMOTION_RATING_CHOICES
from bot.gemini_api import ask_gemini

logger = logging.getLogger(__name__)

# Emotion descriptions for better AI detection
EMOTION_DESCRIPTIONS = {
    'FEAR': 'Fear, anxiety, worry, nervousness, or apprehension about health, pregnancy, STIs, or safety',
    'SHAME': 'Shame, embarrassment, guilt, or self-blame related to sexual health, experiences, or body',
    'CONFUSION': 'Confusion, uncertainty, lack of understanding, or feeling lost about sexual/reproductive health',
    'SADNESS': 'Sadness, depression, grief, disappointment, or feeling down about health or relationships',
    'ANGER': 'Anger, frustration, irritation, or feeling upset about treatment, relationships, or circumstances',
    'HELPLESSNESS': 'Helplessness, powerlessness, feeling stuck, or unable to control health/relationship situations',
    'NEUTRAL': 'Calm, neutral, matter-of-fact tone without strong emotional content'
}

def build_emotion_detection_prompt(messages: List[ChatMessage], language: str = 'en') -> str:
    """
    Build a prompt for emotion detection based on recent user messages.
    
    Args:
        messages: List of recent ChatMessage objects (user messages only)
        language: Language for the prompt ('en' or 'am')
    
    Returns:
        Formatted prompt for AI emotion detection
    """
    
    # Create message context
    message_context = ""
    for i, msg in enumerate(messages, 1):
        message_context += f"Message {i}: {msg.message}\n"
    
    # Emotion options for the prompt
    emotion_options = ""
    for code, en_label, am_label in EMOTION_CHOICES:
        description = EMOTION_DESCRIPTIONS[code]
        emotion_options += f"- {code}: {en_label} ({description})\n"
    
    if language == 'am':
        prompt = f"""
የተጠቃሚ መልእክቶችን በመተንተን ስሜቶችን ይለዩ እና ይገምግሙ።

የተጠቃሚ መልእክቶች:
{message_context}

የሚለዩ ስሜቶች:
{emotion_options}

ለእያንዳንዱ ስሜት ደረጃ ይስጡ:
- 0: የለም (ስሜቱ በፍጹም አይታይም)
- 1: መካከለኛ (ስሜቱ ትንሽ ይታያል)  
- 2: ጠንካራ (ስሜቱ በግልጽ እና በጠንካራ ሁኔታ ይታያል)

እንዲሁም በጣም ጠንካራውን ስሜት (primary_emotion) እና አጠቃላይ የመተማመኛ ደረጃ (0-1) ይስጡ።

መልስዎን በሚከተለው JSON ቅርጸት ይመልሱ:
{{
    "emotion_ratings": {{
        "FEAR": 0,
        "SHAME": 1,
        "CONFUSION": 0,
        "SADNESS": 2,
        "ANGER": 0,
        "HELPLESSNESS": 1,
        "NEUTRAL": 0
    }},
    "primary_emotion": "SADNESS",
    "confidence": 0.85,
    "reasoning": "የምርጫው ምክንያት በአማርኛ"
}}
"""
    else:
        prompt = f"""
Analyze the following user messages and detect emotions present in the conversation. Rate each emotion on a scale of 0-2.

User Messages:
{message_context}

Emotions to Detect:
{emotion_options}

Rating Scale:
- 0: Not Present (emotion is not detected in the messages)
- 1: Mild (emotion is subtly present or hinted at)
- 2: Strong (emotion is clearly and strongly expressed)

Also identify the primary (strongest) emotion and provide an overall confidence score (0-1).

Respond in the following JSON format:
{{
    "emotion_ratings": {{
        "FEAR": 0,
        "SHAME": 1,
        "CONFUSION": 0,
        "SADNESS": 2,
        "ANGER": 0,
        "HELPLESSNESS": 1,
        "NEUTRAL": 0
    }},
    "primary_emotion": "SADNESS",
    "confidence": 0.85,
    "reasoning": "Brief explanation of the emotional analysis"
}}

Important:
- Rate ALL emotions (including NEUTRAL)
- Only one emotion should be marked as primary_emotion
- Consider the overall emotional tone across all messages
- Focus on sexual and reproductive health context
- If no strong emotions are detected, NEUTRAL should have the highest rating
"""
    
    return prompt

async def detect_user_emotions(messages: List[ChatMessage], language: str = 'en') -> Optional[Dict]:
    """
    Detect user emotions based on recent messages using AI.
    
    Args:
        messages: List of recent user ChatMessage objects
        language: Language for emotion detection prompt
    
    Returns:
        Dictionary with emotion detection results or None if failed
    """
    if not messages:
        logger.warning("No messages provided for emotion detection")
        return None
    
    try:
        # Build emotion detection prompt
        prompt = build_emotion_detection_prompt(messages, language)
        
        # Get AI emotion analysis with lower temperature for consistency
        response = await ask_gemini(prompt, temperature=0.1)
        
        if not response:
            logger.error("Empty response from Gemini API for emotion detection")
            return None
        
        # Try to parse JSON response
        try:
            # Extract JSON from response (in case there's extra text)
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                logger.error("No JSON found in emotion detection response")
                return None
                
            json_str = response[start_idx:end_idx]
            emotion_result = json.loads(json_str)
            
            # Validate the response
            emotion_ratings = emotion_result.get('emotion_ratings', {})
            primary_emotion = emotion_result.get('primary_emotion')
            confidence = emotion_result.get('confidence', 0.0)
            reasoning = emotion_result.get('reasoning', '')
            
            # Validate emotion ratings
            valid_emotions = [choice[0] for choice in EMOTION_CHOICES]
            validated_ratings = {}
            
            for emotion_code in valid_emotions:
                rating = emotion_ratings.get(emotion_code, 0)
                # Ensure rating is 0, 1, or 2
                if not isinstance(rating, int) or rating < 0 or rating > 2:
                    logger.warning(f"Invalid emotion rating for {emotion_code}: {rating}")
                    rating = 0
                validated_ratings[emotion_code] = rating
            
            # Validate primary emotion
            if primary_emotion not in valid_emotions:
                # Find the emotion with highest rating as primary
                primary_emotion = max(validated_ratings, key=validated_ratings.get)
                logger.warning(f"Invalid primary emotion, defaulting to: {primary_emotion}")
            
            # Validate confidence score
            if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
                logger.warning(f"Invalid confidence score: {confidence}")
                confidence = 0.5
            
            return {
                'emotion_ratings': validated_ratings,
                'primary_emotion': primary_emotion,
                'confidence': float(confidence),
                'reasoning': reasoning,
                'raw_response': response
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from emotion detection response: {e}")
            logger.error(f"Raw response: {response}")
            return None
            
    except Exception as e:
        logger.error(f"Error during emotion detection: {e}")
        return None

@sync_to_async
def save_emotion_detection(session, emotion_ratings: Dict, primary_emotion: str, 
                          confidence: float, analysis_context: Dict, messages_count: int = 10) -> Optional[Emotion]:
    """
    Save emotion detection results to database.
    
    Args:
        session: UserSession object
        emotion_ratings: Dictionary of emotion ratings {emotion_code: rating(0-2)}
        primary_emotion: Primary emotion code
        confidence: Confidence score (0-1)
        analysis_context: Context data used for emotion detection
        messages_count: Number of messages analyzed
    
    Returns:
        Emotion object or None if failed
    """
    try:
        emotion = Emotion.objects.create(
            session=session,
            emotion_ratings=emotion_ratings,
            primary_emotion=primary_emotion,
            confidence_score=confidence,
            analysis_context=analysis_context,
            messages_analyzed=messages_count
        )
        logger.info(f"Saved emotion detection for session {session.id}: {primary_emotion} (confidence: {confidence})")
        return emotion
    except Exception as e:
        logger.error(f"Failed to save emotion detection: {e}")
        return None

@sync_to_async
def get_user_messages_for_emotion_detection(session, limit: int = 10) -> List[ChatMessage]:
    """
    Get recent user messages for emotion detection.
    
    Args:
        session: UserSession object
        limit: Number of recent messages to retrieve
    
    Returns:
        List of recent user ChatMessage objects
    """
    try:
        return list(
            ChatMessage.objects.filter(session=session, sender='user')
            .order_by('-timestamp')[:limit][::-1]  # Reverse to get chronological order
        )
    except Exception as e:
        logger.error(f"Failed to get user messages for emotion detection: {e}")
        return []

@sync_to_async
def should_perform_emotion_detection(session) -> Tuple[bool, int]:
    """
    Check if emotion detection should be performed based on message count.
    Emotion detection happens at: 5th, 20th, 80th, 320th, 1280th... conversations
    (pattern: 5 * 4^n)
    
    Args:
        session: UserSession object
    
    Returns:
        Tuple of (should_detect, total_user_messages)
    """
    try:
        # Count total user messages
        total_messages = ChatMessage.objects.filter(session=session, sender='user').count()
        
        # Count existing emotion detections
        emotions_count = Emotion.objects.filter(session=session).count()
        
        # Calculate emotion detection thresholds: 5, 20, 80, 320, 1280...
        def get_emotion_thresholds(max_messages):
            thresholds = []
            n = 0
            while True:
                threshold = 5 * (4 ** n)
                if threshold > max_messages:
                    break
                thresholds.append(threshold)
                n += 1
            return thresholds
        
        # Get all thresholds up to current message count
        thresholds = get_emotion_thresholds(total_messages)
        
        # Check if we should perform a new emotion detection
        should_detect = len(thresholds) > emotions_count
        
        if should_detect:
            next_threshold = thresholds[emotions_count]
            logger.debug(f"Session {session.id}: {total_messages} messages, "
                        f"{emotions_count} emotion detections completed, "
                        f"triggering emotion detection at {next_threshold}th message")
        else:
            logger.debug(f"Session {session.id}: {total_messages} messages, "
                        f"{emotions_count} emotion detections, no detection needed")
        
        return should_detect, total_messages
    except Exception as e:
        logger.error(f"Error checking emotion detection requirement: {e}")
        return False, 0

async def perform_emotion_detection(session, language: str = 'en') -> Optional[Emotion]:
    """
    Main function to perform emotion detection if needed.
    
    Args:
        session: UserSession object
        language: Language for emotion detection
    
    Returns:
        Emotion object if performed, None otherwise
    """
    try:
        # Check if emotion detection is needed
        should_detect, total_messages = await should_perform_emotion_detection(session)
        
        if not should_detect:
            return None
        
        # Get recent user messages for analysis (adjust limit based on total messages available)
        messages_limit = min(total_messages, 10)
        messages = await get_user_messages_for_emotion_detection(session, limit=messages_limit)
        
        if not messages:
            logger.warning(f"No user messages found for emotion detection in session {session.id}")
            return None
        
        # Perform emotion detection
        emotion_result = await detect_user_emotions(messages, language)
        
        if not emotion_result:
            logger.error(f"Emotion detection failed for session {session.id}")
            return None
        
        # Prepare context for saving
        analysis_context = {
            'messages_analyzed': [
                {
                    'id': str(msg.id),
                    'message': msg.message,
                    'timestamp': msg.timestamp.isoformat(),
                    'language': msg.language
                }
                for msg in messages
            ],
            'emotion_result': emotion_result,
            'total_user_messages': total_messages
        }
        
        # Save emotion detection
        emotion = await save_emotion_detection(
            session=session,
            emotion_ratings=emotion_result['emotion_ratings'],
            primary_emotion=emotion_result['primary_emotion'],
            confidence=emotion_result['confidence'],
            analysis_context=analysis_context,
            messages_count=len(messages)
        )
        
        return emotion
        
    except Exception as e:
        logger.error(f"Error performing emotion detection: {e}")
        return None

