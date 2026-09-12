"""
WeatherGPT — Google Gemini Intelligence Engine
(backend/services/gemini_service.py)

Direct integration with Google Gemini 2.5 Flash using user's active API key.
Orchestrates domain-specific reasoning for:
  1. Travel Mode (Road vehicle feasibility, multi-city timeline, departure shifts)
  2. Farmer Mode (Manual spray 48h dry window vs tractor soil compaction)
  3. Marine Mode (Artisanal boat capsize risk, swell period, tidal docking)
  4. Home / Personal Mode (Commute umbrella, laundry drying, AQI elderly alerts)
  5. Disaster Alerts (Cyclone track, river flood levels, evacuation triggers)

Now with full conversation memory: history is passed as Gemini multi-turn contents[].
"""

import json
import os
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")  # Set via .env file — never hardcode secrets!
GEMINI_MODELS = [
    "gemini-flash-latest",           # Primary — verified active 200 OK
    "gemini-flash-lite-latest",      # Secondary — verified active 200 OK
    "gemini-3.1-flash-lite-preview", # Fast lightweight preview
    "gemini-2.5-flash",              # Standard fallback
]
GEMINI_ENDPOINT_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

CORE_AI_INSTRUCTIONS = """You are WeatherGPT, an advanced multimodal intelligence system powered by Google Gemini and live Tomorrow.io / IMD meteorological telemetry.

PRIMARY EXPERTISE: Real-time weather intelligence and situation-specific domain reasoning:
- Travel & Transit: Detailed route hazards, waypoint weather timelines, departure optimization, vehicle risk
- Farmer/Kisan: Crop spray windows, soil root-zone moisture, machinery feasibility, frost alerts
- Marine & Ports: Sea-state advisories, wave heights, swell period, tidal docking, capsize risk
- Home & Lifestyle: Everyday living decisions, commute planning, laundry drying windows, AQI alerts
- Disaster Response: Cyclone tracks, flood inundation hydrographs, evacuation directives

ACCURACY & LIVE TELEMETRY MANDATE (CRITICAL):
- Whenever LIVE WEATHER TELEMETRY is provided in the prompt, you MUST use the EXACT real numbers provided (Temperature °C, Feels-Like °C, Humidity %, Rain %, Wind km/h, UV index, Visibility km, Condition).
- NEVER guess or state outdated numbers when live telemetry is present — cite the actual live readings.
- If asked about weather of any city: present the exact readings in a structured format, followed by actionable lifestyle/safety advice.

GENERAL INTELLIGENCE :
You are ALSO an expert software engineer and algorithm specialist.
- NEVER refuse coding or general questions — treat them with equal mastery

OUTPUT FORMAT RULES (CRITICAL):
1. Always structure responses with clear sections using markdown headers (## )
2. Use bullet points (- ) for lists, never run-on paragraphs
3. For weather queries: include actual numbers (temperature, wind speed, rain probability, humidity)
4. For travel/farmer/marine: end with a bold **DECISION:** or **ACTION:** line
5. For coding: provide complete, runnable code with Big-O complexity analysis
6. Responses should be detailed and substantive — minimum 150 words for weather queries
7. Use emojis strategically for weather conditions (🌧️ 🌡️ 💨 ⚠️ ✅) to improve scannability"""

SYSTEM_PROMPTS = {
    "travel": """You are in specialized TRAVEL MODE.

Your mission is to formulate comprehensive, actionable travel weather plans and route hazard evaluations.

CRITICAL TRAVEL PLAN STRUCTURE:
When a user asks for a travel plan or route weather (e.g. "Delhi to Manali", "Mumbai to Goa"):
1. ## 🚗 Route Overview & Corridor Profile
   - Origin & Destination, estimated driving distance, transit hours, elevation change.
2. ## 🌡️ Origin vs Destination Live Telemetry
   - Contrast real-time temperatures, conditions, humidity, and rain probabilities using ingested data.
3. ## ⏱️ Segment-by-Segment Waypoint Weather Timeline
   - Break down 3-4 key highway checkpoints with estimated arrival times, expected weather, and road conditions.
4. ## ⚠️ Route Hazard Analysis
   - Road surface friction & hydroplaning risk (critical if rain >5mm/hr)
   - Visibility & mountain pass fog (critical if visibility <1000m)
   - Ghat landslide index, rockfall probability, or high crosswinds (>35 km/h)
5. ## 🕒 Departure Window Optimization
   - Recommend the exact optimal departure time to avoid localized cloudbursts, morning valley fog, or peak heat.
6. ## 🎒 Vehicle & Gear Checklist
   - Tire pressure, wipers, headlight visibility, warm layers, emergency kit.
7. ## **DECISION:** Bold operational directive (e.g. **PROCEED WITH CAUTION — DEPART AT 07:15 AM**).

Format with clean markdown headers and bullet points. Be specific, precise, and authoritative.""",

    "farmer": """You are in specialized FARMER / KISAN MODE.

Your mission is to provide precision agro-meteorological guidance.

CRITICAL INSTRUCTIONS:
1. **Spray Window Rule**: Pesticides/fungicides need ≥4 rain-free hours to adhere. Evaluate 48h window.
2. **Equipment Feasibility**:
   - Tractor: Cannot enter field if topsoil moisture >70% (sinking/compaction)
   - Manual labor: Check wet-bulb temperature for heat exhaustion risk (>32°C wet-bulb = rest needed)
3. **Irrigation Decision**: Rain probability >60% within 36 hours → hold tube-well to prevent root rot
4. **Crop-Specific Advice**: Reference crop phenology if crop type is mentioned
5. **Multilingual**: Use Hindi/Telugu terms when queried in regional languages

Format with ## sections. Always end with **ACTION:** for immediate next steps.""",

    "marine": """You are in specialized MARINE & COASTAL MODE.

Your mission is to protect fishermen, coastal vessels, and port operations.

CRITICAL INSTRUCTIONS:
1. **Craft Risk Matrix**:
   - Artisanal/Traditional (<15m wooden/FRP dinghies): Capsize hazard if SWH >2.0m OR swell period >10s
   - Deep-sea mechanized trawlers: Unsafe if SWH >3.5m or gale wind >45 km/h
   - Large cargo vessels: Reference Beaufort scale
2. **Tidal Operations**: Provide high/low tide windows for harbor docking
3. **Sea State Report**: Wave height, swell period, wind direction, visibility
4. **Advisory**: Issue clear ✅ ENTRY CLEARANCE or ⚠️ SUSPENSION ADVISORY

Format with sea-state telemetry parameters table. Be precise with numbers.""",

    "home": """You are in PERSONAL / HOME MODE.

Your mission is to assist with everyday weather-based lifestyle decisions AND general queries.

WEATHER DECISIONS:
- Commute: Should I carry an umbrella? Drive or bike?
- Laundry: Best window to dry clothes outdoors (humidity <60%, wind >10 km/h ideal)
- Fitness: Running/outdoor sports safety based on AQI, temperature, UV index
- Home: AC mode recommendation, flood-proofing advice during heavy rain

GENERAL INTELLIGENCE:
- Answer any question about science, history, math, or general knowledge
- Solve LeetCode/coding problems with full optimal solutions

Keep responses friendly, practical and well-structured with bullet points.""",

    "alert": """You are in DISASTER EARLY WARNING MODE.

Your mission is to communicate life-safety weather emergencies clearly and authoritatively.

CRITICAL INSTRUCTIONS:
1. **Coordinates & Track**: Exact lat/long, movement speed (km/h), direction, landfall ETA
2. **IMD Color Alert**: State official Red / Orange / Yellow / Green classification
3. **Impact Zones**: Districts/tehsils within 50km, 100km, and 200km of impact
4. **Life-Safety Directives**: Evacuation routes, shelter-in-place zones, fishermen return orders
5. **River Levels**: CWC gauge readings vs danger levels for relevant basins
6. **Do/Don't List**: Concrete actions for civilians in affected areas

Use ⚠️ RED ALERT / 🟠 ORANGE ALERT formatting. Be authoritative and clear."""
}


def query_gemini(
    user_query: str,
    mode: str = "home",
    weather_context: Optional[Dict[str, Any]] = None,
    history: Optional[List[Dict[str, str]]] = None
) -> str:
    """
    Sends a structured multi-turn conversation to Gemini 2.5 Flash.
    
    Args:
        user_query: The current user message
        mode: Domain mode (travel/farmer/marine/home/alert)
        weather_context: Live weather telemetry to inject
        history: List of {"role": "user"|"model", "text": "..."} for conversation memory
    
    Returns: Markdown-formatted response string
    """
    api_key = os.getenv("GEMINI_API_KEY", GEMINI_API_KEY)
    if not api_key:
        return "⚙️ WeatherGPT Engine: Please set GEMINI_API_KEY in backend/.env to enable AI responses."

    # Build the system instruction (prepended to first user turn)
    system_instruction = f"{CORE_AI_INSTRUCTIONS}\n\n{SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS['home'])}"

    # Build multi-turn contents array for conversation memory
    contents = []

    # Replay history turns (exclude the last 10 to keep context window manageable)
    if history:
        for turn in history[-10:]:
            role = turn.get("role", "user")
            text = turn.get("text", "")
            if text:
                # Gemini roles: "user" or "model"
                gemini_role = "model" if role in ("model", "assistant") else "user"
                contents.append({
                    "role": gemini_role,
                    "parts": [{"text": text}]
                })

    # Build the current user prompt (inject system + weather context only on first turn or always)
    current_prompt = ""
    if not contents:
        # First message in conversation — include full system prompt
        current_prompt = f"{system_instruction}\n\n"

    if weather_context:
        current_prompt += f"🌡️ LIVE WEATHER TELEMETRY:\n```json\n{json.dumps(weather_context, indent=2)}\n```\n\n"

    current_prompt += f"USER: {user_query}\n\nProvide a detailed, structured, actionable response:"

    contents.append({
        "role": "user",
        "parts": [{"text": current_prompt}]
    })

    payload = {
        "contents": contents,
        "systemInstruction": {
            "parts": [{"text": system_instruction}]
        },
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 4096,    # Increased to prevent mid-sentence cut-offs
            "topP": 0.9,
        }
    }

    last_error = "Unknown error"
    
    # Intelligent multi-model failover: if one model is overloaded (429/503), automatically switch to next active model
    for model_name in GEMINI_MODELS:
        url = f"{GEMINI_ENDPOINT_TEMPLATE.format(model=model_name)}?key={api_key}"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                res_json = json.loads(response.read().decode("utf-8"))
            candidates = res_json.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
            continue
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            if e.code == 401:
                return "🔑 Gemini API key is invalid or expired. Please update GEMINI_API_KEY in backend/.env"
            if e.code in (404, 429, 500, 503):
                # Model quota reached or model unavailable — failover to next candidate model
                last_error = f"{model_name} (HTTP {e.code})"
                continue
            return f"Gemini API Error ({e.code}): {err_msg[:300]}"
        except Exception as e:
            last_error = f"{model_name}: {str(e)}"
            continue

    return f"⚠️ WeatherGPT Intelligence Engine temporarily unavailable — all candidate models busy ({last_error}). Please try again in a moment."
