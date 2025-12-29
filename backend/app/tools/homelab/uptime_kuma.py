"""
Uptime Kuma Tool for JARVIS v3
Get service health monitoring status from Uptime Kuma
"""
import httpx
from typing import Dict, Any, List

from app.tools.base import BaseTool, ToolParameter, ToolDomain
from app.config.settings import get_settings

settings = get_settings()


class UptimeKumaTool(BaseTool):
    """Query Uptime Kuma for service health monitoring status"""
    
    name = "uptime_kuma"
    description = """Get service health status from Uptime Kuma monitoring. Shows which services are up or down.
Use this to check the health and availability of all monitored services in the homelab."""
    
    domain = ToolDomain.HOMELAB
    
    parameters = []  # No parameters required - returns all services
    
    def __init__(self):
        self.base_url = settings.uptime_kuma_url
    
    async def execute(self) -> Dict[str, Any]:
        """Fetch service health status from Uptime Kuma"""
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            try:
                # Fetch both monitors and heartbeats in parallel
                monitors_response = await client.get(
                    f"{self.base_url}/api/status-page/default"
                )
                heartbeats_response = await client.get(
                    f"{self.base_url}/api/status-page/heartbeat/default"
                )
                
                monitors_response.raise_for_status()
                heartbeats_response.raise_for_status()
                
                monitors_data = monitors_response.json()
                heartbeats_data = heartbeats_response.json()
                
                # Build status map from heartbeats
                status_map = {}
                if heartbeats_data.get("heartbeatList"):
                    for monitor_id, heartbeat_list in heartbeats_data["heartbeatList"].items():
                        if heartbeat_list and len(heartbeat_list) > 0:
                            # Last heartbeat status: 1 = up, 0 = down
                            last_status = heartbeat_list[-1].get("status")
                            status_map[int(monitor_id)] = "up" if last_status == 1 else "down"
                
                # Extract services from monitor groups
                services = []
                if monitors_data.get("publicGroupList"):
                    for group in monitors_data["publicGroupList"]:
                        if group.get("monitorList"):
                            for monitor in group["monitorList"]:
                                services.append({
                                    "name": monitor.get("name"),
                                    "status": status_map.get(monitor.get("id"), "unknown")
                                })
                
                # Calculate summary statistics
                up_count = len([s for s in services if s["status"] == "up"])
                down_count = len([s for s in services if s["status"] == "down"])
                unknown_count = len([s for s in services if s["status"] == "unknown"])
                
                return {
                    "success": True,
                    "summary": f"{up_count} up, {down_count} down, {unknown_count} unknown",
                    "total_services": len(services),
                    "up": up_count,
                    "down": down_count,
                    "unknown": unknown_count,
                    "services": services
                }
                
            except httpx.HTTPStatusError as e:
                return {
                    "success": False,
                    "error": f"HTTP {e.response.status_code}: Failed to fetch from Uptime Kuma"
                }
            except httpx.RequestError as e:
                return {
                    "success": False,
                    "error": f"Connection error: {str(e)}"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Unexpected error: {str(e)}"
                }
