import httpx
import os
import asyncio
import logging
from typing import Optional

# Configure logging
logger = logging.getLogger(__name__)

GEMINI_API_URL = os.getenv("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyAE9971K7sOniZHZzhrK_dQEzX-RpkpQ84")

# Rate limiting for concurrent requests to avoid hitting API limits
_api_semaphore = asyncio.Semaphore(8)  # Max 8 concurrent API calls

# Shared HTTP client for connection reuse
_http_client: Optional[httpx.AsyncClient] = None

async def get_http_client() -> httpx.AsyncClient:
    """Get or create a shared HTTP client for connection reuse"""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),  # 30 second timeout
            limits=httpx.Limits(
                max_keepalive_connections=10,  # Keep connections alive
                max_connections=20  # Max total connections
            )
        )
    return _http_client

async def close_http_client():
    """Close the shared HTTP client"""
    global _http_client
    if _http_client and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None

async def ask_gemini(prompt, temperature=0.2, max_retries=2):
    """
    Make a request to Gemini API with rate limiting and connection reuse.
    
    Args:
        prompt: The text prompt to send
        temperature: Response randomness (0.0-1.0)
        max_retries: Number of retries on failure
    
    Returns:
        Generated text response
    """
    headers = {"Content-Type": "application/json"}
    url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": 1024}
    }
    
    # Rate limiting to prevent overwhelming the API
    async with _api_semaphore:
        for attempt in range(max_retries + 1):
            try:
                client = await get_http_client()
                resp = await client.post(url, json=data, headers=headers)
                resp.raise_for_status()
                out = resp.json()
                
                # Gemini returns answer in: out["candidates"][0]["content"]["parts"][0]["text"]
                if out.get("candidates") and len(out["candidates"]) > 0:
                    content = out["candidates"][0].get("content", {})
                    parts = content.get("parts", [])
                    if parts and len(parts) > 0:
                        return parts[0].get("text", "")
                
                # Fallback if response structure is unexpected
                logger.warning("Unexpected Gemini API response structure: %s", out)
                return "Sorry, I received an unexpected response format."
                
            except httpx.TimeoutException:
                logger.warning("Gemini API timeout (attempt %d/%d)", attempt + 1, max_retries + 1)
                if attempt == max_retries:
                    return "Sorry, the request timed out. Please try again."
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
            except httpx.HTTPStatusError as e:
                logger.error("Gemini API HTTP error %d (attempt %d/%d): %s", e.response.status_code, attempt + 1, max_retries + 1, e)
                if e.response.status_code == 429:  # Rate limited
                    if attempt == max_retries:
                        return "Sorry, the service is busy. Please try again in a moment."
                    await asyncio.sleep(5 * (attempt + 1))  # Wait longer for rate limits
                elif e.response.status_code >= 500:  # Server error
                    if attempt == max_retries:
                        return "Sorry, there was a server error. Please try again later."
                    await asyncio.sleep(2 ** attempt)
                else:
                    # Client error (4xx) - don't retry
                    return "Sorry, there was an error processing your request."
                    
            except Exception as e:
                logger.error("Unexpected error calling Gemini API (attempt %d/%d): %s", attempt + 1, max_retries + 1, e)
                if attempt == max_retries:
                    return "Sorry, I encountered an unexpected error. Please try again."
                await asyncio.sleep(2 ** attempt)
        
        return "Sorry, I couldn't process your request after multiple attempts."
