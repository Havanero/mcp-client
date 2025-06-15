#!/usr/bin/env python3
"""
Test Script - Verify LLM CLI Agent components
Quick tests for configuration, LLM client, and MCP integration
"""
import asyncio
import os
import sys

# Add the current directory to path
sys.path.append(os.path.dirname(__file__))

from llm_agent.config import ConfigManager, get_available_models
from llm_agent.llm_client import LLMClientFactory, LLMMessage
from llm_agent.mcp_orchestrator import MCPOrchestrator


async def test_configuration():
    """Test configuration loading"""
    print("🔧 Testing Configuration...")
    
    try:
        # Test environment config
        config = ConfigManager.load_from_env()
        print(f"✅ Environment config: {config.llm.provider} - {config.llm.model}")
    except Exception as e:
        print(f"⚠️  Environment config error: {e}")
    
    # Test direct config creation
    if api_key := os.getenv("OPENAI_API_KEY"):
        config = ConfigManager.create_openai_config(api_key, "gpt-3.5-turbo")
        print(f"✅ OpenAI config created: {config.llm.model}")
    
    # Show available models
    print(f"📋 OpenAI models: {list(get_available_models('openai').keys())}")
    print(f"📋 Anthropic models: {list(get_available_models('anthropic').keys())}")


async def test_llm_client():
    """Test LLM client functionality"""
    print("\n🤖 Testing LLM Client...")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set, skipping LLM test")
        return
    
    try:
        # Create config and client
        config = ConfigManager.create_openai_config(api_key, "gpt-3.5-turbo")
        client = LLMClientFactory.create_client(config.llm)
        
        # Test simple completion
        response = await client.simple_complete("Say 'Hello from LLM test!' if you can hear me.")
        print(f"✅ LLM response: {response[:100]}...")
        
        # Test message-based completion
        messages = [
            LLMMessage(role="system", content="You are a helpful assistant."),
            LLMMessage(role="user", content="What is 2+2?")
        ]
        response = await client.complete(messages)
        print(f"✅ Structured response: {response.content[:50]}...")
        
        await client.close()
        print("✅ LLM client test completed successfully")
        
    except Exception as e:
        print(f"❌ LLM client test failed: {e}")


async def test_mcp_connection():
    """Test MCP server connection"""
    print("\n🌊 Testing MCP Connection...")
    
    try:
        # Test with SSE client directly
        from sse_client import SSEMCPClient
        
        client = SSEMCPClient("http://localhost:8081")
        
        # Test health check
        health = await client.get_health()
        print(f"✅ MCP server health: {health.get('status', 'unknown')}")
        
        # Test tool discovery
        tools = await client.get_tools()
        print(f"✅ Found {len(tools)} tools: {[t['name'] for t in tools]}")
        
        # Test tool execution if file_ops is available
        if any(tool['name'] == 'file_ops' for tool in tools):
            print("🔧 Testing file_ops tool...")
            result_found = False
            
            async for event in client.stream_tool('file_ops', {'operation': 'list', 'path': '.'}):
                if event.get('event') == 'result':
                    result = event.get('data', {})
                    print(f"✅ file_ops result: {type(result.get('result', 'unknown'))}")
                    result_found = True
                    break
            
            if not result_found:
                print("⚠️  No result received from file_ops")
        
        await client.disconnect()
        print("✅ MCP connection test completed")
        
    except Exception as e:
        print(f"❌ MCP connection test failed: {e}")
        print("💡 Make sure MCP server is running: python3 ../mcp-server/server_sse.py")


async def test_full_integration():
    """Test full LLM + MCP integration"""
    print("\n🧠 Testing Full Integration...")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set, skipping integration test")
        return
    
    try:
        # Create agent components
        config = ConfigManager.create_openai_config(api_key, "gpt-3.5-turbo")
        llm_client = LLMClientFactory.create_client(config.llm)
        orchestrator = MCPOrchestrator(llm_client, config.mcp)
        
        # Test with orchestrator
        async with orchestrator.session():
            print("✅ Orchestrator session started")
            
            # Test tool discovery
            tools = await orchestrator.discover_tools()
            print(f"✅ Orchestrator found {len(tools)} tools")
            
            # Test simple chat
            response, context = await orchestrator.chat("What tools are available to you?")
            print(f"✅ Chat response: {response[:100]}...")
            
            # Test tool usage if file_ops is available
            if any(tool['name'] == 'file_ops' for tool in tools):
                print("🔧 Testing tool usage via orchestrator...")
                response, context = await orchestrator.chat("List the files in the current directory", context)
                print(f"✅ Tool usage response: {response[:100]}...")
        
        await llm_client.close()
        print("✅ Full integration test completed successfully")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests"""
    print("🧪 LLM CLI Agent Component Tests")
    print("=" * 50)
    
    await test_configuration()
    await test_llm_client()
    await test_mcp_connection()
    await test_full_integration()
    
    print("\n" + "=" * 50)
    print("🎉 Testing completed!")
    print("\n💡 If all tests pass, you're ready to run:")
    print("   python3 start_agent.py")


if __name__ == "__main__":
    asyncio.run(main())
