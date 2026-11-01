/* ═══════════════════════════════════════════════════════════════
   JARVIS REMOTE CONTROL — Client Application
   ═══════════════════════════════════════════════════════════════ */

(() => {
  'use strict';

  // ── Configuration ──
  const API_BASE = '';
  const STATUS_POLL_INTERVAL = 2000;
  const TOKEN_KEY = 'jarvis_token';

  // ── State ──
  let token = localStorage.getItem(TOKEN_KEY) || '';
  let isConnected = false;
  let commandHistory = [];
  let statusPollTimer = null;
  let recognition = null;
  let isRecording = false;

  // ── DOM References ──
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const dom = {
    authScreen:     $('#auth-screen'),
    dashboard:      $('#dashboard'),
    authInput:      $('#auth-token-input'),
    authSubmit:     $('#auth-submit-btn'),
    authError:      $('#auth-error'),
    connectionDot:  $('#connection-dot'),
    accessUrl:      $('#access-url'),
    btnLogout:      $('#btn-logout'),
    statusOrb:      $('#status-orb'),
    statusLabel:    $('#status-label'),
    commandInput:   $('#command-input'),
    sendCmdBtn:     $('#send-cmd-btn'),
    micBtn:         $('#mic-btn'),
    appInput:       $('#app-input'),
    appOpenBtn:     $('#app-open-btn'),
    appCloseBtn:    $('#app-close-btn'),
    chatMessages:   $('#chat-messages'),
    chatInput:      $('#chat-input'),
    chatSendBtn:    $('#chat-send-btn'),
    historyList:    $('#history-list'),
    screenshotModal:$('#screenshot-modal'),
    screenshotImg:  $('#screenshot-img'),
    modalCloseBtn:  $('#modal-close-btn'),
    toastContainer: $('#toast-container'),
    particles:      $('#particles'),
    apodImg:        $('#apod-img'),
    apodTitle:      $('#apod-title'),
    apodLoading:    $('#apod-loading'),
    marsImg:        $('#mars-img'),
    marsSol:        $('#mars-sol'),
    marsLoading:    $('#mars-loading'),
    launchesList:   $('#launches-list'),
    asteroidsList:  $('#asteroids-list')
  };

  // ═══════════════════════════════════════════════════════════════
  //  UTILITIES
  // ═══════════════════════════════════════════════════════════════

  function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    dom.toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.animation = 'toastOut 0.4s ease forwards';
      setTimeout(() => toast.remove(), 400);
    }, 3500);
  }

  function formatTime(date) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
  }

  function playAudioIfPresent(data) {
    if (data && data.audio_data) {
      const snd = new Audio("data:audio/mp3;base64," + data.audio_data);
      snd.play().catch(e => console.error("Audio play error:", e));
    }
  }

  // ═══════════════════════════════════════════════════════════════
  //  API LAYER
  // ═══════════════════════════════════════════════════════════════

  async function apiFetch(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const headers = {
      'Authorization': `Bearer ${token}`,
      ...(options.headers || {}),
    };
    if (options.body && typeof options.body === 'object' && !(options.body instanceof Blob)) {
      headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(options.body);
    }
    const res = await fetch(url, { ...options, headers });
    if (res.status === 401 || res.status === 403) {
      showToast('Authentication failed — token invalid', 'error');
      logout();
      throw new Error('Unauthorized');
    }
    return res;
  }

  async function apiJSON(endpoint, options = {}) {
    const res = await apiFetch(endpoint, options);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  }

  // ═══════════════════════════════════════════════════════════════
  //  AUTH
  // ═══════════════════════════════════════════════════════════════

  function showAuth() {
    dom.authScreen.style.display = 'flex';
    dom.dashboard.classList.remove('active');
    stopStatusPolling();
    dom.authInput.value = '';
    dom.authError.style.display = 'none';
    setTimeout(() => dom.authInput.focus(), 300);
  }

  function showDashboard() {
    dom.authScreen.style.display = 'none';
    dom.dashboard.classList.add('active');
    dom.accessUrl.textContent = window.location.origin;
    startStatusPolling();
    dom.commandInput.focus();
    loadSpaceData();
  }

  async function loadSpaceData() {
    fetchApod();
    fetchMars();
    fetchLaunches();
    fetchAsteroids();
  }

  async function fetchApod() {
    try {
      const res = await apiJSON('/api/space/apod');
      if (res && res.data) {
        dom.apodImg.src = res.data.url || res.data.local_path || '';
        dom.apodImg.style.display = 'block';
        dom.apodTitle.textContent = res.data.title || 'APOD';
        dom.apodLoading.style.display = 'none';
      }
    } catch (e) {
      dom.apodLoading.textContent = 'Feed offline';
      dom.apodTitle.textContent = 'Data Unavailable';
    }
  }

  async function fetchMars() {
    try {
      const res = await apiJSON('/api/space/mars');
      if (res && res.data) {
        dom.marsImg.src = res.data.img_src || '';
        dom.marsImg.style.display = 'block';
        dom.marsSol.textContent = `Sol: ${res.data.sol || '--'}`;
        dom.marsLoading.style.display = 'none';
      }
    } catch (e) {
      dom.marsLoading.textContent = 'Feed offline';
      dom.marsSol.textContent = 'Sol: --';
    }
  }

  async function fetchLaunches() {
    try {
      const res = await apiJSON('/api/space/launches');
      if (res && res.data && res.data.length > 0) {
        dom.launchesList.innerHTML = res.data.map(l => `<li>${escapeHtml(l.name)}<br><small style="color:var(--text-muted)">${new Date(l.window_start).toLocaleString()}</small></li>`).join('');
      } else {
        dom.launchesList.innerHTML = '<li>No upcoming launches</li>';
      }
    } catch (e) {
      dom.launchesList.innerHTML = '<li class="loading">Feed offline</li>';
    }
  }

  async function fetchAsteroids() {
    try {
      const res = await apiJSON('/api/space/asteroids');
      if (res && res.data && res.data.length > 0) {
        dom.asteroidsList.innerHTML = res.data.map(a => {
          const isHazardous = a.is_potentially_hazardous_asteroid;
          return `<li style="border-left-color: ${isHazardous ? 'var(--accent-red)' : 'var(--accent-green)'}">
            ${escapeHtml(a.name)}<br>
            <small style="color:var(--text-muted)">Miss Distance: ${parseFloat(a.close_approach_data[0].miss_distance.lunar).toFixed(2)} LD | Hazard: ${isHazardous ? 'YES' : 'NO'}</small>
          </li>`;
        }).join('');
      } else {
        dom.asteroidsList.innerHTML = '<li>No hazardous objects detected</li>';
      }
    } catch (e) {
      dom.asteroidsList.innerHTML = '<li class="loading">Scanner offline</li>';
    }
  }

  async function authenticate() {
    const inputToken = dom.authInput.value.trim();
    if (!inputToken) {
      dom.authError.textContent = 'Please enter an access token.';
      dom.authError.style.display = 'block';
      return;
    }
    token = inputToken;
    dom.authSubmit.disabled = true;
    dom.authSubmit.textContent = 'Connecting…';

    try {
      const res = await fetch(`${API_BASE}/api/status`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        localStorage.setItem(TOKEN_KEY, token);
        showToast('Connected to Jarvis', 'success');
        showDashboard();
      } else {
        dom.authError.textContent = 'Invalid token or server unreachable.';
        dom.authError.style.display = 'block';
        token = '';
      }
    } catch {
      dom.authError.textContent = 'Cannot reach the server. Check your connection.';
      dom.authError.style.display = 'block';
      token = '';
    } finally {
      dom.authSubmit.disabled = false;
      dom.authSubmit.textContent = 'Authenticate';
    }
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    token = '';
    isConnected = false;
    updateConnectionDot(false);
    showAuth();
    showToast('Disconnected', 'info');
  }

  // ═══════════════════════════════════════════════════════════════
  //  STATUS POLLING & LIVE SYNC
  // ═══════════════════════════════════════════════════════════════

  let lastChatlogJson = '';

  function startStatusPolling() {
    pollStatus();
    statusPollTimer = setInterval(pollStatus, 800);
  }

  function stopStatusPolling() {
    if (statusPollTimer) {
      clearInterval(statusPollTimer);
      statusPollTimer = null;
    }
  }

  async function pollStatus() {
    try {
      const data = await apiJSON('/api/live');
      updateConnectionDot(true);
      updateStatusOrb(data.assistant_status || 'available');

      // Update mic button status in top bar
      const topMicBtn = document.getElementById('top-mic-btn');
      if (topMicBtn) {
        if (data.mic_active) {
          topMicBtn.innerHTML = '🎙 Mic: ON';
          topMicBtn.style.color = '#50fa7b';
          topMicBtn.style.borderColor = 'rgba(80, 250, 123, 0.4)';
          topMicBtn.style.background = 'rgba(80, 250, 123, 0.15)';
        } else {
          topMicBtn.innerHTML = '🔇 Mic: OFF';
          topMicBtn.style.color = '#ff5555';
          topMicBtn.style.borderColor = 'rgba(255, 85, 85, 0.4)';
          topMicBtn.style.background = 'rgba(255, 85, 85, 0.15)';
        }
      }

      // Live synchronize chat messages with backend ChatLog
      if (data.chatlog && Array.isArray(data.chatlog) && data.chatlog.length > 0) {
        const curJson = JSON.stringify(data.chatlog);
        if (curJson !== lastChatlogJson) {
          lastChatlogJson = curJson;
          renderLiveChat(data.chatlog);
        }
      }
    } catch {
      updateConnectionDot(false);
    }
  }

  function renderLiveChat(chatlog) {
    if (!dom.chatMessages) return;
    dom.chatMessages.innerHTML = '';
    chatlog.forEach(msg => {
      const isUser = (msg.role === 'user');
      const sender = isUser ? 'user' : 'jarvis';
      const label = isUser ? 'Pruthvi' : 'FRIDAY';
      const bubble = document.createElement('div');
      bubble.className = `chat-bubble ${sender}`;
      bubble.innerHTML = `<div class="sender">${label}</div>${escapeHtml(msg.content)}`;
      dom.chatMessages.appendChild(bubble);
    });
    dom.chatMessages.scrollTop = dom.chatMessages.scrollHeight;
  }

  function updateConnectionDot(connected) {
    isConnected = connected;
    dom.connectionDot.classList.toggle('connected', connected);
    dom.connectionDot.title = connected ? 'Connected' : 'Disconnected';
  }

  function updateStatusOrb(status) {
    const state = status.toLowerCase();
    const states = ['available', 'listening', 'thinking', 'answering'];
    const icons  = { available: '🤖', listening: '👂', thinking: '🧠', answering: '💬' };
    const labels = { available: 'AVAILABLE', listening: 'LISTENING', thinking: 'THINKING', answering: 'ANSWERING' };

    const current = states.includes(state) ? state : 'available';

    dom.statusOrb.className = `orb ${current}`;
    dom.statusOrb.querySelector('.orb-icon').textContent = icons[current];
    dom.statusLabel.className = `status-label ${current}`;
    dom.statusLabel.textContent = labels[current];
  }

  // ═══════════════════════════════════════════════════════════════
  //  COMMANDS
  // ═══════════════════════════════════════════════════════════════

  async function sendCommand(text) {
    if (!text.trim()) return;
    dom.commandInput.value = '';

    try {
      const data = await apiJSON('/api/command', {
        method: 'POST',
        body: { command: text },
      });
      addHistoryItem(text, data.result || 'Done', 'success');
      showToast('Command executed', 'success');
      playAudioIfPresent(data);
    } catch (err) {
      addHistoryItem(text, err.message, 'error');
      showToast('Command failed', 'error');
    }
  }

  async function sendSystemCommand(cmd) {
    try {
      const data = await apiJSON('/api/system', {
        method: 'POST',
        body: { command: cmd },
      });
      addHistoryItem(`[system] ${cmd}`, data.result || 'Done', 'success');
      showToast(`${cmd} — OK`, 'success');
    } catch (err) {
      addHistoryItem(`[system] ${cmd}`, err.message, 'error');
      showToast(`${cmd} — failed`, 'error');
    }
  }

  // ═══════════════════════════════════════════════════════════════
  //  APP LAUNCHER
  // ═══════════════════════════════════════════════════════════════

  async function openApp(name) {
    if (!name.trim()) return showToast('Enter an app name', 'error');
    try {
      await apiJSON('/api/open', { method: 'POST', body: { app: name } });
      addHistoryItem(`Open: ${name}`, 'Launched', 'success');
      showToast(`Opened ${name}`, 'success');
    } catch {
      addHistoryItem(`Open: ${name}`, 'Failed', 'error');
      showToast(`Failed to open ${name}`, 'error');
    }
  }

  async function closeApp(name) {
    if (!name.trim()) return showToast('Enter an app name', 'error');
    try {
      await apiJSON('/api/close', { method: 'POST', body: { app: name } });
      addHistoryItem(`Close: ${name}`, 'Closed', 'success');
      showToast(`Closed ${name}`, 'success');
    } catch {
      addHistoryItem(`Close: ${name}`, 'Failed', 'error');
      showToast(`Failed to close ${name}`, 'error');
    }
  }

  // ═══════════════════════════════════════════════════════════════
  //  CHAT
  // ═══════════════════════════════════════════════════════════════

  async function sendChat(message) {
    if (!message.trim()) return;
    dom.chatInput.value = '';

    addChatBubble(message, 'user');

    try {
      const data = await apiJSON('/api/chat', {
        method: 'POST',
        body: { message },
      });
      addChatBubble(data.response || 'No response.', 'jarvis');
      playAudioIfPresent(data);
    } catch {
      addChatBubble('Error: Could not reach Jarvis.', 'jarvis');
    }
  }

  function addChatBubble(text, sender) {
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${sender}`;
    bubble.innerHTML = `<div class="sender">${sender === 'user' ? 'You' : 'Jarvis'}</div>${escapeHtml(text)}`;
    dom.chatMessages.appendChild(bubble);
    dom.chatMessages.scrollTop = dom.chatMessages.scrollHeight;
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // ═══════════════════════════════════════════════════════════════
  //  SPEAK
  // ═══════════════════════════════════════════════════════════════

  async function speak(text) {
    try {
      const data = await apiJSON('/api/speak', { method: 'POST', body: { text } });
      playAudioIfPresent(data);
    } catch {
      // silent fail
    }
  }

  // ═══════════════════════════════════════════════════════════════
  //  SCREENSHOT
  // ═══════════════════════════════════════════════════════════════

  async function takeScreenshot() {
    showToast('Capturing screenshot…', 'info');
    try {
      const res = await apiFetch('/api/screenshot');
      if (!res.ok) throw new Error('Failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      dom.screenshotImg.src = url;
      dom.screenshotModal.classList.add('active');
      addHistoryItem('[system] screenshot', 'Captured', 'success');
    } catch {
      showToast('Screenshot failed', 'error');
      addHistoryItem('[system] screenshot', 'Failed', 'error');
    }
  }

  function closeModal() {
    dom.screenshotModal.classList.remove('active');
    // Revoke blob URL after closing
    setTimeout(() => {
      if (dom.screenshotImg.src.startsWith('blob:')) {
        URL.revokeObjectURL(dom.screenshotImg.src);
      }
    }, 300);
  }

  // ═══════════════════════════════════════════════════════════════
  //  COMMAND HISTORY
  // ═══════════════════════════════════════════════════════════════

  function addHistoryItem(cmd, result, status) {
    const item = { cmd, result, status, time: new Date() };
    commandHistory.unshift(item);
    if (commandHistory.length > 100) commandHistory.pop();
    renderHistory();
  }

  function renderHistory() {
    if (commandHistory.length === 0) {
      dom.historyList.innerHTML = '<div class="history-empty">No commands yet</div>';
      return;
    }
    dom.historyList.innerHTML = commandHistory.map(item => `
      <div class="history-item">
        <span class="history-time">${formatTime(item.time)}</span>
        <div class="history-content">
          <div class="history-cmd">${escapeHtml(item.cmd)}</div>
          ${item.result ? `<div class="history-result">${escapeHtml(item.result)}</div>` : ''}
        </div>
        <span class="history-badge ${item.status}">${item.status}</span>
      </div>
    `).join('');
  }

  // ═══════════════════════════════════════════════════════════════
  //  SPEECH RECOGNITION
  // ═══════════════════════════════════════════════════════════════

  function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      dom.micBtn.title = 'Speech not supported in this browser';
      dom.micBtn.style.opacity = '0.4';
      dom.micBtn.style.cursor = 'not-allowed';
      return;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onresult = (e) => {
      const transcript = e.results[0][0].transcript;
      dom.commandInput.value = transcript;
      stopRecording();
      showToast(`Heard: "${transcript}"`, 'info');
    };

    recognition.onerror = (e) => {
      console.error('Speech error:', e.error);
      stopRecording();
      if (e.error !== 'aborted') {
        showToast('Voice recognition error', 'error');
      }
    };

    recognition.onend = () => {
      stopRecording();
    };
  }

  function toggleRecording() {
    if (!recognition) return showToast('Speech not supported', 'error');
    if (isRecording) {
      recognition.abort();
      stopRecording();
    } else {
      startRecording();
    }
  }

  function startRecording() {
    isRecording = true;
    dom.micBtn.classList.add('recording');
    dom.micBtn.title = 'Listening… (click to stop)';
    try {
      recognition.start();
    } catch {
      stopRecording();
    }
  }

  function stopRecording() {
    isRecording = false;
    dom.micBtn.classList.remove('recording');
    dom.micBtn.title = 'Voice Input';
  }

  // ═══════════════════════════════════════════════════════════════
  //  PARTICLES (decorative background)
  // ═══════════════════════════════════════════════════════════════

  function initParticles() {
    const count = 30;
    for (let i = 0; i < count; i++) {
      const p = document.createElement('div');
      p.className = 'particle';
      p.style.left = `${Math.random() * 100}%`;
      p.style.animationDuration = `${12 + Math.random() * 20}s`;
      p.style.animationDelay = `${Math.random() * 15}s`;
      p.style.width = p.style.height = `${1 + Math.random() * 2}px`;
      p.style.background = Math.random() > 0.5
        ? 'rgba(0, 212, 255, 0.25)'
        : 'rgba(189, 147, 249, 0.2)';
      dom.particles.appendChild(p);
    }
  }

  // ═══════════════════════════════════════════════════════════════
  //  EVENT BINDINGS
  // ═══════════════════════════════════════════════════════════════

  function bindEvents() {
    // Auth
    dom.authSubmit.addEventListener('click', authenticate);
    dom.authInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') authenticate();
    });

    // Logout
    dom.btnLogout.addEventListener('click', logout);

    // Command bar
    dom.sendCmdBtn.addEventListener('click', () => sendCommand(dom.commandInput.value));
    dom.commandInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') sendCommand(dom.commandInput.value);
    });

    // Mic
    dom.micBtn.addEventListener('click', toggleRecording);

    // Quick actions
    $$('.action-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const cmd = btn.dataset.cmd;
        if (!cmd) return;
        if (cmd === 'screenshot') {
          takeScreenshot();
        } else if (cmd === 'camera' || cmd === 'switch camera' || cmd.startsWith('learn face')) {
          sendCommand(cmd);
        } else {
          sendSystemCommand(cmd);
        }
      });
    });

    // Top Bar Stop & Mic controls
    document.getElementById('top-stop-btn')?.addEventListener('click', async () => {
      try {
        await apiJSON('/api/stop', { method: 'POST' });
        showToast('Speech halted', 'info');
      } catch (e) {
        showToast('Stop error: ' + e.message, 'error');
      }
    });

    document.getElementById('top-mic-btn')?.addEventListener('click', async () => {
      try {
        const res = await apiJSON('/api/mic/toggle', { method: 'POST' });
        showToast(`Mic turned ${res.mic_active ? 'ON' : 'OFF'}`, 'info');
        pollStatus();
      } catch (e) {
        showToast('Toggle error: ' + e.message, 'error');
      }
    });

    // App launcher
    dom.appOpenBtn.addEventListener('click', () => openApp(dom.appInput.value));
    dom.appCloseBtn.addEventListener('click', () => closeApp(dom.appInput.value));
    dom.appInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') openApp(dom.appInput.value);
    });

    // Chat
    dom.chatSendBtn.addEventListener('click', () => sendChat(dom.chatInput.value));
    dom.chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') sendChat(dom.chatInput.value);
    });

    // Screenshot modal
    dom.screenshotModal.addEventListener('click', (e) => {
      if (e.target === dom.screenshotModal) closeModal();
    });
    dom.modalCloseBtn.addEventListener('click', closeModal);
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && dom.screenshotModal.classList.contains('active')) {
        closeModal();
      }
    });
  }

  // ═══════════════════════════════════════════════════════════════
  //  INITIALIZATION
  // ═══════════════════════════════════════════════════════════════

  async function init() {
    initParticles();
    initSpeechRecognition();
    bindEvents();

    if (!token) {
      token = 'jarvis2026';
    }

    // Try auto-connecting
    try {
      const res = await fetch(`${API_BASE}/api/status`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        localStorage.setItem(TOKEN_KEY, token);
        showDashboard();
        return;
      }
    } catch (e) {
      // Server may still be starting up, continue to dashboard
    }

    if (token) {
      showDashboard();
    } else {
      showAuth();
    }
  }

  // Boot
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

// ==========================================
// MOBILE COMMAND CENTER — GPS & NAVIGATION
// ==========================================

let watchId = null;

function getJarvisToken() {
    return localStorage.getItem('jarvisToken');
}

function startGPS() {
    if ('geolocation' in navigator) {
        const el = document.getElementById('nav-current-location');
        if (el) el.innerText = 'Acquiring GPS signal...';
        watchId = navigator.geolocation.watchPosition(
            (pos) => {
                const lat = pos.coords.latitude;
                const lon = pos.coords.longitude;
                if (el) el.innerText = lat.toFixed(5) + ', ' + lon.toFixed(5);
                
                const t = getJarvisToken();
                if(t) {
                    fetch('/api/location', {
                        method: 'POST',
                        headers: { 'Authorization': 'Bearer ' + t, 'Content-Type': 'application/json' },
                        body: JSON.stringify({ lat: lat, lon: lon, accuracy: pos.coords.accuracy })
                    }).catch(e => console.error('GPS send failed:', e));
                }
            },
            (err) => {
                console.error('GPS Error:', err);
                if (el) el.innerText = 'GPS Denied or Error';
            },
            { enableHighAccuracy: true, maximumAge: 5000 }
        );
    }
}

function stopGPS() {
    if (watchId !== null) {
        navigator.geolocation.clearWatch(watchId);
        watchId = null;
    }
}

function displayNavigationResult(data) {
    const routeInfo = document.getElementById('nav-route-info');
    if (routeInfo) routeInfo.style.display = 'block';
    
    const d = document.getElementById('nav-distance');
    if(d) d.innerText = data.distance_km + ' km';
    const eta = document.getElementById('nav-eta');
    if(eta) eta.innerText = data.duration_min + ' min';
    const cdir = document.getElementById('nav-compass-dir');
    if(cdir) cdir.innerText = data.compass;
    
    // Rotate arrow
    const arrow = document.getElementById('nav-compass-arrow');
    if(arrow) arrow.style.transform = `rotate(${data.bearing}deg)`;
    const cb = document.getElementById('nav-compass-bearing');
    if(cb) cb.innerText = data.bearing + '°';
    
    // Weather
    const weatherEl = document.getElementById('nav-weather');
    if (data.dest_weather && weatherEl) {
        weatherEl.style.display = 'block';
        document.getElementById('nav-weather-info').innerText = `${data.dest_weather.temp}°C, ${data.dest_weather.condition}`;
    } else if (weatherEl) {
        weatherEl.style.display = 'none';
    }
    
    // Steps
    const stepsList = document.getElementById('nav-steps-list');
    if (stepsList) {
        stepsList.innerHTML = '';
        if (data.steps && data.steps.length > 0) {
            data.steps.forEach(s => {
                const li = document.createElement('li');
                li.innerHTML = `<span class="step-dist">${s.distance_m}m</span><span class="step-text">${s.instruction}</span>`;
                stepsList.appendChild(li);
            });
        } else {
            stepsList.innerHTML = '<li>No steps available.</li>';
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('nav-go-btn')?.addEventListener('click', async () => {
        const dest = document.getElementById('nav-dest-input').value.trim();
        if (!dest) return;
        const btn = document.getElementById('nav-go-btn');
        btn.innerText = '...';
        try {
            const res = await fetch('/api/navigate', {
                method: 'POST',
                headers: { 'Authorization': 'Bearer ' + getJarvisToken(), 'Content-Type': 'application/json' },
                body: JSON.stringify({ destination: dest })
            });
            const json = await res.json();
            if (json.status === 'success') {
                displayNavigationResult(json.data);
            } else {
                alert(json.message);
            }
        } catch (e) {
            alert('Navigation failed');
        }
        btn.innerText = 'Navigate';
    });

    document.getElementById('nav-home-btn')?.addEventListener('click', async () => {
        const btn = document.getElementById('nav-home-btn');
        btn.innerText = '...';
        try {
            const res = await fetch('/api/navigate/home', {
                method: 'POST',
                headers: { 'Authorization': 'Bearer ' + getJarvisToken() }
            });
            const json = await res.json();
            if (json.status === 'success') {
                displayNavigationResult(json.data);
            } else {
                alert(json.message);
            }
        } catch (e) {
            alert('Navigation failed');
        }
        btn.innerText = '🏠 Home';
    });

    // ==========================================
    // MOBILE COMMAND CENTER — CAMERA
    // ==========================================

    let cameraStream = null;
    const video = document.getElementById('camera-video');
    const canvas = document.getElementById('camera-canvas');

    async function startCamera() {
        try {
            cameraStream = await navigator.mediaDevices.getUserMedia({ 
                video: { facingMode: 'environment', width: { ideal: 640 } } 
            });
            if(video) video.srcObject = cameraStream;
            const ov = document.getElementById('camera-overlay');
            if(ov) ov.style.display = 'none';
            const cap = document.getElementById('camera-capture-btn');
            if(cap) cap.disabled = false;
            const st = document.getElementById('camera-start-btn');
            if(st) {
                st.innerText = 'Stop Camera';
                st.style.backgroundColor = 'rgba(255, 85, 85, 0.2)';
                st.style.color = '#ff5555';
                st.style.borderColor = '#ff5555';
            }
        } catch (err) {
            console.error('Camera error:', err);
        }
    }

    function stopCamera() {
        if (cameraStream) {
            cameraStream.getTracks().forEach(t => t.stop());
            cameraStream = null;
        }
        if (video) video.srcObject = null;
        const ov = document.getElementById('camera-overlay');
        if(ov) ov.style.display = 'flex';
        const cap = document.getElementById('camera-capture-btn');
        if(cap) cap.disabled = true;
        const st = document.getElementById('camera-start-btn');
        if(st) {
            st.innerText = 'Start Camera';
            st.style.backgroundColor = '';
            st.style.color = '';
            st.style.borderColor = '';
        }
    }

    document.getElementById('camera-start-btn')?.addEventListener('click', () => {
        if (cameraStream) stopCamera();
        else startCamera();
    });
    document.getElementById('camera-overlay')?.addEventListener('click', () => {
        if (!cameraStream) startCamera();
    });

    document.getElementById('camera-capture-btn')?.addEventListener('click', async () => {
        if (!cameraStream || !video || !canvas) return;
        
        const btn = document.getElementById('camera-capture-btn');
        btn.innerText = 'Analyzing...';
        btn.disabled = true;
        
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0);
        const base64Data = canvas.toDataURL('image/jpeg', 0.7).split(',')[1];
        
        try {
            const res = await fetch('/api/camera/analyze', {
                method: 'POST',
                headers: { 'Authorization': 'Bearer ' + getJarvisToken(), 'Content-Type': 'application/json' },
                body: JSON.stringify({ frame: base64Data, question: 'What objects do you see?' })
            });
            const json = await res.json();
            if (json.status === 'success') {
                const resDiv = document.getElementById('camera-result');
                if(resDiv) resDiv.style.display = 'block';
                const cont = document.getElementById('camera-result-content');
                if(cont) cont.innerText = json.summary;
                
                const objContainer = document.getElementById('camera-result-objects');
                if(objContainer) {
                    objContainer.innerHTML = '';
                    json.objects.forEach(o => {
                        const span = document.createElement('span');
                        span.innerText = `${o.name} (${o.confidence})`;
                        objContainer.appendChild(span);
                    });
                }
                
                if (json.audio_data) {
                    const snd = new Audio("data:audio/mp3;base64," + json.audio_data);
                    snd.play().catch(e => console.error("Audio play error:", e));
                }
            } else {
                alert(json.message);
            }
        } catch (e) {
            console.error(e);
            alert('Analysis failed');
        }
        
        btn.innerText = 'Capture & Analyze';
        btn.disabled = false;
    });

    // Start GPS if token exists on load
    if (getJarvisToken()) startGPS();
});
