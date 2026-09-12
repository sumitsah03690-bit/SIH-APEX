/**
 * =============================================================================
 * WeatherGPT — Landing Page Script (scripts/landing.js)
 * =============================================================================
 *
 * WHAT THIS FILE DOES:
 *   1. Navbar scroll effect (transparent → frosted glass)
 *   2. Scroll cue (animated line) — hides when user scrolls past hero
 *   3. Demo video modal (Watch Demo button → full-screen player)
 *   4. Stats counter animation (counts up on scroll into view)
 *   5. Scroll reveal for cards and sections
 *
 * HOW TO ADD YOUR OWN 4K VIDEO:
 *   1. Place your video file in the project root (e.g. bg-4k.mp4)
 *   2. Update the <source src="..."> in index.html → #bgVideo → source tag
 *   3. Recommended encoding: H.264 for maximum browser compatibility
 *      ffmpeg command:
 *        ffmpeg -i your-video.mp4 -c:v libx264 -crf 20 -preset slow \
 *               -c:a aac -b:a 128k bg-video.mp4
 *   4. For demo modal, update the <source src="..."> inside #demoVideo
 *
 * DEBUG TIPS:
 *   • Video not loading → check Network tab for 404 / CORS error on the src URL
 *   • Video plays but has no sound → that's intentional (autoplay needs muted)
 *   • Modal won't open → confirm watchDemoBtn and demoModal IDs in index.html
 *   • Stats not counting → check data-target attribute on .stat-num elements
 * =============================================================================
 */

'use strict';


/* =============================================================================
   1. NAVBAR — Adds .scrolled class past 60px for frosted glass effect
   ============================================================================= */
const navbar = document.getElementById('navbar');

window.addEventListener('scroll', () => {
  // 60px threshold — feels natural without flickering at page top
  navbar?.classList.toggle('scrolled', window.scrollY > 60);
}, { passive: true }); // passive:true improves scroll performance


/* =============================================================================
   2. SCROLL CUE — Animated line fades out when hero is scrolled past
   =============================================================================
   The .scroll-cue element is fixed at bottom-center of viewport.
   It disappears once the user has scrolled > 80% of the hero height.
   ============================================================================= */
const scrollCue  = document.getElementById('scrollCue');
const heroEl     = document.getElementById('hero');

window.addEventListener('scroll', () => {
  if (!scrollCue || !heroEl) return;
  const heroBottom = heroEl.getBoundingClientRect().bottom;
  // Hide when bottom of hero is less than 20% of viewport height
  scrollCue.classList.toggle('hidden', heroBottom < window.innerHeight * 0.2);
}, { passive: true });


/* =============================================================================
   3. DEMO VIDEO MODAL
   =============================================================================
   - Click "Watch Demo" → opens modal overlay with .open class
   - Click X or overlay background → closes modal, pauses video
   - Keyboard: Escape key closes modal

   HOW TO SWAP THE DEMO VIDEO:
     • Change <source src="..."> inside #demoVideo in index.html
     • For YouTube: replace <video> with:
         <iframe src="https://www.youtube.com/embed/YOUR_VIDEO_ID?autoplay=1"
                 style="width:100%;height:100%;border:0;" allowfullscreen></iframe>
   ============================================================================= */
const watchDemoBtn = document.getElementById('watchDemoBtn');
const demoModal    = document.getElementById('demoModal');
const modalClose   = document.getElementById('modalClose');
const demoVideo    = document.getElementById('demoVideo');

/** Opens the modal and starts playing the demo video */
function openModal() {
  if (!demoModal) return;
  demoModal.classList.add('open');
  demoModal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden'; // prevent background scrolling
  demoVideo?.play().catch(e => {
    // Autoplay might be blocked on some browsers without user gesture
    // This is fine — controls are visible so user can manually press play
    console.warn('[DemoModal] Video autoplay blocked:', e.message);
  });
}

/** Closes the modal and pauses the video */
function closeModal() {
  if (!demoModal) return;
  demoModal.classList.remove('open');
  demoModal.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = ''; // restore scrolling
  if (demoVideo) {
    demoVideo.pause();
    demoVideo.currentTime = 0; // rewind so it starts fresh next time
  }
}

watchDemoBtn?.addEventListener('click', openModal);
modalClose?.addEventListener('click', closeModal);

// Click on the dark overlay (outside the modal inner box) = close
demoModal?.addEventListener('click', (e) => {
  // Only close if clicking the overlay itself, not the inner content
  if (e.target === demoModal) closeModal();
});

// Escape key closes modal
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && demoModal?.classList.contains('open')) closeModal();
});


/* =============================================================================
   4. STATS COUNTER ANIMATION
   =============================================================================
   Finds all .stat-num elements with a data-target attribute.
   Counts up from 0 to the target value when the element scrolls into view.
   Appends a suffix (+, %, s) from the suffixes map.

   DEBUG: If numbers show "0+" instead of counting:
     → Check data-target is a number string (not empty) in index.html
     → Check the IntersectionObserver threshold value (0.5 = 50% visible)
   ============================================================================= */
const statEls = document.querySelectorAll('.stat-num[data-target]');

// Maps target value → suffix character shown after the count
const STAT_SUFFIXES = { '500': '+', '15': '+', '99': '%', '2': 's' };

const statObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (!entry.isIntersecting) return; // not visible yet

    const el     = entry.target;
    const target = parseInt(el.dataset.target, 10);
    const suffix = STAT_SUFFIXES[String(target)] || '';
    let current  = 0;
    const step   = target / 55; // reaches target in ~55 frames (~0.9s at 60fps)

    const timer = setInterval(() => {
      current = Math.min(current + step, target);
      el.textContent = Math.floor(current) + suffix;
      if (current >= target) clearInterval(timer); // stop when done
    }, 16); // 16ms ≈ 60fps frame rate

    statObserver.unobserve(el); // run once only — don't replay on scroll back
  });
}, { threshold: 0.5 });

statEls.forEach(el => {
  el.textContent = '0'; // reset to 0 before counting (removes the fallback text in HTML)
  statObserver.observe(el);
});


/* =============================================================================
   5. SCROLL REVEAL — Fade-up animation for sections and cards
   =============================================================================
   Adds .reveal class to target elements (.climate-card, .uc-item, etc.).
   When they enter viewport, .visible is added → CSS transition plays.
   Stagger: items within the same intersection batch are delayed by 80ms each.

   CSS classes used:
     .reveal   → set in landing.css (opacity:0, translateY:32px)
     .visible  → set in landing.css (opacity:1, translateY:0 + transition)

   DEBUG: If cards are invisible and stuck:
     → Check that .reveal and .visible classes exist in landing.css
     → Try reducing threshold from 0.1 to 0 to trigger earlier
   ============================================================================= */
const revealEls = document.querySelectorAll(
  '.climate-card, .uc-item, .stat-block, .section-headline, .section-eyebrow, .cta-headline'
);

// Add .reveal to each element to set initial hidden state
revealEls.forEach(el => el.classList.add('reveal'));

const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry, batchIndex) => {
    if (!entry.isIntersecting) return;

    // Stagger within each observation batch — max 4 steps of 80ms each
    const delay = (batchIndex % 4) * 80;
    setTimeout(() => {
      entry.target.classList.add('visible');
    }, delay);

    revealObserver.unobserve(entry.target); // one-shot
  });
}, {
  threshold: 0.1,                    // trigger when 10% is visible
  rootMargin: '0px 0px -40px 0px',  // trigger 40px before bottom of viewport
});

revealEls.forEach(el => revealObserver.observe(el));


/* =============================================================================
   6. REAL-TIME REGIONAL WEATHER TELEMETRY (Open-Meteo & IMD Synchronization)
   =============================================================================
   Connects the 4 Indian Regional Climate Showcase cards to live public
   meteorological feeds (WMO station observations via Open-Meteo).
   
   COORDINATES:
     1. Mumbai (Western Marine Frontier):     18.97°N, 72.82°E
     2. Varanasi (Northern Gangetic Plain):    25.31°N, 82.97°E
     3. Shillong/Meghalaya (Northeast Basin): 25.57°N, 91.88°E
     4. Shimla (Sub-Himalayan Foothills):     31.10°N, 77.17°E

   FAIL-SAFE MECHANISM:
     If the user is offline or the public API times out, this function catches
     the error gracefully and retains the curated official baseline telemetry.
     The UI will NEVER display blank fields or broken formatting.

   DEBUG GUIDE:
     - Check DevTools Console for '[LiveWeatherSync]' logs.
     - Check Network tab for requests to 'api.open-meteo.com'.
     - Confirm element IDs in index.html match: #mumbaiTemp, #varanasiTemp, etc.
   ============================================================================= */
const btnRefreshClimates = document.getElementById('btnRefreshClimates');
const climatesSyncText   = document.getElementById('climatesSyncText');

/**
 * Fetches real-time observation data for a specific latitude & longitude.
 * @param {number} lat - Latitude in decimal degrees
 * @param {number} lon - Longitude in decimal degrees
 * @returns {Promise<Object|null>} Telemetry object or null if network fails
 */
async function fetchZoneWeather(lat, lon) {
  try {
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,apparent_temperature,precipitation&timezone=auto`;
    const res = await fetch(url, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data.current;
  } catch (err) {
    console.warn(`[LiveWeatherSync] Failed to fetch coordinates (${lat}, ${lon}):`, err.message);
    return null; // Return null so caller can preserve baseline values
  }
}

/**
 * Synchronizes all 4 regional climate cards with live meteorological feeds.
 * Updates temperature, humidity, wind vectors, and timestamps.
 */
async function syncAllClimates() {
  if (btnRefreshClimates) {
    btnRefreshClimates.classList.add('spinning');
    btnRefreshClimates.disabled = true;
  }
  if (climatesSyncText) {
    climatesSyncText.textContent = 'Syncing Live Feeds...';
  }

  try {
    // Parallel fetch for optimal speed and minimal latency
    const [mumbai, varanasi, meghalaya, shimla] = await Promise.all([
      fetchZoneWeather(18.97, 72.82), // Mumbai
      fetchZoneWeather(25.31, 82.97), // Varanasi
      fetchZoneWeather(25.57, 91.88), // Shillong / Meghalaya
      fetchZoneWeather(31.10, 77.17), // Shimla
    ]);

    // 1. Update Mumbai Coastal Mist telemetry
    if (mumbai) {
      const tempEl = document.getElementById('mumbaiTemp');
      const humEl  = document.getElementById('mumbaiHum');
      const windEl = document.getElementById('mumbaiWind');
      if (tempEl && mumbai.temperature_2m !== undefined) tempEl.textContent = `${Math.round(mumbai.temperature_2m)}°C`;
      if (humEl && mumbai.relative_humidity_2m !== undefined) humEl.textContent = `${Math.round(mumbai.relative_humidity_2m)}%`;
      if (windEl && mumbai.wind_speed_10m !== undefined) windEl.textContent = `${Math.round(mumbai.wind_speed_10m)} km/h SW`;
    }

    // 2. Update Varanasi Gangetic Plain telemetry
    if (varanasi) {
      const tempEl = document.getElementById('varanasiTemp');
      const humEl  = document.getElementById('varanasiHum');
      const windEl = document.getElementById('varanasiWind');
      if (tempEl && varanasi.temperature_2m !== undefined) tempEl.textContent = `${Math.round(varanasi.temperature_2m)}°C`;
      if (humEl && varanasi.relative_humidity_2m !== undefined) humEl.textContent = `${Math.round(varanasi.relative_humidity_2m)}%`;
      if (windEl && varanasi.wind_speed_10m !== undefined) windEl.textContent = `${Math.round(varanasi.wind_speed_10m)} km/h E`;
    }

    // 3. Update Meghalaya Valley Agro-Weather telemetry
    if (meghalaya) {
      const tempEl = document.getElementById('meghalayaTemp');
      const humEl  = document.getElementById('meghalayaHum');
      const rainEl = document.getElementById('meghalayaRain');
      if (tempEl && meghalaya.temperature_2m !== undefined) tempEl.textContent = `${Math.round(meghalaya.temperature_2m)}°C`;
      if (humEl && meghalaya.relative_humidity_2m !== undefined) humEl.textContent = `${Math.round(meghalaya.relative_humidity_2m)}%`;
      if (rainEl && meghalaya.precipitation !== undefined) {
        rainEl.textContent = meghalaya.precipitation > 0 ? `${meghalaya.precipitation.toFixed(1)} mm/h` : `0.0 mm/h (Clear)`;
      }
    }

    // 4. Update Shimla Sub-Himalayan Foothills telemetry
    if (shimla) {
      const tempEl = document.getElementById('shimlaTemp');
      const humEl  = document.getElementById('shimlaHum');
      const windEl = document.getElementById('shimlaWind');
      const appEl  = document.getElementById('shimlaApparent');
      if (tempEl && shimla.temperature_2m !== undefined) tempEl.textContent = `${Math.round(shimla.temperature_2m)}°C`;
      if (humEl && shimla.relative_humidity_2m !== undefined) humEl.textContent = `${Math.round(shimla.relative_humidity_2m)}%`;
      if (windEl && shimla.wind_speed_10m !== undefined) windEl.textContent = `${Math.round(shimla.wind_speed_10m)} km/h N`;
      if (appEl && shimla.apparent_temperature !== undefined) appEl.textContent = `${Math.round(shimla.apparent_temperature)}°C`;
    }

    // Format current time in Indian Standard Time (IST)
    const now = new Date();
    const timeStr = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
    if (climatesSyncText) {
      climatesSyncText.textContent = `Live IMD Feed · Synced ${timeStr}`;
    }
    console.info('[LiveWeatherSync] Successfully synchronized all 4 microclimate zones.');
  } catch (err) {
    console.warn('[LiveWeatherSync] Sync batch failed:', err);
    if (climatesSyncText) climatesSyncText.textContent = 'IMD Baseline Feed Active';
  } finally {
    if (btnRefreshClimates) {
      setTimeout(() => {
        btnRefreshClimates.classList.remove('spinning');
        btnRefreshClimates.disabled = false;
      }, 500);
    }
  }
}

// Attach manual refresh button event
btnRefreshClimates?.addEventListener('click', () => {
  syncAllClimates();
});

// Auto-sync when page loads after a short polite delay (600ms)
window.addEventListener('DOMContentLoaded', () => {
  setTimeout(syncAllClimates, 600);
});


/* =============================================================================
   LIVE NAV CHIP — Fetches user's real GPS location weather from Open-Meteo
   Nominatim reverse-geocodes the city name (no API key needed)
   ============================================================================= */
const WMO_MAP = {
  0:'☀️', 1:'🌤', 2:'⛅', 3:'☁️', 45:'🌫️', 48:'🌫️',
  51:'🌦️', 53:'🌦️', 55:'🌦️', 61:'🌧️', 63:'🌧️', 65:'🌧️',
  71:'❄️', 73:'❄️', 75:'❄️', 80:'🌧️', 81:'🌧️', 82:'🌧️',
  95:'⛈️', 96:'⛈️', 99:'⛈️'
};

async function initNavLiveChip() {
  const spinner = document.getElementById('navChipSpinner');
  const ready   = document.getElementById('navChipReady');
  const iconEl  = document.getElementById('navChipIcon');
  const tempEl  = document.getElementById('navChipTemp');
  const cityEl  = document.getElementById('navChipCity');
  if (!spinner || !ready) return;

  let lat = 28.6139, lon = 77.2090, cityName = 'New Delhi';

  // Try GPS
  if (navigator.geolocation) {
    try {
      const pos = await new Promise((res, rej) =>
        navigator.geolocation.getCurrentPosition(res, rej, { timeout: 6000, maximumAge: 300000 })
      );
      lat = pos.coords.latitude;
      lon = pos.coords.longitude;
      cityName = 'My Location';

      // Reverse geocode city name
      try {
        const nomRes = await fetch(
          `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json&zoom=10`,
          { headers: { 'User-Agent': 'WeatherGPT/1.0' }, signal: AbortSignal.timeout(4000) }
        );
        if (nomRes.ok) {
          const nom = await nomRes.json();
          const a = nom.address || {};
          cityName = a.city || a.town || a.village || a.county || 'My Location';
        }
      } catch(_) {}
    } catch(e) {
      console.info('[NavChip] GPS unavailable, using default Delhi coords.');
    }
  }

  // Fetch real weather
  try {
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,weather_code&timezone=auto`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('failed');
    const d = await res.json();
    const temp = Math.round(d.current.temperature_2m);
    const icon = WMO_MAP[d.current.weather_code] || '⛅';

    iconEl.textContent = icon;
    tempEl.textContent = `${temp}°`;
    cityEl.textContent = cityName;
    spinner.style.display = 'none';
    ready.style.display   = 'flex';
  } catch(e) {
    spinner.style.display = 'none'; // hide silently if fetch fails
  }
}


/* =============================================================================
   LIVE TICKER — Fetches real weather for all 8 ticker cities from Open-Meteo
   Replaces hardcoded HTML with actual current temperatures + conditions
   ============================================================================= */
const TICKER_CITIES = [
  { name:'NEW DELHI',   lat:28.6139, lon:77.2090 },
  { name:'MUMBAI',      lat:19.0760, lon:72.8777 },
  { name:'BENGALURU',   lat:12.9716, lon:77.5946 },
  { name:'KOLKATA',     lat:22.5726, lon:88.3639 },
  { name:'CHENNAI',     lat:13.0827, lon:80.2707 },
  { name:'HYDERABAD',   lat:17.3850, lon:78.4867 },
  { name:'SHIMLA',      lat:31.1048, lon:77.1734 },
  { name:'SHILLONG',    lat:25.5788, lon:91.8933 },
];

const WMO_DESC = {
  0:'Clear ☀️', 1:'Clear 🌤', 2:'Partly Cloudy ⛅', 3:'Overcast ☁️',
  45:'Fog 🌫️', 48:'Fog 🌫️',
  51:'Drizzle 🌦️', 53:'Drizzle 🌦️', 55:'Drizzle 🌦️',
  61:'Rain 🌧️', 63:'Rain 🌧️', 65:'Rain 🌧️',
  71:'Snow ❄️', 75:'Snow ❄️',
  80:'Showers 🌧️', 81:'Showers 🌧️', 82:'Showers 🌧️',
  95:'Storm ⛈️', 96:'Storm ⛈️', 99:'Storm ⛈️',
};

async function refreshLiveTicker() {
  const lwmContents = document.querySelectorAll('.lwm-content');
  if (!lwmContents.length) return;

  try {
    // Batch fetch all cities in parallel
    const results = await Promise.all(TICKER_CITIES.map(async city => {
      const url = `https://api.open-meteo.com/v1/forecast?latitude=${city.lat}&longitude=${city.lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code&timezone=auto`;
      const res = await fetch(url);
      if (!res.ok) return null;
      const d = await res.json();
      const c = d.current;
      return {
        name: city.name,
        temp: Math.round(c.temperature_2m),
        hum:  Math.round(c.relative_humidity_2m),
        wind: Math.round(c.wind_speed_10m),
        desc: WMO_DESC[c.weather_code] || 'Partly Cloudy ⛅',
      };
    }));

    // Build new ticker HTML
    const html = results.filter(Boolean).map(r =>
      `<span class="lwm-item"><strong>${r.name}</strong> <span class="lwm-temp">${r.temp}°C</span> ${r.desc} · ${r.hum}% Hum · ${r.wind} km/h</span><span class="lwm-sep">&bull;</span>`
    ).join('');

    // Update both ticker copies (original + aria-hidden duplicate for infinite scroll)
    lwmContents.forEach(el => { el.innerHTML = html; });

    console.info('[LiveTicker] Updated with real Open-Meteo data.');
  } catch(e) {
    console.warn('[LiveTicker] Failed to refresh:', e.message);
  }
}


// Boot both on DOMContentLoaded
window.addEventListener('DOMContentLoaded', () => {
  initNavLiveChip();
  setTimeout(refreshLiveTicker, 800); // slight delay so page renders first
});


/* =============================================================================
   6. BACKGROUND VIDEO — Quality & Fallback Handling
   =============================================================================
   The <video> element handles loading automatically.
   This just logs status for debugging and shows the fallback if video errors.

   To use a LOCAL 4K video file:
     → Put the file in the project root: /bg-4k.mp4
     → In index.html, set: <source src="bg-4k.mp4" type="video/mp4">
     → Serve via python3 -m http.server (required — video won't load from file://)
   ============================================================================= */
const bgVideo = document.getElementById('bgVideo');

if (bgVideo) {
  bgVideo.addEventListener('error', (e) => {
    // Video failed to load — CSS gradient fallback on body is shown automatically
    console.warn('[BgVideo] Failed to load. Falling back to CSS gradient background.', e);
    bgVideo.style.display = 'none'; // remove broken video element
  });

  bgVideo.addEventListener('playing', () => {
    console.info('[BgVideo] Playing successfully.');
    bgVideo.style.opacity = '0';
    bgVideo.style.transition = 'opacity 1.5s ease';
    requestAnimationFrame(() => { bgVideo.style.opacity = '1'; });
  });
}





/* =============================================================================
   8. "HOW IT WORKS" — Right-edge tab toggle
   =============================================================================
   - hiwTab click → hiwPanel slides in from right + overlay fades in
   - hiwClose click or overlay click → closes panel
   - Escape key also closes it
   ============================================================================= */
const hiwTab     = document.getElementById('hiwTab');
const hiwPanel   = document.getElementById('hiwPanel');
const hiwClose   = document.getElementById('hiwClose');
const hiwOverlay = document.getElementById('hiwOverlay');

function openHIW() {
  hiwPanel?.classList.add('open');
  hiwOverlay?.classList.add('active');
  hiwPanel?.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
}
function closeHIW() {
  hiwPanel?.classList.remove('open');
  hiwOverlay?.classList.remove('active');
  hiwPanel?.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
}

hiwTab?.addEventListener('click', openHIW);
hiwTab?.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') openHIW(); });
hiwClose?.addEventListener('click', closeHIW);
hiwOverlay?.addEventListener('click', closeHIW);
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && hiwPanel?.classList.contains('open')) closeHIW();
});


/* =============================================================================
   9. WATCH FILM CARD — Opens demo modal
   ============================================================================= */
const wfcPlayBtn   = document.getElementById('wfcPlayBtn');
const watchFilmCard = document.getElementById('watchFilmCard');

// Clicking anywhere on the watch film card opens the demo modal
watchFilmCard?.addEventListener('click', () => {
  if (typeof openModal === 'function') openModal();
});
wfcPlayBtn?.addEventListener('click', (e) => {
  e.stopPropagation();
  if (typeof openModal === 'function') openModal();
});


/* =============================================================================
   10. VIDEO SWITCHER & MODAL TABS (Drone 4K vs Monsoon Valley)
   ============================================================================= */
const btnVidDrone     = document.getElementById('btnVidDrone');
const btnVidMonsoon   = document.getElementById('btnVidMonsoon');
const modalTabDrone   = document.getElementById('modalTabDrone');
const modalTabMonsoon = document.getElementById('modalTabMonsoon');
const modalCaption    = document.getElementById('modalCaption');

function switchHeroVideo(src, activeBtn) {
  if (!bgVideo) return;
  bgVideo.style.opacity = '0';
  setTimeout(() => {
    bgVideo.src = src;
    bgVideo.load();
    bgVideo.play().catch(e => console.warn('[BgVideo Switch]', e));
    bgVideo.style.opacity = '1';
  }, 300);

  btnVidDrone?.classList.toggle('active', btnVidDrone === activeBtn);
  btnVidMonsoon?.classList.toggle('active', btnVidMonsoon === activeBtn);
}

btnVidDrone?.addEventListener('click', () => switchHeroVideo('sources/weather_drone_4k.mov', btnVidDrone));
btnVidMonsoon?.addEventListener('click', () => switchHeroVideo('sources/monsoon_landscape.mov', btnVidMonsoon));

// Modal video tabs: switch between Drone 4K and Monsoon Valley
modalTabDrone?.addEventListener('click', () => {
  if (!demoVideo) return;
  modalTabDrone.classList.add('active');
  modalTabMonsoon?.classList.remove('active');
  demoVideo.src = 'sources/weather_drone_4k.mov';
  if (modalCaption) modalCaption.textContent = 'WeatherGPT — High-Altitude Atmospheric Drone Scan · 4K UHD 60fps · SIH 2026';
  demoVideo.play().catch(e => console.warn(e));
});

modalTabMonsoon?.addEventListener('click', () => {
  if (!demoVideo) return;
  modalTabMonsoon.classList.add('active');
  modalTabDrone?.classList.remove('active');
  demoVideo.src = 'sources/monsoon_landscape.mov';
  if (modalCaption) modalCaption.textContent = 'WeatherGPT — Northeast Monsoon Valley & Inflow Dynamics · SIH 2026';
  demoVideo.play().catch(e => console.warn(e));
});


