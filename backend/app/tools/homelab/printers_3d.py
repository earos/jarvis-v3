"""
3D Printer Tool for JARVIS v3
Query 3D printers (Bambu Lab, Prusa) for print status, temperatures, and job progress
"""
import httpx
import json
from typing import Dict, Any, Optional

from app.tools.base import BaseTool, ToolParameter, ToolDomain
from app.config.settings import get_settings

settings = get_settings()


class Printers3DTool(BaseTool):
    """Query 3D printers for status, temperatures, and job information"""
    
    name = "printers_3d"
    description = """Query 3D printers (Bambu Lab X1C, Prusa MK3.5) for print status, temperatures, current job progress, and print history. Use this to monitor active prints or check printer availability."""
    
    domain = ToolDomain.HOMELAB
    
    parameters = [
        ToolParameter(
            name="printer",
            type="string",
            description="Which printer to query",
            enum=["bambu_x1c", "prusa_mk35"]
        ),
        ToolParameter(
            name="action",
            type="string",
            description="What information to retrieve",
            enum=["status", "temperatures", "current_job", "history"]
        )
    ]
    
    def __init__(self):
        # Bambu Lab settings
        self.bambu_host = getattr(settings, 'bambu_host', None)
        self.bambu_access_code = getattr(settings, 'bambu_access_code', None)
        
        # Prusa settings
        self.prusa_host = getattr(settings, 'prusa_host', None)
        self.prusa_api_key = getattr(settings, 'prusa_api_key', None)
    
    async def execute(self, printer: str, action: str) -> Dict[str, Any]:
        """Execute 3D printer query"""
        
        if printer == "bambu_x1c":
            return await self._query_bambu(action)
        elif printer == "prusa_mk35":
            return await self._query_prusa(action)
        else:
            return {
                "success": False,
                "error": f"Unknown printer: {printer}"
            }
    
    async def _query_bambu(self, action: str) -> Dict[str, Any]:
        """Query Bambu Lab X1C via local API"""
        
        if not self.bambu_host or not self.bambu_access_code:
            return {
                "success": False,
                "error": "Bambu Lab credentials not configured (BAMBU_HOST, BAMBU_ACCESS_CODE)"
            }
        
        # Bambu Lab uses HTTPS with self-signed cert
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            try:
                headers = {
                    "Authorization": f"Bearer {self.bambu_access_code}",
                    "Content-Type": "application/json"
                }
                
                base_url = f"https://{self.bambu_host}"
                
                if action == "status":
                    # Get printer status
                    response = await client.get(
                        f"{base_url}/api/v1/status",
                        headers=headers
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    return {
                        "success": True,
                        "printer": "bambu_x1c",
                        "action": "status",
                        "data": data
                    }
                
                elif action == "temperatures":
                    # Get temperature information
                    response = await client.get(
                        f"{base_url}/api/v1/status",
                        headers=headers
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    temps = {
                        "nozzle_temp": data.get("nozzle_temp"),
                        "nozzle_target": data.get("nozzle_target_temp"),
                        "bed_temp": data.get("bed_temp"),
                        "bed_target": data.get("bed_target_temp"),
                        "chamber_temp": data.get("chamber_temp")
                    }
                    
                    return {
                        "success": True,
                        "printer": "bambu_x1c",
                        "action": "temperatures",
                        "temperatures": temps
                    }
                
                elif action == "current_job":
                    # Get current print job
                    response = await client.get(
                        f"{base_url}/api/v1/status",
                        headers=headers
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    job_info = {
                        "state": data.get("print_status"),
                        "progress": data.get("print_percentage"),
                        "file_name": data.get("gcode_file"),
                        "time_elapsed": data.get("print_time_elapsed"),
                        "time_remaining": data.get("print_time_remaining"),
                        "layer_current": data.get("layer_num"),
                        "layer_total": data.get("total_layers")
                    }
                    
                    return {
                        "success": True,
                        "printer": "bambu_x1c",
                        "action": "current_job",
                        "job": job_info
                    }
                
                elif action == "history":
                    # Get print history
                    response = await client.get(
                        f"{base_url}/api/v1/jobs",
                        headers=headers
                    )
                    response.raise_for_status()
                    history = response.json()
                    
                    return {
                        "success": True,
                        "printer": "bambu_x1c",
                        "action": "history",
                        "history": history
                    }
                
                else:
                    return {
                        "success": False,
                        "error": f"Invalid action for Bambu Lab: {action}"
                    }
                    
            except httpx.HTTPStatusError as e:
                return {
                    "success": False,
                    "error": f"Bambu Lab HTTP {e.response.status_code}: {e.response.text[:200]}"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Bambu Lab error: {str(e)}"
                }
    
    async def _query_prusa(self, action: str) -> Dict[str, Any]:
        """Query Prusa via PrusaLink API"""
        
        if not self.prusa_host or not self.prusa_api_key:
            return {
                "success": False,
                "error": "Prusa credentials not configured (PRUSA_HOST, PRUSA_API_KEY)"
            }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                headers = {
                    "X-Api-Key": self.prusa_api_key,
                    "Content-Type": "application/json"
                }
                
                base_url = f"http://{self.prusa_host}/api"
                
                if action == "status":
                    # Get printer status
                    response = await client.get(
                        f"{base_url}/v1/status",
                        headers=headers
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    return {
                        "success": True,
                        "printer": "prusa_mk35",
                        "action": "status",
                        "data": data
                    }
                
                elif action == "temperatures":
                    # Get temperature information
                    response = await client.get(
                        f"{base_url}/v1/status",
                        headers=headers
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    printer_data = data.get("printer", {})
                    temps = {
                        "nozzle_temp": printer_data.get("temp_nozzle"),
                        "nozzle_target": printer_data.get("target_nozzle"),
                        "bed_temp": printer_data.get("temp_bed"),
                        "bed_target": printer_data.get("target_bed")
                    }
                    
                    return {
                        "success": True,
                        "printer": "prusa_mk35",
                        "action": "temperatures",
                        "temperatures": temps
                    }
                
                elif action == "current_job":
                    # Get current print job
                    response = await client.get(
                        f"{base_url}/v1/job",
                        headers=headers
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    job = data.get("job", {})
                    progress = data.get("progress", {})
                    
                    job_info = {
                        "state": data.get("state"),
                        "progress": progress.get("completion"),
                        "file_name": job.get("file", {}).get("display_name"),
                        "time_elapsed": progress.get("printTime"),
                        "time_remaining": progress.get("printTimeLeft")
                    }
                    
                    return {
                        "success": True,
                        "printer": "prusa_mk35",
                        "action": "current_job",
                        "job": job_info
                    }
                
                elif action == "history":
                    # Get print history (PrusaLink stores files, not full history)
                    response = await client.get(
                        f"{base_url}/v1/files",
                        headers=headers
                    )
                    response.raise_for_status()
                    files = response.json()
                    
                    return {
                        "success": True,
                        "printer": "prusa_mk35",
                        "action": "history",
                        "files": files
                    }
                
                else:
                    return {
                        "success": False,
                        "error": f"Invalid action for Prusa: {action}"
                    }
                    
            except httpx.HTTPStatusError as e:
                return {
                    "success": False,
                    "error": f"Prusa HTTP {e.response.status_code}: {e.response.text[:200]}"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Prusa error: {str(e)}"
                }
