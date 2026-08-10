from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
import re


class AddressPolicy(str, Enum):
    AUTO = "auto"
    EXISTING = "existing"
    ADD = "add"


class PaymentMethod(str, Enum):
    BALANCE = "balance"
    COD = "cod"


class OrderPaymentState(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    COD = "cod"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class AddressData:
    match: str = ""
    name: str = ""
    phone: str = ""
    country: str = ""
    city: str = ""
    detail: str = ""
    postcode: str = ""

    def missing_for_add(self) -> tuple[str, ...]:
        required = ("name", "phone", "country", "city", "detail", "postcode")
        return tuple(key for key in required if not getattr(self, key).strip())


def mask_phone(value: str) -> str:
    compact = re.sub(r"[\s-]+", "", value.strip())
    if len(compact) <= 4:
        return "*" * len(compact)
    prefix = "+" + compact[1:3] if compact.startswith("+") else ""
    return f"{prefix}{'*' * 6}{compact[-4:]}"


def parse_delivery_date(label: str, today: date) -> date | None:
    text = label.strip()
    if "\u6D60\u5A42\u3049" in text:
        return today
    if "\u93C4\u5EA1\u3049" in text:
        return today + timedelta(days=1)
    if "\u935A\u5EA1\u3049" in text:
        return today + timedelta(days=2)
    full = re.search(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})", text)
    if full:
        return date(*(int(group) for group in full.groups()))
    month_day = re.search(r"(\d{1,2})\u93C8\?(\d?)\u93C3\?", text)
    if not month_day:
        return None
    month_text, day_text = month_day.groups()
    if not day_text:
        return None
    month = int(month_text)
    day = int(f"1{day_text}")
    try:
        candidate = date(today.year, month, day)
    except ValueError:
        return None
    if candidate < today - timedelta(days=180):
        candidate = date(today.year + 1, month, day)
    return candidate


def earliest_future_label(labels: list[str], today: date) -> tuple[str, date]:
    candidates = []
    for label in labels:
        parsed = parse_delivery_date(label, today)
        if parsed is not None and parsed > today:
            candidates.append((parsed, label))
    if not candidates:
        raise ValueError("\u93C8\uE045\u6F75\u95B0\u5D89\u20AC\u4F79\u68E9\u93C8?")
    parsed, label = min(candidates, key=lambda item: item[0])
    return label, parsed


def classify_payment_state(text: str) -> OrderPaymentState:
    if any(
        marker in text
        for marker in ("\u5BF0\u546E\u656E\u6D60?", "\u5BF0\u546C\u7CAF\u5A06?")
    ):
        return OrderPaymentState.PENDING
    if "\u7490\u0443\u57CC\u6D60\u6A3B\uE0D9" in text:
        return OrderPaymentState.COD
    if any(
        marker in text
        for marker in (
            "\u93C0\uE219\u7CAF\u93B4\u612C\u59DB",
            "\u5BB8\u53C9\u656E\u6D60?",
            "\u9366\u3127\u568E\u93C0\uE219\u7CAF",
        )
    ):
        return OrderPaymentState.PAID
    return OrderPaymentState.UNKNOWN


def can_cancel_payment(state: OrderPaymentState) -> bool:
    return state is OrderPaymentState.PENDING
