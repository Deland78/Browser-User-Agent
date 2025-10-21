"""Unit tests for element finder with multi-strategy element location.

Following TDD methodology per tasks.md US1-006:
1. RED: Write failing tests
2. GREEN: Implement minimal code to pass
3. REFACTOR: Improve code while keeping tests green

Per FR-010: Agent MUST identify elements using multiple strategies
(text content, labels, position, element type)
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from browser_agent.browser.element_finder import ElementFinder, FindStrategy


class TestElementFinderTextStrategy:
    """Test finding elements by text content."""

    @pytest.fixture
    def mock_page(self):
        """Create mock Playwright page."""
        from unittest.mock import MagicMock
        # Use MagicMock since Playwright page methods like get_by_text() are sync
        page = MagicMock()
        return page

    @pytest.fixture
    def element_finder(self, mock_page):
        """Create ElementFinder instance."""
        return ElementFinder(page=mock_page)

    @pytest.mark.asyncio
    async def test_find_by_text_single_match(self, element_finder, mock_page):
        """Test finding element by exact text match."""
        # Mock Playwright locator - use MagicMock for better control
        from unittest.mock import MagicMock

        mock_locator = MagicMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_locator.nth.return_value = mock_locator  # nth() is sync, returns same locator
        mock_locator.get_attribute = AsyncMock(return_value="button")
        mock_locator.is_visible = AsyncMock(return_value=True)
        mock_locator.inner_text = AsyncMock(return_value="Login")

        mock_page.get_by_text.return_value = mock_locator  # get_by_text() is sync

        # Execute
        elements = await element_finder.find_elements(
            strategy=FindStrategy.TEXT,
            value="Login"
        )

        # Verify
        assert len(elements) == 1
        assert elements[0]["text"] == "Login"
        assert elements[0]["tag_name"] == "button"
        assert elements[0]["is_visible"] is True
        mock_page.get_by_text.assert_called_once_with("Login", exact=True)

    @pytest.mark.asyncio
    async def test_find_by_text_multiple_matches(self, element_finder, mock_page):
        """Test finding multiple elements with same text."""
        from unittest.mock import MagicMock

        mock_locator = MagicMock()
        mock_locator.count = AsyncMock(return_value=3)

        # Create mocks for each element
        mock_elements = []
        for i in range(3):
            elem = MagicMock()
            elem.get_attribute = AsyncMock(return_value="button")
            elem.is_visible = AsyncMock(return_value=True)
            elem.inner_text = AsyncMock(return_value="Submit")
            mock_elements.append(elem)

        mock_locator.nth.side_effect = mock_elements
        mock_page.get_by_text.return_value = mock_locator

        elements = await element_finder.find_elements(
            strategy=FindStrategy.TEXT,
            value="Submit"
        )

        assert len(elements) == 3
        assert all(e["text"] == "Submit" for e in elements)

    @pytest.mark.asyncio
    async def test_find_by_text_no_matches(self, element_finder, mock_page):
        """Test finding with text that doesn't exist."""
        mock_locator = AsyncMock()
        mock_locator.count.return_value = 0
        mock_page.get_by_text.return_value = mock_locator

        elements = await element_finder.find_elements(
            strategy=FindStrategy.TEXT,
            value="NonexistentText"
        )

        assert len(elements) == 0

    @pytest.mark.asyncio
    async def test_find_by_text_partial_match(self, element_finder, mock_page):
        """Test finding element by partial text match."""
        from unittest.mock import MagicMock

        mock_locator = MagicMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_locator.nth.return_value = mock_locator
        mock_locator.get_attribute = AsyncMock(return_value="button")
        mock_locator.is_visible = AsyncMock(return_value=True)
        mock_locator.inner_text = AsyncMock(return_value="Sign In to Account")

        mock_page.get_by_text.return_value = mock_locator

        elements = await element_finder.find_elements(
            strategy=FindStrategy.TEXT,
            value="Sign In",
            exact=False
        )

        assert len(elements) == 1
        mock_page.get_by_text.assert_called_once_with("Sign In", exact=False)


class TestElementFinderRoleStrategy:
    """Test finding elements by ARIA role."""

    @pytest.fixture
    def mock_page(self):
        """Create mock Playwright page."""
        from unittest.mock import MagicMock
        # Use MagicMock since Playwright page methods like get_by_text() are sync
        page = MagicMock()
        return page

    @pytest.fixture
    def element_finder(self, mock_page):
        """Create ElementFinder instance."""
        return ElementFinder(page=mock_page)

    @pytest.mark.asyncio
    async def test_find_by_role_button(self, element_finder, mock_page):
        """Test finding all buttons by role."""
        from unittest.mock import MagicMock

        mock_locator = MagicMock()
        mock_locator.count = AsyncMock(return_value=5)

        mock_elements = []
        for i in range(5):
            elem = MagicMock()
            elem.get_attribute = AsyncMock(return_value="button")
            elem.is_visible = AsyncMock(return_value=True)
            elem.inner_text = AsyncMock(return_value=f"Button {i+1}")
            mock_elements.append(elem)

        mock_locator.nth.side_effect = mock_elements
        mock_page.get_by_role.return_value = mock_locator

        elements = await element_finder.find_elements(
            strategy=FindStrategy.ROLE,
            value="button"
        )

        assert len(elements) == 5
        mock_page.get_by_role.assert_called_once_with("button")

    @pytest.mark.asyncio
    async def test_find_by_role_with_name(self, element_finder, mock_page):
        """Test finding button by role and accessible name."""
        from unittest.mock import MagicMock

        mock_locator = MagicMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_locator.nth.return_value = mock_locator
        mock_locator.get_attribute = AsyncMock(return_value="button")
        mock_locator.is_visible = AsyncMock(return_value=True)
        mock_locator.inner_text = AsyncMock(return_value="Submit Form")

        mock_page.get_by_role.return_value = mock_locator

        elements = await element_finder.find_elements(
            strategy=FindStrategy.ROLE,
            value="button",
            name="Submit Form"
        )

        assert len(elements) == 1
        assert elements[0]["text"] == "Submit Form"
        mock_page.get_by_role.assert_called_once_with("button", name="Submit Form")


class TestElementFinderLabelStrategy:
    """Test finding elements by ARIA label."""

    @pytest.fixture
    def mock_page(self):
        """Create mock Playwright page."""
        from unittest.mock import MagicMock
        # Use MagicMock since Playwright page methods like get_by_text() are sync
        page = MagicMock()
        return page

    @pytest.fixture
    def element_finder(self, mock_page):
        """Create ElementFinder instance."""
        return ElementFinder(page=mock_page)

    @pytest.mark.asyncio
    async def test_find_by_label(self, element_finder, mock_page):
        """Test finding input by label text."""
        from unittest.mock import MagicMock

        mock_locator = MagicMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_locator.nth.return_value = mock_locator
        mock_locator.get_attribute = AsyncMock(return_value="input")
        mock_locator.is_visible = AsyncMock(return_value=True)

        mock_page.get_by_label.return_value = mock_locator

        elements = await element_finder.find_elements(
            strategy=FindStrategy.LABEL,
            value="Email Address"
        )

        assert len(elements) == 1
        mock_page.get_by_label.assert_called_once_with("Email Address", exact=True)


class TestElementFinderSelectorStrategy:
    """Test finding elements by CSS selector."""

    @pytest.fixture
    def mock_page(self):
        """Create mock Playwright page."""
        from unittest.mock import MagicMock
        # Use MagicMock since Playwright page methods like get_by_text() are sync
        page = MagicMock()
        return page

    @pytest.fixture
    def element_finder(self, mock_page):
        """Create ElementFinder instance."""
        return ElementFinder(page=mock_page)

    @pytest.mark.asyncio
    async def test_find_by_selector(self, element_finder, mock_page):
        """Test finding element by CSS selector."""
        from unittest.mock import MagicMock

        mock_locator = MagicMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_locator.nth.return_value = mock_locator
        mock_locator.get_attribute = AsyncMock(return_value="button")
        mock_locator.is_visible = AsyncMock(return_value=True)
        mock_locator.inner_text = AsyncMock(return_value="Click Me")

        mock_page.locator.return_value = mock_locator

        elements = await element_finder.find_elements(
            strategy=FindStrategy.SELECTOR,
            value="#submit-button"
        )

        assert len(elements) == 1
        mock_page.locator.assert_called_once_with("#submit-button")

    @pytest.mark.asyncio
    async def test_find_by_selector_class(self, element_finder, mock_page):
        """Test finding elements by class name."""
        from unittest.mock import MagicMock

        mock_locator = MagicMock()
        mock_locator.count = AsyncMock(return_value=3)
        mock_elements = []
        for i in range(3):
            elem = MagicMock()
            elem.get_attribute = AsyncMock(return_value="div")
            elem.is_visible = AsyncMock(return_value=True)
            elem.inner_text = AsyncMock(return_value=f"Item {i+1}")
            mock_elements.append(elem)

        mock_locator.nth.side_effect = mock_elements
        mock_page.locator.return_value = mock_locator

        elements = await element_finder.find_elements(
            strategy=FindStrategy.SELECTOR,
            value=".product-card"
        )

        assert len(elements) == 3


class TestElementFinderCombinedStrategy:
    """Test finding elements with combined/fallback strategies."""

    @pytest.fixture
    def mock_page(self):
        """Create mock Playwright page."""
        from unittest.mock import MagicMock
        # Use MagicMock since Playwright page methods like get_by_text() are sync
        page = MagicMock()
        return page

    @pytest.fixture
    def element_finder(self, mock_page):
        """Create ElementFinder instance."""
        return ElementFinder(page=mock_page)

    @pytest.mark.asyncio
    async def test_combined_strategy_first_succeeds(self, element_finder, mock_page):
        """Test combined strategy stops when first strategy finds elements."""
        from unittest.mock import MagicMock

        # Mock first strategy (TEXT) succeeds
        mock_text_locator = MagicMock()
        mock_text_locator.count = AsyncMock(return_value=1)
        mock_text_locator.nth.return_value = mock_text_locator
        mock_text_locator.get_attribute = AsyncMock(return_value="button")
        mock_text_locator.is_visible = AsyncMock(return_value=True)
        mock_text_locator.inner_text = AsyncMock(return_value="Login")

        mock_page.get_by_text.return_value = mock_text_locator

        elements = await element_finder.find_elements(
            strategy=FindStrategy.COMBINED,
            value="Login",
            strategies=[FindStrategy.TEXT, FindStrategy.ROLE, FindStrategy.SELECTOR]
        )

        # Should find with first strategy and not try others
        assert len(elements) == 1
        mock_page.get_by_text.assert_called_once()
        mock_page.get_by_role.assert_not_called()

    @pytest.mark.asyncio
    async def test_combined_strategy_fallback(self, element_finder, mock_page):
        """Test combined strategy tries next when first fails."""
        from unittest.mock import MagicMock

        # Mock TEXT strategy finds nothing
        mock_text_locator = MagicMock()
        mock_text_locator.count = AsyncMock(return_value=0)

        # Mock ROLE strategy succeeds
        mock_role_locator = MagicMock()
        mock_role_locator.count = AsyncMock(return_value=1)
        mock_role_locator.nth.return_value = mock_role_locator
        mock_role_locator.get_attribute = AsyncMock(return_value="button")
        mock_role_locator.is_visible = AsyncMock(return_value=True)
        mock_role_locator.inner_text = AsyncMock(return_value="Submit")

        mock_page.get_by_text.return_value = mock_text_locator
        mock_page.get_by_role.return_value = mock_role_locator

        elements = await element_finder.find_elements(
            strategy=FindStrategy.COMBINED,
            value="Submit",
            role="button",
            strategies=[FindStrategy.TEXT, FindStrategy.ROLE]
        )

        assert len(elements) == 1
        # Both strategies should have been tried
        mock_page.get_by_text.assert_called_once()
        mock_page.get_by_role.assert_called_once()


class TestElementFinderVisibilityFiltering:
    """Test filtering by element visibility."""

    @pytest.fixture
    def mock_page(self):
        """Create mock Playwright page."""
        from unittest.mock import MagicMock
        # Use MagicMock since Playwright page methods like get_by_text() are sync
        page = MagicMock()
        return page

    @pytest.fixture
    def element_finder(self, mock_page):
        """Create ElementFinder instance."""
        return ElementFinder(page=mock_page)

    @pytest.mark.asyncio
    async def test_filter_visible_only(self, element_finder, mock_page):
        """Test that only visible elements are returned by default."""
        from unittest.mock import MagicMock

        mock_locator = MagicMock()
        mock_locator.count = AsyncMock(return_value=3)

        mock_elements = []
        for i in range(3):
            elem = MagicMock()
            elem.get_attribute = AsyncMock(return_value="button")
            elem.is_visible = AsyncMock(return_value=(i < 2))  # First 2 visible, last hidden
            elem.inner_text = AsyncMock(return_value=f"Button {i+1}")
            mock_elements.append(elem)

        mock_locator.nth.side_effect = mock_elements
        mock_page.get_by_role.return_value = mock_locator

        elements = await element_finder.find_elements(
            strategy=FindStrategy.ROLE,
            value="button",
            visible_only=True
        )

        # Should only return the 2 visible elements
        assert len(elements) == 2

    @pytest.mark.asyncio
    async def test_include_hidden_elements(self, element_finder, mock_page):
        """Test including hidden elements when visible_only=False."""
        mock_locator = AsyncMock()
        mock_locator.count.return_value = 3

        mock_elements = []
        for i in range(3):
            elem = AsyncMock()
            elem.get_attribute.return_value = "button"
            elem.is_visible.return_value = (i < 2)  # First 2 visible, last hidden
            elem.inner_text.return_value = f"Button {i+1}"
            mock_elements.append(elem)

        mock_locator.nth.side_effect = mock_elements
        mock_page.get_by_role.return_value = mock_locator

        elements = await element_finder.find_elements(
            strategy=FindStrategy.ROLE,
            value="button",
            visible_only=False
        )

        # Should return all 3 elements
        assert len(elements) == 3
