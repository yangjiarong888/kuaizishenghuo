import pytest

from pages.business_search_spec import (
    BUSINESS_SEARCH_KEYWORDS,
    SearchMatrixError,
    SearchProductSummary,
    run_search_matrix,
)


pytestmark = pytest.mark.unit


class RecordingAdapter:
    source_name = "recording"

    def __init__(self, fail_keyword=None):
        self.events = []
        self.fail_keyword = fail_keyword
        self.current = ""

    def open_search(self):
        self.events.append("open")
        return True

    def search_keyword(self, keyword):
        self.current = keyword
        self.events.append(("search", keyword))
        return keyword != self.fail_keyword

    def prefer_goods_results(self):
        self.events.append(("goods", self.current))
        return True

    def open_first_goods(self):
        self.events.append(("open_first", self.current))
        return True

    def read_goods_summary(self, keyword):
        self.events.append(("read", keyword))
        return SearchProductSummary(keyword, f"product-{keyword}", "₱1", "spec")

    def return_to_results(self):
        self.events.append(("back", self.current))
        return True

    def finish_search(self):
        self.events.append("finish")
        return True


def test_runner_preserves_fixed_keyword_order_and_exact_characters():
    adapter = RecordingAdapter()

    summaries = run_search_matrix(adapter)

    assert [item.keyword for item in summaries] == [
        "旺仔牛奶",
        "水",
        "可乐",
        "泡面",
        "coffee",
        "NVV床上",
        "DUDAO22.5W超级快充迷",
        "Adidas",
        "Keep",
    ]
    assert BUSINESS_SEARCH_KEYWORDS == tuple(item.keyword for item in summaries)
    assert adapter.events[0] == "open"
    assert adapter.events[-1] == "finish"


def test_runner_strips_only_keyword_edges():
    adapter = RecordingAdapter()

    summaries = run_search_matrix(adapter, ("  DUDAO22.5W超级快充迷  ",))

    assert summaries == [
        SearchProductSummary("DUDAO22.5W超级快充迷", "product-DUDAO22.5W超级快充迷", "₱1", "spec")
    ]


def test_runner_stops_at_first_failed_keyword_and_reports_stage():
    adapter = RecordingAdapter(fail_keyword="可乐")

    with pytest.raises(SearchMatrixError) as exc_info:
        run_search_matrix(adapter)

    assert exc_info.value.source == "recording"
    assert exc_info.value.keyword == "可乐"
    assert exc_info.value.stage == "search_keyword"
    assert exc_info.value.index == 3
    assert ("search", "泡面") not in adapter.events
    assert "finish" not in adapter.events


def test_runner_rejects_empty_normalized_keyword_before_opening_search():
    adapter = RecordingAdapter()

    with pytest.raises(ValueError, match="keyword"):
        run_search_matrix(adapter, ("  ",))

    assert adapter.events == []
