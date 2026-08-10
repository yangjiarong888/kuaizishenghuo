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
    if "今天" in text:
        return today
    if "明天" in text:
        return today + timedelta(days=1)
    if "后天" in text:
        return today + timedelta(days=2)
    full = re.search(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})", text)
    if full:
        return date(*(int(group) for group in full.groups()))
    month_day = re.search(r"(\d{1,2})月(\d{1,2})日", text)
    if not month_day:
        return None
    month, day = (int(group) for group in month_day.groups())
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
        raise ValueError("未找到严格晚于今天的未来配送日期")
    parsed, label = min(candidates, key=lambda item: item[0])
    return label, parsed


def classify_payment_state(text: str) -> OrderPaymentState:
    if any(marker in text for marker in ("待支付", "待付款")):
        return OrderPaymentState.PENDING
    if "货到付款" in text:
        return OrderPaymentState.COD
    if any(marker in text for marker in ("支付成功", "已支付", "在线支付")):
        return OrderPaymentState.PAID
    return OrderPaymentState.UNKNOWN


def can_cancel_payment(state: OrderPaymentState) -> bool:
    return state is OrderPaymentState.PENDING
