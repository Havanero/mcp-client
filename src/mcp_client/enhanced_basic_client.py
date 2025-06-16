#!/usr/bin/env python3
"""
Enhanced Basic MCP Client - Protocol-only interface with advanced diagnostics
Pure MCP protocol communication without LLM integration

Búvár-style enhancements:
- Comprehensive error handling with context
- Tool validation and parameter checking  
- Connection diagnostics and auto-recovery
- Async-first design with proper lifecycle management
"""
import asyncio
import json
import logging
import os
import traceback
from typing import Dict, Any, List, Optional
from functools import wraps

from .client import MCPClient
from .config import MCPConfig


def async_error_handler(func):
    """Decorator for comprehensive async error handling"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except asyncio.TimeoutError:
            print(f"⏰ Timeout in {func.__name__}: Operation took too long")
            raise
        except ConnectionError as e:
            print(f"🔌 Connection error in {func.__name__}: {e}")
            raise
        except Exception as e:
            print(f"❌ Unexpected error in {func.__name__}: {e}")
            if os.getenv("DEBUG"):
                traceback.print_exc()
            raise
    return wrapper


class EnhancedBasicMCPClient:
    """
    Enhanced Basic MCP protocol client with comprehensive diagnostics
    
    Features:
    - Advanced error handling and diagnostics
    - Tool validation and parameter checking
    - Connection health monitoring
    - Auto-recovery mechanisms
    """
    
    def __init__(self, mcp_url: str = "http://localhost:8081"):
        self.mcp_url = mcp_url
        self.client = None
        self.tools_cache: List[Dict[str, Any]] = []
        self.connection_healthy = False
        self.logger = logging.getLogger("basic_mcp_client")
        
    @async_error_handler
    async def connect(self) -> bool:
        """Connect to MCP server with enhanced diagnostics"""
        try:
            # Create SSE client
            from .transports.sse import SSEMCPClient
            self.client = SSEMCPClient(self.mcp_url)
            
            print(f"🔌 Connecting to {self.mcp_url}...")
            
            # Test connection with health check
            health = await asyncio.wait_for(self.client.get_health(), timeout=10.0)
            
            print(f"✅ Connected to MCP server")
            print(f"   Status: {health.get('status', 'unknown')}")
            print(f"   Version: {health.get('version', 'unknown')}")
            
            self.connection_healthy = True
            
            # Cache available tools
            await self._refresh_tools_cache()
            
            return True
            
        except asyncio.TimeoutError:
            print(f"❌ Connection timeout to {self.mcp_url}")
            print(f"💡 Is the MCP server running on {self.mcp_url}?")
            return False
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            print(f"💡 Check if MCP server is running and accessible")
            return False
    
    @async_error_handler
    async def _refresh_tools_cache(self):
        """Refresh cached tools list"""
        if not self.client:
            return
            
        try:
            self.tools_cache = await self.client.get_tools()
            print(f"🔧 Discovered {len(self.tools_cache)} tools")
        except Exception as e:
            self.logger.warning(f"Failed to refresh tools cache: {e}")
            self.tools_cache = []
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools with enhanced information"""
        if not self.client:
            raise RuntimeError("Not connected")
        
        if not self.tools_cache:
            await self._refresh_tools_cache()
            
        return self.tools_cache
    
    def _validate_tool_exists(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Validate tool exists and return its metadata"""
        tool = next((t for t in self.tools_cache if t["name"] == tool_name), None)
        if not tool:
            available = [t["name"] for t in self.tools_cache]
            print(f"❌ Tool '{tool_name}' not found!")
            print(f"💡 Available tools: {', '.join(available) if available else 'None'}")
            return None
        return tool
    
    def _validate_tool_arguments(self, tool: Dict[str, Any], arguments: Dict[str, Any]) -> bool:
        """Validate tool arguments against schema"""
        schema = tool.get("inputSchema", {})
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        
        # Check required parameters
        missing_required = [req for req in required if req not in arguments]
        if missing_required:
            print(f"❌ Missing required parameters: {', '.join(missing_required)}")
            return False
        
        # Show parameter info if no arguments provided but parameters exist
        if not arguments and properties:
            print(f"💡 Tool '{tool['name']}' accepts parameters:")
            for param, info in properties.items():
                param_type = info.get("type", "unknown")
                description = info.get("description", "No description")
                required_marker = " (required)" if param in required else ""
                print(f"   • {param} ({param_type}){required_marker}: {description}")
            print(f"💡 Example: call {tool['name']} {{\"param\": \"value\"}}")
            return len(required) == 0  # Only proceed if no required params
        
        return True
    
    @async_error_handler
    async def call_tool(self, name: str, arguments: Dict[str, Any] = None) -> Any:
        """Call a tool with comprehensive validation and error handling"""
        if not self.client:
            raise RuntimeError("Not connected")
        
        # Validate tool exists
        tool = self._validate_tool_exists(name)
        if not tool:
            return None
        
        # Validate arguments
        arguments = arguments or {}
        if not self._validate_tool_arguments(tool, arguments):
            return None
        
        print(f"⚡ Calling tool: {name}")
        if arguments:
            print(f"📝 Arguments: {json.dumps(arguments, indent=2)}")
        
        try:
            result_data = None
            event_count = 0
            
            async for event in self.client.stream_tool(name, arguments):
                event_count += 1
                event_type = event.get("event")
                data = event.get("data", {})
                
                self.logger.debug(f"📨 Event {event_count}: {event_type} | {data}")
                
                if event_type == "started":
                    print(f"🚀 Tool execution started")
                elif event_type == "progress":
                    message = data.get("message", "Processing...")
                    progress = data.get("progress")
                    if progress is not None:
                        print(f"📈 Progress: {message} ({progress}%)")
                    else:
                        print(f"📈 Progress: {message}")
                elif event_type == "result":
                    result_data = data.get("result", data)
                    print(f"📄 Result received")
                    break
                elif event_type == "completed":
                    duration = data.get("duration", 0)
                    print(f"🏁 Completed in {duration:.3f}s")
                    break
                elif event_type == "error":
                    error_msg = data.get("error", "Unknown error")
                    error_code = data.get("code", "UNKNOWN")
                    print(f"❌ Tool error [{error_code}]: {error_msg}")
                    raise Exception(f"Tool error: {error_msg}")
                else:
                    # Handle unexpected event types
                    print(f"📨 Event: {event_type} | {data}")
            
            if event_count == 0:
                print("⚠️  No events received from tool execution")
                print("💡 The tool might not support streaming or the server might be unresponsive")
            
            return result_data
            
        except asyncio.TimeoutError:
            print(f"⏰ Tool '{name}' execution timed out")
            print(f"💡 The tool might be processing a complex request")
            raise
        except Exception as e:
            print(f"❌ Tool execution failed: {e}")
            if "404" in str(e):
                print(f"💡 Tool '{name}' endpoint not found - server might not support this tool")
            elif "500" in str(e):
                print(f"💡 Server error - check server logs for details")
            raise
    
    @async_error_handler
    async def check_connection_health(self) -> bool:
        """Check if connection is still healthy"""
        if not self.client:
            return False
        
        try:
            await asyncio.wait_for(self.client.get_health(), timeout=5.0)
            self.connection_healthy = True
            return True
        except Exception:
            self.connection_healthy = False
            return False
    
    async def disconnect(self):
        """Disconnect from server"""
        if self.client:
            try:
                await self.client.disconnect()
                print("👋 Disconnected from MCP server")
            except Exception as e:
                self.logger.warning(f"Error during disconnect: {e}")
            finally:
                self.client = None
                self.connection_healthy = False


async def run_enhanced_cli():
    """Run enhanced MCP CLI interface with comprehensive diagnostics"""
    print("🔧 Enhanced Basic MCP Client - Protocol Only")
    print("=" * 60)
    print("Pure MCP protocol communication with advanced diagnostics")
    print("Features: Tool validation, error diagnostics, auto-recovery")
    print()
    
    # Enable debug mode if requested
    if os.getenv("DEBUG"):
        logging.basicConfig(level=logging.DEBUG)
        print("🐛 Debug mode enabled")
    
    mcp_url = os.getenv("MCP_BASE_URL", "http://localhost:8081")
    client = EnhancedBasicMCPClient(mcp_url)
    
    try:
        # Connect to server
        connected = await client.connect()
        if not connected:
            print("💡 Troubleshooting:")
            print("   1. Start the MCP server: python server.py")
            print("   2. Check the URL is correct")
            print("   3. Verify network connectivity")
            return
        
        # List available tools
        tools = await client.list_tools()
        print(f"\\n🔧 Available Tools ({len(tools)}):")
        for i, tool in enumerate(tools, 1):
            name = tool["name"]
            desc = tool.get("description", "No description")
            print(f"  {i}. {name}: {desc}")
            
            # Show if tool has required parameters
            schema = tool.get("inputSchema", {})
            required = schema.get("required", [])
            if required:
                print(f"     ⚠️  Requires: {', '.join(required)}")
        
        print(f"\\n📋 Enhanced Commands:")
        print(f"  list                    - List available tools with details")
        print(f"  call <tool> [args]      - Call a tool with validation")
        print(f"  help <tool>             - Show detailed tool help")
        print(f"  health                  - Check connection health")
        print(f"  debug                   - Toggle debug mode")
        print(f"  exit                    - Exit client")
        print(f"\\n💡 Examples:")
        print(f"  call echo {{\\\"text\\\": \\\"Hello World!\\\"}}")
        print(f"  call opensearch {{\\\"query\\\": \\\"example search\\\"}}")
        print(f"  help opensearch")
        print()
        
        # Interactive loop
        while True:
            try:
                # Check connection health periodically
                if not await client.check_connection_health():
                    print("⚠️  Connection lost! Attempting to reconnect...")
                    if not await client.connect():
                        print("❌ Failed to reconnect. Exiting...")
                        break
                
                command = input("mcp> ").strip()
                
                if not command:
                    continue
                    
                if command == "exit":
                    print("👋 Goodbye!")
                    break
                    
                elif command == "list":
                    tools = await client.list_tools()
                    print(f"\\n🔧 Available Tools ({len(tools)}):")
                    for tool in tools:
                        name = tool["name"] 
                        desc = tool.get("description", "No description")
                        print(f"  • {name}: {desc}")
                        
                        # Show parameter details
                        schema = tool.get("inputSchema", {})
                        properties = schema.get("properties", {})
                        required = schema.get("required", [])
                        
                        if properties:
                            params = []
                            for param, info in properties.items():
                                param_type = info.get("type", "any")
                                required_marker = "*" if param in required else ""
                                params.append(f"{param}({param_type}){required_marker}")
                            print(f"    📋 Parameters: {', '.join(params)}")
                            print(f"    💡 * = required")
                    print()
                
                elif command.startswith("call "):
                    # Parse tool call with enhanced validation
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
                                # Enhanced key=value parsing
                                if "=" in args_str:
                                    for pair in args_str.split():
                                        if "=" in pair:
                                            key, value = pair.split("=", 1)
                                            # Intelligent type conversion
                                            if value.isdigit():
                                                arguments[key] = int(value)
                                            elif value.replace(".", "").isdigit():
                                                arguments[key] = float(value)
                                            elif value.lower() in ["true", "false"]:
                                                arguments[key] = value.lower() == "true"
                                            else:
                                                arguments[key] = value
                                else:
                                    # Treat as single query parameter
                                    arguments = {"query": args_str}
                                    
                        except json.JSONDecodeError as e:
                            print(f"❌ Invalid JSON arguments: {e}")
                            print(f"💡 Use JSON format: {{\\\"key\\\": \\\"value\\\"}}")
                            print(f"💡 Or key=value format: key=value key2=value2")
                            continue
                    
                    # Execute tool with validation
                    try:
                        result = await client.call_tool(tool_name, arguments)
                        
                        if result is not None:
                            print(f"✅ Tool result:")
                            
                            # Enhanced result formatting
                            if isinstance(result, dict) and "content" in result:
                                content = result["content"]
                                for item in content:
                                    if isinstance(item, dict) and "text" in item:
                                        print(f"  📄 {item['text']}")
                                    else:
                                        print(f"  📊 {item}")
                            elif isinstance(result, dict):
                                print(json.dumps(result, indent=2))
                            else:
                                print(f"  {result}")
                        
                    except Exception as e:
                        print(f"❌ Error: {e}")
                        print(f"💡 Use 'help {tool_name}' for parameter details")
                
                elif command.startswith("help "):
                    tool_name = command[5:].strip()
                    tool = next((t for t in tools if t["name"] == tool_name), None)
                    if tool:
                        print(f"\\n🔧 Tool: {tool['name']}")
                        print(f"📝 Description: {tool.get('description', 'No description')}")
                        
                        schema = tool.get("inputSchema", {})
                        if schema:
                            print(f"\\n📋 Input Schema:")
                            properties = schema.get("properties", {})
                            required = schema.get("required", [])
                            
                            if properties:
                                print(f"Parameters:")
                                for param, info in properties.items():
                                    param_type = info.get("type", "any")
                                    description = info.get("description", "No description")
                                    required_marker = " (required)" if param in required else ""
                                    print(f"  • {param} ({param_type}){required_marker}")
                                    print(f"    {description}")
                                
                                print(f"\\n💡 Example usage:")
                                if required:
                                    example_args = {req: f"<{req}_value>" for req in required[:2]}
                                    print(f"  call {tool_name} {json.dumps(example_args)}")
                                else:
                                    print(f"  call {tool_name}")
                            else:
                                print(f"  No parameters required")
                        print()
                    else:
                        print(f"❌ Tool '{tool_name}' not found")
                        available = [t["name"] for t in tools]
                        print(f"💡 Available: {', '.join(available)}")
                
                elif command == "health":
                    healthy = await client.check_connection_health()
                    status = "✅ Healthy" if healthy else "❌ Unhealthy"
                    print(f"🏥 Connection health: {status}")
                    
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
                print("\\n👋 Goodbye!")
                break
            except EOFError:
                print("\\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                if os.getenv("DEBUG"):
                    traceback.print_exc()
    
    finally:
        await client.disconnect()


async def main():
    """Main entry point for enhanced basic MCP client"""
    await run_enhanced_cli()


if __name__ == "__main__":
    # Set default logging level (can be overridden with DEBUG env var)
    log_level = logging.DEBUG if os.getenv("DEBUG") else logging.WARNING
    logging.basicConfig(level=log_level)
    asyncio.run(main())
