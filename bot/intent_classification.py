import json
import logging
from typing import List, Dict, Tuple, Optional
from asgiref.sync import sync_to_async
from bot.models import ChatMessage, Classification, INTENT_CHOICES
from bot.gemini_api import ask_gemini

logger = logging.getLogger(__name__)

# Intent descriptions for better AI classification
INTENT_DESCRIPTIONS = {
    'ASK_INFO': 'User is asking for information, facts, explanations, or knowledge about sexual and reproductive health topics',
    'ASK_ACTION': 'User is asking for specific help, actions to take, recommendations, or requesting assistance with a problem',
    'REPORT_INCIDENT': 'User is reporting an incident, abuse, assault, harassment, or describing a harmful experience',
    'EXPRESS_EMOTION': 'User is primarily expressing emotions, feelings, concerns, fears, anxiety, or emotional distress',
    'ASK_CONFIDENTIALITY': 'User is asking about privacy, confidentiality, or expressing concerns about information being shared',
    'SEEK_VALIDATION': 'User is seeking reassurance, validation, confirmation that their feelings/experiences are normal or valid',
    'REFUSE_HELP': 'User is declining help, refusing assistance, or expressing that they don\'t want support',
    'OTHER': 'Message doesn\'t clearly fit into other categories or contains mixed/unclear intent'
}

def build_classification_prompt(messages: List[ChatMessage], language: str = 'en') -> str:
    """
    Build a prompt for intent classification based on recent user messages.
    
    Args:
        messages: List of recent ChatMessage objects (user messages only)
        language: Language for the prompt ('en' or 'am')
    
    Returns:
        Formatted prompt for AI classification
    """
    
    # Create message context
    message_context = ""
    for i, msg in enumerate(messages, 1):
        message_context += f"Message {i}: {msg.message}\n"
    
    # Intent choices for the prompt
    intent_options = ""
    for code, en_label, am_label in INTENT_CHOICES:
        description = INTENT_DESCRIPTIONS[code]
        intent_options += f"- {code}: {en_label} ({description})\n"
    
    if language == 'am':
        prompt = f"""
የተጠቃሚ መልእክቶችን በመተንተን የዋናውን ዓላማ (intent) ይለዩ።

የተጠቃሚ መልእክቶች:
{message_context}

የሚቻሉ ዓላማዎች:
{intent_options}

እባክዎ የተጠቃሚውን ዋና ዓላማ ይለዩ እና ከ0-1 መካከል የመተማመኛ ደረጃ ይስጡ።

መልስዎን በሚከተለው JSON ቅርጸት ይመልሱ:
{{
    "intent": "INTENT_CODE",
    "confidence": 0.85,
    "reasoning": "የምርጫው ምክንያት በአማርኛ"
}}
"""
    else:
        prompt = f"""
Analyze the following user messages and classify the primary intent of the conversation.

User Messages:
{message_context}

Available Intent Categories:
{intent_options}

Based on the messages above, determine the user's primary intent and provide a confidence score between 0-1.

Respond in the following JSON format:
{{
    "intent": "INTENT_CODE",
    "confidence": 0.85,
    "reasoning": "Brief explanation of why this intent was chosen"
}}

Important:
- Consider the overall pattern across all messages
- If multiple intents are present, choose the most prominent one
- Provide confidence based on how clear the intent is
- Focus on sexual and reproductive health context
"""
    
    return prompt

async def classify_user_intent(messages: List[ChatMessage], language: str = 'en') -> Optional[Dict]:
    """
    Classify user intent based on recent messages using AI.
    
    Args:
        messages: List of recent user ChatMessage objects
        language: Language for classification prompt
    
    Returns:
        Dictionary with classification results or None if failed
    """
    if not messages:
        logger.warning("No messages provided for intent classification")
        return None
    
    try:
        # Build classification prompt
        prompt = build_classification_prompt(messages, language)
        
        # Get AI classification with lower temperature for consistency
        response = await ask_gemini(prompt, temperature=0.1)
        
        if not response:
            logger.error("Empty response from Gemini API for intent classification")
            return None
        
        # Try to parse JSON response
        try:
            # Extract JSON from response (in case there's extra text)
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                logger.error("No JSON found in classification response")
                return None
                
            json_str = response[start_idx:end_idx]
            classification_result = json.loads(json_str)
            
            # Validate the response
            intent_code = classification_result.get('intent')
            confidence = classification_result.get('confidence', 0.0)
            reasoning = classification_result.get('reasoning', '')
            
            # Validate intent code
            valid_intents = [choice[0] for choice in INTENT_CHOICES]
            if intent_code not in valid_intents:
                logger.warning(f"Invalid intent code received: {intent_code}")
                intent_code = 'OTHER'
            
            # Validate confidence score
            if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
                logger.warning(f"Invalid confidence score: {confidence}")
                confidence = 0.5
            
            return {
                'intent': intent_code,
                'confidence': float(confidence),
                'reasoning': reasoning,
                'raw_response': response
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from classification response: {e}")
            logger.error(f"Raw response: {response}")
            return None
            
    except Exception as e:
        logger.error(f"Error during intent classification: {e}")
        return None

@sync_to_async
def save_classification(session, intent_code: str, confidence: float, 
                       analysis_context: Dict, messages_count: int = 10) -> Optional[Classification]:
    """
    Save classification results to database.
    
    Args:
        session: UserSession object
        intent_code: Classified intent code
        confidence: Confidence score (0-1)
        analysis_context: Context data used for classification
        messages_count: Number of messages analyzed
    
    Returns:
        Classification object or None if failed
    """
    try:
        classification = Classification.objects.create(
            session=session,
            intent=intent_code,
            confidence_score=confidence,
            analysis_context=analysis_context,
            messages_analyzed=messages_count
        )
        logger.info(f"Saved classification for session {session.id}: {intent_code} (confidence: {confidence})")
        return classification
    except Exception as e:
        logger.error(f"Failed to save classification: {e}")
        return None

@sync_to_async
def get_user_messages_for_classification(session, limit: int = 10) -> List[ChatMessage]:
    """
    Get recent user messages for intent classification.
    
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
        logger.error(f"Failed to get user messages for classification: {e}")
        return []

@sync_to_async
def should_perform_classification(session) -> Tuple[bool, int]:
    """
    Check if classification should be performed based on message count.
    Classifications happen at: 5th, 10th, 20th, 40th, 80th, 160th... conversations
    (doubling pattern starting from 5)
    
    Args:
        session: UserSession object
    
    Returns:
        Tuple of (should_classify, total_user_messages)
    """
    try:
        # Count total user messages
        total_messages = ChatMessage.objects.filter(session=session, sender='user').count()
        
        # Count existing classifications
        classifications_count = Classification.objects.filter(session=session).count()
        
        # Calculate classification thresholds: 5, 10, 20, 40, 80, 160, 320...
        def get_classification_thresholds(max_messages):
            thresholds = []
            threshold = 5
            while threshold <= max_messages:
                thresholds.append(threshold)
                threshold *= 2
            return thresholds
        
        # Get all thresholds up to current message count
        thresholds = get_classification_thresholds(total_messages)
        
        # Check if we should perform a new classification
        should_classify = len(thresholds) > classifications_count
        
        if should_classify:
            next_threshold = thresholds[classifications_count]
            logger.debug(f"Session {session.id}: {total_messages} messages, "
                        f"{classifications_count} classifications completed, "
                        f"triggering classification at {next_threshold}th message")
        else:
            logger.debug(f"Session {session.id}: {total_messages} messages, "
                        f"{classifications_count} classifications, no classification needed")
        
        return should_classify, total_messages
    except Exception as e:
        logger.error(f"Error checking classification requirement: {e}")
        return False, 0

async def perform_intent_classification(session, language: str = 'en') -> Optional[Classification]:
    """
    Main function to perform intent classification if needed.
    
    Args:
        session: UserSession object
        language: Language for classification
    
    Returns:
        Classification object if performed, None otherwise
    """
    try:
        # Check if classification is needed
        should_classify, total_messages = await should_perform_classification(session)
        
        if not should_classify:
            return None
        
        # Get recent user messages for analysis (adjust limit based on total messages available)
        messages_limit = min(total_messages, 10)
        messages = await get_user_messages_for_classification(session, limit=messages_limit)
        
        if not messages:
            logger.warning(f"No user messages found for classification in session {session.id}")
            return None
        
        # Perform classification
        classification_result = await classify_user_intent(messages, language)
        
        if not classification_result:
            logger.error(f"Classification failed for session {session.id}")
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
            'classification_result': classification_result,
            'total_user_messages': total_messages
        }
        
        # Save classification
        classification = await save_classification(
            session=session,
            intent_code=classification_result['intent'],
            confidence=classification_result['confidence'],
            analysis_context=analysis_context,
            messages_count=len(messages)
        )
        
        return classification
        
    except Exception as e:
        logger.error(f"Error performing intent classification: {e}")
        return None
