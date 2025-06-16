"""
MCP Client Exception Classes

Custom exceptions for MCP client operations with clear error hierarchy.
"""

from typing import Any, Optional


class MCPClientError(Exception):
    """Base exception for all MCP client errors"""

    def __init__(self, message: str, details: Optional[Any] = None):
        self.message = message
        self.details = details
        super().__init__(message)


class MCPConnectionError(MCPClientError):
    """Raised when MCP server connection fails"""

    def __init__(
        self, message: str, url: Optional[str] = None, status_code: Optional[int] = None
    ):
        self.url = url
        self.status_code = status_code
        super().__init__(message, {"url": url, "status_code": status_code})


class MCPToolError(MCPClientError):
    """Raised when tool execution fails"""

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        tool_args: Optional[dict] = None,
    ):
        self.tool_name = tool_name
        self.tool_args = tool_args
        super().__init__(message, {"tool_name": tool_name, "tool_args": tool_args})


class MCPStreamError(MCPClientError):
    """Raised when streaming operations fail"""

    def __init__(self, message: str, stream_id: Optional[str] = None):
        self.stream_id = stream_id
        super().__init__(message, {"stream_id": stream_id})


class MCPConfigurationError(MCPClientError):
    """Raised when configuration is invalid"""

    def __init__(self, message: str, config_key: Optional[str] = None):
        self.config_key = config_key
        super().__init__(message, {"config_key": config_key})


class MCPAuthenticationError(MCPClientError):
    """Raised when authentication fails"""

    def __init__(self, message: str, provider: Optional[str] = None):
        self.provider = provider
        super().__init__(message, {"provider": provider})
