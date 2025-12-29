# JARVIS v3 Backend

Python/FastAPI backend for JARVIS AI assistant.

## Quick Reference

```bash
# Server
http://192.168.10.100:3939

# Service
systemctl restart jarvis-v3
journalctl -u jarvis-v3 -f

# Virtual Environment
cd /opt/jarvis-v3/backend
source venv/bin/activate
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/chat/v2` | POST | Streaming chat (SSE) |
| `/api/metrics` | GET | Prometheus metrics |
| `/api/services` | GET | Uptime Kuma status |
| `/api/settings` | GET/POST | User settings |
| `/api/costs` | GET | Cost tracking |
| `/api/cameras` | GET | UniFi Protect cameras |
| `/api/alerts` | GET | Recent alerts |
| `/api/tts` | POST | Text-to-speech |
| `/api/v1/tools` | GET | List all tools |
| `/ws` | WebSocket | Real-time events |
| `/api/webhook/protect` | POST | Protect webhooks |

## Tools (15 Total)

### Homelab (12)
- `proxmox_query` / `proxmox_manage`
- `prometheus`
- `uptime_kuma`
- `unifi_network`
- `unifi_protect_query` / `unifi_protect_automation` / `unifi_protect_webhook`
- `query_home_assistant` / `manage_home_assistant`
- `query_portainer` / `manage_portainer`

### Utilities (3)
- `get_time`
- `get_weather`
- `research`

## Configuration

Edit `/opt/jarvis-v3/backend/.env` for API keys and service URLs.

## Development

```bash
# Activate venv
source venv/bin/activate

# Run manually
python -m uvicorn app.main:app --host 0.0.0.0 --port 3939 --reload

# Test imports
python -c "from app.main import app"

# Install new dependency
pip install <package>
pip freeze > requirements.txt
```

## Adding New Tools

1. Create file in `app/tools/homelab/` or `app/tools/utilities/`
2. Inherit from `BaseTool`
3. Define `name`, `description`, `domain`, `parameters`
4. Implement `async def execute(self, **kwargs)`
5. Tool auto-discovers on restart

Example:
```python
from app.tools.base import BaseTool, ToolDomain, ToolParameter

class MyTool(BaseTool):
    name = "my_tool"
    description = "Does something useful"
    domain = ToolDomain.HOMELAB
    parameters = [
        ToolParameter(name="query", type="string", description="What to query")
    ]

    async def execute(self, query: str) -> dict:
        # Implementation
        return {"result": "data"}
```
