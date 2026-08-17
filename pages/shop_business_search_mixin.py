"""Shared interaction and read-only search behavior for ShopBusinessPage."""
from __future__ import annotations

import re
import time
from typing import Iterable, Optional, Sequence, Tuple

from appium.webdriver.common.appiumby import AppiumBy

from commons.logger import setup_logger
from pages.shop_locators import (
    SHOP_SEARCH_ID_SUFFIXES,
    SHOP_TEXT_DAILY_BAIHUO,
)

logger = setup_logger(__name__)


class MallBusinessSearchMixin:
    """Search-page behavior; host supplies ShopHomePage capabilities."""

    def _safe_text(self, el) -> str:
        try:
            return (el.text or "").strip()
        except Exception:
            return ""
    def _safe_desc(self, el) -> str:
        try:
            return (el.get_attribute("content-desc") or "").strip()
        except Exception:
            return ""
    @staticmethod
    def _clean_xpath_text(text: str) -> str:
        return text.replace('"', "").replace("'", "")[:48]
    def _page_contains_any(self, markers: Sequence[str]) -> bool:
        try:
            src = self.driver.page_source or ""
        except Exception:
            return False
        return any(m in src for m in markers)
    def _wait_page_contains_any(
        self, markers: Sequence[str], timeout: float = 8.0
    ) -> bool:
        end = time.time() + timeout
        while time.time() < end:
            if self._page_contains_any(markers):
                return True
            time.sleep(0.35)
        return False
    def _click_element_center(self, el, desc: str) -> bool:
        try:
            self._nearest_clickable_ancestor(el).click()
            logger.info("已点击%s（可点击祖先）", desc)
            time.sleep(0.65)
            return True
        except Exception:
            pass
        try:
            el.click()
            logger.info("已点击%s（元素自身）", desc)
            time.sleep(0.65)
            return True
        except Exception:
            pass
        try:
            loc = el.location
            sz = el.size
            cx = int(loc["x"] + sz["width"] / 2)
            cy = int(loc["y"] + sz["height"] / 2)
            self.driver.execute_script("mobile: clickGesture", {"x": cx, "y": cy})
            logger.info("已点击%s（坐标 %d,%d）", desc, cx, cy)
            time.sleep(0.65)
            return True
        except Exception:
            return False
    def _click_first_text_or_desc(
        self,
        labels: Iterable[str],
        *,
        y_min_ratio: float = 0.0,
        y_max_ratio: float = 1.0,
        exact: bool = False,
        desc: str = "目标控件",
    ) -> bool:
        h = self._window_size()[1]
        y_min, y_max = int(h * y_min_ratio), int(h * y_max_ratio)
        with self._mall_ctx.zero_implicit_wait():
            for raw in labels:
                label = self._clean_xpath_text(raw)
                if not label:
                    continue
                if exact:
                    xp = f'//*[@text="{label}" or @content-desc="{label}"]'
                else:
                    xp = (
                        f'//*[contains(@text,"{label}") or '
                        f'contains(@content-desc,"{label}")]'
                    )
                try:
                    for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                        try:
                            if not el.is_displayed():
                                continue
                            y = int(el.location.get("y", 0))
                            if not (y_min <= y <= y_max):
                                continue
                            return self._click_element_center(el, f"{desc}:{label}")
                        except Exception:
                            continue
                except Exception:
                    continue
        return False
    def _type_into_best_edit_text(self, text: str, *, allow_open_search: bool = True) -> bool:
        for suffix in ("et_search", "edit_search", "search_edit", "input_search"):
            el = self._first_displayed_by_pkg_id(suffix)
            if not el:
                continue
            try:
                el.click()
                time.sleep(0.15)
                try:
                    el.clear()
                except Exception:
                    pass
                el.send_keys(text)
                logger.info("\u5df2\u5411\u8f93\u5165\u6846(%s)\u8f93\u5165\u6587\u672c\uff1a%s", suffix, text[:32])
                return True
            except Exception:
                continue
        edit_texts = []
        try:
            edit_texts = self.driver.find_elements(
                AppiumBy.CLASS_NAME, "android.widget.EditText"
            )
        except Exception:
            edit_texts = []
        scored = []
        for el in edit_texts:
            try:
                if not el.is_displayed():
                    continue
                y = int(el.location.get("y", 0))
                scored.append((y, el))
            except Exception:
                continue
        scored.sort(key=lambda t: t[0])
        for _, el in scored[:3]:
            try:
                el.click()
                time.sleep(0.15)
                try:
                    el.clear()
                except Exception:
                    pass
                el.send_keys(text)
                logger.info("已输入文本：%s", text[:32])
                return True
            except Exception:
                continue
        if allow_open_search:
            for suffix in SHOP_SEARCH_ID_SUFFIXES:
                el = self._first_displayed_by_pkg_id(suffix)
                if el and self._click_element_center(el, f"搜索输入恢复({suffix})"):
                    time.sleep(0.8)
                    return self._type_into_best_edit_text(text, allow_open_search=False)
        return False
    def _press_enter_or_search(self) -> None:
        for suffix in ("layout_right", "tv_right"):
            el = self._first_displayed_by_pkg_id(suffix)
            if el and self._click_element_center(el, f"\u641c\u7d22\u786e\u8ba4({suffix})"):
                time.sleep(0.9)
                return
        try:
            self.driver.press_keycode(66)
            time.sleep(0.75)
        except Exception:
            pass
        self._click_first_text_or_desc(
            ("搜索", "确定"),
            y_min_ratio=0.0,
            y_max_ratio=0.28,
            exact=True,
            desc="搜索确认",
        )
    def _swipe_fraction(
        self,
        x_from: float,
        y_from: float,
        x_to: float,
        y_to: float,
        duration_ms: int = 450,
    ) -> bool:
        w, h = self._window_size()
        try:
            self.driver.swipe(
                int(w * x_from),
                int(h * y_from),
                int(w * x_to),
                int(h * y_to),
                duration_ms,
            )
            time.sleep(0.45)
            return True
        except Exception:
            try:
                direction = "up" if y_to < y_from else "down"
                self.driver.execute_script(
                    "mobile: swipeGesture",
                    {
                        "left": int(w * min(x_from, x_to, 0.18)),
                        "top": int(h * min(y_from, y_to, 0.20)),
                        "width": int(w * 0.64),
                        "height": int(h * 0.52),
                        "direction": direction,
                        "percent": 0.55,
                    },
                )
                time.sleep(0.45)
                return True
            except Exception:
                return False
    def tap_search_entry(self) -> bool:
        """商城页顶部搜索入口。"""
        with self._mall_ctx.zero_implicit_wait():
            for suffix in SHOP_SEARCH_ID_SUFFIXES:
                el = self._first_displayed_by_pkg_id(suffix)
                if el and self._click_element_center(el, f"搜索入口({suffix})"):
                    return True
            for label in ("搜索商家或商品", "搜索商品", "搜索"):
                if self._click_first_text_or_desc(
                    (label,),
                    y_min_ratio=0.0,
                    y_max_ratio=0.28,
                    desc="搜索入口",
                ):
                    return True
        w, h = self._window_size()
        for xf, yf in ((0.43, 0.085), (0.50, 0.10), (0.35, 0.12)):
            try:
                self.driver.execute_script(
                    "mobile: clickGesture", {"x": int(w * xf), "y": int(h * yf)}
                )
                logger.info("搜索入口坐标兜底 (%d,%d)", int(w * xf), int(h * yf))
                time.sleep(0.85)
                if self._type_into_best_edit_text(" "):
                    self.driver.press_keycode(67)
                    return True
            except Exception:
                continue
        logger.error("未找到商城搜索入口")
        return False
    def _search_page_visible(self) -> bool:
        if self._current_activity_contains("NewSearchActivity"):
            return True
        if self._first_displayed_by_pkg_id("et_search"):
            return True
        return self._page_contains_any(
            (
                "\u5386\u53f2\u641c\u7d22",
                "\u70ed\u95e8\u641c\u7d22",
                "\u641c\u7d22\u5546\u54c1",
                "\u7279\u4ef7\u7206\u6b3e",
            )
        )
    def open_search_page(self) -> bool:
        if self._search_page_visible():
            logger.info("\u5f53\u524d\u5df2\u5728\u641c\u7d22\u9875\uff0c\u76f4\u63a5\u7ee7\u7eed\u641c\u7d22\u4e1a\u52a1")
            return True
        if not self.ensure_mall_tab():
            return False
        if not self.tap_search_entry():
            return False
        return self._wait_page_contains_any(
            (
                "\u5386\u53f2\u641c\u7d22",
                "\u70ed\u95e8\u641c\u7d22",
                "\u641c\u7d22\u5546\u54c1",
                "\u641c\u7d22",
            ),
            timeout=5.0,
        )
    @staticmethod
    def _bounds_from_tag(tag: str) -> Optional[Tuple[int, int, int, int]]:
        bm = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', tag)
        if not bm:
            return None
        return tuple(int(v) for v in bm.groups())  # type: ignore[return-value]
    def _tap_chip_below_title(self, title: str, desc: str, *, pick: str = "first") -> bool:
        try:
            src = self.driver.page_source or ""
        except Exception:
            return False
        tags = re.findall(r"<[^!?/][^>]*>", src)
        title_bottom = None
        for tag in tags:
            if f'text="{title}"' not in tag:
                continue
            bounds = self._bounds_from_tag(tag)
            if bounds:
                title_bottom = bounds[3]
                break
        if title_bottom is None:
            return False

        w, h = self._window_size()
        candidates = []
        for tag in tags:
            if "ll_hot" not in tag:
                continue
            bounds = self._bounds_from_tag(tag)
            if not bounds:
                continue
            x1, y1, x2, y2 = bounds
            cy = (y1 + y2) // 2
            if title_bottom < cy < int(h * 0.92):
                candidates.append((cy, x1, y1, x2, y2))
        candidates.sort(key=lambda item: (item[0], item[1]))
        chosen = candidates[-1:] if pick == "last" else candidates[:1]
        for _, x1, y1, x2, y2 in chosen:
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            if not (0 <= cx <= w and 0 <= cy <= h):
                continue
            try:
                self.driver.execute_script("mobile: clickGesture", {"x": cx, "y": cy})
                logger.info("%s\u5750\u6807\u70b9\u51fb (%d,%d)", desc, cx, cy)
                time.sleep(0.9)
                return True
            except Exception:
                continue
        fallback_ratios = {
            ("\u70ed\u95e8\u641c\u7d22", "first"): (0.19, 0.27),
            ("\u70ed\u95e8\u641c\u7d22", "last"): (0.82, 0.37),
            "\u5386\u53f2\u641c\u7d22": (0.10, 0.18),
        }
        key = (title, pick) if title == "\u70ed\u95e8\u641c\u7d22" else title
        if key in fallback_ratios and self._page_contains_any((title,)):
            xf, yf = fallback_ratios[key]
            try:
                cx, cy = int(w * xf), int(h * yf)
                self.driver.execute_script("mobile: clickGesture", {"x": cx, "y": cy})
                logger.info("%s\u5750\u6807\u515c\u5e95\u70b9\u51fb (%d,%d)", desc, cx, cy)
                time.sleep(0.9)
                return True
            except Exception:
                pass
        return False
    def _tap_first_chip_below_title(self, title: str, desc: str) -> bool:
        return self._tap_chip_below_title(title, desc, pick="first")
    def browse_search_landing(self) -> None:
        """Cover history search and hot search chips before keyword search."""
        if not self._search_page_visible():
            return
        if self._tap_chip_below_title("\u70ed\u95e8\u641c\u7d22", "\u70ed\u95e8\u641c\u7d22\u8bcd\u9996\u4e2a", pick="first"):
            if not self._page_contains_any(("\u5386\u53f2\u641c\u7d22", "\u70ed\u95e8\u641c\u7d22")):
                self.tap_top_back()
                time.sleep(0.8)
                self.open_search_page()
        if self._tap_chip_below_title("\u70ed\u95e8\u641c\u7d22", "\u70ed\u95e8\u641c\u7d22\u8bcd\u6700\u540e\u4e00\u4e2a", pick="last"):
            if not self._page_contains_any(("\u5386\u53f2\u641c\u7d22", "\u70ed\u95e8\u641c\u7d22")):
                self.tap_top_back()
                time.sleep(0.8)
                self.open_search_page()
        self._click_first_text_or_desc(
            ("\u66f4\u591a\u5386\u53f2", "\u5386\u53f2\u641c\u7d22"),
            y_min_ratio=0.08,
            y_max_ratio=0.55,
            desc="\u5386\u53f2\u641c\u7d22",
        )
        if self._tap_first_chip_below_title("\u5386\u53f2\u641c\u7d22", "\u5386\u53f2\u641c\u7d22\u8bcd"):
            self.open_search_page()
    def tap_search_result_filters(self) -> None:
        """Cover common sort/filter labels on the search result page."""
        def tap_labels(labels: Tuple[str, ...], desc: str, *, exact: bool = True) -> bool:
            clicked = self._click_first_text_or_desc(
                labels,
                y_min_ratio=0.10,
                y_max_ratio=0.72,
                exact=exact,
                desc=desc,
            )
            if clicked:
                time.sleep(0.75)
            else:
                logger.warning("\u641c\u7d22\u7ed3\u679c\u672a\u627e\u5230\u7b5b\u9009\u9879\uff1a%s", "/".join(labels))
            return clicked

        tap_labels(("\u7efc\u5408",), "\u641c\u7d22\u7ed3\u679c\u7efc\u5408")
        for i in range(2):
            if tap_labels(("\u9500\u91cf",), f"\u641c\u7d22\u7ed3\u679c\u9500\u91cf\u6392\u5e8f{i + 1}"):
                logger.info("\u5df2\u70b9\u51fb\u9500\u91cf\u6392\u5e8f %d/2\uff08\u8986\u76d6\u5347\u5e8f/\u964d\u5e8f\u5207\u6362\uff09", i + 1)
        for i in range(2):
            if tap_labels(("\u4ef7\u683c",), f"\u641c\u7d22\u7ed3\u679c\u4ef7\u683c\u6392\u5e8f{i + 1}"):
                logger.info("\u5df2\u70b9\u51fb\u4ef7\u683c\u6392\u5e8f %d/2\uff08\u8986\u76d6\u5347\u5e8f/\u964d\u5e8f\u5207\u6362\uff09", i + 1)

        discount_labels = (
            "\u6298\u6263",
            "\u4f18\u60e0",
            "\u9650\u65f6\u7279\u4ef7",
            "\u7279\u4ef7",
            "\u4fc3\u9500",
        )
        discount_clicked = False
        for i in range(2):
            if tap_labels(discount_labels, f"\u641c\u7d22\u7ed3\u679c\u6298\u6263\u6392\u5e8f{i + 1}", exact=False):
                logger.info("\u5df2\u70b9\u51fb\u6298\u6263\u6392\u5e8f %d/2\uff08\u8986\u76d6\u5347\u5e8f/\u964d\u5e8f\u5207\u6362\uff09", i + 1)
                discount_clicked = True
        if discount_clicked:
            logger.info("\u5df2\u547d\u4e2d\u6298\u6263/\u4f18\u60e0\u7c7b\u7b5b\u9009")
            return
        if tap_labels(("\u7b5b\u9009",), "\u641c\u7d22\u7ed3\u679c\u7b5b\u9009\u5165\u53e3", exact=False):
            if tap_labels(discount_labels, "\u7b5b\u9009\u9762\u677f\u6298\u6263\u6761\u4ef6", exact=False):
                logger.info("\u5df2\u5728\u7b5b\u9009\u9762\u677f\u547d\u4e2d\u6298\u6263/\u4f18\u60e0\u6761\u4ef6")
            self._click_first_text_or_desc(
                ("\u786e\u5b9a", "\u5b8c\u6210", "\u67e5\u770b\u7ed3\u679c"),
                y_min_ratio=0.45,
                y_max_ratio=1.0,
                exact=False,
                desc="\u7b5b\u9009\u9762\u677f\u786e\u8ba4",
            )
    def _tap_sort_control(self, label: str, id_suffix: str, desc: str) -> bool:
        el = self._first_displayed_by_pkg_id(id_suffix)
        if el and self._click_element_center(el, desc):
            return True
        return self._click_first_text_or_desc(
            (label,),
            y_min_ratio=0.16,
            y_max_ratio=0.56,
            exact=False,
            desc=desc,
        )
    def tap_secondary_category_filters(self) -> None:
        """二级分类页销量/价格/折扣排序；每项点两次覆盖升降序。"""
        for label, suffix in (
            ("\u9500\u91cf", "ll_sort_sales"),
            ("\u4ef7\u683c", "ll_sort_price"),
            ("\u6298\u6263", "ll_sort_discount"),
        ):
            clicked_any = False
            for i in range(2):
                if self._tap_sort_control(label, suffix, f"\u4e8c\u7ea7\u5206\u7c7b{label}\u6392\u5e8f{i + 1}"):
                    logger.info("\u5df2\u70b9\u51fb\u4e8c\u7ea7\u5206\u7c7b%s\u6392\u5e8f %d/2\uff08\u8986\u76d6\u5347\u5e8f/\u964d\u5e8f\uff09", label, i + 1)
                    clicked_any = True
                    time.sleep(0.75)
            if not clicked_any:
                logger.warning("\u4e8c\u7ea7\u5206\u7c7b\u672a\u627e\u5230%s\u6392\u5e8f\u63a7\u4ef6", label)
    def browse_special_deals_products(self) -> None:
        """Browse the special-deal section and briefly open one product when possible."""
        clicked_tag = self._click_first_text_or_desc(
            ("\u7279\u4ef7\u7206\u6b3e", "\u9650\u65f6\u7279\u4ef7", "\u7206\u6b3e"),
            y_min_ratio=0.20,
            y_max_ratio=0.86,
            desc="\u7279\u4ef7\u7206\u6b3e\u6807\u7b7e",
        )
        if clicked_tag:
            logger.info("\u5df2\u67e5\u770b\u7279\u4ef7/\u7206\u6b3e\u6807\u7b7e")
        self._swipe_fraction(0.48, 0.80, 0.48, 0.54, 360)
        self._swipe_fraction(0.48, 0.78, 0.48, 0.52, 360)
        self._swipe_fraction(0.48, 0.38, 0.48, 0.70, 320)
        opened = self._tap_first_search_result_image_by_source_bounds()
        if not opened:
            opened = self.open_first_visible_goods_detail()
        if opened:
            logger.info("\u5df2\u6253\u5f00\u7279\u4ef7\u7206\u6b3e\u5546\u54c1\u4fe1\u606f")
            time.sleep(1.0)
            self.tap_top_back()
            time.sleep(0.9)
        else:
            logger.warning("\u672a\u6253\u5f00\u7279\u4ef7\u7206\u6b3e\u5546\u54c1\u4fe1\u606f\uff0c\u5df2\u5b8c\u6210\u5217\u8868\u6d4f\u89c8")
    def browse_search_results(self) -> None:
        self.tap_search_result_filters()
        self.browse_special_deals_products()
    def search_goods(self, keyword: str) -> bool:
        """进入搜索页并搜索商品关键字。"""
        if not keyword.strip():
            logger.error("搜索关键字为空")
            return False
        if not self.open_search_page():
            return False
        self.browse_search_landing()
        time.sleep(0.45)
        if not self._type_into_best_edit_text(keyword.strip()):
            logger.error("搜索页未找到输入框")
            return False
        self._press_enter_or_search()
        ok = self._wait_page_contains_any(
            (keyword.strip(), "综合", "销量", "价格", "商品", "搜索"), timeout=8.0
        )
        if ok:
            logger.info("搜索结果页已出现：%s", keyword)
        else:
            logger.warning("未明确识别搜索结果页，继续尝试点商品")
        self.browse_search_results()
        return True
