# Speckit Constitution

## Purpose

This document defines the engineering contract for the Python-based AI Agent web application, covering browser automation, chat UX, and supporting services. Each section sets non-negotiable expectations for planning, building, testing, and operating the product.

---

## 1. Guiding Engineering Principles

- **Code Quality**: Follow PEP 8, enforce type hints on public APIs, and require Google-style docstrings for modules, classes, and functions. Organize imports in the order standard library → third-party → local with blank line separation.
- **Architecture**: Maintain clear separation among agent reasoning, browser automation utilities, chat interface, API/data services, and configuration layers. Each module keeps a single responsibility and exposes small, purpose-built interfaces.
- **Extensibility**: Prefer dependency injection for browser drivers, LLM clients, and other external integrations. Provide interface contracts that allow mocking and swapping implementations.
- **Reliability**: Use structured logging with consistent metadata, raise domain-specific exceptions, and degrade gracefully on browser issues with actionable messaging to the user.
- **Security & Compliance**: Store secrets in environment variables or managed vaults, validate external inputs, and ensure data access complies with privacy commitments.

---

## 2. Development Workflow

1. **Plan** features with explicit acceptance criteria, risk assessment, and UX considerations.
2. **Design** by annotating architecture impacts, interfaces, and dependency boundaries before coding.
3. **Test First** following strict Test-Driven Development (TDD) as defined in Section 3.1 below. Write failing tests before any production code.
4. **Implement** in small, reviewable increments with clear commit history.
5. **Verify** through automated test suites, linting, type checks, and manual smoke testing of high-risk paths.
6. **Review** using the checklist below; capture decisions in the PR description.
7. **Release** only after quality gates pass and documentation is updated.

**Code Review Checklist**

- [ ] Style, typing, and documentation align with project standards.
- [ ] Tests cover new and impacted logic with meaningful assertions.
- [ ] Error handling, logging, and user messaging are intentional.
- [ ] Performance, accessibility, and security implications are addressed.
- [ ] Feature flags, configs, and migrations include rollback guidance.

**Task Completion Requirement**

Apply Section 6 Delivery Quality Gates to each task before marking it complete in `tasks.md`. Compilation failures, test failures, or linting errors mean the task is NOT done, regardless of implementation progress. No partial credit for incomplete validation.

---

## 3. Testing Strategy

### 3.1 Test-Driven Development (TDD) - Mandatory

**All new production code MUST follow the RED-GREEN-REFACTOR cycle:**

**🔴 RED: Write failing test first**

- Write test describing desired behavior before ANY production code
- Run test and verify it FAILS with meaningful error
- If test passes without implementation, you haven't written a new test

**🟢 GREEN: Make test pass with minimal code**

- Write simplest implementation to make test pass
- No extra features, no premature optimization
- Run test and verify it PASSES

**🔵 REFACTOR: Improve while keeping tests green**

- Clean up duplication, improve names, optimize
- Run tests after each change to ensure they still pass

**Example TDD Flow:**

```python
# 🔴 RED: Write test first
def test_navigate_to_url():
    service = BrowserService()
    service.navigate("http://example.com")
    assert service.current_url == "http://example.com"
# Run: pytest → FAILS (BrowserService doesn't exist)

# 🟢 GREEN: Minimal implementation
class BrowserService:
    def navigate(self, url: str):
        self.current_url = url
# Run: pytest → PASSES

# 🔴 RED: Next test
def test_navigate_calls_playwright():
    mock_page = Mock()
    service = BrowserService(page=mock_page)
    service.navigate("http://example.com")
    mock_page.goto.assert_called_once()
# Run: pytest → FAILS

# 🟢 GREEN: Real implementation
class BrowserService:
    def __init__(self, page=None):
        self.page = page
    def navigate(self, url: str):
        self.page.goto(url)
        self.current_url = url
# Run: pytest → PASSES

# 🔵 REFACTOR: Add type hints, error handling
# Run: pytest → STILL PASSES
```

**TDD Verification (Required for Code Review):**

- Git commits show test-before-code pattern
- Tests existed and failed before implementation
- Can reproduce RED phase from git history

**TDD Violations = Automatic Rejection:**

- Production code committed before tests
- Tests written after implementation exists
- No evidence of failing tests (RED phase)

**Exceptions (must be marked):**

- Legacy code coverage (tag: `@pytest.mark.legacy_coverage`)
- Critical production hotfix (write failing test first, then fix)

### 3.2 Test Categories and Standards

- **Methodology**: Practice TDD for all new logic (Section 3.1) and BDD for user-facing behaviors using Given-When-Then language.
- **Categories**: Unit tests for pure logic, integration tests for module collaborations, E2E tests for workflows, regression/performance suites for critical paths.
- **Coverage Targets**: ≥80% overall, 100% for automation control flows. Explicit tests for edge cases and failure handling.
- **pytest Standards**: Use fixtures for setup, `@pytest.mark.parametrize` for scenarios, mocks for external systems. Tests must be deterministic and isolated.
- **Continuous Validation**: Fast suites on each commit, full suites in CI on PRs. Address flaky tests immediately.

```python
def test_agent_navigates_to_website():
    # Given: agent initialized with mocked browser
    # When: user requests navigation
    # Then: correct browser command issued
    assert result.status == "success"
```

---

## 4. User Experience & Accessibility

- **Responsiveness**: UI scales from mobile to desktop with consistent layout, typography, and spacing based on the design system.
- **Feedback**: Provide visible loading indicators, progress updates for long browser runs, and confirmation on success. Error messages must be actionable and human-readable.
- **Accessibility**: Achieve WCAG 2.1 AA compliance, including keyboard-only navigation, ARIA labeling, sufficient contrast, and focus management.
- **Interaction Patterns**: Keep navigation consistent, support undo/redo when feasible, and embed contextual help for complex flows.

---

## 5. Performance & Reliability

- **Frontend Targets**: Initial chat load < 2s, time-to-interactive < 3s, and optimized bundles with lazy loading for secondary features. Apply caching for static assets.
- **Backend Targets**: Core API responses return < 500ms excluding agent execution time, support concurrent sessions, and monitor resource utilization.
- **Browser Automation**: Enforce timeouts, reuse sessions when safe, and clean up browser instances to prevent leaks. Track metrics for navigation success rates and retries.
- **Observability**: Collect logs, metrics, and traces with alert thresholds. Investigate regressions promptly and document remediation actions.

---

## 6. Delivery Quality Gates

- All automated tests, linters, and type checks must pass.
- Code coverage and performance benchmarks must meet section targets.
- Security scans and dependency checks must be green or explicitly waived with rationale.
- Documentation (README, API references, runbooks) must reflect the shipped behavior.

---

## 7. Continuous Improvement & Governance

- **Review Cadence**: Run monthly architecture reviews, quarterly performance audits, biannual standards refreshes, and annual technology evaluations.
- **Metrics**: Track maintainability, coverage trends, production performance, UX satisfaction, and delivery velocity. Use data to shape backlog priorities.
- **Learning Culture**: Provide recurring training, host knowledge-sharing sessions, and encourage open-source/community participation.
- **Document Stewardship**: Revisit this constitution at least biannually. Proposed changes require team consensus and recorded decision notes.

---

_This constitution is a living document. Update it whenever practices evolve, and hold the team accountable to the commitments captured here._
