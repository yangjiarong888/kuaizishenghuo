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
