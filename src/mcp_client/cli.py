#!/usr/bin/env python3
"""
MCP Client CLI - Main Entry Point

This demonstrates the evolution from basic MCP protocol understanding
to AI-enhanced intelligent agent:

Evolution Story:
1. Basic MCP Client (client.py) - Protocol communication
2. LLM Integration (llm.py) - AI capabilities
3. AI Orchestration (orchestrator.py) - Smart tool execution
4. Enhanced CLI Agent (cli_agent.py) - Complete AI assistant

Usage:
    mcp-agent                    # Start AI-enhanced interactive agent
    mcp-agent --basic           # Use basic MCP client
    mcp-agent --provider=openai # Specify LLM provider
"""
import asyncio
import os
import sys
from typing import Optional

import click

from .agent import main as agent_runner
from .basic_client import main as basic_client_runner  # True basic MCP client
from .cli_agent import create_agent, create_agent_from_env
from .cli_agent import main as enhanced_main
from .config import get_available_models


@click.command()
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic"]),
    help="LLM provider (overrides LLM_PROVIDER env var)",
)
@click.option("--model", help="Model name (overrides MODEL env vars)")
@click.option("--api-key", help="API key (overrides API_KEY env vars)")
@click.option("--mcp-url", default="http://localhost:8081", help="MCP server URL")
@click.option("--basic", is_flag=True, help="Use basic MCP client (no AI)")
@click.option("--debug", is_flag=True, help="Enable debug logging")
def main(
    provider: Optional[str],
    model: Optional[str],
    api_key: Optional[str],
    mcp_url: str,
    basic: bool,
    debug: bool,
):
    """
    MCP Client - From Protocol to AI Assistant

    This CLI demonstrates the evolution of MCP understanding:
    • Basic MCP protocol communication
    • AI-enhanced intelligent agent with tool orchestration
    """

    if debug:
        os.environ["DEBUG"] = "true"
        os.environ["LOG_LEVEL"] = "DEBUG"

    # Update environment if CLI args provided
    if provider:
        os.environ["LLM_PROVIDER"] = provider
    if model:
        if provider == "anthropic":
            os.environ["ANTHROPIC_MODEL"] = model
        else:
            os.environ["OPENAI_MODEL"] = model
    if api_key:
        if provider == "anthropic":
            os.environ["ANTHROPIC_API_KEY"] = api_key
        else:
            os.environ["OPENAI_API_KEY"] = api_key
    if mcp_url:
        os.environ["MCP_BASE_URL"] = mcp_url

    # Route to appropriate interface
    if basic:
        print("🔧 Starting Basic MCP Client (Protocol Only)")
        asyncio.run(basic_client_runner())
    else:
        print("🧠 Starting MCP Client with LLM Integration")
        asyncio.run(enhanced_main())


@click.command()
@click.option(
    "--provider", type=click.Choice(["openai", "anthropic"]), default="openai"
)
def list_models(provider: str):
    """List available models for a provider"""
    models = get_available_models(provider)

    print(f"\\n📋 Available {provider.title()} Models:")
    print("-" * 40)

    for key, model_id in models.items():
        print(f"  {key:<15} → {model_id}")

    print(f"\\n💡 Usage:")
    print(f"  mcp-agent --provider={provider} --model={list(models.keys())[0]}")
    print(f"  export {provider.upper()}_MODEL={list(models.values())[0]}")


@click.command()
def doctor():
    """Diagnose MCP client setup"""
    print("🔍 MCP Client Setup Diagnosis")
    print("=" * 40)

    # Check API keys
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    print(f"\\n🔑 API Keys:")
    print(f"  OpenAI:    {'✅ Set' if openai_key else '❌ Missing'}")
    print(f"  Anthropic: {'✅ Set' if anthropic_key else '❌ Missing'}")

    # Check environment
    provider = os.getenv("LLM_PROVIDER", "openai")
    print(f"\\n⚙️  Configuration:")
    print(f"  Provider:  {provider}")
    print(f"  MCP URL:   {os.getenv('MCP_BASE_URL', 'http://localhost:8081')}")
    print(f"  Debug:     {os.getenv('DEBUG', 'false')}")

    # Check models
    if provider == "openai" and openai_key:
        model = os.getenv("OPENAI_MODEL", "gpt-4")
        print(f"  Model:     {model}")
    elif provider == "anthropic" and anthropic_key:
        model = os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")
        print(f"  Model:     {model}")

    # Recommendations
    print(f"\\n💡 Recommendations:")
    if not openai_key and not anthropic_key:
        print("  ❌ No API keys found! Set OPENAI_API_KEY or ANTHROPIC_API_KEY")
    elif openai_key and anthropic_key:
        print("  ✅ Both providers available - great setup!")
    else:
        available = "OpenAI" if openai_key else "Anthropic"
        print(f"  ✅ {available} available - ready to go!")

    print(f"\\n🚀 Quick Start:")
    print(f"  mcp-agent                    # Start AI agent")
    print(f"  mcp-agent --basic           # Basic MCP only")
    print(f"  mcp-agent --provider=openai # Force OpenAI")


@click.group()
def cli():
    """MCP Client - Model Context Protocol with LLM Integration"""
    pass


# Register commands
cli.add_command(main, name="agent")
cli.add_command(list_models, name="models")
cli.add_command(doctor, name="doctor")

# Create specific entry points for different use cases
def agent_main():
    """Entry point for MCP agent functionality"""
    print("🤖 Starting MCP Agent (LLM-Enhanced)")
    asyncio.run(enhanced_main())

def basic_client_main():
    """Entry point for basic MCP client"""
    print("🔧 Starting Basic MCP Client (Protocol Only)")
    asyncio.run(basic_client_runner())

# Make main the default when called directly
if __name__ == "__main__":
    main()
