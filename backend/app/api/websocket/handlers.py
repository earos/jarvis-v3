"""
WebSocket Handlers for JARVIS v3
Manages WebSocket connections and real-time event broadcasting
"""
import asyncio
import json
import logging
from typing import Dict, Set, Optional
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect
from app.core.events import event_bus, Event, EventType

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections and broadcasts events to connected clients.
    Singleton pattern to maintain a single connection pool.
    """
    _instance: Optional['ConnectionManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        # Only initialize once
        if self._initialized:
            return
        
        self.active_connections: Set[WebSocket] = set()
        self.client_info: Dict[WebSocket, Dict] = {}
        self._initialized = True
        
        # Subscribe to all events from event bus
        event_bus.subscribe_all(self._on_event)
        
        logger.info("ConnectionManager initialized")
    
    async def connect(self, websocket: WebSocket, client_id: Optional[str] = None) -> None:
        """
        Accept and register a new WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            client_id: Optional client identifier
        """
        await websocket.accept()
        self.active_connections.add(websocket)
        
        # Store client info
        self.client_info[websocket] = {
            "client_id": client_id or f"client_{id(websocket)}",
            "connected_at": datetime.now().isoformat(),
            "events_sent": 0
        }
        
        logger.info(f"WebSocket client connected: {self.client_info[websocket]['client_id']} (Total: {len(self.active_connections)})")
        
        # Send welcome message
        await self.send_personal_message(
            {
                "type": "system",
                "event": "connected",
                "message": "Connected to JARVIS v3",
                "timestamp": datetime.now().isoformat()
            },
            websocket
        )
    
    def disconnect(self, websocket: WebSocket) -> None:
        """
        Remove a WebSocket connection.
        
        Args:
            websocket: WebSocket connection to remove
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            
            client_id = self.client_info.get(websocket, {}).get("client_id", "unknown")
            logger.info(f"WebSocket client disconnected: {client_id} (Remaining: {len(self.active_connections)})")
            
            # Clean up client info
            if websocket in self.client_info:
                del self.client_info[websocket]
    
    async def send_personal_message(self, message: Dict, websocket: WebSocket) -> None:
        """
        Send a message to a specific client.
        
        Args:
            message: Message to send (will be JSON serialized)
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_json(message)
            
            # Update stats
            if websocket in self.client_info:
                self.client_info[websocket]["events_sent"] += 1
        except Exception as e:
            logger.error(f"Error sending message to client: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict, exclude: Optional[WebSocket] = None) -> None:
        """
        Broadcast a message to all connected clients.
        
        Args:
            message: Message to broadcast (will be JSON serialized)
            exclude: Optional WebSocket connection to exclude from broadcast
        """
        disconnected = []
        
        for connection in self.active_connections:
            if exclude and connection == exclude:
                continue
            
            try:
                await connection.send_json(message)
                
                # Update stats
                if connection in self.client_info:
                    self.client_info[connection]["events_sent"] += 1
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
    
    async def _on_event(self, event: Event) -> None:
        """
        Event bus callback - broadcasts events to all WebSocket clients.
        
        Args:
            event: Event from the event bus
        """
        # Convert event to WebSocket message format
        message = event.to_dict()
        
        logger.debug(f"Broadcasting {event.type.value} event to {len(self.active_connections)} clients")
        
        # Broadcast to all connected clients
        await self.broadcast(message)
    
    async def send_ping(self, websocket: WebSocket) -> None:
        """
        Send a ping message to check if connection is alive.
        
        Args:
            websocket: WebSocket connection to ping
        """
        try:
            await websocket.send_json({
                "type": "ping",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error sending ping: {e}")
            self.disconnect(websocket)
    
    def get_stats(self) -> Dict:
        """Get statistics about active connections"""
        return {
            "total_connections": len(self.active_connections),
            "clients": [
                {
                    "client_id": info["client_id"],
                    "connected_at": info["connected_at"],
                    "events_sent": info["events_sent"]
                }
                for info in self.client_info.values()
            ]
        }


# Global instance
connection_manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, client_id: Optional[str] = None):
    """
    WebSocket endpoint handler.
    
    Args:
        websocket: WebSocket connection
        client_id: Optional client identifier from query params
    """
    await connection_manager.connect(websocket, client_id)
    
    try:
        # Keep connection alive with ping/pong
        while True:
            try:
                # Wait for message with timeout
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0  # 30 second timeout
                )
                
                # Parse message
                try:
                    message = json.loads(data)
                except json.JSONDecodeError:
                    await connection_manager.send_personal_message(
                        {
                            "type": "error",
                            "message": "Invalid JSON"
                        },
                        websocket
                    )
                    continue
                
                # Handle different message types
                msg_type = message.get("type")
                
                if msg_type == "ping":
                    # Respond to ping with pong
                    await connection_manager.send_personal_message(
                        {
                            "type": "pong",
                            "timestamp": datetime.now().isoformat()
                        },
                        websocket
                    )
                
                elif msg_type == "subscribe":
                    # Client wants to subscribe to specific event types
                    # For now we broadcast all events, but this could be extended
                    await connection_manager.send_personal_message(
                        {
                            "type": "subscribed",
                            "events": [e.value for e in EventType]
                        },
                        websocket
                    )
                
                elif msg_type == "stats":
                    # Client requesting connection stats
                    stats = connection_manager.get_stats()
                    await connection_manager.send_personal_message(
                        {
                            "type": "stats",
                            "data": stats
                        },
                        websocket
                    )
                
                elif msg_type == "history":
                    # Client requesting event history
                    limit = message.get("limit", 10)
                    history = event_bus.get_history(limit)
                    await connection_manager.send_personal_message(
                        {
                            "type": "history",
                            "events": history
                        },
                        websocket
                    )
                
                else:
                    logger.warning(f"Unknown message type: {msg_type}")
            
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await connection_manager.send_ping(websocket)
    
    except WebSocketDisconnect:
        logger.info("Client disconnected normally")
        connection_manager.disconnect(websocket)
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        connection_manager.disconnect(websocket)


# Helper function to broadcast custom events
async def broadcast_event(
    event_type: str,
    data: Dict,
    source: Optional[str] = None
) -> None:
    """
    Broadcast a custom event to all WebSocket clients.
    
    Args:
        event_type: Type of event
        data: Event data
        source: Source of the event
    """
    message = {
        "type": event_type,
        "data": data,
        "timestamp": datetime.now().isoformat(),
        "source": source
    }
    
    await connection_manager.broadcast(message)
