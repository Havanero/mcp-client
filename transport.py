#!/usr/bin/env python3
"""
MCP Client - Stdio Transport Layer

Handles process communication with MCP servers via stdin/stdout.
Uses async subprocess for non-blocking I/O.
"""
import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Optional


@dataclass
class MCPMessage:
    """MCP protocol message wrapper"""
    method: str
    params: Dict[str, Any]
    id: Optional[str] = None

    def to_json(self) -> str:
        msg = {"method": self.method, "params": self.params}
        if self.id:
            msg["id"] = self.id
        return json.dumps(msg)


class StdioTransport:
    """Async stdio transport for MCP server communication"""

    def __init__(self, server_command: list[str]):
        self.server_command = server_command
        self.process: Optional[asyncio.subprocess.Process] = None
        self._message_counter = 0

    async def connect(self) -> None:
        """Start the MCP server process"""
        self.process = await asyncio.create_subprocess_exec(
            *self.server_command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        logging.info(f"Connected to MCP server: {' '.join(self.server_command)}")

    async def send_message(self, message: MCPMessage) -> None:
        """Send message to MCP server"""
        if not self.process or not self.process.stdin:
            raise RuntimeError("Not connected to server")

        json_msg = message.to_json() + "\n"
        self.process.stdin.write(json_msg.encode())
        await self.process.stdin.drain()
        logging.debug(f"Sent: {json_msg.strip()}")

    async def read_messages(self) -> AsyncIterator[Dict[str, Any]]:
        """Read messages from MCP server"""
        if not self.process or not self.process.stdout:
            raise RuntimeError("Not connected to server")

        async for line in self.process.stdout:
            try:
                message = json.loads(line.decode().strip())
                logging.debug(f"Received: {message}")
                yield message
            except json.JSONDecodeError as e:
                logging.error(f"Invalid JSON received: {line} - {e}")

    def next_id(self) -> str:
        """Generate unique message ID"""
        self._message_counter += 1
        return str(self._message_counter)

    async def close(self) -> None:
        """Close connection to server"""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            logging.info("Disconnected from MCP server")


# Quick test function
async def test_transport():
    """Test the stdio transport with a simple echo"""
    transport = StdioTransport(["python3", "-c", """
import sys, json
for line in sys.stdin:
    msg = json.loads(line)
    response = {"id": msg.get("id"), "result": {"echo": msg}}
    print(json.dumps(response))
    sys.stdout.flush()
"""])

    await transport.connect()

    # Send test message
    test_msg = MCPMessage("test", {"hello": "world"}, transport.next_id())
    await transport.send_message(test_msg)

    # Read response
    async for response in transport.read_messages():
        print(f"Got response: {response}")
        break

    await transport.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(test_transport())
