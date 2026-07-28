import inspect

import pytest

from pages.shop_business_search_mixin import MallBusinessSearchMixin


pytestmark = pytest.mark.unit


SEARCH_METHODS = (
    "_safe_text",
    "_safe_desc",
    "_clean_xpath_text",
    "_page_contains_any",
    "_wait_page_contains_any",
    "_click_element_center",
    "_click_first_text_or_desc",
    "_type_into_best_edit_text",
    "_press_enter_or_search",
    "_swipe_fraction",
    "tap_search_entry",
    "_search_page_visible",
    "open_search_page",
    "_bounds_from_tag",
    "_tap_chip_below_title",
    "_tap_first_chip_below_title",
    "browse_search_landing",
    "tap_search_result_filters",
    "_tap_sort_control",
    "tap_secondary_category_filters",
    "browse_special_deals_products",
    "browse_search_results",
    "search_goods",
)


@pytest.mark.parametrize("name", SEARCH_METHODS)
def test_search_mixin_keeps_method_surface(name):
    assert callable(getattr(MallBusinessSearchMixin, name))


class SearchRecorder(MallBusinessSearchMixin):
    def __init__(self, *, open_ok=True, type_ok=True):
        self.open_ok = open_ok
        self.type_ok = type_ok
        self.events = []

    def open_search_page(self):
        self.events.append(("open",))
        return self.open_ok

    def browse_search_landing(self):
        self.events.append(("landing",))

    def _type_into_best_edit_text(self, text, *, allow_open_search=True):
        self.events.append(("type", text, allow_open_search))
        return self.type_ok

    def _press_enter_or_search(self):
        self.events.append(("submit",))

    def _wait_page_contains_any(self, markers, timeout=8.0):
        self.events.append(("wait", tuple(markers), timeout))
        return True

    def browse_search_results(self):
        self.events.append(("browse-results",))


def test_search_goods_keeps_bound_sequence(monkeypatch):
    from pages import shop_business_search_mixin

    monkeypatch.setattr(
        shop_business_search_mixin.time,
        "sleep",
        lambda _seconds: None,
    )
    page = SearchRecorder()

    assert inspect.ismethod(page.search_goods)
    assert page.search_goods(" 可乐 ") is True
    assert page.events == [
        ("open",),
        ("landing",),
        ("type", "可乐", True),
        ("submit",),
        (
            "wait",
            ("可乐", "综合", "销量", "价格", "商品", "搜索"),
            8.0,
        ),
        ("browse-results",),
    ]


def test_search_failure_stops_before_typing():
    page = SearchRecorder(open_ok=False)

    assert page.search_goods("可乐") is False
    assert page.events == [("open",)]


def test_empty_search_stops_before_page_navigation():
    page = SearchRecorder()

    assert page.search_goods("  ") is False
    assert page.events == []
