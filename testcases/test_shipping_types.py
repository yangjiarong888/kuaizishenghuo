from datetime import date

import pytest

from pages.shipping_types import (
    AddressData,
    OrderPaymentState,
    can_cancel_payment,
    classify_payment_state,
    earliest_future_label,
    mask_phone,
    parse_delivery_date,
)


def test_address_data_reports_missing_required_fields():
    data = AddressData(
        match="",
        name="Tester",
        phone="",
        country="Philippines",
        city="Manila",
        detail="Unit 1",
        postcode="1000",
    )

    assert data.missing_for_add() == ("phone",)


def test_mask_phone_never_returns_full_number():
    assert mask_phone("+63 9621170994") == "+63******0994"


@pytest.mark.parametrize(
    ("label", "expected"),
    (
        ("今天", date(2026, 8, 10)),
        ("明天", date(2026, 8, 11)),
        ("后天", date(2026, 8, 12)),
        ("8月2日", date(2026, 8, 2)),
        ("8月12日", date(2026, 8, 12)),
        ("2026-08-10", date(2026, 8, 10)),
    ),
)
def test_parse_delivery_date_recognizes_normal_ui_labels(label, expected):
    assert parse_delivery_date(label, date(2026, 8, 10)) == expected


def test_earliest_future_label_ignores_today_past_and_unparseable():
    today = date(2026, 8, 10)
    labels = ["请选择", "8月2日", "今天", "8月12日", "后天", "明天"]

    assert earliest_future_label(labels, today) == ("明天", date(2026, 8, 11))


def test_earliest_future_label_fails_when_only_today_exists():
    with pytest.raises(ValueError, match="未来配送日期"):
        earliest_future_label(["今天", "8月2日"], date(2026, 8, 10))


@pytest.mark.parametrize(
    "text",
    ("订单状态：待支付", "订单状态：待付款"),
)
def test_pending_payment_is_the_only_cancellable_state(text):
    state = classify_payment_state(text)

    assert state is OrderPaymentState.PENDING
    assert can_cancel_payment(state) is True


@pytest.mark.parametrize(
    ("text", "expected"),
    (
        ("已支付", OrderPaymentState.PAID),
        ("支付成功", OrderPaymentState.PAID),
        ("在线支付", OrderPaymentState.PAID),
        ("货到付款", OrderPaymentState.COD),
        ("unknown", OrderPaymentState.UNKNOWN),
    ),
)
def test_non_pending_payment_states_cannot_cancel(text, expected):
    state = classify_payment_state(text)

    assert state is expected
    assert can_cancel_payment(state) is False


@pytest.mark.parametrize(
    ("text", "expected_name"),
    (
        ("支付已取消", "CANCELLED"),
        ("订单已关闭", "CLOSED"),
        ("当前订单不可支付", "NONPAYABLE"),
    ),
)
def test_explicit_cancel_terminal_states_are_classified(text, expected_name):
    expected = getattr(OrderPaymentState, expected_name, None)
    assert classify_payment_state(text) is expected
    assert can_cancel_payment(expected) is False
