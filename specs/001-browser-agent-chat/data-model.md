# Data Model: Browser Automation Agent with Chat Interface

**Feature**: 001-browser-agent-chat
**Date**: 2025-10-18
**Source**: Derived from spec.md Key Entities and functional requirements

---

## Overview

This document defines the core data entities and their relationships for the browser automation agent system. All entities are derived from the feature specification's Key Entities section and functional requirements.

---

## Entity Definitions

### 1. ChatSession

**Purpose**: Represents a continuous conversation between user and agent

**Fields**:
- `session_id`: string (UUID) - Unique identifier
- `created_at`: datetime - Session creation timestamp
- `last_activity_at`: datetime - Last message timestamp
- `timeout_seconds`: integer - Page load timeout (default: 20, configurable via /timeout)
- `browser_instance_id`: string (optional) - Reference to active browser instance
- `status`: enum - [active, ended, error]

**Relationships**:
- Has many `ChatMessage` (one-to-many)
- Has one active `BrowserContext` (one-to-one, optional)

**Validation Rules**:
- `timeout_seconds` must be > 0 and <= 300 (5 minutes max)
- `session_id` must be unique
- `last_activity_at` >= `created_at`

**State Transitions**:
```
[created] → active → ended
         → active → error
```

**Notes**:
- Ephemeral: Not persisted across application restarts (per spec Assumptions)
- Supports up to 100-200 message pairs without degradation (SC-004)

---

### 2. ChatMessage

**Purpose**: A single message in the conversation (user command or agent response)

**Fields**:
- `message_id`: string (UUID) - Unique identifier
- `session_id`: string (foreign key) - Parent session
- `timestamp`: datetime - When message was created
- `sender`: enum - [user, agent]
- `message_type`: enum - [command, response, clarification_request, clarification_response, error, progress_update]
- `content`: string - Message text content
- `metadata`: JSON (optional) - Additional data (confidence score, command structure, etc.)
- `parent_message_id`: string (optional) - For clarification threads
- `status`: enum - [pending, processing, completed, failed, cancelled]

**Relationships**:
- Belongs to `ChatSession` (many-to-one)
- May reference `BrowserAction` (one-to-many)
- May have parent/child messages for clarifications (self-referential)

**Validation Rules**:
- `content` must not be empty for user messages
- `sender` = agent requires `message_type` in [response, clarification_request, error, progress_update]
- `sender` = user requires `message_type` in [command, clarification_response]
- `parent_message_id` only valid for `message_type` = clarification_response

**Examples**:
```json
// User command
{
  "message_id": "msg-001",
  "session_id": "session-abc",
  "timestamp": "2025-10-18T10:30:00Z",
  "sender": "user",
  "message_type": "command",
  "content": "Go to google.com and search for weather",
  "metadata": null,
  "status": "pending"
}

// Agent clarification request
{
  "message_id": "msg-002",
  "session_id": "session-abc",
  "timestamp": "2025-10-18T10:30:01Z",
  "sender": "agent",
  "message_type": "clarification_request",
  "content": "I found 2 search buttons. Which one? 1) Google Search 2) I'm Feeling Lucky",
  "metadata": {"confidence": 0.65, "reason": "multiple_elements"},
  "parent_message_id": "msg-001",
  "status": "completed"
}
```

---

### 3. BrowserAction

**Purpose**: An individual browser operation performed by the agent

**Fields**:
- `action_id`: string (UUID) - Unique identifier
- `message_id`: string (foreign key) - Command message that triggered this action
- `action_type`: enum - [navigate, click, type, scroll, extract, wait, back, forward, refresh]
- `target`: JSON - Element identifier or URL
  - For navigate: `{"url": "https://example.com"}`
  - For click: `{"selector": "button", "text": "Login", "strategy": "text"}`
  - For type: `{"selector": "input[type=email]", "value": "test@example.com"}`
  - For extract: `{"selector": "h1", "attribute": "textContent"}`
- `timestamp`: datetime - When action was attempted
- `duration_ms`: integer - How long action took
- `result_status`: enum - [success, failed, timeout, cancelled]
- `result_data`: JSON (optional) - Extracted data or error details
- `error_message`: string (optional) - Human-readable error description

**Relationships**:
- Belongs to `ChatMessage` (many-to-one)
- Part of `BrowserContext` (many-to-one)

**Validation Rules**:
- `action_type` = navigate requires `target.url`
- `action_type` = click requires `target.selector` or `target.text`
- `action_type` = type requires `target.selector` and `target.value`
- `action_type` = extract requires `target.selector`
- `result_status` = failed requires `error_message`

**Notes**:
- Supports multi-step commands (FR-011): Multiple actions for single message
- Enables progress tracking (FR-012): Can query in-progress actions

---

### 4. BrowserContext

**Purpose**: Represents the state of the browser instance being controlled

**Fields**:
- `context_id`: string (UUID) - Unique identifier
- `session_id`: string (foreign key) - Parent session
- `current_url`: string - Currently loaded page URL
- `page_title`: string - Title of current page
- `page_state`: enum - [loading, loaded, error, idle]
- `created_at`: datetime - When browser instance was launched
- `last_action_at`: datetime - Last browser action timestamp

**Relationships**:
- Belongs to `ChatSession` (one-to-one)
- Has many `BrowserAction` (one-to-many)
- Has many `PageElement` (one-to-many, cache of visible elements)

**Validation Rules**:
- `current_url` must be valid URL or empty string (for new context)
- Single active context per session (enforced at application level)

**Notes**:
- Persistent within session (per research.md: persistent browser per session)
- Cleaned up when session ends

---

### 5. PageElement

**Purpose**: Cached representation of a page element for fast lookups

**Fields**:
- `element_id`: string (UUID) - Unique identifier
- `context_id`: string (foreign key) - Parent browser context
- `selector`: string - CSS/XPath/text selector
- `element_type`: string - HTML tag name (button, input, link, etc.)
- `text_content`: string - Visible text
- `aria_label`: string (optional) - Accessibility label
- `position`: JSON - `{"x": 100, "y": 200}` (screen coordinates)
- `is_visible`: boolean - Element visibility state
- `cached_at`: datetime - When element was cached

**Relationships**:
- Belongs to `BrowserContext` (many-to-one)

**Validation Rules**:
- `selector` must not be empty
- `cached_at` must be recent (< 5 seconds for validity)

**Notes**:
- Short-lived cache (invalidated on page change or after timeout)
- Supports multi-strategy element identification (FR-010)
- Enables confidence evaluation (count matches for ambiguity detection)

---

### 6. ConfidenceEvaluation

**Purpose**: Records confidence assessment for command interpretation

**Fields**:
- `evaluation_id`: string (UUID) - Unique identifier
- `message_id`: string (foreign key) - Command being evaluated
- `confidence_score`: float - 0.0 to 1.0 (0.9 threshold per FR-014)
- `factors`: JSON - Breakdown of confidence factors
  ```json
  {
    "command_clarity": 0.95,
    "element_match_count": 1,
    "element_ambiguity": 0.85,
    "context_availability": 1.0
  }
  ```
- `evaluation_method`: enum - [llm, heuristic, hybrid]
- `clarification_needed`: boolean - Derived from `confidence_score < 0.9`
- `clarification_reason`: string (optional) - Why confidence is low
- `timestamp`: datetime

**Relationships**:
- Belongs to `ChatMessage` (one-to-one)

**Validation Rules**:
- `confidence_score` must be between 0.0 and 1.0
- `clarification_needed` = true requires `clarification_reason`
- `clarification_needed` = true if `confidence_score` < 0.9

**Notes**:
- Core to FR-014a-d (confidence-based clarification)
- May evolve over clarification cycle (re-evaluated after user response)

---

## Entity Relationships Diagram

```
ChatSession (1) ----< (many) ChatMessage
     |                       |
     | (1:1)                 | (1:many)
     |                       |
BrowserContext          BrowserAction
     |
     | (1:many)
     |
PageElement

ChatMessage (1) ----< (1:1) ConfidenceEvaluation
```

---

## Data Flow Examples

### Example 1: Simple Command Flow

1. User sends message: "Go to google.com"
   - Create `ChatMessage` (sender=user, type=command, status=pending)
   - Create `ConfidenceEvaluation` (score=0.98, clarification_needed=false)
   - confidence >= 0.9 → proceed

2. Agent executes:
   - Create `BrowserAction` (type=navigate, target={url: "https://google.com"})
   - Update `BrowserContext` (current_url, page_title, page_state=loading)
   - Update `BrowserAction` (result_status=success, duration_ms=1200)

3. Agent responds:
   - Create `ChatMessage` (sender=agent, type=response, content="Successfully navigated to google.com")
   - Update original command message (status=completed)

### Example 2: Clarification Flow (Confidence < 90%)

1. User sends: "Click the button"
   - Create `ChatMessage` (msg-001, sender=user, type=command)
   - Find elements: 5 buttons found
   - Create `ConfidenceEvaluation` (score=0.45, clarification_needed=true, reason="multiple_elements")

2. Agent requests clarification:
   - Create `ChatMessage` (msg-002, sender=agent, type=clarification_request, parent=msg-001)
   - Content: "I found 5 buttons. Which one? 1) Submit 2) Cancel..."

3. User clarifies: "The submit button"
   - Create `ChatMessage` (msg-003, sender=user, type=clarification_response, parent=msg-002)
   - Create new `ConfidenceEvaluation` for msg-001 (score=0.95, clarification_needed=false)
   - confidence >= 0.9 → proceed with click action

---

## Storage Strategy

**In-Memory (Python dict/dataclass)**:
- `ChatSession` - Active sessions only
- `PageElement` - Short-lived cache (5 second TTL)
- `ConfidenceEvaluation` - Tied to message lifecycle

**SQLite (Ephemeral)**:
- `ChatMessage` - Conversation history (max 100-200 pairs per session)
- `BrowserAction` - Action logs for debugging
- `BrowserContext` - Current browser state

**Notes**:
- Database file created per application start, deleted on shutdown
- No cross-session persistence (per spec Assumptions)
- SQLite enables easy querying for conversation context (FR-007, FR-017)

---

## Validation & Constraints Summary

| Requirement | Implementation |
|-------------|----------------|
| FR-007: Maintain conversation history | `ChatMessage` table with session_id foreign key |
| FR-014: Confidence evaluation (0-100% scale) | `ConfidenceEvaluation.confidence_score` (0.0-1.0) |
| FR-014a: Ask clarification if < 90% | `clarification_needed` derived from score < 0.9 |
| FR-017: Preserve history for session duration | SQLite keeps messages until session ends |
| SC-004: Support 100-200 message pairs | No hard limit, but query optimizations for large histories |
| SC-005: 90% element identification accuracy | `PageElement` caching + multi-strategy matching |

---

**Data Model Complete**: Ready for API contract generation.
