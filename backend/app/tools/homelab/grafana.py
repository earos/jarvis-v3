"""
Grafana Tool for JARVIS v3
Query Grafana for dashboards, alerts, and visualization status
"""
import httpx
from typing import Dict, Any, Optional

from app.tools.base import BaseTool, ToolParameter, ToolDomain
from app.config.settings import get_settings

settings = get_settings()


class GrafanaTool(BaseTool):
    """Query Grafana for dashboards, alerts, datasources, and health status"""
    
    name = "grafana"
    description = """Query Grafana for monitoring and visualization information. Use for questions about:
- Dashboard list and details
- Active alerts and alert status
- Configured data sources
- Grafana health status
- Visualization and monitoring overview"""
    
    domain = ToolDomain.HOMELAB
    
    parameters = [
        ToolParameter(
            name="action",
            type="string",
            description="Action to perform: 'dashboards' (list all dashboards), 'alerts' (check alert status), 'datasources' (list data sources), 'health' (check Grafana health)"
        )
    ]
    
    def __init__(self):
        self.base_url = settings.grafana_url
        self.api_key = settings.grafana_api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def execute(self, action: str) -> Dict[str, Any]:
        """Execute Grafana API query based on action"""
        action = action.lower().strip()
        
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            try:
                if action == "dashboards":
                    return await self._get_dashboards(client)
                elif action == "alerts":
                    return await self._get_alerts(client)
                elif action == "datasources":
                    return await self._get_datasources(client)
                elif action == "health":
                    return await self._get_health(client)
                else:
                    return {
                        "success": False,
                        "error": f"Unknown action: {action}",
                        "valid_actions": ["dashboards", "alerts", "datasources", "health"]
                    }
                    
            except httpx.HTTPStatusError as e:
                return {
                    "success": False,
                    "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
                    "action": action
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "action": action
                }
    
    async def _get_dashboards(self, client: httpx.AsyncClient) -> Dict[str, Any]:
        """Get list of all dashboards"""
        response = await client.get(
            f"{self.base_url}/api/search",
            headers=self.headers,
            params={"type": "dash-db"}
        )
        response.raise_for_status()
        dashboards = response.json()
        
        # Format dashboard info
        formatted = []
        for dash in dashboards:
            formatted.append({
                "title": dash.get("title"),
                "uid": dash.get("uid"),
                "url": dash.get("url"),
                "type": dash.get("type"),
                "tags": dash.get("tags", []),
                "folder_title": dash.get("folderTitle", "General")
            })
        
        return {
            "success": True,
            "action": "dashboards",
            "count": len(formatted),
            "dashboards": formatted
        }
    
    async def _get_alerts(self, client: httpx.AsyncClient) -> Dict[str, Any]:
        """Get alert status"""
        response = await client.get(
            f"{self.base_url}/api/alerts",
            headers=self.headers
        )
        response.raise_for_status()
        alerts = response.json()
        
        # Categorize alerts by state
        alert_summary = {
            "alerting": [],
            "ok": [],
            "pending": [],
            "no_data": [],
            "paused": []
        }
        
        for alert in alerts:
            state = alert.get("state", "unknown").lower()
            alert_info = {
                "name": alert.get("name"),
                "state": alert.get("state"),
                "dashboard_title": alert.get("dashboardTitle"),
                "panel_name": alert.get("panelName"),
                "eval_date": alert.get("evalDate")
            }
            
            if state in alert_summary:
                alert_summary[state].append(alert_info)
        
        return {
            "success": True,
            "action": "alerts",
            "total_alerts": len(alerts),
            "alerting_count": len(alert_summary["alerting"]),
            "ok_count": len(alert_summary["ok"]),
            "pending_count": len(alert_summary["pending"]),
            "no_data_count": len(alert_summary["no_data"]),
            "paused_count": len(alert_summary["paused"]),
            "summary": alert_summary
        }
    
    async def _get_datasources(self, client: httpx.AsyncClient) -> Dict[str, Any]:
        """Get list of configured data sources"""
        response = await client.get(
            f"{self.base_url}/api/datasources",
            headers=self.headers
        )
        response.raise_for_status()
        datasources = response.json()
        
        # Format datasource info
        formatted = []
        for ds in datasources:
            formatted.append({
                "name": ds.get("name"),
                "type": ds.get("type"),
                "url": ds.get("url"),
                "is_default": ds.get("isDefault", False),
                "access": ds.get("access"),
                "id": ds.get("id")
            })
        
        return {
            "success": True,
            "action": "datasources",
            "count": len(formatted),
            "datasources": formatted
        }
    
    async def _get_health(self, client: httpx.AsyncClient) -> Dict[str, Any]:
        """Check Grafana health status"""
        response = await client.get(
            f"{self.base_url}/api/health",
            headers=self.headers
        )
        response.raise_for_status()
        health = response.json()
        
        return {
            "success": True,
            "action": "health",
            "status": health.get("database"),
            "version": health.get("version"),
            "health_check": health
        }
