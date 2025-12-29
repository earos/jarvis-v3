# WebSocket & Event System

Real-time event broadcasting for JARVIS v3.

## Quick Start

```javascript
// Connect
const ws = new WebSocket('ws://192.168.10.100:3939/ws');

// Receive events
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.type, data.data);
};
```

## Architecture

```
UniFi Protect → Webhook → Event Bus → WebSocket → Clients
                              ↓
                        Event History
```

## Event Types

| Type | Source | Description |
|------|--------|-------------|
| `doorbell` | UniFi Protect | Doorbell ring |
| `motion` | UniFi Protect | Motion detected |
| `alert` | System | General alerts |
| `system` | Server | Connection events |

## WebSocket Messages

### Server → Client
```json
{"type": "system", "event": "connected", "message": "Connected to JARVIS v3"}
{"type": "doorbell", "data": {"camera_name": "Front Door", ...}}
{"type": "motion", "data": {"camera_name": "Driveway", "smart_detect_types": ["person"]}}
{"type": "pong", "timestamp": "..."}
```

### Client → Server
```json
{"type": "ping"}
{"type": "stats"}
{"type": "history", "limit": 10}
```

## API Endpoints

```bash
# WebSocket connection
ws://192.168.10.100:3939/ws

# Connection stats
GET /api/v1/websocket/stats

# Event history
GET /api/v1/events/history?limit=10

# Webhook receiver
POST /api/webhook/protect

# Test webhook
GET /api/webhook/protect/test
```

## UniFi Protect Setup

1. Open Protect UI: https://192.168.20.250
2. Settings → Alarm Manager
3. Add Automation:
   - Trigger: Doorbell Ring / Smart Detection
   - Action: Webhook
   - URL: `http://192.168.10.100:3939/api/webhook/protect`

## Files

| File | Purpose |
|------|---------|
| `app/core/events.py` | Event bus (pub/sub) |
| `app/api/websocket/handlers.py` | WebSocket manager |
| `app/api/v1/webhooks.py` | Webhook endpoints |

## Testing

```bash
# Test webhook
curl -X POST http://localhost:3939/api/webhook/protect \
  -H "Content-Type: application/json" \
  -d '{"type": "ring", "event": {"camera": {"name": "Front Door"}}}'

# Check event history
curl http://localhost:3939/api/v1/events/history

# Check connections
curl http://localhost:3939/api/v1/websocket/stats
```
