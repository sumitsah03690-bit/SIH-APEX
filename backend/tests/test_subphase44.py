import os
import sys
import unittest
from dotenv import load_dotenv
from fastapi import HTTPException

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, ".env"))

from fastapi.testclient import TestClient
from main import app
from models.schemas import QueryUnderstanding
from services.weather_context import build_weather_context


class TestSubPhase44(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    # -------------------------------------------------------------------------
    # Test 1: Current weather in Hyderabad
    # -------------------------------------------------------------------------
    def test_01_current_weather_context(self):
        """Test 1: 'What's the weather in Hyderabad?' -> current-weather context retrieved with Open-Meteo source."""
        query = QueryUnderstanding(
            intent="current_weather",
            location="Hyderabad",
            city="Hyderabad",
            time_period="current",
            weather_variable="general_weather",
            requires_location=False,
        )
        context = build_weather_context(query)

        self.assertEqual(context["status"], "success")
        self.assertEqual(context["intent"], "current_weather")
        self.assertEqual(context["location"], "Hyderabad")
        self.assertEqual(context["source"], "Open-Meteo")
        self.assertIsNotNone(context["coordinates"])
        self.assertIn("latitude", context["coordinates"])
        self.assertIn("longitude", context["coordinates"])

        weather = context["weather_data"]
        self.assertIn("temperature", weather)
        self.assertIn("apparent_temperature", weather)
        self.assertIn("humidity", weather)
        self.assertIn("wind_speed", weather)
        self.assertIsNotNone(weather["temperature"])
        print(f"\n[TEST 1 PASS] Current weather in Hyderabad: Temp {weather['temperature']}°C, Humidity {weather['humidity']}%, Source: {context['source']}")

    # -------------------------------------------------------------------------
    # Test 2: Rain tomorrow in Delhi
    # -------------------------------------------------------------------------
    def test_02_rain_tomorrow_context(self):
        """Test 2: 'Will it rain tomorrow in Delhi?' -> rain/precipitation forecast context for Delhi."""
        query = QueryUnderstanding(
            intent="rain",
            location="Delhi",
            city="Delhi",
            time_period="tomorrow",
            forecast_period="tomorrow",
            weather_variable="precipitation",
            requires_location=False,
        )
        context = build_weather_context(query)

        self.assertEqual(context["status"], "success")
        self.assertEqual(context["intent"], "rain")
        self.assertEqual(context["location"], "Delhi")
        self.assertEqual(context["time_period"], "tomorrow")
        self.assertEqual(context["source"], "Open-Meteo")

        weather = context["weather_data"]
        self.assertEqual(weather["forecast_period"], "tomorrow")
        self.assertIn("precipitation_data", weather)
        self.assertTrue(len(weather["precipitation_data"]) > 0)
        p_data = weather["precipitation_data"][0]
        self.assertIn("rain_probability", p_data)
        self.assertIn("rainfall_mm", p_data)
        print(f"[TEST 2 PASS] Rain tomorrow in Delhi: Rain Prob {p_data['rain_probability']}%, Rainfall {p_data['rainfall_mm']} mm, Source: {context['source']}")

    # -------------------------------------------------------------------------
    # Test 3: Temperature in Mumbai
    # -------------------------------------------------------------------------
    def test_03_temperature_context(self):
        """Test 3: 'What's the temperature in Mumbai?' -> temperature-specific context for Mumbai."""
        query = QueryUnderstanding(
            intent="temperature",
            location="Mumbai",
            city="Mumbai",
            time_period="current",
            weather_variable="temperature",
            requires_location=False,
        )
        context = build_weather_context(query)

        self.assertEqual(context["status"], "success")
        self.assertEqual(context["intent"], "temperature")
        self.assertEqual(context["location"], "Mumbai")
        self.assertEqual(context["source"], "Open-Meteo")

        weather = context["weather_data"]
        self.assertIn("temperature", weather)
        self.assertIn("apparent_temperature", weather)
        self.assertEqual(weather.get("unit"), "°C")
        self.assertIsNotNone(weather["temperature"])
        print(f"[TEST 3 PASS] Temperature in Mumbai: {weather['temperature']}°C (Feels like {weather['apparent_temperature']}°C)")

    # -------------------------------------------------------------------------
    # Test 4: Humidity in Chennai
    # -------------------------------------------------------------------------
    def test_04_humidity_context(self):
        """Test 4: 'What's the humidity in Chennai?' -> humidity-specific context for Chennai."""
        query = QueryUnderstanding(
            intent="humidity",
            location="Chennai",
            city="Chennai",
            time_period="current",
            weather_variable="humidity",
            requires_location=False,
        )
        context = build_weather_context(query)

        self.assertEqual(context["status"], "success")
        self.assertEqual(context["intent"], "humidity")
        self.assertEqual(context["location"], "Chennai")
        self.assertEqual(context["source"], "Open-Meteo")

        weather = context["weather_data"]
        self.assertIn("humidity", weather)
        self.assertEqual(weather.get("unit"), "%")
        self.assertIsNotNone(weather["humidity"])
        print(f"[TEST 4 PASS] Humidity in Chennai: {weather['humidity']}%")

    # -------------------------------------------------------------------------
    # Test 5: Wind in Pune
    # -------------------------------------------------------------------------
    def test_05_wind_context(self):
        """Test 5: 'Is it windy in Pune?' -> wind speed and direction context for Pune."""
        query = QueryUnderstanding(
            intent="wind",
            location="Pune",
            city="Pune",
            time_period="current",
            weather_variable="wind",
            requires_location=False,
        )
        context = build_weather_context(query)

        self.assertEqual(context["status"], "success")
        self.assertEqual(context["intent"], "wind")
        self.assertEqual(context["location"], "Pune")
        self.assertEqual(context["source"], "Open-Meteo")

        weather = context["weather_data"]
        self.assertIn("wind_speed", weather)
        self.assertIn("wind_direction", weather)
        self.assertEqual(weather.get("unit"), "km/h")
        self.assertIsNotNone(weather["wind_speed"])
        print(f"[TEST 5 PASS] Wind in Pune: {weather['wind_speed']} km/h (Direction {weather['wind_direction']}°)")

    # -------------------------------------------------------------------------
    # Test 6: Advisory in Hyderabad tomorrow (Umbrella check)
    # -------------------------------------------------------------------------
    def test_06_advisory_context(self):
        """Test 6: 'Should I carry an umbrella tomorrow in Hyderabad?' -> advisory context with forecast and alerts."""
        query = QueryUnderstanding(
            intent="advisory",
            location="Hyderabad",
            city="Hyderabad",
            time_period="tomorrow",
            forecast_period="tomorrow",
            weather_variable="precipitation",
            requires_location=False,
        )
        context = build_weather_context(query)

        self.assertEqual(context["status"], "success")
        self.assertEqual(context["intent"], "advisory")
        self.assertEqual(context["location"], "Hyderabad")
        self.assertEqual(context["time_period"], "tomorrow")

        weather = context["weather_data"]
        self.assertIn("forecast", weather)
        self.assertIn("alerts", weather)
        self.assertTrue(len(weather["forecast"]) > 0)
        f_day = weather["forecast"][0]
        self.assertIn("rain_probability", f_day)
        self.assertIn("rainfall", f_day)
        self.assertIn("max_temperature", f_day)
        print(f"[TEST 6 PASS] Advisory context for Hyderabad: Rain Prob {f_day['rain_probability']}%, Alerts count: {len(weather['alerts'])}")

    # -------------------------------------------------------------------------
    # Test 7: Missing location ('What's the weather?')
    # -------------------------------------------------------------------------
    def test_07_missing_location_handling(self):
        """Test 7: 'What's the weather?' -> structured location_required response without inventing location."""
        query = QueryUnderstanding(
            intent="current_weather",
            location=None,
            city=None,
            time_period="current",
            weather_variable="general_weather",
            requires_location=True,
        )
        context = build_weather_context(query)

        self.assertEqual(context["status"], "location_required")
        self.assertIsNone(context["location"])
        self.assertIsNone(context["weather_data"])
        self.assertIn("Location is required", context["message"])
        print(f"[TEST 7 PASS] Missing location: status={context['status']}, message='{context['message']}'")

    # -------------------------------------------------------------------------
    # Test 8: Invalid location ('What's the weather in InvalidLocationXYZ123456?')
    # -------------------------------------------------------------------------
    def test_08_invalid_location_handling(self):
        """Test 8: 'What's the weather in InvalidLocationXYZ123456?' -> raises HTTP 404 from geocoding layer, no fake data."""
        query = QueryUnderstanding(
            intent="current_weather",
            location="InvalidLocationXYZ123456",
            city="InvalidLocationXYZ123456",
            time_period="current",
            weather_variable="general_weather",
            requires_location=False,
        )
        with self.assertRaises(HTTPException) as cm:
            build_weather_context(query)

        self.assertEqual(cm.exception.status_code, 404)
        self.assertEqual(cm.exception.detail, "City not found")
        print(f"[TEST 8 PASS] Invalid location 'InvalidLocationXYZ123456' properly raised HTTP {cm.exception.status_code} ({cm.exception.detail}), zero fake data")

    # -------------------------------------------------------------------------
    # Test 9: Regression Tests on All Existing Endpoints
    # -------------------------------------------------------------------------
    def test_09_regression_endpoints(self):
        """Verify that all existing endpoints remain operational."""
        endpoints = [
            ("GET", "/", None, 200),
            ("GET", "/chat?message=hello", None, 200),
            ("GET", "/weather-by-city?city=Hyderabad", None, 200),
            ("GET", "/weather-by-location?latitude=17.38&longitude=78.47", None, 200),
            ("GET", "/forecast?city=Delhi&period=tomorrow", None, 200),
            ("GET", "/forecast?city=Delhi&period=next_7_days", None, 200),
            ("GET", "/alerts?city=Hyderabad", None, 200),
            ("POST", "/ask-demo", {"message": "Will it rain tomorrow in Delhi?"}, 200),
            ("GET", "/ai-test?message=ping", None, 200),
        ]
        for method, url, body, expected in endpoints:
            if method == "GET":
                r = self.client.get(url)
            else:
                r = self.client.post(url, json=body)
            self.assertEqual(r.status_code, expected, f"{method} {url} failed with {r.status_code}")

        print("[TEST 9 PASS] Regression tests on all 9 endpoints: 100% PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
