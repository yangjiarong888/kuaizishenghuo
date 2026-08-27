import pytest

from pages.business_search_spec import SearchProductSummary
from pages.takeout_home_search_adapter import TakeoutHomeSearchAdapter
from pages.takeout_merchant_search_adapter import TakeoutMerchantSearchAdapter


pytestmark = pytest.mark.unit


class FakeTakeoutSearchPage:
    def __init__(self):
        self.events = []
        self.result_states = [True]

    def open_takeout_home_search(self):
        self.events.append("open-home")
        return True

    def browse_takeout_search_landing_business(self):
        self.events.append("browse-home-search-landing")
        return True

    def open_takeout_merchant_search(self):
        self.events.append("open-merchant")
        return True

    def type_takeout_search_keyword(self, keyword):
        self.events.append(("type", keyword))
        return True

    def submit_takeout_search(self):
        self.events.append("submit")
        return True

    def takeout_search_results_visible(self, keyword, timeout=8.0):
        self.events.append(("results", keyword, timeout))
        return self.result_states.pop(0) if self.result_states else False

    def click_takeout_search_suggestion(self, keyword):
        self.events.append(("suggestion", keyword))
        return True

    def search_takeout_merchant_keyword(self, keyword):
        self.events.append(("merchant-search", keyword))
        return True

    def prefer_takeout_goods_results(self):
        self.events.append("goods")
        return True

    def open_first_takeout_search_goods(self):
        self.events.append("open-first")
        return True

    def read_takeout_goods_summary(self, keyword):
        self.events.append(("read", keyword))
        return SearchProductSummary(keyword, "DUDAO charger", "₱100", "22.5W")

    def return_from_takeout_search_goods(self):
        self.events.append("back")
        return True

    def finish_takeout_home_search(self):
        self.events.append("finish-home")
        return True

    def finish_takeout_merchant_search(self):
        self.events.append("finish-merchant")
        return True


@pytest.mark.parametrize(
    "adapter_type,source",
    [
        (TakeoutHomeSearchAdapter, "外卖首页搜索"),
        (TakeoutMerchantSearchAdapter, "旺旺店内搜索"),
    ],
)
def test_takeout_adapter_runs_search_product_readback_and_return(adapter_type, source):
    page = FakeTakeoutSearchPage()
    adapter = adapter_type(page)
    assert adapter.source_name == source
    assert adapter.open_search()
    assert adapter.search_keyword("DUDAO22.5W超级快充迷")
    assert adapter.prefer_goods_results()
    assert adapter.open_first_goods()
    assert adapter.read_goods_summary("DUDAO22.5W超级快充迷").name == "DUDAO charger"
    assert adapter.return_to_results()
    assert adapter.finish_search()


def test_takeout_home_search_uses_suggestion_when_button_stays_on_list():
    page = FakeTakeoutSearchPage()
    page.result_states = [False, True]
    assert TakeoutHomeSearchAdapter(page).search_keyword("coffee")
    assert ("suggestion", "coffee") in page.events


def test_takeout_home_search_covers_landing_business_before_keyword_matrix():
    page = FakeTakeoutSearchPage()

    assert TakeoutHomeSearchAdapter(page).open_search() is True
    assert page.events == ["open-home", "browse-home-search-landing"]


def test_takeout_home_search_stops_when_landing_business_fails():
    page = FakeTakeoutSearchPage()
    page.browse_takeout_search_landing_business = lambda: False

    assert TakeoutHomeSearchAdapter(page).open_search() is False


def test_merchant_search_never_uses_external_suggestion_fallback():
    page = FakeTakeoutSearchPage()
    assert TakeoutMerchantSearchAdapter(page).search_keyword("coffee")
    assert page.events == [("merchant-search", "coffee")]
