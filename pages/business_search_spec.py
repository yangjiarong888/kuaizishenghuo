"""Locator-free contract for reusable business search matrices."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, Sequence


BUSINESS_SEARCH_KEYWORDS = (
    "旺仔牛奶",
    "水",
    "可乐",
    "泡面",
    "coffee",
    "NVV床上",
    "DUDAO22.5W超级快充迷",
    "Adidas",
    "Keep",
)


@dataclass(frozen=True)
class SearchProductSummary:
    keyword: str
    name: str
    price: str = ""
    specification: str = ""


class SearchMatrixAdapter(Protocol):
    source_name: str

    def open_search(self) -> bool: ...

    def search_keyword(self, keyword: str) -> bool: ...

    def prefer_goods_results(self) -> bool: ...

    def open_first_goods(self) -> bool: ...

    def read_goods_summary(self, keyword: str) -> Optional[SearchProductSummary]: ...

    def return_to_results(self) -> bool: ...

    def finish_search(self) -> bool: ...


class SearchMatrixError(AssertionError):
    def __init__(self, source: str, stage: str, index: int, keyword: str):
        super().__init__(
            f"{source} search failed stage={stage} index={index} keyword={keyword!r}"
        )
        self.source = source
        self.stage = stage
        self.index = index
        self.keyword = keyword


def run_search_matrix(
    adapter: SearchMatrixAdapter,
    keywords: Sequence[str] = BUSINESS_SEARCH_KEYWORDS,
) -> list[SearchProductSummary]:
    normalized = tuple(value.strip() for value in keywords)
    if any(not keyword for keyword in normalized):
        raise ValueError("search keyword must not be empty")
    if not adapter.open_search():
        raise SearchMatrixError(adapter.source_name, "open_search", 0, "")

    summaries = []
    for index, keyword in enumerate(normalized, 1):
        for stage, action in (
            ("search_keyword", lambda: adapter.search_keyword(keyword)),
            ("prefer_goods_results", adapter.prefer_goods_results),
            ("open_first_goods", adapter.open_first_goods),
        ):
            if not action():
                raise SearchMatrixError(adapter.source_name, stage, index, keyword)
        summary = adapter.read_goods_summary(keyword)
        if summary is None:
            raise SearchMatrixError(
                adapter.source_name, "read_goods_summary", index, keyword
            )
        summaries.append(summary)
        if not adapter.return_to_results():
            raise SearchMatrixError(
                adapter.source_name, "return_to_results", index, keyword
            )

    if not adapter.finish_search():
        last_keyword = normalized[-1] if normalized else ""
        raise SearchMatrixError(
            adapter.source_name, "finish_search", len(normalized), last_keyword
        )
    return summaries
