"""
Unit tests for OpenRouter LLM client.

Following TDD approach - these tests are written BEFORE the implementation.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

# This import will fail initially - that's expected in RED phase
try:
    from browser_agent.agent.llm_client import (
        LLMClient,
        OpenRouterClient,
        LLMError,
        LLMAPIError,
        LLMTimeoutError,
    )
except ImportError:
    pytest.skip("llm_client module not yet implemented", allow_module_level=True)


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient for testing."""
    client = AsyncMock()
    return client


@pytest.fixture
def openrouter_client(mock_httpx_client):
    """Create OpenRouterClient with mocked HTTP client."""
    with patch("httpx.AsyncClient", return_value=mock_httpx_client):
        client = OpenRouterClient(
            api_key="test_api_key",
            model="anthropic/claude-3.5-sonnet",
            timeout_seconds=30,
        )
        client._client = mock_httpx_client
        return client


class TestLLMClientProtocol:
    """Test that LLMClient protocol is defined correctly."""

    def test_llm_client_protocol_exists(self):
        """LLMClient protocol should be defined."""
        assert hasattr(LLMClient, "chat_completion")

class TestOpenRouterClient:
    """Test OpenRouter client implementation."""

    @pytest.mark.asyncio
    async def test_chat_completion_returns_response(self, openrouter_client, mock_httpx_client):
        """
        🔴 RED TEST: chat_completion() should return LLM response.

        This test will FAIL until we implement the OpenRouterClient.
        """
        # Arrange: Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "gen-123",
            "model": "anthropic/claude-3.5-sonnet",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "I understand you want to navigate to google.com",
                        "tool_calls": [
                            {
                                "id": "call_abc",
                                "type": "function",
                                "function": {
                                    "name": "navigate",
                                    "arguments": '{"url": "https://google.com"}'
                                }
                            }
                        ]
                    },
                    "finish_reason": "tool_calls"
                }
            ]
        }
        mock_httpx_client.post.return_value = mock_response

        # Act: Call chat_completion
        result = await openrouter_client.chat_completion(
            messages=[{"role": "user", "content": "Go to google.com"}],
            tools=[]
        )

        # Assert: Response should contain tool calls
        assert result is not None
        assert "choices" in result
        assert len(result["choices"]) > 0
        assert "tool_calls" in result["choices"][0]["message"]

        # Verify API was called correctly
        mock_httpx_client.post.assert_called_once()
        call_args = mock_httpx_client.post.call_args
        assert call_args[0][0] == "https://openrouter.ai/api/v1/chat/completions"

    @pytest.mark.asyncio
    async def test_chat_completion_includes_auth_header(self, openrouter_client, mock_httpx_client):
        """
        🔴 RED TEST: Requests should include Authorization header with API key.
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "OK"}}]
        }
        mock_httpx_client.post.return_value = mock_response

        await openrouter_client.chat_completion(
            messages=[{"role": "user", "content": "test"}],
            tools=[]
        )

        # Verify headers include Authorization
        call_args = mock_httpx_client.post.call_args
        headers = call_args[1]["headers"]
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_api_key"

    @pytest.mark.asyncio
    async def test_chat_completion_with_tools(self, openrouter_client, mock_httpx_client):
        """
        🔴 RED TEST: chat_completion should send tools in the request.
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "OK"}}]
        }
        mock_httpx_client.post.return_value = mock_response

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "navigate",
                    "description": "Navigate to a URL",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]

        await openrouter_client.chat_completion(
            messages=[{"role": "user", "content": "Go to google.com"}],
            tools=tools
        )

        # Verify tools were included in request body
        call_args = mock_httpx_client.post.call_args
        request_body = call_args[1]["json"]
        assert "tools" in request_body
        assert request_body["tools"] == tools

    @pytest.mark.asyncio
    async def test_chat_completion_handles_api_error(self, openrouter_client, mock_httpx_client):
        """
        🔴 RED TEST: Should raise LLMAPIError on API errors (4xx, 5xx).
        """
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": {"message": "Internal server error"}}
        mock_httpx_client.post.return_value = mock_response

        with pytest.raises(LLMAPIError) as exc_info:
            await openrouter_client.chat_completion(
                messages=[{"role": "user", "content": "test"}],
                tools=[]
            )

        assert "500" in str(exc_info.value) or "Internal server error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_chat_completion_handles_timeout(self, openrouter_client, mock_httpx_client):
        """
        🔴 RED TEST: Should raise LLMTimeoutError on timeout.
        """
        import httpx
        mock_httpx_client.post.side_effect = httpx.TimeoutException("Request timed out")

        with pytest.raises(LLMTimeoutError):
            await openrouter_client.chat_completion(
                messages=[{"role": "user", "content": "test"}],
                tools=[]
            )

    @pytest.mark.asyncio
    async def test_chat_completion_retries_on_transient_failure(self, openrouter_client, mock_httpx_client):
        """
        🔴 RED TEST: Should retry on transient failures (429, 503).
        """
        # First call fails with 429, second succeeds
        error_response = MagicMock()
        error_response.status_code = 429
        error_response.json.return_value = {"error": {"message": "Rate limited"}}

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "Success after retry"}}]
        }

        mock_httpx_client.post.side_effect = [error_response, success_response]

        result = await openrouter_client.chat_completion(
            messages=[{"role": "user", "content": "test"}],
            tools=[],
            max_retries=2
        )

        # Should succeed after retry
        assert result is not None
        assert mock_httpx_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_close_client(self, openrouter_client, mock_httpx_client):
        """
        🔴 RED TEST: close() should close the HTTP client.
        """
        await openrouter_client.close()
        mock_httpx_client.aclose.assert_called_once()


class TestLLMClientInitialization:
    """Test client initialization and configuration."""

    def test_openrouter_client_requires_api_key(self):
        """Should raise error if API key is missing."""
        with pytest.raises((ValueError, TypeError)):
            OpenRouterClient(api_key="", model="test-model")

    def test_openrouter_client_sets_default_timeout(self):
        """Should set default timeout if not provided."""
        client = OpenRouterClient(api_key="test_key", model="test-model")
        assert client.timeout_seconds > 0
        assert client.timeout_seconds == 30  # Expected default

    def test_openrouter_client_accepts_custom_timeout(self):
        """Should accept custom timeout value."""
        client = OpenRouterClient(
            api_key="test_key",
            model="test-model",
            timeout_seconds=60
        )
        assert client.timeout_seconds == 60


# Run tests to verify they FAIL (RED phase)
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
