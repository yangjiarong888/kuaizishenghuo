import pytest

from scripts import run_home_search_matrix as script


pytestmark = pytest.mark.unit


def test_home_search_matrix_command_owns_one_driver_lifecycle(monkeypatch):
    events = []
    fake_driver = object()

    class FakeManager:
        def get_driver(self, *, session_name):
            events.append(("get", session_name))
            return fake_driver

        def close_driver(self, session_name):
            events.append(("close", session_name))

    class FakeTester:
        def __init__(self, *, driver, session_name):
            assert driver is fake_driver
            events.append(("tester", session_name))

        def run_home_search_matrix(self):
            events.append("matrix")
            return ["summary"]

    monkeypatch.setattr(script, "DriverManager", FakeManager)
    monkeypatch.setattr(script, "ChopsticksTester", FakeTester)

    assert script.main(["--session", "home-matrix"]) == 0
    assert events == [
        ("get", "home-matrix"),
        ("tester", "home-matrix"),
        "matrix",
        ("close", "home-matrix"),
    ]
