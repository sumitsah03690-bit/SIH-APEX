/**
 * =============================================================================
 * WeatherGPT — Authentic Google Gemini Standard Chat Interface Script
 * (scripts/chat.js)
 * =============================================================================
 * Features:
 *   1. Authentic Google Gemini layout matching user's reference screenshot:
 *      - Centered greeting ("The mic is yours, CODING") & input pill when empty
 *      - Ambient luminous blue radial glow in background
 *      - Slim left icon rail with 4-pointed Gemini sparkle icon
 *   2. Smooth transition between centered empty state and active bottom input
 *   3. Mode selector dropdown inside input pill (Flash, Farmer, Travel, Alerts)
 *   4. Live Voice recording with dynamic audio wave status bar
 *   5. Local Media & 4K Satellite Observation feeds modal (from sources/ folder)
 *   6. Multilingual intelligence (English, Hindi, Telugu) + rich IMD data cards
 * =============================================================================
 */

'use strict';

/* =============================================================================
   STATE — Single source of truth for all runtime data
   ============================================================================= */
const state = {
  messages:           [],       // [{role:'user'|'ai', content:'...'}]
  isTyping:           false,    // blocks duplicate sends while AI processes
  conversationCount:  1,        // history counter
  mode:               'home',   // 'home' | 'farmer' | 'travel' | 'alert'
  lang:               'en',     // 'en' | 'hi' | 'te'
  isRecording:        false,    // voice recognition active
  recognition:        null,     // SpeechRecognition instance
  conversationHistory: [],      // [{role:'user'|'model', text:'...'}] — sent to Gemini for memory
  currentSessionId:   null,     // Active localStorage session ID
  sessionTitle:       null,     // Auto-generated from first user message
  userLocation:       null,     // { lat: number, lon: number, city: string }
};

/* =============================================================================
   WEATHER PUNCHLINES — Rotates on each new chat
   ============================================================================= */
const WEATHER_PUNCHLINES = [
  'Because "70% rain" shouldn\'t ruin your road trip.',
  'Turning chaotic atmospheric physics into your next safe move.',
  'Know before you go — weather, live, for every Indian road.',
  'IMD data + AI reasoning = no more weather surprises.',
  'Sun or storm? Ask before you pack the umbrella.',
  'Smart weather is not a forecast. It\'s a decision engine.',
  'Your daily commute, backed by real-time satellite telemetry.',
  'Rain gauge + AI = the world\'s clearest travel plan.',
  'Where monsoons meet machine learning. Welcome home.',
  'Live radar. AI reasoning. Zero weather guesswork.',
  'Because farmers, travelers, and fisherfolk deserve real data.',
  'The only forecast that tells you when to skip the trek.',
];

let _punchlineIdx = Math.floor(Math.random() * WEATHER_PUNCHLINES.length);
function nextPunchline() {
  _punchlineIdx = (_punchlineIdx + 1) % WEATHER_PUNCHLINES.length;
  return WEATHER_PUNCHLINES[_punchlineIdx];
}
function randomPunchline() {
  return WEATHER_PUNCHLINES[Math.floor(Math.random() * WEATHER_PUNCHLINES.length)];
}

/* =============================================================================
   DOM REFERENCES
   ============================================================================= */
const chatWorkspace      = document.getElementById('chatWorkspace');
const chatStage          = document.getElementById('chatStage');
const emptyHero          = document.getElementById('emptyHero');
const heroTitle          = document.getElementById('heroTitle');
const heroSub            = document.getElementById('heroSub');
const messagesFlowWrap   = document.getElementById('messagesFlowWrap');
const messagesList       = document.getElementById('messagesList');
const inputContainer     = document.getElementById('inputContainer');
const inputPill          = document.getElementById('inputPill');
const messageInput       = document.getElementById('messageInput');
const sendBtn            = document.getElementById('sendBtn');
const voiceBtn           = document.getElementById('voiceBtn');
const attachBtn          = document.getElementById('attachBtn');
const promptChips        = document.getElementById('promptChips');
const recordingBar       = document.getElementById('recordingBar');
const recLabel           = document.getElementById('recLabel');
const upgradeBtn         = document.getElementById('upgradeBtn');
const clearBtn           = document.getElementById('clearBtn');

// Mode dropdown inside pill
const modeDropdownWrap   = document.getElementById('modeDropdownWrap');
const modeSelectorBtn    = document.getElementById('modeSelectorBtn');
const activeModeLabel    = document.getElementById('activeModeLabel');
const modeMenu           = document.getElementById('modeMenu');

// Icon rail buttons
const railNewChat        = document.getElementById('railNewChat');
const railSearch         = document.getElementById('railSearch');
const railModes          = document.getElementById('railModes');
const railMedia          = document.getElementById('railMedia');
const railApps           = document.getElementById('railApps');
const railSettings       = document.getElementById('railSettings');
const mobileMenuBtn      = document.getElementById('mobileMenuBtn');

// Collapsible drawer
const drawerPanel        = document.getElementById('drawerPanel');
const drawerBackdrop     = document.getElementById('drawerBackdrop');
const drawerClose        = document.getElementById('drawerClose');
const drawerNewBtn       = document.getElementById('drawerNewBtn');
const chatHistory        = document.getElementById('chatHistory');
const quickQueries       = document.getElementById('quickQueries');
const historySearchInput = document.getElementById('historySearchInput');
const clearAllHistoryBtn = document.getElementById('clearAllHistoryBtn');

// Header elements
const headerPunchline    = document.getElementById('headerPunchline');
const sidebarToggleBtn   = document.getElementById('sidebarToggleBtn');

// Header weather chip
const hwcSpinner         = document.getElementById('hwcSpinner');
const hwcReady           = document.getElementById('hwcReady');
const hwcCityName        = document.getElementById('hwcCityName');
const hwcCondIcon        = document.getElementById('hwcCondIcon');
const hwcBigTemp         = document.getElementById('hwcBigTemp');
const hwcCondText        = document.getElementById('hwcCondText');
const hwcHLText          = document.getElementById('hwcHLText');
const headerWeatherChip  = document.getElementById('headerWeatherChip');

// Media modal (sources/ feeds)
const mediaModal         = document.getElementById('mediaModal');
const mediaModalClose    = document.getElementById('mediaModalClose');

/* =============================================================================
   MODE DEFINITIONS
   ============================================================================= */
const MODES = {
  home: {
    label: 'Flash',
    title: 'The mic is yours, CODING',
    sub:   'Ask anything about real-time weather, IMD cyclone alerts, rainfall, or city forecasts',
    placeholder: 'Ask WeatherGPT',
    chips: [
      { icon:'🌧', label:"Today's Mumbai rain nowcast", query:"What is today's weather in Mumbai?" },
      { icon:'🚨', label:'Active cyclone & flood alerts', query:'Are there any active cyclone or flood warnings in India right now?' },
      { icon:'📅', label:'Delhi 7-day monsoon forecast', query:'What is the 7-day forecast for Delhi?' },
      { icon:'🌡', label:'Hottest cities today', query:'Which are the hottest cities in India today?' },
    ],
    quick: [
      { icon:'🌧', label:'Mumbai rain nowcast', query:"What is today's weather in Mumbai?" },
      { icon:'🌀', label:'Cyclone track alerts', query:'Are there any active cyclone warnings in India?' },
      { icon:'📅', label:'Delhi 7-day forecast', query:'What is the 7-day forecast for Delhi?' },
    ]
  },
  farmer: {
    label: 'Farmer',
    title: 'Agro-Meteorological Advisory',
    sub:   'Soil moisture tracking, sowing windows, crop pest warnings & IMD monsoon outlooks',
    placeholder: 'Ask about crop weather, irrigation, or soil moisture...',
    chips: [
      { icon:'🌾', label:'Punjab wheat crop advisory', query:'What is the crop weather advisory for Punjab wheat this week?' },
      { icon:'💧', label:'Sugarcane irrigation timing', query:'When should I irrigate sugarcane in Maharashtra?' },
      { icon:'🐛', label:'Rice pest & blast risk', query:'What is the pest and blast disease risk for rice in Andhra Pradesh?' },
      { icon:'🌧', label:'Monsoon rainfall forecast', query:'What is the climate trend for monsoon rainfall in Maharashtra over last 10 years?' },
    ],
    quick: [
      { icon:'🌾', label:'Punjab wheat advisory', query:'What is the crop weather advisory for Punjab wheat this week?' },
      { icon:'💧', label:'Sugarcane irrigation', query:'When should I irrigate sugarcane in Maharashtra?' },
      { icon:'🐛', label:'Rice disease alert', query:'What is the pest and blast disease risk for rice in Andhra Pradesh?' },
    ]
  },
  travel: {
    label: 'Travel',
    title: 'Travel & Journey Intelligence',
    sub:   'Route road conditions, highway rainfall, mountain passes & flight weather',
    placeholder: 'Ask about highway weather, hill stations, or flight conditions...',
    chips: [
      { icon:'🛣️', label:'Delhi to Manali highway status', query:'What are the weather and road conditions from Delhi to Manali?' },
      { icon:'🏔️', label:'Kedarnath trek 5-day forecast', query:'What is the 5-day forecast for Kedarnath trek route?' },
      { icon:'🌊', label:'Goa beach & sea wave forecast', query:'What are the beach and sea conditions in Goa this weekend?' },
      { icon:'✈️', label:'Chennai airport METAR/TAF', query:'What is the aviation weather and METAR for Chennai airport?' },
    ],
    quick: [
      { icon:'🛣️', label:'Delhi-Manali Highway', query:'What are the weather and road conditions from Delhi to Manali?' },
      { icon:'🏔️', label:'Kedarnath Trek weather', query:'What is the 5-day forecast for Kedarnath trek route?' },
      { icon:'🌊', label:'Goa beach conditions', query:'What are the beach and sea conditions in Goa this weekend?' },
    ]
  },
  marine: {
    label: 'Marine',
    title: 'Marine & Coastal Intelligence',
    sub:   'INCOIS wave buoys, tidal harmonics, sea-state swell & coastal fishing safety',
    placeholder: 'Ask about wave height, sea conditions, or fishing advisories...',
    chips: [
      { icon:'🌊', label:'Vizag coast wave & swell advisory', query:'Can artisanal fishing boats safely venture off Vizag coast tonight?' },
      { icon:'⚓', label:'Mumbai harbor high tide & swell', query:'What is the tidal window and wave height for Mumbai harbor operations?' },
      { icon:'🐟', label:'Bay of Bengal fishing zone advisories', query:'What are the INCOIS potential fishing zone advisories for Bay of Bengal?' },
      { icon:'🏖️', label:'Goa coastal sea-state & surf', query:'What are the beach and sea conditions in Goa this weekend?' },
    ],
    quick: [
      { icon:'🌊', label:'Vizag sea-state', query:'Can artisanal fishing boats safely venture off Vizag coast tonight?' },
      { icon:'⚓', label:'Mumbai tidal window', query:'What is the tidal window and wave height for Mumbai harbor operations?' },
      { icon:'🐟', label:'Fishing zone alerts', query:'What are the INCOIS potential fishing zone advisories for Bay of Bengal?' },
    ]
  },
  alert: {
    label: 'Alerts',
    title: 'Disaster Warning & Radar Center',
    sub:   'Real-time IMD red/orange warnings, cyclone tracks & river basin flood telemetry',
    placeholder: 'Check cyclone coordinates, red alerts, or flood levels...',
    chips: [
      { icon:'🌀', label:'Bay of Bengal cyclone track', query:'Are there any active cyclone or flood warnings in India right now?' },
      { icon:'🌊', label:'Ganga basin river flood level', query:'What is the Ganga river basin flood level and mist forecast in Varanasi?' },
      { icon:'⚡', label:'Active severe thunderstorms', query:'Which areas have active thunderstorm or orange alerts right now?' },
    ],
    quick: [
      { icon:'🌀', label:'Cyclone Vayu track', query:'Are there any active cyclone or flood warnings in India right now?' },
      { icon:'🌊', label:'Ganga river telemetry', query:'What is the Ganga river basin flood level and mist forecast in Varanasi?' },
    ]
  }
};

/* weatherData dictionary removed — all data comes from backend API only */

/**
 * Maps WMO weather interpretation codes to human-readable text and emojis.
 * Used by the header weather chip to display current conditions.
 * @param {number} code - WMO weather code (0 to 99)
 * @returns {{desc: string, icon: string}}
 */
function getWmoWeatherInfo(code) {
  if (code === 0) return { desc:'Clear Sky', icon:'☀️' };
  if (code === 1 || code === 2) return { desc:'Mainly Clear · Passing Clouds', icon:'🌤' };
  if (code === 3) return { desc:'Overcast · Cloud Blanket', icon:'☁️' };
  if (code === 45 || code === 48) return { desc:'Fog · Low Visibility', icon:'🌫️' };
  if (code >= 51 && code <= 55) return { desc:'Light Drizzle', icon:'🌦️' };
  if (code >= 61 && code <= 65) return { desc:'Rainfall', icon:'🌧️' };
  if (code >= 71 && code <= 75) return { desc:'Snowfall', icon:'❄️' };
  if (code >= 80 && code <= 82) return { desc:'Rain Showers', icon:'🌧️' };
  if (code >= 95 && code <= 99) return { desc:'Thunderstorm', icon:'⛈️' };
  return { desc:'Partly Cloudy', icon:'⛅' };
}


/* =============================================================================
   CORE INTERACTION LOGIC: SEND MESSAGE & STATE TRANSITION
   ============================================================================= */

/**
 * Sends a message from the input pill.
 * Automatically switches the UI from centered empty state to active bottom chat!
 * Asynchronously checks live public APIs with instantaneous fallback.
 */
async function sendMessage() {
  const text = messageInput.value.trim();
  if (!text || state.isTyping) return;

  // 1. Transition UI from centered empty-state to active chat stream
  if (!chatStage.classList.contains('is-chatting')) {
    chatStage.classList.add('is-chatting');
  }

  // 2. Append user bubble
  appendUserMessage(text);
  state.messages.push({ role: 'user', content: text });

  // Auto-title from first message
  if (!state.sessionTitle) state.sessionTitle = text.slice(0, 60);

  // 3. Reset input field
  messageInput.value = '';
  messageInput.style.height = 'auto';
  updateSendBtnState();

  // 4. Show animated typing indicator
  state.isTyping = true;
  const typingEl = appendTyping();
  scrollToBottom();

  // 5. Generate intelligent response with slight realistic delay
  const minDelay = 600;
  const startTime = Date.now();

  try {
    const response = await generateResponseAsync(text, state.mode, state.lang);
    const elapsed = Date.now() - startTime;
    const remaining = Math.max(0, minDelay - elapsed);

    setTimeout(() => {
      typingEl.remove();
      state.isTyping = false;
      appendAIMessage(response.text, response.card);
      state.messages.push({ role: 'ai', content: response.text });
      scrollToBottom();
      // Persist session to localStorage
      saveCurrentSession();
      renderChatHistory();
    }, remaining);
  } catch (err) {
    console.error('[WeatherGPT Chat] Response generation failed:', err);
    typingEl.remove();
    state.isTyping = false;
    appendAIMessage("⚠️ Something went wrong. Please check that the backend server is running on `localhost:8000`.");
    scrollToBottom();
  }
}

/**
 * Resets the chat interface back to the standard Google Gemini centered empty state.
 */
function resetToEmptyState() {
  state.messages = [];
  state.conversationHistory = [];   // ← clear Gemini memory on new chat
  messagesList.innerHTML = '';
  chatStage.classList.remove('is-chatting');
  messageInput.value = '';
  messageInput.style.height = 'auto';
  updateSendBtnState();
  closeDrawer();
  messageInput.focus();
}

/** Renders user message */
function appendUserMessage(text) {
  const row = document.createElement('div');
  row.className = 'message-row user';
  row.innerHTML = `<div class="user-msg-content">${escapeHtml(text)}</div>`;
  messagesList.appendChild(row);
}

/** Renders typing dots */
function appendTyping() {
  const row = document.createElement('div');
  row.className = 'message-row ai typing-row';
  row.innerHTML = `
    <div class="ai-sparkle-avatar">
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
        <path d="M14 0C14 7.732 7.732 14 0 14C7.732 14 14 20.268 14 28C14 20.268 20.268 14 28 14C20.268 14 14 7.732 14 0Z" fill="url(#aiGradTyping)"/>
        <defs>
          <linearGradient id="aiGradTyping" x1="0" y1="0" x2="28" y2="28" gradientUnits="userSpaceOnUse">
            <stop stop-color="#4285F4"/>
            <stop offset="0.32" stop-color="#9B72CF"/>
            <stop offset="0.68" stop-color="#D96570"/>
            <stop offset="1" stop-color="#F2A600"/>
          </linearGradient>
        </defs>
      </svg>
    </div>
    <div class="typing-dots">
      <span></span><span></span><span></span>
    </div>
  `;
  messagesList.appendChild(row);
  return row;
}

/** Renders AI reply with the authentic 4-pointed Gemini sparkle avatar */
function appendAIMessage(text, card = null) {
  const row = document.createElement('div');
  row.className = 'message-row ai';
  row.innerHTML = `
    <div class="ai-sparkle-avatar">
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
        <path d="M14 0C14 7.732 7.732 14 0 14C7.732 14 14 20.268 14 28C14 20.268 20.268 14 28 14C20.268 14 14 7.732 14 0Z" fill="url(#aiGradMsg)"/>
        <defs>
          <linearGradient id="aiGradMsg" x1="0" y1="0" x2="28" y2="28" gradientUnits="userSpaceOnUse">
            <stop stop-color="#4285F4"/>
            <stop offset="0.32" stop-color="#9B72CF"/>
            <stop offset="0.68" stop-color="#D96570"/>
            <stop offset="1" stop-color="#F2A600"/>
          </linearGradient>
        </defs>
      </svg>
    </div>
    <div class="ai-msg-content">
      <div class="ai-text-body">${formatMarkdown(text)}</div>
      ${card ? renderWeatherCard(card) : ''}
      <div class="ai-msg-actions">
        <button class="ai-action-btn" title="Copy reply" onclick="copyResponse(this)">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
        </button>
        <button class="ai-action-btn" title="Read aloud" onclick="speakResponse(this)">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>
        </button>
      </div>
    </div>
  `;
  messagesList.appendChild(row);
}

/**
 * Renders a rich meteorological telemetry card inside an AI message bubble.
 * Displays city name, condition icon, temperature, humidity, wind, visibility,
 * and optional telemetry (AQI, Atmospheric Pressure, and Feels-like temperature).
 *
 * @param {Object} c - Weather telemetry object
 * @returns {string} HTML string
 */
function renderWeatherCard(c) {
  const extraItems = [];
  if (c.aqi) {
    extraItems.push(`
      <div class="wcr-item">
        <div class="wcr-lbl">Air Quality</div>
        <div class="wcr-val" style="color:#38bdf8;font-size:0.85rem;">${escapeHtml(c.aqi)}</div>
      </div>
    `);
  }
  if (c.pressure) {
    extraItems.push(`
      <div class="wcr-item">
        <div class="wcr-lbl">Pressure</div>
        <div class="wcr-val">${escapeHtml(c.pressure)}</div>
      </div>
    `);
  }
  if (c.apparent) {
    extraItems.push(`
      <div class="wcr-item">
        <div class="wcr-lbl">Feels Like</div>
        <div class="wcr-val" style="color:#bae6fd;">${escapeHtml(c.apparent)}</div>
      </div>
    `);
  }

  return `
    <div class="weather-card-rich">
      <div class="wcr-header">
        <span class="wcr-city">${c.icon || '🌤'} ${escapeHtml(c.city)}</span>
        ${c.alert ? `<span class="wcr-badge" style="background:rgba(239,68,68,0.2);color:#fca5a5;">${escapeHtml(c.alert)}</span>` : `<span class="wcr-badge">Live IMD / NWP</span>`}
      </div>
      <div class="wcr-grid">
        <div class="wcr-item">
          <div class="wcr-lbl">Temperature</div>
          <div class="wcr-val">${escapeHtml(c.temp)}</div>
        </div>
        <div class="wcr-item">
          <div class="wcr-lbl">Humidity</div>
          <div class="wcr-val">${escapeHtml(c.humidity)}</div>
        </div>
        <div class="wcr-item">
          <div class="wcr-lbl">Wind</div>
          <div class="wcr-val">${escapeHtml(c.wind)}</div>
        </div>
        <div class="wcr-item">
          <div class="wcr-lbl">Visibility</div>
          <div class="wcr-val">${escapeHtml(c.visibility)}</div>
        </div>
        ${extraItems.join('')}
      </div>
    </div>
  `;
}

/** Auto scroll to bottom */
function scrollToBottom() {
  requestAnimationFrame(() => {
    messagesFlowWrap.scrollTop = messagesFlowWrap.scrollHeight;
  });
}

/** Update send button style based on textarea content */
function updateSendBtnState() {
  const hasText = messageInput.value.trim().length > 0;
  if (hasText) {
    sendBtn.classList.add('active');
    sendBtn.disabled = false;
  } else {
    sendBtn.classList.remove('active');
    sendBtn.disabled = true;
  }
}

/* =============================================================================
   MODE SWITCHING LOGIC
   ============================================================================= */
function setMode(modeKey) {
  const conf = MODES[modeKey] || MODES.home;
  state.mode = modeKey;

  // Update label on pill button
  activeModeLabel.textContent = conf.label;

  // Update hero texts
  heroTitle.textContent = conf.title;
  heroSub.textContent   = conf.sub;
  messageInput.placeholder = conf.placeholder;

  // Render Prompt Chips
  promptChips.innerHTML = conf.chips.map(c => `
    <button class="chip-item" data-query="${escapeHtml(c.query)}">
      <span class="chip-icon">${c.icon}</span> ${escapeHtml(c.label)}
    </button>
  `).join('');

  // Render Drawer Quick Queries
  quickQueries.innerHTML = conf.quick.map(q => `
    <button class="quick-btn" data-query="${escapeHtml(q.query)}">
      ${q.icon} ${escapeHtml(q.label)}
    </button>
  `).join('');

  // Update active item in dropdown menu
  document.querySelectorAll('.mode-menu-item').forEach(el => {
    el.classList.toggle('active', el.dataset.mode === modeKey);
  });

  modeDropdownWrap.classList.remove('open');
}

/* =============================================================================
   VOICE RECORDER LOGIC (Web Speech API)
   ============================================================================= */
function setupVoice() {
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRec) {
    voiceBtn.style.display = 'none';
    return;
  }

  const rec = new SpeechRec();
  rec.continuous = false;
  rec.interimResults = true;
  rec.lang = state.lang === 'hi' ? 'hi-IN' : state.lang === 'te' ? 'te-IN' : 'en-IN';

  rec.onstart = () => {
    state.isRecording = true;
    voiceBtn.classList.add('recording');
    recordingBar.classList.add('active');
    recLabel.textContent = 'Listening... speak your weather question';
  };

  rec.onresult = (e) => {
    let transcript = '';
    for (let i = e.resultIndex; i < e.results.length; i++) {
      transcript += e.results[i][0].transcript;
    }
    messageInput.value = transcript;
    updateSendBtnState();
  };

  rec.onerror = (e) => {
    console.warn('[VoiceRec] Error:', e.error);
    stopRecording();
  };

  rec.onend = () => {
    stopRecording();
    if (messageInput.value.trim().length > 0) {
      sendMessage();
    }
  };

  state.recognition = rec;

  voiceBtn.addEventListener('click', () => {
    if (state.isRecording) {
      state.recognition.stop();
    } else {
      try {
        state.recognition.lang = state.lang === 'hi' ? 'hi-IN' : state.lang === 'te' ? 'te-IN' : 'en-IN';
        state.recognition.start();
      } catch (err) {
        console.error(err);
      }
    }
  });
}

function stopRecording() {
  state.isRecording = false;
  voiceBtn.classList.remove('recording');
  recordingBar.classList.remove('active');
}

/* =============================================================================
   DRAWER & SATELLITE MODAL HANDLERS
   ============================================================================= */
function openDrawer() {
  drawerPanel.classList.add('open');
  drawerBackdrop.classList.add('open');
}
function closeDrawer() {
  drawerPanel.classList.remove('open');
  drawerBackdrop.classList.remove('open');
}

function openMediaModal() {
  mediaModal.classList.add('open');
}
function closeMediaModal() {
  mediaModal.classList.remove('open');
}

/* =============================================================================
   AI INTELLIGENCE ROUTER — Backend Only (No Fake Fallbacks)
   =============================================================================
   All responses come from the FastAPI backend → Gemini 2.5 Flash + Open-Meteo.
   If the backend is unreachable, a clear error is shown to the user.
   ============================================================================= */
async function generateResponseAsync(query, mode, lang) {
  const MAX_RETRIES = 3;

  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    try {
      const backendRes = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: query,
          mode: mode,
          lang: lang,
          latitude: state.userLocation?.lat ?? null,
          longitude: state.userLocation?.lon ?? null,
          conversation_history: state.conversationHistory
        })
      });

      if (backendRes.ok) {
        const data = await backendRes.json();
        const answer = data.answer || '';

        // Retry if Gemini was overloaded
        if (answer.includes('overloaded') || answer.includes('temporarily unavailable') || answer.length < 10) {
          if (attempt < MAX_RETRIES) {
            await new Promise(r => setTimeout(r, attempt * 1500));
            continue;
          }
        }

        if (answer) {
          // Update conversation history from backend
          if (data.conversation_history && Array.isArray(data.conversation_history)) {
            state.conversationHistory = data.conversation_history;
          } else {
            state.conversationHistory.push(
              { role: 'user',  text: query },
              { role: 'model', text: answer }
            );
          }
          return { text: answer };
        }
      } else if (backendRes.status === 503 || backendRes.status === 429) {
        if (attempt < MAX_RETRIES) {
          await new Promise(r => setTimeout(r, attempt * 2000));
          continue;
        }
      }
    } catch (err) {
      if (attempt < MAX_RETRIES) {
        await new Promise(r => setTimeout(r, attempt * 1000));
        continue;
      }
    }
    break;
  }

  // Backend unreachable — show clear error (no fake data)
  return {
    text: "⚠️ **Could not connect to WeatherGPT server.**\n\n" +
          "The backend server at `localhost:8000` is not running.\n\n" +
          "**To start it:**\n" +
          "```bash\ncd backend\npip install -r requirements.txt\nuvicorn main:app --reload\n```\n\n" +
          "Make sure your `backend/.env` file has `GEMINI_API_KEY` set."
  };
}






/* =============================================================================
   MARKDOWN PARSER & HELPERS
   ============================================================================= */
function formatMarkdown(text) {
  if (!text) return '';

  // 1. Extract and preserve multiline fenced code blocks (```lang ... ```)
  const codeBlocks = [];
  let processed = text.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    const idx = codeBlocks.length;
    const safeLang = lang ? lang.trim() : 'code';
    codeBlocks.push(`
      <div class="code-block-wrap" style="background:#0e1320;border:1px solid rgba(255,255,255,0.12);border-radius:8px;margin:14px 0;overflow:hidden;font-family:monospace;">
        <div style="display:flex;justify-content:space-between;align-items:center;background:rgba(255,255,255,0.05);padding:6px 14px;border-bottom:1px solid rgba(255,255,255,0.08);font-size:0.75rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;">
          <span>${escapeHtml(safeLang)}</span>
          <button style="background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.15);color:#cbd5e1;cursor:pointer;font-size:0.72rem;padding:3px 8px;border-radius:4px;" onclick="navigator.clipboard.writeText(this.parentElement.nextElementSibling.innerText);this.innerText='Copied!';setTimeout(()=>this.innerText='Copy',1500)">Copy</button>
        </div>
        <pre style="margin:0;padding:14px;overflow-x:auto;font-size:0.86rem;line-height:1.55;color:#e2e8f0;tab-size:4;"><code>${escapeHtml(code.trim())}</code></pre>
      </div>
    `);
    return `%%%CODEBLOCK_${idx}%%%`;
  });

  // 2. Headings: ### and ## and #
  processed = processed
    .replace(/^### (.*$)/gim, '<h3 class="ai-md-h3" style="font-size:1.02rem;color:#bae6fd;margin:14px 0 6px;font-weight:600;">$1</h3>')
    .replace(/^## (.*$)/gim, '<h2 class="ai-md-h2" style="font-size:1.18rem;color:#a8c7fa;margin:18px 0 8px;font-weight:700;letter-spacing:-0.01em;">$1</h2>')
    .replace(/^# (.*$)/gim, '<h1 class="ai-md-h1" style="font-size:1.3rem;color:#e3e3e3;margin:20px 0 10px;font-weight:700;">$1</h1>');

  // 3. Horizontal rules
  processed = processed.replace(/^---$/gim, '<hr style="border:none;border-top:1px solid rgba(255,255,255,0.12);margin:16px 0;">');

  // 4. Blockquotes: > quote
  processed = processed.replace(/^> (.*$)/gim, '<blockquote style="border-left:3px solid #a8c7fa;padding:6px 12px;margin:10px 0;background:rgba(168,199,250,0.06);border-radius:0 6px 6px 0;">$1</blockquote>');

  // 5. Bold & Inline Code
  processed = processed
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+?)`/g, '<code style="background:rgba(255,255,255,0.08);padding:2px 6px;border-radius:4px;font-size:0.85em;font-family:monospace;color:#fca5a5;">$1</code>');

  // 6. Bullet lists (* item, - item, * - item, or • item)
  processed = processed.replace(/^[\s]*[\*\-\•][\*\-\•\s]*\s+(.+)$/gim, '<li style="margin:4px 0;padding-left:4px;line-height:1.55;">$1</li>');
  // Group adjacent <li> into <ul>
  processed = processed.replace(/((?:<li[\s\S]*?<\/li>\n?)+)/g, '<ul style="list-style:disc;padding-left:22px;margin:10px 0;">$1</ul>');

  // 7. Inline italics (only match *word* that is not at the start of a tag or bullet)
  processed = processed.replace(/(?<![<a-zA-Z0-9])\*([^\*\n]+?)\*(?![a-zA-Z0-9>])/g, '<em>$1</em>');

  // 8. Markdown Tables
  processed = processed.replace(/\|(.+)\|\n\|[-| ]+\|\n((?:\|.+\|\n?)+)/g, (match) => {
    const lines   = match.trim().split('\n');
    const headers = lines[0].split('|').filter(c => c.trim())
      .map(c => `<th style="padding:6px 12px;text-align:left;border-bottom:1px solid rgba(255,255,255,0.1);color:#a8c7fa;font-size:0.8rem;">${c.trim()}</th>`).join('');
    const rows = lines.slice(2).map(line => {
      const cells = line.split('|').filter(c => c.trim())
        .map(c => `<td style="padding:6px 12px;border-bottom:1px solid rgba(255,255,255,0.05);font-size:0.85rem;">${c.trim()}</td>`).join('');
      return `<tr>${cells}</tr>`;
    }).join('');
    return `<div style="overflow-x:auto;margin:12px 0;"><table style="width:100%;border-collapse:collapse;background:rgba(255,255,255,0.02);border-radius:8px;"><thead><tr>${headers}</tr></thead><tbody>${rows}</tbody></table></div>`;
  });

  // 9. Paragraph wrapping: split on double newlines without breaking structured HTML blocks
  const blocks = processed.split(/\n\n+/);
  processed = blocks.map(block => {
    const b = block.trim();
    if (!b) return '';
    if (b.startsWith('<h1') || b.startsWith('<h2') || b.startsWith('<h3') ||
        b.startsWith('<ul') || b.startsWith('<pre') || b.startsWith('<blockquote') ||
        b.startsWith('<hr') || b.startsWith('<div') || b.startsWith('%%%CODEBLOCK_')) {
      return b;
    }
    return `<p style="margin:8px 0;line-height:1.65;">${b.replace(/\n/g, '<br>')}</p>`;
  }).join('\n');

  // 10. Re-inject code blocks
  codeBlocks.forEach((block, idx) => {
    processed = processed.replace(`<p>%%%CODEBLOCK_${idx}%%%</p>`, block);
    processed = processed.replace(`%%%CODEBLOCK_${idx}%%%`, block);
  });

  return processed;
}

function escapeHtml(t) {
  return t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/* =============================================================================
   WINDOW-EXPOSED ACTION HANDLERS
   ============================================================================= */
window.copyResponse = function(btn) {
  const text = btn.closest('.ai-msg-content')?.querySelector('.ai-text-body')?.innerText || '';
  navigator.clipboard.writeText(text).then(() => {
    btn.style.color = '#a8c7fa';
    setTimeout(() => { btn.style.color = ''; }, 2000);
  });
};

window.speakResponse = function(btn) {
  const text = btn.closest('.ai-msg-content')?.querySelector('.ai-text-body')?.innerText || '';
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utt = new SpeechSynthesisUtterance(text);
  utt.lang = state.lang === 'hi' ? 'hi-IN' : state.lang === 'te' ? 'te-IN' : 'en-IN';
  utt.rate = 0.95;
  window.speechSynthesis.speak(utt);
};

/* =============================================================================
   EVENT LISTENERS INITIALIZATION
   ============================================================================= */
function initEventListeners() {
  // Input auto-expand & send on Enter
  messageInput.addEventListener('input', () => {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 160) + 'px';
    updateSendBtnState();
  });

  messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  sendBtn.addEventListener('click', sendMessage);

  // Attach button — asks for location context
  attachBtn.addEventListener('click', () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          messageInput.value = `Weather at my coordinates (${pos.coords.latitude.toFixed(2)}°N, ${pos.coords.longitude.toFixed(2)}°E)`;
          updateSendBtnState();
          sendMessage();
        },
        () => {
          messageInput.value = "What is the weather in Delhi?";
          updateSendBtnState();
          messageInput.focus();
        }
      );
    }
  });

  // Mode Dropdown toggle
  modeSelectorBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    modeDropdownWrap.classList.toggle('open');
  });

  // Mode Menu items
  modeMenu.querySelectorAll('.mode-menu-item').forEach(item => {
    item.addEventListener('click', () => {
      const targetMode = item.dataset.mode;
      setMode(targetMode);
    });
  });

  // Close dropdown on outside click
  document.addEventListener('click', (e) => {
    if (!modeDropdownWrap.contains(e.target)) {
      modeDropdownWrap.classList.remove('open');
    }
  });

  // Clear / Reset chat to centered state
  clearBtn.addEventListener('click', createNewChat);
  railNewChat.addEventListener('click', createNewChat);
  drawerNewBtn.addEventListener('click', createNewChat);

  // Prompt chips clicks
  document.addEventListener('click', (e) => {
    const chip = e.target.closest('.chip-item') || e.target.closest('.quick-btn');
    if (chip && chip.dataset.query) {
      messageInput.value = chip.dataset.query;
      updateSendBtnState();
      closeDrawer();
      sendMessage();
    }
  });

  // Drawer toggles
  railSearch.addEventListener('click', openDrawer);
  railModes.addEventListener('click', openDrawer);
  railSettings.addEventListener('click', openDrawer);
  mobileMenuBtn.addEventListener('click', openDrawer);
  drawerClose.addEventListener('click', closeDrawer);
  drawerBackdrop.addEventListener('click', closeDrawer);

  // Media Modal toggles (Sources folder feeds)
  railMedia.addEventListener('click', openMediaModal);
  mediaModalClose.addEventListener('click', closeMediaModal);
  mediaModal.addEventListener('click', (e) => {
    if (e.target === mediaModal) closeMediaModal();
  });

  // Query buttons inside media modal
  mediaModal.querySelectorAll('.mm-query-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const q = btn.dataset.query;
      closeMediaModal();
      messageInput.value = q;
      updateSendBtnState();
      sendMessage();
    });
  });

  // Live Radar Upgrade Button
  upgradeBtn.addEventListener('click', () => {
    messageInput.value = "what is the current weather?";
    updateSendBtnState();
    sendMessage();
  });

  // Language buttons in drawer
  document.querySelectorAll('.drawer-lang-toggle .lang-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.drawer-lang-toggle .lang-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.lang = btn.dataset.lang;
    });
  });

  // Setup Voice Input
  setupVoice();
}

/* =============================================================================
   LIVE HEADER WEATHER CHIP — Fetches GPS → Open-Meteo → displays iOS-style
   Includes instant regional fallback so the chip ALWAYS shows live weather even if GPS is denied
   ============================================================================= */
async function renderChipWithLocation(lat, lon, cityLabel) {
  try {
    const wxUrl = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m,relative_humidity_2m&daily=temperature_2m_max,temperature_2m_min&timezone=auto&forecast_days=1`;
    const wxRes  = await fetch(wxUrl);
    if (!wxRes.ok) throw new Error('Weather fetch failed');
    const wxJson  = await wxRes.json();
    const curr    = wxJson.current;
    const daily   = wxJson.daily;

    const temp    = Math.round(curr.temperature_2m);
    const feelsLk = Math.round(curr.apparent_temperature);
    const high    = daily && daily.temperature_2m_max ? Math.round(daily.temperature_2m_max[0]) : feelsLk + 2;
    const low     = daily && daily.temperature_2m_min ? Math.round(daily.temperature_2m_min[0]) : temp - 4;
    const wmo     = getWmoWeatherInfo(curr.weather_code);

    // Save to global state so subsequent queries know user's coordinates!
    state.userLocation = { lat, lon, city: cityLabel };

    // Populate chip
    if (hwcCityName) hwcCityName.textContent  = cityLabel;
    if (hwcCondIcon) hwcCondIcon.textContent  = wmo.icon;
    if (hwcBigTemp)  hwcBigTemp.textContent   = `${temp}°`;
    if (hwcCondText) hwcCondText.textContent  = wmo.desc.split(' ·')[0];
    if (hwcHLText)   hwcHLText.textContent    = `H:${high}° L:${low}°`;

    if (hwcSpinner) hwcSpinner.style.display = 'none';
    if (hwcReady)   hwcReady.style.display   = 'block';

    if (headerWeatherChip) {
      headerWeatherChip.onclick = () => {
        messageInput.value = `What is the current weather in ${cityLabel}?`;
        updateSendBtnState();
        messageInput.focus();
      };
    }
  } catch (err) {
    console.warn('[WeatherChip] Render error:', err.message);
    if (hwcSpinner) hwcSpinner.style.display = 'none';
  }
}

async function initHeaderWeatherChip() {
  const hwcSpinner = document.getElementById('hwcSpinner');
  const hwcContent = document.getElementById('hwcContent');

  // Check if we already have cached GPS coords from this session
  const cached = sessionStorage.getItem('wgpt_location');
  let lat, lon, cityLabel;

  if (cached) {
    try {
      const c = JSON.parse(cached);
      lat = c.lat; lon = c.lon; cityLabel = c.city;
    } catch(_) {}
  }

  if (lat && lon) {
    // Use cached coords directly
    await renderChipWithLocation(lat, lon, cityLabel || 'My Location');
    return;
  }

  // Try GPS
  if (navigator.geolocation) {
    try {
      const pos = await new Promise((res, rej) =>
        navigator.geolocation.getCurrentPosition(res, rej, { timeout: 6000, maximumAge: 60000 })
      );
      lat = pos.coords.latitude;
      lon = pos.coords.longitude;
      cityLabel = 'My Location';

      // Reverse geocode
      try {
        const nomRes = await fetch(
          `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json&accept-language=en&zoom=10`,
          { headers: { 'User-Agent': 'WeatherGPT/1.0' }, signal: AbortSignal.timeout(4000) }
        );
        if (nomRes.ok) {
          const addr = (await nomRes.json()).address || {};
          cityLabel = addr.city || addr.town || addr.village || addr.state_district || 'My Location';
        }
      } catch(_) {}

      // Cache for this session
      sessionStorage.setItem('wgpt_location', JSON.stringify({ lat, lon, city: cityLabel }));
      await renderChipWithLocation(lat, lon, cityLabel);
      return;

    } catch (geoErr) {
      console.info('[WeatherChip] GPS denied or unavailable:', geoErr.message);
    }
  }

  // GPS unavailable / denied — show clickable "Allow Location" button, NOT fake Delhi data
  if (hwcSpinner) hwcSpinner.style.display = 'none';
  if (hwcContent) {
    hwcContent.innerHTML = `
      <span style="font-size:1rem">📍</span>
      <span style="font-size:0.7rem;opacity:0.7">Allow Location</span>
    `;
    hwcContent.style.cursor = 'pointer';
    hwcContent.title = 'Click to share your location for live weather';
    hwcContent.onclick = async () => {
      hwcContent.innerHTML = `<span style="font-size:0.7rem;opacity:0.6">Detecting…</span>`;
      try {
        const pos = await new Promise((res, rej) =>
          navigator.geolocation.getCurrentPosition(res, rej, { timeout: 10000 })
        );
        lat = pos.coords.latitude;
        lon = pos.coords.longitude;
        cityLabel = 'My Location';
        try {
          const r = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json&accept-language=en&zoom=10`, { headers:{'User-Agent':'WeatherGPT/1.0'} });
          if (r.ok) {
            const a = (await r.json()).address || {};
            cityLabel = a.city || a.town || a.village || a.state_district || 'My Location';
          }
        } catch(_) {}
        sessionStorage.setItem('wgpt_location', JSON.stringify({ lat, lon, city: cityLabel }));
        hwcContent.onclick = null;
        hwcContent.style.cursor = 'default';
        await renderChipWithLocation(lat, lon, cityLabel);
      } catch(e) {
        hwcContent.innerHTML = `<span style="font-size:0.7rem;opacity:0.5">Location blocked</span>`;
      }
    };
  }
}

/* =============================================================================
   SESSION MANAGER — localStorage-backed chat history
   ============================================================================= */
const SESSION_KEY = 'weathergpt_sessions_v2';

function generateSessionId() {
  return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
}

function loadSessions() {
  try {
    return JSON.parse(localStorage.getItem(SESSION_KEY) || '{}');
  } catch (_) { return {}; }
}

function saveSessions(sessions) {
  try {
    localStorage.setItem(SESSION_KEY, JSON.stringify(sessions));
  } catch (_) { /* quota exceeded */ }
}

function saveCurrentSession() {
  if (!state.currentSessionId || state.messages.length === 0) return;
  const sessions = loadSessions();
  const firstUserMsg = state.messages.find(m => m.role === 'user');
  sessions[state.currentSessionId] = {
    id:        state.currentSessionId,
    title:     state.sessionTitle || (firstUserMsg ? firstUserMsg.content.slice(0, 60) : 'New Chat'),
    mode:      state.mode,
    timestamp: Date.now(),
    messages:  state.messages,
    history:   state.conversationHistory,
  };
  saveSessions(sessions);
}

function renderChatHistory(filterText = '') {
  if (!chatHistory) return;
  const sessions = loadSessions();
  const list = Object.values(sessions).sort((a, b) => b.timestamp - a.timestamp);
  const filtered = filterText.trim()
    ? list.filter(s => s.title.toLowerCase().includes(filterText.toLowerCase()))
    : list;

  if (filtered.length === 0) {
    chatHistory.innerHTML = `
      <div class="history-empty">
        <div class="history-empty-icon">💬</div>
        <div>${filterText ? 'No chats match your search.' : 'No saved conversations yet.\nStart chatting to build your history!'}</div>
      </div>`;
    return;
  }

  const modeIcons = { home:'⚡', farmer:'🌾', travel:'✈️', marine:'⚓', alert:'🚨' };
  chatHistory.innerHTML = filtered.map(s => {
    const relTime = formatRelativeTime(s.timestamp);
    const icon    = modeIcons[s.mode] || '💬';
    const isActive = s.id === state.currentSessionId ? ' active-session' : '';
    return `
      <div class="history-item${isActive}" data-session-id="${s.id}">
        <div class="hi-icon">${icon}</div>
        <div class="hi-info">
          <div class="hi-title">${escapeHtml(s.title)}</div>
          <div class="hi-time">${relTime}</div>
        </div>
        <button class="hi-delete-btn" data-delete-id="${s.id}" title="Delete">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
        </button>
      </div>`;
  }).join('');

  // Wire click events
  chatHistory.querySelectorAll('.history-item').forEach(item => {
    item.addEventListener('click', (e) => {
      if (e.target.closest('.hi-delete-btn')) return; // handled separately
      loadChatSession(item.dataset.sessionId);
    });
  });
  chatHistory.querySelectorAll('.hi-delete-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      deleteSession(btn.dataset.deleteId);
    });
  });
}

function loadChatSession(sessionId) {
  const sessions = loadSessions();
  const session  = sessions[sessionId];
  if (!session) return;

  // Save current session before switching
  saveCurrentSession();

  // Restore session state
  state.currentSessionId    = sessionId;
  state.sessionTitle        = session.title;
  state.mode                = session.mode || 'home';
  state.messages            = session.messages || [];
  state.conversationHistory = session.history || [];

  // Re-render messages
  messagesList.innerHTML = '';
  state.messages.forEach(m => {
    if (m.role === 'user') appendUserMessage(m.content);
    else if (m.role === 'ai') appendAIMessage(m.content);
  });

  if (state.messages.length > 0) {
    chatStage.classList.add('is-chatting');
  }
  setMode(state.mode);
  closeDrawer();
  scrollToBottom();
  renderChatHistory();
}

function deleteSession(sessionId) {
  const sessions = loadSessions();
  delete sessions[sessionId];
  saveSessions(sessions);
  if (state.currentSessionId === sessionId) {
    createNewChat();
  }
  renderChatHistory(historySearchInput ? historySearchInput.value : '');
}

function createNewChat() {
  saveCurrentSession();
  state.currentSessionId    = generateSessionId();
  state.sessionTitle        = null;
  state.messages            = [];
  state.conversationHistory = [];
  messagesList.innerHTML    = '';
  chatStage.classList.remove('is-chatting');
  messageInput.value        = '';
  messageInput.style.height = 'auto';
  updateSendBtnState();
  setMode(state.mode);
  // Rotate punchline
  if (headerPunchline) headerPunchline.textContent = nextPunchline();
  closeDrawer();
  messageInput.focus();
  renderChatHistory();
}

function formatRelativeTime(ts) {
  const diff = Date.now() - ts;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(ts).toLocaleDateString('en-IN', { day:'numeric', month:'short' });
}

/* =============================================================================
   BOOTSTRAP — Full initialization
   ============================================================================= */
document.addEventListener('DOMContentLoaded', () => {
  // Init session ID for this page load
  state.currentSessionId = generateSessionId();

  // Set punchline
  if (headerPunchline) headerPunchline.textContent = randomPunchline();

  // Wire all existing event listeners
  initEventListeners();

  // Wire sidebar toggle button
  if (sidebarToggleBtn) {
    sidebarToggleBtn.addEventListener('click', () => {
      if (drawerPanel.classList.contains('open')) closeDrawer();
      else openDrawer();
    });
  }

  // Wire drawer search
  if (historySearchInput) {
    historySearchInput.addEventListener('input', () => {
      renderChatHistory(historySearchInput.value);
    });
  }

  // Wire clear all history
  if (clearAllHistoryBtn) {
    clearAllHistoryBtn.addEventListener('click', () => {
      if (confirm('Delete all chat history? This cannot be undone.')) {
        saveSessions({});
        createNewChat();
      }
    });
  }

  // Render saved history in drawer
  renderChatHistory();

  // Start URL mode or default
  const urlParams     = new URLSearchParams(window.location.search);
  const requestedMode = urlParams.get('mode');
  if (requestedMode && MODES[requestedMode]) {
    setMode(requestedMode);
  } else {
    setMode('home');
  }

  // Auto-save session every 30 seconds
  setInterval(saveCurrentSession, 30000);

  // Load live weather chip
  initHeaderWeatherChip();

  messageInput.focus();
});

// Save session on page unload
window.addEventListener('beforeunload', saveCurrentSession);
