import os
import logging
import requests

logger = logging.getLogger(__name__)

CITY_COORDINATES = {
    "chennai": {"lat": 13.0827, "lon": 80.2707},
    "coimbatore": {"lat": 11.0168, "lon": 76.9558},
    "kanyakumari": {"lat": 8.0883, "lon": 77.5385}
}

def get_weather_for_city(city_name):
    city_name = city_name.lower().strip()
    coords = CITY_COORDINATES.get(city_name)
    
    if not coords:
        return {"error": "City weather coordinates not found."}
        
    api_key = os.getenv("OPENWEATHERMAP_API_KEY", "").strip().strip('"\'')
    if not api_key or api_key == "your_openweathermap_api_key_here":
        return get_mock_weather(city_name, is_fallback=False)
        
    try:
        lat = coords["lat"]
        lon = coords["lon"]
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
        
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        temp = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        condition = data["weather"][0]["main"]
        description = data["weather"][0]["description"].capitalize()
        icon = data["weather"][0]["icon"]
        
        recommendation = get_travel_recommendation(temp, condition)
        
        return {
            "city": city_name.title(),
            "temperature": f"{temp:.1f}°C",
            "humidity": f"{humidity}%",
            "condition": condition,
            "description": description,
            "recommendation": recommendation,
            "icon": icon,
            "is_mock": False
        }
    except Exception as e:
        logger.warning("Weather API error for %s: %s", city_name, str(e))
        return get_mock_weather(city_name, is_fallback=True)

def get_travel_recommendation(temp, condition):
    condition_lower = condition.lower()
    
    if "rain" in condition_lower or "drizzle" in condition_lower or "thunderstorm" in condition_lower:
        return "🌧️ Heavy rains or thunderstorms are expected. Carry an umbrella or a raincoat, and focus on indoor attractions like museums or temple halls."
    elif temp > 35:
        return "🥵 Extremely hot! Sightseeing is recommended during early morning or late evening. Stay hydrated and wear light cotton clothing."
    elif temp < 20:
        return "🍃 Pleasant and cool winds. Perfect for hiking, walking along the beach, and sightseeing all day long."
    else:
        return "☀️ Weather is clear and warm. Ideal for outdoor temple visits, ferry rides, and beach walks. Remember to wear sunscreen!"

def get_mock_weather(city_name, is_fallback=False):
    # Dynamic realistic mock data based on general climates
    city_mock_data = {
        "chennai": {
            "temperature": "31.5°C",
            "humidity": "74%",
            "condition": "Clouds",
            "description": "Scattered clouds",
            "recommendation": "☀️ Warm and humid. Perfect for an evening stroll at Marina Beach, but carry water.",
            "icon": "03d"
        },
        "coimbatore": {
            "temperature": "28.2°C",
            "humidity": "58%",
            "condition": "Clear",
            "description": "Clear sky",
            "recommendation": "🍃 The weather is very pleasant. Excellent conditions to visit Isha Yoga Center and explore the Velliangiri foothills.",
            "icon": "01d"
        },
        "kanyakumari": {
            "temperature": "29.4°C",
            "humidity": "68%",
            "condition": "Haze",
            "description": "Mild haze",
            "recommendation": "🚢 Great day for a ferry ride to Vivekananda Rock Memorial. Enjoy the gentle sea breeze!",
            "icon": "50d"
        }
    }
    
    data = city_mock_data.get(city_name, {
        "temperature": "27.0°C",
        "humidity": "65%",
        "condition": "Clear",
        "description": "Clear skies",
        "recommendation": "☀️ Good day for sightseeing.",
        "icon": "01d"
    })
    
    data["city"] = city_name.title()
    data["is_mock"] = True
    if is_fallback:
        data["note"] = "Live weather API unavailable; displaying seasonal fallback."
    else:
        data["note"] = "Demo seasonal weather (API key not configured)."
    return data
