import pytest

from pages.business_search_spec import SearchProductSummary
from pages.mall_search_matrix_adapter import MallSearchMatrixAdapter
from scripts import run_shop_business as shop_script


pytestmark = pytest.mark.unit


class FakeMallPage:
    def __init__(self):
        self.events = []
        self.result_states = [True]

    def open_search_page(self):
        self.events.append("open")
        return True

    def _type_into_best_edit_text(self, keyword, *, allow_open_search=True):
        self.events.append(("type", keyword, allow_open_search))
        return True

    def _press_enter_or_search(self):
        self.events.append("submit")

    def _wait_page_contains_any(self, markers, timeout=8.0):
        self.events.append(("wait", tuple(markers), timeout))
        return True

    def _mall_search_results_visible(self, keyword, timeout=8.0):
        self.events.append(("results", keyword, timeout))
        return self.result_states.pop(0) if self.result_states else False

    def _click_first_text_or_desc(self, labels, **kwargs):
        self.events.append(("prefer", tuple(labels), kwargs))
        return True

    def open_first_visible_goods_detail(self):
        self.events.append("open-first")
        return True

    def read_visible_goods_summary(self, keyword):
        self.events.append(("read", keyword))
        return SearchProductSummary(keyword, "Coffee Beans", "₱299", "500g")

    def tap_top_back(self):
        self.events.append("back")
        return True

    def _search_page_visible(self):
        self.events.append("search-visible")
        return True

    def ensure_mall_tab(self):
        self.events.append("mall-tab")
        return True


def test_mall_adapter_opens_searches_reads_product_and_returns():
    page = FakeMallPage()
    adapter = MallSearchMatrixAdapter(page)

    assert adapter.source_name == "商城首页搜索"
    assert adapter.open_search()
    assert adapter.search_keyword("coffee")
    assert adapter.prefer_goods_results()
    assert adapter.open_first_goods()
    assert adapter.read_goods_summary("coffee") == SearchProductSummary(
        "coffee", "Coffee Beans", "₱299", "500g"
    )
    assert adapter.return_to_results()
    assert adapter.finish_search()
    assert page.events == [
        "open",
        ("type", "coffee", False),
        "submit",
        ("results", "coffee", 8.0),
        (
            "prefer",
            ("商品",),
            {
                "y_min_ratio": 0.08,
                "y_max_ratio": 0.45,
                "exact": True,
                "desc": "商品结果",
            },
        ),
        "open-first",
        ("read", "coffee"),
        "back",
        "search-visible",
        "back",
        "mall-tab",
    ]


def test_mall_adapter_accepts_product_grid_when_goods_tab_is_absent():
    page = FakeMallPage()
    page._click_first_text_or_desc = lambda *_args, **_kwargs: False
    adapter = MallSearchMatrixAdapter(page)

    assert adapter.prefer_goods_results() is True


def test_mall_adapter_stops_when_result_page_is_not_observed():
    page = FakeMallPage()
    page.result_states = [False, False]
    page._click_first_text_or_desc = lambda *_args, **_kwargs: False
    adapter = MallSearchMatrixAdapter(page)

    assert adapter.search_keyword("Keep") is False


def test_mall_adapter_clicks_matching_suggestion_when_submit_stays_on_list():
    page = FakeMallPage()
    page.result_states = [False, True]

    assert MallSearchMatrixAdapter(page).search_keyword("NVV床上") is True
    assert (
        "prefer",
        ("NVV床上",),
        {
            "y_min_ratio": 0.08,
            "y_max_ratio": 0.88,
            "exact": False,
            "desc": "搜索联想词",
        },
    ) in page.events


def test_shop_search_matrix_action_dispatches_shared_runner_and_closes_owned_session(
    monkeypatch,
):
    events = []
    fake_driver = object()

    class FakeManager:
        def get_driver(self, *, session_name):
            events.append(("get", session_name))
            return fake_driver

        def close_driver(self, session_name):
            events.append(("close", session_name))

    class FakePage:
        def __init__(self, driver):
            assert driver is fake_driver

    monkeypatch.setattr(shop_script, "DriverManager", FakeManager)
    monkeypatch.setattr(shop_script, "ShopBusinessPage", FakePage)
    monkeypatch.setattr(
        shop_script,
        "run_search_matrix",
        lambda adapter: events.append(("matrix", type(adapter).__name__)) or [],
        raising=False,
    )

    assert (
        shop_script.main(
            ["--action", "search_matrix", "--session", "mall-matrix", "--quit-driver"]
        )
        == 0
    )
    assert events == [
        ("get", "mall-matrix"),
        ("matrix", "MallSearchMatrixAdapter"),
        ("close", "mall-matrix"),
    ]
