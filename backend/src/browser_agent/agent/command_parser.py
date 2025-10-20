"""Command Parser foundation for browser automation agent.

Implements:
- CommandParser class for parsing natural language commands
- ParsedCommand dataclass with intent, actions, confidence
- BrowserAction structures for different action types
- CommandIntent enum
- LLM integration for command interpretation (US1-002)

Per tasks.md US1-001, US1-002:
- Foundation for command parsing
- LLM-based interpretation via OpenRouter
- Tool schema loading from llm-tools-schema.json
- Structured action representation per agent-interface.md
- Confidence scoring placeholder (full implementation in US5-001)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional, Union, Protocol
from pathlib import Path
import json
import re


class CommandIntent(str, Enum):
    """High-level intent classification for commands."""

    NAVIGATE = "navigate"
    INTERACT = "interact"
    EXTRACT = "extract"
    CONFIGURE = "configure"


class ParsingError(Exception):
    """Raised when command cannot be parsed."""

    pass


# ============================================================================
# Browser Action Dataclasses
# Per llm-tools-schema.json tool definitions
# ============================================================================


@dataclass
class NavigateAction:
    """Navigate browser to a URL.

    Per llm-tools-schema.json 'navigate' tool.
    """

    url: str
    wait_for: str = "load"  # load, domcontentloaded, networkidle


@dataclass
class ClickAction:
    """Click an element on the page.

    Per llm-tools-schema.json 'click' tool.
    """

    element_description: str
    selector: Optional[str] = None
    text: Optional[str] = None
    role: Optional[str] = None  # button, link, checkbox, radio, tab, menuitem


@dataclass
class TypeAction:
    """Type text into an input field.

    Per llm-tools-schema.json 'type_text' tool.
    """

    element_description: str
    text: str
    selector: Optional[str] = None
    clear_first: bool = True
    press_enter: bool = False


@dataclass
class ExtractAction:
    """Extract information from the page.

    Per llm-tools-schema.json 'extract_information' tool.
    """

    extraction_type: str  # text, attribute, count, list
    target_description: str
    selector: Optional[str] = None
    attribute_name: Optional[str] = None
    limit: int = 10


@dataclass
class ScrollAction:
    """Scroll the page or element.

    Per llm-tools-schema.json 'scroll' tool.
    """

    direction: str  # down, up, to_element
    element_description: Optional[str] = None
    pixels: Optional[int] = None


@dataclass
class ConfigureAction:
    """Configure agent settings.

    Per llm-tools-schema.json 'configure_timeout' tool.
    """

    setting: str  # timeout, etc.
    value: Any


# Union type for all browser actions
BrowserAction = Union[
    NavigateAction,
    ClickAction,
    TypeAction,
    ExtractAction,
    ScrollAction,
    ConfigureAction,
]


# ============================================================================
# Parsed Command Structure
# Per agent-interface.md
# ============================================================================


@dataclass
class ParsedCommand:
    """Result of command parsing.

    Per agent-interface.md ParsedCommand specification.

    Attributes:
        original_input: User's raw command text
        intent: High-level command intent
        actions: Structured browser actions to execute
        confidence_score: Confidence in interpretation (0.0-1.0)
        ambiguities: List of detected ambiguous aspects
        context_used: Message IDs from conversation context that were referenced
    """

    original_input: str
    intent: CommandIntent
    actions: List[BrowserAction]
    confidence_score: float
    ambiguities: List[str] = field(default_factory=list)
    context_used: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate confidence score range."""
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")


# ============================================================================
# Command Parser
# ============================================================================


class CommandParser:
    """Parse natural language commands into structured browser actions.

    Per agent-interface.md CommandParser specification.

    Integration Points:
    - US1-001: Foundation with simple pattern matching
    - US1-002: LLM-based interpretation via OpenRouter (current)
    - US5-001: Comprehensive confidence evaluation
    - US5-002: Clarification generation
    """

    def __init__(self, llm_client: Optional[Any] = None):
        """Initialize command parser.

        Args:
            llm_client: Optional LLM client for advanced parsing.
                       If None, falls back to simple pattern matching.
        """
        self.llm_client = llm_client

        # Load tool schemas from llm-tools-schema.json
        self.tool_schemas = self._load_tool_schemas()

        # Simple patterns for fallback (when LLM not available)
        self._navigate_patterns = [
            r"go to (.+)",
            r"navigate to (.+)",
            r"open (.+)",
            r"visit (.+)",
        ]

        self._click_patterns = [
            r"click (?:the )?(.+)",
            r"press (?:the )?(.+)",
            r"tap (?:the )?(.+)",
        ]

        self._type_patterns = [
            r"type (.+) in (?:the )?(.+)",
            r"enter (.+) in (?:the )?(.+)",
            r"fill (.+) with (.+)",
        ]

    def _load_tool_schemas(self) -> List[dict]:
        """Load tool definitions from llm-tools-schema.json.

        Returns:
            List of tool definitions in OpenRouter/OpenAI format

        Per tasks.md US1-002: Load tool definitions from contracts/llm-tools-schema.json
        """
        # Try multiple possible paths (for different execution contexts)
        possible_paths = [
            Path("specs/001-browser-agent-chat/contracts/llm-tools-schema.json"),
            Path("../specs/001-browser-agent-chat/contracts/llm-tools-schema.json"),
            Path(__file__).parent.parent.parent.parent.parent / "specs" / "001-browser-agent-chat" / "contracts" / "llm-tools-schema.json",
        ]

        for schema_path in possible_paths:
            try:
                if schema_path.exists():
                    with open(schema_path) as f:
                        schema = json.load(f)
                        return schema.get("tools", [])
            except (FileNotFoundError, json.JSONDecodeError):
                continue

        # Fallback: return empty list if schema file not found
        # Parser will still work with pattern matching
        return []

    def parse(
        self,
        user_input: str,
        conversation_context: List[Any],
        page_context: Optional[dict],
    ) -> ParsedCommand:
        """Parse natural language command into structured format.

        Args:
            user_input: Raw user command text
            conversation_context: Recent messages for context (FR-007)
            page_context: Current page state (FR-015)

        Returns:
            ParsedCommand with interpreted actions and confidence score

        Raises:
            ParsingError: If command is completely unintelligible

        Example:
            >>> parser = CommandParser()
            >>> result = parser.parse("Go to google.com", [], None)
            >>> assert result.intent == CommandIntent.NAVIGATE
        """
        # Validate input
        if not user_input or not user_input.strip():
            raise ParsingError("Command input cannot be empty")

        user_input = user_input.strip()

        # Try to match simple patterns (MVP implementation)
        # Full LLM-based parsing in US1-002
        parsed = self._try_simple_parse(user_input)

        if parsed is None:
            # Fallback: treat as generic interaction
            # In US1-002, this will go through LLM interpretation
            parsed = ParsedCommand(
                original_input=user_input,
                intent=CommandIntent.INTERACT,
                actions=[],
                confidence_score=0.5,  # Low confidence for unparsed
                ambiguities=["Command pattern not recognized"],
                context_used=[],
            )

        return parsed

    async def parse_async(
        self,
        user_input: str,
        conversation_context: List[Any],
        page_context: Optional[dict],
    ) -> ParsedCommand:
        """Parse natural language command asynchronously using LLM.

        This method uses the LLM client for advanced interpretation.
        Falls back to simple pattern matching if LLM is not available.

        Args:
            user_input: Raw user command text
            conversation_context: Recent messages for context (FR-007)
            page_context: Current page state (FR-015)

        Returns:
            ParsedCommand with interpreted actions and confidence score

        Raises:
            ParsingError: If command is completely unintelligible

        Example:
            >>> parser = CommandParser(llm_client=client)
            >>> result = await parser.parse_async("Go to google.com", [], None)
            >>> assert result.intent == CommandIntent.NAVIGATE
        """
        # Validate input
        if not user_input or not user_input.strip():
            raise ParsingError("Command input cannot be empty")

        user_input = user_input.strip()

        # If LLM client available, use it
        if self.llm_client:
            from browser_agent.agent.llm_parser import parse_with_llm

            return await parse_with_llm(
                llm_client=self.llm_client,
                user_input=user_input,
                conversation_context=conversation_context,
                page_context=page_context,
                tool_schemas=self.tool_schemas,
            )

        # Fallback to synchronous simple parsing if no LLM
        return self.parse(user_input, conversation_context, page_context)

    def _try_simple_parse(self, user_input: str) -> Optional[ParsedCommand]:
        """Try to parse using simple patterns (MVP implementation).

        This is a placeholder for US1-001. Will be replaced with LLM-based
        parsing in US1-002.

        Args:
            user_input: User's command text

        Returns:
            ParsedCommand if pattern matched, None otherwise
        """
        user_input_lower = user_input.lower()

        # Try navigate patterns
        for pattern in self._navigate_patterns:
            match = re.match(pattern, user_input_lower)
            if match:
                url = match.group(1).strip()

                # Add protocol if missing
                if not url.startswith(("http://", "https://")):
                    url = f"https://{url}"

                return ParsedCommand(
                    original_input=user_input,
                    intent=CommandIntent.NAVIGATE,
                    actions=[NavigateAction(url=url, wait_for="load")],
                    confidence_score=0.95,  # High confidence for clear navigation
                    ambiguities=[],
                    context_used=[],
                )

        # Try click patterns
        for pattern in self._click_patterns:
            match = re.match(pattern, user_input_lower)
            if match:
                element_desc = match.group(1).strip()

                return ParsedCommand(
                    original_input=user_input,
                    intent=CommandIntent.INTERACT,
                    actions=[ClickAction(element_description=element_desc)],
                    confidence_score=0.75,  # Medium confidence (element ambiguity possible)
                    ambiguities=["Element identification may require clarification"],
                    context_used=[],
                )

        # Try type patterns
        for pattern in self._type_patterns:
            match = re.match(pattern, user_input_lower)
            if match:
                text = match.group(1).strip()
                element_desc = match.group(2).strip()

                return ParsedCommand(
                    original_input=user_input,
                    intent=CommandIntent.INTERACT,
                    actions=[
                        TypeAction(
                            element_description=element_desc,
                            text=text,
                            clear_first=True,
                            press_enter=False,
                        )
                    ],
                    confidence_score=0.80,
                    ambiguities=[],
                    context_used=[],
                )

        # No pattern matched
        return None
