import os
from urllib.parse import quote

def get_map_embed_url(latitude, longitude, place_name="Tourist Attraction"):
    """
    Returns a Google Maps Embed URL. 
    If GOOGLE_MAPS_API_KEY is in the environment, it uses the official Google Maps Embed API.
    Otherwise, it falls back to a standard coordinates-based free iframe embed URL.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip().strip('"\'')
    if api_key and api_key != "your_google_maps_api_key_here":
        encoded_name = quote(str(place_name))
        return f"https://www.google.com/maps/embed/v1/place?key={api_key}&q={encoded_name}&center={latitude},{longitude}&zoom=15"
    else:
        # Fallback standard embed URL using coordinates (free, no credentials required)
        return f"https://maps.google.com/maps?q={latitude},{longitude}&t=&z=15&ie=UTF8&iwloc=&output=embed"

def get_directions_url(latitude, longitude):
    """
    Returns a URL that opens Google Maps with turn-by-turn directions to the coordinates.
    """
    return f"https://www.google.com/maps/dir/?api=1&destination={latitude},{longitude}"
