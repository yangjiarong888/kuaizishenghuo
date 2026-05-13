"""店铺详情下单流程（TakeoutPageBase 混入）。"""
from __future__ import annotations

import random
import re
import time
from contextlib import nullcontext
from datetime import date, timedelta
import unicodedata
from typing import Any, List, Optional, Sequence, Set, Tuple

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from commons.logger import setup_logger
from pages.takeout_locators import (
    _WEB_REASON_FRAGMENTS,
    _WEB_XPATH_CANCEL_ORDER,
    _WEB_XPATH_CONFIRM_CANCEL,
    _WEB_XPATH_SUBMIT,
    _XPATH_DESC_CART,
    _XPATH_DESC_SELECT_ADDRESS,
    _XPATH_NATIVE_CANCEL_ORDER,
    _XPATH_NATIVE_CONFIRM_CANCEL,
    _XPATH_NATIVE_SUBMIT,
)

logger = setup_logger(__name__)



from pages.takeout_delivery_time_mixin import TakeoutDeliveryTimeMixin
from pages.takeout_cancel_order_mixin import TakeoutCancelOrderMixin

class TakeoutCheckoutMixin(TakeoutDeliveryTimeMixin, TakeoutCancelOrderMixin):

    def _maybe_zero_implicit_wait(self):
        """TakeoutPageBase 提供 _zero_implicit_wait；纯 Mixin 无该属性时用空上下文。"""
        zw = getattr(self, "_zero_implicit_wait", None)
        if callable(zw):
            return zw()
        return nullcontext()
    

    def _window_size_safe(self) -> Tuple[int, int]:
        """
        宽高；长时间 UiAutomator 操作后 Instrumentation 常崩，
        此处失败时退回默认值，避免改试别名时再抛未捕获异常。
        """
        try:
            s = self.driver.get_window_size()
            return int(s["width"]), int(s["height"])
        except WebDriverException as ex:
            logger.warning(
                "get_window_size 失败（UiAutomator2/Instrumentation 可能已崩）: %s，"
                "退回 1080×2220",
                ex,
            )
            return 1080, 2220
        except Exception as ex:
            logger.warning("get_window_size 失败: %s，退回 1080×2220", ex)
            return 1080, 2220
    

    def _tap_first_displayed(
        self,
        by: str,
        value: str,
        require_bottom_half: bool = False,
    ) -> bool:
        try:
            h = self._window_height()
            y_cut = h // 2
            for el in self.driver.find_elements(by, value):
                try:
                    if not el.is_displayed():
                        continue
                    if require_bottom_half and int(el.location.get("y", 0)) < y_cut:
                        continue
                    el.click()
                    return True
                except Exception:
                    continue
        except Exception:
            pass
        return False
    

    def _coord_tap_or_click(self, el: Any, log_line: str) -> bool:
        """Flutter 常用：优先坐标点击，再试 el.click()。"""
        try:
            loc = el.location
            sz = el.size
            cx = int(loc["x"]) + max(1, int(sz["width"]) // 2)
            cy = int(loc["y"]) + max(1, int(sz["height"]) // 2)
        except Exception:
            return False
        try:
            self.driver.execute_script(
                "mobile: clickGesture", {"x": cx, "y": cy}
            )
            logger.info("%s (%d,%d)", log_line, cx, cy)
            time.sleep(0.45)
            return True
        except Exception:
            pass
        try:
            el.click()
            logger.info("%s（元素 click）", log_line)
            time.sleep(0.45)
            return True
        except Exception:
            return False
    

    def _uia_desc_escape(self, s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"')
    

    def _xpath_contains_content_desc(self, sub: str) -> str:
        safe = sub.replace('"', "")
        return f'//*[contains(@content-desc,"{safe}")]'
    

    def _collect_sidebar_category_xpaths(self, category_desc: str) -> List[str]:
        xs: List[str] = [self._xpath_contains_content_desc(category_desc)]
        if "健康" in category_desc and "粮油" in category_desc:
            xs.append(
                '//*[contains(@content-desc,"健康") and contains(@content-desc,"粮油")]'
            )
        return xs
    

    def _sidebar_merged_xpath(self, category_desc: str) -> str:
        """单条 XPath 覆盖 content-desc / text，避免多次全树扫描。"""
        parts: List[str] = []
        safe_cd = category_desc.replace('"', "")
        parts.append(f'contains(@content-desc,"{safe_cd}")')
        if "健康" in category_desc and "粮油" in category_desc:
            parts.append(
                '(contains(@content-desc,"健康") and contains(@content-desc,"粮油"))'
            )
            parts.append(
                '(contains(@text,"健康") and contains(@text,"粮油"))'
            )
        if "'" not in category_desc:
            parts.append(f"@content-desc='{category_desc}'")
        if '"' not in category_desc:
            parts.append(f'@text="{category_desc}"')
        elif "'" not in category_desc:
            parts.append(f"@text='{category_desc}'")
        return f"//*[{' or '.join(parts)}]"
    

    def _sidebar_uia_needles(self, category_desc: str) -> List[str]:
        """
        勿用单独的 descriptionContains("健康")：会命中大量节点，单次 gather 极慢。
        优先整串与「粮油」等较窄子串。
        """
        out: List[str] = []
        s = category_desc.strip()
        if len(s) >= 2 and s not in out:
            out.append(s)
        if "健康" in category_desc and "粮油" in category_desc:
            for frag in ("健康粮油", "粮油"):
                if frag not in out:
                    out.append(frag)
        return out
    

    def _sidebar_rect_key(self, el: Any) -> Optional[Tuple[int, int, int, int]]:
        try:
            loc = el.location
            sz = el.size
            x, y = int(loc["x"]), int(loc["y"])
            ww, hh = int(sz["width"]), int(sz["height"])
            if ww <= 0 or hh <= 0:
                return None
            return (x, y, ww, hh)
        except Exception:
            return None
    

    def _sidebar_element_in_band(self, el: Any, left_max_x: int) -> bool:
        try:
            loc = el.location
            sz = el.size
            x = int(loc.get("x", 0))
            cx = x + int(sz.get("width", 0)) // 2
            return cx <= left_max_x or x <= left_max_x
        except Exception:
            return False
    

    def _sidebar_text_blob(self, el: Any) -> str:
        try:
            d = (el.get_attribute("content-desc") or "").strip()
            t = (el.get_attribute("text") or "").strip()
            blob = f"{d} {t}".replace("\n", " ").replace("\r", " ")
            blob = re.sub(r"\s+", " ", blob)
            return blob.strip()
        except Exception:
            return ""
    

    def _sidebar_blob_matches_category(self, el: Any, category_desc: str) -> bool:
        blob = self._sidebar_text_blob(el)
        if not blob:
            return False
        if category_desc in blob:
            return True
        compact_cat = re.sub(r"\s+", "", category_desc)
        compact_blob = re.sub(r"\s+", "", blob)
        if compact_cat and compact_cat in compact_blob:
            return True
        if "健康" in category_desc and "粮油" in category_desc:
            return "健康" in blob and "粮油" in blob
        return False
    

    def _sidebar_blob_matches_category_loose(
        self,
        el: Any,
        category_desc: str,
        item_width: int,
        screen_w: int,
    ) -> bool:
        """侧栏可能只标「粮油」；右侧商品也可能含油字，用宽度限制窄条。"""
        if self._sidebar_blob_matches_category(el, category_desc):
            return True
        blob = self._sidebar_text_blob(el)
        if "健康" in category_desc and "粮油" in category_desc:
            if "粮油" in blob and item_width <= int(screen_w * 0.40):
                return True
        return False
    

    def _try_tap_sidebar_category_loose_xpath(
        self, category_desc: str, screen_w: int, h: int
    ) -> bool:
        """不依赖 ScrollView scrollIntoView；直接找树上含关键词的左半屏节点并坐标点。"""
        ymin = int(h * 0.06)
        cx_max = int(screen_w * 0.54)
        xps: List[str] = []
        safe = category_desc.replace('"', "").strip()
        if "健康" in category_desc and "粮油" in category_desc:
            xps.extend(
                (
                    '//*[contains(@content-desc,"健康") and contains(@content-desc,"粮油")]',
                    '//android.view.View[contains(@content-desc,"粮油")]',
                    '//*[contains(@text,"健康") and contains(@text,"粮油")]',
                )
            )
        if safe:
            xps.append(f'//*[contains(@content-desc,"{safe}")]')
        scored: List[Tuple[int, int, Any]] = []
        seen: Set[int] = set()
        for xp in xps:
            try:
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    try:
                        eid = id(el)
                        if eid in seen:
                            continue
                        if not el.is_displayed():
                            continue
                        loc = el.location
                        sz = el.size
                        y = int(loc.get("y", 0))
                        x = int(loc.get("x", 0))
                        ww = int(sz.get("width", 0))
                        if y < ymin or ww <= 0:
                            continue
                        cx = x + ww // 2
                        if cx > cx_max:
                            continue
                        if ww > int(screen_w * 0.78) and x > int(screen_w * 0.08):
                            continue
                        if not self._sidebar_blob_matches_category_loose(
                            el, category_desc, ww, screen_w
                        ):
                            continue
                        sc = self._sidebar_match_score(el, category_desc)
                        if sc <= 0:
                            sc = 100
                        seen.add(eid)
                        scored.append((sc, -y, el))
                    except Exception:
                        continue
            except Exception:
                continue
        scored.sort(key=lambda t: (-t[0], t[1]))
        for _sc, _ny, el in scored[:12]:
            if self._tap_sidebar_coordinate_or_click(el, category_desc):
                logger.info("已宽匹配点到分类「%s」", category_desc)
                time.sleep(0.45)
                return True
        return False
    

    def _sidebar_is_left_column(self, el: Any, screen_w: int) -> bool:
        """
        Flutter 侧栏常把整行做成接近屏宽的 semantics，旧逻辑要求 cx<=0.38w 会把真实分类行全滤掉。
        窄块仍用中心；宽行只要左缘在左侧约 42% 内即视为分类列（文字在左，与右侧商品区分）。
        """
        k = self._sidebar_rect_key(el)
        if not k:
            return False
        x, _y, ww, _hh = k
        cx = x + ww // 2
        narrow = ww <= int(screen_w * 0.42)
        if narrow:
            return cx <= int(screen_w * 0.52)
        if x <= int(screen_w * 0.42):
            return True
        return x < int(screen_w * 0.28) and cx <= int(screen_w * 0.40)
    

    def _sidebar_match_score(self, el: Any, category_desc: str) -> int:
        blob = self._sidebar_text_blob(el)
        if not blob:
            return 0
        if category_desc in blob:
            return 5000 + len(blob)
        if "健康" in category_desc and "粮油" in category_desc:
            if "健康" in blob and "粮油" in blob:
                return 3000 + len(blob)
        return len(blob)
    

    def _gather_sidebar_category_matches(
        self,
        category_desc: str,
        gather_band_x: int,
        *,
        with_xpath: bool = True,
    ) -> List[Any]:
        """
        gather_band_x 宜宽（如 0.78*屏宽）：Flutter 父节点往往很宽，中心会超出窄左带，
        但仍需在后续用 _sidebar_is_left_column 过滤后再点击。
        """
        rects: Set[Tuple[int, int, int, int]] = set()
        bucket: List[Any] = []
    
        def push(el: Any) -> None:
            try:
                if not el.is_displayed():
                    return
            except Exception:
                return
            if not self._sidebar_element_in_band(el, gather_band_x):
                return
            k = self._sidebar_rect_key(el)
            if not k or k in rects:
                return
            rects.add(k)
            bucket.append(el)
    
        for needle in self._sidebar_uia_needles(category_desc):
            esc = self._uia_desc_escape(needle)
            sel = f'new UiSelector().descriptionContains("{esc}")'
            try:
                for el in self.driver.find_elements(
                    AppiumBy.ANDROID_UIAUTOMATOR, sel
                ):
                    push(el)
            except Exception:
                pass
    
        if with_xpath:
            try:
                for el in self.driver.find_elements(
                    AppiumBy.XPATH, self._sidebar_merged_xpath(category_desc)
                ):
                    push(el)
            except Exception:
                pass
    
        def sort_key(el: Any) -> Tuple[int, int, int]:
            sc = self._sidebar_match_score(el, category_desc)
            k = self._sidebar_rect_key(el) or (99999, 0, 99999, 99999)
            return (-sc, k[0], k[2])
    
        bucket.sort(key=sort_key)
        return bucket
    

    def _scroll_sidebar_scrollview_forward_once(self) -> bool:
        """用 UiScrollable 滚「某一个」垂直 ScrollView，优先带动左侧分类列（instance 小）。"""
        for inst in range(4):
            try:
                uia = (
                    "new UiScrollable(new UiSelector().className("
                    f'"android.widget.ScrollView").instance({inst})).scrollForward()'
                )
                self.driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, uia)
                time.sleep(0.22)
                return True
            except Exception:
                continue
        return False
    

    def _scroll_vertical_list_widget_forward_once(self) -> bool:
        """Flutter 店铺左侧常为 RecyclerView，仅滚 ScrollView 时分类不动。"""
        for cls in (
            "androidx.recyclerview.widget.RecyclerView",
            "android.support.v7.widget.RecyclerView",
            "android.widget.ScrollView",
        ):
            for inst in range(5):
                try:
                    uia = (
                        f'new UiScrollable(new UiSelector().className("{cls}")'
                        f'.instance({inst})).scrollForward()'
                    )
                    self.driver.find_element(
                        AppiumBy.ANDROID_UIAUTOMATOR, uia
                    )
                    time.sleep(0.2)
                    return True
                except Exception:
                    continue
        return False
    

    def _uia_scroll_into_exact_category_desc(
        self, desc: str, *, max_swipes: int = 10
    ) -> None:
        """ScrollView / RecyclerView / ListView 上 scrollIntoView，覆盖 Flutter 侧栏。"""
        esc = self._uia_desc_escape(desc.strip())
        target = f'new UiSelector().description("{esc}")'
        for cls_name in (
            "android.widget.ScrollView",
            "androidx.recyclerview.widget.RecyclerView",
            "android.support.v7.widget.RecyclerView",
            "android.widget.ListView",
        ):
            for inst in range(5):
                try:
                    uia = (
                        f'new UiScrollable(new UiSelector().className('
                        f'"{cls_name}").instance({inst}))'
                        f".setMaxSearchSwipes({max_swipes}).scrollIntoView({target})"
                    )
                    self.driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, uia)
                    time.sleep(0.28)
                    return
                except Exception:
                    continue
    

    def _try_tap_exact_sidebar_view_if_visible(
        self, category_desc: str, screen_w: int
    ) -> bool:
        """Inspector：//android.view.View[@content-desc=\"…\"] 已在屏内则左偏点击。"""
        safe = category_desc.replace('"', "").strip()
        if not safe or "'" in category_desc:
            return False
        xp = f'//android.view.View[@content-desc="{safe}"]'
        x_m = int(screen_w * 0.52)
        for el in self.driver.find_elements(AppiumBy.XPATH, xp):
            try:
                if not el.is_displayed():
                    continue
                if (el.get_attribute("content-desc") or "").strip() != safe:
                    continue
                x0 = int(el.location.get("x", 0))
                ww = int(el.size.get("width", 0))
                if ww < int(screen_w * 0.62) and x0 > x_m:
                    continue
                if self._tap_sidebar_coordinate_or_click(el, category_desc):
                    logger.info("侧栏「%s」已在可视区，直接点击", safe)
                    time.sleep(0.4)
                    return True
            except Exception:
                continue
        return False
    

    def _try_sidebar_scrollview_scroll_into_then_tap(
        self,
        category_desc: str,
        screen_w: int,
        h: int,
        *,
        max_swipes: int = 8,
        max_instances: int = 5,
    ) -> bool:
        """
        侧栏分类在 android.widget.ScrollView 内（见 Inspector 树）。
        对每个 ScrollView instance 尝试 scrollIntoView；**max_swipes 勿过大**，否则 UiAutomator
        会长时间阻塞，表现为页面卡住数分钟。
        """
        safe = category_desc.replace('"', "").replace("'", "").strip()
        if not safe:
            return False
        esc = self._uia_desc_escape(safe)
        targets = (
            f'new UiSelector().description("{esc}").clickable(true)',
            f'new UiSelector().description("{esc}")',
        )
        x_m = int(screen_w * 0.52)
        for inst in range(max_instances):
            logger.info(
                "侧栏：ScrollView.instance(%d) scrollIntoView「%s」（最多 %d 滑次）…",
                inst,
                safe,
                max_swipes,
            )
            for target in targets:
                try:
                    uia = (
                        f'new UiScrollable(new UiSelector().className('
                        f'"android.widget.ScrollView").instance({inst}))'
                        f".setMaxSearchSwipes({max_swipes}).scrollIntoView({target})"
                    )
                    self.driver.find_element(
                        AppiumBy.ANDROID_UIAUTOMATOR, uia
                    )
                    time.sleep(0.22)
                except Exception:
                    continue
                xp = f'//android.view.View[@content-desc="{safe}"]'
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    try:
                        if not el.is_displayed():
                            continue
                        if (el.get_attribute("content-desc") or "").strip() != safe:
                            continue
                        x0 = int(el.location.get("x", 0))
                        ww = int(el.size.get("width", 0))
                        if ww < int(screen_w * 0.62) and x0 > x_m:
                            continue
                        if self._tap_sidebar_coordinate_or_click(
                            el, category_desc
                        ):
                            logger.info(
                                "已 ScrollView[%d].scrollIntoView 后点到侧栏「%s」",
                                inst,
                                safe,
                            )
                            time.sleep(0.45)
                            return True
                    except Exception:
                        continue
        return False
    

    def _try_tap_exact_flutter_category_view(
        self, category_desc: str, screen_w: int
    ) -> bool:
        """
        Inspector：//android.view.View[@content-desc=…]。
        屏外时 is_displayed 常为 false，先 scrollIntoView 再重查。
        """
        safe_cd = category_desc.replace('"', "").strip()
        if safe_cd != category_desc.strip() or "'" in category_desc:
            return False
        xp_view = f'//android.view.View[@content-desc="{safe_cd}"]'
        for pass_i in range(2):
            try:
                for el in self.driver.find_elements(
                    AppiumBy.XPATH, xp_view
                ):
                    try:
                        if (el.get_attribute("content-desc") or "").strip() != safe_cd:
                            continue
                        if el.is_displayed():
                            if self._tap_sidebar_coordinate_or_click(
                                el, category_desc
                            ):
                                logger.info(
                                    "已点侧栏精确 View[@content-desc=\"%s\"]",
                                    safe_cd,
                                )
                                return True
                    except Exception:
                        continue
            except Exception:
                pass
            if "健康" in category_desc and "粮油" in category_desc:
                try:
                    xp_loose = (
                        '//android.view.View['
                        'contains(@content-desc,"健康") and contains(@content-desc,"粮油")]'
                    )
                    x_cut = int(screen_w * 0.48)
                    for el in self.driver.find_elements(
                        AppiumBy.XPATH, xp_loose
                    ):
                        try:
                            if not el.is_displayed():
                                continue
                            d = (el.get_attribute("content-desc") or "").strip()
                            if "健康" not in d or "粮油" not in d:
                                continue
                            if int(el.location.get("x", 9999)) > x_cut:
                                continue
                            if self._tap_sidebar_coordinate_or_click(
                                el, category_desc
                            ):
                                logger.info(
                                    "已点侧栏 View[contains 健康+粮油]"
                                )
                                return True
                        except Exception:
                            continue
                except Exception:
                    pass
            if pass_i == 0:
                self._uia_scroll_into_exact_category_desc(safe_cd)
                time.sleep(0.4)
        try:
            esc = self._uia_desc_escape(safe_cd)
            for sel in (
                f'new UiSelector().description("{esc}")',
                f'new UiSelector().description("{esc}").clickable(true)',
            ):
                for el in self.driver.find_elements(
                    AppiumBy.ANDROID_UIAUTOMATOR, sel
                ):
                    try:
                        if not el.is_displayed():
                            continue
                        if self._tap_sidebar_coordinate_or_click(
                            el, category_desc
                        ):
                            logger.info(
                                "已 UiSelector.description 点中「%s」", safe_cd
                            )
                            return True
                    except Exception:
                        continue
        except Exception:
            pass
        return False
    

    def _try_sidebar_category_ultralight(
        self, category_desc: str, screen_w: int, h: int
    ) -> bool:
        """
        滚动循环内每步调用：禁止 scrollIntoView、禁止 textContains 扫全树
        （否则单步可达数十秒～数分钟）。
        """
        if self._tap_first_displayed(
            AppiumBy.ACCESSIBILITY_ID, category_desc
        ):
            logger.info("已 ACCESSIBILITY_ID 选中「%s」", category_desc)
            time.sleep(0.4)
            return True
        safe = category_desc.replace('"', "").strip()
        esc = self._uia_desc_escape(safe) if safe else ""
        x_m = int(screen_w * 0.52)
        ymin = int(h * 0.05)
        if esc:
            for sel in (
                f'new UiSelector().description("{esc}")',
                f'new UiSelector().description("{esc}").clickable(true)',
            ):
                try:
                    for el in self.driver.find_elements(
                        AppiumBy.ANDROID_UIAUTOMATOR, sel
                    ):
                        try:
                            if not el.is_displayed():
                                continue
                            if int(el.location.get("y", 0)) < ymin:
                                continue
                            if int(el.location.get("x", 9999)) > x_m:
                                continue
                            if self._tap_sidebar_coordinate_or_click(
                                el, category_desc
                            ):
                                logger.info(
                                    "已 UiA 精确点到「%s」", category_desc
                                )
                                time.sleep(0.4)
                                return True
                        except Exception:
                            continue
                except Exception:
                    pass
        if safe and "'" not in category_desc:
            xp = f'//android.view.View[@content-desc="{safe}"]'
            for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                try:
                    if not el.is_displayed():
                        continue
                    if (el.get_attribute("content-desc") or "").strip() != safe:
                        continue
                    if int(el.location.get("x", 9999)) > x_m:
                        continue
                    if self._tap_sidebar_coordinate_or_click(
                        el, category_desc
                    ):
                        logger.info("已精确 View 点到「%s」", category_desc)
                        time.sleep(0.4)
                        return True
                except Exception:
                    continue
        if "健康" in category_desc and "粮油" in category_desc:
            xp2 = (
                '//android.view.View['
                'contains(@content-desc,"健康") and contains(@content-desc,"粮油")]'
            )
            for el in self.driver.find_elements(AppiumBy.XPATH, xp2):
                try:
                    if not el.is_displayed():
                        continue
                    d = (el.get_attribute("content-desc") or "").strip()
                    if "健康" not in d or "粮油" not in d:
                        continue
                    if int(el.location.get("x", 9999)) > x_m:
                        continue
                    if self._tap_sidebar_coordinate_or_click(
                        el, category_desc
                    ):
                        logger.info("已 View(健康+粮油) 点到分类")
                        time.sleep(0.4)
                        return True
                except Exception:
                    continue
        return False
    

    def _try_sidebar_category_quick(
        self, category_desc: str, screen_w: int
    ) -> bool:
        """轻量路径：无全树合并 XPath，供滚动循环内高频调用。"""
        if self._tap_first_displayed(
            AppiumBy.ACCESSIBILITY_ID, category_desc
        ):
            logger.info("已 ACCESSIBILITY_ID 选中「%s」", category_desc)
            time.sleep(0.45)
            return True
        if self._try_tap_exact_flutter_category_view(
            category_desc, screen_w
        ):
            return True
        try:
            esc = self._uia_desc_escape(category_desc.strip())
            sel = f'new UiSelector().textContains("{esc}")'
            scored: List[Tuple[int, Any]] = []
            for el in self.driver.find_elements(
                AppiumBy.ANDROID_UIAUTOMATOR, sel
            ):
                try:
                    if not el.is_displayed():
                        continue
                    if not self._sidebar_blob_matches_category(
                        el, category_desc
                    ):
                        continue
                    if not self._sidebar_is_left_column(el, screen_w):
                        continue
                    y = int(el.location.get("y", 0))
                    scored.append((y, el))
                except Exception:
                    continue
            scored.sort(key=lambda t: -t[0])
            for _, el in scored[:4]:
                if self._tap_sidebar_coordinate_or_click(el, category_desc):
                    logger.info("已 textContains 点中「%s」", category_desc)
                    return True
        except Exception:
            pass
        return False
    

    def _tap_sidebar_coordinate_or_click(self, el: Any, category_desc: str) -> bool:
        try:
            loc = el.location
            sz = el.size
            x0 = int(loc["x"])
            wel = max(1, int(sz["width"]))
            cy = int(loc["y"]) + max(1, int(sz["height"]) // 2)
            try:
                sw = self._window_size_safe()[0]
            except Exception:
                sw = 1080
            if wel > int(sw * 0.48):
                cx = x0 + min(int(wel * 0.20), int(sw * 0.18))
            else:
                cx = x0 + wel // 2
        except Exception:
            return False
        try:
            self.driver.execute_script(
                "mobile: clickGesture", {"x": cx, "y": cy}
            )
            logger.info(
                "已坐标点击侧栏「%s」中心 (%d,%d)", category_desc, cx, cy
            )
            time.sleep(0.5)
            return True
        except Exception:
            pass
        try:
            el.click()
            logger.info("已元素 click 侧栏「%s」", category_desc)
            time.sleep(0.5)
            return True
        except Exception:
            return False
    

    def _try_activate_sidebar_category(
        self,
        category_desc: str,
        left_max_x: int,
        screen_w: int,
        *,
        with_xpath: bool = True,
        use_full_gather: bool = True,
    ) -> bool:
        if self._try_sidebar_category_quick(category_desc, screen_w):
            return True
        if not use_full_gather:
            return False
        tried: Set[Tuple[int, int, int, int]] = set()
        gather_x = max(int(screen_w * 0.78), left_max_x + 1)
        for el in self._gather_sidebar_category_matches(
            category_desc, gather_x, with_xpath=with_xpath
        ):
            if not self._sidebar_blob_matches_category(el, category_desc):
                continue
            if not self._sidebar_is_left_column(el, screen_w):
                continue
            k = self._sidebar_rect_key(el)
            if k and k in tried:
                continue
            if k:
                tried.add(k)
            if self._tap_sidebar_coordinate_or_click(el, category_desc):
                return True
        return False
    

    def _uia_scroll_sidebar_scroll_into_view(
        self, category_desc: str, *, max_swipes: int = 8
    ) -> None:
        """descriptionContains 比精确串更易滚到靠后的分类；max_swipes 大可一次拉到位。"""
        needles = self._sidebar_uia_needles(category_desc)
        for needle in needles[:2]:
            esc = self._uia_desc_escape(needle)
            targets = (
                f'new UiSelector().description("{esc}")',
                f'new UiSelector().descriptionContains("{esc}")',
            )
            for target in targets:
                for cls_name in (
                    "android.widget.ScrollView",
                    "androidx.recyclerview.widget.RecyclerView",
                    "android.support.v7.widget.RecyclerView",
                ):
                    for inst in range(5):
                        try:
                            uia = (
                                f'new UiScrollable(new UiSelector().className('
                                f'"{cls_name}").instance({inst}))'
                                f".setMaxSearchSwipes({max_swipes}).scrollIntoView({target})"
                            )
                            self.driver.find_element(
                                AppiumBy.ANDROID_UIAUTOMATOR, uia
                            )
                            time.sleep(0.25)
                            return
                        except Exception:
                            continue
        return
    

    def _scroll_shop_category_sidebar_once(
        self, w: int, h: int, round_i: int, *, aggressive: bool
    ) -> None:
        x0 = max(28, int(w * 0.10)) if round_i % 2 == 0 else max(36, int(w * 0.16))
        y_top, y_bot = int(h * 0.24), int(h * 0.80)
        pct = 0.82 if aggressive else 0.48
        try:
            self.driver.execute_script(
                "mobile: swipeGesture",
                {
                    "left": max(0, int(w * 0.02)),
                    "top": int(h * 0.20),
                    "width": max(64, int(w * 0.22)),
                    "height": int(h * 0.58),
                    "direction": "up",
                    "percent": pct,
                },
            )
        except Exception:
            try:
                dur = 280 if aggressive else 380
                self.driver.swipe(x0, y_bot, x0, y_top, dur)
            except Exception:
                pass
        time.sleep(0.05)
    

    def _scroll_shop_category_sidebar_toward_top_once(
        self, w: int, h: int, round_i: int
    ) -> None:
        """与 _scroll_shop_category_sidebar_once 对称：左带向下滑，把分类列表滚回上方/顶部。"""
        x0 = max(28, int(w * 0.10)) if round_i % 2 == 0 else max(36, int(w * 0.16))
        y_top, y_bot = int(h * 0.26), int(h * 0.82)
        try:
            self.driver.execute_script(
                "mobile: swipeGesture",
                {
                    "left": max(0, int(w * 0.02)),
                    "top": int(h * 0.20),
                    "width": max(64, int(w * 0.22)),
                    "height": int(h * 0.58),
                    "direction": "down",
                    "percent": 0.78,
                },
            )
        except Exception:
            try:
                self.driver.swipe(x0, y_top, x0, y_bot, 340)
            except Exception:
                pass
        time.sleep(0.05)
    

    def _reset_shop_category_sidebar_to_top(
        self, w: int, h: int, category_desc: str
    ) -> None:
        """进店后侧栏可能停在中部，先固定滚到顶再查目标分类，易命中 ACCESSIBILITY_ID 快路径。"""
        logger.info("左侧分类条先滚至顶部，再查找「%s」", category_desc)
        # 步数过多易与后续下滚对冲；滚顶本身应轻量
        for i in range(5):
            self._scroll_shop_category_sidebar_toward_top_once(w, h, i)
            time.sleep(0.04)
        time.sleep(0.12)
    

    def _left_sidebar_quick_scan_for_category(
        self,
        category_desc: str,
        left_max_x: int,
        w: int,
        h: int,
        *,
        max_steps: int = 20,
    ) -> bool:
        """
        只在左条上逐步下滚，每步仅快路径（ACCESSIBILITY / 精确 View / textContains），
        不做全树 descriptionContains，避免进店后空等近一分钟才进入「左条滚动」循环。
        """
        logger.info(
            "左侧优先：沿分类条下滚至多 %d 步，每步快路径点「%s」",
            max_steps,
            category_desc,
        )
        if self._try_tap_sidebar_category_loose_xpath(category_desc, w, h):
            return True
        for step in range(max_steps):
            if self._try_sidebar_category_ultralight(
                category_desc, w, h
            ):
                return True
            if self._try_tap_left_rail_uia_needle(category_desc, w, h):
                return True
            if step % 5 == 0:
                if self._try_tap_sidebar_category_loose_xpath(
                    category_desc, w, h
                ):
                    return True
                if step > 0 and step % 10 == 0:
                    self._uia_scroll_sidebar_scroll_into_view(
                        category_desc, max_swipes=5
                    )
                    time.sleep(0.2)
                    if self._try_tap_sidebar_category_loose_xpath(
                        category_desc, w, h
                    ):
                        return True
            if step > 0 and step % 4 == 0:
                logger.info(
                    "左侧快路径：已沿侧栏下滚 %d/%d 步，仍未点到「%s」",
                    step,
                    max_steps,
                    category_desc,
                )
            self._scroll_shop_category_sidebar_once(
                w, h, step, aggressive=(step < 18)
            )
            if step >= 10:
                self._scroll_shop_category_sidebar_once(
                    w, h, step + 7, aggressive=True
                )
            time.sleep(0.1)
        return False
    

    def _implicit_category_alias_needles(self, category_desc: str) -> List[str]:
        """App 侧栏文案常与脚本里写的略不一致，自动追加一批近义关键词。"""
        out: List[str] = []
        if "健康" in category_desc and "粮油" in category_desc:
            # 只保留少数近义，避免「主名失败后」再各跑一遍 24 轮深搜导致总耗时可数十分钟
            for a in ("米面粮油", "粮油调味", "粮油"):
                if a != category_desc.strip() and a not in out:
                    out.append(a)
        if "招牌" in category_desc:
            for a in ("本店招牌", "店铺招牌"):
                if a != category_desc.strip() and a not in out:
                    out.append(a)
        return out
    

    def _try_tap_left_rail_uia_needle(
        self, needle: str, screen_w: int, h: int
    ) -> bool:
        """在左半屏用 UiSelector.description / Contains 找节点，宽行左偏点击。"""
        raw = (needle or "").strip()
        if len(raw) < 2:
            return False
        esc = self._uia_desc_escape(raw)
        y_min = int(h * 0.08)
        cx_max = int(screen_w * 0.42)
        use_contains = len(raw) >= 3
        selectors: List[str] = [
            f'new UiSelector().description("{esc}").clickable(true)',
            f'new UiSelector().description("{esc}")',
        ]
        if use_contains:
            selectors.append(
                f'new UiSelector().descriptionContains("{esc}").clickable(true)'
            )
        compact_needle = re.sub(r"\s+", "", raw)
        for sel in selectors:
            is_contains = "Contains" in sel
            try:
                els = self.driver.find_elements(
                    AppiumBy.ANDROID_UIAUTOMATOR, sel
                )
            except Exception:
                continue
            bucket: List[Tuple[int, Any]] = []
            for el in els[:40]:
                try:
                    if not el.is_displayed():
                        continue
                    loc = el.location
                    sz = el.size
                    x = int(loc.get("x", 0))
                    y = int(loc.get("y", 0))
                    ww = int(sz.get("width", 0))
                    hh = int(sz.get("height", 0))
                    if y < y_min or hh < 10:
                        continue
                    cx = x + ww // 2
                    blob = self._sidebar_text_blob(el)
                    compact_blob = re.sub(r"\s+", "", blob)
                    if is_contains:
                        if (
                            raw not in blob
                            and compact_needle not in compact_blob
                        ):
                            continue
                        if len(raw) <= 3 and ww > int(screen_w * 0.48):
                            continue
                    if cx > cx_max and x > int(screen_w * 0.12):
                        continue
                    bucket.append((y, el))
                except Exception:
                    continue
            bucket.sort(key=lambda t: t[0])
            for _y, el in bucket[:10]:
                if self._tap_sidebar_coordinate_or_click(el, raw):
                    logger.info("已左轨 UiSelector 命中「%s」", raw)
                    time.sleep(0.45)
                    return True
        return False
    

    def shop_detail_scroll_to_category(
        self,
        category_desc: str = "店内招牌",
        *,
        category_aliases: Optional[Sequence[str]] = None,
    ) -> bool:
        time.sleep(0.45)
        names: List[str] = []
        seen: Set[str] = set()
    
        def add(name: str) -> None:
            n = (name or "").strip()
            if not n or n in seen:
                return
            seen.add(n)
            names.append(n)
    
        add(category_desc)
        if category_aliases:
            for a in category_aliases:
                add(str(a).strip())
        for a in self._implicit_category_alias_needles(category_desc):
            add(a)
        for idx, name in enumerate(names):
            if idx:
                logger.info(
                    "改试侧栏关键词「%s」（你指定的是「%s」）",
                    name,
                    category_desc,
                )
            try:
                if self._shop_detail_scroll_to_category_once(
                    name, deep=(idx < 2)
                ):
                    return True
            except WebDriverException as ex:
                logger.error(
                    "查找分类「%s」时驱动异常，停止尝试其余关键词: %s",
                    name,
                    ex,
                )
                return False
        logger.error(
            "未点到指定分类（已依次尝试：%s），流程将终止，不会无限重试。",
            "、".join(names),
        )
        return False
    

    def _shop_detail_scroll_to_category_once(
        self, category_desc: str, *, deep: bool = True
    ) -> bool:
        w, h = self._window_size_safe()
        logger.info("侧栏：查找分类「%s」…", category_desc)
        if self._try_tap_exact_sidebar_view_if_visible(category_desc, w):
            return True
        # 勿在滚顶前做「全 instance × 高 max_swipes」scrollIntoView，否则 UiA 会卡数分钟
        self._reset_shop_category_sidebar_to_top(w, h, category_desc)
        if self._try_tap_exact_sidebar_view_if_visible(category_desc, w):
            return True
        if self._try_sidebar_scrollview_scroll_into_then_tap(
            category_desc, w, h, max_swipes=8, max_instances=5
        ):
            return True
    
        left_max_x = max(260, int(w * 0.44))
        max_rounds = 14 if deep else 0
    
        if self._try_tap_left_rail_uia_needle(category_desc, w, h):
            return True
        if self._try_tap_sidebar_category_loose_xpath(
            category_desc, w, h
        ):
            return True
    
        if self._left_sidebar_quick_scan_for_category(
            category_desc,
            left_max_x,
            w,
            h,
            max_steps=16 if deep else 10,
        ):
            return True
    
        if not deep:
            logger.info(
                "侧栏关键词「%s」：轻量尝试未命中，跳过全树搜集与多轮滚动（避免长时间占用）",
                category_desc,
            )
            return False
    
        logger.info("左侧快路径未命中，进行全树搜集（较慢）…")
        if self._try_activate_sidebar_category(
            category_desc,
            left_max_x,
            w,
            with_xpath=True,
            use_full_gather=True,
        ):
            return True
        self._uia_scroll_sidebar_scroll_into_view(category_desc)
        if self._try_tap_left_rail_uia_needle(category_desc, w, h):
            return True
        if self._try_tap_sidebar_category_loose_xpath(category_desc, w, h):
            return True
        if self._try_activate_sidebar_category(
            category_desc,
            left_max_x,
            w,
            with_xpath=True,
            use_full_gather=True,
        ):
            return True
    
        for round_i in range(max_rounds):
            aggressive = round_i < 10
            if round_i % 3 == 0:
                logger.info(
                    "侧栏寻找「%s」：左条滚动 %d/%d（%s）…",
                    category_desc,
                    round_i + 1,
                    max_rounds,
                    "大步" if aggressive else "细调",
                )
            if round_i % 6 == 0:
                self._scroll_vertical_list_widget_forward_once()
            if round_i >= 5:
                self._scroll_sidebar_scrollview_forward_once()
            self._scroll_shop_category_sidebar_once(
                w, h, round_i, aggressive=aggressive
            )
            time.sleep(0.12)
            if round_i % 6 == 0:
                self._uia_scroll_into_exact_category_desc(category_desc)
                time.sleep(0.18)
            if round_i % 4 == 0:
                if self._try_sidebar_scrollview_scroll_into_then_tap(
                    category_desc,
                    w,
                    h,
                    max_swipes=5,
                    max_instances=3,
                ):
                    return True
            heavy = round_i % 2 == 0
            if self._try_tap_left_rail_uia_needle(category_desc, w, h):
                return True
            if self._try_activate_sidebar_category(
                category_desc,
                left_max_x,
                w,
                with_xpath=True,
                use_full_gather=heavy,
            ):
                return True
            if self._try_tap_sidebar_category_loose_xpath(
                category_desc, w, h
            ):
                return True
    
        for last_i in range(8):
            if last_i % 2 == 0 and self._try_sidebar_scrollview_scroll_into_then_tap(
                category_desc,
                w,
                h,
                max_swipes=5,
                max_instances=3,
            ):
                return True
            if self._try_tap_left_rail_uia_needle(category_desc, w, h):
                return True
            if self._try_tap_sidebar_category_loose_xpath(
                category_desc, w, h
            ):
                return True
            self._scroll_shop_category_sidebar_once(
                w, h, last_i + 30, aggressive=True
            )
            self._scroll_vertical_list_widget_forward_once()
            time.sleep(0.14)
    
        logger.info("本关键词「%s」仍未点到分类", category_desc)
        return False
    

    def _parse_price_amount_from_blob(self, blob: str) -> Optional[float]:
        """从 content-desc / 文案中抽出金额数字（₱、¥、P 等），取匹配到的最大值。"""
        if not blob:
            return None
        s = (
            blob.replace(",", "")
            .replace("，", "")
            .replace("：", ":")
        )
        vals: List[float] = []
        for pat in (
            r"₱\s*(\d+(?:\.\d+)?)",
            r"[¥￥]\s*(\d+(?:\.\d+)?)",
            r"P\s*:?\s*(\d+(?:\.\d+)?)",
            r"(?<![A-Za-z])P(\d+(?:\.\d+)?)",
            r"(?:PHP|php)\s*(\d+(?:\.\d+)?)",
        ):
            for m in re.finditer(pat, s, re.I):
                try:
                    v = float(m.group(1))
                    if 1.0 <= v <= 9_999_999.0:
                        vals.append(v)
                except ValueError:
                    continue
        return max(vals) if vals else None
    

    def _element_merchant_blob(self, el: Any) -> str:
        """合并 content-desc / text（列表价有时只在 text 上）。"""
        try:
            parts = [
                el.get_attribute("content-desc") or "",
                el.get_attribute("text") or "",
            ]
            s = " ".join(parts)
            s = unicodedata.normalize("NFKC", s)
            return re.sub(r"\s+", " ", s).strip()
        except Exception:
            return ""

    @staticmethod

    def _blob_has_price_hint(blob: str) -> bool:
        if not blob or len(blob) < 4:
            return False
        if any(c in blob for c in ("₱", "¥", "￥", "＄")):
            return True
        if "PHP" in blob.upper():
            return True
        if re.search(r"\bP\s*[\d]", blob, re.I):
            return True
        if re.search(r"(?<![A-Za-z])P\d{1,5}(?:\.\d+)?", blob):
            return True
        return False


    def _tap_open_product_detail_center(self, el: Any) -> bool:
        """
        点击首张商品卡 **偏左、偏上** 区域进详情（标题/主图区），
        避免点在行右侧 `+` 附近误触下一行或误加购第二条（见 Inspector 首条红框）。
        """
        try:
            loc = el.location
            sz = el.size
            cw = max(1, int(sz.get("width", 0)))
            ch = max(1, int(sz.get("height", 0)))
            ax = int(loc.get("x", 0)) + max(8, int(cw * 0.26))
            ay = int(loc.get("y", 0)) + max(8, int(ch * 0.40))
            self.driver.execute_script(
                "mobile: clickGesture",
                {"x": ax, "y": ay},
            )
            logger.info("已点主区首张商品左上进详情 (%d,%d)", ax, ay)
            time.sleep(0.35)
            return True
        except Exception as ex:
            logger.warning("点击进入详情失败: %s", ex)
            return False


    def _first_main_area_product_row_geometry(
        self, w: int, h: int
    ) -> Optional[Any]:
        """
        当 accessibility 上无 ₱ 时，用主区大块 View/ImageView 几何特征取「第一条商品行」。
        阈值偏宽，避免 Flutter 拆条后宽度不足 0.42*w 被全部过滤。
        """
        x_main = int(w * 0.16)
        y_top = int(h * 0.11)
        y_max = int(h * 0.84)
        w_min = max(100, int(w * 0.26))
        w_max = int(w * 0.99)
        raw: List[Tuple[int, int, Any]] = []
        seen: Set[str] = set()

        def _push(el: Any) -> None:
            try:
                eid = getattr(el, "id", None) or str(id(el))
                if eid in seen:
                    return
                if not el.is_displayed():
                    return
                loc = el.location
                sz = el.size
                x0 = int(loc.get("x", 0))
                y0 = int(loc.get("y", 0))
                cw = int(sz.get("width", 0))
                ch = int(sz.get("height", 0))
                if (
                    x0 < x_main
                    or y0 < y_top
                    or y0 > y_max
                    or cw < w_min
                    or cw > w_max
                    or ch < 58
                    or ch > 520
                ):
                    return
                blob = self._element_merchant_blob(el)
                if len(blob) < 6 and ch < 110:
                    return
                seen.add(eid)
                raw.append((y0, cw * ch, el))
            except Exception:
                return

        for xp in (
            '//android.view.View[@clickable="true"]',
            '//android.widget.ImageView[@clickable="true"]',
            '//android.widget.ImageView',
        ):
            try:
                n = 0
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    n += 1
                    if n > 260:
                        break
                    _push(el)
            except Exception:
                continue
        if not raw:
            return None
        raw.sort(key=lambda t: (t[0], -t[1]))
        out: List[Tuple[int, Any]] = []
        for y0, _area, el in raw:
            if out and (y0 - out[-1][0]) < 44:
                continue
            out.append((y0, el))
        return out[0][1] if out else None


    def _shop_detail_tap_first_product_coordinate_fallback(
        self, w: int, h: int
    ) -> bool:
        """
        侧栏已选分类后，主列表首条商品常见热区（多档 x/y），进入详情再价高+加购。
        不依赖 accessibility 树里是否出现 ₱。
        **y 从小到大优先**，避免先点到屏上偏下的第二条。
        """
        for x_frac, y_frac in (
            (0.44, 0.195),
            (0.47, 0.205),
            (0.50, 0.20),
            (0.55, 0.21),
            (0.58, 0.22),
            (0.52, 0.24),
            (0.60, 0.23),
            (0.56, 0.26),
        ):
            ax = max(24, int(w * x_frac))
            ay = max(int(h * 0.16), int(h * y_frac))
            try:
                self.driver.execute_script(
                    "mobile: clickGesture",
                    {"x": ax, "y": ay},
                )
                logger.info("主区坐标兜底：试点首商品 (%d,%d)", ax, ay)
                time.sleep(1.05)
                if self._pick_highest_visible_spec_row(
                    w, h, top_y_ratio=0.02
                ) or self._tap_spec_sheet_primary_button():
                    return True
            except Exception:
                continue
        return False


    def _tap_spec_sheet_primary_button(self) -> bool:
        """规格弹层底部主按钮：Flutter 常为「加购 ₱xx」；其次为确定类。"""
        h = self._window_height()
        for lab in ("加购", "加入购物车", "确定", "选好了", "完成", "确认"):
            bottom = lab in ("加购", "加入购物车")
            xp = (
                f'//*[@clickable="true" and (contains(@content-desc,"{lab}") '
                f'or contains(@text,"{lab}"))]'
            )
            if self._tap_first_displayed(
                AppiumBy.XPATH,
                xp,
                require_bottom_half=bottom,
            ):
                logger.info("已点规格层「%s」", lab)
                time.sleep(0.5)
                return True
        return False


    def _pick_highest_visible_spec_row(
        self, w: int, h: int, *, top_y_ratio: float = 0.2
    ) -> bool:
        """
        多规格底部弹层：收集带价的可点行；若至少两种不同价格则点最高价行，
        再点底部「加购」或「确定」等（Inspector：加购在 content-desc 内）。
        top_y_ratio：忽略屏上方多高的节点；详情页规格靠上时宜调小（如 0.05）。
        """
        time.sleep(0.38)
        y_cut = int(h * float(top_y_ratio))
        rows: List[Tuple[float, Any]] = []
        xps = (
            '//android.widget.ScrollView//*[@clickable="true"][contains(@content-desc,"₱")]',
            '//android.widget.ScrollView//*[@clickable="true"][contains(@text,"₱")]',
            '//android.widget.ScrollView//*[@clickable="true"][contains(@content-desc,"¥")]',
            '//*[@clickable="true"][contains(@content-desc,"₱")]',
            '//*[@clickable="true"][contains(@content-desc,"¥")]',
            '//*[@clickable="true"][contains(@content-desc,"￥")]',
            '//*[@clickable="true"][contains(@text,"₱")]',
            '//*[@clickable="true"][contains(@text,"¥")]',
            '//android.widget.TextView[@clickable="true"][contains(@text,"₱")]',
        )
        for xp in xps:
            try:
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    try:
                        if not el.is_displayed():
                            continue
                        y0 = int(el.location.get("y", 0))
                        if y0 < y_cut:
                            continue
                        blob = self._element_merchant_blob(el)
                        if blob.strip().startswith("加购"):
                            continue
                        if "加购" in blob and "罐" not in blob and "箱" not in blob and "pic" not in blob.lower():
                            if len(blob) < 36:
                                continue
                        p = self._parse_price_amount_from_blob(blob)
                        if p is None:
                            continue
                        rows.append((p, el))
                    except Exception:
                        continue
            except Exception:
                continue
        distinct = {round(t[0], 2) for t in rows}
        if len(distinct) >= 2:
            max_p = max(distinct)
            for pr, el in rows:
                if abs(pr - max_p) < 0.02:
                    if self._coord_tap_or_click(el, "已点最高价规格行"):
                        logger.info("多规格：已选价高约 %.2f", max_p)
                        time.sleep(0.4)
                        if self._tap_spec_sheet_primary_button():
                            return True
                        return True
            logger.warning("多规格：未能点中最高价行，改试底部加购/确定")
            return self._tap_spec_sheet_primary_button()
        if len(rows) == 1:
            logger.info("规格层仅见一行带价，尝试直接点底部加购")
        return self._tap_spec_sheet_primary_button()

    @staticmethod

    def _element_class_name(el: Any) -> str:
        try:
            return (el.get_attribute("class") or "") or ""
        except Exception:
            return ""


    def _collect_main_area_price_cards_ranked(
        self,
        w: int,
        h: int,
        *,
        min_desc_len: int = 6,
        x_main_ratio: float = 0.21,
        y_min_ratio: float = 0.155,
        y_max_ratio: float = 0.82,
        min_row_height: int = 88,
        imageview_only: bool = False,
    ) -> List[Tuple[int, Any]]:
        """
        主商品区含价卡片，按屏幕上边 y 升序；同一行父子节点 y 接近时只保留一条（避免重复）。
        默认过滤顶栏/底栏间 y，并优先 **ImageView** 商品大图（与 Inspector 首条一致）。
        """
        x_main = int(w * x_main_ratio)
        y_lo = int(h * float(y_min_ratio))
        y_hi = int(h * float(y_max_ratio))
        raw: List[Tuple[int, int, int, Any]] = []
        seen: Set[str] = set()
        xps_all = (
            '//android.widget.ImageView[contains(@content-desc,"₱")]',
            '//android.widget.ImageView[contains(@text,"₱")]',
            '//android.view.View[contains(@content-desc,"₱")]',
            '//*[contains(@content-desc,"₱") or contains(@content-desc,"P ")]',
            '//*[contains(@content-desc,"P") and contains(@content-desc,".")]',
        )
        xps_iv = (
            '//android.widget.ImageView[contains(@content-desc,"₱")]',
            '//android.widget.ImageView[contains(@text,"₱")]',
        )
        xps = xps_iv if imageview_only else xps_all

        def _consider(el: Any) -> None:
            try:
                eid = getattr(el, "id", None) or str(id(el))
                if eid in seen:
                    return
                if not el.is_displayed():
                    return
                cls = self._element_class_name(el)
                if imageview_only and "ImageView" not in cls:
                    return
                blob = self._element_merchant_blob(el)
                if len(blob) < min_desc_len:
                    return
                if not self._blob_has_price_hint(blob):
                    return
                x0 = int(el.location.get("x", 0))
                if x0 < x_main:
                    return
                y0 = int(el.location.get("y", 0))
                hh = max(1, int(el.size.get("height", 0)))
                if y0 < y_lo or y0 + hh > y_hi or hh < min_row_height:
                    return
                pri = 0 if "ImageView" in cls else 1
                seen.add(eid)
                raw.append((y0, pri, hh, el))
            except Exception:
                return

        for xp in xps:
            try:
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    _consider(el)
            except Exception:
                continue
        if imageview_only and not raw:
            return self._collect_main_area_price_cards_ranked(
                w,
                h,
                min_desc_len=min_desc_len,
                x_main_ratio=x_main_ratio,
                y_min_ratio=y_min_ratio,
                y_max_ratio=y_max_ratio,
                min_row_height=min_row_height,
                imageview_only=False,
            )
        raw.sort(key=lambda t: (t[0], t[1], -t[2]))
        out: List[Tuple[int, Any]] = []
        for y0, _pri, hh, el in raw:
            if out and (y0 - out[-1][0]) < max(56, int(hh * 0.42)):
                continue
            out.append((y0, el))
        return out


    def _try_open_add_on_price_card(self, card: Any) -> bool:
        """对单张商品卡尝试小加号 → 右下角手势 → 整卡点击。"""
        try:
            for sub in card.find_elements(
                AppiumBy.XPATH,
                './/android.view.View[@clickable="true"]',
            ):
                try:
                    if not sub.is_displayed():
                        continue
                    sz = sub.size
                    ww = int(sz.get("width", 0))
                    hh = int(sz.get("height", 0))
                    if 18 <= ww <= 120 and 18 <= hh <= 120:
                        sub.click()
                        logger.info("已点击商品卡内加号 View (%d×%d)", ww, hh)
                        time.sleep(0.55)
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        try:
            loc = card.location
            sz = card.size
            cw = int(sz.get("width", 0))
            ch = int(sz.get("height", 0))
            if cw > 80 and ch > 80:
                ax = int(loc.get("x", 0)) + int(cw * 0.88)
                ay = int(loc.get("y", 0)) + int(ch * 0.88)
                self.driver.execute_script(
                    "mobile: clickGesture",
                    {"x": ax, "y": ay},
                )
                logger.info("已点商品卡右下角加号区 (%d,%d)", ax, ay)
                time.sleep(0.55)
                return True
        except Exception:
            pass
        return self._coord_tap_or_click(card, "已点整张商品卡")
    

    def _strict_find_first_product_image_under_category(
        self, category_desc: str, w: int
    ) -> Optional[Any]:
        """
        Inspector 严格思路：侧栏 ``content-desc=分类名`` 的节点之后（following-sibling
        或父级兄弟）主区内 **第一个足够大的** ``ImageView``（首张商品图）。
        与「全屏 y 排序 + 含价」解耦，避免误点第二条或误滑侧栏。
        """
        cat = (category_desc or "店内招牌").strip() or "店内招牌"
        if '"' in cat or "'" in cat:
            logger.warning(
                "分类名含引号，严格 XPath 可能失效，退回通用路径: %r",
                cat[:40],
            )
            return None
        templates = (
            '(//android.view.View[@content-desc="{c}"]/following-sibling::*//android.widget.ImageView)[1]',
            '(//*[@content-desc="{c}"]/following-sibling::*//android.widget.ImageView)[1]',
            '(//android.view.View[@content-desc="{c}"]/following-sibling::android.view.View//android.widget.ImageView)[1]',
            '(//*[@content-desc="{c}"]/following-sibling::android.view.View//android.widget.ImageView)[1]',
            '(//android.view.View[@content-desc="{c}"]/following-sibling::android.widget.ImageView)[1]',
            '(//android.view.View[@content-desc="{c}"]/../following-sibling::*//android.widget.ImageView)[1]',
            '(//*[@content-desc="{c}"]/../following-sibling::*//android.widget.ImageView)[1]',
        )
        for tpl in templates:
            xp = tpl.format(c=cat)
            try:
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    try:
                        if not el.is_displayed():
                            continue
                        sz = el.size
                        wv = int(sz.get("width", 0))
                        hv = int(sz.get("height", 0))
                        if wv < 48 or hv < 48:
                            continue
                        loc = el.location
                        x0 = int(loc.get("x", 0))
                        if x0 < int(w * 0.12):
                            continue
                    except Exception:
                        continue
                    logger.info("严格 XPath 命中首张商品图: %s", xp[:120])
                    return el
            except Exception:
                continue
        return None
    

    def shop_detail_add_first_visible_product_highest_spec(
        self, sidebar_category: str = "店内招牌",
    ) -> bool:
        """
        与业务一致：主列表 **第一条** 商品 → 进 **详情/规格** → 多规格时选 **价高**
        （如 ₱1400 箱装）→ 点 **「加购」**；不进第二条、不点行尾 `+` 误触邻行。
        **优先** 侧栏 ``content-desc=sidebar_category`` 锚点后的首个主区 ``ImageView``
       （与 Inspector 步骤严格一致）；失败再回退含价节点 / 几何 / 坐标。
        调用前应先 ``shop_detail_scroll_to_category`` 点到同一分类名。
        """
        w, h = self._window_size_safe()
        time.sleep(0.82)
        target: Optional[Any] = None
        how = ""
        _y0 = -1
        strict_el = self._strict_find_first_product_image_under_category(
            sidebar_category, w
        )
        if strict_el is not None:
            target = strict_el
            how = "严格侧栏锚点首图"
            try:
                _y0 = int(strict_el.location.get("y", -1))
            except Exception:
                _y0 = -1
        if target is None:
            ranked = self._collect_main_area_price_cards_ranked(
                w, h, min_desc_len=8, imageview_only=True
            )
            if not ranked:
                ranked = self._collect_main_area_price_cards_ranked(w, h, min_desc_len=4)
            if not ranked:
                ranked = self._collect_main_area_price_cards_ranked(
                    w, h, min_desc_len=2, x_main_ratio=0.16
                )
            if ranked:
                target = ranked[0][1]
                _y0 = ranked[0][0]
                how = "含价节点"
            else:
                target = self._first_main_area_product_row_geometry(w, h)
                _y0 = -1
                how = "几何首行"
        if target is None:
            logger.warning("树/几何均未命中首条，走主区坐标兜底（详情→价高→加购）")
            if self._shop_detail_tap_first_product_coordinate_fallback(w, h):
                time.sleep(0.4)
                return True
            return self.shop_detail_add_first_product_plus()
        logger.info(
            "商品加购：%s y≈%s → 点击中部进入详情",
            how,
            _y0 if _y0 >= 0 else "?",
        )
        if not self._tap_open_product_detail_center(target):
            if not self._coord_tap_or_click(target, "已点主区首张商品卡"):
                if self._shop_detail_tap_first_product_coordinate_fallback(w, h):
                    time.sleep(0.4)
                    return True
                return self.shop_detail_add_first_product_plus()
        time.sleep(1.15)
        ok = self._pick_highest_visible_spec_row(w, h, top_y_ratio=0.05)
        if not ok:
            ok = self._tap_spec_sheet_primary_button()
        if not ok:
            logger.warning("详情规格/加购未完成，试主区坐标兜底后再退回列表")
            if self._shop_detail_tap_first_product_coordinate_fallback(w, h):
                time.sleep(0.4)
                return True
            try:
                self.driver.back()
                time.sleep(0.55)
            except Exception:
                pass
            return self.shop_detail_add_first_product_plus()
        time.sleep(0.45)
        return True
    

    def shop_detail_add_first_product_plus(self) -> bool:
        """按主区屏序 y 最小的一张含 ₱ 卡加购，并处理多规格（价高 + 加购）。"""
        w, h = self._window_size_safe()
        for xp in (
            '(//android.widget.ImageView[contains(@content-desc,"₱")])[1]//android.view.View[@clickable="true"]',
            '(//android.view.View[contains(@content-desc,"₱")])[1]//android.view.View[@clickable="true"]',
        ):
            try:
                for card in self.driver.find_elements(AppiumBy.XPATH, xp):
                    try:
                        if not card.is_displayed():
                            continue
                        sz = card.size
                        if sz.get("width", 999) <= 120 and sz.get("height", 999) <= 120:
                            card.click()
                            logger.info("已点击首个商品的加号（XPath 子 View）")
                            time.sleep(0.75)
                            if not self._pick_highest_visible_spec_row(w, h):
                                logger.warning("规格层未完整处理（XPath 子 View 路径）")
                            return True
                    except Exception:
                        continue
            except Exception:
                pass
        ranked = self._collect_main_area_price_cards_ranked(
            w, h, min_desc_len=6, imageview_only=True
        )
        if not ranked:
            ranked = self._collect_main_area_price_cards_ranked(
                w, h, min_desc_len=2, x_main_ratio=0.16
            )
        if not ranked:
            geom = self._first_main_area_product_row_geometry(w, h)
            if geom and self._tap_open_product_detail_center(geom):
                time.sleep(1.05)
                if self._pick_highest_visible_spec_row(
                    w, h, top_y_ratio=0.05
                ) or self._tap_spec_sheet_primary_button():
                    return True
            if self._shop_detail_tap_first_product_coordinate_fallback(w, h):
                return True
            logger.error("未找到主区含价的商品卡")
            return False
        _y0, card = ranked[0]
        logger.info("fallback：仅主区屏序第一张含价卡 y≈%d", _y0)
        if self._try_open_add_on_price_card(card):
            time.sleep(0.45)
            if not self._pick_highest_visible_spec_row(w, h):
                logger.warning("规格层未完整处理（fallback 路径）")
            return True
        logger.error("未找到首张商品卡的加号按钮")
        return False
    

    def shop_tap_bottom_cart_bar(self) -> bool:
        """
        加购后唤起底部购物车弹层。Flutter 底栏常为整段 ``content-desc``，``el.click()`` 易失效，
        优先 ``clickGesture``；并尝试 ``text`` / 「已选…件」/ 左下角坐标兜底。
        """
        w, h = self._window_size_safe()
        time.sleep(0.95)
        y_min = int(h * 0.56)
        xpaths = (
            _XPATH_DESC_CART,
            '//*[contains(@text,"购物车")]',
            '//*[contains(@content-desc,"已选") and contains(@content-desc,"件")]',
            '//*[contains(@content-desc,"共") and contains(@content-desc,"件")]',
        )
        for attempt in range(2):
            for xp in xpaths:
                try:
                    with self._maybe_zero_implicit_wait():
                        for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                            try:
                                if not el.is_displayed():
                                    continue
                                if int(el.location.get("y", 0)) < y_min:
                                    continue
                                if self._coord_tap_or_click(
                                    el, "已点击底部购物车条"
                                ):
                                    time.sleep(0.95)
                                    return True
                            except Exception:
                                continue
                except Exception:
                    continue
            try:
                esc = self._uia_desc_escape("购物车")
                for sel in (
                    f'new UiSelector().descriptionContains("{esc}")',
                ):
                    for el in self.driver.find_elements(
                        AppiumBy.ANDROID_UIAUTOMATOR, sel
                    ):
                        try:
                            if not el.is_displayed():
                                continue
                            if int(el.location.get("y", 0)) < y_min:
                                continue
                            if self._coord_tap_or_click(
                                el, "已点击底部购物车条（UiAutomator）"
                            ):
                                time.sleep(0.95)
                                return True
                        except Exception:
                            continue
            except Exception:
                pass
            if attempt == 0:
                time.sleep(0.55)
        for xf, yf in ((0.11, 0.915), (0.15, 0.925), (0.08, 0.905), (0.20, 0.91)):
            cx, cy = int(w * xf), int(h * yf)
            try:
                self.driver.execute_script(
                    "mobile: clickGesture", {"x": cx, "y": cy}
                )
                logger.info("底部购物车条坐标兜底 (%d,%d)", cx, cy)
                time.sleep(0.9)
                return True
            except Exception:
                continue
        return False
    

    def shop_tap_go_checkout(self) -> bool:
        w, h = self._window_size_safe()
        time.sleep(0.4)
        for xp in (
            '//*[contains(@content-desc,"去结算")]',
            '//*[contains(@text,"去结算")]',
            '//android.widget.TextView[@text="去结算"]',
        ):
            try:
                with self._maybe_zero_implicit_wait():
                    for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                        try:
                            if not el.is_displayed():
                                continue
                            if self._coord_tap_or_click(el, "已点击「去结算」"):
                                time.sleep(1.15)
                                return True
                        except Exception:
                            continue
            except Exception:
                pass
        try:
            for el in self.driver.find_elements(
                AppiumBy.ANDROID_UIAUTOMATOR,
                'new UiSelector().textContains("去结算")',
            ):
                try:
                    if el.is_displayed() and self._coord_tap_or_click(
                        el, "已点击「去结算」（UiAutomator）"
                    ):
                        time.sleep(1.15)
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        for xf, yf in ((0.82, 0.86), (0.76, 0.85), (0.88, 0.88)):
            cx, cy = int(w * xf), int(h * yf)
            if cy < int(h * 0.62):
                continue
            try:
                self.driver.execute_script(
                    "mobile: clickGesture", {"x": cx, "y": cy}
                )
                logger.info("「去结算」坐标兜底 (%d,%d)", cx, cy)
                time.sleep(1.15)
                return True
            except Exception:
                continue
        return False
    

    def shop_tap_confirm_pay_bar(self) -> bool:
        """
        结算底栏文案可能是「确认支付」「提交订单」「立即支付」等，且 Flutter 常只在
        ``@text`` 或只在 ``@content-desc`` 上带文案；多轮等待以覆盖结算页慢渲染。
        """
        w, h = self._window_size_safe()
        y_cut = h // 2
        labels = ("确认支付", "提交订单", "立即支付", "去支付")
        for attempt in range(6):
            if attempt:
                time.sleep(0.48)
            else:
                time.sleep(0.55)
            for label in labels:
                for xp in (
                    f'//*[contains(@content-desc,"{label}")]',
                    f'//*[contains(@text,"{label}")]',
                ):
                    try:
                        for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                            try:
                                if not el.is_displayed():
                                    continue
                                if int(el.location.get("y", 0)) < y_cut:
                                    continue
                                if self._coord_tap_or_click(el, f"已点结算底栏「{label}」"):
                                    logger.info("已点击「%s」", label)
                                    time.sleep(1.0)
                                    return True
                            except Exception:
                                continue
                    except Exception:
                        pass
                for desc_key, tmpl in (
                    ("text", 'new UiSelector().textContains("{lb}").clickable(true)'),
                    (
                        "desc",
                        'new UiSelector().descriptionContains("{lb}").clickable(true)',
                    ),
                ):
                    try:
                        uia = tmpl.format(lb=label)
                        for el in self.driver.find_elements(
                            AppiumBy.ANDROID_UIAUTOMATOR, uia
                        ):
                            try:
                                if not el.is_displayed():
                                    continue
                                if int(el.location.get("y", 0)) < y_cut:
                                    continue
                                if self._coord_tap_or_click(
                                    el,
                                    f"已点「{label}」（UiAutomator {desc_key}）",
                                ):
                                    logger.info("已点击「%s」", label)
                                    time.sleep(1.0)
                                    return True
                            except Exception:
                                continue
                    except Exception:
                        pass
        for yf in (0.905, 0.92, 0.88, 0.94, 0.86):
            cx, cy = int(w * 0.5), int(h * yf)
            if cy < int(h * 0.62):
                continue
            try:
                self.driver.execute_script(
                    "mobile: clickGesture", {"x": cx, "y": cy}
                )
                logger.info("「确认支付」坐标兜底 (%d,%d)", cx, cy)
                time.sleep(1.0)
                return True
            except Exception:
                continue
        return False
    

    def _address_sheet_label_skippable(self, blob: str, *, short_max: int = 28) -> bool:
        """短条多为标题/按钮；长条多为具体地址，不因含个别词整行丢弃。"""
        s = (blob or "").strip()
        if not s:
            return True
        if len(s) > short_max:
            return False
        chrome = (
            "新增地址",
            "请选择收货地址",
            "请选择",
            "提交订单",
            "提交",
            "取消",
            "关闭",
            "去结算",
            "确认支付",
            "管理地址",
            "编辑",
        )
        return any(k in s for k in chrome)
    

    def _looks_like_address_row_blob(self, blob: str) -> bool:
        """Flutter 地址行：手机号可能带空格/横线，不必 9 位连在一起。"""
        s = (blob or "").strip().replace("：", ":")
        if len(s) < 10:
            return False
        if self._address_sheet_label_skippable(s):
            return False
        if re.search(r"\d{6,}", s):
            return True
        if re.search(r"09\d{9}", re.sub(r"\s+", "", s)):
            return True
        markers = (
            "省",
            "市",
            "区",
            "路",
            "巷",
            "号",
            "室",
            "座",
            "Barangay",
            "Manila",
            "Street",
            "Blk",
            "Unit",
            "Floor",
            "收货人",
            "默认",
        )
        return len(s) >= 14 and any(m in s for m in markers)
    

    def _gather_address_sheet_candidates(self) -> List[Any]:
        out: List[Any] = []
        seen: Set[int] = set()
        queries = (
            '//android.view.View[@clickable="true"]',
            '//android.widget.TextView[@clickable="true"]',
            '//*[@clickable="true" and string-length(@content-desc)>12]',
        )
        for xp in queries:
            try:
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    try:
                        eid = id(el)
                        if eid in seen:
                            continue
                        if not el.is_displayed():
                            continue
                        d = (el.get_attribute("content-desc") or "").strip()
                        t = (el.get_attribute("text") or "").strip()
                        if self._looks_like_address_row_blob(d) or self._looks_like_address_row_blob(
                            t
                        ):
                            seen.add(eid)
                            out.append(el)
                    except Exception:
                        continue
            except Exception:
                continue
        return out
    

    def _scroll_address_sheet_list_once(self, w: int, h: int, step: int) -> None:
        """弹窗列表区域上滑，露出下方地址行（勿用中线全屏，减少误触关闭）。"""
        try:
            self.driver.execute_script(
                "mobile: swipeGesture",
                {
                    "left": int(w * 0.22),
                    "top": int(h * 0.38),
                    "width": int(w * 0.56),
                    "height": int(h * 0.42),
                    "direction": "up",
                    "percent": 0.52 + (step % 3) * 0.06,
                },
            )
        except Exception:
            try:
                x = int(w * (0.42 + (step % 4) * 0.05))
                self.driver.swipe(x, int(h * 0.66), x, int(h * 0.36), 420)
            except Exception:
                pass
        time.sleep(0.32)
    

    def shop_pick_random_address_in_sheet(self, *, _retry_depth: int = 0) -> bool:
        time.sleep(0.85)
        try:
            w = self._window_size_safe()[0]
            h = self._window_height()
        except Exception:
            w, h = 1080, 2200
    
        max_scroll_rounds = 14
        for rnd in range(max_scroll_rounds + 1):
            candidates = self._gather_address_sheet_candidates()
            if candidates:
                pick = random.choice(candidates)
                if self._coord_tap_or_click(pick, "已随机选择一条地址"):
                    logger.info("已随机选择一条地址")
                    time.sleep(1.0)
                    return True
            if rnd < max_scroll_rounds:
                if rnd % 4 == 0 and rnd > 0:
                    logger.info(
                        "地址弹窗内上滑查找，第 %d/%d 轮…",
                        rnd,
                        max_scroll_rounds,
                    )
                self._scroll_address_sheet_list_once(w, h, rnd)
    
        if _retry_depth < 2 and self._tap_first_displayed(
            AppiumBy.XPATH, _XPATH_DESC_SELECT_ADDRESS
        ):
            time.sleep(1.0)
            return self.shop_pick_random_address_in_sheet(
                _retry_depth=_retry_depth + 1
            )
        logger.warning("未找到可选地址条目")
        return False
    

    def shop_select_balance_payment(self) -> bool:
        time.sleep(0.6)
        if self._tap_first_displayed(
            AppiumBy.XPATH,
            '//*[contains(@content-desc,"可用余额")]',
        ):
            logger.info("已选择余额支付")
            time.sleep(0.8)
            return True
        if self._tap_first_displayed(
            AppiumBy.XPATH,
            '//*[contains(@content-desc,"余额")]',
        ):
            logger.info("已点击含「余额」的支付方式")
            time.sleep(0.8)
            return True
        return False
    

    def shop_select_cash_on_delivery_payment(self) -> bool:
        """提交页支付方式弹层内点「货到付款」等（不进余额、不输支付密码）。"""
        time.sleep(0.6)
        for sub in ("货到付款", "到付", "现金支付", "当面付款"):
            if self._tap_first_displayed(
                AppiumBy.XPATH,
                f'//*[contains(@content-desc,"{sub}")]',
            ) or self._tap_first_displayed(
                AppiumBy.XPATH,
                f'//*[contains(@text,"{sub}")]',
            ):
                logger.info("已选择货到付款类支付方式（匹配「%s」）", sub)
                time.sleep(0.8)
                return True
        try:
            for esc in ("货到付款", "到付"):
                safe = self._uia_desc_escape(esc)
                sel = f'new UiSelector().descriptionContains("{safe}")'
                for el in self.driver.find_elements(
                    AppiumBy.ANDROID_UIAUTOMATOR, sel
                ):
                    try:
                        if el.is_displayed() and self._coord_tap_or_click(
                            el, "已点货到付款（UiAutomator）"
                        ):
                            time.sleep(0.8)
                            return True
                    except Exception:
                        continue
        except Exception:
            pass
        return False
    

    def shop_enter_pay_password(self, password: str = "123456") -> bool:
        time.sleep(0.5)
        try:
            self._wait(8).until(
                EC.presence_of_element_located(
                    (
                        AppiumBy.XPATH,
                        '//*[contains(@content-desc,"请输入支付密码") or contains(@text,"请输入支付密码")]',
                    )
                )
            )
        except TimeoutException:
            # 须先于 WebDriverException：TimeoutException 是其子类，否则会被误捕获并 re-raise
            logger.warning("未检测到支付密码弹窗标题，仍尝试点数字键")
        except WebDriverException as ex:
            if "instrumentation process is not running" in str(ex).lower():
                logger.error("支付密码阶段失败：UiAutomator2 instrumentation 已崩溃")
                return False
            raise
        for ch in password:
            tapped = False
            for xp in (
                f'//android.view.View[@content-desc="{ch}"]',
                f'//android.widget.TextView[@text="{ch}"]',
                f'//android.widget.Button[@text="{ch}"]',
            ):
                if self._tap_first_displayed(AppiumBy.XPATH, xp):
                    tapped = True
                    time.sleep(0.18)
                    break
            if not tapped:
                try:
                    self.driver.find_element(
                        AppiumBy.ANDROID_UIAUTOMATOR,
                        f'new UiSelector().text("{ch}")',
                    ).click()
                    time.sleep(0.18)
                except WebDriverException as ex:
                    if "instrumentation process is not running" in str(ex).lower():
                        logger.error("输入支付密码中断：UiAutomator2 instrumentation 已崩溃")
                        return False
                    logger.warning("未点到密码键「%s」: %s", ch, ex)
                except Exception:
                    logger.warning("未点到密码键「%s」", ch)
        time.sleep(1.2)
        return True
    

    def run_shop_checkout_pay_and_cancel_flow(
        self,
        pay_password: str = "123456",
        *,
        category: Optional[str] = None,
        category_aliases: Optional[Sequence[str]] = None,
        delivery_prefer_scheduled: bool = False,
        delivery_slot_contains: Optional[str] = None,
        delivery_time_slot_ordinal: Optional[int] = None,
        checkout_payment: str = "balance",
    ) -> bool:
        """
        ``checkout_payment``：``balance``（默认）选余额并输支付密码；
        ``cod`` / 传 ``\"货到付款\"`` 选货到付款并跳过 ``shop_enter_pay_password``。
        """
        logger.info("店铺详情：开始下单支付并取消流程…")
        cat = (category or "").strip() or "店内招牌"
        aliases = (
            list(category_aliases)
            if category_aliases
            else None
        )
        logger.info(
            "侧栏：先进入分类「%s」，再在主区首个含价商品上加购（多规格选价高）",
            cat,
        )
        if not self.shop_detail_scroll_to_category(
            cat, category_aliases=aliases
        ):
            logger.error("未点到侧栏分类「%s」，终止加购", cat)
            return False
        time.sleep(0.55)
        if not self.shop_detail_add_first_visible_product_highest_spec(cat):
            logger.error("主区首个商品加购失败（加号/规格层未就绪）")
            return False
        if not self.shop_tap_bottom_cart_bar():
            logger.warning("底部购物车条未点到，尝试直接去结算类入口")
        if not self.shop_tap_go_checkout():
            time.sleep(0.55)
            if self.shop_tap_bottom_cart_bar():
                time.sleep(0.5)
            if not self.shop_tap_go_checkout():
                logger.error("未点到「去结算」")
                return False
        if not self.shop_tap_confirm_pay_bar():
            logger.error("首次「确认支付」失败")
            return False
        time.sleep(0.6)
        ok_addr = self.shop_pick_random_address_in_sheet()
        if not ok_addr:
            self._tap_first_displayed(AppiumBy.XPATH, _XPATH_DESC_SELECT_ADDRESS)
            time.sleep(0.8)
            ok_addr = self.shop_pick_random_address_in_sheet()
        if not ok_addr:
            logger.warning("地址选择可能失败，继续尝试支付方式")
        raw = (checkout_payment or "balance").strip()
        low = raw.lower()
        if low in ("cod", "cash_on_delivery") or raw in (
            "货到付款",
            "货到",
        ):
            pay_mode = "cod"
        else:
            pay_mode = "balance"
        if pay_mode == "cod":
            if not self.shop_select_cash_on_delivery_payment():
                logger.warning("货到付款未点到，请检查支付方式树")
        else:
            if not self.shop_select_balance_payment():
                logger.warning("余额支付未点到，请检查支付方式树")
        time.sleep(1.0)
        slot_ok = self.shop_open_delivery_time_and_pick_future_slot(
            prefer_scheduled=delivery_prefer_scheduled,
            preferred_slot_contains=delivery_slot_contains,
            delivery_time_slot_ordinal=delivery_time_slot_ordinal,
        )
        if not slot_ok:
            logger.error("未选到配送时段，终止支付流程")
            return False
        time.sleep(0.5)
        if not self.shop_tap_confirm_pay_bar():
            logger.error("第二次「确认支付」未点到，终止支付流程")
            return False
        if pay_mode == "cod":
            time.sleep(1.0)
            logger.info("货到付款：跳过输入支付密码")
        else:
            if not self.shop_enter_pay_password(pay_password):
                logger.error("输入支付密码失败，终止流程")
                return False
        if not self.shop_assert_order_detail_cancel_visible():
            return False
        if not self.shop_cancel_order_flow():
            logger.error("取消流程失败：未提交成功或取消结果校验未通过")
            return False
        logger.info("店铺下单→支付→取消 流程已执行完毕")
        return True
