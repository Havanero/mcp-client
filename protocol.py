#!/usr/bin/env python3
"""
MCP Client - Protocol Layer

Implements MCP protocol handshake, capability negotiation, and tool management.
Builds on the stdio transport for actual MCP server communication.
"""
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from transport import MCPMessage, StdioTransport


@dataclass
class MCPTool:
    """Represents an available MCP tool"""
    name: str
    description: str
    input_schema: Dict[str, Any]


@dataclass
class MCPClient:
    """Main MCP client with protocol handling"""
    transport: StdioTransport
    tools: List[MCPTool] = field(default_factory=list)
    server_info: Dict[str, Any] = field(default_factory=dict)
    _pending_requests: Dict[str, asyncio.Future] = field(default_factory=dict)

    async def initialize(self) -> bool:
        """Perform MCP handshake and discover capabilities"""
        try:
            await self.transport.connect()
            # Start response handler first
            self._response_task = asyncio.create_task(self._handle_responses())
            await self._send_initialize()
            await self._discover_tools()
            return True
        except Exception as e:
            logging.error(f"Initialization failed: {e}")
            return False

    async def _send_initialize(self) -> None:
        """Send MCP initialize request"""
        msg_id = self.transport.next_id()
        init_msg = MCPMessage(
            method="initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}  # We want to use tools
                },
                "clientInfo": {
                    "name": "mcp-python-client",
                    "version": "1.0.0"
                }
            },
            id=msg_id
        )

        # Set up future for response
        future = asyncio.Future()
        self._pending_requests[msg_id] = future

        await self.transport.send_message(init_msg)

        # Wait for initialize response
        result = await future
        self.server_info = result.get("result", {})
        logging.info(f"Server initialized: {self.server_info}")

        # Send initialized notification
        await self.transport.send_message(MCPMessage("initialized", {}))

    async def _discover_tools(self) -> None:
        """Discover available tools from server"""
        msg_id = self.transport.next_id()
        tools_msg = MCPMessage("tools/list", {}, msg_id)

        future = asyncio.Future()
        self._pending_requests[msg_id] = future

        await self.transport.send_message(tools_msg)
        result = await future

        # Parse tools
        tools_data = result.get("result", {}).get("tools", [])
        self.tools = [
            MCPTool(
                name=tool["name"],
                description=tool["description"],
                input_schema=tool["inputSchema"]
            )
            for tool in tools_data
        ]

        logging.info(f"Discovered {len(self.tools)} tools: {[t.name for t in self.tools]}")

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool on the MCP server"""
        msg_id = self.transport.next_id()
        call_msg = MCPMessage(
            method="tools/call",
            params={
                "name": tool_name,
                "arguments": arguments
            },
            id=msg_id
        )

        future = asyncio.Future()
        self._pending_requests[msg_id] = future

        await self.transport.send_message(call_msg)
        result = await future

        return result.get("result", {})



    async def _handle_responses(self) -> None:
        """Background task to handle ongoing server responses"""
        async for message in self.transport.read_messages():
            msg_id = message.get("id")
            if msg_id and msg_id in self._pending_requests:
                future = self._pending_requests.pop(msg_id)
                if "error" in message:
                    future.set_exception(Exception(f"MCP Error: {message['error']}"))
                else:
                    future.set_result(message)

    async def start_response_handler(self) -> None:
        """Start background response handling (already started in initialize)"""
        if not hasattr(self, '_response_task'):
            self._response_task = asyncio.create_task(self._handle_responses())

    async def close(self) -> None:
        """Close MCP client connection"""
        if hasattr(self, '_response_task'):
            self._response_task.cancel()
            try:
                await self._response_task
            except asyncio.CancelledError:
                pass
        await self.transport.close()


# Test with a mock MCP server
async def test_mcp_protocol():
    """Test MCP protocol with mock server that implements basic MCP flow"""
    mock_server = """
import sys, json

# Mock server responses
responses = {
    "initialize": {"result": {"protocolVersion": "2024-11-05", "serverInfo": {"name": "test-server"}}},
    "tools/list": {"result": {"tools": [{"name": "echo", "description": "Echo input", "inputSchema": {"type": "object"}}]}}
}

for line in sys.stdin:
    msg = json.loads(line.strip())
    method = msg.get("method")
    msg_id = msg.get("id")

    if method == "initialized":
        continue  # No response needed

    if method in responses:
        response = responses[method].copy()
        response["id"] = msg_id
        print(json.dumps(response))
        sys.stdout.flush()
    elif method == "tools/call":
        response = {"id": msg_id, "result": {"content": [{"type": "text", "text": f"Called {msg['params']['name']}"}]}}
        print(json.dumps(response))
        sys.stdout.flush()
"""

    transport = StdioTransport(["python3", "-c", mock_server])
    client = MCPClient(transport)

    # Test initialization
    success = await client.initialize()
    if success:
        print(f"✓ Connected to server: {client.server_info}")
        print(f"✓ Found tools: {[t.name for t in client.tools]}")
        
        # Test tool call (response handler already running)
        if client.tools:
            result = await client.call_tool("echo", {"text": "Hello MCP!"})
            print(f"✓ Tool result: {result}")

    await client.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_mcp_protocol())
