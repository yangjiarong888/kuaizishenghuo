import pytest

from pages.takeout_home_business_mixin import TakeoutHomeBusinessMixin


pytestmark = pytest.mark.unit


class HomeRecorder(TakeoutHomeBusinessMixin):
    driver = object()

    def __init__(self, snapshots):
        self.snapshots = list(snapshots)
        self.index = 0

    def ensure_takeout_tab(self):
        return True

    def _takeout_merchant_snapshot(self):
        return self.snapshots[min(self.index, len(self.snapshots) - 1)]

    def _takeout_swipe_next_page(self):
        self.index += 1
        return True


def test_paging_requires_three_changed_merchant_sets():
    page = HomeRecorder(
        [("shop-a", "shop-b"), ("shop-c", "shop-d"), ("shop-e", "shop-f")]
    )
    assert page.browse_takeout_merchant_pages(min_pages=3) == [
        ("shop-a", "shop-b"),
        ("shop-c", "shop-d"),
        ("shop-e", "shop-f"),
    ]


def test_paging_rejects_unchanged_screen():
    assert HomeRecorder([("shop-a",)]).browse_takeout_merchant_pages(3) is False


class InteractionRecorder(TakeoutHomeBusinessMixin):
    driver = object()

    def __init__(self):
        self.events = []
        self.filter_count = 0

    def _takeout_click_label(self, labels, **kwargs):
        label = tuple(labels)[0]
        self.events.append(("click", label))
        if label == "满减活动":
            self.filter_count = 0 if self.filter_count else 1
        return True

    def _takeout_cart_page_visible(self):
        self.events.append("cart-visible")
        return True

    def wait_merchant_list_present(self, timeout=None):
        self.events.append(("merchant-list", timeout))
        return True

    def _takeout_category_grid_visible(self):
        return True

    def _takeout_filter_count(self):
        self.events.append("assert-count")
        return self.filter_count

    def _takeout_discount_results_visible(self):
        self.events.append("assert-labels")
        return True

    def _takeout_category_results_visible(self):
        self.events.append("category-results")
        return True

    def _takeout_im_conversation_visible(self):
        self.events.append("im-visible")
        return True


def test_discount_filter_is_enabled_asserted_and_disabled():
    page = InteractionRecorder()
    assert page.verify_discount_filter_cycle()
    assert page.events == [
        ("click", "满减活动"),
        "assert-count",
        "assert-labels",
        ("click", "满减活动"),
        "assert-count",
    ]


def test_cart_entry_and_return_uses_distinct_cart_control():
    page = InteractionRecorder()
    page.driver = type("D", (), {"back": lambda self: page.events.append("back")})()
    assert page.open_home_floating_cart_and_return()
    assert page.events == [
        ("click", "购物车"),
        "cart-visible",
        "back",
        ("merchant-list", 6.0),
    ]


def test_back_to_top_requires_category_grid():
    page = InteractionRecorder()
    assert page.return_takeout_list_to_top()
    assert page.events == [("click", "回到顶部")]


def test_congee_category_enters_results_and_returns():
    page = InteractionRecorder()
    page.driver = type("D", (), {"back": lambda self: page.events.append("back")})()
    assert page.open_congee_category_and_return()
    assert page.events == [
        ("click", "粥粉面饺"),
        "category-results",
        "back",
        ("merchant-list", 6.0),
    ]


def test_home_service_opens_conversation_without_sending():
    page = InteractionRecorder()
    assert page.open_takeout_home_service_im()
    assert page.events == [("click", "客服"), "im-visible"]


class DynamicSearchEntry:
    def __init__(self, events):
        self.events = events

    def is_displayed(self):
        return True

    def is_enabled(self):
        return True

    def click(self):
        self.events.append(("click-id", "ll_search"))


class DynamicSearchEntryDriver:
    def __init__(self, events):
        self.events = events
        self.entry = DynamicSearchEntry(events)

    def find_elements(self, by, value):
        self.events.append(("find", by, value))
        return [self.entry] if value.endswith(":id/ll_search") else []


class DynamicSearchEntryPage(TakeoutHomeBusinessMixin):
    def __init__(self):
        self.events = []
        self.driver = DynamicSearchEntryDriver(self.events)

    def ensure_takeout_tab(self):
        return True

    def _takeout_search_input(self):
        self.events.append("input-visible")
        return object()

    def _nearest_clickable_ancestor(self, element):
        return element

    def _takeout_click_label(self, labels, **kwargs):
        self.events.append(("text-fallback", tuple(labels)))
        return False


def test_takeout_home_search_opens_by_stable_id_when_placeholder_is_dynamic():
    page = DynamicSearchEntryPage()

    assert page.open_takeout_home_search() is True
    assert ("click-id", "ll_search") in page.events
    assert not any(event[0] == "text-fallback" for event in page.events if isinstance(event, tuple))


class SearchLandingRecorder(TakeoutHomeBusinessMixin):
    driver = object()

    def __init__(self, *, history_present=True, step_results=None):
        self.events = []
        self.history_present = history_present
        self.step_results = step_results or {}

    def _takeout_search_landing_visible(self):
        self.events.append("landing-visible")
        return self.step_results.get("landing", True)

    def _open_takeout_hot_search_destination_and_return(self):
        self.events.append("hot")
        return self.step_results.get("hot", True)

    def _open_takeout_ranking_merchant_and_return(self):
        self.events.append("ranking")
        return self.step_results.get("ranking", True)

    def _swipe_takeout_rankings_left_and_open_merchant(self):
        self.events.append("ranking-left")
        return self.step_results.get("ranking-left", True)

    def _takeout_search_history_present(self):
        self.events.append("history-present")
        return self.history_present

    def _open_takeout_history_result_and_return(self):
        self.events.append("history")
        return self.step_results.get("history", True)


def test_takeout_search_landing_covers_hot_rankings_swipe_and_history_in_order():
    page = SearchLandingRecorder()

    assert page.browse_takeout_search_landing_business() is True
    assert page.events == [
        "landing-visible",
        "hot",
        "ranking",
        "ranking-left",
        "history-present",
        "history",
    ]


def test_takeout_search_landing_skips_history_when_no_data_exists():
    page = SearchLandingRecorder(history_present=False)

    assert page.browse_takeout_search_landing_business() is True
    assert page.events == [
        "landing-visible",
        "hot",
        "ranking",
        "ranking-left",
        "history-present",
    ]


@pytest.mark.parametrize("failed_step", ("hot", "ranking", "ranking-left", "history"))
def test_takeout_search_landing_fails_at_first_invalid_destination(failed_step):
    page = SearchLandingRecorder(step_results={failed_step: False})

    assert page.browse_takeout_search_landing_business() is False


class ConfiguredDestinationRecorder(TakeoutHomeBusinessMixin):
    def __init__(self, source):
        self.source = source

    def _takeout_search_landing_visible(self):
        return False

    def _takeout_source(self):
        return self.source


def test_takeout_hot_destination_recognizes_native_activity_webview_shell():
    page = ConfiguredDestinationRecorder(
        "android.webkit.WebView com.bs.feifubao:id/rl_activity_title "
        "com.bs.feifubao:id/iv_back_white com.bs.feifubao:id/iv_share_white"
    )

    assert page._takeout_configured_destination_kind() == "activity"


def test_takeout_ranking_destination_recognizes_flutter_merchant_header():
    page = ConfiguredDestinationRecorder(
        'content-desc="销量 23824   营业时间10:55-03:00" '
        'content-desc="查看评价" content-desc="到店消费"'
    )

    assert page._takeout_configured_destination_kind() == "merchant"


class PositionedTextElement:
    def __init__(self, text, x, y, width=120, height=40, resource_id=""):
        self.text = text
        self.rect = {"x": x, "y": y, "width": width, "height": height}
        self.resource_id = resource_id

    def is_displayed(self):
        return True

    def is_enabled(self):
        return True

    def get_attribute(self, name):
        if name == "content-desc":
            return ""
        if name == "resource-id":
            return self.resource_id
        return None


class PositionedTextDriver:
    def __init__(self, elements):
        self.elements = elements

    def find_elements(self, by, value):
        return self.elements

    def get_window_size(self):
        return {"width": 1080, "height": 2400}


def test_takeout_visible_text_nodes_excludes_horizontal_carousel_nodes_offscreen():
    page = TakeoutHomeBusinessMixin()
    page.driver = PositionedTextDriver(
        [
            PositionedTextElement("left-offscreen", -300, 900, width=120),
            PositionedTextElement("partially-visible", -40, 900, width=120),
            PositionedTextElement("visible-ranking", 400, 900),
            PositionedTextElement("right-offscreen", 1200, 900),
        ]
    )

    assert [node[0] for node in page._takeout_visible_text_nodes()] == [
        "partially-visible",
        "visible-ranking",
    ]


def test_takeout_ranking_title_uses_stable_tv_title_for_dynamic_module_name():
    page = TakeoutHomeBusinessMixin()
    page.driver = PositionedTextDriver(
        [
            PositionedTextElement(
                "生鲜便利",
                392,
                880,
                width=232,
                height=115,
                resource_id="com.bs.feifubao:id/tv_title",
            )
        ]
    )

    assert [node[0] for node in page._takeout_ranking_titles()] == ["生鲜便利"]


class StickySearchEdit:
    def __init__(self, events, text="旺仔牛奶"):
        self.events = events
        self.text = text

    def click(self):
        self.events.append("edit-click")

    def clear(self):
        self.events.append("edit-clear-noop")

    def send_keys(self, keyword):
        self.events.append(("send", keyword))
        if self.text:
            raise RuntimeError("old suggestion keyword was not cleared")
        self.text = keyword


class SearchCloseButton:
    def __init__(self, events, edit):
        self.events = events
        self.edit = edit

    def is_displayed(self):
        return True

    def is_enabled(self):
        return True

    def click(self):
        self.events.append("close-click")
        self.edit.text = ""


class StickySearchDriver:
    def __init__(self, events, edit):
        self.close = SearchCloseButton(events, edit)

    def find_elements(self, by, value):
        return [self.close] if value.endswith(":id/iv_close") else []


class StickySearchKeywordPage(TakeoutHomeBusinessMixin):
    def __init__(self):
        self.events = []
        self.edit = StickySearchEdit(self.events)
        self.driver = StickySearchDriver(self.events, self.edit)

    def _takeout_search_input(self):
        return self.edit

    def _takeout_source(self):
        return f'text="{self.edit.text}" resource-id="com.bs.feifubao:id/et_search"'


def test_takeout_keyword_uses_close_button_when_edit_clear_is_ineffective():
    page = StickySearchKeywordPage()

    assert page.type_takeout_search_keyword("水") is True
    assert page.edit.text == "水"
    assert page.events.index("close-click") < page.events.index(("send", "水"))


class ChipNode:
    text = "旺仔牛奶"
    rect = {"x": 71, "y": 382, "width": 132, "height": 79}

    def __init__(self, events):
        self.events = events

    def get_attribute(self, name):
        return {
            "resource-id": "com.bs.feifubao:id/tv_hot",
            "clickable": "false",
            "content-desc": "",
        }.get(name, "")

    def click(self):
        self.events.append("text-click")


class ChipContainer:
    rect = {"x": 32, "y": 382, "width": 210, "height": 79}

    def __init__(self, events):
        self.events = events

    def is_displayed(self):
        return True

    def is_enabled(self):
        return True

    def click(self):
        self.events.append("container-click")


class ChipDriver:
    def __init__(self, events):
        self.container = ChipContainer(events)

    def find_elements(self, by, value):
        return [self.container] if value.endswith(":id/ll_hot") else []


class ChipClickPage(TakeoutHomeBusinessMixin):
    def __init__(self):
        self.events = []
        self.driver = ChipDriver(self.events)

    def _nearest_clickable_ancestor(self, element):
        return element


def test_takeout_hot_chip_clicks_containing_ll_hot_instead_of_text_node(monkeypatch):
    from pages import takeout_home_business_mixin

    monkeypatch.setattr(takeout_home_business_mixin.time, "sleep", lambda _s: None)
    page = ChipClickPage()
    text_node = ChipNode(page.events)
    node = ("旺仔牛奶", 71, 382, 132, 79, text_node)

    assert page._takeout_click_text_node(node, "外卖历史搜索词") is True
    assert page.events == ["container-click"]


class HistoryBackStackDriver:
    def __init__(self, events):
        self.events = events

    def back(self):
        self.events.append("back-to-home")


class HistoryBackStackPage(TakeoutHomeBusinessMixin):
    def __init__(self):
        self.events = []
        self.driver = HistoryBackStackDriver(self.events)

    def _takeout_search_landing_visible(self):
        self.events.append("landing-check")
        return False

    def is_on_takeout_merchant_home(self):
        self.events.append("home-check")
        return True

    def open_takeout_home_search(self):
        self.events.append("reopen-search")
        return True


def test_history_result_return_reopens_search_when_android_back_goes_home():
    page = HistoryBackStackPage()

    assert page._return_to_takeout_search_landing(reopen_from_home=True) is True
    assert page.events == [
        "back-to-home",
        "landing-check",
        "home-check",
        "reopen-search",
    ]


class ResultsActivityKeywordDriver(StickySearchDriver):
    def __init__(self, events, edit):
        super().__init__(events, edit)
        self.events = events
        self.current_activity = ".activity.food.TakeoutSearchActivity"

    def back(self):
        self.events.append("results-back")
        self.current_activity = ".activity.NewSearchActivity"


class ResultsActivityKeywordPage(StickySearchKeywordPage):
    def __init__(self):
        self.events = []
        self.edit = StickySearchEdit(self.events)
        self.driver = ResultsActivityKeywordDriver(self.events, self.edit)


def test_next_takeout_keyword_leaves_results_activity_before_clearing_old_text():
    page = ResultsActivityKeywordPage()

    assert page.type_takeout_search_keyword("水") is True
    assert page.events[0] == "results-back"
    assert page.driver.current_activity == ".activity.NewSearchActivity"
    assert page.edit.text == "水"


class ResultsBackHomeDriver(ResultsActivityKeywordDriver):
    def back(self):
        self.events.append("results-back-home")
        self.current_activity = ".activity.MainActivity"


class ResultsBackHomeKeywordPage(ResultsActivityKeywordPage):
    def __init__(self):
        self.events = []
        self.edit = StickySearchEdit(self.events, text="")
        self.driver = ResultsBackHomeDriver(self.events, self.edit)

    def _takeout_search_input(self):
        if self.driver.current_activity == ".activity.MainActivity":
            return None
        return self.edit

    def is_on_takeout_merchant_home(self):
        self.events.append("home-check")
        return self.driver.current_activity == ".activity.MainActivity"

    def open_takeout_home_search(self):
        self.events.append("reopen-search")
        self.driver.current_activity = ".activity.NewSearchActivity"
        return True


def test_next_takeout_keyword_reopens_search_when_results_back_goes_home(monkeypatch):
    from pages import takeout_home_business_mixin

    ticks = iter((0.0, 0.1, 10.0))
    monkeypatch.setattr(
        takeout_home_business_mixin.time,
        "monotonic",
        lambda: next(ticks, 10.0),
    )
    monkeypatch.setattr(takeout_home_business_mixin.time, "sleep", lambda _s: None)
    page = ResultsBackHomeKeywordPage()

    assert page.type_takeout_search_keyword("水") is True
    assert page.events[:3] == ["results-back-home", "home-check", "reopen-search"]
    assert page.edit.text == "水"


class FlutterGoodsSummaryDriver:
    page_source = (
        '<hierarchy><android.widget.ImageView '
        'content-desc="旺仔牛奶罐装 245ml &#10;旺仔牛奶，经典味道，好喝有营养&#10;₱60.00" '
        'clickable="true" /></hierarchy>'
    )

    def find_elements(self, by, value):
        return []


class DelayedFlutterGoodsSummaryPage(TakeoutHomeBusinessMixin):
    def __init__(self):
        self.sources = iter(
            (
                "<hierarchy />",
                FlutterGoodsSummaryDriver.page_source,
            )
        )
        self.driver = FlutterGoodsSummaryDriver()

    def _takeout_source(self):
        return next(self.sources, FlutterGoodsSummaryDriver.page_source)


def test_takeout_goods_summary_reads_keyword_product_from_flutter_content_desc():
    page = TakeoutHomeBusinessMixin()
    page.driver = FlutterGoodsSummaryDriver()

    summary = page.read_takeout_goods_summary("旺仔牛奶")

    assert summary is not None
    assert summary.name == "旺仔牛奶罐装 245ml"
    assert summary.price == "₱60.00"


def test_takeout_goods_summary_waits_for_delayed_flutter_product(monkeypatch):
    from pages import takeout_home_business_mixin

    ticks = iter((0.0, 0.1, 0.2))
    monkeypatch.setattr(
        takeout_home_business_mixin.time,
        "monotonic",
        lambda: next(ticks, 10.0),
    )
    monkeypatch.setattr(takeout_home_business_mixin.time, "sleep", lambda _s: None)
    page = DelayedFlutterGoodsSummaryPage()

    summary = page.read_takeout_goods_summary("旺仔牛奶")

    assert summary is not None
    assert summary.name == "旺仔牛奶罐装 245ml"
    assert summary.price == "₱60.00"
