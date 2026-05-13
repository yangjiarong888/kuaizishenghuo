"""商城多规格底部弹层：选 SKU、数量、确定/完成。"""
from __future__ import annotations

import re
import time
from typing import Callable

from appium.webdriver.common.appiumby import AppiumBy

from commons.logger import setup_logger
from pages.shop_locators import (
    SHOP_ID_BOTTOM_POPUP,
    SHOP_ID_CHOOSE_RECYCLER,
    SHOP_ID_CHOOSE_SCROLL,
    SHOP_ID_CHOOSE_SKU_CONTAINER,
    SHOP_ID_COUNT_ADD,
    SHOP_ID_DIALOG_CHOOSE_CONTAINER,
    SHOP_ID_DIALOG_COMPLETE,
    SHOP_TEXT_FINISH_SPEC,
)
from pages.shop_mall_context import ShopMallContext

logger = setup_logger(__name__)


class MallSpecSheet:
    """规格弹层交互，供 ``ShopHomePage`` 委托。"""

    def __init__(
        self,
        ctx: ShopMallContext,
        login_like_visible: Callable[[], bool],
    ) -> None:
        self._ctx = ctx
        self._login_like_visible = login_like_visible

    def tx_looks_like_mall_spec_chip(self, tx: str) -> bool:
        if not tx or len(tx) > 44:
            return False
        t = tx.strip()
        ban_exact = (
            "确定",
            SHOP_TEXT_FINISH_SPEC,
            "取消",
            "加入购物车",
            "规格",
            "数量",
            "库存",
            "选择",
            "已选",
            "+",
            "-",
            "＋",
            "－",
        )
        if t in ban_exact:
            return False
        if re.fullmatch(r"\d{1,4}", t):
            return False
        low = t.lower()
        return bool(
            re.search(
                r"(pcs|pic|pc\b|box|箱|盒|袋|包|瓶|罐|条|/"
                r"|ml\b|\bmg\b|\bg\b|\d+\s*(瓶|罐|包|pcs|pic|箱|件|盒|条))",
                low,
                re.I,
            )
        )

    def try_pick_one_chip(self, root, tag: str) -> bool:
        if not root:
            return False
        try:
            for tel in root.find_elements(
                AppiumBy.CLASS_NAME, "android.widget.TextView"
            ):
                try:
                    if not tel.is_displayed():
                        continue
                    tx = (tel.text or "").strip()
                    if not self.tx_looks_like_mall_spec_chip(tx):
                        continue
                    self._ctx.nearest_clickable_ancestor(tel).click()
                    logger.info("已选规格项(%s): %s", tag, tx[:40])
                    time.sleep(0.45)
                    return True
                except Exception as ex:
                    logger.debug("try_pick_one_chip 跳过: %s", ex)
                    continue
        except Exception as ex:
            logger.debug("try_pick_one_chip 容器失败: %s", ex)
        return False

    def popup_pick_and_confirm(self) -> bool:
        end = time.time() + 14.0
        while time.time() < end:
            if self._login_like_visible():
                logger.error("选规格后进入登录页，请先登录")
                return False
            if self._ctx.first_displayed_by_pkg_id(SHOP_ID_DIALOG_COMPLETE):
                break
            if self._ctx.first_displayed_by_pkg_id(SHOP_ID_BOTTOM_POPUP):
                break
            if self._ctx.first_displayed_by_pkg_id(SHOP_ID_DIALOG_CHOOSE_CONTAINER):
                break
            time.sleep(0.35)
        picked = False
        sku_root = self._ctx.first_displayed_by_pkg_id(SHOP_ID_CHOOSE_SKU_CONTAINER)
        if self.try_pick_one_chip(sku_root, "choose_sku"):
            picked = True
        if not picked:
            rv = self._ctx.first_displayed_by_pkg_id(SHOP_ID_CHOOSE_RECYCLER)
            if self.try_pick_one_chip(rv, "choose_recycler"):
                picked = True
        if not picked:
            sv = self._ctx.first_displayed_by_pkg_id(SHOP_ID_CHOOSE_SCROLL)
            self.try_pick_one_chip(sv, "choose_scroll")
        add_el = self._ctx.first_displayed_by_pkg_id(SHOP_ID_COUNT_ADD)
        if add_el:
            if self._ctx.try_click(add_el, "count_add"):
                logger.info("已点击规格弹层数量加（count_add）")
                time.sleep(0.45)
        if self.tap_confirm_button():
            return True
        logger.error("多规格弹层未点到「确定/完成」等主按钮")
        return False

    @staticmethod
    def _short_bottom_text(el, y_cut: int, *, max_len: int = 10) -> bool:
        try:
            if not el.is_displayed():
                return False
            if int(el.location.get("y", 0)) < y_cut:
                return False
            return len((el.text or "").strip()) <= max_len
        except Exception:
            return False

    def _click_confirm_candidate(self, el, desc: str, *, sleep_sec: float = 0.85) -> bool:
        try:
            self._ctx.nearest_clickable_ancestor(el).click()
            logger.info("已点击多规格弹层主按钮（%s）", desc)
            time.sleep(sleep_sec)
            return True
        except Exception:
            if self._ctx.try_click(el, desc):
                logger.info("已点击多规格弹层主按钮（%s 自身）", desc)
                time.sleep(sleep_sec)
                return True
        return False

    def _tap_confirm_by_dialog_complete_id(self) -> bool:
        for pkg in self._ctx.shop_packages_prioritized():
            rid = self._ctx.rid(pkg, SHOP_ID_DIALOG_COMPLETE)
            try:
                for el in self._ctx.driver.find_elements(AppiumBy.ID, rid):
                    try:
                        if not el.is_displayed():
                            continue
                        if self._click_confirm_candidate(el, f"dialog_complete / {pkg}"):
                            return True
                    except Exception as ex:
                        logger.debug("dialog_complete 候选跳过: %s", ex)
            except Exception as ex:
                logger.debug("dialog_complete id 扫描: %s", ex)
        return False

    def _tap_confirm_by_dialog_complete_xpath(self) -> bool:
        try:
            for el in self._ctx.driver.find_elements(
                AppiumBy.XPATH,
                '//*[contains(@resource-id,"dialog_complete")]',
            ):
                try:
                    if el.is_displayed() and self._click_confirm_candidate(
                        el, "resource-id 含 dialog_complete"
                    ):
                        return True
                except Exception:
                    continue
        except Exception as ex:
            logger.debug("dialog_complete XPath: %s", ex)
        return False

    def _tap_confirm_by_exact_text(self, y_cut: int) -> bool:
        for label in (SHOP_TEXT_FINISH_SPEC, "确定", "加入购物车"):
            try:
                for el in self._ctx.driver.find_elements(
                    AppiumBy.XPATH, f'//*[@text="{label}"]'
                ):
                    if self._short_bottom_text(el, y_cut) and self._click_confirm_candidate(
                        el, f"文案 {label}"
                    ):
                        return True
            except Exception as ex:
                logger.debug("规格弹层文案 %s: %s", label, ex)
        return False

    def _tap_confirm_by_contains_text(self, y_cut: int) -> bool:
        for sub, disp in ((SHOP_TEXT_FINISH_SPEC, "完成"), ("确定", "确定")):
            try:
                xp = f'//*[contains(@text,"{sub}")]'
                for el in self._ctx.driver.find_elements(AppiumBy.XPATH, xp):
                    if self._short_bottom_text(el, y_cut) and self._click_confirm_candidate(
                        el, f"contains 文案 {disp}"
                    ):
                        return True
            except Exception as ex:
                logger.debug("规格弹层 contains %s: %s", sub, ex)
        return False

    def _tap_confirm_by_button_text(self, y_cut: int) -> bool:
        try:
            for el in self._ctx.driver.find_elements(
                AppiumBy.XPATH,
                (
                    '//android.widget.Button['
                    'contains(@text,"完成") or contains(@text,"确定")]'
                ),
            ):
                if self._short_bottom_text(el, y_cut) and self._ctx.try_click(
                    el, "Button 完成/确定"
                ):
                    logger.info("已点击多规格弹层主按钮（Button 完成/确定）")
                    time.sleep(0.85)
                    return True
        except Exception as ex:
            logger.debug("规格 Button: %s", ex)
        return False

    def _tap_confirm_by_uiautomator(self) -> bool:
        for label in (SHOP_TEXT_FINISH_SPEC, "确定"):
            try:
                self._ctx.driver.find_element(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    f'new UiSelector().text("{label}").clickable(true)',
                ).click()
                logger.info("已点击多规格弹层「%s」（UiAutomator）", label)
                time.sleep(0.85)
                return True
            except Exception as ex:
                logger.debug("规格 UiAutomator %s: %s", label, ex)
                continue
        return False

    def tap_confirm_button(self) -> bool:
        y_cut = int(self._ctx.window_size()[1] * 0.32)
        for strategy in (
            self._tap_confirm_by_dialog_complete_id,
            self._tap_confirm_by_dialog_complete_xpath,
            lambda: self._tap_confirm_by_exact_text(y_cut),
            lambda: self._tap_confirm_by_contains_text(y_cut),
            lambda: self._tap_confirm_by_button_text(y_cut),
            self._tap_confirm_by_uiautomator,
        ):
            if strategy():
                return True
        return False
