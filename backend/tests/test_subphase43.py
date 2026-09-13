import os
import sys
import json
import unittest
from unittest.mock import MagicMock
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, ".env"))

from fastapi.testclient import TestClient
from main import app
from services import ai_service
from services.ai_service import (
    understand_query,
    validate_and_normalize_query,
    set_openai_client,
    get_openai_client,
    SUPPORTED_INTENTS,
    SUPPORTED_TIME_PERIODS,
    SUPPORTED_WEATHER_VARIABLES,
)


class TestSubPhase43(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.real_openai_client = get_openai_client()

    def tearDown(self):
        # Restore real client after each test
        set_openai_client(self.real_openai_client)

    # -------------------------------------------------------------------------
    # Helper to create mock response for understand_query
    # -------------------------------------------------------------------------
    def _create_mock_client(self, output_dict):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.output_text = json.dumps(output_dict)
        mock_client.responses.create.return_value = mock_resp
        mock_client.api_key = "test-mock-key"
        return mock_client

    # -------------------------------------------------------------------------
    # Test 1: "What's the weather in Hyderabad?"
    # -------------------------------------------------------------------------
    def test_01_query_current_weather(self):
        """Test 1: 'What's the weather in Hyderabad?' -> intent=current_weather, location=Hyderabad"""
        mock = self._create_mock_client({
            "intent": "current_weather",
            "location": "Hyderabad",
            "city": "Hyderabad",
            "time_period": "current",
            "forecast_period": None,
            "weather_variable": "general_weather",
            "requires_location": False,
        })
        set_openai_client(mock)

        raw = understand_query("What's the weather in Hyderabad?")
        res = json.loads(raw)
        self.assertEqual(res["intent"], "current_weather")
        self.assertEqual(res["location"], "Hyderabad")
        self.assertEqual(res["city"], "Hyderabad")
        self.assertFalse(res["requires_location"])
        print("\n[TEST 1 PASS] 'What's the weather in Hyderabad?' -> intent=current_weather, location=Hyderabad")

    # -------------------------------------------------------------------------
    # Test 2: "Will it rain tomorrow in Delhi?"
    # -------------------------------------------------------------------------
    def test_02_query_rain_tomorrow(self):
        """Test 2: 'Will it rain tomorrow in Delhi?' -> intent=rain, location=Delhi, time=tomorrow, variable=precipitation"""
        mock = self._create_mock_client({
            "intent": "rain",
            "location": "Delhi",
            "city": "Delhi",
            "time_period": "tomorrow",
            "forecast_period": "tomorrow",
            "weather_variable": "precipitation",
            "requires_location": False,
        })
        set_openai_client(mock)

        raw = understand_query("Will it rain tomorrow in Delhi?")
        res = json.loads(raw)
        self.assertIn(res["intent"], ["rain", "forecast"])
        self.assertEqual(res["location"], "Delhi")
        self.assertEqual(res["time_period"], "tomorrow")
        self.assertEqual(res["weather_variable"], "precipitation")
        print("[TEST 2 PASS] 'Will it rain tomorrow in Delhi?' -> intent=rain/forecast, location=Delhi, time=tomorrow, variable=precipitation")

    # -------------------------------------------------------------------------
    # Test 3: "What's the temperature in Mumbai?"
    # -------------------------------------------------------------------------
    def test_03_query_temperature(self):
        """Test 3: 'What's the temperature in Mumbai?' -> intent=temperature, location=Mumbai, variable=temperature"""
        mock = self._create_mock_client({
            "intent": "temperature",
            "location": "Mumbai",
            "city": "Mumbai",
            "time_period": "current",
            "forecast_period": None,
            "weather_variable": "temperature",
            "requires_location": False,
        })
        set_openai_client(mock)

        raw = understand_query("What's the temperature in Mumbai?")
        res = json.loads(raw)
        self.assertIn(res["intent"], ["temperature", "current_weather"])
        self.assertEqual(res["location"], "Mumbai")
        self.assertEqual(res["weather_variable"], "temperature")
        print("[TEST 3 PASS] 'What's the temperature in Mumbai?' -> intent=temperature, location=Mumbai, variable=temperature")

    # -------------------------------------------------------------------------
    # Test 4: "What's the humidity in Chennai?"
    # -------------------------------------------------------------------------
    def test_04_query_humidity(self):
        """Test 4: 'What's the humidity in Chennai?' -> intent=humidity, location=Chennai, variable=humidity"""
        mock = self._create_mock_client({
            "intent": "humidity",
            "location": "Chennai",
            "city": "Chennai",
            "time_period": "current",
            "forecast_period": None,
            "weather_variable": "humidity",
            "requires_location": False,
        })
        set_openai_client(mock)

        raw = understand_query("What's the humidity in Chennai?")
        res = json.loads(raw)
        self.assertIn(res["intent"], ["humidity", "current_weather"])
        self.assertEqual(res["location"], "Chennai")
        self.assertEqual(res["weather_variable"], "humidity")
        print("[TEST 4 PASS] 'What's the humidity in Chennai?' -> intent=humidity, location=Chennai, variable=humidity")

    # -------------------------------------------------------------------------
    # Test 5: "Is it windy in Pune?"
    # -------------------------------------------------------------------------
    def test_05_query_wind(self):
        """Test 5: 'Is it windy in Pune?' -> intent=wind, location=Pune, variable=wind"""
        mock = self._create_mock_client({
            "intent": "wind",
            "location": "Pune",
            "city": "Pune",
            "time_period": "current",
            "forecast_period": None,
            "weather_variable": "wind",
            "requires_location": False,
        })
        set_openai_client(mock)

        raw = understand_query("Is it windy in Pune?")
        res = json.loads(raw)
        self.assertIn(res["intent"], ["wind", "current_weather"])
        self.assertEqual(res["location"], "Pune")
        self.assertEqual(res["weather_variable"], "wind")
        print("[TEST 5 PASS] 'Is it windy in Pune?' -> intent=wind, location=Pune, variable=wind")

    # -------------------------------------------------------------------------
    # Test 6: "Should I carry an umbrella tomorrow in Hyderabad?"
    # -------------------------------------------------------------------------
    def test_06_query_advisory(self):
        """Test 6: 'Should I carry an umbrella tomorrow in Hyderabad?' -> intent=advisory, location=Hyderabad, time=tomorrow"""
        mock = self._create_mock_client({
            "intent": "advisory",
            "location": "Hyderabad",
            "city": "Hyderabad",
            "time_period": "tomorrow",
            "forecast_period": "tomorrow",
            "weather_variable": "precipitation",
            "requires_location": False,
        })
        set_openai_client(mock)

        raw = understand_query("Should I carry an umbrella tomorrow in Hyderabad?")
        res = json.loads(raw)
        self.assertIn(res["intent"], ["advisory", "forecast", "rain"])
        self.assertEqual(res["location"], "Hyderabad")
        self.assertEqual(res["time_period"], "tomorrow")
        print("[TEST 6 PASS] 'Should I carry an umbrella tomorrow in Hyderabad?' -> intent=advisory, location=Hyderabad, time=tomorrow")

    # -------------------------------------------------------------------------
    # Test 7: "What's the weather?" (No Location -> Must NOT invent location)
    # -------------------------------------------------------------------------
    def test_07_query_missing_location(self):
        """Test 7: 'What's the weather?' -> location=None, requires_location=True (must NOT invent location)"""
        mock = self._create_mock_client({
            "intent": "current_weather",
            "location": None,
            "city": None,
            "time_period": "current",
            "forecast_period": None,
            "weather_variable": "general_weather",
            "requires_location": True,
        })
        set_openai_client(mock)

        raw = understand_query("What's the weather?")
        res = json.loads(raw)
        self.assertIsNone(res["location"])
        self.assertIsNone(res["city"])
        self.assertTrue(res["requires_location"])
        print("[TEST 7 PASS] 'What's the weather?' -> location=None, requires_location=True (no invented location)")

    # -------------------------------------------------------------------------
    # Test 8: "What's the weather in InvalidLocationXYZ123456?"
    # -------------------------------------------------------------------------
    def test_08_query_arbitrary_location_extraction(self):
        """Test 8: 'What's the weather in InvalidLocationXYZ123456?' -> extracts string without validating existence"""
        mock = self._create_mock_client({
            "intent": "current_weather",
            "location": "InvalidLocationXYZ123456",
            "city": "InvalidLocationXYZ123456",
            "time_period": "current",
            "forecast_period": None,
            "weather_variable": "general_weather",
            "requires_location": False,
        })
        set_openai_client(mock)

        raw = understand_query("What's the weather in InvalidLocationXYZ123456?")
        res = json.loads(raw)
        self.assertEqual(res["location"], "InvalidLocationXYZ123456")
        self.assertEqual(res["city"], "InvalidLocationXYZ123456")
        print("[TEST 8 PASS] 'What's the weather in InvalidLocationXYZ123456?' -> location='InvalidLocationXYZ123456' extracted verbatim")

    # -------------------------------------------------------------------------
    # Test 9: Markdown Code Fence Stripping & Validation Normalization
    # -------------------------------------------------------------------------
    def test_09_markdown_fence_and_normalization(self):
        """Test that understand_query strips ```json fences and normalizes fields."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.output_text = "```json\n{\"intent\": \"FORECAST\", \"location\": \"Warangal\", \"time_period\": \"weekend\"}\n```"
        mock_client.responses.create.return_value = mock_resp
        mock_client.api_key = "test-mock-key"
        set_openai_client(mock_client)

        raw = understand_query("Forecast for Warangal this weekend")
        res = json.loads(raw)
        self.assertEqual(res["intent"], "forecast")
        self.assertEqual(res["location"], "Warangal")
        self.assertEqual(res["city"], "Warangal")
        self.assertEqual(res["time_period"], "weekend")
        self.assertEqual(res["forecast_period"], "weekend")
        print("[TEST 9 PASS] Markdown code fence stripping and normalization: PASS")

    # -------------------------------------------------------------------------
    # Test 10: Real OpenAI Path (Quota Exhaustion Clean Failure)
    # -------------------------------------------------------------------------
    def test_10_real_openai_path_clean_503(self):
        """Test that real OpenAI path (with zero credits) returns clean HTTP 503 on /understand."""
        # Ensure real client is active
        set_openai_client(self.real_openai_client)
        resp = self.client.get("/understand?message=What+is+the+weather+in+Hyderabad")
        self.assertEqual(resp.status_code, 503)
        data = resp.json()
        self.assertTrue(
            "quota or credit balance is exhausted" in data["detail"] or "OpenAI client not configured" in data["detail"]
        )
        print(f"[TEST 10 PASS] Real OpenAI path: Clean HTTP {resp.status_code} - {data['detail']}")

    # -------------------------------------------------------------------------
    # Test 11: Regression Suite (Non-AI Endpoints)
    # -------------------------------------------------------------------------
    def test_11_regression_all_endpoints(self):
        """Test all regression endpoints to ensure zero regressions."""
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

        print("[TEST 11 PASS] Regression tests on all 9 endpoints: 100% PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
