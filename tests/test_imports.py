#!/usr/bin/env python3
"""
Test script to verify MCP client imports and command structure
"""
import sys
import os

def test_imports():
    """Test that all imports work correctly"""
    print("🧪 Testing MCP Client imports...")
    
    try:
        # Test transport imports
        sys.path.insert(0, '/home/cubanguy/Projects/ai-framework/mcp-server/file-dir-projects/mcp-client/src')
        
        print("Testing transport imports...")
        from mcp_client.transports import SSETransport, HTTPTransport, WebSocketTransport, StdioTransport
        print("✅ Transport imports successful")
        
        print("Testing main package imports...")
        from mcp_client import MCPClient, MCPAgentCLI, MCPOrchestrator
        print("✅ Main package imports successful")
        
        print("Testing CLI entry points...")
        from mcp_client.cli import main, agent_main, basic_client_main
        print("✅ CLI entry points accessible")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def show_command_structure():
    """Show the available command structure"""
    print("\n📋 Available Commands:")
    print("=" * 50)
    
    commands = {
        "mcp": "General MCP client interface",
        "mcp-client": "Same as mcp",
        "mcp-agent": "Direct to LLM-enhanced agent",
        "mcp-basic": "Direct to basic MCP protocol client"
    }
    
    for cmd, desc in commands.items():
        print(f"  {cmd:<15} - {desc}")
    
    print(f"\n💡 Usage Examples:")
    print(f"  mcp-basic                    # Pure MCP protocol")
    print(f"  mcp-agent                    # LLM-enhanced MCP client")
    print(f"  mcp --basic                  # Basic via general interface")
    print(f"  mcp --provider=openai        # LLM via general interface")
    print(f"  mcp doctor                   # Setup diagnosis")

if __name__ == "__main__":
    print("🔧 MCP Client - Import & Command Structure Test")
    print("=" * 60)
    
    success = test_imports()
    show_command_structure()
    
    if success:
        print(f"\n✅ All tests passed! Ready to install:")
        print(f"   cd /home/cubanguy/Projects/ai-framework/mcp-server/file-dir-projects/mcp-client")
        print(f"   pip install -e .")
        print(f"   mcp-basic  # Test basic MCP client")
    else:
        print(f"\n❌ Some tests failed. Check the imports.")
