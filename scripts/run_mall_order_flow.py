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
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from appium.webdriver.common.appiumby import AppiumBy

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from commons.driver import DriverManager
from commons.diagnostics import capture_failure
from commons.logger import setup_logger
from flows.mall_order_types import (
    AmountSnapshot,
    ProductSnapshot,
    SubmitResult,
    nearly_equal,
    parse_money,
)
from pages.shop_business_page import ShopBusinessPage
from pages.shop_locators import (
    SHOP_ID_COUNT_ADD,
    SHOP_ID_COUNT_SUB,
    SHOP_ID_MALL_ADD_SHOP_CAR,
    SHOP_ID_MALL_BUY_NOW,
    SHOP_ID_MALL_SHOP_CAR_CONTAINER,
    SHOP_ID_MALL_CATEGORY_GOODS_NAME,
    SHOP_IM_INPUT_ID_SUFFIXES,
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
CASHIER_MARKERS: Tuple[str, ...] = (
    "收银台",
    "微信支付",
    "货到付款",
    "COD",
    "待支付",
    "立即支付",
    "去支付",
    "支付方式",
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
WAIT_SHIP_MARKERS: Tuple[str, ...] = (
    "待发货",
    "待配送",
    "待出库",
    "订单详情",
    "支付成功",
)
PREORDER_TIME_OPENERS: Tuple[str, ...] = (
    "预订时间",
    "预定时间",
    "预约时间",
    "配送时间",
    "送达时间",
    "选择时间",
    "指定时间",
    "立即配送",
    "立即送达",
)
IM_PAGE_MARKERS: Tuple[str, ...] = (
    "消息",
    "输入",
    "发送",
    "在线咨询",
    "客服",
    "联系商家",
)
MALL_COUPON_LABEL = "平台优惠券"
MERCHANT_COUPON_LABEL = "商家优惠券"
COUPON_SHEET_MARKERS: Tuple[str, ...] = (
    "选择优惠券",
    "可用优惠券",
    "不使用优惠券",
    "立即使用",
)
DEFAULT_RIDER_REMARK = "请把餐品放到大楼前台 Please place the meal at the reception desk"
DEFAULT_MERCHANT_REMARK = "如缺货，直接取消订单 Any product no stock, cancel order"
DEFAULT_REMARK_TEXT = "test order"
DEFAULT_ADDRESS_QUERY = os.environ.get("MALL_TEST_ADDRESS_QUERY", "").strip()
DEFAULT_ADDRESS_NAME = os.environ.get("MALL_TEST_ADDRESS_NAME", "").strip()
DEFAULT_ADDRESS_PHONE = os.environ.get("MALL_TEST_ADDRESS_PHONE", "").strip()
DEFAULT_ADDRESS_WECHAT = os.environ.get("MALL_TEST_ADDRESS_WECHAT", "").strip()
DEFAULT_ADDRESS_DETAIL = os.environ.get("MALL_TEST_ADDRESS_DETAIL", "").strip()
ADDRESS_LIST_MARKERS: Tuple[str, ...] = (
    "选择地址",
    "选择收货地址",
    "收货地址",
    "新增地址",
    "地址管理",
)
ADDRESS_EDIT_MARKERS: Tuple[str, ...] = (
    "新增收货地址",
    "编辑收货地址",
    "编辑地址",
    "地图地址",
    "地址详情",
    "联系人姓名",
    "联系人电话",
    "保存",
    "联系人",
    "收货人",
    "姓名",
    "手机号",
)
ADDRESS_SEARCH_MARKERS: Tuple[str, ...] = (
    "定位地址",
    "如有大厦",
    "街道名称",
    "请直接搜索",
    "搜索收货地址",
    "搜索地址",
    "搜索地点",
    "请输入地址",
    "选择地址",
)
ADDRESS_SEARCH_STRONG_MARKERS: Tuple[str, ...] = (
    "定位地址",
    "如有大厦",
    "街道名称",
    "请直接搜索",
    "搜索收货地址",
    "搜索地址",
    "搜索地点",
    "请输入地址",
    "搜索",
)
ADDRESS_MAP_ENTRY_LABELS: Tuple[str, ...] = (
    "地图地址",
    "请从地图上选择地址",
    "从地图上选择地址",
    "选择地图地址",
    "定位地址",
)
ADDRESS_CHECKOUT_ENTRY_LABELS: Tuple[str, ...] = (
    "请选择收货地址",
    "收货地址",
    "选择地址",
    "地址",
    "送货地址",
)
ADDRESS_ADD_LABELS: Tuple[str, ...] = (
    "新增地址",
    "添加地址",
    "新建地址",
    "新增收货地址",
    "+ 新增地址",
)


class MallOrderFlow(ShopBusinessPage):
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
        if not self.stock_api_url:
            return None
        data = self.call_json_url(self.stock_api_url, payload={"sku": self.sku}, method="GET")
        stock = self.find_first_json_value(data, ("stock", "inventory", "availableStock"))
        if stock is None:
            raise AssertionError(f"库存接口未返回 stock/inventory 字段：{data}")
        return int(stock)

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

    @staticmethod
    def tomorrow_date_fragments() -> Tuple[str, ...]:
        tomorrow = date.today() + timedelta(days=1)
        raw = (
            "明天",
            f"{tomorrow.month}月{tomorrow.day}日",
            f"{tomorrow.month}月{tomorrow.day}",
            f"{tomorrow.month:02d}月{tomorrow.day:02d}日",
            f"{tomorrow.month:02d}月{tomorrow.day:02d}",
            f"{tomorrow.month}-{tomorrow.day}",
            f"{tomorrow.month:02d}-{tomorrow.day:02d}",
        )
        return tuple(dict.fromkeys(raw))

    @staticmethod
    def looks_like_time_slot_label(label: str) -> bool:
        text = (label or "").strip()
        if not text or len(text) > 80:
            return False
        text = text.replace("：", ":").replace("至", "-").replace("—", "-")
        return bool(
            re.search(r"(?<!\d)\d{1,2}:\d{2}(?!\d)", text)
            or re.search(r"\d{1,2}\s*点", text)
        )

    def element_label(self, el) -> str:
        parts = []
        for attr in ("text", "content-desc"):
            try:
                val = (el.text if attr == "text" else el.get_attribute(attr)) or ""
            except Exception:
                val = ""
            val = val.strip()
            if val:
                parts.append(val)
        return " ".join(dict.fromkeys(parts)).strip()

    def open_preorder_time_sheet(self) -> bool:
        for _ in range(3):
            if self.click_labels(
                PREORDER_TIME_OPENERS,
                desc="预订/配送时间入口",
                y_min_ratio=0.12,
                y_max_ratio=0.95,
                exact=False,
            ):
                time.sleep(1.0)
                return True
            try:
                w, h = self._window_size()
                self.driver.swipe(int(w * 0.50), int(h * 0.30), int(w * 0.50), int(h * 0.74), 420)
            except Exception:
                pass
            time.sleep(0.35)
        return False

    def tap_tomorrow_in_time_sheet(self) -> bool:
        for frag in self.tomorrow_date_fragments():
            if self.click_labels(
                (frag,),
                desc=f"预订日期:{frag}",
                y_min_ratio=0.10,
                y_max_ratio=0.95,
                exact=False,
            ):
                time.sleep(0.7)
                return True
        return False

    def collect_time_slot_elements(self) -> List:
        slots = []
        seen = set()
        h = self._window_size()[1]
        queries = (
            '//*[contains(@text,":") or contains(@content-desc,":")]',
            '//android.widget.TextView',
            '//android.view.View',
            '//android.widget.Button',
        )
        for xp in queries:
            try:
                elements = self.driver.find_elements(AppiumBy.XPATH, xp)
            except Exception:
                continue
            for el in elements:
                try:
                    if not el.is_displayed():
                        continue
                    eid = id(el)
                    if eid in seen:
                        continue
                    cy = int(el.location.get("y", 0)) + int(el.size.get("height", 0)) // 2
                    if cy < int(h * 0.18) or cy > int(h * 0.94):
                        continue
                    label = self.element_label(el)
                    if not self.looks_like_time_slot_label(label):
                        continue
                    seen.add(eid)
                    slots.append(el)
                except Exception:
                    continue
        return slots

    def pick_random_time_slot(self) -> str:
        for attempt in range(8):
            slots = self.collect_time_slot_elements()
            if slots:
                pick = random.choice(slots)
                label = self.element_label(pick)
                if self._click_element_center(pick, f"随机预订时段:{label[:40]}"):
                    time.sleep(0.8)
                    self.click_labels(
                        ("确定", "完成", "确认"),
                        desc="预订时间确认",
                        y_min_ratio=0.45,
                        y_max_ratio=1.0,
                        exact=False,
                    )
                    logger.info("已选择明天随机预订时段：%s", label)
                    return label
            try:
                w, h = self._window_size()
                self.driver.swipe(int(w * 0.72), int(h * 0.58), int(w * 0.72), int(h * 0.24), 430)
            except Exception:
                pass
            logger.debug("未找到可点时段，继续滚动查找：%d/8", attempt + 1)
            time.sleep(0.4)
        raise AssertionError("未找到明天可选的预订时间段")

    def pick_tomorrow_random_preorder_time_if_needed(self) -> Optional[str]:
        if not self.pick_preorder_time:
            logger.info("已按参数跳过预订时间选择")
            return None
        if not self.open_preorder_time_sheet():
            raise AssertionError("订单确认页未找到预订/配送时间入口")
        if not self.tap_tomorrow_in_time_sheet():
            raise AssertionError("预订时间弹层未找到明天日期")
        selected = self.pick_random_time_slot()
        self.assert_page_contains_any(CHECKOUT_MARKERS, "选择预订时间后未回到订单确认页", timeout=8.0)
        return selected

    # ---------- 订单确认页与金额 ----------

    def first_money_after(
        self,
        labels: Sequence[str],
        *,
        default: Optional[float] = None,
        window: int = 8,
    ) -> Optional[float]:
        texts = self.page_texts()
        for i, tx in enumerate(texts):
            if not any(label in tx for label in labels):
                continue
            for candidate in texts[i : i + window]:
                val = parse_money(candidate)
                if val is not None:
                    return val
        return default

    def coupon_available_count(self, label: str = MALL_COUPON_LABEL) -> Optional[int]:
        for tx in self.page_texts():
            if label not in tx:
                continue
            m = re.search(r"(\d+)\s*张\s*可用", tx)
            if m:
                return int(m.group(1))
            if "无可用" in tx or "暂无可用" in tx or "0张可用" in tx:
                return 0
            if "可用" in tx:
                return None
        return None

    def first_money_between_labels(
        self,
        start_label: str,
        stop_labels: Sequence[str],
        *,
        default: float = 0.0,
        window: int = 8,
    ) -> float:
        texts = self.page_texts()
        skip_words = (
            "张可用",
            "可用",
            "不可用",
            "无可用",
            "暂无",
            "合计",
            "实付",
            "应付",
            "支付金额",
            "商品金额",
            "商品总价",
            "运费",
            "配送费",
        )
        for i, tx in enumerate(texts):
            if start_label not in tx:
                continue
            for candidate in texts[i + 1 : i + 1 + window]:
                if any(stop in candidate for stop in stop_labels):
                    return default
                if any(word in candidate for word in skip_words):
                    continue
                val = parse_money(candidate)
                if val is not None:
                    return abs(val)
            return default
        return default

    def read_platform_coupon_amount(self) -> float:
        amount = self.first_money_between_labels(
            MALL_COUPON_LABEL,
            (
                MERCHANT_COUPON_LABEL,
                "商品金额",
                "商品总价",
                "运费",
                "配送费",
                "合计",
                "实付",
                "应付",
                "支付金额",
                "确认支付",
                "提交订单",
            ),
            default=0.0,
            window=8,
        )
        logger.info("商城优惠券金额读取：仅计算%s=%.2f", MALL_COUPON_LABEL, amount)
        return amount

    def click_first_coupon_candidate(self) -> bool:
        h = self._window_size()[1]
        banned = ("不使用", "暂无", "不可用", "已失效", "已过期")
        xpaths = (
            '//*[contains(@text,"₱") or contains(@content-desc,"₱")]',
            '//*[contains(@text,"减") or contains(@content-desc,"减")]',
            '//*[contains(@text,"满") or contains(@content-desc,"满")]',
            '//*[contains(@text,"折") or contains(@content-desc,"折")]',
            '//*[contains(@text,"使用") or contains(@content-desc,"使用")]',
        )
        for xp in xpaths:
            try:
                elements = self.driver.find_elements(AppiumBy.XPATH, xp)
            except Exception:
                elements = []
            for el in elements:
                try:
                    if not el.is_displayed():
                        continue
                    label = self.element_label(el)
                    if any(word in label for word in banned):
                        continue
                    y = int(el.location.get("y", 0))
                    if y < int(h * 0.16) or y > int(h * 0.88):
                        continue
                    if self._click_element_center(el, "平台优惠券候选项"):
                        return True
                except Exception:
                    continue
        return self.tap_ratio(0.50, 0.32, "平台优惠券首项兜底")

    def apply_mall_platform_coupon_if_needed(self) -> bool:
        policy = self.coupon_policy
        if policy in ("skip", "none", "off"):
            logger.info("已按 --coupon-policy skip 跳过商城平台优惠券选择")
            return False
        count = self.coupon_available_count(MALL_COUPON_LABEL)
        if count == 0:
            if policy == "require":
                raise AssertionError("商城平台优惠券要求可用，但页面显示 0 张可用")
            logger.info("商城平台优惠券 0 张可用，跳过选择")
            return False
        if count is None:
            logger.info("未明确识别商城平台优惠券可用张数，尝试打开平台优惠券入口")
        else:
            logger.info("商城平台优惠券可用张数：%s", count)
        if not self.click_labels(
            (MALL_COUPON_LABEL,),
            desc="商城平台优惠券入口",
            y_min_ratio=0.18,
            y_max_ratio=0.88,
        ):
            if policy == "require":
                raise AssertionError("商城平台优惠券要求选择，但未找到平台优惠券入口")
            logger.warning("未找到商城平台优惠券入口，跳过选择")
            return False
        if not self.wait_page_contains_any(COUPON_SHEET_MARKERS, timeout=5.0):
            logger.warning("点击平台优惠券后未识别优惠券弹层，继续返回确认页判断")
            return False
        if not self.click_first_coupon_candidate():
            if policy == "require":
                raise AssertionError("平台优惠券弹层未选中任何可用券")
            logger.warning("平台优惠券弹层未找到可用券，尝试返回确认页")
            self.tap_top_back()
            return False
        self.click_labels(
            ("确定", "完成", "确认", "使用", "立即使用"),
            desc="平台优惠券确认",
            y_min_ratio=0.42,
            y_max_ratio=1.0,
        )
        self.assert_page_contains_any(CHECKOUT_MARKERS, "选择平台优惠券后未回到订单确认页", timeout=8.0)
        logger.info("商城平台优惠券处理完成")
        return True

    def find_checkout_anchor(self, labels: Sequence[str], *, y_min_ratio: float = 0.0, y_max_ratio: float = 1.0):
        h = self._window_size()[1]
        y_min, y_max = int(h * y_min_ratio), int(h * y_max_ratio)
        for raw in labels:
            label = self._clean_xpath_text(raw)
            if not label:
                continue
            xp = f'//*[contains(@text,"{label}") or contains(@content-desc,"{label}")]'
            try:
                elements = self.driver.find_elements(AppiumBy.XPATH, xp)
            except Exception:
                elements = []
            for el in elements:
                try:
                    if not el.is_displayed():
                        continue
                    y = int(el.location.get("y", 0))
                    if y_min <= y <= y_max:
                        return el
                except Exception:
                    continue
        return None

    def scroll_checkout_until_visible(self, labels: Sequence[str], *, max_rounds: int = 5) -> bool:
        for idx in range(max_rounds):
            if self.find_checkout_anchor(labels, y_min_ratio=0.08, y_max_ratio=0.92):
                return True
            self.scroll_vertical(0.76, 0.34)
            logger.debug("订单确认页查找%s：%d/%d", "/".join(labels), idx + 1, max_rounds)
        return self.find_checkout_anchor(labels, y_min_ratio=0.08, y_max_ratio=0.92) is not None

    def checkout_anchor_y_ratio(self, labels: Sequence[str], default: float = 0.55) -> float:
        el = self.find_checkout_anchor(labels, y_min_ratio=0.06, y_max_ratio=0.94)
        if not el:
            return default
        try:
            loc = el.location
            size = el.size
            _, h = self._window_size()
            return (int(loc.get("y", 0)) + int(size.get("height", 0)) // 2) / max(h, 1)
        except Exception:
            return default

    def set_pickup_code_if_needed(self) -> bool:
        policy = self.pickup_code
        if policy in ("keep", "skip", "none", "off_default"):
            logger.info("商城取件码保持当前状态")
            return True
        if policy not in ("on", "off"):
            raise AssertionError(f"不支持的取件码策略：{self.pickup_code}")
        if not self.scroll_checkout_until_visible(("取件码",), max_rounds=5):
            logger.warning("商城确认页未找到取件码区域，跳过")
            return True
        target = "开启" if policy == "on" else "关闭"
        row_y = self.checkout_anchor_y_ratio(("取件码",), default=0.56)
        if self.click_labels(
            (target,),
            desc=f"商城取件码{target}",
            y_min_ratio=max(0.08, row_y - 0.08),
            y_max_ratio=min(0.94, row_y + 0.08),
            exact=False,
        ):
            logger.info("商城取件码已切换为：%s", target)
            return True
        x_ratio = 0.88 if policy == "on" else 0.70
        if self.tap_ratio(x_ratio, row_y, f"商城取件码{target}兜底"):
            logger.info("商城取件码已尝试切换为：%s", target)
            return True
        raise AssertionError(f"商城取件码未能切换为：{target}")

    def set_notify_method_if_needed(self) -> bool:
        method = self.notify_method
        if method in ("keep", "skip", "none"):
            logger.info("商城通知方式保持当前状态")
            return True
        if method not in ("app", "phone"):
            raise AssertionError(f"不支持的通知方式：{self.notify_method}")
        if not self.scroll_checkout_until_visible(("通知方式",), max_rounds=6):
            logger.warning("商城确认页未找到通知方式区域，跳过")
            return True
        labels = ("APP联系", "APP联络", "APP通知", "APP") if method == "app" else (
            "电话联系",
            "电话",
            "手机联系",
        )
        row_y = self.checkout_anchor_y_ratio(("通知方式",), default=0.78)
        if self.click_labels(
            labels,
            desc="商城通知方式",
            y_min_ratio=max(0.08, row_y - 0.08),
            y_max_ratio=min(0.94, row_y + 0.08),
            exact=False,
        ):
            logger.info("商城通知方式已切换为：%s", method)
            return True
        x_ratio = 0.56 if method == "app" else 0.84
        if self.tap_ratio(x_ratio, row_y, f"商城通知方式{method}兜底"):
            logger.info("商城通知方式已尝试切换为：%s", method)
            return True
        raise AssertionError(f"商城通知方式未能切换为：{method}")

    def fill_remark_if_needed(self) -> bool:
        if not (self.remark_text or self.rider_remark or self.merchant_remark):
            logger.info("商城备注为空且未配置骑手/商家快捷备注，跳过")
            return True
        if not self.scroll_checkout_until_visible(("备注信息", "备注", "留言"), max_rounds=7):
            logger.warning("商城确认页未找到备注入口，跳过")
            return True
        if not self.click_labels(
            ("备注信息", "备注", "留言"),
            desc="商城备注入口",
            y_min_ratio=0.10,
            y_max_ratio=0.94,
        ):
            row_y = self.checkout_anchor_y_ratio(("备注信息", "备注", "留言"), default=0.84)
            self.tap_ratio(0.72, row_y, "商城备注入口兜底")
        if not self.wait_page_contains_any(("添加备注", "备注", "留言", "完成"), timeout=6.0):
            logger.warning("点击备注入口后未识别备注页，继续尝试输入")
        if self.remark_text:
            typed = False
            for el in self.visible_edit_texts(y_min_ratio=0.10, y_max_ratio=0.92):
                if self.type_text_element(el, self.remark_text, "商城备注文本"):
                    typed = True
                    break
            if not typed and not self._type_into_best_edit_text(self.remark_text, allow_open_search=False):
                raise AssertionError("商城备注页未找到输入框")
        self.select_remark_quick_notes()
        try:
            self.driver.hide_keyboard()
        except Exception:
            pass
        if not self.click_labels(
            ("完成", "保存", "确定", "确认"),
            desc="商城备注完成",
            y_min_ratio=0.02,
            y_max_ratio=1.0,
        ):
            self.tap_top_back()
        self.assert_page_contains_any(CHECKOUT_MARKERS, "填写商城备注后未回到订单确认页", timeout=8.0)
        logger.info(
            "商城备注已处理：remark=%s rider=%s merchant=%s",
            self.remark_text,
            self.rider_remark,
            self.merchant_remark,
        )
        return True

    def select_remark_quick_notes(self) -> None:
        def short_label(text: str) -> str:
            return (text or "").split(" Please ")[0].split(" Any ")[0].strip()

        if self.rider_remark:
            labels = tuple(dict.fromkeys((self.rider_remark, short_label(self.rider_remark))))
            if self.click_labels(
                labels,
                desc="商城对骑手快捷备注",
                y_min_ratio=0.16,
                y_max_ratio=0.78,
            ):
                logger.info("已选择商城对骑手备注：%s", self.rider_remark)
            else:
                logger.warning("未选中商城对骑手快捷备注：%s", self.rider_remark)
        if self.merchant_remark:
            labels = tuple(dict.fromkeys((self.merchant_remark, short_label(self.merchant_remark))))
            clicked = False
            for attempt in range(4):
                clicked = self.click_labels(
                    labels,
                    desc="商城对商家快捷备注",
                    y_min_ratio=0.18,
                    y_max_ratio=0.92,
                )
                if clicked:
                    break
                self.scroll_vertical(0.76, 0.36)
                logger.debug("查找商城商家快捷备注：%d/4", attempt + 1)
            if clicked:
                logger.info("已选择商城对商家备注：%s", self.merchant_remark)
            else:
                logger.warning("未选中商城对商家快捷备注：%s", self.merchant_remark)

    def apply_checkout_preferences(self) -> None:
        self.set_pickup_code_if_needed()
        self.set_notify_method_if_needed()
        self.fill_remark_if_needed()

    def read_amounts(self, product: ProductSnapshot) -> AmountSnapshot:
        goods_total = self.first_money_after(
            ("商品金额", "商品总价", "商品合计", "小计"),
            default=product.unit_price * product.quantity,
            window=5,
        )
        coupon = self.read_platform_coupon_amount()
        freight = self.first_money_after(("运费", "配送费", "物流费"), default=0.0, window=3)
        payable = self.first_money_after(("实付", "应付", "支付金额", "合计"), default=None)
        if goods_total is None:
            raise AssertionError("确认订单页未解析到商品总价")
        if payable is None:
            raise AssertionError("确认订单页未解析到实付/应付金额")
        coupon_abs = abs(coupon or 0.0)
        freight_abs = abs(freight or 0.0)
        amounts = AmountSnapshot(
            goods_total=abs(goods_total),
            coupon=coupon_abs,
            freight=freight_abs,
            payable=abs(payable),
        )
        expected = amounts.goods_total - amounts.coupon + amounts.freight
        if not nearly_equal(amounts.payable, expected):
            raise AssertionError(
                "金额校验失败：实付 %.2f != 商品总价 %.2f - 优惠 %.2f + 运费 %.2f = %.2f"
                % (
                    amounts.payable,
                    amounts.goods_total,
                    amounts.coupon,
                    amounts.freight,
                    expected,
                )
            )
        logger.info(
            "金额校验通过：实付 %.2f = 商品总价 %.2f - 优惠 %.2f + 运费 %.2f",
            amounts.payable,
            amounts.goods_total,
            amounts.coupon,
            amounts.freight,
        )
        return amounts

    def assert_checkout_matches_detail(self, product: ProductSnapshot) -> AmountSnapshot:
        self.assert_page_contains_any(CHECKOUT_MARKERS, "未跳转到订单确认页", timeout=10.0)
        blob = self.page_blob()
        if product.name and product.name not in blob:
            raise AssertionError(f"确认订单页商品名称不一致：未找到 {product.name}")
        for spec in product.specs:
            if spec not in blob:
                raise AssertionError(f"确认订单页规格不一致：未找到 {spec}")
        detail_price = product.unit_price
        if not any(
            (parse_money(tx) is not None and nearly_equal(abs(parse_money(tx) or 0.0), detail_price))
            for tx in self.page_texts()
        ):
            raise AssertionError(f"确认订单页未找到详情页单价：{detail_price:.2f}")
        logger.info("确认订单页商品信息校验通过：名称/规格/单价与详情页一致")
        return self.read_amounts(product)

    # ---------- 预订单、收银台、支付 ----------

    def drain_logcat(self) -> None:
        try:
            self.driver.get_log("logcat")
        except Exception as ex:
            logger.debug("logcat 预清理失败：%s", ex)

    def read_logcat_blob(self) -> str:
        try:
            entries = self.driver.get_log("logcat")
        except Exception as ex:
            if self.skip_api_log_assert:
                logger.warning("当前 Appium 不支持读取 logcat，已按 --skip-api-log-assert 跳过：%s", ex)
                return ""
            raise AssertionError(f"无法读取 logcat，不能断言预订单接口调用：{ex}") from ex
        lines = []
        for item in entries:
            msg = str(item.get("message", ""))
            if msg:
                lines.append(msg)
        return "\n".join(lines)

    @staticmethod
    def extract_order_no(blob: str) -> Optional[str]:
        patterns = (
            r"(?:预订单号|预订单|订单号)\s*[:：=]?\s*([A-Za-z0-9_-]{6,})",
            r"(?:preOrderNo|pre_order_no|orderNo|order_no|orderId|order_id)"
            r'["\s:=]+([A-Za-z0-9_-]{6,})',
        )
        for pat in patterns:
            m = re.search(pat, blob, flags=re.I)
            if m:
                return m.group(1)
        return None

    def assert_preorder_api_called(self, log_blob: str) -> None:
        if self.skip_api_log_assert:
            logger.info("已跳过预订单接口 logcat 断言")
            return
        if not self.preorder_api_pattern:
            logger.info("未配置 --preorder-api-pattern，跳过接口名匹配，仅断言预订单号")
            return
        if not re.search(self.preorder_api_pattern, log_blob, flags=re.I):
            raise AssertionError(
                "未在 logcat 中匹配到预订单接口；可通过 --preorder-api-pattern 配置接口关键字，"
                "或在黑盒环境临时加 --skip-api-log-assert"
            )
        logger.info("预订单接口调用断言通过：pattern=%s", self.preorder_api_pattern)

    def submit_order(self, amounts: AmountSnapshot) -> SubmitResult:
        self.drain_logcat()
        for _ in range(2):
            if not self.click_labels(
                ("提交订单", "确认订单"),
                desc="提交订单",
                y_min_ratio=0.52,
                y_max_ratio=1.0,
            ):
                raise AssertionError("未找到「提交订单」按钮")
            time.sleep(1.5)
            if not self.select_default_address_if_popup_visible():
                break
        if self.wait_page_contains_any(STOCKOUT_MARKERS, timeout=2.0):
            raise AssertionError("正常下单路径出现库存不足提示")
        if self.wait_page_contains_any(NETWORK_ERROR_MARKERS, timeout=1.0):
            raise AssertionError("正常下单路径出现网络异常提示")
        self.assert_page_contains_any(CASHIER_MARKERS, "提交订单后未进入收银台/支付页", timeout=12.0)

        log_blob = self.read_logcat_blob()
        self.assert_preorder_api_called(log_blob)
        order_no = self.extract_order_no(log_blob) or self.extract_order_no(self.page_blob())
        if not order_no:
            raise AssertionError("未从预订单接口日志或页面解析到预订单号/订单号")

        cashier_amount = self.first_money_after(
            ("实付", "应付", "支付金额", "合计"),
            default=None,
        )
        if cashier_amount is None:
            raise AssertionError("收银台未解析到支付金额")
        cashier_amount = abs(cashier_amount)
        if not nearly_equal(cashier_amount, amounts.payable):
            raise AssertionError(
                "收银台金额不正确：%.2f != 确认页实付 %.2f"
                % (cashier_amount, amounts.payable)
            )
        logger.info("提交订单校验通过：order_no=%s cashier_amount=%.2f", order_no, cashier_amount)
        return SubmitResult(order_no=order_no, cashier_amount=cashier_amount)

    def select_wechat_pay(self) -> None:
        if not self.click_labels(
            ("微信支付", "微信"),
            desc="微信支付",
            y_min_ratio=0.15,
            y_max_ratio=0.95,
        ):
            raise AssertionError("收银台未找到微信支付选项")
        self.click_labels(
            ("确认支付", "立即支付", "去支付", "支付"),
            desc="发起支付",
            y_min_ratio=0.52,
            y_max_ratio=1.0,
        )
        logger.info("已选择微信支付并尝试发起支付")

    def select_cash_on_delivery_pay(self) -> None:
        if self.wait_page_contains_any(WAIT_SHIP_MARKERS, timeout=1.0):
            logger.info("提交后已进入订单结果页，视为货到付款已生效")
            return
        if not self.click_labels(
            ("货到付款", "到付", "现金支付", "COD", "Cash on Delivery"),
            desc="货到付款",
            y_min_ratio=0.12,
            y_max_ratio=0.95,
        ):
            self.click_labels(
                ("支付方式", "选择支付方式", "付款方式"),
                desc="打开支付方式",
                y_min_ratio=0.12,
                y_max_ratio=0.95,
            )
            if not self.click_labels(
                ("货到付款", "到付", "现金支付", "COD", "Cash on Delivery"),
                desc="货到付款",
                y_min_ratio=0.12,
                y_max_ratio=0.95,
            ):
                raise AssertionError("收银台未找到货到付款选项")
        self.click_labels(
            ("确认支付", "立即支付", "提交订单", "确认", "完成"),
            desc="确认货到付款",
            y_min_ratio=0.45,
            y_max_ratio=1.0,
        )
        logger.info("已选择货到付款并提交支付确认")

    def call_json_url(
        self,
        url_template: str,
        *,
        payload: Optional[Dict[str, Any]] = None,
        method: str = "POST",
    ) -> Any:
        values = {
            "sku": self.sku,
            "order_no": (payload or {}).get("order_no", ""),
            "amount": (payload or {}).get("amount", ""),
            "quantity": self.quantity,
        }
        url = url_template.format(**values)
        body = None
        headers = {"Accept": "application/json"}
        if method.upper() != "GET":
            body = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=body, headers=headers, method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as ex:
            raise AssertionError(f"调用测试钩子失败：{url} -> {ex}") from ex
        if not raw.strip():
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw": raw}

    @staticmethod
    def find_first_json_value(data: Any, keys: Sequence[str]) -> Optional[Any]:
        if isinstance(data, dict):
            for key in keys:
                if key in data:
                    return data[key]
            for value in data.values():
                got = MallOrderFlow.find_first_json_value(value, keys)
                if got is not None:
                    return got
        elif isinstance(data, list):
            for value in data:
                got = MallOrderFlow.find_first_json_value(value, keys)
                if got is not None:
                    return got
        return None

    def mock_payment_success(self, submit: SubmitResult) -> None:
        if self.mock_pay_success_url:
            data = self.call_json_url(
                self.mock_pay_success_url,
                payload={"order_no": submit.order_no, "amount": submit.cashier_amount},
                method="POST",
            )
            logger.info("支付成功测试钩子返回：%s", data)
            try:
                app_pkg = self.driver.current_package
                if app_pkg:
                    self.driver.activate_app(app_pkg)
            except Exception:
                pass
            time.sleep(2.0)
            return
        if self.click_labels(
            ("模拟支付成功", "支付成功", "完成支付", "已支付"),
            desc="支付成功模拟按钮",
            y_min_ratio=0.15,
            y_max_ratio=1.0,
        ):
            time.sleep(2.0)
            return
        raise AssertionError("未配置 --mock-pay-success-url，且页面未找到支付成功模拟按钮")

    def assert_order_wait_ship(self, order_no: str) -> None:
        status = None
        if self.order_status_api_url:
            data = self.call_json_url(
                self.order_status_api_url,
                payload={"order_no": order_no},
                method="GET",
            )
            status = self.find_first_json_value(data, ("statusText", "status", "orderStatus"))
        if status is not None:
            status_text = str(status)
            status_low = status_text.lower()
            ok_status = (
                "待发货" in status_text
                or "待配送" in status_text
                or "待出库" in status_text
                or "wait_ship" in status_low
                or "wait_deliver" in status_low
                or "to_ship" in status_low
            )
            if not ok_status:
                raise AssertionError(f"订单状态不是待发货：{status}")
            logger.info("订单状态接口校验通过：%s", status)
            return
        self.assert_page_contains_any(WAIT_SHIP_MARKERS, "页面未出现待发货/支付成功/订单详情", timeout=15.0)
        blob = self.page_blob()
        if not any(mark in blob for mark in ("待发货", "待配送", "待出库", "支付成功")):
            logger.warning("页面未直接出现「待发货」，但已出现订单详情/支付成功标识")
        logger.info("订单状态页面校验通过")

    def assert_stock_decremented(self, product: ProductSnapshot) -> None:
        if self.skip_stock_assert:
            logger.info("已按 --skip-stock-assert 跳过库存扣减断言")
            return
        if not self.stock_api_url:
            if product.stock_before is None:
                raise AssertionError("未配置 --stock-api-url，且页面未解析到下单前库存，无法断言库存扣减")
            raise AssertionError("库存扣减需要下单后库存来源，请配置 --stock-api-url 或加 --skip-stock-assert")
        before = product.stock_before
        if before is None:
            raise AssertionError("库存接口未返回下单前库存，无法断言库存扣减")
        after = self.read_stock_by_api()
        expected = before - product.quantity
        if after != expected:
            raise AssertionError(f"库存扣减失败：before={before}, after={after}, expected={expected}")
        logger.info("库存扣减校验通过：%s -> %s", before, after)

    def pay_and_assert(self, submit: SubmitResult, product: ProductSnapshot) -> None:
        if self.payment_method in ("cod", "cash_on_delivery", "货到付款"):
            self.select_cash_on_delivery_pay()
        elif self.payment_method in ("wechat", "wechat_mock", "微信"):
            self.select_wechat_pay()
            self.mock_payment_success(submit)
        else:
            raise AssertionError(f"不支持的支付方式：{self.payment_method}")
        self.assert_order_wait_ship(submit.order_no)
        self.assert_stock_decremented(product)

    # ---------- 订单详情 IM ----------

    def ensure_order_detail_page(self) -> None:
        if self.wait_page_contains_any(("订单详情", "订单编号", "订单号", "待发货"), timeout=2.0):
            return
        self.click_labels(
            ("查看订单", "订单详情", "查看详情", "完成"),
            desc="进入订单详情",
            y_min_ratio=0.20,
            y_max_ratio=1.0,
        )
        self.assert_page_contains_any(
            ("订单详情", "订单编号", "订单号", "待发货"),
            "未进入订单详情页，无法联系商家发送取消测试订单消息",
            timeout=10.0,
        )

    def order_no_from_detail_or_submit(self, submit: SubmitResult) -> str:
        self.ensure_order_detail_page()
        detail_order_no = self.extract_order_no(self.page_blob())
        order_no = detail_order_no or submit.order_no
        if not order_no:
            raise AssertionError("订单详情页未解析到订单号")
        if self.click_labels(
            ("复制", "复制订单号"),
            desc="复制订单号",
            y_min_ratio=0.05,
            y_max_ratio=0.95,
        ):
            logger.info("已点击订单详情页复制订单号控件")
        else:
            logger.warning("订单详情页未找到复制订单号控件，使用已解析订单号继续发送 IM")
        return order_no

    def open_im_from_order_detail(self) -> None:
        self.ensure_order_detail_page()
        if not self.click_labels(
            ("联系商家", "联系卖家", "联系客服", "客服", "商家"),
            desc="订单详情联系商家",
            y_min_ratio=0.12,
            y_max_ratio=1.0,
        ):
            raise AssertionError("订单详情页未找到「联系商家」入口")
        self.assert_page_contains_any(IM_PAGE_MARKERS, "点击联系商家后未进入 IM/客服页面", timeout=10.0)

    def find_im_input(self):
        for suffix in SHOP_IM_INPUT_ID_SUFFIXES:
            el = self._first_displayed_by_pkg_id(suffix)
            if el:
                return el
        try:
            edits = self.driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.EditText")
        except Exception:
            edits = []
        visible = []
        for el in edits:
            try:
                if el.is_displayed():
                    visible.append((int(el.location.get("y", 0)), el))
            except Exception:
                continue
        visible.sort(key=lambda item: -item[0])
        return visible[0][1] if visible else None

    def paste_and_send_im_message(self, message: str) -> None:
        target = self.find_im_input()
        if not target:
            self.click_labels(
                ("输入", "说点什么", "请输入"),
                desc="IM 输入框",
                y_min_ratio=0.45,
                y_max_ratio=1.0,
            )
            target = self.find_im_input()
        if not target:
            raise AssertionError("IM 页面未找到输入框")
        try:
            target.click()
            time.sleep(0.2)
            self.driver.set_clipboard_text(message)
            self.driver.press_keycode(279)  # Android KEYCODE_PASTE
            logger.info("已通过剪贴板粘贴 IM 消息")
        except Exception as ex:
            logger.warning("剪贴板粘贴失败，改用 send_keys：%s", ex)
            target.click()
            target.send_keys(message)
        try:
            self.driver.hide_keyboard()
        except Exception:
            pass
        if not self.click_labels(
            ("发送",),
            desc="IM 发送",
            y_min_ratio=0.45,
            y_max_ratio=1.0,
            exact=True,
        ):
            try:
                self.driver.press_keycode(66)
                logger.info("IM 发送：键盘回车兜底")
            except Exception as ex:
                raise AssertionError(f"IM 页面未找到发送按钮：{ex}") from ex
        time.sleep(1.0)

    def send_order_cancel_im_if_needed(self, submit: SubmitResult) -> None:
        if not self.send_im_after_order:
            logger.info("已按参数跳过订单后 IM 消息")
            return
        order_no = self.order_no_from_detail_or_submit(submit)
        message = self.im_message_template.format(order_no=order_no)
        self.open_im_from_order_detail()
        self.paste_and_send_im_message(message)
        logger.info("已发送订单取消测试 IM：%s", message)

    # ---------- 新增/选择测试地址 ----------

    def visible_edit_texts(
        self,
        *,
        y_min_ratio: float = 0.0,
        y_max_ratio: float = 1.0,
    ) -> List:
        h = self._window_size()[1]
        y_min, y_max = int(h * y_min_ratio), int(h * y_max_ratio)
        try:
            edits = self.driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.EditText")
        except Exception:
            edits = []
        visible = []
        for el in edits:
            try:
                if not el.is_displayed():
                    continue
                y = int(el.location.get("y", 0))
                if not (y_min <= y <= y_max):
                    continue
                x = int(el.location.get("x", 0))
                visible.append((y, x, el))
            except Exception:
                continue
        visible.sort(key=lambda item: (item[0], item[1]))
        return [item[2] for item in visible]

    def edit_text_value(self, el) -> str:
        values = []
        for attr in ("text", "content-desc", "hint"):
            try:
                val = el.text if attr == "text" else el.get_attribute(attr)
            except Exception:
                val = ""
            val = (val or "").strip()
            if val:
                values.append(val)
        return " ".join(dict.fromkeys(values)).strip()

    def type_text_element(self, el, text: str, desc: str) -> bool:
        try:
            el.click()
            time.sleep(0.15)
            try:
                el.clear()
            except Exception:
                pass
            el.send_keys(text)
            logger.info("已输入%s：%s", desc, text)
            return True
        except Exception as send_ex:
            try:
                el.click()
                time.sleep(0.15)
                try:
                    el.clear()
                except Exception:
                    pass
                self.driver.set_clipboard_text(text)
                self.driver.press_keycode(279)  # Android KEYCODE_PASTE
                logger.info("已通过剪贴板输入%s：%s", desc, text)
                return True
            except Exception:
                logger.debug("输入%s失败：%s", desc, send_ex)
                return False

    def tap_ratio(self, x_ratio: float, y_ratio: float, desc: str) -> bool:
        try:
            w, h = self._window_size()
            x, y = int(w * x_ratio), int(h * y_ratio)
            self.driver.execute_script("mobile: clickGesture", {"x": x, "y": y})
            logger.info("已点击%s（坐标 %d,%d）", desc, x, y)
            time.sleep(0.65)
            return True
        except Exception as ex:
            logger.debug("坐标点击%s失败：%s", desc, ex)
            return False

    def scroll_vertical(self, start_ratio: float, end_ratio: float, *, x_ratio: float = 0.50) -> None:
        try:
            w, h = self._window_size()
            self.driver.swipe(
                int(w * x_ratio),
                int(h * start_ratio),
                int(w * x_ratio),
                int(h * end_ratio),
                430,
            )
            time.sleep(0.45)
        except Exception:
            pass

    def type_into_field_near_label(
        self,
        labels: Sequence[str],
        text: str,
        desc: str,
    ) -> bool:
        for raw in labels:
            label = self._clean_xpath_text(raw)
            if not label:
                continue
            xpaths = (
                f'//*[contains(@text,"{label}")]/following::android.widget.EditText[1]',
                f'//*[contains(@content-desc,"{label}")]/following::android.widget.EditText[1]',
                f'//android.widget.EditText[contains(@text,"{label}") or '
                f'contains(@content-desc,"{label}") or contains(@hint,"{label}")]',
            )
            for xp in xpaths:
                try:
                    elements = self.driver.find_elements(AppiumBy.XPATH, xp)
                except Exception:
                    elements = []
                for el in elements:
                    try:
                        if not el.is_displayed():
                            continue
                    except Exception:
                        continue
                    if self.type_text_element(el, text, desc):
                        return True
        return False

    def target_address_labels(self) -> Tuple[str, ...]:
        first_line = self.address_query.split(",")[0].strip()
        labels = (
            self.address_phone,
            self.address_query,
            first_line,
            "Syquia",
            "Santa Ana",
            "Maynila",
            "Manila",
        )
        return tuple(dict.fromkeys(label for label in labels if label))

    def page_has_target_address(self) -> bool:
        blob = self.page_blob()
        return any(label in blob for label in self.target_address_labels())

    def is_address_search_page(self) -> bool:
        blob = self.page_blob()
        if "定位地址" in blob and any(
            marker in blob for marker in ("如有大厦", "街道名称", "请直接搜索")
        ):
            return True
        if not any(marker in blob for marker in ADDRESS_SEARCH_STRONG_MARKERS):
            return False
        return bool(self.visible_edit_texts(y_min_ratio=0.0, y_max_ratio=0.42))

    def wait_address_search_page(self, timeout: float = 6.0) -> bool:
        end = time.time() + timeout
        while time.time() < end:
            if self.is_address_search_page():
                return True
            time.sleep(0.35)
        return False

    def is_address_edit_form(self) -> bool:
        blob = self.page_blob()
        strong = (
            "新增收货地址",
            "编辑收货地址",
            "地图地址",
            "地址详情",
            "联系人姓名",
            "联系人电话",
        )
        return any(marker in blob for marker in strong) and "保存" in blob

    def wait_address_edit_form(self, timeout: float = 6.0) -> bool:
        end = time.time() + timeout
        while time.time() < end:
            if self.is_address_edit_form():
                return True
            time.sleep(0.35)
        return False

    def click_bottom_my_tab(self) -> bool:
        h = self._window_size()[1]
        candidates = []
        for xp in ('//*[@text="我的"]', '//*[@content-desc="我的"]'):
            try:
                elements = self.driver.find_elements(AppiumBy.XPATH, xp)
            except Exception:
                elements = []
            for el in elements:
                try:
                    if not el.is_displayed():
                        continue
                    y = int(el.location.get("y", 0))
                    if y < int(h * 0.55):
                        continue
                    candidates.append((y, el))
                except Exception:
                    continue
        candidates.sort(key=lambda item: item[0], reverse=True)
        for _, el in candidates:
            if self._click_element_center(el, "底部我的 Tab"):
                time.sleep(1.2)
                return True
        return self.tap_ratio(0.88, 0.95, "底部我的 Tab 兜底")

    def open_address_manage_from_my_page(self) -> None:
        if not self.click_bottom_my_tab():
            raise AssertionError("未点击到底部「我的」Tab，无法从我的页面新增地址")
        for attempt in range(5):
            if self.click_labels(
                ("我的地址", "收货地址", "地址管理", "管理地址"),
                desc="我的地址入口",
                y_min_ratio=0.10,
                y_max_ratio=0.95,
            ):
                if self.wait_page_contains_any(ADDRESS_LIST_MARKERS + ADDRESS_EDIT_MARKERS, timeout=8.0):
                    logger.info("已进入我的地址/地址管理页")
                    return
            self.scroll_vertical(0.75, 0.34)
            logger.debug("我的页查找地址入口：%d/5", attempt + 1)
        raise AssertionError("我的页面未找到「我的地址/收货地址/地址管理」入口")

    def open_address_sheet_from_checkout(self) -> None:
        self.assert_page_contains_any(CHECKOUT_MARKERS, "当前不在订单确认页，无法点击收货地址", timeout=8.0)
        for attempt in range(4):
            if self.click_labels(
                ADDRESS_CHECKOUT_ENTRY_LABELS,
                desc="订单确认页地址入口",
                y_min_ratio=0.08,
                y_max_ratio=0.62,
            ):
                if self.wait_page_contains_any(ADDRESS_LIST_MARKERS + ADDRESS_EDIT_MARKERS, timeout=6.0):
                    logger.info("已从订单确认页打开地址弹窗/地址页")
                    return
            if attempt == 1:
                self.tap_ratio(0.50, 0.20, "订单确认页地址行兜底")
                if self.wait_page_contains_any(ADDRESS_LIST_MARKERS + ADDRESS_EDIT_MARKERS, timeout=5.0):
                    logger.info("已从订单确认页打开地址弹窗/地址页")
                    return
            self.scroll_vertical(0.30, 0.76)
        raise AssertionError("订单确认页未能打开收货地址弹窗/地址列表")

    def select_existing_target_address(self, *, expect_checkout: bool) -> bool:
        if not self.page_has_target_address():
            return False
        for label in self.target_address_labels():
            if self.click_labels(
                (label,),
                desc="选择已有测试地址",
                y_min_ratio=0.12,
                y_max_ratio=0.92,
            ):
                time.sleep(1.0)
                self.click_labels(
                    ("确定", "确认", "完成"),
                    desc="确认选择已有测试地址",
                    y_min_ratio=0.45,
                    y_max_ratio=1.0,
                )
                if expect_checkout:
                    if self.wait_page_contains_any(CHECKOUT_MARKERS, timeout=6.0):
                        logger.info("已选择已有测试地址并回到确认订单页")
                        return True
                else:
                    logger.info("已命中已有测试地址")
                    return True
        return False

    def find_target_address_anchor(self):
        h = self._window_size()[1]
        y_min, y_max = int(h * 0.12), int(h * 0.90)
        for raw in self.target_address_labels():
            label = self._clean_xpath_text(raw)
            if not label:
                continue
            xp = f'//*[contains(@text,"{label}") or contains(@content-desc,"{label}")]'
            try:
                elements = self.driver.find_elements(AppiumBy.XPATH, xp)
            except Exception:
                elements = []
            for el in elements:
                try:
                    if not el.is_displayed():
                        continue
                    y = int(el.location.get("y", 0))
                    if not (y_min <= y <= y_max):
                        continue
                    return el
                except Exception:
                    continue
        return None

    def address_anchor_row_y_ratio(self, anchor) -> float:
        try:
            loc = anchor.location
            size = anchor.size
            _, h = self._window_size()
            return (int(loc.get("y", 0)) + int(size.get("height", 0)) // 2) / max(h, 1)
        except Exception:
            return 0.42

    def open_target_address_edit_form(self) -> bool:
        anchor = self.find_target_address_anchor()
        if not anchor:
            logger.warning("当前地址列表/弹窗未找到目标地址，无法进入编辑")
            return False
        row_y_ratio = self.address_anchor_row_y_ratio(anchor)

        for x_ratio in (0.84, 0.88, 0.78):
            if self.tap_ratio(x_ratio, row_y_ratio, "目标地址右侧编辑按钮"):
                if self.wait_address_edit_form(timeout=7.0):
                    logger.info("已进入编辑收货地址页")
                    return True
        if self.click_labels(
            ("编辑", "修改"),
            desc="地址编辑按钮",
            y_min_ratio=max(0.10, row_y_ratio - 0.08),
            y_max_ratio=min(0.95, row_y_ratio + 0.08),
        ):
            if self.wait_address_edit_form(timeout=7.0):
                logger.info("已进入编辑收货地址页")
                return True
        logger.warning("已尝试点击目标地址编辑按钮，但未进入编辑收货地址页")
        return False

    def copy_target_address_in_current_parent(self, *, expect_checkout: bool) -> bool:
        anchor = self.find_target_address_anchor()
        if not anchor:
            logger.warning("当前地址列表/弹窗未找到目标地址，无法复制")
            return False
        row_y_ratio = self.address_anchor_row_y_ratio(anchor)
        x_candidates = (0.94, 0.92, 0.90) if expect_checkout else (0.66, 0.69, 0.72)
        for x_ratio in x_candidates:
            if not self.tap_ratio(x_ratio, row_y_ratio, "目标地址复制按钮"):
                continue
            time.sleep(0.8)
            self.click_labels(
                ("确认复制", "复制", "确定", "确认"),
                desc="复制地址确认",
                y_min_ratio=0.25,
                y_max_ratio=1.0,
            )
            if self.wait_address_search_page(timeout=2.0):
                self.search_and_select_address_location()
                self.fill_test_address_form()
                self.save_test_address_form()
                return self.finish_address_copy_parent(expect_checkout=expect_checkout)
            if self.wait_address_edit_form(timeout=3.0):
                if "请从地图上选择地址" in self.page_blob():
                    self.search_and_select_address_location()
                self.fill_test_address_form()
                self.save_test_address_form()
                return self.finish_address_copy_parent(expect_checkout=expect_checkout)
            if self.wait_page_contains_any(ADDRESS_LIST_MARKERS + CHECKOUT_MARKERS, timeout=3.0):
                return self.finish_address_copy_parent(expect_checkout=expect_checkout)
        logger.warning("已尝试点击目标地址复制按钮，但未识别到复制后的页面状态")
        return False

    def finish_address_copy_parent(self, *, expect_checkout: bool) -> bool:
        if expect_checkout:
            if self.wait_page_contains_any(CHECKOUT_MARKERS, timeout=3.0):
                logger.info("复制地址后已回到订单确认页")
                return True
            if self.select_existing_target_address(expect_checkout=True):
                logger.info("复制地址后已选择地址并回到订单确认页")
                return True
            self.tap_top_back()
            ok = self.wait_page_contains_any(CHECKOUT_MARKERS, timeout=5.0)
            if ok:
                logger.info("复制地址后通过返回回到订单确认页")
            return ok
        if self.wait_page_contains_any(ADDRESS_LIST_MARKERS, timeout=5.0):
            logger.info("复制地址后停留/返回地址管理页")
            return True
        return True

    def edit_test_address_in_current_parent(self, *, expect_checkout: bool) -> bool:
        if not self.open_target_address_edit_form():
            return False
        self.search_and_select_address_location()
        self.fill_test_address_form()
        self.save_test_address_form()
        if expect_checkout:
            if self.wait_page_contains_any(CHECKOUT_MARKERS, timeout=3.0):
                return True
            if self.select_existing_target_address(expect_checkout=True):
                return True
            self.tap_top_back()
            return self.wait_page_contains_any(CHECKOUT_MARKERS, timeout=5.0)
        return True

    def open_add_address_form(self) -> None:
        if self.wait_address_edit_form(timeout=1.0) or self.wait_address_search_page(timeout=1.0):
            return
        for attempt in range(4):
            if self.click_labels(
                ADDRESS_ADD_LABELS,
                desc="新增地址按钮",
                y_min_ratio=0.06,
                y_max_ratio=0.98,
            ):
                if self.wait_address_edit_form(timeout=8.0) or self.wait_address_search_page(timeout=2.0):
                    logger.info("已进入新增收货地址/定位地址页")
                    return
            if attempt == 1:
                self.tap_ratio(0.50, 0.92, "新增地址底部按钮兜底")
                if self.wait_address_edit_form(timeout=6.0) or self.wait_address_search_page(timeout=2.0):
                    logger.info("已进入新增收货地址/定位地址页")
                    return
            if attempt == 2:
                self.tap_ratio(0.92, 0.08, "新增地址右上角按钮兜底")
                if self.wait_address_edit_form(timeout=6.0) or self.wait_address_search_page(timeout=2.0):
                    logger.info("已进入新增收货地址/定位地址页")
                    return
            self.scroll_vertical(0.75, 0.34)
        raise AssertionError("地址列表/弹窗中未找到「新增地址」按钮")

    def open_address_search_from_edit(self) -> None:
        if self.wait_address_search_page(timeout=1.0):
            return
        self.assert_page_contains_any(ADDRESS_EDIT_MARKERS, "当前不在新增/编辑收货地址页，无法唤起地图", timeout=6.0)
        opener_groups = (
            ADDRESS_MAP_ENTRY_LABELS,
            ("请选择地址", "选择地址", "所在地址", "所在地区"),
        )
        for labels in opener_groups:
            if self.click_labels(
                labels,
                desc="新增/编辑页地图地址入口",
                y_min_ratio=0.08,
                y_max_ratio=0.38,
            ):
                if self.wait_address_search_page(timeout=6.0):
                    logger.info("已进入定位地址地图页")
                    return
        for y_ratio in (0.34, 0.28, 0.40):
            self.tap_ratio(0.55, y_ratio, "新增/编辑页地图地址入口兜底")
            if self.wait_address_search_page(timeout=5.0):
                logger.info("已进入定位地址地图页")
                return
        raise AssertionError("新增/编辑收货地址页未打开定位地址地图页")

    def type_into_address_map_search(self) -> bool:
        if self._type_into_best_edit_text(self.address_query, allow_open_search=False):
            return True
        if self.click_labels(
            ("如有大厦", "街道名称", "请直接搜索", "搜索"),
            desc="定位地址搜索框",
            y_min_ratio=0.05,
            y_max_ratio=0.22,
        ):
            if self._type_into_best_edit_text(self.address_query, allow_open_search=False):
                return True
        self.tap_ratio(0.45, 0.13, "定位地址搜索框兜底")
        return self._type_into_best_edit_text(self.address_query, allow_open_search=False)

    def search_and_select_address_location(self) -> None:
        self.open_address_search_from_edit()
        if not self.type_into_address_map_search():
            raise AssertionError("定位地址地图页未找到可输入的搜索框")
        self._press_enter_or_search()
        try:
            self.driver.hide_keyboard()
        except Exception:
            pass
        result_labels = (
            self.address_query,
            self.address_query.split(",")[0].strip(),
            "Syquia",
            "Santa Ana",
            "Maynila",
            "Manila",
            "2515",
        )
        if not self.wait_page_contains_any(result_labels, timeout=8.0):
            logger.warning("地址搜索结果未明确出现目标文案，尝试点击首条结果")
        clicked = False
        for y_min in (0.20, 0.12):
            if self.click_labels(
                result_labels,
                desc="地址搜索结果",
                y_min_ratio=y_min,
                y_max_ratio=0.92,
            ):
                clicked = True
                break
        if not clicked:
            for y_ratio in (0.30, 0.58, 0.66):
                if self.tap_ratio(0.50, y_ratio, "定位地址搜索结果兜底"):
                    clicked = True
                    break
        if not clicked:
            raise AssertionError("地址搜索页未选中目标地址结果")
        time.sleep(1.0)
        self.click_labels(
            ("使用该地址", "选择该地址", "确认地址", "确定", "完成"),
            desc="确认地址搜索结果",
            y_min_ratio=0.42,
            y_max_ratio=1.0,
        )
        if not self.wait_address_edit_form(timeout=8.0):
            if self.wait_page_contains_any(ADDRESS_SEARCH_MARKERS, timeout=1.0):
                self.tap_top_back()
                time.sleep(0.8)
        if not self.wait_address_edit_form(timeout=6.0):
            raise AssertionError("地图地址选中后未回到新增/编辑收货地址页")
        logger.info("已搜索并选中地址：%s", self.address_query)

    def fill_test_address_form(self) -> None:
        if not self.wait_address_edit_form(timeout=8.0):
            raise AssertionError("当前不在新增/编辑收货地址页，无法填写地址表单")
        detail_ok = False
        name_ok = False
        phone_ok = False
        wechat_ok = False
        for attempt in range(3):
            if not detail_ok and self.address_detail:
                detail_ok = self.type_into_field_near_label(
                    ("地址详情", "详细地址", "门牌号", "楼层", "房间号", "补充地址"),
                    self.address_detail,
                    "详细地址",
                )
            if not name_ok:
                name_ok = self.type_into_field_near_label(
                    ("联系人姓名", "姓名", "收货人", "联系人", "名称"),
                    self.address_name,
                    "收货人姓名",
                )
            if not phone_ok:
                phone_ok = self.type_into_field_near_label(
                    ("联系人电话", "手机号", "手机号码", "联系电话", "电话"),
                    self.address_phone,
                    "手机号",
                )
            if not wechat_ok:
                wechat_ok = self.type_into_field_near_label(
                    ("微信号", "微信", "Wechat", "WeChat"),
                    self.address_wechat,
                    "微信号",
                )
            if name_ok and phone_ok and wechat_ok:
                break
            self.scroll_vertical(0.72, 0.36)
            logger.debug("地址表单按标签填写未完成，继续滚动查找：%d/3", attempt + 1)

        fallback_values = []
        if not name_ok:
            fallback_values.append((self.address_name, "收货人姓名"))
        if not phone_ok:
            fallback_values.append((self.address_phone, "手机号"))
        if not wechat_ok:
            fallback_values.append((self.address_wechat, "微信号"))
        used = set()
        for text, desc in fallback_values:
            typed = False
            for el in self.visible_edit_texts(y_min_ratio=0.12, y_max_ratio=0.92):
                key = id(el)
                if key in used:
                    continue
                current = self.edit_text_value(el)
                if text in current or self.address_query in current:
                    continue
                if self.type_text_element(el, text, f"{desc}(顺序兜底)"):
                    used.add(key)
                    typed = True
                    break
            if desc == "收货人姓名":
                name_ok = name_ok or typed
            elif desc == "手机号":
                phone_ok = phone_ok or typed
            elif desc == "微信号":
                wechat_ok = wechat_ok or typed

        if not (name_ok and phone_ok and wechat_ok):
            raise AssertionError(
                "地址编辑页未完成必填信息："
                f"name={name_ok}, phone={phone_ok}, wechat={wechat_ok}"
            )
        logger.info(
            "地址表单填写完成：name=%s phone=%s wechat=%s",
            self.address_name,
            self.address_phone,
            self.address_wechat,
        )

    def save_test_address_form(self) -> None:
        try:
            self.driver.hide_keyboard()
        except Exception:
            pass
        if not self.click_labels(
            ("保存", "完成", "确定", "提交"),
            desc="保存地址",
            y_min_ratio=0.42,
            y_max_ratio=1.0,
        ):
            if not self.tap_ratio(0.50, 0.92, "保存地址按钮兜底"):
                raise AssertionError("地址编辑页未找到保存/完成按钮")
        deadline = time.time() + 10.0
        while time.time() < deadline:
            blob = self.page_blob()
            if (
                any(marker in blob for marker in CHECKOUT_MARKERS + ADDRESS_LIST_MARKERS)
                and ("保存" not in blob or self.page_has_target_address())
            ):
                logger.info("地址保存后已返回上级页面")
                return
            time.sleep(0.4)
        logger.warning("地址保存后未明确返回上级页，继续由后续页面断言判断")

    def add_test_address(self) -> None:
        self.open_add_address_form()
        self.search_and_select_address_location()
        self.fill_test_address_form()
        self.save_test_address_form()

    def ensure_test_address_from_checkout_flow(self, *, force_add: bool = False) -> None:
        logger.info("开始在订单确认页处理测试收货地址")
        self.open_address_sheet_from_checkout()
        if self.copy_test_address and self.page_has_target_address():
            if self.copy_target_address_in_current_parent(expect_checkout=True):
                logger.info("订单确认页测试地址复制完成")
                return
            logger.warning("目标地址复制未完成，继续按编辑/新增/选择地址流程处理")
        if self.edit_test_address and self.page_has_target_address():
            if self.edit_test_address_in_current_parent(expect_checkout=True):
                logger.info("订单确认页测试地址编辑完成")
                return
            logger.warning("目标地址编辑未完成，继续按新增/选择地址流程处理")
        if not force_add and self.select_existing_target_address(expect_checkout=True):
            return
        self.add_test_address()
        if not self.wait_page_contains_any(CHECKOUT_MARKERS, timeout=5.0):
            blob = self.page_blob()
            if "保存" not in blob and self.select_existing_target_address(expect_checkout=True):
                return
            self.tap_top_back()
        self.assert_page_contains_any(CHECKOUT_MARKERS, "新增地址后未回到订单确认页", timeout=8.0)
        logger.info("订单确认页测试地址处理完成")

    def ensure_test_address_from_my_page_flow(self, *, force_add: bool = False) -> bool:
        logger.info("开始从我的页面处理测试收货地址")
        self.open_address_manage_from_my_page()
        if self.copy_test_address and self.page_has_target_address():
            if self.copy_target_address_in_current_parent(expect_checkout=False):
                logger.info("我的页面测试地址复制完成")
                return True
            logger.warning("目标地址复制未完成，继续按编辑/新增/选择地址流程处理")
        if self.edit_test_address and self.page_has_target_address():
            if self.edit_test_address_in_current_parent(expect_checkout=False):
                logger.info("我的页面测试地址编辑完成")
                return True
            logger.warning("目标地址编辑未完成，继续按新增/选择地址流程处理")
        if not force_add and self.select_existing_target_address(expect_checkout=False):
            return True
        self.add_test_address()
        if not self.wait_page_contains_any(ADDRESS_LIST_MARKERS, timeout=5.0):
            logger.warning("新增地址后未明确回到地址列表，当前页面将由日志辅助确认")
        if not self.page_has_target_address():
            logger.warning("地址列表未直接识别到目标地址，可能需要在真机确认保存结果")
        logger.info("我的页面测试地址处理完成")
        return True

    # ---------- 正常流 ----------

    def cart_page_visible(self) -> bool:
        blob = self.page_blob()
        return "购物车" in blob and any(
            marker in blob for marker in ("管理", "完成", "去结算", "结算", "全选", "删除")
        )

    def cart_manage_mode_visible(self) -> bool:
        blob = self.page_blob()
        return "购物车" in blob and "完成" in blob and "删除" in blob

    def open_cart_page(self) -> None:
        if self.cart_page_visible():
            return
        opened = False
        detail_cart = self._first_displayed_by_pkg_id(SHOP_ID_MALL_SHOP_CAR_CONTAINER)
        if detail_cart:
            opened = self._click_element_center(detail_cart, "详情页购物车入口")
        if not opened:
            self.ensure_mall_tab()
            opened = self.tap_floating_or_entry_cart()
        if not opened:
            raise AssertionError("未能打开购物车")
        self.assert_page_contains_any(("购物车", "管理", "去结算", "结算"), "未进入购物车页", timeout=8.0)

    def ensure_cart_normal_mode(self) -> None:
        if self.cart_manage_mode_visible():
            if not self.click_labels(
                ("完成",),
                desc="退出购物车管理模式",
                y_min_ratio=0.0,
                y_max_ratio=0.18,
                exact=True,
            ):
                self.tap_ratio(0.93, 0.09, "退出购物车管理模式坐标")
            self.assert_page_contains_any(("管理", "去结算", "结算"), "购物车未退出管理模式", timeout=5.0)

    def enter_cart_manage_mode(self) -> None:
        self.open_cart_page()
        if self.cart_manage_mode_visible():
            return
        if not self.click_labels(
            ("管理",),
            desc="进入购物车管理模式",
            y_min_ratio=0.0,
            y_max_ratio=0.20,
            exact=True,
        ):
            if not self.tap_ratio(0.93, 0.09, "进入购物车管理模式坐标"):
                raise AssertionError("购物车页未找到「管理」按钮")
        self.assert_page_contains_any(("完成", "删除", "全选"), "进入购物车管理模式失败", timeout=6.0)

    def cart_select_all_items(self) -> None:
        if not self.click_labels(
            ("全选",),
            desc="购物车全选",
            y_min_ratio=0.68,
            y_max_ratio=1.0,
            exact=False,
        ):
            if not self.tap_ratio(0.10, 0.92, "购物车全选坐标"):
                raise AssertionError("购物车管理模式未找到「全选」")
        time.sleep(0.5)

    def cart_select_first_item(self) -> None:
        for y_ratio in (0.38, 0.46, 0.54, 0.62):
            if self.tap_ratio(0.08, y_ratio, "购物车部分选择首个商品"):
                time.sleep(0.35)
                return
        raise AssertionError("购物车管理模式未能选择首个商品")

    def cart_confirm_delete_popup(self, *, required: bool = True) -> bool:
        markers = ("是否要删除", "删除已选", "确认删除", "确定删除")
        if not self.wait_page_contains_any(markers, timeout=3.0):
            if required:
                raise AssertionError("点击删除后未出现二次确认弹窗")
            return False
        if not self.click_labels(
            ("删除", "确定", "确认"),
            desc="二次确认删除",
            y_min_ratio=0.42,
            y_max_ratio=0.72,
            exact=True,
        ):
            if not self.tap_ratio(0.70, 0.59, "二次确认删除坐标"):
                raise AssertionError("删除二次确认弹窗未找到确认按钮")
        time.sleep(1.0)
        if self.wait_page_contains_any(markers, timeout=1.0):
            raise AssertionError("点击二次确认删除后弹窗未关闭")
        logger.info("购物车删除二次确认弹窗处理完成")
        return True

    def cart_assert_delete_without_selection_toast(self) -> None:
        self.enter_cart_manage_mode()
        if not self.click_labels(
            ("删除",),
            desc="购物车未选商品删除",
            y_min_ratio=0.68,
            y_max_ratio=1.0,
            exact=True,
        ):
            if not self.tap_ratio(0.82, 0.92, "购物车未选商品删除坐标"):
                raise AssertionError("购物车管理模式未找到底部「删除」按钮")
        if self.wait_page_contains_any(("还没有选择任何商品", "没有选择任何商品", "请选择商品"), timeout=4.0):
            logger.info("购物车未选商品删除提示断言通过")
            return
        if self.wait_page_contains_any(("是否要删除", "删除已选"), timeout=0.8):
            self.click_labels(("取消",), desc="未选删除误触弹窗取消", y_min_ratio=0.42, y_max_ratio=0.72, exact=True)
        raise AssertionError("未选择商品点击删除后未出现「还没有选择任何商品」提示")

    def cart_delete_by_manage(self, *, all_items: bool) -> None:
        self.enter_cart_manage_mode()
        if all_items:
            self.cart_select_all_items()
        else:
            self.cart_select_first_item()
        if not self.click_labels(
            ("删除",),
            desc="购物车管理删除",
            y_min_ratio=0.68,
            y_max_ratio=1.0,
            exact=True,
        ):
            if not self.tap_ratio(0.82, 0.92, "购物车管理删除坐标"):
                raise AssertionError("购物车管理模式未找到底部「删除」按钮")
        self.cart_confirm_delete_popup(required=True)
        self.assert_page_contains_any(("购物车", "管理", "完成", "去结算", "结算"), "删除后未停留在购物车页", timeout=6.0)
        logger.info("购物车管理模式%s删除流程通过", "全选" if all_items else "部分选择")

    def cart_delete_by_minus(self) -> None:
        self.open_cart_page()
        self.ensure_cart_normal_mode()
        clicked = False
        for idx in range(5):
            if not self.click_first_by_id_in_band(
                SHOP_ID_COUNT_SUB,
                f"购物车商品数量减号{idx + 1}",
                x_min_ratio=0.48,
                x_max_ratio=0.92,
                y_min_ratio=0.24,
                y_max_ratio=0.78,
            ):
                if idx == 0:
                    clicked = self.tap_ratio(0.78, 0.47, "购物车商品数量减号坐标")
                else:
                    clicked = False
            else:
                clicked = True
            if not clicked:
                break
            if self.cart_confirm_delete_popup(required=False):
                self.assert_page_contains_any(("购物车", "管理", "去结算", "结算"), "减号删除后未停留在购物车页", timeout=6.0)
                logger.info("购物车减号删除流程通过")
                return
            time.sleep(0.4)
        raise AssertionError("点击购物车数量减号后未触发删除确认；请确认当前商品数量可减到 0")

    def cart_swipe_left_first_item(self) -> None:
        self.open_cart_page()
        self.ensure_cart_normal_mode()
        w, h = self._window_size()
        for y_ratio in (0.42, 0.50, 0.58):
            try:
                self.driver.swipe(
                    int(w * 0.86),
                    int(h * y_ratio),
                    int(w * 0.34),
                    int(h * y_ratio),
                    520,
                )
                logger.info("已左滑购物车商品行 y=%.2f", y_ratio)
                time.sleep(0.7)
                if self.wait_page_contains_any(("找相似", "收藏", "删除"), timeout=1.2):
                    return
            except Exception:
                continue
        raise AssertionError("购物车商品左滑后未出现「删除/收藏/找相似」菜单")

    def cart_delete_by_swipe(self) -> None:
        self.cart_swipe_left_first_item()
        if not self.click_first_by_id_in_band(
            "tv_delete",
            "购物车左滑删除",
            x_min_ratio=0.58,
            x_max_ratio=1.0,
            y_min_ratio=0.20,
            y_max_ratio=0.78,
        ):
            if not self.click_labels(
                ("删除",),
                desc="购物车左滑删除",
                y_min_ratio=0.20,
                y_max_ratio=0.78,
                exact=True,
            ):
                if not self.tap_ratio(0.93, 0.42, "购物车左滑删除坐标"):
                    raise AssertionError("购物车左滑菜单未找到「删除」")
        self.cart_confirm_delete_popup(required=True)
        self.assert_page_contains_any(("购物车", "管理", "去结算", "结算"), "左滑删除后未停留在购物车页", timeout=6.0)
        logger.info("购物车左滑删除流程通过")

    def prepare_cart_delete_item(self, keyword: str) -> None:
        logger.info("准备购物车删除测试商品：%s", keyword)
        product = self.open_detail_and_snapshot(keyword)
        if not self.click_by_id_or_label(
            SHOP_ID_MALL_ADD_SHOP_CAR,
            ("加入购物车", "加购"),
            desc="删除用例-加入购物车",
            y_min_ratio=0.52,
            y_max_ratio=1.0,
        ):
            raise AssertionError("商品详情页未找到「加入购物车」")
        time.sleep(0.8)
        self.select_specs_and_quantity()
        if self.wait_page_contains_any(STOCKOUT_MARKERS, timeout=2.0):
            raise AssertionError("删除用例准备商品时提示库存不足")
        self.open_cart_page()
        blob = self.page_blob()
        if product.name and product.name not in blob:
            logger.warning("准备删除商品后购物车未直接出现商品名：%s", product.name)

    def run_cart_delete_case(self, mode: str, *, prepare_keyword: Optional[str] = None) -> bool:
        if prepare_keyword:
            self.prepare_cart_delete_item(prepare_keyword)
        else:
            self.open_cart_page()
        if mode == "manage_all":
            self.cart_delete_by_manage(all_items=True)
        elif mode == "manage_partial":
            self.cart_delete_by_manage(all_items=False)
        elif mode == "manage_none":
            self.cart_assert_delete_without_selection_toast()
        elif mode == "minus":
            self.cart_delete_by_minus()
        elif mode == "swipe":
            self.cart_delete_by_swipe()
        else:
            raise AssertionError(f"未知购物车删除模式：{mode}")
        return True

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
        product = self.open_detail_and_snapshot(keyword)
        if not product.name:
            raise AssertionError("商品详情未读取到商品名称")
        capture_failure(self.driver, "mall_navigation_verification")
        self.safe_back_to_mall()
        return True

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

    def add_cart_to_checkout_exact_specs(self, product: ProductSnapshot) -> ProductSnapshot:
        if not self.click_by_id_or_label(
            SHOP_ID_MALL_ADD_SHOP_CAR,
            ("加入购物车", "加购"),
            desc="加入购物车",
            y_min_ratio=0.52,
            y_max_ratio=1.0,
        ):
            raise AssertionError("商品详情页未找到「加入购物车」")
        time.sleep(0.8)
        if self._login_like_screen_visible():
            raise AssertionError("加入购物车后进入登录页，前置条件不满足：用户未登录")
        sheet_stock = self.select_specs_and_quantity()
        if product.stock_before is None and sheet_stock is not None:
            product.stock_before = sheet_stock
        if self.wait_page_contains_any(STOCKOUT_MARKERS, timeout=2.0):
            raise AssertionError("库存充足商品加入购物车时提示库存不足")
        detail_cart = self._first_displayed_by_pkg_id(SHOP_ID_MALL_SHOP_CAR_CONTAINER)
        opened_cart = False
        if detail_cart:
            opened_cart = self._click_element_center(detail_cart, "详情页购物车入口")
        if not opened_cart and not self.tap_floating_or_entry_cart():
            raise AssertionError("未能打开购物车")
        self.assert_page_contains_any(("购物车", "结算", "去结算"), "未进入购物车页", timeout=8.0)
        blob = self.page_blob()
        if product.name and product.name not in blob:
            logger.warning("购物车页未直接出现商品名：%s，继续尝试结算", product.name)
        self.click_labels(("全选", "选择"), desc="购物车勾选", y_min_ratio=0.30, y_max_ratio=1.0)
        if not self.click_labels(
            ("去结算", "结算", "提交订单"),
            desc="购物车结算",
            y_min_ratio=0.52,
            y_max_ratio=1.0,
        ):
            raise AssertionError("购物车页未找到「去结算/结算」按钮")
        self.assert_page_contains_any(CHECKOUT_MARKERS, "购物车结算后未跳转至订单确认页", timeout=10.0)
        logger.info("购物车路径：已跳转至订单确认页")
        return product

    def finish_checkout(
        self,
        product: ProductSnapshot,
        *,
        submit_order: bool,
    ) -> None:
        self.dismiss_checkout_upsell_if_visible()
        amounts = self.assert_checkout_matches_detail(product)
        if self.ensure_test_address:
            self.ensure_test_address_from_checkout_flow(force_add=self.force_add_test_address)
            amounts = self.assert_checkout_matches_detail(product)
        if self.apply_mall_platform_coupon_if_needed():
            amounts = self.assert_checkout_matches_detail(product)
        self.apply_checkout_preferences()
        amounts = self.read_amounts(product)
        selected_slot = self.pick_tomorrow_random_preorder_time_if_needed()
        if selected_slot:
            amounts = self.read_amounts(product)
        if not submit_order:
            logger.info("未传 --submit-order：停在确认订单页，跳过真实提交/支付/库存扣减")
            return
        if self.max_payable is None or self.max_payable <= 0:
            raise AssertionError("真实提交缺少正数 --max-payable")
        if amounts.payable > self.max_payable:
            raise AssertionError(
                "确认页实付 %.2f 超过 --max-payable %.2f"
                % (amounts.payable, self.max_payable)
            )
        submit = self.submit_order(amounts)
        self.pay_and_assert(submit, product)
        self.send_order_cancel_im_if_needed(submit)

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

    def run_cart_flow(self, keyword: str, *, submit_order: bool) -> bool:
        logger.info("开始购物车提交订单路径")
        product = self.open_detail_and_snapshot(keyword)
        product = self.add_cart_to_checkout_exact_specs(product)
        self.finish_checkout(product, submit_order=submit_order)
        logger.info("购物车提交订单路径通过")
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
