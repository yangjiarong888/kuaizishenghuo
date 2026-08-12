from types import SimpleNamespace

import pytest

import pages.shipping_page as shipping_page_module
import pages.shipping_payment_mixin as shipping_payment_module

from pages.shipping_page import ShippingPage
from pages.shipping_types import AddressData, AddressPolicy, OrderPaymentState, PaymentMethod


@pytest.fixture(autouse=True)
def zero_ui_wait(monkeypatch):
    monkeypatch.setattr(shipping_page_module.AppConfig, "WAIT_TIMEOUT", 0)


class UiNode:
    def __init__(
        self,
        driver,
        text="",
        on_click=None,
        *,
        enabled=True,
        attributes=None,
        kind="",
    ):
        self.driver = driver
        self.text = text
        self.on_click = on_click
        self.enabled = enabled
        self.attributes = attributes or {}
        self.kind = kind

    def is_displayed(self):
        return True

    def is_enabled(self):
        return self.enabled

    def get_attribute(self, name):
        values = {
            "text": self.text,
            "content-desc": self.attributes.get("content-desc", ""),
            "enabled": "true" if self.enabled else "false",
        }
        return self.attributes.get(name, values.get(name, ""))

    def click(self):
        self.driver.clicks.append(self.text)
        if self.on_click:
            self.on_click()

    def find_elements(self, by, value):
        return self.driver.find_in_node(self, value)


class PasswordField(UiNode):
    def send_keys(self, value):
        self.driver.sent_values.append(value)


class NavigationDriver:
    def __init__(self, screen="app_home"):
        self.screen = screen
        self.ambiguous_roots = False
        self.clicks = []
        self.current_activity = "com.bs.feifubao.MainActivity"
        self.current_context = "NATIVE_APP"
        self.screenshot_calls = 0

    @property
    def page_source(self):
        if self.screen == "app_home":
            return "筷子生活 首页 国际货运"
        if self.screen in {"shipping_home", "delivery_orders"}:
            # Both tab labels and both families of content text deliberately coexist.
            return "国际货运 寄件全球 配送订单 全部 待付款"
        return "国际货运 寄件全球 reused wrong page"

    def save_screenshot(self, path):
        self.screenshot_calls += 1
        return True

    @staticmethod
    def _mentions(value, label):
        return label in value

    def find_elements(self, by, value):
        if ("app_home_root" in value or "筷子生活首页" in value) and (
            self.screen == "app_home" or self.ambiguous_roots
        ):
            return [UiNode(self, "筷子生活 首页", kind="app_home")]
        if (
            "shipping_home_content" in value or "国际货运首页内容" in value
        ) and (self.screen == "shipping_home" or self.ambiguous_roots):
            return [UiNode(self, "国际货运 寄件全球", kind="shipping_home")]
        if (
            "delivery_order_list" in value or "配送订单列表" in value
        ) and (self.screen == "delivery_orders" or self.ambiguous_roots):
            return [UiNode(self, "配送订单 全部 待付款", kind="delivery_orders")]
        if self.screen == "app_home" and self._mentions(value, "国际货运"):
            return [UiNode(self, "国际货运", lambda: setattr(self, "screen", "shipping_home"))]
        if self.screen == "shipping_home" and self._mentions(value, "配送订单"):
            return [UiNode(self, "配送订单", lambda: setattr(self, "screen", "delivery_orders"))]
        if self.screen == "delivery_orders" and any(
            self._mentions(value, label) for label in ("国际货运", "首页")
        ):
            return [UiNode(self, "首页", lambda: setattr(self, "screen", "shipping_home"))]
        return []


def test_simultaneous_tab_labels_still_require_bidirectional_clicks():
    driver = NavigationDriver("shipping_home")
    page = ShippingPage(driver)

    assert page.switch_to_delivery_orders() is True
    assert driver.screen == "delivery_orders"
    assert page.switch_to_shipping_home() is True
    assert driver.screen == "shipping_home"
    assert driver.clicks == ["配送订单", "首页"]


@pytest.mark.parametrize("screen", ("shipping_home", "wrong_page"))
def test_home_entry_reused_or_wrong_page_fails_closed_without_literal_entry_click(screen):
    driver = NavigationDriver(screen)

    assert ShippingPage(driver).enter_from_app_home() is False
    assert driver.clicks == []


def test_home_entry_emits_privacy_safe_navigation_evidence(monkeypatch):
    messages = []
    monkeypatch.setattr(shipping_page_module.logger, "info", lambda *args: messages.append(args))
    driver = NavigationDriver("app_home")

    assert ShippingPage(driver).enter_from_app_home() is True

    rendered = repr(messages)
    assert "app_home_to_shipping" in rendered
    assert "国际货运" in rendered
    assert "success" in rendered


@pytest.mark.parametrize(
    ("screen", "operation"),
    (
        ("app_home", "enter"),
        ("shipping_home", "delivery"),
        ("delivery_orders", "home"),
    ),
)
def test_ambiguous_active_navigation_roots_fail_closed_without_click(screen, operation):
    driver = NavigationDriver(screen)
    driver.ambiguous_roots = True
    page = ShippingPage(driver)

    result = {
        "enter": page.enter_from_app_home,
        "delivery": page.switch_to_delivery_orders,
        "home": page.switch_to_shipping_home,
    }[operation]()

    assert result is False
    assert driver.clicks == []


class AddressDriver:
    def __init__(self, rows, *, click_noop=False, lookup_error=False):
        self.rows = list(rows)
        self.screen = "checkout"
        self.selected_address = ""
        self.click_noop = click_noop
        self.lookup_error = lookup_error
        self.clicks = []
        self.add_clicks = 0
        self.queries = []
        self.current_activity = ".MainActivity"
        self.current_context = "NATIVE_APP"

    @property
    def page_source(self):
        if self.screen == "checkout":
            suffix = f" 收货地址 {self.selected_address}" if self.selected_address else " 请选择收货地址"
            return "提交订单" + suffix
        if self.screen == "address_book":
            return "选择收货地址 新增地址 " + " ".join(self.rows)
        if self.screen == "address_form":
            return "新增地址 国家 城市 联系人 手机号码 详细地址 邮编 保存"
        return ""

    def _open_book(self):
        self.screen = "address_book"

    def _open_add(self):
        self.add_clicks += 1
        self.screen = "address_form"

    def _select(self, row):
        if self.click_noop:
            return
        self.selected_address = row
        self.screen = "checkout"

    def find_elements(self, by, value):
        if ("shipping_checkout_root" in value or "配送提交订单页" in value) and self.screen == "checkout":
            return [UiNode(self, "提交订单", kind="checkout")]
        if ("shipping_checkout_address" in value or "配送地址回填" in value) and self.screen == "checkout" and self.selected_address:
            return [UiNode(self, self.selected_address, kind="checkout_address")]
        if ("shipping_address_book" in value or "公共地址簿" in value) and self.screen == "address_book":
            return [UiNode(self, "选择收货地址", kind="address_book")]
        if self.screen == "checkout" and any(label in value for label in ("请选择收货地址", "收货地址", "配送地址")):
            return [UiNode(self, "请选择收货地址", self._open_book)]
        if self.screen == "address_book" and any(label in value for label in ("新增地址", "添加地址")):
            return [UiNode(self, "新增地址", self._open_add)]
        if self.screen == "address_book" and (
            "shipping_address_row" in value or "contains(@text" in value
        ):
            self.queries.append(value)
            if self.lookup_error:
                raise RuntimeError("address hierarchy unavailable")
            if any('"' in row and "'" in row for row in self.rows) and "concat(" not in value:
                raise RuntimeError("malformed XPath")
            return [
                UiNode(
                    self,
                    row,
                    lambda selected=row: self._select(selected),
                    attributes={"resource-id": "shipping_address_row"},
                )
                for row in self.rows
            ]
        return []

    def get_window_size(self):
        return {"width": 1080, "height": 1920}

    def execute_script(self, name, payload):
        return None


def complete_address(**overrides):
    values = {
        "match": "0994",
        "name": "Tester",
        "phone": "+639621170994",
        "country": "菲律宾",
        "city": "Manila",
        "detail": "100 Test Street",
        "postcode": "1000",
    }
    values.update(overrides)
    return AddressData(**values)


def test_existing_match_only_selects_and_verifies_checkout_application():
    driver = AddressDriver(["Shared recipient 0994 Manila"])

    assert ShippingPage(driver).ensure_shipping_address(
        AddressPolicy.EXISTING, AddressData(match="0994")
    ) is True
    assert driver.selected_address == "Shared recipient 0994 Manila"
    assert driver.screen == "checkout"


def test_existing_address_click_noop_cannot_pass_on_still_visible_address_row():
    driver = AddressDriver(["Tester +639621170994 Manila"], click_noop=True)

    with pytest.raises(AssertionError, match="提交订单页|回填"):
        ShippingPage(driver).ensure_shipping_address(AddressPolicy.EXISTING, complete_address())

    assert driver.screen == "address_book"


def test_auto_lookup_error_fails_closed_without_adding_duplicate_address():
    driver = AddressDriver(["Other 0000 Cebu"], lookup_error=True)

    with pytest.raises(AssertionError, match="查找|地址簿"):
        ShippingPage(driver).ensure_shipping_address(AddressPolicy.AUTO, complete_address())

    assert driver.add_clicks == 0


def test_address_match_with_both_quote_types_uses_safe_xpath_and_never_adds():
    match = 'He said "it\'s home"'
    driver = AddressDriver([f"Shared {match} Manila"])

    assert ShippingPage(driver).ensure_shipping_address(
        AddressPolicy.EXISTING, AddressData(match=match)
    ) is True
    assert driver.add_clicks == 0
    assert driver.queries and "concat(" in driver.queries[0]


def test_ambiguous_existing_address_match_fails_without_click_or_add():
    driver = AddressDriver(["Recipient A 0994 Manila", "Recipient B 0994 Cebu"])

    with pytest.raises(AssertionError, match="多个|不唯一|歧义"):
        ShippingPage(driver).ensure_shipping_address(
            AddressPolicy.EXISTING, AddressData(match="0994")
        )

    assert driver.clicks == ["请选择收货地址"]
    assert driver.add_clicks == 0


class OrderDriver:
    def __init__(
        self,
        *,
        screen="payment",
        order_number="NEW-1234",
        detail_order_number=None,
        status="待支付",
    ):
        self.screen = screen
        self.order_number = order_number
        self.detail_order_number = detail_order_number or order_number
        self.status = status
        self.selected_method = ""
        self.clicks = []
        self.sent_values = []
        self.payment_confirm_responsive = True
        self.password_confirm_responsive = True
        self.dismiss_responsive = True
        self.back_responsive = True
        self.cancel_result = "已取消"
        self.cancel_enabled = status == "待支付"
        self.global_cancel_decoy = False
        self.detail_decoys = True
        self.password_background_pending = False
        self.extra_detail_order_numbers = []
        self.extra_payment_order_numbers = []
        self.global_payment_action_queries = 0
        self.current_activity = ".MainActivity"
        self.current_context = "NATIVE_APP"

    @property
    def page_source(self):
        if self.screen == "checkout":
            return "提交订单 已选择地址 明天"
        if self.screen == "payment":
            return "支付方式 余额支付 货到付款"
        if self.screen == "balance_password":
            if self.password_background_pending:
                return "请输入支付密码 背景订单待支付"
            return "请输入支付密码 在线支付"
        if self.screen == "order_detail":
            decoys = " 待付款筛选 货到付款选项" if self.detail_decoys else ""
            return f"订单详情 订单号 {self.detail_order_number} {self.status}{decoys}"
        if self.screen == "cancel_dialog":
            return "确认取消支付 加载中"
        if self.screen == "order_list":
            return "配送订单 OTHER-9999 待支付 取消支付"
        return ""

    def _show_payment(self):
        self.screen = "payment"

    def _select_balance(self):
        self.selected_method = "balance"

    def _select_cod(self):
        self.selected_method = "cod"

    def _confirm_method(self):
        if not self.payment_confirm_responsive:
            return
        if self.selected_method == "balance":
            self.screen = "balance_password"
        elif self.selected_method == "cod":
            self.screen = "order_detail"
            self.detail_order_number = self.order_number
            self.status = "货到付款"
            self.cancel_enabled = False

    def _confirm_password(self):
        if not self.password_confirm_responsive:
            return
        self.screen = "order_detail"
        self.detail_order_number = self.order_number
        self.status = "已支付"
        self.cancel_enabled = False

    def _dismiss_password(self):
        if self.dismiss_responsive:
            self.screen = "order_detail"
            self.detail_order_number = self.order_number
            self.status = "待支付"
            self.cancel_enabled = True

    def back(self):
        self.clicks.append("driver.back")
        if self.back_responsive:
            self.screen = "order_detail"
            self.detail_order_number = self.order_number
            self.status = "待支付"
            self.cancel_enabled = True

    def _open_cancel(self):
        self.screen = "cancel_dialog"

    def _confirm_cancel(self):
        if self.cancel_result == "dialog_noop":
            return
        self.screen = "order_detail"
        self.status = self.cancel_result
        self.cancel_enabled = False

    def find_elements(self, by, value):
        if ("shipping_checkout_root" in value or "配送提交订单页" in value) and self.screen == "checkout":
            return [UiNode(self, "提交订单", kind="checkout")]
        if ("shipping_payment_page" in value or "配送支付页" in value) and self.screen == "payment":
            return [
                UiNode(self, "支付方式", kind="payment"),
                *[
                    UiNode(
                        self,
                        "支付方式",
                        kind="payment_extra",
                        attributes={"order-number": number},
                    )
                    for number in self.extra_payment_order_numbers
                ],
            ]
        if ("shipping_balance_password" in value or "余额支付密码弹窗" in value) and self.screen == "balance_password":
            return [UiNode(self, "请输入支付密码", kind="password")]
        if ("shipping_order_detail" in value or "配送订单详情" in value) and self.screen == "order_detail":
            return [
                UiNode(self, "订单详情", kind="detail"),
                *[
                    UiNode(
                        self,
                        "订单详情",
                        kind="detail_extra",
                        attributes={"order-number": number},
                    )
                    for number in self.extra_detail_order_numbers
                ],
            ]
        if ("shipping_cancel_dialog" in value or "取消支付确认弹窗" in value) and self.screen == "cancel_dialog":
            return [UiNode(self, "确认取消支付", kind="cancel_dialog")]
        if self.screen == "checkout" and "提交订单" in value:
            return [UiNode(self, "提交订单", self._show_payment)]
        if self.screen == "payment" and "余额支付" in value:
            self.global_payment_action_queries += 1
            return [UiNode(self, "余额支付", self._select_balance)]
        if self.screen == "payment" and "货到付款" in value:
            self.global_payment_action_queries += 1
            return [UiNode(self, "货到付款", self._select_cod)]
        if self.screen == "payment" and any(label in value for label in ("确认支付", "确认选择", "确定")):
            self.global_payment_action_queries += 1
            return [UiNode(self, "确认支付", self._confirm_method)]
        if self.screen == "balance_password" and "android.widget.EditText" in value:
            return [PasswordField(self, "支付密码")]
        if self.screen == "balance_password" and any(label in value for label in ("确定", "确认")):
            return [UiNode(self, "确定", self._confirm_password)]
        if (
            self.screen == "order_detail"
            and "取消支付" in value
            and "shipping_cancel_dialog" not in value
            and "取消支付确认弹窗" not in value
        ):
            return [UiNode(self, "取消支付", self._open_cancel, enabled=self.cancel_enabled)]
        if self.screen == "cancel_dialog" and any(label in value for label in ("确定", "确认取消")):
            return [UiNode(self, "确定", self._confirm_cancel)]
        if self.screen == "order_list" and self.global_cancel_decoy and "取消支付" in value:
            return [UiNode(self, "取消支付", self._open_cancel)]
        return []

    def find_in_node(self, node, value):
        if node.kind in {"payment", "payment_extra", "detail", "detail_extra"} and any(
            marker in value for marker in ("shipping_order_number", "配送订单号")
        ):
            if node.kind == "payment":
                number = self.order_number
            elif node.kind == "detail":
                number = self.detail_order_number
            else:
                number = node.attributes["order-number"]
            return [UiNode(self, f"订单号: {number}")]
        if node.kind in {"detail", "detail_extra"} and any(
            marker in value for marker in ("shipping_order_status", "配送订单状态")
        ):
            return [UiNode(self, self.status)]
        if node.kind == "payment" and "余额支付" in value:
            return [UiNode(self, "余额支付", self._select_balance)]
        if node.kind == "payment" and "货到付款" in value:
            return [UiNode(self, "货到付款", self._select_cod)]
        if node.kind == "payment" and any(
            label in value for label in ("确认支付", "立即支付", "确认选择", "确定")
        ):
            return [UiNode(self, "确认支付", self._confirm_method)]
        if node.kind == "detail" and "取消支付" in value:
            return [UiNode(self, "取消支付", self._open_cancel, enabled=self.cancel_enabled)]
        if node.kind == "password" and "android.widget.EditText" in value:
            return [PasswordField(self, "支付密码")]
        if node.kind == "password" and any(label in value for label in ("取消", "关闭", "返回")):
            return [UiNode(self, "关闭", self._dismiss_password)]
        if node.kind == "password" and any(label in value for label in ("确定", "确认")):
            return [UiNode(self, "确定", self._confirm_password)]
        if node.kind == "cancel_dialog" and any(label in value for label in ("确定", "确认取消")):
            return [UiNode(self, "确定", self._confirm_cancel)]
        return []


def bind(page, order_number="NEW-1234"):
    page._shipping_order_number = order_number
    page._shipping_order_submitted = True
    return page


def test_submit_requires_a_new_dedicated_order_identity_after_transition():
    driver = OrderDriver(screen="checkout", order_number=None)

    with pytest.raises(AssertionError, match="订单号|订单身份"):
        ShippingPage(driver).submit_order_once()

    assert driver.clicks.count("提交订单") == 1


def test_cod_option_decoy_cannot_be_terminal_success_when_confirmation_is_noop():
    driver = OrderDriver(screen="payment")
    driver.payment_confirm_responsive = False
    page = bind(ShippingPage(driver))

    with pytest.raises(AssertionError, match="支付结果|订单详情"):
        page.confirm_cash_on_delivery()


def test_balance_option_decoy_cannot_be_paid_when_password_confirmation_is_noop():
    driver = OrderDriver(screen="payment")
    driver.password_confirm_responsive = False
    page = bind(ShippingPage(driver))

    with pytest.raises(AssertionError, match="支付结果|订单详情"):
        page.pay_balance("safe-password")


def test_status_comes_only_from_dedicated_node_in_exact_order_detail():
    driver = OrderDriver(screen="order_detail", status="已支付")
    page = bind(ShippingPage(driver))

    assert page.current_payment_state() is OrderPaymentState.PAID

    driver.screen = "payment"
    assert page.current_payment_state() is OrderPaymentState.UNKNOWN


def test_wrong_order_detail_never_uses_its_status_or_cancel_action():
    driver = OrderDriver(
        screen="order_detail",
        order_number="NEW-1234",
        detail_order_number="OLD-9999",
        status="待支付",
    )
    driver.detail_decoys = False
    page = bind(ShippingPage(driver), "NEW-1234")

    assert page.current_payment_state() is OrderPaymentState.UNKNOWN
    assert page.cancel_pending_payment() is False
    assert driver.clicks == []


def test_multi_order_list_never_uses_global_first_cancel_action():
    driver = OrderDriver(screen="order_list", order_number="NEW-1234")
    driver.global_cancel_decoy = True
    page = bind(ShippingPage(driver), "NEW-1234")

    assert page.cancel_pending_payment() is False
    assert driver.clicks == []


def test_multiple_order_detail_roots_fail_closed_even_with_one_matching_identity():
    driver = OrderDriver(screen="order_detail", status="待支付")
    driver.detail_decoys = False
    driver.extra_detail_order_numbers = ["OLD-9999"]
    page = bind(ShippingPage(driver), "NEW-1234")

    assert page.current_payment_state() is OrderPaymentState.UNKNOWN
    assert page.cancel_pending_payment() is False
    assert driver.clicks == []


def test_multiple_payment_roots_cannot_select_a_method():
    driver = OrderDriver(screen="payment")
    driver.extra_payment_order_numbers = ["OLD-9999"]
    page = bind(ShippingPage(driver), "NEW-1234")

    with pytest.raises(AssertionError, match="支付页|订单身份"):
        page.confirm_cash_on_delivery()

    assert driver.clicks == []


@pytest.mark.parametrize("method", ("cod", "balance"))
def test_payment_method_actions_are_scoped_to_the_bound_payment_root(method):
    driver = OrderDriver(screen="payment")
    page = bind(ShippingPage(driver), "NEW-1234")

    if method == "cod":
        assert page.confirm_cash_on_delivery() is True
    else:
        assert page.pay_balance("safe-password") is True

    assert driver.global_payment_action_queries == 0


def test_unpaid_balance_flow_dismisses_password_modal_and_reaches_new_pending_detail():
    driver = OrderDriver(screen="payment")
    driver.password_background_pending = True
    page = bind(ShippingPage(driver))

    assert page.leave_balance_payment_unconfirmed() is True
    assert driver.screen == "order_detail"
    assert page.current_payment_state() is OrderPaymentState.PENDING
    assert "关闭" in driver.clicks


def test_unpaid_balance_flow_fails_if_dismiss_and_back_do_not_leave_password_modal():
    driver = OrderDriver(screen="payment")
    driver.password_background_pending = True
    driver.dismiss_responsive = False
    driver.back_responsive = False
    page = bind(ShippingPage(driver))

    with pytest.raises(AssertionError, match="密码|待支付订单详情"):
        page.leave_balance_payment_unconfirmed()

    assert driver.screen == "balance_password"
    assert "取消支付" not in driver.clicks


@pytest.mark.parametrize("cancel_result", ("加载中", "dialog_noop"))
def test_cancel_unknown_loading_or_stale_dialog_fails_closed(cancel_result):
    driver = OrderDriver(screen="order_detail", status="待支付")
    driver.detail_decoys = False
    driver.cancel_result = cancel_result
    page = bind(ShippingPage(driver))

    with pytest.raises(AssertionError, match="取消.*未确认|终态"):
        page.cancel_pending_payment()


@pytest.mark.parametrize("terminal", ("已取消", "已关闭", "不可支付"))
def test_cancel_accepts_only_explicit_terminal_state_for_same_order(terminal):
    driver = OrderDriver(screen="order_detail", status="待支付")
    driver.detail_decoys = False
    driver.cancel_result = terminal
    page = bind(ShippingPage(driver))

    assert page.cancel_pending_payment() is True
    assert page.current_payment_state().value in {"cancelled", "closed", "nonpayable"}


def test_paid_result_rejects_enabled_cancel_on_exact_paid_detail_without_clicking_it():
    driver = OrderDriver(screen="order_detail", status="已支付")
    driver.detail_decoys = False
    driver.cancel_enabled = True
    page = bind(ShippingPage(driver))

    with pytest.raises(AssertionError, match="取消支付"):
        page.assert_payment_result(PaymentMethod.BALANCE)

    assert "取消支付" not in driver.clicks


def test_business_evidence_logs_mask_identity_and_include_method_state_and_cancel(monkeypatch):
    messages = []
    monkeypatch.setattr(shipping_payment_module.logger, "info", lambda *args: messages.append(args))

    submit_driver = OrderDriver(screen="checkout", order_number="PRIVATE-1234")
    submit_page = ShippingPage(submit_driver)
    assert submit_page.submit_order_once() == "PRIVATE-1234"

    cod_driver = OrderDriver(screen="payment", order_number="PRIVATE-1234")
    cod_page = bind(ShippingPage(cod_driver), "PRIVATE-1234")
    assert cod_page.confirm_cash_on_delivery() is True

    cancel_driver = OrderDriver(screen="order_detail", order_number="PRIVATE-1234", status="待支付")
    cancel_driver.detail_decoys = False
    cancel_page = bind(ShippingPage(cancel_driver), "PRIVATE-1234")
    assert cancel_page.cancel_pending_payment() is True

    rendered = repr(messages)
    assert "PRIVATE-1234" not in rendered
    assert "***1234" in rendered
    assert "payment_method=cod" in rendered
    assert "state=cod" in rendered
    assert "cancel_result=success" in rendered


def _record_capture(monkeypatch):
    calls = []

    def capture(driver, stage, artifacts_dir, include_screenshot=True, redact_values=()):
        calls.append(
            SimpleNamespace(
                driver=driver,
                stage=stage,
                include_screenshot=include_screenshot,
                redact_values=tuple(redact_values),
            )
        )
        return SimpleNamespace(
            screenshot="artifact.png" if include_screenshot else None,
            page_source="artifact.xml",
        )

    monkeypatch.setattr(shipping_page_module, "capture_failure", capture)
    return calls


def test_navigation_failure_on_order_detail_derives_sensitive_xml_only_capture(monkeypatch):
    calls = _record_capture(monkeypatch)
    driver = OrderDriver(screen="order_detail", status="已支付")
    page = bind(ShippingPage(driver))

    assert page.switch_to_shipping_home() is False
    assert calls[-1].include_screenshot is False


def test_root_only_order_context_still_derives_sensitive_xml_only_capture(monkeypatch):
    calls = _record_capture(monkeypatch)
    driver = OrderDriver(screen="order_detail", status="已支付")
    driver.page_source_override = ""
    page = bind(ShippingPage(driver))
    monkeypatch.setattr(page, "page_blob", lambda: "")

    page.capture_shipping_failure("root_only_order_probe")

    assert calls[-1].include_screenshot is False


def test_demonstrably_nonsensitive_home_failure_retains_screenshot(monkeypatch):
    calls = _record_capture(monkeypatch)
    driver = NavigationDriver("app_home")

    ShippingPage(driver).capture_shipping_failure("home_probe")

    assert calls[-1].include_screenshot is True


def test_unknown_unverified_page_context_defaults_to_xml_only(monkeypatch):
    calls = _record_capture(monkeypatch)
    driver = NavigationDriver("wrong_page")

    ShippingPage(driver).capture_shipping_failure("unknown_page_probe")

    assert calls[-1].include_screenshot is False


def test_explicit_pii_is_removed_from_artifact_stage_and_logged_paths(monkeypatch):
    calls = _record_capture(monkeypatch)
    logged = []
    monkeypatch.setattr(shipping_page_module.logger, "error", lambda *args: logged.append(args))
    secret_name = 'Private & <Name> "Q"\'S'
    secret_detail = 'Unit & <One> "Two"\'Three\''
    secret_match = 'Match & <M> "D"\'E\''
    secret_password = 'pw&<>"\''
    driver = OrderDriver(screen="order_detail", status="已支付")

    ShippingPage(driver).capture_shipping_failure(
        f"order failure {secret_name} password={secret_password}",
        redact_values=(secret_name, secret_detail, secret_match, secret_password),
    )

    rendered = repr((calls[-1].stage, logged))
    for fragment in ("private", "name", "unit", "match", secret_password):
        assert fragment.lower() not in rendered.lower()
