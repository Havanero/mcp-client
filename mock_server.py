#!/usr/bin/env python3
"""
Mock MCP Server for testing the CLI client.
Provides a few sample tools to demonstrate functionality.
"""
import sys
import json


def mock_mcp_server():
    """Simple mock MCP server with sample tools"""
    
    # Server responses
    responses = {
        "initialize": {
            "result": {
                "protocolVersion": "2024-11-05", 
                "serverInfo": {
                    "name": "test-server",
                    "version": "1.0.0"
                }
            }
        },
        "tools/list": {
            "result": {
                "tools": [
                    {
                        "name": "echo",
                        "description": "Echo back the input text",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string", "description": "Text to echo"}
                            },
                            "required": ["text"]
                        }
                    },
                    {
                        "name": "add",
                        "description": "Add two numbers together",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "a": {"type": "number", "description": "First number"},
                                "b": {"type": "number", "description": "Second number"}
                            },
                            "required": ["a", "b"]
                        }
                    },
                    {
                        "name": "weather",
                        "description": "Get weather for a location",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "location": {"type": "string", "description": "City name"}
                            },
                            "required": ["location"]
                        }
                    }
                ]
            }
        }
    }
    
    # Handle tool calls
    def handle_tool_call(msg):
        tool_name = msg["params"]["name"]
        args = msg["params"]["arguments"]
        
        if tool_name == "echo":
            return {
                "content": [{
                    "type": "text",
                    "text": f"Echo: {args.get('text', '')}"
                }]
            }
        elif tool_name == "add":
            result = args.get("a", 0) + args.get("b", 0)
            return {
                "content": [{
                    "type": "text", 
                    "text": f"Result: {result}"
                }]
            }
        elif tool_name == "weather":
            location = args.get("location", "Unknown")
            return {
                "content": [{
                    "type": "text",
                    "text": f"Weather in {location}: Sunny, 22°C 🌞"
                }]
            }
        else:
            return {"error": {"code": -1, "message": f"Unknown tool: {tool_name}"}}
    
    # Main server loop
    for line in sys.stdin:
        try:
            msg = json.loads(line.strip())
            method = msg.get("method")
            msg_id = msg.get("id")
            
            # Handle different message types
            if method == "initialized":
                continue  # No response needed
            
            if method in responses:
                response = responses[method].copy()
                response["id"] = msg_id
                print(json.dumps(response))
                sys.stdout.flush()
            elif method == "tools/call":
                result = handle_tool_call(msg)
                response = {"id": msg_id, "result": result}
                print(json.dumps(response))
                sys.stdout.flush()
                
        except json.JSONDecodeError:
            continue
        except Exception as e:
            error_response = {
                "id": msg.get("id"),
                "error": {"code": -1, "message": str(e)}
            }
            print(json.dumps(error_response))
            sys.stdout.flush()


if __name__ == "__main__":
    mock_mcp_server()
