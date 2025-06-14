# MCP Python Client

## Quick Start

### Test with Mock Server
```bash
# Start the interactive CLI with mock server
python3 cli.py python3 mock_server.py
```

### Available Commands
- `list` - Show available tools
- `help [tool]` - Show help or tool details  
- `call <tool> <json_args>` - Execute a tool
- `info` - Show server information
- `exit` - Close and exit

### Example Session
```
🔌 Connecting to MCP server...
✅ Connected! Server: test-server
📦 Available tools: 3
Type 'help' for commands or 'list' to see tools

mcp> list
🔧 Available Tools (3):
  1. echo
     Echo back the input text
  2. add
     Add two numbers together
  3. weather
     Get weather for a location

mcp> call echo {"text": "Hello World!"}
⚡ Calling echo...
✅ Result:
  📄 Echo: Hello World!

mcp> call add {"a": 15, "b": 27}
⚡ Calling add...
✅ Result:
  📄 Result: 42
```

## Architecture

- `transport.py` - Stdio transport layer
- `protocol.py` - MCP protocol handling
- `cli.py` - Interactive CLI interface
- `mock_server.py` - Test server for development
