"""商城业务流：搜索、详情、下单、客服 IM、分享。"""
from __future__ import annotations

import random
import time
from typing import Optional, Sequence, Tuple

from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.remote.webdriver import WebDriver

from commons.logger import setup_logger
from pages.shop_business_detail_mixin import (
    MallBusinessDetailMixin,
    parse_price_text,
)
from pages.shop_business_search_mixin import MallBusinessSearchMixin
from pages.shop_home_page import ShopHomePage
from pages.shop_locators import (
    SHOP_ID_DIALOG_COMPLETE,
    SHOP_ID_MALL_BUY_NOW,
    SHOP_ID_MALL_KEFU,
    SHOP_IM_INPUT_ID_SUFFIXES,
    SHOP_SHARE_ID_SUFFIXES,
    SHOP_TEXT_DAILY_BAIHUO,
)

logger = setup_logger(__name__)


class ShopBusinessPage(
    MallBusinessSearchMixin,
    MallBusinessDetailMixin,
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
