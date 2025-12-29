"""
Home Assistant Tool for JARVIS v3
Query and control Home Assistant devices and entities
"""
import httpx
from typing import Dict, Any, Optional

from app.tools.base import BaseTool, ToolParameter, ToolDomain
from app.config.settings import get_settings

settings = get_settings()


class QueryHomeAssistantTool(BaseTool):
    """Query Home Assistant for entity states and information"""
    
    name = "query_home_assistant"
    description = """Query Home Assistant for device and sensor information. Use this to check the state of lights, switches, sensors, climate controls, and other entities. Can retrieve all states or query specific entities."""
    
    domain = ToolDomain.HOMELAB
    
    parameters = [
        ToolParameter(
            name="info_type",
            type="string",
            description="Type of information to retrieve",
            enum=["all", "entity"]
        ),
        ToolParameter(
            name="entity_id",
            type="string",
            description="Entity ID to query (e.g., 'light.living_room', 'sensor.temperature'). Required when info_type is 'entity'.",
            required=False
        )
    ]
    
    def __init__(self):
        self.base_url = settings.home_assistant_url
        self.token = settings.home_assistant_token
        if not self.token:
            raise ValueError("HOME_ASSISTANT_TOKEN not configured")
    
    async def execute(self, info_type: str, entity_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute Home Assistant query"""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                if info_type == "all":
                    response = await client.get(
                        f"{self.base_url}/api/states",
                        headers=headers
                    )
                    response.raise_for_status()
                    states = response.json()
                    
                    return {
                        "success": True,
                        "info_type": "all",
                        "entity_count": len(states),
                        "states": states
                    }
                
                elif info_type == "entity":
                    if not entity_id:
                        return {
                            "success": False,
                            "error": "entity_id is required when info_type is 'entity'"
                        }
                    
                    response = await client.get(
                        f"{self.base_url}/api/states/{entity_id}",
                        headers=headers
                    )
                    response.raise_for_status()
                    state = response.json()
                    
                    return {
                        "success": True,
                        "info_type": "entity",
                        "entity_id": entity_id,
                        "state": state
                    }
                
                else:
                    return {
                        "success": False,
                        "error": f"Invalid info_type: {info_type}"
                    }
                    
            except httpx.HTTPStatusError as e:
                return {
                    "success": False,
                    "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }


class ManageHomeAssistantTool(BaseTool):
    """Control Home Assistant devices and entities"""
    
    name = "manage_home_assistant"
    description = """Control Home Assistant devices. Use this to turn lights/switches on/off, toggle devices, adjust brightness, or set climate temperature. This tool performs actions that change device states."""
    
    domain = ToolDomain.HOMELAB
    
    parameters = [
        ToolParameter(
            name="action",
            type="string",
            description="Action to perform",
            enum=["turn_on", "turn_off", "toggle", "set_temperature"]
        ),
        ToolParameter(
            name="entity_id",
            type="string",
            description="Entity ID to control (e.g., 'light.living_room', 'climate.bedroom')"
        ),
        ToolParameter(
            name="brightness",
            type="integer",
            description="Brightness percentage (0-100) for lights. Only used with turn_on action.",
            required=False
        ),
        ToolParameter(
            name="temperature",
            type="number",
            description="Target temperature for climate devices. Required when action is 'set_temperature'.",
            required=False
        )
    ]
    
    requires_confirmation = True  # Changing physical devices
    
    def __init__(self):
        self.base_url = settings.home_assistant_url
        self.token = settings.home_assistant_token
        if not self.token:
            raise ValueError("HOME_ASSISTANT_TOKEN not configured")
    
    async def execute(
        self, 
        action: str, 
        entity_id: str,
        brightness: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """Execute Home Assistant control action"""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                service_data = {"entity_id": entity_id}
                
                # Determine domain and service
                domain = entity_id.split(".")[0]
                
                if action == "turn_on":
                    service = "turn_on"
                    if brightness is not None:
                        service_data["brightness_pct"] = brightness
                
                elif action == "turn_off":
                    service = "turn_off"
                
                elif action == "toggle":
                    service = "toggle"
                
                elif action == "set_temperature":
                    if temperature is None:
                        return {
                            "success": False,
                            "error": "temperature is required when action is 'set_temperature'"
                        }
                    domain = "climate"
                    service = "set_temperature"
                    service_data["temperature"] = temperature
                
                else:
                    return {
                        "success": False,
                        "error": f"Invalid action: {action}"
                    }
                
                # Call service
                response = await client.post(
                    f"{self.base_url}/api/services/{domain}/{service}",
                    headers=headers,
                    json=service_data
                )
                response.raise_for_status()
                result = response.json()
                
                return {
                    "success": True,
                    "action": action,
                    "entity_id": entity_id,
                    "result": result
                }
                    
            except httpx.HTTPStatusError as e:
                return {
                    "success": False,
                    "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }
