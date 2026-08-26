"""Store-local Wangwang search adapter (no external suggestion behavior)."""

from __future__ import annotations

from typing import Optional

from pages.business_search_spec import SearchProductSummary


class TakeoutMerchantSearchAdapter:
    source_name = "旺旺店内搜索"

    def __init__(self, page):
        self.page = page

    def open_search(self) -> bool:
        return bool(self.page.open_takeout_merchant_search())

    def search_keyword(self, keyword: str) -> bool:
        # Merchant-home search is deliberately independent: submit directly,
        # never apply the three-home-entry suggestion fallback.
        return bool(self.page.search_takeout_merchant_keyword(keyword))

    def prefer_goods_results(self) -> bool:
        return True

    def open_first_goods(self) -> bool:
        return bool(self.page.open_first_takeout_search_goods())

    def read_goods_summary(self, keyword: str) -> Optional[SearchProductSummary]:
        return self.page.read_takeout_goods_summary(keyword)

    def return_to_results(self) -> bool:
        return bool(self.page.return_from_takeout_search_goods())

    def finish_search(self) -> bool:
        return bool(self.page.finish_takeout_merchant_search())
