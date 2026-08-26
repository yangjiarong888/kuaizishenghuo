"""Idempotent Wangwang merchant behavior and cart invariants."""

from __future__ import annotations

import html
import re
import time
from typing import Optional

from appium.webdriver.common.appiumby import AppiumBy

from commons.logger import setup_logger
from pages.business_search_spec import run_search_matrix
from pages.takeout_merchant_search_adapter import TakeoutMerchantSearchAdapter


logger = setup_logger(__name__)


class TakeoutMerchantBusinessMixin:
    def _merchant_source(self) -> str:
        try:
            return self.driver.page_source or ""
        except Exception:
            return ""

    def _takeout_merchant_favorite_state(self) -> Optional[bool]:
        source = html.unescape(self._merchant_source())
        if any(marker in source for marker in ("已收藏", "取消收藏")):
            return True
        if "收藏" in source:
            return False
        return None

    def _click_takeout_merchant_favorite(self) -> bool:
        return self._takeout_click_label(
            ("收藏", "已收藏"), y_max_ratio=0.32
        )

    def ensure_takeout_merchant_favorited(self) -> bool:
        state = self._takeout_merchant_favorite_state()
        if state is True:
            logger.info("旺旺商家已收藏，不重复点击")
            return True
        if state is None or not self._click_takeout_merchant_favorite():
            return False
        end = time.monotonic() + 5.0
        while time.monotonic() < end:
            if self._takeout_merchant_favorite_state() is True:
                return True
            if any(
                marker in self._merchant_source()
                for marker in ("收藏成功", "已加入收藏")
            ):
                return True
            time.sleep(0.25)
        return False

    def _open_takeout_merchant_im(self) -> bool:
        return self._takeout_click_label(
            ("联系商家", "聊天", "消息", "客服"), y_max_ratio=0.34
        )

    def _takeout_merchant_im_visible(self) -> bool:
        source = self._merchant_source()
        return any(marker in source for marker in ("输入消息", "表情", "相册"))

    def run_wangwang_merchant_im(self) -> bool:
        if not self._open_takeout_merchant_im() or not self._takeout_merchant_im_visible():
            return False
        if not self.send_takeout_im_bundle():
            return False
        try:
            self.driver.back()
        except Exception:
            return False
        return self._looks_inside_takeout_shop()

    def run_wangwang_search_matrix(self):
        return run_search_matrix(TakeoutMerchantSearchAdapter(self))

    def open_takeout_merchant_search(self) -> bool:
        return self._takeout_click_label(
            ("店内搜索", "搜索店内商品", "搜索"), y_max_ratio=0.34
        ) and self._takeout_search_input() is not None

    def search_takeout_merchant_keyword(self, keyword: str) -> bool:
        if not self.type_takeout_search_keyword(keyword):
            return False
        if not self.submit_takeout_search():
            return False
        return self.takeout_search_results_visible(keyword, timeout=8.0)

    def finish_takeout_merchant_search(self) -> bool:
        try:
            self.driver.back()
        except Exception:
            return False
        return self._looks_inside_takeout_shop()

    def _explicit_shop_cart_count(self) -> Optional[int]:
        source = html.unescape(self._merchant_source())
        labels = re.findall(r'(?:text|content-desc)="([^"]*)"', source)
        for label in labels:
            count = self._cart_item_count_from_label(label)
            if count is not None:
                return count
        return None

    def assert_cart_reuse_or_empty(self):
        count = self._explicit_shop_cart_count()
        if count is not None:
            return "reuse" if count > 0 else "empty"
        if self.shop_cart_has_purchasable_items():
            return "reuse"
        logger.error("购物车数量未知，禁止将未知状态当成空车加购")
        return False
