"""Real-order submission and fail-closed shipping payment handling."""

from __future__ import annotations

import re

from appium.webdriver.common.appiumby import AppiumBy

from .app_common import logger
from .shipping_types import (
    AddressData,
    AddressPolicy,
    OrderPaymentState,
    PaymentMethod,
    can_cancel_payment,
    classify_payment_state,
    parse_delivery_date,
)


class ShippingPaymentMixin:
    """Keep real submission and payment transitions single-shot and observable."""

    _SUBMIT_ORDER_LABELS = ("提交订单",)
    _PAYMENT_TRANSITION_MARKERS = (
        "支付方式",
        "支付密码",
        "订单详情",
        "待支付",
        "已支付",
        "货到付款",
    )
    _PAYMENT_PASSWORD_SELECTOR = (
        '//android.widget.EditText['
        'contains(@resource-id,"pay") or contains(@resource-id,"password") '
        'or @password="true" or contains(@hint,"支付密码")] '
        '|//android.widget.EditText'
    )
    _ORDER_NUMBER = re.compile(
        r"(?:订单号|订单编号|order(?:\s*number|\s*no\.?)?)\s*[:：#]?\s*([A-Za-z0-9-]{4,})",
        re.IGNORECASE,
    )
    _DELIVERABLE_MARKERS = ("可配送", "可提交", "可寄件", "可下单")

    def submit_order_once(self) -> str | None:
        """Submit the checkout exactly once for this page object instance."""
        if getattr(self, "_shipping_order_submitted", False):
            logger.warning("已触发提交订单，阻止重复点击")
            return getattr(self, "_shipping_order_number", None)
        button = self._find_submit_order_button()
        if button is None:
            raise AssertionError("提交订单页未找到提交订单按钮")
        self._shipping_order_submitted = True
        try:
            button.click()
        except Exception as exc:
            self._payment_failure("submit_order_click_failed")
            raise AssertionError("提交订单按钮点击失败") from exc
        if not self._wait_for_payment_or_order_detail():
            self._payment_failure("submit_transition_timeout")
            raise AssertionError("提交订单后未进入支付页或订单详情")
        self._shipping_order_number = self._read_order_number()
        return self._shipping_order_number

    def pay_balance(self, pay_password: str) -> bool:
        if not pay_password:
            raise ValueError("余额支付需要 SHIPPING_PAY_PASSWORD")
        logger.info("payment_method=balance password_configured=true")
        self._click_payment_text(("余额支付", "余额"), "balance_payment_missing")
        self._click_payment_text(("确认支付", "立即支付"), "balance_payment_confirm_missing")
        field = self._payment_password_field()
        if field is None:
            self._payment_failure("balance_password_field_missing")
            raise AssertionError("支付密码弹窗未找到输入框")
        try:
            field.send_keys(pay_password)
        except Exception as exc:
            self._payment_failure("balance_password_entry_failed")
            raise AssertionError("支付密码输入失败") from exc
        self._click_payment_text(
            ("确定", "确认"),
            "balance_password_confirm_missing",
            redact_values=(pay_password,),
        )
        return self.assert_payment_result(
            PaymentMethod.BALANCE, redact_values=(pay_password,)
        )

    def confirm_cash_on_delivery(self) -> bool:
        self._click_payment_text(("货到付款",), "cod_payment_missing")
        self._click_payment_text(
            ("确认支付", "确认选择", "确定"), "cod_payment_confirm_missing"
        )
        return self.assert_payment_result(PaymentMethod.COD)

    def current_payment_state(self) -> OrderPaymentState:
        return self._unambiguous_payment_state(self.page_blob())

    def cancel_pending_payment(self) -> bool:
        state = self.current_payment_state()
        if not can_cancel_payment(state):
            return False
        self._click_payment_text(("取消支付",), "cancel_payment_missing")
        self._click_payment_text(("确定", "确认取消"), "cancel_payment_confirm_missing")
        if self.current_payment_state() is OrderPaymentState.PENDING:
            self._payment_failure("cancel_payment_still_pending")
            raise AssertionError("取消支付后订单仍为待支付")
        return True

    def assert_payment_result(
        self, method: PaymentMethod, *, redact_values: tuple[str, ...] = ()
    ) -> bool:
        expected = (
            OrderPaymentState.COD
            if method is PaymentMethod.COD
            else OrderPaymentState.PAID
        )
        if self._wait_until(lambda: self.current_payment_state() is expected):
            return True
        self._payment_failure(
            f"{method.value}_payment_result_unconfirmed", redact_values=redact_values
        )
        raise AssertionError("支付结果未确认")

    def leave_balance_payment_unconfirmed(self) -> bool:
        """Select balance without entering a password, then require a pending order."""
        if self.current_payment_state() is OrderPaymentState.PENDING:
            return True
        self._click_payment_text(("余额支付", "余额"), "balance_payment_missing")
        self._click_payment_text(("确认支付", "立即支付"), "balance_payment_confirm_missing")
        if not self._wait_until(
            lambda: self.current_payment_state() is OrderPaymentState.PENDING
        ):
            self._payment_failure("balance_pending_state_unconfirmed")
            raise AssertionError("未输入余额支付密码时订单未进入待支付状态")
        return True

    def prevalidate_order_inputs(
        self,
        *,
        payment_method: PaymentMethod,
        cancel_unpaid: bool,
        pay_password: str,
        address_policy: AddressPolicy,
        address_data: AddressData,
    ) -> None:
        if not isinstance(payment_method, PaymentMethod):
            raise ValueError("payment_method 必须是 PaymentMethod")
        if not isinstance(address_policy, AddressPolicy):
            raise ValueError("address_policy 必须是 AddressPolicy")
        if not isinstance(address_data, AddressData):
            raise ValueError("address_data 必须是 AddressData")
        if not isinstance(cancel_unpaid, bool):
            raise ValueError("cancel_unpaid 必须是 bool")
        if payment_method is PaymentMethod.COD and cancel_unpaid:
            raise ValueError("货到付款订单不允许取消待支付")
        if payment_method is PaymentMethod.BALANCE and not cancel_unpaid and not pay_password:
            raise ValueError("余额支付需要 SHIPPING_PAY_PASSWORD")
        if address_policy is AddressPolicy.EXISTING and not address_data.match.strip():
            raise ValueError("现有地址策略需要 SHIPPING_ADDRESS_MATCH")
        if address_policy is AddressPolicy.ADD and address_data.missing_for_add():
            raise ValueError("新增地址缺少必填字段")
        if address_policy is AddressPolicy.AUTO and not address_data.match.strip() and address_data.missing_for_add():
            raise ValueError("自动地址策略需要匹配关键字或完整新增地址")

    def open_first_deliverable_package(self) -> bool:
        """Open only a package explicitly marked available for shipping submission."""
        try:
            candidates = self.driver.find_elements(AppiumBy.XPATH, "//*[@text or @content-desc]")
        except Exception as exc:
            logger.debug("Shipping package lookup failed error_type=%s", type(exc).__name__)
            candidates = []
        for candidate in candidates:
            try:
                marker_text = self._element_blob(candidate)
                if not candidate.is_displayed() or not candidate.is_enabled():
                    continue
                if not any(marker in marker_text for marker in self._DELIVERABLE_MARKERS):
                    continue
                candidate.click()
                return True
            except Exception as exc:
                logger.debug("Shipping package selection failed error_type=%s", type(exc).__name__)
        raise AssertionError("未找到明确标记可配送或可提交的包裹")

    def verify_checkout_ready(self) -> bool:
        """Re-read applied address and future delivery selection before real submission."""
        data = getattr(self, "_shipping_address_data", None)
        if not isinstance(data, AddressData):
            raise AssertionError("提交订单前缺少已验证的收货地址")
        self.verify_shipping_address_applied(data)
        today = self.device_today()
        delivery_text = self._checkout_delivery_text()
        parsed = parse_delivery_date(delivery_text, today)
        if parsed is None or parsed <= today:
            raise AssertionError("提交订单前配送日期必须可解析且严格晚于今天")
        selected = getattr(self, "_shipping_delivery_date", None)
        if selected is not None and parsed != selected:
            raise AssertionError("提交订单前配送日期回读不一致")
        return True

    def run_order_flow(
        self,
        *,
        payment_method: PaymentMethod,
        cancel_unpaid: bool,
        pay_password: str,
        address_policy: AddressPolicy,
        address_data: AddressData,
    ) -> bool:
        self.prevalidate_order_inputs(
            payment_method=payment_method,
            cancel_unpaid=cancel_unpaid,
            pay_password=pay_password,
            address_policy=address_policy,
            address_data=address_data,
        )
        if not self.enter_from_app_home():
            return False
        if not self.switch_to_delivery_orders():
            return False
        self.open_first_deliverable_package()
        self.ensure_shipping_address(address_policy, address_data)
        self._shipping_address_data = address_data
        self._shipping_delivery_date = self.select_earliest_future_delivery()
        self.verify_checkout_ready()
        self.submit_order_once()
        if payment_method is PaymentMethod.COD:
            ok = self.confirm_cash_on_delivery()
        elif cancel_unpaid:
            self.leave_balance_payment_unconfirmed()
            ok = self.cancel_pending_payment()
        else:
            ok = self.pay_balance(pay_password)
        if ok:
            ok = self.switch_to_shipping_home() and self.switch_to_delivery_orders()
        return ok

    def _find_submit_order_button(self):
        for label in self._SUBMIT_ORDER_LABELS:
            button = self._first_displayed(
                AppiumBy.XPATH,
                f'//*[@text="{label}" or @content-desc="{label}"]',
            )
            if button is not None:
                return button
        return None

    def _wait_for_payment_or_order_detail(self) -> bool:
        return self._wait_until(
            lambda: any(marker in self.page_blob() for marker in self._PAYMENT_TRANSITION_MARKERS)
        )

    def _read_order_number(self) -> str | None:
        match = self._ORDER_NUMBER.search(self.page_blob())
        return match.group(1) if match else None

    def _payment_password_field(self):
        return self._first_displayed(AppiumBy.XPATH, self._PAYMENT_PASSWORD_SELECTOR)

    def _click_payment_text(
        self,
        labels: tuple[str, ...],
        failure_stage: str,
        *,
        redact_values: tuple[str, ...] = (),
    ) -> None:
        if not self._click_text(labels):
            self._payment_failure(failure_stage, redact_values=redact_values)
            raise AssertionError("支付页面未找到所需操作")

    @staticmethod
    def _unambiguous_payment_state(text: str) -> OrderPaymentState:
        markers = {
            OrderPaymentState.PENDING: ("待支付", "待付款"),
            OrderPaymentState.PAID: ("支付成功", "已支付", "在线支付"),
            OrderPaymentState.COD: ("货到付款",),
        }
        observed = {
            state
            for state, state_markers in markers.items()
            if any(marker in text for marker in state_markers)
        }
        if len(observed) != 1:
            return OrderPaymentState.UNKNOWN
        return classify_payment_state(text)

    def _payment_failure(self, stage: str, *, redact_values: tuple[str, ...] = ()) -> None:
        self.capture_shipping_failure(
            stage,
            sensitive=True,
            redact_values=(*self._payment_redaction_values(), *redact_values),
        )

    def _payment_redaction_values(self) -> tuple[str, ...]:
        data = getattr(self, "_shipping_address_data", None)
        if not isinstance(data, AddressData):
            return ()
        return (data.match, data.name, data.phone, data.detail, data.postcode)
