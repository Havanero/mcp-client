#!/usr/bin/env python3
"""
MCP JSON-RPC Transport - Proper MCP protocol over HTTP

This transport maintains full MCP compliance with JSON-RPC 2.0 over HTTP.
All MCP benefits are preserved while using HTTP for transport.
"""
import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional

import aiohttp


class MCPJSONRPCClient:
    """
    Proper MCP client using JSON-RPC 2.0 over HTTP transport
    
    Features:
    - Full MCP protocol compliance
    - JSON-RPC 2.0 message structure  
    - Standard MCP methods (initialize, tools/list, tools/call)
    - Proper protocol handshake and versioning
    - HTTP transport for easy debugging and monitoring
    """
    
    def __init__(self, base_url: str = "http://localhost:8081", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.mcp_endpoint = f"{self.base_url}/mcp"
        self.timeout = timeout
        
        # MCP protocol state
        self.protocol_version = "2024-11-05"
        self.client_info = {
            "name": "mcp-python-client",
            "version": "1.0.0"
        }
        self.initialized = False
        self.server_capabilities = {}
        self.server_info = {}
        
        # HTTP session
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger("mcp.jsonrpc.client")
        
    async def connect(self):
        """Connect to MCP server and perform handshake"""
        # Create HTTP session
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)
        
        try:
            # Check if server is available
            await self._check_server()
            
            # MCP handshake: initialize
            await self._initialize()
            
            # MCP handshake: send initialized notification
            await self._send_initialized()
            
            self.logger.info("🎯 MCP client connected (JSON-RPC 2.0)")
            return True
            
        except Exception as e:
            await self.disconnect()
            self.logger.error(f"Connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from server"""
        if self.session:
            await self.session.close()
            self.session = None
        self.initialized = False
        self.logger.info("👋 MCP client disconnected")
    
    async def _check_server(self):
        """Check if MCP server is available"""
        try:
            self.logger.debug(f"Checking server health at {self.base_url}/health")
            async with self.session.get(f"{self.base_url}/health") as response:
                self.logger.debug(f"Health check response: {response.status}")
                
                if response.status == 200:
                    health_data = await response.json()
                    self.logger.debug(f"Health data: {health_data}")
                    return
                elif response.status == 204:
                    # Some servers return 204 for health checks, treat as healthy
                    self.logger.debug("Server returned 204 (No Content) - treating as healthy")
                    return
                else:
                    response_text = await response.text()
                    raise ConnectionError(f"Server health check failed: HTTP {response.status} - {response_text}")
                    
        except aiohttp.ClientConnectorError as e:
            raise ConnectionError(f"Cannot connect to MCP server at {self.base_url}: {e}")
        except Exception as e:
            raise ConnectionError(f"Health check error: {e}")
    
    async def _send_jsonrpc_request(self, method: str, params: Dict[str, Any] = None, request_id: str = None) -> Any:
        """Send JSON-RPC 2.0 request to MCP server with automatic recovery"""
        if not self.session:
            raise RuntimeError("Not connected to server")
        
        # Create JSON-RPC request
        request_data = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        
        # Add ID for requests (not notifications)
        if request_id is not None:
            request_data["id"] = request_id
        
        is_notification = request_id is None
        self.logger.debug(f"MCP {'Notification' if is_notification else 'Request'}: {method}")
        
        try:
            return await self._execute_request(request_data, is_notification)
        except (ConnectionError, RuntimeError) as e:
            # Check if this looks like a server restart
            error_str = str(e).lower()
            if "server not initialized" in error_str or "connection" in error_str:
                self.logger.warning(f"🔄 Server restart detected, attempting recovery...")
                
                # Try to reconnect and re-initialize
                if await self._recover_connection():
                    # Retry the original request
                    self.logger.info(f"🔄 Retrying {method} after recovery...")
                    return await self._execute_request(request_data, is_notification)
                else:
                    raise RuntimeError(f"Failed to recover connection: {e}")
            else:
                raise
    
    async def _send_jsonrpc_notification(self, method: str, params: Dict[str, Any] = None):
        """Send JSON-RPC 2.0 notification (no response expected)"""
        await self._send_jsonrpc_request(method, params, request_id=None)
    
    async def _execute_request(self, request_data: Dict[str, Any], is_notification: bool) -> Any:
        """Execute the actual HTTP request"""
        try:
            async with self.session.post(self.mcp_endpoint, json=request_data) as response:
                # Handle notifications (expect 204 No Content)
                if is_notification:
                    if response.status == 204:
                        self.logger.debug(f"Notification {request_data['method']} sent successfully (204)")
                        return None  # Notifications don't return data
                    elif response.status == 200:
                        # Some servers might return 200 for notifications
                        self.logger.debug(f"Notification {request_data['method']} sent successfully (200)")
                        return None
                    else:
                        error_text = await response.text()
                        raise ConnectionError(f"Notification failed: HTTP {response.status} - {error_text}")
                
                # Handle requests (expect 200 OK)
                else:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ConnectionError(f"HTTP {response.status}: {error_text}")
                    
                    response_data = await response.json()
                    
                    # Handle JSON-RPC response
                    if "error" in response_data:
                        error = response_data["error"]
                        raise RuntimeError(f"MCP Error [{error['code']}]: {error['message']}")
                    
                    return response_data.get("result")
                    
        except aiohttp.ClientError as e:
            raise ConnectionError(f"HTTP request failed: {e}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response: {e}")
    
    async def _recover_connection(self) -> bool:
        """Attempt to recover connection after server restart"""
        try:
            self.logger.info("🔄 Attempting connection recovery...")
            
            # Reset initialization state
            self.initialized = False
            
            # Test if server is responding
            await self._check_server()
            
            # Re-run MCP handshake
            await self._initialize()
            await self._send_initialized()
            
            self.logger.info("✅ Connection recovery successful")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Connection recovery failed: {e}")
            return False
    
    async def _initialize(self):
        """Send MCP initialize request"""
        params = {
            "protocolVersion": self.protocol_version,
            "clientInfo": self.client_info,
            "capabilities": {}  # Client capabilities
        }
        
        result = await self._send_jsonrpc_request("initialize", params, str(uuid.uuid4()))
        
        # Store server info
        self.server_capabilities = result.get("capabilities", {})
        self.server_info = result.get("serverInfo", {})
        
        server_version = result.get("protocolVersion")
        if server_version != self.protocol_version:
            self.logger.warning(f"Protocol version mismatch: client={self.protocol_version}, server={server_version}")
        
        server_name = self.server_info.get('name', 'unknown')
        server_ver = self.server_info.get('version', 'unknown')
        self.logger.info(f"Connected to: {server_name} v{server_ver}")
    
    async def _send_initialized(self):
        """Send initialized notification"""
        await self._send_jsonrpc_notification("initialized", {})
        self.initialized = True
    
    async def get_tools(self) -> List[Dict[str, Any]]:
        """Get available tools using MCP tools/list method"""
        if not self.initialized:
            raise RuntimeError("Client not initialized")
        
        result = await self._send_jsonrpc_request("tools/list", {}, str(uuid.uuid4()))
        return result.get("tools", [])
    
    async def call_tool(self, name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a tool using MCP tools/call method"""
        if not self.initialized:
            raise RuntimeError("Client not initialized")
        
        params = {
            "name": name,
            "arguments": arguments or {}
        }
        
        result = await self._send_jsonrpc_request("tools/call", params, str(uuid.uuid4()))
        return result
    
    async def get_health(self) -> Dict[str, Any]:
        """Get server health (non-MCP endpoint)"""
        if not self.session:
            raise RuntimeError("Not connected to server")
        
        async with self.session.get(f"{self.base_url}/health") as response:
            if response.status == 200:
                return await response.json()
            else:
                raise ConnectionError(f"Health check failed: HTTP {response.status}")


# Factory function for creating MCP JSON-RPC clients
def create_mcp_client(base_url: str = "http://localhost:8081", **kwargs) -> MCPJSONRPCClient:
    """Factory for creating MCP JSON-RPC clients"""
    return MCPJSONRPCClient(base_url, **kwargs)
