# Implementation Tasks: Browser Automation Agent with Chat Interface

**Feature**: 001-browser-agent-chat
**Generated**: 2025-10-18
**Source**: [spec.md](spec.md) | [plan.md](plan.md) | [data-model.md](data-model.md)

---

## Quick Reference

**Total Tasks**: 78
**Estimated Effort**: 8-10 weeks (1-2 developers)
**MVP Scope**: Phases 1-4 (User Stories 1-2)

**Task Format**: `[ID] Task Name (Effort: XS/S/M/L/XL) - Brief description`
- XS = 1-2 hours
- S = 2-4 hours
- M = 4-8 hours (half day to full day)
- L = 1-2 days
- XL = 2-3 days

---

## Phase 0: Project Setup and Infrastructure

**Purpose**: Initialize project structure, configure development environment, set up foundational tooling
**Dependency**: None (start here)
**Deliverable**: Working development environment with all dependencies installed

### Tasks

- [X] **[SETUP-001]** Initialize backend project structure (Effort: M)
  - Create `backend/` directory structure per plan.md
  - Set up Python virtual environment (Python 3.11+)
  - Initialize pyproject.toml or requirements.txt with core dependencies
  - Configure src/ directory with __init__.py files
  - **Test**: `python -m pytest --version` succeeds
  - **Files**: `backend/pyproject.toml`, `backend/src/**/__init__.py`

- [X] **[SETUP-002]** Initialize frontend project structure (Effort: M)
  - Create `frontend/` directory with Vite + React + TypeScript
  - Run `npm create vite@latest frontend -- --template react-ts`
  - Configure TypeScript with strict mode enabled
  - Set up project structure per plan.md (components/, services/, types/)
  - **Test**: `npm run dev` starts development server
  - **Files**: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`

- [X] **[SETUP-003]** Install and configure backend dependencies (Effort: S)
  - Install FastAPI 0.104+, uvicorn, pydantic
  - Install Playwright 1.40+ for Python (`pip install playwright`)
  - Install pytest, pytest-cov, pytest-asyncio for testing
  - Install OpenRouter.ai client dependencies (httpx or openai-compatible library)
  - Run `playwright install chromium` to download browser binaries
  - **Test**: `playwright --version` and `uvicorn --version` succeed
  - **Files**: `backend/requirements.txt` or `backend/pyproject.toml`

- [X] **[SETUP-004]** Install and configure frontend dependencies (Effort: S)
  - Install React 18+, TypeScript, Vite 5.0+
  - Install testing libraries: Vitest, React Testing Library
  - Install UI component library (@radix-ui/react per research.md)
  - Install accessibility testing: axe-core
  - **Test**: `npm test` runs (even with zero tests)
  - **Files**: `frontend/package.json`

- [X] **[SETUP-005]** Configure environment variables and secrets (Effort: S)
  - Copy `.env.example` files to `.env` in backend and frontend directories
  - Document required environment variables in README
  - Set up OPENROUTER_API_KEY in backend/.env (user provides key)
  - Configure VITE_API_URL and VITE_WS_URL in frontend/.env
  - **Test**: Backend can read `os.getenv("OPENROUTER_API_KEY")`
  - **Files**: `backend/.env`, `frontend/.env`, `README.md`

- [X] **[SETUP-006]** Set up linting and code quality tools (Effort: M)
  - Backend: Install and configure ruff (linter), black (formatter), mypy (type checker)
  - Frontend: Configure ESLint, Prettier for TypeScript
  - Create pre-commit hooks configuration
  - Add scripts to package.json and pyproject.toml for lint/format commands
  - **Test**: `npm run lint` and `ruff check .` execute without errors (on empty codebase)
  - **Files**: `backend/.ruff.toml`, `frontend/.eslintrc.json`, `.pre-commit-config.yaml`

- [X] **[SETUP-007]** Configure logging infrastructure (Effort: S)
  - Set up Python structured logging with JSON formatter
  - Create logger configuration in `backend/src/config/logging.py`
  - Configure log levels (DEBUG for dev, INFO for prod)
  - Set up log file rotation in `backend/logs/`
  - **Test**: Logger emits structured JSON logs to file
  - **Files**: `backend/src/config/logging.py`

- [X] **[SETUP-008]** Create database setup script (Effort: M)
  - Create SQLite initialization script in `backend/src/db/init.py`
  - Define database schema from data-model.md (ChatMessage, BrowserAction, etc.)
  - Use SQLAlchemy or raw SQL for schema creation
  - Implement database connection singleton
  - **Test**: Script creates `browser_agent.db` with expected tables
  - **Files**: `backend/src/db/init.py`, `backend/src/db/models.py`

- [X] **[SETUP-009]** Write project README with quickstart instructions (Effort: S)
  - Document prerequisites (Python 3.11+, Node.js 18+, OpenRouter API key)
  - Add setup instructions (virtualenv, npm install, playwright install)
  - Include example commands for running backend and frontend
  - Link to quickstart.md for detailed setup
  - **Test**: New developer can follow README and start both servers
  - **Files**: `README.md`

---

## Phase 1: Core Infrastructure (Foundational Layer)

**Purpose**: Build shared infrastructure used by all features
**Dependency**: Phase 0 complete
**Deliverable**: Configuration system, API foundation, browser driver abstraction

### Tasks

- [X] **[INFRA-001]** Implement settings configuration module (Effort: M)
  - Create `backend/src/config/settings.py` with Pydantic BaseSettings ✓
  - Load environment variables (OPENROUTER_API_KEY, timeouts, etc.) ✓
  - Implement validation for required settings ✓
  - Define defaults: timeout_seconds=20, confidence_threshold=0.90 ✓
  - **Timeout Architecture**: Default timeout (20s) defined in settings, copied to session on creation, propagated to browser driver ✓
  - **Test**: Unit test for settings loading with mock env vars ✓
  - **Files**: `backend/src/config/settings.py`, `tests/unit/test_settings.py`
  - **Spec**: FR-020 (20s default timeout), FR-014 (90% confidence), FR-021/022 (timeout configuration)
  - **Notes**:
    - Updated settings.py to use Pydantic v2 (pydantic-settings package)
    - Changed `BaseSettings` import from `pydantic` to `pydantic_settings`
    - Updated validators from `@validator` to `@field_validator` with `@classmethod`
    - Changed `class Config` to `model_config = SettingsConfigDict(...)`
    - Added comprehensive settings: OpenRouter config, browser settings, API config, CORS origins
    - Implemented field validators for API key format and confidence threshold (must be 0.90)
    - **Issue**: CORS_origins parsing from .env file - pydantic-settings attempts JSON decode on list fields from env vars
    - **CC Attempted fixes**: (1) Used `@field_validator` with `mode="before"` to parse comma-separated string, (2) Added `SettingsConfigDict` with `env_ignore_empty=True`
    - **Codex fixes**: (1) Removed the tracked backend .env.bak, (2) Enhanced cors_origins validator to handle JSON array strings and comma-separated/plain string inputs, (3) Extended unit tests to cover JSON-style and comma-separated CORS_ORIGINS inputs, (4) Documented the accepted CORS_ORIGINS formats in README
    - **Resolution**: All CORS tests passing. Supports JSON arrays, CSV, and plain strings. Added *.env.bak to .gitignore.

- [X] **[INFRA-002]** Set up FastAPI application and basic routes (Effort: M)
  - Create `backend/src/main.py` with FastAPI app initialization ✓
  - Add health check endpoint: `GET /api/v1/health` ✓
  - Configure CORS for frontend origin ✓
  - Set up error handlers for common exceptions ✓
  - **Test**: `curl http://localhost:8000/api/v1/health` returns 200 OK ✓
  - **Files**: `backend/src/browser_agent/app.py`, `backend/src/browser_agent/main.py`, `backend/src/browser_agent/api/routes/__init__.py`, `backend/src/browser_agent/api/routes/health.py`
  - **Notes**:
    - Created FastAPI application factory in app.py with CORS middleware configured from settings
    - Implemented health check endpoint at /api/v1/health returning status, environment, and version
    - Added global exception handlers for RequestValidationError (422) and generic Exception (500)
    - CORS properly configured for origins from settings.cors_origins (supports http://localhost:5173)
    - Fixed pyproject.toml: removed invalid ../README.md reference, added pydantic-settings dependency
    - Successfully tested: health endpoint returns 200 OK, CORS preflight requests work correctly

- [X] **[INFRA-003]** Implement browser driver abstraction (Effort: L)
  - Create `backend/src/browser/driver.py` with BrowserService protocol ✓
  - Implement Playwright adapter class with context management ✓
  - Support headless/headful mode from config ✓
  - Implement browser launch, context creation, page management ✓
  - Add cleanup on context close ✓
  - **Test**: Unit test with mocked Playwright, integration test launching real browser ✓
  - **Files**: `backend/src/browser_agent/browser/driver.py`, `tests/unit/test_driver.py`, `tests/integration/test_browser_driver.py`
  - **Notes**:
    - Implemented BrowserService protocol with type hints for clean interface
    - Created PlaywrightBrowserService with full lifecycle management (initialize, shutdown)
    - Supports per-session browser contexts with configurable viewport
    - Headless mode controlled by settings.browser_headless
    - Comprehensive error handling with custom exceptions (BrowserError, ContextNotFoundError)
    - Session-to-context mapping for easy lookup
    - Unit tests: 15/15 passing with mocked Playwright using pytest-asyncio
    - Integration tests created for real browser testing (marked with @pytest.mark.integration)
    - Proper cleanup on context close and service shutdown

- [X] **[INFRA-004]** Implement OpenRouter LLM client (Effort: L) **✅ COMPLETED**
  - **Status**: COMPLETE - TDD cycle successful (11/11 tests passing)
  - **Implementation Notes**:
    - Implemented LLMClient protocol for extensibility ✓
    - Created OpenRouterClient with httpx AsyncClient ✓
    - Support for chat completions endpoint: `https://openrouter.ai/api/v1/chat/completions` ✓
    - API key authentication via Bearer token + HTTP-Referer headers ✓
    - Exponential backoff retry logic for transient failures (429, 503, 504) ✓
    - Proper error handling: LLMAPIError, LLMTimeoutError, LLMConnectionError ✓
    - Structured logging for debugging and monitoring ✓
    - Resource cleanup with async context manager support ✓
  - **TDD Results**:
    - 🔴 RED: 11 tests written first, all failed as expected
    - 🟢 GREEN: Implementation completed, all 11 tests passing
    - 🔵 REFACTOR: Code structured with proper separation, docstrings, type hints
  - **Test Coverage**: 11 unit tests covering initialization, API calls, error handling, retries, timeouts
  - **Files**: `backend/src/browser_agent/agent/llm_client.py`, `tests/unit/test_llm_client.py`
  - **Spec**: Uses claude-3.5-sonnet via OpenRouter (research.md Decision 2)
  - **Tool Schema Reference**: contracts/llm-tools-schema.json for function calling definitions

- [X] **[INFRA-005]** Create ChatSession management service (Effort: M) **✅ COMPLETED**
  - Create `backend/src/chat/session.py` with session CRUD operations ✓
  - Implement in-memory session store (dict) with ChatSession model ✓
  - Support create, get, update, delete operations ✓
  - Track session status (active, ended, error) ✓
  - **Test**: Unit test for session lifecycle ✓ (19/19 tests passing)
  - **Files**: `backend/src/browser_agent/chat/session.py`, `tests/unit/test_session.py`
  - **Spec**: FR-017 (session duration persistence), data-model.md Entity 1
  - **Implementation Notes**:
    - ChatSession model with validation per data-model.md Entity 1
    - SessionService with in-memory dict storage
    - SessionStatus enum (active, ended, error)
    - Full CRUD operations: create, get, update, delete, list
    - Proper validation: timeout 1-300s, timestamps, status transitions
    - **TDD Results**: 🔴 RED → 🟢 GREEN → 🔵 REFACTOR cycle completed

- [X] **[INFRA-006]** Create ChatMessage storage service (Effort: M) **✅ COMPLETED**
  - Create `backend/src/chat/message.py` with message CRUD operations ✓
  - Implement async SQLite storage for messages using database from SETUP-008 ✓
  - Support create, get, list by session_id with pagination ✓
  - Enforce message validation rules from data-model.md ✓
  - **Test**: Unit test with async SQLite ✓ (17/17 tests passing)
  - **Files**: `backend/src/browser_agent/chat/message.py`, `tests/unit/test_message.py`, `tests/conftest.py`
  - **Spec**: FR-007 (conversation history), data-model.md Entity 2
  - **Implementation Notes**:
    - ChatMessage model with comprehensive validation
    - MessageService with full async CRUD operations
    - Message validation: sender/type compatibility, content non-empty, parent references
    - Pagination support for listing messages (limit/offset)
    - Session-based isolation and chronological ordering
    - Fixed SQLAlchemy reserved name conflict (metadata → message_metadata)
    - Created conftest.py for test database initialization
    - **TDD Results**: 🔴 RED → 🟢 GREEN → 🔵 REFACTOR cycle completed

- [X] **[INFRA-007]** Implement BrowserContext state management (Effort: M) **✅ COMPLETED**
  - Create `backend/src/browser/context.py` for browser context state ✓
  - Track current_url, page_title, page_state per data-model.md Entity 4 ✓
  - Implement get_page_state() method per browser-api.yaml ✓
  - Link context to session (one-to-one relationship) ✓
  - **Test**: Unit test for state tracking ✓ (15/15 tests passing)
  - **Files**: `backend/src/browser_agent/browser/context.py`, `tests/unit/test_context.py`
  - **Spec**: FR-015 (browser state awareness), data-model.md Entity 4
  - **Implementation Notes**:
    - BrowserContext model with page state tracking (idle, loading, ready, error)
    - ContextService with full async CRUD operations
    - One-to-one session relationship enforced via unique constraint
    - get_page_state() method returns current browser state per browser-api.yaml
    - Automatic timestamp tracking on page changes
    - Session isolation verified
    - **TDD Results**: 🔴 RED → 🟢 GREEN → 🔵 REFACTOR cycle completed

---

## Phase 2: User Story 1 - Basic Command Execution (Priority P1)

**Purpose**: MVP core functionality - execute simple browser commands
**Dependency**: Phase 1 complete
**Deliverable**: Users can navigate, click, type via natural language commands

**⚠️ TDD MANDATORY**: All tasks in this phase MUST follow RED-GREEN-REFACTOR cycle per constitution Section 3.1. Write failing tests first, make them pass with minimal code, then refactor. See "Test-Driven Development (TDD) - MANDATORY" section below for details.

### Tasks

- [X] **[US1-001]** Implement command parser foundation (Effort: L)
  - Create `backend/src/agent/command_parser.py` with CommandParser class
  - Implement parse() method per agent-interface.md
  - Define ParsedCommand dataclass with intent, actions, confidence_score
  - Add CommandIntent enum (navigate, interact, extract, configure)
  - **Test**: Unit test parsing simple command "Go to google.com"
  - **Files**: `backend/src/agent/command_parser.py`, `tests/unit/test_command_parser.py`
  - **Spec**: FR-003 (interpret natural language), agent-interface.md CommandParser
  - **Completed**: 17/17 tests passing

- [X] **[US1-002]** Integrate LLM for command interpretation (Effort: L)
  - Enhance CommandParser to call LLMClient.parse_command()
  - Load tool definitions from contracts/llm-tools-schema.json (6 tools: navigate, click, type_text, extract_information, scroll, configure_timeout)
  - Send tool schemas with LLM requests using OpenRouter function calling format
  - Map LLM tool calls to BrowserAction objects
  - Handle LLM errors gracefully (timeout, API errors)
  - **TDD Steps**:
    1. 🔴 Write test: "Go to google.com" → navigate tool call with url parameter
    2. 🟢 Implement tool schema loading and LLM request formatting
    3. 🔵 Add tool call → BrowserAction mapping
  - **Test**: Integration test with mocked LLM responses returning tool calls
  - **Files**: `backend/src/agent/command_parser.py`, `backend/src/agent/llm_parser.py`, `tests/unit/test_llm_integration.py`
  - **Spec**: FR-003, agent-interface.md LLMClient interface, contracts/llm-tools-schema.json
  - **Completed**: 16/16 tests passing

- [X] **[US1-003]** Implement navigation action handler (Effort: M)
  - Create `backend/src/browser/actions.py` with NavigateAction handler
  - Implement navigate() method using Playwright page.goto()
  - Support wait_for options (load, domcontentloaded, networkidle)
  - Apply timeout from session config (FR-020)
  - Return ActionResult with success status and duration
  - **Test**: Unit test with mocked browser, integration test with real navigation
  - **Files**: `backend/src/browser/actions.py`, `tests/unit/test_actions.py`
  - **Spec**: FR-004 (navigation commands), browser-api.yaml /navigate endpoint
  - **Completed**: 15/15 tests passing

- [X] **[US1-006]** Implement multi-strategy element finder (Effort: L)
  - Create `backend/src/browser/element_finder.py` with ElementFinder class
  - Implement find_elements() method with strategies: selector, text, aria_label, role
  - Use Playwright locators (get_by_text, get_by_label, get_by_role, locator)
  - Return list of matching PageElement objects
  - Support combined strategy (try multiple approaches)
  - **TDD Steps**:
    1. 🔴 Write test: find_by_text("Login") returns button element
    2. 🟢 Implement text-based finding using page.get_by_text()
    3. 🔴 Write test: find_by_role("button") returns all buttons
    4. 🟢 Add role-based strategy using page.get_by_role()
    5. 🔵 Refactor to unified find_elements() with strategy parameter
  - **Test**: Unit test for each strategy, integration test on real HTML page
  - **Files**: `backend/src/browser/element_finder.py`, `tests/unit/test_element_finder.py`
  - **Spec**: FR-010 (multi-strategy identification), browser-api.yaml /elements endpoint
  - **Completed**: 13/13 tests passing

- [X] **[US1-004]** Implement click action handler (Effort: M)
  - Add ClickAction handler to `actions.py`
  - Use ElementFinder (from US1-006) to locate target element
  - Implement click() using Playwright locator.click()
  - Handle click failures (element not found, not clickable)
  - **Test**: Unit test with mocked elements, integration test clicking real button
  - **Files**: `backend/src/browser/actions.py`, `tests/unit/test_actions.py`
  - **Spec**: FR-005 (click interaction), browser-api.yaml /click endpoint
  - **Completed**: 2/2 tests passing (execute_click_with_finder)

- [X] **[US1-005]** Implement type action handler (Effort: M)
  - Add TypeAction handler to `actions.py` ✓
  - Locate input element using ElementFinder (from US1-006) ✓
  - Implement type() using Playwright locator.fill() or type() ✓
  - Support clear_first and press_enter options (browser-api.yaml) ✓
  - **Test**: Unit test with mocked inputs, integration test typing into real form ✓
  - **Files**: `backend/src/browser/actions.py`, `tests/unit/test_actions.py`, `tests/integration/test_type.py`
  - **Spec**: FR-005 (type interaction), browser-api.yaml /type endpoint
  - **Completed**: 5/5 tests passing (execute_type_with_finder)
  - **TDD Results**:
    - 🔴 RED: 5 tests written first, all failed as expected (ImportError)
    - 🟢 GREEN: Implementation completed, all 5 tests passing
    - 🔵 REFACTOR: Exports updated, all 172 unit tests passing (171 functional + 1 test infra issue)

- **[US1-007]** Implement CommandExecutor for action orchestration (Effort: L)
  - Create `backend/src/agent/executor.py` with CommandExecutor class
  - Implement execute() method per agent-interface.md
  - Coordinate action execution via BrowserService
  - Handle errors and timeouts per FR-009
  - Return ExecutionResult with success status and message
  - **Test**: Unit test with mocked browser, integration test executing real command
  - **Files**: `backend/src/agent/executor.py`, `tests/unit/test_executor.py`, `tests/integration/test_agent_browser.py`
  - **Spec**: FR-011 (multi-step commands), agent-interface.md CommandExecutor

- **[US1-008]** Create chat message API endpoints (Effort: M)
  - Create `backend/src/api/routes.py` with chat routes
  - Implement POST /sessions (create session) per chat-api.yaml
  - Implement POST /sessions/{session_id}/messages (send command)
  - Implement GET /sessions/{session_id}/messages (get history)
  - Wire up CommandParser and CommandExecutor
  - **Test**: Integration test for each endpoint using TestClient
  - **Files**: `backend/src/api/routes.py`, `tests/integration/test_api_routes.py`
  - **Spec**: FR-001 (chat interface), chat-api.yaml paths

- **[US1-009]** Build basic chat UI components (Effort: L)
  - Create `frontend/src/components/ChatWindow.tsx` container
  - Create `MessageList.tsx` to display message history
  - Create `MessageInput.tsx` for user input with send button
  - Create `MessageBubble.tsx` for individual message rendering
  - Style with Radix UI components (research.md Decision 6)
  - **Test**: Component tests with React Testing Library
  - **Files**: `frontend/src/components/*.tsx`, `tests/components/ChatWindow.test.tsx`
  - **Spec**: FR-001 (chat interface), FR-018 (scrolling)

- **[US1-010]** Implement chat API client service (Effort: M)
  - Create `frontend/src/services/chatApi.ts` with API client
  - Implement createSession(), sendMessage(), getMessages() functions
  - Use fetch API or axios for HTTP requests
  - Handle errors and loading states
  - **Test**: Unit test with mocked fetch responses
  - **Files**: `frontend/src/services/chatApi.ts`, `tests/services/chatApi.test.ts`

- **[US1-011]** Wire up frontend to backend API (Effort: M)
  - Connect ChatWindow component to chatApi service
  - Implement state management for messages (React state or Zustand)
  - Handle sending messages and receiving responses
  - Display loading state while agent processes command
  - **Test**: Integration test with mocked API, E2E test with real backend
  - **Files**: `frontend/src/App.tsx`, `frontend/src/components/ChatWindow.tsx`

- **[US1-012]** Implement success confirmation messages (Effort: S)
  - Enhance ExecutionResult to include human-readable messages per FR-008
  - Format success messages: "Successfully navigated to {url}", "Clicked '{element}' button"
  - Display confirmation in chat UI within 3 seconds (SC-002)
  - **Test**: E2E test verifies confirmation appears in chat
  - **Files**: `backend/src/agent/executor.py`, `frontend/src/components/MessageBubble.tsx`
  - **Spec**: FR-008 (confirmation messages), SC-002 (3s response time)

- **[US1-013]** Implement error handling and reporting (Effort: M)
  - Create domain exception classes in `backend/src/exceptions.py`
  - Implement clear error messages per FR-009
  - Map exceptions to user-friendly responses
  - Display errors in chat UI with red styling
  - **Test**: Unit test for each exception type, E2E test error scenarios
  - **Files**: `backend/src/exceptions.py`, `backend/src/agent/executor.py`, `tests/unit/test_exceptions.py`
  - **Spec**: FR-009 (clear error messages), agent-interface.md Error Handling Contract

- **[US1-014]** E2E test for User Story 1 acceptance scenarios (Effort: L)
  - Create `tests/e2e/test_user_story_1.py` with 4 acceptance scenarios from spec.md
  - Scenario 1: Navigate to https://example.com
  - Scenario 2: Click the login button
  - Scenario 3: Type 'john@example.com' in email field
  - Scenario 4: Response within 3 seconds
  - Use pytest with real browser and backend server
  - **Test**: All 4 scenarios pass
  - **Files**: `tests/e2e/test_user_story_1.py`
  - **Spec**: User Story 1 acceptance scenarios (spec.md lines 20-23)

---

## Phase 3: User Story 2 - Information Extraction (Priority P2)

**Purpose**: Enable users to ask for information and receive results in chat
**Dependency**: Phase 2 complete (US1 working)
**Deliverable**: Agent can extract text, counts, lists from pages

**⚠️ TDD MANDATORY**: All tasks in this phase MUST follow RED-GREEN-REFACTOR cycle per constitution Section 3.1. Write failing tests first, make them pass with minimal code, then refactor. See "Test-Driven Development (TDD) - MANDATORY" section below for details.

### Tasks

- **[US2-001]** Implement information extraction actions (Effort: L)
  - Create `backend/src/browser/extraction.py` with ExtractionService
  - Implement extract_text() for single element text extraction
  - Implement extract_attribute() for element attributes (href, src, etc.)
  - Implement extract_list() for multiple elements (e.g., all links)
  - Implement count_elements() for element counting
  - **Test**: Unit test each extraction type, integration test on real HTML
  - **Files**: `backend/src/browser/extraction.py`, `tests/unit/test_extraction.py`, `tests/integration/test_extraction.py`
  - **Spec**: FR-006a (locate information), FR-006c (extraction types), browser-api.yaml /extract endpoint

- **[US2-002]** Enhance command parser for information-seeking questions (Effort: M)
  - Update CommandParser to recognize question patterns ("What is...", "How many...", "List...")
  - Map questions to extraction actions using LLM interpretation
  - Define extraction intent and target elements
  - **Test**: Unit test parsing "What is the page title?" → extract(target=title)
  - **Files**: `backend/src/agent/command_parser.py`, `tests/unit/test_command_parser.py`
  - **Spec**: FR-006 (interpret information-seeking questions)

- **[US2-003]** Implement extraction result formatting (Effort: M)
  - Create formatter in `backend/src/agent/formatter.py`
  - Format single values: "The page title is '{title}'"
  - Format lists: "Found 5 links: 1) Home 2) About..."
  - Format counts: "There are 12 images on this page"
  - Add context to results per US2 acceptance scenario 7
  - **Test**: Unit test each format type
  - **Files**: `backend/src/agent/formatter.py`, `tests/unit/test_formatter.py`
  - **Spec**: FR-006b (format found information), FR-019 (distinguish actions vs info)

- **[US2-004]** Handle information not found scenarios (Effort: S)
  - Detect when extraction returns empty results
  - Generate helpful "not found" messages per FR-009a
  - Suggest alternatives: "I couldn't find a phone number. Try asking about contact information or email address."
  - **Test**: Unit test not found handling
  - **Files**: `backend/src/agent/executor.py`, `tests/unit/test_executor.py`
  - **Spec**: FR-009a (inform when info not found, suggest alternatives)

- **[US2-005]** Implement page context extraction for LLM (Effort: M)
  - Create `backend/src/browser/page_analyzer.py` to extract page summary
  - Generate brief page content summary (headings, key elements)
  - Pass page context to LLM for better extraction accuracy
  - Cache page context for performance (5 second TTL per data-model.md)
  - **Test**: Unit test context extraction, integration test with real page
  - **Files**: `backend/src/browser/page_analyzer.py`, `tests/unit/test_page_analyzer.py`
  - **Spec**: FR-015 (browser state awareness), agent-interface.md page_context parameter

- **[US2-006]** Add extraction API endpoints (Effort: S)
  - Add POST /contexts/{context_id}/extract to browser API routes
  - Implement extraction_type parameter (text, attribute, count, list)
  - Return ExtractionResult per browser-api.yaml schema
  - **Test**: Integration test for endpoint
  - **Files**: `backend/src/api/routes.py`, `tests/integration/test_api_routes.py`
  - **Spec**: browser-api.yaml /extract endpoint

- **[US2-007]** Update chat UI to display extracted information (Effort: S)
  - Enhance MessageBubble to render formatted extraction results
  - Support numbered lists, counts, and text values
  - Apply distinct styling for info vs action messages (FR-019)
  - **Test**: Component test with sample extraction result
  - **Files**: `frontend/src/components/MessageBubble.tsx`, `tests/components/MessageBubble.test.tsx`
  - **Spec**: FR-019 (distinguish actions and information)

- **[US2-008]** E2E test for User Story 2 acceptance scenarios (Effort: XL)
  - Create `tests/e2e/test_user_story_2.py` with 7 acceptance scenarios
  - Scenario 1: Extract page title
  - Scenario 2: Find price on product page
  - Scenario 3: List first 5 search results
  - Scenario 4: Extract main headings
  - Scenario 5: Find phone number
  - Scenario 6: Count images
  - Scenario 7: Verify formatted output with context
  - **Test**: All scenarios pass with 90% success rate (SC-003a)
  - **Files**: `tests/e2e/test_user_story_2.py`
  - **Spec**: User Story 2 acceptance scenarios (spec.md lines 37-43), SC-003 (<5s), SC-003a (90% accuracy)

---

## Phase 4: User Story 3 - Multi-Step Task Automation (Priority P2)

**Purpose**: Execute complex multi-step workflows with progress updates
**Dependency**: Phase 3 complete
**Deliverable**: Agent handles multi-step commands and reports progress

**⚠️ TDD MANDATORY**: All tasks in this phase MUST follow RED-GREEN-REFACTOR cycle per constitution Section 3.1. Write failing tests first, make them pass with minimal code, then refactor. See "Test-Driven Development (TDD) - MANDATORY" section below for details.

### Tasks

- **[US3-001]** Enhance command parser for multi-step commands (Effort: M)
  - Update CommandParser to detect compound commands ("Go to X, search for Y, click Z")
  - Parse into sequence of BrowserAction objects
  - Assign step numbers to each action
  - **Test**: Unit test parsing "Go to amazon.com, search for 'laptop', show first 3 results"
  - **Files**: `backend/src/agent/command_parser.py`, `tests/unit/test_command_parser.py`
  - **Spec**: FR-011 (handle multi-step commands)

- **[US3-002]** Implement progress reporting in executor (Effort: M)
  - Enhance CommandExecutor.execute() to support progress_callback
  - Emit progress updates for each step completion: "Step 2 of 4: Typing 'laptop' in search..."
  - Store progress updates as ChatMessage with type=progress_update
  - **Test**: Unit test progress callback invocations
  - **Files**: `backend/src/agent/executor.py`, `tests/unit/test_executor.py`
  - **Spec**: FR-012 (progress updates for multi-step tasks)

- **[US3-003]** Add WebSocket support for real-time updates (Effort: L)
  - Create `backend/src/api/websocket.py` with WebSocket endpoint
  - Implement /ws/chat/{session_id} per chat-api.yaml
  - Broadcast progress updates to connected clients
  - Support message types: message.created, action.progress, session.ended
  - **Test**: Integration test WebSocket connection and message flow
  - **Files**: `backend/src/api/websocket.py`, `tests/integration/test_websocket.py`
  - **Spec**: chat-api.yaml /ws/chat endpoint

- **[US3-004]** Implement frontend WebSocket client (Effort: M)
  - Create `frontend/src/services/websocket.ts` WebSocket client
  - Connect to /ws/chat/{session_id} on session creation
  - Listen for progress updates and display in real-time
  - Handle reconnection on connection loss
  - **Test**: Unit test with mocked WebSocket
  - **Files**: `frontend/src/services/websocket.ts`, `tests/services/websocket.test.ts`

- **[US3-005]** Display progress updates in chat UI (Effort: S)
  - Update MessageList to show progress_update messages
  - Style progress messages differently (e.g., italic, smaller font)
  - Show "Step X of Y" indicator
  - Auto-scroll to latest progress update
  - **Test**: Component test with sample progress messages
  - **Files**: `frontend/src/components/MessageList.tsx`, `frontend/src/components/MessageBubble.tsx`
  - **Spec**: FR-012 (progress updates display)

- **[US3-006]** Implement error handling for multi-step failures (Effort: M)
  - Detect when a step in multi-step task fails
  - Stop execution immediately (don't proceed to next step)
  - Report which step failed and why: "Step 2 of 4 failed: Could not find search button"
  - **Test**: E2E test multi-step task with intentional failure at step 2
  - **Files**: `backend/src/agent/executor.py`, `tests/e2e/test_multistep_error.py`
  - **Spec**: User Story 3 acceptance scenario 3 (spec.md line 59)

- **[US3-007]** Implement task completion summary (Effort: S)
  - Generate summary message after multi-step task completes
  - List all actions taken: "Completed 3 steps: 1) Navigated to amazon.com 2) Searched for 'laptop' 3) Extracted 3 results"
  - Include final result (e.g., extracted data)
  - **Test**: E2E test verifies summary message
  - **Files**: `backend/src/agent/executor.py`
  - **Spec**: User Story 3 acceptance scenario 4 (spec.md line 60)

- **[US3-008]** E2E test for User Story 3 acceptance scenarios (Effort: L)
  - Create `tests/e2e/test_user_story_3.py` with 4 acceptance scenarios
  - Scenario 1: Multi-step amazon search workflow
  - Scenario 2: Progress updates for each step
  - Scenario 3: Failure stops execution with clear error
  - Scenario 4: Completion summary with all actions
  - **Test**: All scenarios pass within 30s (SC-007)
  - **Files**: `tests/e2e/test_user_story_3.py`
  - **Spec**: User Story 3 acceptance scenarios (spec.md lines 57-60), SC-007 (<30s workflow)

---

## Phase 5: User Story 4 - Conversation History and Context (Priority P3)

**Purpose**: Enable contextual references to previous commands and results
**Dependency**: Phase 2 complete (can be parallel with Phase 4)
**Deliverable**: Agent uses conversation history to resolve references

**⚠️ TDD MANDATORY**: All tasks in this phase MUST follow RED-GREEN-REFACTOR cycle per constitution Section 3.1. Write failing tests first, make them pass with minimal code, then refactor. See "Test-Driven Development (TDD) - MANDATORY" section below for details.

### Tasks

- **[US4-001]** Enhance command parser with conversation context (Effort: M)
  - Update CommandParser.parse() to accept conversation_context parameter
  - Pass recent messages (last 10) to LLM for context
  - Resolve references like "it", "that page", "third result" using history
  - **Test**: Unit test parsing "Click the third result" after previous extraction
  - **Files**: `backend/src/agent/command_parser.py`, `tests/unit/test_command_parser.py`
  - **Spec**: FR-007 (maintain conversation history), agent-interface.md conversation_context

- **[US4-002]** Implement conversation history retrieval (Effort: S)
  - Create get_conversation_context() method in ChatService
  - Return last N messages for session (default 10, max 200)
  - Format messages for LLM consumption
  - **Test**: Unit test retrieval with various message counts
  - **Files**: `backend/src/chat/session.py`, `tests/unit/test_session.py`
  - **Spec**: FR-007, agent-interface.md ChatService.get_conversation_context

- **[US4-003]** Add conversation history scrolling to UI (Effort: S)
  - Ensure MessageList supports scrolling per FR-018
  - Load initial messages on session start
  - Implement auto-scroll to bottom on new message
  - Allow user to scroll up to view history
  - **Test**: Component test with 50+ messages
  - **Files**: `frontend/src/components/MessageList.tsx`
  - **Spec**: FR-018 (chat interface scrolling)

- **[US4-004]** Implement session isolation (Effort: S)
  - Ensure new sessions don't access previous session history
  - Clear context on session end
  - Test that "that page" fails without prior context
  - **Test**: E2E test with two sequential sessions
  - **Files**: `backend/src/chat/session.py`
  - **Spec**: User Story 4 acceptance scenario 4 (spec.md line 77)

- **[US4-005]** Optimize conversation history performance (Effort: M)
  - Implement pagination for message history (GET /messages?limit=50&offset=0)
  - Add database indexes for session_id and timestamp
  - Lazy load older messages on scroll-up
  - **Test**: Performance test with 200 messages (SC-004, SC-009)
  - **Files**: `backend/src/chat/message.py`, `frontend/src/components/MessageList.tsx`
  - **Spec**: SC-004 (100+ pairs), SC-009 (200 messages responsive)

- **[US4-006]** E2E test for User Story 4 acceptance scenarios (Effort: M)
  - Create `tests/e2e/test_user_story_4.py` with 4 acceptance scenarios
  - Scenario 1: Reference "third result" from previous extraction
  - Scenario 2: Scroll to view previous conversation
  - Scenario 3: Resolve "it" or "that page" from context
  - Scenario 4: New session has no access to old history
  - **Test**: All scenarios pass
  - **Files**: `tests/e2e/test_user_story_4.py`
  - **Spec**: User Story 4 acceptance scenarios (spec.md lines 74-77)

---

## Phase 6: User Story 5 - Confidence-Based Clarification (Priority P3)

**Purpose**: Implement 90% confidence threshold with clarification flow
**Dependency**: Phase 2 complete
**Deliverable**: Agent asks clarifying questions when confidence < 90%

**⚠️ TDD MANDATORY**: All tasks in this phase MUST follow RED-GREEN-REFACTOR cycle per constitution Section 3.1. Write failing tests first, make them pass with minimal code, then refactor. See "Test-Driven Development (TDD) - MANDATORY" section below for details.

### Tasks

- **[US5-001]** Implement confidence evaluator (Effort: L)
  - Create `backend/src/agent/confidence.py` with ConfidenceEvaluator class
  - Implement evaluate() method per agent-interface.md
  - Calculate confidence score using weighted formula (lines 116-124)
  - Factors: command_clarity (40%), element_ambiguity (35%), context_availability (15%), action_complexity (10%)
  - Return ConfidenceEvaluation with score and factors breakdown
  - **TDD Steps**:
    1. 🔴 Write test: Clear command "Go to google.com" → confidence ≥ 0.95
    2. 🟢 Implement basic confidence calculation with command_clarity factor
    3. 🔴 Write test: Ambiguous "Click the button" with 5 buttons → confidence < 0.50
    4. 🟢 Add element_ambiguity factor based on matching element count
    5. 🔴 Write test: Weighted formula produces 0-100 scale scores
    6. 🟢 Implement full weighted calculation with all 4 factors
    7. 🔵 Refactor to separate factor calculation methods
  - **Test**: Unit test confidence calculation for various scenarios
  - **Files**: `backend/src/agent/confidence.py`, `tests/unit/test_confidence.py`
  - **Spec**: FR-014 (0-100% scale), FR-014b (factors), agent-interface.md ConfidenceEvaluator

- **[US5-002]** Implement should_clarify threshold check (Effort: XS)
  - Add should_clarify() method to ConfidenceEvaluator
  - Return True if confidence_score < 0.90 (FR-014a)
  - **Test**: Unit test boundary conditions (0.89, 0.90, 0.91)
  - **Files**: `backend/src/agent/confidence.py`, `tests/unit/test_confidence.py`
  - **Spec**: FR-014a (90% threshold), SC-006 (100% clarification below 90%)

- **[US5-003]** Implement clarification question generator (Effort: L)
  - Create `backend/src/agent/clarification.py` with ClarificationGenerator class
  - Implement generate_question() per agent-interface.md
  - Support question types: multiple_choice, text_input, yes_no
  - Use question templates from agent-interface.md lines 189-193
  - **Test**: Unit test question generation for multiple elements scenario
  - **Files**: `backend/src/agent/clarification.py`, `tests/unit/test_clarification.py`
  - **Spec**: FR-014b (specific feedback), agent-interface.md ClarificationGenerator

- **[US5-004]** Integrate confidence evaluation into executor (Effort: M)
  - Update CommandExecutor.execute() to call ConfidenceEvaluator
  - Check should_clarify() before executing command
  - If True, send clarification question instead of executing
  - Store original command for retry after clarification
  - **Test**: Integration test low confidence flow
  - **Files**: `backend/src/agent/executor.py`, `tests/integration/test_confidence_flow.py`
  - **Spec**: FR-014a (ask clarification < 90%)

- **[US5-005]** Implement clarification response processing (Effort: M)
  - Add process_clarification() method to ClarificationGenerator
  - Re-parse original command with user's clarifying response
  - Re-evaluate confidence with new context
  - Proceed if confidence >= 0.9, else ask follow-up question
  - **Test**: Unit test clarification processing with various responses
  - **Files**: `backend/src/agent/clarification.py`, `tests/unit/test_clarification.py`
  - **Spec**: FR-014c (re-evaluate after clarification), FR-014d (continue until 90%)

- **[US5-006]** Implement multi-round clarification support (Effort: M)
  - Track clarification attempts count (max 3 per constitution)
  - Link clarification messages via parent_message_id
  - Stop after 3 failed attempts and suggest alternative
  - **Test**: E2E test 3 clarification rounds failing to reach 90%
  - **Files**: `backend/src/agent/clarification.py`, `tests/e2e/test_clarification_limit.py`
  - **Spec**: FR-014d (continue asking until 90% or determine cannot complete)

- **[US5-007]** Display clarification questions in chat UI (Effort: S)
  - Render clarification_request messages with options
  - For multiple_choice: show numbered list of options
  - For text_input: show free-form input prompt
  - Style differently from regular responses
  - **Test**: Component test with clarification message
  - **Files**: `frontend/src/components/MessageBubble.tsx`
  - **Spec**: FR-014b (specific feedback)

- **[US5-008]** Implement clarification response UI (Effort: S)
  - Allow user to click option number or type response
  - Link clarification response to parent_message_id
  - Send as clarification_response message type
  - **Test**: Component test clarification interaction
  - **Files**: `frontend/src/components/MessageInput.tsx`, `frontend/src/components/MessageBubble.tsx`

- **[US5-009]** Add metadata to messages for confidence tracking (Effort: S)
  - Store confidence score in ChatMessage.metadata per chat-api.yaml
  - Include clarification_reason in metadata
  - Display confidence score in UI (optional, for debugging)
  - **Test**: E2E test verifies metadata persisted
  - **Files**: `backend/src/chat/message.py`, `frontend/src/types/message.ts`
  - **Spec**: data-model.md ChatMessage.metadata, chat-api.yaml metadata schema

- **[US5-010]** E2E test for User Story 5 acceptance scenarios (Effort: XL)
  - Create `tests/e2e/test_user_story_5.py` with 7 acceptance scenarios
  - Scenario 1: Agent detects <90% confidence and asks clarification
  - Scenario 2: Multiple buttons scenario with numbered options
  - Scenario 3: User clarifies, confidence reaches 90%, execution proceeds
  - Scenario 4: Multiple clarification rounds until 90%
  - Scenario 5: Element not found error with clear explanation
  - Scenario 6: Unclear command triggers clarification question
  - Scenario 7: User corrects error without restarting task
  - **Test**: All scenarios pass, SC-006 (100% clarification), SC-006a (95% success after clarification), SC-006b (85% one-exchange resolution)
  - **Files**: `tests/e2e/test_user_story_5.py`
  - **Spec**: User Story 5 acceptance scenarios (spec.md lines 91-97), SC-006/006a/006b

---

## Phase 7: Configuration and User Experience Polish

**Purpose**: Implement timeout configuration, cancellation, and UX improvements
**Dependency**: Phase 2 complete
**Deliverable**: Timeout slash command, cancel button, improved error messages

**⚠️ TDD MANDATORY**: All tasks in this phase MUST follow RED-GREEN-REFACTOR cycle per constitution Section 3.1. Write failing tests first, make them pass with minimal code, then refactor. See "Test-Driven Development (TDD) - MANDATORY" section below for details.

### Tasks

- **[POLISH-001]** Implement /timeout slash command (Effort: M)
  - Detect /timeout pattern in command parser
  - Create configuration action handler in executor
  - Update session.timeout_seconds per FR-021
  - Respond with confirmation: "Updated timeout to 60 seconds (was 20 seconds)"
  - **Test**: E2E test /timeout command
  - **Files**: `backend/src/agent/command_parser.py`, `backend/src/chat/session.py`, `tests/e2e/test_timeout_config.py`
  - **Spec**: FR-021 (configurable timeout via slash command)

- **[POLISH-002]** Implement timeout configuration API endpoint (Effort: S)
  - Add PUT /sessions/{session_id}/config/timeout per chat-api.yaml
  - Validate timeout range (1-300 seconds)
  - Return previous and new timeout values
  - **Test**: Integration test endpoint
  - **Files**: `backend/src/api/routes.py`, `tests/integration/test_api_routes.py`
  - **Spec**: chat-api.yaml /config/timeout endpoint

- **[POLISH-003]** Implement timeout reset on restart (Effort: XS)
  - Set default timeout_seconds=20 on new session creation
  - Document that timeout resets to 20s on app restart per FR-022
  - **Test**: E2E test session creation has default timeout
  - **Files**: `backend/src/chat/session.py`
  - **Spec**: FR-022 (reset to 20s default on restart)

- **[POLISH-004]** Implement command cancellation backend (Effort: M)
  - Add cancel flag to BrowserAction execution
  - Implement POST /sessions/{session_id}/messages/{message_id}/cancel per chat-api.yaml
  - Stop in-progress actions and set status=cancelled
  - **Test**: Integration test cancellation during execution
  - **Files**: `backend/src/agent/executor.py`, `backend/src/api/routes.py`, `tests/integration/test_cancellation.py`
  - **Spec**: FR-013 (allow stop/cancel), chat-api.yaml /cancel endpoint

- **[POLISH-005]** Implement cancel button UI (Effort: M)
  - Create `frontend/src/components/CancelButton.tsx`
  - Show button when message status=processing
  - Call cancel API endpoint on click
  - Display "Cancelling..." state while waiting
  - **Test**: Component test cancel button interaction
  - **Files**: `frontend/src/components/CancelButton.tsx`, `tests/components/CancelButton.test.tsx`
  - **Spec**: FR-013 (dedicated cancel button in UI)

- **[POLISH-006]** Support chat "stop" command (Effort: S)
  - Detect "stop" or "cancel" keywords in command parser
  - Cancel most recent in-progress command
  - Respond with confirmation: "Cancelled navigation to example.com"
  - **Test**: E2E test typing "stop" cancels command
  - **Files**: `backend/src/agent/command_parser.py`
  - **Spec**: FR-013 (typing "stop" or "cancel" commands)

- **[POLISH-007]** Enhance error messages with retry suggestions (Effort: M)
  - Update domain exceptions to include retry_suggestion per FR-009a
  - Implement suggestions for common errors:
    - Element not found → "Wait a few seconds, or ask me to list all buttons first"
    - Timeout → "Try increasing timeout with /timeout 60"
    - Page load error → "Check the URL or try refreshing"
  - **Test**: Unit test each error type has suggestion
  - **Files**: `backend/src/exceptions.py`, `backend/src/agent/executor.py`, `tests/unit/test_exceptions.py`
  - **Spec**: FR-009a (actionable retry suggestions), SC-008 (80% successful retry)

- **[POLISH-008]** Implement loading indicators in UI (Effort: S)
  - Show spinner or "Agent is typing..." indicator when message status=processing
  - Display progress bar for multi-step tasks (optional)
  - Clear indicator on completion or error
  - **Test**: Component test loading states
  - **Files**: `frontend/src/components/MessageList.tsx`
  - **Spec**: FR-002 (response within 3s), feedback principle

- **[POLISH-009]** Add accessibility testing (Effort: M)
  - Install axe-core for automated accessibility testing
  - Run axe tests on all chat UI components
  - Ensure ARIA labels for buttons, inputs, messages
  - Test keyboard navigation (tab, enter, esc)
  - **Test**: Accessibility test suite with axe-core
  - **Files**: `tests/accessibility/test_chat_ui.ts`
  - **Spec**: Constitution UX & Accessibility section 4, research.md Decision 6

- **[POLISH-010]** Implement browser cleanup on session end (Effort: S)
  - Close browser context when session status=ended
  - Clean up database records (optional, or let SQLite auto-clean)
  - Release resources (memory, file handles)
  - **Test**: Integration test verifies browser closes
  - **Files**: `backend/src/browser/context.py`, `backend/src/chat/session.py`
  - **Spec**: Constitution reliability principle, browser resource management

---

## Phase 8: Testing, Documentation, and Deployment

**Purpose**: Comprehensive testing, documentation, and deployment readiness
**Dependency**: All features complete
**Deliverable**: Production-ready application with full test coverage and documentation

### Tasks

- **[TEST-001]** Achieve 80% overall test coverage (Effort: L)
  - Run `pytest --cov=src --cov-report=html` to measure coverage
  - Write additional unit tests for uncovered lines
  - Focus on edge cases and error paths
  - **Test**: Coverage report shows ≥80%
  - **Files**: `tests/unit/**/*.py`
  - **Spec**: Constitution testing strategy, coverage targets

- **[TEST-002]** Achieve 100% coverage for critical paths (Effort: M)
  - Identify automation control flows (browser actions, command execution)
  - Write targeted tests for 100% coverage of these modules
  - **Test**: Coverage report shows 100% for browser/, agent/executor.py
  - **Files**: `tests/unit/test_actions.py`, `tests/unit/test_executor.py`
  - **Spec**: Constitution coverage requirement (100% critical paths)

- **[TEST-003]** Run end-to-end test suite (Effort: S)
  - Execute all E2E tests for User Stories 1-5
  - Verify all acceptance scenarios pass
  - Measure success criteria (SC-001 to SC-010)
  - **Test**: All E2E tests green, success criteria met
  - **Files**: `tests/e2e/*.py`
  - **Spec**: All user story acceptance scenarios

- **[TEST-004]** Performance testing for success criteria (Effort: M)
  - Measure response times (SC-002: <3s simple, <10s complex)
  - Test extraction speed (SC-003: <5s)
  - Load test conversation history (SC-004: 100-200 pairs)
  - Verify element identification accuracy (SC-005: 90%)
  - **Test**: Performance benchmarks meet all SC targets
  - **Files**: `tests/performance/*.py`
  - **Spec**: Success criteria SC-002 to SC-010

- **[TEST-005]** Security testing and API key validation (Effort: M)
  - Test that .env files are gitignored (verify no accidental commits)
  - Validate API key is required for OpenRouter client
  - Test input validation prevents injection attacks
  - Scan dependencies for known vulnerabilities
  - **Test**: Security scan passes with no critical issues
  - **Files**: Security scan reports
  - **Spec**: Constitution security & compliance

- **[DOC-001]** Update README with complete setup instructions (Effort: S)
  - Finalize setup steps (prerequisites, installation, configuration)
  - Add troubleshooting section
  - Include example commands for testing
  - Link to quickstart.md for detailed guide
  - **Test**: New developer can set up from README alone
  - **Files**: `README.md`

- **[DOC-002]** Generate API documentation (Effort: S)
  - Generate OpenAPI docs from FastAPI (available at /docs)
  - Document WebSocket message formats
  - Add example requests/responses
  - **Test**: Swagger UI accessible at http://localhost:8000/docs
  - **Files**: Auto-generated from FastAPI

- **[DOC-003]** Write developer guide (Effort: M)
  - Document architecture and design decisions
  - Explain key modules (agent, browser, chat)
  - Add diagrams (architecture, data flow)
  - Include extension points for future features
  - **Test**: Documentation review by team
  - **Files**: `docs/developer-guide.md`

- **[DOC-004]** Create user guide (Effort: M)
  - Write end-user documentation for using the agent
  - Include example commands and workflows
  - Document slash commands (/timeout)
  - Add FAQ and troubleshooting
  - **Test**: User testing with documentation
  - **Files**: `docs/user-guide.md`

- **[DEPLOY-001]** Create production configuration (Effort: S)
  - Set up production .env.example with secure defaults
  - Configure headless browser mode for production
  - Set production log levels (INFO, not DEBUG)
  - Document production environment variables
  - **Test**: Production config validated
  - **Files**: `.env.production.example`, `docs/deployment.md`

- **[DEPLOY-002]** Create Docker configuration (optional) (Effort: L)
  - Write Dockerfile for backend service
  - Write Dockerfile for frontend service
  - Create docker-compose.yml for local deployment
  - Include Playwright browser installation in image
  - **Test**: `docker-compose up` starts application
  - **Files**: `Dockerfile.backend`, `Dockerfile.frontend`, `docker-compose.yml`

- **[DEPLOY-003]** Set up CI/CD pipeline (Effort: L)
  - Configure GitHub Actions or similar CI
  - Run linting, type checks, tests on every PR
  - Generate coverage reports
  - Run E2E tests in CI environment
  - **Test**: CI pipeline passes on main branch
  - **Files**: `.github/workflows/ci.yml`

---

## Dependency Graph

```
Phase 0: Setup
    ↓
Phase 1: Core Infrastructure
    ↓
Phase 2: US1 (Basic Commands) ← MVP Core
    ↓
    ├─→ Phase 3: US2 (Information Extraction) ← MVP Extended
    │       ↓
    ├─→ Phase 4: US3 (Multi-Step Automation)
    │       ↓
    ├─→ Phase 5: US4 (Conversation History) ─┐
    │       ↓                                  │
    └─→ Phase 6: US5 (Confidence/Clarification)┘
            ↓
    Phase 7: Polish (Timeout, Cancel, UX)
            ↓
    Phase 8: Testing, Docs, Deployment
```

**Parallel Execution Opportunities**:
- Phase 3 (US2) and Phase 5 (US4) can run in parallel after Phase 2
- Phase 4 (US3) and Phase 6 (US5) can run in parallel after Phase 2
- POLISH tasks can be incrementally integrated during feature development

---

## Task Count Summary

| Phase | Task Count | Est. Effort (Person-Days) |
|-------|-----------|---------------------------|
| Phase 0: Setup | 9 | 3-4 days |
| Phase 1: Infrastructure | 7 | 4-5 days |
| Phase 2: US1 (P1) | 14 | 7-9 days |
| Phase 3: US2 (P2) | 8 | 5-6 days |
| Phase 4: US3 (P2) | 8 | 4-5 days |
| Phase 5: US4 (P3) | 6 | 3-4 days |
| Phase 6: US5 (P3) | 10 | 6-8 days |
| Phase 7: Polish | 10 | 4-5 days |
| Phase 8: Test/Doc/Deploy | 11 | 5-7 days |
| **TOTAL** | **78** | **41-53 days** |

**MVP Recommendation**: Phases 0-3 (US1-US2) = ~24-30 days for a working browser automation agent with basic commands and information extraction.

---

## Notes for Implementation

### Test-Driven Development (TDD) - MANDATORY

**⚠️ CONSTITUTIONAL REQUIREMENT: All production code MUST follow RED-GREEN-REFACTOR cycle**

Per constitution Section 3.1, TDD is non-negotiable:

**Before writing ANY production code:**

1. **🔴 RED: Write failing test first**
   - Write test describing desired behavior
   - Run test and verify it FAILS
   - If test passes without implementation, you haven't written a valid test

2. **🟢 GREEN: Make test pass with minimal code**
   - Write simplest implementation to pass
   - No extra features, no premature optimization
   - Run test and verify it PASSES

3. **🔵 REFACTOR: Improve while keeping tests green**
   - Clean up duplication, improve names
   - Run tests after each change
   - All tests must stay green

**Code Review Verification:**
- Git commits must show test-before-code pattern
- Evidence of failing tests (RED phase) required
- **Violations = Automatic PR Rejection**

**For tasks marked with specific "TDD Steps", follow those examples. For all other tasks, apply the RED-GREEN-REFACTOR cycle to the acceptance criteria listed in the task.**

### Incremental Delivery
Deliver working software at the end of each phase:
- Phase 2: Demo basic commands (navigate, click, type)
- Phase 3: Demo information extraction
- Phase 4: Demo multi-step workflows
- Phases 5-6: Demo advanced features (context, clarification)

### Quality Gates
Before marking phase complete:
- ✅ All tests passing (unit, integration, E2E)
- ✅ Linting and type checks pass
- ✅ Code reviewed
- ✅ Documentation updated

### Risk Mitigation
High-risk areas requiring extra attention:
1. **OpenRouter API integration** - Mock responses for testing, handle rate limits
2. **Playwright stability** - Handle browser crashes, implement retry logic
3. **Confidence evaluation accuracy** - Iterate on formula based on real-world testing
4. **WebSocket reliability** - Test reconnection scenarios

---

**Tasks Generated**: 2025-10-18
**Ready for**: `/speckit.implement` or manual incremental implementation
