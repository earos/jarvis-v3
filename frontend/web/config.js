// JARVIS Frontend Configuration
const JARVIS_CONFIG = {
  // API Endpoints
  API: {
    CHAT: "/api/chat/v2",
    TTS: "/api/tts",
    TTS_SENTENCE: "/api/tts/sentence",  // Optimized endpoint for streaming
    TTS_STREAM: "/api/tts/stream",      // Full streaming endpoint
    TTS_VOICE: "/api/tts/voice",
    METRICS: "/api/metrics",
    SERVICES: "/api/services",
    ALERTS: "/api/alerts",
    TOPOLOGY: "/api/topology",
    CAMERAS: "/api/cameras",
    COSTS: "/api/costs",
    SETTINGS: "/api/settings",
    HISTORY: "/api/history",
    HEALTH: "/api/health",
    WEBHOOK_TEST: "/api/webhook/protect/test"
  },
  
  // Wake Word Detection
  WAKE_WORDS: ["jarvis", "hey jarvis", "ok jarvis", "hello jarvis"],
  
  // Timing (ms)
  TIMEOUTS: {
    ALERT_DISPLAY: 8000,
    ALERT_POLL: 30000,
    METRICS_POLL: 30000,
    SERVICES_POLL: 30000,
    RECONNECT_DELAY: 5000
  },
  
  // WebSocket
  WS_URL: `ws://${window.location.host}/ws`,
  
  // Audio
  DOORBELL_SOUND: "/sounds/doorbell.mp3"
};

// Make globally available
window.JARVIS_CONFIG = JARVIS_CONFIG;
