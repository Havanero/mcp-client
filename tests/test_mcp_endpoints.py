#!/usr/bin/env python3
"""
Test MCP server endpoints directly
"""
import asyncio
import aiohttp
import json

async def test_mcp_endpoints():
    """Test MCP server endpoints"""
    base_url = "http://localhost:8081"
    
    async with aiohttp.ClientSession() as session:
        
        # Test health endpoint
        try:
            print("🏥 Testing /health endpoint...")
            async with session.get(f"{base_url}/health") as response:
                print(f"  Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"  Response: {json.dumps(data, indent=2)}")
                else:
                    text = await response.text()
                    print(f"  Error: {text}")
        except Exception as e:
            print(f"  ❌ Health endpoint error: {e}")
        
        print()
        
        # Test tools endpoint
        try:
            print("🔧 Testing /tools endpoint...")
            async with session.get(f"{base_url}/tools") as response:
                print(f"  Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"  Response: {json.dumps(data, indent=2)}")
                    
                    # Check if it has the expected format
                    if "tools" in data:
                        tools = data["tools"]
                        print(f"  ✅ Found {len(tools)} tools: {[t.get('name', 'unnamed') for t in tools]}")
                    else:
                        print(f"  ⚠️ Response doesn't have 'tools' key. Keys: {list(data.keys())}")
                else:
                    text = await response.text()
                    print(f"  Error: {text}")
        except Exception as e:
            print(f"  ❌ Tools endpoint error: {e}")
        
        print()
        
        # Test what endpoints are available
        try:
            print("📋 Testing available endpoints...")
            endpoints = ["/", "/stats", "/stream", "/api/tools"]
            
            for endpoint in endpoints:
                try:
                    async with session.get(f"{base_url}{endpoint}") as response:
                        print(f"  {endpoint}: {response.status}")
                        if response.status == 200 and endpoint != "/stream":
                            try:
                                data = await response.json()
                                if "tools" in data:
                                    print(f"    🔧 Has tools: {len(data['tools'])}")
                            except:
                                pass
                except Exception as e:
                    print(f"  {endpoint}: Error - {e}")
                    
        except Exception as e:
            print(f"  ❌ Endpoint discovery error: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_endpoints())
