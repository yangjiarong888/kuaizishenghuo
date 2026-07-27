from pathlib import Path
from types import SimpleNamespace

import pytest

import pages.Home as home_module


pytestmark = pytest.mark.unit


class FakeDriver:
    def __init__(self):
        self.quit_calls = 0

    def quit(self):
        self.quit_calls += 1


def test_home_injected_driver_is_not_created_or_closed(monkeypatch):
    fake = FakeDriver()

    def unexpected_manager():
        raise AssertionError("DriverManager must not run for injected driver")

    monkeypatch.setattr(home_module, "DriverManager", unexpected_manager, raising=False)

    tester = home_module.ChopsticksTester(driver=fake)

    assert tester.setup_driver() is True
    tester.cleanup()
    assert tester.driver is fake
    assert fake.quit_calls == 0


def test_home_owned_driver_uses_named_driver_manager_session(monkeypatch):
    fake = FakeDriver()
    calls = []

    class FakeManager:
        def get_driver(self, *, session_name):
            calls.append(("get", session_name))
            return fake

        def close_driver(self, session_name):
            calls.append(("close", session_name))

    manager = FakeManager()
    monkeypatch.setattr(home_module, "DriverManager", lambda: manager, raising=False)
    tester = home_module.ChopsticksTester(session_name="home-unit")

    assert tester.setup_driver() is True
    assert tester.setup_driver() is True
    tester.cleanup()

    assert calls == [("get", "home-unit"), ("close", "home-unit")]


def test_home_save_screenshot_delegates_to_sanitized_diagnostics(
    tmp_path, monkeypatch
):
    fake = FakeDriver()
    calls = []
    expected = tmp_path / "failure.png"

    def capture(driver, action, artifacts_dir):
        calls.append((driver, action, artifacts_dir))
        return SimpleNamespace(screenshot=expected)

    monkeypatch.setattr(home_module, "capture_failure", capture, raising=False)
    monkeypatch.setattr(home_module.AppConfig, "ARTIFACTS_DIR", str(tmp_path))
    tester = home_module.ChopsticksTester(driver=fake)

    assert tester.save_screenshot("homepage failed") == expected
    assert calls == [(fake, "homepage failed", str(tmp_path))]
