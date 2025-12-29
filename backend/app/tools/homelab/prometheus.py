"""
Prometheus Tool for JARVIS v3
Query Prometheus for system metrics
"""
import httpx
from typing import Dict, Any, List, Optional

from app.tools.base import BaseTool, ToolParameter, ToolDomain
from app.config.settings import get_settings

settings = get_settings()


class PrometheusTool(BaseTool):
    """Query Prometheus for system metrics like CPU, RAM, disk usage"""
    
    name = "prometheus"
    description = """Query Prometheus for system metrics. Use for questions about:
- CPU usage (use query: 100 - (avg by(instance)(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100))
- Memory usage (use query: node_memory_MemAvailable_bytes or node_memory_MemTotal_bytes)
- Disk usage (use query: node_filesystem_avail_bytes or node_filesystem_size_bytes)
- Service status (use query: up)
- Custom PromQL queries"""
    
    domain = ToolDomain.HOMELAB
    
    parameters = [
        ToolParameter(
            name="query",
            type="string",
            description="PromQL query to execute. Examples: 'up', 'node_memory_MemAvailable_bytes', '100 - (avg by(instance)(rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)'"
        ),
        ToolParameter(
            name="time",
            type="string",
            description="Optional timestamp (RFC3339 or Unix). Defaults to now.",
            required=False
        )
    ]
    
    def __init__(self):
        self.base_url = settings.prometheus_url
    
    async def execute(self, query: str, time: Optional[str] = None) -> Dict[str, Any]:
        """Execute Prometheus query"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            params = {"query": query}
            if time:
                params["time"] = time
            
            try:
                response = await client.get(
                    f"{self.base_url}/api/v1/query",
                    params=params
                )
                response.raise_for_status()
                data = response.json()
                
                if data.get("status") == "success":
                    results = data.get("data", {}).get("result", [])
                    
                    # Format results for readability
                    formatted = []
                    for r in results:
                        metric = r.get("metric", {})
                        value = r.get("value", [None, None])
                        formatted.append({
                            "metric": metric,
                            "value": value[1] if len(value) > 1 else None,
                            "timestamp": value[0] if len(value) > 0 else None
                        })
                    
                    return {
                        "success": True,
                        "query": query,
                        "result_count": len(formatted),
                        "results": formatted[:20]  # Limit to 20 results
                    }
                else:
                    return {
                        "success": False,
                        "error": data.get("error", "Unknown error"),
                        "query": query
                    }
                    
            except httpx.HTTPStatusError as e:
                return {
                    "success": False,
                    "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
                    "query": query
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "query": query
                }
