# MCP Client Examples - Evolution Demonstration

This directory contains examples showing the progression from basic MCP protocol to AI-enhanced agent.

## Evolution Examples

### 1. Basic MCP Protocol Client
```python
#!/usr/bin/env python3
"""
Example: Basic MCP Protocol Communication
Shows fundamental MCP tool discovery and execution.
"""
import asyncio
from mcp_client import MCPClient

async def basic_mcp_example():
    """Basic MCP protocol usage"""
    print("🔧 Basic MCP Protocol Example")
    print("=" * 40)
    
    # Create basic MCP client
    async with MCPClient.create_openai("your-api-key") as client:
        # Discover tools
        tools = await client.discover_tools()
        print(f"📋 Found {len(tools)} tools:")
        for tool in tools:
            print(f"  • {tool['name']}: {tool.get('description', 'No description')}")
        
        # Execute tool directly
        if tools:
            tool_name = tools[0]['name']
            print(f"\\n⚡ Executing {tool_name}...")
            
            # Direct tool execution (no AI reasoning)
            # This is pure MCP protocol communication
            result = await client.execute_tool({
                "name": tool_name,
                "arguments": {"query": "test"}
            })
            print(f"📄 Result: {result}")

if __name__ == "__main__":
    asyncio.run(basic_mcp_example())
```

### 2. AI-Enhanced Agent
```python
#!/usr/bin/env python3
"""
Example: AI-Enhanced MCP Agent
Shows intelligent tool selection and orchestration.
"""
import asyncio
from mcp_client import EnhancedCLIAgent

async def ai_enhanced_example():
    """AI-enhanced MCP agent usage"""
    print("🧠 AI-Enhanced MCP Agent Example")
    print("=" * 40)
    
    # Create AI agent
    agent = EnhancedCLIAgent.from_env()
    
    async with agent.session():
        # AI determines which tools to use and how
        print("💬 User: 'Find and analyze the README file'")
        print("🤖 Assistant: ", end="", flush=True)
        
        # AI will:
        # 1. Discover available tools
        # 2. Choose appropriate tools (file listing, reading)
        # 3. Execute tools in logical sequence
        # 4. Synthesize results into coherent response
        response = await agent.chat("Find and analyze the README file")
        
        print(f"\\n\\n📊 Response length: {len(response)} characters")
        print("✅ AI automatically orchestrated multiple tools!")

if __name__ == "__main__":
    asyncio.run(ai_enhanced_example())
```

### 3. Custom Orchestration
```python
#!/usr/bin/env python3
"""
Example: Custom Orchestration
Shows how to build custom AI + MCP workflows.
"""
import asyncio
from mcp_client import MCPOrchestrator, LLMClientFactory, ConfigManager

async def custom_orchestration_example():
    """Custom orchestration example"""
    print("🎯 Custom Orchestration Example")
    print("=" * 40)
    
    # Load configuration
    config = ConfigManager.load_from_env()
    
    # Create components
    llm_client = LLMClientFactory.create_client(config.llm)
    orchestrator = MCPOrchestrator(llm_client, config.mcp)
    
    async with orchestrator.session():
        # Custom streaming workflow
        print("🌊 Starting custom workflow...")
        
        async for event in orchestrator.chat_stream(
            "Create a summary of all Python files in the project",
        ):
            if event["type"] == "chunk":
                print(event["content"], end="", flush=True)
            elif event["type"] == "tool_notification":
                print(f"\\n🔍 {event['content']}")
            elif event["type"] == "error":
                print(f"\\n❌ {event['content']}")
                break
        
        print("\\n\\n✅ Custom orchestration completed!")
    
    await llm_client.close()

if __name__ == "__main__":
    asyncio.run(custom_orchestration_example())
```

## Running Examples

### Prerequisites
```bash
# Set API key
export OPENAI_API_KEY=your-api-key

# Start MCP server (in another terminal)
cd ../mcp-server
python server.py

# Install package in development mode
cd ../mcp-client
pip install -e .
```

### Run Examples
```bash
# Basic MCP protocol
python examples/basic_mcp_example.py

# AI-enhanced agent  
python examples/ai_enhanced_example.py

# Custom orchestration
python examples/custom_orchestration_example.py

# Interactive CLI
mcp-agent

# Basic CLI (no AI)
mcp-agent --basic
```

## Example Output

### Basic MCP Protocol
```
🔧 Basic MCP Protocol Example
========================================
📋 Found 3 tools:
  • search_files: Search for files
  • read_file: Read file contents
  • system_info: Get system information

⚡ Executing search_files...
📄 Result: {"files": ["README.md", "setup.py"]}
```

### AI-Enhanced Agent
```
🧠 AI-Enhanced MCP Agent Example
========================================
💬 User: 'Find and analyze the README file'
🤖 Assistant: 
🔍 Using search_files tool...
🔍 Using read_file tool...

I found and analyzed your README file. Here's what I discovered:

**File: README.md**
- **Size**: 2,847 characters
- **Purpose**: Project documentation for MCP Client
- **Key Sections**:
  - Features overview with streaming support
  - Quick start guide
  - Installation instructions
  - Architecture explanation

**Analysis**:
The README effectively communicates the project's evolution from basic MCP protocol to AI-enhanced agent. It includes practical examples and clear setup instructions. The documentation structure follows best practices with features, usage, and architecture sections.

📊 Response length: 487 characters
✅ AI automatically orchestrated multiple tools!
```

### Key Differences

| Aspect | Basic MCP | AI-Enhanced |
|--------|-----------|-------------|
| **Tool Selection** | Manual/Programmatic | AI-driven reasoning |
| **Execution** | Direct protocol calls | Intelligent orchestration |
| **Context** | Stateless | Conversation-aware |
| **Error Handling** | Basic exceptions | AI-guided recovery |
| **User Experience** | Technical interface | Natural language |
| **Tool Chaining** | Manual sequencing | Automatic workflow |

## Learning Path

1. **Start with Basic MCP** (`basic_mcp_example.py`)
   - Understand MCP protocol fundamentals
   - Learn tool discovery and execution
   - See raw MCP communication

2. **Explore AI Enhancement** (`ai_enhanced_example.py`)
   - Experience intelligent tool selection
   - See conversation context management
   - Understand streaming responses

3. **Build Custom Solutions** (`custom_orchestration_example.py`)
   - Create tailored workflows
   - Implement specific business logic
   - Integrate with existing systems

4. **Use Interactive CLI** (`mcp-agent`)
   - Daily usage patterns
   - Command system exploration
   - Real-time AI assistance

This progression shows how MCP protocol understanding evolves into sophisticated AI-driven applications while maintaining the underlying simplicity and power of the MCP specification.
