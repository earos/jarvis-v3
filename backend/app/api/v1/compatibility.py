"""
JARVIS v3 - Compatibility API Routes
Endpoints to maintain compatibility with existing JARVIS frontend
"""
import json
import logging
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config.settings import get_settings
from app.core.orchestrator.shared import get_orchestrator
from app.tools.registry import tool_registry
from app.tools.homelab.prometheus import PrometheusTool
from app.tools.homelab.uptime_kuma import UptimeKumaTool
from app.tools.homelab.unifi_protect import UniFiProtectQueryTool

logger = logging.getLogger(__name__)
settings = get_settings()

# Create router
router = APIRouter()

# Database setup
Base = declarative_base()
engine = create_engine('sqlite:////opt/jarvis-v3/backend/data/jarvis.db')
SessionLocal = sessionmaker(bind=engine)


# Database Models
class UserSettings(Base):
    __tablename__ = 'user_settings'

    id = Column(Integer, primary_key=True)
    user_id = Column(String, default='default')
    settings_json = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class APICost(Base):
    __tablename__ = 'api_costs'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    model = Column(String)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    cost_usd = Column(Float)
    tool_name = Column(String, nullable=True)
    session_id = Column(String, nullable=True)


# Create tables
# Get shared orchestrator instance


# Request/Response Models
class ChatRequestV2(BaseModel):
    message: str
    session_id: Optional[str] = None


class SettingsUpdate(BaseModel):
    settings: Dict[str, Any]




# ============================================================================
# 1. CHAT ENDPOINT - /api/chat/v2 (POST)
# ============================================================================
@router.post("/api/chat/v2")
async def chat_v2(request: ChatRequestV2):
    """
    Streaming chat endpoint with SSE format.
    Compatible with frontend expectations.
    """
    async def generate():
        try:
            # Track for cost calculation
            input_tokens = 0
            output_tokens = 0
            tools_used = []

            async for chunk in get_orchestrator().process_stream(
                message=request.message,
                domain="homelab"
            ):
                if chunk["type"] == "text":
                    # Send text chunk
                    yield f"data: {json.dumps({'type': 'content', 'content': chunk['content']})}\n\n"

                elif chunk["type"] == "tool_use":
                    # Send tool start event
                    tools_used.append(chunk["name"])
                    yield f"data: {json.dumps({'type': 'tool_start', 'content': chunk['name']})}\n\n"

                elif chunk["type"] == "tool_result":
                    # Send tool end event
                    yield f"data: {json.dumps({'type': 'tool_end', 'content': 'Tool completed'})}\n\n"

                elif chunk["type"] == "done":
                    # Track usage for costs
                    usage = chunk.get("usage", {})
                    input_tokens = usage.get("input_tokens", 0)
                    output_tokens = usage.get("output_tokens", 0)

                    # Calculate cost (Claude Sonnet 4 pricing)
                    cost = (input_tokens * 0.000003) + (output_tokens * 0.000015)

                    # Save to database
                    try:
                        db = SessionLocal()
                        cost_record = APICost(
                            model=settings.default_model,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            cost_usd=cost,
                            tool_name=",".join(tools_used) if tools_used else None,
                            session_id=request.session_id
                        )
                        db.add(cost_record)
                        db.commit()
                        db.close()
                    except Exception as e:
                        logger.error(f"Failed to save cost record: {e}")

                    # Send done event
                    yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"

        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# ============================================================================
# 2. METRICS ENDPOINT - /api/metrics (GET)
# ============================================================================
@router.get("/api/metrics")
async def get_metrics():
    """
    Get system metrics from Prometheus.
    Returns CPU, RAM, and Disk usage.
    """
    try:
        prometheus = PrometheusTool()

        # Query CPU usage
        cpu_result = await prometheus.execute(
            query='100 - (avg by(instance)(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
        )

        # Query RAM usage
        ram_total = await prometheus.execute(query='node_memory_MemTotal_bytes')
        ram_available = await prometheus.execute(query='node_memory_MemAvailable_bytes')

        # Query Disk usage
        disk_total = await prometheus.execute(
            query='node_filesystem_size_bytes{mountpoint="/"}'
        )
        disk_available = await prometheus.execute(
            query='node_filesystem_avail_bytes{mountpoint="/"}'
        )

        metrics = []

        # Process CPU
        if cpu_result.get("success") and cpu_result.get("results"):
            for result in cpu_result["results"][:3]:  # Limit to 3 instances
                instance = result["metric"].get("instance", "unknown")
                value = float(result["value"]) if result["value"] else 0
                metrics.append({
                    "name": f"CPU ({instance})",
                    "value": f"{value:.1f}%",
                    "percent": value,
                    "unit": "%"
                })

        # Process RAM
        if ram_total.get("success") and ram_available.get("success"):
            for i, total_result in enumerate(ram_total.get("results", [])[:3]):
                if i < len(ram_available.get("results", [])):
                    available_result = ram_available["results"][i]

                    instance = total_result["metric"].get("instance", "unknown")
                    total_bytes = float(total_result["value"]) if total_result["value"] else 0
                    available_bytes = float(available_result["value"]) if available_result["value"] else 0

                    used_bytes = total_bytes - available_bytes
                    percent = (used_bytes / total_bytes * 100) if total_bytes > 0 else 0

                    metrics.append({
                        "name": f"RAM ({instance})",
                        "value": f"{used_bytes / 1024**3:.1f} / {total_bytes / 1024**3:.1f} GB",
                        "percent": percent,
                        "unit": "GB"
                    })

        # Process Disk
        if disk_total.get("success") and disk_available.get("success"):
            for i, total_result in enumerate(disk_total.get("results", [])[:3]):
                if i < len(disk_available.get("results", [])):
                    available_result = disk_available["results"][i]

                    instance = total_result["metric"].get("instance", "unknown")
                    total_bytes = float(total_result["value"]) if total_result["value"] else 0
                    available_bytes = float(available_result["value"]) if available_result["value"] else 0

                    used_bytes = total_bytes - available_bytes
                    percent = (used_bytes / total_bytes * 100) if total_bytes > 0 else 0

                    metrics.append({
                        "name": f"Disk ({instance})",
                        "value": f"{used_bytes / 1024**3:.0f} / {total_bytes / 1024**3:.0f} GB",
                        "percent": percent,
                        "unit": "GB"
                    })

        return {"metrics": metrics}

    except Exception as e:
        logger.error(f"Metrics error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 3. SERVICES ENDPOINT - /api/services (GET)
# ============================================================================
@router.get("/api/services")
async def get_services():
    """
    Get service status from Uptime Kuma.
    Returns list of services with health status.
    """
    try:
        uptime_kuma = UptimeKumaTool()
        result = await uptime_kuma.execute()

        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))

        services = []
        for service in result.get("services", []):
            services.append({
                "name": service["name"],
                "status": service["status"],
                "url": ""  # Uptime Kuma doesn't provide URL in current implementation
            })

        return {
            "services": services,
            "summary": {
                "up": result.get("up", 0),
                "down": result.get("down", 0),
                "total": result.get("total_services", 0)
            }
        }

    except Exception as e:
        logger.error(f"Services error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 4. SETTINGS ENDPOINTS - /api/settings (GET/POST)
# ============================================================================
@router.get("/api/settings")
async def get_settings():
    """
    Get user settings and available options.
    """
    try:
        db = SessionLocal()
        settings_record = db.query(UserSettings).filter_by(user_id='default').first()

        if settings_record:
            user_settings = json.loads(settings_record.settings_json)
        else:
            # Default settings
            user_settings = {
                "theme": "dark",
                "model": "claude-sonnet-4-20250514",
                "voice": "onwK4e9ZLuTAKqWW03F9",
                "notifications": True,
                "streaming": True
            }

        db.close()

        return {
            "settings": user_settings,
            "available_models": [
                {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4"},
                {"id": "claude-opus-4-20250514", "name": "Claude Opus 4"},
                {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet"},
                {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku"}
            ],
            "available_voices": [
                {"id": "onwK4e9ZLuTAKqWW03F9", "name": "Daniel"},
                {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Sarah"},
                {"id": "pNInz6obpgDQGcFmaJgB", "name": "Adam"}
            ]
        }

    except Exception as e:
        logger.error(f"Get settings error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/settings")
async def update_settings(update: SettingsUpdate):
    """
    Save user settings to database.
    """
    try:
        db = SessionLocal()
        settings_record = db.query(UserSettings).filter_by(user_id='default').first()

        if settings_record:
            settings_record.settings_json = json.dumps(update.settings)
            settings_record.updated_at = datetime.utcnow()
        else:
            settings_record = UserSettings(
                user_id='default',
                settings_json=json.dumps(update.settings)
            )
            db.add(settings_record)

        db.commit()
        db.close()

        return {"success": True, "settings": update.settings}

    except Exception as e:
        logger.error(f"Update settings error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 5. COSTS ENDPOINT - /api/costs (GET)
# ============================================================================
@router.get("/api/costs")
async def get_costs(
    days: int = Query(default=7, ge=1, le=365),
    breakdown: str = Query(default="summary", regex="^(summary|tool|day)$")
):
    """
    Get API cost tracking data.
    """
    try:
        db = SessionLocal()

        # Calculate date range
        start_date = datetime.utcnow() - timedelta(days=days)

        # Query costs
        costs = db.query(APICost).filter(APICost.timestamp >= start_date).all()

        if breakdown == "summary":
            # Total summary
            total_cost = sum(c.cost_usd for c in costs)
            total_input_tokens = sum(c.input_tokens for c in costs)
            total_output_tokens = sum(c.output_tokens for c in costs)

            result = {
                "period": f"{days} days",
                "total_cost": round(total_cost, 4),
                "total_requests": len(costs),
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "average_cost_per_request": round(total_cost / len(costs), 4) if costs else 0
            }

        elif breakdown == "tool":
            # Breakdown by tool
            tool_costs = {}
            for cost in costs:
                tool = cost.tool_name or "no_tool"
                if tool not in tool_costs:
                    tool_costs[tool] = {"cost": 0, "requests": 0}
                tool_costs[tool]["cost"] += cost.cost_usd
                tool_costs[tool]["requests"] += 1

            result = {
                "period": f"{days} days",
                "by_tool": [
                    {"tool": k, "cost": round(v["cost"], 4), "requests": v["requests"]}
                    for k, v in sorted(tool_costs.items(), key=lambda x: x[1]["cost"], reverse=True)
                ]
            }

        else:  # breakdown == "day"
            # Breakdown by day
            daily_costs = {}
            for cost in costs:
                day = cost.timestamp.strftime("%Y-%m-%d")
                if day not in daily_costs:
                    daily_costs[day] = {"cost": 0, "requests": 0}
                daily_costs[day]["cost"] += cost.cost_usd
                daily_costs[day]["requests"] += 1

            result = {
                "period": f"{days} days",
                "by_day": [
                    {"date": k, "cost": round(v["cost"], 4), "requests": v["requests"]}
                    for k, v in sorted(daily_costs.items())
                ]
            }

        db.close()
        return result

    except Exception as e:
        logger.error(f"Costs error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 6. CAMERAS ENDPOINT - /api/cameras (GET)
# ============================================================================
@router.get("/api/cameras")
async def get_cameras():
    """
    Get camera list from UniFi Protect.
    """
    try:
        # Use UniFi Protect query tool
        protect_tool = UniFiProtectQueryTool()
        result = await protect_tool.execute(query="list all cameras")

        cameras = []

        # Parse the result (it returns a structured response)
        if result.get("success") and result.get("cameras"):
            for camera in result["cameras"]:
                cameras.append({
                    "id": camera.get("id"),
                    "name": camera.get("name"),
                    "type": camera.get("type", "camera"),
                    "rtspUrl": camera.get("rtsp_url", "")
                })

        return {"cameras": cameras}

    except Exception as e:
        logger.error(f"Cameras error: {e}", exc_info=True)
        # Return empty list on error rather than failing
        return {"cameras": []}


# ============================================================================
# 7. TTS ENDPOINT - /api/tts (POST)
# ============================================================================
class TTSRequest(BaseModel):
    text: str
    voice_id: Optional[str] = None


@router.post("/api/tts")
async def text_to_speech(request: TTSRequest):
    """
    Convert text to speech using ElevenLabs with optimized settings.
    Returns audio/mpeg stream.
    """
    try:
        if not settings.elevenlabs_api_key:
            raise HTTPException(status_code=500, detail="ElevenLabs API key not configured")

        voice_id = request.voice_id or settings.elevenlabs_voice_id

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": settings.elevenlabs_api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "text": request.text,
                    "model_id": "eleven_turbo_v2_5",  # 3x faster than eleven_monolingual_v1
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75
                    },
                    "optimize_streaming_latency": 4,  # Maximum latency optimization
                    "output_format": "mp3_44100_128"  # Optimized format
                }
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"ElevenLabs API error: {response.text}"
                )

            return StreamingResponse(
                iter([response.content]),
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": "inline; filename=speech.mp3"
                }
            )

    except httpx.HTTPError as e:
        logger.error(f"TTS HTTP error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"TTS error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/tts/stream")
async def text_to_speech_stream(request: TTSRequest):
    """
    Stream TTS audio using ElevenLabs streaming API.
    This provides much lower latency by starting playback immediately.
    """
    try:
        if not settings.elevenlabs_api_key:
            raise HTTPException(status_code=500, detail="ElevenLabs API key not configured")

        voice_id = request.voice_id or settings.elevenlabs_voice_id

        async def generate_audio():
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Use streaming endpoint with turbo-v2.5 model for lowest latency
                async with client.stream(
                    "POST",
                    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream",
                    headers={
                        "xi-api-key": settings.elevenlabs_api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "text": request.text,
                        "model_id": "eleven_turbo_v2_5",  # Fastest model
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.75,
                            "use_speaker_boost": True
                        },
                        "optimize_streaming_latency": 4,  # Maximum optimization
                        "output_format": "mp3_44100_128"  # Lower quality for speed
                    }
                ) as response:
                    if response.status_code != 200:
                        logger.error(f"ElevenLabs error: {response.status_code}")
                        return
                    
                    async for chunk in response.aiter_bytes(chunk_size=4096):
                        if chunk:
                            yield chunk

        return StreamingResponse(
            generate_audio(),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=speech.mp3",
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )

    except Exception as e:
        logger.error(f"TTS stream error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/tts/sentence")
async def text_to_speech_sentence(request: TTSRequest):
    """
    Optimized endpoint for single sentences with minimal latency.
    Uses turbo model for fastest response.
    """
    try:
        if not settings.elevenlabs_api_key:
            raise HTTPException(status_code=500, detail="ElevenLabs API key not configured")

        voice_id = request.voice_id or settings.elevenlabs_voice_id

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": settings.elevenlabs_api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "text": request.text,
                    "model_id": "eleven_turbo_v2_5",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75
                    },
                    "optimize_streaming_latency": 4,
                    "output_format": "mp3_44100_128"
                }
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"ElevenLabs API error: {response.text}"
                )

            return StreamingResponse(
                iter([response.content]),
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": "inline; filename=speech.mp3"
                }
            )

    except Exception as e:
        logger.error(f"TTS sentence error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))



# ============================================================================
# 8. ALERTS ENDPOINT - /api/alerts (GET)
# ============================================================================
@router.get("/api/alerts")
async def get_alerts():
    """
    Get recent alerts/events.
    Returns events from the event bus history.
    """
    try:
        from app.core.events import event_bus
        events = event_bus.get_history(limit=20)
        
        # Format as alerts
        alerts = []
        for event in events:
            alerts.append({
                "id": str(event.get("timestamp", 0)),
                "type": event.get("type", "unknown"),
                "message": event.get("data", {}).get("message", ""),
                "timestamp": event.get("timestamp"),
                "source": event.get("source", "system")
            })
        
        return {"alerts": alerts}
    except Exception as e:
        logger.error(f"Alerts error: {e}")
        return {"alerts": []}


# ============================================================================
# 9. TOPOLOGY ENDPOINT - /api/topology (GET)
# ============================================================================
@router.get("/api/topology")
async def get_topology():
    """
    Get network topology data for visualization.
    """
    # Return a basic topology structure
    return {
        "nodes": [
            {"id": "router", "label": "UDM SE", "type": "router", "ip": "192.168.10.1"},
            {"id": "pve1", "label": "PVE1", "type": "server", "ip": "192.168.10.50"},
            {"id": "pve2", "label": "PVE2", "type": "server", "ip": "192.168.10.51"},
            {"id": "pve3", "label": "PVE3", "type": "server", "ip": "192.168.10.52"},
            {"id": "nas", "label": "Synology", "type": "storage", "ip": "192.168.10.100"},
            {"id": "nvr", "label": "NVR Pro", "type": "camera", "ip": "192.168.20.250"}
        ],
        "edges": [
            {"from": "router", "to": "pve1"},
            {"from": "router", "to": "pve2"},
            {"from": "router", "to": "pve3"},
            {"from": "router", "to": "nas"},
            {"from": "router", "to": "nvr"}
        ]
    }


# ============================================================================
# 10. HISTORY ENDPOINT - /api/history (GET)
# ============================================================================
@router.get("/api/history")
async def get_history(limit: int = 20):
    """
    Get conversation history.
    """
    # For now return empty - can be extended to store conversations
    return {"history": [], "count": 0}
