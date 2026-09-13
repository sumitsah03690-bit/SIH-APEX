"""
Sub-Phase 4.5 Test Suite — Grounded /ask Pipeline
Tests the complete pipeline:
  understand_query() -> QueryUnderstanding -> build_weather_context() -> get_final_answer()
Uses mocked OpenAI client (test injection) for all AI calls.
Verifies:
  - All 8 canonical queries required for Sub-Phase 4.5
  - Explicit grounding assertion (LLM input contains real weather metrics)
  - Missing location handling (location_required)
  - Invalid location handling (HTTP 404)
  - Unknown/non-weather queries (unsupported_intent)
  - GPS coordinates fallback
  - build_weather_context() unit test
  - Regression for all non-AI endpoints
"""

import json
import sys
import os
import unittest
from unittest.mock import MagicMock
from dotenv import load_dotenv
from fastapi import HTTPException

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, ".env"))

from services.ai_service import set_openai_client, get_openai_client
from services.weather_context import build_weather_context
from fastapi.testclient import TestClient
from main import app

client_http = TestClient(app)


def make_mock_openai(understand_json: dict, final_answer: str = "Mocked grounded answer"):
    """
    Build a mock OpenAI client that:
    - On the 1st call (understand_query), returns understand_json as JSON string.
    - On the 2nd call (get_final_answer), returns final_answer.
    """
    call_count = [0]

    def side_effect(**kwargs):
        call_count[0] += 1
        mock_resp = MagicMock()
        if call_count[0] == 1:
            mock_resp.output_text = json.dumps(understand_json)
        else:
            mock_resp.output_text = final_answer
        return mock_resp

    mock_client = MagicMock()
    mock_client.responses.create.side_effect = side_effect
    return mock_client


class TestSubPhase45GroundedPipeline(unittest.TestCase):

    def setUp(self):
        self._real_client = get_openai_client()

    def tearDown(self):
        set_openai_client(self._real_client)

    # -------------------------------------------------------------------------
    # Canonical Test 1: Current weather query — Hyderabad
    # -------------------------------------------------------------------------
    def test_01_current_weather_hyderabad(self):
        """1. What's the weather in Hyderabad? -> returns grounded current weather."""
        understand_output = {
            "intent": "current_weather",
            "location": "Hyderabad",
            "city": "Hyderabad",
            "time_period": "current",
            "forecast_period": None,
            "weather_variable": None,
            "requires_location": False,
        }
        mock_answer = "The current weather in Hyderabad is 25°C with moderate humidity."
        mock_client = make_mock_openai(understand_output, mock_answer)
        set_openai_client(mock_client)

        resp = client_http.post("/ask", json={"message": "What's the weather in Hyderabad?"})
        self.assertEqual(resp.status_code, 200, msg=f"Unexpected status: {resp.text}")
        data = resp.json()
        self.assertEqual(data["intent"], "current_weather")
        self.assertIn("Hyderabad", data["city"])
        self.assertEqual(data["answer"], mock_answer)
        self.assertIsNotNone(data["weather_data"])
        self.assertIn("temperature", data["weather_data"])
        self.assertEqual(data["source"], "Open-Meteo")

    # -------------------------------------------------------------------------
    # Canonical Test 2: Rain query — Delhi tomorrow
    # -------------------------------------------------------------------------
    def test_02_rain_tomorrow_delhi(self):
        """2. Will it rain tomorrow in Delhi? -> returns grounded precipitation data."""
        understand_output = {
            "intent": "rain",
            "location": "Delhi",
            "city": "Delhi",
            "time_period": "tomorrow",
            "forecast_period": "tomorrow",
            "weather_variable": "precipitation",
            "requires_location": False,
        }
        mock_answer = "Tomorrow in Delhi, rain probability is approximately 90%."
        mock_client = make_mock_openai(understand_output, mock_answer)
        set_openai_client(mock_client)

        resp = client_http.post("/ask", json={"message": "Will it rain tomorrow in Delhi?"})
        self.assertEqual(resp.status_code, 200, msg=f"Unexpected status: {resp.text}")
        data = resp.json()
        self.assertEqual(data["intent"], "rain")
        self.assertIn("Delhi", data["city"])
        self.assertEqual(data["answer"], mock_answer)
        self.assertIsNotNone(data["weather_data"])
        self.assertIn("precipitation_data", data["weather_data"])
        self.assertEqual(data["source"], "Open-Meteo")

    # -------------------------------------------------------------------------
    # Canonical Test 3: Temperature query — Mumbai
    # -------------------------------------------------------------------------
    def test_03_temperature_mumbai(self):
        """3. What's the temperature in Mumbai? -> returns grounded temperature metrics."""
        understand_output = {
            "intent": "temperature",
            "location": "Mumbai",
            "city": "Mumbai",
            "time_period": "current",
            "forecast_period": None,
            "weather_variable": "temperature",
            "requires_location": False,
        }
        mock_answer = "The temperature in Mumbai is currently 26°C (feels like 32°C)."
        mock_client = make_mock_openai(understand_output, mock_answer)
        set_openai_client(mock_client)

        resp = client_http.post("/ask", json={"message": "What's the temperature in Mumbai?"})
        self.assertEqual(resp.status_code, 200, msg=f"Unexpected status: {resp.text}")
        data = resp.json()
        self.assertEqual(data["intent"], "temperature")
        self.assertIn("Mumbai", data["city"])
        self.assertEqual(data["answer"], mock_answer)
        self.assertIsNotNone(data["weather_data"])
        self.assertIn("temperature", data["weather_data"])

    # -------------------------------------------------------------------------
    # Canonical Test 4: Humidity query — Chennai
    # -------------------------------------------------------------------------
    def test_04_humidity_chennai(self):
        """4. What's the humidity in Chennai? -> returns grounded humidity data."""
        understand_output = {
            "intent": "humidity",
            "location": "Chennai",
            "city": "Chennai",
            "time_period": "current",
            "forecast_period": None,
            "weather_variable": "humidity",
            "requires_location": False,
        }
        mock_answer = "The relative humidity in Chennai is 88%."
        mock_client = make_mock_openai(understand_output, mock_answer)
        set_openai_client(mock_client)

        resp = client_http.post("/ask", json={"message": "What's the humidity in Chennai?"})
        self.assertEqual(resp.status_code, 200, msg=f"Unexpected status: {resp.text}")
        data = resp.json()
        self.assertEqual(data["intent"], "humidity")
        self.assertIn("Chennai", data["city"])
        self.assertEqual(data["answer"], mock_answer)
        self.assertIsNotNone(data["weather_data"])
        self.assertIn("humidity", data["weather_data"])

    # -------------------------------------------------------------------------
    # Canonical Test 5: Wind query — Pune
    # -------------------------------------------------------------------------
    def test_05_wind_pune(self):
        """5. Is it windy in Pune? -> returns grounded wind speed & direction."""
        understand_output = {
            "intent": "wind",
            "location": "Pune",
            "city": "Pune",
            "time_period": "current",
            "forecast_period": None,
            "weather_variable": "wind",
            "requires_location": False,
        }
        mock_answer = "Current wind speed in Pune is 8 km/h."
        mock_client = make_mock_openai(understand_output, mock_answer)
        set_openai_client(mock_client)

        resp = client_http.post("/ask", json={"message": "Is it windy in Pune?"})
        self.assertEqual(resp.status_code, 200, msg=f"Unexpected status: {resp.text}")
        data = resp.json()
        self.assertEqual(data["intent"], "wind")
        self.assertIn("Pune", data["city"])
        self.assertEqual(data["answer"], mock_answer)
        self.assertIsNotNone(data["weather_data"])
        self.assertIn("wind_speed", data["weather_data"])

    # -------------------------------------------------------------------------
    # Canonical Test 6: Advisory query — Hyderabad tomorrow
    # -------------------------------------------------------------------------
    def test_06_advisory_umbrella_hyderabad(self):
        """6. Should I carry an umbrella tomorrow in Hyderabad? -> advisory grounded in forecast & alerts."""
        understand_output = {
            "intent": "advisory",
            "location": "Hyderabad",
            "city": "Hyderabad",
            "time_period": "tomorrow",
            "forecast_period": "tomorrow",
            "weather_variable": "precipitation",
            "requires_location": False,
        }
        mock_answer = "Tomorrow in Hyderabad has a rain probability of around 20%, carry an umbrella just in case."
        mock_client = make_mock_openai(understand_output, mock_answer)
        set_openai_client(mock_client)

        resp = client_http.post("/ask", json={"message": "Should I carry an umbrella tomorrow in Hyderabad?"})
        self.assertEqual(resp.status_code, 200, msg=f"Unexpected status: {resp.text}")
        data = resp.json()
        self.assertEqual(data["intent"], "advisory")
        self.assertIn("Hyderabad", data["city"])
        self.assertEqual(data["answer"], mock_answer)
        self.assertIsNotNone(data["weather_data"])
        self.assertIn("forecast", data["weather_data"])

    # -------------------------------------------------------------------------
    # Canonical Test 7: Missing location — no city
    # -------------------------------------------------------------------------
    def test_07_missing_location(self):
        """7. What's the weather? -> returns location_required without guessing or assuming a city."""
        understand_output = {
            "intent": "current_weather",
            "location": None,
            "city": None,
            "time_period": "current",
            "forecast_period": None,
            "weather_variable": None,
            "requires_location": True,
        }
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.output_text = json.dumps(understand_output)
        mock_client.responses.create.return_value = mock_resp
        set_openai_client(mock_client)

        resp = client_http.post("/ask", json={"message": "What's the weather?"})
        self.assertEqual(resp.status_code, 200, msg=f"Unexpected status: {resp.text}")
        data = resp.json()
        self.assertIsNone(data["city"])
        self.assertIn("Location is required", data["answer"])
        self.assertIsNone(data["weather_data"])
        # Verify LLM was called only once (understand_query); no final_answer call
        self.assertEqual(mock_client.responses.create.call_count, 1)

    # -------------------------------------------------------------------------
    # Canonical Test 8: Invalid location — InvalidLocationXYZ123456
    # -------------------------------------------------------------------------
    def test_08_invalid_location(self):
        """8. What's the weather in InvalidLocationXYZ123456? -> HTTP 404 City not found, zero fake data."""
        understand_output = {
            "intent": "current_weather",
            "location": "InvalidLocationXYZ123456",
            "city": "InvalidLocationXYZ123456",
            "time_period": "current",
            "forecast_period": None,
            "weather_variable": None,
            "requires_location": False,
        }
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.output_text = json.dumps(understand_output)
        mock_client.responses.create.return_value = mock_resp
        set_openai_client(mock_client)

        resp = client_http.post("/ask", json={"message": "What's the weather in InvalidLocationXYZ123456?"})
        self.assertEqual(resp.status_code, 404, msg=f"Expected 404, got: {resp.status_code} {resp.text}")
        self.assertIn("City not found", resp.json().get("detail", ""))

    # -------------------------------------------------------------------------
    # Step 9: Grounding assertion — Verify actual weather context reaches LLM
    # -------------------------------------------------------------------------
    def test_09_grounding_context_reaches_llm(self):
        """Step 9: Assert that actual Open-Meteo weather context is passed to the final LLM input."""
        understand_output = {
            "intent": "current_weather",
            "location": "Hyderabad",
            "city": "Hyderabad",
            "time_period": "current",
            "forecast_period": None,
            "weather_variable": None,
            "requires_location": False,
        }
        mock_client = make_mock_openai(understand_output, "Grounded response")
        set_openai_client(mock_client)

        resp = client_http.post("/ask", json={"message": "What is the weather in Hyderabad?"})
        self.assertEqual(resp.status_code, 200)

        # Verify exactly 2 calls were made to client.responses.create
        self.assertEqual(mock_client.responses.create.call_count, 2)

        # Inspect the 2nd call (get_final_answer) arguments
        second_call = mock_client.responses.create.call_args_list[1]
        call_kwargs = second_call.kwargs
        input_text = call_kwargs.get("input", "")

        # Assert grounding facts are inside the LLM input payload
        self.assertIn("Hyderabad", input_text, "LLM input must contain city name")
        self.assertIn("current_weather", input_text, "LLM input must contain intent")
        self.assertIn("temperature", input_text, "LLM input must contain temperature metric")
        self.assertIn("Open-Meteo", input_text, "LLM input must contain source attribution")

    # -------------------------------------------------------------------------
    # Test 10: 7-day forecast query — Delhi
    # -------------------------------------------------------------------------
    def test_10_forecast_7_days_delhi(self):
        """What will the weather be like for the next 7 days in Delhi?"""
        understand_output = {
            "intent": "forecast",
            "location": "Delhi",
            "city": "Delhi",
            "time_period": "next_7_days",
            "forecast_period": "next_7_days",
            "weather_variable": None,
            "requires_location": False,
        }
        mock_answer = "Delhi 7-day forecast: highs around 34°C, lows around 26°C."
        mock_client = make_mock_openai(understand_output, mock_answer)
        set_openai_client(mock_client)

        resp = client_http.post("/ask", json={"message": "What will the weather be like for the next 7 days in Delhi?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "forecast")
        self.assertIsNotNone(data["weather_data"])
        self.assertIn("forecast", data["weather_data"])
        self.assertGreater(len(data["weather_data"]["forecast"]), 0)

    # -------------------------------------------------------------------------
    # Test 11: Weekend forecast query — Chennai
    # -------------------------------------------------------------------------
    def test_11_weekend_forecast_chennai(self):
        """What will the weather be this weekend in Chennai?"""
        understand_output = {
            "intent": "forecast",
            "location": "Chennai",
            "city": "Chennai",
            "time_period": "weekend",
            "forecast_period": "weekend",
            "weather_variable": None,
            "requires_location": False,
        }
        mock_answer = "Weekend in Chennai: 32°C with high humidity."
        mock_client = make_mock_openai(understand_output, mock_answer)
        set_openai_client(mock_client)

        resp = client_http.post("/ask", json={"message": "What will the weather be this weekend in Chennai?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "forecast")
        self.assertIsNotNone(data["weather_data"])

    # -------------------------------------------------------------------------
    # Test 12: Unknown / non-weather query — 2+2
    # -------------------------------------------------------------------------
    def test_12_unknown_intent(self):
        """What is 2+2? -> returns unsupported_intent without calling weather service."""
        understand_output = {
            "intent": "unknown",
            "location": None,
            "city": None,
            "time_period": None,
            "forecast_period": None,
            "weather_variable": None,
            "requires_location": False,
        }
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.output_text = json.dumps(understand_output)
        mock_client.responses.create.return_value = mock_resp
        set_openai_client(mock_client)

        resp = client_http.post("/ask", json={"message": "What is 2+2?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "unknown")
        self.assertIsNone(data["weather_data"])
        self.assertIn("could not understand", data["answer"].lower())

    # -------------------------------------------------------------------------
    # Test 13: GPS coordinates fallback
    # -------------------------------------------------------------------------
    def test_13_gps_coordinates_fallback(self):
        """What's the weather here? with coordinates -> resolves location via GPS."""
        understand_output = {
            "intent": "current_weather",
            "location": None,
            "city": None,
            "time_period": "current",
            "forecast_period": None,
            "weather_variable": None,
            "requires_location": True,
        }
        mock_answer = "Current weather at coordinates: 27°C."
        mock_client = make_mock_openai(understand_output, mock_answer)
        set_openai_client(mock_client)

        resp = client_http.post("/ask", json={
            "message": "What's the weather here?",
            "latitude": 17.38,
            "longitude": 78.47
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "current_weather")
        self.assertIsNotNone(data["weather_data"])

    # -------------------------------------------------------------------------
    # Test 14: build_weather_context() unit test
    # -------------------------------------------------------------------------
    def test_14_build_weather_context_unit(self):
        """build_weather_context returns wind metrics for Pune without LLM."""
        query = {
            "intent": "wind",
            "location": "Pune",
            "city": "Pune",
            "time_period": "current",
            "forecast_period": None,
            "weather_variable": "wind",
            "requires_location": False,
        }
        ctx = build_weather_context(query)
        self.assertEqual(ctx["status"], "success")
        self.assertEqual(ctx["intent"], "wind")
        self.assertIn("Pune", ctx["location"])
        self.assertIn("wind_speed", ctx["weather_data"])
        self.assertEqual(ctx["source"], "Open-Meteo")

    # -------------------------------------------------------------------------
    # Test 15: Non-AI endpoint regressions
    # -------------------------------------------------------------------------
    def test_15_regression_non_ai_endpoints(self):
        """All non-AI endpoints return HTTP 200 after Sub-Phase 4.5 wiring."""
        endpoints = [
            ("GET", "/", None),
            ("GET", "/chat?message=hello", None),
            ("POST", "/ask-demo", {"message": "What is the weather in Hyderabad?"}),
            ("GET", "/weather-by-city?city=Hyderabad", None),
            ("GET", "/weather-by-location?latitude=17.38&longitude=78.47", None),
            ("GET", "/forecast?city=Delhi&period=tomorrow", None),
            ("GET", "/forecast?city=Delhi&period=next_7_days", None),
            ("GET", "/alerts?city=Hyderabad", None),
        ]
        for method, path, body in endpoints:
            with self.subTest(endpoint=path):
                if method == "GET":
                    r = client_http.get(path)
                else:
                    r = client_http.post(path, json=body)
                self.assertEqual(
                    r.status_code, 200,
                    msg=f"{method} {path} returned {r.status_code}: {r.text[:200]}"
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
