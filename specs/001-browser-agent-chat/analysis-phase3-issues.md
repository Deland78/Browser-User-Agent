# Specification Analysis - Phase 3 Issues

**Feature**: 001-browser-agent-chat
**Analysis Date**: 2025-10-19
**Status**: DEFERRED TO PHASE 3

This document tracks specification issues identified during analysis that are deferred for resolution during Phase 3 implementation.

---

## Critical Issues (Address Before Phase 3 Completion)

### C1: Edge Case Coverage Gap
**Severity**: CRITICAL
**Location**: spec.md:103-115, tasks.md (all phases)
**Issue**: 16 edge cases listed as questions with ZERO task coverage. Critical scenarios like browser crashes, concurrent commands, CAPTCHA, authentication popups completely unaddressed.

**Action Required**:
- Review all 16 edge cases during Phase 3 planning
- For EACH edge case, either:
  1. Add explicit FR + task to handle it, OR
  2. Move to "Out of Scope" section with justification, OR
  3. Document design decision in plan.md

**Edge Cases to Address**:
1. Browser window closed during execution
2. Commands taking longer than 30 seconds
3. New command while previous executing
4. Dynamic content changes during execution
5. ✅ Element doesn't exist (covered by US1-013)
6. ✅ Info doesn't exist (covered by US2-004)
7. Hidden/collapsed content
8. Browser permissions interrupting automation
9. ⚠️ Scrolling to find element (implied by US1-006, needs explicit coverage)
10. Auth popups/CAPTCHA (marked out-of-scope but not documented)
11. ✅ Confidence hovering around 90% (covered by US5-002)
12. ✅ Repeated clarification cycles (covered by US5-006)
13. ✅ Clarification doesn't help (covered by US5-006)
14. Session timeout/inactivity
15. Browser memory leaks with long sessions
16. Network disconnection during page load

---

## High Priority Issues

### H1: Accessibility Coverage Insufficient
**Severity**: HIGH
**Location**: constitution.md:124, tasks.md:POLISH-009
**Issue**: WCAG 2.1 AA compliance is constitutionally mandatory but only single task (POLISH-009, effort: M) addresses accessibility - grossly insufficient for chat UI.

**Action Required**:
- Add accessibility tasks to EACH UI component phase during Phase 3:
  - `[US1-A11Y]` Test keyboard navigation in chat UI (Effort: S)
  - `[US2-A11Y]` Verify ARIA labels for extraction results (Effort: S)
  - `[US3-A11Y]` Screen reader testing for progress updates (Effort: S)
  - `[US5-A11Y]` Keyboard interaction with clarification options (Effort: S)
- Expand POLISH-009 to include automated axe-core testing + manual screen reader validation

### H3: Edge Cases Underspecified
**Severity**: HIGH
**Location**: spec.md:103-115
**Issue**: All 16 edge cases are unanswered questions ("What happens when...?") with no design decisions, requirements, or handling strategy.

**Action Required**:
- Convert each edge case to either:
  1. FR with handling requirement
  2. "Out of Scope" entry
  3. Design decision in plan.md
- Update tasks.md with edge case handling tasks

---

## Medium Priority Issues

### M2: Performance Testing Too Broad
**Severity**: MEDIUM
**Location**: tasks.md:TEST-004:825-832
**Issue**: Performance testing task covers 4+ success criteria (SC-002, SC-003, SC-007, SC-005) in single task (Effort: M). Too broad for measurable validation.

**Action Required**:
- Split TEST-004 into separate tasks:
  - `[TEST-004a]` Response time testing (SC-002: <3s simple, <10s complex)
  - `[TEST-004b]` Extraction speed testing (SC-003: <5s)
  - `[TEST-004c]` History load testing (SC-004: 100-200 pairs)
  - `[TEST-004d]` Accuracy benchmarking (SC-005: 90% element ID)

### M3: Security Testing Insufficient
**Severity**: MEDIUM
**Location**: constitution.md:142, tasks.md:TEST-005:834-841
**Issue**: Security testing (TEST-005) only covers API keys, gitignore, input validation, dependency scan. Constitution Section 6 requires comprehensive security - missing auth testing, CORS validation, XSS prevention.

**Action Required**:
- Expand TEST-005 or add security tasks:
  - CORS policy testing (verify origins)
  - Input sanitization verification (prevent injection)
  - Browser sandbox validation (ensure isolation)
  - XSS prevention testing (escape user content)

### M4: Manual Testing Protocol Missing
**Severity**: MEDIUM
**Location**: spec.md:SC-003a:168, tasks.md
**Issue**: SC-003a specifies "measured by manual testing with known-present data" but no tasks define manual test protocol or data sets.

**Action Required**:
- Add task or acceptance criteria:
  - Create test data sets with known-present information for extraction accuracy validation
  - Document manual testing protocol for SC-003a validation
  - Define sample pages for testing (e.g., product pages, contact pages, article pages)

### M6: Success Criteria Measurement Methodology
**Severity**: MEDIUM
**Location**: spec.md:SC-001:165, SC-005:170, SC-006b:173
**Issue**: Success criteria cite percentages (95%, 90%, 85%) without defining measurement methodology or sample size.

**Action Required**:
- Add measurement protocol to each SC:
  - "measured across N test scenarios"
  - Reference E2E test suites that validate these thresholds
  - Define minimum sample sizes for statistical validity

---

## Low Priority Issues (Cleanup)

### L1: Terminology Drift - Chat Interface
**Severity**: LOW
**Location**: spec.md:multiple, plan.md:multiple
**Issue**: Terminology drift: "chat window" (spec.md:10,64) vs "chat interface" (spec.md:121,199)

**Action Required**:
- Find-replace: "chat window" → "chat interface" throughout spec and plan

### L2: Terminology Drift - LLM vs NLP
**Severity**: LOW
**Location**: plan.md:17, CLAUDE.md
**Issue**: "LLM/NLP" used interchangeably but LLM (model) ≠ NLP (field). OpenRouter is LLM service, not general NLP.

**Action Required**:
- Use "LLM" consistently (OpenRouter provides LLM access)
- Remove "NLP" or clarify if NLP techniques are separate concern

---

## Resolution Timeline

| Issue | Priority | Target Phase | Estimated Effort |
|-------|----------|--------------|------------------|
| C1 | CRITICAL | Phase 3 Start | L (2-3 days) |
| H1 | HIGH | Phase 3 (US2-US5) | M (1 day) |
| H3 | HIGH | Phase 3 Start | M (1 day) |
| M2 | MEDIUM | Phase 8 (Testing) | S (half day) |
| M3 | MEDIUM | Phase 8 (Testing) | S (half day) |
| M4 | MEDIUM | Phase 3 (US2) | S (half day) |
| M6 | MEDIUM | Phase 8 (Testing) | XS (2 hours) |
| L1 | LOW | Phase 3 (anytime) | XS (1 hour) |
| L2 | LOW | Phase 3 (anytime) | XS (1 hour) |

---

## Recommended Workflow

### Before Phase 3 Starts
1. ✅ Resolve C1 (edge cases) - critical for implementation planning
2. ✅ Resolve H3 (edge case design decisions)

### During Phase 3 Implementation
1. Address H1 (accessibility) as each UI component is built
2. Address M4 (manual testing protocol) when implementing US2
3. Address L1, L2 (terminology cleanup) during any spec updates

### During Phase 8 Testing
1. Split M2 (performance testing) into granular tasks
2. Expand M3 (security testing) with additional coverage
3. Add M6 (measurement methodology) to success criteria validation

---

**Next Review**: Before starting Phase 3 implementation (after Phase 2 completion)
