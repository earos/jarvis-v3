"""
Portainer Tool for JARVIS v3
Query and manage Docker containers via Portainer
"""
import httpx
from typing import Dict, Any, Optional

from app.tools.base import BaseTool, ToolParameter, ToolDomain
from app.config.settings import get_settings

settings = get_settings()


class QueryPortainerTool(BaseTool):
    """Query Portainer for endpoints and container information"""
    
    name = "query_portainer"
    description = """Query Portainer for Docker container and endpoint information. Use this to check container status, get list of containers, or view available endpoints."""
    
    domain = ToolDomain.HOMELAB
    
    parameters = [
        ToolParameter(
            name="info_type",
            type="string",
            description="Type of information to retrieve",
            enum=["endpoints", "containers"]
        ),
        ToolParameter(
            name="endpoint_id",
            type="integer",
            description="Portainer endpoint ID. Defaults to 3 if not specified.",
            required=False
        )
    ]
    
    def __init__(self):
        self.base_url = settings.portainer_url
        self.api_key = settings.portainer_api_key
        if not self.api_key:
            raise ValueError("PORTAINER_API_KEY not configured")
    
    async def execute(self, info_type: str, endpoint_id: Optional[int] = None) -> Dict[str, Any]:
        """Execute Portainer query"""
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            try:
                if info_type == "endpoints":
                    response = await client.get(
                        f"{self.base_url}/api/endpoints",
                        headers=headers
                    )
                    response.raise_for_status()
                    endpoints = response.json()
                    
                    return {
                        "success": True,
                        "info_type": "endpoints",
                        "endpoint_count": len(endpoints),
                        "endpoints": endpoints
                    }
                
                elif info_type == "containers":
                    eid = endpoint_id if endpoint_id is not None else 3
                    response = await client.get(
                        f"{self.base_url}/api/endpoints/{eid}/docker/containers/json?all=1",
                        headers=headers
                    )
                    response.raise_for_status()
                    containers = response.json()
                    
                    return {
                        "success": True,
                        "info_type": "containers",
                        "endpoint_id": eid,
                        "container_count": len(containers),
                        "containers": containers
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


class ManagePortainerTool(BaseTool):
    """Manage Docker containers via Portainer"""
    
    name = "manage_portainer"
    description = """Control Docker containers via Portainer. Use this to start, stop, or restart containers. This tool performs actions that change container states."""
    
    domain = ToolDomain.HOMELAB
    
    parameters = [
        ToolParameter(
            name="action",
            type="string",
            description="Action to perform on the container",
            enum=["start", "stop", "restart"]
        ),
        ToolParameter(
            name="container_id",
            type="string",
            description="Docker container ID or name to control"
        ),
        ToolParameter(
            name="endpoint_id",
            type="integer",
            description="Portainer endpoint ID. Defaults to 3 if not specified.",
            required=False
        )
    ]
    
    requires_confirmation = True  # Managing containers
    
    def __init__(self):
        self.base_url = settings.portainer_url
        self.api_key = settings.portainer_api_key
        if not self.api_key:
            raise ValueError("PORTAINER_API_KEY not configured")
    
    async def execute(
        self, 
        action: str, 
        container_id: str,
        endpoint_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute Portainer container management action"""
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        eid = endpoint_id if endpoint_id is not None else 3
        
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            try:
                if action == "start":
                    endpoint = f"{self.base_url}/api/endpoints/{eid}/docker/containers/{container_id}/start"
                elif action == "stop":
                    endpoint = f"{self.base_url}/api/endpoints/{eid}/docker/containers/{container_id}/stop"
                elif action == "restart":
                    endpoint = f"{self.base_url}/api/endpoints/{eid}/docker/containers/{container_id}/restart"
                else:
                    return {
                        "success": False,
                        "error": f"Invalid action: {action}"
                    }
                
                response = await client.post(endpoint, headers=headers)
                response.raise_for_status()
                
                # Portainer returns empty response on success
                return {
                    "success": True,
                    "action": action,
                    "container_id": container_id,
                    "endpoint_id": eid,
                    "message": f"Container {action} successful"
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
