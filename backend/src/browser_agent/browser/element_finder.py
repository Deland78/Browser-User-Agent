"""Multi-strategy element finder for browser automation.

Per tasks.md US1-006 and FR-010:
- Supports multiple finding strategies: selector, text, aria_label, role
- Uses Playwright locators (get_by_text, get_by_label, get_by_role, locator)
- Returns list of PageElement dictionaries
- Supports combined strategy with fallback

Following TDD methodology per constitution Section 3.1.
"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FindStrategy(str, Enum):
    """Element finding strategies."""

    TEXT = "text"  # Find by visible text content
    ROLE = "role"  # Find by ARIA role
    LABEL = "label"  # Find by ARIA label or associated label text
    SELECTOR = "selector"  # Find by CSS selector
    COMBINED = "combined"  # Try multiple strategies in order


class ElementFinder:
    """Multi-strategy element finder using Playwright locators.

    Supports finding elements by:
    - Text content (exact or partial match)
    - ARIA role (with optional accessible name)
    - ARIA label / associated label
    - CSS selector
    - Combined strategy (try multiple approaches)

    Per FR-010: Identifies elements using multiple strategies
    (text content, labels, position, element type)
    """

    def __init__(self, page: Any):
        """Initialize element finder with Playwright page.

        Args:
            page: Playwright Page instance for element finding
        """
        self.page = page

    async def find_elements(
        self,
        strategy: FindStrategy,
        value: str,
        exact: bool = True,
        name: Optional[str] = None,
        role: Optional[str] = None,
        strategies: Optional[List[FindStrategy]] = None,
        visible_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """Find elements using specified strategy.

        Args:
            strategy: Finding strategy to use
            value: Search value (text, selector, label, or role name)
            exact: For text/label strategies, require exact match (default True)
            name: For role strategy, accessible name to match
            role: For combined strategy, role to use with ROLE strategy
            strategies: For combined strategy, list of strategies to try in order
            visible_only: If True, filter out hidden elements (default True)

        Returns:
            List of PageElement dictionaries with:
            - tag_name: HTML tag name
            - text: Visible text content
            - is_visible: Whether element is currently visible
            - (additional attributes as available)

        Per FR-010: Multiple identification strategies for web elements
        """
        logger.debug(f"Finding elements with strategy={strategy}, value={value}")

        if strategy == FindStrategy.COMBINED:
            return await self._find_combined(
                value=value,
                exact=exact,
                role=role,
                strategies=strategies or [FindStrategy.TEXT, FindStrategy.ROLE, FindStrategy.SELECTOR],
                visible_only=visible_only,
            )

        # Get locator based on strategy
        locator = self._get_locator(strategy, value, exact=exact, name=name)

        # Get count of matching elements
        count = await locator.count()
        logger.debug(f"Found {count} elements with {strategy} strategy")

        if count == 0:
            return []

        # Extract element information
        elements = []
        for i in range(count):
            elem_locator = locator.nth(i)
            elem_info = await self._extract_element_info(elem_locator)

            # Filter by visibility if requested
            if visible_only and not elem_info.get("is_visible", False):
                continue

            elements.append(elem_info)

        logger.info(f"Returning {len(elements)} elements (visible_only={visible_only})")
        return elements

    def _get_locator(
        self,
        strategy: FindStrategy,
        value: str,
        exact: bool = True,
        name: Optional[str] = None,
    ) -> Any:
        """Get Playwright locator for given strategy.

        Args:
            strategy: Finding strategy
            value: Search value
            exact: For text/label, require exact match
            name: For role, accessible name to match

        Returns:
            Playwright Locator instance
        """
        if strategy == FindStrategy.TEXT:
            return self.page.get_by_text(value, exact=exact)

        elif strategy == FindStrategy.ROLE:
            if name:
                return self.page.get_by_role(value, name=name)
            return self.page.get_by_role(value)

        elif strategy == FindStrategy.LABEL:
            return self.page.get_by_label(value, exact=exact)

        elif strategy == FindStrategy.SELECTOR:
            return self.page.locator(value)

        else:
            raise ValueError(f"Unsupported strategy: {strategy}")

    async def _extract_element_info(self, locator: Any) -> Dict[str, Any]:
        """Extract information from element locator.

        Args:
            locator: Playwright Locator for single element

        Returns:
            Dictionary with element properties
        """
        try:
            # Get tag name
            tag_name = await locator.get_attribute("tagName")
            if not tag_name:
                tag_name = await locator.evaluate("el => el.tagName")

            # Get text content
            try:
                text = await locator.inner_text()
            except Exception:
                text = ""

            # Check visibility
            try:
                is_visible = await locator.is_visible()
            except Exception:
                is_visible = False

            return {
                "tag_name": (tag_name or "").lower(),
                "text": text,
                "is_visible": is_visible,
            }

        except Exception as e:
            logger.warning(f"Error extracting element info: {e}")
            return {
                "tag_name": "unknown",
                "text": "",
                "is_visible": False,
            }

    async def _find_combined(
        self,
        value: str,
        exact: bool = True,
        role: Optional[str] = None,
        strategies: List[FindStrategy] = None,
        visible_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """Try multiple strategies in order until elements are found.

        Args:
            value: Search value
            exact: For text/label strategies, require exact match
            role: Role value for ROLE strategy
            strategies: List of strategies to try in order
            visible_only: Filter out hidden elements

        Returns:
            List of elements from first successful strategy
        """
        strategies = strategies or [FindStrategy.TEXT, FindStrategy.ROLE, FindStrategy.SELECTOR]

        logger.debug(f"Trying combined strategies: {strategies}")

        for strat in strategies:
            try:
                # Prepare strategy-specific arguments
                kwargs = {"strategy": strat, "value": value, "exact": exact, "visible_only": visible_only}

                # For ROLE strategy, use role parameter if provided
                if strat == FindStrategy.ROLE and role:
                    kwargs["value"] = role

                elements = await self.find_elements(**kwargs)

                if elements:
                    logger.info(f"Found {len(elements)} elements with {strat} strategy")
                    return elements

                logger.debug(f"Strategy {strat} found no elements, trying next")

            except Exception as e:
                logger.warning(f"Strategy {strat} failed: {e}, trying next")
                continue

        logger.info("No elements found with any combined strategy")
        return []
