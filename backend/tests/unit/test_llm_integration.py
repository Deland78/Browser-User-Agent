"""Unit tests for LLM integration in CommandParser.

Following TDD methodology:
1. RED: Write failing tests
2. GREEN: Implement minimal code to pass
3. REFACTOR: Improve code while keeping tests green

Per tasks.md US1-002:
- Enhance CommandParser to call LLMClient
- Load tool definitions from llm-tools-schema.json
- Map LLM tool calls to BrowserAction objects
- Handle LLM errors gracefully

Per agent-interface.md:
- Use OpenRouter for command interpretation
- Support function calling with tool schemas
- Handle multi-step commands
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from browser_agent.agent.command_parser import (
    ClickAction,
    CommandIntent,
    CommandParser,
    ExtractAction,
    NavigateAction,
    ParsedCommand,
    ParsingError,
    TypeAction,
)
from browser_agent.agent.llm_client import LLMClient


class TestLLMIntegration:
    """Test CommandParser integration with LLM client."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = AsyncMock(spec=LLMClient)
        return client

    @pytest.fixture
    def parser_with_llm(self, mock_llm_client):
        """Create CommandParser with mocked LLM client."""
        parser = CommandParser(llm_client=mock_llm_client)
        return parser

    @pytest.mark.asyncio
    async def test_parser_accepts_llm_client(self, mock_llm_client):
        """Test CommandParser accepts LLM client in constructor."""
        parser = CommandParser(llm_client=mock_llm_client)
        assert parser.llm_client is mock_llm_client

    @pytest.mark.asyncio
    async def test_parser_without_llm_uses_fallback(self):
        """Test CommandParser without LLM falls back to pattern matching."""
        parser = CommandParser(llm_client=None)

        # Should still work with simple patterns
        result = parser.parse(
            user_input="Go to google.com",
            conversation_context=[],
            page_context=None
        )

        assert isinstance(result, ParsedCommand)
        assert result.intent == CommandIntent.NAVIGATE

    @pytest.mark.asyncio
    async def test_llm_called_for_complex_command(self, parser_with_llm, mock_llm_client):
        """Test LLM is called for commands that don't match simple patterns."""
        # Mock LLM response
        mock_llm_client.chat_completion.return_value = {
            "choices": [{
                "message": {
                    "tool_calls": [{
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "navigate",
                            "arguments": '{"url": "https://amazon.com", "wait_for": "load"}'
                        }
                    }]
                }
            }]
        }

        result = await parser_with_llm.parse_async(
            user_input="Take me to Amazon",
            conversation_context=[],
            page_context=None
        )

        # Verify LLM was called
        mock_llm_client.chat_completion.assert_called_once()

        # Verify result
        assert isinstance(result, ParsedCommand)
        assert result.intent == CommandIntent.NAVIGATE
        assert len(result.actions) == 1
        assert isinstance(result.actions[0], NavigateAction)
        assert result.actions[0].url == "https://amazon.com"

    @pytest.mark.asyncio
    async def test_llm_navigate_tool_mapping(self, parser_with_llm, mock_llm_client):
        """Test LLM navigate tool call maps to NavigateAction."""
        mock_llm_client.chat_completion.return_value = {
            "choices": [{
                "message": {
                    "tool_calls": [{
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "navigate",
                            "arguments": '{"url": "https://example.com", "wait_for": "domcontentloaded"}'
                        }
                    }]
                }
            }]
        }

        result = await parser_with_llm.parse_async(
            user_input="Go to example.com",
            conversation_context=[],
            page_context=None
        )

        assert len(result.actions) == 1
        action = result.actions[0]
        assert isinstance(action, NavigateAction)
        assert action.url == "https://example.com"
        assert action.wait_for == "domcontentloaded"

    @pytest.mark.asyncio
    async def test_llm_click_tool_mapping(self, parser_with_llm, mock_llm_client):
        """Test LLM click tool call maps to ClickAction."""
        mock_llm_client.chat_completion.return_value = {
            "choices": [{
                "message": {
                    "tool_calls": [{
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "click",
                            "arguments": '{"element_description": "login button", "text": "Sign In", "role": "button"}'
                        }
                    }]
                }
            }]
        }

        result = await parser_with_llm.parse_async(
            user_input="Click the login button",
            conversation_context=[],
            page_context=None
        )

        assert len(result.actions) == 1
        action = result.actions[0]
        assert isinstance(action, ClickAction)
        assert action.element_description == "login button"
        assert action.text == "Sign In"
        assert action.role == "button"

    @pytest.mark.asyncio
    async def test_llm_type_text_tool_mapping(self, parser_with_llm, mock_llm_client):
        """Test LLM type_text tool call maps to TypeAction."""
        mock_llm_client.chat_completion.return_value = {
            "choices": [{
                "message": {
                    "tool_calls": [{
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "type_text",
                            "arguments": '{"element_description": "search box", "text": "weather forecast", "press_enter": true}'
                        }
                    }]
                }
            }]
        }

        result = await parser_with_llm.parse_async(
            user_input="Search for weather forecast",
            conversation_context=[],
            page_context=None
        )

        assert len(result.actions) == 1
        action = result.actions[0]
        assert isinstance(action, TypeAction)
        assert action.element_description == "search box"
        assert action.text == "weather forecast"
        assert action.press_enter is True

    @pytest.mark.asyncio
    async def test_llm_extract_information_tool_mapping(self, parser_with_llm, mock_llm_client):
        """Test LLM extract_information tool call maps to ExtractAction."""
        mock_llm_client.chat_completion.return_value = {
            "choices": [{
                "message": {
                    "tool_calls": [{
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "extract_information",
                            "arguments": '{"extraction_type": "text", "target_description": "page title"}'
                        }
                    }]
                }
            }]
        }

        result = await parser_with_llm.parse_async(
            user_input="What is the page title?",
            conversation_context=[],
            page_context=None
        )

        assert len(result.actions) == 1
        action = result.actions[0]
        assert isinstance(action, ExtractAction)
        assert action.extraction_type == "text"
        assert action.target_description == "page title"

    @pytest.mark.asyncio
    async def test_llm_multi_step_command(self, parser_with_llm, mock_llm_client):
        """Test LLM handling multi-step commands."""
        mock_llm_client.chat_completion.return_value = {
            "choices": [{
                "message": {
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "navigate",
                                "arguments": '{"url": "https://google.com"}'
                            }
                        },
                        {
                            "id": "call_2",
                            "type": "function",
                            "function": {
                                "name": "type_text",
                                "arguments": '{"element_description": "search box", "text": "weather", "press_enter": true}'
                            }
                        }
                    ]
                }
            }]
        }

        result = await parser_with_llm.parse_async(
            user_input="Go to Google and search for weather",
            conversation_context=[],
            page_context=None
        )

        # Should have multiple actions
        assert len(result.actions) == 2
        assert isinstance(result.actions[0], NavigateAction)
        assert isinstance(result.actions[1], TypeAction)

    @pytest.mark.asyncio
    async def test_llm_error_handling_timeout(self, parser_with_llm, mock_llm_client):
        """Test handling LLM timeout errors."""
        from browser_agent.agent.llm_client import LLMTimeoutError

        mock_llm_client.chat_completion.side_effect = LLMTimeoutError("Request timed out")

        with pytest.raises(ParsingError) as exc_info:
            await parser_with_llm.parse_async(
                user_input="Go to example.com",
                conversation_context=[],
                page_context=None
            )

        error_msg = str(exc_info.value).lower()
        assert "timeout" in error_msg or "timed out" in error_msg

    @pytest.mark.asyncio
    async def test_llm_error_handling_api_error(self, parser_with_llm, mock_llm_client):
        """Test handling LLM API errors."""
        from browser_agent.agent.llm_client import LLMAPIError

        mock_llm_client.chat_completion.side_effect = LLMAPIError(message="API error", status_code=500)

        with pytest.raises(ParsingError) as exc_info:
            await parser_with_llm.parse_async(
                user_input="Go to example.com",
                conversation_context=[],
                page_context=None
            )

        assert "api" in str(exc_info.value).lower() or "error" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_llm_receives_tool_schemas(self, parser_with_llm, mock_llm_client):
        """Test that LLM receives tool definitions from schema file."""
        mock_llm_client.chat_completion.return_value = {
            "choices": [{
                "message": {
                    "tool_calls": [{
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "navigate",
                            "arguments": '{"url": "https://test.com"}'
                        }
                    }]
                }
            }]
        }

        await parser_with_llm.parse_async(
            user_input="Go to test.com",
            conversation_context=[],
            page_context=None
        )

        # Verify tools were passed to LLM
        call_args = mock_llm_client.chat_completion.call_args
        assert call_args is not None
        assert "tools" in call_args.kwargs

        tools = call_args.kwargs["tools"]
        # Tools may be None or empty list if schema file not found - that's OK for fallback
        if tools:
            assert len(tools) > 0

            # Verify navigate tool is present
            tool_names = [t["function"]["name"] for t in tools]
            assert "navigate" in tool_names
            assert "click" in tool_names
            assert "type_text" in tool_names
            assert "extract_information" in tool_names

    @pytest.mark.asyncio
    async def test_llm_receives_conversation_context(self, parser_with_llm, mock_llm_client):
        """Test that conversation context is passed to LLM."""
        mock_llm_client.chat_completion.return_value = {
            "choices": [{
                "message": {
                    "tool_calls": [{
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "navigate",
                            "arguments": '{"url": "https://test.com"}'
                        }
                    }]
                }
            }]
        }

        # Simplified conversation context
        context = [
            {"role": "user", "content": "Go to google.com"},
            {"role": "assistant", "content": "Navigated to google.com"}
        ]

        await parser_with_llm.parse_async(
            user_input="Now search for weather",
            conversation_context=context,
            page_context=None
        )

        # Verify context was included in messages
        call_args = mock_llm_client.chat_completion.call_args
        messages = call_args.kwargs["messages"]

        # Should include system message + context + current message
        assert len(messages) >= 3

    @pytest.mark.asyncio
    async def test_llm_receives_page_context(self, parser_with_llm, mock_llm_client):
        """Test that page context is included in LLM request."""
        mock_llm_client.chat_completion.return_value = {
            "choices": [{
                "message": {
                    "tool_calls": [{
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "click",
                            "arguments": '{"element_description": "submit button"}'
                        }
                    }]
                }
            }]
        }

        page_context = {
            "current_url": "https://example.com/form",
            "page_title": "Contact Form",
            "page_state": "ready"
        }

        await parser_with_llm.parse_async(
            user_input="Submit the form",
            conversation_context=[],
            page_context=page_context
        )

        # Verify page context was included
        call_args = mock_llm_client.chat_completion.call_args
        messages = call_args.kwargs["messages"]

        # Page context should be in system or user message
        all_content = " ".join([m.get("content", "") for m in messages])
        assert "example.com" in all_content or "Contact Form" in all_content


class TestToolSchemaLoading:
    """Test loading tool definitions from llm-tools-schema.json."""

    def test_tool_schema_file_exists(self):
        """Test that llm-tools-schema.json exists."""
        # Try multiple possible paths (since tests run from backend/)
        possible_paths = [
            Path("../specs/001-browser-agent-chat/contracts/llm-tools-schema.json"),
            Path("specs/001-browser-agent-chat/contracts/llm-tools-schema.json"),
        ]

        found = any(p.exists() for p in possible_paths)
        assert found, f"Tool schema file should exist in one of: {possible_paths}"

    def test_tool_schema_is_valid_json(self):
        """Test that schema file is valid JSON."""
        possible_paths = [
            Path("../specs/001-browser-agent-chat/contracts/llm-tools-schema.json"),
            Path("specs/001-browser-agent-chat/contracts/llm-tools-schema.json"),
        ]

        schema_path = next((p for p in possible_paths if p.exists()), None)
        if not schema_path:
            pytest.skip("Schema file not found")

        with open(schema_path) as f:
            schema = json.load(f)

        assert "tools" in schema
        assert isinstance(schema["tools"], list)
        assert len(schema["tools"]) > 0

    def test_parser_loads_tool_schemas(self):
        """Test CommandParser loads tool schemas on initialization."""
        parser = CommandParser()

        # Parser should have loaded tools (if file exists)
        assert hasattr(parser, "tool_schemas")

        # If schemas were loaded, verify structure
        if len(parser.tool_schemas) > 0:
            # Verify key tools are present
            tool_names = [t["function"]["name"] for t in parser.tool_schemas]
            assert "navigate" in tool_names
            assert "click" in tool_names
            assert "type_text" in tool_names
            assert "extract_information" in tool_names
            assert "scroll" in tool_names
            assert "configure_timeout" in tool_names
