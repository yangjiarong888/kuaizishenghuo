"""商城首页上方区域：金刚区「爆款零食」、列表 Tab「新品优选」。"""
from __future__ import annotations

import time

from typing import Tuple

from appium.webdriver.common.appiumby import AppiumBy

from commons.logger import setup_logger
from pages.shop_locators import (
    SHOP_ID_LL_ITEM,
    SHOP_ID_TV_TITLE,
    SHOP_KINGKONG_HOT_SNACKS,
    SHOP_PACKAGES,
    SHOP_TEXT_NEW_PRODUCT_PICK,
    SHOP_TEXT_NEW_PRODUCT_PICK_EMOJI,
)

logger = setup_logger(__name__)


class MallHomeChrome:
    """首页金刚区与横向 Tab；依赖 ``owner`` 的 driver、坐标与可点祖先解析。"""

    def __init__(self, owner) -> None:
        self._o = owner

    def kingkong_hot_snacks_label_visible(self) -> bool:
        label = SHOP_KINGKONG_HOT_SNACKS
        for pkg in SHOP_PACKAGES:
            xp = (
                f'//*[@resource-id="{pkg}:id/{SHOP_ID_TV_TITLE}" and @text="{label}"]'
            )
            try:
                for el in self._o.driver.find_elements(AppiumBy.XPATH, xp):
                    if el.is_displayed():
                        return True
            except Exception:
                continue
        return False

    def _click_hot_snacks_from_tv_title_el(
        self, el, pkg: str, label: str, *, retry: bool
    ) -> bool:
        if not el.is_displayed():
            return False
        try:
            p_rid = self._o._rid(pkg, SHOP_ID_LL_ITEM)
            parent = el.find_element(
                AppiumBy.XPATH,
                f'./ancestor::android.widget.LinearLayout[@resource-id="{p_rid}"][1]',
            )
            if parent.is_displayed():
                parent.click()
                if retry:
                    logger.info(
                        "已点击金刚区「%s」（重试 ll_item / %s）", label, pkg
                    )
                else:
                    logger.info(
                        "已点击金刚区「%s」（父级 ll_item / %s）", label, pkg
                    )
                time.sleep(1.4)
                return True
        except Exception:
            pass
        try:
            self._o._nearest_clickable_ancestor(el).click()
            if retry:
                logger.info(
                    "已点击金刚区「%s」（重试 tv_title / %s）", label, pkg
                )
            else:
                logger.info("已点击金刚区「%s」（%s）", label, pkg)
            time.sleep(1.4)
            return True
        except Exception:
            return False

    def _try_hot_snacks_tv_title_all_packages(self, label: str, *, retry: bool) -> bool:
        for pkg in SHOP_PACKAGES:
            xp = (
                f'//*[@resource-id="{pkg}:id/{SHOP_ID_TV_TITLE}" and @text="{label}"]'
            )
            try:
                for el in self._o.driver.find_elements(AppiumBy.XPATH, xp):
                    if self._click_hot_snacks_from_tv_title_el(
                        el, pkg, label, retry=retry
                    ):
                        return True
            except Exception:
                continue
        return False

    def _try_hot_snacks_plain_text_xpath(self, label: str) -> bool:
        try:
            for el in self._o.driver.find_elements(
                AppiumBy.XPATH, f'//android.widget.TextView[@text="{label}"]'
            ):
                try:
                    if not el.is_displayed():
                        continue
                    y = int(el.location.get("y", 0))
                    h = self._o._window_size()[1]
                    if y > int(h * 0.92):
                        continue
                    try:
                        parent = el.find_element(
                            AppiumBy.XPATH,
                            './ancestor::android.widget.LinearLayout'
                            '[contains(@resource-id,"ll_item")][1]',
                        )
                        if parent.is_displayed():
                            parent.click()
                            logger.info(
                                "已点击金刚区「%s」（纯文案 + 祖先 ll_item）",
                                label,
                            )
                            time.sleep(1.4)
                            return True
                    except Exception:
                        pass
                    self._o._nearest_clickable_ancestor(el).click()
                    logger.info("已点击金刚区「%s」（纯文案 XPath）", label)
                    time.sleep(1.4)
                    return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    def _try_hot_snacks_uiautomator(self, label: str) -> bool:
        try:
            self._o.driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                f'new UiSelector().text("{label}")',
            ).click()
            logger.info("已点击金刚区「%s」（UiAutomator）", label)
            time.sleep(1.4)
            return True
        except Exception:
            return False

    def tap_kingkong_hot_snacks(self) -> bool:
        """金刚区点击「爆款零食」。"""
        label = SHOP_KINGKONG_HOT_SNACKS
        if not self.kingkong_hot_snacks_label_visible():
            self._o.mall_list_gesture_scroll_to_top(6)
            time.sleep(0.45)
        if self._try_hot_snacks_tv_title_all_packages(label, retry=False):
            return True
        if self._try_hot_snacks_plain_text_xpath(label):
            return True
        if self._try_hot_snacks_uiautomator(label):
            return True
        logger.warning("金刚区「%s」首次未命中，手势回顶后重试", label)
        self._o.mall_list_gesture_scroll_to_top(8)
        time.sleep(0.5)
        self._o.tap_back_to_top_if_visible()
        time.sleep(0.35)
        if self._try_hot_snacks_tv_title_all_packages(label, retry=True):
            return True
        logger.error("未找到金刚区「%s」", label)
        return False

    def _new_product_tab_y_bounds(self) -> Tuple[int, int]:
        h = self._o._window_size()[1]
        return int(h * 0.10), int(h * 0.72)

    def _try_new_product_tv_title_contains(self, y_lo: int, y_hi: int) -> bool:
        for pkg in SHOP_PACKAGES:
            rid = self._o._rid(pkg, SHOP_ID_TV_TITLE)
            xp = f'//*[@resource-id="{rid}" and contains(@text,"新品优选")]'
            try:
                for el in self._o.driver.find_elements(AppiumBy.XPATH, xp):
                    try:
                        if not el.is_displayed():
                            continue
                        y = int(el.location.get("y", -1))
                        if not (y_lo <= y <= y_hi):
                            continue
                        try:
                            p_rid = self._o._rid(pkg, SHOP_ID_LL_ITEM)
                            parent = el.find_element(
                                AppiumBy.XPATH,
                                f'./ancestor::android.widget.LinearLayout[@resource-id="{p_rid}"][1]',
                            )
                            if parent.is_displayed():
                                parent.click()
                                logger.info(
                                    "已点击 Tab「新品优选」（tv_title+ll_item / %s）",
                                    pkg,
                                )
                                time.sleep(0.55)
                                return True
                        except Exception:
                            pass
                        self._o._nearest_clickable_ancestor(el).click()
                        logger.info(
                            "已点击 Tab「新品优选」（tv_title / %s）", pkg
                        )
                        time.sleep(0.55)
                        return True
                    except Exception:
                        continue
            except Exception:
                pass
        return False

    def _try_new_product_exact_text_labels(self, y_lo: int, y_hi: int) -> bool:
        for label in (SHOP_TEXT_NEW_PRODUCT_PICK_EMOJI, SHOP_TEXT_NEW_PRODUCT_PICK):
            try:
                for el in self._o.driver.find_elements(
                    AppiumBy.XPATH,
                    f'//android.widget.TextView[@text="{label}"]',
                ):
                    try:
                        if not el.is_displayed():
                            continue
                        y = int(el.location.get("y", -1))
                        if not (y_lo <= y <= y_hi):
                            continue
                        self._o._nearest_clickable_ancestor(el).click()
                        logger.info("已点击 Tab「新品优选」（精确文案 %s）", label)
                        time.sleep(0.55)
                        return True
                    except Exception:
                        continue
            except Exception:
                pass
        return False

    def _try_new_product_uiautomator(self, y_lo: int, y_hi: int) -> bool:
        try:
            for el in self._o.driver.find_elements(
                AppiumBy.ANDROID_UIAUTOMATOR,
                'new UiSelector().textContains("新品优选")',
            ):
                try:
                    if not el.is_displayed():
                        continue
                    y = int(el.location.get("y", -1))
                    if not (y_lo <= y <= y_hi):
                        continue
                    self._o._nearest_clickable_ancestor(el).click()
                    logger.info("已点击 Tab「新品优选」（UiAutomator）")
                    time.sleep(0.55)
                    return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    def _try_new_product_xpath_contains_loose_y(self, h: int) -> bool:
        try:
            for el in self._o.driver.find_elements(
                AppiumBy.XPATH,
                '//android.widget.TextView[contains(@text,"新品优选")]',
            ):
                try:
                    if not el.is_displayed():
                        continue
                    y = int(el.location.get("y", 99999))
                    if y > int(h * 0.84):
                        continue
                    self._o._nearest_clickable_ancestor(el).click()
                    logger.info("已点击 Tab「新品优选」（含 emoji 等宽 y 兜底）")
                    time.sleep(0.55)
                    return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    def tap_new_product_prefer_tab(self) -> bool:
        """
        列表上方 Tab「新品优选」。
        与金刚区相同为 ``tv_title``，文案常为 ``✨新品优选``（非 ``activity_filter`` 精确「新品优选」）。
        """
        y_lo, y_hi = self._new_product_tab_y_bounds()
        if self._try_new_product_tv_title_contains(y_lo, y_hi):
            return True
        if self._try_new_product_exact_text_labels(y_lo, y_hi):
            return True
        if self._try_new_product_uiautomator(y_lo, y_hi):
            return True
        h = self._o._window_size()[1]
        if self._try_new_product_xpath_contains_loose_y(h):
            return True
        return self._o.tap_mall_text_filter(
            SHOP_TEXT_NEW_PRODUCT_PICK,
            y_min_ratio=0.10,
            y_max_ratio=0.72,
        )
