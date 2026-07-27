import pytest

from flows.mall_order_types import ProductSnapshot
from pages.mall_order_cart_mixin import MallOrderCartMixin


pytestmark = pytest.mark.unit


class RecordingCart(MallOrderCartMixin):
    def __init__(self):
        self.events = []

    def open_detail_and_snapshot(self, keyword):
        self.events.append(("detail", keyword))
        return ProductSnapshot(
            name="测试可乐",
            specs=("大份",),
            unit_price=10.0,
            quantity=1,
            sku="SKU-1",
        )

    def add_product_to_cart_exact_specs(self, product):
        self.events.append(("add", product.sku))
        return product

    def assert_cart_contains_product(self, product):
        self.events.append(("assert-cart", product.name))


def test_add_to_cart_only_stops_after_exact_cart_assertion():
    page = RecordingCart()

    assert page.run_add_to_cart_only("可乐") is True
    assert page.events == [
        ("detail", "可乐"),
        ("add", "SKU-1"),
        ("assert-cart", "测试可乐"),
    ]


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("manage_all", ("manage", True)),
        ("manage_partial", ("manage", False)),
        ("manage_none", ("manage-none",)),
        ("minus", ("minus",)),
        ("swipe", ("swipe",)),
    ],
)
def test_cart_delete_mode_dispatches_one_exact_strategy(mode, expected):
    page = object.__new__(MallOrderCartMixin)
    events = []
    page.open_cart_page = lambda: events.append(("open",))
    page.cart_delete_by_manage = (
        lambda *, all_items: events.append(("manage", all_items))
    )
    page.cart_assert_delete_without_selection_toast = (
        lambda: events.append(("manage-none",))
    )
    page.cart_delete_by_minus = lambda: events.append(("minus",))
    page.cart_delete_by_swipe = lambda: events.append(("swipe",))

    assert page.run_cart_delete_case(mode) is True
    assert events == [("open",), expected]


def test_cart_assertion_rejects_missing_exact_product_name():
    page = object.__new__(MallOrderCartMixin)
    page.open_cart_page = lambda: None
    page.page_blob = lambda: "购物车\n其他商品"
    product = ProductSnapshot(
        name="测试可乐",
        specs=(),
        unit_price=10.0,
        quantity=1,
        sku="SKU-1",
    )

    with pytest.raises(AssertionError, match="测试可乐"):
        page.assert_cart_contains_product(product)


def test_add_product_uses_detail_button_then_specs_and_stock_check(
    monkeypatch,
):
    events = []
    page = object.__new__(MallOrderCartMixin)
    page.click_by_id_or_label = (
        lambda *args, **kwargs: events.append(("click",)) or True
    )
    page._login_like_screen_visible = lambda: False
    page.select_specs_and_quantity = (
        lambda: events.append(("specs",)) or 8
    )
    page.wait_page_contains_any = (
        lambda markers, *, timeout: events.append(
            ("stock-check", tuple(markers), timeout)
        )
        or False
    )
    monkeypatch.setattr(
        "pages.mall_order_cart_mixin.time.sleep",
        lambda seconds: events.append(("sleep", seconds)),
    )
    product = ProductSnapshot(
        name="测试可乐",
        specs=("大份",),
        unit_price=10.0,
        quantity=1,
        sku="SKU-1",
    )

    assert page.add_product_to_cart_exact_specs(product) is product
    assert product.stock_before == 8
    assert events[0:3] == [
        ("click",),
        ("sleep", 0.8),
        ("specs",),
    ]
    assert events[3][0] == "stock-check"
