#!/usr/bin/env python3
"""
SSE MCP Client - Búvár-style EventSource client for streaming MCP
Implements dependency injection, context management, and auto-reconnection
"""
import asyncio
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

import aiohttp


class StreamState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    STREAMING = "streaming"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class SSEStreamContext:
    """SSE stream context with hierarchical management"""

    stream_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    base_url: str = ""
    endpoint: str = ""
    state: StreamState = StreamState.DISCONNECTED
    start_time: Optional[float] = None
    last_event_id: str = "0"
    message_count: int = 0
    reconnect_attempts: int = 0
    max_reconnects: int = 5
    event_handlers: Dict[str, List[Callable]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SSEMCPError(Exception):
    """SSE client exception"""

    def __init__(self, message: str, event_data: Any = None):
        self.message = message
        self.event_data = event_data
        super().__init__(message)


class SSEMCPClient:
    """
    Búvár-style SSE MCP Client with:
    - Context-driven stream management
    - Dependency injection for event handlers
    - Auto-reconnection with exponential backoff
    - Async-first design for streaming
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8081",
        timeout: float = 60.0,
        reconnect_delay: float = 1.0,
        **session_kwargs,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.reconnect_delay = reconnect_delay
        self.session_kwargs = session_kwargs
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger("mcp.sse.client")

        # Global event handlers (dependency injection)
        self.global_handlers: Dict[str, List[Callable]] = {
            "started": [],
            "progress": [],
            "result": [],
            "completed": [],
            "error": [],
            "token": [],  # For LLM streaming
        }

    def register_handler(self, event_type: str, handler: Callable) -> None:
        """Register global event handler"""
        if event_type not in self.global_handlers:
            self.global_handlers[event_type] = []
        self.global_handlers[event_type].append(handler)

    def register_handlers(self, handlers: Dict[str, Callable]) -> None:
        """Register multiple handlers at once"""
        for event_type, handler in handlers.items():
            self.register_handler(event_type, handler)

    @asynccontextmanager
    async def session_context(self):
        """Async context manager for HTTP session"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout, **self.session_kwargs)

        try:
            yield self.session
        finally:
            pass  # Keep session alive for multiple streams

    async def _parse_sse_line(self, line: str) -> Optional[Dict[str, str]]:
        """Parse SSE message line"""
        line = line.strip()
        if not line or line.startswith("#"):
            return None

        if ":" in line:
            field, _, value = line.partition(":")
            return {field.strip(): value.strip()}

        return {line: ""}

    async def _parse_sse_message(self, lines: List[str]) -> Optional[Dict[str, Any]]:
        """Parse complete SSE message"""
        if not lines:
            return None

        message = {}
        data_lines = []

        for line in lines:
            parsed = await self._parse_sse_line(line)
            if not parsed:
                continue

            for key, value in parsed.items():
                if key == "data":
                    data_lines.append(value)
                else:
                    message[key] = value

        if data_lines:
            data_str = "\n".join(data_lines)
            try:
                message["data"] = json.loads(data_str) if data_str else None
            except json.JSONDecodeError:
                message["data"] = data_str

        return message if message else None

    async def _handle_event(
        self, context: SSEStreamContext, event_type: str, event_data: Any
    ):
        """Handle parsed SSE event"""
        context.message_count += 1

        # Call stream-specific handlers
        handlers = context.event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_data)
                else:
                    handler(event_data)
            except Exception as e:
                self.logger.error(f"❌ Stream handler error: {e}")

        # Call global handlers
        global_handlers = self.global_handlers.get(event_type, [])
        for handler in global_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_data)
                else:
                    handler(event_data)
            except Exception as e:
                self.logger.error(f"❌ Global handler error: {e}")

        # Update stream state based on event
        if event_type == "started":
            context.state = StreamState.STREAMING
        elif event_type in ["completed", "error"]:
            context.state = (
                StreamState.COMPLETED
                if event_type == "completed"
                else StreamState.ERROR
            )

    async def stream_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any] = None,
        handlers: Dict[str, Callable] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream tool execution with real-time updates"""
        endpoint = f"/stream/tools/{tool_name}"
        params = arguments or {}

        async for event in self._stream_endpoint(endpoint, params, handlers):
            yield event

    async def stream_llm(
        self, prompt: str, model: str = "default", handlers: Dict[str, Callable] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream LLM token generation"""
        endpoint = "/stream/llm"
        params = {"prompt": prompt, "model": model}

        async for event in self._stream_endpoint(endpoint, params, handlers):
            yield event

    async def stream_mcp_method(
        self,
        method: str,
        params: Dict[str, Any] = None,
        handlers: Dict[str, Callable] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream MCP method execution"""
        endpoint = "/stream/mcp"
        stream_params = {"method": method, **(params or {})}

        async for event in self._stream_endpoint(endpoint, stream_params, handlers):
            yield event

    async def _stream_endpoint(
        self,
        endpoint: str,
        params: Dict[str, Any],
        handlers: Dict[str, Callable] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Generic endpoint streaming with auto-reconnection"""
        context = SSEStreamContext(base_url=self.base_url, endpoint=endpoint)

        # Register stream-specific handlers
        if handlers:
            context.event_handlers = {
                event_type: [handler] if not isinstance(handler, list) else handler
                for event_type, handler in handlers.items()
            }

        async with self.session_context() as session:
            while context.reconnect_attempts < context.max_reconnects:
                try:
                    context.state = StreamState.CONNECTING
                    context.start_time = time.time()

                    # Build URL with query parameters
                    url = f"{self.base_url}{endpoint}"

                    headers = {
                        "Accept": "text/event-stream",
                        "Cache-Control": "no-cache",
                    }

                    # Add Last-Event-ID for reconnection
                    if context.last_event_id != "0":
                        headers["Last-Event-ID"] = context.last_event_id

                    self.logger.info(f"🌊 Connecting to {url}")

                    async with session.get(
                        url, params=params, headers=headers
                    ) as response:
                        if response.status != 200:
                            raise SSEMCPError(
                                f"HTTP {response.status}: {await response.text()}"
                            )

                        context.state = StreamState.CONNECTED

                        # Get stream ID from headers
                        stream_id = response.headers.get("X-Stream-ID")
                        if stream_id:
                            context.stream_id = stream_id

                        # Process SSE stream
                        buffer = []

                        async for line in response.content:
                            line_str = line.decode("utf-8").rstrip("\r\n")
                            self.logger.debug(f"📜 SSE Line: {repr(line_str)}")

                            if line_str == "":
                                # Empty line indicates end of message
                                if buffer:
                                    self.logger.debug(f"📜 SSE Buffer: {buffer}")
                                    message = await self._parse_sse_message(buffer)
                                    self.logger.debug(f"📜 SSE Message: {message}")
                                    if message:
                                        event = await self._process_sse_message(
                                            context, message
                                        )
                                        self.logger.debug(f"📜 SSE Event: {event}")
                                        yield event
                                    buffer = []
                            else:
                                buffer.append(line_str)

                        # Stream completed normally
                        context.state = StreamState.COMPLETED
                        break

                except asyncio.TimeoutError:
                    self.logger.warning(f"⏰ Stream timeout, attempting reconnection...")
                    context.reconnect_attempts += 1

                except Exception as e:
                    self.logger.error(f"❌ Stream error: {e}")
                    context.state = StreamState.ERROR

                    # Yield error event
                    yield {
                        "event": "error",
                        "data": {
                            "error": str(e),
                            "reconnect_attempt": context.reconnect_attempts,
                        },
                    }

                    context.reconnect_attempts += 1

                # Exponential backoff for reconnection
                if context.reconnect_attempts < context.max_reconnects:
                    delay = self.reconnect_delay * (2**context.reconnect_attempts)
                    self.logger.info(f"🔄 Reconnecting in {delay}s...")
                    await asyncio.sleep(delay)

            if context.reconnect_attempts >= context.max_reconnects:
                self.logger.error(f"❌ Max reconnection attempts reached")
                yield {
                    "event": "error",
                    "data": {"error": "Max reconnection attempts reached"},
                }

    async def _process_sse_message(
        self, context: SSEStreamContext, message: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process parsed SSE message and trigger handlers"""
        event_type = message.get("event", "message")
        event_data = message.get("data")
        event_id = message.get("id")

        if event_id:
            context.last_event_id = event_id

        # Trigger event handlers
        await self._handle_event(context, event_type, event_data)

        return {
            "event": event_type,
            "data": event_data,
            "id": event_id,
            "stream_id": context.stream_id,
        }

    async def get_tools(self) -> List[Dict[str, Any]]:
        """Get available tools (non-streaming)"""
        async with self.session_context() as session:
            try:
                async with session.get(f"{self.base_url}/tools") as response:
                    if response.status == 200:
                        data = await response.json()
                        tools = data.get("tools", [])
                        return tools
                    else:
                        error_text = await response.text()
                        self.logger.error(f"❌ Tools request failed: HTTP {response.status} - {error_text}")
                        raise SSEMCPError(f"Failed to get tools: HTTP {response.status}")
                        
            except Exception as e:
                self.logger.error(f"❌ Tools request exception: {e}")
                raise

    async def get_health(self) -> Dict[str, Any]:
        """Get server health"""
        async with self.session_context() as session:
            async with session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise SSEMCPError(f"Health check failed: HTTP {response.status}")

    async def get_stats(self) -> Dict[str, Any]:
        """Get server statistics"""
        async with self.session_context() as session:
            async with session.get(f"{self.base_url}/stats") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise SSEMCPError(f"Stats failed: HTTP {response.status}")

    async def disconnect(self):
        """Close session and cleanup"""
        if self.session:
            await self.session.close()
            self.session = None
        self.logger.info("👋 SSE client disconnected")


# Factory function
def create_sse_client(
    base_url: str = "http://localhost:8081", **kwargs
) -> SSEMCPClient:
    """Factory for creating SSE MCP clients"""
    return SSEMCPClient(base_url, **kwargs)


# Interactive SSE CLI
async def sse_cli():
    """Interactive CLI for SSE MCP client"""
    print("🌊 SSE MCP Client")
    print("=" * 50)

    base_url = input("Enter base URL (default: http://localhost:8081): ").strip()
    if not base_url:
        base_url = "http://localhost:8081"

    client = create_sse_client(base_url)

    # Register example global handlers
    def on_progress(data):
        if isinstance(data, dict) and "message" in data:
            print(f"📊 Progress: {data['message']}")

    def on_error(data):
        print(f"❌ Error: {data}")

    def on_token(data):
        if isinstance(data, dict) and "token" in data:
            print(f"🔤 Token: {data['token']}")

    client.register_handlers(
        {"progress": on_progress, "error": on_error, "token": on_token}
    )

    try:
        # Check server health
        health = await client.get_health()
        print(f"\\n✅ Server health: {health.get('status', 'unknown')}")

        # Get available tools
        tools = await client.get_tools()
        print(f"🔧 Available tools: {[t['name'] for t in tools]}")

        print("\\n📋 Commands:")
        print("  list          - List available tools")
        print("  stream <tool> - Stream tool execution")
        print("  llm <prompt>  - Stream LLM response")
        print("  stats         - Show server stats")
        print("  exit          - Exit client")
        print("\\n💡 Argument Examples:")
        print('  JSON:      {\\"name\\": \\"World\\", \\"style\\": \\"friendly\\"}')
        print("  Key=Value: name=World style=friendly")
        print("  Simple:    Hello world")
        print("  Empty:     [just press Enter]")

        while True:
            try:
                command = input("\\nsse-mcp> ").strip()

                if command == "exit":
                    break
                elif command == "list":
                    tools = await client.get_tools()
                    print(f"\\n🔧 Available Tools ({len(tools)}):")
                    for tool in tools:
                        streaming_url = tool.get("streaming_url", "N/A")
                        print(
                            f"  • {tool['name']}: {tool.get('description', 'No description')}"
                        )
                        print(f"    📡 Stream: {streaming_url}")
                elif command == "stats":
                    stats = await client.get_stats()
                    print("\\n📊 Server Stats:")
                    print(f"  Streaming: {stats.get('streaming', {})}")
                    print(f"  Server: {stats.get('server', {})}")
                elif command.startswith("stream "):
                    tool_name = command[7:].strip()
                    await _stream_tool_interactive(client, tool_name)
                elif command.startswith("llm "):
                    prompt = command[4:].strip()
                    await _stream_llm_interactive(client, prompt)
                else:
                    print(f"Unknown command: {command}")

            except KeyboardInterrupt:
                print("\\n⏹️  Stream interrupted")
            except Exception as e:
                print(f"❌ Error: {e}")

    finally:
        await client.disconnect()


async def _stream_tool_interactive(client: SSEMCPClient, tool_name: str):
    """Interactively stream tool execution"""
    print(f"\\n🌊 Streaming tool: {tool_name}")

    # Get tool arguments
    args_input = input("Arguments (JSON, key=value, or empty): ").strip()
    arguments = {}

    if args_input:
        # Try JSON first
        if args_input.startswith("{"):
            try:
                arguments = json.loads(args_input)
                print(f"✅ Parsed as JSON: {arguments}")
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON: {e}")
                return

        # Try simple key=value format
        elif "=" in args_input:
            try:
                pairs = args_input.split()
                for pair in pairs:
                    if "=" in pair:
                        key, value = pair.split("=", 1)
                        # Simple type conversion
                        if value.isdigit():
                            arguments[key] = int(value)
                        elif value.lower() in ["true", "false"]:
                            arguments[key] = value.lower() == "true"
                        else:
                            arguments[key] = value
                print(f"✅ Parsed as key=value: {arguments}")
            except Exception as e:
                print(f"❌ Invalid key=value format: {e}")
                return

        # Fallback: treat as single string argument
        else:
            arguments = {"query": args_input}
            print(f"✅ Treated as query: {arguments}")

    print(f"🚀 Starting stream...")

    try:
        async for event in client.stream_tool(tool_name, arguments):
            event_type = event.get("event")
            data = event.get("data", {})

            print(f"📨 Event: {event_type} | Data: {data}")  # Debug line

            if event_type == "started":
                print(f"✅ Stream started: {data}")
            elif event_type == "progress":
                message = data.get("message", "Processing...")
                progress = data.get("progress", 0)
                print(f"📈 Progress: {message} ({progress})")
            elif event_type == "result":
                print(f"📄 Result:")
                if isinstance(data, dict) and "result" in data:
                    result = data["result"]
                    if isinstance(result, dict) and "content" in result:
                        print(f"  📊 Tool: {data.get('tool', 'unknown')}")
                        for item in result["content"]:
                            text = item.get("text", str(item))
                            print(f"  {text}")
                    else:
                        print(f"  {result}")
                else:
                    print(f"  {data}")
            elif event_type == "completed":
                duration = data.get("duration", 0)
                print(f"🏁 Completed in {duration:.3f}s: {data}")
                break
            elif event_type == "error":
                print(f"❌ Error: {data}")
                break

    except Exception as e:
        print(f"❌ Stream error: {e}")


async def _stream_llm_interactive(client: SSEMCPClient, prompt: str):
    """Interactively stream LLM response"""
    print("\\n🤖 Streaming LLM response...")
    print(f"📝 Prompt: {prompt}")

    tokens = []

    try:
        async for event in client.stream_llm(prompt):
            event_type = event.get("event")
            data = event.get("data", {})

            if event_type == "started":
                print(f"✅ LLM started: {data}")
                print("🔤 Response: ", end="", flush=True)
            elif event_type == "token":
                token = data.get("token", "")
                tokens.append(token)
                print(token, end=" ", flush=True)
            elif event_type == "completed":
                print(f"\\n🏁 Completed: {data}")
                print(f"📊 Full response: {' '.join(tokens)}")
                break
            elif event_type == "error":
                print(f"\\n❌ Error: {data}")
                break

    except Exception as e:
        print(f"❌ Stream error: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)  # Changed to DEBUG
    asyncio.run(sse_cli())
