"""
Event Bus for JARVIS v3
Singleton event emitter for pub/sub pattern between components
"""
import asyncio
import logging
from typing import Callable, Dict, List, Any, Optional
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Event types for the system"""
    DOORBELL = "doorbell"
    MOTION = "motion"
    ALERT = "alert"
    RESPONSE = "response"
    TOOL_EXECUTION = "tool_execution"
    SYSTEM = "system"


@dataclass
class Event:
    """Event object"""
    type: EventType
    data: Dict[str, Any]
    timestamp: Optional[float] = None
    source: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().timestamp()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "source": self.source
        }


class EventBus:
    """
    Singleton event bus for pub/sub pattern.
    Allows components to publish events and subscribe to event types.
    """
    _instance: Optional['EventBus'] = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        # Only initialize once
        if self._initialized:
            return
        
        self._subscribers: Dict[EventType, List[Callable]] = {
            event_type: [] for event_type in EventType
        }
        self._wildcard_subscribers: List[Callable] = []
        self._event_history: List[Event] = []
        self._max_history = 100
        self._initialized = True
        
        logger.info("EventBus initialized")
    
    def subscribe(self, event_type: EventType, callback: Callable) -> None:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to listen for
            callback: Async function to call when event is published
        """
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)
            logger.info(f"Subscribed to {event_type.value} events")
    
    def subscribe_all(self, callback: Callable) -> None:
        """
        Subscribe to all event types.
        
        Args:
            callback: Async function to call for any event
        """
        if callback not in self._wildcard_subscribers:
            self._wildcard_subscribers.append(callback)
            logger.info("Subscribed to all events")
    
    def unsubscribe(self, event_type: EventType, callback: Callable) -> None:
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: Type of event to stop listening for
            callback: Callback function to remove
        """
        if callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)
            logger.info(f"Unsubscribed from {event_type.value} events")
    
    def unsubscribe_all(self, callback: Callable) -> None:
        """
        Unsubscribe from all events.
        
        Args:
            callback: Callback function to remove
        """
        if callback in self._wildcard_subscribers:
            self._wildcard_subscribers.remove(callback)
            logger.info("Unsubscribed from all events")
    
    async def publish(
        self,
        event_type: EventType,
        data: Dict[str, Any],
        source: Optional[str] = None
    ) -> None:
        """
        Publish an event to all subscribers.
        
        Args:
            event_type: Type of event being published
            data: Event data payload
            source: Source component that published the event
        """
        event = Event(
            type=event_type,
            data=data,
            source=source
        )
        
        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        logger.info(f"Publishing {event_type.value} event from {source}")
        logger.debug(f"Event data: {data}")
        
        # Notify specific subscribers
        subscribers = self._subscribers[event_type].copy()
        for callback in subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in event subscriber: {e}", exc_info=True)
        
        # Notify wildcard subscribers
        wildcard = self._wildcard_subscribers.copy()
        for callback in wildcard:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in wildcard subscriber: {e}", exc_info=True)
    
    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent event history.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of recent events as dictionaries
        """
        return [event.to_dict() for event in self._event_history[-limit:]]
    
    def get_subscribers_count(self) -> Dict[str, int]:
        """Get count of subscribers per event type"""
        return {
            event_type.value: len(callbacks)
            for event_type, callbacks in self._subscribers.items()
        }
    
    def clear_history(self) -> None:
        """Clear event history"""
        self._event_history.clear()
        logger.info("Event history cleared")


# Global instance
event_bus = EventBus()


# Helper functions
async def publish_doorbell_event(camera_name: str, event_data: Dict[str, Any]) -> None:
    """Publish a doorbell ring event"""
    await event_bus.publish(
        EventType.DOORBELL,
        {
            "camera_name": camera_name,
            "event": event_data,
            "timestamp": datetime.now().isoformat()
        },
        source="unifi_protect"
    )


async def publish_motion_event(camera_name: str, event_data: Dict[str, Any]) -> None:
    """Publish a motion detection event"""
    await event_bus.publish(
        EventType.MOTION,
        {
            "camera_name": camera_name,
            "event": event_data,
            "timestamp": datetime.now().isoformat()
        },
        source="unifi_protect"
    )


async def publish_alert_event(
    alert_type: str,
    message: str,
    severity: str = "info",
    extra: Optional[Dict[str, Any]] = None
) -> None:
    """Publish a general alert event"""
    await event_bus.publish(
        EventType.ALERT,
        {
            "alert_type": alert_type,
            "message": message,
            "severity": severity,
            **(extra or {})
        },
        source="system"
    )


async def publish_response_event(response: str, context: Optional[Dict[str, Any]] = None) -> None:
    """Publish an AI response event"""
    await event_bus.publish(
        EventType.RESPONSE,
        {
            "response": response,
            "context": context or {}
        },
        source="orchestrator"
    )


async def publish_tool_execution_event(
    tool_name: str,
    status: str,
    result: Optional[Dict[str, Any]] = None
) -> None:
    """Publish a tool execution event"""
    await event_bus.publish(
        EventType.TOOL_EXECUTION,
        {
            "tool_name": tool_name,
            "status": status,
            "result": result
        },
        source="orchestrator"
    )
