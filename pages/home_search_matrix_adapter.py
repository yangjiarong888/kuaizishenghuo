"""Shared search-matrix adapter for the application home search entrance."""

from __future__ import annotations

from typing import Optional

from appium.webdriver.common.appiumby import AppiumBy

from pages.business_search_spec import SearchProductSummary


class HomeSearchMatrixAdapter:
    source_name = "App首页搜索"
    SEARCH_INPUT_ID = "com.bs.feifubao:id/et_search"

    def __init__(self, tester):
        self.tester = tester
        self.driver = tester.driver

    def open_search(self) -> bool:
        self.tester.handle_new_user_popup_smart()
        if not self.tester.ensure_homepage():
            return False
        for selector in self.tester.SEARCH_ELEMENTS:
            element = self.tester._find(
                selector["by"], selector["value"], timeout=5
            )
            if not element:
                continue
            try:
                if element.is_displayed() and element.is_enabled():
                    element.click()
                    return bool(
                        self.tester._find(
                            AppiumBy.ID, self.SEARCH_INPUT_ID, timeout=6
                        )
                    )
            except Exception:
                continue
        return False

    def search_keyword(self, keyword: str) -> bool:
        element = self.tester._find(AppiumBy.ID, self.SEARCH_INPUT_ID, timeout=5)
        if not element:
            return False
        try:
            element.click()
            element.clear()
            element.send_keys(keyword)
            self.driver.press_keycode(66)
        except Exception:
            return False
        source = self.driver.page_source or ""
        return keyword in source or any(
            marker in source for marker in ("商品", "综合", "销量", "价格")
        )

    def prefer_goods_results(self) -> bool:
        try:
            elements = self.driver.find_elements(
                AppiumBy.XPATH, '//*[@text="商品" or @content-desc="商品"]'
            )
        except Exception:
            elements = []
        for element in elements:
            try:
                if element.is_displayed() and element.is_enabled():
                    element.click()
                    return True
            except Exception:
                continue
        return True

    def open_first_goods(self) -> bool:
        candidates = (
            '//*[contains(@resource-id,"goods_name") or '
            'contains(@resource-id,"product_name")]',
            '//*[contains(@resource-id,"iv_goods") or '
            'contains(@resource-id,"product_image")]',
        )
        for xpath in candidates:
            try:
                elements = self.driver.find_elements(AppiumBy.XPATH, xpath)
            except Exception:
                elements = []
            for element in elements:
                try:
                    if element.is_displayed() and element.is_enabled():
                        element.click()
                        return True
                except Exception:
                    continue
        return False

    def read_goods_summary(self, keyword: str) -> Optional[SearchProductSummary]:
        try:
            elements = self.driver.find_elements(
                AppiumBy.XPATH, "//android.widget.TextView"
            )
        except Exception:
            elements = []
        texts = []
        for element in elements:
            try:
                text = (element.text or "").strip()
                if element.is_displayed() and text and text not in texts:
                    texts.append(text)
            except Exception:
                continue
        excluded = {"加入购物车", "立即购买", "客服", "购物车", "分享"}
        name = next(
            (
                text
                for text in texts
                if text not in excluded
                and "₱" not in text
                and not text.startswith("P ")
            ),
            "",
        )
        price = next(
            (text for text in texts if "₱" in text or text.startswith("P ")),
            "",
        )
        specification = next(
            (
                text
                for text in texts
                if text not in excluded
                and text not in (name, price)
                and any(char.isdigit() for char in text)
            ),
            "",
        )
        if not name:
            return None
        return SearchProductSummary(keyword, name, price, specification)

    def return_to_results(self) -> bool:
        try:
            self.driver.back()
        except Exception:
            return False
        return bool(
            self.tester._find(AppiumBy.ID, self.SEARCH_INPUT_ID, timeout=5)
        )

    def finish_search(self) -> bool:
        try:
            self.driver.back()
        except Exception:
            pass
        return bool(self.tester.navigate_back_to_home_safe())
