#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
商城下单 E2E 脚本：立即购买路径 + 购物车提交订单路径。

前置条件：
  1. Appium 已启动，设备已连接。
  2. 用户已登录，且账号存在默认收货地址。
  3. 测试商品库存充足；如需严格校验库存扣减，传入 --stock-api-url。

安全说明：
  默认只走到「确认订单」页并做页面断言，不点击「提交订单」。
  需要真实提交/收银台/货到付款/订单详情 IM 时，必须显式传入 --submit-order。

示例：
  python scripts/run_mall_order_flow.py --flow buy_now --keyword "可乐" --spec 黑色 --spec L
  python scripts/run_mall_order_flow.py --flow cart --keyword "可乐" --spec 黑色 --spec L
  python scripts/run_mall_order_flow.py --flow buy_now --keyword "可乐" --ensure-test-address
  python scripts/run_mall_order_flow.py --flow buy_now --keyword "可乐" --coupon-policy require
  python scripts/run_mall_order_flow.py --add-test-address-only --force-add-test-address
  python scripts/run_mall_order_flow.py --add-test-address-only --edit-test-address
  python scripts/run_mall_order_flow.py --add-test-address-only --copy-test-address
  python scripts/run_mall_order_flow.py --flow both --keyword "可乐" --spec 黑色 --spec L ^
    --submit-order --payment-method cod --stock-api-url "http://test-api/sku/{sku}/stock"
  python scripts/run_mall_order_flow.py --flow buy_now --keyword "123" --spec 黑色 --spec L ^
    --submit-order --payment-method wechat_mock ^
    --mock-pay-success-url "http://test-api/pay/mock_success?orderNo={order_no}"

异常流：
  python scripts/run_mall_order_flow.py --run-stockout --stockout-keyword "库存不足商品"
  python scripts/run_mall_order_flow.py --run-network-exception --keyword "可乐" --spec 黑色 --spec L
"""
from __future__ import annotations

import argparse
import html
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence, Tuple

from appium.webdriver.common.appiumby import AppiumBy

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from commons.driver import DriverManager
from commons.diagnostics import capture_failure
from commons.logger import setup_logger
from flows.mall_order_http import (
    MallOrderHttpClient,
    MallOrderHttpError,
)
from flows.mall_order_types import (
    ProductSnapshot,
    parse_money,
)
from pages.mall_order_address_mixin import MallOrderAddressMixin
from pages.mall_order_cart_mixin import MallOrderCartMixin
from pages.mall_order_checkout_mixin import MallOrderCheckoutMixin
from pages.shop_business_page import ShopBusinessPage
from pages.shop_locators import (
    SHOP_ID_COUNT_ADD,
    SHOP_ID_MALL_BUY_NOW,
    SHOP_ID_MALL_CATEGORY_GOODS_NAME,
    SHOP_ID_TV_GOODS_NAME,
    SHOP_ID_TV_PRICE,
)

logger = setup_logger(__name__)


CHECKOUT_MARKERS: Tuple[str, ...] = (
    "确认订单",
    "提交订单",
    "收货地址",
    "商品金额",
    "实付",
    "应付",
)
NETWORK_ERROR_MARKERS: Tuple[str, ...] = (
    "网络异常",
    "网络错误",
    "请求失败",
    "请检查网络",
    "加载失败",
    "重试",
)
STOCKOUT_MARKERS: Tuple[str, ...] = (
    "库存不足",
    "库存不够",
    "已售罄",
    "补货中",
)
DEFAULT_RIDER_REMARK = "请把餐品放到大楼前台 Please place the meal at the reception desk"
DEFAULT_MERCHANT_REMARK = "如缺货，直接取消订单 Any product no stock, cancel order"
DEFAULT_REMARK_TEXT = "test order"
DEFAULT_ADDRESS_QUERY = os.environ.get("MALL_TEST_ADDRESS_QUERY", "").strip()
DEFAULT_ADDRESS_NAME = os.environ.get("MALL_TEST_ADDRESS_NAME", "").strip()
DEFAULT_ADDRESS_PHONE = os.environ.get("MALL_TEST_ADDRESS_PHONE", "").strip()
DEFAULT_ADDRESS_WECHAT = os.environ.get("MALL_TEST_ADDRESS_WECHAT", "").strip()
DEFAULT_ADDRESS_DETAIL = os.environ.get("MALL_TEST_ADDRESS_DETAIL", "").strip()
class MallOrderFlow(
    MallOrderAddressMixin,
    MallOrderCartMixin,
    MallOrderCheckoutMixin,
    ShopBusinessPage,
):
    """基于现有 ShopBusinessPage 补齐下单场景断言。"""

    def __init__(
        self,
        driver,
        *,
        sku: str,
        specs: Sequence[str],
        quantity: int,
        expected_name: Optional[str],
        expected_name_contains: Optional[str],
        preorder_api_pattern: str,
        skip_api_log_assert: bool,
        stock_api_url: Optional[str],
        order_status_api_url: Optional[str],
        mock_pay_success_url: Optional[str],
        skip_stock_assert: bool,
        payment_method: str,
        min_order_amount: float,
        max_payable: Optional[float],
        cancel_after_order: bool,
        pick_preorder_time: bool,
        send_im_after_order: bool,
        im_message_template: str,
        coupon_policy: str,
        pickup_code: str,
        notify_method: str,
        remark_text: Optional[str],
        rider_remark: Optional[str],
        merchant_remark: Optional[str],
        ensure_test_address: bool,
        force_add_test_address: bool,
        edit_test_address: bool,
        copy_test_address: bool,
        address_query: str,
        address_name: str,
        address_phone: str,
        address_wechat: str,
        address_detail: str,
    ) -> None:
        super().__init__(driver)
        self.sku = sku
        self.specs = tuple(s for s in specs if s)
        self.quantity = max(1, quantity)
        self.expected_name = expected_name
        self.expected_name_contains = (expected_name_contains or "").strip()
        self.preorder_api_pattern = preorder_api_pattern
        self.skip_api_log_assert = skip_api_log_assert
        self.stock_api_url = stock_api_url
        self.order_status_api_url = order_status_api_url
        self.mock_pay_success_url = mock_pay_success_url
        self.skip_stock_assert = skip_stock_assert
        self.payment_method = (payment_method or "cod").strip().lower()
        self.min_order_amount = float(min_order_amount or 0.0)
        self.max_payable = max_payable
        self.cancel_after_order = cancel_after_order
        self.pick_preorder_time = pick_preorder_time
        self.send_im_after_order = send_im_after_order
        self.im_message_template = im_message_template
        self.coupon_policy = (coupon_policy or "auto").strip().lower()
        self.pickup_code = (pickup_code or "keep").strip().lower()
        self.notify_method = (notify_method or "keep").strip().lower()
        self.remark_text = (remark_text if remark_text is not None else DEFAULT_REMARK_TEXT).strip()
        self.rider_remark = (rider_remark or "").strip()
        self.merchant_remark = (merchant_remark or "").strip()
        self.ensure_test_address = ensure_test_address
        self.force_add_test_address = force_add_test_address
        self.edit_test_address = edit_test_address
        self.copy_test_address = copy_test_address
        self.address_query = (address_query or DEFAULT_ADDRESS_QUERY).strip()
        self.address_name = (address_name or DEFAULT_ADDRESS_NAME).strip()
        self.address_phone = (address_phone or DEFAULT_ADDRESS_PHONE).strip()
        self.address_wechat = (address_wechat or DEFAULT_ADDRESS_WECHAT).strip()
        self.address_detail = (address_detail or DEFAULT_ADDRESS_DETAIL).strip()
        self.http = MallOrderHttpClient(
            sku=self.sku,
            quantity=self.quantity,
            stock_api_url=self.stock_api_url,
            order_status_api_url=self.order_status_api_url,
            mock_pay_success_url=self.mock_pay_success_url,
        )

    # ---------- 通用读取与点击 ----------

    def page_texts(self) -> List[str]:
        try:
            src = self.driver.page_source or ""
        except Exception:
            src = ""
        texts: List[str] = []
        for m in re.finditer(r'(?:text|content-desc)="([^"]*)"', src):
            tx = html.unescape(m.group(1)).strip()
            if tx and tx.lower() != "null":
                texts.append(tx)
        return texts

    def page_blob(self) -> str:
        return "\n".join(self.page_texts())

    def wait_page_contains_any(
        self, markers: Sequence[str], timeout: float = 8.0
    ) -> bool:
        end = time.time() + timeout
        while time.time() < end:
            blob = self.page_blob()
            if any(m in blob for m in markers):
                return True
            time.sleep(0.35)
        return False

    def assert_page_contains_any(
        self, markers: Sequence[str], msg: str, timeout: float = 8.0
    ) -> None:
        if not self.wait_page_contains_any(markers, timeout=timeout):
            raise AssertionError(msg)

    def click_labels(
        self,
        labels: Iterable[str],
        *,
        desc: str,
        y_min_ratio: float = 0.0,
        y_max_ratio: float = 1.0,
        exact: bool = False,
    ) -> bool:
        return self._click_first_text_or_desc(
            tuple(labels),
            y_min_ratio=y_min_ratio,
            y_max_ratio=y_max_ratio,
            exact=exact,
            desc=desc,
        )

    def click_by_id_or_label(
        self,
        id_suffix: str,
        labels: Sequence[str],
        *,
        desc: str,
        y_min_ratio: float = 0.0,
        y_max_ratio: float = 1.0,
    ) -> bool:
        el = self._first_displayed_by_pkg_id(id_suffix)
        if el and self._click_element_center(el, desc):
            return True
        return self.click_labels(
            labels,
            desc=desc,
            y_min_ratio=y_min_ratio,
            y_max_ratio=y_max_ratio,
        )

    def safe_back_to_mall(self) -> None:
        for _ in range(5):
            if self._is_mall_home_main_list_visible():
                return
            if self._is_mall_product_detail_visible():
                self.tap_top_back()
                time.sleep(0.6)
                continue
            self.tap_top_back()
            time.sleep(0.5)
            self.click_labels(("确定", "确认", "放弃", "离开"), desc="返回确认", exact=True)
        self.ensure_mall_tab()

    def click_first_by_id_in_band(
        self,
        id_suffix: str,
        desc: str,
        *,
        x_min_ratio: float = 0.0,
        x_max_ratio: float = 1.0,
        y_min_ratio: float = 0.0,
        y_max_ratio: float = 1.0,
    ) -> bool:
        w, h = self._window_size()
        x_min, x_max = int(w * x_min_ratio), int(w * x_max_ratio)
        y_min, y_max = int(h * y_min_ratio), int(h * y_max_ratio)
        candidates = []
        for el in self._all_displayed_by_pkg_id(id_suffix):
            try:
                if not el.is_displayed():
                    continue
                loc, size = el.location, el.size
                cx = int(loc.get("x", 0) + size.get("width", 0) / 2)
                cy = int(loc.get("y", 0) + size.get("height", 0) / 2)
                if not (x_min <= cx <= x_max and y_min <= cy <= y_max):
                    continue
                candidates.append((cy, cx, el))
            except Exception:
                continue
        candidates.sort(key=lambda item: (item[0], item[1]))
        for _, _, el in candidates:
            if self._click_element_center(el, desc):
                return True
        return False

    # ---------- 商品信息与规格 ----------

    def read_first_text_by_suffixes(self, suffixes: Sequence[str]) -> str:
        for suffix in suffixes:
            els = self._all_displayed_by_pkg_id(suffix)
            for el in els:
                try:
                    tx = (el.text or "").strip()
                    if tx:
                        return tx
                except Exception:
                    continue
        return ""

    def read_first_price_by_suffixes(self, suffixes: Sequence[str]) -> Optional[float]:
        for suffix in suffixes:
            els = self._all_displayed_by_pkg_id(suffix)
            for el in els:
                try:
                    val = parse_money(el.text or "")
                    if val is not None:
                        return abs(val)
                except Exception:
                    continue
        for tx in self.page_texts():
            if any(ch in tx for ch in ("￥", "¥", "₱", "P")):
                val = parse_money(tx)
                if val is not None:
                    return abs(val)
        return None

    def read_stock_from_page(self) -> Optional[int]:
        blob = self.page_blob()
        for pat in (
            r"库存\s*[:：]?\s*(\d+)",
            r"剩余\s*[:：]?\s*(\d+)",
            r"仅剩\s*(\d+)",
        ):
            m = re.search(pat, blob)
            if m:
                return int(m.group(1))
        return None

    def read_stock_by_api(self) -> Optional[int]:
        try:
            return self.http.read_stock()
        except MallOrderHttpError as exc:
            raise AssertionError(str(exc)) from exc

    def read_probable_product_name_from_texts(self) -> str:
        ban = (
            "商品详情",
            "购物车",
            "立即购买",
            "加入购物车",
            "客服",
            "首页",
            "商城",
            "搜索",
            "销量",
            "价格",
            "折扣",
            "优惠",
            "规格",
            "数量",
            "库存",
            "配送",
            "确认订单",
            "提交订单",
            "请选择",
            "请选择规格",
        )
        candidates: List[str] = []
        for tx in self.page_texts():
            text = re.sub(r"\s+", " ", tx).strip()
            if len(text) < 2 or len(text) > 90:
                continue
            if parse_money(text) is not None:
                continue
            if text in ban or any(text.startswith(prefix) for prefix in ("已选", "选择", "月售")):
                continue
            if re.fullmatch(r"[\d\s:：./-]+", text):
                continue
            candidates.append(text)
        if self.expected_name_contains:
            for text in candidates:
                if self.expected_name_contains in text:
                    return text
        return candidates[0] if candidates else ""

    def read_detail_snapshot(self) -> ProductSnapshot:
        name = self.expected_name or self.read_first_text_by_suffixes(
            (SHOP_ID_TV_GOODS_NAME, SHOP_ID_MALL_CATEGORY_GOODS_NAME)
        )
        if not name:
            name = self.read_probable_product_name_from_texts()
        if not name:
            raise AssertionError("商品详情页未解析到商品名称，请传 --expected-name 或核对商品名称控件")
        if self.expected_name_contains and self.expected_name_contains not in name:
            raise AssertionError(
                f"商品名称断言失败：详情页商品名「{name}」未包含「{self.expected_name_contains}」"
            )
        unit_price = self.read_first_price_by_suffixes((SHOP_ID_TV_PRICE,))
        if unit_price is None:
            raise AssertionError("商品详情页未解析到单价，请核对 tv_price 或金额文案")
        stock_before = self.read_stock_by_api()
        if stock_before is None:
            stock_before = self.read_stock_from_page()
        logger.info(
            "商品快照：name=%s specs=%s unit_price=%s qty=%s stock_before=%s",
            name,
            "/".join(self.specs) or "(未指定)",
            unit_price,
            self.quantity,
            stock_before,
        )
        return ProductSnapshot(
            name=name,
            specs=self.specs,
            unit_price=unit_price,
            quantity=self.quantity,
            sku=self.sku,
            stock_before=stock_before,
        )

    def tap_spec_text(self, label: str) -> bool:
        safe = label.replace('"', "").replace("'", "")[:32]
        h = self._window_size()[1]
        with self._mall_ctx.zero_implicit_wait():
            xpaths = (
                f'//*[@text="{safe}" or @content-desc="{safe}"]',
                f'//*[contains(@text,"{safe}") or contains(@content-desc,"{safe}")]',
            )
            for xp in xpaths:
                try:
                    for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                        try:
                            if not el.is_displayed():
                                continue
                            y = int(el.location.get("y", 0))
                            if y < int(h * 0.22):
                                continue
                            if self._click_element_center(el, f"规格项:{label}"):
                                return True
                        except Exception:
                            continue
                except Exception:
                    continue
        return False

    def select_specs_and_quantity(self) -> Optional[int]:
        """规格弹层可见时选择指定规格与数量；返回弹层中读到的库存。"""
        if not self._spec_bottom_sheet_visible():
            return None
        stock = self.read_stock_from_page()
        if self.specs:
            for spec in self.specs:
                if not self.tap_spec_text(spec):
                    raise AssertionError(f"规格弹层未找到指定规格：{spec}")
                time.sleep(0.25)
            for _ in range(self.quantity - 1):
                add = self._first_displayed_by_pkg_id(SHOP_ID_COUNT_ADD)
                if add and self._click_element_center(add, "数量加号"):
                    time.sleep(0.2)
                    continue
                if not self.click_labels(("+",), desc="数量加号", y_min_ratio=0.35, y_max_ratio=1.0, exact=True):
                    raise AssertionError("规格弹层未找到数量加号，无法设置购买数量")
            if not self._tap_mall_spec_sheet_confirm_button():
                raise AssertionError("规格弹层未点到「完成/确定」按钮")
        elif not self._mall_spec_popup_pick_and_confirm():
            raise AssertionError("规格弹层未能按元素结构完成选择")
        time.sleep(1.2)
        return stock

    def assert_under_min_popup_and_return(self, product: ProductSnapshot) -> None:
        """商品金额未超过门槛时，断言出现限制提示并回到商品详情页。"""
        if not self.wait_under_min_amount_prompt(timeout=5.0):
            raise AssertionError(
                "商品金额 %.2f 未超过 %.2f，但未出现 400P/最低金额相关提示"
                % (product.unit_price * product.quantity, self.min_order_amount)
            )
        self.click_labels(
            ("确定", "确认", "知道了", "我知道了"),
            desc="金额不足弹窗确认",
            y_min_ratio=0.20,
            y_max_ratio=1.0,
            exact=False,
        )
        time.sleep(0.8)
        if not self._is_mall_product_detail_visible():
            self.tap_top_back()
            time.sleep(0.8)
        if not self._is_mall_product_detail_visible():
            raise AssertionError("金额不足弹窗确认后未返回商品详情页")
        logger.info("金额不足保护校验通过：已确认弹窗并返回商品详情页")

    def wait_under_min_amount_prompt(self, timeout: float = 3.0) -> bool:
        end = time.time() + timeout
        amount_words = ("400", "四百", "披索", "比索", "P400", "₱400")
        reject_words = ("不满足", "未满足", "不能购买", "无法购买", "起购", "最低", "满", "不足")
        while time.time() < end:
            blob = self.page_blob()
            if "低价换购" in blob or "确认换购" in blob or "放弃机会" in blob:
                return False
            if any(a in blob for a in amount_words) and any(r in blob for r in reject_words):
                return True
            if any(mark in blob for mark in ("低于起购金额", "未达到起购金额", "未达到最低购买金额")):
                return True
            time.sleep(0.3)
        return False

    def dismiss_checkout_upsell_if_visible(self) -> bool:
        """确认订单页满额低价换购弹窗：放弃换购，继续主订单流程。"""
        if not self.wait_page_contains_any(("低价换购", "确认换购", "放弃机会"), timeout=1.0):
            return False
        if self.click_labels(
            ("放弃机会", "暂不换购", "不换购"),
            desc="放弃换购",
            y_min_ratio=0.50,
            y_max_ratio=0.88,
        ):
            time.sleep(1.0)
            logger.info("已关闭满额低价换购弹窗")
            return True
        raise AssertionError("出现低价换购弹窗，但未找到「放弃机会」")

    def select_default_address_if_popup_visible(self) -> bool:
        """提交后若出现「配送至」地址弹层，选择第一条可见地址。"""
        if not self.wait_page_contains_any(("配送至", "选择其他收货地址"), timeout=1.0):
            return False
        for pkg in self._shop_packages_prioritized():
            rid = self._rid(pkg, "tv_address")
            try:
                for el in self.driver.find_elements(AppiumBy.ID, rid):
                    try:
                        if not el.is_displayed():
                            continue
                        if self._click_element_center(el, "地址弹层第一条地址"):
                            time.sleep(1.0)
                            return True
                    except Exception:
                        continue
            except Exception:
                continue
        raise AssertionError("出现地址选择弹层，但未能选择默认地址")

    # ---------- 预订时间 ----------

    def search_goods(self, keyword: str) -> bool:
        """下单脚本专用搜索：禁用历史/热门搜索与活动浏览，直接搜索指定关键词。"""
        search_word = keyword.strip()
        if not search_word:
            logger.error("搜索关键字为空")
            return False
        if not self.open_search_page():
            return False
        time.sleep(0.45)
        if not self._type_into_best_edit_text(search_word):
            logger.error("搜索页未找到输入框")
            return False
        self._press_enter_or_search()
        ok = self._wait_page_contains_any(
            (search_word, "综合", "销量", "价格", "商品", "搜索"),
            timeout=8.0,
        )
        if ok:
            logger.info("下单搜索结果页已出现：%s", search_word)
        else:
            logger.warning("未明确识别搜索结果页，继续尝试点商品")
        return True

    def open_detail_and_snapshot(self, keyword: str) -> ProductSnapshot:
        if not self.open_goods_detail(keyword):
            raise AssertionError(f"未能进入商品详情页：keyword={keyword}")
        if not self._is_mall_product_detail_visible():
            raise AssertionError("当前页面不是商品详情页")
        return self.read_detail_snapshot()

    def run_navigation_verification(self, keyword: str) -> bool:
        """Read mall detail evidence and return without a business-data mutation."""
        previous_coordinate_fallback_disabled = getattr(
            self, "_mall_tab_coordinate_fallback_disabled", False
        )
        self._mall_tab_coordinate_fallback_disabled = True
        try:
            product = self.open_detail_and_snapshot(keyword)
            if not product.name:
                raise AssertionError("商品详情未读取到商品名称")
            capture_failure(self.driver, "mall_navigation_verification")
            self.safe_back_to_mall()
            return True
        finally:
            self._mall_tab_coordinate_fallback_disabled = (
                previous_coordinate_fallback_disabled
            )

    def open_daily_baihuo_detail_and_snapshot(self) -> ProductSnapshot:
        """日用百货分类选品入口，复用 ShopBusinessPage 中已验证的分类路径。"""
        if not self.ensure_mall_tab():
            raise AssertionError("未能进入商城首页")
        if not self.tap_mall_kingkong_daily_baihuo_via_popup():
            raise AssertionError("未能进入「日用百货」分类")
        time.sleep(1.0)
        if not self._tap_first_category_goods_item(min_price=self.min_order_amount):
            logger.warning(
                "日用百货未找到价格 >= %.2f 的可见商品，改点首个可见商品",
                self.min_order_amount,
            )
            if not self._tap_first_category_goods_item(min_price=None):
                raise AssertionError("日用百货分类未能打开商品详情")
        if not self._is_mall_product_detail_visible():
            raise AssertionError("日用百货商品未进入详情页")
        return self.read_detail_snapshot()

    def buy_now_to_checkout_exact_specs(self, product: ProductSnapshot) -> ProductSnapshot:
        under_min = (
            self.min_order_amount > 0
            and product.unit_price * product.quantity <= self.min_order_amount
        )
        if not self.click_by_id_or_label(
            SHOP_ID_MALL_BUY_NOW,
            ("立即购买", "马上抢", "购买"),
            desc="立即购买",
            y_min_ratio=0.52,
            y_max_ratio=1.0,
        ):
            raise AssertionError("商品详情页未找到「立即购买」")
        time.sleep(0.8)
        if self._login_like_screen_visible():
            raise AssertionError("立即购买后进入登录页，前置条件不满足：用户未登录")
        sheet_stock = self.select_specs_and_quantity()
        if product.stock_before is None and sheet_stock is not None:
            product.stock_before = sheet_stock
        if under_min:
            self.assert_under_min_popup_and_return(product)
            raise AssertionError(
                "商品金额 %.2f 未超过 %.2f，已按要求确认弹窗并返回商品详情页"
                % (product.unit_price * product.quantity, self.min_order_amount)
            )
        if self.wait_under_min_amount_prompt(timeout=1.2):
            raise AssertionError("商品金额满足门槛时仍出现 400P/最低金额相关提示")
        self.assert_page_contains_any(CHECKOUT_MARKERS, "立即购买后未跳转至订单确认页", timeout=10.0)
        logger.info("立即购买路径：已跳转至订单确认页")
        return product

    def run_buy_now_flow(self, keyword: str, *, submit_order: bool) -> bool:
        logger.info("开始立即购买路径")
        product = self.open_detail_and_snapshot(keyword)
        product = self.buy_now_to_checkout_exact_specs(product)
        self.finish_checkout(product, submit_order=submit_order)
        logger.info("立即购买路径通过")
        return True

    def run_daily_baihuo_buy_now_flow(self, *, submit_order: bool) -> bool:
        logger.info("开始日用百货立即购买路径")
        product = self.open_daily_baihuo_detail_and_snapshot()
        product = self.buy_now_to_checkout_exact_specs(product)
        self.finish_checkout(product, submit_order=submit_order)
        logger.info("日用百货立即购买路径通过")
        return True

    # ---------- 异常流 ----------

    def run_stockout_case(self, keyword: str, specs: Sequence[str]) -> bool:
        logger.info("开始库存不足异常流")
        old_specs = self.specs
        self.specs = tuple(s for s in specs if s) or self.specs
        try:
            self.open_detail_and_snapshot(keyword)
            self.click_by_id_or_label(
                SHOP_ID_MALL_BUY_NOW,
                ("立即购买", "马上抢", "购买"),
                desc="库存不足-立即购买",
                y_min_ratio=0.52,
                y_max_ratio=1.0,
            )
            time.sleep(0.8)
            if self._spec_bottom_sheet_visible():
                for spec in self.specs:
                    self.tap_spec_text(spec)
                    time.sleep(0.2)
                self._tap_mall_spec_sheet_confirm_button()
            self.assert_page_contains_any(STOCKOUT_MARKERS, "库存不足商品未出现库存不足提示", timeout=8.0)
            logger.info("库存不足异常流通过")
            return True
        finally:
            self.specs = old_specs

    def set_network_offline(self) -> Optional[Any]:
        try:
            original = self.driver.network_connection
        except Exception:
            original = None
        try:
            self.driver.set_network_connection(0)
            logger.info("已切断设备网络")
            time.sleep(1.0)
            return original
        except Exception as ex:
            raise AssertionError(f"无法通过 Appium 切断网络，不能执行网络异常流：{ex}") from ex

    def restore_network(self, original: Optional[Any]) -> None:
        try:
            if original is None:
                self.driver.set_network_connection(6)
            else:
                self.driver.set_network_connection(original)
            logger.info("已恢复设备网络")
        except Exception as ex:
            logger.warning("恢复网络失败，请手动检查设备网络：%s", ex)

    def run_network_exception_case(self, keyword: str) -> bool:
        logger.info("开始网络异常提交订单流")
        product = self.open_detail_and_snapshot(keyword)
        product = self.buy_now_to_checkout_exact_specs(product)
        self.assert_checkout_matches_detail(product)
        original = self.set_network_offline()
        try:
            clicked = self.click_labels(
                ("提交订单", "确认订单"),
                desc="网络异常-提交订单",
                y_min_ratio=0.52,
                y_max_ratio=1.0,
            )
            if not clicked:
                raise AssertionError("网络异常流未找到提交订单按钮")
            self.assert_page_contains_any(
                NETWORK_ERROR_MARKERS,
                "断网提交订单后未出现网络异常/重试/友好提示",
                timeout=12.0,
            )
            logger.info("网络异常提示校验通过")
            if self.click_labels(("重试", "重新加载"), desc="网络异常-重试", y_min_ratio=0.20, y_max_ratio=1.0):
                self.assert_page_contains_any(
                    NETWORK_ERROR_MARKERS,
                    "点击重试后未保留网络异常友好提示",
                    timeout=6.0,
                )
            logger.info("网络异常流通过")
            return True
        finally:
            self.restore_network(original)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="商城下单：立即购买/购物车提交订单 E2E")
    parser.add_argument("--flow", choices=("buy_now", "cart", "both"), default="buy_now")
    parser.add_argument(
        "--verify-navigation-only",
        action="store_true",
        help="只验证商城搜索、详情读取和安全返回，不改变业务数据",
    )
    parser.add_argument(
        "--allow-cart-mutation",
        action="store_true",
        help="显式授权本次运行新增或删除购物车商品",
    )
    parser.add_argument(
        "--add-to-cart-only",
        action="store_true",
        help="只加购并验证购物车商品，不进入结算",
    )
    parser.add_argument(
        "--product-source",
        choices=("daily_baihuo", "search"),
        default="daily_baihuo",
        help="下单商品来源：默认走日用百货分类选品；search 走关键字搜索",
    )
    parser.add_argument("--keyword", default="可乐", help="商品搜索关键字；默认搜索常见商品名「可乐」")
    parser.add_argument("--sku", default="123", help="库存/支付测试钩子使用的 SKU")
    parser.add_argument("--expected-name", default=None, help="商品名称断言；不传则从详情页读取")
    parser.add_argument(
        "--expected-name-contains",
        default=None,
        help="商品名称需包含的文案；不传时默认使用 --keyword，例如搜索可乐则断言商品名包含可乐",
    )
    parser.add_argument(
        "--spec",
        action="append",
        default=[],
        help="需选择的规格文案，可重复传入，如 --spec 黑色 --spec L",
    )
    parser.add_argument("--quantity", type=int, default=1, help="购买数量")
    parser.add_argument(
        "--min-order-amount",
        type=float,
        default=400.0,
        help="立即购买金额门槛；商品金额需大于该值，不满足时断言弹窗并返回详情页",
    )
    parser.add_argument(
        "--skip-preorder-time",
        action="store_true",
        help="跳过订单确认页选择明天随机预订时间段",
    )
    parser.add_argument(
        "--coupon-policy",
        choices=("auto", "skip", "require"),
        default="auto",
        help="商城只处理平台优惠券：auto 有可用则选；skip 不选；require 必须有可用平台券",
    )
    parser.add_argument(
        "--pickup-code",
        choices=("keep", "on", "off"),
        default="keep",
        help="取件码开关：keep 保持当前；on 开启；off 关闭",
    )
    parser.add_argument(
        "--notify-method",
        choices=("keep", "app", "phone"),
        default="keep",
        help="通知方式：keep 保持当前；app 选择 APP 联系；phone 选择电话联系",
    )
    parser.add_argument(
        "--remark-text",
        default=DEFAULT_REMARK_TEXT,
        help="订单备注/留言自由输入文案；默认 test order，传空字符串可只选快捷备注",
    )
    parser.add_argument(
        "--rider-remark",
        default=DEFAULT_RIDER_REMARK,
        help="对骑手快捷备注；传空字符串可跳过",
    )
    parser.add_argument(
        "--merchant-remark",
        default=DEFAULT_MERCHANT_REMARK,
        help="对商家快捷备注；传空字符串可跳过",
    )
    parser.add_argument(
        "--run-cart-delete",
        action="store_true",
        help="只执行商城购物车删除逻辑，不执行下单主流程",
    )
    parser.add_argument(
        "--cart-delete-mode",
        choices=("manage_all", "manage_partial", "manage_none", "minus", "swipe"),
        default="manage_all",
        help="购物车删除方式：管理全选/管理部分/未选提示/减号删除/左滑删除",
    )
    parser.add_argument(
        "--cart-delete-prepare-item",
        action="store_true",
        help="删除前先按 --keyword/--spec 加购一个商品作为测试数据",
    )
    parser.add_argument(
        "--ensure-test-address",
        action="store_true",
        help="订单确认页点击收货地址，选择已有测试地址；不存在则新增测试地址",
    )
    parser.add_argument(
        "--force-add-test-address",
        action="store_true",
        help="不复用已有测试地址，强制点击新增地址按钮创建一条测试地址",
    )
    parser.add_argument(
        "--edit-test-address",
        action="store_true",
        help="目标地址已存在时进入编辑收货地址页，重新选择地图地址并保存",
    )
    parser.add_argument(
        "--copy-test-address",
        action="store_true",
        help="目标地址已存在时点击复制图标；若进入表单页则补齐必填信息并保存",
    )
    parser.add_argument(
        "--add-test-address-only",
        action="store_true",
        help="只从「我的」页进入我的地址并新增/选择测试地址，不执行商城下单",
    )
    parser.add_argument(
        "--allow-address-mutation",
        action="store_true",
        help="显式授权本次运行新增、编辑、复制或强制选择测试地址",
    )
    parser.add_argument(
        "--address-query",
        default=DEFAULT_ADDRESS_QUERY,
        help="地址搜索关键字",
    )
    parser.add_argument("--address-name", default=DEFAULT_ADDRESS_NAME, help="新增地址收货人名称")
    parser.add_argument("--address-phone", default=DEFAULT_ADDRESS_PHONE, help="新增地址手机号")
    parser.add_argument("--address-wechat", default=DEFAULT_ADDRESS_WECHAT, help="新增地址微信号")
    parser.add_argument(
        "--address-detail",
        default=DEFAULT_ADDRESS_DETAIL,
        help="新增地址详细门牌/补充地址；仅当页面存在对应字段时填写",
    )
    parser.add_argument(
        "--payment-method",
        choices=("cod", "wechat_mock"),
        default="cod",
        help="支付方式：cod 货到付款；wechat_mock 微信支付并使用支付成功测试钩子/模拟按钮",
    )
    parser.add_argument(
        "--submit-order",
        action="store_true",
        help="真正点击提交订单，并继续收银台/货到付款或模拟支付/订单状态/库存扣减/IM 断言",
    )
    parser.add_argument(
        "--allow-order-creation",
        action="store_true",
        help="显式授权本次运行创建真实订单",
    )
    parser.add_argument(
        "--max-payable",
        type=float,
        default=None,
        help="本次允许提交的最大实付金额；真实下单必须显式提供正数",
    )
    parser.add_argument(
        "--cancel-created-order",
        action="store_true",
        help="订单验证完成后取消本次创建且已解析订单号的订单",
    )
    parser.add_argument(
        "--allow-order-cancellation",
        action="store_true",
        help="显式授权取消本次创建的订单",
    )
    parser.add_argument(
        "--preorder-api-pattern",
        default=r"pre.?order|preOrder|createOrder|order/create|order/confirm|预订单",
        help="用于 logcat 匹配预订单接口调用的正则",
    )
    parser.add_argument(
        "--skip-api-log-assert",
        action="store_true",
        help="跳过预订单接口 logcat 断言；仍会尝试从页面/日志解析订单号",
    )
    parser.add_argument(
        "--mock-pay-success-url",
        default=None,
        help="支付成功测试钩子 URL，支持 {order_no}/{amount}/{sku}/{quantity} 占位",
    )
    parser.add_argument(
        "--stock-api-url",
        default=None,
        help="库存查询 URL，支持 {sku} 占位；返回 JSON 中需含 stock/inventory/availableStock",
    )
    parser.add_argument(
        "--order-status-api-url",
        default=None,
        help="订单状态查询 URL，支持 {order_no} 占位；返回 JSON 中需含 status/statusText/orderStatus",
    )
    parser.add_argument(
        "--skip-stock-assert",
        action="store_true",
        help="跳过库存扣减断言；无库存测试钩子时可用于 UI-only 冒烟",
    )
    parser.add_argument(
        "--skip-order-im",
        action="store_true",
        help="提交并支付后跳过订单详情页联系商家的 IM 消息",
    )
    parser.add_argument(
        "--send-order-im",
        action="store_true",
        help="订单验证后发送订单 IM；还需显式消息授权",
    )
    parser.add_argument(
        "--allow-order-message",
        action="store_true",
        help="显式授权本次运行发送订单消息",
    )
    parser.add_argument(
        "--im-message-template",
        default="{order_no} 申请取消测试订单，谢谢",
        help="订单后发送给商家的消息模板，支持 {order_no}",
    )
    parser.add_argument("--run-stockout", action="store_true", help="执行库存不足异常流")
    parser.add_argument("--stockout-keyword", default=None, help="库存不足商品关键字")
    parser.add_argument(
        "--stockout-spec",
        action="append",
        default=[],
        help="库存不足商品规格，可重复传入；不传则沿用 --spec",
    )
    parser.add_argument("--run-network-exception", action="store_true", help="执行网络异常提交异常流")
    parser.add_argument("--session", default="mall_order", help="DriverManager 会话名")
    parser.add_argument("--cold", action="store_true", help="冷启动 App")
    parser.add_argument(
        "--start-mode",
        choices=("cold", "activate", "off"),
        default=None,
        help="覆盖 START_MODE；默认 activate，除非指定 --cold",
    )
    parser.add_argument("--quit-driver", action="store_true", help="流程结束后关闭 Appium session")
    return parser


def validate_args(args) -> None:
    """Reject unsafe or contradictory mall capabilities before Driver creation."""
    address_mutation = any(
        (
            args.ensure_test_address,
            args.force_add_test_address,
            args.edit_test_address,
            args.copy_test_address,
            args.add_test_address_only,
        )
    )
    if args.verify_navigation_only:
        blocked = any(
            (
                args.submit_order,
                args.allow_cart_mutation,
                args.add_to_cart_only,
                address_mutation,
                args.run_cart_delete,
                args.run_stockout,
                args.run_network_exception,
                args.send_order_im,
                args.cancel_created_order,
            )
        )
        if blocked:
            raise ValueError(
                "--verify-navigation-only conflicts with mutating or "
                "exception-test options"
            )

    if address_mutation and not args.allow_address_mutation:
        raise ValueError(
            "address mutation requires explicit --allow-address-mutation"
        )

    cart_mutation = (
        args.flow in ("cart", "both")
        or args.add_to_cart_only
        or args.run_cart_delete
        or args.cart_delete_prepare_item
    )
    if cart_mutation and not args.allow_cart_mutation:
        raise ValueError(
            "cart mutation requires explicit --allow-cart-mutation"
        )
    if args.add_to_cart_only and args.submit_order:
        raise ValueError(
            "--add-to-cart-only conflicts with --submit-order"
        )

    if args.submit_order:
        if not args.allow_order_creation:
            raise ValueError(
                "order creation requires explicit --allow-order-creation"
            )
        if args.max_payable is None or args.max_payable <= 0:
            raise ValueError(
                "order creation requires positive --max-payable"
            )

    if args.cancel_created_order and not (
        args.submit_order and args.allow_order_cancellation
    ):
        raise ValueError(
            "order cancellation requires --submit-order and "
            "--allow-order-cancellation"
        )

    if args.send_order_im and not (
        args.submit_order and args.allow_order_message
    ):
        raise ValueError(
            "order message requires --submit-order and "
            "--allow-order-message"
        )
    if args.send_order_im and args.skip_order_im:
        raise ValueError(
            "--send-order-im conflicts with --skip-order-im"
        )


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        validate_args(args)
    except ValueError as exc:
        logger.error("商城下单参数安全校验失败: %s", exc)
        return 2
    specs = args.spec or ([] if args.product_source == "daily_baihuo" else ["黑色", "L"])
    expected_name_contains = (
        args.expected_name_contains
        if args.expected_name_contains is not None
        else ("" if args.product_source == "daily_baihuo" else args.keyword)
    )

    if args.cold:
        os.environ["START_MODE"] = "cold"
    elif args.start_mode is not None:
        os.environ["START_MODE"] = args.start_mode
    else:
        os.environ["START_MODE"] = "activate"

    if args.submit_order and args.payment_method == "wechat_mock" and not args.mock_pay_success_url:
        logger.warning("已选择 wechat_mock 但未传 --mock-pay-success-url；将尝试页面内「模拟支付成功」按钮")
    if args.submit_order and not args.stock_api_url and not args.skip_stock_assert:
        logger.warning("已传 --submit-order 但未传 --stock-api-url；支付后库存扣减断言可能失败")

    driver = DriverManager().get_driver(session_name=args.session)
    page = MallOrderFlow(
        driver,
        sku=args.sku,
        specs=specs,
        quantity=args.quantity,
        expected_name=args.expected_name,
        expected_name_contains=expected_name_contains,
        preorder_api_pattern=args.preorder_api_pattern,
        skip_api_log_assert=args.skip_api_log_assert,
        stock_api_url=args.stock_api_url,
        order_status_api_url=args.order_status_api_url,
        mock_pay_success_url=args.mock_pay_success_url,
        skip_stock_assert=args.skip_stock_assert,
        payment_method=args.payment_method,
        min_order_amount=args.min_order_amount,
        max_payable=args.max_payable,
        cancel_after_order=args.cancel_created_order,
        pick_preorder_time=not args.skip_preorder_time,
        send_im_after_order=args.send_order_im and not args.skip_order_im,
        im_message_template=args.im_message_template,
        coupon_policy=args.coupon_policy,
        pickup_code=args.pickup_code,
        notify_method=args.notify_method,
        remark_text=args.remark_text,
        rider_remark=args.rider_remark,
        merchant_remark=args.merchant_remark,
        ensure_test_address=args.ensure_test_address,
        force_add_test_address=args.force_add_test_address,
        edit_test_address=args.edit_test_address,
        copy_test_address=args.copy_test_address,
        address_query=args.address_query,
        address_name=args.address_name,
        address_phone=args.address_phone,
        address_wechat=args.address_wechat,
        address_detail=args.address_detail,
    )

    ok = False
    try:
        if args.verify_navigation_only:
            page.run_navigation_verification(args.keyword)
            ok = True
            return 0
        if args.add_to_cart_only:
            page.run_add_to_cart_only(args.keyword)
            ok = True
            return 0
        if args.add_test_address_only:
            page.ensure_test_address_from_my_page_flow(force_add=args.force_add_test_address)
            ok = True
            return 0
        if args.run_cart_delete:
            page.run_cart_delete_case(
                args.cart_delete_mode,
                prepare_keyword=args.keyword if args.cart_delete_prepare_item else None,
            )
            ok = True
            return 0
        if args.flow in ("buy_now", "both"):
            if args.product_source == "daily_baihuo":
                page.run_daily_baihuo_buy_now_flow(submit_order=args.submit_order)
            else:
                page.run_buy_now_flow(args.keyword, submit_order=args.submit_order)
            if args.flow == "both":
                page.safe_back_to_mall()
        if args.flow in ("cart", "both"):
            page.run_cart_flow(args.keyword, submit_order=args.submit_order)
            if args.run_stockout or args.run_network_exception:
                page.safe_back_to_mall()
        if args.run_stockout:
            if not args.stockout_keyword:
                raise AssertionError("--run-stockout 需要传 --stockout-keyword")
            page.run_stockout_case(args.stockout_keyword, args.stockout_spec or specs)
            page.safe_back_to_mall()
        if args.run_network_exception:
            page.run_network_exception_case(args.keyword)
        ok = True
    except AssertionError as ex:
        logger.error("商城下单脚本断言失败：%s", ex)
        ok = False
    finally:
        if args.quit_driver:
            try:
                DriverManager().close_driver(session_name=args.session)
            except Exception as ex:
                logger.warning("close_driver 失败: %s", ex)

    if ok:
        logger.info("商城下单脚本执行通过")
        return 0
    logger.error("商城下单脚本执行失败")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
