"""
Plugin System Package

Búvár-style plugin architecture with dependency injection and lifecycle management.
Supports dynamic plugin loading and hierarchical component stacking.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Optional, Protocol, Type, runtime_checkable


@runtime_checkable
class Plugin(Protocol):
    """Base plugin protocol for dependency injection"""

    name: str
    version: str

    async def initialize(self, context: Any) -> None: ...
    async def shutdown(self) -> None: ...


@dataclass
class PluginInfo:
    """Plugin metadata for registration"""

    name: str
    version: str
    description: str
    dependencies: List[str]
    plugin_class: Type[Plugin]


class PluginManager:
    """
    Plugin lifecycle manager following Búvár patterns

    Features:
    - Dependency resolution
    - Async lifecycle management
    - Context-aware initialization
    """

    def __init__(self):
        self._plugins: Dict[str, PluginInfo] = {}
        self._loaded: Dict[str, Plugin] = {}
        self._context_stack: List[Any] = []

    def register(self, info: PluginInfo) -> None:
        """Register plugin for lazy loading"""
        self._plugins[info.name] = info

    @lru_cache(maxsize=128)
    def resolve_dependencies(self, plugin_name: str) -> List[str]:
        """Resolve plugin dependency graph (cached)"""
        if plugin_name not in self._plugins:
            raise ValueError(f"Plugin '{plugin_name}' not found")

        info = self._plugins[plugin_name]
        deps = []

        for dep in info.dependencies:
            deps.extend(self.resolve_dependencies(dep))
            deps.append(dep)

        return deps

    async def load_plugin(self, name: str, context: Any = None) -> Plugin:
        """Load plugin with dependency injection"""
        if name in self._loaded:
            return self._loaded[name]

        if name not in self._plugins:
            raise ValueError(f"Plugin '{name}' not registered")

        # Load dependencies first
        deps = self.resolve_dependencies(name)
        for dep in deps:
            if dep not in self._loaded:
                await self.load_plugin(dep, context)

        # Initialize plugin
        info = self._plugins[name]
        plugin = info.plugin_class()

        await plugin.initialize(context)
        self._loaded[name] = plugin

        return plugin

    async def shutdown_all(self) -> None:
        """Graceful shutdown of all plugins"""
        # Shutdown in reverse order
        for plugin in reversed(list(self._loaded.values())):
            try:
                await plugin.shutdown()
            except Exception as e:
                # Log but continue shutdown
                print(f"Error shutting down plugin: {e}")

        self._loaded.clear()


# Global plugin manager
plugin_manager = PluginManager()


def register_plugin(
    name: str, version: str, description: str, dependencies: List[str] = None
) -> callable:
    """Decorator for plugin registration"""

    def decorator(cls: Type[Plugin]) -> Type[Plugin]:
        info = PluginInfo(
            name=name,
            version=version,
            description=description,
            dependencies=dependencies or [],
            plugin_class=cls,
        )
        plugin_manager.register(info)
        return cls

    return decorator


__all__ = [
    "Plugin",
    "PluginInfo",
    "PluginManager",
    "plugin_manager",
    "register_plugin",
]
