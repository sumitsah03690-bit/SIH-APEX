from datetime import datetime
from typing import Dict, Any
import requests
from fastapi import HTTPException
from .base import BaseWeatherProvider


WMO_WEATHER_MAP = {
    0: "Clear Sky", 1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing Rime Fog",
    51: "Light Drizzle", 53: "Moderate Drizzle", 55: "Dense Drizzle",
    56: "Light Freezing Drizzle", 57: "Dense Freezing Drizzle",
    61: "Slight Rain", 63: "Moderate Rain", 65: "Heavy Rain",
    66: "Light Freezing Rain", 67: "Heavy Freezing Rain",
    71: "Slight Snow Fall", 73: "Moderate Snow Fall", 75: "Heavy Snow Fall",
    77: "Snow Grains",
    80: "Slight Rain Showers", 81: "Moderate Rain Showers", 82: "Violent Rain Showers",
    85: "Slight Snow Showers", 86: "Heavy Snow Showers",
    95: "Thunderstorm", 96: "Thunderstorm with Slight Hail", 99: "Thunderstorm with Heavy Hail"
}


class OpenMeteoProvider(BaseWeatherProvider):
    """
    Active Weather Provider using Open-Meteo API.
    Provides 100% free, keyless global & Indian weather data, forecasts, and condition-derived advisories.
    Reliable: 10,000 requests/day, sub-second latency, zero API-key rate-limit headaches.
    """

    @property
    def name(self) -> str:
        return "Open-Meteo"

    def get_current_weather(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Fetch current weather metrics from Open-Meteo including:
        temperature, apparent temperature, humidity, precipitation, rain, weather_code,
        wind speed, wind direction, sea-level pressure (pressure_msl), and UV index.
        Also pulls daily & hourly context for accurate precipitation and conditions.
        """
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={latitude}"
            f"&longitude={longitude}"
            "&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
            "precipitation,rain,showers,weather_code,wind_speed_10m,wind_direction_10m,"
            "pressure_msl,surface_pressure,uv_index,is_day"
            "&hourly=precipitation_probability,precipitation,weather_code"
            "&daily=precipitation_sum,precipitation_probability_max,temperature_2m_max,temperature_2m_min"
            "&forecast_days=1"
            "&timezone=auto"
        )
        try:
            response = requests.get(url, timeout=10)
        except requests.RequestException as e:
            raise HTTPException(
                status_code=503,
                detail=f"Open-Meteo service unreachable: {str(e)}"
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Open-Meteo error (HTTP {response.status_code}): Weather service is not available"
            )

        data = response.json()
        current = data.get("current", {})
        daily   = data.get("daily", {})
        hourly  = data.get("hourly", {})
        code    = current.get("weather_code", 0)

        temp_c = current.get("temperature_2m")
        humid  = current.get("relative_humidity_2m", 50)
        wind_k = current.get("wind_speed_10m", 0)

        # Standard barometric pressure: Always report Sea-Level Pressure (pressure_msl)
        # Standard in Apple Weather, Google, IMD, aviation, and consumer apps (~1008-1015 hPa).
        msl_pressure = current.get("pressure_msl")
        surf_pressure = current.get("surface_pressure")
        pressure_val = round(msl_pressure if msl_pressure is not None else (surf_pressure or 1013.2), 1)

        # Realistic feels-like calculation:
        # Avoid Canadian Humidex over-inflation under 27°C (where humidex adds +4°C artificially).
        # At 24°C with 10 km/h wind, human perceived temperature is ~24.5-25°C.
        app_temp = current.get("apparent_temperature")
        if temp_c is not None:
            if temp_c < 26.5:
                # Moderate/mild temps: feels-like stays close to air temp with slight moisture offset
                feels_like_val = round(temp_c + (0.01 * (humid - 50) if humid > 50 else 0) - (0.05 * (wind_k - 5) if wind_k > 5 else 0), 1)
            else:
                feels_like_val = round(app_temp if app_temp is not None else temp_c, 1)
        else:
            feels_like_val = app_temp

        # Check for Drizzle / rain conditions
        # If current code is 51, 53, 55 or upcoming 2-hour forecast has active drizzle/precipitation probability > 30%
        condition_str = WMO_WEATHER_MAP.get(code, "Partly Cloudy")
        next_codes = hourly.get("weather_code", [])[:3]
        next_probs = hourly.get("precipitation_probability", [])[:3]
        if code in (51, 53, 55):
            condition_str = "Drizzle"
        elif code in (1, 2, 3) and any(c in (51, 53, 55) for c in next_codes) and any(p >= 25 for p in next_probs):
            condition_str = "Drizzle"

        # Populate universal normalized aliases so every consumer gets consistent fields
        current["temperature"] = round(temp_c, 1) if temp_c is not None else None
        current["humidity"] = humid
        current["wind_speed"] = round(wind_k, 1) if wind_k is not None else None
        current["feels_like"] = feels_like_val
        current["condition"] = condition_str
        current["weather_description"] = condition_str
        current["pressure"] = pressure_val
        current["pressure_msl"] = msl_pressure
        current["pressure_surface"] = surf_pressure
        current["precipitation_sum_today"] = daily.get("precipitation_sum", [0.0])[0] if daily.get("precipitation_sum") else 0.0

        data["source"] = self.name
        return data

    def get_forecast(self, latitude: float, longitude: float, period: str = "next_7_days") -> Dict[str, Any]:
        """
        Fetch 7-day daily and hourly forecast from Open-Meteo.
        Supports filtering by period: today, tomorrow, next_3_days, next_7_days, weekend, hourly.
        """
        forecast_url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={latitude}"
            f"&longitude={longitude}"
            "&daily=temperature_2m_max,temperature_2m_min,"
            "precipitation_probability_max,precipitation_sum,wind_speed_10m_max"
            "&hourly=temperature_2m,precipitation_probability,precipitation,wind_speed_10m"
            "&forecast_days=7"
            "&timezone=auto"
        )
        try:
            forecast_response = requests.get(forecast_url, timeout=10)
        except requests.RequestException as e:
            raise HTTPException(
                status_code=503,
                detail=f"Open-Meteo service unreachable: {str(e)}"
            )

        if forecast_response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Open-Meteo error (HTTP {forecast_response.status_code}): Forecast service is not available"
            )

        forecast_data = forecast_response.json()
        daily = forecast_data.get("daily", {})
        hourly = forecast_data.get("hourly", {})

        days = []
        if "time" in daily:
            for i in range(len(daily["time"])):
                day = {
                    "date": daily["time"][i],
                    "max_temperature": daily["temperature_2m_max"][i],
                    "min_temperature": daily["temperature_2m_min"][i],
                    "rain_probability": daily["precipitation_probability_max"][i],
                    "rainfall": daily["precipitation_sum"][i],
                    "max_wind_speed": daily.get("wind_speed_10m_max", [None] * len(daily["time"]))[i]
                }
                days.append(day)

        period_norm = (period or "next_7_days").lower()
        filtered_days = days
        hourly_filtered = []

        if period_norm == "today":
            filtered_days = days[:1]
            target_date = days[0]["date"] if days else ""
            if hourly and "time" in hourly:
                for h_i, h_time in enumerate(hourly["time"]):
                    if h_time.startswith(target_date):
                        hourly_filtered.append({
                            "time": h_time,
                            "temperature": hourly["temperature_2m"][h_i],
                            "rain_probability": hourly["precipitation_probability"][h_i],
                            "rainfall": hourly["precipitation"][h_i],
                            "wind_speed": hourly["wind_speed_10m"][h_i]
                        })
        elif period_norm == "tomorrow":
            filtered_days = [days[1]] if len(days) > 1 else days[:1]
            target_date = days[1]["date"] if len(days) > 1 else (days[0]["date"] if days else "")
            if hourly and "time" in hourly:
                for h_i, h_time in enumerate(hourly["time"]):
                    if h_time.startswith(target_date):
                        hourly_filtered.append({
                            "time": h_time,
                            "temperature": hourly["temperature_2m"][h_i],
                            "rain_probability": hourly["precipitation_probability"][h_i],
                            "rainfall": hourly["precipitation"][h_i],
                            "wind_speed": hourly["wind_speed_10m"][h_i]
                        })
        elif period_norm == "next_3_days":
            filtered_days = days[:3]
        elif period_norm == "weekend":
            weekend_days = []
            for d in days:
                try:
                    dt = datetime.fromisoformat(d["date"])
                    if dt.weekday() in (5, 6):  # Saturday (5) or Sunday (6)
                        weekend_days.append(d)
                except Exception:
                    pass
            filtered_days = weekend_days if weekend_days else days[:2]
        elif period_norm == "hourly":
            if hourly and "time" in hourly:
                for h_i in range(min(24, len(hourly["time"]))):
                    hourly_filtered.append({
                        "time": hourly["time"][h_i],
                        "temperature": hourly["temperature_2m"][h_i],
                        "rain_probability": hourly["precipitation_probability"][h_i],
                        "rainfall": hourly["precipitation"][h_i],
                        "wind_speed": hourly["wind_speed_10m"][h_i]
                    })
        else:
            period_norm = "next_7_days"
            filtered_days = days[:7]

        result = {
            "latitude": latitude,
            "longitude": longitude,
            "forecast_period": period_norm,
            "forecast": filtered_days,
            "source": self.name
        }
        if hourly_filtered:
            result["hourly_forecast"] = hourly_filtered

        return result

    def get_alerts(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Evaluate real weather forecast data to generate condition-based advisories.
        Transparently tags alerts as derived from Open-Meteo, distinct from official IMD warnings.
        """
        weather_url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={latitude}"
            f"&longitude={longitude}"
            "&current=temperature_2m,wind_speed_10m"
            "&daily=precipitation_probability_max,precipitation_sum,temperature_2m_max"
            "&forecast_days=1"
            "&timezone=auto"
        )
        try:
            weather_response = requests.get(weather_url, timeout=10)
        except requests.RequestException as e:
            raise HTTPException(
                status_code=503,
                detail=f"Open-Meteo service unreachable: {str(e)}"
            )

        if weather_response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Open-Meteo error (HTTP {weather_response.status_code}): Weather service is not available"
            )

        weather_data = weather_response.json()
        current = weather_data.get("current", {})
        daily = weather_data.get("daily", {})
        alerts = []

        temperature = current.get("temperature_2m", 0)
        if temperature >= 40:
            alerts.append({
                "type": "Extreme Heat",
                "severity": "High",
                "message": "Extreme heat conditions are currently present. (Automated advisory derived from Open-Meteo forecast data; not an official IMD government warning)."
            })
        elif temperature >= 35:
            alerts.append({
                "type": "Heat",
                "severity": "Moderate",
                "message": "High temperature detected. Stay hydrated and avoid prolonged exposure to heat. (Automated advisory derived from Open-Meteo forecast data; not an official IMD government warning)."
            })

        wind_speed = current.get("wind_speed_10m", 0)
        if wind_speed >= 60:
            alerts.append({
                "type": "Strong Wind",
                "severity": "High",
                "message": "Very strong winds are currently present. Avoid unnecessary outdoor travel. (Automated advisory derived from Open-Meteo forecast data; not an official IMD government warning)."
            })
        elif wind_speed >= 40:
            alerts.append({
                "type": "Strong Wind",
                "severity": "Moderate",
                "message": "Strong winds are expected. Take caution outdoors. (Automated advisory derived from Open-Meteo forecast data; not an official IMD government warning)."
            })

        rain_probability = daily.get("precipitation_probability_max", [0])[0] if daily.get("precipitation_probability_max") else 0
        rainfall = daily.get("precipitation_sum", [0])[0] if daily.get("precipitation_sum") else 0

        if rain_probability >= 80 and rainfall >= 20:
            alerts.append({
                "type": "Heavy Rain",
                "severity": "High",
                "message": "Heavy rainfall is possible. Be cautious in low-lying areas. (Automated advisory derived from Open-Meteo forecast data; not an official IMD government warning)."
            })
        elif rain_probability >= 70:
            alerts.append({
                "type": "Rain",
                "severity": "Moderate",
                "message": "There is a high probability of rainfall. (Automated advisory derived from Open-Meteo forecast data; not an official IMD government warning)."
            })

        if len(alerts) == 0:
            alerts.append({
                "type": "No Major Alert",
                "severity": "Low",
                "message": "No major weather risk detected from the available Open-Meteo forecast data."
            })

        return {
            "latitude": latitude,
            "longitude": longitude,
            "alerts": alerts,
            "source": f"{self.name} (Derived Advisory)"
        }
