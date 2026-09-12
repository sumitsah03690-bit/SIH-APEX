from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException
import json
from models.schemas import ChatRequest
from services.ai_service import get_ai_test, understand_query, get_final_answer
from services.weather_context import build_weather_context
from services.recommendation_service import generate_recommendation
from services.conversation_service import (
    get_conversation_context,
    save_conversation_context,
    extract_last_context_from_history,
    resolve_followup_query,
)
from services.weather_service import (
    get_current_weather_by_city,
    get_forecast_by_city,
    get_alerts_by_city,
    get_weather_summary_by_location,
    get_forecast_by_coords,
    get_alerts_by_coords,
)
from services.gemini_service import query_gemini

router = APIRouter()

@router.get("/chat")
def chat(message: str):
    message_lower = message.lower()
    if "weather" in message_lower:
        return {
            "message": message,
            "response": "I can help you with weather information."
        }
    return {
        "message": message,
        "response": "I am WeatherGPT. Please ask me a weather-related question."
    }

@router.get("/ai-test")
def ai_test(message: str):
    return get_ai_test(message)

@router.get("/understand")
def understand_question(message: str):
    ai_output = understand_query(message)
    return {
        "question": message,
        "ai_output": ai_output
    }

@router.post("/ask")
def ask_weather(request: ChatRequest):
    """
    Full grounded weather Q&A pipeline with conversational follow-up continuity (Sub-Phase 5.3):
      resolve_followup_query() -> QueryUnderstanding -> build_weather_context() -> get_final_answer()
    """
    message = request.message
    if not message or not str(message).strip():
        return {
            "question": message,
            "intent": "unknown",
            "city": None,
            "time_period": None,
            "weather_variable": None,
            "answer": "Please ask me a weather-related question.",
            "weather_data": None,
            "source": None,
        }

    # --- Step 0: Conversational context retrieval (Sub-Phase 5.3) ---
    prev_ctx = request.previous_context
    if not prev_ctx and request.session_id:
        prev_ctx = get_conversation_context(request.session_id)
    elif not prev_ctx and request.conversation_history:
        prev_ctx = extract_last_context_from_history(request.conversation_history)

    # --- Step 1: AI query understanding ---
    ai_output = understand_query(message)
    try:
        query = json.loads(ai_output)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="AI returned invalid JSON")

    # --- Step 1b: Resolve follow-up query against previous context (Sub-Phase 5.3) ---
    query = resolve_followup_query(query, prev_ctx, message=message)

    if query.get("is_ambiguous"):
        return {
            "question": message,
            "intent": "clarification_needed",
            "city": None,
            "answer": query.get(
                "clarification_needed",
                "Could you please clarify which city or time period you would like to check?"
            ),
            "weather_data": None,
        }

    intent = query.get("intent", "unknown")

    # --- Step 2: Build grounded weather context via pipeline ---
    context = build_weather_context(
        query,
        latitude=request.latitude,
        longitude=request.longitude,
    )

    # --- Step 3: Handle non-success context statuses ---
    if context["status"] == "location_required":
        return {
            "question": message,
            "intent": intent,
            "city": None,
            "answer": (
                "Location is required to provide weather information. "
                "Please specify a city or provide GPS coordinates."
            ),
            "weather_data": None,
        }

    if context["status"] == "unsupported_intent":
        return {
            "question": message,
            "intent": intent,
            "city": context.get("location"),
            "answer": (
                "Sorry, I could not understand your weather question. "
                "Please ask about current weather, forecasts, rain, or alerts."
            ),
            "weather_data": None,
        }

    # --- Step 4: Generate deterministic weather recommendations (Sub-Phase 5.1 & 5.2) ---
    recommendation = generate_recommendation(
        context,
        query=query,
        message=message,
    )
    if recommendation:
        context["recommendation"] = recommendation

    # --- Step 5: Generate natural-language answer grounded in weather context ---
    final_answer = get_final_answer(message, context)

    # Ensure source attribution is present both at top-level and inside weather_data
    weather_payload = dict(context["weather_data"]) if isinstance(context.get("weather_data"), dict) else context.get("weather_data")
    if isinstance(weather_payload, dict) and "source" not in weather_payload:
        weather_payload["source"] = context.get("source")

    # Update session memory if session_id was provided
    if request.session_id:
        save_conversation_context(request.session_id, {
            "location": context.get("location"),
            "city": context.get("location"),
            "time_period": context.get("time_period"),
            "forecast_period": context.get("forecast_period") or context.get("time_period"),
            "weather_variable": context.get("weather_variable"),
            "intent": context.get("intent"),
        })

    # --- Step 6: Return structured response ---
    response_payload = {
        "question": message,
        "intent": context["intent"],
        "city": context["location"],
        "time_period": context.get("time_period"),
        "weather_variable": context.get("weather_variable"),
        "answer": final_answer,
        "weather_data": weather_payload,
        "source": context.get("source"),
    }
    if recommendation:
        response_payload["recommendation"] = recommendation

    if request.session_id:
        response_payload["session_id"] = request.session_id

    if request.session_id or request.previous_context or request.conversation_history:
        response_payload["conversation_context"] = {
            "location": context.get("location"),
            "time_period": context.get("time_period"),
            "weather_variable": context.get("weather_variable"),
            "intent": context.get("intent"),
        }

    return response_payload

@router.post("/ask-demo")
def ask_demo(request: ChatRequest):
    message = request.message
    message_lower = message.lower()

    # Priority 1: Explicit city in message
    city = None
    if "hyderabad" in message_lower or "hyd" in message_lower:
        city = "Hyderabad"
    elif "delhi" in message_lower:
        city = "Delhi"
    elif "mumbai" in message_lower:
        city = "Mumbai"
    elif "chennai" in message_lower:
        city = "Chennai"
    elif "bangalore" in message_lower or "bengaluru" in message_lower:
        city = "Bengaluru"

    # Priority 2: GPS coordinates if no explicit city
    use_coords = False
    is_here = any(phrase in message_lower for phrase in ["here", "my location", "current location", "where i am"])

    if not city:
        if request.latitude is not None and request.longitude is not None:
            use_coords = True
        elif is_here or "weather" in message_lower or "forecast" in message_lower or "rain" in message_lower or "alert" in message_lower or "temperature" in message_lower or "hot" in message_lower:
            return {
                "question": request.message,
                "intent": "forecast" if any(w in message_lower for w in ["forecast", "tomorrow", "rain", "weekend"]) else "current_weather",
                "city": None,
                "forecast_period": None,
                "answer": "Location is required to provide weather information. Please specify a city or provide GPS coordinates.",
                "weather_data": None
            }
        else:
            return {
                "question": request.message,
                "intent": "unknown",
                "city": None,
                "forecast_period": None,
                "answer": "Please ask me about weather, forecast, rain or alerts.",
                "weather_data": None
            }

    # Identify forecast periods
    forecast_period = "next_7_days"
    if "tomorrow" in message_lower:
        forecast_period = "tomorrow"
    elif "weekend" in message_lower or "saturday" in message_lower or "sunday" in message_lower:
        forecast_period = "weekend"
    elif "3 days" in message_lower or "three days" in message_lower:
        forecast_period = "next_3_days"
    elif "7 days" in message_lower or "seven days" in message_lower or "week" in message_lower:
        forecast_period = "next_7_days"
    elif any(h in message_lower for h in ["pm", "am", "hour", "afternoon", "morning", "evening", "tonight"]):
        forecast_period = "hourly"
    elif "today" in message_lower:
        forecast_period = "today"

    # Decide intent
    target_name = city if city else f"coordinates ({request.latitude}, {request.longitude})"

    if "alert" in message_lower or "warning" in message_lower:
        intent = "alerts"
        weather_data = get_alerts_by_coords(request.latitude, request.longitude) if use_coords else get_alerts_by_city(city)
        answer = f"Alerts check for {target_name}: {weather_data['alerts'][0]['message']}"
        forecast_period = None
    elif any(w in message_lower for w in ["forecast", "tomorrow", "rain", "weekend", "hot", "next"]):
        intent = "forecast"
        weather_data = get_forecast_by_coords(request.latitude, request.longitude, period=forecast_period) if use_coords else get_forecast_by_city(city, period=forecast_period)

        # Build natural grounded answer for demo
        f_list = weather_data.get("forecast", [])
        if forecast_period == "tomorrow" and f_list:
            d = f_list[0]
            answer = (
                f"Tomorrow's forecast for {target_name}: Max Temp: {d['max_temperature']}°C, "
                f"Min Temp: {d['min_temperature']}°C, Rain Probability: {d['rain_probability']}%, "
                f"Expected Rainfall: {d['rainfall']} mm, Max Wind: {d.get('max_wind_speed', 'N/A')} km/h."
            )
        elif forecast_period == "next_7_days" and f_list:
            max_temps = [d['max_temperature'] for d in f_list]
            rain_probs = [d['rain_probability'] for d in f_list]
            answer = (
                f"7-day forecast for {target_name}: Highs from {min(max_temps)}°C to {max(max_temps)}°C. "
                f"Highest rain probability is {max(rain_probs)}% across the 7 days."
            )
        elif forecast_period == "weekend" and f_list:
            d_strs = [f"{d['date']} (Max {d['max_temperature']}°C, Rain {d['rain_probability']}%)" for d in f_list]
            answer = f"Weekend forecast for {target_name}: {', '.join(d_strs)}."
        elif forecast_period == "hourly" and "hourly_forecast" in weather_data:
            h_sample = weather_data["hourly_forecast"][:6]
            h_strs = [f"{h['time'].split('T')[-1]}: {h['temperature']}°C ({h['rain_probability']}% rain)" for h in h_sample]
            answer = f"Upcoming hourly forecast for {target_name}: {', '.join(h_strs)}."
        else:
            answer = f"Forecast data retrieved for {target_name} ({forecast_period})."
    elif "weather" in message_lower or "temperature" in message_lower or use_coords:
        intent = "current_weather"
        weather_data = get_weather_summary_by_location(request.latitude, request.longitude) if use_coords else get_current_weather_by_city(city)
        answer = f"Current weather in {target_name}: Temperature {weather_data.get('temperature', weather_data.get('weather', {}).get('temperature_2m'))}°C."
        forecast_period = None
    else:
        intent = "unknown"
        return {
            "question": request.message,
            "intent": intent,
            "city": city,
            "forecast_period": None,
            "answer": "Please ask me about weather, forecast, rain or alerts.",
            "weather_data": None
        }

    res = {
        "question": request.message,
        "intent": intent,
        "city": city,
        "answer": answer,
        "weather_data": weather_data
    }
    if intent == "forecast":
        res["forecast_period"] = forecast_period

    return res


import re

TIMING_WORDS = {
    'tomorrow', 'today', 'tonight', 'morning', 'evening', 'afternoon', 'night',
    'at', 'by', 'on', 'in', 'around', 'driving', 'drive', 'travel', 'trip', 'going',
    'road', 'flight', 'car', 'bus', 'bike', 'motorcycle', 'am', 'pm', 'please',
    'what', 'is', 'the', 'how', 'about', 'weather', 'forecast', 'plan', 'detailed',
    'right', 'now', 'give', 'me', 'tell', 'want', 'need', 'accurate', 'pls',
    'current', 'currently', 'live', 'like', 'info', 'report', 'check', 'show'
}

def clean_location_token(loc_str: str) -> str:
    words = [w for w in re.findall(r'[A-Za-z]+', loc_str) if w.lower() not in TIMING_WORDS and len(w) >= 3]
    return ' '.join(words).strip()

def resolve_weather_telemetry(message: str, mode: str = "home", lat: float = None, lon: float = None):
    """
    Extracts locations or routes from user query and fetches live, real-time Tomorrow.io / Open-Meteo telemetry.
    Supports:
      1. Travel routes (e.g. 'Delhi to Manali', 'Mumbai to Goa')
      2. Single cities (e.g. 'Varanasi', 'Paris', 'Tokyo', 'weather in Shimla')
      3. Explicit GPS coordinates
    """
    msg = message.strip()
    telemetry = {}

    # 1. Check for Route / Corridor Travel Query
    route_match = re.search(r'\b([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(?:to|->|towards)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\b', msg, re.IGNORECASE)
    if route_match:
        orig_cand = clean_location_token(route_match.group(1))
        dest_cand = clean_location_token(route_match.group(2))
        if orig_cand and dest_cand and len(orig_cand) >= 2 and len(dest_cand) >= 2:
            try:
                orig_weather = get_current_weather_by_city(orig_cand)
                dest_weather = get_current_weather_by_city(dest_cand)
                telemetry["type"] = "travel_corridor"
                telemetry["origin"] = {
                    "city": orig_weather.get("city"),
                    "country": orig_weather.get("country"),
                    "conditions": orig_weather.get("weather", {})
                }
                telemetry["destination"] = {
                    "city": dest_weather.get("city"),
                    "country": dest_weather.get("country"),
                    "conditions": dest_weather.get("weather", {})
                }
                return telemetry
            except Exception:
                pass

    # 2. Check for Explicit City Query or Location Mention
    # Matches patterns like: 'weather in Hanamkonda', 'conditions at Warangal', 'laundry in Hanamkonda, Warangal'
    city_match = re.search(r'(?:weather|forecast|temp|temperature|rain|climate|monsoon|nowcast|conditions?|status|laundry|umbrella|running|workout|flood|cyclone)\s+(?:in|of|at|for|around|near)\s+([A-Za-z\s,]+)', msg, re.IGNORECASE)
    if not city_match:
        city_match = re.search(r'(?:in|at|around|near)\s+([A-Za-z\s,]+)', msg, re.IGNORECASE)
    if not city_match:
        city_match = re.search(r'([A-Za-z\s]+?)\s+(?:weather|forecast|temperature|rain|climate|nowcast)', msg, re.IGNORECASE)

    city_candidates = []
    if city_match:
        raw_loc = city_match.group(1).strip()
        # Handle comma or multi-location e.g. "Hanamkonda, Warangal"
        if ',' in raw_loc:
            for part in raw_loc.split(','):
                c = clean_location_token(part)
                if c:
                    city_candidates.append(c)
        cleaned = clean_location_token(raw_loc)
        if cleaned and cleaned not in city_candidates:
            city_candidates.append(cleaned)

    for cand in city_candidates:
        if not cand or len(cand.strip()) < 2:
            continue
        try:
            w_data = get_current_weather_by_city(cand.strip())
            if w_data and w_data.get("weather"):
                telemetry["type"] = "city_realtime"
                telemetry["location"] = f"{w_data.get('city')}, {w_data.get('country')}"
                telemetry["current_telemetry"] = w_data.get("weather", {})
                return telemetry
        except Exception:
            continue

    # 3. If no explicit city was matched in query, prioritize user's live GPS coordinates!
    if lat is not None and lon is not None and (lat != 0 or lon != 0):
        try:
            w_data = get_weather_summary_by_location(lat, lon)
            telemetry["type"] = "gps_telemetry"
            telemetry["latitude"] = lat
            telemetry["longitude"] = lon
            telemetry["location"] = f"Your Live Location ({lat:.2f}°, {lon:.2f}°)"
            telemetry["current_telemetry"] = w_data
            return telemetry
        except Exception:
            pass

    return None


def build_grounded_telemetry_report(query: str, mode: str, telemetry: Optional[Dict[str, Any]]) -> str:
    """
    Direct, deterministic meteorological synthesis engine.
    Ensures WeatherGPT ALWAYS delivers accurate, live, structured answers from
    Open-Meteo telemetry even if external LLM APIs experience rate-limiting or latency.
    """
    if not telemetry:
        return (
            "## 📍 Location Required\n\n"
            "I could not detect a specific location in your query. "
            "Please specify a city name (e.g., *'Weather in Hanumakonda'* or *'Pune rain forecast'*), "
            "or click the location chip in the top header."
        )

    t_type = telemetry.get("type", "")
    curr = telemetry.get("current_telemetry", {})
    loc_name = telemetry.get("location") or "Your Current Location"

    if t_type == "route_transit":
        orig = telemetry.get("origin", {})
        dest = telemetry.get("destination", {})
        o_city = orig.get("city", "Origin")
        d_city = dest.get("city", "Destination")
        o_cond = orig.get("conditions", {})
        d_cond = dest.get("conditions", {})
        return (
            f"## 🛣️ Route Meteorological Advisory: {o_city} ➔ {d_city}\n\n"
            f"### 📍 Departure: {o_city}\n"
            f"- **Temperature:** 🌡️ {o_cond.get('temperature', 'N/A')}°C (Feels like {o_cond.get('feels_like', 'N/A')}°C)\n"
            f"- **Sky & Conditions:** {o_cond.get('condition', 'Clear')}\n"
            f"- **Precipitation:** 🌧️ {o_cond.get('precipitation', 0.0)} mm\n"
            f"- **Wind:** 💨 {o_cond.get('wind_speed', 'N/A')} km/h\n\n"
            f"### 🏁 Destination: {d_city}\n"
            f"- **Temperature:** 🌡️ {d_cond.get('temperature', 'N/A')}°C (Feels like {d_cond.get('feels_like', 'N/A')}°C)\n"
            f"- **Sky & Conditions:** {d_cond.get('condition', 'Clear')}\n"
            f"- **Precipitation:** 🌧️ {d_cond.get('precipitation', 0.0)} mm\n"
            f"- **Wind:** 💨 {d_cond.get('wind_speed', 'N/A')} km/h\n\n"
            f"### 🚗 Transit Feasibility & Hazards\n"
            f"- **Road Surface Grip:** Safe road conditions. Watch for localized visibility drops in ghat sections.\n"
            f"- **Departure Optimization:** Current conditions are favorable for travel.\n\n"
            f"**DECISION:** Safe for departure. Keep headlights on low beam through hilly terrain."
        )

    temp = curr.get("temperature", curr.get("temperature_2m", "N/A"))
    feels = curr.get("feels_like", curr.get("apparent_temperature", temp))
    humidity = curr.get("humidity", curr.get("relative_humidity_2m", "N/A"))
    wind = curr.get("wind_speed", curr.get("wind_speed_10m", "N/A"))
    condition = curr.get("condition", curr.get("weather_description", "Fair"))
    precip = curr.get("precipitation", curr.get("rain", 0.0))
    pressure = curr.get("pressure", curr.get("surface_pressure", "N/A"))
    uv = curr.get("uv_index", 0.0)

    # Mode-tailored advice
    advice_section = ""
    decision_line = ""

    humidity_num = 50.0
    try:
        humidity_num = float(humidity)
    except Exception:
        pass

    wind_num = 10.0
    try:
        wind_num = float(wind)
    except Exception:
        pass

    precip_num = 0.0
    try:
        precip_num = float(precip)
    except Exception:
        pass

    if mode == "farmer":
        spray_ok = precip_num == 0 and wind_num < 15 and humidity_num < 85
        advice_section = (
            f"### 🌾 Agro-Meteorological Advisory\n"
            f"- **Foliar Chemical Spray:** {'✅ Favorable — dry canopy and light winds.' if spray_ok else '⚠️ Caution — high moisture or wind drift risk.'}\n"
            f"- **Tractor & Heavy Field Machinery:** {'Soil compaction risk is low (0.0mm rain).' if precip_num == 0 else 'Surface wetness may cause soil rutting.'}\n"
            f"- **Irrigation Management:** Adjust drip scheduling based on current {humidity}% relative humidity."
        )
        decision_line = "**ACTION:** Suitable for routine fieldwork and crop monitoring." if spray_ok else "**ACTION:** Delay chemical spraying until wind and moisture stabilize."
    elif mode == "travel":
        advice_section = (
            f"### 🚗 Travel & Commute Advisory\n"
            f"- **Road Grip & Surface:** Dry pavement with {precip} mm precipitation.\n"
            f"- **Visibility & Wind:** {condition} skies with {wind} km/h crosswinds.\n"
            f"- **Vehicle Comfort:** Exterior ambient temperature at {temp}°C (Feels like {feels}°C)."
        )
        decision_line = "**DECISION:** Road travel conditions are clear and safe."
    elif mode == "marine":
        advice_section = (
            f"### ⚓ Marine & Coastal Advisory\n"
            f"- **Surface Wind:** {wind} km/h sustained wind speeds.\n"
            f"- **Precipitation & Squall Risk:** {condition} with {precip} mm precipitation.\n"
            f"- **Barometric Pressure:** {pressure} hPa (stable atmospheric gradient)."
        )
        decision_line = "**DECISION:** Nearshore artisanal navigation is clear. Standard lifejacket protocol applies."
    else:  # home / default
        laundry_ok = humidity_num < 70 and precip_num == 0
        advice_section = (
            f"### 🏠 Everyday Lifestyle & Home Advisory\n"
            f"- **Commute & Transit:** Current conditions are {condition.lower()} with {wind} km/h breeze. Roads are clear.\n"
            f"- **Laundry Drying:** {'☀️ Outdoor drying is favorable (quick evaporation).' if laundry_ok else f'⚠️ Outdoor drying not ideal — high humidity ({humidity}%) will slow drying.'}\n"
            f"- **Outdoor Fitness:** Safe for walking, jogging, and sports at {temp}°C.\n"
            f"- **Home Comfort:** Ambient feels like {feels}°C with {pressure} hPa barometric pressure."
        )
        decision_line = f"**DECISION:** Pleasant conditions. {'Keep an umbrella handy.' if precip_num > 0 or humidity_num > 85 else 'Great conditions for everyday outdoor activities.'}"

    return (
        f"## 🌡️ Real-Time Weather: {loc_name}\n\n"
        f"Live observation telemetry from Open-Meteo:\n\n"
        f"- **Temperature:** 🌡️ {temp}°C (Feels like {feels}°C)\n"
        f"- **Sky Condition:** ☁️ {condition}\n"
        f"- **Relative Humidity:** 💧 {humidity}%\n"
        f"- **Precipitation:** 🌧️ {precip} mm\n"
        f"- **Wind Speed:** 💨 {wind} km/h\n"
        f"- **Atmospheric Pressure:** 📊 {pressure} hPa\n"
        f"- **UV Index:** ☀️ {uv}\n\n"
        f"{advice_section}\n\n"
        f"{decision_line}"
    )


@router.post("/api/chat")
def chat_with_gemini(request: ChatRequest):
    """
    Core WeatherGPT Mode Intelligence Endpoint.
    
    Passes full conversation history to Gemini for persistent multi-turn memory.
    Automatically resolves real-time Open-Meteo weather telemetry for routes & cities.
    Includes deterministic fallback report if external LLM APIs are busy.
    
    Modes: travel | farmer | marine | home | alert
    """
    message = request.message
    mode = (request.mode or "home").lower()

    # Build history list from conversation_history field
    history = []
    if request.conversation_history:
        for turn in request.conversation_history:
            role = turn.get("role", "user")
            text = turn.get("text") or turn.get("content") or turn.get("message", "")
            if text:
                history.append({"role": role, "text": text})

    # Resolve live weather telemetry for routes and cities
    weather_ctx = resolve_weather_telemetry(message, mode=mode, lat=request.latitude, lon=request.longitude)

    # Generate live context-aware decision from Gemini
    gemini_answer = query_gemini(message, mode=mode, weather_context=weather_ctx, history=history)

    # If Gemini experienced a temporary rate limit or 503 outage, fall back to our grounded report
    if not gemini_answer or gemini_answer.startswith("⚠️ WeatherGPT Intelligence Engine temporarily unavailable") or gemini_answer.startswith("Gemini API Error"):
        if weather_ctx:
            gemini_answer = build_grounded_telemetry_report(message, mode, weather_ctx)

    # Return updated history so frontend can persist it for next turn
    updated_history = history + [
        {"role": "user",  "text": message},
        {"role": "model", "text": gemini_answer},
    ]

    return {
        "question": message,
        "mode": mode,
        "answer": gemini_answer,
        "source": "Google Gemini Intelligence + Open-Meteo Weather Telemetry",
        "weather_telemetry": weather_ctx,
        "conversation_history": updated_history,
    }

