import pytest

from flows.mall_order_types import (
    AmountSnapshot,
    ProductSnapshot,
    SubmitResult,
)
from pages.mall_order_checkout_mixin import MallOrderCheckoutMixin


pytestmark = pytest.mark.unit


class CheckoutRecorder(MallOrderCheckoutMixin):
    def __init__(self, payable, max_payable):
        self.payable = payable
        self.max_payable = max_payable
        self.events = []
        self.ensure_test_address = False
        self.send_im_after_order = False
        self.cancel_after_order = False

    def dismiss_checkout_upsell_if_visible(self):
        return False

    def assert_checkout_matches_detail(self, product):
        return AmountSnapshot(10.0, 0.0, 0.0, self.payable)

    def apply_mall_platform_coupon_if_needed(self):
        return False

    def apply_checkout_preferences(self):
        return None

    def read_amounts(self, product):
        return AmountSnapshot(10.0, 0.0, 0.0, self.payable)

    def pick_tomorrow_random_preorder_time_if_needed(self):
        return None

    def submit_order(self, amounts):
        self.events.append("submit")
        return SubmitResult("ORDER-1", amounts.payable)

    def pay_and_assert(self, submit, product):
        self.events.append("pay")

    def send_order_cancel_im_if_needed(self, submit):
        self.events.append("im")


@pytest.fixture
def product():
    return ProductSnapshot("测试商品", (), 10.0, 1, "SKU-1")


def test_amount_equal_to_ceiling_can_submit_without_message(product):
    page = CheckoutRecorder(payable=20.0, max_payable=20.0)

    page.finish_checkout(product, submit_order=True)

    assert page.events == ["submit", "pay"]


def test_amount_above_ceiling_stops_before_submit(product):
    page = CheckoutRecorder(payable=20.01, max_payable=20.0)

    with pytest.raises(AssertionError, match="max-payable"):
        page.finish_checkout(product, submit_order=True)
    assert page.events == []


def test_explicit_cancellation_runs_after_order_assertions(product):
    page = CheckoutRecorder(payable=10.0, max_payable=20.0)
    page.cancel_after_order = True
    page.cancel_created_order = lambda submit: page.events.append(
        ("cancel", submit.order_no)
    )

    page.finish_checkout(product, submit_order=True)

    assert page.events == [
        "submit",
        "pay",
        ("cancel", "ORDER-1"),
    ]


def test_cancellation_stops_without_created_order_number():
    page = object.__new__(MallOrderCheckoutMixin)
    page.ensure_order_detail_page = lambda: pytest.fail(
        "must not open cancellation without an order number"
    )

    with pytest.raises(AssertionError, match="订单号"):
        page.cancel_created_order(SubmitResult("", 10.0))
