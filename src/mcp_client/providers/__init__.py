"""
LLM Provider Package

Plugin-based LLM provider implementations following Búvár patterns.
Supports OpenAI, Anthropic, and custom providers via dependency injection.
"""

from functools import lru_cache
from typing import Any, Dict, Optional, Type

# Provider registry for plugin architecture
PROVIDER_REGISTRY: Dict[str, Type] = {}


@lru_cache(maxsize=None)
def get_provider_class(provider_name: str) -> Type:
    """Factory pattern for provider resolution"""
    if provider_name not in PROVIDER_REGISTRY:
        raise ValueError(f"Unknown provider: {provider_name}")
    return PROVIDER_REGISTRY[provider_name]


def register_provider(name: str, provider_class: Type) -> None:
    """Plugin registration for custom providers"""
    PROVIDER_REGISTRY[name] = provider_class


# Auto-registration of built-in providers
def _register_builtin_providers():
    """Register built-in providers"""
    try:
        from .openai import OpenAIProvider

        register_provider("openai", OpenAIProvider)
    except ImportError:
        pass

    try:
        from .anthropic import AnthropicProvider

        register_provider("anthropic", AnthropicProvider)
    except ImportError:
        pass


# Initialize built-in providers
_register_builtin_providers()

__all__ = [
    "get_provider_class",
    "register_provider",
    "PROVIDER_REGISTRY",
]
