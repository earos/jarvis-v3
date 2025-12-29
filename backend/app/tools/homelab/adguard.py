"""
AdGuard Home Tool for JARVIS v3
Query AdGuard Home for DNS stats, blocked queries, and filtering status
"""
import httpx
from typing import Dict, Any
from base64 import b64encode

from app.tools.base import BaseTool, ToolParameter, ToolDomain
from app.config.settings import get_settings

settings = get_settings()


class AdGuardTool(BaseTool):
    """Query AdGuard Home for DNS statistics and filtering status"""
    
    name = "adguard"
    description = """Get DNS filtering statistics from AdGuard Home. Shows blocked queries, top blocked domains, top clients, and protection status.
Use this to check DNS filtering effectiveness and identify blocked domains/clients."""
    
    domain = ToolDomain.HOMELAB
    
    parameters = [
        ToolParameter(
            name="action",
            type="string",
            description="Action to perform: 'status' (general info), 'stats' (query statistics), 'top_blocked' (top blocked domains), 'top_clients' (most active clients), 'toggle_protection' (enable/disable protection)",
            required=True,
            enum=["status", "stats", "top_blocked", "top_clients", "toggle_protection"]
        )
    ]
    
    def __init__(self):
        self.base_url = settings.adguard_url.rstrip('/')
        self.username = settings.adguard_user
        self.password = settings.adguard_password
        
        # Create basic auth header
        credentials = f"{self.username}:{self.password}"
        encoded = b64encode(credentials.encode()).decode()
        self.auth_header = f"Basic {encoded}"
    
    async def execute(self, action: str) -> Dict[str, Any]:
        """Execute AdGuard Home query based on action"""
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            headers = {"Authorization": self.auth_header}
            
            try:
                if action == "status":
                    return await self._get_status(client, headers)
                elif action == "stats":
                    return await self._get_stats(client, headers)
                elif action == "top_blocked":
                    return await self._get_top_blocked(client, headers)
                elif action == "top_clients":
                    return await self._get_top_clients(client, headers)
                elif action == "toggle_protection":
                    return await self._toggle_protection(client, headers)
                else:
                    return {
                        "success": False,
                        "error": f"Unknown action: {action}"
                    }
                    
            except httpx.HTTPStatusError as e:
                return {
                    "success": False,
                    "error": f"HTTP {e.response.status_code}: {e.response.text}"
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
    
    async def _get_status(self, client: httpx.AsyncClient, headers: Dict[str, str]) -> Dict[str, Any]:
        """Get AdGuard Home general status"""
        response = await client.get(f"{self.base_url}/control/status", headers=headers)
        response.raise_for_status()
        data = response.json()
        
        return {
            "success": True,
            "protection_enabled": data.get("protection_enabled", False),
            "version": data.get("version", "unknown"),
            "dns_port": data.get("dns_port", 53),
            "http_port": data.get("http_port", 80),
            "running": data.get("running", False),
            "filters_updated": data.get("filters_update_timestamp", "unknown")
        }
    
    async def _get_stats(self, client: httpx.AsyncClient, headers: Dict[str, str]) -> Dict[str, Any]:
        """Get DNS query statistics"""
        response = await client.get(f"{self.base_url}/control/stats", headers=headers)
        response.raise_for_status()
        data = response.json()
        
        total = data.get("num_dns_queries", 0)
        blocked = data.get("num_blocked_filtering", 0)
        block_rate = (blocked / total * 100) if total > 0 else 0
        
        return {
            "success": True,
            "summary": f"{total:,} queries, {blocked:,} blocked ({block_rate:.1f}%)",
            "total_queries": total,
            "blocked_queries": blocked,
            "replaced_safebrowsing": data.get("num_replaced_safebrowsing", 0),
            "replaced_parental": data.get("num_replaced_parental", 0),
            "avg_processing_time": data.get("avg_processing_time", 0),
            "block_rate_percent": round(block_rate, 2)
        }
    
    async def _get_top_blocked(self, client: httpx.AsyncClient, headers: Dict[str, str]) -> Dict[str, Any]:
        """Get top blocked domains"""
        response = await client.get(f"{self.base_url}/control/stats", headers=headers)
        response.raise_for_status()
        data = response.json()
        
        blocked_filters = data.get("blocked_filtering", [])
        
        # Convert to list of dicts for better readability
        top_blocked = [
            {"domain": domain, "count": count}
            for domain, count in blocked_filters.items()
        ]
        
        # Sort by count descending
        top_blocked.sort(key=lambda x: x["count"], reverse=True)
        
        return {
            "success": True,
            "top_blocked_domains": top_blocked[:10],  # Top 10
            "total_blocked_domains": len(blocked_filters)
        }
    
    async def _get_top_clients(self, client: httpx.AsyncClient, headers: Dict[str, str]) -> Dict[str, Any]:
        """Get top DNS clients by query count"""
        response = await client.get(f"{self.base_url}/control/stats", headers=headers)
        response.raise_for_status()
        data = response.json()
        
        top_queried_domains = data.get("top_queried_domains", [])
        top_clients_data = data.get("top_clients", [])
        
        # Convert to list of dicts
        top_clients = [
            {"client": client, "queries": count}
            for client, count in top_clients_data.items()
        ]
        
        # Sort by queries descending
        top_clients.sort(key=lambda x: x["queries"], reverse=True)
        
        return {
            "success": True,
            "top_clients": top_clients[:10],  # Top 10
            "total_clients": len(top_clients_data)
        }
    
    async def _toggle_protection(self, client: httpx.AsyncClient, headers: Dict[str, str]) -> Dict[str, Any]:
        """Toggle AdGuard Home protection on/off"""
        # First get current status
        status_response = await client.get(f"{self.base_url}/control/status", headers=headers)
        status_response.raise_for_status()
        status_data = status_response.json()
        
        current_protection = status_data.get("protection_enabled", False)
        new_protection = not current_protection
        
        # Toggle protection
        payload = {"enabled": new_protection}
        response = await client.post(
            f"{self.base_url}/control/protection",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        
        return {
            "success": True,
            "protection_enabled": new_protection,
            "message": f"Protection {'enabled' if new_protection else 'disabled'}"
        }
