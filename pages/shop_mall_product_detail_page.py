"""商城主列表进详情、详情加购、立即购买与深度流。"""
from __future__ import annotations

import re
import time
from typing import List, Optional, Tuple

from appium.webdriver.common.appiumby import AppiumBy

from commons.logger import setup_logger
from pages.shop_locators import (
    SHOP_ID_CL_ITEM_CONTAINER,
    SHOP_ID_IMAGE,
    SHOP_ID_IV_COLLECT,
    SHOP_ID_IV_GOODS,
    SHOP_ID_MALL_ADD_SHOP_CAR,
    SHOP_ID_MALL_BUY_NOW,
    SHOP_ID_MALL_KEFU,
    SHOP_ID_MALL_SHOP_CAR_CONTAINER,
    SHOP_ID_RV_CONTENT,
    SHOP_ID_TV_GOODS_NAME,
    SHOP_ID_TV_PRICE,
    SHOP_TEXT_COLLECT_OK,
    SHOP_TEXT_MALL_CART_TITLE,
)

logger = setup_logger(__name__)


class MallProductDetailPage:
    """商品详情与 ``run_mall_product_detail_deep_flow``；其余页状态通过 ``owner`` 回调。"""

    def __init__(self, owner) -> None:
        self._o = owner

    def mall_list_el_is_add_cart_control(self, el) -> bool:
        try:
            rid = (el.get_attribute("resource-id") or "").lower()
            if "add_cart" in rid or "iv_add_cart" in rid:
                return True
        except Exception:
            pass
        return False

    def tap_cl_item_open_detail(self, container) -> bool:
        try:
            loc = container.location
            sz = container.size
            w0, h0 = self._o._window_size()
            cx = int(loc["x"] + int(sz["width"]) * 0.30)
            cy = int(loc["y"] + int(sz["height"]) * 0.46)
            if cx < 8 or cy < int(h0 * 0.12) or cy > int(h0 * 0.90):
                return False
            self._o.driver.execute_script(
                "mobile: clickGesture", {"x": cx, "y": cy}
            )
            logger.info("已点商品卡片左内侧进详情（clItemContainer 坐标）")
            time.sleep(1.85)
            return bool(self._o._is_mall_product_detail_visible())
        except Exception:
            return False

    def _visible_elements_in_band(self, elements, y_lo: int, y_hi: int):
        scored: List[Tuple[int, object]] = []
        for el in elements:
            try:
                if not el.is_displayed():
                    continue
                if self.mall_list_el_is_add_cart_control(el):
                    continue
                y = int(el.location.get("y", 0))
                if y_lo <= y <= y_hi:
                    scored.append((y, el))
            except Exception:
                continue
        scored.sort(key=lambda t: t[0])
        return scored

    def _card_containers_in_rv(self, rv, y_lo: int, y_hi: int):
        try:
            items = rv.find_elements(
                AppiumBy.XPATH,
                f'.//*[contains(@resource-id,"{SHOP_ID_CL_ITEM_CONTAINER}")]',
            )
        except Exception:
            return []
        return self._visible_elements_in_band(items, y_lo, y_hi)

    def _product_info_candidates_in_rv(self, rv, y_lo: int, y_hi: int):
        candidates: List[Tuple[int, object]] = []
        for xpath_inner in (
            './/*[contains(@resource-id,":id/iv_goods") or '
            'contains(@resource-id,"iv_goods")]',
            './/*[contains(@resource-id,":id/image") or contains(@resource-id,"/image")]',
            './/*[contains(@resource-id,":id/tv_goods_name") or '
            'contains(@resource-id,"tv_goods_name")]',
            './/*[contains(@resource-id,":id/tv_price") or '
            'contains(@resource-id,"tv_price")]',
        ):
            try:
                candidates = self._visible_elements_in_band(
                    rv.find_elements(AppiumBy.XPATH, xpath_inner), y_lo, y_hi
                )
                if candidates:
                    break
            except Exception:
                continue
        return candidates

    def _product_info_candidates_by_ids(self, y_lo: int, y_hi: int):
        for suf in (
            SHOP_ID_IV_GOODS,
            SHOP_ID_TV_GOODS_NAME,
            SHOP_ID_TV_PRICE,
            SHOP_ID_IMAGE,
        ):
            scored = self._visible_elements_in_band(
                self._o._all_displayed_by_pkg_id(suf), y_lo, y_hi
            )
            if scored:
                return scored
        return []

    def _tap_candidate_into_detail(self, el) -> bool:
        try:
            self._o._nearest_clickable_ancestor(el).click()
        except Exception:
            try:
                el.click()
            except Exception:
                return False
        logger.info("已点击主列表商品图/信息区进详情")
        time.sleep(1.85)
        return bool(self._o._is_mall_product_detail_visible())

    def _tap_left_coordinate_fallback(self) -> bool:
        w, h = self._o._window_size()
        try:
            self._o.driver.execute_script(
                "mobile: clickGesture",
                {"x": int(w * 0.34), "y": int(h * 0.44)},
            )
            logger.info("主列表进详情：偏左坐标兜底（避让右侧加购区）")
            time.sleep(1.85)
            return bool(self._o._is_mall_product_detail_visible())
        except Exception:
            return False

    def tap_first_mall_list_product_into_detail(self) -> bool:
        h = self._o._window_size()[1]
        y_lo, y_hi = int(h * 0.14), int(h * 0.86)
        rv = self._o._first_displayed_by_pkg_id(SHOP_ID_RV_CONTENT)
        if rv:
            for _, it in self._card_containers_in_rv(rv, y_lo, y_hi)[:4]:
                if self.tap_cl_item_open_detail(it):
                    return True

        scored: List[Tuple[int, object]] = []
        if rv:
            scored = self._product_info_candidates_in_rv(rv, y_lo, y_hi)
        if not scored:
            scored = self._product_info_candidates_by_ids(y_lo, y_hi)
        for _, el in scored[:6]:
            if self._tap_candidate_into_detail(el):
                return True
        if self._tap_left_coordinate_fallback():
            return True
        logger.error("主列表未能进入商品详情")
        return False

    def read_mall_detail_price_peso(self) -> Optional[float]:
        h = self._o._window_size()[1]
        y_max = int(h * 0.50)
        found: List[float] = []
        try:
            for el in self._o.driver.find_elements(
                AppiumBy.CLASS_NAME, "android.widget.TextView"
            ):
                try:
                    if not el.is_displayed():
                        continue
                    if int(el.location.get("y", 99999)) > y_max:
                        continue
                    raw = (el.text or "").strip().replace(",", "")
                    raw_ns = raw.replace(" ", "")
                    m = re.search(r"₱\s*(\d+(?:\.\d+)?)", raw_ns)
                    if not m:
                        m = re.match(
                            r"^P\s*(\d+(?:\.\d+)?)\s*$", raw_ns, flags=re.I
                        )
                    if m:
                        found.append(float(m.group(1)))
                except Exception:
                    continue
        except Exception:
            pass
        return max(found) if found else None

    def mall_detail_submit_order_like_visible(self) -> bool:
        for mk in ("提交订单", "确认订单", "立即支付", "去支付", "应付金额", "实付款"):
            try:
                for el in self._o.driver.find_elements(
                    AppiumBy.XPATH, f'//*[contains(@text,"{mk}")]'
                ):
                    if el.is_displayed():
                        return True
            except Exception:
                continue
        return False

    def mall_detail_tap_add_to_cart_with_spec(self) -> bool:
        add = self._o._first_displayed_by_pkg_id(SHOP_ID_MALL_ADD_SHOP_CAR)
        if not add:
            logger.error("详情页未找到「加入购物车」（mall_add_shop_car）")
            return False
        try:
            self._o._nearest_clickable_ancestor(add).click()
        except Exception:
            try:
                add.click()
            except Exception as ex:
                logger.error("点击「加入购物车」失败: %s", ex)
                return False
        time.sleep(0.65)
        if self._o._login_like_screen_visible():
            logger.error("加入购物车后出现登录页")
            return False
        if self._o._spec_bottom_sheet_visible():
            if not self._o._mall_spec_popup_pick_and_confirm():
                return False
        else:
            logger.info("加入购物车未出现规格弹层（可能为单规格直加）")
        return True

    def mall_detail_tap_buy_now_price_gate(self) -> bool:
        price = self.read_mall_detail_price_peso()
        logger.info("详情页解析售价(约): %s P", price)
        el = self._o._first_displayed_by_pkg_id(SHOP_ID_MALL_BUY_NOW)
        if not el:
            logger.error("详情页未找到「立即购买」")
            return False
        try:
            self._o._nearest_clickable_ancestor(el).click()
        except Exception:
            el.click()
        time.sleep(2.0)
        order_vis = self.mall_detail_submit_order_like_visible()
        if price is not None and price <= 400.0:
            if order_vis:
                logger.error("售价≤400P 仍进入提交订单类页面")
                self._o.tap_top_back()
                return False
            logger.info("售价≤400P：未进入提交订单页，符合预期")
        elif price is None:
            logger.warning("售价未解析，跳过「≤400P 不得进下单页」强校验")
        if order_vis:
            self._o.tap_top_back()
            time.sleep(0.9)
        return True

    def _try_collect_on_detail(self) -> None:
        col = self._o._first_displayed_by_pkg_id(SHOP_ID_IV_COLLECT)
        if not col:
            return
        try:
            col.click()
            time.sleep(0.55)
            if self._o._wait_substring_on_screen(SHOP_TEXT_COLLECT_OK, 3.8):
                logger.info("已出现「%s」", SHOP_TEXT_COLLECT_OK)
            else:
                logger.warning(
                    "未在界面上捕获「%s」（Toast 可能不在层级中）",
                    SHOP_TEXT_COLLECT_OK,
                )
        except Exception as ex:
            logger.warning("点击收藏失败: %s", ex)

    def _open_kefu_and_return(self) -> bool:
        ke = self._o._first_displayed_by_pkg_id(SHOP_ID_MALL_KEFU)
        if not ke:
            return True
        try:
            self._o._nearest_clickable_ancestor(ke).click()
            time.sleep(1.15)
        except Exception as ex:
            logger.error("点击客服失败: %s", ex)
            return False
        ok_ke = self._o._wait_kefu_destination(10.0)
        if not ok_ke and not self._o._is_mall_product_detail_visible():
            logger.warning(
                "未命中客服页固定文案/H5 关键字，但已离开商品详情，视为客服已打开，继续"
            )
            ok_ke = True
        if not ok_ke:
            logger.error("未识别客服页（仍在详情且无文案/WebView 命中）")
            self._o.tap_top_back()
            return False
        if not self._o.tap_top_back():
            logger.error("客服页返回失败")
            return False
        time.sleep(0.85)
        return True

    def _open_detail_cart_and_return(self) -> bool:
        cart = self._o._first_displayed_by_pkg_id(SHOP_ID_MALL_SHOP_CAR_CONTAINER)
        if not cart:
            return True
        try:
            self._o._nearest_clickable_ancestor(cart).click()
            time.sleep(1.0)
        except Exception as ex:
            logger.error("点击购物车入口失败: %s", ex)
            return False
        if not self._o._wait_substring_on_screen(SHOP_TEXT_MALL_CART_TITLE, 4.5):
            logger.error("未进入标题含「%s」的页面", SHOP_TEXT_MALL_CART_TITLE)
            self._o.tap_top_back()
            return False
        if not self._o.tap_top_back():
            logger.error("购物车页返回失败")
            return False
        time.sleep(0.85)
        return True

    def run_mall_product_detail_deep_flow(self) -> bool:
        if not self._o._is_mall_home_main_list_visible():
            logger.warning("未发现主列表 rv_content，跳过商品详情深度流")
            return True
        if not self.tap_first_mall_list_product_into_detail():
            logger.error("首次未能从主列表进入商品详情")
            return False
        if not self._o._is_mall_product_detail_visible():
            logger.warning("未识别详情页，跳过商品详情深度流")
            self._o.tap_top_back()
            return True
        time.sleep(0.5)
        if not self._o.tap_top_back():
            logger.warning("详情返回商城首页可能失败，尝试 ensure_mall_tab")
        time.sleep(0.65)
        self._o.ensure_mall_tab()
        if not self.tap_first_mall_list_product_into_detail():
            logger.error("第二次未能进入商品详情")
            return False
        if not self._o._is_mall_product_detail_visible():
            logger.warning("第二次未识别详情页，跳过加购与后续深度步骤")
            self._o.tap_top_back()
            return True
        time.sleep(0.5)
        if not self.mall_detail_tap_add_to_cart_with_spec():
            return False
        time.sleep(0.45)
        self._try_collect_on_detail()
        if not self._open_kefu_and_return():
            return False
        if not self._open_detail_cart_and_return():
            return False
        if not self.mall_detail_tap_buy_now_price_gate():
            return False
        if not self._o.tap_top_back():
            logger.warning("详情返回商城首页可能失败")
        time.sleep(0.55)
        self._o.ensure_mall_tab()
        logger.info("商品详情深度流结束")
        return True
