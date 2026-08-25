from __future__ import annotations

from pages.takeout_checkout_mixin import TakeoutCheckoutMixin
from pages.takeout_address import TakeoutAddressData


class RecordingCheckout(TakeoutCheckoutMixin):
    def __init__(
        self,
        *,
        manual_payment_ok: bool = True,
        preferences_ok: bool = True,
        payable_values=None,
        address_ok: bool = True,
        cart_has_items: bool = False,
    ) -> None:
        self.events = []
        self.confirm_count = 0
        self.manual_payment_ok = manual_payment_ok
        self.preferences_ok = preferences_ok
        self.payable_values = list(payable_values or [100.0])
        self.address_ok = address_ok
        self.cart_has_items = cart_has_items

    def shop_cart_has_purchasable_items(self):
        self.events.append(("cart-has-items", self.cart_has_items))
        return self.cart_has_items

    def shop_detail_scroll_to_category(self, *args, **kwargs):
        self.events.append("category")
        return True

    def shop_detail_add_first_visible_product_highest_spec(self, *args, **kwargs):
        self.events.append("add")
        return True

    def shop_tap_bottom_cart_bar(self):
        self.events.append("cart")
        return True

    def shop_tap_go_checkout(self):
        self.events.append("checkout")
        return True

    def shop_tap_confirm_pay_bar(self):
        self.confirm_count += 1
        self.events.append(f"confirm-{self.confirm_count}")
        return True

    def shop_pick_random_address_in_sheet(self):
        self.events.append("address")
        return True

    def shop_pick_address_in_sheet(
        self, *, address_ordinal, address_contains=None, require_phone=False
    ):
        self.events.append(("address", address_ordinal, address_contains))
        return self.address_ok

    def shop_add_address_from_sheet(self, data):
        self.events.append("address-added-and-verified")
        return True

    def shop_prepare_address_sheet_for_add(self):
        self.events.append("prepare-address-sheet-for-add")
        return True

    def shop_apply_checkout_coupons(self, **kwargs):
        self.events.append("coupons")
        return True

    def shop_apply_checkout_preferences(self, **kwargs):
        self.events.append("preferences")
        return self.preferences_ok

    def shop_select_balance_payment(self):
        self.events.append("balance")
        return True

    def shop_select_cash_on_delivery_payment(self):
        self.events.append("cod")
        return True

    def shop_open_delivery_time_and_pick_future_slot(self, **kwargs):
        self.events.append("delivery")
        return True

    def checkout_payable_amount(self):
        value = self.payable_values.pop(0)
        self.events.append(("payable", value))
        return value

    def shop_enter_pay_password(self, password="legacy-default"):
        self.events.append(("auto-password", password))
        return True

    def shop_wait_for_manual_payment(self, timeout=120.0):
        self.events.append(("manual-payment", timeout))
        return self.manual_payment_ok

    def shop_assert_order_detail_cancel_visible(self, timeout=25.0):
        self.events.append(("order-detail", timeout))
        return True

    def shop_cancel_order_flow(self):
        self.events.append("cancel")
        return True


def test_cart_item_count_reads_flutter_composite_cart_label() -> None:
    assert (
        TakeoutCheckoutMixin._cart_item_count_from_label(
            "8\n₱1295.00\n购物车"
        )
        == 8
    )


def test_preview_stops_before_final_confirmation(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = RecordingCheckout()

    assert page.run_shop_checkout_pay_and_cancel_flow(
        submit_order=False,
        address_ordinal=1,
    )

    assert page.confirm_count == 1
    assert "cancel" not in page.events
    assert not any(
        isinstance(event, tuple)
        and event[0] in {"auto-password", "manual-payment", "order-detail"}
        for event in page.events
    )


def test_balance_submission_waits_for_manual_payment_then_cancels(
    monkeypatch,
) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = RecordingCheckout()

    assert page.run_shop_checkout_pay_and_cancel_flow(
        submit_order=True,
        checkout_payment="balance",
        manual_payment_timeout=90.0,
        max_payable=500,
        address_ordinal=1,
        delivery_time_slot_ordinal=1,
    )

    assert page.confirm_count == 2
    assert ("manual-payment", 90.0) in page.events
    assert not any(
        isinstance(event, tuple) and event[0] == "auto-password"
        for event in page.events
    )
    assert page.events[-1] == "cancel"


def test_cod_submission_skips_manual_payment(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = RecordingCheckout()

    assert page.run_shop_checkout_pay_and_cancel_flow(
        submit_order=True,
        checkout_payment="cod",
        max_payable=500,
        address_ordinal=1,
        delivery_time_slot_ordinal=1,
    )

    assert page.confirm_count == 2
    assert not any(
        isinstance(event, tuple) and event[0] in {"auto-password", "manual-payment"}
        for event in page.events
    )
    assert ("order-detail", 25.0) in page.events
    assert page.events[-1] == "cancel"


def test_manual_payment_timeout_stops_before_cancel(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = RecordingCheckout(manual_payment_ok=False)

    assert not page.run_shop_checkout_pay_and_cancel_flow(
        submit_order=True,
        checkout_payment="balance",
        manual_payment_timeout=30.0,
        max_payable=500,
        address_ordinal=1,
        delivery_time_slot_ordinal=1,
    )

    assert ("manual-payment", 30.0) in page.events
    assert "cancel" not in page.events


def test_submit_uses_the_explicit_address_match(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = RecordingCheckout()

    assert page.run_shop_checkout_pay_and_cancel_flow(
        submit_order=True,
        checkout_payment="cod",
        max_payable=500,
        address_ordinal=1,
        address_contains="70994",
        delivery_time_slot_ordinal=1,
    )

    assert ("address", 1, "70994") in page.events
    assert "address" not in page.events


def test_payment_sheet_is_resolved_before_checkout_preferences(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = RecordingCheckout()

    assert page.run_shop_checkout_pay_and_cancel_flow(
        submit_order=True,
        checkout_payment="cod",
        max_payable=500,
        address_ordinal=1,
        delivery_time_slot_ordinal=1,
    )

    address_event = ("address", 1, None)
    assert page.events.index(address_event) < page.events.index("cod")
    assert page.events.index("cod") < page.events.index("coupons")
    assert page.events.index("cod") < page.events.index("preferences")


def test_auto_address_creation_is_verified_before_payment_selection(
    monkeypatch,
) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = RecordingCheckout(address_ok=False)
    data = TakeoutAddressData(
        "Automation Contact",
        "09171234567",
        "Robinsons Place Manila",
        "Unit 8 test address",
    )

    assert page.run_shop_checkout_pay_and_cancel_flow(
        submit_order=False,
        checkout_payment="cod",
        address_policy="auto",
        address_data=data,
        address_ordinal=None,
    )

    assert page.events.index("address-added-and-verified") < page.events.index("cod")


def test_add_policy_opens_address_book_before_creating_address(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = RecordingCheckout()
    data = TakeoutAddressData(
        "Automation Contact",
        "09171234567",
        "Robinsons Place Manila",
        "Unit 8 test address",
    )

    assert page.run_shop_checkout_pay_and_cancel_flow(
        submit_order=False,
        checkout_payment="cod",
        address_policy="add",
        address_data=data,
    )

    assert page.events.index("prepare-address-sheet-for-add") < page.events.index(
        "address-added-and-verified"
    )


def test_existing_cart_item_is_reused_without_adding_again(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = RecordingCheckout(cart_has_items=True)

    assert page.run_shop_checkout_pay_and_cancel_flow(
        submit_order=False,
        address_ordinal=1,
    )

    assert "category" not in page.events
    assert "add" not in page.events
    assert page.events.count("cart") == 1
    assert page.events.count("checkout") == 1


def test_empty_cart_adds_exactly_one_product_before_checkout(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = RecordingCheckout(cart_has_items=False)

    assert page.run_shop_checkout_pay_and_cancel_flow(
        submit_order=False,
        address_ordinal=1,
    )

    assert page.events.count("category") == 1
    assert page.events.count("add") == 1


def test_checkout_stops_when_requested_preferences_cannot_be_applied(
    monkeypatch,
) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = RecordingCheckout(preferences_ok=False)

    assert not page.run_shop_checkout_pay_and_cancel_flow(
        submit_order=True,
        checkout_payment="cod",
        max_payable=500,
        address_ordinal=1,
        delivery_time_slot_ordinal=1,
    )

    assert page.events.index("cod") < page.events.index("preferences")
    assert "confirm-2" not in page.events


def test_submit_retries_a_transiently_missing_payable_amount(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = RecordingCheckout(payable_values=[None, 1094.0])

    assert page.run_shop_checkout_pay_and_cancel_flow(
        submit_order=True,
        checkout_payment="cod",
        max_payable=5000,
        address_ordinal=1,
        delivery_time_slot_ordinal=1,
    )

    assert ("payable", None) in page.events
    assert ("payable", 1094.0) in page.events


def test_address_match_failure_is_not_retried(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = RecordingCheckout(address_ok=False)

    assert not page.run_shop_checkout_pay_and_cancel_flow(
        submit_order=True,
        checkout_payment="cod",
        max_payable=5000,
        address_ordinal=1,
        address_contains="app 09621170994",
        delivery_time_slot_ordinal=1,
    )

    assert page.events.count(("address", 1, "app 09621170994")) == 1
