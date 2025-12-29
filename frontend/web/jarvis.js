// JARVIS Hollywood HUD - Refactored to use modular architecture

class JarvisHUD {
  constructor() {
    this.isProcessing = false;
    this.waveformAnimationId = null;
    this.waveformPhase = 0;

    // Session persistence
    this.conversationId = localStorage.getItem('jarvis_conversation_id') || null;

    this.elements = {
      chatContainer: document.getElementById('chatContainer'),
      messageInput: document.getElementById('messageInput'),
      sendBtn: document.getElementById('sendBtn'),
      micBtn: document.getElementById('micBtn'),
      speakerBtn: document.getElementById('speakerBtn'),
      expandBtn: document.getElementById('expandBtn'),
      expandModal: document.getElementById('expandModal'),
      expandedInput: document.getElementById('expandedInput'),
      cancelExpand: document.getElementById('cancelExpand'),
      submitExpand: document.getElementById('submitExpand'),
      hudContainer: document.getElementById('hudContainer'),
      arcReactor: document.getElementById('arcReactor'),
      statusDot: document.getElementById('statusDot'),
      statusText: document.getElementById('statusText'),
      waveformContainer: document.getElementById('waveformContainer'),
      waveformCanvas: document.getElementById('waveformCanvas'),
      quickMenu: document.getElementById('quickMenu'),
      quickMenuTrigger: document.getElementById('quickMenuTrigger'),
      wakeWordBtn: document.getElementById('wakeWordBtn')
    };

    // Initialize speech manager
    this.speechManager = new SpeechManager({
      onResult: (transcript) => {
        this.elements.messageInput.value = transcript;
        this.sendMessage();
      },
      onWakeWord: (command, isAcknowledgement) => {
        if (isAcknowledgement) {
          this.showWakeAcknowledge();
        } else {
          this.elements.messageInput.value = command;
          setTimeout(() => this.sendMessage(), 100);
        }
        this.pulseReactor();
      },
      onSpeakStart: () => {
        this.elements.waveformContainer.classList.add('active');
        this.startWaveform();
      },
      onSpeakEnd: () => {
        this.stopWaveform();
      },
      onListeningStart: () => {
        this.elements.micBtn.classList.add('active');
        this.pulseReactor();
      },
      onListeningEnd: () => {
        this.elements.micBtn.classList.remove('active');
      }
    });

    this.init();
  }

  init() {
    this.setupEventListeners();
    this.setupWaveform();
    this.elements.messageInput.focus();
    this.elements.speakerBtn.classList.add('active');
    this.connectWebSocket();
  }

  setupEventListeners() {
    this.elements.sendBtn.addEventListener('click', () => this.sendMessage());
    this.elements.messageInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') this.sendMessage();
    });

    this.elements.micBtn.addEventListener('click', () => this.toggleVoiceInput());

    this.elements.speakerBtn.addEventListener('click', () => {
      if (this.speechManager.isSpeaking) {
        this.speechManager.stopSpeaking();
        return;
      }
      const enabled = !this.speechManager.speechEnabled;
      this.speechManager.toggleTTS(enabled);
      this.elements.speakerBtn.classList.toggle('active', enabled);
    });

    // Wake word toggle
    if (this.elements.wakeWordBtn) {
      this.elements.wakeWordBtn.addEventListener('click', () => this.toggleWakeWord());
    }

    this.elements.expandBtn.addEventListener('click', () => {
      this.elements.expandedInput.value = this.elements.messageInput.value;
      this.elements.expandModal.classList.add('visible');
      this.elements.expandedInput.focus();
    });

    this.elements.cancelExpand.addEventListener('click', () => {
      this.elements.expandModal.classList.remove('visible');
    });

    this.elements.submitExpand.addEventListener('click', () => {
      this.elements.messageInput.value = this.elements.expandedInput.value;
      this.elements.expandModal.classList.remove('visible');
      this.sendMessage();
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.elements.expandModal.classList.contains('visible')) {
        this.elements.expandModal.classList.remove('visible');
      }
      // Ctrl+J to toggle wake word
      if (e.key === 'j' && e.ctrlKey) {
        e.preventDefault();
        this.toggleWakeWord();
      }
    });

    this.elements.quickMenuTrigger.addEventListener('click', () => {
      this.elements.quickMenu.classList.toggle('open');
    });

    document.querySelectorAll('.quick-menu-item').forEach(item => {
      item.addEventListener('click', () => {
        const command = item.dataset.command;
        this.elements.quickMenu.classList.remove('open');

        if (command.includes('topology') || command.includes('network')) {
          this.showTopology();
        } else {
          this.elements.messageInput.value = command;
          this.sendMessage();
        }
      });
    });

    document.addEventListener('click', (e) => {
      if (!this.elements.quickMenu.contains(e.target)) {
        this.elements.quickMenu.classList.remove('open');
      }
    });
  }

  toggleVoiceInput() {
    this.speechManager.startListening();
  }

  toggleWakeWord() {
    const enabled = this.speechManager.toggleWakeWord();
    if (this.elements.wakeWordBtn) {
      this.elements.wakeWordBtn.classList.toggle('active', enabled);
    }
    this.elements.statusText.textContent = enabled ? 'LISTENING' : 'ONLINE';
    this.elements.hudContainer.classList.toggle('wake-word-mode', enabled);
  }

  showWakeAcknowledge() {
    // Visual feedback that JARVIS heard the wake word
    const ackDiv = document.createElement('div');
    ackDiv.className = 'wake-ack';
    ackDiv.textContent = 'Yes, sir?';
    document.body.appendChild(ackDiv);

    setTimeout(() => {
      ackDiv.classList.add('visible');
    }, 10);

    setTimeout(() => {
      ackDiv.classList.remove('visible');
      setTimeout(() => ackDiv.remove(), 300);
    }, 1500);
  }

  setupWaveform() {
    const canvas = this.elements.waveformCanvas;
    const ctx = canvas.getContext('2d');

    const resize = () => {
      canvas.width = canvas.offsetWidth * 2;
      canvas.height = canvas.offsetHeight * 2;
      ctx.scale(2, 2);
    };
    resize();
    window.addEventListener('resize', resize);

    this.waveformCtx = ctx;
    this.clearWaveform();
  }

  clearWaveform() {
    const ctx = this.waveformCtx;
    const canvas = this.elements.waveformCanvas;
    const width = canvas.offsetWidth;
    const height = canvas.offsetHeight;
    ctx.clearRect(0, 0, width, height);
  }

  pulseReactor() {
    this.elements.arcReactor.classList.add('active');
    setTimeout(() => {
      this.elements.arcReactor.classList.remove('active');
    }, 500);
  }

  addMessage(content, isUser = false, meta = {}) {
    const div = document.createElement('div');
    const agent = meta.agent || 'jarvis';

    if (isUser) {
      div.className = 'chat-line user';
      div.innerHTML = '<span class="chat-label">YOU</span><span class="chat-text">' + this.formatMessage(content) + '</span>';
    } else {
      div.className = 'chat-line ' + agent;
      div.innerHTML = '<span class="chat-label">' + agent.toUpperCase() + '</span><span class="chat-text">' + this.formatMessage(content) + '</span>';
    }

    this.elements.chatContainer.appendChild(div);
    this.elements.chatContainer.scrollTop = this.elements.chatContainer.scrollHeight;

    return div;
  }

  createStreamingMessage(agent = 'jarvis') {
    const div = document.createElement('div');
    div.className = 'chat-line ' + agent;
    div.innerHTML = '<span class="chat-label">' + agent.toUpperCase() + '</span><span class="chat-text streaming-text"></span>';
    this.elements.chatContainer.appendChild(div);
    return div.querySelector('.streaming-text');
  }

  formatMessage(text) {
    return text
      .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>');
  }

  showTyping() {
    const div = document.createElement('div');
    div.className = 'chat-line jarvis typing-line';
    div.innerHTML = '<span class="chat-label">JARVIS</span><span class="chat-text"><span class="typing-indicator"><span></span><span></span><span></span></span></span>';
    this.elements.chatContainer.appendChild(div);
    this.elements.chatContainer.scrollTop = this.elements.chatContainer.scrollHeight;
    return div;
  }

  speak(text) {
    this.speechManager.speak(text);
  }

  startWaveform() {
    if (this.waveformAnimationId) return;
    this.waveformPhase = 0;
    this.animateWaveform();
  }

  stopWaveform() {
    this.elements.waveformContainer.classList.remove('active');
    if (this.waveformAnimationId) {
      cancelAnimationFrame(this.waveformAnimationId);
      this.waveformAnimationId = null;
    }
    this.clearWaveform();
  }

  animateWaveform() {
    if (!this.speechManager.isSpeaking) {
      this.stopWaveform();
      return;
    }

    const ctx = this.waveformCtx;
    const canvas = this.elements.waveformCanvas;
    const width = canvas.offsetWidth;
    const height = canvas.offsetHeight;

    ctx.clearRect(0, 0, width, height);

    const bars = 32;
    const barWidth = (width / bars) - 2;
    const centerY = height / 2;

    ctx.fillStyle = 'rgba(0, 212, 255, 0.8)';

    for (let i = 0; i < bars; i++) {
      const x = i * (barWidth + 2);
      const wave1 = Math.sin((i / bars) * Math.PI * 2 + this.waveformPhase) * 0.4;
      const wave2 = Math.sin((i / bars) * Math.PI * 4 + this.waveformPhase * 1.5) * 0.3;
      const wave3 = Math.sin((i / bars) * Math.PI * 6 + this.waveformPhase * 0.7) * 0.2;
      const noise = (Math.random() - 0.5) * 0.1;
      const amplitude = Math.abs(wave1 + wave2 + wave3 + noise);
      const barHeight = Math.max(4, amplitude * height * 0.8);
      const y = centerY - barHeight / 2;
      const radius = Math.min(barWidth / 2, 3);
      ctx.beginPath();
      ctx.roundRect(x, y, barWidth, barHeight, radius);
      ctx.fill();
    }

    this.waveformPhase += 0.08;
    this.waveformAnimationId = requestAnimationFrame(() => this.animateWaveform());
  }

  async sendMessage() {
    const text = this.elements.messageInput.value.trim();
    if (!text || this.isProcessing) return;

    this.isProcessing = true;
    this.elements.sendBtn.disabled = true;
    this.elements.messageInput.value = '';

    // Pause wake word during processing (handled by SpeechManager internally)
    this.pulseReactor();
    this.addMessage(text, true);

    const streamingText = this.createStreamingMessage('jarvis');
    let fullResponse = '';

    try {
      const response = await fetch(JARVIS_CONFIG.API.CHAT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, conversation_id: this.conversationId })
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));

              if (data.type === 'ack') {
                streamingText.innerHTML = this.formatMessage(data.content);
                this.pulseReactor();
              } else if (data.type === 'content') {
                fullResponse += data.content;
                streamingText.innerHTML = this.formatMessage(fullResponse);
                this.elements.chatContainer.scrollTop = this.elements.chatContainer.scrollHeight;
              } else if (data.type === 'done') {
                if (data.conversation_id) {
                  this.conversationId = data.conversation_id;
                  localStorage.setItem('jarvis_conversation_id', data.conversation_id);
                }
                this.pulseReactor();
                if (fullResponse.trim()) {
                  this.speak(fullResponse);
                }
              } else if (data.type === 'error') {
                streamingText.innerHTML = this.formatMessage('Error: ' + data.content);
              }
            } catch (e) {
              // Ignore parse errors for incomplete JSON
            }
          }
        }
      }

    } catch (error) {
      streamingText.innerHTML = this.formatMessage('Connection error. Please try again.');
      console.error('Chat error:', error);
    }

    this.isProcessing = false;
    this.elements.sendBtn.disabled = false;
    this.elements.messageInput.focus();
  }

  showPanel(panelId) {
    const panel = document.getElementById(panelId);
    if (panel) {
      panel.classList.add('visible');
      if (panelId === 'metricsPanel') this.loadMetrics();
      else if (panelId === 'servicesPanel') this.loadServices();
      
    }
  }

  async loadMetrics() {
    try {
      const response = await fetch(JARVIS_CONFIG.API.METRICS);
      const data = await response.json();
      if (data.metrics && data.metrics.length > 0) {
        this.updateMetricsContent(data.metrics);
      } else {
        this.updateMetricsContent([{ name: 'No metrics available', value: '-', percent: 0 }]);
      }
    } catch (e) {
      console.error('Failed to load metrics:', e);
      this.updateMetricsContent([{ name: 'Error loading metrics', value: '-', percent: 0 }]);
    }
  }

  async loadServices() {
    try {
      const response = await fetch(JARVIS_CONFIG.API.SERVICES);
      const data = await response.json();
      if (data.services && data.services.length > 0) {
        this.updateServicesContent(data.services);
      } else {
        this.updateServicesContent([{ name: 'No services found', status: 'down' }]);
      }
    } catch (e) {
      console.error('Failed to load services:', e);
      this.updateServicesContent([{ name: 'Error loading services', status: 'down' }]);
    }
  }

  hidePanel(panelId) {
    const panel = document.getElementById(panelId);
    if (panel) {
      panel.classList.remove('visible');
    }
  }

  togglePanel(panelId) {
    const panel = document.getElementById(panelId);
    if (panel) {
      const isCurrentlyVisible = panel.classList.contains('visible');
      panel.classList.toggle('visible');

      if (!isCurrentlyVisible) {
        if (panelId === 'metricsPanel') this.loadMetrics();
        else if (panelId === 'servicesPanel') this.loadServices();
      
      }
    }
  }

  updateMetricsContent(data) {
    const content = document.getElementById('metricsPanelContent');
    if (!content) return;

    let html = '';
    if (data && data.length > 0) {
      data.forEach(metric => {
        const valueClass = metric.percent > 80 ? 'critical' : metric.percent > 60 ? 'warning' : 'good';
        html += '<div class="metric-item">';
        html += '<div style="display:flex;justify-content:space-between">';
        html += '<span class="metric-label">' + metric.name + '</span>';
        html += '<span class="metric-value ' + valueClass + '">' + metric.value + '</span>';
        html += '</div>';
        if (metric.percent !== undefined) {
          html += '<div class="metric-bar"><div class="metric-bar-fill ' + valueClass + '" style="width:' + metric.percent + '%"></div></div>';
        }
        html += '</div>';
      });
    } else {
      html = '<div class="metric-item"><span class="metric-label">No metrics available</span></div>';
    }

    content.innerHTML = html;
  }

  updateServicesContent(services) {
    const content = document.getElementById('servicesPanelContent');
    if (!content) return;

    let html = '';
    if (services && services.length > 0) {
      services.forEach(svc => {
        const statusClass = svc.status === 'up' ? 'up' : 'down';
        html += '<div class="service-item">';
        html += '<div class="service-status ' + statusClass + '"></div>';
        html += '<span class="service-name">' + svc.name + '</span>';
        html += '</div>';
      });
    } else {
      html = '<div class="service-item"><span class="metric-label">No services data</span></div>';
    }

    content.innerHTML = html;
  }

  showMetricsPanel(data) {
    this.updateMetricsContent(data);
    const panel = document.getElementById('metricsPanel');
    if (panel) panel.classList.add('visible');
  }

  showServicesPanel(services) {
    this.updateServicesContent(services);
    const panel = document.getElementById('servicesPanel');
    if (panel) panel.classList.add('visible');
  }

  showTopology() {
    document.getElementById('overlay').classList.add('visible');
    document.getElementById('topologyContainer').classList.add('visible');

    if (!this.topology) {
      this.topology = new NetworkTopology('topologyCanvas');
    }
  }

  closeTopology() {
    document.getElementById('overlay').classList.remove('visible');
    document.getElementById('topologyContainer').classList.remove('visible');
  }

  destroy() {
    if (this.speechManager) {
      this.speechManager.cleanup();
    }
    // Stop intervals
    if (this.metricsInterval) clearInterval(this.metricsInterval);
    if (this.servicesInterval) clearInterval(this.servicesInterval);
    if (this.alertsInterval) clearInterval(this.alertsInterval);
    if (this.waveformAnimationId) {
      cancelAnimationFrame(this.waveformAnimationId);
    }
  }


  // ============ WEBSOCKET METHODS ============

  connectWebSocket() {
    try {
      this.ws = new WebSocket(JARVIS_CONFIG.WS_URL);
      
      this.ws.onopen = () => {
        console.log('WebSocket connected');
      };
      
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'protect_event') {
            this.handleProtectEvent(data);
          }
        } catch (e) {
          console.error('WebSocket message parse error:', e);
        }
      };
      
      this.ws.onclose = () => {
        console.log('WebSocket disconnected, reconnecting in 5s...');
        setTimeout(() => this.connectWebSocket(), JARVIS_CONFIG.TIMEOUTS.RECONNECT_DELAY);
      };
      
      this.ws.onerror = (err) => {
        console.error('WebSocket error:', err);
      };
    } catch (e) {
      console.error('Failed to connect WebSocket:', e);
      setTimeout(() => this.connectWebSocket(), JARVIS_CONFIG.TIMEOUTS.RECONNECT_DELAY);
    }
  }

  handleProtectEvent(data) {
    console.log('Protect event received:', data);
    
    const eventType = data.type_detail || data.event_type || data.trigger || '';
    const cameraName = data.camera || data.camera_name || 'Front Door';
    
    // Doorbell ring
    if (eventType === 'ring' || eventType.includes('ring')) {
      this.playDoorbellSound();
      this.showDoorbellAlert(cameraName);
      if (this.speechManager) {
        this.speechManager.speak('Someone is at the ' + cameraName.toLowerCase());
      }
      if (window.showCameras) window.showCameras();
    }
    
    // Person detected
    if (eventType === 'person' || (data.smartDetectTypes && data.smartDetectTypes.includes('person'))) {
      this.showDoorbellAlert(cameraName, 'Person detected');
    }
    
    // Face recognized
    if (eventType === 'face_of_interest' || eventType.includes('face')) {
      const faceName = data.face_name || data.metadata?.face_name || 'someone you know';
      if (this.speechManager) {
        this.speechManager.speak(faceName + ' is at the door');
      }
      if (window.showCameras) window.showCameras();
    }
  }

  playDoorbellSound() {
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioCtx.createOscillator();
      const gainNode = audioCtx.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioCtx.destination);
      
      // Doorbell ding-dong pattern
      oscillator.frequency.setValueAtTime(880, audioCtx.currentTime);
      oscillator.frequency.setValueAtTime(659, audioCtx.currentTime + 0.15);
      
      gainNode.gain.setValueAtTime(0.3, audioCtx.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.5);
      
      oscillator.start(audioCtx.currentTime);
      oscillator.stop(audioCtx.currentTime + 0.5);
    } catch (e) {
      console.log('Web Audio not available:', e);
    }
  }

  showDoorbellAlert(cameraName, message = 'Doorbell Ring') {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'doorbell-alert';
    alertDiv.innerHTML = `
      <div class="doorbell-alert-content">
        <span class="doorbell-icon">🔔</span>
        <div class="doorbell-text">
          <strong>${message}</strong>
          <span>${cameraName}</span>
        </div>
      </div>
    `;
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
      alertDiv.classList.add('fade-out');
      setTimeout(() => alertDiv.remove(), 500);
    }, JARVIS_CONFIG.TIMEOUTS.ALERT_DISPLAY);
    
    // Browser notification
    if (Notification.permission === 'granted') {
      new Notification(message, { body: cameraName, icon: '/images/jarvis-icon.png' });
    } else if (Notification.permission !== 'denied') {
      Notification.requestPermission();
    }
  }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  window.jarvis = new JarvisHUD();

  speechSynthesis.onvoiceschanged = () => speechSynthesis.getVoices();

  document.addEventListener('keydown', (e) => {
    if (e.key === 'm' && e.ctrlKey) {
      e.preventDefault();
      window.jarvis.togglePanel('metricsPanel');
    }
    if (e.key === 's' && e.ctrlKey) {
      e.preventDefault();
      window.jarvis.togglePanel('servicesPanel');
    }
  });
});

// Alert polling system
class AlertSystem {
  constructor(jarvis) {
    this.jarvis = jarvis;
    this.lastAlerts = [];
    this.notifiedAlerts = new Set();
    this.pollInterval = null;
    this.enabled = true;
  }

  start() {
    this.checkAlerts();
    this.pollInterval = setInterval(() => this.checkAlerts(), JARVIS_CONFIG.TIMEOUTS.ALERT_POLL);
  }

  stop() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }

  async checkAlerts() {
    if (!this.enabled) return;

    try {
      const response = await fetch(JARVIS_CONFIG.API.ALERTS);
      const data = await response.json();

      if (data.alerts && data.alerts.length > 0) {
        // Find new alerts
        const newAlerts = data.alerts.filter(alert => {
          const alertKey = alert.type + ':' + alert.message;
          return !this.notifiedAlerts.has(alertKey);
        });

        // Notify for new critical/warning alerts
        newAlerts.forEach(alert => {
          const alertKey = alert.type + ':' + alert.message;
          this.notifiedAlerts.add(alertKey);

          if (alert.severity === 'critical' || alert.severity === 'warning') {
            this.showAlert(alert);
          }
        });

        // Update alert indicator
        this.updateIndicator(data.alerts);
      } else {
        // Clear indicator if no alerts
        this.updateIndicator([]);
        this.notifiedAlerts.clear();
      }

      this.lastAlerts = data.alerts || [];
    } catch (e) {
      console.error('Alert check failed:', e);
    }
  }

  showAlert(alert) {
    // Visual notification
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert-notification ' + alert.severity;
    alertDiv.innerHTML = '<strong>' + alert.type.replace(/_/g, ' ').toUpperCase() + '</strong><br>' + alert.message;
    document.body.appendChild(alertDiv);

    setTimeout(() => alertDiv.classList.add('visible'), 10);

    // Auto-dismiss after configured time
    setTimeout(() => {
      alertDiv.classList.remove('visible');
      setTimeout(() => alertDiv.remove(), 300);
    }, JARVIS_CONFIG.TIMEOUTS.ALERT_DISPLAY);

    // Play alert sound for critical
    if (alert.severity === 'critical') {
      this.playAlertSound();
    }

    // Browser notification if permitted
    if (Notification.permission === 'granted') {
      new Notification('JARVIS Alert', {
        body: alert.message,
        icon: '/favicon.ico',
        tag: alert.type
      });
    }

    // Pulse the reactor
    this.jarvis.pulseReactor();
  }

  playAlertSound() {
    // Simple beep using Web Audio API
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioCtx.createOscillator();
      const gainNode = audioCtx.createGain();
      oscillator.connect(gainNode);
      gainNode.connect(audioCtx.destination);
      oscillator.frequency.value = 800;
      oscillator.type = 'sine';
      gainNode.gain.setValueAtTime(0.3, audioCtx.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.5);
      oscillator.start(audioCtx.currentTime);
      oscillator.stop(audioCtx.currentTime + 0.5);
    } catch (e) {}
  }

  updateIndicator(alerts) {
    const critical = alerts.filter(a => a.severity === 'critical').length;
    const warning = alerts.filter(a => a.severity === 'warning').length;

    let indicator = document.getElementById('alertIndicator');
    if (!indicator) {
      indicator = document.createElement('div');
      indicator.id = 'alertIndicator';
      indicator.className = 'alert-indicator';
      indicator.onclick = () => this.showAlertSummary();
      document.querySelector('.hud-header').appendChild(indicator);
    }

    if (critical > 0) {
      indicator.className = 'alert-indicator critical';
      indicator.textContent = critical;
      indicator.title = critical + ' critical alert(s)';
    } else if (warning > 0) {
      indicator.className = 'alert-indicator warning';
      indicator.textContent = warning;
      indicator.title = warning + ' warning(s)';
    } else {
      indicator.className = 'alert-indicator';
      indicator.textContent = '';
      indicator.title = 'No alerts';
    }
  }

  showAlertSummary() {
    if (this.lastAlerts.length === 0) return;

    let summary = 'Current Alerts:\n\n';
    this.lastAlerts.forEach(a => {
      summary += '• [' + a.severity.toUpperCase() + '] ' + a.message + '\n';
    });
    alert(summary);
  }
}

// Initialize alert system after JARVIS
document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => {
    if (window.jarvis) {
      window.jarvis.alertSystem = new AlertSystem(window.jarvis);
      window.jarvis.alertSystem.start();

      // Request notification permission
      if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
      }
    }
  }, 1000);
});

// Camera functionality
window.showCameras = function() {
  const modal = document.getElementById('cameraModal');
  if (modal) {
    modal.classList.add('visible');
    loadCameras();
  }
};

window.closeCameras = function() {
  const modal = document.getElementById('cameraModal');
  if (modal) modal.classList.remove('visible');

  // Stop all camera streams
  const videos = document.querySelectorAll('.camera-feed video');
  videos.forEach(video => {
    if (video.srcObject) {
      video.srcObject.getTracks().forEach(track => track.stop());
      video.srcObject = null;
    }
  });
};

window.closeCameraFullscreen = function() {
  const fullscreen = document.getElementById('cameraFullscreen');
  if (fullscreen) fullscreen.classList.remove('visible');

  const video = document.getElementById('cameraFullscreenVideo');
  const img = document.getElementById('cameraFullscreenImg');

  if (video && video.srcObject) {
    video.srcObject.getTracks().forEach(track => track.stop());
    video.srcObject = null;
  }

  if (img) img.src = '';
};

async function loadCameras() {
  const grid = document.getElementById('cameraGrid');
  if (!grid) return;

  grid.innerHTML = '<div class="camera-loading">Loading cameras...</div>';

  try {
    const response = await fetch(JARVIS_CONFIG.API.CAMERAS);
    const data = await response.json();

    if (!data.cameras || data.cameras.length === 0) {
      grid.innerHTML = '<div class="camera-loading">No cameras available</div>';
      return;
    }

    grid.innerHTML = '';

    data.cameras.forEach(camera => {
      const cameraDiv = document.createElement('div');
      cameraDiv.className = 'camera-feed';
      cameraDiv.innerHTML = `
        <div class="camera-header">
          <span class="camera-name">${camera.name}</span>
          <span class="camera-status ${camera.status}">${camera.status === 'online' ? '●' : '○'}</span>
        </div>
        <div class="camera-video-container">
          ${camera.stream_url ? `<img src="${camera.stream_url}" alt="${camera.name}">` : '<div class="camera-placeholder">No stream</div>'}
        </div>
      `;

      cameraDiv.addEventListener('click', () => {
        if (camera.stream_url) {
          showCameraFullscreen(camera);
        }
      });

      grid.appendChild(cameraDiv);
    });

  } catch (e) {
    console.error('Failed to load cameras:', e);
    grid.innerHTML = '<div class="camera-loading">Error loading cameras</div>';
  }
}

function showCameraFullscreen(camera) {
  const fullscreen = document.getElementById('cameraFullscreen');
  const title = document.getElementById('cameraFullscreenTitle');
  const img = document.getElementById('cameraFullscreenImg');

  if (fullscreen && title && img) {
    title.textContent = camera.name;
    img.src = camera.stream_url;
    img.style.display = 'block';
    fullscreen.classList.add('visible');
  }
}

// Make camera functions accessible to jarvis instance
if (window.jarvis) {
  window.jarvis.showCameras = window.showCameras;
  window.jarvis.closeCameras = window.closeCameras;
  window.jarvis.closeCameraFullscreen = window.closeCameraFullscreen;
}
