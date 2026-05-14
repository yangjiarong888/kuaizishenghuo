"""商城业务流：搜索、详情、下单、客服 IM、分享。"""
from __future__ import annotations

import time
import re
from typing import Iterable, Optional, Sequence, Tuple

from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.remote.webdriver import WebDriver

from commons.logger import setup_logger
from pages.shop_home_page import ShopHomePage
from pages.shop_locators import (
    SHOP_ID_CL_ITEM_CONTAINER,
    SHOP_ID_DIALOG_COMPLETE,
    SHOP_ID_GOODS_LIST_ITEM,
    SHOP_ID_IMAGE,
    SHOP_ID_IV_GOODS,
    SHOP_ID_IV_UP_TO_TOP,
    SHOP_ID_MALL_ACTIVITY,
    SHOP_ID_MALL_ACTIVITY_INFO,
    SHOP_ID_MALL_BUY_NOW,
    SHOP_ID_MALL_DETAIL_MORE,
    SHOP_ID_MALL_DETAIL_VIEWPAGER,
    SHOP_ID_MALL_KEFU,
    SHOP_ID_RV_CONTENT,
    SHOP_ID_RV_GOODS,
    SHOP_ID_TV_GOODS_NAME,
    SHOP_ID_TV_PRICE,
    SHOP_IM_INPUT_ID_SUFFIXES,
    SHOP_SEARCH_ID_SUFFIXES,
    SHOP_SHARE_ID_SUFFIXES,
)

logger = setup_logger(__name__)


class ShopBusinessPage(ShopHomePage):
    """面向商城业务的高层自动化入口。"""

    CHECKOUT_MARKERS: Tuple[str, ...] = (
        "确认订单",
        "提交订单",
        "收货地址",
        "配送方式",
        "支付方式",
        "商品金额",
        "应付",
        "实付款",
    )
    ORDER_DONE_MARKERS: Tuple[str, ...] = (
        "支付成功",
        "下单成功",
        "订单详情",
        "待支付",
        "立即支付",
        "去支付",
    )

    def __init__(self, driver: WebDriver, wait_sec: float = 18.0):
        super().__init__(driver, wait_sec=wait_sec)

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

    def _current_activity_contains(self, name: str) -> bool:
        try:
            return name.lower() in (self.driver.current_activity or "").lower()
        except Exception:
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
        if tap_labels(discount_labels, "\u641c\u7d22\u7ed3\u679c\u6298\u6263\u7b5b\u9009", exact=False):
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

    def _product_candidate_roots(self):
        h = self._window_size()[1]
        y_lo, y_hi = int(h * 0.16), int(h * 0.86)
        suffixes = (
            SHOP_ID_CL_ITEM_CONTAINER,
            SHOP_ID_GOODS_LIST_ITEM,
            SHOP_ID_IV_GOODS,
            SHOP_ID_IMAGE,
            SHOP_ID_TV_GOODS_NAME,
            SHOP_ID_TV_PRICE,
        )
        out = []
        for suffix in suffixes:
            for el in self._all_displayed_by_pkg_id(suffix):
                try:
                    y = int(el.location.get("y", 0))
                    if y_lo <= y <= y_hi:
                        out.append((y, suffix, el))
                except Exception:
                    continue
        for rv_suffix in (SHOP_ID_RV_CONTENT, SHOP_ID_RV_GOODS):
            rv = self._first_displayed_by_pkg_id(rv_suffix)
            if not rv:
                continue
            for inner in (
                f'.//*[contains(@resource-id,"{SHOP_ID_CL_ITEM_CONTAINER}")]',
                f'.//*[contains(@resource-id,"{SHOP_ID_GOODS_LIST_ITEM}")]',
                f'.//*[contains(@resource-id,"{SHOP_ID_TV_GOODS_NAME}")]',
                f'.//*[contains(@resource-id,"{SHOP_ID_IV_GOODS}")]',
            ):
                try:
                    for el in rv.find_elements(AppiumBy.XPATH, inner):
                        if not el.is_displayed():
                            continue
                        y = int(el.location.get("y", 0))
                        if y_lo <= y <= y_hi:
                            out.append((y, inner, el))
                except Exception:
                    continue
        out.sort(key=lambda t: t[0])
        return out

    def _tap_first_search_result_image_by_source_bounds(self) -> bool:
        """
        搜索结果页（NewSearchActivity）常用 ``iv_shop`` 图片 + ``iv_add_cart`` 结构，
        不导出商城首页的 rv_content/clItemContainer。直接解析 page_source 的图片 bounds，
        点击商品图中心，避开加购按钮。
        """
        try:
            src = self.driver.page_source or ""
        except Exception:
            return False
        w, h = self._window_size()
        candidates = []
        for tag in re.findall(r"<[^!?/][^>]*>", src):
            if "iv_shop" not in tag:
                continue
            bm = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', tag)
            if not bm:
                continue
            x1, y1, x2, y2 = (int(v) for v in bm.groups())
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            if int(h * 0.18) <= cy <= int(h * 0.88) and 0 <= cx <= w:
                candidates.append((cy, cx, x1, y1, x2, y2))
        candidates.sort(key=lambda t: (t[0], t[1]))
        for _, _, x1, y1, x2, y2 in candidates[:8]:
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            try:
                self.driver.execute_script("mobile: clickGesture", {"x": cx, "y": cy})
                logger.info("搜索结果：按 iv_shop bounds 点击商品图 (%d,%d)", cx, cy)
                time.sleep(1.45)
                if self._is_mall_product_detail_visible():
                    return True
            except Exception:
                continue
        return False

    def _tap_first_search_grid_goods_by_source_bounds(self) -> bool:
        """搜索结果 GridView 卡片兜底：点击商品图区域，避开加购按钮。"""
        try:
            src = self.driver.page_source or ""
        except Exception:
            return False
        w, h = self._window_size()
        cards = []
        for tag in re.findall(r"<android\.view\.ViewGroup[^>]*>", src):
            if 'clickable="true"' not in tag:
                continue
            bounds = self._bounds_from_tag(tag)
            if not bounds:
                continue
            x1, y1, x2, y2 = bounds
            if y1 < int(h * 0.20) or y1 > int(h * 0.90):
                continue
            if (x2 - x1) < int(w * 0.24) or (y2 - y1) < int(h * 0.12):
                continue
            cards.append((y1, x1, x2, y2))
        cards.sort(key=lambda item: (item[0], item[1]))
        for y1, x1, x2, y2 in cards[:6]:
            cx = (x1 + x2) // 2
            cy = y1 + min((y2 - y1) // 3, int(h * 0.18))
            try:
                self.driver.execute_script("mobile: clickGesture", {"x": cx, "y": cy})
                logger.info("搜索结果 GridView 卡片点击 (%d,%d)", cx, cy)
                time.sleep(1.45)
                if self._is_mall_product_detail_visible():
                    return True
            except Exception:
                continue
        return False

    def open_first_visible_goods_detail(self) -> bool:
        """从当前列表/搜索结果页打开第一个商品详情。"""
        if self._is_mall_product_detail_visible():
            return True
        if self._tap_first_search_grid_goods_by_source_bounds():
            return True
        if self.tap_first_mall_list_product_into_detail():
            return True
        for _, source, el in self._product_candidate_roots()[:10]:
            if self._click_element_center(el, f"商品结果({source})"):
                time.sleep(1.35)
                if self._is_mall_product_detail_visible():
                    logger.info("已进入商品详情")
                    return True
        if self._tap_first_search_result_image_by_source_bounds():
            return True
        if self._tap_first_search_grid_goods_by_source_bounds():
            return True
        w, h = self._window_size()
        try:
            self.driver.execute_script(
                "mobile: clickGesture", {"x": int(w * 0.35), "y": int(h * 0.42)}
            )
            logger.info("商品结果坐标兜底")
            time.sleep(1.35)
            return self._is_mall_product_detail_visible()
        except Exception:
            return False

    def open_goods_detail(self, keyword: Optional[str] = None) -> bool:
        """可选搜索关键字后打开商品详情；无关键字则从商城首页主列表打开。"""
        if self._is_mall_product_detail_visible():
            logger.info("当前已在商品详情页，直接继续详情业务")
            return True
        if keyword:
            if not self.search_goods(keyword):
                return False
        elif not self.ensure_mall_tab():
            return False
        ok = self.open_first_visible_goods_detail()
        if not ok:
            logger.error("未能打开商品详情")
        return ok

    def tap_detail_main_image(self) -> bool:
        """点击详情页主图，并在预览层中左右翻图后返回详情。"""
        if not self._is_mall_product_detail_visible():
            logger.error("当前不在商品详情页，无法查看商品图片")
            return False
        el = self._first_displayed_by_pkg_id(SHOP_ID_MALL_DETAIL_VIEWPAGER)
        clicked = False
        if el:
            clicked = self._click_element_center(el, "商品主图/轮播图")
        if not clicked:
            w, h = self._window_size()
            try:
                self.driver.execute_script(
                    "mobile: clickGesture", {"x": int(w * 0.50), "y": int(h * 0.26)}
                )
                logger.info("商品主图坐标兜底")
                time.sleep(0.75)
                clicked = True
            except Exception:
                clicked = False
        if not clicked:
            return False
        # 若进入图片预览，左右滑动查看图片；若只是轮播区域消费点击，这几次滑动仍可见。
        self._swipe_fraction(0.78, 0.36, 0.22, 0.36, 360)
        self._swipe_fraction(0.22, 0.36, 0.78, 0.36, 360)
        # 图片预览通常全屏，返回后继续详情页；若未进入预览，back 可能退出详情，所以先看是否仍有详情按钮。
        if not self._is_mall_product_detail_visible():
            try:
                self.driver.back()
                time.sleep(0.8)
            except Exception:
                pass
        return self._is_mall_product_detail_visible()

    def swipe_detail_to_content(self, times: int = 4) -> None:
        """下滑详情页，查看商品详情图文。"""
        for i in range(max(1, times)):
            self._swipe_fraction(0.50, 0.76, 0.50, 0.30, 430)
            logger.info("商品详情页下滑查看详情 %d/%d", i + 1, times)
            time.sleep(0.35)

    def tap_detail_activity_info_if_visible(self) -> bool:
        """点击详情页活动信息/优惠入口，若出现弹层则关闭返回详情。"""
        for suffix in (SHOP_ID_MALL_ACTIVITY_INFO, SHOP_ID_MALL_ACTIVITY):
            el = self._first_displayed_by_pkg_id(suffix)
            if el and self._click_element_center(el, f"活动信息({suffix})"):
                break
        else:
            if not self._click_first_text_or_desc(
                ("活动", "优惠", "促销", "领券", "满减"),
                y_min_ratio=0.12,
                y_max_ratio=0.72,
                desc="活动信息",
            ):
                logger.warning("详情页未找到活动信息入口")
                return False
        time.sleep(1.0)
        if self._page_contains_any(("活动", "优惠", "促销", "满减", "领券")):
            logger.info("已打开/查看活动信息")
        self._click_first_text_or_desc(
            ("关闭", "知道了", "确定"),
            y_min_ratio=0.0,
            y_max_ratio=1.0,
            exact=True,
            desc="关闭活动信息",
        )
        if not self._is_mall_product_detail_visible():
            self.tap_top_back()
        return True

    def tap_view_more_goods_if_visible(self, *, scan_scrolls: int = 0) -> bool:
        """点击详情页「查看更多商品/更多商品」入口。"""
        labels = (
            "查看更多商品",
            "更多商品",
            "查看全部商品",
            "查看全部",
            "进店逛逛",
            "店铺",
            "相似商品",
            "推荐商品",
        )
        for i in range(max(0, scan_scrolls) + 1):
            el = self._first_displayed_by_pkg_id(SHOP_ID_MALL_DETAIL_MORE)
            if el and self._click_element_center(el, "查看更多商品(mall_detail_more)"):
                return True
            ok = self._click_first_text_or_desc(
                labels,
                y_min_ratio=0.16,
                y_max_ratio=0.92,
                desc="查看更多商品",
            )
            if ok:
                logger.info("已点击查看更多商品入口")
                time.sleep(1.0)
                return True
            if i < scan_scrolls:
                self._swipe_fraction(0.50, 0.78, 0.50, 0.24, 450)
                logger.info("继续下滑扫描「查看更多商品」入口 %d/%d", i + 1, scan_scrolls)
        logger.warning("详情页未找到「查看更多商品」入口")
        return False

    def tap_detail_back_to_top(self) -> bool:
        """详情页滚动后点击回到顶部箭头。"""
        el = self._first_displayed_by_pkg_id(SHOP_ID_IV_UP_TO_TOP)
        if el and self._click_element_center(el, "回到顶部箭头"):
            return True
        if self._click_first_text_or_desc(
            ("回到顶部", "顶部"),
            y_min_ratio=0.45,
            y_max_ratio=0.95,
            desc="回到顶部",
        ):
            return True
        # 部分详情页仅在右下角显示无语义箭头。
        w, h = self._window_size()
        try:
            self.driver.execute_script(
                "mobile: clickGesture", {"x": int(w * 0.92), "y": int(h * 0.80)}
            )
            logger.info("回到顶部箭头坐标兜底")
            time.sleep(0.75)
            return True
        except Exception:
            logger.warning("未点击到详情页回到顶部箭头")
            return False

    def browse_goods_detail(self) -> bool:
        """详情页浏览：主图、图文详情、活动信息、查看更多商品、回顶部。"""
        if not self._is_mall_product_detail_visible():
            logger.error("当前不在商品详情页，无法执行详情浏览")
            return False
        self.tap_detail_main_image()
        self.tap_detail_activity_info_if_visible()
        self.swipe_detail_to_content(4)
        self.tap_view_more_goods_if_visible(scan_scrolls=6)
        # 点击查看更多可能进入店铺/列表页；返回详情后再回顶部。
        if not self._is_mall_product_detail_visible():
            self.tap_top_back()
            time.sleep(0.8)
        self.tap_detail_back_to_top()
        logger.info("商品详情浏览动作完成")
        return self._is_mall_product_detail_visible()

    def open_and_browse_goods_detail(self, keyword: Optional[str] = None) -> bool:
        if not self.open_goods_detail(keyword):
            return False
        return self.browse_goods_detail()

    def tap_share_on_detail(self, target: Optional[str] = "复制链接") -> bool:
        """详情页分享；默认选「复制链接」，不会跳到外部 App。"""
        if not self._is_mall_product_detail_visible():
            logger.error("当前不在商品详情页，无法分享")
            return False
        for suffix in SHOP_SHARE_ID_SUFFIXES:
            el = self._first_displayed_by_pkg_id(suffix)
            if el and self._click_element_center(el, f"分享入口({suffix})"):
                break
        else:
            if not self._click_first_text_or_desc(
                ("分享",), y_min_ratio=0.0, y_max_ratio=0.25, desc="分享入口"
            ):
                w, h = self._window_size()
                try:
                    self.driver.execute_script(
                        "mobile: clickGesture",
                        {"x": int(w * 0.92), "y": int(h * 0.065)},
                    )
                    logger.info("分享入口坐标兜底")
                    time.sleep(0.85)
                except Exception:
                    logger.error("未找到分享入口")
                    return False
        if not self._wait_page_contains_any(
            ("微信", "朋友圈", "复制链接", "QQ", "分享"), timeout=5.0
        ):
            logger.warning("未识别分享面板，但已尝试打开分享入口")
            return True
        if not target:
            return True
        labels = (target, "复制链接", "复制", "微信好友", "微信") if target == "复制链接" else (target,)
        if self._click_first_text_or_desc(labels, y_min_ratio=0.20, y_max_ratio=0.95, desc="分享目标"):
            time.sleep(1.0)
            if self._page_contains_any(("复制成功", "已复制", "分享成功")):
                logger.info("分享动作已有成功反馈")
            return True
        logger.warning("分享面板未找到目标：%s", target)
        return False

    def open_im_from_detail(self) -> bool:
        """从商品详情进入客服/IM 页。"""
        if not self._is_mall_product_detail_visible():
            logger.error("当前不在商品详情页，无法进入客服")
            return False
        el = self._first_displayed_by_pkg_id(SHOP_ID_MALL_KEFU)
        if el and self._click_element_center(el, "客服入口(mall_kefu)"):
            return self._wait_page_contains_any(
                ("客服", "消息", "输入", "发送", "在线咨询", "人工客服"), timeout=8.0
            )
        if self._click_first_text_or_desc(
            ("客服", "联系商家", "联系卖家", "咨询"),
            y_min_ratio=0.45,
            y_max_ratio=1.0,
            desc="客服入口",
        ):
            return self._wait_page_contains_any(
                ("客服", "消息", "输入", "发送", "在线咨询", "人工客服"), timeout=8.0
            )
        logger.error("未找到客服/IM 入口")
        return False

    def send_im_message(self, message: str) -> bool:
        """在客服/IM 页发送文本。"""
        if not message.strip():
            logger.error("IM 消息为空")
            return False
        for suffix in SHOP_IM_INPUT_ID_SUFFIXES:
            el = self._first_displayed_by_pkg_id(suffix)
            if el:
                try:
                    el.click()
                    time.sleep(0.2)
                    el.send_keys(message)
                    logger.info("已向 IM 输入框写入消息")
                    break
                except Exception:
                    continue
        else:
            if not self._type_into_best_edit_text(message):
                if not self._click_first_text_or_desc(
                    ("输入", "说点什么", "请输入"),
                    y_min_ratio=0.45,
                    y_max_ratio=1.0,
                    desc="IM 输入入口",
                ):
                    logger.error("未找到 IM 输入框")
                    return False
                if not self._type_into_best_edit_text(message):
                    logger.error("IM 输入框无法写入")
                    return False
        try:
            self.driver.hide_keyboard()
        except Exception:
            pass
        if not self._click_first_text_or_desc(
            ("发送",), y_min_ratio=0.45, y_max_ratio=1.0, exact=True, desc="IM 发送"
        ):
            try:
                self.driver.press_keycode(66)
                logger.info("IM 发送：键盘回车兜底")
            except Exception:
                logger.error("未找到 IM 发送按钮")
                return False
        time.sleep(1.0)
        if self._page_contains_any((message[:16], "发送成功")):
            logger.info("IM 消息已出现在会话中")
        return True

    def send_detail_im_message(self, message: str) -> bool:
        if not self.open_im_from_detail():
            return False
        ok = self.send_im_message(message)
        self.tap_top_back()
        time.sleep(0.7)
        return ok

    def buy_now_to_checkout(self) -> bool:
        """详情页点立即购买，并处理可能出现的规格弹层，停在确认订单页。"""
        if not self._is_mall_product_detail_visible():
            logger.error("当前不在商品详情页，无法立即购买")
            return False
        el = self._first_displayed_by_pkg_id(SHOP_ID_MALL_BUY_NOW)
        if not el:
            if not self._click_first_text_or_desc(
                ("立即购买", "马上抢", "购买"),
                y_min_ratio=0.55,
                y_max_ratio=1.0,
                desc="立即购买",
            ):
                logger.error("未找到「立即购买」")
                return False
        else:
            self._click_element_center(el, "立即购买(mall_buy_now)")
        time.sleep(0.8)
        if self._login_like_screen_visible():
            logger.error("立即购买后进入登录页，请先登录")
            return False
        if self._spec_bottom_sheet_visible():
            if not self._mall_spec_popup_pick_and_confirm():
                return False
            time.sleep(1.2)
        if self._wait_page_contains_any(self.CHECKOUT_MARKERS, timeout=10.0):
            logger.info("已进入确认订单/提交订单页")
            return True
        logger.error("立即购买后未进入确认订单页")
        return False

    def submit_order_if_requested(self, submit_order: bool = False) -> bool:
        """默认不真正提交；submit_order=True 时点击提交订单。"""
        if not self._page_contains_any(self.CHECKOUT_MARKERS):
            logger.error("当前未识别为确认订单页")
            return False
        if not submit_order:
            logger.info("已停在确认订单页；未传 submit_order，不点击「提交订单」")
            return True
        if not self._click_first_text_or_desc(
            ("提交订单", "确认订单", "立即支付", "去支付"),
            y_min_ratio=0.55,
            y_max_ratio=1.0,
            desc="提交订单",
        ):
            logger.error("未找到提交订单按钮")
            return False
        ok = self._wait_page_contains_any(self.ORDER_DONE_MARKERS, timeout=12.0)
        if ok:
            logger.info("提交订单后已出现订单/支付相关页面")
        else:
            logger.warning("已点击提交订单，但未明确识别订单结果页")
        return True

    def run_order_flow(self, keyword: Optional[str] = None, *, submit_order: bool = False) -> bool:
        """搜索/打开详情 -> 立即购买 -> 确认订单页；可选提交订单。"""
        if not self.open_goods_detail(keyword):
            return False
        if not self.buy_now_to_checkout():
            return False
        return self.submit_order_if_requested(submit_order)

    def run_full_business_flow(
        self,
        *,
        keyword: str,
        im_message: str,
        share_target: Optional[str] = "复制链接",
        submit_order: bool = False,
    ) -> bool:
        """搜索 -> 详情 -> 分享 -> IM -> 下单。"""
        if not self.open_goods_detail(keyword):
            return False
        self.browse_goods_detail()
        if share_target is not None and not self.tap_share_on_detail(share_target):
            return False
        if im_message and not self.send_detail_im_message(im_message):
            return False
        if not self._is_mall_product_detail_visible():
            if not self.open_goods_detail(keyword):
                return False
        if not self.buy_now_to_checkout():
            return False
        return self.submit_order_if_requested(submit_order)


def run_shop_business_from_driver(driver: WebDriver, **kwargs) -> bool:
    """供脚本直接调用。"""
    return ShopBusinessPage(driver).run_full_business_flow(**kwargs)
