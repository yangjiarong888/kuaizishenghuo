"""商城首页购物车 Tab 角标读取（与列表价格等数字解耦）。"""
from __future__ import annotations

import re
import time
from typing import Optional, Tuple

from appium.webdriver.common.appiumby import AppiumBy

from commons.logger import setup_logger
from pages.shop_locators import (
    SHOP_ID_COUNT_TEXT,
    SHOP_ID_CV_CART,
    SHOP_ID_FLOAT_VIEW,
    SHOP_ID_IV_CART,
    SHOP_ID_IV_SHOPPING_CART,
    SHOP_ID_RL_CART,
    SHOP_ID_RL_SHOPPING_CART,
)
from pages.shop_mall_context import ShopMallContext

logger = setup_logger(__name__)


class MallCartBadgeReader:
    """购物车角标数字解析，供 ``ShopHomePage`` 委托。"""

    def __init__(self, ctx: ShopMallContext) -> None:
        self._ctx = ctx

    @staticmethod
    def tv_centre_in_bounds(tv, left: int, top: int, right: int, bottom: int) -> bool:
        try:
            loc = tv.location
            sz = tv.size
            cx = int(loc["x"]) + max(int(sz["width"]) // 2, 1)
            cy = int(loc["y"]) + max(int(sz["height"]) // 2, 1)
            return left <= cx <= right and top <= cy <= bottom
        except Exception:
            return False

    @staticmethod
    def _digit_from_text(raw: str) -> Optional[int]:
        m = re.search(r"\d+", (raw or "").strip())
        return int(m.group(0)) if m else None

    def _read_by_common_badge_ids(self) -> Optional[int]:
        suffixes = (
            "tv_cart_count",
            "tv_badge",
            "tv_cart_num",
            "tv_message_count",
            "badge_tv",
            SHOP_ID_COUNT_TEXT,
        )
        for suf in suffixes:
            el = self._ctx.first_displayed_by_pkg_id(suf)
            if not el:
                continue
            try:
                got = self._digit_from_text(el.text or "")
                if got is not None:
                    return got
            except Exception as ex:
                logger.debug("角标 id=%s 读文案失败: %s", suf, ex)
        return None

    def _score_badge_textview(
        self, tv, bounds: Tuple[int, int, int, int]
    ) -> Optional[Tuple[int, int]]:
        try:
            if not tv.is_displayed():
                return None
            tx = (tv.text or "").strip()
            if not re.fullmatch(r"\d{1,4}", tx):
                return None
            if not self.tv_centre_in_bounds(tv, *bounds):
                return None
            if int(tv.size.get("width", 999)) > 96:
                return None
            return int(tv.location["x"]) + int(tv.location["y"]), int(tx)
        except Exception:
            return None

    def _best_digit_near_anchor(self, root, bounds: Tuple[int, int, int, int]):
        best: Optional[Tuple[int, int]] = None
        containers = [root]
        try:
            containers.append(root.find_element(AppiumBy.XPATH, ".."))
        except Exception:
            pass
        for container in containers:
            try:
                textviews = container.find_elements(
                    AppiumBy.CLASS_NAME, "android.widget.TextView"
                )
            except Exception:
                continue
            for tv in textviews:
                scored = self._score_badge_textview(tv, bounds)
                if scored and (best is None or scored[0] > best[0]):
                    best = scored
        return best

    def _read_near_cart_anchors(self) -> Optional[int]:
        best: Optional[Tuple[int, int]] = None
        for anchor in (
            SHOP_ID_IV_SHOPPING_CART,
            SHOP_ID_RL_SHOPPING_CART,
            SHOP_ID_IV_CART,
            SHOP_ID_RL_CART,
            SHOP_ID_CV_CART,
            SHOP_ID_FLOAT_VIEW,
        ):
            root = self._ctx.first_displayed_by_pkg_id(anchor)
            if not root:
                continue
            try:
                loc = root.location
                sz = root.size
                ax, ay = int(loc["x"]), int(loc["y"])
                aw, ah = int(sz["width"]), int(sz["height"])
            except Exception:
                continue
            bounds = (ax - 6, ay - 56, ax + aw + 80, ay + ah + 14)
            scored = self._best_digit_near_anchor(root, bounds)
            if scored and (best is None or scored[0] > best[0]):
                best = scored
        return best[1] if best else None

    def _read_by_uiautomator_badge_id(self) -> Optional[int]:
        try:
            el = self._ctx.driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                "new UiSelector().resourceIdMatches("
                '".+:(tv_cart_count|tv_badge|tv_cart_num|tv_message_count|badge_tv)$")',
            )
            if el and el.is_displayed():
                return self._digit_from_text(el.text or "")
        except Exception as ex:
            logger.debug("角标 UiAutomator 兜底失败: %s", ex)
        return None

    def read_digit(self) -> Optional[int]:
        """
        读取商城首页购物车角标数字；无法解析时返回 None。

        避免 ``find_elements(TextView)`` 扫整页；优先常见 id；
        否则仅在购物车/悬浮入口图标邻近小范围内找纯数字。
        """
        with self._ctx.zero_implicit_wait():
            for reader in (
                self._read_by_common_badge_ids,
                self._read_near_cart_anchors,
                self._read_by_uiautomator_badge_id,
            ):
                got = reader()
                if got is not None:
                    return got
        return None

    def read_expect_increase(
        self,
        baseline: Optional[int],
        *,
        min_delta: int = 1,
        wait_sec: float = 24.0,
        step_sec: float = 1.0,
    ) -> Optional[int]:
        deadline = time.time() + wait_sec
        last: Optional[int] = None
        while time.time() < deadline:
            cur = self.read_digit()
            last = cur
            if cur is None:
                time.sleep(step_sec)
                continue
            if baseline is None or cur >= baseline + min_delta:
                return cur
            time.sleep(step_sec)
        try:
            w, h = self._ctx.window_size()
            self._ctx.driver.swipe(
                int(w * 0.52), int(h * 0.56), int(w * 0.52), int(h * 0.52), 280
            )
        except Exception as ex:
            logger.debug("角标轮询后轻滑失败: %s", ex)
        time.sleep(0.55)
        cur = self.read_digit()
        if cur is not None and baseline is not None and cur >= baseline + min_delta:
            return cur
        return last
