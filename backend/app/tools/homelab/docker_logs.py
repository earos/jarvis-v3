"""
Docker Logs Tool for JARVIS v3
Query Docker container logs via Portainer API for troubleshooting and monitoring
"""
import httpx
from typing import Dict, Any, Optional

from app.tools.base import BaseTool, ToolParameter, ToolDomain
from app.config.settings import get_settings

settings = get_settings()


class DockerLogsTool(BaseTool):
    """Query Docker container logs for troubleshooting and monitoring"""
    
    name = "docker_logs"
    description = """Query Docker container logs for troubleshooting and monitoring. Use this to view recent log entries from any Docker container. You can retrieve a specific number of lines, search for specific text patterns, or view the most recent logs."""
    
    domain = ToolDomain.HOMELAB
    
    parameters = [
        ToolParameter(
            name="container",
            type="string",
            description="Docker container ID or name to retrieve logs from"
        ),
        ToolParameter(
            name="lines",
            type="integer",
            description="Number of log lines to retrieve from the end of the logs. Defaults to 50.",
            required=False
        ),
        ToolParameter(
            name="search_term",
            type="string",
            description="Optional text to search for in logs. If provided, only lines containing this text will be returned.",
            required=False
        ),
        ToolParameter(
            name="endpoint_id",
            type="integer",
            description="Portainer endpoint ID. Defaults to 3 if not specified.",
            required=False
        ),
        ToolParameter(
            name="timestamps",
            type="boolean",
            description="Include timestamps in the log output. Defaults to true.",
            required=False
        )
    ]
    
    def __init__(self):
        self.base_url = settings.portainer_url
        self.api_key = settings.portainer_api_key
        if not self.api_key:
            raise ValueError("PORTAINER_API_KEY not configured")
    
    @staticmethod
    def _clean_docker_log_line(line: str) -> str:
        """
        Clean Docker log stream format.
        Docker logs are prefixed with 8 bytes: [stream_type][000][size(4 bytes)]
        """
        if not line:
            return ""
        
        # Strip leading/trailing whitespace
        line = line.strip()
        
        # If line starts with stream header bytes, skip first 8 bytes
        # The header is: 1 byte stream type + 3 bytes padding + 4 bytes size
        if len(line) > 8 and ord(line[0]) in (0, 1, 2):  # Stream type byte
            line = line[8:]
        
        return line
    
    async def execute(
        self, 
        container: str,
        lines: Optional[int] = None,
        search_term: Optional[str] = None,
        endpoint_id: Optional[int] = None,
        timestamps: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Execute Docker logs query"""
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        eid = endpoint_id if endpoint_id is not None else 3
        tail = lines if lines is not None else 50
        show_timestamps = timestamps if timestamps is not None else True
        
        # Build query parameters for Docker logs API
        params = {
            "stdout": "true",
            "stderr": "true",
            "tail": str(tail),
            "timestamps": "true" if show_timestamps else "false"
        }
        
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            try:
                # Get logs via Portainer's Docker API proxy
                response = await client.get(
                    f"{self.base_url}/api/endpoints/{eid}/docker/containers/{container}/logs",
                    headers=headers,
                    params=params
                )
                response.raise_for_status()
                
                # Docker logs come back with stream headers (8 bytes per line)
                logs_text = response.text
                
                # Split into lines and clean up Docker stream format
                log_lines = []
                for line in logs_text.split('\n'):
                    cleaned = self._clean_docker_log_line(line)
                    if cleaned:
                        log_lines.append(cleaned)
                
                # Apply search filter if provided
                if search_term:
                    log_lines = [line for line in log_lines if search_term.lower() in line.lower()]
                
                # Count total lines
                total_lines = len(log_lines)
                
                # Join lines back together for display
                logs_output = '\n'.join(log_lines)
                
                return {
                    "success": True,
                    "container": container,
                    "endpoint_id": eid,
                    "lines_retrieved": total_lines,
                    "lines_requested": tail,
                    "search_term": search_term,
                    "timestamps": show_timestamps,
                    "logs": logs_output,
                    "message": f"Retrieved {total_lines} log lines from container '{container}'"
                }
                    
            except httpx.HTTPStatusError as e:
                error_msg = f"HTTP {e.response.status_code}"
                if e.response.status_code == 404:
                    error_msg = f"Container '{container}' not found on endpoint {eid}"
                elif e.response.status_code == 500:
                    error_msg = f"Container '{container}' may not be running or accessible"
                else:
                    error_msg = f"{error_msg}: {e.response.text[:200]}"
                
                return {
                    "success": False,
                    "error": error_msg,
                    "container": container,
                    "endpoint_id": eid
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "container": container,
                    "endpoint_id": eid
                }
