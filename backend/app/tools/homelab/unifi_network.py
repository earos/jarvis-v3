"""
UniFi Network Tool for JARVIS v3
Manage UniFi network controller - clients, devices, networks, health
"""
import httpx
from typing import Dict, Any, Optional
from datetime import datetime

from app.tools.base import BaseTool, ToolParameter, ToolDomain
from app.config.settings import get_settings

settings = get_settings()


class UniFiNetworkClient:
    """Client for UniFi Network Controller API"""
    
    def __init__(self, host: str, username: str, password: str, site: str = "default"):
        self.base_url = f"https://{host}"
        self.username = username
        self.password = password
        self.site = site
        self.cookies = {}
        self.cookie_expiry = 0
        self.csrf_token = None
    
    async def login(self) -> bool:
        """Authenticate with UniFi controller"""
        # Check if existing cookies are still valid
        if self.cookies and datetime.now().timestamp() < self.cookie_expiry:
            return True
        
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/auth/login",
                    json={"username": self.username, "password": self.password}
                )
                
                if response.status_code == 200:
                    # Extract cookies
                    self.cookies = dict(response.cookies)
                    self.cookie_expiry = datetime.now().timestamp() + 3600  # 1 hour
                    
                    # Extract CSRF token if present
                    if "csrf_token" in self.cookies:
                        self.csrf_token = self.cookies["csrf_token"]
                    
                    return True
                return False
            except Exception as e:
                print(f"UniFi login error: {e}")
                return False
    
    async def request(self, method: str, path: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request to UniFi API"""
        if not await self.login():
            return {"error": "Authentication failed"}
        
        async with httpx.AsyncClient(verify=False, timeout=10.0, cookies=self.cookies) as client:
            try:
                headers = {}
                if self.csrf_token and method != "GET":
                    headers["X-CSRF-Token"] = self.csrf_token
                
                if method == "GET":
                    response = await client.get(f"{self.base_url}{path}", headers=headers)
                elif method == "POST":
                    response = await client.post(f"{self.base_url}{path}", json=data, headers=headers)
                else:
                    return {"error": f"Unsupported method: {method}"}
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"HTTP {response.status_code}: {response.text[:200]}"}
            except Exception as e:
                return {"error": str(e)}
    
    async def get_clients(self) -> Dict[str, Any]:
        """Get all connected network clients"""
        result = await self.request("GET", f"/proxy/network/api/s/{self.site}/stat/sta")
        
        if "error" in result:
            return result
        
        if "data" not in result:
            return {"error": "Invalid response format"}
        
        clients = result["data"]
        
        # Format response
        return {
            "total": len(clients),
            "wired": len([c for c in clients if c.get("is_wired")]),
            "wireless": len([c for c in clients if not c.get("is_wired")]),
            "top_clients": sorted(
                clients,
                key=lambda c: (c.get("tx_bytes", 0) + c.get("rx_bytes", 0)),
                reverse=True
            )[:5]
        }
    
    async def get_devices(self) -> Dict[str, Any]:
        """Get all UniFi network devices"""
        result = await self.request("GET", f"/proxy/network/api/s/{self.site}/stat/device")
        
        if "error" in result:
            return result
        
        if "data" not in result:
            return {"error": "Invalid response format"}
        
        devices = result["data"]
        
        # Format devices
        formatted_devices = []
        for d in devices:
            formatted_devices.append({
                "name": d.get("name") or d.get("model"),
                "model": d.get("model"),
                "type": d.get("type"),
                "ip": d.get("ip"),
                "mac": d.get("mac"),
                "status": "online" if d.get("state") == 1 else "offline",
                "firmware": d.get("version", "unknown"),
                "upgrade_available": d.get("upgradable", False),
                "upgrade_to": d.get("upgrade_to_firmware"),
                "uptime_hours": d.get("uptime", 0) // 3600,
                "clients": d.get("num_sta", 0)
            })
        
        # Firmware summary
        upgradable = [d for d in devices if d.get("upgradable")]
        firmware_summary = {
            "up_to_date": len(devices) - len(upgradable),
            "updates_available": len(upgradable),
            "devices_needing_update": [
                {
                    "name": d.get("name") or d.get("model"),
                    "current": d.get("version"),
                    "available": d.get("upgrade_to_firmware")
                }
                for d in upgradable
            ]
        }
        
        return {
            "total": len(devices),
            "devices": formatted_devices,
            "firmware_summary": firmware_summary
        }
    
    async def get_health(self) -> Dict[str, Any]:
        """Get network health status"""
        result = await self.request("GET", f"/proxy/network/api/s/{self.site}/stat/health")
        
        if "error" in result:
            return result
        
        if "data" not in result:
            return {"error": "Invalid response format"}
        
        health = result["data"]
        
        return {
            "overall": "healthy" if all(h.get("status") == "ok" for h in health) else "degraded",
            "wan": next((h for h in health if h.get("subsystem") == "wan"), None),
            "wlan": next((h for h in health if h.get("subsystem") == "wlan"), None),
            "lan": next((h for h in health if h.get("subsystem") == "lan"), None)
        }
    
    async def get_networks(self) -> Dict[str, Any]:
        """Get configured networks"""
        result = await self.request("GET", f"/proxy/network/api/s/{self.site}/rest/networkconf")
        
        if "error" in result:
            return result
        
        if "data" not in result:
            return {"error": "Invalid response format"}
        
        networks = result["data"]
        
        return {
            "networks": [
                {
                    "name": n.get("name"),
                    "purpose": n.get("purpose"),
                    "vlan": n.get("vlan", "untagged"),
                    "subnet": n.get("ip_subnet"),
                    "id": n.get("_id")
                }
                for n in networks
            ]
        }
    
    async def get_security_analysis(self) -> Dict[str, Any]:
        """Analyze network for security issues"""
        devices = await self.get_devices()
        
        if "error" in devices:
            return devices
        
        issues = []
        
        # Check for firmware updates
        updates_available = devices["firmware_summary"]["updates_available"]
        if updates_available > 0:
            issues.append({
                "severity": "medium",
                "issue": f"{updates_available} device(s) have firmware updates available"
            })
        
        return {
            "summary": "No critical issues" if len(issues) == 0 else f"{len(issues)} issue(s)",
            "issues": issues,
            "devices_checked": devices["total"]
        }
    
    async def create_network(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new network"""
        network_data = {
            "name": config["name"],
            "purpose": config.get("purpose", "corporate"),
            "vlan": config["vlan"],
            "ip_subnet": config["subnet"],
            "dhcpd_enabled": True,
            "dhcpd_start": config.get("dhcp_start"),
            "dhcpd_stop": config.get("dhcp_stop")
        }
        
        result = await self.request("POST", f"/proxy/network/api/s/{self.site}/rest/networkconf", network_data)
        
        if "error" in result:
            return result
        
        return {
            "success": True,
            "message": f"Network {config['name']} created"
        }
    
    async def restart_device(self, mac: str) -> Dict[str, Any]:
        """Restart a UniFi device"""
        result = await self.request(
            "POST",
            f"/proxy/network/api/s/{self.site}/cmd/devmgr",
            {"cmd": "restart", "mac": mac.lower()}
        )
        
        if "error" in result:
            return result
        
        return {
            "success": True,
            "message": f"Restart initiated for {mac}"
        }


class UniFiNetworkTool(BaseTool):
    """Manage UniFi Network Controller - query and manage network devices, clients, and health"""
    
    name = "unifi_network"
    description = """Control UniFi Network Controller. Actions:
- 'clients': List all connected network clients (wired/wireless)
- 'devices': List all UniFi devices (APs, switches, gateways) with firmware status
- 'health': Check network health (WAN, WLAN, LAN status)
- 'networks': List configured networks and VLANs
- 'security': Analyze network for security issues
- 'create_network': Create a new network (requires network_config)
- 'restart_device': Restart a UniFi device (requires mac address)"""
    
    domain = ToolDomain.HOMELAB
    
    parameters = [
        ToolParameter(
            name="action",
            type="string",
            enum=["clients", "devices", "health", "networks", "security", "create_network", "restart_device"],
            description="Action to perform"
        ),
        ToolParameter(
            name="mac",
            type="string",
            description="MAC address (for restart_device action)",
            required=False
        ),
        ToolParameter(
            name="network_config",
            type="object",
            description="Network configuration (for create_network action). Must include: name, vlan, subnet",
            required=False
        )
    ]
    
    def __init__(self):
        self.client = UniFiNetworkClient(
            host=settings.unifi_host,
            username=settings.unifi_username,
            password=settings.unifi_password,
            site=settings.unifi_site
        )
    
    async def execute(self, action: str, mac: Optional[str] = None, network_config: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute UniFi Network action"""
        try:
            if action == "clients":
                return await self.client.get_clients()
            
            elif action == "devices":
                return await self.client.get_devices()
            
            elif action == "health":
                return await self.client.get_health()
            
            elif action == "networks":
                return await self.client.get_networks()
            
            elif action == "security":
                return await self.client.get_security_analysis()
            
            elif action == "create_network":
                if not network_config:
                    return {"error": "network_config is required for create_network"}
                return await self.client.create_network(network_config)
            
            elif action == "restart_device":
                if not mac:
                    return {"error": "mac is required for restart_device"}
                return await self.client.restart_device(mac)
            
            else:
                return {"error": f"Unknown action: {action}"}
        
        except Exception as e:
            return {"error": str(e)}
