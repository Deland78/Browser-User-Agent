# Agent Interface Contract

**Feature**: 001-browser-agent-chat
**Version**: 1.0.0
**Date**: 2025-10-18

---

## Overview

This document defines the contract between the **Agent Reasoning Module** and other system components (Browser Automation, LLM Client, Chat Service). The agent is responsible for:

1. **Command Interpretation**: Parse natural language → structured browser actions
2. **Confidence Evaluation**: Assess certainty (90% threshold per FR-014)
3. **Clarification Generation**: Create targeted questions when confidence < 90%
4. **Execution Orchestration**: Coordinate multi-step workflows

---

## Agent Module Interface

### Core Classes

#### 1. `CommandParser`

**Purpose**: Convert natural language commands to structured browser actions

**Interface**:
```python
class CommandParser:
    def parse(
        self,
        user_input: str,
        conversation_context: List[ChatMessage],
        page_context: Optional[PageState]
    ) -> ParsedCommand:
        """
        Parse natural language command into structured format.

        Args:
            user_input: Raw user command text
            conversation_context: Recent messages for context (FR-007)
            page_context: Current page state (FR-015)

        Returns:
            ParsedCommand with interpreted actions and confidence score

        Raises:
            ParsingError: If command is completely unintelligible
        """
        pass
```

**Output**:
```python
@dataclass
class ParsedCommand:
    original_input: str
    intent: CommandIntent  # navigate, interact, extract, configure
    actions: List[BrowserAction]  # Structured action sequence
    confidence_score: float  # 0.0 - 1.0 (FR-014)
    ambiguities: List[Ambiguity]  # Detected unclear aspects
    context_used: List[str]  # Referenced message IDs from context
```

---

#### 2. `ConfidenceEvaluator`

**Purpose**: Evaluate confidence in command interpretation and execution

**Interface**:
```python
class ConfidenceEvaluator:
    THRESHOLD = 0.90  # FR-014a threshold

    def evaluate(
        self,
        parsed_command: ParsedCommand,
        element_matches: Dict[str, int]  # action_id -> match_count
    ) -> ConfidenceEvaluation:
        """
        Evaluate confidence for command execution.

        Args:
            parsed_command: Parsed command structure
            element_matches: Number of matching elements per action

        Returns:
            ConfidenceEvaluation with score, factors, and clarification needs
        """
        pass

    def should_clarify(self, evaluation: ConfidenceEvaluation) -> bool:
        """Returns True if confidence < 0.9 (FR-014a)"""
        return evaluation.confidence_score < self.THRESHOLD
```

**Output**:
```python
@dataclass
class ConfidenceEvaluation:
    confidence_score: float  # 0.0 - 1.0
    factors: Dict[str, float]  # breakdown of contributing factors
    clarification_needed: bool  # True if score < 0.9
    clarification_reason: Optional[str]  # Why low confidence
    ambiguous_actions: List[str]  # action_ids needing clarification
```

**Confidence Factors** (FR-014b):
- **Command Clarity** (0.0-1.0): How clear/unambiguous the user's intent is
- **Element Ambiguity** (0.0-1.0): Based on match count (1 match = 1.0, 2-5 = 0.7, >5 = 0.4)
- **Context Availability** (0.0-1.0): Whether sufficient context exists (history, page state)
- **Action Complexity** (0.0-1.0): Single action = 1.0, multi-step reduces confidence

**Scoring Formula**:
```python
confidence_score = (
    command_clarity * 0.40 +
    element_ambiguity * 0.35 +
    context_availability * 0.15 +
    action_complexity * 0.10
)
```

---

#### 3. `ClarificationGenerator`

**Purpose**: Generate targeted clarification questions when confidence < 90%

**Interface**:
```python
class ClarificationGenerator:
    def generate_question(
        self,
        evaluation: ConfidenceEvaluation,
        parsed_command: ParsedCommand,
        elements: List[PageElement]
    ) -> ClarificationQuestion:
        """
        Generate clarification question for user (FR-014b).

        Args:
            evaluation: Confidence evaluation with reasons
            parsed_command: Original parsed command
            elements: Matching page elements (if ambiguity is element-based)

        Returns:
            ClarificationQuestion with options for user
        """
        pass

    def process_clarification(
        self,
        original_command: ParsedCommand,
        user_response: str
    ) -> ParsedCommand:
        """
        Re-parse command with clarification (FR-014c).

        Args:
            original_command: Original parsed command
            user_response: User's clarifying response

        Returns:
            Updated ParsedCommand with increased confidence
        """
        pass
```

**Output**:
```python
@dataclass
class ClarificationQuestion:
    question_text: str  # Human-readable question
    question_type: QuestionType  # multiple_choice, text_input, yes_no
    options: List[ClarificationOption]  # Available choices
    reason: str  # Why clarification is needed
    original_message_id: str  # Reference to original command

@dataclass
class ClarificationOption:
    option_id: str
    label: str  # e.g., "1) Submit button"
    element_selector: Optional[str]  # If option maps to page element
```

**Question Templates**:
- **Multiple Elements**: "I found {count} {element_type}s. Which one? {options}"
- **Ambiguous Action**: "Do you want me to {action1} or {action2}?"
- **Missing Context**: "Which {entity} from earlier? {options from history}"
- **Unclear Intent**: "Did you mean: {interpretation1} or {interpretation2}?"

---

#### 4. `CommandExecutor`

**Purpose**: Orchestrate browser action execution and result reporting

**Interface**:
```python
class CommandExecutor:
    def execute(
        self,
        parsed_command: ParsedCommand,
        browser_context: BrowserContext,
        progress_callback: Optional[Callable[[ProgressUpdate], None]] = None
    ) -> ExecutionResult:
        """
        Execute parsed command via browser automation (FR-011, FR-012).

        Args:
            parsed_command: Validated command (confidence >= 0.9)
            browser_context: Active browser context
            progress_callback: For multi-step progress updates (FR-012)

        Returns:
            ExecutionResult with success status and data

        Raises:
            ExecutionError: If browser action fails
            TimeoutError: If action exceeds timeout (FR-020)
            CancelledError: If user cancels execution (FR-013)
        """
        pass
```

**Output**:
```python
@dataclass
class ExecutionResult:
    success: bool
    message: str  # Human-readable result (FR-008, FR-009)
    actions_executed: List[BrowserAction]  # Actions performed
    extracted_data: Optional[Any]  # For extraction commands
    duration_ms: int
    errors: List[ExecutionError]  # For partial failures
```

---

## Integration Contracts

### 1. Agent ↔ LLM Client (OpenRouter)

**LLM Client Interface**:
```python
class LLMClient(Protocol):
    """
    OpenRouter API client for LLM command interpretation.
    Uses OpenAI-compatible API format via https://openrouter.ai/api/v1
    """

    def parse_command(
        self,
        user_input: str,
        conversation_history: List[dict],
        page_context: Optional[dict],
        available_tools: List[ToolDefinition]
    ) -> LLMResponse:
        """
        Use LLM to interpret user command via OpenRouter.

        API Call Format:
        POST https://openrouter.ai/api/v1/chat/completions
        Headers:
          - Authorization: Bearer {OPENROUTER_API_KEY}
          - HTTP-Referer: {SITE_URL} (optional, for credits)
          - X-Title: {APP_NAME} (optional, for rankings)

        Body (OpenAI-compatible):
        {
          "model": "anthropic/claude-3.5-sonnet",
          "messages": [...conversation_history, {user_input}],
          "tools": available_tools,
          "tool_choice": "auto"
        }

        Returns structured output with tool calls (browser actions).
        """
        pass

    def evaluate_confidence(
        self,
        command: str,
        parsed_result: dict
    ) -> float:
        """
        Ask LLM to self-assess confidence (0.0-1.0) via OpenRouter.
        Used when heuristic confidence is borderline.

        Can use different models for speed (e.g., "openai/gpt-3.5-turbo")
        while keeping Claude for main command parsing.
        """
        pass

    def generate_clarification(
        self,
        ambiguity: Ambiguity,
        context: dict
    ) -> str:
        """
        Generate natural clarification question via OpenRouter LLM.
        """
        pass
```

**Tool Definitions** (for LLM function calling):
```json
[
  {
    "name": "navigate",
    "description": "Navigate browser to a URL",
    "parameters": {
      "type": "object",
      "properties": {
        "url": {"type": "string", "description": "Target URL"},
        "wait_for": {"type": "string", "enum": ["load", "domcontentloaded"]}
      },
      "required": ["url"]
    }
  },
  {
    "name": "click_element",
    "description": "Click an element on the page",
    "parameters": {
      "type": "object",
      "properties": {
        "text": {"type": "string", "description": "Element text"},
        "selector": {"type": "string", "description": "CSS selector"},
        "role": {"type": "string", "description": "ARIA role"}
      }
    }
  },
  {
    "name": "extract_information",
    "description": "Extract information from the page",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {"type": "string", "description": "What to extract"},
        "format": {"type": "string", "enum": ["text", "list", "count"]}
      },
      "required": ["query"]
    }
  }
]
```

---

### 2. Agent ↔ Browser Automation

**Browser Service Interface**:
```python
class BrowserService(Protocol):
    def find_elements(
        self,
        context_id: str,
        target: ElementTarget
    ) -> List[PageElement]:
        """
        Find elements matching target using multi-strategy search (FR-010).

        Returns list of matching elements (empty if none found).
        """
        pass

    def execute_action(
        self,
        context_id: str,
        action: BrowserAction
    ) -> ActionResult:
        """
        Execute single browser action.

        Raises:
            ElementNotFoundError: Element doesn't exist
            TimeoutError: Action exceeded timeout
            BrowserError: Browser crashed or closed
        """
        pass

    def get_page_state(
        self,
        context_id: str
    ) -> PageState:
        """
        Get current page state for context (FR-015).
        """
        pass
```

---

### 3. Agent ↔ Chat Service

**Chat Service Interface**:
```python
class ChatService(Protocol):
    def send_message(
        self,
        session_id: str,
        content: str,
        message_type: MessageType,
        metadata: Optional[dict] = None
    ) -> ChatMessage:
        """
        Send agent message to user.

        Used for responses, clarifications, progress updates, errors.
        """
        pass

    def get_conversation_context(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[ChatMessage]:
        """
        Retrieve recent conversation history for context (FR-007).
        """
        pass
```

---

## Workflow Examples

### Example 1: High Confidence Flow

```
1. User: "Go to google.com"
2. CommandParser.parse() →
   ParsedCommand(
       intent=NAVIGATE,
       actions=[NavigateAction(url="https://google.com")],
       confidence_score=0.98
   )
3. ConfidenceEvaluator.evaluate() → 0.98 (>= 0.9) ✅
4. CommandExecutor.execute() → Navigate action
5. Agent responds: "Successfully navigated to google.com"
```

### Example 2: Low Confidence Flow (Multiple Elements)

```
1. User: "Click the button"
2. CommandParser.parse() →
   ParsedCommand(
       intent=INTERACT,
       actions=[ClickAction(target=ElementTarget(role="button"))],
       confidence_score=0.85  # Multiple buttons found
   )
3. BrowserService.find_elements() → 5 buttons found
4. ConfidenceEvaluator.evaluate() → 0.45 (< 0.9) ❌
5. ClarificationGenerator.generate_question() →
   "I found 5 buttons. Which one?
    1) Submit
    2) Cancel
    3) Login
    4) Register
    5) Search"
6. Wait for user clarification response
7. ClarificationGenerator.process_clarification("The submit button") →
   Updated ParsedCommand with confidence=0.95
8. CommandExecutor.execute() → Click Submit button
9. Agent responds: "Clicked 'Submit' button successfully"
```

### Example 3: Multi-Step with Progress Updates

```
1. User: "Go to amazon.com, search for laptop, and show first 3 results"
2. CommandParser.parse() →
   ParsedCommand(
       intent=MULTI_STEP,
       actions=[
           NavigateAction(url="https://amazon.com"),
           TypeAction(target="search input", text="laptop"),
           ClickAction(target="search button"),
           ExtractAction(query="first 3 search results")
       ],
       confidence_score=0.92
   )
3. CommandExecutor.execute(progress_callback=send_progress):
   - Step 1/4: Navigate → progress_callback("Navigating to amazon.com...")
   - Step 2/4: Type → progress_callback("Typing 'laptop' in search...")
   - Step 3/4: Click → progress_callback("Clicking search button...")
   - Step 4/4: Extract → progress_callback("Extracting results...")
4. Agent responds with formatted results:
   "Found 3 laptop results:
    1) Dell Inspiron 15 - $599
    2) HP Pavilion - $699
    3) Lenovo ThinkPad - $849"
```

---

## Error Handling Contract

**Agent Error Types**:
```python
class AgentError(Exception):
    """Base exception for agent errors"""
    pass

class ParsingError(AgentError):
    """Command could not be parsed"""
    pass

class ConfidenceThresholdError(AgentError):
    """Confidence below threshold after multiple clarifications"""
    pass

class ExecutionError(AgentError):
    """Browser action execution failed"""
    def __init__(
        self,
        message: str,
        retry_suggestion: Optional[str] = None,  # FR-009a
        failed_action: Optional[BrowserAction] = None
    ):
        self.retry_suggestion = retry_suggestion
        self.failed_action = failed_action
        super().__init__(message)
```

**Error Response Format**:
All agent errors must produce user-friendly messages (FR-009):
- **What went wrong**: Clear description of the failure
- **Why it happened**: Context about the error
- **What to do next**: Actionable suggestion (FR-009a)

Example:
```
Error: Could not find 'Login' button on the page.

This might be because:
- The page hasn't fully loaded yet
- The button has different text
- The element is hidden or in a different section

You can try:
- Waiting a few seconds and asking again
- Being more specific (e.g., "Click the blue login button in the header")
- Asking me to list all buttons on the page first
```

---

## Testing Contracts

**Test Coverage Requirements** (per constitution):
- ✅ Unit tests: Each class method with mocked dependencies
- ✅ Integration tests: Agent → Browser, Agent → LLM interactions
- ✅ E2E tests: Full workflows per user stories (spec.md)
- ✅ Confidence threshold tests: Verify 0.9 boundary behavior
- ✅ Clarification cycle tests: Multi-round clarification scenarios

**Key Test Scenarios**:
1. Confidence exactly at threshold (0.9000) → should not clarify
2. Confidence just below threshold (0.8999) → should clarify
3. Repeated clarifications that never reach 90% → graceful failure
4. Cancellation during multi-step execution → cleanup properly
5. Browser crashes during execution → handle gracefully

---

**Contract Version**: 1.0.0
**Last Updated**: 2025-10-18
**Changes**: Initial version
