import asyncio
import logging
import httpx
import json
from django.conf import settings
from asgiref.sync import sync_to_async
from .models import RiskAssessment, ChatMessage

logger = logging.getLogger(__name__)

def should_perform_risk_assessment(total_messages):
    """
    Determine if risk assessment should be performed based on exponential pattern.
    Pattern: 3rd, 6th, 12th, 24th, 48th, 96th... (multiplying by 2)
    This ensures more frequent risk monitoring for safety.
    """
    if total_messages < 3:
        return False
    
    # Check if current message count matches our exponential pattern
    current_threshold = 3
    while current_threshold <= total_messages:
        if current_threshold == total_messages:
            return True
        current_threshold *= 2
    
    return False

@sync_to_async
def get_user_messages_for_risk_assessment(session, total_messages):
    """
    Retrieve recent user messages for risk assessment analysis.
    Dynamically adjust limit based on total messages (max 15 for risk assessment).
    """
    limit = min(total_messages, 15)  # Analyze more messages for better risk detection
    
    messages = ChatMessage.objects.filter(
        session=session, 
        sender='user'
    ).order_by('-timestamp')[:limit]
    
    return [msg.message for msg in reversed(messages)]

@sync_to_async
def save_risk_assessment(session, risk_level, risk_indicators=None, severity_score=None, 
                        messages_count=15, confidence_score=None, analysis_context=None):
    """
    Save risk assessment results to database.
    """
    assessment = RiskAssessment.objects.create(
        session=session,
        risk_level=risk_level,
        risk_indicators=risk_indicators,
        severity_score=severity_score,
        messages_analyzed=messages_count,
        confidence_score=confidence_score,
        analysis_context=analysis_context
    )
    return assessment

async def analyze_risk_with_gemini(messages, session_language):
    """
    Use Gemini AI to assess risk levels from user messages.
    """
    try:
        # Construct the risk assessment prompt
        prompt = f"""
You are an AI risk assessment specialist for sexual and reproductive health (SRH) conversations. 
Analyze the following user messages and assess any potential risks.

RISK CATEGORIES TO ASSESS:
- ABUSE: Physical or sexual abuse indicators
- DOMESTIC_VIOLENCE: Signs of domestic violence or intimate partner violence
- SELF_HARM: Self-harm behaviors or suicide ideation
- ILLEGAL_ABORTION: Unsafe or illegal abortion attempts/plans
- SEXUAL_VIOLENCE: Sexual assault, rape, or non-consensual activities
- UNSAFE_PRACTICES: Dangerous sexual practices that could cause harm
- CRISIS: Mental health crisis requiring immediate attention
- NEUTRAL: No significant risks detected

ASSESSMENT INSTRUCTIONS:
1. Carefully analyze each message for direct or indirect risk indicators
2. Look for concerning patterns, language, or behaviors
3. Consider cultural context (this is from Ethiopia)
4. Pay attention to emotional distress combined with risky situations
5. Assess both immediate and potential future risks

USER MESSAGES:
{chr(10).join([f"Message {i+1}: {msg}" for i, msg in enumerate(messages)])}

SESSION LANGUAGE: {session_language}

RESPONSE FORMAT (JSON):
{{
    "risk_level": "RISK_CATEGORY_CODE",
    "severity_score": 0.0-1.0,
    "risk_indicators": ["specific phrase or pattern 1", "indicator 2"],
    "confidence_score": 0.0-1.0,
    "analysis_summary": "Brief explanation of risk assessment",
    "recommended_action": "Suggested response or intervention if needed"
}}

Be cautious but not overly sensitive. Focus on genuine safety concerns rather than general health questions.
"""

        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
        headers = {
            "Content-Type": "application/json",
        }
        
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,  # Lower temperature for more consistent risk assessment
                "topK": 1,
                "topP": 0.8,
                "maxOutputTokens": 1000,
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
                        risk_data = json.loads(json_content)
                        return risk_data
                    else:
                        logger.error(f"No valid JSON found in Gemini response: {content}")
                        return None
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Gemini risk assessment JSON: {e}")
                    logger.error(f"Raw content: {content}")
                    return None
            else:
                logger.error(f"Gemini API error: {response.status_code} - {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"Risk assessment analysis failed: {e}")
        return None

async def perform_risk_assessment(session, total_messages):
    """
    Main function to perform risk assessment for a user session.
    """
    try:
        if not should_perform_risk_assessment(total_messages):
            return
        
        logger.info(f"Performing risk assessment for session {session.id} at message {total_messages}")
        
        # Get recent user messages
        messages = await get_user_messages_for_risk_assessment(session, total_messages)
        
        if not messages:
            logger.warning(f"No messages found for risk assessment - session {session.id}")
            return
        
        # Analyze with Gemini
        risk_data = await analyze_risk_with_gemini(messages, session.language)
        
        if risk_data:
            # Save to database
            assessment = await save_risk_assessment(
                session=session,
                risk_level=risk_data.get('risk_level', 'NEUTRAL'),
                risk_indicators=risk_data.get('risk_indicators'),
                severity_score=risk_data.get('severity_score'),
                messages_count=len(messages),
                confidence_score=risk_data.get('confidence_score'),
                analysis_context={
                    'analysis_summary': risk_data.get('analysis_summary'),
                    'recommended_action': risk_data.get('recommended_action'),
                    'message_count': total_messages
                }
            )
            
            # Log high-risk assessments for monitoring
            if risk_data.get('severity_score', 0) >= 0.7:
                logger.warning(f"HIGH RISK DETECTED - Session: {session.telegram_user_id}, "
                             f"Risk: {risk_data.get('risk_level')}, "
                             f"Severity: {risk_data.get('severity_score')}")
            
            logger.info(f"Risk assessment completed - Session: {session.id}, "
                       f"Risk Level: {risk_data.get('risk_level')}, "
                       f"Severity: {risk_data.get('severity_score')}")
        else:
            logger.error(f"Risk assessment failed for session {session.id}")
            
    except Exception as e:
        logger.error(f"Risk assessment process failed: {e}")
