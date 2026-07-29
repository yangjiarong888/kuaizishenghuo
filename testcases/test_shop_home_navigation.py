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


class ClickFailingTab:
    def __init__(self, x):
        self.location = {"x": x, "y": 2200}
        self.size = {"width": 120, "height": 120}

    def get_attribute(self, name):
        return "true" if name == "clickable" else ""

    def click(self):
        raise RuntimeError("semantic click failed")


class StructuralFallbackDriver(EmptyHomeDriver):
    def __init__(self):
        super().__init__()
        self.execute_scripts = []
        self._tabs = [ClickFailingTab(x) for x in (100, 400, 700)]

    def find_elements(self, by, value):
        self.find_calls.append((by, value))
        return self._tabs if "ll_tab_content" in value else []

    def execute_script(self, name, args):
        self.execute_scripts.append((name, args))


def test_strict_structural_mall_tab_click_failure_never_uses_coordinates(monkeypatch):
    driver = StructuralFallbackDriver()
    page = ShopHomePage(driver)
    page._mall_tab_coordinate_fallback_disabled = True
    adb_attempts = []
    monkeypatch.setattr(shop_home_page.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        page,
        "_adb_tap",
        lambda *args, **kwargs: adb_attempts.append((args, kwargs)) or True,
    )

    assert page._tap_mall_bottom_tab_by_structure(settle=0) is False
    assert driver.execute_scripts == []
    assert adb_attempts == []


def test_default_structural_mall_tab_click_failure_keeps_coordinate_fallback(
    monkeypatch,
):
    driver = StructuralFallbackDriver()
    page = ShopHomePage(driver)
    monkeypatch.setattr(shop_home_page.time, "sleep", lambda _seconds: None)

    assert page._tap_mall_bottom_tab_by_structure(settle=0) is True
    assert driver.execute_scripts == [
        ("mobile: clickGesture", {"x": 760, "y": 2260})
    ]


class RecoveryFallbackDriver(EmptyHomeDriver):
    def __init__(self):
        super().__init__()
        self.execute_scripts = []

    def execute_script(self, name, args):
        self.execute_scripts.append((name, args))


def install_failed_recovery_boundaries(monkeypatch, page):
    monkeypatch.setattr(shop_home_page.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(page, "_is_mall_home_main_list_visible", lambda: False)
    monkeypatch.setattr(
        page,
        "tap_back_to_top_if_visible",
        lambda *, warn_when_missing=False: False,
    )
    monkeypatch.setattr(
        page,
        "uia2_scroll_mall_content_to_beginning",
        lambda: False,
    )
    monkeypatch.setattr(
        page,
        "mall_list_gesture_scroll_to_top",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(page, "tap_top_back", lambda: None)


def test_strict_recovery_never_bypasses_guard_with_coordinate_fallback(monkeypatch):
    driver = RecoveryFallbackDriver()
    page = ShopHomePage(driver)
    page._mall_tab_coordinate_fallback_disabled = True
    coordinate_attempts = []
    adb_attempts = []
    install_failed_recovery_boundaries(monkeypatch, page)
    real_coordinate_fallback = page._tap_mall_bottom_tab_by_coordinate

    def record_coordinate_fallback():
        coordinate_attempts.append("coordinate")
        return real_coordinate_fallback()

    monkeypatch.setattr(
        page,
        "_tap_mall_bottom_tab_by_coordinate",
        record_coordinate_fallback,
    )
    monkeypatch.setattr(
        page,
        "_adb_tap",
        lambda *args, **kwargs: adb_attempts.append((args, kwargs)) or False,
    )

    assert page.force_recover_mall_home_main_list(attempts=1) is False
    assert coordinate_attempts == []
    assert adb_attempts == []
    assert driver.execute_scripts == []


def test_default_recovery_keeps_coordinate_fallback_compatibility(monkeypatch):
    driver = RecoveryFallbackDriver()
    page = ShopHomePage(driver)
    coordinate_attempts = []
    install_failed_recovery_boundaries(monkeypatch, page)
    monkeypatch.setattr(
        page,
        "_tap_mall_bottom_tab_by_coordinate",
        lambda: coordinate_attempts.append("coordinate") or True,
    )

    assert page.force_recover_mall_home_main_list(attempts=1) is False
    assert coordinate_attempts == ["coordinate"]
    assert driver.execute_scripts == []
