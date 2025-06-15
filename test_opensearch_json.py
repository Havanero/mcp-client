#!/usr/bin/env python3
"""
Test Enhanced OpenSearch JSON Format
"""
import asyncio
import os
import sys

# Add path for imports
sys.path.append(os.path.dirname(__file__))

async def test_opensearch_json():
    """Test the enhanced opensearch tool with JSON format"""
    print("🧪 Testing Enhanced OpenSearch with JSON Format")
    print("=" * 60)
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return
    
    try:
        from llm_agent.config import ConfigManager
        from llm_agent.llm_client import LLMClientFactory
        from llm_agent.mcp_orchestrator import MCPOrchestrator
        
        # Create configuration and clients
        config = ConfigManager.create_openai_config(api_key, "gpt-3.5-turbo")
        llm_client = LLMClientFactory.create_client(config.llm)
        orchestrator = MCPOrchestrator(llm_client, config.mcp)
        
        async with orchestrator.session():
            print("✅ Connected to MCP server")
            
            # Test different opensearch requests
            test_queries = [
                "Search for GDPR documents in JSON format",
                "Use opensearch to find privacy regulations with JSON output",
                "Can you make the output of opensearch tool in json format?",
                "Find GDPR documents using opensearch with format=json"
            ]
            
            for i, query in enumerate(test_queries, 1):
                print(f"\n{i}. Testing: '{query}'")
                print("-" * 50)
                
                try:
                    response, context = await orchestrator.chat(query)
                    print(f"✅ Response received")
                    
                    # Check if tools were called
                    if context.tool_calls:
                        latest_call = context.tool_calls[-1]
                        print(f"🔧 Tool called: {latest_call.name}")
                        print(f"📋 Arguments: {latest_call.arguments}")
                        
                        # Check if format=json was used
                        if latest_call.name == 'opensearch':
                            format_param = latest_call.arguments.get('format', 'text')
                            print(f"📊 Format used: {format_param}")
                            if format_param == 'json':
                                print("✅ JSON format correctly requested!")
                            else:
                                print("⚠️ Text format used (might be intentional)")
                    else:
                        print("❌ No tools were called")
                    
                    # Show response preview
                    print(f"🤖 Response preview: {response[:200]}...")
                    
                except Exception as e:
                    print(f"❌ Error: {e}")
                
                # Small delay between tests
                await asyncio.sleep(1)
    
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure the syntax errors are fixed first")
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🚀 Make sure MCP server is running with updated db.py:")
    print("   cd mcp-server && python3 server_sse.py")
    print()
    asyncio.run(test_opensearch_json())
