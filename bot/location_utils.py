"""
Location utilities for mapping GPS coordinates to Ethiopian regions.
Approximate regional boundaries based on geographical data.
"""

def detect_ethiopian_region(latitude, longitude):
    """
    Detect Ethiopian region based on GPS coordinates.
    Returns region code from REGIONS choices or None if outside Ethiopia.
    
    Args:
        latitude (float): GPS latitude coordinate
        longitude (float): GPS longitude coordinate
    
    Returns:
        str: Region code from REGIONS choices or None
    """
    lat = float(latitude)
    lon = float(longitude)
    
    # Check if coordinates are within Ethiopia's approximate bounds
    # Ethiopia bounds: roughly 3°N to 15°N, 33°E to 48°E
    if not (3.0 <= lat <= 15.0 and 33.0 <= lon <= 48.0):
        return None
    
    # Approximate regional boundaries (simplified for demo)
    # These are rough approximations and would need more precise mapping in production
    
    # Addis Ababa (central point around 9.03°N, 38.74°E)
    if 8.8 <= lat <= 9.3 and 38.5 <= lon <= 39.0:
        return 'ADDIS_ABABA'
    
    # Harari Region (small region around Harar) - check first since it's smaller
    if 9.25 <= lat <= 9.45 and 42.05 <= lon <= 42.25:
        return 'HARARI'
    
    # Dire Dawa (around 9.59°N, 41.87°E)
    if 9.3 <= lat <= 9.8 and 41.5 <= lon <= 42.2:
        return 'DIRE_DAWA'
    
    # Afar Region (northeastern Ethiopia)
    if lat >= 11.0 and lon >= 40.0:
        return 'AFAR'
    
    # Somali Region (southeastern Ethiopia) - expanded coverage
    if lat <= 9.5 and lon >= 42.5:
        return 'SOMALI'
    
    # Tigray Region (northern Ethiopia)
    if lat >= 12.5 and lon <= 39.5:
        return 'TIGRAY'
    
    # Amhara Region (north-central Ethiopia)
    if lat >= 10.0 and lat <= 13.0 and lon >= 36.0 and lon <= 40.0:
        return 'AMHARA'
    
    # Oromia Region (largest region, central and southern Ethiopia)
    if 4.0 <= lat <= 10.0 and 34.0 <= lon <= 42.0:
        return 'OROMIA'
    
    # Benishangul-Gumuz (western Ethiopia)
    if 9.0 <= lat <= 12.5 and 34.0 <= lon <= 36.5:
        return 'BENISHANGUL'
    
    # Gambela (southwestern Ethiopia) - adjusted boundaries
    if 6.5 <= lat <= 8.5 and 33.0 <= lon <= 35.0:
        return 'GAMBELA'
    
    # South West Ethiopia Peoples' Region
    if 5.0 <= lat <= 7.5 and 34.5 <= lon <= 37.0:
        return 'SOUTHWEST'
    
    # South Ethiopia Region (formerly SNNPR parts)
    if 4.5 <= lat <= 7.0 and 36.0 <= lon <= 39.0:
        return 'SOUTH_ETH'
    
    # Sidama Region (separated from SNNPR)
    if 5.5 <= lat <= 6.8 and 38.0 <= lon <= 39.5:
        return 'SIDAMA'
    
    # Central Ethiopia Region (newly formed)
    if 7.5 <= lat <= 9.5 and 37.5 <= lon <= 39.5:
        return 'CENTRAL_ETH'
    
    # Default to Oromia if within Ethiopia but no specific match
    # (Oromia is the largest region and surrounds Addis Ababa)
    return 'OROMIA'


def get_region_name(region_code, language='en'):
    """
    Get the display name for a region code in the specified language.
    """
    from bot.choices import get_choice_label, REGIONS
    return get_choice_label(REGIONS, region_code, language)


def format_coordinates(latitude, longitude):
    """
    Format coordinates for display.
    """
    lat_dir = "N" if latitude >= 0 else "S"
    lon_dir = "E" if longitude >= 0 else "W"
    return f"{abs(latitude):.4f}°{lat_dir}, {abs(longitude):.4f}°{lon_dir}"
