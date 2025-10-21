"""Manual integration test for completed components.

Run with: python test_manual_integration.py

Tests the following completed components:
- CommandParser (US1-001)
- LLM Integration (US1-002)
- Navigation Actions (US1-003)
- Element Finder (US1-006)
- Click Actions (US1-004)
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from playwright.async_api import async_playwright

from browser_agent.agent.command_parser import CommandParser, NavigateAction, ClickAction
from browser_agent.agent.llm_client import OpenRouterClient
from browser_agent.browser.element_finder import ElementFinder, FindStrategy
from browser_agent.browser.actions import execute_navigate, execute_click_with_finder
from browser_agent.browser.context import ContextService
from browser_agent.config.settings import get_settings


async def test_navigation_flow():
    """Test navigation action end-to-end."""
    print("\n" + "=" * 70)
    print("TEST 1: Navigation Flow")
    print("=" * 70)

    context_service = ContextService()

    async with async_playwright() as p:
        # Launch browser
        print("   [*] Launching browser...")
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        # Create session context with unique ID
        import time
        session_id = f"test-nav-{int(time.time()*1000)}"
        await context_service.create_context(session_id=session_id)
        print(f"   [+] Created session: {session_id}")

        # Test: Navigate to example.com
        print("   [*] Navigating to https://example.com...")

        nav_action = NavigateAction(url="https://example.com")
        result = await execute_navigate(
            action=nav_action,
            page=page,
            session_id=session_id,
            context_service=context_service
        )

        if result['status'] == 'success':
            print(f"   [OK] Navigation successful!")
            print(f"      URL: {result['result_data']['final_url']}")
            print(f"      Title: {result['result_data']['page_title']}")
        else:
            print(f"   [FAIL] Navigation failed: {result['error_message']}")

        # Verify context was updated
        context = await context_service.get_context_by_session(session_id)
        print(f"      Context state: {context.page_state}")

        await asyncio.sleep(2)  # Let you see the page
        await browser.close()
        print("   [+] Browser closed")

    return result['status'] == 'success'


async def test_element_finder_strategies():
    """Test element finder with different strategies."""
    print("\n" + "=" * 70)
    print("[TEST] TEST 2: Element Finder Strategies")
    print("=" * 70)

    async with async_playwright() as p:
        print("   [*] Launching browser...")
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("   [*] Navigating to https://example.com...")
        await page.goto("https://example.com")

        element_finder = ElementFinder(page=page)

        # Test 1: Find by text
        print("\n   [SEARCH] Strategy 1: Find by TEXT")
        elements = await element_finder.find_elements(
            strategy=FindStrategy.TEXT,
            value="Example Domain",
            exact=False
        )

        print(f"   [OK] Found {len(elements)} element(s) with text 'Example Domain'")
        for elem in elements[:3]:
            print(f"      - {elem['tag_name']}: '{elem['text'][:50]}'")

        # Test 2: Find by role
        print("\n   [SEARCH] Strategy 2: Find by ROLE")
        links = await element_finder.find_elements(
            strategy=FindStrategy.ROLE,
            value="link"
        )

        print(f"   [OK] Found {len(links)} link(s) on page")
        for link in links[:5]:
            print(f"      - {link['text']}")

        # Test 3: Find by selector
        print("\n   [SEARCH] Strategy 3: Find by SELECTOR")
        headings = await element_finder.find_elements(
            strategy=FindStrategy.SELECTOR,
            value="h1"
        )

        print(f"   [OK] Found {len(headings)} h1 heading(s)")
        for h in headings:
            print(f"      - {h['text']}")

        # Test 4: Combined strategy
        print("\n   [SEARCH] Strategy 4: COMBINED (with fallback)")
        combined = await element_finder.find_elements(
            strategy=FindStrategy.COMBINED,
            value="More information",
            strategies=[FindStrategy.TEXT, FindStrategy.ROLE, FindStrategy.SELECTOR]
        )

        print(f"   [OK] Found {len(combined)} element(s) using combined strategy")

        await asyncio.sleep(2)
        await browser.close()
        print("   [+] Browser closed")

    return len(elements) > 0 and len(links) > 0


async def test_click_flow():
    """Test click action with element finder."""
    print("\n" + "=" * 70)
    print("[TEST] TEST 3: Click Action Flow")
    print("=" * 70)

    context_service = ContextService()

    async with async_playwright() as p:
        print("   [*] Launching browser...")
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        import time
        session_id = f"test-click-{int(time.time()*1000)}"
        await context_service.create_context(session_id=session_id)
        print(f"   [+] Created session: {session_id}")

        # Navigate to test page first
        print("   [*] Navigating to https://example.com...")
        await page.goto("https://example.com")

        # Create element finder
        element_finder = ElementFinder(page=page)

        # Test: Find and click "More information..." link
        print("   [*]  Attempting to click 'More information...' link")

        click_action = ClickAction(
            element_description="More information link",
            text="More information..."
        )

        result = await execute_click_with_finder(
            action=click_action,
            page=page,
            session_id=session_id,
            context_service=context_service,
            element_finder=element_finder
        )

        if result['status'] == 'success':
            print(f"   [OK] Click successful!")
            print(f"      Elements found: {result['result_data']['elements_found']}")
            print(f"      Clicked: {result['result_data']['element_description']}")
            print(f"      Current URL: {page.url}")
        else:
            print(f"   [FAIL] Click failed: {result['error_message']}")

        await asyncio.sleep(3)  # Let you see navigation
        await browser.close()
        print("   [+] Browser closed")

    return result['status'] == 'success'


async def test_command_parser_basic():
    """Test basic command parser without LLM."""
    print("\n" + "=" * 70)
    print("[TEST] TEST 4: Command Parser (Pattern Matching)")
    print("=" * 70)

    parser = CommandParser()  # No LLM client

    test_commands = [
        "Go to google.com",
        "Navigate to https://example.com",
        "Visit github.com",
    ]

    print("   [*] Testing pattern-based parsing...")

    for cmd in test_commands:
        result = parser.parse(cmd, [], None)
        print(f"\n   Input: '{cmd}'")
        print(f"   [OK] Intent: {result.intent}")
        print(f"      Actions: {len(result.actions)} action(s)")
        print(f"      Confidence: {result.confidence_score:.1%}")

        if result.actions:
            action = result.actions[0]
            print(f"      Action type: {type(action).__name__}")
            if hasattr(action, 'url'):
                print(f"      URL: {action.url}")

    return True


async def test_llm_command_parsing():
    """Test LLM-powered command parsing."""
    print("\n" + "=" * 70)
    print("[TEST] TEST 5: LLM-Powered Command Parsing")
    print("=" * 70)

    settings = get_settings()

    if not settings.openrouter_api_key or settings.openrouter_api_key == "your-api-key-here":
        print("   [WARN]  SKIPPED: No OpenRouter API key configured")
        print("      Set OPENROUTER_API_KEY environment variable to test LLM parsing")
        return None

    # Create LLM client
    print("   [*] Creating LLM client...")
    llm_client = OpenRouterClient(
        api_key=settings.openrouter_api_key,
        model=settings.openrouter_model
    )

    # Create parser with LLM
    parser = CommandParser(llm_client=llm_client)

    # Test parsing natural language
    test_commands = [
        "Please navigate to google.com",
        "I want to click the login button",
        "Take me to https://github.com",
    ]

    print("   [*] Testing LLM-powered parsing...")

    success_count = 0
    for cmd in test_commands:
        try:
            result = await parser.parse_async(cmd, [], None)
            print(f"\n   Input: '{cmd}'")
            print(f"   [OK] Intent: {result.intent}")
            print(f"      Actions: {len(result.actions)} action(s)")
            print(f"      Confidence: {result.confidence_score:.1%}")

            for i, action in enumerate(result.actions):
                print(f"      Action {i+1}: {type(action).__name__}")
                if hasattr(action, 'url'):
                    print(f"         URL: {action.url}")
                if hasattr(action, 'element_description'):
                    print(f"         Element: {action.element_description}")

            success_count += 1

        except Exception as e:
            print(f"   [FAIL] Error parsing '{cmd}': {e}")

    return success_count > 0


async def main():
    """Run all integration tests."""
    print("\n" + "=" * 70)
    print("[*] Browser Agent - Manual Integration Tests")
    print("=" * 70)
    print("\nTesting completed components:")
    print("  [+] US1-001: CommandParser foundation")
    print("  [+] US1-002: LLM integration")
    print("  [+] US1-003: Navigation actions")
    print("  [+] US1-004: Click actions")
    print("  [+] US1-006: Multi-strategy element finder")

    results = {}

    try:
        # Test 1: Navigation
        results['navigation'] = await test_navigation_flow()

        # Test 2: Element finder
        results['element_finder'] = await test_element_finder_strategies()

        # Test 3: Click actions
        results['click'] = await test_click_flow()

        # Test 4: Basic parser
        results['parser_basic'] = await test_command_parser_basic()

        # Test 5: LLM parsing (optional)
        results['parser_llm'] = await test_llm_command_parsing()

        # Summary
        print("\n" + "=" * 70)
        print("[SUMMARY] TEST SUMMARY")
        print("=" * 70)

        passed = sum(1 for v in results.values() if v is True)
        skipped = sum(1 for v in results.values() if v is None)
        failed = sum(1 for v in results.values() if v is False)
        total = len(results)

        for test_name, result in results.items():
            status = "[OK] PASS" if result is True else ("[WARN]  SKIP" if result is None else "[FAIL] FAIL")
            print(f"   {status}: {test_name}")

        print(f"\n   Total: {total} tests")
        print(f"   Passed: {passed}")
        print(f"   Skipped: {skipped}")
        print(f"   Failed: {failed}")

        if failed == 0:
            print("\n[SUCCESS] All integration tests passed!")
        else:
            print(f"\n[WARN]  {failed} test(s) failed")

        print("=" * 70)

    except KeyboardInterrupt:
        print("\n\n[WARN]  Tests interrupted by user")
    except Exception as e:
        print(f"\n[FAIL] Integration test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
