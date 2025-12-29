"""
Weather Tool for JARVIS v3
Get weather forecasts via Open-Meteo API
"""
import httpx
from typing import Dict, Any, Optional
from urllib.parse import quote

from app.tools.base import BaseTool, ToolParameter, ToolDomain
from app.config.settings import get_settings

settings = get_settings()


# Weather code descriptions from WMO
WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail"
}


def get_weather_description(code: int) -> str:
    """Convert weather code to human-readable description"""
    return WEATHER_CODES.get(code, "Unknown")


class WeatherTool(BaseTool):
    """Get current weather and forecast from Open-Meteo"""
    
    name = "get_weather"
    description = """Get current weather and forecast. Returns temperature, conditions, humidity, wind, and multi-day forecast. Uses default home location if coordinates not specified."""
    
    domain = ToolDomain.UTILITIES
    
    parameters = [
        ToolParameter(
            name="latitude",
            type="number",
            description=f"Latitude coordinate (default: {settings.location_lat})",
            required=False
        ),
        ToolParameter(
            name="longitude",
            type="number",
            description=f"Longitude coordinate (default: {settings.location_lon})",
            required=False
        ),
        ToolParameter(
            name="timezone",
            type="string",
            description=f"Timezone for times (default: {settings.location_timezone})",
            required=False
        ),
        ToolParameter(
            name="forecast_days",
            type="integer",
            description="Number of forecast days 1-7 (default: 3)",
            required=False
        )
    ]
    
    async def execute(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        timezone: Optional[str] = None,
        forecast_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute weather query"""
        # Use defaults from settings
        lat = latitude if latitude is not None else settings.location_lat
        lon = longitude if longitude is not None else settings.location_lon
        tz = timezone if timezone else settings.location_timezone
        days = min(forecast_days if forecast_days else 3, 7)
        
        # Build URL
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}"
            f"&longitude={lon}"
            f"&timezone={quote(tz)}"
            f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m"
            f"&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset"
            f"&forecast_days={days}"
        )
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                
                # Format current weather
                current = {
                    "temperature": f"{data['current']['temperature_2m']}°C",
                    "feels_like": f"{data['current']['apparent_temperature']}°C",
                    "humidity": f"{data['current']['relative_humidity_2m']}%",
                    "conditions": get_weather_description(data['current']['weather_code']),
                    "wind": f"{data['current']['wind_speed_10m']} km/h",
                    "wind_direction": data['current']['wind_direction_10m']
                }
                
                # Format daily forecast
                forecast = []
                for i, date in enumerate(data['daily']['time']):
                    forecast.append({
                        "date": date,
                        "conditions": get_weather_description(data['daily']['weather_code'][i]),
                        "high": f"{data['daily']['temperature_2m_max'][i]}°C",
                        "low": f"{data['daily']['temperature_2m_min'][i]}°C",
                        "precipitation_chance": f"{data['daily']['precipitation_probability_max'][i]}%",
                        "sunrise": data['daily']['sunrise'][i].split('T')[1] if 'T' in data['daily']['sunrise'][i] else data['daily']['sunrise'][i],
                        "sunset": data['daily']['sunset'][i].split('T')[1] if 'T' in data['daily']['sunset'][i] else data['daily']['sunset'][i]
                    })
                
                return {
                    "success": True,
                    "location": {
                        "latitude": lat,
                        "longitude": lon,
                        "timezone": tz
                    },
                    "current": current,
                    "forecast": forecast
                }
                
            except httpx.HTTPStatusError as e:
                return {
                    "success": False,
                    "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }
