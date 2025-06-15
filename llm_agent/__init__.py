#!/usr/bin/env python3
"""
LLM Agent Package - CLI Agent with MCP Integration
Búvár-style design with dependency injection and context management
"""
from .cli_agent import CLIAgent
from .config import AgentConfig, LLMConfig
from .llm_client import LLMClient, LLMClientFactory
from .mcp_orchestrator import MCPOrchestrator

__version__ = "1.0.0"
__all__ = [
    "LLMConfig",
    "AgentConfig",
    "LLMClient",
    "LLMClientFactory",
    "MCPOrchestrator",
    "CLIAgent",
]
