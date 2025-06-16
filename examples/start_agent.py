#!/usr/bin/env python3
"""
LLM Agent Launcher - Easy start script for the CLI agent
"""
import asyncio
import os
import sys

# Add the current directory to path so we can import the agent
sys.path.append(os.path.dirname(__file__))

from llm_agent.cli_agent import main

if __name__ == "__main__":
    print("🧠 LLM CLI Agent Launcher")
    print("🔗 Connecting to MCP server...")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Agent stopped by user")
    except Exception as e:
        print(f"❌ Agent crashed: {e}")
        import traceback

        traceback.print_exc()
