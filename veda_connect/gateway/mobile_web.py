# veda_connect/gateway/mobile_web.py
"""
Mobile Web Interface for Veda AI.
Provides a zero-install, responsive web client accessible on any smartphone browser
via local network QR code and 6-digit PIN verification.
"""

MOBILE_WEB_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <meta name="theme-color" content="#0a0c10">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <title>Veda AI — Mobile Gateway</title>
  <style>
    :root {
      --bg: #07090e;
      --card-bg: rgba(18, 22, 32, 0.85);
      --card-border: rgba(255, 179, 0, 0.22);
      --pri: #ffb300;
      --pri-glow: rgba(255, 179, 0, 0.35);
      --pri-light: #ffe082;
      --text: #f0f3f8;
      --text-muted: #8b9bb4;
      --danger: #ff5252;
      --success: #00e676;
      --radius: 18px;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
      background-image: 
        radial-gradient(circle at 50% 0%, rgba(255, 179, 0, 0.12) 0%, transparent 60%),
        radial-gradient(circle at 10% 90%, rgba(0, 230, 255, 0.05) 0%, transparent 50%);
    }
    
    /* Header */
    header {
      padding: 14px 18px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
      backdrop-filter: blur(16px);
      position: sticky;
      top: 0;
      z-index: 50;
      background: rgba(7, 9, 14, 0.85);
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .orb-icon {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: radial-gradient(circle at 35% 35%, #ffe082, #ff9100, #b26a00);
      box-shadow: 0 0 14px var(--pri-glow);
      position: relative;
    }
    .brand-text h1 {
      font-size: 17px;
      font-weight: 700;
      letter-spacing: 0.5px;
    }
    .brand-text span {
      font-size: 11px;
      color: var(--pri);
      text-transform: uppercase;
      letter-spacing: 1px;
    }
    .status-badge {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      font-weight: 600;
      padding: 5px 12px;
      border-radius: 20px;
      background: rgba(0, 230, 118, 0.12);
      border: 1px solid rgba(0, 230, 118, 0.3);
      color: var(--success);
    }
    .status-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--success);
      box-shadow: 0 0 8px var(--success);
      animation: pulse 1.8s infinite;
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(0.85); }
    }

    /* Screen Views */
    .view { display: none; flex: 1; flex-direction: column; width: 100%; max-width: 540px; margin: 0 auto; }
    .view.active { display: flex; }

    /* PIN Verification Screen */
    #view-pin {
      justify-content: center;
      align-items: center;
      padding: 28px 20px;
      text-align: center;
    }
    .pin-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 24px;
      padding: 32px 24px;
      width: 100%;
      box-shadow: 0 12px 40px rgba(0,0,0,0.5);
      backdrop-filter: blur(20px);
    }
    .pin-card .hero-orb {
      width: 72px;
      height: 72px;
      margin: 0 auto 18px;
      border-radius: 50%;
      background: radial-gradient(circle at 35% 35%, #fff176, #ffb300, #ff6f00);
      box-shadow: 0 0 28px var(--pri-glow);
      animation: float 3s ease-in-out infinite;
    }
    @keyframes float {
      0%, 100% { transform: translateY(0); }
      50% { transform: translateY(-6px); }
    }
    .pin-card h2 {
      font-size: 20px;
      font-weight: 700;
      margin-bottom: 6px;
    }
    .pin-card p {
      font-size: 13px;
      color: var(--text-muted);
      margin-bottom: 24px;
      line-height: 1.4;
    }
    .pin-inputs {
      display: flex;
      justify-content: center;
      gap: 10px;
      margin-bottom: 24px;
    }
    .pin-input {
      width: 44px;
      height: 52px;
      border-radius: 12px;
      border: 1px solid rgba(255, 179, 0, 0.3);
      background: rgba(255, 255, 255, 0.04);
      color: var(--pri-light);
      font-size: 24px;
      font-weight: 700;
      text-align: center;
      outline: none;
      transition: all 0.2s;
    }
    .pin-input:focus {
      border-color: var(--pri);
      box-shadow: 0 0 12px var(--pri-glow);
      background: rgba(255, 179, 0, 0.08);
    }
    .btn-submit {
      width: 100%;
      padding: 14px;
      border-radius: 14px;
      background: linear-gradient(135deg, #ffb300, #ff8f00);
      color: #050505;
      font-size: 15px;
      font-weight: 700;
      border: none;
      cursor: pointer;
      box-shadow: 0 4px 16px var(--pri-glow);
      transition: transform 0.15s, opacity 0.15s;
    }
    .btn-submit:active { transform: scale(0.98); }
    .pin-error {
      color: var(--danger);
      font-size: 12px;
      font-weight: 600;
      margin-top: 14px;
      min-height: 18px;
    }

    /* Main Assistant Chat Screen */
    #view-chat {
      display: flex;
      flex-direction: column;
      height: calc(100vh - 61px);
    }
    .quick-actions {
      display: flex;
      gap: 8px;
      padding: 12px 16px;
      overflow-x: auto;
      scrollbar-width: none;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
      background: rgba(10, 12, 18, 0.5);
    }
    .quick-actions::-webkit-scrollbar { display: none; }
    .chip {
      white-space: nowrap;
      padding: 7px 13px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 600;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: var(--text);
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s;
    }
    .chip:active { background: rgba(255, 179, 0, 0.2); border-color: var(--pri); }
    
    .chat-feed {
      flex: 1;
      padding: 16px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .msg {
      max-width: 84%;
      padding: 12px 16px;
      border-radius: 18px;
      font-size: 14px;
      line-height: 1.45;
      word-break: break-word;
      animation: fadeIn 0.2s ease-out;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(6px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .msg.user {
      align-self: flex-end;
      background: linear-gradient(135deg, rgba(255, 179, 0, 0.25), rgba(255, 143, 0, 0.2));
      border: 1px solid rgba(255, 179, 0, 0.4);
      color: #fff;
      border-bottom-right-radius: 4px;
    }
    .msg.assistant {
      align-self: flex-start;
      background: var(--card-bg);
      border: 1px solid rgba(255, 255, 255, 0.08);
      color: var(--text);
      border-bottom-left-radius: 4px;
    }
    .msg.sys {
      align-self: center;
      font-size: 11px;
      color: var(--text-muted);
      background: rgba(255, 255, 255, 0.03);
      border-radius: 12px;
      padding: 4px 10px;
    }

    /* Input Dock */
    .input-dock {
      padding: 10px 14px 18px;
      background: rgba(10, 12, 18, 0.95);
      border-top: 1px solid rgba(255, 255, 255, 0.06);
      backdrop-filter: blur(16px);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .mic-btn {
      width: 44px;
      height: 44px;
      border-radius: 50%;
      border: 1px solid rgba(255, 179, 0, 0.3);
      background: rgba(255, 179, 0, 0.1);
      color: var(--pri);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      font-size: 18px;
      flex-shrink: 0;
      transition: all 0.2s;
    }
    .mic-btn.listening {
      background: var(--pri);
      color: #000;
      box-shadow: 0 0 16px var(--pri);
      animation: pulse 1.2s infinite;
    }
    .chat-input {
      flex: 1;
      height: 44px;
      border-radius: 22px;
      border: 1px solid rgba(255, 255, 255, 0.12);
      background: rgba(255, 255, 255, 0.04);
      padding: 0 16px;
      font-size: 14px;
      color: #fff;
      outline: none;
    }
    .chat-input:focus { border-color: var(--pri); }
    .send-btn {
      width: 44px;
      height: 44px;
      border-radius: 50%;
      border: none;
      background: var(--pri);
      color: #050505;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 16px;
      font-weight: bold;
      cursor: pointer;
      flex-shrink: 0;
      transition: transform 0.15s;
    }
    .send-btn:active { transform: scale(0.92); }
  </style>
</head>
<body>

  <header>
    <div class="brand">
      <div class="orb-icon"></div>
      <div class="brand-text">
        <h1>Veda AI</h1>
        <span>Mobile Gateway</span>
      </div>
    </div>
    <div class="status-badge" id="status-badge">
      <div class="status-dot"></div>
      <span id="status-text">DISCONNECTED</span>
    </div>
  </header>

  <!-- View 1: PIN Verification -->
  <div class="view active" id="view-pin">
    <div class="pin-card">
      <div class="hero-orb"></div>
      <h2>Connect to Veda AI</h2>
      <p>Enter the 6-digit PIN shown on your PC screen to unlock control.</p>
      
      <div class="pin-inputs" id="pin-inputs">
        <input type="text" inputmode="numeric" maxlength="1" class="pin-input" autofocus>
        <input type="text" inputmode="numeric" maxlength="1" class="pin-input">
        <input type="text" inputmode="numeric" maxlength="1" class="pin-input">
        <input type="text" inputmode="numeric" maxlength="1" class="pin-input">
        <input type="text" inputmode="numeric" maxlength="1" class="pin-input">
        <input type="text" inputmode="numeric" maxlength="1" class="pin-input">
      </div>

      <button class="btn-submit" id="btn-verify">Unlock Veda AI</button>
      <div class="pin-error" id="pin-error"></div>
    </div>
  </div>

  <!-- View 2: Mobile Assistant Chat -->
  <div class="view" id="view-chat">
    <div class="quick-actions">
      <div class="chip" onclick="quickCommand('Play music on Spotify')">🎵 Play Music</div>
      <div class="chip" onclick="quickCommand('Toggle music play/pause')">⏯️ Play / Pause</div>
      <div class="chip" onclick="quickCommand('Skip to next song')">⏭️ Next Song</div>
      <div class="chip" onclick="quickCommand('Increase volume')">🔊 Vol +</div>
      <div class="chip" onclick="quickCommand('Decrease volume')">🔉 Vol -</div>
      <div class="chip" onclick="quickCommand('What is the battery and system status?')">🖥️ Status</div>
      <div class="chip" onclick="quickCommand('Give me my daily briefing')">☀️ Briefing</div>
    </div>

    <div class="chat-feed" id="chat-feed">
      <div class="msg sys">Connected to Veda Desktop Assistant</div>
      <div class="msg assistant">Hello Rohan! I am Veda AI. You can speak or type any command from your phone to control your PC. What would you like me to do?</div>
    </div>

    <div class="input-dock">
      <button class="mic-btn" id="btn-mic" title="Voice Dictation">🎙️</button>
      <input type="text" class="chat-input" id="chat-input" placeholder="Ask Veda or type command..." autocomplete="off">
      <button class="send-btn" id="btn-send">➤</button>
    </div>
  </div>

  <script>
    let authToken = localStorage.getItem('veda_mobile_token') || '';
    let isListening = false;
    let recognition = null;

    const pinInputs = document.querySelectorAll('.pin-input');
    const pinError = document.getElementById('pin-error');
    const viewPin = document.getElementById('view-pin');
    const viewChat = document.getElementById('view-chat');
    const statusText = document.getElementById('status-text');
    const chatFeed = document.getElementById('chat-feed');
    const chatInput = document.getElementById('chat-input');
    const btnSend = document.getElementById('btn-send');
    const btnMic = document.getElementById('btn-mic');

    // Auto-advance PIN inputs
    pinInputs.forEach((input, index) => {
      input.addEventListener('input', (e) => {
        if (e.target.value.length === 1 && index < pinInputs.length - 1) {
          pinInputs[index + 1].focus();
        }
        checkFullPin();
      });
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Backspace' && !e.target.value && index > 0) {
          pinInputs[index - 1].focus();
        }
      });
      input.addEventListener('paste', (e) => {
        e.preventDefault();
        const text = (e.clipboardData || window.clipboardData).getData('text').trim();
        if (/^\\d{6}$/.test(text)) {
          text.split('').forEach((ch, i) => { if (pinInputs[i]) pinInputs[i].value = ch; });
          verifyPin(text);
        }
      });
    });

    function getPinString() {
      return Array.from(pinInputs).map(i => i.value).join('');
    }

    function checkFullPin() {
      const pin = getPinString();
      if (pin.length === 6) verifyPin(pin);
    }

    document.getElementById('btn-verify').addEventListener('click', () => {
      const pin = getPinString();
      if (pin.length === 6) verifyPin(pin);
      else pinError.textContent = 'Please enter all 6 digits.';
    });

    async function verifyPin(pin) {
      pinError.textContent = '';
      try {
        const res = await fetch('/api/verify_pin', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ pin: pin })
        });
        const data = await res.json();
        if (data.ok) {
          authToken = data.token || 'verified';
          localStorage.setItem('veda_mobile_token', authToken);
          showChatView();
        } else {
          pinError.textContent = data.error || 'Incorrect or expired PIN. Check desktop screen.';
        }
      } catch (err) {
        pinError.textContent = 'Connection error. Ensure phone is on same Wi-Fi.';
      }
    }

    function showChatView() {
      viewPin.classList.remove('active');
      viewChat.classList.add('active');
      statusText.textContent = 'CONNECTED';
      chatInput.focus();
    }

    // Quick command sender
    window.quickCommand = function(text) {
      sendCommand(text);
    };

    btnSend.addEventListener('click', () => {
      const text = chatInput.value.trim();
      if (text) {
        sendCommand(text);
        chatInput.value = '';
      }
    });

    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const text = chatInput.value.trim();
        if (text) {
          sendCommand(text);
          chatInput.value = '';
        }
      }
    });

    function addMessage(text, role) {
      const div = document.createElement('div');
      div.className = 'msg ' + role;
      div.textContent = text;
      chatFeed.appendChild(div);
      chatFeed.scrollTop = chatFeed.scrollHeight;
    }

    async function sendCommand(text) {
      addMessage(text, 'user');
      const typing = document.createElement('div');
      typing.className = 'msg assistant';
      typing.textContent = 'Executing...';
      chatFeed.appendChild(typing);
      chatFeed.scrollTop = chatFeed.scrollHeight;

      try {
        const res = await fetch('/api/command', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ command: text, token: authToken })
        });
        const data = await res.json();
        typing.textContent = data.reply || (data.ok ? 'Action completed on PC.' : 'Error: ' + data.error);
      } catch (err) {
        typing.textContent = 'Error sending command to PC.';
      }
      chatFeed.scrollTop = chatFeed.scrollHeight;
    }

    // Voice Dictation (Web Speech API)
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        isListening = true;
        btnMic.classList.add('listening');
        btnMic.textContent = '🔴';
      };

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        if (transcript.trim()) {
          sendCommand(transcript.trim());
        }
      };

      recognition.onerror = (e) => {
        console.warn('Speech error:', e);
        isListening = false;
        btnMic.classList.remove('listening');
        btnMic.textContent = '🎙️';
      };

      recognition.onend = () => {
        isListening = false;
        btnMic.classList.remove('listening');
        btnMic.textContent = '🎙️';
      };

      btnMic.addEventListener('click', () => {
        if (isListening) {
          recognition.stop();
        } else {
          recognition.start();
        }
      });
    } else {
      btnMic.style.display = 'none';
    }

    // Check existing auth
    if (authToken) {
      fetch('/api/check_auth?token=' + encodeURIComponent(authToken))
        .then(r => r.json())
        .then(d => { if (d.ok) showChatView(); })
        .catch(() => {});
    }
  </script>
</body>
</html>
"""
