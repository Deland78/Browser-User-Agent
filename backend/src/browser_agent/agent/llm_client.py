"""
OpenRouter LLM client for browser automation agent.

This module provides an abstraction for communicating with OpenRouter.ai API
to interpret natural language commands using Claude 3.5 Sonnet.

Protocol-based design allows for easy testing and future LLM provider swaps.
"""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Protocol
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================


class LLMError(Exception):
    """Base exception for all LLM client errors."""
    pass


class LLMAPIError(LLMError):
    """Raised when LLM API returns an error response (4xx, 5xx)."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"LLM API error {status_code}: {message}")


class LLMTimeoutError(LLMError):
    """Raised when LLM API request times out."""
    pass


class LLMConnectionError(LLMError):
    """Raised when connection to LLM API fails."""
    pass


# ============================================================================
# Protocol Definition
# ============================================================================


class LLMClient(Protocol):
    """
    Protocol for LLM clients supporting chat completions with function calling.

    This protocol defines the interface for any LLM provider that can:
    1. Accept chat messages and tool definitions
    2. Return responses with tool calls
    3. Handle retries and error scenarios
    """

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Send chat completion request with function calling support.

        Args:
            messages: List of chat messages (role + content)
            tools: List of tool definitions in OpenAI format
            max_retries: Maximum number of retry attempts for transient failures

        Returns:
            API response containing choices with tool calls

        Raises:
            LLMAPIError: On API errors (4xx, 5xx)
            LLMTimeoutError: On request timeout
            LLMConnectionError: On connection failures
        """
        ...

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        ...


# ============================================================================
# OpenRouter Implementation
# ============================================================================


@dataclass
class OpenRouterConfig:
    """Configuration for OpenRouter client."""
    api_key: str
    model: str = "anthropic/claude-3.5-sonnet"
    base_url: str = "https://openrouter.ai/api/v1"
    timeout_seconds: int = 30
    max_retries: int = 3


class OpenRouterClient:
    """
    OpenRouter.ai API client for chat completions with function calling.

    Implements the LLMClient protocol using OpenRouter as the provider.
    Supports retry logic, proper error handling, and resource cleanup.

    Example:
        >>> client = OpenRouterClient(api_key="sk-...", model="anthropic/claude-3.5-sonnet")
        >>> response = await client.chat_completion(
        ...     messages=[{"role": "user", "content": "Go to google.com"}],
        ...     tools=tool_definitions
        ... )
        >>> await client.close()
    """

    def __init__(
        self,
        api_key: str,
        model: str = "anthropic/claude-3.5-sonnet",
        base_url: str = "https://openrouter.ai/api/v1",
        timeout_seconds: int = 30,
    ):
        """
        Initialize OpenRouter client.

        Args:
            api_key: OpenRouter API key (required)
            model: Model identifier (default: claude-3.5-sonnet)
            base_url: API base URL (default: OpenRouter v1 endpoint)
            timeout_seconds: Request timeout in seconds (default: 30)

        Raises:
            ValueError: If api_key is empty
        """
        if not api_key:
            raise ValueError("OpenRouter API key is required")

        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

        self._client: Optional[httpx.AsyncClient] = None

        logger.info(
            "Initialized OpenRouter client",
            extra={
                "model": model,
                "timeout_seconds": timeout_seconds,
                "base_url": base_url,
            }
        )

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client (lazy initialization)."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout_seconds),
                headers={
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Send chat completion request to OpenRouter with function calling.

        Implements exponential backoff retry logic for transient failures
        (rate limits, temporary server errors).

        Args:
            messages: Chat messages in OpenAI format
            tools: Tool/function definitions
            max_retries: Maximum retry attempts (default: 3)

        Returns:
            OpenRouter API response

        Raises:
            LLMAPIError: On permanent API errors
            LLMTimeoutError: On request timeout
            LLMConnectionError: On connection failures
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/browser-user-agent",  # Required by OpenRouter
            "X-Title": "Browser User Agent",  # Optional but recommended
        }

        # Build request body
        request_body: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }

        # Only include tools if provided
        if tools:
            request_body["tools"] = tools

        client = self._get_client()
        last_exception: Optional[Exception] = None

        # Retry logic with exponential backoff
        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"Sending chat completion request (attempt {attempt + 1}/{max_retries})",
                    extra={
                        "model": self.model,
                        "message_count": len(messages),
                        "tool_count": len(tools),
                    }
                )

                response = await client.post(
                    url,
                    json=request_body,
                    headers=headers,
                )

                # Handle successful response
                if response.status_code == 200:
                    result = response.json()
                    logger.info(
                        "Chat completion successful",
                        extra={
                            "model": self.model,
                            "choices": len(result.get("choices", [])),
                        }
                    )
                    return result

                # Handle transient errors that should be retried
                if response.status_code in (429, 503, 504):
                    error_data = response.json() if response.text else {}
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")

                    logger.warning(
                        f"Transient error (status {response.status_code}), retrying...",
                        extra={
                            "status_code": response.status_code,
                            "error_message": error_msg,
                            "attempt": attempt + 1,
                            "max_retries": max_retries,
                        }
                    )

                    if attempt < max_retries - 1:
                        # Exponential backoff: 1s, 2s, 4s
                        wait_time = 2 ** attempt
                        await asyncio.sleep(wait_time)
                        continue

                # Handle permanent errors
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("error", {}).get("message", "Unknown error")

                logger.error(
                    "API error",
                    extra={
                        "status_code": response.status_code,
                        "error_message": error_msg,
                    }
                )
                raise LLMAPIError(response.status_code, error_msg)

            except httpx.TimeoutException as e:
                logger.error("Request timed out", extra={"timeout_seconds": self.timeout_seconds})
                raise LLMTimeoutError(f"Request timed out after {self.timeout_seconds}s") from e

            except httpx.ConnectError as e:
                logger.error("Connection failed", extra={"base_url": self.base_url})
                raise LLMConnectionError(f"Failed to connect to {self.base_url}") from e

            except LLMError:
                # Re-raise our custom errors
                raise

            except Exception as e:
                # Catch unexpected errors
                logger.exception("Unexpected error during chat completion")
                last_exception = e

                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue

        # If we exhausted all retries
        raise LLMError(
            f"Failed after {max_retries} attempts. Last error: {last_exception}"
        ) from last_exception

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.debug("OpenRouter client closed")


# ============================================================================
# Factory Function
# ============================================================================


def create_openrouter_client(
    api_key: str,
    model: str = "anthropic/claude-3.5-sonnet",
    timeout_seconds: int = 30,
) -> OpenRouterClient:
    """
    Factory function to create an OpenRouter client.

    Args:
        api_key: OpenRouter API key
        model: Model identifier (default: claude-3.5-sonnet)
        timeout_seconds: Request timeout (default: 30)

    Returns:
        Configured OpenRouterClient instance
    """
    return OpenRouterClient(
        api_key=api_key,
        model=model,
        timeout_seconds=timeout_seconds,
    )
