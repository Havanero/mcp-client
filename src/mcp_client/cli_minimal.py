#!/usr/bin/env python3
"""
Minimal CLI for Basic MCP Client

Avoids complex imports that might be causing issues.
"""
import asyncio
import os
import sys
from typing import Optional

import click

# Only import what we absolutely need for basic client
try:
    from .basic_client import main as basic_client_runner
    BASIC_CLIENT_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Warning: Could not import basic_client: {e}")
    BASIC_CLIENT_AVAILABLE = False
    basic_client_runner = None

# Try to import other components, but don't fail if they're not available
try:
    from .config import get_available_models
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    get_available_models = None

@click.command()
@click.option("--mcp-url", default="http://localhost:8081", help="MCP server URL")
@click.option("--debug", is_flag=True, help="Enable debug logging")
def basic(mcp_url: str, debug: bool):
    """
    Basic MCP Client - Protocol Only
    
    Pure MCP protocol communication without LLM integration.
    """
    if not BASIC_CLIENT_AVAILABLE:
        print("❌ Basic MCP client not available")
        print("💡 Check package installation: pip install -e .")
        return
    
    if debug:
        os.environ["DEBUG"] = "true"
        os.environ["LOG_LEVEL"] = "DEBUG"
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    if mcp_url:
        os.environ["MCP_BASE_URL"] = mcp_url
    
    print("🔧 Starting Basic MCP Client (Protocol Only)")
    print(f"🔗 Connecting to: {mcp_url}")
    
    try:
        asyncio.run(basic_client_runner())
    except KeyboardInterrupt:
        print("\\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        if debug:
            import traceback
            traceback.print_exc()

@click.command()
def doctor():
    """Diagnose basic MCP client setup"""
    print("🔍 Basic MCP Client Diagnosis")
    print("=" * 40)
    
    # Check basic client availability
    print(f"\\n🔧 Basic Client:")
    print(f"  Available: {'✅ Yes' if BASIC_CLIENT_AVAILABLE else '❌ No'}")
    
    if BASIC_CLIENT_AVAILABLE:
        try:
            from mcp_client.basic_client import BasicMCPClient
            from mcp_client.transports.jsonrpc import MCPJSONRPCClient
            print(f"  Transport: ✅ JSON-RPC available")
        except ImportError as e:
            print(f"  Transport: ❌ Import error: {e}")
    
    # Check server
    print(f"\\n🌐 Server:")
    mcp_url = os.getenv('MCP_BASE_URL', 'http://localhost:8081')
    print(f"  URL: {mcp_url}")
    
    try:
        import aiohttp
        import asyncio
        
        async def check_server():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{mcp_url}/health", timeout=5) as response:
                        if response.status == 200:
                            data = await response.json()
                            return True, data
                        else:
                            return False, f"HTTP {response.status}"
            except Exception as e:
                return False, str(e)
        
        server_ok, server_info = asyncio.run(check_server())
        if server_ok:
            print(f"  Status: ✅ Running")
            if isinstance(server_info, dict):
                print(f"  Tools: {server_info.get('tools', 0)}")
        else:
            print(f"  Status: ❌ {server_info}")
            
    except ImportError:
        print(f"  Status: ❓ Cannot check (aiohttp not available)")
    
    # Recommendations
    print(f"\\n💡 Quick Start:")
    print(f"  mcp-basic-minimal           # Start basic client")
    print(f"  mcp-basic-minimal --debug   # Debug mode")

@click.group()
def cli():
    """Minimal MCP Client"""
    pass

# Register commands
cli.add_command(basic, name="basic")
cli.add_command(doctor, name="doctor")

# Entry point functions
def basic_client_main():
    """Entry point for basic MCP client (minimal version)"""
    if not BASIC_CLIENT_AVAILABLE:
        print("❌ Basic MCP client not available")
        print("💡 Check package installation: pip install -e .")
        sys.exit(1)
    
    print("🔧 Starting Basic MCP Client (Minimal Version)")
    try:
        asyncio.run(basic_client_runner())
    except KeyboardInterrupt:
        print("\\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# Alternative entry point that bypasses click
def simple_basic_main():
    """Super simple entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Basic MCP Client - connects to http://localhost:8081")
        print("Usage: mcp-basic-simple [--debug]")
        return
    
    if "--debug" in sys.argv:
        os.environ["DEBUG"] = "true"
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    if not BASIC_CLIENT_AVAILABLE:
        print("❌ Basic client not available - check installation")
        sys.exit(1)
    
    print("🔧 Basic MCP Client (Simple)")
    try:
        asyncio.run(basic_client_runner())
    except KeyboardInterrupt:
        print("\\n👋 Goodbye!")

if __name__ == "__main__":
    cli()
