"""
JARVIS v3 - FastAPI Application
Main entry point for the Python backend
"""
import logging
from contextlib import asynccontextmanager
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config.settings import get_settings
from app.tools.registry import tool_registry
from app.tools.base import ToolDomain
from app.core.orchestrator.shared import get_orchestrator
from app.api.websocket.handlers import websocket_endpoint, connection_manager
from app.core.events import event_bus
from app.api.v1.webhooks import router as webhook_router
from app.api.v1.compatibility import router as compatibility_router
from app.api.v1.integrations import router as integrations_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info("Starting JARVIS v3...")

    # Auto-discover tools
    count = tool_registry.auto_discover()
    logger.info(f"Registered {count} tools")
    logger.info(f"Tools by domain: {tool_registry.count_by_domain()}")

    # Initialize event bus and WebSocket manager
    logger.info(f"Event bus initialized with subscribers: {event_bus.get_subscribers_count()}")
    logger.info(f"WebSocket manager ready")

    yield

    # Shutdown
    logger.info("Shutting down JARVIS v3...")


# Create FastAPI app
app = FastAPI(
    title="JARVIS v3 API",
    description="Personal AI Assistant Backend",
    version=settings.version,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Orchestrator instance
# Orchestrator instance (shared singleton)

# Include routers
app.include_router(webhook_router, prefix="/api", tags=["webhooks"])
app.include_router(compatibility_router, tags=["compatibility"])
app.include_router(integrations_router, tags=["integrations"])


# Request/Response models
class ChatRequest(BaseModel):
    message: str
    domain: str = "homelab"
    session_id: Optional[str] = None
    stream: bool = False


class ChatResponse(BaseModel):
    response: str
    domain: str
    usage: Optional[dict] = None


class ToolInfo(BaseModel):
    name: str
    description: str
    domain: str


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_route(websocket: WebSocket, client_id: Optional[str] = None):
    """
    WebSocket endpoint for real-time events.

    Query params:
        client_id: Optional identifier for the client

    Events received:
        - doorbell: Doorbell ring events
        - motion: Motion detection events
        - alert: General alert events
        - response: AI response events
        - tool_execution: Tool execution status
    """
    await websocket_endpoint(websocket, client_id)


# API Endpoints
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "version": settings.version,
        "tools_count": tool_registry.count(),
        "websocket_connections": len(connection_manager.active_connections)
    }


@app.get("/api/v1/tools")
async def list_tools():
    """List all available tools"""
    tools = []
    for name in tool_registry.list_tools():
        tool = tool_registry.get_tool(name)
        tools.append({
            "name": tool.name,
            "description": tool.description,
            "domain": tool.domain.value
        })
    return {"tools": tools, "count": len(tools)}


@app.get("/api/v1/tools/{domain}")
async def list_tools_by_domain(domain: str):
    """List tools for a specific domain"""
    try:
        domain_enum = ToolDomain(domain)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid domain: {domain}")

    tools = tool_registry.get_tools_for_domain(domain_enum)
    return {
        "domain": domain,
        "tools": [
            {"name": t.name, "description": t.description}
            for t in tools
        ],
        "count": len(tools)
    }


@app.post("/api/v1/chat")
async def chat(request: ChatRequest):
    """Process a chat message"""
    if request.stream:
        # Return streaming response
        async def generate():
            async for chunk in get_orchestrator().process_stream(
                message=request.message,
                domain=request.domain
            ):
                import json
                yield f"data: {json.dumps(chunk)}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )
    else:
        # Return complete response
        response = await get_orchestrator().process(
            message=request.message,
            domain=request.domain
        )

        return ChatResponse(
            response=response,
            domain=request.domain
        )


@app.get("/api/v1/domains")
async def list_domains():
    """List available domains"""
    return {
        "domains": [
            {"id": d.value, "name": d.value.title()}
            for d in ToolDomain
        ]
    }


@app.get("/api/v1/events/history")
async def get_event_history(limit: int = 10):
    """Get recent event history"""
    return {
        "events": event_bus.get_history(limit),
        "count": len(event_bus.get_history(limit))
    }


@app.get("/api/v1/websocket/stats")
async def websocket_stats():
    """Get WebSocket connection statistics"""
    return connection_manager.get_stats()


# Mount static files for frontend (must be last)
# Serve the existing JARVIS frontend from /opt/jarvis-v3/frontend/web/
static_path = Path("/opt/jarvis-v3/frontend/web")
if static_path.exists():
    app.mount("/", StaticFiles(directory=str(static_path), html=True), name="static")
    logger.info(f"Mounted static files from {static_path}")
else:
    logger.warning(f"Static files directory not found: {static_path}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
