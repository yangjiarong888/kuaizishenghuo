"""店铺详情下单流程（TakeoutPageBase 混入）。"""
from __future__ import annotations

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



class TakeoutDeliveryTimeMixin:

    def _collect_delivery_hint_elements(
        self, hint: str, h: int, *, min_y_ratio: float = 0.03
    ) -> List[Any]:
        """按 y 从大到小排序，优先点偏下的配送行；min_y 勿过大以免漏掉中部提交区内的入口。"""
        ymin = int(h * min_y_ratio)
        xps = (
            f'//*[contains(@content-desc,"{hint}")]',
            f'//*[contains(@text,"{hint}")]',
        )
        scored: List[Tuple[int, Any]] = []
        for xp in xps:
            try:
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    try:
                        if not el.is_displayed():
                            continue
                        y = int(el.location.get("y", 0))
                        if y < ymin:
                            continue
                        scored.append((y, el))
                    except Exception:
                        continue
            except Exception:
                pass
        scored.sort(key=lambda t: -t[0])
        return [el for _, el in scored]
    

    def _scroll_checkout_form_reveal_delivery(self, w: int, h: int) -> None:
        """
        提交订单页在选完地址/支付后视口常在 **底部**；「立即配送」在表单 **上方**。
        须 **手指从上往下** 拖主区（start_y < end_y），让滚动条回到偏上位置。
        若用 0.72→0.28 手指上移，Flutter 常继续把内容顶向文档底部，看起来像下滑、卡住。
        """
        for x in (int(w * 0.52), int(w * 0.48), int(w * 0.58)):
            try:
                self.driver.swipe(
                    x, int(h * 0.30), x, int(h * 0.72), 450
                )
            except Exception:
                try:
                    self.driver.execute_script(
                        "mobile: swipeGesture",
                        {
                            "left": int(w * 0.28),
                            "top": int(h * 0.18),
                            "width": int(w * 0.50),
                            "height": int(h * 0.58),
                            "direction": "down",
                            "percent": 0.48,
                        },
                    )
                except Exception:
                    pass
            time.sleep(0.12)
    

    def _tap_delivery_opener_flutter(self, hint: str, h: int, log: str) -> bool:
        """Flutter：整行 desc 常为「立即配送 4月10日 17:32-17:47 送达」，须 contains 再坐标点。"""
        safe = hint.replace('"', "").replace("'", "")
        if safe:
            try:
                for xp in (
                    f'//android.view.View[contains(@content-desc,"{safe}")]',
                    f'//*[contains(@content-desc,"{safe}")]',
                ):
                    scored: List[Tuple[int, Any]] = []
                    for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                        try:
                            if not el.is_displayed():
                                continue
                            y = int(el.location.get("y", 0))
                            if y < int(h * 0.06):
                                continue
                            scored.append((y, el))
                        except Exception:
                            continue
                    scored.sort(key=lambda t: -t[0])
                    for _, el in scored[:6]:
                        if self._coord_tap_or_click(el, log):
                            return True
            except Exception:
                pass
        if "'" not in hint and '"' not in hint:
            try:
                xp = f'//android.view.View[@content-desc="{hint}"]'
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    try:
                        y = int(el.location.get("y", 0))
                        if y < int(h * 0.06):
                            continue
                        if self._coord_tap_or_click(el, log):
                            return True
                    except Exception:
                        continue
            except Exception:
                pass
        try:
            esc = self._uia_desc_escape(hint)
            for sel in (
                f'new UiSelector().description("{esc}")',
                f'new UiSelector().description("{esc}").clickable(true)',
                f'new UiSelector().descriptionContains("{esc}")',
            ):
                scored: List[Tuple[int, Any]] = []
                for el in self.driver.find_elements(
                    AppiumBy.ANDROID_UIAUTOMATOR, sel
                ):
                    try:
                        if not el.is_displayed():
                            continue
                        y = int(el.location.get("y", 0))
                        if y < int(h * 0.05):
                            continue
                        scored.append((y, el))
                    except Exception:
                        continue
                scored.sort(key=lambda t: -t[0])
                for _, el in scored[:8]:
                    if self._coord_tap_or_click(el, log):
                        return True
        except Exception:
            pass
        return False
    

    def _open_delivery_time_picker_sheet(
        self, w: int, h: int, *, prefer_scheduled: bool = False
    ) -> bool:
        """
        唤起配送/预约时段弹层；Flutter 多为整行 ``content-desc``。
        **默认** ``prefer_scheduled=False``：与常见流程一致——先 **「立即配送」**
        唤起时段弹层，再选日期/时间（即使要选「后天」也是先点立即配送这一行）。
        ``prefer_scheduled=True`` 时先尝试「预约配送」等（双 Tab 的 App 用）。
        """
        scheduled = (
            ("预约配送", "已点「预约配送」唤起配送时段"),
            ("预约送达", "已点「预约送达」唤起配送时段"),
            ("预约时间", "已点「预约时间」唤起配送时段"),
        )
        neutral = (
            ("送达时间", "已点「送达时间」唤起配送时段"),
            ("配送时间", "已点「配送时间」唤起配送时段"),
            ("选择送达时间", "已点「选择送达时间」唤起配送时段"),
            ("指定时间", "已点「指定时间」唤起配送时段"),
        )
        immediate = (("立即配送", "已点「立即配送」唤起配送时段"),)
        if prefer_scheduled:
            openers = scheduled + neutral + immediate
        else:
            openers = immediate + scheduled + neutral
        with self._maybe_zero_implicit_wait():
            for hint, log in openers:
                if self._tap_delivery_opener_flutter(hint, h, log):
                    return True
                for el in self._collect_delivery_hint_elements(hint, h)[:10]:
                    if self._coord_tap_or_click(el, log):
                        return True
                try:
                    esc = self._uia_desc_escape(hint)
                    sel = f'new UiSelector().textContains("{esc}")'
                    scored: List[Tuple[int, Any]] = []
                    for el in self.driver.find_elements(
                        AppiumBy.ANDROID_UIAUTOMATOR, sel
                    ):
                        try:
                            if not el.is_displayed():
                                continue
                            y = int(el.location.get("y", 0))
                            if y < int(h * 0.05):
                                continue
                            scored.append((y, el))
                        except Exception:
                            continue
                    scored.sort(key=lambda t: -t[0])
                    for _, el in scored[:6]:
                        if self._coord_tap_or_click(el, log):
                            return True
                except Exception:
                    pass
        return False
    

    def _looks_like_time_slot_label(self, label: str) -> bool:
        """匹配时段文案：整段为 02:30，或文案中含独立 ``01:40``（与 Flutter content-desc 一致）。"""
        s = (label or "").strip()
        if not s:
            return False
        s = s.replace("：", ":").replace("－", "-").replace("–", "-")
        if re.match(r"^\d{1,2}:\d{2}$", s):
            return True
        if re.match(r"^\d{1,2}:\d{2}\s*[-~至]\s*\d{1,2}:\d{2}$", s):
            return True
        if re.search(r"(?<![0-9])\d{1,2}:\d{2}(?![0-9])", s):
            return True
        return False
    

    def _format_future_date_cn_fragments(self, days: int) -> List[str]:
        d = date.today() + timedelta(days=days)
        m, dd = d.month, d.day
        raw = (
            f"{m}月{dd}日",
            f"{m}月{dd}",
            f"{m:02d}月{dd:02d}日",
            f"{m:02d}月{dd:02d}",
        )
        out: List[str] = []
        seen: Set[str] = set()
        for s in raw:
            if s not in seen:
                seen.add(s)
                out.append(s)
        return out

    def _format_day_after_tomorrow_cn_fragments(self) -> List[str]:
        """后天在列表里常为「4月25日」而非字面「后天」。"""
        return self._format_future_date_cn_fragments(2)

    def _format_tomorrow_cn_fragments(self) -> List[str]:
        """明天在列表里常只显示动态月日。"""
        return self._format_future_date_cn_fragments(1)
    

    def _collect_date_list_views_ordered(self) -> List[Any]:
        """
        日期竖列表：含「周」或「月」的节点，按 y（再 x）排序；与「第三个 = 后天」脚本一致。
        """
        scored: List[Tuple[int, int, Any]] = []
        queries = (
            '//android.view.View[(contains(@content-desc,"周") or contains(@content-desc,"月"))]',
            '//*[(contains(@content-desc,"周") or contains(@content-desc,"月"))]',
        )
        for xp in queries:
            try:
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    try:
                        if not el.is_displayed():
                            continue
                        desc = (el.get_attribute("content-desc") or "").strip()
                        if "周" not in desc and "月" not in desc:
                            continue
                        loc = el.location
                        y = int(loc.get("y", 0))
                        x = int(loc.get("x", 0))
                        scored.append((y, x, el))
                    except Exception:
                        continue
            except Exception:
                continue
        scored.sort(key=lambda t: (t[0], t[1]))
        merged: List[Any] = []
        last_y = -10_000
        for y, _x, el in scored:
            if y - last_y < 10:
                continue
            merged.append(el)
            last_y = y
        return merged
    

    def _tap_day_after_tomorrow_date_in_sheet(self) -> bool:
        """优先动态日期 ``contains``，再点纵向列表第三项，最后才试字面「后天」。"""
        for frag in self._format_day_after_tomorrow_cn_fragments():
            safe = frag.replace('"', "")
            if not safe:
                continue
            if self._tap_first_displayed(
                AppiumBy.XPATH,
                f'//*[contains(@content-desc,"{safe}")]',
            ) or self._tap_first_displayed(
                AppiumBy.XPATH,
                f'//*[contains(@text,"{safe}")]',
            ):
                logger.info("已选后天等价日期（contains「%s」）", safe)
                time.sleep(0.65)
                return True
        ordered = self._collect_date_list_views_ordered()
        if len(ordered) >= 3:
            if self._coord_tap_or_click(
                ordered[2], "已点日期列表第三项（后天）"
            ):
                logger.info("已选日期：列表第三项（索引 2）")
                time.sleep(0.65)
                return True
        for label in ("后天",):
            if self._tap_first_displayed(
                AppiumBy.XPATH,
                f'//*[contains(@content-desc,"{label}")]',
            ) or self._tap_first_displayed(
                AppiumBy.XPATH,
                f'//*[contains(@text,"{label}")]',
            ):
                logger.info("已选日期「%s」（字面）", label)
                time.sleep(0.65)
                return True
        return False

    def _tap_tomorrow_date_in_sheet(self) -> bool:
        for frag in self._format_tomorrow_cn_fragments():
            safe = frag.replace('"', "")
            if not safe:
                continue
            if self._tap_first_displayed(
                AppiumBy.XPATH,
                f'//*[contains(@content-desc,"{safe}")]',
            ) or self._tap_first_displayed(
                AppiumBy.XPATH,
                f'//*[contains(@text,"{safe}")]',
            ):
                logger.info("已选明天等价日期（动态月日）")
                time.sleep(0.65)
                return True
        ordered = self._collect_date_list_views_ordered()
        if len(ordered) >= 2 and self._coord_tap_or_click(
            ordered[1], "已点日期列表第二项（明天）"
        ):
            logger.info("已选日期：列表第二项（明天）")
            time.sleep(0.65)
            return True
        for selector in (
            '//*[contains(@content-desc,"明天")]',
            '//*[contains(@text,"明天")]',
        ):
            if self._tap_first_displayed(AppiumBy.XPATH, selector):
                logger.info("已选日期「明天」（字面）")
                time.sleep(0.65)
                return True
        return False

    def _tap_allowed_delivery_date_in_sheet(
        self, *, require_day_after_tomorrow: bool = False
    ) -> Optional[str]:
        """Prefer day after tomorrow, then tomorrow; never choose another day."""
        if self._tap_day_after_tomorrow_date_in_sheet():
            return "后天"
        if require_day_after_tomorrow:
            logger.error("完整外卖业务固定选择后天，禁止回退到明天")
            return None
        if self._tap_tomorrow_date_in_sheet():
            return "明天"
        return None
    

    def _tap_delivery_time_confirm_if_present(self) -> None:
        """时段弹层底部「确定」；不存在则忽略。"""
        for xp in (
            '//*[@content-desc="确定"]',
            '//*[contains(@content-desc,"确定")]',
            '//*[@text="确定"]',
        ):
            try:
                if self._tap_first_displayed(AppiumBy.XPATH, xp):
                    logger.info("已点时段弹层「确定」")
                    time.sleep(0.45)
                    return
            except Exception:
                continue
    

    def _scroll_checkout_reveal_delivery_strong(self, w: int, h: int) -> None:
        """首次大幅 **手指下移**（上屏→下屏），把提交区上方配送行滚进视区。"""
        x = int(w * 0.5)
        try:
            self.driver.swipe(x, int(h * 0.24), x, int(h * 0.78), 520)
        except Exception:
            try:
                self.driver.execute_script(
                    "mobile: swipeGesture",
                    {
                        "left": int(w * 0.25),
                        "top": int(h * 0.14),
                        "width": int(w * 0.50),
                        "height": int(h * 0.62),
                        "direction": "down",
                        "percent": 0.52,
                    },
                )
            except Exception:
                pass
        time.sleep(0.25)
    

    def _gather_clickable_time_slot_elements(self, h: int) -> List:
        """
        从 content-desc / text 收集疑似时段节点。
        禁止把 ``//*[@clickable="true"]`` 放首位：Flutter 全树可点节点极多，会导致数分钟卡顿。
        """
        slots: List = []
        seen: set = set()
        y_cut = int(h * 0.22)
        queries = (
            '//*[contains(@content-desc,":")]',
            '//*[contains(@text,":")]',
            '//android.widget.TextView',
            '//android.view.View',
            '//android.widget.Button',
            '//*[@clickable="true"]',
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
                        cy = int(el.location.get("y", 0)) + int(
                            el.size.get("height", 0)
                        ) // 2
                        if cy < y_cut:
                            continue
                        desc = (el.get_attribute("content-desc") or "").strip()
                        text = (el.get_attribute("text") or "").strip()
                        if self._looks_like_time_slot_label(
                            desc
                        ) or self._looks_like_time_slot_label(text):
                            seen.add(eid)
                            slots.append(el)
                    except Exception:
                        continue
            except Exception:
                continue
        return slots
    

    def _filter_time_slots_right_column(self, slots: List, w: int) -> List:
        """时段一般在右侧列表，去掉屏左约 30% 内的误匹配。"""
        out: List = []
        cut = int(w * 0.30)
        for el in slots:
            try:
                loc = el.location
                sz = el.size
                cx = int(loc.get("x", 0)) + int(sz.get("width", 0)) // 2
                if cx >= cut:
                    out.append(el)
            except Exception:
                out.append(el)
        return out if out else slots
    

    def _order_delivery_time_slots_top_down(self, slots: List[Any]) -> List[Any]:
        """
        右侧时段自上而下排序；同一行 y 接近的多节点（父子）只保留 **面积最大** 的一个，
        使「第 5 个」对应屏上第 5 行格子，而不是 XPath 的第 5 个碎片节点。
        """
        rows: List[Tuple[int, int, int, Any]] = []
        for el in slots:
            try:
                loc = el.location
                sz = el.size
                y = int(loc.get("y", 0))
                x = int(loc.get("x", 0))
                area = int(sz.get("width", 0)) * max(1, int(sz.get("height", 0)))
                rows.append((y, x, area, el))
            except Exception:
                continue
        if not rows:
            return []
        rows.sort(key=lambda t: (t[0], t[1]))
        out: List[Any] = []
        y_band = 18
        i = 0
        while i < len(rows):
            y0 = rows[i][0]
            bucket = [rows[i]]
            j = i + 1
            while j < len(rows) and abs(rows[j][0] - y0) <= y_band:
                bucket.append(rows[j])
                j += 1
            best = max(bucket, key=lambda t: t[2])
            out.append(best[3])
            i = j
        return out
    

    def _pick_delivery_time_slot_element(
        self,
        slots: List[Any],
        *,
        preferred_slot_contains: Optional[str],
        slot_ordinal_1based: Optional[int],
    ) -> Tuple[Optional[Any], str]:
        """
        ``slot_ordinal_1based``：1 起算，如 ``5`` = 自上而下第 5 个时段行。
        若同时传 ``preferred_slot_contains``，先在候选里筛含该子串的，再取序数。
        """
        if not slots:
            return None, ""
        pool = list(slots)
        hint = (preferred_slot_contains or "").strip()
        if hint:
            narrowed: List[Any] = []
            for el in pool:
                try:
                    d = el.get_attribute("content-desc") or ""
                    t = el.get_attribute("text") or ""
                    if hint in d or hint in t:
                        narrowed.append(el)
                except Exception:
                    continue
            if not narrowed:
                return None, f"未找到含「{hint}」的时段"
            pool = narrowed
        ordered = self._order_delivery_time_slots_top_down(pool)
        if not ordered:
            return None, ""
        if slot_ordinal_1based is not None and slot_ordinal_1based < 1:
            return None, "配送时段序号必须从 1 开始"
        if slot_ordinal_1based is not None:
            idx = slot_ordinal_1based - 1
            if idx >= len(ordered):
                return None, f"__scroll_for_ordinal__:{len(ordered)}"
            return ordered[idx], f"第{slot_ordinal_1based}项（行数={len(ordered)}）"
        if hint:
            return ordered[0], f"含「{hint}」首条"
        return ordered[0], "首条"
    

    def _tap_checkout_delivery_row_coordinate_fallback(self, w: int, h: int) -> None:
        """
        提交页「预约/立即配送」整行有时不进 accessibility 树；点中部常见热区尝试唤起弹层。
        """
        for yf in (0.42, 0.46, 0.40, 0.50, 0.38):
            for xf in (0.48, 0.52, 0.44, 0.56):
                cx, cy = int(w * xf), int(h * yf)
                try:
                    self.driver.execute_script(
                        "mobile: clickGesture", {"x": cx, "y": cy}
                    )
                    logger.info("配送时段行坐标兜底 (%d,%d)", cx, cy)
                    time.sleep(0.5)
                    return
                except Exception:
                    continue
    

    def shop_open_delivery_time_and_pick_future_slot(
        self,
        *,
        prefer_scheduled: bool = False,
        preferred_slot_contains: Optional[str] = None,
        delivery_time_slot_ordinal: Optional[int] = None,
        require_day_after_tomorrow: bool = False,
    ) -> bool:
        """
        与产品流程对齐：回到订单提交页 → **主区手指下移拖动**（露出上方配送行）→ **立即配送**（默认）唤起弹层
        → 优先 **后天**、不可用则 **明天** → 选时段 → 若有「确定」则点。

        ``prefer_scheduled=True``：先尝试「预约配送」等 Tab（少数 UI）。
        ``preferred_slot_contains``：如 ``\"01:40\"``，在候选里筛含该子串的节点。
        ``delivery_time_slot_ordinal``：1 起算，在 **自上而下、按行去重** 的时段列表里点第 N 个
        （例：``5`` = 第五个选项）；与 ``preferred_slot_contains`` 可同时用（先筛再取序数）。
        两者都不传时确定性选择可见首个时段；真实提交由上层要求显式指定其一。
        """
        w, h = self._window_size_safe()
        opened = False
        self._scroll_checkout_reveal_delivery_strong(w, h)
        time.sleep(0.35)
        for try_open in range(4):
            self._scroll_checkout_form_reveal_delivery(w, h)
            time.sleep(0.35)
            if self._open_delivery_time_picker_sheet(
                w, h, prefer_scheduled=prefer_scheduled
            ):
                opened = True
                logger.info("已唤起配送/预约时段弹层（第 %d 次尝试）", try_open + 1)
                break
            time.sleep(0.45)
        if not opened:
            logger.warning(
                "未点到「预约配送/立即配送」等入口，尝试坐标点后再次匹配文案"
            )
            self._tap_checkout_delivery_row_coordinate_fallback(w, h)
            time.sleep(0.4)
            if self._open_delivery_time_picker_sheet(
                w, h, prefer_scheduled=prefer_scheduled
            ):
                opened = True
                logger.info("坐标兜底后已唤起配送/预约时段弹层")
        if not opened:
            logger.error("未确认配送时段弹层已打开，终止选择")
            return False
        time.sleep(1.0)
        list_x = int(w * 0.72)
        with self._maybe_zero_implicit_wait():
            selected_day = self._tap_allowed_delivery_date_in_sheet(
                require_day_after_tomorrow=require_day_after_tomorrow
            )
            if selected_day is None:
                logger.error("未找到明天或后天，禁止选择其他配送日期")
                return False
            logger.info("配送日期已限制并选择：%s", selected_day)
    
            for attempt in range(8):
                slots: List = []
                hint = (preferred_slot_contains or "").strip()
                if hint:
                    safe = hint.replace('"', "")
                    for xp in (
                        f'//android.view.View[contains(@content-desc,"{safe}")]',
                        f'//*[contains(@content-desc,"{safe}")]',
                        f'//*[contains(@text,"{safe}")]',
                    ):
                        try:
                            for el in self.driver.find_elements(
                                AppiumBy.XPATH, xp
                            ):
                                try:
                                    if not el.is_displayed():
                                        continue
                                    loc = el.location
                                    if int(loc.get("y", 0)) < int(h * 0.18):
                                        continue
                                    if self._looks_like_time_slot_label(
                                        (el.get_attribute("content-desc") or "")
                                    ) or self._looks_like_time_slot_label(
                                        (el.get_attribute("text") or "")
                                    ):
                                        slots.append(el)
                                except Exception:
                                    continue
                        except Exception:
                            continue
                        if slots:
                            break
                    slots = self._filter_time_slots_right_column(slots, w)
                if not slots:
                    slots = self._gather_clickable_time_slot_elements(h)
                slots = self._filter_time_slots_right_column(slots, w)
                if not slots:
                    try:
                        uia_els = self.driver.find_elements(
                            AppiumBy.ANDROID_UIAUTOMATOR,
                            'new UiSelector().textMatches("^\\\\d{1,2}:\\\\d{2}$")',
                        )
                        for el in uia_els:
                            try:
                                if not el.is_displayed():
                                    continue
                                loc = el.location
                                if int(loc.get("y", 0)) < int(h * 0.22):
                                    continue
                                slots.append(el)
                            except Exception:
                                continue
                    except Exception:
                        pass
                    slots = self._filter_time_slots_right_column(slots, w)
                if slots:
                    pick, pick_tag = self._pick_delivery_time_slot_element(
                        slots,
                        preferred_slot_contains=hint or None,
                        slot_ordinal_1based=delivery_time_slot_ordinal,
                    )
                    if pick is None and pick_tag.startswith(
                        "__scroll_for_ordinal__"
                    ):
                        n_vis = 0
                        if ":" in pick_tag:
                            try:
                                n_vis = int(pick_tag.split(":", 1)[1])
                            except ValueError:
                                pass
                        logger.info(
                            "指定第 %d 个时段，当前屏仅见约 %d 行，右侧列表上滑继续",
                            delivery_time_slot_ordinal or 0,
                            n_vis,
                        )
                        try:
                            self.driver.swipe(
                                list_x, int(h * 0.58), list_x, int(h * 0.22), 450
                            )
                        except Exception:
                            pass
                        time.sleep(0.45)
                        continue
                    if pick is None:
                        continue
                    try:
                        if self._coord_tap_or_click(
                            pick, "已选配送时段"
                        ):
                            logger.info(
                                "已选择配送时段（原始候选=%d，%s）",
                                len(slots),
                                pick_tag,
                            )
                            time.sleep(0.75)
                            self._tap_delivery_time_confirm_if_present()
                            return True
                    except Exception as ex:
                        logger.debug("点击时段失败: %s", ex)
    
                try:
                    self.driver.swipe(
                        list_x, int(h * 0.58), list_x, int(h * 0.22), 450
                    )
                except Exception:
                    pass
                time.sleep(0.4)
    
        logger.warning(
            "未找到可点的配送时段（已尝试多类控件与 text/desc 及右侧列表滑动）"
        )
        return False
