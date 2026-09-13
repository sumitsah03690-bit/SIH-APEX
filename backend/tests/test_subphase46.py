"""
Sub-Phase 4.6 Test Suite — Realistic Weather Questions & Grounding Reliability
Tests /ask across a comprehensive set of real-world weather questions.
Verifies:
  - Current weather questions (Hyderabad, Warangal, Bengaluru, Chennai, Pune)
  - Forecast questions (Delhi tomorrow, Mumbai rain, Hyderabad 3-day, Chennai weekend, Pune 7-day)
  - Specific weather variables (temperature, humidity, rain probability, wind, feels-like)
  - Advisory questions (umbrella, travel safety, outdoor guidance)
  - Natural-language variations & normalization
  - Missing location handling (no arbitrary default city, no fake weather)
  - Invalid location handling (HTTP 404, no fake weather)
  - Non-weather / unsupported queries (unknown intent, clean handling)
  - LLM input grounding assertion (actual weather context in prompt payload)
  - Anti-fabrication safeguards
  - Weather data consistency between QueryUnderstanding & Weather Context
  - Structured response contract validation
  - Regression for all baseline non-AI endpoints
"""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, ".env"))

from fastapi.testclient import TestClient
from main import app
from services.ai_service import set_openai_client, get_openai_client
from services.weather_context import build_weather_context

client_http = TestClient(app)


def make_mock_openai(understand_dict: dict, final_answer: str = "Mocked natural weather answer."):
    """
    Factory creating a mock OpenAI client that:
      Call 1 (understand_query): returns understand_dict serialized as JSON
      Call 2 (get_final_answer): returns final_answer string
    """
    call_count = [0]

    def side_effect(**kwargs):
        call_count[0] += 1
        resp = MagicMock()
        if call_count[0] == 1:
            resp.output_text = json.dumps(understand_dict)
        else:
            resp.output_text = final_answer
        return resp

    mock_client = MagicMock()
    mock_client.responses.create.side_effect = side_effect
    return mock_client


class TestSubPhase46RealWeatherQuestions(unittest.TestCase):

    def setUp(self):
        self._real_client = get_openai_client()

    def tearDown(self):
        set_openai_client(self._real_client)

    # =========================================================================
    # Step 3: Current Weather Questions
    # =========================================================================

    def test_01_current_weather_hyderabad(self):
        """Step 3.1: 'What's the weather in Hyderabad?' -> grounded current weather."""
        q = {
            "intent": "current_weather",
            "location": "Hyderabad",
            "city": "Hyderabad",
            "time_period": "current",
            "forecast_period": None,
            "weather_variable": None,
            "requires_location": False,
        }
        set_openai_client(make_mock_openai(q, "Current weather in Hyderabad is 25°C."))
        resp = client_http.post("/ask", json={"message": "What's the weather in Hyderabad?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "current_weather")
        self.assertIn("Hyderabad", data["city"])
        self.assertIsNotNone(data["weather_data"])
        self.assertIn("temperature", data["weather_data"])
        self.assertEqual(data["source"], "Open-Meteo")

    def test_02_current_weather_warangal(self):
        """Step 3.2: 'How is the weather in Warangal right now?' -> geocodes Warangal, returns current weather."""
        q = {
            "intent": "current_weather",
            "location": "Warangal",
            "city": "Warangal",
            "time_period": "current",
            "forecast_period": None,
            "weather_variable": None,
            "requires_location": False,
        }
        set_openai_client(make_mock_openai(q, "Current weather in Warangal is warm."))
        resp = client_http.post("/ask", json={"message": "How is the weather in Warangal right now?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "current_weather")
        self.assertIn("Warangal", data["city"])
        self.assertIsNotNone(data["weather_data"])
        self.assertEqual(data["source"], "Open-Meteo")

    def test_03_current_temperature_bengaluru(self):
        """Step 3.3: 'What is the temperature in Bengaluru?' -> returns temperature metrics for Bengaluru."""
        q = {
            "intent": "temperature",
            "location": "Bengaluru",
            "city": "Bengaluru",
            "time_period": "current",
            "forecast_period": None,
            "weather_variable": "temperature",
            "requires_location": False,
        }
        set_openai_client(make_mock_openai(q, "The temperature in Bengaluru is 22°C."))
        resp = client_http.post("/ask", json={"message": "What is the temperature in Bengaluru?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "temperature")
        self.assertIn("Bengaluru", data["city"])
        self.assertIn("temperature", data["weather_data"])

    def test_04_current_humidity_chennai(self):
        """Step 3.4: 'How humid is Chennai?' -> returns humidity metric for Chennai."""
        q = {
            "intent": "humidity",
            "location": "Chennai",
            "city": "Chennai",
            "time_period": "current",
            "forecast_period": None,
            "weather_variable": "humidity",
            "requires_location": False,
        }
        set_openai_client(make_mock_openai(q, "Relative humidity in Chennai is high at 88%."))
        resp = client_http.post("/ask", json={"message": "How humid is Chennai?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "humidity")
        self.assertIn("humidity", data["weather_data"])
        self.assertEqual(data["weather_data"].get("unit"), "%")

    def test_05_current_wind_pune(self):
        """Step 3.5: 'Is it windy in Pune?' -> returns wind metrics for Pune."""
        q = {
            "intent": "wind",
            "location": "Pune",
            "city": "Pune",
            "time_period": "current",
            "forecast_period": None,
            "weather_variable": "wind",
            "requires_location": False,
        }
        set_openai_client(make_mock_openai(q, "Wind in Pune is around 8 km/h."))
        resp = client_http.post("/ask", json={"message": "Is it windy in Pune?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "wind")
        self.assertIn("wind_speed", data["weather_data"])

    # =========================================================================
    # Step 4: Forecast Questions
    # =========================================================================

    def test_06_forecast_tomorrow_delhi(self):
        """Step 4.1: 'What's the weather tomorrow in Delhi?' -> forecast data for tomorrow."""
        q = {
            "intent": "forecast",
            "location": "Delhi",
            "city": "Delhi",
            "time_period": "tomorrow",
            "forecast_period": "tomorrow",
            "weather_variable": None,
            "requires_location": False,
        }
        set_openai_client(make_mock_openai(q, "Tomorrow in Delhi will be cloudy with highs near 33°C."))
        resp = client_http.post("/ask", json={"message": "What's the weather tomorrow in Delhi?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "forecast")
        self.assertEqual(data["time_period"], "tomorrow")
        self.assertIn("forecast", data["weather_data"])

    def test_07_forecast_rain_tomorrow_mumbai(self):
        """Step 4.2: 'Will it rain tomorrow in Mumbai?' -> rain forecast for Mumbai tomorrow."""
        q = {
            "intent": "rain",
            "location": "Mumbai",
            "city": "Mumbai",
            "time_period": "tomorrow",
            "forecast_period": "tomorrow",
            "weather_variable": "precipitation",
            "requires_location": False,
        }
        set_openai_client(make_mock_openai(q, "Rain probability in Mumbai tomorrow is 40%."))
        resp = client_http.post("/ask", json={"message": "Will it rain tomorrow in Mumbai?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "rain")
        self.assertIn("precipitation_data", data["weather_data"])

    def test_08_forecast_next_3_days_hyderabad(self):
        """Step 4.3: 'What's the forecast for Hyderabad for the next 3 days?' -> 3-day forecast."""
        q = {
            "intent": "forecast",
            "location": "Hyderabad",
            "city": "Hyderabad",
            "time_period": "next_3_days",
            "forecast_period": "next_3_days",
            "weather_variable": None,
            "requires_location": False,
        }
        set_openai_client(make_mock_openai(q, "Hyderabad 3-day forecast: highs around 31°C."))
        resp = client_http.post("/ask", json={"message": "What's the forecast for Hyderabad for the next 3 days?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["time_period"], "next_3_days")
        self.assertIn("forecast", data["weather_data"])

    def test_09_forecast_weekend_chennai(self):
        """Step 4.4: 'What will the weather be like this weekend in Chennai?' -> weekend forecast."""
        q = {
            "intent": "forecast",
            "location": "Chennai",
            "city": "Chennai",
            "time_period": "weekend",
            "forecast_period": "weekend",
            "weather_variable": None,
            "requires_location": False,
        }
        set_openai_client(make_mock_openai(q, "This weekend in Chennai will be warm."))
        resp = client_http.post("/ask", json={"message": "What will the weather be like this weekend in Chennai?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["time_period"], "weekend")
        self.assertIn("forecast", data["weather_data"])

    def test_10_forecast_next_7_days_pune(self):
        """Step 4.5: 'Give me the weather forecast for the next 7 days in Pune.' -> 7-day forecast."""
        q = {
            "intent": "forecast",
            "location": "Pune",
            "city": "Pune",
            "time_period": "next_7_days",
            "forecast_period": "next_7_days",
            "weather_variable": None,
            "requires_location": False,
        }
        set_openai_client(make_mock_openai(q, "Pune 7-day forecast shows highs between 27°C and 30°C."))
        resp = client_http.post("/ask", json={"message": "Give me the weather forecast for the next 7 days in Pune."})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["time_period"], "next_7_days")
        self.assertIn("forecast", data["weather_data"])
        self.assertGreaterEqual(len(data["weather_data"]["forecast"]), 7)

    # =========================================================================
    # Step 5: Specific Weather Variables
    # =========================================================================

    def test_11_variable_temperature_tomorrow_delhi(self):
        """Step 5.1: 'How hot will it be tomorrow in Delhi?' -> temperature forecast for tomorrow."""
        q = {
            "intent": "temperature",
            "location": "Delhi",
            "city": "Delhi",
            "time_period": "tomorrow",
            "forecast_period": "tomorrow",
            "weather_variable": "temperature",
            "requires_location": False,
        }
        set_openai_client(make_mock_openai(q, "Tomorrow's maximum temperature in Delhi will reach 34°C."))
        resp = client_http.post("/ask", json={"message": "How hot will it be tomorrow in Delhi?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "temperature")
        self.assertIn("temperatures", data["weather_data"])

    def test_12_variable_humidity_tomorrow_chennai(self):
        """Step 5.2: 'Will humidity be high tomorrow in Chennai?' -> humidity/forecast data for tomorrow."""
        q = {
            "intent": "humidity",
            "location": "Chennai",
            "city": "Chennai",
            "time_period": "tomorrow",
            "forecast_period": "tomorrow",
            "weather_variable": "humidity",
            "requires_location": False,
        }
        set_openai_client(make_mock_openai(q, "Tomorrow in Chennai humidity is expected to remain high."))
        resp = client_http.post("/ask", json={"message": "Will humidity be high tomorrow in Chennai?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "humidity")
        self.assertIsNotNone(data["weather_data"])

    def test_13_variable_rain_weekend_delhi(self):
        """Step 5.3: 'What's the chance of rain this weekend in Delhi?' -> rain probabilities for weekend."""
        q = {
            "intent": "rain",
            "location": "Delhi",
            "city": "Delhi",
            "time_period": "weekend",
            "forecast_period": "weekend",
            "weather_variable": "precipitation",
            "requires_location": False,
        }
        set_openai_client(make_mock_openai(q, "Rain probability in Delhi this weekend is around 50%."))
        resp = client_http.post("/ask", json={"message": "What's the chance of rain this weekend in Delhi?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "rain")
        self.assertIn("precipitation_data", data["weather_data"])

    def test_14_variable_wind_tomorrow_mumbai(self):
        """Step 5.4: 'Will it be windy tomorrow in Mumbai?' -> wind forecast data for Mumbai."""
        q = {
            "intent": "wind",
            "location": "Mumbai",
            "city": "Mumbai",
            "time_period": "tomorrow",
            "forecast_period": "tomorrow",
            "weather_variable": "wind",
            "requires_location": False,
        }
        set_openai_client(make_mock_openai(q, "Maximum wind speed in Mumbai tomorrow is projected at 18 km/h."))
        resp = client_http.post("/ask", json={"message": "Will it be windy tomorrow in Mumbai?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "wind")
        self.assertIn("wind_data", data["weather_data"])

    def test_15_variable_feels_like_hyderabad(self):
        """Step 5.5: 'How does it actually feel outside in Hyderabad?' -> apparent temperature in context."""
        q = {
            "intent": "temperature",
            "location": "Hyderabad",
            "city": "Hyderabad",
            "time_period": "current",
            "forecast_period": None,
            "weather_variable": "feels_like",
            "requires_location": False,
        }
        set_openai_client(make_mock_openai(q, "It feels like 29°C in Hyderabad."))
        resp = client_http.post("/ask", json={"message": "How does it actually feel outside in Hyderabad?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("apparent_temperature", data["weather_data"])

    # =========================================================================
    # Step 6: Advisory Questions
    # =========================================================================

    def test_16_advisory_umbrella_tomorrow_hyderabad(self):
        """Step 6.1: 'Should I carry an umbrella tomorrow in Hyderabad?' -> advisory with forecast & alerts."""
        q = {
            "intent": "advisory",
            "location": "Hyderabad",
            "city": "Hyderabad",
            "time_period": "tomorrow",
            "forecast_period": "tomorrow",
            "weather_variable": "precipitation",
            "requires_location": False,
        }
        set_openai_client(make_mock_openai(q, "With 20% rain probability, carrying an umbrella is optional."))
        resp = client_http.post("/ask", json={"message": "Should I carry an umbrella tomorrow in Hyderabad?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "advisory")
        self.assertIn("forecast", data["weather_data"])
        self.assertIn("alerts", data["weather_data"])

    def test_17_advisory_travel_delhi(self):
        """Step 6.2: 'Is it safe to travel tomorrow in Delhi based on the weather?' -> travel advisory."""
        q = {
            "intent": "travel_advisory",
            "location": "Delhi",
            "city": "Delhi",
            "time_period": "tomorrow",
            "forecast_period": "tomorrow",
            "weather_variable": None,
            "requires_location": False,
        }
        set_openai_client(make_mock_openai(q, "Travel conditions in Delhi are generally clear with scattered showers."))
        resp = client_http.post("/ask", json={"message": "Is it safe to travel tomorrow in Delhi based on the weather?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "travel_advisory")
        self.assertIn("forecast", data["weather_data"])

    def test_18_advisory_afternoon_mumbai(self):
        """Step 6.3: 'Should I avoid going outside this afternoon in Mumbai?' -> general weather advisory."""
        q = {
            "intent": "advisory",
            "location": "Mumbai",
            "city": "Mumbai",
            "time_period": "today",
            "forecast_period": "today",
            "weather_variable": None,
            "requires_location": False,
        }
        set_openai_client(make_mock_openai(q, "Temperatures are around 28°C; stay hydrated if outside."))
        resp = client_http.post("/ask", json={"message": "Should I avoid going outside this afternoon in Mumbai?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "advisory")

    # =========================================================================
    # Step 7: Natural-Language Variations
    # =========================================================================

    def test_19_variation_whats_it_like_hyderabad(self):
        """Step 7.1: 'What's it like outside in Hyderabad?' -> current_weather intent."""
        q = {
            "intent": "current_weather",
            "location": "Hyderabad",
            "city": "Hyderabad",
            "time_period": "current",
            "forecast_period": None,
            "weather_variable": None,
            "requires_location": False,
        }
        set_openai_client(make_mock_openai(q, "It is currently 25°C outside in Hyderabad."))
        resp = client_http.post("/ask", json={"message": "What's it like outside in Hyderabad?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "current_weather")

    def test_20_variation_need_umbrella_hyderabad(self):
        """Step 7.2: 'Do I need an umbrella tomorrow in Hyderabad?' -> advisory intent."""
        q = {
            "intent": "advisory",
            "location": "Hyderabad",
            "city": "Hyderabad",
            "time_period": "tomorrow",
            "forecast_period": "tomorrow",
            "weather_variable": "precipitation",
            "requires_location": False,
        }
        set_openai_client(make_mock_openai(q, "You likely will not need an umbrella tomorrow."))
        resp = client_http.post("/ask", json={"message": "Do I need an umbrella tomorrow in Hyderabad?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "advisory")

    def test_21_variation_hyderabad_today(self):
        """Step 7.3: 'How's Hyderabad weather today?' -> current_weather / today."""
        q = {
            "intent": "current_weather",
            "location": "Hyderabad",
            "city": "Hyderabad",
            "time_period": "today",
            "forecast_period": "today",
            "weather_variable": None,
            "requires_location": False,
        }
        set_openai_client(make_mock_openai(q, "Today's weather in Hyderabad is pleasant."))
        resp = client_http.post("/ask", json={"message": "How's Hyderabad weather today?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("Hyderabad", data["city"])

    def test_22_variation_rain_tomorrow_hyderabad(self):
        """Step 7.4: 'Is Hyderabad going to get rain tomorrow?' -> rain intent."""
        q = {
            "intent": "rain",
            "location": "Hyderabad",
            "city": "Hyderabad",
            "time_period": "tomorrow",
            "forecast_period": "tomorrow",
            "weather_variable": "precipitation",
            "requires_location": False,
        }
        set_openai_client(make_mock_openai(q, "Moderate chance of scattered rain tomorrow in Hyderabad."))
        resp = client_http.post("/ask", json={"message": "Is Hyderabad going to get rain tomorrow?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "rain")

    def test_23_variation_hot_tomorrow_hyderabad(self):
        """Step 7.5: 'Will Hyderabad be hot tomorrow?' -> temperature intent."""
        q = {
            "intent": "temperature",
            "location": "Hyderabad",
            "city": "Hyderabad",
            "time_period": "tomorrow",
            "forecast_period": "tomorrow",
            "weather_variable": "temperature",
            "requires_location": False,
        }
        set_openai_client(make_mock_openai(q, "Hyderabad will be moderately warm tomorrow with highs near 31°C."))
        resp = client_http.post("/ask", json={"message": "Will Hyderabad be hot tomorrow?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "temperature")

    # =========================================================================
    # Step 8: Missing Location Questions
    # =========================================================================

    def test_24_missing_location_general(self):
        """Step 8.1: 'What's the weather?' -> returns location_required without inventing a city."""
        q = {
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
        mock_resp.output_text = json.dumps(q)
        mock_client.responses.create.return_value = mock_resp
        set_openai_client(mock_client)

        resp = client_http.post("/ask", json={"message": "What's the weather?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsNone(data["city"])
        self.assertIn("Location is required", data["answer"])
        self.assertIsNone(data["weather_data"])
        # Verify LLM final answer was NOT called (only 1 call for understand_query)
        self.assertEqual(mock_client.responses.create.call_count, 1)

    def test_25_missing_location_rain(self):
        """Step 8.2: 'Will it rain tomorrow?' -> location_required, no default city selected."""
        q = {
            "intent": "rain",
            "location": None,
            "city": None,
            "time_period": "tomorrow",
            "forecast_period": "tomorrow",
            "weather_variable": "precipitation",
            "requires_location": True,
        }
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.output_text = json.dumps(q)
        mock_client.responses.create.return_value = mock_resp
        set_openai_client(mock_client)

        resp = client_http.post("/ask", json={"message": "Will it rain tomorrow?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsNone(data["city"])
        self.assertIn("Location is required", data["answer"])
        self.assertEqual(mock_client.responses.create.call_count, 1)

    def test_26_missing_location_temperature(self):
        """Step 8.3: 'What's the temperature?' -> location_required, weather service not called."""
        q = {
            "intent": "temperature",
            "location": None,
            "city": None,
            "time_period": "current",
            "forecast_period": None,
            "weather_variable": "temperature",
            "requires_location": True,
        }
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.output_text = json.dumps(q)
        mock_client.responses.create.return_value = mock_resp
        set_openai_client(mock_client)

        resp = client_http.post("/ask", json={"message": "What's the temperature?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsNone(data["city"])
        self.assertIsNone(data["weather_data"])
        self.assertEqual(mock_client.responses.create.call_count, 1)

    # =========================================================================
    # Step 9: Invalid Location Questions
    # =========================================================================

    def test_27_invalid_location_xyz(self):
        """Step 9: 'What's the weather in InvalidLocationXYZ123456?' -> HTTP 404 City not found."""
        q = {
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
        mock_resp.output_text = json.dumps(q)
        mock_client.responses.create.return_value = mock_resp
        set_openai_client(mock_client)

        resp = client_http.post("/ask", json={"message": "What's the weather in InvalidLocationXYZ123456?"})
        self.assertEqual(resp.status_code, 404)
        self.assertIn("City not found", resp.json().get("detail", ""))

    # =========================================================================
    # Step 10: Non-Weather Questions
    # =========================================================================

    def test_28_non_weather_math(self):
        """Step 10.1: 'What is 2+2?' -> unsupported_intent, weather service not called."""
        q = {
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
        mock_resp.output_text = json.dumps(q)
        mock_client.responses.create.return_value = mock_resp
        set_openai_client(mock_client)

        resp = client_http.post("/ask", json={"message": "What is 2+2?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "unknown")
        self.assertIsNone(data["weather_data"])
        self.assertIn("could not understand", data["answer"].lower())

    def test_29_non_weather_politics(self):
        """Step 10.2: 'Who is the Prime Minister?' -> unknown intent, no weather context."""
        q = {
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
        mock_resp.output_text = json.dumps(q)
        mock_client.responses.create.return_value = mock_resp
        set_openai_client(mock_client)

        resp = client_http.post("/ask", json={"message": "Who is the Prime Minister?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "unknown")
        self.assertIsNone(data["weather_data"])

    def test_30_non_weather_joke(self):
        """Step 10.3: 'Tell me a joke.' -> unknown intent, unsupported prompt."""
        q = {
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
        mock_resp.output_text = json.dumps(q)
        mock_client.responses.create.return_value = mock_resp
        set_openai_client(mock_client)

        resp = client_http.post("/ask", json={"message": "Tell me a joke."})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "unknown")
        self.assertIsNone(data["weather_data"])

    # =========================================================================
    # Step 11: Context Grounding Assertion
    # =========================================================================

    def test_31_grounding_assertion_llm_input(self):
        """Step 11: Inspect LLM input kwargs to verify real weather metrics reach the final LLM prompt."""
        q = {
            "intent": "current_weather",
            "location": "Bengaluru",
            "city": "Bengaluru",
            "time_period": "current",
            "forecast_period": None,
            "weather_variable": None,
            "requires_location": False,
        }
        mock_client = make_mock_openai(q, "Grounded final response.")
        set_openai_client(mock_client)

        resp = client_http.post("/ask", json={"message": "What is the temperature in Bengaluru?"})
        self.assertEqual(resp.status_code, 200)

        # Must make 2 calls (understand_query + get_final_answer)
        self.assertEqual(mock_client.responses.create.call_count, 2)

        # Inspect the 2nd call's input
        second_call = mock_client.responses.create.call_args_list[1]
        input_text = second_call.kwargs.get("input", "")

        # Verify key grounding facts are present in the LLM input
        self.assertIn("Bengaluru", input_text, "LLM input must contain city name")
        self.assertIn("current_weather", input_text, "LLM input must contain intent")
        self.assertIn("temperature", input_text, "LLM input must contain temperature data")
        self.assertIn("Open-Meteo", input_text, "LLM input must contain provider source")

    # =========================================================================
    # Step 12: Anti-Fabrication Safeguards
    # =========================================================================

    def test_32_no_fabrication_on_geocoding_failure(self):
        """Step 12.1: Geocoding failure raises 404; zero imaginary weather is produced."""
        from services.weather_context import build_weather_context
        from fastapi import HTTPException

        q = {
            "intent": "current_weather",
            "location": "NonExistentCity998877",
            "city": "NonExistentCity998877",
            "time_period": "current",
        }
        with self.assertRaises(HTTPException) as cm:
            build_weather_context(q)
        self.assertEqual(cm.exception.status_code, 404)

    def test_33_no_fabrication_on_missing_location(self):
        """Step 12.2: Missing location query returns location_required, zero weather metrics."""
        q = {
            "intent": "forecast",
            "location": None,
            "city": None,
            "time_period": "tomorrow",
            "forecast_period": "tomorrow",
            "requires_location": True,
        }
        ctx = build_weather_context(q)
        self.assertEqual(ctx["status"], "location_required")
        self.assertIsNone(ctx["weather_data"])
        self.assertIsNone(ctx["location"])

    # =========================================================================
    # Step 14: Weather Data Consistency
    # =========================================================================

    def test_34_weather_data_consistency(self):
        """Step 14: Verify consistency between QueryUnderstanding location/period and Weather Context."""
        q = {
            "intent": "rain",
            "location": "Delhi",
            "city": "Delhi",
            "time_period": "tomorrow",
            "forecast_period": "tomorrow",
            "weather_variable": "precipitation",
            "requires_location": False,
        }
        ctx = build_weather_context(q)
        self.assertEqual(ctx["status"], "success")
        self.assertEqual(ctx["intent"], q["intent"])
        self.assertIn("Delhi", ctx["location"])
        self.assertEqual(ctx["time_period"], "tomorrow")
        self.assertIn("precipitation_data", ctx["weather_data"])

    # =========================================================================
    # Step 15: Response Contract Validation
    # =========================================================================

    def test_35_response_contract_fields_and_types(self):
        """Step 15: Verify all required contract fields exist and match expected types."""
        q = {
            "intent": "current_weather",
            "location": "Hyderabad",
            "city": "Hyderabad",
            "time_period": "current",
            "forecast_period": None,
            "weather_variable": None,
            "requires_location": False,
        }
        set_openai_client(make_mock_openai(q, "Pleasant weather in Hyderabad."))
        resp = client_http.post("/ask", json={"message": "What is the weather in Hyderabad?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # Check required top-level contract keys
        required_keys = ["question", "intent", "city", "time_period", "weather_variable", "answer", "weather_data", "source"]
        for k in required_keys:
            self.assertIn(k, data, f"Missing contract key: {k}")

        self.assertIsInstance(data["question"], str)
        self.assertIsInstance(data["intent"], str)
        self.assertIsInstance(data["city"], str)
        self.assertIsInstance(data["answer"], str)
        self.assertIsInstance(data["weather_data"], dict)
        self.assertEqual(data["source"], "Open-Meteo")

    # =========================================================================
    # Step 16: Baseline Regression Tests
    # =========================================================================

    def test_36_regression_all_non_ai_endpoints(self):
        """Step 16: Verify all baseline non-AI endpoints continue returning HTTP 200."""
        endpoints = [
            ("GET", "/", None),
            ("GET", "/chat?message=hello", None),
            ("POST", "/ask-demo", {"message": "What is the weather in Hyderabad?"}),
            ("GET", "/weather-by-city?city=Hyderabad", None),
            ("GET", "/weather-by-location?latitude=17.38&longitude=78.47", None),
            ("GET", "/forecast?city=Delhi&period=tomorrow", None),
            ("GET", "/forecast?city=Delhi&period=next_7_days", None),
            ("GET", "/alerts?city=Hyderabad", None),
            ("GET", "/ai-test?message=ping", None),
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
