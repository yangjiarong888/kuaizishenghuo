import pytest

import commons.driver as driver_module
from commons.driver import DriverManager


pytestmark = pytest.mark.unit


class FakeDriver:
    def __init__(self):
        self.waits = []
        self.quit_calls = 0

    def implicitly_wait(self, value):
        self.waits.append(value)

    def quit(self):
        self.quit_calls += 1


@pytest.fixture(autouse=True)
def reset_manager():
    original = DriverManager._drivers
    DriverManager._drivers = {}
    yield
    DriverManager._drivers = original


def test_get_driver_caches_session_and_disables_implicit_wait(monkeypatch):
    fake = FakeDriver()
    monkeypatch.setattr(driver_module.webdriver, "Remote", lambda **kwargs: fake)
    monkeypatch.setattr(
        driver_module,
        "post_session_android_launch",
        lambda driver, config: "off",
    )

    manager = DriverManager()

    assert manager.get_driver("unit") is fake
    assert manager.get_driver("unit") is fake
    assert fake.waits == [0]


def test_failed_creation_is_not_cached(monkeypatch):
    def fail(**kwargs):
        raise RuntimeError("session failed")

    monkeypatch.setattr(driver_module.webdriver, "Remote", fail)

    with pytest.raises(RuntimeError, match="session failed"):
        DriverManager().get_driver("broken")

    assert "broken" not in DriverManager._drivers


def test_post_session_failure_quits_uncached_driver_to_restore_keyboard(monkeypatch):
    fake = FakeDriver()
    monkeypatch.setattr(driver_module.webdriver, "Remote", lambda **kwargs: fake)

    def fail_after_session(driver, config):
        raise RuntimeError("post-session failed")

    monkeypatch.setattr(driver_module, "post_session_android_launch", fail_after_session)

    with pytest.raises(RuntimeError, match="post-session failed"):
        DriverManager().get_driver("broken-after-session")

    assert fake.quit_calls == 1
    assert "broken-after-session" not in DriverManager._drivers


def test_close_driver_quits_once_and_clears_session():
    fake = FakeDriver()
    DriverManager._drivers["unit"] = fake
    manager = DriverManager()

    manager.close_driver("unit")
    manager.close_driver("unit")

    assert fake.quit_calls == 1
    assert DriverManager._drivers["unit"] is None
