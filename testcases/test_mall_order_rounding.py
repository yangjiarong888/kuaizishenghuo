import pytest

from flows.mall_order_types import AmountSnapshot, ProductSnapshot, SubmitResult
from pages.mall_order_checkout_mixin import MallOrderCheckoutMixin
from pages.rounding_payment import RoundingOption


pytestmark = pytest.mark.unit

PRODUCT = ProductSnapshot("测试商品", (), 425.0, 1, "SKU-ROUND")


class FakeMallCheckout(MallOrderCheckoutMixin):
    def __init__(
        self,
        *,
        rounding_payment: bool,
        rounding_amount: float | None,
        max_payable: float = 500.0,
    ) -> None:
        self.rounding_payment = rounding_payment
        self.rounding_amount = rounding_amount
        self.max_payable = max_payable
        self.ensure_test_address = True
        self.force_add_test_address = False
        self.send_im_after_order = False
        self.cancel_after_order = False
        self.detail_order_no = "ORDER-ROUND"
        self.detail_change = 75.0
        self.events: list[str] = []

    def dismiss_checkout_upsell_if_visible(self):
        self.events.append("checkout")
        return False

    def assert_checkout_matches_detail(self, product):
        return AmountSnapshot(425.0, 0.0, 0.0, 425.0)

    def ensure_test_address_from_checkout_flow(self, *, force_add):
        self.events.append("address")

    def apply_mall_platform_coupon_if_needed(self):
        self.events.append("coupon")
        return False

    def apply_checkout_preferences(self):
        self.events.append("preferences")

    def read_amounts(self, product):
        return AmountSnapshot(425.0, 0.0, 0.0, 425.0)

    def pick_tomorrow_random_preorder_time_if_needed(self):
        self.events.append("delivery")
        return "tomorrow"

    def select_checkout_rounding_payment(self, *, payable, custom_amount):
        assert payable == 425.0
        assert custom_amount == self.rounding_amount
        self.events.append(f"rounding:{custom_amount:g}")
        return RoundingOption(int(custom_amount), custom_amount - payable)

    def assert_within_payable_limit(self, amounts):
        self.events.append(f"limit:{amounts.payable:g}")
        return super().assert_within_payable_limit(amounts)

    def submit_order(self, amounts):
        self.events.append(f"submit:{amounts.payable:g}")
        return SubmitResult("ORDER-ROUND", amounts.payable)

    def pay_and_assert(self, submit, product):
        self.events.append("pay")

    def ensure_order_detail_page(self):
        self.events.append("detail")

    def page_texts(self):
        return [
            f"订单号：{self.detail_order_no}",
            f"找零存入余额：₱{self.detail_change:.2f}",
        ]

    def page_blob(self):
        return "\n".join(self.page_texts())


def test_mall_rounding_occurs_after_delivery_and_before_submit():
    page = FakeMallCheckout(rounding_payment=True, rounding_amount=500)

    page.finish_checkout(PRODUCT, submit_order=True)

    assert page.events == [
        "checkout",
        "address",
        "coupon",
        "preferences",
        "delivery",
        "rounding:500",
        "limit:500",
        "submit:500",
        "pay",
        "detail",
    ]


def test_rounded_amount_above_max_payable_stops_before_submit():
    page = FakeMallCheckout(
        rounding_payment=True,
        rounding_amount=500,
        max_payable=450,
    )

    with pytest.raises(AssertionError, match="max-payable|超过"):
        page.finish_checkout(PRODUCT, submit_order=True)

    assert "submit:500" not in page.events


@pytest.mark.parametrize("max_payable", [float("nan"), float("inf")])
def test_non_finite_max_payable_stops_before_submit(max_payable):
    page = FakeMallCheckout(
        rounding_payment=True,
        rounding_amount=500,
        max_payable=max_payable,
    )

    with pytest.raises(AssertionError, match="max-payable|有限|正数"):
        page.finish_checkout(PRODUCT, submit_order=True)

    assert "submit:500" not in page.events


def test_rounding_detail_must_match_the_submitted_order():
    page = FakeMallCheckout(rounding_payment=True, rounding_amount=500)
    page.detail_order_no = "ORDER-OTHER"

    with pytest.raises(AssertionError, match="订单号|本次订单"):
        page.finish_checkout(PRODUCT, submit_order=True)


def test_rounding_detail_must_show_the_selected_change():
    page = FakeMallCheckout(rounding_payment=True, rounding_amount=500)
    page.detail_change = 74.0

    with pytest.raises(AssertionError, match="找零|75"):
        page.finish_checkout(PRODUCT, submit_order=True)


def test_rounding_detail_rejects_payable_amount_after_unvalued_change_label():
    page = FakeMallCheckout(rounding_payment=True, rounding_amount=500)
    page.page_texts = lambda: [
        "订单号：ORDER-ROUND",
        "找零",
        "应付金额：₱75.00",
    ]
    page.page_blob = lambda: "\n".join(page.page_texts())

    with pytest.raises(AssertionError, match="找零|未解析"):
        page.finish_checkout(PRODUCT, submit_order=True)


def test_rounding_detail_allows_duplicate_same_order_identity():
    page = FakeMallCheckout(rounding_payment=True, rounding_amount=500)
    page.page_texts = lambda: [
        "订单号：ORDER-ROUND",
        "orderNo=order-round",
        "找零存入余额：₱75.00",
    ]
    page.page_blob = lambda: "\n".join(page.page_texts())

    page.finish_checkout(PRODUCT, submit_order=True)


def test_rounding_detail_rejects_conflicting_order_identities():
    page = FakeMallCheckout(rounding_payment=True, rounding_amount=500)
    page.page_texts = lambda: [
        "订单号：ORDER-ROUND",
        "orderNo=ORDER-OTHER",
        "找零存入余额：₱75.00",
    ]
    page.page_blob = lambda: "\n".join(page.page_texts())

    with pytest.raises(AssertionError, match="订单号|冲突|本次订单"):
        page.finish_checkout(PRODUCT, submit_order=True)
