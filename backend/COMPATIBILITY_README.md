# Frontend Compatibility Layer

API endpoints for compatibility with existing JARVIS web frontend.

## Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| /api/chat/v2 | POST | Streaming chat (SSE) |
| /api/metrics | GET | Prometheus metrics |
| /api/services | GET | Uptime Kuma status |
| /api/settings | GET/POST | User settings |
| /api/costs | GET | Cost tracking |
| /api/cameras | GET | Camera list |
| /api/alerts | GET | Recent alerts |
| /api/tts | POST | Text-to-speech |
| /api/topology | GET | Network topology |
| /api/history | GET | Conversation history |

## SSE Event Types

Chat endpoint streams these event types:

| Type | Description |
|------|-------------|
| content | Text chunk |
| tool_start | Tool execution starting |
| tool_end | Tool execution complete |
| done | Response complete |
| error | Error occurred |

## Database

SQLite tables in /opt/jarvis-v3/backend/data/jarvis.db:

- **user_settings**: User preferences (theme, model, voice)
- **api_costs**: Token usage and cost tracking

## Frontend Location

Static files served from: /opt/jarvis-v3/frontend/web/

Files:
- index.html - Main UI
- jarvis.js - Core logic
- speech.js - Voice handling
- config.js - API configuration
- styles.css - Styling
