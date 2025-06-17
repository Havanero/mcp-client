"""
Test configuration and fixtures for MCP Client

This file sets up the testing environment and provides fixtures
for testing both basic MCP protocol and AI-enhanced components.
"""
import asyncio
import os
import pytest
from unittest.mock import AsyncMock, MagicMock

from mcp_client import (
    MCPClient, 
    AgentConfig, 
    LLMConfig, 
    MCPConfig,
    MCPOrchestrator,
    ConversationContext,
    LLMClientFactory
)


@pytest.fixture
def event_loop():
    """Create new event loop for each test"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_openai_config():
    """Mock OpenAI configuration"""
    return LLMConfig(
        provider="openai",
        model="gpt-4",
        api_key="test-api-key",
        temperature=0.7,
        max_tokens=2000
    )


@pytest.fixture
def mock_mcp_config():
    """Mock MCP configuration"""
    return MCPConfig(
        base_url="http://localhost:8081",
        timeout=60.0,
        reconnect_delay=1.0
    )


@pytest.fixture
def mock_agent_config(mock_openai_config, mock_mcp_config):
    """Mock agent configuration"""
    return AgentConfig(
        llm=mock_openai_config,
        mcp=mock_mcp_config,
        debug=True,
        log_level="DEBUG"
    )


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client for testing"""
    client = MagicMock(spec=MCPClient)
    client.get_stats = AsyncMock(return_value={
        "server": {"status": "healthy"},
        "tools_cached": 3,
        "llm_provider": "openai",
        "llm_model": "gpt-4"
    })
    client.discover_tools = AsyncMock(return_value=[
        {"name": "echo", "description": "Echo tool"},
        {"name": "search", "description": "Search tool"},
        {"name": "calculator", "description": "Math tool"}
    ])
    return client


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing"""
    client = AsyncMock()
    client.complete = AsyncMock(return_value=MagicMock(
        content="Test response",
        tool_calls=None
    ))
    client.stream = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_orchestrator(mock_llm_client, mock_mcp_config):
    """Mock orchestrator for testing"""
    orchestrator = MagicMock(spec=MCPOrchestrator)
    orchestrator.discover_tools = AsyncMock(return_value=[
        {"name": "test_tool", "description": "Test tool"}
    ])
    orchestrator.chat_stream = AsyncMock()
    orchestrator.get_stats = AsyncMock(return_value={
        "mcp_server": {"status": "healthy"},
        "tools_cached": 1
    })
    return orchestrator


@pytest.fixture
def conversation_context():
    """Create conversation context for testing"""
    return ConversationContext()


@pytest.fixture(autouse=True)
def mock_environment():
    """Mock environment variables for testing"""
    test_env = {
        "OPENAI_API_KEY": "test-openai-key",
        "ANTHROPIC_API_KEY": "test-anthropic-key", 
        "LLM_PROVIDER": "openai",
        "MCP_BASE_URL": "http://localhost:8081",
        "DEBUG": "true"
    }
    
    # Store original values
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield test_env
    
    # Restore original values
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


# Test utilities
class MockSSEClient:
    """Mock SSE client for testing"""
    
    def __init__(self):
        self.tools = [
            {"name": "echo", "description": "Echo input"},
            {"name": "calculator", "description": "Perform calculations"}
        ]
    
    async def get_tools(self):
        return self.tools
    
    async def get_health(self):
        return {"status": "healthy"}
    
    async def stream_tool(self, name, arguments):
        yield {"event": "started", "data": {"tool": name}}
        yield {"event": "result", "data": {"result": f"Mock result for {name}"}}
        yield {"event": "completed", "data": {"duration": 0.1}}
    
    async def disconnect(self):
        pass


@pytest.fixture
def mock_sse_client():
    """Mock SSE client fixture"""
    return MockSSEClient()
