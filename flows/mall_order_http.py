"""Pure HTTP boundary for mall stock, payment-hook, and order checks."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional, Sequence


class MallOrderHttpError(RuntimeError):
    """A sanitized mall test-hook boundary failure."""


def find_first_json_value(
    data: Any,
    keys: Sequence[str],
) -> Optional[Any]:
    """Return the first matching value found in nested JSON data."""
    if isinstance(data, dict):
        for key in keys:
            if key in data:
                return data[key]
        for value in data.values():
            found = find_first_json_value(value, keys)
            if found is not None:
                return found
    elif isinstance(data, list):
        for value in data:
            found = find_first_json_value(value, keys)
            if found is not None:
                return found
    return None


@dataclass
class MallOrderHttpClient:
    """HTTP client with injectable transport for deterministic unit tests."""

    sku: str
    quantity: int
    stock_api_url: Optional[str]
    order_status_api_url: Optional[str]
    mock_pay_success_url: Optional[str]
    opener: Callable[..., Any] = urllib.request.urlopen

    def _format_url(
        self,
        url_template: str,
        payload: Optional[Mapping[str, Any]],
    ) -> str:
        values = {
            "sku": self.sku,
            "order_no": (payload or {}).get("order_no", ""),
            "amount": (payload or {}).get("amount", ""),
            "quantity": self.quantity,
        }
        encoded = {
            key: urllib.parse.quote(str(value), safe="")
            for key, value in values.items()
        }
        try:
            return url_template.format(**encoded)
        except (KeyError, ValueError) as exc:
            raise MallOrderHttpError(
                "invalid URL template"
            ) from exc

    def call_json_url(
        self,
        url_template: str,
        *,
        payload: Optional[Mapping[str, Any]] = None,
        method: str = "POST",
        timeout: float = 12.0,
    ) -> Any:
        method_name = method.upper()
        url = self._format_url(url_template, payload)
        body = None
        headers = {"Accept": "application/json"}
        if method_name != "GET":
            body = json.dumps(
                payload or {},
                ensure_ascii=False,
            ).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            url,
            data=body,
            headers=headers,
            method=method_name,
        )
        try:
            with self.opener(request, timeout=timeout) as response:
                status = int(getattr(response, "status", 200))
                if status >= 400:
                    raise MallOrderHttpError(
                        f"request failed status={status}"
                    )
                raw = response.read()
        except MallOrderHttpError:
            raise
        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
        ) as exc:
            raise MallOrderHttpError(
                f"request failed error_type={type(exc).__name__}"
            ) from exc
        try:
            return json.loads(raw.decode("utf-8"))
        except (
            AttributeError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise MallOrderHttpError(
                "invalid JSON response"
            ) from exc

    def read_stock(self) -> Optional[int]:
        if not self.stock_api_url:
            return None
        data = self.call_json_url(
            self.stock_api_url,
            payload={"sku": self.sku},
            method="GET",
        )
        stock = find_first_json_value(
            data,
            ("stock", "inventory", "availableStock"),
        )
        if isinstance(stock, (dict, list)):
            stock = find_first_json_value(
                stock,
                ("stock", "availableStock", "inventory"),
            )
        if stock is None or isinstance(stock, (dict, list, bool)):
            raise MallOrderHttpError(
                "configured stock response has no scalar stock field"
            )
        try:
            return int(stock)
        except (TypeError, ValueError) as exc:
            raise MallOrderHttpError(
                "configured stock response has invalid stock value"
            ) from exc

    def mock_payment_success(
        self,
        order_no: str,
        amount: float,
    ) -> Any:
        if not self.mock_pay_success_url:
            raise MallOrderHttpError(
                "mock payment URL is not configured"
            )
        return self.call_json_url(
            self.mock_pay_success_url,
            payload={
                "order_no": order_no,
                "amount": amount,
            },
            method="POST",
        )

    def assert_order_wait_ship(self, order_no: str) -> bool:
        if not self.order_status_api_url:
            return False
        data = self.call_json_url(
            self.order_status_api_url,
            payload={"order_no": order_no},
            method="GET",
        )
        status = find_first_json_value(
            data,
            ("statusText", "status", "orderStatus"),
        )
        status_text = "" if status is None else str(status)
        status_lower = status_text.lower()
        accepted = (
            "待发货" in status_text
            or "待配送" in status_text
            or "待出库" in status_text
            or "wait_ship" in status_lower
            or "wait_deliver" in status_lower
            or "to_ship" in status_lower
        )
        if not accepted:
            raise MallOrderHttpError(
                f"order status is not wait-ship: {status_text or '<missing>'}"
            )
        return True
