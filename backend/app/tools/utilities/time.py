"""
Time Tool for JARVIS v3
Get current date and time with timezone support
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any, Optional

from app.tools.base import BaseTool, ToolParameter, ToolDomain
from app.config.settings import get_settings

settings = get_settings()


class TimeTool(BaseTool):
    """Get current date and time"""
    
    name = "get_time"
    description = """Get the current date and time. Use this when the user asks what time it is, the current date, or any time-related questions."""
    
    domain = ToolDomain.UTILITIES
    
    parameters = [
        ToolParameter(
            name="timezone",
            type="string",
            description=f"Timezone (e.g., 'Europe/London', 'America/New_York'). Defaults to {settings.location_timezone}.",
            required=False
        )
    ]
    
    async def execute(self, timezone: Optional[str] = None) -> Dict[str, Any]:
        """Execute time query"""
        try:
            # Use provided timezone or default from settings
            tz_name = timezone if timezone else settings.location_timezone
            tz = ZoneInfo(tz_name)
            
            # Get current time in specified timezone
            now = datetime.now(tz)
            
            # Format human-readable string
            formatted = now.strftime("%A, %B %d, %Y %I:%M:%S %p %Z")
            
            return {
                "success": True,
                "formatted": formatted,
                "iso": now.isoformat(),
                "unix": int(now.timestamp()),
                "timezone": tz_name,
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "day_of_week": now.strftime("%A"),
                "month": now.strftime("%B"),
                "year": now.year
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
