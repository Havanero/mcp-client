#!/usr/bin/env python3
"""
MCP Client - Interactive CLI Interface

Provides user-friendly commands for MCP server interaction:
- list: Show available tools
- call <tool> [args]: Execute tools with JSON args
- help [tool]: Show tool documentation
- exit: Close connection and exit
"""
import asyncio
import json
import logging
import sys
from functools import lru_cache
from typing import Any, Dict, List, Optional

from protocol import MCPClient, MCPTool
from transport import StdioTransport


class MCPCliClient:
    """Interactive CLI wrapper for MCP client"""

    def __init__(self, server_command: List[str]):
        self.server_command = server_command
        self.client: Optional[MCPClient] = None
        self.running = False

    async def start(self) -> bool:
        """Initialize connection and start CLI"""
        print("🔌 Connecting to MCP server...")

        transport = StdioTransport(self.server_command)
        self.client = MCPClient(transport)

        success = await self.client.initialize()
        if success:
            print(f"✅ Connected! Server: {self.client.server_info.get('serverInfo', {}).get('name', 'Unknown')}")
            print(f"📦 Available tools: {len(self.client.tools)}")
            print("Type 'help' for commands or 'list' to see tools\n")
            return True
        else:
            print("❌ Failed to connect to server")
            return False

    async def run(self) -> None:
        """Main CLI loop"""
        self.running = True

        while self.running:
            try:
                # Get user input
                command = await self._get_input("mcp> ")
                if not command.strip():
                    continue

                await self._execute_command(command.strip())

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    async def _get_input(self, prompt: str) -> str:
        """Async input handling"""
        return await asyncio.get_event_loop().run_in_executor(None, input, prompt)

    async def _execute_command(self, command: str) -> None:
        """Parse and execute CLI commands"""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "help":
            await self._cmd_help(args)
        elif cmd == "list":
            await self._cmd_list()
        elif cmd == "call":
            await self._cmd_call(args)
        elif cmd in ("exit", "quit", "q"):
            self.running = False
        elif cmd == "info":
            await self._cmd_info()
        else:
            print(f"❓ Unknown command: {cmd}")
            await self._cmd_help("")

    async def _cmd_help(self, tool_name: str = "") -> None:
        """Show help for commands or specific tool"""
        if tool_name:
            tool = self._find_tool(tool_name)
            if tool:
                print(f"\n🔧 Tool: {tool.name}")
                print(f"📝 Description: {tool.description}")
                print(f"⚙️  Input Schema:")
                print(json.dumps(tool.input_schema, indent=2))
                print(f"\n💡 Usage: call {tool.name} {{\"arg\": \"value\"}}")
            else:
                print(f"❌ Tool '{tool_name}' not found")
        else:
            print("\n📖 Available Commands:")
            print("  help [tool]    - Show this help or tool details")
            print("  list           - List available tools")
            print("  call <tool> <json_args> - Execute a tool")
            print("  info           - Show server information")
            print("  exit/quit/q    - Close connection and exit")
            print("\n💡 Example: call echo {\"text\": \"Hello World!\"}")

    async def _cmd_list(self) -> None:
        """List all available tools"""
        if not self.client or not self.client.tools:
            print("❌ No tools available")
            return

        print(f"\n🔧 Available Tools ({len(self.client.tools)}):")
        for i, tool in enumerate(self.client.tools, 1):
            print(f"  {i}. {tool.name}")
            print(f"     {tool.description}")
        print("\n💡 Use 'help <tool>' for details or 'call <tool> <args>' to execute")

    async def _cmd_call(self, args: str) -> None:
        """Execute a tool call"""
        if not args:
            print("❌ Usage: call <tool_name> <json_arguments>")
            return

        # Parse tool name and arguments
        parts = args.split(maxsplit=1)
        tool_name = parts[0]
        json_args = parts[1] if len(parts) > 1 else "{}"

        # Validate tool exists
        tool = self._find_tool(tool_name)
        if not tool:
            print(f"❌ Tool '{tool_name}' not found. Use 'list' to see available tools.")
            return

        try:
            # Parse JSON arguments
            arguments = json.loads(json_args)

            print(f"⚡ Calling {tool_name}...")
            result = await self.client.call_tool(tool_name, arguments)

            print("✅ Result:")
            self._pretty_print_result(result)

        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON arguments: {e}")
            print("💡 Example: call echo {\"text\": \"Hello World!\"}")
        except Exception as e:
            print(f"❌ Tool execution failed: {e}")

    async def _cmd_info(self) -> None:
        """Show server information"""
        if not self.client:
            print("❌ Not connected to server")
            return

        print(f"\n📊 Server Information:")
        print(f"  Protocol Version: {self.client.server_info.get('protocolVersion', 'Unknown')}")
        server_info = self.client.server_info.get('serverInfo', {})
        print(f"  Server Name: {server_info.get('name', 'Unknown')}")
        print(f"  Server Version: {server_info.get('version', 'Unknown')}")
        print(f"  Tools Available: {len(self.client.tools)}")

    @lru_cache(maxsize=128)
    def _find_tool(self, name: str) -> Optional[MCPTool]:
        """Find tool by name (cached for performance)"""
        if not self.client:
            return None
        return next((tool for tool in self.client.tools if tool.name == name), None)

    def _pretty_print_result(self, result: Dict[str, Any]) -> None:
        """Pretty print tool execution results"""
        content = result.get('content', [])

        if not content:
            print(json.dumps(result, indent=2))
            return

        for item in content:
            if item.get('type') == 'text':
                print(f"  📄 {item.get('text', '')}")
            elif item.get('type') == 'image':
                print(f"  🖼️  Image: {item.get('data', 'No data')[:50]}...")
            else:
                print(f"  📦 {json.dumps(item, indent=2)}")

    async def close(self) -> None:
        """Clean shutdown"""
        if self.client:
            await self.client.close()


async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python3 cli.py <server_command>")
        print("Example: python3 cli.py python3 my_mcp_server.py")
        return

    server_command = sys.argv[1:]
    cli = MCPCliClient(server_command)

    try:
        if await cli.start():
            await cli.run()
    finally:
        await cli.close()


if __name__ == "__main__":
    # Reduce noise in interactive mode
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(main())
