"""Shared search-matrix adapter for the mall-home search entrance."""

from __future__ import annotations

from typing import Optional

from pages.business_search_spec import SearchProductSummary


class MallSearchMatrixAdapter:
    source_name = "商城首页搜索"

    def __init__(self, page):
        self.page = page

    def open_search(self) -> bool:
        return bool(self.page.open_search_page())

    def search_keyword(self, keyword: str) -> bool:
        if not self.page._type_into_best_edit_text(keyword, allow_open_search=False):
            return False
        self.page._press_enter_or_search()
        if self.page._mall_search_results_visible(keyword, timeout=8.0):
            return True
        if not self.page._click_first_text_or_desc(
            (keyword,),
            y_min_ratio=0.08,
            y_max_ratio=0.88,
            exact=False,
            desc="搜索联想词",
        ):
            return False
        return bool(self.page._mall_search_results_visible(keyword, timeout=8.0))

    def prefer_goods_results(self) -> bool:
        self.page._click_first_text_or_desc(
            ("商品",),
            y_min_ratio=0.08,
            y_max_ratio=0.45,
            exact=True,
            desc="商品结果",
        )
        return True

    def open_first_goods(self) -> bool:
        return bool(self.page.open_first_visible_goods_detail())

    def read_goods_summary(self, keyword: str) -> Optional[SearchProductSummary]:
        return self.page.read_visible_goods_summary(keyword)

    def return_to_results(self) -> bool:
        return bool(self.page.tap_top_back() and self.page._search_page_visible())

    def finish_search(self) -> bool:
        return bool(self.page.tap_top_back() and self.page.ensure_mall_tab())
