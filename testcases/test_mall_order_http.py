import json
import urllib.error

import pytest

import scripts.run_mall_order_flow as mall_cli
from flows.mall_order_http import (
    MallOrderHttpClient,
    MallOrderHttpError,
    find_first_json_value,
)


pytestmark = pytest.mark.unit


class FakeResponse:
    def __init__(self, body, status):
        self.body = body
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self.body


class FakeOpener:
    def __init__(self, *, body=b"{}", status=200, error=None):
        self.body = body
        self.status = status
        self.error = error
        self.requests = []
        self.timeouts = []

    def __call__(self, request, *, timeout):
        self.requests.append(request)
        self.timeouts.append(timeout)
        if self.error is not None:
            raise self.error
        return FakeResponse(self.body, self.status)


def make_client(opener, **overrides):
    values = {
        "sku": "SKU-1",
        "quantity": 1,
        "stock_api_url": None,
        "order_status_api_url": None,
        "mock_pay_success_url": None,
        "opener": opener,
    }
    values.update(overrides)
    return MallOrderHttpClient(**values)


def test_call_json_url_decodes_json_with_injected_opener():
    opener = FakeOpener(body=b'{"data":{"stock":8}}')
    client = make_client(opener)

    assert client.call_json_url(
        "https://test.invalid/stock/{sku}",
        payload={"sku": "SKU-1"},
        method="GET",
    ) == {"data": {"stock": 8}}
    assert opener.requests[0].full_url == (
        "https://test.invalid/stock/SKU-1"
    )
    assert opener.requests[0].get_method() == "GET"
    assert opener.requests[0].data is None


def test_find_first_json_value_searches_nested_lists_and_dicts():
    data = {"items": [{"meta": {"availableStock": 7}}]}

    assert find_first_json_value(
        data,
        ("stock", "availableStock"),
    ) == 7


@pytest.mark.parametrize("body", [b"", b"not-json", b"[] trailing"])
def test_invalid_json_raises_boundary_error(body):
    client = make_client(FakeOpener(body=body))

    with pytest.raises(MallOrderHttpError, match="invalid JSON"):
        client.call_json_url("https://test.invalid/value")


@pytest.mark.parametrize(
    "opener",
    [
        FakeOpener(status=503),
        FakeOpener(error=urllib.error.URLError("offline")),
        FakeOpener(error=TimeoutError("timed out")),
    ],
)
def test_transport_failures_are_wrapped_without_network_io(opener):
    client = make_client(opener)

    with pytest.raises(MallOrderHttpError, match="request failed"):
        client.call_json_url("https://test.invalid/value")


def test_read_stock_formats_sku_and_returns_integer():
    opener = FakeOpener(body=b'{"inventory":{"stock":12}}')
    client = make_client(
        opener,
        stock_api_url="https://test.invalid/stock/{sku}",
        sku="SKU A",
    )

    assert client.read_stock() == 12
    assert opener.requests[0].full_url == (
        "https://test.invalid/stock/SKU%20A"
    )


def test_read_stock_rejects_configured_response_without_stock_field():
    client = make_client(
        FakeOpener(body=b'{"inventory":{}}'),
        stock_api_url="https://test.invalid/stock/{sku}",
    )

    with pytest.raises(MallOrderHttpError, match="stock"):
        client.read_stock()


def test_mock_payment_posts_order_payload_and_formats_url():
    opener = FakeOpener(body=b'{"ok":true}')
    client = make_client(
        opener,
        mock_pay_success_url=(
            "https://test.invalid/pay/{order_no}/{amount}/{sku}/{quantity}"
        ),
        sku="SKU A",
        quantity=2,
    )

    client.mock_payment_success("ORDER/1", 20.5)

    request = opener.requests[0]
    assert request.full_url == (
        "https://test.invalid/pay/ORDER%2F1/20.5/SKU%20A/2"
    )
    assert request.get_method() == "POST"
    assert json.loads(request.data.decode("utf-8")) == {
        "order_no": "ORDER/1",
        "amount": 20.5,
    }


@pytest.mark.parametrize(
    "status",
    ["待发货", "待配送", "WAIT_SHIP", "to_ship"],
)
def test_order_status_accepts_wait_ship_markers(status):
    body = json.dumps({"statusText": status}).encode("utf-8")
    client = make_client(
        FakeOpener(body=body),
        order_status_api_url=(
            "https://test.invalid/order/{order_no}"
        ),
    )

    assert client.assert_order_wait_ship("ORDER-1") is True


def test_order_status_rejects_missing_or_unexpected_state():
    client = make_client(
        FakeOpener(body=b'{"statusText":"cancelled"}'),
        order_status_api_url=(
            "https://test.invalid/order/{order_no}"
        ),
    )

    with pytest.raises(MallOrderHttpError, match="wait-ship"):
        client.assert_order_wait_ship("ORDER-1")


def test_flow_http_compatibility_wrappers_delegate_to_client():
    events = []

    class RecordingClient:
        def read_stock(self):
            events.append(("stock",))
            return 9

        def call_json_url(self, url, *, payload, method):
            events.append(("json", url, payload, method))
            return {"ok": True}

    page = object.__new__(mall_cli.MallOrderFlow)
    page.http = RecordingClient()

    assert page.read_stock_by_api() == 9
    assert page.call_json_url(
        "https://test.invalid/{sku}",
        payload={"sku": "SKU-1"},
        method="GET",
    ) == {"ok": True}
    assert page.find_first_json_value(
        {"nested": {"stock": 4}},
        ("stock",),
    ) == 4
    assert events == [
        ("stock",),
        (
            "json",
            "https://test.invalid/{sku}",
            {"sku": "SKU-1"},
            "GET",
        ),
    ]
