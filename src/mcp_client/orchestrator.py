#!/usr/bin/env python3
"""
MCP Orchestrator - Simplified with Native Function Calling and Streaming
Clean, minimal implementation using OpenAI's built-in function calling with hybrid streaming
"""
import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from .config import LLMConfig, MCPConfig
from .llm import LLMClient, LLMMessage, LLMResponse
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
class ConversationContext:
    """Conversation context with tool history"""

    messages: List[LLMMessage] = field(default_factory=list)
    available_tools: List[Dict[str, Any]] = field(default_factory=list)
    tool_calls: List[ToolCall] = field(default_factory=list)
    tool_results: List[ToolResult] = field(default_factory=list)
    session_id: str = ""


class MCPOrchestrator:
    """
    Simplified MCP Orchestrator using native function calling with streaming

    Features:
    - Native OpenAI function calling (no JSON parsing!)
    - Hybrid streaming (immediate for chat, delayed for tools)
    - Direct MCP tool execution
    - Raw response preservation
    - User notifications during tool execution
    """

    def __init__(self, llm_client: LLMClient, mcp_config: MCPConfig):
        self.llm_client = llm_client
        self.mcp_config = mcp_config
        self.mcp_client: Optional[MCPJSONRPCClient] = None
        self.logger = logging.getLogger("mcp.orchestrator")

        # Caches for performance
        self._tools_cache: Optional[List[Dict[str, Any]]] = None

    @asynccontextmanager
    async def session(self):
        """Context manager for MCP session"""
        self.mcp_client = MCPJSONRPCClient(
            self.mcp_config.base_url, timeout=self.mcp_config.timeout
        )

        try:
            # Connect to server using JSON-RPC
            connected = await self.mcp_client.connect()
            if not connected:
                raise Exception("Failed to connect to MCP server")

            health = await self.mcp_client.get_health()
            self.logger.info(f"🌊 Connected to MCP server: {health.get('status')}")

            # Discover tools immediately when session starts
            self.logger.info("🔍 Discovering available tools...")
            tools = await self.discover_tools()
            self.logger.info(f"🔧 Session ready with {len(tools)} tools")

            yield self
        except Exception as e:
            self.logger.error(f"❌ MCP connection failed: {e}")
            raise
        finally:
            if self.mcp_client:
                await self.mcp_client.disconnect()
            self.mcp_client = None

    async def discover_tools(self) -> List[Dict[str, Any]]:
        """Discover available tools from MCP server"""
        if self._tools_cache is not None:
            return self._tools_cache

        if not self.mcp_client:
            raise RuntimeError(
                "MCP client not initialized. Use 'async with orchestrator.session():'"
            )

        try:
            tools = await self.mcp_client.get_tools()
            self._tools_cache = tools
            self.logger.info(
                f"🔧 Discovered {len(tools)} tools: {[t['name'] for t in tools]}"
            )
            return tools
        except Exception as e:
            self.logger.error(f"❌ Tool discovery failed: {e}")

            # If we got "server not initialized" error, clear cache to force refresh
            if "server not initialized" in str(e).lower():
                self.logger.info("🔄 Clearing tool cache due to server restart")
                self._tools_cache = None

            return []

    async def refresh_tools(self) -> List[Dict[str, Any]]:
        """Force refresh tool cache (useful after server restart)"""
        self.logger.info("🔄 Force refreshing tool cache...")
        self._tools_cache = None  # Clear cache
        return await self.discover_tools()

    @lru_cache(maxsize=1)
    def _convert_mcp_tools_to_openai(self, tools_tuple: tuple) -> List[Dict[str, Any]]:
        """Convert MCP tools to OpenAI function format"""
        openai_tools = []

        for tool_json in tools_tuple:
            tool = json.loads(tool_json)

            # Convert MCP tool schema to OpenAI function format
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
        """Execute a single tool call via MCP"""
        if not self.mcp_client:
            raise RuntimeError("MCP client not initialized")

        self.logger.info(
            f"⚡ Executing tool: {tool_call.name} with args: {tool_call.arguments}"
        )
        start_time = asyncio.get_event_loop().time()

        try:
            result_data = await self.mcp_client.call_tool(
                tool_call.name, tool_call.arguments
            )

            duration = asyncio.get_event_loop().time() - start_time

            return ToolResult(
                name=tool_call.name, success=True, result=result_data, duration=duration
            )

        except Exception as e:
            duration = asyncio.get_event_loop().time() - start_time
            error_msg = str(e)
            self.logger.error(f"❌ Tool execution failed: {error_msg}")

            return ToolResult(
                name=tool_call.name,
                success=False,
                result=None,
                error=error_msg,
                duration=duration,
            )

    async def chat_stream(
        self, user_message: str, context: Optional[ConversationContext] = None
    ):
        """
        Streaming chat interface that yields chunks of response

        Yields:
            Dict with 'type': 'chunk'|'tool_notification'|'error', 'content': str
        """
        if context is None:
            context = ConversationContext()
            context.available_tools = await self.discover_tools()
        elif not context.available_tools:
            self.logger.info("🔄 Context has no tools, refreshing...")
            context.available_tools = await self.discover_tools()
        elif len(context.available_tools) == 0:
            # Force refresh if we had tools before but now have none (server restart?)
            self.logger.info("🔄 Tool list is empty, attempting refresh...")
            context.available_tools = await self.refresh_tools()

        # Convert MCP tools to OpenAI function format
        tools_tuple = tuple(
            json.dumps(tool, sort_keys=True) for tool in context.available_tools
        )
        openai_tools = self._convert_mcp_tools_to_openai(tools_tuple)

        if not openai_tools:
            self.logger.warning("⚠️ No tools available")

        # System prompt
        system_prompt = (
            "You are a helpful assistant with access to tools. "
            "Use the available tools when needed to help the user. "
            "When you receive tool results, format them nicely for the user."
        )

        # Build message context
        messages = [LLMMessage(role="system", content=system_prompt)]
        messages.extend(context.messages)
        messages.append(LLMMessage(role="user", content=user_message))

        try:
            # First, check if LLM wants to use tools (non-streaming)
            initial_response = await self.llm_client.complete(
                messages, tools=openai_tools if openai_tools else None, temperature=0.3
            )

            if initial_response.tool_calls:
                # Notify user about tool execution
                self.logger.info(
                    f"🔧 LLM requested {len(initial_response.tool_calls)} tool calls"
                )

                for i, tool_call in enumerate(initial_response.tool_calls):
                    func_name = tool_call["function"]["name"]
                    func_args = tool_call["function"]["arguments"]

                    # Notify user
                    yield {
                        "type": "tool_notification",
                        "content": f"🔍 Using {func_name} tool...",
                    }

                    # Execute tool
                    result = await self.execute_tool(
                        ToolCall(name=func_name, arguments=json.loads(func_args))
                    )

                    # Store in context
                    context.tool_calls.append(
                        ToolCall(name=func_name, arguments=json.loads(func_args))
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

                # Stream final response after tools
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
            yield {"type": "error", "content": f"❌ Error: {e}"}

    async def chat(
        self, user_message: str, context: Optional[ConversationContext] = None
    ) -> Tuple[str, ConversationContext]:
        """
        Non-streaming chat interface (for compatibility)

        Returns:
            Tuple of (response_text, updated_context)
        """
        if context is None:
            context = ConversationContext()

        response_parts = []

        async for event in self.chat_stream(user_message, context):
            if event["type"] == "chunk":
                response_parts.append(event["content"])
            elif event["type"] == "tool_notification":
                # Log tool notifications but don't include in response
                self.logger.info(event["content"])
            elif event["type"] == "error":
                return event["content"], context

        response_text = "".join(response_parts)

        # Update context
        context.messages.append(LLMMessage(role="user", content=user_message))
        context.messages.append(LLMMessage(role="assistant", content=response_text))

        return response_text, context

    async def debug_tools(self) -> Dict[str, Any]:
        """Debug tool discovery and conversion"""
        debug_info = {
            "tools_discovered": 0,
            "tools_converted": 0,
            "mcp_tools": [],
            "openai_tools": [],
            "sample_openai_tool": None,
        }

        try:
            # Test tool discovery
            mcp_tools = await self.discover_tools()
            debug_info["tools_discovered"] = len(mcp_tools)
            debug_info["mcp_tools"] = [t["name"] for t in mcp_tools]

            # Test conversion
            if mcp_tools:
                tools_tuple = tuple(
                    json.dumps(tool, sort_keys=True) for tool in mcp_tools
                )
                openai_tools = self._convert_mcp_tools_to_openai(tools_tuple)
                debug_info["tools_converted"] = len(openai_tools)
                debug_info["openai_tools"] = [
                    t["function"]["name"] for t in openai_tools
                ]
                if openai_tools:
                    debug_info["sample_openai_tool"] = openai_tools[0]

        except Exception as e:
            debug_info["error"] = str(e)

        return debug_info

    async def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        if not self.mcp_client:
            return {"status": "disconnected"}

        try:
            server_health = await self.mcp_client.get_health()

            # Note: JSON-RPC client may not have get_stats method
            mcp_stats = {}
            if hasattr(self.mcp_client, "get_stats"):
                try:
                    mcp_stats = await self.mcp_client.get_stats()
                except:
                    mcp_stats = {"note": "Stats not available in JSON-RPC transport"}

            return {
                "mcp_server": server_health,
                "mcp_stats": mcp_stats,
                "tools_cached": len(self._tools_cache) if self._tools_cache else 0,
                "llm_provider": self.llm_client.config.provider,
                "llm_model": self.llm_client.config.model,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


if __name__ == "__main__":

    async def test_orchestrator():
        """Test the simplified MCP orchestrator"""
        import os

        from .config import ConfigManager
        from .llm_client import LLMClientFactory

        print("🧪 Testing Simplified MCP Orchestrator")

        # Check for API key
        if not os.getenv("OPENAI_API_KEY"):
            print("❌ OPENAI_API_KEY not set")
            return

        # Create configuration
        config = ConfigManager.create_openai_config(
            os.getenv("OPENAI_API_KEY"), "gpt-4"
        )

        # Create LLM client
        llm_client = LLMClientFactory.create_client(config.llm)

        # Create orchestrator
        orchestrator = MCPOrchestrator(llm_client, config.mcp)

        try:
            async with orchestrator.session():
                # Test tool discovery
                tools = await orchestrator.discover_tools()
                print(f"✅ Discovered {len(tools)} tools")

                # Test simple chat
                response, context = await orchestrator.chat("What tools are available?")
                print(f"🤖 Response: {response[:200]}...")

                # Test tool usage
                if tools:
                    response, context = await orchestrator.chat(
                        "Search for GDPR documents", context
                    )
                    print(f"🔧 Tool response: {response[:200]}...")

        except Exception as e:
            print(f"❌ Test failed: {e}")
        finally:
            await llm_client.close()

    asyncio.run(test_orchestrator())
