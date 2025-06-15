# LLM CLI Agent with MCP Integration

A sophisticated command-line AI assistant that integrates LLMs (OpenAI/Anthropic) with your MCP (Model Context Protocol) server for intelligent tool usage.

## 🏗️ Architecture

```
[CLI Interface] → [LLM Agent] → [LLM Client] → [OpenAI/Anthropic API]
                      ↓
                 [MCP Orchestrator] → [SSE Client] → [Your MCP Server] → [Tools]
```

## 🚀 Quick Start

### 1. Start Your MCP Server
```bash
# In one terminal, start your MCP server
cd mcp-server
python3 server_sse.py
```

### 2. Set API Key
```bash
# Set your OpenAI API key
export OPENAI_API_KEY="your-openai-api-key-here"

# Or for Anthropic
export ANTHROPIC_API_KEY="your-anthropic-api-key-here"
export LLM_PROVIDER="anthropic"
```

### 3. Start the Agent
```bash
# In another terminal, start the CLI agent
cd mcp-client
python3 start_agent.py
```

## 💬 Usage Examples

### Basic Chat
```
💬 You: Hello! What can you help me with?
🤖 Assistant: I'm an AI assistant with access to various tools via MCP...
```

### File Operations
```
💬 You: List the files in the workspace directory
🤖 Assistant: I'll check the workspace directory for you.

[Tool: file_ops executes]

🤖 Assistant: I found 3 items in the workspace:
- 📄 test.txt
- 🐍 example.py  
- 📁 data/
```

### Code Analysis
```
💬 You: Read and analyze the example.py file
🤖 Assistant: Let me read the file and analyze it for you.

[Tool execution shows code content and analysis]
```

### Multi-Tool Workflows
```
💬 You: Create a new file called "hello.txt" with the content "Hello MCP!" and then read it back
🤖 Assistant: I'll create the file and then read it back to confirm.

[Executes: write file → read file]
```

## 🎛️ CLI Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help information |
| `/status` | Show agent and MCP server status |
| `/tools` | List available MCP tools |
| `/clear` | Clear conversation history |
| `/switch` | Switch LLM provider/model |
| `/debug` | Toggle debug logging |
| `/exit` | Exit the agent |

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required for OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic API key | Required for Anthropic |
| `LLM_PROVIDER` | Provider: "openai" or "anthropic" | "openai" |
| `OPENAI_MODEL` | OpenAI model name | "gpt-4" |
| `ANTHROPIC_MODEL` | Anthropic model name | "claude-3-sonnet-20240229" |
| `MCP_BASE_URL` | MCP server URL | "http://localhost:8081" |
| `LLM_TEMPERATURE` | LLM temperature | "0.7" |
| `DEBUG` | Enable debug mode | "false" |

### Provider Switching

#### Use OpenAI GPT-4
```bash
export LLM_PROVIDER="openai"
export OPENAI_MODEL="gpt-4"
export OPENAI_API_KEY="your-key"
```

#### Use Anthropic Claude
```bash
export LLM_PROVIDER="anthropic" 
export ANTHROPIC_MODEL="claude-3-sonnet-20240229"
export ANTHROPIC_API_KEY="your-key"
```

#### Use OpenAI GPT-3.5 (faster/cheaper)
```bash
export LLM_PROVIDER="openai"
export OPENAI_MODEL="gpt-3.5-turbo"
```

## 🔧 Available Models

### OpenAI Models
- `gpt-4` - Most capable
- `gpt-4-turbo-preview` - Faster GPT-4
- `gpt-3.5-turbo` - Fast and economical

### Anthropic Models  
- `claude-3-opus-20240229` - Most capable
- `claude-3-sonnet-20240229` - Balanced performance
- `claude-3-haiku-20240307` - Fast and economical

## 🧠 How It Works

### 1. Tool Discovery
The agent automatically discovers available tools from your MCP server via the `/tools` endpoint.

### 2. Intelligent Tool Selection
The LLM analyzes user requests and determines which tools to use, including:
- Parameter extraction from natural language
- Multi-step tool sequences
- Error handling and retries

### 3. Tool Execution
Tools are executed via the SSE (Server-Sent Events) transport for real-time streaming.

### 4. Result Integration
Tool results are formatted and integrated into the conversation context for follow-up questions.

## 🔍 Example Interactions

### File Management
```
💬 You: Show me what's in the workspace, then create a new file called notes.md
🤖 Assistant: I'll check the workspace contents first, then create the notes file.

[Executes file_ops with operation=list]
[Executes file_ops with operation=write]

🤖 Assistant: The workspace contains 3 files... I've created notes.md successfully!
```

### Tool Chaining
```
💬 You: Read the config file and tell me what settings are defined
🤖 Assistant: Let me read the configuration file and analyze its contents.

[Reads file → Analyzes content → Provides summary]
```

## 🛠️ Development

### Project Structure
```
mcp-client/
├── llm_agent/
│   ├── __init__.py          # Package initialization
│   ├── config.py            # Configuration management
│   ├── llm_client.py        # LLM abstraction layer
│   ├── mcp_orchestrator.py  # MCP integration
│   └── cli_agent.py         # CLI interface
├── start_agent.py           # Launcher script
└── README.md               # This file
```

### Key Components

1. **LLM Client** (`llm_client.py`)
   - Provider-agnostic interface
   - OpenAI and Anthropic support
   - Streaming and completion APIs

2. **MCP Orchestrator** (`mcp_orchestrator.py`)
   - Tool discovery and execution
   - LLM ↔ MCP integration
   - Context management

3. **CLI Agent** (`cli_agent.py`)
   - Interactive command interface
   - Session management
   - User experience

## 🧪 Testing

### Test LLM Connection
```python
from llm_agent.config import ConfigManager
from llm_agent.llm_client import LLMClientFactory

config = ConfigManager.load_from_env()
client = LLMClientFactory.create_client(config.llm)
response = await client.simple_complete("Say hello!")
print(response)
```

### Test MCP Integration
```python
from llm_agent.mcp_orchestrator import MCPOrchestrator

orchestrator = MCPOrchestrator(llm_client, mcp_config)
async with orchestrator.session():
    tools = await orchestrator.discover_tools()
    print(f"Found {len(tools)} tools")
```

## 🐛 Troubleshooting

### Agent Won't Start
- Check API key environment variables
- Verify MCP server is running on http://localhost:8081
- Check network connectivity

### Tools Not Found
- Ensure MCP server is running: `python3 server_sse.py`
- Check server logs for tool registration
- Verify workspace directory has test files

### LLM Errors
- Verify API key is correct
- Check rate limits and quotas
- Try switching to a different model

### Debug Mode
```bash
export DEBUG=true
python3 start_agent.py
```

## 🎯 Next Steps

1. **Add more tools** to your MCP server
2. **Customize prompts** for specific use cases  
3. **Implement tool chaining** for complex workflows
4. **Add memory/persistence** for longer conversations
5. **Create specialized agents** for different domains

## 📝 License

This implementation follows the Búvár architectural patterns with:
- ✅ Dependency injection
- ✅ Context management  
- ✅ Async-first design
- ✅ Performance optimization
- ✅ Clean separation of concerns
