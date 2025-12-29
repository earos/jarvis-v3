"""
Base Tool class for JARVIS v3
All tools inherit from BaseTool and implement the execute method
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from enum import Enum


class ToolDomain(str, Enum):
    """Available tool domains"""
    HOMELAB = "homelab"
    PERSONAL = "personal"
    BUSINESS1 = "business1"
    BUSINESS2 = "business2"
    UTILITIES = "utilities"


class ToolParameter(BaseModel):
    """Defines a parameter for Claude tool schema generation"""
    name: str
    type: str  # string, number, integer, boolean, array, object
    description: str
    required: bool = True
    enum: Optional[List[str]] = None
    default: Optional[Any] = None


class BaseTool(ABC):
    """
    Base class for all JARVIS tools.
    
    Subclasses must define:
    - name: Unique tool identifier
    - description: What the tool does (used by Claude)
    - domain: Which domain this tool belongs to
    - parameters: List of ToolParameter definitions
    
    And implement:
    - execute(**kwargs): Async method to run the tool
    """
    
    name: str
    description: str
    domain: ToolDomain
    parameters: List[ToolParameter] = []
    requires_confirmation: bool = False  # For destructive actions
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool with given parameters.
        
        Returns:
            Dict with at minimum {'success': bool, ...}
        """
        pass
    
    def to_claude_schema(self) -> Dict[str, Any]:
        """
        Generate Claude API tool use schema.
        
        Returns:
            Dict in Claude tool format
        """
        properties = {}
        required = []
        
        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default
                
            properties[param.name] = prop
            
            if param.required:
                required.append(param.name)
        
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }
    
    def __repr__(self) -> str:
        return f"<Tool {self.name} ({self.domain.value})>"
