#!/usr/bin/env python3
"""
Basic MCP Client - Protocol-only interface
Pure MCP protocol communication without LLM integration
"""
import asyncio
import json
import logging
import os
from typing import Dict, Any, List

from .client import MCPClient
from .config import MCPConfig


class BasicMCPClient:
    """
    Basic MCP protocol client without LLM integration
    
    Features:
    - Direct MCP tool discovery and execution
    - Protocol-level communication
    - No AI/LLM dependencies
    """
    
    def __init__(self, mcp_url: str = "http://localhost:8081"):
        self.mcp_url = mcp_url
        self.client = None
        self.tools_cache = []  # Cache for available tools
        
    async def connect(self):
        """Connect to MCP server"""
        # Create basic MCP client without LLM
        mcp_config = MCPConfig(base_url=self.mcp_url)
        
        # For basic mode, we'll use the transport directly instead of full MCPClient
        from .transports.sse import SSEMCPClient
        self.client = SSEMCPClient(self.mcp_url)
        
        try:
            health = await self.client.get_health()
            print(f"✅ Connected to MCP server: {health.get('status', 'unknown')}")
            
            # Cache available tools
            self.tools_cache = await self.client.get_tools()
            print(f"🔧 Discovered {len(self.tools_cache)} tools")
            
            return True
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            print(f"💡 Make sure MCP server is running on {self.mcp_url}")
            return False
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools"""
        if not self.client:
            raise RuntimeError("Not connected")
        
        try:
            tools = await self.client.get_tools()
            return tools
        except Exception as e:
            print(f"❌ Error listing tools: {e}")
            return []
    
    async def call_tool(self, name: str, arguments: Dict[str, Any] = None) -> Any:
        """Call a tool directly"""
        if not self.client:
            raise RuntimeError("Not connected")
        
        # Validate tool exists first
        available_tools = [t["name"] for t in self.tools_cache] if hasattr(self, 'tools_cache') else []
        if available_tools and name not in available_tools:
            print(f"❌ Tool '{name}' not found!")
            print(f"💡 Available tools: {', '.join(available_tools)}")
            return None
        
        try:
            print(f"⚡ Calling tool: {name}")
            if arguments:
                print(f"📝 With arguments: {arguments}")
            
            result_data = None
            event_count = 0
            
            async for event in self.client.stream_tool(name, arguments or {}):
                event_count += 1
                event_type = event.get("event")
                data = event.get("data", {})
                
                if event_type == "started":
                    print(f"🚀 Tool execution started")
                elif event_type == "progress":
                    message = data.get("message", "Processing...")
                    print(f"📈 Progress: {message}")
                elif event_type == "result":
                    result_data = data.get("result", data)
                    print(f"📄 Result received")
                    break
                elif event_type == "completed":
                    print(f"🏁 Completed")
                    break
                elif event_type == "error":
                    error_msg = data.get("error", "Unknown error")
                    print(f"❌ Tool error: {error_msg}")
                    raise Exception(error_msg)
                else:
                    print(f"📨 Event: {event_type} | {data}")
            
            if event_count == 0:
                print("⚠️  No response from tool - it might require specific arguments")
                # Try to show tool help
                tool = next((t for t in self.tools_cache if t["name"] == name), None) if hasattr(self, 'tools_cache') else None
                if tool:
                    schema = tool.get("inputSchema", {})
                    required = schema.get("required", [])
                    if required:
                        print(f"💡 Required parameters: {', '.join(required)}")
                        print(f"💡 Example: call {name} {{\"param\": \"value\"}}")
            
            return result_data
            
        except Exception as e:
            print(f"❌ Tool execution failed: {e}")
            # Provide helpful error context
            if "404" in str(e):
                print(f"💡 Tool '{name}' endpoint not found")
            elif "timeout" in str(e).lower():
                print(f"💡 Tool execution timed out")
            elif "connection" in str(e).lower():
                print(f"💡 Connection issue - check if MCP server is running")
            raise
    
    async def disconnect(self):
        """Disconnect from server"""
        if self.client:
            await self.client.disconnect()


async def run_basic_cli():
    """Run basic MCP CLI interface"""
    print("🔧 Basic MCP Client - Protocol Only")
    print("=" * 50)
    print("This is a pure MCP protocol client without LLM integration.")
    print("You can discover and execute tools directly.\n")
    
    mcp_url = os.getenv("MCP_BASE_URL", "http://localhost:8081")
    client = BasicMCPClient(mcp_url)
    
    try:
        # Connect to server
        connected = await client.connect()
        if not connected:
            return
        
        # List available tools
        tools = await client.list_tools()
        print(f"\n🔧 Available Tools ({len(tools)}):")
        for i, tool in enumerate(tools, 1):
            print(f"  {i}. {tool['name']}: {tool.get('description', 'No description')}")
        
        print(f"\n📋 Enhanced Commands:")
        print(f"  list                    - List available tools with parameter info")
        print(f"  call <tool> [args]      - Call a tool with validation")
        print(f"  help <tool>             - Show detailed tool help and parameters")
        print(f"  debug                   - Toggle debug mode")
        print(f"  exit                    - Exit client")
        print(f"\n💡 Tool Call Examples:")
        print(f"  call echo {{\"text\": \"Hello World!\"}}")  # JSON format
        print(f"  call opensearch {{\"query\": \"search term\"}}")
        print(f"  call tool_name key=value key2=value2")  # Key=value format")
        print()
        
        # Interactive loop
        while True:
            try:
                command = input("mcp> ").strip()
                
                if not command:
                    continue
                    
                if command == "exit":
                    print("👋 Goodbye!")
                    break
                    
                elif command == "list":
                    tools = await client.list_tools()
                    print(f"\n🔧 Available Tools ({len(tools)}):")
                    for tool in tools:
                        name = tool["name"] 
                        desc = tool.get("description", "No description")
                        print(f"  • {name}: {desc}")
                        
                        # Show parameter summary
                        schema = tool.get("inputSchema", {})
                        properties = schema.get("properties", {})
                        required = schema.get("required", [])
                        
                        if properties:
                            param_summary = []
                            for param in properties.keys():
                                marker = "*" if param in required else ""
                                param_summary.append(f"{param}{marker}")
                            print(f"    📋 Parameters: {', '.join(param_summary)}")
                            if required:
                                print(f"    ⚠️  * = required")
                        else:
                            print(f"    📋 No parameters")
                    print(f"\n💡 Use 'help <tool>' for detailed parameter info")
                    print()
                
                elif command.startswith("call "):
                    # Parse tool call
                    parts = command[5:].strip().split(maxsplit=1)
                    tool_name = parts[0]
                    
                    arguments = {}
                    if len(parts) > 1:
                        args_str = parts[1]
                        try:
                            # Try to parse as JSON
                            if args_str.startswith("{"):
                                arguments = json.loads(args_str)
                            else:
                                # Simple key=value parsing
                                for pair in args_str.split():
                                    if "=" in pair:
                                        key, value = pair.split("=", 1)
                                        arguments[key] = value
                                    else:
                                        arguments["query"] = args_str
                                        break
                        except json.JSONDecodeError:
                            print("❌ Invalid JSON arguments")
                            continue
                    
                    try:
                        result = await client.call_tool(tool_name, arguments)
                        print(f"✅ Tool result:")
                        
                        # Pretty print result
                        if isinstance(result, dict) and "content" in result:
                            content = result["content"]
                            for item in content:
                                if isinstance(item, dict) and "text" in item:
                                    print(f"  {item['text']}")
                                else:
                                    print(f"  {item}")
                        else:
                            print(f"  {result}")
                        
                    except Exception as e:
                        print(f"❌ Error: {e}")
                
                elif command.startswith("help "):
                    tool_name = command[5:].strip()
                    # Find tool and show details
                    tool = next((t for t in tools if t["name"] == tool_name), None)
                    if tool:
                        print(f"\n🔧 Tool: {tool['name']}")
                        print(f"📝 Description: {tool.get('description', 'No description')}")
                        
                        schema = tool.get("inputSchema", {})
                        properties = schema.get("properties", {})
                        required = schema.get("required", [])
                        
                        if properties:
                            print(f"\n📋 Parameters:")
                            for param, info in properties.items():
                                param_type = info.get("type", "any")
                                description = info.get("description", "No description")
                                required_marker = " (required)" if param in required else ""
                                print(f"  • {param} ({param_type}){required_marker}: {description}")
                            
                            print(f"\n💡 Usage examples:")
                            if required:
                                example_args = {req: f"<{req}_value>" for req in required[:2]}
                                print(f"  call {tool_name} {json.dumps(example_args)}")
                            else:
                                print(f"  call {tool_name}  # No parameters required")
                                if properties:
                                    first_param = list(properties.keys())[0]
                                    print(f"  call {tool_name} {{\"{first_param}\": \"example_value\"}}")
                        else:
                            print(f"\n📋 No parameters required")
                        print()
                    else:
                        print(f"❌ Tool '{tool_name}' not found")
                        available = [t["name"] for t in tools]
                        print(f"💡 Available: {', '.join(available)}")
                
                elif command == "debug":
                    current_level = logging.getLogger().getEffectiveLevel()
                    if current_level == logging.DEBUG:
                        logging.getLogger().setLevel(logging.WARNING)
                        print("🔧 Debug mode: OFF")
                    else:
                        logging.getLogger().setLevel(logging.DEBUG)
                        print("🔧 Debug mode: ON")
                
                else:
                    print(f"❓ Unknown command: {command}")
                    print(f"💡 Type 'list' to see tools, 'call <tool>' to execute, 'exit' to quit")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except EOFError:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    finally:
        await client.disconnect()


async def main():
    """Main entry point for basic MCP client"""
    await run_basic_cli()


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)  # Quiet for basic mode
    asyncio.run(main())
