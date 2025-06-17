#!/usr/bin/env python3
"""
SSE Transport - Modern EventSource client for MCP streaming
Clean, async-first design with connection pooling and auto-reconnection
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

from .exceptions import MCPConnectionError, MCPStreamError


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


class SSETransport:
    """
    Modern SSE transport for MCP with:
    - Connection pooling and auto-reconnection
    - Event handler dependency injection
    - Async-first streaming design
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
        self.logger = logging.getLogger("mcp_client.transport")

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
                            error_text = await response.text()
                            raise MCPConnectionError(
                                f"HTTP {response.status}: {error_text}",
                                url=url,
                                status_code=response.status,
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

                            if line_str == "":
                                # Empty line indicates end of message
                                if buffer:
                                    message = await self._parse_sse_message(buffer)
                                    if message:
                                        event = await self._process_sse_message(
                                            context, message
                                        )
                                        yield event
                                    buffer = []
                            else:
                                buffer.append(line_str)

                        # Stream completed normally
                        context.state = StreamState.COMPLETED
                        break

                except asyncio.TimeoutError:
                    self.logger.warning(
                        f"⏰ Stream timeout, attempting reconnection..."
                    )
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
                raise MCPStreamError(
                    "Max reconnection attempts reached", context.stream_id
                )

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
                        self.logger.error(
                            f"❌ Tools request failed: HTTP {response.status} - {error_text}"
                        )
                        raise MCPConnectionError(
                            f"Failed to get tools: HTTP {response.status}",
                            url=f"{self.base_url}/tools",
                            status_code=response.status,
                        )

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
                    raise MCPConnectionError(
                        f"Health check failed: HTTP {response.status}",
                        url=f"{self.base_url}/health",
                        status_code=response.status,
                    )

    async def get_stats(self) -> Dict[str, Any]:
        """Get server statistics"""
        async with self.session_context() as session:
            async with session.get(f"{self.base_url}/stats") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise MCPConnectionError(
                        f"Stats failed: HTTP {response.status}",
                        url=f"{self.base_url}/stats",
                        status_code=response.status,
                    )

    async def disconnect(self):
        """Close session and cleanup"""
        if self.session:
            await self.session.close()
            self.session = None
        self.logger.info("👋 SSE transport disconnected")
