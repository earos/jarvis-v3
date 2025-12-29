"""
Research Tool for JARVIS v3
Web search and research via Tavily API
"""
import httpx
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import re

from app.tools.base import BaseTool, ToolParameter, ToolDomain
from app.config.settings import get_settings

settings = get_settings()


TAVILY_API_URL = "https://api.tavily.com/search"
RESEARCH_DIR = Path("/opt/jarvis/research")

# Ensure research directory exists
RESEARCH_DIR.mkdir(parents=True, exist_ok=True)


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug"""
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = text.strip('-')
    return text[:50]


class ResearchTool(BaseTool):
    """Search the web and research topics via Tavily API"""
    
    name = "research"
    description = """Search the web and research topics. Use depth='light' for quick searches (returns summary + sources). Use depth='deep' for comprehensive research (saves full document to file). Always use this tool when the user asks to research, search, or look up information online."""
    
    domain = ToolDomain.UTILITIES
    
    parameters = [
        ToolParameter(
            name="query",
            type="string",
            description="The search query or research question"
        ),
        ToolParameter(
            name="depth",
            type="string",
            description="light = quick search (5 results), deep = comprehensive research (10 results + saved document)",
            enum=["light", "deep"],
            required=False
        ),
        ToolParameter(
            name="topic",
            type="string",
            description="Optional topic name for the research document filename (deep mode only)",
            required=False
        )
    ]
    
    def __init__(self):
        self.api_key = settings.tavily_api_key
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY not configured")
    
    async def _tavily_search(
        self, 
        query: str, 
        search_depth: str = "basic", 
        max_results: int = 5
    ) -> Dict[str, Any]:
        """Execute Tavily API search"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                TAVILY_API_URL,
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "search_depth": search_depth,
                    "include_answer": True,
                    "include_raw_content": search_depth == "advanced",
                    "max_results": max_results
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def execute(
        self,
        query: str,
        depth: Optional[str] = None,
        topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute research query"""
        try:
            research_depth = depth if depth else "light"
            
            if research_depth == "light":
                # Light research - quick search
                results = await self._tavily_search(query, "basic", 5)
                
                return {
                    "success": True,
                    "type": "light_research",
                    "query": query,
                    "answer": results.get("answer"),
                    "sources": [
                        {
                            "title": r.get("title"),
                            "url": r.get("url"),
                            "snippet": r.get("content", "")[:200] + "..." if r.get("content") else None
                        }
                        for r in results.get("results", [])
                    ]
                }
            
            elif research_depth == "deep":
                # Deep research - comprehensive search with document output
                results = await self._tavily_search(query, "advanced", 10)
                
                # Build research document
                doc_topic = topic if topic else query
                now = datetime.now()
                filename = f"{now.strftime('%Y-%m-%d')}-{slugify(doc_topic)}.md"
                filepath = RESEARCH_DIR / filename
                
                # Create markdown document
                document_lines = [
                    f"# Research: {doc_topic}",
                    "",
                    f"**Date:** {now.strftime('%A, %B %d, %Y')}",
                    f"**Query:** {query}",
                    "",
                    "---",
                    "",
                    "## Summary",
                    "",
                    results.get("answer", "No summary available."),
                    "",
                    "---",
                    "",
                    "## Sources",
                    ""
                ]
                
                for i, r in enumerate(results.get("results", []), 1):
                    document_lines.extend([
                        f"### {i}. {r.get('title', 'Unknown')}",
                        f"**URL:** {r.get('url', 'N/A')}",
                        "",
                        r.get("content", r.get("snippet", "No content available.")),
                        "",
                        "---",
                        ""
                    ])
                
                document_lines.append("\n*Generated by JARVIS Research Tool*")
                
                # Write document
                filepath.write_text("\n".join(document_lines))
                
                return {
                    "success": True,
                    "type": "deep_research",
                    "query": query,
                    "topic": doc_topic,
                    "answer": results.get("answer"),
                    "sources_count": len(results.get("results", [])),
                    "document_path": str(filepath),
                    "sources": [
                        {
                            "title": r.get("title"),
                            "url": r.get("url")
                        }
                        for r in results.get("results", [])[:5]
                    ]
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Invalid depth: {research_depth}. Use 'light' or 'deep'."
                }
                
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
