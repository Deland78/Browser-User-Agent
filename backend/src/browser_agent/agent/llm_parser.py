"""LLM integration for command parsing.

This module adds async LLM-based parsing capabilities to CommandParser.
Separated for clarity and to handle async operations.

Per tasks.md US1-002:
- Integrate LLM for command interpretation
- Map LLM tool calls to BrowserAction objects
- Handle LLM errors gracefully
"""

import json
from typing import Any, List, Optional, Dict

from browser_agent.agent.command_parser import (
    ParsedCommand,
    CommandIntent,
    NavigateAction,
    ClickAction,
    TypeAction,
    ExtractAction,
    ScrollAction,
    ConfigureAction,
    ParsingError,
)


async def parse_with_llm(
    llm_client: Any,
    user_input: str,
    conversation_context: List[Any],
    page_context: Optional[dict],
    tool_schemas: List[dict],
) -> ParsedCommand:
    """Parse command using LLM.

    Args:
        llm_client: LLM client instance (OpenRouterClient)
        user_input: User's command text
        conversation_context: Recent conversation messages
        page_context: Current page state
        tool_schemas: Tool definitions to send to LLM

    Returns:
        ParsedCommand with interpreted actions

    Raises:
        ParsingError: If LLM fails or returns invalid response
    """
    # Import error types from llm_client
    try:
        from browser_agent.agent.llm_client import LLMAPIError, LLMTimeoutError, LLMConnectionError
    except ImportError:
        # Define placeholder errors if import fails
        class LLMAPIError(Exception):
            pass

        class LLMTimeoutError(Exception):
            pass

        class LLMConnectionError(Exception):
            pass

    # Build messages for LLM
    messages = _build_messages(user_input, conversation_context, page_context)

    # Call LLM with tool schemas
    try:
        response = await llm_client.chat_completion(
            messages=messages,
            tools=tool_schemas if tool_schemas else None,
            model="anthropic/claude-3.5-sonnet",
        )
    except LLMTimeoutError as e:
        raise ParsingError(f"LLM request timed out: {str(e)}")
    except (LLMAPIError, LLMConnectionError) as e:
        raise ParsingError(f"LLM API error: {str(e)}")
    except Exception as e:
        raise ParsingError(f"Unexpected error during LLM parsing: {str(e)}")

    # Extract tool calls from response
    tool_calls = _extract_tool_calls(response)

    if not tool_calls:
        # No tool calls means LLM couldn't interpret the command
        raise ParsingError("LLM could not interpret the command")

    # Map tool calls to actions
    actions = []
    for tool_call in tool_calls:
        action = _map_tool_call_to_action(tool_call)
        if action:
            actions.append(action)

    # Determine intent from actions
    intent = _determine_intent(actions)

    # Calculate initial confidence (will be enhanced in US5-001)
    confidence_score = _calculate_confidence(actions, tool_calls)

    return ParsedCommand(
        original_input=user_input,
        intent=intent,
        actions=actions,
        confidence_score=confidence_score,
        ambiguities=[],
        context_used=[],
    )


def _build_messages(
    user_input: str,
    conversation_context: List[Any],
    page_context: Optional[dict],
) -> List[Dict[str, str]]:
    """Build message list for LLM request.

    Args:
        user_input: Current user command
        conversation_context: Previous messages
        page_context: Current page state

    Returns:
        List of messages in OpenRouter format
    """
    messages = []

    # System message with instructions
    system_content = """You are a browser automation assistant. Your job is to interpret user commands and convert them into structured browser actions using the provided tools.

Available actions:
- navigate: Go to a URL
- click: Click an element
- type_text: Type text into an input field
- extract_information: Get information from the page
- scroll: Scroll the page
- configure_timeout: Change timeout settings

When the user gives a command, analyze it and call the appropriate tool(s) with the correct parameters. For multi-step commands, call multiple tools in sequence."""

    if page_context:
        system_content += f"\n\nCurrent page context:\n- URL: {page_context.get('current_url', 'unknown')}\n- Title: {page_context.get('page_title', 'unknown')}\n- State: {page_context.get('page_state', 'unknown')}"

    messages.append({"role": "system", "content": system_content})

    # Add conversation context
    for ctx_msg in conversation_context:
        if isinstance(ctx_msg, dict):
            messages.append(ctx_msg)

    # Add current user message
    messages.append({"role": "user", "content": user_input})

    return messages


def _extract_tool_calls(response: dict) -> List[dict]:
    """Extract tool calls from LLM response.

    Args:
        response: LLM response dictionary

    Returns:
        List of tool call dictionaries
    """
    try:
        choices = response.get("choices", [])
        if not choices:
            return []

        message = choices[0].get("message", {})
        tool_calls = message.get("tool_calls", [])

        return tool_calls
    except (KeyError, IndexError, AttributeError):
        return []


def _map_tool_call_to_action(tool_call: dict) -> Optional[Any]:
    """Map LLM tool call to BrowserAction object.

    Args:
        tool_call: Tool call dictionary from LLM

    Returns:
        BrowserAction object or None if mapping fails
    """
    try:
        function = tool_call.get("function", {})
        function_name = function.get("name", "")
        arguments_str = function.get("arguments", "{}")

        # Parse arguments JSON
        try:
            arguments = json.loads(arguments_str)
        except json.JSONDecodeError:
            return None

        # Map to action based on function name
        if function_name == "navigate":
            return NavigateAction(
                url=arguments.get("url", ""),
                wait_for=arguments.get("wait_for", "load"),
            )

        elif function_name == "click":
            return ClickAction(
                element_description=arguments.get("element_description", ""),
                selector=arguments.get("selector"),
                text=arguments.get("text"),
                role=arguments.get("role"),
            )

        elif function_name == "type_text":
            return TypeAction(
                element_description=arguments.get("element_description", ""),
                text=arguments.get("text", ""),
                selector=arguments.get("selector"),
                clear_first=arguments.get("clear_first", True),
                press_enter=arguments.get("press_enter", False),
            )

        elif function_name == "extract_information":
            return ExtractAction(
                extraction_type=arguments.get("extraction_type", "text"),
                target_description=arguments.get("target_description", ""),
                selector=arguments.get("selector"),
                attribute_name=arguments.get("attribute_name"),
                limit=arguments.get("limit", 10),
            )

        elif function_name == "scroll":
            return ScrollAction(
                direction=arguments.get("direction", "down"),
                element_description=arguments.get("element_description"),
                pixels=arguments.get("pixels"),
            )

        elif function_name == "configure_timeout":
            return ConfigureAction(
                setting="timeout",
                value=arguments.get("timeout_seconds", 20),
            )

        else:
            # Unknown tool
            return None

    except (KeyError, TypeError, AttributeError):
        return None


def _determine_intent(actions: List[Any]) -> CommandIntent:
    """Determine command intent from action list.

    Args:
        actions: List of browser actions

    Returns:
        CommandIntent enum value
    """
    if not actions:
        return CommandIntent.INTERACT

    # Check first action to determine intent
    first_action = actions[0]

    if isinstance(first_action, NavigateAction):
        return CommandIntent.NAVIGATE
    elif isinstance(first_action, ExtractAction):
        return CommandIntent.EXTRACT
    elif isinstance(first_action, ConfigureAction):
        return CommandIntent.CONFIGURE
    else:
        return CommandIntent.INTERACT


def _calculate_confidence(actions: List[Any], tool_calls: List[dict]) -> float:
    """Calculate initial confidence score.

    This is a placeholder implementation. Full confidence evaluation
    will be implemented in US5-001.

    Args:
        actions: Parsed browser actions
        tool_calls: Raw tool calls from LLM

    Returns:
        Confidence score 0.0-1.0
    """
    # Simple heuristic for MVP:
    # - Has actions: 0.8 base confidence
    # - Each action with specific selectors: +0.05
    # - Capped at 0.95 (leave room for US5-001 improvements)

    if not actions:
        return 0.5

    base_confidence = 0.8

    # Boost confidence for specific selectors
    specificity_boost = 0.0
    for action in actions:
        if isinstance(action, (ClickAction, TypeAction)):
            if hasattr(action, "selector") and action.selector:
                specificity_boost += 0.05
            if hasattr(action, "text") and action.text:
                specificity_boost += 0.03

    total_confidence = min(base_confidence + specificity_boost, 0.95)

    return total_confidence
