"""
Synology NAS Tool for JARVIS v3
Query Synology DSM for storage, system info, shares, and health
"""
import httpx
from typing import Dict, Any, Optional

from app.tools.base import BaseTool, ToolParameter, ToolDomain
from app.config.settings import get_settings

settings = get_settings()


class SynologyTool(BaseTool):
    """Query Synology NAS for system information and health status"""
    
    name = "synology_nas"
    description = """Query Synology NAS for storage information, system status, shared folders, and health metrics. Use this to check disk usage, system info, available shares, or overall system health."""
    
    domain = ToolDomain.HOMELAB
    
    parameters = [
        ToolParameter(
            name="action",
            type="string",
            description="Type of information to retrieve from Synology NAS",
            enum=["status", "storage", "shares", "system_health"]
        )
    ]
    
    def __init__(self):
        self.host = settings.synology_host
        self.username = settings.synology_user
        self.password = settings.synology_password
        
        if not all([self.host, self.username, self.password]):
            raise ValueError("Synology credentials not fully configured")
        
        self.base_url = f"http://{self.host}:5000"
        self.sid: Optional[str] = None
    
    async def _login(self, client: httpx.AsyncClient) -> bool:
        """Authenticate with Synology DSM API"""
        try:
            response = await client.get(
                f"{self.base_url}/webapi/auth.cgi",
                params={
                    "api": "SYNO.API.Auth",
                    "version": "3",
                    "method": "login",
                    "account": self.username,
                    "passwd": self.password,
                    "session": "FileStation",
                    "format": "sid"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("success"):
                self.sid = data["data"]["sid"]
                return True
            return False
        except Exception:
            return False
    
    async def _logout(self, client: httpx.AsyncClient):
        """Logout from Synology DSM API"""
        if self.sid:
            try:
                await client.get(
                    f"{self.base_url}/webapi/auth.cgi",
                    params={
                        "api": "SYNO.API.Auth",
                        "version": "3",
                        "method": "logout",
                        "session": "FileStation"
                    }
                )
            except Exception:
                pass
    
    async def _get_system_info(self, client: httpx.AsyncClient) -> Dict[str, Any]:
        """Get basic system information"""
        response = await client.get(
            f"{self.base_url}/webapi/entry.cgi",
            params={
                "api": "SYNO.Core.System",
                "version": "3",
                "method": "info",
                "_sid": self.sid
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def _get_storage_info(self, client: httpx.AsyncClient) -> Dict[str, Any]:
        """Get storage volume information"""
        response = await client.get(
            f"{self.base_url}/webapi/entry.cgi",
            params={
                "api": "SYNO.Storage.CGI.Storage",
                "version": "1",
                "method": "load_info",
                "_sid": self.sid
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def _get_shares(self, client: httpx.AsyncClient) -> Dict[str, Any]:
        """Get shared folder list"""
        response = await client.get(
            f"{self.base_url}/webapi/entry.cgi",
            params={
                "api": "SYNO.FileStation.List",
                "version": "2",
                "method": "list_share",
                "additional": "[\"real_path\",\"size\",\"owner\",\"time\"]",
                "_sid": self.sid
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def _get_system_status(self, client: httpx.AsyncClient) -> Dict[str, Any]:
        """Get system utilization status"""
        response = await client.get(
            f"{self.base_url}/webapi/entry.cgi",
            params={
                "api": "SYNO.Core.System.Utilization",
                "version": "1",
                "method": "get",
                "_sid": self.sid
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def execute(self, action: str) -> Dict[str, Any]:
        """Execute Synology NAS query"""
        async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
            try:
                # Login first
                if not await self._login(client):
                    return {
                        "success": False,
                        "error": "Failed to authenticate with Synology NAS"
                    }
                
                result = {"success": True, "action": action}
                
                if action == "status":
                    # Get system info and utilization
                    sys_info = await self._get_system_info(client)
                    sys_status = await self._get_system_status(client)
                    
                    if sys_info.get("success") and sys_status.get("success"):
                        result["system_info"] = sys_info["data"]
                        result["utilization"] = sys_status["data"]
                    else:
                        result["success"] = False
                        result["error"] = "Failed to retrieve system status"
                
                elif action == "storage":
                    # Get storage information
                    storage = await self._get_storage_info(client)
                    
                    if storage.get("success"):
                        result["storage"] = storage["data"]
                    else:
                        result["success"] = False
                        result["error"] = "Failed to retrieve storage info"
                
                elif action == "shares":
                    # Get shared folders
                    shares = await self._get_shares(client)
                    
                    if shares.get("success"):
                        result["shares"] = shares["data"]["shares"]
                        result["share_count"] = len(shares["data"]["shares"])
                    else:
                        result["success"] = False
                        result["error"] = "Failed to retrieve shares"
                
                elif action == "system_health":
                    # Get comprehensive health info
                    sys_info = await self._get_system_info(client)
                    sys_status = await self._get_system_status(client)
                    storage = await self._get_storage_info(client)
                    
                    if all([sys_info.get("success"), sys_status.get("success"), storage.get("success")]):
                        result["system_info"] = sys_info["data"]
                        result["utilization"] = sys_status["data"]
                        result["storage"] = storage["data"]
                    else:
                        result["success"] = False
                        result["error"] = "Failed to retrieve complete health info"
                
                else:
                    result["success"] = False
                    result["error"] = f"Invalid action: {action}"
                
                # Logout
                await self._logout(client)
                
                return result
                
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
