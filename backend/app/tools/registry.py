"""
Tool Registry for JARVIS v3
Auto-discovers and manages all available tools
"""
import importlib
import pkgutil
import logging
from typing import Dict, List, Optional, Type
from pathlib import Path

from app.tools.base import BaseTool, ToolDomain

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Central registry for all JARVIS tools.
    
    Features:
    - Auto-discovery of tools from app.tools subpackages
    - Domain-based tool filtering
    - Claude schema generation
    """
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._by_domain: Dict[ToolDomain, List[str]] = {
            domain: [] for domain in ToolDomain
        }
    
    def register(self, tool: BaseTool) -> None:
        """Register a tool instance"""
        if tool.name in self._tools:
            logger.warning(f"Tool {tool.name} already registered, overwriting")
        
        self._tools[tool.name] = tool
        self._by_domain[tool.domain].append(tool.name)
        logger.info(f"Registered tool: {tool.name} ({tool.domain.value})")
    
    def auto_discover(self, package_name: str = "app.tools") -> int:
        """
        Auto-discover and register all tools from subpackages.
        
        Scans homelab/, personal/, business/, utilities/ for BaseTool subclasses.
        
        Returns:
            Number of tools registered
        """
        count = 0
        subpackages = ["homelab", "personal", "business", "utilities"]
        
        for subpkg in subpackages:
            full_package = f"{package_name}.{subpkg}"
            try:
                package = importlib.import_module(full_package)
            except ImportError as e:
                logger.debug(f"Could not import {full_package}: {e}")
                continue
            
            # Get package path
            if not hasattr(package, "__path__"):
                continue
                
            # Iterate through modules in package
            for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
                if is_pkg or module_name.startswith("_"):
                    continue
                
                try:
                    module = importlib.import_module(f"{full_package}.{module_name}")
                    
                    # Find BaseTool subclasses
                    for attr_name in dir(module):
                        if attr_name.startswith("_"):
                            continue
                        
                        attr = getattr(module, attr_name)
                        
                        # Check if it's a BaseTool subclass (not BaseTool itself)
                        if (isinstance(attr, type) and 
                            issubclass(attr, BaseTool) and 
                            attr is not BaseTool and
                            hasattr(attr, "name") and
                            attr.name):  # Has a name defined
                            
                            # Instantiate and register
                            try:
                                tool_instance = attr()
                                self.register(tool_instance)
                                count += 1
                            except Exception as e:
                                logger.error(f"Failed to instantiate {attr_name}: {e}")
                                
                except Exception as e:
                    logger.error(f"Error loading module {module_name}: {e}")
        
        logger.info(f"Auto-discovered {count} tools")
        return count
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        return self._tools.get(name)
    
    def get_tools_for_domain(self, domain: ToolDomain | str) -> List[BaseTool]:
        """Get all tools for a domain"""
        if isinstance(domain, str):
            domain = ToolDomain(domain)
        
        tool_names = self._by_domain.get(domain, [])
        return [self._tools[name] for name in tool_names]
    
    def get_schemas_for_domain(self, domain: ToolDomain | str) -> List[Dict]:
        """Get Claude tool schemas for a domain"""
        tools = self.get_tools_for_domain(domain)
        return [tool.to_claude_schema() for tool in tools]
    
    def get_all_schemas(self) -> List[Dict]:
        """Get all tool schemas"""
        return [tool.to_claude_schema() for tool in self._tools.values()]
    
    def list_tools(self) -> List[str]:
        """List all registered tool names"""
        return list(self._tools.keys())
    
    def count(self) -> int:
        """Count total registered tools"""
        return len(self._tools)
    
    def count_by_domain(self) -> Dict[str, int]:
        """Count tools per domain"""
        return {
            domain.value: len(names) 
            for domain, names in self._by_domain.items()
        }


# Global registry instance
tool_registry = ToolRegistry()
