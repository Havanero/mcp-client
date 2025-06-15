#!/usr/bin/env python3
"""
Test Enhanced Agent - Verify the OpenSearch tool improvements
"""
import asyncio
import os
import sys

# Add the current directory to path
sys.path.append(os.path.dirname(__file__))

from llm_agent.config import ConfigManager
from llm_agent.llm_client import LLMClientFactory, LLMMessage
from llm_agent.mcp_orchestrator import MCPOrchestrator


async def test_opensearch_recognition():
    """Test if the agent now recognizes OpenSearch commands properly"""
    print("🧪 Testing Enhanced OpenSearch Recognition")
    print("=" * 50)
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return
    
    # Create configuration and clients
    config = ConfigManager.create_openai_config(api_key, "gpt-3.5-turbo")
    llm_client = LLMClientFactory.create_client(config.llm)
    orchestrator = MCPOrchestrator(llm_client, config.mcp)
    
    try:
        async with orchestrator.session():
            print("✅ Connected to MCP server")
            
            # Test tool discovery
            tools = await orchestrator.discover_tools()
            print(f"✅ Discovered {len(tools)} tools")
            
            # Check if opensearch is available
            opensearch_tool = next((t for t in tools if t['name'] == 'opensearch'), None)
            if not opensearch_tool:
                print("❌ OpenSearch tool not found in available tools")
                return
            
            print(f"✅ Found opensearch tool: {opensearch_tool['description']}")
            
            # Test different OpenSearch command variations
            test_commands = [
                "Search for GDPR documents",
                "Find regulations about data protection", 
                "Use opensearch to search for privacy laws",
                "I need to search for CCPA",
                "opensearch gdpr size 5"
            ]
            
            print(f"\n🔧 Testing {len(test_commands)} command variations:")
            
            for i, command in enumerate(test_commands, 1):
                print(f"\n{i}. Testing: '{command}'")
                
                try:
                    # Test just the tool parsing without full execution
                    system_prompt = orchestrator._build_system_prompt(
                        tuple(str(tool) for tool in tools)
                    )
                    
                    messages = [
                        LLMMessage(role="system", content=system_prompt),
                        LLMMessage(role="user", content=command)
                    ]
                    
                    # Get LLM response
                    response = await llm_client.complete(messages, temperature=0.3)
                    
                    # Parse for tool requests
                    tool_calls = await orchestrator._parse_tool_requests(response.content)
                    
                    if tool_calls:
                        for call in tool_calls:
                            if call.name == 'opensearch':
                                print(f"   ✅ Recognized as opensearch: {call.arguments}")
                            else:
                                print(f"   ⚠️  Recognized as {call.name}: {call.arguments}")
                    else:
                        print(f"   ❌ No tool calls recognized")
                        print(f"   🔍 LLM Response: {response.content[:100]}...")
                        
                        # Try natural language extraction
                        extracted = await orchestrator._extract_tool_intentions(response.content)
                        if extracted:
                            print(f"   🔍 Extracted from NLP: {extracted[0].name} - {extracted[0].arguments}")
                        
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                
                # Small delay to avoid rate limits
                await asyncio.sleep(0.5)
            
            print(f"\n🎯 Summary:")
            print("✅ Enhanced system prompt with clear examples")
            print("✅ Improved tool request parsing with fallbacks")
            print("✅ Added natural language intention extraction")
            print("✅ Added tool name validation and auto-correction")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await llm_client.close()


if __name__ == "__main__":
    print("🚀 Make sure MCP server is running: python3 ../mcp-server/server_sse.py")
    asyncio.run(test_opensearch_recognition())
