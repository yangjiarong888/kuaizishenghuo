"""Pure value types used at the mall checkout boundary."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class ProductSnapshot:
    name: str
    specs: Tuple[str, ...]
    unit_price: float
    quantity: int
    sku: str
    stock_before: Optional[int] = None


@dataclass
class AmountSnapshot:
    goods_total: float
    coupon: float
    freight: float
    payable: float


@dataclass
class SubmitResult:
    order_no: str
    cashier_amount: float


def parse_money(raw: str) -> Optional[float]:
    """Parse a checkout amount without accepting partial malformed numbers."""
    if not raw:
        return None

    text = html.unescape(str(raw)).replace(",", "").strip()
    if not text:
        return None

    has_money_hint = bool(
        re.search(r"(￥|¥|₱|PHP|RMB|元|金额|价|费|付|合计|优惠|小计)", text, flags=re.I)
    )
    match = re.search(
        r"(?<![\d.])"
        r"(?P<neg>-)?\s*"
        r"(?:￥|¥|₱|PHP|RMB|P)?\s*"
        r"(?P<num>\d+(?:\.\d{1,2})?)"
        r"(?![\d.])\s*(?:元)?",
        text,
        flags=re.I,
    )
    if not match:
        return None

    number = match.group("num")
    if "." not in number and not has_money_hint:
        return None

    value = float(number)
    if match.group("neg") or "优惠" in text or "减" in text:
        return -value
    return value


def nearly_equal(left: float, right: float, tolerance: float = 0.02) -> bool:
    return abs(left - right) <= tolerance
