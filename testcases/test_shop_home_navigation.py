from types import SimpleNamespace

import pytest

from pages import shop_home_page
from pages.shop_home_page import ShopHomePage


pytestmark = pytest.mark.unit


class EmptyHomeDriver:
    """Minimal driver boundary for an unobstructed home screen."""

    current_package = "com.bs.feifubao"
    capabilities = {}
    page_source = "<hierarchy/>"

    def __init__(self):
        self.timeouts = SimpleNamespace(implicit_wait=0)
        self.find_calls = []

    def get_window_size(self):
        return {"width": 1080, "height": 2400}

    def implicitly_wait(self, seconds):
        self.timeouts.implicit_wait = seconds

    def find_elements(self, by, value):
        self.find_calls.append((by, value))
        return []


def test_popup_probe_stops_after_first_empty_sweep(monkeypatch):
    """An unobstructed home must not repeat expensive global XPath probes."""
    driver = EmptyHomeDriver()
    page = ShopHomePage(driver)
    monkeypatch.setattr(shop_home_page.time, "sleep", lambda _seconds: None)

    assert page.close_home_activity_popup_if_visible(attempts=8) is False
    assert driver.find_calls == []


def test_strict_mall_tab_navigation_fails_without_coordinate_fallback(monkeypatch):
    """An unrelated screen must not receive a coordinate mall-tab tap in strict mode."""
    driver = EmptyHomeDriver()
    page = ShopHomePage(driver)
    page._mall_tab_coordinate_fallback_disabled = True
    coordinate_attempts = []
    monkeypatch.setattr(shop_home_page.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        page,
        "_tap_mall_bottom_tab_by_coordinate",
        lambda: coordinate_attempts.append("coordinate") or True,
    )
    monkeypatch.setattr(
        page,
        "_tap_mall_bottom_tab_by_structure",
        lambda *, settle: False,
    )

    assert page.ensure_mall_tab(settle=0) is False
    assert coordinate_attempts == []
