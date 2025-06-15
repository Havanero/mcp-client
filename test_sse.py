#!/usr/bin/env python3
"""
SSE MCP Quick Test - Test different argument formats
"""
import asyncio
import sys
from sse_client import create_sse_client


async def test_sse_formats():
    """Test different argument formats for SSE streaming"""
    print("🧪 Testing SSE MCP Client Argument Formats")
    print("=" * 50)
    
    client = create_sse_client("http://localhost:8081")
    
    try:
        # Test 1: Empty arguments
        print("\n1️⃣ Testing: Empty arguments")
        print("🌊 Streaming greet with no arguments...")
        async for event in client.stream_tool("greet"):
            if event.get('event') == 'result':
                print(f"✅ Result: {event.get('data')}")
                break
        
        # Test 2: Simple key=value format  
        print("\n2️⃣ Testing: Key=value format")
        print("🌊 Streaming greet with name=SSE style=excited...")
        arguments = {"name": "SSE", "style": "excited"}
        async for event in client.stream_tool("greet", arguments):
            if event.get('event') == 'result':
                print(f"✅ Result: {event.get('data')}")
                break
        
        # Test 3: JSON format
        print("\n3️⃣ Testing: JSON format")
        print("🌊 Streaming current_time with format=readable...")
        arguments = {"format": "readable"}
        async for event in client.stream_tool("current_time", arguments):
            if event.get('event') == 'result':
                print(f"✅ Result: {event.get('data')}")
                break
        
        # Test 4: LLM streaming
        print("\n4️⃣ Testing: LLM streaming")
        print("🌊 Streaming LLM with prompt...")
        tokens = []
        async for event in client.stream_llm("Hello from SSE MCP"):
            if event.get('event') == 'token':
                token = event.get('data', {}).get('token', '')
                tokens.append(token)
                print(f"🔤 {token}", end=" ", flush=True)
            elif event.get('event') == 'completed':
                print(f"\n✅ Full response: {' '.join(tokens)}")
                break
        
        print("\n🎉 All tests completed!")
        
    except Exception as e:
        print(f"❌ Test error: {e}")
    
    finally:
        await client.disconnect()


if __name__ == "__main__":
    print("🚀 Make sure SSE server is running: python3 server_sse.py")
    asyncio.run(test_sse_formats())
