"""
Home Assistant Tool for JARVIS v3
Query and control Home Assistant devices and entities
"""
import httpx
from typing import Dict, Any, Optional, List

from app.tools.base import BaseTool, ToolParameter, ToolDomain
from app.config.settings import get_settings

settings = get_settings()


class QueryHomeAssistantTool(BaseTool):
    """Query Home Assistant for entity states and information"""
    
    name = "query_home_assistant"
    description = """Query Home Assistant for device and sensor information. Use this to check the state of lights, switches, sensors, climate controls, and other entities. Can list entities by domain (light, switch, sensor, etc.) or query specific entities."""
    
    domain = ToolDomain.HOMELAB
    
    parameters = [
        ToolParameter(
            name="info_type",
            type="string",
            description="Type of query: domains (list available domains), list (list entities in a domain), entity (get specific entity state)",
            enum=["domains", "list", "entity"]
        ),
        ToolParameter(
            name="domain_filter",
            type="string",
            description="Domain to filter by (e.g., light, switch, sensor, climate, binary_sensor). Required for list info_type.",
            required=False
        ),
        ToolParameter(
            name="entity_id",
            type="string",
            description="Entity ID to query (e.g., light.living_room, sensor.temperature). Required when info_type is entity.",
            required=False
        )
    ]
    
    def __init__(self):
        self.base_url = settings.home_assistant_url
        self.token = settings.home_assistant_token
        if not self.token:
            raise ValueError("HOME_ASSISTANT_TOKEN not configured")
    
    async def execute(self, info_type: str, domain_filter: Optional[str] = None, entity_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute Home Assistant query"""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                if info_type == "domains":
                    # Get all states and extract unique domains
                    response = await client.get(
                        f"{self.base_url}/api/states",
                        headers=headers
                    )
                    response.raise_for_status()
                    states = response.json()
                    
                    # Count entities per domain
                    domain_counts = {}
                    for state in states:
                        entity_domain = state["entity_id"].split(".")[0]
                        domain_counts[entity_domain] = domain_counts.get(entity_domain, 0) + 1
                    
                    return {
                        "success": True,
                        "info_type": "domains",
                        "total_entities": len(states),
                        "domains": dict(sorted(domain_counts.items(), key=lambda x: -x[1]))
                    }
                
                elif info_type == "list":
                    if not domain_filter:
                        return {
                            "success": False,
                            "error": "domain_filter is required when info_type is list. Use info_type=domains to see available domains."
                        }
                    
                    response = await client.get(
                        f"{self.base_url}/api/states",
                        headers=headers
                    )
                    response.raise_for_status()
                    states = response.json()
                    
                    # Filter by domain and return simplified info
                    filtered = []
                    for state in states:
                        if state["entity_id"].startswith(f"{domain_filter}."):
                            filtered.append({
                                "entity_id": state["entity_id"],
                                "state": state["state"],
                                "name": state.get("attributes", {}).get("friendly_name", state["entity_id"])
                            })
                    
                    return {
                        "success": True,
                        "info_type": "list",
                        "domain": domain_filter,
                        "count": len(filtered),
                        "entities": filtered[:100]  # Limit to 100 entities
                    }
                
                elif info_type == "entity":
                    if not entity_id:
                        return {
                            "success": False,
                            "error": "entity_id is required when info_type is entity"
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
                        "state": state["state"],
                        "attributes": state.get("attributes", {}),
                        "last_changed": state.get("last_changed"),
                        "last_updated": state.get("last_updated")
                    }
                
                else:
                    return {
                        "success": False,
                        "error": f"Invalid info_type: {info_type}. Use domains, list, or entity."
                    }
                    
            except httpx.HTTPStatusError as e:
                return {
                    "success": False,
                    "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Error: {str(e)}"
                }


class ManageHomeAssistantTool(BaseTool):
    """Control Home Assistant devices"""
    
    name = "manage_home_assistant"
    description = """Control Home Assistant devices and entities. Turn lights on/off, adjust thermostats, toggle switches, etc."""
    
    domain = ToolDomain.HOMELAB
    
    parameters = [
        ToolParameter(
            name="action",
            type="string",
            description="Action to perform",
            enum=["turn_on", "turn_off", "toggle", "set_value"]
        ),
        ToolParameter(
            name="entity_id",
            type="string",
            description="Entity ID to control (e.g., light.living_room, switch.fan)",
            required=True
        ),
        ToolParameter(
            name="value",
            type="string",
            description="Value to set (for set_value action, e.g., brightness, temperature)",
            required=False
        )
    ]
    
    def __init__(self):
        self.base_url = settings.home_assistant_url
        self.token = settings.home_assistant_token
        if not self.token:
            raise ValueError("HOME_ASSISTANT_TOKEN not configured")
    
    async def execute(self, action: str, entity_id: str, value: Optional[str] = None) -> Dict[str, Any]:
        """Execute Home Assistant control action"""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        # Determine the domain and service
        domain = entity_id.split(".")[0]
        
        service_map = {
            "turn_on": "turn_on",
            "turn_off": "turn_off",
            "toggle": "toggle"
        }
        
        if action in service_map:
            service = service_map[action]
        elif action == "set_value":
            service = "turn_on"  # Most set_value operations use turn_on with data
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
        
        # Build service data
        data = {"entity_id": entity_id}
        
        if value and action == "set_value":
            # Try to parse as number
            try:
                if "." in value:
                    data["brightness"] = int(float(value) * 255 / 100)  # Assume percentage
                else:
                    data["brightness"] = int(value)
            except ValueError:
                data["value"] = value
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/services/{domain}/{service}",
                    headers=headers,
                    json=data
                )
                response.raise_for_status()
                
                return {
                    "success": True,
                    "action": action,
                    "entity_id": entity_id,
                    "message": f"Successfully executed {action} on {entity_id}"
                }
                
            except httpx.HTTPStatusError as e:
                return {
                    "success": False,
                    "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Error: {str(e)}"
                }
