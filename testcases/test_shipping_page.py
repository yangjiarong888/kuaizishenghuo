import re
from datetime import date
from types import SimpleNamespace

import pytest

import commons.diagnostics as diagnostics_module
import pages.shipping_address_mixin as shipping_address_mixin_module
import pages.shipping_page as shipping_page_module

from pages.shipping_page import ShippingPage
from pages.shipping_types import (
    AddressData,
    AddressPolicy,
    OrderPaymentState,
    PaymentMethod,
)


class FakeElement:
    def __init__(
        self,
        driver,
        text="",
        on_click=None,
        *,
        enabled=True,
        clickable="true",
        content_desc="",
        attributes=None,
    ):
        self.driver = driver
        self.text = text
        self.on_click = on_click
        self.enabled = enabled
        self.clickable = clickable
        self.content_desc = content_desc
        self.attributes = attributes or {}

    def is_displayed(self):
        return True

    def is_enabled(self):
        return self.enabled

    def get_attribute(self, name):
        values = {
            "text": self.text,
            "content-desc": self.content_desc,
            "enabled": "true" if self.enabled else "false",
            "clickable": self.clickable,
        }
        return self.attributes.get(name, values.get(name, ""))

    def click(self):
        self.driver.clicks.append(self.text)
        if self.on_click:
            self.on_click()


class FakePaymentField(FakeElement):
    def send_keys(self, value):
        self.driver.sent_values.append(value)
        if self.driver.password_send_mutates_page:
            self.driver.page_source = f"支付密码 {value}"
        if self.driver.password_send_raises:
            raise RuntimeError("input interrupted")


class FakePackageContainer(FakeElement):
    def __init__(self, driver, text, action_label="", on_action=None, *, resource_id):
        super().__init__(
            driver,
            text,
            attributes={"resource-id": resource_id},
        )
        self.action_label = action_label
        self.on_action = on_action

    def find_elements(self, by, value):
        if self.action_label and self.action_label in value:
            return [FakeElement(self.driver, self.action_label, self.on_action)]
        return []


class FakeShippingDriver:
    def __init__(self):
        self._page_source = ""
        self.screen = "app_home"
        self.clicks = []
        self.page_source = "筷子生活 首页 国际货运"
        self.current_activity = "com.bs.feifubao.MainActivity"
        self.entry_action = self._show_shipping_home
        self.delivery_action = self._show_delivery_orders
        self.home_action = self._show_shipping_home
        self.entry_available = True
        self.delivery_available = True
        self.home_available = True
        self.delivery_slots = []
        self.delivery_date_controls = []
        self.delivery_time_controls = []
        self.delayed_time_controls = []
        self.time_slots_visible_after_checks = None
        self.time_slot_checks = 0
        self.unrelated_picker_elements = []
        self.pending_delivery_slot = ""
        self.checkout_delivery_text = ""
        self.confirm_available = True
        self.confirm_responsive = True
        self.auto_close_after_checks = None
        self.auto_close_checks = 0
        self.keep_submit_button_visible = False
        self.sent_values = []
        self.password_field_available = True
        self.decoy_edit_text_available = False
        self.password_send_mutates_page = False
        self.password_send_raises = False
        self.balance_payment_completes = True

    @property
    def page_source(self):
        if (
            self.screen == "delivery_picker"
            and self.pending_delivery_slot
            and self.auto_close_after_checks is not None
        ):
            self.auto_close_checks += 1
            if self.auto_close_checks >= self.auto_close_after_checks:
                self._confirm_delivery_slot()
        return self._page_source

    @page_source.setter
    def page_source(self, value):
        self._page_source = value

    @classmethod
    def with_delivery_dates(cls, labels, disabled_labels=(), time_ranges=()):
        driver = cls()
        driver.screen = "checkout"
        driver.page_source = "提交订单 预约配送"
        disabled = set(disabled_labels)
        for label in labels:
            element = FakeElement(
                driver,
                label,
                lambda selected=label: driver._select_delivery_slot(selected),
                enabled=label not in disabled,
                clickable="true" if label not in disabled else "false",
                attributes={
                    "class": "disabled" if label in disabled else "",
                    "resource-id": "shipping_delivery_slot",
                },
            )
            if cls._is_time_range(label):
                driver.delivery_time_controls.append(element)
            elif cls._is_combined_slot(label):
                driver.delivery_slots.append(element)
            else:
                driver.delivery_date_controls.append(element)
        driver.delivery_time_controls.extend(
            FakeElement(
                driver,
                label,
                lambda selected=label: driver._select_delivery_slot(selected),
                attributes={"resource-id": "shipping_delivery_slot"},
            )
            for label in time_ranges
        )
        return driver

    @classmethod
    def with_checkout_delivery_text(cls, label):
        driver = cls()
        driver.screen = "checkout"
        driver.checkout_delivery_text = label
        driver.page_source = f"提交订单 预约配送 {label}"
        return driver

    @classmethod
    def on_submit_page(cls):
        driver = cls()
        driver.screen = "checkout"
        driver.page_source = "提交订单 已选择地址 明天 19:15-19:45"
        return driver

    @classmethod
    def on_payment_page(cls):
        driver = cls()
        driver._show_payment_page()
        return driver

    @classmethod
    def on_order_detail(cls, payment_status):
        driver = cls()
        driver.screen = "order_detail"
        driver.payment_status = payment_status
        driver.page_source = f"订单详情 {payment_status}"
        return driver

    @staticmethod
    def _is_time_range(label):
        return bool(re.search(r"\d{2}:\d{2}\s*-\s*\d{2}:\d{2}", label)) and not any(
            marker in label for marker in ("今天", "明天", "后天", "月")
        )

    @classmethod
    def _is_combined_slot(cls, label):
        return cls._is_time_range(label) is False and bool(
            re.search(r"\d{2}:\d{2}\s*-\s*\d{2}:\d{2}", label)
        )

    @staticmethod
    def _text_selector(label):
        return f'//*[@text="{label}" or @content-desc="{label}"]'

    def find_elements(self, by, value):
        if (
            (self.screen == "checkout" or self.keep_submit_button_visible)
            and value == self._text_selector("提交订单")
        ):
            return [FakeElement(self, "提交订单", self._show_payment_page)]
        if self.screen == "payment" and value == self._text_selector("余额支付"):
            return [FakeElement(self, "余额支付", self._select_balance)]
        if self.screen == "payment" and value == self._text_selector("余额"):
            return [FakeElement(self, "余额", self._select_balance)]
        if self.screen == "payment" and value == self._text_selector("货到付款"):
            return [FakeElement(self, "货到付款", self._select_cod)]
        if self.screen == "payment" and value in {
            self._text_selector("确认支付"),
            self._text_selector("立即支付"),
            self._text_selector("确认选择"),
            self._text_selector("确定"),
            self._text_selector("确认"),
        }:
            return [FakeElement(self, "确认支付", self._confirm_payment_selection)]
        if self.screen == "balance_password" and "android.widget.EditText" in value:
            if "|//android.widget.EditText" in value and self.decoy_edit_text_available:
                return [FakePaymentField(self, "备注")]
            if self.password_field_available:
                return [
                    FakePaymentField(
                        self,
                        "支付密码",
                        attributes={"resource-id": "shipping_payment_password"},
                    )
                ]
            return []
        if self.screen == "balance_password" and value in {
            self._text_selector("确定"),
            self._text_selector("确认"),
        }:
            return [FakeElement(self, "确定", self._complete_balance_payment)]
        if self.screen == "order_detail" and value == self._text_selector("取消支付"):
            if self.payment_status == "待支付":
                return [FakeElement(self, "取消支付", self._show_cancel_confirmation)]
        if self.screen == "cancel_confirmation" and value in {
            self._text_selector("确定"),
            self._text_selector("确认取消"),
        }:
            return [FakeElement(self, "确定", self._cancel_payment)]
        if self.screen == "checkout" and value == self._text_selector("预约配送"):
            return [FakeElement(self, "预约配送", self._show_delivery_picker)]
        if self.screen == "delivery_picker" and self.confirm_available and value in {
            self._text_selector("确定"),
            self._text_selector("确认"),
        }:
            action = self._confirm_delivery_slot if self.confirm_responsive else None
            return [FakeElement(self, "确定", action)]
        if self.screen == "delivery_picker" and value == "//*[@text or @content-desc]":
            return (
                self.unrelated_picker_elements
                + self.delivery_slots
                + self.delivery_date_controls
                + self.delivery_time_controls
            )
        if self.screen == "delivery_picker" and "resource-id" in value:
            time_controls = self.delivery_time_controls
            if self.pending_delivery_slot and self.delayed_time_controls:
                self.time_slot_checks += 1
                if self.time_slot_checks >= self.time_slots_visible_after_checks:
                    time_controls = time_controls + self.delayed_time_controls
            return self.delivery_slots + self.delivery_date_controls + time_controls
        if self.screen == "checkout" and "resource-id" in value and self.checkout_delivery_text:
            return [
                FakeElement(
                    self,
                    self.checkout_delivery_text,
                    attributes={"resource-id": "shipping_delivery_time"},
                )
            ]
        if (
            self.screen == "app_home"
            and self.entry_available
            and value == self._text_selector("国际货运")
        ):
            return [FakeElement(self, "国际货运", self.entry_action)]
        if (
            self.screen == "shipping_home"
            and self.delivery_available
            and value == self._text_selector("配送订单")
        ):
            return [FakeElement(self, "配送订单", self.delivery_action)]
        if self.screen == "delivery_orders" and self.home_available and value in {
            self._text_selector("国际货运"),
            self._text_selector("首页"),
        }:
            return [FakeElement(self, "首页", self.home_action)]
        return []

    def _show_delivery_picker(self):
        self.screen = "delivery_picker"
        self.page_source = "选择配送时间 " + " ".join(
            slot.text
            for slot in (
                self.unrelated_picker_elements
                + self.delivery_slots
                + self.delivery_date_controls
                + self.delivery_time_controls
            )
        )

    def _show_payment_page(self):
        self.screen = "payment"
        self.selected_payment_method = ""
        self.page_source = "支付方式"

    def _select_balance(self):
        self.selected_payment_method = "balance"

    def _select_cod(self):
        self.selected_payment_method = "cod"

    def _confirm_payment_selection(self):
        if self.selected_payment_method == "balance":
            self.screen = "balance_password"
            self.page_source = "请输入支付密码"
        elif self.selected_payment_method == "cod":
            self.screen = "order_detail"
            self.payment_status = "货到付款"
            self.page_source = "订单详情 货到付款"

    def _complete_balance_payment(self):
        if not self.balance_payment_completes:
            return
        self.screen = "order_detail"
        self.payment_status = "已支付"
        self.page_source = "订单详情 已支付"

    def _show_cancel_confirmation(self):
        self.screen = "cancel_confirmation"
        self.page_source = "确认取消支付"

    def _cancel_payment(self):
        self.screen = "order_detail"
        self.payment_status = "已取消"
        self.page_source = "订单详情 已取消"

    def _select_delivery_slot(self, label):
        if self._is_time_range(label) and self.pending_delivery_slot:
            self.pending_delivery_slot = f"{self.pending_delivery_slot} {label}"
        else:
            self.pending_delivery_slot = label

    def _confirm_delivery_slot(self):
        self.screen = "checkout"
        self.checkout_delivery_text = self.pending_delivery_slot
        self.page_source = f"提交订单 预约配送 {self.checkout_delivery_text}"

    def _show_shipping_home(self):
        self.screen = "shipping_home"
        self.page_source = "国际货运 寄件菲律宾 寄件全球 配送订单"

    def _show_delivery_orders(self):
        self.screen = "delivery_orders"
        self.page_source = "配送订单 全部 待付款 待收货 已完成 已取消"


class FakePackageShippingDriver(FakeShippingDriver):
    def __init__(self, package_containers=(), history_decoys=()):
        super().__init__()
        self.screen = "delivery_orders"
        self.package_containers = list(package_containers)
        self.history_decoys = list(history_decoys)
        self.page_source = "配送订单 全部"

    def _show_package_checkout(self):
        self.screen = "checkout"
        self.page_source = "提交订单 请选择收货地址"

    def find_elements(self, by, value):
        if value == "//*[@text or @content-desc]":
            return self.history_decoys
        if "shipping_package_card" in value:
            return self.package_containers
        return super().find_elements(by, value)


class FakeAddressElement(FakeElement):
    def __init__(self, driver, text="", on_click=None, content_desc=""):
        super().__init__(driver, text, on_click)
        self.content_desc = content_desc

    def get_attribute(self, name):
        if name == "text":
            return self.text
        if name == "content-desc":
            return self.content_desc
        return ""


class FakeAddressField(FakeAddressElement):
    def __init__(self, driver, field):
        super().__init__(driver, field)
        self.field = field

    def clear(self):
        self.driver.address_form_values[self.field] = ""

    def send_keys(self, value):
        self.driver.address_form_values[self.field] = value


class FakeAddressShippingDriver(FakeShippingDriver):
    """A small address-book model that exposes only public UI interactions."""

    FIELD_LABELS = {
        "name": "联系人",
        "phone": "手机号码",
        "detail": "详细地址",
        "postcode": "邮政编码",
    }

    def __init__(self, address_book=()):
        super().__init__()
        self.screen = "checkout"
        self.address_book = list(address_book)
        self.selected_address = ""
        self.address_form_values = {}
        self.save_applies_directly = False
        self.address_searches = 0
        self.page_source = "提交订单 请选择收货地址"

    @classmethod
    def with_address_book(cls, address_book):
        return cls(address_book)

    def _show_address_book(self):
        self.screen = "address_book"
        self.page_source = "选择收货地址 新增地址 " + " ".join(self.address_book)

    def _show_address_form(self):
        self.screen = "address_form"
        self.page_source = "新增地址 联系人 手机号码 国家 城市 详细地址 邮政编码 保存"

    def _select_address(self, address):
        self.selected_address = address
        self.screen = "checkout"
        self.page_source = "提交订单 收货地址 " + address

    def _save_address(self):
        values = self.address_form_values
        address = "{name} {phone} {city} {detail}".format(
            name=values.get("name", ""),
            phone=values.get("phone", ""),
            city=values.get("city", ""),
            detail=values.get("detail", ""),
        ).strip()
        self.address_book.append(address)
        if self.save_applies_directly:
            self._select_address(address)
        else:
            self._show_address_book()

    def find_elements(self, by, value):
        exact_labels = {
            self._text_selector("请选择收货地址"): FakeAddressElement(
                self, "请选择收货地址", self._show_address_book
            ),
            self._text_selector("收货地址"): FakeAddressElement(
                self, "收货地址", self._show_address_book
            ),
            self._text_selector("配送地址"): FakeAddressElement(
                self, "配送地址", self._show_address_book
            ),
            self._text_selector("新增地址"): FakeAddressElement(
                self, "新增地址", self._show_address_form
            ),
            self._text_selector("添加地址"): FakeAddressElement(
                self, "添加地址", self._show_address_form
            ),
            self._text_selector("保存"): FakeAddressElement(self, "保存", self._save_address),
            self._text_selector("菲律宾"): FakeAddressElement(
                self,
                "菲律宾",
                lambda: self.address_form_values.__setitem__("country", "菲律宾"),
            ),
            self._text_selector("Manila"): FakeAddressElement(
                self,
                "Manila",
                lambda: self.address_form_values.__setitem__("city", "Manila"),
            ),
        }
        if value in exact_labels:
            element = exact_labels[value]
            if self.screen == "checkout" and element.text in {"请选择收货地址", "收货地址", "配送地址"}:
                return [element]
            if self.screen == "address_book" and element.text in {"新增地址", "添加地址"}:
                return [element]
            if self.screen == "address_form" and element.text in {"保存", "菲律宾", "Manila"}:
                return [element]
            return []
        if self.screen == "address_book" and "contains(@text" in value:
            self.address_searches += 1
            requested = re.findall(r'contains\(@(?:text|content-desc),"([^"]+)"\)', value)
            return [
                FakeAddressElement(self, address, lambda a=address: self._select_address(a))
                for address in self.address_book
                if any(match in address for match in requested)
            ]
        if self.screen == "address_form":
            for field, label in self.FIELD_LABELS.items():
                if label in value:
                    return [FakeAddressField(self, field)]
        return super().find_elements(by, value)


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


def test_device_today_uses_appium_device_clock():
    driver = FakeShippingDriver()
    driver.get_device_time = lambda: "2026-08-10T21:30:00+08:00"

    assert ShippingPage(driver).device_today() == date(2026, 8, 10)


def test_device_today_fails_closed_when_clock_is_unavailable():
    driver = FakeShippingDriver()
    driver.get_device_time = lambda: (_ for _ in ()).throw(RuntimeError("offline"))

    with pytest.raises(AssertionError, match="无法读取设备日期"):
        ShippingPage(driver).device_today()


def test_delivery_picker_selects_earliest_future_not_today():
    driver = FakeShippingDriver.with_delivery_dates(
        ["今天 19:15-19:45", "8月12日 20:15-20:45", "明天 19:45-20:15"]
    )

    selected = ShippingPage(driver).select_earliest_future_delivery(today=date(2026, 8, 10))

    assert selected == date(2026, 8, 11)
    assert "明天 19:45-20:15" in driver.clicks
    assert "今天 19:15-19:45" not in driver.clicks


def test_delivery_picker_rejects_disabled_earlier_future_slot():
    driver = FakeShippingDriver.with_delivery_dates(
        ["明天 19:15-19:45", "后天 19:45-20:15"], disabled_labels={"明天 19:15-19:45"}
    )

    selected = ShippingPage(driver).select_earliest_future_delivery(today=date(2026, 8, 10))

    assert selected == date(2026, 8, 12)
    assert "后天 19:45-20:15" in driver.clicks
    assert "明天 19:15-19:45" not in driver.clicks


def test_delivery_picker_rejects_boolean_false_clickable_slot():
    driver = FakeShippingDriver.with_delivery_dates(
        ["明天 19:15-19:45", "后天 19:45-20:15"]
    )
    driver.delivery_slots[0].clickable = False

    selected = ShippingPage(driver).select_earliest_future_delivery(today=date(2026, 8, 10))

    assert selected == date(2026, 8, 12)
    assert "后天 19:45-20:15" in driver.clicks
    assert "明天 19:15-19:45" not in driver.clicks


def test_delivery_picker_ignores_unrelated_date_bearing_picker_control():
    driver = FakeShippingDriver.with_delivery_dates(["后天 19:45-20:15"])
    driver.unrelated_picker_elements = [
        FakeElement(
            driver,
            "明天 08:00-08:30",
            lambda: driver._select_delivery_slot("明天 08:00-08:30"),
            attributes={"resource-id": "calendar_event_date"},
        )
    ]

    selected = ShippingPage(driver).select_earliest_future_delivery(today=date(2026, 8, 10))

    assert selected == date(2026, 8, 12)
    assert "后天 19:45-20:15" in driver.clicks
    assert "明天 08:00-08:30" not in driver.clicks


def test_delivery_picker_rejects_visible_full_slot_marker():
    driver = FakeShippingDriver.with_delivery_dates(
        ["明天 已满 19:15-19:45", "后天 19:45-20:15"]
    )

    selected = ShippingPage(driver).select_earliest_future_delivery(today=date(2026, 8, 10))

    assert selected == date(2026, 8, 12)
    assert "后天 19:45-20:15" in driver.clicks
    assert "明天 已满 19:15-19:45" not in driver.clicks


def test_delivery_picker_selects_date_then_first_enabled_time_range():
    driver = FakeShippingDriver.with_delivery_dates(
        ["今天", "明天"], time_ranges=["19:15-19:45", "20:15-20:45"]
    )

    selected = ShippingPage(driver).select_earliest_future_delivery(today=date(2026, 8, 10))

    assert selected == date(2026, 8, 11)
    assert "明天" in driver.clicks
    assert "19:15-19:45" in driver.clicks


def test_delivery_picker_waits_for_time_range_after_date_selection():
    driver = FakeShippingDriver.with_delivery_dates(["明天"])
    driver.delayed_time_controls = [
        FakeElement(
            driver,
            "19:15-19:45",
            lambda: driver._select_delivery_slot("19:15-19:45"),
            attributes={"resource-id": "shipping_delivery_slot"},
        )
    ]
    driver.time_slots_visible_after_checks = 2

    selected = ShippingPage(driver).select_earliest_future_delivery(today=date(2026, 8, 10))

    assert selected == date(2026, 8, 11)
    assert "19:15-19:45" in driver.clicks
    assert driver.time_slot_checks >= 2


def test_delivery_picker_waits_for_delayed_auto_close_before_confirming():
    driver = FakeShippingDriver.with_delivery_dates(["明天 19:15-19:45"])
    driver.confirm_available = False
    driver.auto_close_after_checks = 3

    selected = ShippingPage(driver).select_earliest_future_delivery(today=date(2026, 8, 10))

    assert selected == date(2026, 8, 11)
    assert driver.screen == "checkout"
    assert driver.auto_close_checks >= 3


@pytest.mark.parametrize(
    ("confirm_available", "confirm_responsive"), [(False, True), (True, False)]
)
def test_delivery_picker_fails_without_a_confirmed_checkout_transition(
    confirm_available, confirm_responsive
):
    driver = FakeShippingDriver.with_delivery_dates(["明天 19:15-19:45"])
    driver.confirm_available = confirm_available
    driver.confirm_responsive = confirm_responsive

    with pytest.raises(AssertionError, match="确认|提交订单"):
        ShippingPage(driver).select_earliest_future_delivery(today=date(2026, 8, 10))


def test_delivery_readback_rejects_today_after_picker_click():
    driver = FakeShippingDriver.with_checkout_delivery_text("8月10日 19:15-19:45")

    with pytest.raises(AssertionError, match="严格晚于今天"):
        ShippingPage(driver).verify_selected_delivery_date(
            date(2026, 8, 10), date(2026, 8, 10)
        )


def test_delivery_readback_rejects_unparseable_text():
    driver = FakeShippingDriver.with_checkout_delivery_text("已预约")

    with pytest.raises(AssertionError, match="无法解析"):
        ShippingPage(driver).verify_selected_delivery_date(
            date(2026, 8, 11), date(2026, 8, 10)
        )


def test_delivery_readback_uses_checkout_field_instead_of_page_source():
    driver = FakeShippingDriver.with_checkout_delivery_text("明天 19:15-19:45")
    driver.page_source = "提交订单 预约配送 今天 09:00-09:30"

    assert ShippingPage(driver).verify_selected_delivery_date(
        date(2026, 8, 11), date(2026, 8, 10)
    ) is True


def test_existing_policy_requires_match_before_clicking():
    driver = FakeAddressShippingDriver()
    page = ShippingPage(driver)

    with pytest.raises(ValueError, match="SHIPPING_ADDRESS_MATCH"):
        page.ensure_shipping_address(AddressPolicy.EXISTING, AddressData())

    assert driver.clicks == []


def test_add_policy_requires_complete_fields_before_clicking():
    driver = FakeAddressShippingDriver()
    page = ShippingPage(driver)

    with pytest.raises(ValueError, match="phone,country,city,detail,postcode"):
        page.ensure_shipping_address(AddressPolicy.ADD, AddressData(name="Tester"))

    assert driver.clicks == []


def test_auto_selects_matching_existing_address_without_adding():
    driver = FakeAddressShippingDriver.with_address_book(["Tester +63******0994 Manila"])
    page = ShippingPage(driver)

    assert page.ensure_shipping_address(AddressPolicy.AUTO, complete_address()) is True
    assert "新增地址" not in driver.clicks
    assert driver.selected_address == "Tester +63******0994 Manila"


def test_auto_adds_when_matching_address_is_absent():
    driver = FakeAddressShippingDriver.with_address_book(["Other +63******0000 Cebu"])
    page = ShippingPage(driver)
    data = complete_address()

    assert page.ensure_shipping_address(AddressPolicy.AUTO, data) is True
    assert "新增地址" in driver.clicks
    assert driver.address_form_values["phone"] == "+639621170994"


def test_public_add_rejects_incomplete_data_before_clicking_address_form():
    driver = FakeAddressShippingDriver()

    with pytest.raises(ValueError, match="phone,country,city,detail,postcode"):
        ShippingPage(driver).add_shipping_address(AddressData(name="Tester"))

    assert driver.clicks == []


def test_auto_verifies_an_address_saved_directly_to_checkout_without_reselecting():
    driver = FakeAddressShippingDriver.with_address_book(["Other +63******0000 Cebu"])
    driver.save_applies_directly = True

    assert ShippingPage(driver).ensure_shipping_address(AddressPolicy.AUTO, complete_address()) is True
    assert driver.selected_address.endswith("Manila 100 Test Street")
    assert driver.address_searches == 4


def test_address_form_failures_capture_sensitive_diagnostics(monkeypatch):
    driver = FakeAddressShippingDriver()
    page = ShippingPage(driver)
    calls = []
    monkeypatch.setattr(
        page,
        "capture_shipping_failure",
        lambda stage, sensitive=False, redact_values=(): calls.append(
            (stage, sensitive, redact_values)
        ),
    )

    with pytest.raises(AssertionError, match="未找到国家"):
        page.ensure_shipping_address(
            AddressPolicy.ADD, complete_address(country="不存在的国家")
        )

    assert calls == [
        (
            "shipping_address_country_missing",
            True,
            (
                "0994",
                "Tester",
                "+639621170994",
                "不存在的国家",
                "Manila",
                "100 Test Street",
                "1000",
            ),
        )
    ]


def test_applied_address_logs_a_masked_phone_without_detail(monkeypatch):
    driver = FakeAddressShippingDriver.with_address_book(["Tester +63******0994 Manila"])
    messages = []
    monkeypatch.setattr(shipping_address_mixin_module.logger, "info", lambda *args: messages.append(args))

    assert ShippingPage(driver).ensure_shipping_address(AddressPolicy.AUTO, complete_address()) is True

    rendered = repr(messages)
    assert "+639621170994" not in rendered
    assert "100 Test Street" not in rendered
    assert "******0994" in rendered


def _record_capture(monkeypatch):
    class CaptureCalls(list):
        artifacts = []

    calls = CaptureCalls()

    def capture(driver, stage, artifacts_dir, include_screenshot=True, redact_values=()):
        calls.append((driver, stage, artifacts_dir, include_screenshot))
        artifacts = SimpleNamespace(
            screenshot=f"artifacts/{stage}.png" if include_screenshot else None,
            page_source=f"artifacts/{stage}.xml",
        )
        calls.artifacts.append(artifacts)
        return artifacts

    monkeypatch.setattr(shipping_page_module, "capture_failure", capture)
    return calls


def test_enter_from_app_home_clicks_international_shipping():
    driver = FakeShippingDriver()

    assert ShippingPage(driver).enter_from_app_home() is True
    assert driver.clicks == ["国际货运"]
    assert driver.screen == "shipping_home"


def test_shipping_tabs_switch_both_directions():
    driver = FakeShippingDriver()
    driver._show_shipping_home()
    page = ShippingPage(driver)

    assert page.switch_to_delivery_orders() is True
    assert driver.screen == "delivery_orders"
    assert page.switch_to_shipping_home() is True
    assert driver.screen == "shipping_home"


def test_submit_order_clicks_once_even_if_button_remains_visible():
    driver = FakeShippingDriver.on_submit_page()
    driver.keep_submit_button_visible = True
    page = ShippingPage(driver)

    page.submit_order_once()
    page.submit_order_once()

    assert driver.clicks.count("提交订单") == 1


def test_balance_payment_requires_password_before_typing():
    driver = FakeShippingDriver.on_payment_page()

    with pytest.raises(ValueError, match="SHIPPING_PAY_PASSWORD"):
        ShippingPage(driver).pay_balance("")

    assert driver.sent_values == []


def test_paid_order_never_clicks_cancel_payment():
    driver = FakeShippingDriver.on_order_detail("已支付")
    page = ShippingPage(driver)

    assert page.current_payment_state() is OrderPaymentState.PAID
    assert page.cancel_pending_payment() is False
    assert "取消支付" not in driver.clicks


def test_pending_order_can_cancel_payment_and_verify_result():
    driver = FakeShippingDriver.on_order_detail("待支付")
    page = ShippingPage(driver)

    assert page.cancel_pending_payment() is True
    assert driver.clicks[-2:] == ["取消支付", "确定"]
    assert page.current_payment_state() is not OrderPaymentState.PENDING


def test_cod_does_not_type_password_or_cancel_payment():
    driver = FakeShippingDriver.on_payment_page()
    page = ShippingPage(driver)

    assert page.confirm_cash_on_delivery() is True
    assert driver.sent_values == []
    assert "取消支付" not in driver.clicks


def test_balance_payment_enters_password_only_in_explicit_password_field():
    driver = FakeShippingDriver.on_payment_page()

    assert ShippingPage(driver).pay_balance("safe-password") is True
    assert driver.sent_values == ["safe-password"]
    assert driver.payment_status == "已支付"


def test_balance_payment_rejects_decoy_edit_text_without_typing_password():
    driver = FakeShippingDriver.on_payment_page()
    driver.password_field_available = False
    driver.decoy_edit_text_available = True

    with pytest.raises(AssertionError, match="支付密码弹窗未找到输入框"):
        ShippingPage(driver).pay_balance("safe-password")

    assert driver.sent_values == []


def test_password_input_exception_redacts_password_from_xml_artifacts_and_logs(
    monkeypatch, tmp_path
):
    driver = FakeShippingDriver.on_payment_page()
    driver.password_send_mutates_page = True
    driver.password_send_raises = True
    logged = []
    captured_stages = []
    artifacts = []
    monkeypatch.setattr(shipping_page_module.AppConfig, "ARTIFACTS_DIR", str(tmp_path))
    monkeypatch.setattr(
        shipping_page_module.logger, "error", lambda *args: logged.append(args)
    )

    def capture_with_stage(*args, **kwargs):
        captured_stages.append(args[1])
        artifact = diagnostics_module.capture_failure(*args, **kwargs)
        artifacts.append(artifact)
        return artifact

    monkeypatch.setattr(shipping_page_module, "capture_failure", capture_with_stage)

    with pytest.raises(AssertionError, match="支付密码输入失败"):
        ShippingPage(driver).pay_balance("input-secret")

    artifact_paths = tuple(tmp_path.iterdir())
    assert len(artifact_paths) == 1
    assert artifact_paths[0].suffix == ".xml"
    assert "input-secret" not in artifact_paths[0].read_text(encoding="utf-8")
    assert "input-secret" not in artifact_paths[0].name
    assert "input-secret" not in repr(captured_stages)
    assert "input-secret" not in repr(logged)
    assert artifacts[0].screenshot is None
    assert not list(tmp_path.glob("*.png"))


def test_balance_result_timeout_redacts_entered_password_from_diagnostics(
    monkeypatch, tmp_path
):
    driver = FakeShippingDriver.on_payment_page()
    driver.password_send_mutates_page = True
    driver.balance_payment_completes = False
    logged = []
    artifacts = []
    monkeypatch.setattr(shipping_page_module.AppConfig, "ARTIFACTS_DIR", str(tmp_path))
    monkeypatch.setattr(shipping_page_module.AppConfig, "WAIT_TIMEOUT", 0)
    monkeypatch.setattr(
        shipping_page_module.logger, "error", lambda *args: logged.append(args)
    )

    def capture_artifact(*args, **kwargs):
        artifact = diagnostics_module.capture_failure(*args, **kwargs)
        artifacts.append(artifact)
        return artifact

    monkeypatch.setattr(shipping_page_module, "capture_failure", capture_artifact)

    with pytest.raises(AssertionError, match="支付结果未确认"):
        ShippingPage(driver).pay_balance("result-secret")

    artifact_paths = tuple(tmp_path.iterdir())
    assert len(artifact_paths) == 1
    assert "result-secret" not in artifact_paths[0].read_text(encoding="utf-8")
    assert "result-secret" not in artifact_paths[0].name
    assert "result-secret" not in repr(logged)
    assert artifacts[0].screenshot is None
    assert not list(tmp_path.glob("*.png"))


def test_open_first_deliverable_package_clicks_eligible_package_action_and_enters_checkout():
    driver = FakePackageShippingDriver()
    driver.package_containers = [
        FakePackageContainer(
            driver,
            "历史订单 包裹 X 可配送",
            "立即寄件",
            driver._show_package_checkout,
            resource_id="shipping_package_card",
        ),
        FakePackageContainer(
            driver,
            "包裹 A 可配送",
            "去寄件",
            driver._show_package_checkout,
            resource_id="shipping_package_card",
        )
    ]
    driver.history_decoys = [FakeElement(driver, "历史订单 可配送")]

    assert ShippingPage(driver).open_first_deliverable_package() is True
    assert driver.clicks == ["去寄件"]
    assert driver.screen == "checkout"


def test_open_first_deliverable_package_rejects_history_status_decoy():
    driver = FakePackageShippingDriver()
    driver.history_decoys = [FakeElement(driver, "历史订单 可配送")]
    driver.package_containers = [
        FakePackageContainer(
            driver,
            "历史订单 包裹 X 可配送",
            "立即寄件",
            driver._show_package_checkout,
            resource_id="shipping_package_card",
        )
    ]

    with pytest.raises(AssertionError, match="可配送或可提交"):
        ShippingPage(driver).open_first_deliverable_package()

    assert driver.clicks == []


def test_open_first_deliverable_package_stops_after_first_action_without_checkout(
    monkeypatch
):
    driver = FakePackageShippingDriver()
    driver.package_containers = [
        FakePackageContainer(
            driver,
            "包裹 A 可配送",
            "立即寄件",
            resource_id="shipping_package_card",
        ),
        FakePackageContainer(
            driver,
            "包裹 B 可配送",
            "去寄件",
            driver._show_package_checkout,
            resource_id="shipping_package_card",
        ),
    ]
    monkeypatch.setattr(shipping_page_module.AppConfig, "WAIT_TIMEOUT", 0)

    with pytest.raises(AssertionError, match="未进入提交订单页"):
        ShippingPage(driver).open_first_deliverable_package()

    assert driver.clicks == ["立即寄件"]


@pytest.mark.parametrize("status", ("已支付 待付款", "货到付款 待支付"))
def test_ambiguous_order_status_never_clicks_cancel_payment(status):
    driver = FakeShippingDriver.on_order_detail(status)
    page = ShippingPage(driver)

    assert page.current_payment_state() is OrderPaymentState.UNKNOWN
    assert page.cancel_pending_payment() is False
    assert "取消支付" not in driver.clicks


def test_balance_payment_failure_redacts_password_from_sensitive_diagnostic(monkeypatch):
    driver = FakeShippingDriver.on_payment_page()
    page = ShippingPage(driver)
    captures = []
    original_click = page._click_text

    def click_without_password_confirmation(labels):
        if labels == ("确定", "确认"):
            return False
        return original_click(labels)

    monkeypatch.setattr(page, "_click_text", click_without_password_confirmation)
    monkeypatch.setattr(
        page,
        "capture_shipping_failure",
        lambda stage, sensitive=False, redact_values=(): captures.append(
            (stage, sensitive, redact_values)
        ),
    )

    with pytest.raises(AssertionError, match="支付页面未找到所需操作"):
        page.pay_balance("not-a-password")

    assert captures == [
        ("balance_password_confirm_missing", True, ("not-a-password",))
    ]


def test_run_order_flow_cancels_only_a_confirmed_pending_order(monkeypatch):
    driver = FakeShippingDriver.on_order_detail("待支付")
    page = ShippingPage(driver)
    events = []
    address = complete_address()

    monkeypatch.setattr(page, "enter_from_app_home", lambda: events.append("home") or True)
    monkeypatch.setattr(page, "switch_to_delivery_orders", lambda: events.append("orders") or True)
    monkeypatch.setattr(
        page, "open_first_deliverable_package", lambda: events.append("package") or True
    )
    monkeypatch.setattr(
        page, "ensure_shipping_address", lambda *_: events.append("address") or True
    )
    monkeypatch.setattr(
        page,
        "select_earliest_future_delivery",
        lambda: events.append("delivery") or date(2026, 8, 11),
    )
    monkeypatch.setattr(page, "verify_checkout_ready", lambda: events.append("ready") or True)
    monkeypatch.setattr(page, "submit_order_once", lambda: events.append("submit") or "ORDER-1")
    monkeypatch.setattr(
        page, "switch_to_shipping_home", lambda: events.append("return-home") or True
    )

    assert page.run_order_flow(
        payment_method=PaymentMethod.BALANCE,
        cancel_unpaid=True,
        pay_password="",
        address_policy=AddressPolicy.AUTO,
        address_data=address,
    ) is True
    assert events == [
        "home",
        "orders",
        "package",
        "address",
        "delivery",
        "ready",
        "submit",
        "return-home",
        "orders",
    ]
    assert driver.clicks[-2:] == ["取消支付", "确定"]


def test_navigation_failures_capture_non_sensitive_diagnostics(monkeypatch):
    monkeypatch.setattr(shipping_page_module.AppConfig, "WAIT_TIMEOUT", 0)
    calls = _record_capture(monkeypatch)
    driver = FakeShippingDriver()
    page = ShippingPage(driver)

    driver._show_shipping_home()
    driver.delivery_available = False
    assert page.switch_to_delivery_orders() is False
    driver.delivery_available = True
    driver.delivery_action = None
    assert page.switch_to_delivery_orders() is False

    driver._show_delivery_orders()
    driver.home_available = False
    assert page.switch_to_shipping_home() is False
    driver.home_available = True
    driver.home_action = None
    assert page.switch_to_shipping_home() is False

    assert [stage for _, stage, _, _ in calls] == [
        "shipping_delivery_tab_missing",
        "shipping_delivery_tab_timeout",
        "shipping_home_tab_missing",
        "shipping_home_tab_timeout",
    ]
    assert all(include_screenshot for *_, include_screenshot in calls)


def test_home_entry_click_exception_and_timeout_capture_failure(monkeypatch):
    monkeypatch.setattr(shipping_page_module.AppConfig, "WAIT_TIMEOUT", 0)
    calls = _record_capture(monkeypatch)
    driver = FakeShippingDriver()
    page = ShippingPage(driver)

    def raise_click_error():
        raise RuntimeError("password=do-not-log")

    driver.entry_action = raise_click_error
    assert page.enter_from_app_home() is False
    driver.entry_action = None
    assert page.enter_from_app_home() is False

    assert [stage for _, stage, _, _ in calls] == [
        "shipping_entry_click_failed",
        "shipping_entry_timeout",
    ]
    assert all(include_screenshot for *_, include_screenshot in calls)


@pytest.mark.parametrize(
    ("stage", "secret", "expected_stage"),
    [
        (
            "Payment Password=sup3rSecret/Retry",
            "sup3rSecret",
            "payment_password_redacted_retry",
        ),
        ("Login Token superToken/Retry", "superToken", "login_token_redacted_retry"),
        ("Order Secret: extraSecret/Retry", "extraSecret", "order_secret_redacted_retry"),
        (
            "Checkout Pay_Password=123456/Retry",
            "123456",
            "checkout_pay_password_redacted_retry",
        ),
        (
            "Refresh Access_Token:abc/Retry",
            "abc",
            "refresh_access_token_redacted_retry",
        ),
    ],
)
def test_capture_shipping_failure_redacts_stage_secrets_and_hides_sensitive_screenshots(
    monkeypatch, stage, secret, expected_stage
):
    calls = _record_capture(monkeypatch)
    logged = []
    monkeypatch.setattr(shipping_page_module.logger, "error", lambda *args: logged.append(args))
    driver = FakeShippingDriver()

    ShippingPage(driver).capture_shipping_failure(stage, sensitive=True)

    assert calls[0][0] is driver
    assert calls[0][1] == expected_stage
    assert calls[0][3] is False
    assert calls.artifacts[0].screenshot is None
    assert secret not in calls.artifacts[0].page_source
    assert secret not in calls[0][1]
    assert secret not in repr(logged[0][2:])


@pytest.mark.parametrize(
    ("stage", "secret"),
    [
        ("Checkout Pay_Password=123456/Retry", "123456"),
        ("Refresh Access_Token:abc/Retry", "abc"),
    ],
)
def test_composite_stage_secrets_are_absent_from_non_sensitive_artifact_paths(
    monkeypatch, stage, secret
):
    calls = _record_capture(monkeypatch)

    ShippingPage(FakeShippingDriver()).capture_shipping_failure(stage)

    assert calls.artifacts[0].screenshot is not None
    assert secret not in calls.artifacts[0].screenshot
    assert secret not in calls.artifacts[0].page_source
