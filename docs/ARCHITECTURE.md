# MCP Client Architecture - Evolution from Protocol to AI

This document explains the evolution of the MCP client from basic protocol understanding to AI-enhanced intelligent agent.

## Project Evolution Story

### Phase 1: Basic MCP Protocol Understanding
```
src/mcp_client/
├── client.py          # Basic MCP client with streaming
├── transport.py       # Protocol communication 
└── exceptions.py      # Error handling
```

**Goal**: Understand and implement the MCP protocol for tool communication.

### Phase 2: LLM Integration
```
src/mcp_client/
├── llm.py            # LLM provider abstraction
├── config.py         # Configuration management
└── agent.py          # Basic CLI interface
```

**Goal**: Add AI capabilities through LLM provider integration.

### Phase 3: AI-Enhanced Orchestration (Current)
```
src/mcp_client/
├── orchestrator.py   # 🧠 AI + MCP orchestration
├── cli_agent.py      # 🤖 Enhanced AI agent
├── core/             # 🏗️ Foundation abstractions
├── transports/       # 🚀 Plugin-based transports
├── providers/        # 🔌 LLM provider plugins  
└── plugins/          # ⚡ Plugin architecture
```

**Goal**: Intelligent orchestration of LLM reasoning with MCP tool execution.

## Architecture Overview

### Búvár-Style Patterns Used

#### 1. Plugin-Based Architecture
```python
# Transport registry for dependency injection
TRANSPORT_REGISTRY = {
    "sse": SSETransport,
    "websocket": WebSocketTransport, 
    "http": HTTPTransport,
    "stdio": StdioTransport,
}

# Provider registry for LLM plugins
PROVIDER_REGISTRY = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
}
```

#### 2. Context Management
```python
class ContextRegistry:
    """Hierarchical context management"""
    
    def resolve(self, name: str) -> Any:
        if name in self._contexts:
            return self._contexts[name]
        if self._parent:
            return self._parent.resolve(name)
        raise KeyError(f"Context '{name}' not found")
```

#### 3. Dependency Injection
```python
@lru_cache(maxsize=None)
def get_transport_class(transport_type: str) -> Type:
    """Factory pattern for transport resolution"""
    return TRANSPORT_REGISTRY[transport_type]
```

#### 4. Async-First Design
```python
class MCPOrchestrator:
    """Orchestrates LLM + MCP with streaming"""
    
    async def chat_stream(self, message: str):
        # Stream AI response with tool notifications
        async for event in self._stream_response():
            yield event
```

## Key Components

### 1. MCPOrchestrator - The AI Brain
```python
from mcp_client import MCPOrchestrator

orchestrator = MCPOrchestrator(llm_client, mcp_config)

async with orchestrator.session():
    async for event in orchestrator.chat_stream("Search for GDPR documents"):
        if event["type"] == "chunk":
            print(event["content"], end="")
        elif event["type"] == "tool_notification":
            print(f"\\n{event['content']}")
```

**Features:**
- Native OpenAI function calling (no JSON parsing!)
- Hybrid streaming (immediate for chat, notifications for tools)
- Context-aware conversation management
- Tool result integration

### 2. Enhanced CLI Agent
```python
from mcp_client import EnhancedCLIAgent

agent = EnhancedCLIAgent.from_env()
await agent.run_interactive()
```

**Features:**
- Interactive streaming chat
- Tool execution notifications  
- Command system (/help, /tools, /status)
- Provider switching support
- Session management

### 3. Plugin System
```python
from mcp_client.plugins import register_plugin

@register_plugin("custom_provider", "1.0.0", "Custom LLM provider")
class CustomProvider:
    async def initialize(self, context): ...
    async def shutdown(self): ...
```

## Usage Examples

### Basic MCP Client (Protocol Only)
```python
from mcp_client import MCPClient

async with MCPClient.create_openai("api-key") as client:
    tools = await client.discover_tools()
    response, context = await client.chat("List files")
```

### AI-Enhanced Agent (Full AI)
```python
from mcp_client import EnhancedCLIAgent

agent = EnhancedCLIAgent.from_env()
async with agent.session():
    response = await agent.chat("Analyze the code in main.py")
```

### Custom Orchestration
```python
from mcp_client import MCPOrchestrator, LLMClientFactory

llm_client = LLMClientFactory.create_client(llm_config)
orchestrator = MCPOrchestrator(llm_client, mcp_config)

async with orchestrator.session():
    context = ConversationContext()
    async for event in orchestrator.chat_stream("Help me debug this error", context):
        handle_stream_event(event)
```

## CLI Usage

### Start AI Agent
```bash
# Auto-detect from environment
mcp-agent

# Specify provider
mcp-agent --provider=openai --model=gpt-4

# Debug mode
mcp-agent --debug

# Basic MCP only (no AI)
mcp-agent --basic
```

### Utility Commands
```bash
# Check setup
mcp-agent doctor

# List available models
mcp-agent models --provider=openai

# Show help
mcp-agent --help
```

## Environment Configuration

```bash
# LLM Provider
export LLM_PROVIDER=openai  # or anthropic
export OPENAI_API_KEY=your-key
export OPENAI_MODEL=gpt-4

# MCP Server
export MCP_BASE_URL=http://localhost:8081

# Debug
export DEBUG=true
export LOG_LEVEL=DEBUG
```

## Design Principles

### 1. Evolution Clarity
The codebase clearly shows progression from basic MCP to AI-enhanced agent:
- `client.py` → `orchestrator.py` → `cli_agent.py`
- Each component builds on the previous one
- Backward compatibility maintained

### 2. Performance Optimization
```python
@lru_cache(maxsize=1)
def _convert_mcp_tools_to_openai(self, tools_tuple: tuple):
    """Cached tool conversion for performance"""
    
from functools import partial
execute_with_context = partial(self.execute_tool, context=context)
```

### 3. Type Safety
```python
@runtime_checkable
class MCPTransport(Protocol):
    async def connect(self) -> None: ...
    async def send_message(self, message: Dict[str, Any]) -> None: ...

def get_transport(transport_type: str) -> MCPTransport:
    return transport_registry[transport_type]()
```

### 4. Extensibility
- Plugin-based architecture for transports and providers
- Context registry for dependency injection
- Event-driven streaming for real-time updates

## Testing

```bash
# Run all tests
pytest

# Test specific component
pytest tests/test_orchestrator.py

# Test with coverage
pytest --cov=src/mcp_client
```

## Future Extensions

1. **More LLM Providers**: Gemini, Claude-3, local models
2. **Advanced Tool Orchestration**: Parallel execution, dependency resolution  
3. **Memory Management**: Conversation persistence, semantic search
4. **Multi-Modal Support**: Image, audio, video processing
5. **Plugin Marketplace**: Community-contributed tools and providers

---

This architecture demonstrates how to build sophisticated AI systems while maintaining clean separation of concerns and evolutionary clarity.
