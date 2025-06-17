"""
Core MCP Client Components

Foundation classes and protocols following Búvár architecture patterns.
Provides base abstractions for dependency injection and plugin systems.
"""
from typing import Protocol, runtime_checkable, Any, Dict, Optional
from abc import ABC, abstractmethod

@runtime_checkable
class MCPTransport(Protocol):
    """Transport protocol for dependency injection"""
    
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def send_message(self, message: Dict[str, Any]) -> None: ...
    async def read_messages(self) -> Any: ...

@runtime_checkable  
class LLMProvider(Protocol):
    """LLM provider protocol for plugin architecture"""
    
    async def complete(self, messages: list, **kwargs) -> Any: ...
    async def stream(self, messages: list, **kwargs) -> Any: ...
    async def close(self) -> None: ...

class ContextRegistry:
    """Hierarchical context management following Búvár patterns"""
    
    def __init__(self):
        self._contexts: Dict[str, Any] = {}
        self._parent: Optional['ContextRegistry'] = None
    
    def set_parent(self, parent: 'ContextRegistry') -> None:
        self._parent = parent
    
    def register(self, name: str, value: Any) -> None:
        self._contexts[name] = value
    
    def resolve(self, name: str) -> Any:
        if name in self._contexts:
            return self._contexts[name]
        if self._parent:
            return self._parent.resolve(name)
        raise KeyError(f"Context '{name}' not found")
    
    def create_child(self) -> 'ContextRegistry':
        child = ContextRegistry()
        child.set_parent(self)
        return child

# Global context registry
global_context = ContextRegistry()

__all__ = [
    "MCPTransport",
    "LLMProvider", 
    "ContextRegistry",
    "global_context",
]
