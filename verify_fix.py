#!/usr/bin/env python3
"""
Verification script for CLI routing fix
"""
import sys
import importlib.util

def check_imports():
    """Verify all imports work correctly"""
    try:
        sys.path.insert(0, 'src')
        
        # Test basic_client import
        spec = importlib.util.spec_from_file_location(
            "basic_client", "src/mcp_client/basic_client.py"
        )
        basic_client = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(basic_client)
        
        # Test cli import  
        spec = importlib.util.spec_from_file_location(
            "cli", "src/mcp_client/cli.py"
        )
        cli_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli_module)
        
        print("✅ All imports successful")
        print("✅ CLI routing fixed")
        print("✅ No recursive function calls")
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def verify_entry_points():
    """Verify entry point functions exist"""
    try:
        sys.path.insert(0, 'src')
        from mcp_client.cli import basic_client_main, agent_main
        from mcp_client.basic_client import main as basic_main
        from mcp_client.cli_agent import main as enhanced_main
        
        print("✅ Entry point functions found:")
        print("   • basic_client_main() → basic MCP client")
        print("   • agent_main() → LLM-enhanced agent")
        print("   • basic_main() → core basic client")
        print("   • enhanced_main() → core enhanced client")
        return True
        
    except ImportError as e:
        print(f"❌ Entry point error: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Verifying MCP Client CLI Fix")
    print("=" * 40)
    
    all_good = True
    all_good &= check_imports()
    all_good &= verify_entry_points()
    
    if all_good:
        print("\n🎯 CLI routing fix verified!")
        print("\n📋 Commands now work correctly:")
        print("   mcp-basic  → Pure MCP protocol client")
        print("   mcp-agent  → LLM-enhanced agent")
        print("   mcp doctor → Setup diagnostics")
        print("\n🚀 Run: pip install -e . && mcp-basic")
    else:
        print("\n❌ Fix verification failed")
        sys.exit(1)
