#!/usr/bin/env python3
"""
Test script for MCP Basic Client fixes

Demonstrates the enhanced error handling and tool validation
"""
import asyncio
import sys
import os

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_basic_client():
    """Test the enhanced basic client functionality"""
    from mcp_client.basic_client import BasicMCPClient
    
    print("🧪 Testing Enhanced Basic MCP Client")
    print("=" * 50)
    
    # Test connection
    client = BasicMCPClient()
    
    print("1. Testing connection...")
    connected = await client.connect()
    
    if not connected:
        print("❌ Connection failed - MCP server not running?")
        print("💡 Start server with: python server.py")
        return
    
    print("✅ Connection successful!")
    
    # Test tool listing
    print("\n2. Testing tool discovery...")
    tools = await client.list_tools()
    print(f"✅ Found {len(tools)} tools")
    
    if tools:
        print("\n3. Testing tool validation...")
        # Test with non-existent tool
        result = await client.call_tool("nonexistent_tool")
        print(f"✅ Non-existent tool handled: {result is None}")
        
        # Test with existing tool (if any)
        if tools:
            first_tool = tools[0]
            tool_name = first_tool["name"]
            print(f"\n4. Testing tool call: {tool_name}")
            
            try:
                # Call without arguments first
                result = await client.call_tool(tool_name)
                print(f"✅ Tool call completed")
            except Exception as e:
                print(f"⚠️  Tool call failed (expected): {e}")
                
                # Try with opensearch if available
                opensearch_tool = next((t for t in tools if t["name"] == "opensearch"), None)
                if opensearch_tool:
                    print("\n5. Testing opensearch with proper arguments...")
                    try:
                        result = await client.call_tool("opensearch", {"query": "test search"})
                        print(f"✅ OpenSearch with arguments: {result is not None}")
                    except Exception as e:
                        print(f"⚠️  OpenSearch failed: {e}")
    
    await client.disconnect()
    print("\n🎯 Test completed!")

if __name__ == "__main__":
    asyncio.run(test_basic_client())
