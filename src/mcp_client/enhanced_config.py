#!/usr/bin/env python3
"""
Configuration Management for LLM Agent
Supports OpenAI and Anthropic with environment-based configuration
"""
import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, Optional


@dataclass(frozen=True)
class LLMConfig:
    """LLM provider configuration"""

    provider: str  # "openai" | "anthropic"
    model: str
    api_key: str
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000

    def __post_init__(self):
        if self.provider not in ["openai", "anthropic"]:
            raise ValueError(f"Unsupported provider: {self.provider}")


@dataclass(frozen=True)
class MCPConfig:
    """MCP server connection configuration"""

    base_url: str = "http://localhost:8081"
    timeout: float = 60.0
    reconnect_delay: float = 1.0


@dataclass(frozen=True)
class AgentConfig:
    """Complete agent configuration"""

    llm: LLMConfig
    mcp: MCPConfig = field(default_factory=MCPConfig)
    debug: bool = False
    log_level: str = "INFO"


class ConfigManager:
    """Environment-based configuration management"""

    @staticmethod
    @lru_cache(maxsize=1)
    def load_from_env() -> AgentConfig:
        """Load configuration from environment variables"""

        # LLM Configuration
        provider = os.getenv("LLM_PROVIDER", "openai").lower()

        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            model = os.getenv("OPENAI_MODEL", "gpt-4")
            base_url = os.getenv("OPENAI_BASE_URL")
        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            model = os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")
            base_url = os.getenv("ANTHROPIC_BASE_URL")
        else:
            raise ValueError(f"Unknown provider: {provider}")

        if not api_key:
            raise ValueError(
                f"Missing API key for {provider}. Set {provider.upper()}_API_KEY environment variable."
            )

        llm_config = LLMConfig(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2000")),
        )

        # MCP Configuration
        mcp_config = MCPConfig(
            base_url=os.getenv("MCP_BASE_URL", "http://localhost:8081"),
            timeout=float(os.getenv("MCP_TIMEOUT", "60.0")),
            reconnect_delay=float(os.getenv("MCP_RECONNECT_DELAY", "1.0")),
        )

        return AgentConfig(
            llm=llm_config,
            mcp=mcp_config,
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )

    @staticmethod
    def create_openai_config(api_key: str, model: str = "gpt-4") -> AgentConfig:
        """Create OpenAI configuration"""
        llm_config = LLMConfig(provider="openai", model=model, api_key=api_key)
        return AgentConfig(llm=llm_config)

    @staticmethod
    def create_anthropic_config(
        api_key: str, model: str = "claude-3-sonnet-20240229"
    ) -> AgentConfig:
        """Create Anthropic configuration"""
        llm_config = LLMConfig(provider="anthropic", model=model, api_key=api_key)
        return AgentConfig(llm=llm_config)


# Predefined configurations for easy switching
OPENAI_CONFIGS = {
    "gpt-4": "gpt-4",
    "gpt-4-turbo": "gpt-4-turbo-preview",
    "gpt-3.5": "gpt-3.5-turbo",
}

ANTHROPIC_CONFIGS = {
    "claude-3-opus": "claude-3-opus-20240229",
    "claude-3-sonnet": "claude-3-sonnet-20240229",
    "claude-3-haiku": "claude-3-haiku-20240307",
}


def get_available_models(provider: str) -> Dict[str, str]:
    """Get available models for a provider"""
    if provider == "openai":
        return OPENAI_CONFIGS
    elif provider == "anthropic":
        return ANTHROPIC_CONFIGS
    else:
        return {}


if __name__ == "__main__":
    # Example configuration usage
    print("🔧 Configuration Examples:")

    # Environment-based config
    try:
        config = ConfigManager.load_from_env()
        print(f"✅ Loaded from environment: {config.llm.provider} - {config.llm.model}")
    except ValueError as e:
        print(f"❌ Environment config error: {e}")

    # Direct config creation
    if api_key := os.getenv("OPENAI_API_KEY"):
        openai_config = ConfigManager.create_openai_config(api_key)
        print(f"✅ OpenAI config created: {openai_config.llm.model}")

    print(f"📋 Available OpenAI models: {list(OPENAI_CONFIGS.keys())}")
    print(f"📋 Available Anthropic models: {list(ANTHROPIC_CONFIGS.keys())}")
