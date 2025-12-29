"""
Proxmox Tool for JARVIS v3
Query and manage Proxmox VMs and containers with token auth
"""
import httpx
from typing import Dict, Any, List, Optional

from app.tools.base import BaseTool, ToolParameter, ToolDomain
from app.config.settings import get_settings

settings = get_settings()


class ProxmoxClient:
    """Shared Proxmox API client with token auth"""
    
    def __init__(self):
        self.base_url = f"https://{settings.proxmox_pve1_host}:8006/api2/json"
        self.token_name = settings.proxmox_token_name
        self.token_value = settings.proxmox_token_value
    
    def _get_headers(self) -> Dict[str, str]:
        """Get auth headers using API token"""
        if self.token_name and self.token_value:
            return {"Authorization": f"PVEAPIToken={self.token_name}={self.token_value}"}
        return {}
    
    async def request(self, client: httpx.AsyncClient, method: str, path: str) -> Optional[Dict]:
        """Make authenticated request to Proxmox API"""
        try:
            response = await client.request(
                method,
                f"{self.base_url}{path}",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}


class ProxmoxQueryTool(BaseTool):
    """Query Proxmox for nodes, VMs, and containers"""
    
    name = "proxmox_query"
    description = """Query Proxmox for infrastructure information:
- nodes: Get all Proxmox nodes with CPU, memory, and uptime
- vms: Get all virtual machines on a specific node
- containers: Get all LXC containers on a specific node  
- all: Get all resources across the cluster (nodes, VMs, containers)"""
    
    domain = ToolDomain.HOMELAB
    
    parameters = [
        ToolParameter(
            name="info_type",
            type="string",
            description="Type of information to query",
            enum=["nodes", "vms", "containers", "all"]
        ),
        ToolParameter(
            name="node",
            type="string",
            description="Node name (pve1, pve2, etc.) - required for vms and containers queries",
            required=False
        )
    ]
    
    def __init__(self):
        if not settings.proxmox_token_name or not settings.proxmox_token_value:
            raise ValueError("PROXMOX_TOKEN_NAME and PROXMOX_TOKEN_VALUE not configured")
        self.client = ProxmoxClient()
    
    async def execute(self, info_type: str, node: Optional[str] = None) -> Dict[str, Any]:
        """Execute Proxmox query"""
        async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
            try:
                if info_type == "nodes":
                    return await self._get_nodes(client)
                elif info_type == "vms":
                    if not node:
                        return {"success": False, "error": "node parameter required for vms query"}
                    return await self._get_vms(client, node)
                elif info_type == "containers":
                    if not node:
                        return {"success": False, "error": "node parameter required for containers query"}
                    return await self._get_containers(client, node)
                elif info_type == "all":
                    return await self._get_all_resources(client)
                else:
                    return {"success": False, "error": f"Invalid info_type: {info_type}"}
                    
            except Exception as e:
                return {"success": False, "error": f"Proxmox query failed: {str(e)}"}
    
    async def _get_nodes(self, client: httpx.AsyncClient) -> Dict[str, Any]:
        """Get all Proxmox nodes"""
        result = await self.client.request(client, "GET", "/nodes")
        if not result or result.get("error") or not result.get("data"):
            return {"success": False, "error": result.get("error", "Failed to fetch nodes")}
        
        nodes = []
        for node in result["data"]:
            nodes.append({
                "name": node.get("node"),
                "status": node.get("status"),
                "cpu": f"{(node.get('cpu', 0) * 100):.1f}%",
                "memory_used": f"{round(node.get('mem', 0) / 1024 / 1024 / 1024)}GB",
                "memory_total": f"{round(node.get('maxmem', 0) / 1024 / 1024 / 1024)}GB",
                "memory_percent": f"{(node.get('mem', 0) / node.get('maxmem', 1) * 100):.1f}%",
                "uptime_hours": node.get("uptime", 0) // 3600
            })
        
        return {"success": True, "nodes": nodes}
    
    async def _get_vms(self, client: httpx.AsyncClient, node: str) -> Dict[str, Any]:
        """Get VMs on a specific node"""
        result = await self.client.request(client, "GET", f"/nodes/{node}/qemu")
        if not result or result.get("error") or not result.get("data"):
            return {"success": False, "error": result.get("error", f"Failed to fetch VMs for node {node}")}
        
        vms = []
        for vm in result["data"]:
            vms.append({
                "vmid": vm.get("vmid"),
                "name": vm.get("name"),
                "status": vm.get("status"),
                "cpu": f"{(vm.get('cpu', 0) * 100):.1f}%",
                "memory_used": f"{round(vm.get('mem', 0) / 1024 / 1024 / 1024)}GB",
                "memory_max": f"{round(vm.get('maxmem', 0) / 1024 / 1024 / 1024)}GB",
                "uptime_hours": vm.get("uptime", 0) // 3600
            })
        
        return {"success": True, "node": node, "vms": vms}
    
    async def _get_containers(self, client: httpx.AsyncClient, node: str) -> Dict[str, Any]:
        """Get LXC containers on a specific node"""
        result = await self.client.request(client, "GET", f"/nodes/{node}/lxc")
        if not result or result.get("error") or not result.get("data"):
            return {"success": False, "error": result.get("error", f"Failed to fetch containers for node {node}")}
        
        containers = []
        for ct in result["data"]:
            containers.append({
                "vmid": ct.get("vmid"),
                "name": ct.get("name"),
                "status": ct.get("status"),
                "cpu": f"{(ct.get('cpu', 0) * 100):.1f}%",
                "memory_used": f"{round(ct.get('mem', 0) / 1024 / 1024)}MB",
                "memory_max": f"{round(ct.get('maxmem', 0) / 1024 / 1024 / 1024)}GB",
                "uptime_hours": ct.get("uptime", 0) // 3600
            })
        
        return {"success": True, "node": node, "containers": containers}
    
    async def _get_all_resources(self, client: httpx.AsyncClient) -> Dict[str, Any]:
        """Get all resources across the cluster"""
        result = await self.client.request(client, "GET", "/cluster/resources")
        if not result or result.get("error") or not result.get("data"):
            return {"success": False, "error": result.get("error", "Failed to fetch cluster resources")}
        
        resources = result["data"]
        nodes = []
        vms = []
        containers = []
        
        for resource in resources:
            res_type = resource.get("type")
            
            if res_type == "node":
                nodes.append({
                    "name": resource.get("node"),
                    "status": resource.get("status"),
                    "cpu": f"{(resource.get('cpu', 0) * 100):.1f}%",
                    "memory_percent": f"{(resource.get('mem', 0) / resource.get('maxmem', 1) * 100):.1f}%"
                })
            elif res_type == "qemu":
                vms.append({
                    "vmid": resource.get("vmid"),
                    "name": resource.get("name"),
                    "node": resource.get("node"),
                    "status": resource.get("status"),
                    "cpu": f"{(resource.get('cpu', 0) * 100):.1f}%",
                    "memory_percent": f"{(resource.get('mem', 0) / resource.get('maxmem', 1) * 100):.1f}%" if resource.get(maxmem) else "0%"
                })
            elif res_type == "lxc":
                containers.append({
                    "vmid": resource.get("vmid"),
                    "name": resource.get("name"),
                    "node": resource.get("node"),
                    "status": resource.get("status"),
                    "cpu": f"{(resource.get('cpu', 0) * 100):.1f}%",
                    "memory_percent": f"{(resource.get('mem', 0) / resource.get('maxmem', 1) * 100):.1f}%" if resource.get(maxmem) else "0%"
                })
        
        running_count = len([v for v in vms if v["status"] == "running"]) + len([c for c in containers if c["status"] == "running"])
        
        return {
            "success": True,
            "nodes": nodes,
            "vms": vms,
            "containers": containers,
            "summary": {
                "nodes": len(nodes),
                "vms": len(vms),
                "containers": len(containers),
                "running": running_count
            }
        }


class ProxmoxManageTool(BaseTool):
    """Manage Proxmox VMs and containers (start, stop, reboot)"""
    
    name = "proxmox_manage"
    description = """Manage Proxmox VMs and containers. Perform actions like:
- start: Start a VM or container
- stop: Stop a VM or container
- reboot: Reboot a VM or container"""
    
    domain = ToolDomain.HOMELAB
    requires_confirmation = True
    
    parameters = [
        ToolParameter(
            name="action",
            type="string",
            description="Action to perform",
            enum=["start", "stop", "reboot"]
        ),
        ToolParameter(
            name="node",
            type="string",
            description="Node name (pve1, pve2, etc.)"
        ),
        ToolParameter(
            name="vmid",
            type="integer",
            description="VM or container ID"
        ),
        ToolParameter(
            name="type",
            type="string",
            description="Resource type",
            enum=["qemu", "lxc"],
            required=False
        )
    ]
    
    def __init__(self):
        if not settings.proxmox_token_name or not settings.proxmox_token_value:
            raise ValueError("PROXMOX_TOKEN_NAME and PROXMOX_TOKEN_VALUE not configured")
        self.client = ProxmoxClient()
    
    async def execute(self, action: str, node: str, vmid: int, type: str = "qemu") -> Dict[str, Any]:
        """Execute Proxmox management action"""
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            try:
                endpoint = f"/nodes/{node}/{type}/{vmid}/status/{action}"
                result = await self.client.request(client, "POST", endpoint)
                
                if result and not result.get("error") and result.get("data"):
                    return {
                        "success": True,
                        "message": f"Successfully {action}ed {type} {vmid} on {node}",
                        "task": result.get("data")
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get("error", f"Failed to {action} {type} {vmid} on {node}")
                    }
                    
            except Exception as e:
                return {"success": False, "error": f"Proxmox management failed: {str(e)}"}
