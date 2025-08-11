"""
Automatic location detection without user input.
Uses various methods to determine user location automatically.
"""

import asyncio
import logging
import httpx
from typing import Optional, Tuple
from bot.location_utils import detect_ethiopian_region

logger = logging.getLogger(__name__)

async def get_ip_geolocation() -> Optional[Tuple[float, float, str]]:
    """
    Get user location using IP geolocation service.
    Returns (latitude, longitude, country) or None if failed.
    """
    try:
        # Use ipapi.co - free service with good accuracy
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("https://ipapi.co/json/")
            if response.status_code == 200:
                data = response.json()
                
                latitude = float(data.get('latitude', 0))
                longitude = float(data.get('longitude', 0))
                country = data.get('country_name', 'Unknown')
                city = data.get('city', 'Unknown')
                region = data.get('region', 'Unknown')
                
                logger.info(f"IP Geolocation: {city}, {region}, {country} ({latitude}, {longitude})")
                
                return latitude, longitude, country
                
    except Exception as e:
        logger.warning(f"IP geolocation failed: {e}")
    
    return None

async def get_fallback_location() -> Optional[Tuple[float, float, str]]:
    """
    Fallback method using a different service.
    """
    try:
        # Use ip-api.com as fallback
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://ip-api.com/json/")
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'success':
                    latitude = float(data.get('lat', 0))
                    longitude = float(data.get('lon', 0))
                    country = data.get('country', 'Unknown')
                    
                    logger.info(f"Fallback location: {country} ({latitude}, {longitude})")
                    
                    return latitude, longitude, country
                    
    except Exception as e:
        logger.warning(f"Fallback geolocation failed: {e}")
    
    return None

async def detect_user_location() -> Tuple[float, float, str, str]:
    """
    Automatically detect user location using multiple methods.
    Returns (latitude, longitude, country, detected_region_code).
    
    Raises Exception if all detection methods fail.
    """
    
    detection_errors = []
    
    # Try primary IP geolocation
    try:
        location_data = await get_ip_geolocation()
        if location_data:
            latitude, longitude, country = location_data
            
            # Check if location is in Ethiopia
            if country.lower() in ['ethiopia', 'ethiopia']:
                # Use our existing Ethiopian region detection
                region_code = detect_ethiopian_region(latitude, longitude)
                if region_code:
                    logger.info(f"Detected Ethiopian region: {region_code}")
                    return latitude, longitude, country, region_code
                else:
                    # In Ethiopia but no specific region detected - default to Addis Ababa
                    logger.info("In Ethiopia but region not detected, defaulting to Addis Ababa")
                    return 9.0307, 38.7407, "Ethiopia", "ADDIS_ABABA"
            else:
                # User is outside Ethiopia - still provide service with Addis Ababa as base
                logger.info(f"User detected outside Ethiopia ({country}), defaulting to Addis Ababa")
                return 9.0307, 38.7407, "Ethiopia", "ADDIS_ABABA"
    except Exception as e:
        detection_errors.append(f"Primary geolocation failed: {e}")
    
    # Try fallback if primary failed
    try:
        location_data = await get_fallback_location()
        if location_data:
            latitude, longitude, country = location_data
            
            # Check if location is in Ethiopia
            if country.lower() in ['ethiopia', 'ethiopia']:
                region_code = detect_ethiopian_region(latitude, longitude)
                if region_code:
                    logger.info(f"Fallback detected Ethiopian region: {region_code}")
                    return latitude, longitude, country, region_code
                else:
                    logger.info("Fallback: In Ethiopia but region not detected, defaulting to Addis Ababa")
                    return 9.0307, 38.7407, "Ethiopia", "ADDIS_ABABA"
            else:
                logger.info(f"Fallback: User detected outside Ethiopia ({country}), defaulting to Addis Ababa")
                return 9.0307, 38.7407, "Ethiopia", "ADDIS_ABABA"
    except Exception as e:
        detection_errors.append(f"Fallback geolocation failed: {e}")
    
    # All detection methods failed
    error_msg = "All location detection methods failed: " + "; ".join(detection_errors)
    logger.error(error_msg)
    raise Exception(error_msg)

async def get_location_display_info(latitude: float, longitude: float, country: str, region_code: str) -> dict:
    """
    Get user-friendly display information for detected location.
    """
    from bot.location_utils import get_region_name, format_coordinates
    
    coordinates_text = format_coordinates(latitude, longitude)
    
    return {
        'coordinates': coordinates_text,
        'country': country,
        'region_code': region_code,
        'region_name_en': get_region_name(region_code, 'en'),
        'region_name_am': get_region_name(region_code, 'am'),
        'is_ethiopia': country.lower() in ['ethiopia', 'ethiopia'],
    }
