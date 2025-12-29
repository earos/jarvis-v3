"""
Starlink Tool for JARVIS v3
Query Starlink satellite internet for connection status, speed, latency, and obstructions
"""
import httpx
from typing import Dict, Any, Optional

from app.tools.base import BaseTool, ToolParameter, ToolDomain
from app.config.settings import get_settings

settings = get_settings()


class StarlinkTool(BaseTool):
    """Query Starlink satellite internet for connection status, speed, latency, and obstructions"""
    
    name = "starlink"
    description = """Query Starlink satellite internet for connection status and metrics. Use for questions about:
- Connection status and uptime
- Current speed (download/upload)
- Latency and ping times
- Obstructions and signal quality
- Service history and statistics"""
    
    domain = ToolDomain.HOMELAB
    
    parameters = [
        ToolParameter(
            name="action",
            type="string",
            description="Action to perform: 'status' (general status), 'speed' (current speeds), 'latency' (ping/latency), 'obstructions' (obstruction data), 'history' (recent statistics)"
        )
    ]
    
    def __init__(self):
        self.base_url = f"http://{settings.starlink_host}"
    
    async def execute(self, action: str) -> Dict[str, Any]:
        """Execute Starlink query"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # Query the Starlink status endpoint
                # The Starlink dish provides a JSON API at /api/status
                response = await client.post(
                    f"{self.base_url}/api/status",
                    json={},
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                data = response.json()
                
                # Extract relevant information based on action
                if action == "status":
                    return self._format_status(data)
                elif action == "speed":
                    return self._format_speed(data)
                elif action == "latency":
                    return self._format_latency(data)
                elif action == "obstructions":
                    return self._format_obstructions(data)
                elif action == "history":
                    return self._format_history(data)
                else:
                    return {
                        "success": False,
                        "error": f"Unknown action: {action}. Valid actions: status, speed, latency, obstructions, history"
                    }
                    
            except httpx.HTTPStatusError as e:
                return {
                    "success": False,
                    "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
                    "action": action
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "action": action
                }
    
    def _format_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format general status information"""
        try:
            status = data.get("status", {})
            device_info = data.get("deviceInfo", {})
            
            return {
                "success": True,
                "action": "status",
                "data": {
                    "state": status.get("state", "unknown"),
                    "uptime": status.get("uptimeS", 0),
                    "uptime_hours": round(status.get("uptimeS", 0) / 3600, 2),
                    "alerts": status.get("alerts", {}),
                    "hardware_version": device_info.get("hardwareVersion", "unknown"),
                    "software_version": device_info.get("softwareVersion", "unknown"),
                    "country_code": device_info.get("countryCode", "unknown")
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to parse status data: {str(e)}"
            }
    
    def _format_speed(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format speed information"""
        try:
            status = data.get("status", {})
            
            return {
                "success": True,
                "action": "speed",
                "data": {
                    "download_mbps": round(status.get("downlinkThroughputBps", 0) / 1_000_000, 2),
                    "upload_mbps": round(status.get("uplinkThroughputBps", 0) / 1_000_000, 2)
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to parse speed data: {str(e)}"
            }
    
    def _format_latency(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format latency information"""
        try:
            status = data.get("status", {})
            
            return {
                "success": True,
                "action": "latency",
                "data": {
                    "ping_ms": round(status.get("popPingLatencyMs", 0), 2),
                    "ping_drop_rate": round(status.get("popPingDropRate", 0) * 100, 2)
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to parse latency data: {str(e)}"
            }
    
    def _format_obstructions(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format obstruction information"""
        try:
            obstruction_stats = data.get("obstructionStats", {})
            
            return {
                "success": True,
                "action": "obstructions",
                "data": {
                    "currently_obstructed": obstruction_stats.get("currentlyObstructed", False),
                    "fraction_obstructed": round(obstruction_stats.get("fractionObstructed", 0) * 100, 2),
                    "time_obstructed": obstruction_stats.get("validS", 0),
                    "wedge_fraction_obstructed": obstruction_stats.get("wedgeFractionObstructed", [])[:10]
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to parse obstruction data: {str(e)}"
            }
    
    def _format_history(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format historical statistics"""
        try:
            status = data.get("status", {})
            
            return {
                "success": True,
                "action": "history",
                "data": {
                    "outage_count": status.get("outages", {}).get("count", 0),
                    "last_24h_outage_duration_s": status.get("outages", {}).get("last24hOutageDurationS", 0),
                    "uptime_s": status.get("uptimeS", 0),
                    "uptime_hours": round(status.get("uptimeS", 0) / 3600, 2)
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to parse history data: {str(e)}"
            }
