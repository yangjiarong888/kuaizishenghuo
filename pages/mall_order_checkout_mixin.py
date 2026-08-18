"""Guarded mall checkout side effects."""

from __future__ import annotations

import math
import random
import re
import time
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

from appium.webdriver.common.appiumby import AppiumBy

from commons.logger import setup_logger
from flows.mall_order_http import MallOrderHttpError, find_first_json_value
from flows.mall_order_types import AmountSnapshot, ProductSnapshot, SubmitResult
from flows.mall_order_types import nearly_equal, parse_money
from pages.shop_locators import SHOP_IM_INPUT_ID_SUFFIXES


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

class MallOrderCheckoutMixin:
    """Checkout boundary with amount and explicit side-effect guards."""

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

    @staticmethod
    def extract_order_identities(blob: str) -> List[str]:
        patterns = (
            r"(?:预订单号|预订单|订单编号|订单号)\s*[:：=]?\s*"
            r"([A-Za-z0-9_-]{6,})",
            r"(?:preOrderNo|pre_order_no|orderNo|order_no|orderId|order_id)"
            r'["\s:=]+([A-Za-z0-9_-]{6,})',
        )
        identities = []
        for pattern in patterns:
            for match in re.finditer(pattern, blob, flags=re.I):
                identity = match.group(1).strip()
                if identity:
                    identities.append(identity)
        return identities

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
        try:
            return self.http.call_json_url(
                url_template,
                payload=payload,
                method=method,
            )
        except MallOrderHttpError as exc:
            raise AssertionError(str(exc)) from exc

    @staticmethod
    def find_first_json_value(data: Any, keys: Sequence[str]) -> Optional[Any]:
        return find_first_json_value(data, keys)

    def mock_payment_success(self, submit: SubmitResult) -> None:
        if self.mock_pay_success_url:
            try:
                data = self.http.mock_payment_success(
                    submit.order_no,
                    submit.cashier_amount,
                )
            except MallOrderHttpError as exc:
                raise AssertionError(str(exc)) from exc
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
        if self.order_status_api_url:
            try:
                self.http.assert_order_wait_ship(order_no)
            except MallOrderHttpError as exc:
                raise AssertionError(str(exc)) from exc
            logger.info("订单状态接口校验通过")
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

    def assert_order_detail_rounding_change(
        self,
        submit: SubmitResult,
        expected_change: float,
    ) -> None:
        self.ensure_order_detail_page()
        detail_order_nos = self.extract_order_identities(self.page_blob())
        normalized_order_nos = {
            order_no.casefold() for order_no in detail_order_nos
        }
        submitted_order_no = str(submit.order_no or "").strip().casefold()
        if not normalized_order_nos:
            raise AssertionError("订单详情页未解析到本次订单号，无法校验取整找零")
        if (
            len(normalized_order_nos) != 1
            or not submitted_order_no
            or submitted_order_no not in normalized_order_nos
        ):
            raise AssertionError(
                "订单详情订单号冲突或与本次提交不一致：%s != %s"
                % (detail_order_nos, submit.order_no)
            )

        texts = self.page_texts()
        change_values = []
        conflicting_markers = (
            "应付",
            "实付",
            "支付金额",
            "合计",
            "总计",
            "总额",
            "商品金额",
            "运费",
            "优惠",
        )
        for text in texts:
            if not any(marker in text for marker in ("找零", "找回", "存入余额")):
                continue
            if any(marker in text for marker in conflicting_markers):
                continue
            value = parse_money(text)
            if value is not None and value not in change_values:
                change_values.append(value)
        expected = round(float(expected_change), 2)
        if len(change_values) != 1 or round(change_values[0], 2) != expected:
            raise AssertionError(
                "订单详情取整找零不正确：expected %.2f, actual %s"
                % (expected, change_values or "未解析")
            )
        logger.info(
            "本次订单详情取整找零校验通过：order_no=%s change=%.2f",
            submit.order_no,
            expected,
        )

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

    def assert_within_payable_limit(
        self,
        amounts: AmountSnapshot,
    ) -> None:
        try:
            max_payable = float(self.max_payable)
        except (TypeError, ValueError):
            max_payable = float("nan")
        if not math.isfinite(max_payable) or max_payable <= 0:
            raise AssertionError("真实提交缺少有限正数 --max-payable")
        if amounts.payable > max_payable:
            raise AssertionError(
                "确认页实付 %.2f 超过 --max-payable %.2f"
                % (amounts.payable, max_payable)
            )

    def finish_checkout(
        self,
        product: ProductSnapshot,
        *,
        submit_order: bool,
    ) -> None:
        self.dismiss_checkout_upsell_if_visible()
        amounts = self.assert_checkout_matches_detail(product)
        if self.ensure_test_address:
            self.ensure_test_address_from_checkout_flow(
                force_add=self.force_add_test_address
            )
            amounts = self.assert_checkout_matches_detail(product)
        if self.apply_mall_platform_coupon_if_needed():
            amounts = self.assert_checkout_matches_detail(product)
        self.apply_checkout_preferences()
        amounts = self.read_amounts(product)
        selected_slot = self.pick_tomorrow_random_preorder_time_if_needed()
        if selected_slot:
            amounts = self.read_amounts(product)
        selected_rounding = None
        if getattr(self, "rounding_payment", False):
            selected_rounding = self.select_checkout_rounding_payment(
                payable=amounts.payable,
                custom_amount=getattr(self, "rounding_amount", None),
            )
            amounts = AmountSnapshot(
                goods_total=amounts.goods_total,
                coupon=amounts.coupon,
                freight=amounts.freight,
                payable=float(selected_rounding.amount),
            )
        if not submit_order:
            logger.info(
                "未传 --submit-order：停在确认订单页，跳过真实提交和支付"
            )
            return
        self.assert_within_payable_limit(amounts)
        submit = self.submit_order(amounts)
        self.pay_and_assert(submit, product)
        if selected_rounding is not None:
            self.assert_order_detail_rounding_change(
                submit,
                selected_rounding.change,
            )
        if self.send_im_after_order:
            self.send_order_cancel_im_if_needed(submit)
        if self.cancel_after_order:
            self.cancel_created_order(submit)

    def cancel_created_order(self, submit: SubmitResult) -> None:
        if not submit.order_no:
            raise AssertionError(
                "本次创建订单未解析到订单号，禁止自动取消；需要人工检查"
            )
        self.ensure_order_detail_page()
        if not self.click_labels(
            ("取消订单", "申请取消"),
            desc="取消本次测试订单",
            y_min_ratio=0.20,
            y_max_ratio=1.0,
        ):
            raise AssertionError(
                f"订单 {submit.order_no} 未找到取消入口，需要人工处理"
            )
        self.click_labels(
            ("测试订单", "不想要了", "其他"),
            desc="选择取消原因",
            y_min_ratio=0.15,
            y_max_ratio=1.0,
        )
        if not self.click_labels(
            ("确认取消", "确定", "提交"),
            desc="确认取消本次测试订单",
            y_min_ratio=0.40,
            y_max_ratio=1.0,
        ):
            raise AssertionError(
                f"订单 {submit.order_no} 取消确认失败，需要人工处理"
            )
        self.assert_page_contains_any(
            ("已取消", "取消成功", "订单关闭"),
            f"订单 {submit.order_no} 未确认取消成功，需要人工处理",
            timeout=20.0,
        )
