"""
Weather Agent — free Open-Meteo, no API key needed.
"""
import requests
from datetime import datetime

WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icy fog", 51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Slight rain", 63: "Rain", 65: "Heavy rain", 71: "Slight snow", 73: "Snow",
    75: "Heavy snow", 80: "Rain showers", 81: "Rain showers", 82: "Heavy rain showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Heavy thunderstorm with hail",
}

def _geocode(city: str):
    r = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                     params={"name": city, "count": 1, "language": "en", "format": "json"}, timeout=10)
    r.raise_for_status()
    results = r.json().get("results", [])
    if not results:
        raise ValueError(f"City not found: {city}")
    return results[0]["latitude"], results[0]["longitude"]

class WeatherAgent:
    def __init__(self, city: str = "Chennai", unit: str = "celsius"):
        self.city = city
        self.unit = unit

    def get_weather(self) -> dict:
        try:
            lat, lon = _geocode(self.city)
        except Exception as e:
            return {"error": str(e), "city": self.city}
        temp_unit = "celsius" if self.unit == "celsius" else "fahrenheit"
        r = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": lat, "longitude": lon,
            "current": ["temperature_2m", "relative_humidity_2m", "wind_speed_10m", "weather_code", "apparent_temperature"],
            "hourly": ["temperature_2m", "weather_code", "precipitation_probability"],
            "temperature_unit": temp_unit, "wind_speed_unit": "kmh", "forecast_days": 1,
        }, timeout=10)
        r.raise_for_status()
        data = r.json()
        current = data.get("current", {})
        hourly = data.get("hourly", {})
        unit_sym = "°C" if self.unit == "celsius" else "°F"
        now_hour = datetime.now().hour
        hours = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        codes = hourly.get("weather_code", [])
        precip = hourly.get("precipitation_probability", [])
        forecast = []
        for i, h in enumerate(hours[now_hour:now_hour + 8]):
            idx = now_hour + i
            forecast.append({
                "time": h[-5:],
                "temp": f"{temps[idx]}{unit_sym}" if idx < len(temps) else "—",
                "condition": WMO_CODES.get(codes[idx] if idx < len(codes) else 0, "Unknown"),
                "rain_chance": f"{precip[idx]}%" if idx < len(precip) else "—",
            })
        wmo = current.get("weather_code", 0)
        return {
            "city": self.city,
            "temperature": f"{current.get('temperature_2m', '?')}{unit_sym}",
            "feels_like": f"{current.get('apparent_temperature', '?')}{unit_sym}",
            "humidity": f"{current.get('relative_humidity_2m', '?')}%",
            "wind": f"{current.get('wind_speed_10m', '?')} km/h",
            "condition": WMO_CODES.get(wmo, "Unknown"),
            "condition_code": wmo,
            "hourly_forecast": forecast,
            "unit": unit_sym,
        }
