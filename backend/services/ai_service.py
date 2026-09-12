import json
import os
from typing import Tuple
from fastapi import HTTPException
try:
    from openai import (
        OpenAI,
        OpenAIError,
        RateLimitError,
        AuthenticationError,
        NotFoundError,
        APITimeoutError,
        APIConnectionError,
    )
    MODEL_NAME = "gpt-4o-mini"
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
except ImportError:
    OpenAI = None
    OpenAIError = Exception
    RateLimitError = Exception
    AuthenticationError = Exception
    NotFoundError = Exception
    APITimeoutError = Exception
    APIConnectionError = Exception
    MODEL_NAME = "gpt-4o-mini"
    client = None


def set_openai_client(custom_client):
    """Test helper to inject a mock client for automated testing without modifying production behavior."""
    global client
    client = custom_client


def get_openai_client():
    """Return the active OpenAI client instance."""
    global client
    return client


def classify_openai_error(e: Exception) -> Tuple[int, str, str]:
    """
    Classify OpenAI exceptions into (status_code, user_facing_detail, category).
    Ensures that secrets, API keys, internal URLs, and stack traces are never exposed.

    Categories:
      - 'quota_exhausted': 503 (OpenAI billing quota/credits exhausted)
      - 'rate_limit': 429 (temporary request/token rate limiting)
      - 'auth_failed': 503 (API key missing, invalid, or revoked)
      - 'model_unavailable': 503 (model not found or unavailable)
      - 'timeout': 504 (timeout communicating with OpenAI)
      - 'connection_error': 503 (network connection issue)
      - 'provider_error': 503 (generic upstream OpenAI API error)
    """
    # 1. RateLimitError & Quota Exhaustion
    if isinstance(e, RateLimitError):
        code = getattr(e, "code", None)
        body = getattr(e, "body", {}) or {}
        err_type = body.get("type") if isinstance(body, dict) else None
        err_code = body.get("code") if isinstance(body, dict) else None
        msg = str(getattr(e, "message", "")).lower()

        if (
            code in ("credit_balance_exhausted", "insufficient_quota")
            or err_code in ("credit_balance_exhausted", "insufficient_quota")
            or err_type == "insufficient_quota"
            or "credit" in msg
            or "quota" in msg
        ):
            return (
                503,
                "AI service temporarily unavailable: OpenAI quota or credit balance is exhausted.",
                "quota_exhausted",
            )
        return (
            429,
            "AI service rate limit reached. Please retry after a brief pause.",
            "rate_limit",
        )

    # 2. Authentication failure
    if isinstance(e, AuthenticationError):
        return (
            503,
            "AI service authentication failed: configured API key is invalid or revoked.",
            "auth_failed",
        )

    # 3. Model or resource unavailable
    if isinstance(e, NotFoundError):
        return (
            503,
            "AI service model or provider resource is currently unavailable.",
            "model_unavailable",
        )

    # 4. Timeout
    if isinstance(e, APITimeoutError):
        return (
            504,
            "AI service request timed out while contacting the AI provider.",
            "timeout",
        )

    # 5. Connection Error
    if isinstance(e, APIConnectionError):
        return (
            503,
            "AI service network connection error while contacting the AI provider.",
            "connection_error",
        )

    # 6. Other OpenAI provider errors
    if isinstance(e, OpenAIError):
        return (
            503,
            "AI service error: unexpected response from the AI provider.",
            "provider_error",
        )

    # 7. Fallback unexpected error
    return (
        500,
        "An unexpected error occurred in the AI service.",
        "unexpected_error",
    )


def get_ai_test(message: str):
    """
    Diagnostic endpoint handler for OpenAI status.
    Distinguishes between:
      - OpenAI configured and working
      - OpenAI authenticated but quota exhausted
      - OpenAI authentication failed
      - OpenAI provider/model unavailable
      - unexpected AI provider error
    Never exposes API keys or internal stack traces.
    """
    if not client or not getattr(client, "api_key", None):
        return {
            "status": "error",
            "diagnostic": "OpenAI authentication failed",
            "report": "authentication failed",
            "detail": "AI service authentication failed: configured API key is missing.",
        }

    try:
        response = client.responses.create(
            model=MODEL_NAME,
            input=message,
        )
        return {
            "status": "ok",
            "diagnostic": "OpenAI configured and working",
            "report": "working",
            "question": message,
            "answer": response.output_text,
        }
    except Exception as e:
        status_code, detail, category = classify_openai_error(e)
        if category == "quota_exhausted":
            diagnostic = "OpenAI authenticated but quota exhausted"
            report = "quota unavailable"
        elif category == "auth_failed":
            diagnostic = "OpenAI authentication failed"
            report = "authentication failed"
        elif category in ("model_unavailable", "connection_error", "timeout"):
            diagnostic = "OpenAI provider/model unavailable"
            report = "provider/model unavailable"
        else:
            diagnostic = "unexpected AI provider error"
            report = "unexpected AI provider error"

        return {
            "status": "error",
            "diagnostic": diagnostic,
            "report": report,
            "detail": detail,
        }


SUPPORTED_INTENTS = {
    "current_weather",
    "forecast",
    "rain",
    "temperature",
    "humidity",
    "wind",
    "advisory",
    "alerts",
    "farmer_advisory",
    "travel_advisory",
    "general_weather",
    "unknown",
}

SUPPORTED_TIME_PERIODS = {
    "current",
    "today",
    "tomorrow",
    "next_3_days",
    "this_week",
    "next_7_days",
    "weekend",
    "hourly",
    "unknown",
}

SUPPORTED_WEATHER_VARIABLES = {
    "temperature",
    "feels_like",
    "humidity",
    "precipitation",
    "rainfall",
    "wind",
    "conditions",
    "general_weather",
    "unknown",
}


def validate_and_normalize_query(data: dict) -> dict:
    """
    Validates and normalizes structured query understanding output.
    Ensures:
      - intent is a recognized supported intent
      - location and city are strings or None, and kept in sync
      - time_period and forecast_period are recognized periods or None, and kept in sync
      - weather_variable is recognized or None
      - requires_location is a boolean
    """
    if not isinstance(data, dict):
        raise ValueError("Query understanding output must be a dictionary.")

    # 1. Intent validation
    intent = str(data.get("intent", "unknown")).strip().lower()
    if intent not in SUPPORTED_INTENTS:
        intent = "unknown"

    # 2. Location / City validation & normalization
    location = data.get("location") or data.get("city")
    if location is not None:
        location = str(location).strip()
        for prefix in ["in ", "at ", "around ", "near ", "for "]:
            if location.lower().startswith(prefix):
                location = location[len(prefix):].strip()
        if not location or location.lower() in ("null", "none", "unknown"):
            location = None
    city = location  # Keep both in sync for backwards and forwards compatibility

    # 3. Time period / Forecast period validation & normalization
    period = data.get("time_period") or data.get("forecast_period")
    if period is not None:
        period = str(period).strip().lower()
        if period not in SUPPORTED_TIME_PERIODS or period in ("null", "none"):
            period = None
    time_period = period
    forecast_period = period or ("next_7_days" if intent in ("forecast", "rain") else None)

    # 4. Weather variable validation & normalization
    var = data.get("weather_variable")
    if var is not None:
        var = str(var).strip().lower()
        if var not in SUPPORTED_WEATHER_VARIABLES or var in ("null", "none"):
            var = None
    weather_variable = var

    # 5. Requires location determination
    requires_loc = data.get("requires_location")
    if requires_loc is None:
        requires_loc = location is None and intent != "unknown"
    else:
        requires_loc = bool(requires_loc)

    return {
        "intent": intent,
        "location": location,
        "city": city,
        "time_period": time_period,
        "forecast_period": forecast_period,
        "weather_variable": weather_variable,
        "requires_location": requires_loc,
    }


def understand_query(message: str) -> str:
    """
    Analyzes a user's natural-language query and returns a validated JSON string
    containing structured intent, location, time period, and weather variable.
    """
    if not message or not str(message).strip():
        return json.dumps({
            "intent": "unknown",
            "location": None,
            "city": None,
            "time_period": None,
            "forecast_period": None,
            "weather_variable": None,
            "requires_location": False,
        })
    if not client:
        raise HTTPException(
            status_code=503,
            detail="OpenAI client not configured. Please set OPENAI_API_KEY in backend/.env to enable the /ask pipeline."
        )
    try:
        response = client.responses.create(
            model=MODEL_NAME,
            instructions="""
            You are the query understanding engine of WeatherGPT.

            Understand the user's weather-related question.

            Return ONLY valid JSON in this exact format:

            {
                "intent": "forecast",
                "location": "Hyderabad",
                "city": "Hyderabad",
                "time_period": "tomorrow",
                "forecast_period": "tomorrow",
                "weather_variable": "precipitation",
                "requires_location": false
            }

            Supported intents:
            - current_weather: general current weather inquiries
            - forecast: general upcoming or future weather inquiries
            - rain: questions specifically about rain, precipitation, showers, or storms
            - temperature: questions specifically about temperature, heat, or cold
            - humidity: questions specifically about humidity or dampness
            - wind: questions specifically about wind speed, windiness, or breeze
            - advisory: questions asking for guidance (e.g. carry umbrella, travel safety, farming)
            - alerts: questions asking for weather warnings, alerts, or hazards
            - general_weather: broad or open-ended weather inquiries
            - unknown: non-weather questions

            Supported time_period / forecast_period values:
            - current
            - today
            - tomorrow
            - next_3_days
            - this_week
            - next_7_days
            - weekend
            - hourly
            - unknown

            Supported weather_variable values:
            - temperature
            - feels_like
            - humidity
            - precipitation
            - rainfall
            - wind
            - conditions
            - general_weather

            Rules:
            1. If a city or location name is mentioned:
               Extract the exact location string. Set "location" and "city" to that string.
               Set "requires_location": false.
               Do NOT validate whether the location exists; simply extract the user's string.
            2. If the user refers to their current location (e.g. "here", "my location", "where I am", "around here"):
               Set "location": null, "city": null, and "requires_location": true.
            3. If no city is mentioned and location is required to answer:
               Set "location": null, "city": null, and "requires_location": true.
               Do NOT invent or assume a location.
            4. If intent is non-weather ("unknown"):
               Set "intent": "unknown", "location": null, "city": null, "time_period": null, "forecast_period": null, "weather_variable": null, and "requires_location": false.
            5. Set "weather_variable" to the specific variable asked about (e.g., "precipitation" for rain questions, "temperature" for temperature questions, "wind" for wind questions), or null if general.

            Do not answer the user's question.
            Only identify the intent, location, time_period, weather_variable, and requires_location.
            Return ONLY raw JSON without markdown fences.
            """,
            input=message,
        )
        raw_text = response.output_text.strip()
        # Clean potential markdown fences
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            raw_text = "\n".join(lines).strip()

        parsed = json.loads(raw_text)
        validated = validate_and_normalize_query(parsed)
        return json.dumps(validated)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="AI returned invalid JSON in query understanding.",
        )
    except HTTPException:
        raise
    except Exception as e:
        status_code, detail, _ = classify_openai_error(e)
        raise HTTPException(
            status_code=status_code,
            detail=detail,
        )

def get_final_answer(message: str, weather_data: dict):
    if not client:
        raise HTTPException(
            status_code=503,
            detail="OpenAI client not configured. Please set OPENAI_API_KEY in backend/.env to enable the /ask pipeline."
        )
    try:
        response = client.responses.create(
            model=MODEL_NAME,
            instructions="""
            You are WeatherGPT, an intelligent weather assistant.

            Answer the user's question using ONLY the retrieved weather context provided to you.

            STRICT GROUNDING RULES:
            - Use the supplied weather context as the sole source of truth.
            - Ground your answer strictly in the provided data.
            - Do NOT invent temperature, rainfall amounts, rain probabilities, wind speeds, weather conditions, locations, or dates.
            - Do not claim unavailable weather information; if context or data is insufficient, say so clearly.
            - If forecast data is provided, explain the requested period (today, tomorrow, weekend, 7-day, hourly) naturally.
            - Include specific numbers from the data: high/low temperatures, rain probability %, rainfall (mm), and wind speeds where relevant.
            - If alerts are provided, clearly explain them.
            - Do NOT claim that data or computed alerts are official IMD (India Meteorological Department) warnings.
            - Attribute the data to the active provider in the context (e.g. Open-Meteo) when asked or relevant.
            - Give a clear, helpful, and concise answer.
            """,
            input=f"""
            User question:
            {message}

            Weather context:
            {json.dumps(weather_data)}
            """
        )
        return response.output_text
    except Exception as e:
        status_code, detail, _ = classify_openai_error(e)
        raise HTTPException(
            status_code=status_code,
            detail=detail,
        )
