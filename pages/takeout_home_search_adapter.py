"""Shared nine-keyword matrix adapter for the external takeout-home search."""

from __future__ import annotations

from typing import Optional

from pages.business_search_spec import SearchProductSummary


class TakeoutHomeSearchAdapter:
    source_name = "外卖首页搜索"

    def __init__(self, page):
        self.page = page

    def open_search(self) -> bool:
        return bool(self.page.open_takeout_home_search())

    def search_keyword(self, keyword: str) -> bool:
        if not self.page.type_takeout_search_keyword(keyword):
            return False
        if not self.page.submit_takeout_search():
            return False
        if self.page.takeout_search_results_visible(keyword, timeout=8.0):
            return True
        if not self.page.click_takeout_search_suggestion(keyword):
            return False
        return bool(self.page.takeout_search_results_visible(keyword, timeout=8.0))

    def prefer_goods_results(self) -> bool:
        return bool(self.page.prefer_takeout_goods_results())

    def open_first_goods(self) -> bool:
        return bool(self.page.open_first_takeout_search_goods())

    def read_goods_summary(self, keyword: str) -> Optional[SearchProductSummary]:
        return self.page.read_takeout_goods_summary(keyword)

    def return_to_results(self) -> bool:
        return bool(self.page.return_from_takeout_search_goods())

    def finish_search(self) -> bool:
        return bool(self.page.finish_takeout_home_search())
