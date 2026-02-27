/* ============================================
   AgriMitra — Full App Logic + AI Chatbot
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {

  // ===== AUTH STATE CHECK =====
  const user = JSON.parse(localStorage.getItem('agrimitra_user') || 'null');
  if (!user || !user.loggedIn) {
    window.location.href = 'login.html';
    return;
  }

  // Populate user info
  const nameInitials = user.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
  const sidebarAvatar = document.getElementById('sidebarAvatar');
  const sidebarName = document.getElementById('sidebarUserName');
  const sidebarLoc = document.getElementById('sidebarUserLoc');
  if (sidebarAvatar) sidebarAvatar.textContent = nameInitials;
  if (sidebarName) sidebarName.textContent = user.name;
  if (sidebarLoc) sidebarLoc.textContent = '📍 ' + (user.location || 'India');

  // Logout
  document.getElementById('logoutBtn')?.addEventListener('click', () => {
    localStorage.removeItem('agrimitra_user');
    window.location.href = 'login.html';
  });

  // Apply translations based on saved language
  const savedLang = getSavedLanguage();
  applyTranslations(savedLang);

  // ===== ELEMENTS =====
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');
  const hamburger = document.getElementById('hamburgerBtn');
  const sidebarNavItems = document.querySelectorAll('.sidebar-nav .nav-item[data-screen]');
  const mobileNavItems = document.querySelectorAll('.mobile-nav-item[data-screen]');
  const screens = document.querySelectorAll('.screen');
  const pageTitleText = document.getElementById('pageTitleText');
  const pageTitle = document.getElementById('pageTitle');

  let currentScreen = 'screen-home';
  let riskInterval = null;
  let weatherMap = null;
  let mapMarkers = [];
  let chromeAISession = null;
  let isUsingLocalAI = false;

  const pageTitles = {
    'screen-home': { icon: '🏠', textKey: 'harvestDashboard', defaultText: 'Harvest Dashboard' },
    'screen-markets': { icon: '🏪', textKey: 'marketMatchmaker', defaultText: 'Market Matchmaker' },
    'screen-protect': { icon: '🛡️', textKey: 'storageProtection', defaultText: 'Storage & Protection' },
    'screen-sodhak': { icon: '💎', textKey: 'liveGemini', defaultText: 'Sodhak AI' },
    'screen-weather': { icon: '🌦️', textKey: 'weatherOutlook', defaultText: 'Weather Forecast' },
    'screen-harvest-detail': { icon: '🌾', textKey: 'harvestInsights', defaultText: 'Harvest Insights' },
    'screen-settings': { icon: '⚙️', textKey: 'userSettings', defaultText: 'Settings' },
    'screen-market-detail': { icon: '📈', textKey: 'priceAnalysis', defaultText: 'Market Detail' },
    'screen-protect-detail': { icon: '📊', textKey: 'protectionAnalytics', defaultText: 'Protection Analytics' },
  };

  // ===== NAVIGATION =====
  function navigateTo(screenId) {
    if (screenId === currentScreen) return;
    screens.forEach(s => {
      s.classList.remove('active');
      if (s.id === screenId) s.classList.add('active');
    });
    sidebarNavItems.forEach(i => i.classList.toggle('active', i.dataset.screen === screenId));
    mobileNavItems.forEach(i => i.classList.toggle('active', i.dataset.screen === screenId));

    const titleInfo = pageTitles[screenId] || { icon: '📄', textKey: 'dashboard' };
    if (pageTitleText && titleInfo) {
      pageTitleText.textContent = t(titleInfo.textKey) || titleInfo.defaultText;
      pageTitle.querySelector('span:first-child').textContent = titleInfo.icon;
    }

    currentScreen = screenId;
    closeSidebar();

    // Manage intervals
    if (riskInterval) { clearInterval(riskInterval); riskInterval = null; }
    if (screenId === 'screen-protect') {
      updateRiskLogic(); // Initial run
      riskInterval = setInterval(updateRiskLogic, 240000); // 4 minute gap
    }

    triggerScreenAnimations(screenId);
  }

  sidebarNavItems.forEach(i => i.addEventListener('click', () => { if (i.dataset.screen) navigateTo(i.dataset.screen); }));
  mobileNavItems.forEach(i => i.addEventListener('click', () => { if (i.dataset.screen) navigateTo(i.dataset.screen); }));

  // ===== SIDEBAR TOGGLE =====
  function openSidebar() { sidebar.classList.add('open'); overlay.classList.add('visible'); document.body.style.overflow = 'hidden'; }
  function closeSidebar() { sidebar.classList.remove('open'); overlay.classList.remove('visible'); document.body.style.overflow = ''; }

  hamburger?.addEventListener('click', () => sidebar.classList.contains('open') ? closeSidebar() : openSidebar());
  overlay?.addEventListener('click', closeSidebar);

  // ===== GRAIN SELECTION DATA =====
  const GRAIN_DATA = {
    wheat: {
      id: 'wheat',
      icon: '🌾',
      nameKey: 'wheat',
      seasonKey: 'rabiSeason',
      price: '₹2,200',
      statusKey: 'waitToHarvest',
      subKey: 'bestTime',
      health: 'Excellent',
      moisture: '18%',
      day: '95'
    },
    rice: {
      id: 'rice',
      icon: '🍚',
      nameKey: 'ricePaddy',
      seasonKey: 'kharifSeason',
      price: '₹2,450',
      statusKey: 'harvestNow',
      subKey: 'perfectConditions',
      health: 'Good',
      moisture: '22%',
      day: '110'
    },
    corn: {
      id: 'corn',
      icon: '🌽',
      nameKey: 'cornMaize',
      seasonKey: 'kharifSeason',
      price: '₹1,850',
      statusKey: 'waitToHarvest',
      subKey: 'bestTime',
      health: 'Excellent',
      moisture: '15%',
      day: '85'
    },
    mustard: {
      id: 'mustard',
      icon: '🌱',
      nameKey: 'mustard',
      seasonKey: 'rabiSeason',
      price: '₹5,400',
      statusKey: 'harvestNow',
      subKey: 'perfectConditions',
      health: 'Excellent',
      moisture: '12%',
      day: '90'
    }
  };

  let selectedGrain = localStorage.getItem('agrimitra_selected_grain') || 'wheat';

  function updateGrainUI(grainId) {
    const data = GRAIN_DATA[grainId] || GRAIN_DATA.wheat;

    // Update pills
    document.querySelectorAll('.grain-pill').forEach(p => {
      p.classList.toggle('active', p.dataset.grain === grainId);
    });

    // Update Hero Card
    const harvestHero = document.getElementById('harvestCard');
    if (harvestHero) {
      harvestHero.querySelector('.crop-icon').textContent = data.icon;
      harvestHero.querySelector('.crop-name').textContent = `${t(data.nameKey)} · ${t(data.seasonKey)}`;

      const statusText = document.getElementById('harvestStatus');
      const statusSub = document.getElementById('harvestSub');

      if (statusText) statusText.textContent = t(data.statusKey);
      if (statusSub) statusSub.textContent = t(data.subKey);

      harvestHero.classList.remove('wait', 'go');
      harvestHero.classList.add(data.statusKey === 'harvestNow' ? 'go' : 'wait');
    }

    // Update Hero Stats (Best Price)
    const bestPriceEl = document.querySelector('.hero-stat-number');
    if (bestPriceEl) bestPriceEl.textContent = data.price;

    // Update Quick Stats
    const statsValue = document.querySelectorAll('.stat-value-bold');
    if (statsValue.length >= 3) {
      statsValue[0].textContent = t(data.nameKey);
      statsValue[1].textContent = `Day ${data.day}`;
      statsValue[2].textContent = data.health;
    }

    // Update Detail Screen if present
    const detailTitle = document.querySelector('#screen-harvest-detail .detail-title');
    const detailSubtitle = document.querySelector('#screen-harvest-detail .detail-subtitle');
    const detailIcon = document.querySelector('#screen-harvest-detail .detail-icon');

    if (detailTitle) detailTitle.textContent = `${t(data.nameKey)} · ${t(data.seasonKey)}`;
    if (detailSubtitle) detailSubtitle.textContent = `Sown on ${data.id === 'wheat' ? 'Nov 15, 2025' : 'Aug 10, 2025'}`;
    if (detailIcon) detailIcon.textContent = data.icon;

    // Save
    localStorage.setItem('agrimitra_selected_grain', grainId);
    selectedGrain = grainId;
  }

  // Add click listeners to grain pills
  document.querySelectorAll('.grain-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      updateGrainUI(pill.dataset.grain);
    });
  });

  // Initial UI Update
  updateGrainUI(selectedGrain);

  // Dashboard Card Clicks
  document.querySelectorAll('.clickable-card').forEach(card => {
    card.addEventListener('click', () => {
      const target = card.dataset.screen;
      const mandiName = card.dataset.mandi;
      if (target) {
        if (target === 'screen-market-detail' && mandiName) {
          initMarketDetail(mandiName, card);
        }
        navigateTo(target);
      }
    });
  });

  // Settings logic
  const settingsLangSelect = document.getElementById('settingsLangSelect');
  if (settingsLangSelect) {
    settingsLangSelect.value = localStorage.getItem('agrimitra_lang') || 'en';
    settingsLangSelect.addEventListener('change', (e) => {
      const newLang = e.target.value;
      localStorage.setItem('agrimitra_lang', newLang);
      window.location.reload(); // Quickest way to apply everything globally
    });
  }

  // Toggle units logic
  document.querySelectorAll('.toggle-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      btn.parentElement.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      localStorage.setItem('agrimitra_units', btn.innerText.includes('°C') ? 'metric' : 'imperial');
    });
  });

  // ===== ANIMATIONS =====
  function triggerScreenAnimations(screenId) {
    if (screenId === 'screen-protect') animateRiskNeedle();
    if (screenId === 'screen-weather') initWeatherMap();
    if (screenId === 'screen-sodhak') initChromeAI();
    if (screenId === 'screen-protect-detail') initProtectDetail();

    const target = document.getElementById(screenId);
    if (!target) return;
    target.querySelectorAll('.animate-in').forEach((el, i) => {
      el.style.animation = 'none';
      el.offsetHeight;
      el.style.animation = `fadeInUp 0.5s ease forwards`;
      el.style.animationDelay = `${i * 0.06}s`;
    });
  }

  // ===== WEATHER MAP (NAGPUR) =====
  function initWeatherMap() {
    if (weatherMap) {
      setTimeout(() => weatherMap.invalidateSize(), 200);
      return;
    }

    const mapContainer = document.getElementById('weatherMap');
    if (!mapContainer || typeof L === 'undefined') return;

    // Center on Nagpur
    const nagpurCoords = [21.1458, 79.0882];
    weatherMap = L.map('weatherMap', {
      zoomControl: false,
      attributionControl: false
    }).setView(nagpurCoords, 10);

    // Premium dark/light hybrid tiles
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      maxZoom: 19
    }).addTo(weatherMap);

    // Weather Data Points
    const weatherData = [
      { name: 'Nagpur City', coords: [21.1458, 79.0882], type: 'sunny', icon: '☀️' },
      { name: 'Ramtek', coords: [21.3857, 79.3275], type: 'wind', icon: '💨' },
      { name: 'Wardha', coords: [20.7453, 78.6022], type: 'rain', icon: '🌧️' },
      { name: 'Bhandara', coords: [21.1895, 79.6465], type: 'cloudy', icon: '☁️' },
      { name: 'Kamptee', coords: [21.2183, 79.2003], type: 'rain', icon: '🌧️' },
      { name: 'Kalmeshwar', coords: [21.2429, 78.9174], type: 'wind', icon: '🚩' }
    ];

    weatherData.forEach(point => {
      const markerHtml = `
        <div class="weather-marker ${point.type}">
          <span>${point.icon}</span>
          <div class="marker-label">${point.name}</div>
        </div>
      `;

      const customIcon = L.divIcon({
        html: markerHtml,
        className: '',
        iconSize: [35, 35],
        iconAnchor: [17, 17]
      });

      L.marker(point.coords, { icon: customIcon }).addTo(weatherMap)
        .bindPopup(`<strong>${point.name}</strong><br>Status: ${point.type.toUpperCase()}`);
    });

    // Add a pulsing circle for "Heavy Rain" area (Wardha)
    L.circle([20.7453, 78.6022], {
      color: '#2196F3',
      fillColor: '#2196F3',
      fillOpacity: 0.2,
      radius: 5000
    }).addTo(weatherMap);

    // Add a pulsing circle for "Heavy Wind" area (Ramtek)
    L.circle([21.3857, 79.3275], {
      color: '#FF9800',
      fillColor: '#FF9800',
      fillOpacity: 0.2,
      radius: 7000
    }).addTo(weatherMap);
  }

  // ===== RISK NEEDLE =====
  function animateRiskNeedle(targetScore = 30) {
    const needle = document.getElementById('riskNeedle');
    const label = document.getElementById('riskLabel');
    const activeArc = document.getElementById('activeArc');
    if (!needle) return;

    // Map score (0-100) to rotation (-90 to 90)
    // 0 = -90 (Safe), 33 = -30 (Moderate), 100 = 90 (High)
    const toAngle = (targetScore * 1.8) - 90;
    const startAngle = needle.dataset.currentAngle ? parseFloat(needle.dataset.currentAngle) : -90;

    const start = performance.now();
    const dur = 1400;

    (function anim(now) {
      const p = Math.min((now - start) / dur, 1);
      // Elastic easing
      const e = p === 1 ? 1 : -Math.pow(2, -10 * p) * Math.sin((p * 10 - 0.75) * (2 * Math.PI / 3)) + 1;
      const currentAngle = startAngle + (toAngle - startAngle) * e;

      needle.setAttribute('transform', `rotate(${currentAngle}, 140, 145)`);
      needle.dataset.currentAngle = currentAngle;

      if (p < 1) requestAnimationFrame(anim);
      else {
        // Update label and color after animation
        if (targetScore < 40) {
          label.className = 'risk-status safe';
          label.innerHTML = `✅ ${t('lowRiskSafe') || 'Low Risk — Safe'}`;
        } else if (targetScore < 75) {
          label.className = 'risk-status moderate';
          label.innerHTML = `🟠 ${t('moderateRisk') || 'Moderate Risk'}`;
        } else {
          label.className = 'risk-status high';
          label.innerHTML = `🚨 ${t('highRiskDanger') || 'High Risk — Danger'}`;
        }
      }
    })(start);
  }

  function updateRiskLogic() {
    const label = document.getElementById('riskLabel');
    const subtitle = label?.nextElementSibling;

    // Simulated live sensor logic (Oscillates between safe and warm)
    const timeFactor = Math.sin(Date.now() / 600000); // Gradual wave
    const temp = Math.floor(25 + (timeFactor * 10) + (Math.random() * 5));
    const hum = Math.floor(30 + (timeFactor * 20) + (Math.random() * 10));

    // Update any visible temp/hum values on screen
    document.querySelectorAll('.condition-value').forEach(el => {
      if (el.innerText.includes('°C')) el.innerText = temp + '°C';
      if (el.innerText.includes('%')) el.innerText = hum + '%';
    });

    if (subtitle && subtitle.dataset.i18n === 'basedOnTemp') {
      subtitle.innerHTML = `${t('basedOnTemp').split(':')[0]}: ${temp}°C & ${hum}%`;
    }

    // Simple risk score calculation (higher temp/hum = higher risk)
    let score = (temp - 25) * 4 + (hum - 30) * 1.5;
    score = Math.max(10, Math.min(95, score));

    animateRiskNeedle(score);

    // Update Warning (Chetavni) Card
    const warningCard = document.querySelector('.warning-card-rich');
    if (warningCard) {
      const iconEl = warningCard.querySelector('.warning-card-icon');
      const titleEl = warningCard.querySelector('.warning-card-text strong');
      const descEl = warningCard.querySelector('.warning-card-text span');

      if (score < 40) {
        warningCard.style.borderLeft = "4px solid var(--primary)";
        iconEl.innerText = "✅";
        titleEl.innerHTML = t('safeWarning');
        descEl.innerHTML = t('safeWarningDesc');
      } else if (score < 75) {
        warningCard.style.borderLeft = "4px solid #FF9800";
        iconEl.innerText = "⚠️";
        titleEl.innerHTML = t('moderateWarning');
        descEl.innerHTML = t('moderateWarningDesc');
      } else {
        warningCard.style.borderLeft = "4px solid #f44336";
        iconEl.innerText = "🚨";
        titleEl.innerHTML = t('highWarning');
        descEl.innerHTML = t('highWarningDesc');
      }
    }
  }

  // ===== INSIGHT BANNER =====
  document.getElementById('insightBanner')?.addEventListener('click', function () { this.classList.toggle('expanded'); });

  // ===== SPEAKER BUTTONS (Audio Support) =====
  document.addEventListener('click', e => {
    const btn = e.target.closest('.speaker-btn');
    if (!btn) return;
    e.stopPropagation();

    // Find nearest text to read
    const card = btn.closest('.card, .card-rich, .warning-card-rich, .tip-card-rich, .risk-meter-container');
    let textToRead = "";

    if (card) {
      // Logic to find specific text based on card type
      const title = card.querySelector('.card-title, .tip-title, .warning-card-text strong, .risk-status');
      const desc = card.querySelector('.hero-desc, .tip-meta, .warning-card-text span, .risk-subtitle');
      textToRead = (title?.innerText || "") + ". " + (desc?.innerText || "");
    }

    if (textToRead && 'speechSynthesis' in window) {
      // Cancel any ongoing speech
      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(textToRead);
      // Try to find a matching language voice
      const lang = getSavedLanguage();
      utterance.lang = lang === 'hi' ? 'hi-IN' : (lang === 'te' ? 'te-IN' : 'en-IN');

      utterance.onstart = () => btn.classList.add('playing');
      utterance.onend = () => btn.classList.remove('playing');
      utterance.onerror = () => btn.classList.remove('playing');

      window.speechSynthesis.speak(utterance);
    } else {
      // Fallback visual animation if speech fails
      btn.classList.add('playing');
      setTimeout(() => btn.classList.remove('playing'), 2000);
    }
  });

  // ===== VOICE ASSISTANT =====
  document.getElementById('sidebarMicBtn')?.addEventListener('click', function () {
    const icon = this.querySelector('.mic-icon');
    icon.textContent = '🔴';
    this.style.background = 'linear-gradient(135deg, rgba(198,40,40,0.3), rgba(198,40,40,0.2))';
    setTimeout(() => { icon.textContent = '🎙️'; this.style.background = ''; }, 3000);
  });

  // ===== HARVEST TOGGLE =====
  const harvestCard = document.getElementById('harvestCard');
  const harvestStatus = document.getElementById('harvestStatus');
  const harvestSub = document.getElementById('harvestSub');
  let isWaiting = true;

  harvestCard?.addEventListener('click', e => {
    if (e.target.closest('.speaker-btn')) return;
    isWaiting = !isWaiting;
    if (isWaiting) {
      harvestCard.classList.remove('go'); harvestCard.classList.add('wait');
      harvestStatus.textContent = t('waitToHarvest');
      harvestSub.textContent = t('bestTime');
      harvestCard.querySelector('.crop-name').textContent = t('wheatRabi');
    } else {
      harvestCard.classList.remove('wait'); harvestCard.classList.add('go');
      harvestStatus.textContent = t('harvestNow');
      harvestSub.textContent = t('perfectConditions');
      harvestCard.querySelector('.crop-name').textContent = t('wheatReady');
    }
    harvestCard.style.transform = 'scale(0.97)';
    setTimeout(() => { harvestCard.style.transform = ''; }, 200);
  });

  // ===== GREETING =====
  (function () {
    const h = new Date().getHours();
    const g = document.getElementById('greetingText');
    if (!g) return;
    const firstName = user.name.split(' ')[0];
    let timeKey = 'goodEvening';
    let icon = '🌙';
    if (h < 12) { timeKey = 'goodMorning'; icon = '🌅'; }
    else if (h < 17) { timeKey = 'goodAfternoon'; icon = '☀️'; }
    g.textContent = `${icon} ${t(timeKey)}, ${firstName}!`;
  })();

  // ===== CARD FEEDBACK =====
  document.querySelectorAll('.mandi-card').forEach(card => {
    card.addEventListener('click', e => {
      if (e.target.closest('.speaker-btn')) return;
      card.style.borderColor = 'var(--green-400)';
      card.style.backgroundColor = 'var(--green-50)';
      setTimeout(() => { card.style.borderColor = ''; card.style.backgroundColor = ''; }, 600);
    });
  });

  // ===== KEYBOARD NAV =====
  document.addEventListener('keydown', e => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    if (e.key === '1') navigateTo('screen-home');
    if (e.key === '2') navigateTo('screen-markets');
    if (e.key === '3') navigateTo('screen-protect');
    if (e.key === 'Escape') closeSidebar();
  });

  // Init
  triggerScreenAnimations('screen-home');
  // Initialize page title translation and active state on load
  const initialTitleData = pageTitles[currentScreen];
  if (pageTitleText && initialTitleData) {
    pageTitleText.textContent = t(initialTitleData.textKey) || initialTitleData.defaultText;
    pageTitle.querySelector('span:first-child').textContent = initialTitleData.icon;
  }

  const protectScreen = document.getElementById('screen-protect');
  if (protectScreen) {
    new MutationObserver(() => {
      if (protectScreen.classList.contains('active')) animateRiskNeedle();
    }).observe(protectScreen, { attributes: true, attributeFilter: ['class'] });
  }


  // =============================================
  //  AI CHATBOT ENGINE
  // =============================================

  const chatFab = document.getElementById('chatbotFab');
  const chatWindow = document.getElementById('chatbotWindow');
  const chatClose = document.getElementById('chatbotClose');
  const chatMessages = document.getElementById('chatMessages');
  const chatInput = document.getElementById('chatInput');
  const chatSendBtn = document.getElementById('chatSendBtn');
  const quickReplies = document.getElementById('quickReplies');

  let chatOpen = false;
  let firstOpen = true;

  // Toggle chat
  function toggleChat() {
    chatOpen = !chatOpen;
    chatWindow.classList.toggle('open', chatOpen);
    chatFab.classList.toggle('hidden', chatOpen);
    if (chatOpen && firstOpen) {
      firstOpen = false;
      addBotMessage("Namaste! 🙏 I'm **AgriBot**, your AI farming assistant. I can help you with:\n\n🌾 Harvest timing\n💰 Market prices\n🛡️ Storage tips\n🌦️ Weather updates\n\nAsk me anything or use the quick buttons below!");
    }
    if (chatOpen) {
      setTimeout(() => chatInput.focus(), 400);
      const badge = chatFab.querySelector('.fab-badge');
      if (badge) badge.style.display = 'none';
    }
  }

  chatFab?.addEventListener('click', toggleChat);
  chatClose?.addEventListener('click', toggleChat);

  // Send
  function sendMessage() {
    const text = chatInput.value.trim();
    if (!text) return;
    addUserMessage(text);
    chatInput.value = '';
    showTyping();
    setTimeout(() => {
      hideTyping();
      const reply = generateReply(text);
      addBotMessage(reply);
    }, 800 + Math.random() * 800);
  }

  chatSendBtn?.addEventListener('click', sendMessage);
  chatInput?.addEventListener('keydown', e => { if (e.key === 'Enter') sendMessage(); });

  // Quick replies
  quickReplies?.addEventListener('click', e => {
    const btn = e.target.closest('.quick-reply-btn');
    if (!btn) return;
    chatInput.value = btn.dataset.msg;
    sendMessage();
  });

  // Message helpers
  function addUserMessage(text) {
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const html = `
      <div class="chat-msg user">
        <div class="chat-msg-avatar">👤</div>
        <div>
          <div class="chat-msg-bubble">${escapeHtml(text)}</div>
          <div class="chat-msg-time">${time}</div>
        </div>
      </div>`;
    chatMessages.insertAdjacentHTML('beforeend', html);
    scrollChat();
  }

  function addBotMessage(text) {
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    // Simple markdown-like bold
    const formatted = escapeHtml(text).replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');
    const html = `
      <div class="chat-msg bot">
        <div class="chat-msg-avatar">🤖</div>
        <div>
          <div class="chat-msg-bubble">${formatted}</div>
          <div class="chat-msg-time">${time}</div>
        </div>
      </div>`;
    chatMessages.insertAdjacentHTML('beforeend', html);
    scrollChat();
  }

  function showTyping() {
    const html = `
      <div class="chat-msg bot" id="typingMsg">
        <div class="chat-msg-avatar">🤖</div>
        <div class="chat-msg-bubble">
          <div class="typing-indicator"><span></span><span></span><span></span></div>
        </div>
      </div>`;
    chatMessages.insertAdjacentHTML('beforeend', html);
    scrollChat();
  }

  function hideTyping() {
    document.getElementById('typingMsg')?.remove();
  }

  function scrollChat() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // ===== AI RESPONSE ENGINE =====
  function generateReply(input) {
    const q = input.toLowerCase();

    // Harvest
    if (match(q, ['harvest', 'when to harvest', 'harvesting', 'katai', 'kab kate'])) {
      return "🌾 **Harvest Recommendation: WAIT 3-4 days**\n\nHere's why:\n• 🌧️ Rain expected tomorrow — wet wheat can't be sold well\n• 📈 Wheat prices are rising — ₹200/quintal more by Friday\n• 💧 Soil moisture needs to drop a bit for clean harvesting\n\n**Best day:** Around February 28-29. I'll remind you!";
    }

    // Price / Market
    if (match(q, ['price', 'mandi', 'market', 'sell', 'wheat price', 'rate', 'bhav', 'daam', 'kimat'])) {
      return "💰 **Today's Wheat Prices:**\n\n1. **Ravi Mandi** — ₹2,200/quintal ⬆ (Best!)\n2. **Krishna Market** — ₹2,150/quintal\n3. **Guntur APMC** — ₹2,100/quintal\n4. **Tenali Mandi** — ₹2,050/quintal\n5. **Mangalagiri** — ₹1,980/quintal\n\n📈 Prices went UP ₹150 this week. Expected to rise ₹50 more by Friday!";
    }

    // Weather
    if (match(q, ['weather', 'rain', 'barish', 'mausam', 'temperature', 'forecast'])) {
      return "🌦️ **Weather Forecast — Vijayawada:**\n\n**Today:** 32°C, Partly Cloudy\n**Tomorrow:** 🌧️ Heavy rain expected (afternoon)\n**Day After:** Clearing up, 30°C\n**Weekend:** ☀️ Hot — up to 38°C\n\n⚠️ **Tip:** Don't harvest before the rain. Wait for dry weather!";
    }

    // Storage / Protection
    if (match(q, ['storage', 'store', 'spoil', 'protect', 'preservation', 'rot', 'damage', 'tarpaulin', 'cold storage'])) {
      return "🛡️ **Top Storage Tips:**\n\n1. **Cover with Tarpaulin** — ₹ Low cost, saves 15% crop\n2. **Raised Platform** — ₹₹ Medium, saves 20%\n3. **Neem Leaves** — ₹ Low cost, saves 12%\n4. **Cold Storage** — ₹₹₹ High, saves 35%\n5. **Ventilation** — Free! Saves 8%\n\n⚠️ **Warning:** Move grain to shade — 38°C expected this weekend!";
    }

    // Soil
    if (match(q, ['soil', 'mitti', 'moisture', 'fertilizer', 'manure', 'khad'])) {
      return "🌱 **Soil Update:**\n\n• **Moisture Level:** Good (optimal for wheat)\n• **pH:** 6.8 (ideal range: 6.0 - 7.5)\n• **Recommendation:** Don't irrigate before harvest — let soil dry naturally\n\n**After harvest:** Apply organic compost (₹500/acre) to replenish nutrients for next season.";
    }

    // Crop info
    if (match(q, ['crop', 'wheat', 'rice', 'what to grow', 'kya ugaye', 'fasal'])) {
      return "🌾 **Your Current Crop: Wheat (Rabi)**\n\n• Growth Stage: Day 95 of ~120\n• Health: ✅ Good\n• Expected Yield: ~18 quintals per acre\n• Expected Revenue: ~₹36,000 - ₹40,000\n\n**Next Season Tip:** Consider mustard or chickpeas for rotation!";
    }

    // Loan / Finance
    if (match(q, ['loan', 'kcc', 'kisan', 'credit', 'paisa', 'money', 'subsidy', 'scheme'])) {
      return "💳 **Government Schemes for You:**\n\n1. **Kisan Credit Card (KCC)** — Up to ₹3 lakh at 4% interest\n2. **PM-KISAN** — ₹6,000/year direct transfer\n3. **Crop Insurance (PMFBY)** — Protect against weather damage\n4. **Soil Health Card** — Free soil testing\n\n📞 Call **1800-180-1551** (toll-free) for more details.";
    }

    // Help / What can you do
    if (match(q, ['help', 'what can you do', 'features', 'kya kar sakte', 'options'])) {
      return "🤖 **I can help you with:**\n\n🌾 **Harvest Timing** — When to harvest for best results\n💰 **Market Prices** — Live mandi rates near you\n🛡️ **Storage Tips** — Protect your crop from spoilage\n🌦️ **Weather** — Forecast and alerts\n🌱 **Soil Health** — Moisture and nutrient info\n💳 **Schemes** — Government loans & subsidies\n📞 **Expert Help** — Connect with agriculture experts\n\nJust ask me anything!";
    }

    // Greeting
    if (match(q, ['hi', 'hello', 'namaste', 'hey', 'good morning', 'good afternoon', 'good evening'])) {
      const firstName = user.name.split(' ')[0];
      return `🙏 Namaste ${firstName}! How can I help you today?\n\nYou can ask me about harvest timing, market prices, weather, storage tips, or government schemes!`;
    }

    // Thank you
    if (match(q, ['thank', 'thanks', 'dhanyavaad', 'shukriya'])) {
      return "🙏 You're welcome! Happy to help. If you have more questions, just ask anytime!\n\n**Jai Kisan! 🌾**";
    }

    // Transport
    if (match(q, ['transport', 'truck', 'vehicle', 'gaadi'])) {
      return "🚛 **Transport Options:**\n\n1. **Ravi Mandi** — 12 km, ~₹800 by truck\n2. **Krishna Market** — 18 km, ~₹1,200\n3. **Guntur APMC** — 25 km, ~₹1,500\n\n💡 **Tip:** Book shared transport with neighbours to save 40% on costs! Call local transport union at 0866-XXXXXXX.";
    }

    // Pest / Disease
    if (match(q, ['pest', 'disease', 'insect', 'bug', 'keet', 'rog', 'bimari'])) {
      return "🐛 **Pest & Disease Alert:**\n\n✅ **Current Status:** No major pest threats detected\n\n**Common Wheat Issues:**\n• Yellow Rust — Watch for yellow stripes on leaves\n• Aphids — Small green insects on stems\n\n**Prevention:** Neem-based spray (₹200/acre), apply every 15 days.\n\n📞 Report issues to agriculture officer: 1800-XXX-XXXX";
    }

    // Default
    return "🤔 I'm not sure about that, but I'm learning every day! Here are things I can help with:\n\n🌾 Harvest timing\n💰 Market prices\n🛡️ Storage tips\n🌦️ Weather forecast\n🌱 Soil health\n💳 Government schemes\n🚛 Transport\n🐛 Pest control\n\nTry asking about any of these!";
  }

  // =============================================
  //  CHROME BUILT-IN AI (GEMINI NANO) ONLY
  // =============================================
  async function initChromeAI() {
    if (chromeAISession) return;

    console.log("🛠️ Starting Chrome AI Initialization...");

    try {
      if (typeof window.ai === 'undefined') {
        console.error("❌ window.ai is undefined. Built-in AI API is not exposed by this browser.");
        isUsingLocalAI = false;
        return;
      }

      if (!window.ai.languageModel) {
        console.error("❌ window.ai.languageModel is undefined. The language model API is missing.");
        isUsingLocalAI = false;
        return;
      }

      console.log("✅ window.ai API exists. Checking capabilities...");
      const capabilities = await window.ai.languageModel.capabilities();
      console.log("📊 AI Capabilities:", capabilities);

      if (capabilities.available === 'no') {
        console.error("❌ Chrome AI model is completely unavailable (capabilities.available === 'no').");
        isUsingLocalAI = false;
        return;
      }

      if (capabilities.available === 'readily') {
        console.log("🟢 Chrome AI is 'readily' available. Creating session...");
      } else if (capabilities.available === 'after-download') {
        console.log("🟡 Chrome AI requires a download ('after-download'). Creating session will trigger download...");
      }

      chromeAISession = await window.ai.languageModel.create({
        systemPrompt: "You are Sodhak AI, a helpful agricultural expert assistant for Indian farmers. Provide practical, accurate, and localized farming advice. Keep formatting clean with bullet points and bold text where helpful."
      });

      isUsingLocalAI = true;
      console.log("🚀 Sodhak AI Session Created Successfully!");

      // Update UI badge if exists
      const badge = document.getElementById('aiBadge');
      if (badge) {
        badge.innerText = "⚡ Local AI";
        badge.className = "ai-badge local";
      }
    } catch (error) {
      console.error("❌ Fatal Error initializing Chrome AI:", error);
      isUsingLocalAI = false;
    }
  }

  // Initialize Chrome AI when app loads
  initChromeAI();

  async function generateSodhakReply(userMessage) {
    // 1. Try Chrome Built-in AI
    if (isUsingLocalAI && chromeAISession) {
      try {
        const response = await chromeAISession.prompt(userMessage);
        return response;
      } catch (error) {
        console.error("Chrome AI Prompt Error:", error);
        return "❌ **Local AI Error:** Something went wrong while thinking. Please try asking again.";
      }
    }

    // 2. Fallback to predefined offline responses
    const badge = document.getElementById('aiBadge');
    if (badge) {
      badge.innerText = "☁️ Offline Mode";
      badge.className = "ai-badge cloud";
    }

    // Use the existing match logic for an offline experience
    return generateReply(userMessage);
  }

  function match(text, keywords) {
    return keywords.some(k => text.includes(k));
  }

  // =============================================
  //  SODHAK AI (SCREEN 4) LOGIC
  // =============================================
  const sodhakMessages = document.getElementById('sodhakMessages');
  const sodhakInput = document.getElementById('sodhakInput');
  const sodhakSendBtn = document.getElementById('sodhakSendBtn');
  const sodhakSuggestions = document.querySelector('.sodhak-suggestions');

  async function sendSodhakMessage() {
    const text = sodhakInput.value.trim();
    if (!text) return;
    addSodhakMessage('user', text);
    sodhakInput.value = '';

    // Show typing
    const typingId = 'sodhak-typing-' + Date.now();
    const typingHtml = `
      <div class="message bot animate-in" id="${typingId}">
        <div class="message-content">
          <div class="typing-indicator"><span></span><span></span><span></span></div>
        </div>
      </div>`;
    sodhakMessages.insertAdjacentHTML('beforeend', typingHtml);
    sodhakMessages.scrollTop = sodhakMessages.scrollHeight;

    // Fetch real AI reply
    const reply = await generateSodhakReply(text);

    document.getElementById(typingId)?.remove();
    addSodhakMessage('bot', reply);
  }

  function addSodhakMessage(side, text) {
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const formatted = side === 'bot'
      ? escapeHtml(text).replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>')
      : escapeHtml(text);

    const html = `
      <div class="message ${side} animate-in">
        <div class="message-content">${formatted}</div>
        <div class="message-time" style="font-size:0.7rem; opacity:0.6; margin-top:4px; text-align:${side === 'user' ? 'right' : 'left'}">${time}</div>
      </div>`;

    sodhakMessages.insertAdjacentHTML('beforeend', html);
    sodhakMessages.scrollTop = sodhakMessages.scrollHeight;
  }

  sodhakSendBtn?.addEventListener('click', sendSodhakMessage);
  sodhakInput?.addEventListener('keydown', e => { if (e.key === 'Enter') sendSodhakMessage(); });

  sodhakSuggestions?.addEventListener('click', e => {
    const btn = e.target.closest('.sodhak-suggest-btn');
    if (!btn) return;
    sodhakInput.value = btn.dataset.msg;
    sendSodhakMessage();
  });

  // ===== MARKET DETAIL =====
  function initMarketDetail(mandiName, cardEl) {
    const detailName = document.getElementById('mandiDetailName');
    const detailRank = document.getElementById('mandiDetailRank');
    if (!detailName || !detailRank) return;

    detailName.textContent = mandiName;

    // Extract rank from the card that was clicked
    const rankBadge = cardEl.querySelector('.mandi-rank-badge');
    if (rankBadge) {
      detailRank.textContent = rankBadge.textContent;
    }

    // Animate bars
    const chartBars = document.querySelectorAll('.chart-bar');
    chartBars.forEach((bar, i) => {
      const originalHeight = bar.style.height;
      bar.style.height = '0';
      setTimeout(() => {
        bar.style.height = originalHeight;
      }, 300 + (i * 100));
    });
  }

  // ===== PROTECTION DETAIL =====
  function initProtectDetail() {
    const points = document.querySelectorAll('.log-point');
    const path = document.querySelector('.log-line-svg path');

    if (path) {
      const length = path.getTotalLength();
      path.style.strokeDasharray = length;
      path.style.strokeDashoffset = length;
      path.getBoundingClientRect(); // trigger reflow
      path.style.transition = 'stroke-dashoffset 2s ease-in-out';
      path.style.strokeDashoffset = '0';
    }

    points.forEach((p, i) => {
      p.style.opacity = '0';
      p.style.transform = 'scale(0)';
      setTimeout(() => {
        p.style.opacity = '1';
        p.style.transform = 'scale(1)';
        p.style.transition = 'all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
      }, 500 + (i * 200));
    });
  }

});

// Register Service Worker for PWA
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js')
      .then(reg => console.log('Service Worker registered', reg))
      .catch(err => console.log('Service Worker registration failed', err));
  });
}
