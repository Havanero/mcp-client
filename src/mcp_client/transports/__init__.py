"""
Transport Layer Package

MCP client transport abstractions for various communication protocols.
Plugin-based architecture supporting multiple transport backends.
"""
from functools import lru_cache
from typing import Type, Dict, Any

from .stdio import StdioTransport
from .sse import SSEMCPClient as SSETransport  # Alias for consistency
from .websocket import WebSocketMCPClient as WebSocketTransport  # Alias for consistency
from .http import HTTPMCPClient as HTTPTransport  # Alias for consistency

# Transport registry for dependency injection
TRANSPORT_REGISTRY: Dict[str, Type] = {
    "stdio": StdioTransport,
    "sse": SSETransport,
    "websocket": WebSocketTransport,
    "http": HTTPTransport,
}

@lru_cache(maxsize=None)
def get_transport_class(transport_type: str) -> Type:
    """Factory pattern for transport resolution"""
    if transport_type not in TRANSPORT_REGISTRY:
        raise ValueError(f"Unknown transport type: {transport_type}")
    return TRANSPORT_REGISTRY[transport_type]

def register_transport(name: str, transport_class: Type) -> None:
    """Plugin registration for custom transports"""
    TRANSPORT_REGISTRY[name] = transport_class

__all__ = [
    "StdioTransport",
    "SSETransport", 
    "WebSocketTransport",
    "HTTPTransport",
    "get_transport_class",
    "register_transport",
    "TRANSPORT_REGISTRY",
]
