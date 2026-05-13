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

    def read_digit(self) -> Optional[int]:
        """
        读取商城首页购物车角标数字；无法解析时返回 None。

        避免 ``find_elements(TextView)`` 扫整页；优先常见 id；
        否则仅在购物车/悬浮入口图标邻近小范围内找纯数字。
        """
        with self._ctx.zero_implicit_wait():
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
                if el:
                    try:
                        raw = (el.text or "").strip()
                        m = re.search(r"\d+", raw)
                        if m:
                            return int(m.group(0))
                    except Exception as ex:
                        logger.debug("角标 id=%s 读文案失败: %s", suf, ex)

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
                pad_l, pad_t, pad_r, pad_b = 6, 56, 80, 14
                L, T, R, B = ax - pad_l, ay - pad_t, ax + aw + pad_r, ay + ah + pad_b
                for tv in root.find_elements(
                    AppiumBy.CLASS_NAME, "android.widget.TextView"
                ):
                    try:
                        if not tv.is_displayed():
                            continue
                        tx = (tv.text or "").strip()
                        if not re.fullmatch(r"\d{1,4}", tx):
                            continue
                        if not self.tv_centre_in_bounds(tv, L, T, R, B):
                            continue
                        tw = int(tv.size.get("width", 999))
                        if tw > 96:
                            continue
                        val = int(tx)
                        if best is None:
                            best = (ax + ay, val)
                        else:
                            s = int(tv.location["x"]) + int(tv.location["y"])
                            if s > best[0]:
                                best = (s, val)
                    except Exception:
                        continue
                try:
                    par = root.find_element(AppiumBy.XPATH, "..")
                    for tv in par.find_elements(
                        AppiumBy.CLASS_NAME, "android.widget.TextView"
                    ):
                        try:
                            if not tv.is_displayed():
                                continue
                            tx = (tv.text or "").strip()
                            if not re.fullmatch(r"\d{1,4}", tx):
                                continue
                            if not self.tv_centre_in_bounds(tv, L, T, R, B):
                                continue
                            tw = int(tv.size.get("width", 999))
                            if tw > 96:
                                continue
                            val = int(tx)
                            s = int(tv.location["x"]) + int(tv.location["y"])
                            if best is None or s > best[0]:
                                best = (s, val)
                        except Exception:
                            continue
                except Exception:
                    pass

            if best:
                return best[1]

            try:
                el = self._ctx.driver.find_element(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    "new UiSelector().resourceIdMatches("
                    '".+:(tv_cart_count|tv_badge|tv_cart_num|tv_message_count|badge_tv)$")',
                )
                if el and el.is_displayed():
                    raw = (el.text or "").strip()
                    m = re.search(r"\d+", raw)
                    if m:
                        return int(m.group(0))
            except Exception as ex:
                logger.debug("角标 UiAutomator 兜底失败: %s", ex)
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
