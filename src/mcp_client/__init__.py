"""
MCP Client - Modern Python package for MCP server integration

A powerful, streaming-enabled client for Model Context Protocol (MCP) servers
with built-in LLM integration and native function calling support.
"""

__version__ = "0.1.0"
__author__ = "MCP Client Team"
__email__ = "team@mcp-client.dev"

from .agent import CLIAgent
from .cli_agent import CLIAgent as MCPAgentCLI  # Enhanced MCP client with agent capabilities
from .client import MCPClient
from .config import AgentConfig, LLMConfig, MCPConfig
from .exceptions import MCPClientError, MCPConnectionError, MCPToolError
from .llm import LLMClient, LLMClientFactory, LLMMessage  # LLM abstraction for MCP
from .orchestrator import ConversationContext, MCPOrchestrator  # MCP + LLM orchestration

__all__ = [
    # Main MCP Client Classes
    "MCPClient",           # Core MCP protocol client
    "CLIAgent",            # Basic MCP CLI interface
    "MCPAgentCLI",         # Enhanced MCP client with agent capabilities
    # MCP + LLM Components (Evolution: Basic MCP -> LLM-enhanced MCP)
    "MCPOrchestrator",     # Orchestrates LLM + MCP tools
    "ConversationContext", # Context management for MCP conversations
    # LLM Integration for MCP
    "LLMClient",
    "LLMClientFactory",
    "LLMMessage",
    # Configuration
    "AgentConfig",
    "LLMConfig",
    "MCPConfig",
    # Exceptions
    "MCPClientError",
    "MCPConnectionError",
    "MCPToolError",
    # Metadata
    "__version__",
    "__author__",
    "__email__",
]

# Package-level configuration
import logging

# Set up default logging
logging.getLogger(__name__).addHandler(logging.NullHandler())
