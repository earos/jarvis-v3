"""
3D Printer Tool for JARVIS v3
Query 3D printers (Bambu Lab, Prusa) for print status, temperatures, and job progress
"""
import ssl
import json
import asyncio
import httpx
from typing import Dict, Any, Optional
from threading import Event

from app.tools.base import BaseTool, ToolParameter, ToolDomain
from app.config.settings import get_settings

settings = get_settings()


class Printers3DTool(BaseTool):
    """Query 3D printers for status, temperatures, and job information"""
    
    name = "printers_3d"
    description = """Query 3D printers (Bambu Lab X1C, Prusa MK3.5) for print status, temperatures, current job progress. Use this to monitor active prints or check printer availability."""
    
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
            enum=["status", "temperatures", "current_job"]
        )
    ]
    
    def __init__(self):
        self.bambu_host = getattr(settings, 'bambu_host', None)
        self.bambu_access_code = getattr(settings, 'bambu_access_code', None)
        self.bambu_serial = getattr(settings, 'bambu_serial', None)
        
        self.prusa_host = getattr(settings, 'prusa_host', None)
        self.prusa_api_key = getattr(settings, 'prusa_api_key', None)
        self.prusa_username = getattr(settings, 'prusa_username', None)
        self.prusa_password = getattr(settings, 'prusa_password', None)
    
    async def execute(self, printer: str, action: str) -> Dict[str, Any]:
        """Execute 3D printer query"""
        
        if printer == "bambu_x1c":
            return await self._query_bambu(action)
        elif printer == "prusa_mk35":
            return await self._query_prusa(action)
        else:
            return {"success": False, "error": f"Unknown printer: {printer}"}
    
    async def _query_bambu(self, action: str) -> Dict[str, Any]:
        """Query Bambu Lab X1C via MQTT"""
        import paho.mqtt.client as mqtt
        
        if not self.bambu_host or not self.bambu_access_code:
            return {
                "success": False,
                "error": "Bambu Lab credentials not configured (BAMBU_HOST, BAMBU_ACCESS_CODE)"
            }
        
        result_data = {}
        connected_event = Event()
        message_event = Event()
        error_msg = None
        
        def on_connect(client, userdata, flags, rc, properties=None):
            nonlocal error_msg
            if rc == 0:
                # Subscribe to report topic
                client.subscribe(f"device/+/report")
                connected_event.set()
                # Request push of all data
                client.publish(f"device/{self.bambu_serial or 'local'}/request", 
                             json.dumps({"pushing": {"command": "pushall"}}))
            else:
                error_msg = f"MQTT connect failed with code {rc}"
                connected_event.set()
        
        def on_message(client, userdata, msg):
            nonlocal result_data
            try:
                payload = json.loads(msg.payload.decode())
                if "print" in payload:
                    result_data = payload["print"]
                    message_event.set()
            except Exception as e:
                pass
        
        def on_disconnect(client, userdata, disconnect_flags, rc, properties=None):
            pass
        
        try:
            # Create MQTT client
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="jarvis_monitor")
            client.username_pw_set("bblp", self.bambu_access_code)
            
            # Configure TLS (Bambu uses self-signed cert)
            client.tls_set(cert_reqs=ssl.CERT_NONE)
            client.tls_insecure_set(True)
            
            client.on_connect = on_connect
            client.on_message = on_message
            client.on_disconnect = on_disconnect
            
            # Connect
            client.connect(self.bambu_host, 8883, keepalive=60)
            client.loop_start()
            
            # Wait for connection
            if not connected_event.wait(timeout=5):
                client.loop_stop()
                return {"success": False, "error": "Connection timeout"}
            
            if error_msg:
                client.loop_stop()
                return {"success": False, "error": error_msg}
            
            # Wait for message
            if not message_event.wait(timeout=10):
                client.loop_stop()
                client.disconnect()
                return {"success": False, "error": "No status message received (printer may be off or idle)"}
            
            client.loop_stop()
            client.disconnect()
            
            # Format response based on action
            if action == "status":
                return {
                    "success": True,
                    "printer": "bambu_x1c",
                    "action": "status",
                    "data": {
                        "state": result_data.get("gcode_state", "unknown"),
                        "wifi_signal": result_data.get("wifi_signal"),
                        "print_type": result_data.get("print_type"),
                        "mc_percent": result_data.get("mc_percent"),
                        "mc_remaining_time": result_data.get("mc_remaining_time"),
                        "subtask_name": result_data.get("subtask_name"),
                        "layer_num": result_data.get("layer_num"),
                        "total_layer_num": result_data.get("total_layer_num"),
                    }
                }
            
            elif action == "temperatures":
                return {
                    "success": True,
                    "printer": "bambu_x1c",
                    "action": "temperatures",
                    "temperatures": {
                        "nozzle_temp": result_data.get("nozzle_temper"),
                        "nozzle_target": result_data.get("nozzle_target_temper"),
                        "bed_temp": result_data.get("bed_temper"),
                        "bed_target": result_data.get("bed_target_temper"),
                        "chamber_temp": result_data.get("chamber_temper"),
                    }
                }
            
            elif action == "current_job":
                return {
                    "success": True,
                    "printer": "bambu_x1c",
                    "action": "current_job",
                    "job": {
                        "state": result_data.get("gcode_state"),
                        "progress_percent": result_data.get("mc_percent"),
                        "remaining_minutes": result_data.get("mc_remaining_time"),
                        "file_name": result_data.get("subtask_name"),
                        "layer_current": result_data.get("layer_num"),
                        "layer_total": result_data.get("total_layer_num"),
                        "print_type": result_data.get("print_type"),
                    }
                }
            
            return {"success": False, "error": f"Invalid action: {action}"}
            
        except Exception as e:
            return {"success": False, "error": f"Bambu Lab error: {str(e)}"}
    
    async def _query_prusa(self, action: str) -> Dict[str, Any]:
        """Query Prusa via PrusaLink API"""
        
        if not self.prusa_host:
            return {
                "success": False,
                "error": "Prusa not configured (PRUSA_HOST required)"
            }
        
        if not self.prusa_api_key and not (self.prusa_username and self.prusa_password):
            return {
                "success": False,
                "error": "Prusa credentials not configured (need PRUSA_API_KEY or PRUSA_USERNAME+PRUSA_PASSWORD)"
            }
        
        # Set up auth
        auth = None
        if self.prusa_username and self.prusa_password:
            auth = httpx.DigestAuth(self.prusa_username, self.prusa_password)
        
        async with httpx.AsyncClient(timeout=10.0, auth=auth) as client:
            try:
                headers = {"Content-Type": "application/json"}
                if self.prusa_api_key:
                    headers["X-Api-Key"] = self.prusa_api_key
                
                base_url = f"http://{self.prusa_host}/api"
                
                if action == "status":
                    response = await client.get(f"{base_url}/v1/status", headers=headers)
                    response.raise_for_status()
                    return {
                        "success": True,
                        "printer": "prusa_mk35",
                        "action": "status",
                        "data": response.json()
                    }
                
                elif action == "temperatures":
                    response = await client.get(f"{base_url}/v1/status", headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    printer_data = data.get("printer", {})
                    return {
                        "success": True,
                        "printer": "prusa_mk35",
                        "action": "temperatures",
                        "temperatures": {
                            "nozzle_temp": printer_data.get("temp_nozzle"),
                            "nozzle_target": printer_data.get("target_nozzle"),
                            "bed_temp": printer_data.get("temp_bed"),
                            "bed_target": printer_data.get("target_bed")
                        }
                    }
                
                elif action == "current_job":
                    response = await client.get(f"{base_url}/v1/job", headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    job = data.get("job", {})
                    progress = data.get("progress", {})
                    return {
                        "success": True,
                        "printer": "prusa_mk35",
                        "action": "current_job",
                        "job": {
                            "state": data.get("state"),
                            "progress": progress.get("completion"),
                            "file_name": job.get("file", {}).get("display_name"),
                            "time_elapsed": progress.get("printTime"),
                            "time_remaining": progress.get("printTimeLeft")
                        }
                    }
                
                return {"success": False, "error": f"Invalid action: {action}"}
                    
            except httpx.HTTPStatusError as e:
                return {"success": False, "error": f"Prusa HTTP {e.response.status_code}"}
            except Exception as e:
                return {"success": False, "error": f"Prusa error: {str(e)}"}
