import pytest

from scripts import run_takeout_search_matrix as script


pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("scope", "adapter_name", "open_shop"),
    [
        ("home", "TakeoutHomeSearchAdapter", False),
        ("wangwang", "TakeoutMerchantSearchAdapter", True),
    ],
)
def test_takeout_search_cli_dispatches_one_adapter_and_closes_session(
    monkeypatch, scope, adapter_name, open_shop
):
    events = []
    driver = object()

    class FakeManager:
        def get_driver(self, *, session_name):
            events.append(("get", session_name))
            return driver

        def close_driver(self, session_name):
            events.append(("close", session_name))

    class FakePage:
        def __init__(self, received):
            assert received is driver

        def ensure_takeout_tab(self):
            events.append("home")
            return True

        def scroll_to_and_open_shop(self, name):
            events.append(("shop", name))
            return True

    monkeypatch.setattr(script, "DriverManager", FakeManager)
    monkeypatch.setattr(script, "TakeoutPageBase", FakePage)
    monkeypatch.setattr(
        script,
        "run_search_matrix",
        lambda adapter: events.append(("matrix", type(adapter).__name__)) or [],
    )

    assert script.main(["--scope", scope, "--session", "matrix"]) == 0
    assert ("matrix", adapter_name) in events
    assert (("shop", "旺旺超市 WWCS") in events) is open_shop
    assert events[-1] == ("close", "matrix")
