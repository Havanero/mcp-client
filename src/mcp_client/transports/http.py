#!/usr/bin/env python3
"""
HTTP MCP Client - Búvár-style REST client for MCP servers
Implements dependency injection, context management, and async-first design
"""
import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache, partial
from typing import Any, Callable, Dict, List, Optional

import aiohttp


class ClientState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    INITIALIZED = "initialized"
    ERROR = "error"


@dataclass
class HTTPContext:
    """HTTP client context with hierarchical stacking"""

    client_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    base_url: str = ""
    session: Optional[aiohttp.ClientSession] = None
    server_info: Dict[str, Any] = field(default_factory=dict)
    tools: List[Dict[str, Any]] = field(default_factory=list)
    state: ClientState = ClientState.DISCONNECTED
    timeout: float = 30.0
    headers: Dict[str, str] = field(
        default_factory=lambda: {"Content-Type": "application/json"}
    )


class MCPHTTPError(Exception):
    """Custom HTTP client exception"""

    def __init__(self, message: str, status: int = 0, response_data: Any = None):
        self.message = message
        self.status = status
        self.response_data = response_data
        super().__init__(f"HTTP {status}: {message}")


class HTTPMCPClient:
    """
    Búvár-style HTTP MCP Client with:
    - Context-driven configuration
    - Async-first design with proper lifecycle
    - Functools optimization for caching
    - Dependency injection for handlers
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        timeout: float = 30.0,
        **session_kwargs,
    ):
        self.context = HTTPContext(base_url=base_url.rstrip("/"), timeout=timeout)
        self.session_kwargs = session_kwargs
        self.logger = logging.getLogger(f"mcp.http.{self.context.client_id[:8]}")

        # Event handlers (dependency injection)
        self._response_handlers: Dict[str, Callable] = {}
        self._error_handlers: List[Callable[[Exception], None]] = []

    def register_response_handler(self, endpoint: str, handler: Callable) -> None:
        """Register response handler for specific endpoint"""
        self._response_handlers[endpoint] = handler

    def register_error_handler(self, handler: Callable[[Exception], None]) -> None:
        """Register error handler"""
        self._error_handlers.append(handler)

    @asynccontextmanager
    async def session_context(self):
        """Async context manager for HTTP session lifecycle"""
        try:
            connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
            timeout = aiohttp.ClientTimeout(total=self.context.timeout)

            self.context.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self.context.headers,
                **self.session_kwargs,
            )
            self.context.state = ClientState.CONNECTED
            yield self.context.session

        finally:
            if self.context.session:
                await self.context.session.close()
                self.context.session = None
                self.context.state = ClientState.DISCONNECTED

    async def _handle_response(
        self, response: aiohttp.ClientResponse, endpoint: str = ""
    ) -> Any:
        """Handle HTTP response with error checking"""
        try:
            if response.status >= 400:
                error_text = await response.text()
                raise MCPHTTPError(
                    f"HTTP {response.status}: {error_text}", response.status
                )

            # Check content type
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                data = await response.json()
            else:
                data = await response.text()

            # Apply custom handlers
            if endpoint in self._response_handlers:
                data = await self._response_handlers[endpoint](data)

            return data

        except Exception as e:
            await self._handle_error(e)
            raise

    async def _handle_error(self, error: Exception):
        """Handle errors through registered handlers"""
        for handler in self._error_handlers:
            try:
                handler(error)
            except Exception as handler_error:
                self.logger.error(f"Error handler failed: {handler_error}")

    async def connect(self) -> bool:
        """Initialize connection and discover server capabilities"""
        try:
            # Create persistent session
            connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
            timeout = aiohttp.ClientTimeout(total=self.context.timeout)

            self.context.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self.context.headers,
                **self.session_kwargs,
            )
            self.context.state = ClientState.CONNECTED

            # Health check
            health_url = f"{self.context.base_url}/health"
            async with self.context.session.get(health_url) as response:
                health_data = await self._handle_response(response, "health")
                self.logger.info(
                    f"✅ Server health: {health_data.get('status', 'unknown') if health_data else 'unknown'}"
                )

            # Get server info (if available)
            try:
                info_url = f"{self.context.base_url}/info"
                async with self.context.session.get(info_url) as response:
                    if response.status == 200:
                        self.context.server_info = await self._handle_response(
                            response, "info"
                        )
            except:
                pass  # Optional endpoint

            # Discover tools
            await self._discover_tools()

            self.context.state = ClientState.INITIALIZED
            self.logger.info(f"🔧 Discovered {len(self.context.tools)} tools")
            return True

        except Exception as e:
            self.logger.error(f"❌ Connection failed: {e}")
            self.context.state = ClientState.ERROR
            if self.context.session:
                await self.context.session.close()
                self.context.session = None
            return False

    async def _discover_tools(self):
        """Discover available tools"""
        try:
            tools_url = f"{self.context.base_url}/tools"
            async with self.context.session.get(tools_url) as response:
                data = await self._handle_response(response, "tools")
                if data is None:
                    data = {}
                self.context.tools = data.get("tools", [])

        except Exception as e:
            self.logger.warning(f"⚠️  Tool discovery failed: {e}")
            self.context.tools = []

    @lru_cache(maxsize=64)
    def get_tool_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get tool by name with caching"""
        return next(
            (tool for tool in self.context.tools if tool.get("name") == name), None
        )

    async def call_tool(
        self, name: str, arguments: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Call a tool via REST API"""
        if self.context.state != ClientState.INITIALIZED:
            raise MCPHTTPError("Client not initialized")

        if not self.context.session:
            raise MCPHTTPError("No active session")

        tool = self.get_tool_by_name(name)
        if not tool:
            raise MCPHTTPError(f"Tool '{name}' not found")

        try:
            # REST-style tool call
            tool_url = f"{self.context.base_url}/tools/{name}"
            payload = arguments or {}

            async with self.context.session.post(tool_url, json=payload) as response:
                result = await self._handle_response(response, f"tool_{name}")
                return result

        except MCPHTTPError:
            raise
        except Exception as e:
            raise MCPHTTPError(f"Tool call failed: {e}")

    async def call_mcp_method(
        self, method: str, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Call MCP method via JSON-RPC over HTTP"""
        if self.context.state != ClientState.INITIALIZED:
            raise MCPHTTPError("Client not initialized")

        if not self.context.session:
            raise MCPHTTPError("No active session")

        try:
            mcp_url = f"{self.context.base_url}/mcp"
            request_data = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": method,
                "params": params or {},
            }

            async with self.context.session.post(
                mcp_url, json=request_data
            ) as response:
                data = await self._handle_response(response, "mcp")

                if "error" in data:
                    error = data["error"]
                    raise MCPHTTPError(
                        f"MCP Error: {error.get('message', 'Unknown')}",
                        error.get("code", -32603),
                    )

                return data.get("result", {})

        except MCPHTTPError:
            raise
        except Exception as e:
            raise MCPHTTPError(f"MCP method call failed: {e}")

    async def list_tools(self) -> List[Dict[str, Any]]:
        """Get fresh list of tools"""
        if self.context.state != ClientState.INITIALIZED:
            raise MCPHTTPError("Client not initialized")

        if not self.context.session:
            raise MCPHTTPError("No active session")

        try:
            tools_url = f"{self.context.base_url}/tools"
            async with self.context.session.get(tools_url) as response:
                data = await self._handle_response(response, "tools")
                if data is None:
                    data = {}
                tools = data.get("tools", [])
                self.context.tools = tools  # Update cache
                self.get_tool_by_name.cache_clear()  # Clear cache
                return tools

        except Exception as e:
            raise MCPHTTPError(f"Failed to list tools: {e}")

    async def get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics"""
        if self.context.state != ClientState.INITIALIZED:
            raise MCPHTTPError("Client not initialized")

        if not self.context.session:
            raise MCPHTTPError("No active session")

        try:
            stats_url = f"{self.context.base_url}/stats"
            async with self.context.session.get(stats_url) as response:
                return await self._handle_response(response, "stats")

        except Exception as e:
            raise MCPHTTPError(f"Failed to get stats: {e}")

    @property
    def is_connected(self) -> bool:
        """Check if client is connected and initialized"""
        return self.context.state == ClientState.INITIALIZED

    @property
    def tools(self) -> List[Dict[str, Any]]:
        """Get available tools"""
        return self.context.tools

    @property
    def server_info(self) -> Dict[str, Any]:
        """Get server info"""
        return self.context.server_info

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        return {
            "client_id": self.context.client_id,
            "state": self.context.state.value,
            "base_url": self.context.base_url,
            "tools_count": len(self.context.tools),
            "server_info": self.context.server_info,
        }

    async def disconnect(self):
        """Disconnect and cleanup"""
        if self.context.session:
            await self.context.session.close()
            self.context.session = None
        self.context.state = ClientState.DISCONNECTED
        self.logger.info("👋 Disconnected from HTTP server")


# Factory function with dependency injection
def create_http_client(
    base_url: str = "http://localhost:8080", **kwargs
) -> HTTPMCPClient:
    """Factory for creating HTTP MCP clients"""
    return HTTPMCPClient(base_url, **kwargs)


# Interactive HTTP CLI
async def http_cli():
    """Interactive CLI for HTTP MCP client"""
    print("🔗 HTTP MCP Client")
    print("=" * 50)

    # Connect to server
    base_url = input("Enter base URL (default: http://localhost:8080): ").strip()
    if not base_url:
        base_url = "http://localhost:8080"

    client = create_http_client(base_url)

    # Register example handlers
    def log_error(error: Exception):
        print(f"🚨 Error: {error}")

    client.register_error_handler(log_error)

    try:
        connected = await client.connect()
        if not connected:
            print("❌ Failed to connect to server")
            return

        print(f"\n✅ Connected to HTTP MCP server!")
        print(f"Server info: {client.server_info}")
        print(f"Available tools: {[t['name'] for t in client.tools]}")

        print(f"\n📋 Commands:")
        print(f"  list          - List available tools")
        print(f"  call <tool>   - Call a tool")
        print(f"  mcp <method>  - Call MCP method")
        print(f"  stats         - Show server stats")
        print(f"  exit          - Exit client")

        # Interactive loop
        while True:
            try:
                command = input(f"\nhttp-mcp> ").strip()

                if command == "exit":
                    break
                elif command == "list":
                    tools = await client.list_tools()
                    print(f"\n🔧 Available Tools ({len(tools)}):")
                    for tool in tools:
                        print(
                            f"  • {tool['name']}: {tool.get('description', 'No description')}"
                        )
                elif command == "stats":
                    stats = await client.get_server_stats()
                    print(f"\n📊 Server Stats:")
                    for key, value in stats.items():
                        print(f"  {key}: {value}")
                elif command.startswith("call "):
                    tool_name = command[5:].strip()
                    await _interactive_tool_call(client, tool_name)
                elif command.startswith("mcp "):
                    method = command[4:].strip()
                    await _interactive_mcp_call(client, method)
                else:
                    print(f"Unknown command: {command}")

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    except Exception as e:
        print(f"❌ Client error: {e}")
    finally:
        await client.disconnect()


async def _interactive_tool_call(client: HTTPMCPClient, tool_name: str):
    """Interactively call a tool"""
    tool = client.get_tool_by_name(tool_name)
    if not tool:
        print(f"❌ Tool not found: {tool_name}")
        return

    print(f"\n🔧 Calling tool: {tool_name}")
    print(f"Description: {tool.get('description', 'No description')}")

    # Simple argument input
    args_input = input("Arguments (JSON, or empty): ").strip()
    arguments = {}

    if args_input:
        try:
            arguments = json.loads(args_input)
        except json.JSONDecodeError:
            print("❌ Invalid JSON, using empty arguments")

    try:
        print(f"⚡ Executing {tool_name}...")
        result = await client.call_tool(tool_name, arguments)

        print(f"✅ Result:")
        if isinstance(result, dict) and "result" in result:
            content = result["result"].get("content", [])
            for item in content:
                print(f"  📄 {item.get('text', str(item))}")
        else:
            print(f"  📄 {result}")

    except Exception as e:
        print(f"❌ Tool execution failed: {e}")


async def _interactive_mcp_call(client: HTTPMCPClient, method: str):
    """Interactively call MCP method"""
    print(f"\n📡 Calling MCP method: {method}")

    params_input = input("Parameters (JSON, or empty): ").strip()
    params = {}

    if params_input:
        try:
            params = json.loads(params_input)
        except json.JSONDecodeError:
            print("❌ Invalid JSON, using empty parameters")

    try:
        result = await client.call_mcp_method(method, params)
        print(f"✅ Result: {result}")

    except Exception as e:
        print(f"❌ MCP call failed: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(http_cli())
