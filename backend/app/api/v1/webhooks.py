"""
Webhook endpoints for JARVIS v3
Handles incoming webhooks from external services
"""
import logging
from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from app.core.events import (
    event_bus,
    EventType,
    publish_doorbell_event,
    publish_motion_event,
    publish_alert_event
)

logger = logging.getLogger(__name__)

router = APIRouter()


class ProtectWebhookPayload(BaseModel):
    """UniFi Protect webhook payload"""
    type: str
    event: Dict[str, Any]


@router.post("/webhook/protect")
async def protect_webhook(request: Request):
    """
    Webhook endpoint for UniFi Protect events.
    
    Receives doorbell rings, motion detection, and smart detection events.
    Publishes events to the event bus which broadcasts to WebSocket clients.
    """
    try:
        # Get raw payload
        payload = await request.json()
        
        logger.info(f"Received Protect webhook: {payload.get('type', 'unknown')}")
        logger.debug(f"Payload: {payload}")
        
        event_type = payload.get("type", "")
        event_data = payload.get("event", {})
        
        # Extract camera information
        camera_name = event_data.get("camera", {}).get("name", "Unknown Camera")
        camera_id = event_data.get("camera", {}).get("id", "")
        
        # Handle different event types
        if event_type == "ring" or "ring" in event_type.lower():
            # Doorbell ring event
            logger.info(f"Doorbell ring detected: {camera_name}")
            
            await publish_doorbell_event(
                camera_name=camera_name,
                event_data={
                    "camera_id": camera_id,
                    "camera_name": camera_name,
                    "event_type": event_type,
                    "timestamp": event_data.get("start", datetime.now().timestamp() * 1000),
                    "raw_event": event_data
                }
            )
            
            # Also publish as alert for visibility
            await publish_alert_event(
                alert_type="doorbell",
                message=f"Doorbell ring at {camera_name}",
                severity="info",
                extra={
                    "camera_name": camera_name,
                    "camera_id": camera_id
                }
            )
        
        elif event_type == "motion" or "motion" in event_type.lower():
            # Motion detection event
            logger.info(f"Motion detected: {camera_name}")
            
            # Check for smart detection types
            smart_detect_types = event_data.get("smartDetectTypes", [])
            
            await publish_motion_event(
                camera_name=camera_name,
                event_data={
                    "camera_id": camera_id,
                    "camera_name": camera_name,
                    "event_type": event_type,
                    "smart_detect_types": smart_detect_types,
                    "timestamp": event_data.get("start", datetime.now().timestamp() * 1000),
                    "raw_event": event_data
                }
            )
            
            # If person detected, publish alert
            if "person" in smart_detect_types:
                await publish_alert_event(
                    alert_type="person_detected",
                    message=f"Person detected at {camera_name}",
                    severity="info",
                    extra={
                        "camera_name": camera_name,
                        "camera_id": camera_id,
                        "smart_detect_types": smart_detect_types
                    }
                )
        
        elif "smartDetect" in event_type or "smart" in event_type.lower():
            # Smart detection event (person, vehicle, animal, etc.)
            smart_detect_types = event_data.get("smartDetectTypes", [])
            
            logger.info(f"Smart detection at {camera_name}: {smart_detect_types}")
            
            await publish_motion_event(
                camera_name=camera_name,
                event_data={
                    "camera_id": camera_id,
                    "camera_name": camera_name,
                    "event_type": event_type,
                    "smart_detect_types": smart_detect_types,
                    "timestamp": event_data.get("start", datetime.now().timestamp() * 1000),
                    "raw_event": event_data
                }
            )
            
            # Publish alert for smart detections
            if smart_detect_types:
                detection_type = smart_detect_types[0] if smart_detect_types else "object"
                await publish_alert_event(
                    alert_type=f"{detection_type}_detected",
                    message=f"{detection_type.title()} detected at {camera_name}",
                    severity="info",
                    extra={
                        "camera_name": camera_name,
                        "camera_id": camera_id,
                        "smart_detect_types": smart_detect_types
                    }
                )
        
        else:
            # Unknown event type
            logger.warning(f"Unknown Protect event type: {event_type}")
            
            # Still publish as generic alert
            await publish_alert_event(
                alert_type="protect_event",
                message=f"Protect event at {camera_name}: {event_type}",
                severity="info",
                extra={
                    "camera_name": camera_name,
                    "event_type": event_type,
                    "raw_event": event_data
                }
            )
        
        return {
            "status": "ok",
            "event_type": event_type,
            "camera": camera_name,
            "processed_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error processing Protect webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhook/protect/test")
async def test_protect_webhook():
    """Test endpoint to verify webhook is accessible"""
    return {
        "status": "ok",
        "endpoint": "/api/webhook/protect",
        "message": "Webhook endpoint is active"
    }
