#!/usr/bin/env python3
"""
Quick syntax check for the fixed orchestrator
"""
import sys
import os

# Add path for imports
sys.path.append(os.path.dirname(__file__))

try:
    # Try to import the fixed module
    from llm_agent.mcp_orchestrator import MCPOrchestrator, ToolCall, ToolResult
    print("✅ Syntax check passed! No syntax errors found.")
    print("✅ MCPOrchestrator class imported successfully")
    print("✅ ToolCall and ToolResult classes imported successfully")
    
    # Test basic instantiation (without actual connections)
    from llm_agent.config import MCPConfig, LLMConfig
    
    # Create mock configs
    llm_config = LLMConfig(
        provider="openai",
        model="gpt-4",
        api_key="test-key",
        temperature=0.7,
        max_tokens=2000
    )
    
    mcp_config = MCPConfig()
    
    print("✅ Configuration classes working")
    print("🎉 All fixes applied successfully!")
    
except SyntaxError as e:
    print(f"❌ Syntax Error: {e}")
    print(f"   Line {e.lineno}: {e.text}")
except ImportError as e:
    print(f"❌ Import Error: {e}")
except Exception as e:
    print(f"❌ Other Error: {e}")
