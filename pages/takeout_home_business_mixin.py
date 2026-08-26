"""Read-only and reversible business coverage for the takeout home page."""

from __future__ import annotations

import time
from typing import Optional, Sequence

from appium.webdriver.common.appiumby import AppiumBy

from commons.logger import setup_logger
from pages.business_search_spec import SearchProductSummary
from pages.takeout_locators import (
    TAKEOUT_CONGEE_CATEGORY_LABEL,
    TAKEOUT_DISCOUNT_LABEL,
    TAKEOUT_HOME_CART_LABELS,
    TAKEOUT_HOME_TOP_LABELS,
    TAKEOUT_SERVICE_LABELS,
    _PACKAGES,
)


logger = setup_logger(__name__)


class TakeoutHomeBusinessMixin:
    """Host supplies ``driver``, takeout navigation, and merchant-list waits."""

    _HOME_EXCLUDED_LABELS = {
        "外卖",
        "首页",
        "商城",
        "我的",
        TAKEOUT_DISCOUNT_LABEL,
        TAKEOUT_CONGEE_CATEGORY_LABEL,
    }

    def _takeout_source(self) -> str:
        try:
            return self.driver.page_source or ""
        except Exception:
            return ""

    def _takeout_click_label(
        self,
        labels: Sequence[str],
        *,
        exact: bool = False,
        y_min_ratio: float = 0.0,
        y_max_ratio: float = 1.0,
    ) -> bool:
        try:
            height = int(self.driver.get_window_size().get("height", 1920))
        except Exception:
            height = 1920
        for raw in labels:
            safe = raw.replace('"', "").replace("'", "")[:48]
            xpath = (
                f'//*[@text="{safe}" or @content-desc="{safe}"]'
                if exact
                else f'//*[contains(@text,"{safe}") or contains(@content-desc,"{safe}")]'
            )
            try:
                elements = self.driver.find_elements(AppiumBy.XPATH, xpath)
            except Exception:
                elements = []
            for element in elements:
                try:
                    if not element.is_displayed() or not element.is_enabled():
                        continue
                    y = int(element.location.get("y", 0))
                    if not int(height * y_min_ratio) <= y <= int(
                        height * y_max_ratio
                    ):
                        continue
                    target = self._nearest_clickable_ancestor(element)
                    target.click()
                    time.sleep(0.6)
                    return True
                except Exception:
                    continue
        return False

    def _takeout_merchant_snapshot(self) -> tuple[str, ...]:
        values: set[str] = set()
        for pkg in _PACKAGES:
            for suffix in ("tv_merchant_name", "tv_shop_name"):
                try:
                    elements = self.driver.find_elements(
                        AppiumBy.ID, f"{pkg}:id/{suffix}"
                    )
                except Exception:
                    elements = []
                for element in elements:
                    try:
                        if not element.is_displayed():
                            continue
                        value = (element.text or "").strip()
                        if value and value not in self._HOME_EXCLUDED_LABELS:
                            values.add(value)
                    except Exception:
                        continue
        return tuple(sorted(values))

    def _takeout_swipe_next_page(self) -> bool:
        try:
            self._swipe_merchant_list_once()
            return True
        except Exception:
            return False

    def browse_takeout_merchant_pages(self, min_pages: int = 3):
        if min_pages < 1 or not self.ensure_takeout_tab():
            return False
        snapshots: list[tuple[str, ...]] = []
        attempts = max(min_pages * 3, min_pages)
        for _ in range(attempts):
            snapshot = self._takeout_merchant_snapshot()
            if snapshot and snapshot not in snapshots:
                snapshots.append(snapshot)
                logger.info("外卖首页分页 %s merchants=%s", len(snapshots), snapshot)
                if len(snapshots) >= min_pages:
                    return snapshots
            if not self._takeout_swipe_next_page():
                break
        return False

    def _takeout_cart_page_visible(self) -> bool:
        source = self._takeout_source()
        return "购物车" in source and any(
            marker in source for marker in ("去结算", "清空购物车", "购物车为空", "结算")
        )

    def open_home_floating_cart_and_return(self) -> bool:
        if not self._takeout_click_label(
            TAKEOUT_HOME_CART_LABELS, y_min_ratio=0.12, y_max_ratio=0.88
        ):
            return False
        if not self._takeout_cart_page_visible():
            return False
        try:
            self.driver.back()
        except Exception:
            return False
        return bool(self.wait_merchant_list_present(timeout=6.0))

    def _takeout_category_grid_visible(self) -> bool:
        return TAKEOUT_CONGEE_CATEGORY_LABEL in self._takeout_source()

    def return_takeout_list_to_top(self) -> bool:
        if not self._takeout_click_label(
            TAKEOUT_HOME_TOP_LABELS, y_min_ratio=0.18, y_max_ratio=0.90
        ):
            return False
        end = time.monotonic() + 6.0
        while time.monotonic() < end:
            if self._takeout_category_grid_visible():
                return True
            time.sleep(0.25)
        return False

    def _takeout_filter_count(self) -> Optional[int]:
        source = self._takeout_source()
        for value in range(1, 10):
            if f'content-desc="{value}"' in source or f'text="{value}"' in source:
                return value
        return 0 if TAKEOUT_DISCOUNT_LABEL in source else None

    def _takeout_discount_results_visible(self) -> bool:
        source = self._takeout_source()
        return any(marker in source for marker in ("满减", "满₱", "减₱"))

    def verify_discount_filter_cycle(self) -> bool:
        if not self._takeout_click_label((TAKEOUT_DISCOUNT_LABEL,), exact=True):
            return False
        if self._takeout_filter_count() != 1:
            return False
        if not self._takeout_discount_results_visible():
            return False
        if not self._takeout_click_label((TAKEOUT_DISCOUNT_LABEL,), exact=True):
            return False
        return self._takeout_filter_count() in (0, None)

    def _takeout_category_results_visible(self) -> bool:
        source = self._takeout_source()
        return TAKEOUT_CONGEE_CATEGORY_LABEL in source and any(
            marker in source for marker in ("rv_merchant", "tv_merchant_name", "商家")
        )

    def open_congee_category_and_return(self) -> bool:
        if not self._takeout_click_label(
            (TAKEOUT_CONGEE_CATEGORY_LABEL,), exact=True, y_max_ratio=0.58
        ):
            return False
        if not self._takeout_category_results_visible():
            return False
        try:
            self.driver.back()
        except Exception:
            return False
        return bool(self.wait_merchant_list_present(timeout=6.0))

    def _takeout_im_conversation_visible(self) -> bool:
        source = self._takeout_source()
        return "24小时客服" in source and any(
            marker in source for marker in ("输入消息", "表情", "相册", "图片")
        )

    def open_takeout_home_service_im(self) -> bool:
        if not self._takeout_click_label(
            TAKEOUT_SERVICE_LABELS, y_max_ratio=0.28
        ):
            return False
        return self._takeout_im_conversation_visible()

    # External takeout-home search support. Merchant search has its own entry
    # and intentionally does not use the suggestion fallback.
    def open_takeout_home_search(self) -> bool:
        if not self.ensure_takeout_tab():
            return False
        return self._takeout_click_label(
            ("搜索商家或商品", "搜索商品", "搜索"), y_max_ratio=0.28
        ) and self._takeout_search_input() is not None

    def _takeout_search_input(self):
        for suffix in ("et_search", "edit_search", "search_edit", "input_search"):
            for pkg in _PACKAGES:
                try:
                    elements = self.driver.find_elements(
                        AppiumBy.ID, f"{pkg}:id/{suffix}"
                    )
                except Exception:
                    elements = []
                for element in elements:
                    try:
                        if element.is_displayed() and element.is_enabled():
                            return element
                    except Exception:
                        continue
        try:
            return next(
                (
                    el
                    for el in self.driver.find_elements(
                        AppiumBy.CLASS_NAME, "android.widget.EditText"
                    )
                    if el.is_displayed() and el.is_enabled()
                ),
                None,
            )
        except Exception:
            return None

    def type_takeout_search_keyword(self, keyword: str) -> bool:
        edit = self._takeout_search_input()
        if not edit:
            return False
        try:
            edit.click()
            edit.clear()
            edit.send_keys(keyword)
        except Exception:
            return False
        end = time.monotonic() + 3.0
        while time.monotonic() < end:
            try:
                if (edit.text or "").strip() == keyword:
                    return True
            except Exception:
                pass
            if keyword in self._takeout_source():
                return True
            time.sleep(0.2)
        return False

    def submit_takeout_search(self) -> bool:
        for label in ("搜索", "确定"):
            if self._takeout_click_label((label,), exact=True, y_max_ratio=0.28):
                return True
        try:
            self.driver.press_keycode(66)
            return True
        except Exception:
            return False

    def takeout_search_results_visible(
        self, keyword: str, timeout: float = 8.0
    ) -> bool:
        markers = (
            "vp_search_result",
            "rv_goods",
            "tv_good_name",
            "goods_name",
            "product_name",
            "商品结果",
        )
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            source = self._takeout_source()
            suggestions_only = "rv_search" in source and not any(
                marker in source for marker in markers
            )
            if keyword in source and not suggestions_only and any(
                marker in source for marker in markers
            ):
                return True
            time.sleep(0.25)
        return False

    def click_takeout_search_suggestion(self, keyword: str) -> bool:
        return self._takeout_click_label(
            (keyword,), y_min_ratio=0.08, y_max_ratio=0.88
        )

    def prefer_takeout_goods_results(self) -> bool:
        self._takeout_click_label(
            ("商品",), exact=True, y_min_ratio=0.08, y_max_ratio=0.45
        )
        return True

    def open_first_takeout_search_goods(self) -> bool:
        xpaths = (
            '//*[contains(@resource-id,"tv_good_name")]',
            '//*[contains(@resource-id,"goods_name") or contains(@resource-id,"product_name")]',
            '//*[@clickable="true" and contains(@content-desc,"₱")]',
        )
        for xpath in xpaths:
            try:
                elements = self.driver.find_elements(AppiumBy.XPATH, xpath)
            except Exception:
                elements = []
            for element in elements:
                try:
                    if not element.is_displayed() or not element.is_enabled():
                        continue
                    blob = " ".join(
                        str(element.get_attribute(name) or "")
                        for name in ("text", "content-desc", "resource-id")
                    )
                    if any(word in blob for word in ("加购", "加入购物车", "iv_add")):
                        continue
                    self._nearest_clickable_ancestor(element).click()
                    time.sleep(0.8)
                    return True
                except Exception:
                    continue
        return False

    def read_takeout_goods_summary(
        self, keyword: str
    ) -> Optional[SearchProductSummary]:
        values: list[str] = []
        try:
            elements = self.driver.find_elements(
                AppiumBy.XPATH,
                '//android.widget.TextView | //*[@content-desc!=""]',
            )
        except Exception:
            elements = []
        for element in elements:
            try:
                if not element.is_displayed():
                    continue
                value = (
                    (element.text or "").strip()
                    or (element.get_attribute("content-desc") or "").strip()
                )
                if value and value not in values:
                    values.append(value)
            except Exception:
                continue
        excluded = {"加入购物车", "立即购买", "客服", "分享", "购物车"}
        name = next(
            (value for value in values if value not in excluded and "₱" not in value),
            "",
        )
        price = next((value for value in values if "₱" in value), "")
        specification = next(
            (
                value
                for value in values
                if value not in excluded
                and value not in (name, price)
                and any(ch.isdigit() for ch in value)
                and "₱" not in value
            ),
            "",
        )
        return (
            SearchProductSummary(keyword, name, price, specification)
            if name
            else None
        )

    def return_from_takeout_search_goods(self) -> bool:
        try:
            self.driver.back()
        except Exception:
            return False
        return self._takeout_search_input() is not None

    def finish_takeout_home_search(self) -> bool:
        try:
            self.driver.back()
        except Exception:
            return False
        return bool(self.wait_merchant_list_present(timeout=6.0))
