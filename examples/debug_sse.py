#!/usr/bin/env python3
"""
Quick SSE Debug Tool - Test streaming directly
"""
import asyncio
import aiohttp
import json


async def debug_sse_stream():
    """Debug SSE streaming directly"""
    print("🔍 Debugging SSE streaming...")
    
    url = "http://localhost:8081/stream/tools/file_ops"
    params = {"operation": "list", "path": "."}
    
    async with aiohttp.ClientSession() as session:
        print(f"📡 Connecting to: {url}")
        print(f"📋 Params: {params}")
        
        try:
            async with session.get(url, params=params) as response:
                print(f"📊 Status: {response.status}")
                print(f"📜 Headers: {dict(response.headers)}")
                
                if response.status != 200:
                    error_text = await response.text()
                    print(f"❌ Error: {error_text}")
                    return
                
                print("🌊 Reading SSE stream...")
                buffer = []
                message_count = 0
                
                async for line in response.content:
                    line_str = line.decode('utf-8').rstrip('\r\n')
                    print(f"📨 Line: {repr(line_str)}")
                    
                    if line_str == '':
                        # End of message
                        if buffer:
                            print(f"🔍 Message {message_count}: {buffer}")
                            message_count += 1
                            buffer = []
                    else:
                        buffer.append(line_str)
                    
                    # Stop after a few messages for debugging
                    if message_count >= 5:
                        break
                        
        except Exception as e:
            print(f"❌ Stream error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    print("🚀 Make sure SSE server is running with DEBUG logging")
    asyncio.run(debug_sse_stream())
