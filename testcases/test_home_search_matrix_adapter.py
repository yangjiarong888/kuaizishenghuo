import pytest

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
        self.events.append(("type", self.name, value))

    def get_attribute(self, name):
        if name == "content-desc":
            return self.desc
        return ""


class FakeDriver:
    def __init__(self, events):
        self.events = events
        self.page_source = "商品 综合 Keep"
        self.goods_tab = FakeElement(events, "goods-tab", text="商品")
        self.product = FakeElement(events, "product", text="Keep bottle")
        self.detail_texts = [
            FakeElement(events, "name", text="Keep bottle"),
            FakeElement(events, "price", text="₱99"),
            FakeElement(events, "spec", text="500ml"),
        ]

    def press_keycode(self, code):
        self.events.append(("key", code))

    def find_elements(self, by, value):
        if '@text="商品"' in value:
            return [self.goods_tab]
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
    assert ("click", "goods-tab") in tester.events
    assert ("click", "product") in tester.events
    assert tester.events[-2:] == ["back", "home-safe"]


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
