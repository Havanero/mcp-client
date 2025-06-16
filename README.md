# MCP Client - From Protocol to AI Assistant

A complete evolution story showing the progression from basic MCP protocol understanding to sophisticated AI-enhanced intelligent agent.

## 🚀 Evolution Story

**Phase 1**: Basic MCP Protocol → **Phase 2**: LLM Integration → **Phase 3**: AI Orchestration → **Phase 4**: Enhanced Agent

## ✨ Features

- 🧠 **AI-Enhanced MCP Client** - Intelligent tool selection and orchestration
- 🔗 **Native Function Calling** - Direct OpenAI function calling integration  
- 🌊 **Hybrid Streaming** - Real-time responses with tool execution notifications
- 🎯 **Búvár Architecture** - Plugin-based, dependency injection patterns
- ⚡ **High Performance** - Async-first design with functools optimization
- 🔧 **Multi-Transport** - SSE, WebSocket, HTTP, StdIO support

## Quick Start

### 🧠 AI-Enhanced Agent (Recommended)
```python
import asyncio
from mcp_client import EnhancedCLIAgent

async def main():
    agent = EnhancedCLIAgent.from_env()
    async with agent.session():
        # AI automatically selects and orchestrates tools
        response = await agent.chat("Search for Python files and analyze their structure")
        print(response)

asyncio.run(main())
```

### 🔧 Basic MCP Client (Protocol Only)
```python
import asyncio
from mcp_client import MCPClient

async def main():
    async with MCPClient.create_openai("your-api-key") as client:
        response, context = await client.chat("Search for GDPR regulations")
        print(response)

asyncio.run(main())
```

## 💻 CLI Usage

### **Multiple Command Options**
```bash
# Install package
pip install -e .

# Basic MCP client (protocol only)
mcp-basic

# MCP client with agent capabilities
mcp-agent

# General interface with options
mcp --basic                      # Use basic client
mcp --provider=openai           # Use with LLM
mcp doctor                       # Check setup
```

## Installation

```bash
# Development install
pip install -e .

# Production install  
pip install mcp-client
```

## 🏗️ Architecture - Evolution Story

### **Phase 1: Basic MCP Protocol**
- `client.py` - Core MCP client with tool discovery and execution
- `transport.py` - Protocol communication layer

### **Phase 2: LLM Integration** 
- `llm.py` - Multi-provider LLM abstraction (OpenAI, Anthropic)
- `config.py` - Environment-based configuration management

### **Phase 3: AI Orchestration**
- `orchestrator.py` - 🎆 **Smart LLM + MCP coordination**
- Native function calling with streaming notifications
- Context-aware conversation management

### **Phase 4: Enhanced Agent**
- `cli_agent.py` - 🤖 **Interactive AI assistant**
- Real-time streaming with tool orchestration
- Command system with session management

### **Búvár Architecture Foundation**
- `core/` - Protocols and dependency injection
- `transports/` - Plugin-based transport layer (SSE, WebSocket, HTTP, StdIO)
- `providers/` - LLM provider plugins
- `plugins/` - Extensible plugin system

## 📋 Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) - Complete architecture guide
- [`examples/README.md`](examples/README.md) - Evolution examples
- [`docs/RESTRUCTURING_COMPLETE.md`](docs/RESTRUCTURING_COMPLETE.md) - Project summary

## ⚙️ Requirements

- Python 3.8+
- aiohttp, pydantic, click, rich
- OpenAI API key (or Anthropic)
- MCP server running on localhost:8081

## 🚀 Quick Commands

```bash
# Check setup
mcp doctor

# List available models  
mcp models --provider=openai

# Basic MCP client (protocol only)
mcp-basic

# MCP agent (LLM-enhanced) 
mcp-agent

# General interface
mcp --basic              # Basic mode
mcp --provider=openai    # With LLM
```
