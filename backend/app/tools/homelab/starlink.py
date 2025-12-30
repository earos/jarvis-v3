"""
Starlink Tool for JARVIS v3
Query Starlink satellite internet via gRPC for connection status, speed, latency, and obstructions
"""
from typing import Dict, Any

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
- Device info and software version"""
    
    domain = ToolDomain.HOMELAB
    
    parameters = [
        ToolParameter(
            name="action",
            type="string",
            description="Action to perform: 'status' (connection status, speeds, latency), 'device' (hardware/software info), 'obstructions' (obstruction data)"
        )
    ]
    
    def __init__(self):
        self.host = settings.starlink_host
    
    async def execute(self, action: str) -> Dict[str, Any]:
        """Execute Starlink query via gRPC"""
        try:
            import starlink_grpc
            
            # Create channel context with custom host if not default
            context = None
            if self.host and self.host != "192.168.100.1":
                context = starlink_grpc.ChannelContext(target=self.host)
            
            if action == "status":
                return self._get_status(starlink_grpc, context)
            elif action == "device":
                return self._get_device_info(starlink_grpc, context)
            elif action == "obstructions":
                return self._get_obstructions(starlink_grpc, context)
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}. Valid: status, device, obstructions"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "action": action
            }
    
    def _get_status(self, starlink_grpc, context) -> Dict[str, Any]:
        """Get connection status including speeds and latency"""
        try:
            status, obs, alerts = starlink_grpc.status_data(context=context)
            
            return {
                "success": True,
                "action": "status",
                "data": {
                    "state": status.get("state", "unknown"),
                    "uptime_seconds": status.get("uptime", 0),
                    "uptime_hours": round(status.get("uptime", 0) / 3600, 2),
                    "download_mbps": round(status.get("downlink_throughput_bps", 0) / 1_000_000, 2),
                    "upload_mbps": round(status.get("uplink_throughput_bps", 0) / 1_000_000, 2),
                    "ping_latency_ms": round(status.get("pop_ping_latency_ms", 0), 1),
                    "ping_drop_rate_percent": round(status.get("pop_ping_drop_rate", 0) * 100, 2),
                    "snr": status.get("snr"),
                    "alerts": [k for k, v in alerts.items() if v],
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e), "action": "status"}
    
    def _get_device_info(self, starlink_grpc, context) -> Dict[str, Any]:
        """Get device hardware and software info"""
        try:
            status, obs, alerts = starlink_grpc.status_data(context=context)
            
            return {
                "success": True,
                "action": "device",
                "data": {
                    "device_id": status.get("id", "unknown"),
                    "hardware_version": status.get("hardware_version", "unknown"),
                    "software_version": status.get("software_version", "unknown"),
                    "country_code": status.get("country_code", "unknown"),
                    "utc_offset_s": status.get("utc_offset_s"),
                    "uptime_seconds": status.get("uptime", 0),
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e), "action": "device"}
    
    def _get_obstructions(self, starlink_grpc, context) -> Dict[str, Any]:
        """Get obstruction data"""
        try:
            status, obs, alerts = starlink_grpc.status_data(context=context)
            
            return {
                "success": True,
                "action": "obstructions",
                "data": {
                    "currently_obstructed": obs.get("currently_obstructed", False),
                    "fraction_obstructed_percent": round(obs.get("fraction_obstructed", 0) * 100, 2),
                    "last_24h_obstructed_seconds": obs.get("last_24h_obstructed_s", 0),
                    "valid_seconds": obs.get("valid_s", 0),
                    "wedge_fraction_obstructed": [round(w * 100, 1) for w in obs.get("wedge_fraction_obstructed", [])],
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e), "action": "obstructions"}
