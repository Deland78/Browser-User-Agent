# Research: Browser Automation Agent with Chat Interface

**Feature**: 001-browser-agent-chat
**Date**: 2025-10-18
**Purpose**: Resolve technology choices and architectural decisions for implementation

## Research Questions

Based on Technical Context NEEDS CLARIFICATION items:
1. Browser automation library selection
2. LLM/NLP approach for command interpretation
3. Web framework for backend API
4. Frontend framework for chat UI
5. Deployment target (desktop vs web)
6. Accessibility strategy for WCAG 2.1 AA compliance

---

## Decision 1: Browser Automation Library

**Decision**: **Playwright** (Python)

**Rationale**:
- **Modern & Maintained**: Active development, Microsoft-backed, excellent documentation
- **Multi-browser**: Supports Chromium, Firefox, WebKit with single API
- **Python Support**: First-class Python async/await support
- **Element Identification**: Robust selectors including text content, labels, ARIA roles → aligns with FR-010 (multi-strategy element identification)
- **Auto-waiting**: Built-in smart waiting for elements reduces flaky tests
- **Network Control**: Can intercept/modify network traffic for testing
- **Headless + Headed**: Supports both modes for debugging and production
- **Performance**: Faster than Selenium due to CDP (Chrome DevTools Protocol)

**Alternatives Considered**:

| Library | Pros | Cons | Why Rejected |
|---------|------|------|--------------|
| Selenium | Mature, widely adopted, extensive community | Slower, more brittle element finding, legacy architecture | Performance concerns; less robust waiting mechanisms |
| Puppeteer | Fast, good Chrome support | Node.js-first (Python wrapper pyppeteer is less mature), Chromium-only | Python support is secondary; single-browser limitation |
| Helium | Simpler API, built on Selenium | Less control, fewer features, smaller community | Insufficient flexibility for confidence evaluation |

**Implementation Notes**:
- Use Playwright's `page.locator()` with multiple strategies (text, role, label)
- Leverage `page.wait_for_load_state()` for 20s timeout implementation
- Use `page.evaluate()` for information extraction from DOM

---

## Decision 2: LLM/NLP for Command Interpretation

**Decision**: **OpenRouter.ai** (accessing Claude 3.5 Sonnet or other models)

**Rationale**:
- **Model Flexibility**: Single API to access multiple LLM providers (Anthropic Claude, OpenAI, Google, Meta, etc.)
- **Cost Optimization**: Can switch between models based on cost/performance without code changes
- **Function Calling**: Supports tool/function calling for all compatible models → maps user commands to structured browser actions
- **Context Window**: 200K tokens (Claude) supports full conversation history (100-200 message pairs per SC-004)
- **Fallback Options**: If primary model unavailable, can automatically failover to alternative models
- **Unified API**: OpenAI-compatible API format simplifies integration
- **Rate Limits**: Better rate limit handling across multiple providers

**Alternatives Considered**:

| Approach | Pros | Cons | Why Rejected |
|----------|------|------|--------------|
| Direct Anthropic API | Native Claude access, official SDK | Single provider lock-in, no fallback options | Less flexible than OpenRouter multi-provider approach |
| OpenAI GPT-4 | Excellent performance, function calling | Higher cost, shorter context (128K), single provider | OpenRouter provides access to multiple providers including OpenAI |
| Local Model (Llama 2/3) | No API costs, full data control, offline | Requires GPU, slower inference, less accurate for complex tasks | Performance/accuracy trade-off not worth deployment complexity for MVP |
| spaCy + Rule-based NLP | Fast, deterministic, no API costs | Limited understanding of complex/ambiguous commands, high maintenance | Cannot handle natural language flexibility required by spec |

**Implementation Notes**:
- Default model: `anthropic/claude-3.5-sonnet` via OpenRouter
- API endpoint: `https://openrouter.ai/api/v1/chat/completions`
- System prompt defines browser action schema (navigate, click, type, extract)
- Use `tools` parameter for structured command output (OpenAI-compatible format)
- Implement confidence scoring via model's response confidence or explicit prompt asking "How confident are you (0-100%)?"
- Store API key in environment variable `OPENROUTER_API_KEY` per constitution security requirements
- Optional: Set `HTTP-Referer` and `X-Title` headers for OpenRouter credits/rankings

---

## Decision 3: Web Framework (Backend)

**Decision**: **FastAPI**

**Rationale**:
- **Modern Python**: Native async/await support → works well with Playwright (async) and LLM API calls
- **Performance**: Fastest Python web framework (Starlette + Pydantic)
- **Type Safety**: Pydantic models provide automatic validation and serialization → aligns with constitution's type hints requirement
- **OpenAPI**: Auto-generates OpenAPI/Swagger docs → satisfies contracts/ artifact generation
- **WebSocket Support**: Built-in WebSocket for real-time chat updates (FR-002: 3s response time)
- **Testing**: Excellent test client support for integration tests

**Alternatives Considered**:

| Framework | Pros | Cons | Why Rejected |
|-----------|------|------|--------------|
| Flask | Simple, mature, large ecosystem | Synchronous (requires threading for async), manual validation | Async support is clunky; missing built-in validation |
| Django | Full-featured, admin panel, ORM | Heavy for this use case, slower, opinionated structure | Overkill for MVP; performance overhead |
| Sanic | Async, fast | Smaller community, less mature than FastAPI | FastAPI has better documentation and OpenAPI generation |

**Implementation Notes**:
- Use Pydantic models for `ChatMessage`, `BrowserCommand`, `AgentResponse` schemas
- WebSocket endpoint for real-time chat (`/ws/chat/{session_id}`)
- REST endpoints for session management, timeout configuration (`POST /config/timeout`)
- Dependency injection for browser driver and LLM client (enables mocking per constitution extensibility)

---

## Decision 4: Frontend Framework

**Decision**: **React** with TypeScript + Vite

**Rationale**:
- **Ecosystem**: Largest component library ecosystem for accessible UI (Material-UI, Chakra UI, Radix UI)
- **Accessibility**: Excellent accessibility tooling (react-aria, @reach/ui) → supports WCAG 2.1 AA requirement
- **TypeScript**: Type safety for message contracts, reduces runtime errors
- **Vite**: Fast dev experience, optimized production builds → meets <2s load time (constitution section 5)
- **Testing**: React Testing Library + Jest for component tests
- **Community**: Largest community, extensive documentation and patterns

**Alternatives Considered**:

| Framework | Pros | Cons | Why Rejected |
|-----------|------|------|--------------|
| Vue 3 | Simpler learning curve, good performance | Smaller accessibility ecosystem | React has better a11y tooling |
| Svelte | Smallest bundle size, reactive | Smaller ecosystem, fewer UI libraries | Accessibility library support is limited |
| Vanilla JS | No framework overhead, full control | More manual work, harder to maintain, no built-in a11y | Development speed too slow; a11y harder to implement correctly |
| Angular | Full-featured, enterprise-ready | Heavy, opinionated, steeper learning curve | Overkill for chat UI |

**Implementation Notes**:
- Use `react-aria` or `@radix-ui/react` for accessible chat components
- Implement virtual scrolling for conversation history (SC-004: 100-200 messages)
- WebSocket client for real-time message updates
- Markdown rendering for agent responses (formatted information display)

---

## Decision 5: Deployment Target

**Decision**: **Web Application** (browser-based chat UI + backend service)

**Rationale**:
- **Accessibility**: Easier to achieve WCAG 2.1 AA in web browsers (screen readers, keyboard nav)
- **Cross-platform**: Works on any OS with modern browser
- **Deployment**: Simpler than distributing desktop app (just deploy backend + serve frontend)
- **Updates**: Instant updates without client distribution
- **Testing**: Standard web testing tools and CI/CD
- **Browser Control**: Backend can control system browser (Playwright runs locally or in container)

**Alternatives Considered**:

| Approach | Pros | Cons | Why Rejected |
|----------|------|------|--------------|
| Desktop App (Electron) | Bundled experience, offline-capable | Large bundle size (>100MB), harder accessibility, distribution complexity | Accessibility harder, unnecessary overhead |
| Desktop App (Tauri) | Smaller bundle, native performance | Less mature, Rust learning curve for backend | Development complexity not justified for MVP |
| Browser Extension | Integrated with browser | Limited UI space, extension approval process, security restrictions | Cannot meet chat UI requirements (FR-001) |

**Deployment Architecture**:
- Frontend: Static files served via CDN or backend
- Backend: FastAPI service running Playwright + LLM client
- Browser: Playwright launches/controls local browser instance
- Single-user model: One backend instance per user (can evolve to multi-user later)

---

## Decision 6: Accessibility Strategy

**Decision**: Use **@radix-ui/react** + **manual ARIA** + **axe-core testing**

**Rationale**:
- **Radix UI**: Unstyled, accessible components (Dialog, DropdownMenu, etc.) with WCAG 2.1 AA baked in
- **Chat-specific patterns**:
  - Chat log as ARIA live region (`role="log"` with `aria-live="polite"`) for screen reader announcements
  - Message list with `aria-label` for context
  - Input with clear labels and error announcements
  - Cancel button with keyboard shortcut (Escape) and visible focus states
- **Testing**:
  - axe-core for automated a11y checks in CI
  - Manual keyboard navigation testing (Tab, Enter, Escape)
  - Screen reader testing (NVDA/JAWS on Windows, VoiceOver on Mac)
- **Compliance Checklist**:
  - ✅ Keyboard navigation (Tab, Enter, Escape for cancel)
  - ✅ Focus management (focus input after message sent)
  - ✅ ARIA labels and roles (log, region, button)
  - ✅ Color contrast (4.5:1 for text, 3:1 for UI components)
  - ✅ Responsive text sizing (rem units, user can zoom)

**Implementation Notes**:
- Use Radix `Dialog` for clarification questions (modal accessibility)
- Implement focus trap for cancel button activation
- Announce agent responses to screen readers via live region
- Add "Skip to input" link for keyboard users
- Test with browser extensions: axe DevTools, WAVE

---

## Best Practices & Patterns

### Browser Automation Patterns
- **Page Object Model**: Encapsulate page interactions in classes (e.g., `SearchPage`, `FormPage`)
- **Retry Logic**: Implement exponential backoff for flaky element finding
- **Resource Cleanup**: Use context managers (`async with browser:`) to ensure browser closes
- **Error Categorization**: Distinguish timeout vs element-not-found vs network errors

### LLM Integration Patterns
- **Prompt Engineering**: Use few-shot examples for command parsing consistency
- **Streaming Responses**: Stream LLM output for perceived performance (show "Agent is thinking...")
- **Fallback**: If LLM unavailable, return friendly error with retry option
- **Rate Limiting**: Implement token bucket for API calls to avoid quota exhaustion

### Chat UX Patterns
- **Optimistic UI**: Show user message immediately, update with confirmation/error asynchronously
- **Loading States**: Show spinner/typing indicator during command execution
- **Error Recovery**: Inline retry button on failed messages
- **Context Preservation**: Highlight referenced previous messages when using conversation context

### Confidence Evaluation Pattern
```python
def evaluate_confidence(command: str, page_context: dict) -> float:
    """
    Returns confidence score 0.0-1.0 based on:
    - Command clarity (ambiguous verbs, missing targets)
    - Element match count (1 = high confidence, many = low)
    - Context availability (has prior info vs cold start)
    """
    # Use LLM to score or heuristic rules
    # Return < 0.9 triggers clarification flow (FR-014a)
```

---

## Technology Stack Summary

| Layer | Technology | Version |
|-------|-----------|---------|
| Language | Python | 3.11+ |
| Browser Automation | Playwright | 1.40+ |
| LLM Gateway | OpenRouter.ai | API v1 |
| Default LLM Model | Claude 3.5 Sonnet (via OpenRouter) | anthropic/claude-3.5-sonnet |
| Backend Framework | FastAPI | 0.104+ |
| Frontend Framework | React + TypeScript | 18.2+ |
| Build Tool | Vite | 5.0+ |
| Testing (Backend) | pytest + pytest-bdd | 7.4+ |
| Testing (Frontend) | React Testing Library + Vitest | 1.0+ |
| Accessibility | @radix-ui/react + axe-core | Latest |
| Database | SQLite (ephemeral) | 3.40+ |
| WebSocket | FastAPI WebSocket | Built-in |

---

## Open Questions for Implementation Phase

1. **Confidence Scoring Method**: Use LLM explicit scoring vs heuristic rules vs hybrid? → Recommend hybrid (fast heuristics + LLM for edge cases)
2. **Session Storage**: In-memory dict vs SQLite for conversation history? → Recommend SQLite for easier testing and potential future persistence
3. **Browser Instance**: Persistent browser vs launch per command? → Recommend persistent (per session) for performance
4. **Error Retry Strategy**: User-initiated vs automatic retry? → Recommend user-initiated per FR-009a (suggest alternatives)
5. **Frontend State Management**: Context API vs Zustand vs Redux? → Recommend Context API (simpler for MVP, no external library)

---

**Research Complete**: All NEEDS CLARIFICATION items resolved. Ready for Phase 1 design artifacts.
