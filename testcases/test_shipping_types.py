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
    "label",
    ("\u6D60\u5A42\u3049", "8\u93C8?0\u93C3?", "2026-08-10"),
)
def test_today_is_never_future(label):
    today = date(2026, 8, 10)

    assert parse_delivery_date(label, today) == today


def test_earliest_future_label_ignores_today_past_and_unparseable():
    today = date(2026, 8, 10)
    labels = [
        "\u7487\u70FD\u20AC\u590B\u5AE8",
        "8\u93C8?\u93C3?",
        "\u6D60\u5A42\u3049",
        "8\u93C8?2\u93C3?",
        "\u93C4\u5EA1\u3049",
        "8\u93C8?3\u93C3?",
    ]

    assert earliest_future_label(labels, today) == (
        "\u93C4\u5EA1\u3049",
        date(2026, 8, 11),
    )


def test_earliest_future_label_fails_when_only_today_exists():
    with pytest.raises(ValueError, match="\u93C8\uE045\u6F75\u95B0\u5D89\u20AC\u4F79\u68E9\u93C8?"):
        earliest_future_label(
            ["\u6D60\u5A42\u3049", "8\u93C8?0\u93C3?"],
            date(2026, 8, 10),
        )


def test_only_pending_payment_can_cancel_payment():
    assert classify_payment_state(
        "\u7481\u3220\u5D1F\u9418\u8235\u20AC\u4F8A\u7D30\u5BF0\u546E\u656E\u6D60?"
    ) is OrderPaymentState.PENDING
    assert can_cancel_payment(OrderPaymentState.PENDING) is True
    assert can_cancel_payment(OrderPaymentState.PAID) is False
    assert can_cancel_payment(OrderPaymentState.COD) is False
    assert can_cancel_payment(OrderPaymentState.UNKNOWN) is False
