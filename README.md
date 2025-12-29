# JARVIS v3 - AI Homelab Assistant

A Python/FastAPI-powered AI assistant for homelab management with real-time alerts, voice interaction, and comprehensive infrastructure monitoring.

## Quick Start

```bash
# Access JARVIS
http://192.168.10.100:3939/

# API Health Check
curl http://192.168.10.100:3939/api/health

# Service Management
systemctl status jarvis-v3
systemctl restart jarvis-v3
journalctl -u jarvis-v3 -f
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    JARVIS v3 Stack                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Menu Bar    │  │  Web UI     │  │  WebSocket  │         │
│  │ (Electron)  │  │  (Browser)  │  │  (Alerts)   │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         └────────────────┼────────────────┘                 │
│                ┌─────────▼─────────┐                        │
│                │   FastAPI Server  │                        │
│                │    (Port 3939)    │                        │
│                └─────────┬─────────┘                        │
│         ┌────────────────┼────────────────┐                 │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐         │
│  │ Orchestrator│  │  Event Bus  │  │    Tools    │         │
│  │  (Claude)   │  │  (Pub/Sub)  │  │  Registry   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

## Features

| Feature | Description |
|---------|-------------|
| AI Chat | Claude-powered with streaming responses |
| 15 Tools | Homelab monitoring and management |
| Voice I/O | ElevenLabs TTS (30-90x optimized) |
| Menu Bar | macOS app with Cmd+Shift+J shortcut |
| WebSocket | Real-time doorbell/motion alerts |
| Metrics | Prometheus integration |
| Services | Uptime Kuma monitoring |
| Cameras | UniFi Protect integration |

## Tools (15 Total)

### Homelab (12)
| Tool | Description |
|------|-------------|
| `proxmox_query` | Query Proxmox cluster status |
| `proxmox_manage` | Start/stop VMs and containers |
| `prometheus` | Query metrics via PromQL |
| `uptime_kuma` | Service health monitoring |
| `unifi_network` | Network status and clients |
| `unifi_protect_query` | Camera and NVR status |
| `unifi_protect_automation` | Camera automations |
| `unifi_protect_webhook` | Webhook configuration |
| `query_home_assistant` | HA sensor states |
| `manage_home_assistant` | Control HA devices |
| `query_portainer` | Docker container status |
| `manage_portainer` | Start/stop containers |

### Utilities (3)
| Tool | Description |
|------|-------------|
| `get_time` | Current date and time |
| `get_weather` | Weather forecast |
| `research` | Web search via Tavily |

## Clients

### Web UI
- URL: http://192.168.10.100:3939/
- Features: Chat, TTS, services panel

### Menu Bar App (macOS)
- Location: `/opt/jarvis-v3/menubar/` (server) or `~/jarvis-menubar/` (local)
- Shortcut: `Cmd+Shift+J`
- Features: Quick chat, doorbell alerts, native notifications

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/chat/v2` | POST | Streaming chat (SSE) |
| `/api/v1/tools` | GET | List all tools |
| `/api/services` | GET | Uptime Kuma status |
| `/api/settings` | GET/POST | User settings |
| `/api/costs` | GET | Cost tracking |
| `/api/tts` | POST | Text-to-speech |
| `/ws` | WebSocket | Real-time events |
| `/api/webhook/protect` | POST | UniFi Protect webhooks |

## Configuration

Environment: `/opt/jarvis-v3/backend/.env`

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Homelab Services
PROMETHEUS_URL=http://192.168.10.104:9090
UPTIME_KUMA_URL=http://192.168.10.104:3001
PROXMOX_TOKEN_NAME=...
PROXMOX_TOKEN_VALUE=...
UNIFI_HOST=192.168.10.1
PROTECT_HOST=192.168.20.250
HOME_ASSISTANT_TOKEN=...
PORTAINER_API_KEY=...

# Optional
ELEVENLABS_API_KEY=...
TAVILY_API_KEY=...
```

## Directory Structure

```
/opt/jarvis-v3/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry
│   │   ├── config/settings.py   # Configuration
│   │   ├── api/v1/              # REST endpoints
│   │   ├── api/websocket/       # WebSocket
│   │   ├── core/orchestrator/   # Claude agent
│   │   └── tools/               # 15 tools
│   ├── data/jarvis.db           # SQLite
│   └── .env                     # Config
├── frontend/web/                # Web UI static files
├── menubar/                     # Electron app
└── README.md
```

## Service Management

```bash
systemctl status jarvis-v3    # Status
systemctl restart jarvis-v3   # Restart
journalctl -u jarvis-v3 -f    # Logs
```

## Version History

### v3.0.0 (2025-12-29)
- Complete rewrite: Node.js → Python/FastAPI
- 15 modular tools with auto-discovery
- Electron menu bar app with Cmd+Shift+J
- WebSocket for real-time alerts
- TTS optimization (30-90x faster)
- Cost tracking and analytics
