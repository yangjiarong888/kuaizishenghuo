from __future__ import annotations

import pytest

from flows.mall_order_types import (
    AmountSnapshot,
    ProductSnapshot,
    SubmitResult,
    nearly_equal,
    parse_money,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("₱1,234.50", 1234.50),
        ("PHP 99", 99.0),
        ("￥12.30", 12.30),
        ("12.30元", 12.30),
        ("优惠 8.50", -8.50),
        ("减 ￥3.00", -3.0),
        ("-P 2.25", -2.25),
        ("12.30", 12.30),
    ],
)
def test_parse_money_accepts_supported_checkout_formats(raw: str, expected: float) -> None:
    assert parse_money(raw) == pytest.approx(expected)


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "N/A",
        "商品编号 12345",
        "￥12.345",
        "PHP 1.2.3",
    ],
)
def test_parse_money_rejects_missing_or_ambiguous_values(raw: str) -> None:
    assert parse_money(raw) is None


def test_nearly_equal_includes_tolerance_boundary() -> None:
    assert nearly_equal(10.00, 10.02)
    assert not nearly_equal(10.00, 10.021)


def test_snapshot_types_hold_order_boundary_values() -> None:
    product = ProductSnapshot(
        name="测试商品",
        specs=("大份", "热"),
        unit_price=12.5,
        quantity=2,
        sku="SKU-1",
        stock_before=8,
    )
    amount = AmountSnapshot(goods_total=25.0, coupon=-3.0, freight=2.0, payable=24.0)
    result = SubmitResult(order_no="ORDER-1", cashier_amount=24.0)

    assert product.specs == ("大份", "热")
    assert product.stock_before == 8
    assert amount.payable == 24.0
    assert result.order_no == "ORDER-1"
