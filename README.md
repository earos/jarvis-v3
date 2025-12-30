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
| 22 Tools | Homelab monitoring and management |
| Voice I/O | ElevenLabs TTS (30-90x optimized) |
| Menu Bar | macOS app with Cmd+Shift+J shortcut |
| WebSocket | Real-time doorbell/motion alerts |
| Settings UI | Configure all integrations via menu bar app |
| Metrics | Prometheus/Grafana integration |
| Services | Uptime Kuma monitoring |
| Cameras | UniFi Protect integration |

## Tools (22 Total)

### Infrastructure (8)
| Tool | Description |
|------|-------------|
| `proxmox_query` | Query Proxmox cluster status |
| `proxmox_manage` | Start/stop VMs and containers |
| `prometheus` | Query metrics via PromQL |
| `uptime_kuma` | Service health monitoring |
| `query_portainer` | Docker container status |
| `manage_portainer` | Start/stop containers |
| `grafana` | Query Grafana dashboards |
| `nginx_proxy_manager` | Manage proxy hosts |

### Network (4)
| Tool | Description |
|------|-------------|
| `unifi_network` | Network status and clients |
| `adguard` | DNS and ad-blocking stats |
| `starlink` | Satellite internet status/speed/obstructions |

### Home Automation (4)
| Tool | Description |
|------|-------------|
| `unifi_protect_query` | Camera and NVR status |
| `unifi_protect_automation` | Camera automations |
| `unifi_protect_webhook` | Webhook configuration |
| `query_home_assistant` | HA sensor states |
| `manage_home_assistant` | Control HA devices |

### Storage (1)
| Tool | Description |
|------|-------------|
| `synology_nas` | NAS status, shares, storage |

### 3D Printing (1)
| Tool | Description |
|------|-------------|
| `printers_3d` | Bambu Lab X1C & Prusa MK3.5 status |

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
- Location: `~/jarvis-menubar/` (local development)
- Shortcut: `Cmd+Shift+J`
- Features: Quick chat, settings UI, doorbell alerts, native notifications, API cost tracking

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/chat/v2` | POST | Streaming chat (SSE) |
| `/api/v1/tools` | GET | List all tools |
| `/api/v1/integrations` | GET | List integrations |
| `/api/v1/integrations/{name}` | PUT | Update integration |
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

# Infrastructure
PROMETHEUS_URL=http://192.168.10.104:9090
UPTIME_KUMA_URL=http://192.168.10.104:3001
PROXMOX_TOKEN_NAME=...
PROXMOX_TOKEN_VALUE=...
PORTAINER_API_KEY=...
GRAFANA_URL=http://192.168.10.104:3000
GRAFANA_API_KEY=...
NPM_URL=http://192.168.10.104:81
NPM_USER=...
NPM_PASSWORD=...

# Network
UNIFI_HOST=192.168.10.1
UNIFI_USER=...
UNIFI_PASSWORD=...
ADGUARD_URL=http://192.168.10.249:8080
ADGUARD_USER=...
ADGUARD_PASSWORD=...
STARLINK_HOST=192.168.100.1

# Home Automation
PROTECT_HOST=192.168.20.250
PROTECT_USER=...
PROTECT_PASSWORD=...
HOME_ASSISTANT_URL=http://192.168.10.104:8123
HOME_ASSISTANT_TOKEN=...

# Storage
SYNOLOGY_HOST=192.168.10.249
SYNOLOGY_USER=...
SYNOLOGY_PASSWORD=...

# 3D Printing
BAMBU_HOST=192.168.10.172
BAMBU_ACCESS_CODE=...
PRUSA_HOST=192.168.10.186
PRUSA_USERNAME=...
PRUSA_PASSWORD=...

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
│   │   └── tools/               # 22 tools
│   ├── data/jarvis.db           # SQLite
│   └── .env                     # Config
├── frontend/web/                # Web UI static files
└── README.md
```

## Service Management

```bash
systemctl status jarvis-v3    # Status
systemctl restart jarvis-v3   # Restart
journalctl -u jarvis-v3 -f    # Logs
```

## Version History

### v3.0.1 (2025-12-30)
- All 22 tools working
- Added: Starlink (gRPC), Bambu Lab (MQTT), Prusa (HTTP Digest)
- Settings UI for all integrations via menu bar app
- Prusa username/password authentication support

### v3.0.0 (2025-12-29)
- Complete rewrite: Node.js → Python/FastAPI
- 15 modular tools with auto-discovery
- Electron menu bar app with Cmd+Shift+J
- WebSocket for real-time alerts
- TTS optimization (30-90x faster)
- Cost tracking and analytics
