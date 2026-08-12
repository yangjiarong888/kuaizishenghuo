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
    xpath_literal,
)


class ShippingPaymentMixin:
    """Keep real submission and payment transitions single-shot and observable."""

    _SUBMIT_ORDER_LABELS = ("提交订单",)
    _PAYMENT_PAGE_ROOT_SELECTOR = (
        '//*[contains(@resource-id,"shipping_payment_page") '
        'or @content-desc="配送支付页"]'
    )
    _PAYMENT_PASSWORD_ROOT_SELECTOR = (
        '//*[contains(@resource-id,"shipping_balance_password") '
        'or @content-desc="余额支付密码弹窗"]'
    )
    _ORDER_DETAIL_ROOT_SELECTOR = (
        '//*[contains(@resource-id,"shipping_order_detail") '
        'or @content-desc="配送订单详情"]'
    )
    _CANCEL_DIALOG_ROOT_SELECTOR = (
        '//*[contains(@resource-id,"shipping_cancel_dialog") '
        'or @content-desc="取消支付确认弹窗"]'
    )
    _CONTEXT_ORDER_NUMBER_SELECTOR = (
        './/*[contains(@resource-id,"shipping_order_number") '
        'or @content-desc="配送订单号"]'
    )
    _ORDER_STATUS_SELECTOR = (
        './/*[contains(@resource-id,"shipping_order_status") '
        'or @content-desc="配送订单状态"]'
    )
    _PAYMENT_PASSWORD_SELECTOR = (
        '//android.widget.EditText['
        '@resource-id="shipping_payment_password" '
        'or @resource-id="pay_password" '
        'or contains(@resource-id,"password") '
        'or contains(@resource-id,"passcode") '
        'or contains(@resource-id,"pwd") '
        'or @password="true" '
        'or contains(@hint,"支付密码")]'
    )
    _ORDER_NUMBER = re.compile(
        r"(?:订单号|订单编号|order(?:\s*number|\s*no\.?)?)\s*[:：#]?\s*([A-Za-z0-9-]{4,})",
        re.IGNORECASE,
    )
    _DELIVERABLE_MARKERS = ("可配送", "可提交", "可寄件", "可下单")
    _HISTORICAL_PACKAGE_MARKERS = ("历史订单", "已完成", "已取消")
    _PACKAGE_CONTAINER_SELECTOR = (
        '//*[contains(@resource-id,"shipping_package_card") '
        'or contains(@resource-id,"shipping_package") '
        'or contains(@resource-id,"delivery_package") '
        'or @content-desc="寄件包裹"]'
    )
    _PACKAGE_ACTION_LABELS = ("去寄件", "立即寄件", "去配送", "提交订单")

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
        order_number = self._read_transition_order_number()
        if not order_number:
            self._payment_failure("submitted_order_identity_unverified")
            raise AssertionError("提交订单后未从专用节点确认新订单号/订单身份")
        self._shipping_order_number = order_number
        logger.info(
            f"shipping_order_identity order={self._masked_order_number(order_number)} "
            "result=verified"
        )
        return order_number

    def pay_balance(self, pay_password: str) -> bool:
        if not pay_password:
            raise ValueError("余额支付需要 SHIPPING_PAY_PASSWORD")
        payment_root = self._require_bound_payment_page()
        logger.info("payment_method=balance password_configured=true")
        self._click_within(
            payment_root, ("余额支付", "余额"), "balance_payment_missing"
        )
        payment_root = self._require_bound_payment_page()
        self._click_within(
            payment_root,
            ("确认支付", "立即支付"),
            "balance_payment_confirm_missing",
        )
        password_root = self._password_root()
        if password_root is None:
            self._payment_failure("balance_password_dialog_missing")
            raise AssertionError("余额支付确认后未进入支付密码弹窗")
        field = self._payment_password_field(password_root)
        if field is None:
            self._payment_failure("balance_password_field_missing")
            raise AssertionError("支付密码弹窗未找到输入框")
        try:
            field.send_keys(pay_password)
        except Exception as exc:
            self._payment_failure(
                "balance_password_entry_failed", redact_values=(pay_password,)
            )
            raise AssertionError("支付密码输入失败") from exc
        self._click_within(
            password_root,
            ("确定", "确认"),
            "balance_password_confirm_missing",
            redact_values=(pay_password,),
        )
        return self.assert_payment_result(
            PaymentMethod.BALANCE, redact_values=(pay_password,)
        )

    def confirm_cash_on_delivery(self) -> bool:
        payment_root = self._require_bound_payment_page()
        logger.info("payment_method=cod selection=started")
        self._click_within(payment_root, ("货到付款",), "cod_payment_missing")
        payment_root = self._require_bound_payment_page()
        self._click_within(
            payment_root,
            ("确认支付", "确认选择", "确定"),
            "cod_payment_confirm_missing",
        )
        return self.assert_payment_result(PaymentMethod.COD)

    def current_payment_state(self) -> OrderPaymentState:
        if self._password_root() is not None or self._cancel_dialog_root() is not None:
            return OrderPaymentState.UNKNOWN
        detail = self._verified_target_order_detail_root()
        if detail is None:
            return OrderPaymentState.UNKNOWN
        statuses = self._displayed_children(detail, self._ORDER_STATUS_SELECTOR)
        if len(statuses) != 1:
            return OrderPaymentState.UNKNOWN
        return self._unambiguous_payment_state(self._element_blob(statuses[0]))

    def cancel_pending_payment(self) -> bool:
        state = self.current_payment_state()
        if not can_cancel_payment(state):
            logger.info(
                "shipping_cancel "
                f"order={self._masked_order_number(getattr(self, '_shipping_order_number', None))} "
                f"state={state.value} cancel_result=blocked"
            )
            return False
        detail = self._verified_target_order_detail_root()
        if detail is None:
            return False
        cancel_actions = self._displayed_children(
            detail, self._relative_text_selector(("取消支付",))
        )
        enabled = [action for action in cancel_actions if self._is_enabled(action)]
        if len(enabled) != 1:
            self._payment_failure("cancel_payment_action_unverified")
            raise AssertionError("待支付订单详情未找到唯一可用的取消支付操作")
        try:
            enabled[0].click()
        except Exception as exc:
            self._payment_failure("cancel_payment_click_failed")
            raise AssertionError("取消支付点击失败") from exc
        dialog = self._cancel_dialog_root()
        if dialog is None:
            self._payment_failure("cancel_payment_dialog_unverified")
            raise AssertionError("取消支付确认弹窗未验证")
        self._click_within(dialog, ("确定", "确认取消"), "cancel_payment_confirm_missing")
        terminal_states = {
            OrderPaymentState.CANCELLED,
            OrderPaymentState.CLOSED,
            OrderPaymentState.NONPAYABLE,
        }
        if not self._wait_until(lambda: self.current_payment_state() in terminal_states):
            self._payment_failure("cancel_payment_terminal_unconfirmed")
            raise AssertionError("取消支付终态未确认")
        final_state = self.current_payment_state()
        logger.info(
            "shipping_cancel "
            f"order={self._masked_order_number(getattr(self, '_shipping_order_number', None))} "
            f"state={final_state.value} cancel_result=success"
        )
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
            detail = self._verified_target_order_detail_root()
            if detail is None:
                self._payment_failure(
                    f"{method.value}_order_detail_unverified",
                    redact_values=redact_values,
                )
                raise AssertionError("支付结果未在新订单详情中确认")
            self._assert_cancel_unavailable(detail, redact_values=redact_values)
            logger.info(
                "shipping_payment "
                f"order={self._masked_order_number(getattr(self, '_shipping_order_number', None))} "
                f"payment_method={method.value} state={expected.value} result=success"
            )
            return True
        self._payment_failure(
            f"{method.value}_payment_result_unconfirmed", redact_values=redact_values
        )
        raise AssertionError("支付结果未确认")

    def leave_balance_payment_unconfirmed(self) -> bool:
        """Select balance without entering a password, then require a pending order."""
        if (
            self._password_root() is None
            and self.current_payment_state() is OrderPaymentState.PENDING
        ):
            return True
        payment_root = self._require_bound_payment_page()
        logger.info("payment_method=balance action=leave_unconfirmed")
        self._click_within(
            payment_root, ("余额支付", "余额"), "balance_payment_missing"
        )
        payment_root = self._require_bound_payment_page()
        self._click_within(
            payment_root,
            ("确认支付", "立即支付"),
            "balance_payment_confirm_missing",
        )
        password_root = self._password_root()
        if password_root is not None:
            dismissal = self._first_displayed_child(
                password_root, self._relative_text_selector(("取消", "关闭", "返回"))
            )
            if dismissal is not None:
                try:
                    dismissal.click()
                except Exception as exc:
                    logger.debug(
                        "Balance password dismissal click failed error_type=%s",
                        type(exc).__name__,
                    )
            if not self._is_exact_pending_order_detail():
                try:
                    self.driver.back()
                except Exception as exc:
                    logger.debug(
                        "Balance password back failed error_type=%s",
                        type(exc).__name__,
                    )
        if not self._wait_until(self._is_exact_pending_order_detail):
            self._payment_failure("balance_pending_order_detail_unconfirmed")
            raise AssertionError("未能退出支付密码流程并到达新订单待支付订单详情")
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
            candidates = self.driver.find_elements(
                AppiumBy.XPATH, self._PACKAGE_CONTAINER_SELECTOR
            )
        except Exception as exc:
            logger.debug("Shipping package lookup failed error_type=%s", type(exc).__name__)
            candidates = []
        for candidate in candidates:
            try:
                marker_text = self._element_blob(candidate)
                if not candidate.is_displayed() or not candidate.is_enabled():
                    continue
                if any(marker in marker_text for marker in self._HISTORICAL_PACKAGE_MARKERS):
                    continue
                if not any(marker in marker_text for marker in self._DELIVERABLE_MARKERS):
                    continue
                action = self._first_package_action(candidate)
                if action is None:
                    continue
            except Exception as exc:
                logger.debug("Shipping package selection failed error_type=%s", type(exc).__name__)
                continue
            try:
                action.click()
            except Exception as exc:
                raise AssertionError("可配送包裹操作点击失败") from exc
            if self._wait_until(self._is_package_checkout):
                return True
            raise AssertionError("可配送包裹操作后未进入提交订单页")
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
            literal = xpath_literal(label)
            button = self._first_displayed(
                AppiumBy.XPATH,
                f'//*[@text={literal} or @content-desc={literal}]',
            )
            if button is not None:
                return button
        return None

    def _wait_for_payment_or_order_detail(self) -> bool:
        return self._wait_until(
            lambda: self._payment_root() is not None
            or bool(self._order_detail_roots())
        )

    def _read_transition_order_number(self) -> str | None:
        roots = []
        payment = self._payment_root()
        if payment is not None:
            roots.append(payment)
        roots.extend(self._order_detail_roots())
        if len(roots) != 1:
            return None
        return self._read_order_number_from_root(roots[0])

    def _read_order_number_from_root(self, root) -> str | None:
        nodes = self._displayed_children(root, self._CONTEXT_ORDER_NUMBER_SELECTOR)
        if len(nodes) != 1:
            return None
        match = self._ORDER_NUMBER.search(self._element_blob(nodes[0]))
        if match is None:
            return None
        value = match.group(1).strip()
        if value.lower() in {"none", "null", "unknown", "unavailable"}:
            return None
        return value

    @staticmethod
    def _masked_order_number(order_number: str | None) -> str:
        value = str(order_number or "").strip()
        return f"***{value[-4:]}" if value else "unverified"

    def _payment_root(self):
        return self._single_displayed_root(self._PAYMENT_PAGE_ROOT_SELECTOR)

    def _password_root(self):
        return self._single_displayed_root(self._PAYMENT_PASSWORD_ROOT_SELECTOR)

    def _cancel_dialog_root(self):
        return self._single_displayed_root(self._CANCEL_DIALOG_ROOT_SELECTOR)

    def _single_displayed_root(self, selector: str):
        try:
            candidates = self.driver.find_elements(AppiumBy.XPATH, selector)
        except Exception as exc:
            logger.debug(
                "Payment context lookup failed error_type=%s", type(exc).__name__
            )
            return None
        displayed = [
            candidate for candidate in candidates if self._is_displayed(candidate)
        ]
        return displayed[0] if len(displayed) == 1 else None

    def _order_detail_roots(self) -> list:
        try:
            candidates = self.driver.find_elements(
                AppiumBy.XPATH, self._ORDER_DETAIL_ROOT_SELECTOR
            )
        except Exception as exc:
            logger.debug(
                "Order detail lookup failed error_type=%s", type(exc).__name__
            )
            return []
        return [candidate for candidate in candidates if self._is_displayed(candidate)]

    def _verified_target_order_detail_root(self):
        target = getattr(self, "_shipping_order_number", None)
        if not target:
            return None
        roots = self._order_detail_roots()
        if len(roots) != 1:
            return None
        return (
            roots[0]
            if self._read_order_number_from_root(roots[0]) == target
            else None
        )

    def _require_bound_payment_page(self):
        target = getattr(self, "_shipping_order_number", None)
        root = self._payment_root()
        if (
            not target
            or root is None
            or self._read_order_number_from_root(root) != target
        ):
            self._payment_failure("payment_order_identity_unverified")
            raise AssertionError("支付页未绑定到新提交订单身份")
        return root

    def _payment_password_field(self, password_root):
        return self._first_displayed_child(password_root, self._PAYMENT_PASSWORD_SELECTOR)

    def _first_package_action(self, container):
        for label in self._PACKAGE_ACTION_LABELS:
            literal = xpath_literal(label)
            try:
                actions = container.find_elements(
                    AppiumBy.XPATH,
                    f'.//*[@text={literal} or @content-desc={literal}]',
                )
            except Exception as exc:
                logger.debug("Shipping package action lookup failed error_type=%s", type(exc).__name__)
                continue
            for action in actions:
                try:
                    if action.is_displayed() and action.is_enabled():
                        return action
                except Exception as exc:
                    logger.debug(
                        "Shipping package action visibility failed error_type=%s",
                        type(exc).__name__,
                    )
        return None

    def _is_package_checkout(self) -> bool:
        return "提交订单" in self.page_blob() and not self._is_delivery_orders_page()

    def _click_within(
        self,
        root,
        labels: tuple[str, ...],
        failure_stage: str,
        *,
        redact_values: tuple[str, ...] = (),
    ) -> None:
        action = self._first_displayed_child(root, self._relative_text_selector(labels))
        if action is None or not self._is_enabled(action):
            self._payment_failure(failure_stage, redact_values=redact_values)
            raise AssertionError("支付上下文内未找到唯一可用操作")
        try:
            action.click()
        except Exception as exc:
            self._payment_failure(failure_stage, redact_values=redact_values)
            raise AssertionError("支付上下文操作点击失败") from exc

    @staticmethod
    def _relative_text_selector(labels: tuple[str, ...]) -> str:
        clauses = []
        for label in labels:
            literal = xpath_literal(label)
            clauses.extend((f"@text={literal}", f"@content-desc={literal}"))
        return ".//*[" + " or ".join(clauses) + "]"

    def _displayed_children(self, root, selector: str) -> list:
        try:
            candidates = root.find_elements(AppiumBy.XPATH, selector)
        except Exception as exc:
            logger.debug(
                "Scoped payment lookup failed error_type=%s", type(exc).__name__
            )
            return []
        return [candidate for candidate in candidates if self._is_displayed(candidate)]

    def _first_displayed_child(self, root, selector: str):
        candidates = self._displayed_children(root, selector)
        return candidates[0] if len(candidates) == 1 else None

    @staticmethod
    def _is_displayed(element) -> bool:
        try:
            return bool(element.is_displayed())
        except Exception:
            return False

    @staticmethod
    def _is_enabled(element) -> bool:
        try:
            return bool(element.is_enabled())
        except Exception:
            return False

    def _is_exact_pending_order_detail(self) -> bool:
        return (
            self._password_root() is None
            and self.current_payment_state() is OrderPaymentState.PENDING
        )

    def _assert_cancel_unavailable(
        self, detail, *, redact_values: tuple[str, ...] = ()
    ) -> None:
        cancel_actions = self._displayed_children(
            detail, self._relative_text_selector(("取消支付",))
        )
        if any(self._is_enabled(action) for action in cancel_actions):
            self._payment_failure(
                "paid_order_cancel_still_available", redact_values=redact_values
            )
            raise AssertionError("已支付/货到付款订单详情仍存在可用取消支付操作")

    @staticmethod
    def _unambiguous_payment_state(text: str) -> OrderPaymentState:
        markers = {
            OrderPaymentState.PENDING: ("待支付", "待付款"),
            OrderPaymentState.PAID: ("支付成功", "已支付", "在线支付"),
            OrderPaymentState.COD: ("货到付款",),
            OrderPaymentState.CANCELLED: ("支付已取消", "已取消", "取消成功"),
            OrderPaymentState.CLOSED: ("订单已关闭", "已关闭", "订单关闭"),
            OrderPaymentState.NONPAYABLE: ("不可支付", "已失效", "支付失效"),
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
