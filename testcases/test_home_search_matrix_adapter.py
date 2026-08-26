import time
from itertools import count

import pytest
from selenium.common.exceptions import StaleElementReferenceException

import pages.home_search_matrix_adapter as adapter_module
from pages.business_search_spec import SearchProductSummary
from pages.home_search_matrix_adapter import HomeSearchMatrixAdapter


pytestmark = pytest.mark.unit


class FakeElement:
    def __init__(self, events, name, *, text="", desc="", displayed=True):
        self.events = events
        self.name = name
        self.text = text
        self.desc = desc
        self.displayed = displayed
        self.location = {"x": 20, "y": 200}
        self.size = {"width": 180, "height": 80}

    def is_displayed(self):
        return self.displayed

    def is_enabled(self):
        return True

    def click(self):
        self.events.append(("click", self.name))

    def clear(self):
        self.events.append(("clear", self.name))

    def send_keys(self, value):
        self.text = value
        self.events.append(("type", self.name, value))

    def get_attribute(self, name):
        if name == "content-desc":
            return self.desc
        return ""


class FakeDriver:
    def __init__(self, events):
        self.events = events
        self.page_source = "com.bs.feifubao:id/vp_search_result 商城 综合 Keep"
        self.goods_tab = FakeElement(events, "mall-tab", text="商城")
        self.product = FakeElement(events, "product", text="Keep bottle")
        self.detail_texts = [
            FakeElement(events, "name", text="Keep bottle"),
            FakeElement(events, "price", text="₱99"),
            FakeElement(events, "spec", text="500ml"),
        ]

    def press_keycode(self, code):
        self.events.append(("key", code))

    def find_elements(self, by, value):
        if '@text="商城"' in value:
            return [self.goods_tab]
        if "tv_goods_title" in value:
            return [self.detail_texts[0]]
        if "tv_price" in value:
            return [self.detail_texts[1]]
        if "tv_select" in value:
            return [self.detail_texts[2]]
        if "goods_name" in value or "product" in value:
            return [self.product]
        if "android.widget.TextView" in value:
            return self.detail_texts
        return []

    def back(self):
        self.events.append("back")


class FakeHomeTester:
    SEARCH_ELEMENTS = [{"by": "xpath", "value": "home-search", "desc": "首页搜索"}]

    def __init__(self):
        self.events = []
        self.driver = FakeDriver(self.events)
        self.entry = FakeElement(self.events, "entry")
        self.input = FakeElement(self.events, "input")

    def ensure_homepage(self):
        self.events.append("ensure-home")
        return True

    def handle_new_user_popup_smart(self):
        self.events.append("dismiss-popup")

    def _find(self, by, value, timeout=None):
        self.events.append(("find", by, value, timeout))
        if value == "home-search":
            return self.entry
        if value == "com.bs.feifubao:id/et_search":
            return self.input
        return None

    def navigate_back_to_home_safe(self):
        self.events.append("home-safe")
        return True


def test_home_adapter_prioritizes_goods_reads_summary_and_finishes_home():
    tester = FakeHomeTester()
    adapter = HomeSearchMatrixAdapter(tester)

    assert adapter.source_name == "App首页搜索"
    assert adapter.open_search()
    assert adapter.search_keyword("Keep")
    assert adapter.prefer_goods_results()
    assert adapter.open_first_goods()
    assert adapter.read_goods_summary("Keep") == SearchProductSummary(
        "Keep", "Keep bottle", "₱99", "500ml"
    )
    assert adapter.return_to_results()
    assert adapter.finish_search()

    assert ("type", "input", "Keep") in tester.events
    assert ("key", 66) in tester.events
    assert ("click", "mall-tab") in tester.events
    assert ("click", "product") in tester.events
    assert tester.events[-2:] == ["back", "home-safe"]


def test_home_adapter_selects_mall_tab_instead_of_takeout_goods_card():
    tester = FakeHomeTester()
    mall_tab = FakeElement(tester.events, "mall-tab", text="商城")
    takeout_goods = FakeElement(tester.events, "takeout-goods", text="商品")

    def evidence_find_elements(_by, value):
        if '@text="商城"' in value:
            return [mall_tab]
        if '@text="商品"' in value:
            return [takeout_goods]
        return []

    tester.driver.find_elements = evidence_find_elements

    assert HomeSearchMatrixAdapter(tester).prefer_goods_results() is True
    assert tester.events == [("click", "mall-tab")]


def test_home_adapter_rejects_missing_search_input():
    tester = FakeHomeTester()
    original_find = tester._find
    tester._find = lambda by, value, timeout=None: (
        None
        if value == "com.bs.feifubao:id/et_search"
        else original_find(by, value, timeout)
    )
    adapter = HomeSearchMatrixAdapter(tester)

    assert adapter.open_search() is False


def test_home_adapter_opens_tv_good_name_through_clickable_ll_item_parent():
    tester = FakeHomeTester()
    parent = FakeElement(tester.events, "ll-item")

    class EvidenceGoodsName(FakeElement):
        def click(self):
            raise AssertionError("tv_good_name is not clickable on the device")

        def find_element(self, by, value):
            assert by == "xpath"
            assert value == "./ancestor::*[@clickable='true'][1]"
            return parent

    child = EvidenceGoodsName(tester.events, "tv-good-name", text="旺仔牛奶罐装")

    def evidence_find_elements(_by, value):
        if "tv_good_name" in value:
            return [child]
        return []

    tester.driver.find_elements = evidence_find_elements

    assert HomeSearchMatrixAdapter(tester).open_first_goods() is True
    assert tester.events == [("click", "ll-item")]


def test_home_adapter_waits_for_delayed_detail_title_instead_of_reading_early(
    monkeypatch,
):
    tester = FakeHomeTester()

    class DelayedDetailDriver(FakeDriver):
        def __init__(self, events):
            super().__init__(events)
            self.title_queries = 0

        def find_elements(self, _by, value):
            if "tv_goods_title" in value:
                self.title_queries += 1
                return [] if self.title_queries < 3 else [self.detail_texts[0]]
            if "tv_price" in value:
                return [] if self.title_queries < 3 else [self.detail_texts[1]]
            if "tv_select" in value:
                return [] if self.title_queries < 3 else [self.detail_texts[2]]
            if value == "//android.widget.TextView":
                self.title_queries += 1
                return [] if self.title_queries < 3 else self.detail_texts
            return []

    tester.driver = DelayedDetailDriver(tester.events)
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)

    assert HomeSearchMatrixAdapter(tester).read_goods_summary(
        "旺仔牛奶"
    ) == SearchProductSummary("旺仔牛奶", "Keep bottle", "₱99", "500ml")
    assert tester.driver.title_queries >= 3


def test_home_adapter_uses_close_button_when_edit_text_clear_keeps_old_keyword():
    tester = FakeHomeTester()

    class StickyInput(FakeElement):
        def clear(self):
            self.events.append(("clear-noop", self.name))

        def send_keys(self, value):
            self.text += value
            self.events.append(("type", self.name, value))

    sticky = StickyInput(tester.events, "input", text="旺仔牛奶")

    class CloseButton(FakeElement):
        def click(self):
            sticky.text = ""
            self.events.append(("click", self.name))

    close = CloseButton(tester.events, "close")

    def evidence_find(_by, value, timeout=None):
        tester.events.append(("find", _by, value, timeout))
        if value == "com.bs.feifubao:id/et_search":
            return sticky
        if value == "com.bs.feifubao:id/iv_close":
            return close
        return None

    tester._find = evidence_find
    tester.driver.page_source = "com.bs.feifubao:id/vp_search_result 水"

    assert HomeSearchMatrixAdapter(tester).search_keyword("水") is True
    assert sticky.text == "水"
    assert ("click", "close") in tester.events


def test_home_adapter_treats_showing_hint_text_as_empty_input():
    tester = FakeHomeTester()

    class HintInput(FakeElement):
        def __init__(self, events):
            super().__init__(
                events,
                "input",
                text="搜索外卖、商家或商品",
            )
            self.showing_hint = True

        def clear(self):
            self.events.append(("clear", self.name))

        def send_keys(self, value):
            self.text = value
            self.showing_hint = False
            self.events.append(("type", self.name, value))

        def get_attribute(self, name):
            if name == "showing-hint":
                return "true" if self.showing_hint else "false"
            return super().get_attribute(name)

    hint_input = HintInput(tester.events)
    tester._find = lambda _by, value, timeout=None: (
        hint_input if value == "com.bs.feifubao:id/et_search" else None
    )
    tester.driver.page_source = "com.bs.feifubao:id/vp_search_result 旺仔牛奶"

    assert HomeSearchMatrixAdapter(tester).search_keyword("旺仔牛奶") is True
    assert hint_input.text == "旺仔牛奶"


def test_home_adapter_clicks_visible_search_button_to_leave_suggestion_list():
    tester = FakeHomeTester()
    tester.driver.page_source = "com.bs.feifubao:id/rv_search 旺仔牛奶"

    class SearchButton(FakeElement):
        def click(self):
            self.events.append(("click", self.name))
            tester.driver.page_source = (
                "com.bs.feifubao:id/vp_search_result 旺仔牛奶"
            )

    search_button = SearchButton(tester.events, "search-button")
    original_find = tester._find

    def evidence_find(by, value, timeout=None):
        if value == "com.bs.feifubao:id/tv_search":
            return search_button
        return original_find(by, value, timeout)

    tester._find = evidence_find

    assert HomeSearchMatrixAdapter(tester).search_keyword("旺仔牛奶") is True
    assert ("click", "search-button") in tester.events


def test_home_adapter_submits_tv_right_through_clickable_parent(monkeypatch):
    tester = FakeHomeTester()
    tester.driver.page_source = "com.bs.feifubao:id/rv_search 旺仔牛奶"
    parent = FakeElement(tester.events, "right-parent")

    def click_parent():
        tester.events.append(("click", "right-parent"))
        tester.driver.page_source = "com.bs.feifubao:id/vp_search_result 旺仔牛奶"

    parent.click = click_parent

    class RightText(FakeElement):
        def find_element(self, by, value):
            assert by == "xpath"
            assert value == "./ancestor::*[@clickable='true'][1]"
            return parent

    right = RightText(tester.events, "tv-right", text="搜索")
    original_find = tester._find

    def evidence_find(by, value, timeout=None):
        if value == "com.bs.feifubao:id/tv_search":
            return None
        if value == "com.bs.feifubao:id/tv_right":
            return right
        return original_find(by, value, timeout)

    tester._find = evidence_find
    monkeypatch.setattr(adapter_module.time, "sleep", lambda _seconds: None)

    assert HomeSearchMatrixAdapter(tester).search_keyword("旺仔牛奶") is True
    assert ("click", "right-parent") in tester.events


def test_home_adapter_prefers_direct_layout_right_when_child_click_does_nothing(
    monkeypatch,
):
    tester = FakeHomeTester()
    tester.driver.page_source = "com.bs.feifubao:id/rv_search 旺仔牛奶"

    class LayoutRight(FakeElement):
        def click(self):
            self.events.append(("click", self.name))
            tester.driver.page_source = (
                "com.bs.feifubao:id/vp_search_result 旺仔牛奶"
            )

    layout_right = LayoutRight(tester.events, "layout-right")
    child = FakeElement(tester.events, "tv-right", text="搜索")
    original_find = tester._find

    def evidence_find(by, value, timeout=None):
        if value == "com.bs.feifubao:id/layout_right":
            return layout_right
        if value == "com.bs.feifubao:id/tv_search":
            return None
        if value == "com.bs.feifubao:id/tv_right":
            return child
        return original_find(by, value, timeout)

    tester._find = evidence_find
    monkeypatch.setattr(adapter_module.time, "sleep", lambda _seconds: None)

    assert HomeSearchMatrixAdapter(tester).search_keyword("旺仔牛奶") is True
    assert ("click", "layout-right") in tester.events


def test_home_adapter_waits_for_send_keys_value_to_arrive_before_submitting(
    monkeypatch,
):
    tester = FakeHomeTester()

    class DelayedInput:
        def __init__(self):
            self.sent = False
            self.reads_after_send = 0

        @property
        def text(self):
            if not self.sent:
                return ""
            self.reads_after_send += 1
            return "旺仔牛奶" if self.reads_after_send >= 3 else ""

        def get_attribute(self, name):
            return "false" if name == "showing-hint" else ""

        def click(self):
            pass

        def clear(self):
            pass

        def send_keys(self, value):
            assert value == "旺仔牛奶"
            self.sent = True

    delayed_input = DelayedInput()

    class SearchButton(FakeElement):
        def click(self):
            tester.driver.page_source = (
                "com.bs.feifubao:id/vp_search_result 旺仔牛奶"
            )

    search_button = SearchButton(tester.events, "search-button")

    def evidence_find(_by, value, timeout=None):
        if value == "com.bs.feifubao:id/et_search":
            return delayed_input
        if value == "com.bs.feifubao:id/layout_right":
            return search_button
        return None

    tester._find = evidence_find
    monkeypatch.setattr(adapter_module.time, "sleep", lambda _seconds: None)

    assert HomeSearchMatrixAdapter(tester).search_keyword("旺仔牛奶") is True
    assert delayed_input.reads_after_send >= 3


def test_home_adapter_uses_fresh_page_source_when_edit_element_text_is_stale(
    monkeypatch,
):
    tester = FakeHomeTester()

    class StaleInput:
        text = ""

        def get_attribute(self, name):
            return "false" if name == "showing-hint" else ""

        def click(self):
            pass

        def clear(self):
            pass

        def send_keys(self, value):
            tester.driver.page_source = (
                '<android.widget.EditText text="旺仔牛奶" '
                'resource-id="com.bs.feifubao:id/et_search" />'
                '<node resource-id="com.bs.feifubao:id/vp_search_result" />'
            )

    stale_input = StaleInput()
    search_button = FakeElement(tester.events, "search-button")

    def evidence_find(_by, value, timeout=None):
        if value == "com.bs.feifubao:id/et_search":
            return stale_input
        if value == "com.bs.feifubao:id/layout_right":
            return search_button
        return None

    tester._find = evidence_find
    monkeypatch.setattr(adapter_module.time, "sleep", lambda _seconds: None)

    assert HomeSearchMatrixAdapter(tester).search_keyword("旺仔牛奶") is True


def test_home_adapter_waits_for_close_button_to_clear_old_keyword(monkeypatch):
    tester = FakeHomeTester()

    class DelayedClearDriver(FakeDriver):
        def __init__(self, events):
            self.clearing = False
            self.source_reads = 0
            self._source = ""
            super().__init__(events)

        @property
        def page_source(self):
            if self.clearing:
                self.source_reads += 1
                if self.source_reads < 3:
                    return (
                        '<android.widget.EditText text="旺仔牛奶" '
                        'resource-id="com.bs.feifubao:id/et_search" '
                        'showing-hint="false" />'
                    )
                return (
                    '<android.widget.EditText text="搜索外卖、商家或商品" '
                    'resource-id="com.bs.feifubao:id/et_search" '
                    'showing-hint="true" />'
                )
            return self._source

        @page_source.setter
        def page_source(self, value):
            self._source = value

    driver = DelayedClearDriver(tester.events)
    tester.driver = driver
    old_input = FakeElement(tester.events, "old-input", text="旺仔牛奶")
    fresh_input = FakeElement(tester.events, "fresh-input", text="")

    class CloseButton(FakeElement):
        def click(self):
            driver.clearing = True
            self.events.append(("click", self.name))

    close = CloseButton(tester.events, "close")

    class SearchButton(FakeElement):
        def click(self):
            driver.clearing = False
            driver.page_source = "com.bs.feifubao:id/vp_search_result 水"

    submit = SearchButton(tester.events, "submit")

    def evidence_find(_by, value, timeout=None):
        if value == "com.bs.feifubao:id/et_search":
            return fresh_input if driver.source_reads >= 3 else old_input
        if value == "com.bs.feifubao:id/iv_close":
            return close
        if value == "com.bs.feifubao:id/layout_right":
            return submit
        return None

    tester._find = evidence_find
    monkeypatch.setattr(adapter_module.time, "sleep", lambda _seconds: None)

    assert HomeSearchMatrixAdapter(tester).search_keyword("水") is True
    assert driver.source_reads >= 3
    assert fresh_input.text == "水"


def test_home_adapter_clicks_matching_suggestion_when_search_button_stays_on_list(
    monkeypatch,
):
    tester = FakeHomeTester()
    tester.driver.page_source = "com.bs.feifubao:id/rv_search 旺仔牛奶"
    submit = FakeElement(tester.events, "submit-noop")
    suggestion_parent = FakeElement(tester.events, "suggestion-parent")

    def click_suggestion():
        tester.events.append(("click", "suggestion-parent"))
        tester.driver.page_source = "com.bs.feifubao:id/vp_search_result 旺仔牛奶"

    suggestion_parent.click = click_suggestion

    class SuggestionText(FakeElement):
        def find_element(self, by, value):
            assert by == "xpath"
            assert value == "./ancestor::*[@clickable='true'][1]"
            return suggestion_parent

    suggestion = SuggestionText(tester.events, "suggestion", text="旺仔牛奶罐装 245ml")
    original_find = tester._find

    def evidence_find(by, value, timeout=None):
        if value == "com.bs.feifubao:id/layout_right":
            return submit
        return original_find(by, value, timeout)

    tester._find = evidence_find
    tester.driver.find_elements = lambda _by, value: (
        [suggestion] if "tv_name" in value else []
    )
    ticks = count()
    monkeypatch.setattr(adapter_module.time, "monotonic", lambda: float(next(ticks)))
    monkeypatch.setattr(adapter_module.time, "sleep", lambda _seconds: None)

    assert HomeSearchMatrixAdapter(tester).search_keyword("旺仔牛奶") is True
    assert ("click", "suggestion-parent") in tester.events


def test_home_adapter_detects_old_keyword_from_source_when_element_cache_is_empty(
    monkeypatch,
):
    tester = FakeHomeTester()
    cleared = {"value": False}
    stale = FakeElement(tester.events, "stale-input", text="")
    fresh = FakeElement(tester.events, "fresh-input", text="")
    tester.driver.page_source = (
        '<android.widget.EditText text="旺仔牛奶" '
        'resource-id="com.bs.feifubao:id/et_search" '
        'showing-hint="false" />'
    )

    def reject_stale_send(_value):
        raise AssertionError("must clear the old source value before typing")

    stale.send_keys = reject_stale_send

    class CloseButton(FakeElement):
        def click(self):
            cleared["value"] = True
            tester.driver.page_source = (
                '<android.widget.EditText text="搜索外卖、商家或商品" '
                'resource-id="com.bs.feifubao:id/et_search" '
                'showing-hint="true" />'
            )

    close = CloseButton(tester.events, "close")

    class SubmitButton(FakeElement):
        def click(self):
            tester.driver.page_source = "com.bs.feifubao:id/vp_search_result 水"

    submit = SubmitButton(tester.events, "submit")

    def evidence_find(_by, value, timeout=None):
        if value == "com.bs.feifubao:id/et_search":
            return fresh if cleared["value"] else stale
        if value == "com.bs.feifubao:id/iv_close":
            return close
        if value == "com.bs.feifubao:id/layout_right":
            return submit
        return None

    tester._find = evidence_find
    monkeypatch.setattr(adapter_module.time, "sleep", lambda _seconds: None)

    assert HomeSearchMatrixAdapter(tester).search_keyword("水") is True
    assert cleared["value"] is True
    assert fresh.text == "水"


def test_home_adapter_relocates_input_once_after_stale_element(monkeypatch):
    tester = FakeHomeTester()
    lookups = {"input": 0}

    class StaleInput(FakeElement):
        def click(self):
            raise StaleElementReferenceException("rebuilt after returning from detail")

    stale = StaleInput(tester.events, "stale")
    fresh = FakeElement(tester.events, "fresh", text="")

    class SubmitButton(FakeElement):
        def click(self):
            tester.driver.page_source = "com.bs.feifubao:id/vp_search_result 水"

    submit = SubmitButton(tester.events, "submit")

    def evidence_find(_by, value, timeout=None):
        if value == "com.bs.feifubao:id/et_search":
            lookups["input"] += 1
            return stale if lookups["input"] == 1 else fresh
        if value == "com.bs.feifubao:id/layout_right":
            return submit
        return None

    tester._find = evidence_find
    tester.driver.page_source = (
        '<android.widget.EditText text="搜索外卖、商家或商品" '
        'resource-id="com.bs.feifubao:id/et_search" showing-hint="true" />'
    )
    monkeypatch.setattr(adapter_module.time, "sleep", lambda _seconds: None)

    assert HomeSearchMatrixAdapter(tester).search_keyword("水") is True
    assert lookups["input"] >= 2
    assert fresh.text == "水"
