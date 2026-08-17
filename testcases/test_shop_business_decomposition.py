import inspect

import pytest

from pages.shop_business_search_mixin import MallBusinessSearchMixin
from pages.shop_business_detail_mixin import (
    MallBusinessDetailMixin,
    parse_price_text,
)


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


DETAIL_METHODS = (
    "_product_candidate_roots",
    "_tap_first_search_result_image_by_source_bounds",
    "_tap_first_search_grid_goods_by_source_bounds",
    "open_first_visible_goods_detail",
    "_category_goods_item_price",
    "_tap_category_goods_item",
    "_tap_first_category_goods_item",
    "open_goods_detail",
    "tap_detail_main_image",
    "swipe_detail_to_content",
    "tap_detail_activity_info_if_visible",
    "tap_view_more_goods_if_visible",
    "tap_detail_back_to_top",
    "browse_goods_detail",
    "open_and_browse_goods_detail",
)


@pytest.mark.parametrize("name", DETAIL_METHODS)
def test_detail_mixin_keeps_method_surface(name):
    assert callable(getattr(MallBusinessDetailMixin, name))


class DetailRecorder(MallBusinessDetailMixin):
    def __init__(
        self,
        *,
        already_detail=False,
        search_ok=True,
        open_ok=True,
    ):
        self.already_detail = already_detail
        self.search_ok = search_ok
        self.open_ok = open_ok
        self.events = []

    def _is_mall_product_detail_visible(self):
        self.events.append(("is-detail",))
        return self.already_detail

    def search_goods(self, keyword):
        self.events.append(("search", keyword))
        return self.search_ok

    def ensure_mall_tab(self):
        self.events.append(("mall-tab",))
        return True

    def open_first_visible_goods_detail(self):
        self.events.append(("open-first",))
        return self.open_ok


def test_open_goods_detail_searches_before_opening_product():
    page = DetailRecorder()

    assert page.open_goods_detail("可乐") is True
    assert page.events == [
        ("is-detail",),
        ("search", "可乐"),
        ("open-first",),
    ]


def test_open_goods_detail_stops_when_search_fails():
    page = DetailRecorder(search_ok=False)

    assert page.open_goods_detail("可乐") is False
    assert page.events == [
        ("is-detail",),
        ("search", "可乐"),
    ]


def test_open_goods_detail_returns_false_when_first_product_cannot_open():
    page = DetailRecorder(open_ok=False)

    assert page.open_goods_detail("可乐") is False
    assert page.events == [
        ("is-detail",),
        ("search", "可乐"),
        ("open-first",),
    ]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("₱33.00", 33.0),
        ("P 12.5", 12.5),
        ("20", None),
        ("", None),
    ],
)
def test_detail_price_parser_keeps_behavior(raw, expected):
    assert parse_price_text(raw) == expected


def test_facade_reexports_price_parser():
    from pages.shop_business_page import (
        parse_price_text as facade_parse_price_text,
    )

    assert facade_parse_price_text("₱33.00") == 33.0
