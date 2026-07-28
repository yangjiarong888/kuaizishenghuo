"""商城业务流：搜索、详情、下单、客服 IM、分享。"""
from __future__ import annotations

import random
import time
import re
from typing import Optional, Sequence, Tuple

from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.remote.webdriver import WebDriver

from commons.logger import setup_logger
from pages.shop_home_page import ShopHomePage
from pages.shop_business_search_mixin import MallBusinessSearchMixin
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
    SHOP_ID_MALL_CATEGORY_GOODS_NAME,
    SHOP_ID_TV_GOODS_NAME,
    SHOP_ID_TV_PRICE,
    SHOP_IM_INPUT_ID_SUFFIXES,
    SHOP_SHARE_ID_SUFFIXES,
    SHOP_TEXT_DAILY_BAIHUO,
)

logger = setup_logger(__name__)


class ShopBusinessPage(
    MallBusinessSearchMixin,
    ShopHomePage,
):
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



    def _current_activity_contains(self, name: str) -> bool:
        try:
            return name.lower() in (self.driver.current_activity or "").lower()
        except Exception:
            return False

    def _is_checkout_activity(self) -> bool:
        return self._current_activity_contains("SubmitMallOrderActivity")

    def _dismiss_checkout_upsell_if_visible(self) -> bool:
        """确认订单页满额换购弹窗：不参与换购，继续提交主订单。"""
        if not self._page_contains_any(("低价换购", "确认换购", "放弃机会")):
            return False
        if self._click_first_text_or_desc(
            ("放弃机会", "暂不换购", "不换购"),
            y_min_ratio=0.55,
            y_max_ratio=0.85,
            desc="关闭换购弹窗",
        ):
            time.sleep(1.0)
            return True
        w, h = self._window_size()
        if self._adb_tap(int(w * 0.30), int(h * 0.72), desc="放弃换购"):
            logger.info("已通过 ADB 坐标点击「放弃机会」")
            time.sleep(1.0)
            return True
        return False

    def _select_default_address_if_popup_visible(self) -> bool:
        """确认订单页地址底弹层：选择第一条可见地址继续提交。"""
        if not self._page_contains_any(("配送至", "选择其他收货地址")):
            return False
        for pkg in self._shop_packages_prioritized():
            rid = self._rid(pkg, "tv_address")
            try:
                for el in self.driver.find_elements(AppiumBy.ID, rid):
                    try:
                        if not el.is_displayed():
                            continue
                        self._nearest_clickable_ancestor(el, max_hops=6).click()
                        logger.info("已选择地址弹层第一条地址")
                        time.sleep(1.0)
                        return True
                    except Exception:
                        continue
            except Exception:
                continue
        w, h = self._window_size()
        if self._adb_tap(int(w * 0.50), int(h * 0.62), desc="选择默认地址"):
            logger.info("已通过 ADB 坐标选择地址弹层第一条地址")
            time.sleep(1.0)
            return True
        return False



    def _visible_text_candidates_by_band(
        self,
        *,
        x_min_ratio: float,
        x_max_ratio: float,
        y_min_ratio: float,
        y_max_ratio: float,
        exclude: Sequence[str] = (),
        min_len: int = 2,
    ):
        w, h = self._window_size()
        x_lo, x_hi = int(w * x_min_ratio), int(w * x_max_ratio)
        y_lo, y_hi = int(h * y_min_ratio), int(h * y_max_ratio)
        out = []
        seen = set()
        with self._mall_ctx.zero_implicit_wait():
            try:
                els = self.driver.find_elements(
                    AppiumBy.XPATH,
                    '//*[@text and string-length(@text)>0]',
                )
            except Exception:
                els = []
            for el in els:
                try:
                    if not el.is_displayed():
                        continue
                    text = self._safe_text(el)
                    if len(text) < min_len:
                        continue
                    if any(part and part in text for part in exclude):
                        continue
                    loc, size = el.location, el.size
                    cx = int(loc.get("x", 0) + size.get("width", 0) / 2)
                    cy = int(loc.get("y", 0) + size.get("height", 0) / 2)
                    if not (x_lo <= cx <= x_hi and y_lo <= cy <= y_hi):
                        continue
                    key = (text, cx // 12, cy // 12)
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append((cy, cx, text, el))
                except Exception:
                    continue
        out.sort(key=lambda item: (item[0], item[1]))
        return out

    def tap_random_top_category(self) -> bool:
        """随机点击分类页顶部横向二级分类。"""
        if not self._page_contains_any(("\u5168\u90e8\u5206\u7c7b",)):
            logger.warning("\u5f53\u524d\u4e0d\u50cf\u5206\u7c7b\u9875\uff0c\u8df3\u8fc7\u9876\u90e8\u4e8c\u7ea7\u5206\u7c7b\u70b9\u51fb")
            return False
        candidates = self._visible_text_candidates_by_band(
            x_min_ratio=0.02,
            x_max_ratio=0.92,
            y_min_ratio=0.12,
            y_max_ratio=0.32,
            exclude=("\u641c\u7d22", "\u5168\u90e8\u5206\u7c7b", "\u9500\u91cf", "\u4ef7\u683c", "\u6298\u6263", "\u7efc\u5408"),
        )
        if not candidates:
            logger.warning("\u672a\u627e\u5230\u9876\u90e8\u4e8c\u7ea7\u5206\u7c7b\u5019\u9009")
            return False
        _, _, text, el = random.choice(candidates)
        ok = self._click_element_center(el, f"\u968f\u673a\u9876\u90e8\u4e8c\u7ea7\u5206\u7c7b:{text}")
        if ok:
            logger.info("\u5df2\u968f\u673a\u547d\u4e2d\u9876\u90e8\u4e8c\u7ea7\u5206\u7c7b\uff1a%s", text)
        return ok

    def tap_random_left_category(self) -> bool:
        """随机点击分类页左侧分类栏。"""
        if not self._page_contains_any(("\u5168\u90e8\u5206\u7c7b",)):
            logger.warning("\u5f53\u524d\u4e0d\u50cf\u5206\u7c7b\u9875\uff0c\u8df3\u8fc7\u5de6\u4fa7\u5206\u7c7b\u70b9\u51fb")
            return False
        candidates = self._visible_text_candidates_by_band(
            x_min_ratio=0.00,
            x_max_ratio=0.34,
            y_min_ratio=0.26,
            y_max_ratio=0.84,
            exclude=("\u7206\u6b3e\u63a8\u8350", "\u641c\u7d22", "\u5168\u90e8\u5206\u7c7b", "\u9500\u91cf", "\u4ef7\u683c", "\u6298\u6263"),
        )
        if not candidates:
            logger.warning("\u672a\u627e\u5230\u5de6\u4fa7\u5206\u7c7b\u5019\u9009")
            return False
        _, _, text, el = random.choice(candidates)
        ok = self._click_element_center(el, f"\u968f\u673a\u5de6\u4fa7\u5206\u7c7b:{text}")
        if ok:
            logger.info("\u5df2\u968f\u673a\u547d\u4e2d\u5de6\u4fa7\u5206\u7c7b\uff1a%s", text)
        return ok

    def run_random_category_flow(self) -> bool:
        """进入分类页后随机覆盖顶部二级分类和左侧分类。"""
        if not self._page_contains_any(("\u5168\u90e8\u5206\u7c7b",)):
            for _ in range(3):
                if self.ensure_mall_tab() and self._is_mall_home_main_list_visible():
                    break
                self.tap_top_back()
                time.sleep(0.8)
            if not self.ensure_mall_tab():
                return False
            if not self.tap_kingkong_hot_snacks():
                logger.warning("\u672a\u901a\u8fc7\u5546\u57ce\u9996\u9875\u91d1\u521a\u533a\u8fdb\u5165\u4e8c\u7ea7\u5206\u7c7b\u9875")
                return False
            time.sleep(1.6)
        self.tap_secondary_category_filters()
        top_ok = self.tap_random_top_category()
        time.sleep(1.0)
        left_ok = self.tap_random_left_category()
        time.sleep(1.0)
        return top_ok or left_ok

    def tap_random_visible_add_cart(self) -> bool:
        """随机点击当前列表/活动页可见加购按钮。"""
        w, h = self._window_size()
        candidates = []
        for suffix in ("iv_add_cart", "tv_add_cart_more", "mall_add_shop_car"):
            for el in self._all_displayed_by_pkg_id(suffix):
                try:
                    loc, size = el.location, el.size
                    cx = int(loc.get("x", 0) + size.get("width", 0) / 2)
                    cy = int(loc.get("y", 0) + size.get("height", 0) / 2)
                    if int(h * 0.20) <= cy <= int(h * 0.92) and 0 <= cx <= w:
                        candidates.append((cy, cx, suffix, el))
                except Exception:
                    continue
        if not candidates:
            logger.warning("\u6d3b\u52a8/\u5217\u8868\u9875\u672a\u627e\u5230\u53ef\u89c1\u52a0\u8d2d\u6309\u94ae")
            return False
        _, _, suffix, el = random.choice(candidates)
        if not self._click_element_center(el, f"\u968f\u673a\u52a0\u8d2d({suffix})"):
            return False
        self.handle_add_cart_followups()
        logger.info("\u5df2\u5728\u6d3b\u52a8/\u5217\u8868\u9875\u968f\u673a\u52a0\u8d2d")
        return True

    def run_activity_random_add_cart_to_cart(self) -> bool:
        """进入活动页后随机加购商品，并跳转购物车。"""
        if not self._page_contains_any(("\u9650\u65f6\u7279\u4ef7", "\u6298\u6263", "\u4f18\u60e0", "\u7279\u4ef7")):
            if not self.ensure_mall_tab():
                return False
        self._click_first_text_or_desc(
            ("\u9650\u65f6\u7279\u4ef7", "\u6298\u6263", "\u4f18\u60e0", "\u7279\u4ef7", "\u4fc3\u9500"),
            y_min_ratio=0.12,
            y_max_ratio=0.72,
            exact=False,
            desc="\u6d3b\u52a8\u5165\u53e3",
        )
        time.sleep(1.5)
        add_ok = self.tap_random_visible_add_cart()
        cart_ok = self.tap_floating_or_entry_cart()
        if cart_ok:
            logger.info("\u5df2\u4ece\u6d3b\u52a8\u9875\u8df3\u8f6c\u8d2d\u7269\u8f66")
        return add_ok and cart_ok

    def run_category_and_activity_explore(self) -> bool:
        category_ok = self.run_random_category_flow()
        self.tap_top_back()
        time.sleep(1.0)
        activity_ok = self.run_activity_random_add_cart_to_cart()
        return category_ok and activity_ok


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
        if self._is_checkout_activity():
            self._dismiss_checkout_upsell_if_visible()
            logger.info("已进入确认订单页（SubmitMallOrderActivity）")
            return True
        if self._wait_page_contains_any(self.CHECKOUT_MARKERS, timeout=10.0):
            self._dismiss_checkout_upsell_if_visible()
            logger.info("已进入确认订单/提交订单页")
            return True
        logger.error("立即购买后未进入确认订单页")
        return False

    def submit_order_if_requested(self, submit_order: bool = False) -> bool:
        """默认不真正提交；submit_order=True 时点击提交订单。"""
        if self._is_checkout_activity():
            self._dismiss_checkout_upsell_if_visible()
        if not self._is_checkout_activity() and not self._page_contains_any(self.CHECKOUT_MARKERS):
            logger.error("当前未识别为确认订单页")
            return False
        if not submit_order:
            logger.info("已停在确认订单页；未传 submit_order，不点击「提交订单」")
            return True
        for attempt in range(2):
            self._select_default_address_if_popup_visible()
            if not self._click_first_text_or_desc(
                ("提交订单", "确认订单", "立即支付", "去支付"),
                y_min_ratio=0.55,
                y_max_ratio=1.0,
                desc="提交订单",
            ):
                if attempt == 0 and self._select_default_address_if_popup_visible():
                    continue
                logger.error("未找到提交订单按钮")
                return False
            time.sleep(1.0)
            if not self._select_default_address_if_popup_visible():
                break
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

    def run_daily_baihuo_order_flow(
        self,
        *,
        submit_order: bool = False,
        min_price: float = 400.0,
    ) -> bool:
        """固定路径：商城首页 -> 全部分类 -> 日用百货 -> 分类商品 -> 立即购买。"""
        if not self.ensure_mall_tab():
            return False
        if not self.tap_mall_kingkong_daily_baihuo_via_popup():
            logger.error("未能进入「%s」分类", SHOP_TEXT_DAILY_BAIHUO)
            return False
        time.sleep(1.0)
        if not self._tap_first_category_goods_item(min_price=min_price):
            logger.warning("日用百货未找到价格 >= %.2f 的可见商品，改点首个可见商品", min_price)
            if not self._tap_first_category_goods_item(min_price=None):
                logger.error("日用百货分类未能打开商品详情")
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


def parse_price_text(raw: str) -> Optional[float]:
    text = (raw or "").replace(",", "").strip()
    m = re.search(r"(?:₱|P|￥|¥)?\s*(\d+(?:\.\d{1,2})?)", text, flags=re.I)
    if not m:
        return None
    if not any(mark in text for mark in ("₱", "P", "￥", "¥", "元")) and "." not in m.group(1):
        return None
    return float(m.group(1))
