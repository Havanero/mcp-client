#!/usr/bin/env python3
"""
CLI Agent - Interactive command-line interface for MCP Client
Clean, modern interface with streaming support and rich formatting
"""
import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from .client import ChatContext, MCPClient
from .config import AgentConfig, ConfigManager, get_available_models
from .llm import LLMMessage


class CLIAgent:
    """
    Modern CLI agent for MCP client interaction

    Features:
    - Interactive streaming chat
    - Tool integration notifications
    - Command system for control
    - Session management
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.client: Optional[MCPClient] = None
        self.context: Optional[ChatContext] = None
        self.session_active = False

        # Setup logging
        logging.basicConfig(
            level=getattr(logging, config.log_level),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger("mcp_client.cli")

    @asynccontextmanager
    async def session(self):
        """Context manager for agent session"""
        self.client = MCPClient(self.config)

        try:
            async with self.client.session():
                self.session_active = True
                self.context = ChatContext()
                yield self
        finally:
            self.session_active = False
            self.client = None

    async def chat(self, message: str) -> str:
        """Send a message and get response with streaming"""
        if not self.client or not self.session_active:
            return "❌ Agent session not active"

        try:
            response_parts = []

            async for event in self.client.chat_stream(message, self.context):
                if event["type"] == "chunk":
                    # Print chunk immediately and collect for return
                    print(event["content"], end="", flush=True)
                    response_parts.append(event["content"])
                elif event["type"] == "tool_notification":
                    # Show tool notifications to user
                    print(f"\n{event['content']}")
                elif event["type"] == "error":
                    return event["content"]

            response_text = "".join(response_parts)

            # Update context manually since we're using the streaming interface
            self.context.messages.append(LLMMessage(role="user", content=message))
            self.context.messages.append(
                LLMMessage(role="assistant", content=response_text)
            )

            return response_text

        except Exception as e:
            self.logger.error(f"Chat error: {e}")
            return f"❌ Error: {e}"

    async def get_status(self) -> str:
        """Get agent status information"""
        if not self.client:
            return "❌ Agent not initialized"

        try:
            stats = await self.client.get_stats()

            status_lines = [
                f"🤖 LLM: {self.config.llm.provider} - {self.config.llm.model}",
                f"🌊 MCP Server: {stats.get('server', {}).get('status', 'unknown')}",
                f"🔧 Tools: {stats.get('tools_cached', 0)} available",
                f"💬 Context: {len(self.context.messages) if self.context else 0} messages",
            ]

            if self.context and self.context.tool_calls:
                status_lines.append(
                    f"⚡ Tool calls: {len(self.context.tool_calls)} executed"
                )

            return "\n".join(status_lines)

        except Exception as e:
            return f"❌ Status error: {e}"

    def _print_banner(self):
        """Print welcome banner"""
        print("=" * 60)
        print("🧠 MCP Client - Interactive CLI Agent")
        print("=" * 60)
        print(f"🤖 Provider: {self.config.llm.provider}")
        print(f"🎯 Model: {self.config.llm.model}")
        print(f"🌊 MCP Server: {self.config.mcp.base_url}")
        print("=" * 60)
        print()
        print("💡 Commands:")
        print("  /help      - Show this help")
        print("  /status    - Show agent status")
        print("  /tools     - List available tools")
        print("  /clear     - Clear conversation history")
        print("  /switch    - Switch LLM provider/model")
        print("  /debug     - Toggle debug mode")
        print("  /exit      - Exit the agent")
        print()
        print("💬 Just type your message to chat with the AI assistant!")
        print("   The assistant can use tools via the MCP server automatically.")
        print()

    def _print_help(self):
        """Print help information"""
        print("\n📋 MCP Client Help")
        print("-" * 30)
        print("💬 Chat Commands:")
        print("  - Type any message to chat with the AI")
        print("  - The AI can automatically use available tools")
        print("  - Watch for tool notifications during execution")
        print()
        print("🎛️  System Commands:")
        print("  /help      - Show this help message")
        print("  /status    - Show current agent status")
        print("  /tools     - List all available MCP tools")
        print("  /clear     - Clear conversation history")
        print("  /switch    - Switch between LLM providers")
        print("  /debug     - Toggle debug logging")
        print("  /exit      - Exit the agent")
        print()
        print("🔧 Example Queries:")
        print("  - 'Search for GDPR regulations'")
        print("  - 'List files in the workspace'")
        print("  - 'Get system information'")
        print("  - 'What tools are available?'")
        print()

    async def _handle_tools_command(self):
        """Handle /tools command"""
        if not self.client:
            print("❌ Agent not initialized")
            return

        try:
            tools = await self.client.discover_tools()

            if not tools:
                print("📭 No tools available")
                return

            print(f"\n🔧 Available Tools ({len(tools)}):")
            print("-" * 40)

            for tool in tools:
                name = tool["name"]
                description = tool.get("description", "No description")

                print(f"• {name}")
                print(f"  📝 {description}")

                # Show parameters
                schema = tool.get("inputSchema", {})
                properties = schema.get("properties", {})

                if properties:
                    print(f"  📋 Parameters: {', '.join(properties.keys())}")

                print()

        except Exception as e:
            print(f"❌ Error listing tools: {e}")

    def _handle_clear_command(self):
        """Handle /clear command"""
        if self.context:
            self.context.messages.clear()
            self.context.tool_calls.clear()
            self.context.tool_results.clear()
            print("🧹 Conversation history cleared")
        else:
            print("❌ No active context to clear")

    def _handle_switch_command(self):
        """Handle /switch command"""
        print("\n🔄 Switch LLM Provider")
        print("-" * 25)

        current = f"{self.config.llm.provider} - {self.config.llm.model}"
        print(f"Current: {current}")
        print()

        print("Available providers:")
        print("1. OpenAI")
        print("2. Anthropic")
        print()

        choice = input("Select provider (1-2, or press Enter to cancel): ").strip()

        if choice == "1":
            models = get_available_models("openai")
            print(f"\nOpenAI models: {', '.join(models.keys())}")
            model_choice = input(
                "Enter model name (or press Enter for gpt-4): "
            ).strip()
            model = model_choice if model_choice else "gpt-4"
            print(f"💡 To switch to OpenAI {model}, restart with: OPENAI_MODEL={model}")

        elif choice == "2":
            models = get_available_models("anthropic")
            print(f"\nAnthropic models: {', '.join(models.keys())}")
            model_choice = input(
                "Enter model name (or press Enter for claude-3-sonnet): "
            ).strip()
            model = model_choice if model_choice else "claude-3-sonnet"
            print(
                f"💡 To switch to Anthropic {model}, restart with: LLM_PROVIDER=anthropic ANTHROPIC_MODEL={models.get(model, model)}"
            )

        print(
            "\n💡 Note: Provider switching requires restarting the agent with environment variables"
        )

    def _handle_debug_command(self):
        """Handle /debug command"""
        current_level = logging.getLogger().getEffectiveLevel()

        if current_level == logging.DEBUG:
            logging.getLogger().setLevel(logging.INFO)
            print("🔧 Debug mode: OFF")
        else:
            logging.getLogger().setLevel(logging.DEBUG)
            print("🔧 Debug mode: ON")

    async def run_interactive(self):
        """Run interactive CLI session"""
        self._print_banner()

        try:
            async with self.session():
                print("✅ Agent initialized successfully!")
                print("🔌 Connected to MCP server")

                # Show initial status
                status = await self.get_status()
                print(f"\n{status}\n")

                while True:
                    try:
                        # Get user input
                        user_input = input("💬 You: ").strip()

                        if not user_input:
                            continue

                        # Handle commands
                        if user_input.startswith("/"):
                            command = user_input[1:].lower()

                            if command == "exit":
                                print("👋 Goodbye!")
                                break
                            elif command == "help":
                                self._print_help()
                            elif command == "status":
                                status = await self.get_status()
                                print(f"\n📊 Status:\n{status}\n")
                            elif command == "tools":
                                await self._handle_tools_command()
                            elif command == "clear":
                                self._handle_clear_command()
                            elif command == "switch":
                                self._handle_switch_command()
                            elif command == "debug":
                                self._handle_debug_command()
                            else:
                                print(
                                    f"❓ Unknown command: {command}. Type /help for available commands."
                                )

                            continue

                        # Handle chat message with streaming
                        print("🤖 Assistant: ", end="", flush=True)
                        start_time = asyncio.get_event_loop().time()

                        response = await self.chat(user_input)

                        duration = asyncio.get_event_loop().time() - start_time
                        print(f"\n⏱️  Response time: {duration:.2f}s\n")

                    except KeyboardInterrupt:
                        print("\n⏹️  Use /exit to quit gracefully")
                    except EOFError:
                        print("\n👋 Goodbye!")
                        break
                    except Exception as e:
                        print(f"\n❌ Error: {e}\n")

        except Exception as e:
            print(f"❌ Failed to start agent: {e}")
            if self.config.debug:
                import traceback

                traceback.print_exc()


def create_agent_from_env() -> CLIAgent:
    """Create agent from environment configuration"""
    config = ConfigManager.load_from_env()
    return CLIAgent(config)


def create_agent(api_key: str, provider: str = "openai", model: str = None) -> CLIAgent:
    """Create agent with explicit configuration"""
    if provider == "openai":
        config = ConfigManager.create_openai_config(api_key, model or "gpt-4")
    elif provider == "anthropic":
        config = ConfigManager.create_anthropic_config(
            api_key, model or "claude-3-sonnet-20240229"
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    return CLIAgent(config)


async def main():
    """Main CLI entry point"""
    print("🚀 Starting MCP Client CLI...")

    # Check for API keys
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if not openai_key and not anthropic_key:
        print("❌ No API keys found!")
        print("💡 Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable")
        print("💡 Example: export OPENAI_API_KEY='your-key-here'")
        return

    try:
        # Try to create agent from environment
        agent = create_agent_from_env()
        await agent.run_interactive()

    except ValueError as e:
        print(f"❌ Configuration error: {e}")

        # Fallback to direct configuration
        if openai_key:
            print("🔄 Falling back to OpenAI with default settings...")
            agent = create_agent(openai_key, "openai", "gpt-4")
            await agent.run_interactive()
        else:
            print("💡 Please set LLM_PROVIDER and appropriate API key")


if __name__ == "__main__":
    asyncio.run(main())
