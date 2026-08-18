from __future__ import annotations

import pytest

from pages.rounding_payment import RoundingOption, RoundingPaymentMixin
from pages.takeout_checkout_mixin import TakeoutCheckoutMixin


pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _avoid_checkout_sleeps(monkeypatch):
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)


class FakeTakeoutCheckout(TakeoutCheckoutMixin):
    def __init__(
        self,
        *,
        payable: float = 425.0,
        cod_selection_ok: bool = True,
    ) -> None:
        self.payable = payable
        self.cod_selection_ok = cod_selection_ok
        self.events: list[str] = []
        self.confirm_count = 0

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
        self.events.append("first-confirm" if self.confirm_count == 1 else "submit")
        return True

    def shop_pick_random_address_in_sheet(self):
        self.events.append("address")
        return True

    def shop_apply_checkout_coupons(self, **kwargs):
        self.events.append("coupons")
        return True

    def shop_apply_checkout_preferences(self, **kwargs):
        self.events.append("preferences")

    def shop_select_balance_payment(self):
        self.events.append("balance")
        return True

    def shop_select_cash_on_delivery_payment(self):
        self.events.append("cod")
        return self.cod_selection_ok

    def shop_open_delivery_time_and_pick_future_slot(self, **kwargs):
        self.events.append("delivery")
        return True

    def checkout_payable_amount(self):
        self.events.append(f"payable:{self.payable:g}")
        return self.payable

    def select_checkout_rounding_payment(self, *, payable, custom_amount):
        assert payable == self.payable
        amount = custom_amount if custom_amount is not None else 500
        self.events.append(f"rounding:{amount:g}")
        return RoundingOption(int(amount), amount - payable)

    def shop_assert_order_detail_cancel_visible(self, timeout=25.0):
        self.events.append("order-detail")
        return False

    def shop_cancel_order_flow(self):
        self.events.append("cancel")
        return True


def test_takeout_mixin_composes_shared_rounding_core():
    assert issubclass(TakeoutCheckoutMixin, RoundingPaymentMixin)


def test_takeout_cod_rounding_is_selected_before_submit():
    page = FakeTakeoutCheckout()
    assert page.run_shop_checkout_pay_and_cancel_flow(
        submit_order=True,
        checkout_payment="cod",
        rounding_payment=True,
        rounding_amount=500,
        max_payable=500,
    ) is False
    assert page.events.index("rounding:500") < page.events.index("submit")
    assert page._takeout_order_submitted is True


def test_takeout_cod_rounding_follows_payment_and_delivery_selection():
    page = FakeTakeoutCheckout()

    page.run_shop_checkout_pay_and_cancel_flow(
        submit_order=False,
        checkout_payment="cod",
        rounding_payment=True,
        rounding_amount=500,
    )

    assert page.events.index("cod") < page.events.index("delivery")
    assert page.events.index("delivery") < page.events.index("rounding:500")


def test_takeout_balance_never_calls_rounding_or_password_input():
    page = FakeTakeoutCheckout()
    page.run_shop_checkout_pay_and_cancel_flow(
        submit_order=False,
        checkout_payment="balance",
    )
    assert not any(event.startswith("rounding") for event in page.events)
    assert not hasattr(page, "shop_enter_pay_password")


def test_takeout_rounded_amount_above_limit_stops_before_submit():
    page = FakeTakeoutCheckout()

    with pytest.raises(AssertionError, match="max-payable|超过"):
        page.run_shop_checkout_pay_and_cancel_flow(
            submit_order=True,
            checkout_payment="cod",
            rounding_payment=True,
            rounding_amount=500,
            max_payable=499,
        )

    assert "submit" not in page.events
    assert not getattr(page, "_takeout_order_submitted", False)


@pytest.mark.parametrize(
    "max_payable",
    [None, 0, -1, float("nan"), float("inf"), float("-inf")],
)
def test_takeout_submit_requires_finite_positive_limit(max_payable):
    page = FakeTakeoutCheckout()

    with pytest.raises(AssertionError, match="max-payable|有限|正数"):
        page.run_shop_checkout_pay_and_cancel_flow(
            submit_order=True,
            checkout_payment="cod",
            max_payable=max_payable,
        )

    assert page.events == []


@pytest.mark.parametrize(
    ("submit_order", "rounding_payment"),
    [(True, False), (False, True)],
)
def test_takeout_required_cod_selection_failure_stops_before_later_checkout(
    submit_order,
    rounding_payment,
):
    page = FakeTakeoutCheckout(cod_selection_ok=False)

    assert page.run_shop_checkout_pay_and_cancel_flow(
        submit_order=submit_order,
        checkout_payment="cod",
        rounding_payment=rounding_payment,
        rounding_amount=500 if rounding_payment else None,
        max_payable=500 if submit_order else None,
    ) is False

    assert page.events[-1] == "cod"
    assert "delivery" not in page.events
    assert not any(event.startswith("rounding") for event in page.events)
    assert not any(event.startswith("payable") for event in page.events)
    assert "submit" not in page.events


def test_takeout_rounding_requires_cod_defensively():
    page = FakeTakeoutCheckout()

    with pytest.raises(AssertionError, match="COD|货到付款"):
        page.run_shop_checkout_pay_and_cancel_flow(
            submit_order=False,
            checkout_payment="balance",
            rounding_payment=True,
            rounding_amount=500,
        )

    assert "rounding:500" not in page.events


def test_takeout_rounding_amount_requires_explicit_rounding_defensively():
    page = FakeTakeoutCheckout()

    with pytest.raises(AssertionError, match="rounding-payment|显式"):
        page.run_shop_checkout_pay_and_cancel_flow(
            submit_order=False,
            checkout_payment="cod",
            rounding_amount=500,
        )

    assert "rounding:500" not in page.events
