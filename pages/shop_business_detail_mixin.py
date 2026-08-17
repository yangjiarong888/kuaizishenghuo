"""Product discovery and read-only detail browsing for ShopBusinessPage."""
from __future__ import annotations

import re
import time
from typing import Optional

from appium.webdriver.common.appiumby import AppiumBy

from commons.logger import setup_logger
from pages.shop_locators import (
    SHOP_ID_CL_ITEM_CONTAINER,
    SHOP_ID_GOODS_LIST_ITEM,
    SHOP_ID_IMAGE,
    SHOP_ID_IV_GOODS,
    SHOP_ID_IV_UP_TO_TOP,
    SHOP_ID_MALL_ACTIVITY,
    SHOP_ID_MALL_ACTIVITY_INFO,
    SHOP_ID_MALL_DETAIL_MORE,
    SHOP_ID_MALL_DETAIL_VIEWPAGER,
    SHOP_ID_RV_CONTENT,
    SHOP_ID_RV_GOODS,
    SHOP_ID_TV_GOODS_NAME,
    SHOP_ID_TV_PRICE,
)

logger = setup_logger(__name__)


class MallBusinessDetailMixin:
    """Product/detail behavior; host supplies search and home capabilities."""
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
        if self._tap_first_category_goods_item():
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

    def _category_goods_item_price(self, item) -> Optional[float]:
        try:
            texts = item.find_elements(AppiumBy.CLASS_NAME, "android.widget.TextView")
        except Exception:
            return None
        vals = []
        for el in texts:
            try:
                if not el.is_displayed():
                    continue
                val = parse_price_text(el.text or "")
                if val is not None:
                    vals.append(val)
            except Exception:
                continue
        return max(vals) if vals else None

    def _tap_category_goods_item(self, item, *, desc: str) -> bool:
        try:
            loc = item.location
            size = item.size
            x = int(loc["x"] + size["width"] * 0.35)
            y = int(loc["y"] + size["height"] * 0.42)
            self.driver.execute_script("mobile: clickGesture", {"x": x, "y": y})
            logger.info("已点击分类商品行进入详情：%s (%d,%d)", desc, x, y)
            time.sleep(1.8)
            return self._is_mall_product_detail_visible()
        except Exception:
            return False

    def _tap_first_category_goods_item(self, *, min_price: Optional[float] = None) -> bool:
        with self._mall_ctx.zero_implicit_wait():
            for _ in range(8):
                try:
                    items = self.driver.find_elements(
                        AppiumBy.XPATH, '//*[contains(@resource-id,"goodsListItemLayout")]'
                    )
                except Exception:
                    items = []
                for item in items:
                    try:
                        if not item.is_displayed():
                            continue
                        price = self._category_goods_item_price(item)
                        if min_price is not None and (price is None or price < min_price):
                            continue
                        name = ""
                        try:
                            name = self.mall_category_goods_name_text(item)
                        except Exception:
                            pass
                        if self._tap_category_goods_item(
                            item,
                            desc=f"{name or '?'} price={price}",
                        ):
                            return True
                    except Exception:
                        continue
                self._swipe_mall_vertical_list_down(
                    1, 0.8, "日用百货分类找可下单商品", x_ratio=0.58
                )
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


def parse_price_text(raw: str) -> Optional[float]:
    text = (raw or "").replace(",", "").strip()
    m = re.search(r"(?:₱|P|￥|¥)?\s*(\d+(?:\.\d{1,2})?)", text, flags=re.I)
    if not m:
        return None
    if not any(mark in text for mark in ("₱", "P", "￥", "¥", "元")) and "." not in m.group(1):
        return None
    return float(m.group(1))
