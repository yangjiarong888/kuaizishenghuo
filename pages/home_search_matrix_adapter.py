"""Shared search-matrix adapter for the application home search entrance."""

from __future__ import annotations

import html
import re
import time
from typing import Optional

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import StaleElementReferenceException

from commons.logger import setup_logger
from pages.business_search_spec import SearchProductSummary


logger = setup_logger(__name__)


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
        entered = False
        for attempt in range(1, 3):
            try:
                entered = self._enter_keyword_once(keyword)
            except StaleElementReferenceException:
                logger.warning(
                    "App首页搜索输入框已重建，重新定位 keyword=%r attempt=%s/2",
                    keyword,
                    attempt,
                )
                continue
            except Exception as exc:
                logger.error(
                    "App首页搜索输入异常 keyword=%r error=%s",
                    keyword,
                    type(exc).__name__,
                )
                return False
            break
        if not entered:
            return False
        try:
            if not self._submit_search():
                return False
        except Exception as exc:
            logger.error(
                "App首页搜索提交异常 keyword=%r error=%s",
                keyword,
                type(exc).__name__,
            )
            return False
        if self._wait_for_result_page(keyword, timeout=5.0):
            return True
        if self._click_matching_suggestion(keyword) and self._wait_for_result_page(
            keyword, timeout=8.0
        ):
            return True
        try:
            source = self.driver.page_source or ""
        except Exception:
            source = ""
        logger.error(
            "App首页搜索结果等待超时 keyword=%r has_rv_search=%s has_vp_search_result=%s",
            keyword,
            "rv_search" in source,
            "vp_search_result" in source,
        )
        return False

    def _enter_keyword_once(self, keyword: str) -> bool:
        element = self.tester._find(AppiumBy.ID, self.SEARCH_INPUT_ID, timeout=5)
        if not element:
            return False
        element.click()
        element.clear()
        old_text = self._element_text(element)
        if not old_text:
            old_text = self._input_text_from_page_source() or ""
        if old_text:
            logger.info("App首页搜索准备清空旧关键词 actual=%r", old_text)
            close = self.tester._find(
                AppiumBy.ID, "com.bs.feifubao:id/iv_close", timeout=2
            )
            if not close or not close.is_displayed() or not close.is_enabled():
                logger.error("App首页搜索未找到可用清空按钮 iv_close")
                return False
            close.click()
            logger.info("App首页搜索已点击清空按钮 iv_close")
            if self._wait_for_input_text("", timeout=3.0) is None:
                logger.error(
                    "App首页搜索等待清空超时 source_actual=%r",
                    self._input_text_from_page_source(),
                )
                return False
            element = self.tester._find(
                AppiumBy.ID, self.SEARCH_INPUT_ID, timeout=3
            )
            if not element:
                return False
        element.send_keys(keyword)
        input_text = self._wait_for_input_text(keyword)
        logger.info("App首页搜索已输入 keyword=%r actual=%r", keyword, input_text)
        return input_text == keyword

    def _wait_for_result_page(self, keyword: str, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                source = self.driver.page_source or ""
            except Exception:
                source = ""
            if keyword in source and "vp_search_result" in source:
                return True
            time.sleep(0.25)
        return False

    def _click_matching_suggestion(self, keyword: str) -> bool:
        safe = keyword.replace('"', "").replace("'", "")[:48]
        xpath = (
            f'//*[contains(@resource-id,"tv_name") and contains(@text,"{safe}")]'
        )
        try:
            elements = self.driver.find_elements(AppiumBy.XPATH, xpath)
        except Exception:
            elements = []
        for element in elements:
            try:
                if not element.is_displayed() or not element.is_enabled():
                    continue
                try:
                    target = element.find_element(
                        AppiumBy.XPATH,
                        "./ancestor::*[@clickable='true'][1]",
                    )
                except Exception:
                    target = element
                target.click()
                logger.info("App首页搜索已点击联想词 keyword=%r", keyword)
                return True
            except Exception:
                continue
        return False

    def _wait_for_input_text(
        self, expected: str, timeout: float = 3.0
    ) -> Optional[str]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            element = self.tester._find(
                AppiumBy.ID, self.SEARCH_INPUT_ID, timeout=1
            )
            if element:
                latest = self._element_text(element)
                if latest == expected:
                    return latest
            source_text = self._input_text_from_page_source()
            if source_text is not None and source_text == expected:
                return source_text
            time.sleep(0.2)
        return None

    def _input_text_from_page_source(self) -> Optional[str]:
        try:
            source = self.driver.page_source or ""
        except Exception:
            return None
        tag_match = re.search(
            r'<[^>]*resource-id="com\.bs\.feifubao:id/et_search"[^>]*>',
            source,
        )
        if not tag_match:
            return None
        tag = tag_match.group(0)
        if re.search(r'\bshowing-hint="true"', tag, flags=re.I):
            return ""
        text_match = re.search(r'\btext="([^"]*)"', tag)
        return html.unescape(text_match.group(1)).strip() if text_match else None

    def _submit_search(self) -> bool:
        for suffix in ("layout_right", "tv_search", "tv_right"):
            button = self.tester._find(
                AppiumBy.ID, f"com.bs.feifubao:id/{suffix}", timeout=2
            )
            if not button:
                logger.debug("App首页搜索提交控件未找到 suffix=%s", suffix)
                continue
            try:
                if not button.is_displayed() or not button.is_enabled():
                    continue
                try:
                    target = button.find_element(
                        AppiumBy.XPATH,
                        "./ancestor::*[@clickable='true'][1]",
                    )
                except Exception:
                    target = button
                target.click()
                logger.info("App首页搜索已点击提交控件 suffix=%s", suffix)
                return True
            except Exception:
                logger.warning("App首页搜索提交控件点击失败 suffix=%s", suffix)
                continue
        try:
            self.driver.press_keycode(66)
            logger.info("App首页搜索已使用回车提交兜底")
            return True
        except Exception:
            return False

    @staticmethod
    def _element_text(element) -> str:
        try:
            showing_hint = element.get_attribute("showing-hint")
            if str(showing_hint).strip().lower() == "true":
                return ""
            return (element.text or "").strip()
        except Exception:
            return ""

    def prefer_goods_results(self) -> bool:
        try:
            elements = self.driver.find_elements(
                AppiumBy.XPATH, '//*[@text="商城" or @content-desc="商城"]'
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
            '//*[contains(@resource-id,"tv_good_name")]',
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
                        try:
                            target = element.find_element(
                                AppiumBy.XPATH,
                                "./ancestor::*[@clickable='true'][1]",
                            )
                        except Exception:
                            target = element
                        target.click()
                        return True
                except Exception:
                    continue
        return False

    def read_goods_summary(self, keyword: str) -> Optional[SearchProductSummary]:
        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            name = self._first_visible_text_by_id_suffixes(
                ("tv_goods_title", "tv_good_name")
            )
            if name:
                price = self._first_visible_text_by_id_suffixes(
                    ("tv_price", "tv_goods_price")
                )
                specification = self._first_visible_text_by_id_suffixes(
                    ("tv_select", "tv_spec", "tv_sku")
                )
                return SearchProductSummary(keyword, name, price, specification)
            time.sleep(0.25)
        return None

    def _first_visible_text_by_id_suffixes(self, suffixes: tuple[str, ...]) -> str:
        conditions = " or ".join(
            f'contains(@resource-id,"{suffix}")' for suffix in suffixes
        )
        try:
            elements = self.driver.find_elements(
                AppiumBy.XPATH, f"//*[{conditions}]"
            )
        except Exception:
            elements = []
        for element in elements:
            try:
                text = (element.text or "").strip()
                if element.is_displayed() and text:
                    return text
            except Exception:
                continue
        return ""

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
