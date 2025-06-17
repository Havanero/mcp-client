#!/usr/bin/env python3
"""
MCP Client - Main client interface for MCP integration

Unified, high-level client that combines LLM capabilities with MCP tool execution
in a clean, streaming-enabled interface.
"""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from .config import AgentConfig, ConfigManager, LLMConfig, MCPConfig
from .exceptions import MCPClientError, MCPConnectionError, MCPToolError
from .llm import LLMClient, LLMClientFactory, LLMMessage
from .transports.jsonrpc import MCPJSONRPCClient


@dataclass
class ToolCall:
    """Represents a tool call request"""

    name: str
    arguments: Dict[str, Any]
    reasoning: str = ""


@dataclass
class ToolResult:
    """Represents a tool execution result"""

    name: str
    success: bool
    result: Any
    error: Optional[str] = None
    duration: float = 0.0


@dataclass
class ChatContext:
    """Chat conversation context"""

    messages: List[LLMMessage] = field(default_factory=list)
    available_tools: List[Dict[str, Any]] = field(default_factory=list)
    tool_calls: List[ToolCall] = field(default_factory=list)
    tool_results: List[ToolResult] = field(default_factory=list)
    session_id: str = ""


class MCPClient:
    """
    High-level MCP client with streaming support

    Features:
    - Unified LLM + MCP tool integration
    - Real-time streaming responses
    - Tool execution notifications
    - Connection management
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.llm_client: Optional[LLMClient] = None
        self.transport: Optional[MCPJSONRPCClient] = None
        self.logger = logging.getLogger("mcp_client.client")

        # Tool caching
        self._tools_cache: Optional[List[Dict[str, Any]]] = None

    @classmethod
    def create_openai(
        cls, api_key: str, model: str = "gpt-4", mcp_url: str = "http://localhost:8081"
    ) -> "MCPClient":
        """Create client with OpenAI configuration"""
        config = AgentConfig(
            llm=LLMConfig(provider="openai", model=model, api_key=api_key),
            mcp=MCPConfig(base_url=mcp_url),
        )
        return cls(config)

    @classmethod
    def create_anthropic(
        cls,
        api_key: str,
        model: str = "claude-3-sonnet-20240229",
        mcp_url: str = "http://localhost:8081",
    ) -> "MCPClient":
        """Create client with Anthropic configuration"""
        config = AgentConfig(
            llm=LLMConfig(provider="anthropic", model=model, api_key=api_key),
            mcp=MCPConfig(base_url=mcp_url),
        )
        return cls(config)

    @classmethod
    def from_env(cls) -> "MCPClient":
        """Create client from environment variables"""
        config = ConfigManager.load_from_env()
        return cls(config)

    @asynccontextmanager
    async def session(self):
        """Context manager for client session"""
        # Initialize LLM client
        self.llm_client = LLMClientFactory.create_client(self.config.llm)

        # Initialize transport  
        self.transport = MCPJSONRPCClient(
            self.config.mcp.base_url,
            timeout=self.config.mcp.timeout
        )

        try:
            # Test MCP connection
            connected = await self.transport.connect()
            if not connected:
                raise MCPConnectionError("Failed to connect to MCP server")
            
            health = await self.transport.get_health()
            self.logger.info(f"🌊 Connected to MCP server: {health.get('status')}")
            
            # Discover tools immediately when session starts
            self.logger.info("🔍 Discovering available tools...")
            tools = await self.discover_tools()
            self.logger.info(f"🔧 Session ready with {len(tools)} tools")
            
            yield self
        except Exception as e:
            self.logger.error(f"❌ MCP connection failed: {e}")
            raise MCPConnectionError(f"Failed to connect to MCP server: {e}")
        finally:
            # Cleanup
            if self.transport:
                await self.transport.disconnect()
            if self.llm_client:
                await self.llm_client.close()
            self.transport = None
            self.llm_client = None

    async def discover_tools(self) -> List[Dict[str, Any]]:
        """Discover available tools from MCP server"""
        if self._tools_cache is not None:
            return self._tools_cache

        if not self.transport:
            raise MCPClientError(
                "Client not initialized. Use 'async with client.session():'"
            )

        try:
            tools = await self.transport.get_tools()
            self._tools_cache = tools
            self.logger.info(
                f"🔧 Discovered {len(tools)} tools: {[t['name'] for t in tools]}"
            )
            return tools
        except Exception as e:
            self.logger.error(f"❌ Tool discovery failed: {e}")
            raise MCPToolError(f"Tool discovery failed: {e}")

    @lru_cache(maxsize=1)
    def _convert_mcp_tools_to_openai(self, tools_tuple: tuple) -> List[Dict[str, Any]]:
        """Convert MCP tools to OpenAI function format"""
        openai_tools = []

        for tool_json in tools_tuple:
            tool = json.loads(tool_json)

            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get(
                        "inputSchema", {"type": "object", "properties": {}}
                    ),
                },
            }
            openai_tools.append(openai_tool)

        return openai_tools

    async def execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """Execute a single tool call"""
        if not self.transport:
            raise MCPClientError("Transport not initialized")

        self.logger.info(f"⚡ Executing tool: {tool_call.name}")
        start_time = asyncio.get_event_loop().time()

        try:
            result_data = await self.transport.call_tool(
                tool_call.name, tool_call.arguments
            )

            duration = asyncio.get_event_loop().time() - start_time

            return ToolResult(
                name=tool_call.name, success=True, result=result_data, duration=duration
            )

        except Exception as e:
            duration = asyncio.get_event_loop().time() - start_time
            self.logger.error(f"❌ Tool execution failed: {e}")

            return ToolResult(
                name=tool_call.name,
                success=False,
                result=None,
                error=str(e),
                duration=duration,
            )

    async def chat_stream(
        self, message: str, context: Optional[ChatContext] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream chat response with tool execution

        Yields events:
        - {"type": "chunk", "content": "text"}
        - {"type": "tool_notification", "content": "Using tool..."}
        - {"type": "error", "content": "Error message"}
        """
        if context is None:
            context = ChatContext()
            context.available_tools = await self.discover_tools()
        elif not context.available_tools:
            self.logger.info("🔄 Refreshing tools...")
            context.available_tools = await self.discover_tools()

        if not self.llm_client:
            raise MCPClientError("LLM client not initialized")

        # Convert tools to OpenAI format
        tools_tuple = tuple(
            json.dumps(tool, sort_keys=True) for tool in context.available_tools
        )
        openai_tools = self._convert_mcp_tools_to_openai(tools_tuple)

        # Build messages
        system_prompt = (
            "You are a helpful assistant with access to tools. "
            "Use the available tools when needed to help the user. "
            "When you receive tool results, format them nicely for the user."
        )

        messages = [LLMMessage(role="system", content=system_prompt)]
        messages.extend(context.messages)
        messages.append(LLMMessage(role="user", content=message))

        try:
            # Check if LLM wants to use tools
            initial_response = await self.llm_client.complete(
                messages, tools=openai_tools if openai_tools else None, temperature=0.3
            )

            if initial_response.tool_calls:
                # Execute tools with notifications
                for tool_call in initial_response.tool_calls:
                    func_name = tool_call["function"]["name"]
                    func_args = json.loads(tool_call["function"]["arguments"])

                    # Notify user
                    yield {
                        "type": "tool_notification",
                        "content": f"🔍 Using {func_name} tool...",
                    }

                    # Execute tool
                    result = await self.execute_tool(
                        ToolCall(name=func_name, arguments=func_args)
                    )

                    # Store in context
                    context.tool_calls.append(
                        ToolCall(name=func_name, arguments=func_args)
                    )
                    context.tool_results.append(result)

                    # Add to conversation
                    if not messages or messages[-1].role != "assistant":
                        messages.append(
                            LLMMessage(
                                role="assistant",
                                content=initial_response.content or "",
                                tool_calls=initial_response.tool_calls,
                            )
                        )

                    # Add tool result
                    tool_result_content = (
                        json.dumps(result.result, indent=2)
                        if result.success
                        else f"Error: {result.error}"
                    )
                    messages.append(
                        LLMMessage(
                            role="tool",
                            content=tool_result_content,
                            name=func_name,
                            tool_call_id=tool_call["id"],
                        )
                    )

                # Stream final response
                yield {
                    "type": "tool_notification",
                    "content": "✅ Tools completed, generating response...",
                }

                async for chunk in self.llm_client.stream(messages):
                    yield {"type": "chunk", "content": chunk}

            else:
                # No tools needed - stream immediately
                async for chunk in self.llm_client.stream(
                    messages,
                    tools=openai_tools if openai_tools else None,
                    temperature=0.3,
                ):
                    yield {"type": "chunk", "content": chunk}

        except Exception as e:
            self.logger.error(f"❌ Chat stream error: {e}")
            yield {"type": "error", "content": f"❌ Error: {e}"}

    async def chat(
        self, message: str, context: Optional[ChatContext] = None
    ) -> Tuple[str, ChatContext]:
        """
        Non-streaming chat interface

        Returns:
            Tuple of (response_text, updated_context)
        """
        if context is None:
            context = ChatContext()

        response_parts = []

        async for event in self.chat_stream(message, context):
            if event["type"] == "chunk":
                response_parts.append(event["content"])
            elif event["type"] == "tool_notification":
                # Log but don't include in response
                self.logger.info(event["content"])
            elif event["type"] == "error":
                return event["content"], context

        response_text = "".join(response_parts)

        # Update context
        context.messages.append(LLMMessage(role="user", content=message))
        context.messages.append(LLMMessage(role="assistant", content=response_text))

        return response_text, context

    async def get_stats(self) -> Dict[str, Any]:
        """Get client and server statistics"""
        if not self.transport:
            return {"status": "disconnected"}

        try:
            server_health = await self.transport.get_health()
            
            # Note: JSON-RPC client may not have get_stats method
            server_stats = {}
            if hasattr(self.transport, 'get_stats'):
                try:
                    server_stats = await self.transport.get_stats()
                except:
                    server_stats = {"note": "Stats not available in JSON-RPC transport"}

            return {
                "server": server_health,
                "server_stats": server_stats,
                "tools_cached": len(self._tools_cache) if self._tools_cache else 0,
                "llm_provider": self.config.llm.provider,
                "llm_model": self.config.llm.model,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
