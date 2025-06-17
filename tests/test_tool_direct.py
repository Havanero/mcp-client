#!/usr/bin/env python3
"""
Test tool execution directly - bypass streaming
"""
import asyncio
import os
import sys

# Add path for imports
sys.path.insert(0, os.path.abspath("../mcp-server"))


async def test_tool_direct():
    """Test file_ops tool directly"""
    try:
        from plugin_manager import PluginManager

        print("🔧 Loading plugin manager...")
        plugin_manager = PluginManager("../mcp-server/tools")

        print("🔄 Discovering tools...")
        tools = await plugin_manager.discover_and_load_tools()
        print(f"✅ Loaded tools: {list(tools.keys())}")

        if "file_ops" in tools:
            print("\n🧪 Testing file_ops tool directly...")
            arguments = {"operation": "list", "path": "."}
            print(f"📋 Arguments: {arguments}")

            result = await plugin_manager.execute_tool("file_ops", arguments)
            print(f"✅ Result: {result}")
            print(f"📊 Result type: {type(result)}")

        else:
            print("❌ file_ops tool not found")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_tool_direct())
