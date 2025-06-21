#!/usr/bin/env python3
"""
LLM Client Abstraction Layer
Provider-agnostic interface for OpenAI and Anthropic APIs
"""
import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, AsyncGenerator, Dict, List, Optional

import aiohttp

from .config import LLMConfig
from .exceptions import MCPAuthenticationError


@dataclass(frozen=True)
class LLMMessage:
    """Standardized message format across providers"""

    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    name: Optional[str] = None  # For tool/function messages
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None  # For tool response messages


@dataclass
class LLMResponse:
    """Standardized response format"""

    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    tool_calls: Optional[List[Dict[str, Any]]] = None


class LLMClient(ABC):
    """Abstract LLM client interface"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.logger = logging.getLogger(f"mcp_client.llm.{config.provider}")

    @abstractmethod
    async def complete(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> LLMResponse:
        """Complete a conversation"""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Stream a conversation response"""
        pass

    async def simple_complete(self, prompt: str, **kwargs) -> str:
        """Simple completion for single prompts"""
        messages = [LLMMessage(role="user", content=prompt)]
        response = await self.complete(messages, **kwargs)
        return response.content

    async def close(self):
        """Close client connections"""
        pass


class OpenAIClient(LLMClient):
    """OpenAI API client implementation"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.base_url or "https://api.openai.com/v1"
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if not self.session:
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            }
            timeout = aiohttp.ClientTimeout(total=60)
            self.session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        return self.session

    def _format_messages(self, messages: List[LLMMessage]) -> List[Dict[str, Any]]:
        """Convert to OpenAI message format"""
        formatted = []
        for msg in messages:
            openai_msg = {"role": msg.role, "content": msg.content}
            if msg.name:
                openai_msg["name"] = msg.name
            if msg.tool_calls:
                openai_msg["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                openai_msg["tool_call_id"] = msg.tool_call_id
            formatted.append(openai_msg)
        return formatted

    async def complete(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> LLMResponse:
        """Complete using OpenAI API"""
        session = await self._get_session()

        payload = {
            "model": self.config.model,
            "messages": self._format_messages(messages),
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            **kwargs,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
            
            # DEBUG: Print what we're sending to OpenAI (streaming)
            opensearch_tools = [t for t in tools if t.get('function', {}).get('name') == 'opensearch']
            if opensearch_tools:
                print(f"DEBUG OpenAI API streaming - opensearch tool:")
                print(json.dumps(opensearch_tools[0], indent=2))

        try:
            async with session.post(
                f"{self.base_url}/chat/completions", json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    if response.status == 401:
                        raise MCPAuthenticationError(
                            f"OpenAI authentication failed: {error_text}", "openai"
                        )
                    raise Exception(f"OpenAI API error {response.status}: {error_text}")

                data = await response.json()
                choice = data["choices"][0]

                return LLMResponse(
                    content=choice["message"]["content"] or "",
                    model=data["model"],
                    usage=data.get("usage", {}),
                    finish_reason=choice["finish_reason"],
                    tool_calls=choice["message"].get("tool_calls"),
                )
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            raise

    async def stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Stream using OpenAI API"""
        session = await self._get_session()

        payload = {
            "model": self.config.model,
            "messages": self._format_messages(messages),
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": True,
            **kwargs,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            async with session.post(
                f"{self.base_url}/chat/completions", json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    if response.status == 401:
                        raise MCPAuthenticationError(
                            f"OpenAI authentication failed: {error_text}", "openai"
                        )
                    raise Exception(f"OpenAI API error {response.status}: {error_text}")

                async for line in response.content:
                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]
                        if data_str == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                            choice = data["choices"][0]
                            delta = choice.get("delta", {})
                            if "content" in delta and delta["content"]:
                                yield delta["content"]
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            self.logger.error(f"OpenAI streaming error: {e}")
            raise

    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None


class AnthropicClient(LLMClient):
    """Anthropic API client implementation"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.base_url or "https://api.anthropic.com"
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if not self.session:
            headers = {
                "x-api-key": self.config.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }
            timeout = aiohttp.ClientTimeout(total=60)
            self.session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        return self.session

    def _format_messages(self, messages: List[LLMMessage]) -> tuple:
        """Convert to Anthropic message format"""
        formatted = []
        system_message = ""

        for msg in messages:
            if msg.role == "system":
                system_message += msg.content + "\n"
            else:
                # Map roles for Anthropic
                role = "assistant" if msg.role == "assistant" else "user"
                formatted.append({"role": role, "content": msg.content})

        return formatted, system_message.strip()

    async def complete(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> LLMResponse:
        """Complete using Anthropic API"""
        session = await self._get_session()

        formatted_messages, system_message = self._format_messages(messages)

        payload = {
            "model": self.config.model,
            "messages": formatted_messages,
            "max_tokens": self.config.max_tokens,
            **kwargs,
        }

        if system_message:
            payload["system"] = system_message

        # Note: Tool support for Anthropic would need to be implemented
        # based on their specific API format

        try:
            async with session.post(
                f"{self.base_url}/v1/messages", json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    if response.status == 401:
                        raise MCPAuthenticationError(
                            f"Anthropic authentication failed: {error_text}",
                            "anthropic",
                        )
                    raise Exception(
                        f"Anthropic API error {response.status}: {error_text}"
                    )

                data = await response.json()

                return LLMResponse(
                    content=data["content"][0]["text"] if data["content"] else "",
                    model=data["model"],
                    usage=data.get("usage", {}),
                    finish_reason=data.get("stop_reason", "stop"),
                )
        except Exception as e:
            self.logger.error(f"Anthropic API error: {e}")
            raise

    async def stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Stream using Anthropic API (fallback to complete)"""
        # For now, fall back to complete and yield the full response
        response = await self.complete(messages, tools, **kwargs)
        yield response.content

    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None


class LLMClientFactory:
    """Factory for creating LLM clients"""

    @staticmethod
    @lru_cache(maxsize=5)
    def create_client(config: LLMConfig) -> LLMClient:
        """Create appropriate LLM client based on provider"""
        if config.provider == "openai":
            return OpenAIClient(config)
        elif config.provider == "anthropic":
            return AnthropicClient(config)
        else:
            raise ValueError(f"Unsupported LLM provider: {config.provider}")

    @staticmethod
    async def test_client(client: LLMClient) -> bool:
        """Test if LLM client is working"""
        try:
            response = await client.simple_complete("Say 'Hello' if you can hear me.")
            return "hello" in response.lower()
        except Exception as e:
            logging.error(f"LLM client test failed: {e}")
            return False


# Utility functions
async def quick_complete(prompt: str, config: LLMConfig) -> str:
    """Quick completion utility"""
    client = LLMClientFactory.create_client(config)
    try:
        return await client.simple_complete(prompt)
    finally:
        await client.close()
