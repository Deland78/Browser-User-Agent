"""Unit tests for CommandParser foundation.

Following TDD methodology:
1. RED: Write failing tests
2. GREEN: Implement minimal code to pass
3. REFACTOR: Improve code while keeping tests green

Per tasks.md US1-001:
- CommandParser class with parse() method
- ParsedCommand dataclass with intent, actions, confidence_score
- CommandIntent enum (navigate, interact, extract, configure)
- BrowserAction structures for different action types

Per agent-interface.md:
- parse() accepts user_input, conversation_context, page_context
- Returns ParsedCommand with structured actions
- Confidence score 0.0-1.0
"""

import pytest
from datetime import datetime
from typing import List, Optional

from browser_agent.agent.command_parser import (
    CommandParser,
    ParsedCommand,
    CommandIntent,
    BrowserAction,
    NavigateAction,
    ClickAction,
    TypeAction,
    ExtractAction,
    ScrollAction,
    ConfigureAction,
    ParsingError,
)


class TestCommandIntent:
    """Test CommandIntent enum."""

    def test_command_intent_values(self):
        """Test all command intent types exist."""
        assert CommandIntent.NAVIGATE == "navigate"
        assert CommandIntent.INTERACT == "interact"
        assert CommandIntent.EXTRACT == "extract"
        assert CommandIntent.CONFIGURE == "configure"


class TestBrowserActions:
    """Test BrowserAction dataclasses."""

    def test_navigate_action(self):
        """Test NavigateAction structure."""
        action = NavigateAction(
            url="https://google.com",
            wait_for="load"
        )

        assert action.url == "https://google.com"
        assert action.wait_for == "load"

    def test_click_action(self):
        """Test ClickAction structure."""
        action = ClickAction(
            element_description="login button",
            text="Sign In",
            role="button"
        )

        assert action.element_description == "login button"
        assert action.text == "Sign In"
        assert action.role == "button"

    def test_type_action(self):
        """Test TypeAction structure."""
        action = TypeAction(
            element_description="search box",
            text="weather forecast",
            clear_first=True,
            press_enter=True
        )

        assert action.element_description == "search box"
        assert action.text == "weather forecast"
        assert action.clear_first is True
        assert action.press_enter is True

    def test_extract_action(self):
        """Test ExtractAction structure."""
        action = ExtractAction(
            extraction_type="text",
            target_description="page title"
        )

        assert action.extraction_type == "text"
        assert action.target_description == "page title"

    def test_scroll_action(self):
        """Test ScrollAction structure."""
        action = ScrollAction(
            direction="down",
            pixels=500
        )

        assert action.direction == "down"
        assert action.pixels == 500

    def test_configure_action(self):
        """Test ConfigureAction structure."""
        action = ConfigureAction(
            setting="timeout",
            value=60
        )

        assert action.setting == "timeout"
        assert action.value == 60


class TestParsedCommand:
    """Test ParsedCommand dataclass."""

    def test_create_parsed_command(self):
        """Test creating a ParsedCommand."""
        navigate_action = NavigateAction(url="https://example.com", wait_for="load")

        parsed = ParsedCommand(
            original_input="Go to example.com",
            intent=CommandIntent.NAVIGATE,
            actions=[navigate_action],
            confidence_score=0.95,
            ambiguities=[],
            context_used=[]
        )

        assert parsed.original_input == "Go to example.com"
        assert parsed.intent == CommandIntent.NAVIGATE
        assert len(parsed.actions) == 1
        assert isinstance(parsed.actions[0], NavigateAction)
        assert parsed.confidence_score == 0.95
        assert parsed.ambiguities == []
        assert parsed.context_used == []

    def test_parsed_command_multi_action(self):
        """Test ParsedCommand with multiple actions."""
        actions = [
            NavigateAction(url="https://google.com", wait_for="load"),
            TypeAction(element_description="search box", text="weather", press_enter=True),
        ]

        parsed = ParsedCommand(
            original_input="Go to google and search for weather",
            intent=CommandIntent.INTERACT,
            actions=actions,
            confidence_score=0.88,
            ambiguities=["multiple interpretations possible"],
            context_used=[]
        )

        assert len(parsed.actions) == 2
        assert parsed.confidence_score == 0.88
        assert len(parsed.ambiguities) == 1

    def test_confidence_score_validation(self):
        """Test confidence score must be between 0.0 and 1.0."""
        # Valid confidence scores
        for score in [0.0, 0.5, 0.9, 1.0]:
            parsed = ParsedCommand(
                original_input="test",
                intent=CommandIntent.NAVIGATE,
                actions=[NavigateAction(url="https://test.com", wait_for="load")],
                confidence_score=score,
                ambiguities=[],
                context_used=[]
            )
            assert parsed.confidence_score == score

        # Invalid confidence scores should raise error
        with pytest.raises(ValueError) as exc_info:
            ParsedCommand(
                original_input="test",
                intent=CommandIntent.NAVIGATE,
                actions=[],
                confidence_score=1.5,
                ambiguities=[],
                context_used=[]
            )
        assert "between 0.0 and 1.0" in str(exc_info.value)


class TestCommandParser:
    """Test CommandParser basic functionality."""

    @pytest.fixture
    def parser(self):
        """Create CommandParser instance."""
        return CommandParser()

    def test_parser_initialization(self, parser):
        """Test CommandParser can be instantiated."""
        assert parser is not None
        assert isinstance(parser, CommandParser)

    def test_parse_simple_navigate_command(self, parser):
        """Test parsing simple navigation command."""
        # For now, this is a basic structure test
        # Full LLM integration comes in US1-002
        result = parser.parse(
            user_input="Go to google.com",
            conversation_context=[],
            page_context=None
        )

        assert isinstance(result, ParsedCommand)
        assert result.original_input == "Go to google.com"
        assert result.intent == CommandIntent.NAVIGATE
        assert len(result.actions) >= 1
        assert isinstance(result.actions[0], NavigateAction)
        assert 0.0 <= result.confidence_score <= 1.0

    def test_parse_with_empty_input(self, parser):
        """Test parsing empty input raises error."""
        with pytest.raises(ParsingError) as exc_info:
            parser.parse(
                user_input="",
                conversation_context=[],
                page_context=None
            )

        assert "empty" in str(exc_info.value).lower()

    def test_parse_with_whitespace_only(self, parser):
        """Test parsing whitespace-only input raises error."""
        with pytest.raises(ParsingError) as exc_info:
            parser.parse(
                user_input="   \n  \t  ",
                conversation_context=[],
                page_context=None
            )

        assert "empty" in str(exc_info.value).lower()

    def test_parse_accepts_conversation_context(self, parser):
        """Test parser accepts conversation context parameter."""
        # Context will be used for clarifications in later user stories
        context = []  # Simplified for now

        result = parser.parse(
            user_input="Go to google.com",
            conversation_context=context,
            page_context=None
        )

        assert isinstance(result, ParsedCommand)

    def test_parse_accepts_page_context(self, parser):
        """Test parser accepts page context parameter."""
        # Page context will be used for element finding in later tasks
        page_context = {
            "current_url": "https://example.com",
            "page_title": "Example",
            "page_state": "ready"
        }

        result = parser.parse(
            user_input="Click the login button",
            conversation_context=[],
            page_context=page_context
        )

        assert isinstance(result, ParsedCommand)

    def test_parse_returns_valid_confidence_score(self, parser):
        """Test confidence score is always in valid range."""
        commands = [
            "Go to google.com",
            "Click the button",
            "Type hello in the search box",
        ]

        for command in commands:
            result = parser.parse(
                user_input=command,
                conversation_context=[],
                page_context=None
            )

            assert 0.0 <= result.confidence_score <= 1.0
