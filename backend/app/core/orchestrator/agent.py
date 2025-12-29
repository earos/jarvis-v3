"""
JARVIS Orchestrator Agent
Handles Claude API interactions with tool use
"""
import json
import logging
from typing import AsyncGenerator, Dict, Any, List, Optional
from anthropic import AsyncAnthropic

from app.config.settings import get_settings
from app.tools.registry import tool_registry
from app.tools.base import ToolDomain

logger = logging.getLogger(__name__)
settings = get_settings()


class JarvisOrchestrator:
    """
    Main AI orchestrator using Claude with native tool use.
    
    Features:
    - Streaming responses
    - Tool execution loop
    - Domain-based tool filtering
    - Conversation context management
    """
    
    SYSTEM_PROMPTS = {
        ToolDomain.HOMELAB: """You are JARVIS, Paul's homelab AI assistant. Be extremely concise.

RESPONSE STYLE:
- Lead with the bottom line, not the process
- For health checks: confirm all good OR list only problems with solutions
- Skip details that are normal/expected
- 1-2 sentences for simple queries
- Sound natural for text-to-speech - avoid markdown like ## and **
- Be conversational, not robotic

GOOD EXAMPLE:
"All systems healthy - 18 services up, Proxmox nodes running well. One issue: 2 WiFi APs are disconnected, might need a power cycle."

BAD EXAMPLE (too verbose):
"I'll run a comprehensive system check... System Status: Overall Good. Service Monitoring: All 18 services operational..."

CAPABILITIES:
Proxmox cluster, Synology NAS, UniFi network/Protect, Prometheus metrics, Docker via Portainer.

GUIDELINES:
- Use tools to get real data, never guess
- Only report problems and their solutions
- Confirm things are working in one brief statement""",

        ToolDomain.PERSONAL: """You are JARVIS, Paul's personal assistant.

## Personality  
- Helpful and efficient
- Proactive about scheduling and reminders
- Respects privacy and confidentiality

## Capabilities
- Calendar management
- Email triage and drafting
- Note-taking and retrieval
- Reminders and task tracking
- Weather and time utilities

## Guidelines
- Be concise and actionable
- Summarize rather than list everything
- Proactively suggest follow-ups""",

        ToolDomain.UTILITIES: """You are JARVIS, a helpful AI assistant.
Be concise and direct. Use available tools when needed."""
    }
    
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.default_model
        self.max_tokens = settings.max_tokens
    
    def get_system_prompt(self, domain: ToolDomain) -> str:
        """Get system prompt for a domain"""
        return self.SYSTEM_PROMPTS.get(domain, self.SYSTEM_PROMPTS[ToolDomain.UTILITIES])
    
    async def process(
        self,
        message: str,
        domain: ToolDomain | str = ToolDomain.HOMELAB,
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
        """
        Process a user message and return response.
        
        Args:
            message: User's message
            domain: Tool domain to use
            conversation_history: Previous messages for context
            
        Returns:
            Final text response
        """
        if isinstance(domain, str):
            domain = ToolDomain(domain)
        
        # Get tools for domain
        tools = tool_registry.get_schemas_for_domain(domain) + tool_registry.get_schemas_for_domain(ToolDomain.UTILITIES)
        
        # Build messages
        messages = conversation_history.copy() if conversation_history else []
        messages.append({"role": "user", "content": message})
        
        # Initial Claude call
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.get_system_prompt(domain),
            tools=tools if tools else None,
            messages=messages
        )
        
        # Tool use loop
        while response.stop_reason == "tool_use":
            # Execute tools
            tool_results = await self._execute_tools(response.content)
            
            # Continue conversation with tool results
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self.get_system_prompt(domain),
                tools=tools if tools else None,
                messages=messages
            )
        
        # Extract final text response
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        
        return "I apologize, but I couldn't generate a response."
    
    async def process_stream(
        self,
        message: str,
        domain: ToolDomain | str = ToolDomain.HOMELAB,
        conversation_history: Optional[List[Dict]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a user message with streaming response.
        
        Yields:
            Dict with type and content:
            - {"type": "text", "content": "..."} for text chunks
            - {"type": "tool_use", "name": "...", "input": {...}} for tool calls
            - {"type": "tool_result", "name": "...", "result": {...}} for results
            - {"type": "done", "usage": {...}} when complete
        """
        if isinstance(domain, str):
            domain = ToolDomain(domain)
        
        tools = tool_registry.get_schemas_for_domain(domain) + tool_registry.get_schemas_for_domain(ToolDomain.UTILITIES)
        messages = conversation_history.copy() if conversation_history else []
        messages.append({"role": "user", "content": message})
        
        while True:
            # Stream response
            current_tool = None
            tool_input_json = ""
            response_content = []
            
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self.get_system_prompt(domain),
                tools=tools if tools else None,
                messages=messages
            ) as stream:
                async for event in stream:
                    if event.type == "content_block_start":
                        if hasattr(event.content_block, "type"):
                            if event.content_block.type == "tool_use":
                                current_tool = {
                                    "id": event.content_block.id,
                                    "name": event.content_block.name
                                }
                                tool_input_json = ""
                    
                    elif event.type == "content_block_delta":
                        if hasattr(event.delta, "text"):
                            yield {"type": "text", "content": event.delta.text}
                        
                        elif hasattr(event.delta, "partial_json"):
                            tool_input_json += event.delta.partial_json
                    
                    elif event.type == "content_block_stop":
                        if current_tool:
                            try:
                                tool_input = json.loads(tool_input_json) if tool_input_json else {}
                            except json.JSONDecodeError:
                                tool_input = {}
                            
                            yield {
                                "type": "tool_use",
                                "name": current_tool["name"],
                                "input": tool_input
                            }
                            
                            response_content.append({
                                "type": "tool_use",
                                "id": current_tool["id"],
                                "name": current_tool["name"],
                                "input": tool_input
                            })
                            current_tool = None
                
                # Get final message
                final_message = await stream.get_final_message()
            
            # Check if we need to execute tools
            if final_message.stop_reason == "tool_use":
                tool_results = await self._execute_tools(final_message.content)
                
                # Yield tool results
                for result in tool_results:
                    yield {
                        "type": "tool_result",
                        "tool_use_id": result["tool_use_id"],
                        "result": result["content"]
                    }
                
                # Continue conversation
                messages.append({"role": "assistant", "content": final_message.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                # Done - yield usage info
                yield {
                    "type": "done",
                    "usage": {
                        "input_tokens": final_message.usage.input_tokens,
                        "output_tokens": final_message.usage.output_tokens
                    }
                }
                break
    
    async def _execute_tools(self, content: List) -> List[Dict]:
        """Execute tool calls from Claude response"""
        results = []
        
        for block in content:
            if hasattr(block, "type") and block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input if hasattr(block, "input") else {}
                
                logger.info(f"Executing tool: {tool_name}", extra={"input": tool_input})
                
                tool = tool_registry.get_tool(tool_name)
                if tool:
                    try:
                        result = await tool.execute(**tool_input)
                        result_str = json.dumps(result)
                    except Exception as e:
                        logger.error(f"Tool {tool_name} failed: {e}")
                        result_str = json.dumps({"error": str(e)})
                else:
                    result_str = json.dumps({"error": f"Unknown tool: {tool_name}"})
                
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_str
                })
        
        return results
