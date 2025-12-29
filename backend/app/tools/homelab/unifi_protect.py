"""
UniFi Protect Tool for JARVIS v3
Manage UniFi Protect - cameras, doorbell, events, NVR, automations
"""
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.tools.base import BaseTool, ToolParameter, ToolDomain
from app.config.settings import get_settings

settings = get_settings()


class UniFiProtectClient:
    """Client for UniFi Protect API"""
    
    def __init__(self, host: str, username: str, password: str):
        self.host = host
        self.base_url = f"https://{host}"
        self.username = username
        self.password = password
        self.token = None
        self.csrf_token = None
        self.token_expiry = 0
    
    async def login(self) -> bool:
        """Authenticate with UniFi Protect"""
        # Check if existing token is still valid
        if self.token and datetime.now().timestamp() < self.token_expiry:
            return True
        
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/auth/login",
                    json={"username": self.username, "password": self.password}
                )
                
                if response.status_code == 200:
                    # Extract token from cookies
                    if "TOKEN" in response.cookies:
                        self.token = response.cookies["TOKEN"]
                        self.token_expiry = datetime.now().timestamp() + 3600  # 1 hour
                    
                    # Extract CSRF token from headers
                    if "x-csrf-token" in response.headers:
                        self.csrf_token = response.headers["x-csrf-token"]
                    
                    return True
                return False
            except Exception as e:
                print(f"UniFi Protect login error: {e}")
                return False
    
    async def request(self, path: str, method: str = "GET", data: Optional[Dict] = None) -> Any:
        """Make authenticated request to Protect API"""
        if not await self.login():
            return {"error": "Authentication failed"}
        
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            try:
                headers = {
                    "Cookie": f"TOKEN={self.token}"
                }
                
                if self.csrf_token:
                    headers["X-CSRF-Token"] = self.csrf_token
                
                url = f"{self.base_url}/proxy/protect{path}"
                
                if method == "GET":
                    response = await client.get(url, headers=headers)
                elif method == "POST":
                    response = await client.post(url, json=data, headers=headers)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    return {"error": f"Unsupported method: {method}"}
                
                if response.status_code in [200, 201]:
                    return response.json()
                else:
                    return {"error": f"HTTP {response.status_code}: {response.text[:200]}"}
            except Exception as e:
                return {"error": str(e)}
    
    async def get_cameras(self) -> List[Dict[str, Any]]:
        """Get all cameras"""
        bootstrap = await self.request("/api/bootstrap")
        
        if isinstance(bootstrap, dict) and "error" in bootstrap:
            return bootstrap
        
        cameras = bootstrap.get("cameras", [])
        
        return [
            {
                "id": c.get("id"),
                "name": c.get("name"),
                "type": c.get("type"),
                "model": c.get("model"),
                "state": c.get("state"),
                "isConnected": c.get("isConnected"),
                "lastMotion": c.get("lastMotion"),
                "lastRing": c.get("lastRing"),
                "mac": c.get("mac"),
                "firmwareVersion": c.get("firmwareVersion")
            }
            for c in cameras
        ]
    
    async def get_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent events"""
        events = await self.request(f"/api/events?limit={limit}")
        
        if isinstance(events, dict) and "error" in events:
            return events
        
        return [
            {
                "id": e.get("id"),
                "type": e.get("type"),
                "camera": e.get("camera"),
                "start": e.get("start"),
                "end": e.get("end"),
                "smartDetectTypes": e.get("smartDetectTypes", []),
                "score": e.get("score")
            }
            for e in events[:limit]
        ]
    
    async def get_nvr(self) -> Dict[str, Any]:
        """Get NVR information"""
        bootstrap = await self.request("/api/bootstrap")
        
        if isinstance(bootstrap, dict) and "error" in bootstrap:
            return bootstrap
        
        nvr = bootstrap.get("nvr", {})
        
        storage_info = nvr.get("storageInfo", {})
        storage_used_gb = (storage_info.get("used", 0) / 1024 / 1024 / 1024)
        storage_total_gb = (storage_info.get("totalSize", 0) / 1024 / 1024 / 1024)
        
        return {
            "name": nvr.get("name"),
            "version": nvr.get("version"),
            "firmwareVersion": nvr.get("firmwareVersion"),
            "uptime": nvr.get("uptime"),
            "uptime_hours": nvr.get("uptime", 0) // 3600,
            "storageUsedGB": round(storage_used_gb, 2),
            "storageTotalGB": round(storage_total_gb, 2),
            "storageUsedPercent": round((storage_used_gb / storage_total_gb * 100) if storage_total_gb > 0 else 0, 1),
            "isRecording": nvr.get("isRecording"),
            "canAutoUpdate": nvr.get("canAutoUpdate")
        }
    
    async def get_doorbell_camera(self) -> Dict[str, Any]:
        """Get doorbell camera specifically"""
        cameras = await self.get_cameras()
        
        if isinstance(cameras, dict) and "error" in cameras:
            return cameras
        
        # Find doorbell
        doorbell = None
        for c in cameras:
            if c.get("type") == "doorbell" or "doorbell" in c.get("name", "").lower():
                doorbell = c
                break
        
        if not doorbell:
            return {"error": "No doorbell camera found"}
        
        return doorbell
    
    async def list_automations(self) -> List[Dict[str, Any]]:
        """List all automations (webhooks)"""
        automations = await self.request("/api/automations")
        
        if isinstance(automations, dict) and "error" in automations:
            return automations
        
        # Filter for JARVIS automations
        jarvis_automations = [a for a in automations if "JARVIS" in a.get("name", "")]
        
        return [
            {
                "id": a.get("id"),
                "name": a.get("name"),
                "enabled": a.get("enable"),
                "trigger": a.get("conditions", [{}])[0].get("condition", {}).get("source"),
                "url": a.get("actions", [{}])[0].get("metadata", {}).get("url"),
                "lastExecuted": a.get("status", {}).get("lastExecutedAt"),
                "totalExecutions": a.get("status", {}).get("total", 0)
            }
            for a in jarvis_automations
        ]
    
    async def create_automation(self, trigger: str, camera_mac: Optional[str] = None) -> Dict[str, Any]:
        """Create a new automation webhook"""
        camera_mac = camera_mac or "7845583FBF15"  # Default to front door
        
        trigger_names = {
            "ring": "Doorbell Alert",
            "person": "Person Detection",
            "vehicle": "Vehicle Detection",
            "animal": "Animal Detection",
            "face_of_interest": "Face Recognition"
        }
        
        automation_data = {
            "name": f"JARVIS {trigger_names.get(trigger, trigger)}",
            "enable": True,
            "sources": [{"device": camera_mac, "type": "include"}],
            "conditions": [{"condition": {"type": "is", "source": trigger}}],
            "schedules": [],
            "actions": [{
                "type": "HTTP_REQUEST",
                "metadata": {
                    "url": "http://192.168.10.100:3939/api/webhook/protect",
                    "method": "POST"
                },
                "order": -1
            }]
        }
        
        result = await self.request("/api/automations", "POST", automation_data)
        
        if isinstance(result, dict) and "error" in result:
            return result
        
        return {
            "success": True,
            "id": result.get("id"),
            "name": result.get("name")
        }
    
    async def delete_automation(self, automation_id: str) -> Dict[str, Any]:
        """Delete an automation"""
        result = await self.request(f"/api/automations/{automation_id}", "DELETE")
        
        if isinstance(result, dict) and "error" in result:
            return result
        
        return {
            "success": True,
            "deleted": automation_id
        }


class UniFiProtectQueryTool(BaseTool):
    """Query UniFi Protect for camera information, events, and system status"""
    
    name = "unifi_protect_query"
    description = """Query UniFi Protect system. Actions:
- 'cameras': List all cameras with status and last activity
- 'events': Get recent motion/detection events (last 10)
- 'nvr': Get NVR status (storage, uptime, recording status)
- 'doorbell': Get doorbell camera specific info (rings, motion, connection)"""
    
    domain = ToolDomain.HOMELAB
    
    parameters = [
        ToolParameter(
            name="action",
            type="string",
            enum=["cameras", "events", "nvr", "doorbell"],
            description="Type of information to retrieve"
        )
    ]
    
    def __init__(self):
        self.client = UniFiProtectClient(
            host=settings.protect_host,
            username=settings.protect_username,
            password=settings.protect_password
        )
    
    async def execute(self, action: str) -> Dict[str, Any]:
        """Execute Protect query action"""
        try:
            if action == "cameras":
                cameras = await self.client.get_cameras()
                if isinstance(cameras, dict) and "error" in cameras:
                    return cameras
                
                # Format for readability
                return {
                    "total": len(cameras),
                    "cameras": [
                        {
                            "name": c.get("name"),
                            "type": c.get("type"),
                            "state": c.get("state"),
                            "isConnected": c.get("isConnected"),
                            "lastMotion": datetime.fromtimestamp(c.get("lastMotion", 0) / 1000).isoformat() if c.get("lastMotion") else None,
                            "lastRing": datetime.fromtimestamp(c.get("lastRing", 0) / 1000).isoformat() if c.get("lastRing") else None
                        }
                        for c in cameras
                    ]
                }
            
            elif action == "events":
                events = await self.client.get_events(10)
                if isinstance(events, dict) and "error" in events:
                    return events
                
                # Format events
                return {
                    "total": len(events),
                    "events": [
                        {
                            "type": e.get("type"),
                            "camera": e.get("camera"),
                            "timestamp": datetime.fromtimestamp(e.get("start", 0) / 1000).isoformat() if e.get("start") else None,
                            "smartDetectTypes": e.get("smartDetectTypes", [])
                        }
                        for e in events
                    ]
                }
            
            elif action == "nvr":
                return await self.client.get_nvr()
            
            elif action == "doorbell":
                doorbell = await self.client.get_doorbell_camera()
                if isinstance(doorbell, dict) and "error" in doorbell:
                    return doorbell
                
                # Format doorbell info
                return {
                    "name": doorbell.get("name"),
                    "type": doorbell.get("type"),
                    "isConnected": doorbell.get("isConnected"),
                    "lastRing": datetime.fromtimestamp(doorbell.get("lastRing", 0) / 1000).isoformat() if doorbell.get("lastRing") else "Never",
                    "lastMotion": datetime.fromtimestamp(doorbell.get("lastMotion", 0) / 1000).isoformat() if doorbell.get("lastMotion") else None,
                    "state": doorbell.get("state")
                }
            
            else:
                return {"error": f"Unknown action: {action}"}
        
        except Exception as e:
            return {"error": str(e)}


class UniFiProtectAutomationTool(BaseTool):
    """Manage UniFi Protect automations (webhooks for doorbell, motion, smart detection)"""
    
    name = "unifi_protect_automation"
    description = """Manage UniFi Protect automations/webhooks. Actions:
- 'list': List all JARVIS automations with status and execution count
- 'create': Create new automation webhook (requires trigger type)
- 'delete': Delete an automation (requires automation_id)

Triggers: ring, person, vehicle, animal, face_of_interest"""
    
    domain = ToolDomain.HOMELAB
    
    parameters = [
        ToolParameter(
            name="action",
            type="string",
            enum=["list", "create", "delete"],
            description="Action to perform"
        ),
        ToolParameter(
            name="trigger",
            type="string",
            enum=["ring", "person", "vehicle", "animal", "face_of_interest"],
            description="Trigger type (for create action)",
            required=False
        ),
        ToolParameter(
            name="camera_mac",
            type="string",
            description="Camera MAC address (for create action, optional - defaults to front door)",
            required=False
        ),
        ToolParameter(
            name="automation_id",
            type="string",
            description="Automation ID (for delete action)",
            required=False
        )
    ]
    
    def __init__(self):
        self.client = UniFiProtectClient(
            host=settings.protect_host,
            username=settings.protect_username,
            password=settings.protect_password
        )
    
    async def execute(
        self,
        action: str,
        trigger: Optional[str] = None,
        camera_mac: Optional[str] = None,
        automation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute Protect automation action"""
        try:
            if action == "list":
                automations = await self.client.list_automations()
                if isinstance(automations, dict) and "error" in automations:
                    return automations
                
                # Format automation list
                return {
                    "total": len(automations),
                    "automations": [
                        {
                            "id": a.get("id"),
                            "name": a.get("name"),
                            "enabled": a.get("enabled"),
                            "trigger": a.get("trigger"),
                            "url": a.get("url"),
                            "lastExecuted": datetime.fromtimestamp(a.get("lastExecuted", 0) / 1000).isoformat() if a.get("lastExecuted") else "Never",
                            "totalExecutions": a.get("totalExecutions", 0)
                        }
                        for a in automations
                    ]
                }
            
            elif action == "create":
                if not trigger:
                    return {"error": "trigger is required for create action"}
                
                return await self.client.create_automation(trigger, camera_mac)
            
            elif action == "delete":
                if not automation_id:
                    return {"error": "automation_id is required for delete action"}
                
                return await self.client.delete_automation(automation_id)
            
            else:
                return {"error": f"Unknown action: {action}"}
        
        except Exception as e:
            return {"error": str(e)}


class UniFiProtectWebhookTool(BaseTool):
    """Get webhook configuration and setup instructions for UniFi Protect"""
    
    name = "unifi_protect_webhook"
    description = """Get webhook setup information. Actions:
- 'instructions': Get step-by-step setup guide for Protect webhooks
- 'status': Get current webhook endpoint status and features"""
    
    domain = ToolDomain.HOMELAB
    
    parameters = [
        ToolParameter(
            name="action",
            type="string",
            enum=["instructions", "status"],
            description="What information to retrieve"
        )
    ]
    
    async def execute(self, action: str) -> Dict[str, Any]:
        """Execute webhook config action"""
        jarvis_host = "192.168.10.100:3939"
        
        if action == "instructions":
            return {
                "title": "UniFi Protect Webhook Setup",
                "steps": [
                    "1. Open UniFi Protect web UI (https://192.168.20.250)",
                    "2. Go to Settings → Alarm Manager",
                    "3. Click Add Alarm",
                    "4. For doorbell alerts:",
                    "   - Trigger: Select Doorbell Ring",
                    "   - Cameras: Select Front Door",
                    "   - Action: Webhook",
                    f"   - URL: http://{jarvis_host}/api/webhook/protect",
                    "5. For person detection alerts:",
                    "   - Trigger: Select Smart Detection → Person",
                    "   - Cameras: Select your cameras",
                    "   - Action: Webhook",
                    f"   - URL: http://{jarvis_host}/api/webhook/protect",
                    "6. Save the alarm configuration"
                ],
                "webhookUrl": f"http://{jarvis_host}/api/webhook/protect",
                "note": "Webhooks will trigger JARVIS to show camera feeds and announce visitors automatically"
            }
        
        elif action == "status":
            return {
                "webhookEndpoint": f"http://{jarvis_host}/api/webhook/protect",
                "status": "active",
                "features": [
                    "Doorbell ring detection",
                    "Person smart detection",
                    "Face recognition announcements",
                    "Auto camera popup",
                    "Voice announcements"
                ]
            }
        
        else:
            return {"error": f"Unknown action: {action}"}
