import asyncio
import logging
import httpx
import json
from django.conf import settings
from asgiref.sync import sync_to_async
from .models import MythAssessment, ChatMessage

logger = logging.getLogger(__name__)

def should_perform_myth_detection(total_messages):
    """
    Determine if myth detection should be performed.
    We'll run it more frequently than risk assessment since myths are educational opportunities.
    Pattern: Every 2 messages starting from the 2nd message (2nd, 4th, 6th, 8th...)
    """
    if total_messages < 2:
        return False
    
    # Run on every 2nd message 
    return total_messages % 2 == 0

@sync_to_async
def get_user_messages_for_myth_detection(session, total_messages):
    """
    Retrieve recent user messages for myth detection analysis.
    We'll analyze fewer messages than risk assessment since myths are usually in individual messages.
    """
    limit = min(total_messages, 5)  # Analyze recent 5 messages max
    
    messages = ChatMessage.objects.filter(
        session=session, 
        sender='user'
    ).order_by('-timestamp')[:limit]
    
    return [msg.message for msg in reversed(messages)]

@sync_to_async
def get_latest_user_message(session):
    """
    Get the most recent user message for myth detection.
    """
    try:
        latest_message = ChatMessage.objects.filter(
            session=session, 
            sender='user'
        ).order_by('-timestamp').first()
        return latest_message
    except:
        return None

@sync_to_async
def save_myth_assessment(session, message, myth_type, confidence_score=None, 
                        myth_detected=False, specific_myth=None, severity_level=None, 
                        correction_provided=False, analysis_context=None):
    """
    Save myth assessment results to database.
    """
    assessment = MythAssessment.objects.create(
        session=session,
        message=message,
        myth_type=myth_type,
        confidence_score=confidence_score,
        myth_detected=myth_detected,
        specific_myth=specific_myth,
        severity_level=severity_level,
        correction_provided=correction_provided,
        analysis_context=analysis_context
    )
    return assessment

async def analyze_myths_with_gemini(messages, session_language):
    """
    Use Gemini AI to detect myths and misconceptions in user messages.
    """
    try:
        # Construct the myth detection prompt
        prompt = f"""
You are an AI myth detection specialist for sexual and reproductive health (SRH) conversations. 
Analyze the following user messages for myths, misconceptions, and misinformation.

CATEGORIES TO DETECT:

CULTURAL/TRADITIONAL MYTHS:
- CULTURAL_HYMEN: Beliefs about hymens proving virginity
- CULTURAL_MENSTRUATION: Traditional taboos about menstruation 
- CULTURAL_FERTILITY: Cultural beliefs about fertility/infertility
- CULTURAL_PREGNANCY: Traditional pregnancy beliefs
- CULTURAL_CONTRACEPTION: Cultural myths about contraception

MEDICAL MISCONCEPTIONS:
- MEDICAL_CONTRACEPTION: Wrong medical facts about contraception
- MEDICAL_STI: Incorrect information about STI/HIV transmission/prevention
- MEDICAL_PREGNANCY: Medical misinformation about pregnancy
- MEDICAL_ANATOMY: Wrong understanding of sexual/reproductive anatomy
- MEDICAL_PUBERTY: Misconceptions about puberty and development
- MEDICAL_MENSTRUATION: Medical misinformation about menstrual health

NO_MYTH: No myths or misconceptions detected

DETECTION GUIDELINES:
1. Look for statements that contain factually incorrect information
2. Identify cultural beliefs that may contradict medical evidence
3. Focus on SRH-related myths only
4. Consider Ethiopian cultural context
5. Differentiate between cultural myths (harder to correct) and medical misconceptions (easier to educate)
6. Assess severity based on potential health impact

COMMON ETHIOPIAN SRH MYTHS TO WATCH FOR:
- Hymen/virginity misconceptions
- Menstrual taboos and restrictions
- Contraception side effects fears
- STI transmission myths
- Pregnancy and birth beliefs
- Fertility misconceptions

USER MESSAGES:
{chr(10).join([f"Message {i+1}: {msg}" for i, msg in enumerate(messages)])}

SESSION LANGUAGE: {session_language}

RESPONSE FORMAT (JSON):
{{
    "myth_detected": true/false,
    "myth_type": "CATEGORY_CODE",
    "confidence_score": 0.0-1.0,
    "specific_myth": "Brief description of the specific myth/misconception detected",
    "severity_level": "LOW|MEDIUM|HIGH|CRITICAL",
    "cultural_sensitivity_needed": true/false,
    "correction_approach": "gentle|educational|medical_facts",
    "analysis_summary": "Brief explanation of what was detected"
}}

Be thorough but not overly sensitive. Focus on genuine myths and misconceptions rather than general questions.
"""

        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
        headers = {
            "Content-Type": "application/json",
        }
        
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,  # Low temperature for consistent myth detection
                "topK": 1,
                "topP": 0.8,
                "maxOutputTokens": 800,
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{url}?key={settings.GEMINI_API_KEY}",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['candidates'][0]['content']['parts'][0]['text']
                
                # Try to parse JSON response
                try:
                    # Clean up the response to extract JSON
                    json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    if json_start != -1 and json_end != -1:
                        json_content = content[json_start:json_end]
                        myth_data = json.loads(json_content)
                        return myth_data
                    else:
                        logger.error(f"No valid JSON found in Gemini myth detection response: {content}")
                        return None
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Gemini myth detection JSON: {e}")
                    logger.error(f"Raw content: {content}")
                    return None
            else:
                logger.error(f"Gemini API error for myth detection: {response.status_code} - {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"Myth detection analysis failed: {e}")
        return None

async def perform_myth_detection(session, total_messages):
    """
    Main function to perform myth detection for a user session.
    """
    try:
        if not should_perform_myth_detection(total_messages):
            return
        
        logger.info(f"Performing myth detection for session {session.id} at message {total_messages}")
        
        # Get recent user messages
        messages = await get_user_messages_for_myth_detection(session, total_messages)
        
        if not messages:
            logger.warning(f"No messages found for myth detection - session {session.id}")
            return
        
        # Get the latest message object for linking
        latest_message = await get_latest_user_message(session)
        if not latest_message:
            logger.warning(f"Could not find latest message for myth detection - session {session.id}")
            return
        
        # Analyze with Gemini
        myth_data = await analyze_myths_with_gemini(messages, session.language)
        
        if myth_data:
            # Save to database
            assessment = await save_myth_assessment(
                session=session,
                message=latest_message,
                myth_type=myth_data.get('myth_type', 'NO_MYTH'),
                confidence_score=myth_data.get('confidence_score'),
                myth_detected=myth_data.get('myth_detected', False),
                specific_myth=myth_data.get('specific_myth'),
                severity_level=myth_data.get('severity_level'),
                correction_provided=False,  # Will be updated when bot provides correction
                analysis_context={
                    'cultural_sensitivity_needed': myth_data.get('cultural_sensitivity_needed'),
                    'correction_approach': myth_data.get('correction_approach'),
                    'analysis_summary': myth_data.get('analysis_summary'),
                    'message_count': total_messages
                }
            )
            
            # Log detected myths for monitoring and education purposes
            if myth_data.get('myth_detected'):
                logger.info(f"MYTH DETECTED - Session: {session.telegram_user_id}, "
                           f"Type: {myth_data.get('myth_type')}, "
                           f"Myth: {myth_data.get('specific_myth')}, "
                           f"Severity: {myth_data.get('severity_level')}")
                
                # Log high-severity myths
                if myth_data.get('severity_level') in ['HIGH', 'CRITICAL']:
                    logger.warning(f"HIGH SEVERITY MYTH - Session: {session.telegram_user_id}, "
                                 f"Type: {myth_data.get('myth_type')}, "
                                 f"Details: {myth_data.get('specific_myth')}")
            
            logger.info(f"Myth detection completed - Session: {session.id}, "
                       f"Myth Detected: {myth_data.get('myth_detected')}, "
                       f"Type: {myth_data.get('myth_type')}")
        else:
            logger.error(f"Myth detection failed for session {session.id}")
            
    except Exception as e:
        logger.error(f"Myth detection process failed: {e}")

@sync_to_async  
def mark_myth_correction_provided(assessment_id):
    """
    Mark that a correction was provided for a detected myth.
    """
    try:
        assessment = MythAssessment.objects.get(id=assessment_id)
        assessment.correction_provided = True
        assessment.save()
        return assessment
    except MythAssessment.DoesNotExist:
        logger.error(f"MythAssessment {assessment_id} not found")
        return None
