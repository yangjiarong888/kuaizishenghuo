# Mall Safe Decomposition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the oversized mall order script into testable HTTP, address, cart, and checkout units while enforcing explicit capabilities for every persistent business-data mutation.

**Architecture:** `MallOrderFlow` remains the compatible facade and composes focused mixins. CLI validation happens before Driver creation; a pure HTTP client isolates network behavior; destructive cart, order, message, address, and cancellation actions each require an explicit capability.

**Tech Stack:** Python 3.11, argparse, dataclasses, urllib, pytest, Appium Python Client, Selenium, Android UiAutomator2.

## Global Constraints

- Default execution and `--verify-navigation-only` must not change cart, address, order, payment, or message data.
- Normal navigation may still produce App analytics or recent-view records outside automation control.
- Cart changes require `--allow-cart-mutation`.
- Order creation requires `--submit-order`, `--allow-order-creation`, and an explicit positive `--max-payable`.
- Address writes continue to require `--allow-address-mutation`.
- Order cancellation requires `--cancel-created-order` and `--allow-order-cancellation`.
- Order IM is off by default and requires `--send-order-im` plus `--allow-order-message`.
- `wechat_mock` is test-hook-only; no real WeChat payment is added.
- Do not run cart mutation, order creation, payment, address write, message, or cancellation on the connected device without a fresh per-run user authorization.
- Every production batch follows RED→GREEN, focused tests, full offline regression, in-memory compilation, and a selective Git commit.

---

### Task 1: Capability-Based CLI and Navigation-Only Verification

**Files:**
- Create: `testcases/test_mall_order_safety.py`
- Modify: `scripts/run_mall_order_flow.py:223-3077`

**Interfaces:**
- Consumes: existing `build_parser()`, `validate_args(args)`, `main(argv=None)`, `MallOrderFlow`.
- Produces: CLI flags `--verify-navigation-only`, `--allow-cart-mutation`, `--add-to-cart-only`, `--allow-order-creation`, `--max-payable`, `--cancel-created-order`, `--allow-order-cancellation`, `--send-order-im`, `--allow-order-message`; `MallOrderFlow.run_navigation_verification(keyword: str) -> bool`.

- [x] **Step 1: Write failing default and capability tests**

```python
def test_mall_safety_defaults_are_non_destructive():
    args = mall_cli.build_parser().parse_args([])
    assert args.flow == "buy_now"
    assert args.verify_navigation_only is False
    assert args.allow_cart_mutation is False
    assert args.add_to_cart_only is False
    assert args.allow_order_creation is False
    assert args.max_payable is None
    assert args.cancel_created_order is False
    assert args.allow_order_cancellation is False
    assert args.send_order_im is False
    assert args.allow_order_message is False


@pytest.mark.parametrize(
    "argv",
    [
        ["--flow", "cart"],
        ["--flow", "both"],
        ["--add-to-cart-only"],
        ["--run-cart-delete"],
        ["--cart-delete-prepare-item"],
    ],
)
def test_cart_mutation_requires_explicit_capability(argv):
    args = mall_cli.build_parser().parse_args(argv)
    with pytest.raises(ValueError, match="allow-cart-mutation"):
        mall_cli.validate_args(args)


def test_submit_requires_order_capability_and_positive_limit():
    parser = mall_cli.build_parser()
    for argv in (
        ["--submit-order"],
        ["--submit-order", "--allow-order-creation"],
        ["--submit-order", "--allow-order-creation", "--max-payable", "0"],
    ):
        with pytest.raises(ValueError, match="max-payable|allow-order-creation"):
            mall_cli.validate_args(parser.parse_args(argv))


def test_add_only_rejects_submit_order():
    args = mall_cli.build_parser().parse_args(
        [
            "--add-to-cart-only",
            "--allow-cart-mutation",
            "--submit-order",
            "--allow-order-creation",
            "--max-payable",
            "20",
        ]
    )
    with pytest.raises(ValueError, match="add-to-cart-only"):
        mall_cli.validate_args(args)
```

- [x] **Step 2: Write failing cancellation, message, and navigation-only tests**

```python
def test_order_cancellation_requires_creation_and_its_own_capability():
    parser = mall_cli.build_parser()
    args = parser.parse_args(["--cancel-created-order"])
    with pytest.raises(ValueError, match="allow-order-cancellation"):
        mall_cli.validate_args(args)


def test_order_message_requires_its_own_capability():
    args = mall_cli.build_parser().parse_args(["--send-order-im"])
    with pytest.raises(ValueError, match="submit-order|allow-order-message"):
        mall_cli.validate_args(args)


@pytest.mark.parametrize(
    "extra",
    [
        ["--submit-order"],
        ["--allow-cart-mutation"],
        ["--add-to-cart-only"],
        ["--run-cart-delete"],
        ["--ensure-test-address"],
        ["--run-stockout"],
        ["--run-network-exception"],
        ["--send-order-im"],
    ],
)
def test_navigation_only_rejects_mutating_or_exception_modes(extra):
    args = mall_cli.build_parser().parse_args(["--verify-navigation-only", *extra])
    with pytest.raises(ValueError, match="navigation-only"):
        mall_cli.validate_args(args)
```

- [x] **Step 3: Prove invalid combinations fail before Driver creation**

```python
def test_invalid_cart_mode_returns_two_before_driver(monkeypatch):
    class ForbiddenManager:
        def __init__(self):
            raise AssertionError("Driver must not be created")

    monkeypatch.setattr(mall_cli, "DriverManager", ForbiddenManager)
    assert mall_cli.main(["--flow", "cart"]) == 2
```

- [x] **Step 4: Run the safety tests and verify RED**

```powershell
& '..\Scripts\python.exe' -m pytest testcases\test_mall_order_safety.py -q
```

Expected: failures for missing parser attributes and missing validation branches.

- [x] **Step 5: Add parser flags and validation**

```python
parser.add_argument("--verify-navigation-only", action="store_true")
parser.add_argument("--allow-cart-mutation", action="store_true")
parser.add_argument("--add-to-cart-only", action="store_true")
parser.add_argument("--allow-order-creation", action="store_true")
parser.add_argument("--max-payable", type=float, default=None)
parser.add_argument("--cancel-created-order", action="store_true")
parser.add_argument("--allow-order-cancellation", action="store_true")
parser.add_argument("--send-order-im", action="store_true")
parser.add_argument("--allow-order-message", action="store_true")
```

Also change the existing `--flow` default from `both` to `buy_now`.
This keeps an argument-free invocation free of cart mutations; explicit
`cart` and `both` selections remain capability-gated.

Implement exact validation:

```python
def validate_args(args) -> None:
    address_mutation = any(
        (
            args.ensure_test_address,
            args.force_add_test_address,
            args.edit_test_address,
            args.copy_test_address,
            args.add_test_address_only,
        )
    )
    if address_mutation and not args.allow_address_mutation:
        raise ValueError(
            "address mutation requires explicit --allow-address-mutation"
        )

    cart_mutation = (
        args.flow in ("cart", "both")
        or args.add_to_cart_only
        or args.run_cart_delete
        or args.cart_delete_prepare_item
    )
    if cart_mutation and not args.allow_cart_mutation:
        raise ValueError(
            "cart mutation requires explicit --allow-cart-mutation"
        )
    if args.add_to_cart_only and args.submit_order:
        raise ValueError(
            "--add-to-cart-only conflicts with --submit-order"
        )

    if args.submit_order:
        if not args.allow_order_creation:
            raise ValueError(
                "order creation requires explicit --allow-order-creation"
            )
        if args.max_payable is None or args.max_payable <= 0:
            raise ValueError(
                "order creation requires positive --max-payable"
            )

    if args.cancel_created_order and not (
        args.submit_order and args.allow_order_cancellation
    ):
        raise ValueError(
            "order cancellation requires --submit-order and "
            "--allow-order-cancellation"
        )

    if args.send_order_im and not (
        args.submit_order and args.allow_order_message
    ):
        raise ValueError(
            "order message requires --submit-order and "
            "--allow-order-message"
        )
    if args.send_order_im and args.skip_order_im:
        raise ValueError(
            "--send-order-im conflicts with --skip-order-im"
        )

    if args.verify_navigation_only:
        blocked = any(
            (
                args.submit_order,
                args.allow_cart_mutation,
                address_mutation,
                args.run_cart_delete,
                args.run_stockout,
                args.run_network_exception,
                args.send_order_im,
                args.cancel_created_order,
            )
        )
        if blocked:
            raise ValueError(
                "--verify-navigation-only conflicts with mutating or "
                "exception-test options"
            )
```

- [x] **Step 6: Write a failing navigation dispatch test**

```python
def test_navigation_only_dispatches_no_mutating_flow(monkeypatch):
    events = []

    class FakeFlow:
        def __init__(self, driver, **kwargs):
            events.append(("init", kwargs["send_im_after_order"]))

        def run_navigation_verification(self, keyword):
            events.append(("navigation", keyword))
            return True

    install_fake_driver_boundaries(monkeypatch, FakeFlow)
    assert mall_cli.main(
        [
            "--verify-navigation-only",
            "--product-source",
            "search",
            "--keyword",
            "可乐",
        ]
    ) == 0
    assert events == [("init", False), ("navigation", "可乐")]
```

Add this test-only helper above the test:

```python
def install_fake_driver_boundaries(monkeypatch, flow_class):
    class FakeManager:
        def get_driver(self, *, session_name):
            return object()

        def close_driver(self, *, session_name):
            raise AssertionError(
                "navigation test must not close the fake driver"
            )

    monkeypatch.setattr(mall_cli, "DriverManager", FakeManager)
    monkeypatch.setattr(mall_cli, "MallOrderFlow", flow_class)
```

- [x] **Step 7: Implement navigation-only behavior**

```python
from commons.diagnostics import capture_failure


def run_navigation_verification(self, keyword: str) -> bool:
    product = self.open_detail_and_snapshot(keyword)
    if not product.name:
        raise AssertionError("商品详情未读取到商品名称")
    capture_failure(
        self.driver,
        "mall_navigation_verification",
    )
    self.safe_back_to_mall()
    return True
```

Dispatch it before all other flows:

```python
if args.verify_navigation_only:
    page.run_navigation_verification(args.keyword)
    ok = True
    return 0
```

Pass safe constructor values:

```python
send_im_after_order=args.send_order_im and not args.skip_order_im
```

- [x] **Step 8: Run focused and full offline verification**

```powershell
& '..\Scripts\python.exe' -m pytest `
  testcases\test_mall_order_cli.py `
  testcases\test_mall_order_types.py `
  testcases\test_mall_order_safety.py -q
& '..\Scripts\python.exe' -m pytest -m 'not device' -q
```

Expected: all focused tests pass; full suite has zero failures.

- [x] **Step 9: Commit Task 1**

```powershell
git add -- scripts/run_mall_order_flow.py testcases/test_mall_order_safety.py
git diff --cached --check
git commit -m "fix: enforce mall mutation capabilities"
```

---

### Task 2: Pure Mall HTTP Client

**Files:**
- Create: `flows/mall_order_http.py`
- Create: `testcases/test_mall_order_http.py`
- Modify: `scripts/run_mall_order_flow.py:450-458`
- Modify: `scripts/run_mall_order_flow.py:1348-1468`

**Interfaces:**
- Consumes: URL templates, `sku`, `quantity`, `SubmitResult`.
- Produces: `MallOrderHttpClient`, compatible `call_json_url(url_template, *, payload=None, method="POST", timeout=12.0) -> Any`, `find_first_json_value(data: Any, keys: Sequence[str]) -> Optional[Any]`, `read_stock() -> Optional[int]`, `mock_payment_success(order_no: str, amount: float) -> Any`, `assert_order_wait_ship(order_no: str) -> bool`.

- [x] **Step 1: Write failing pure HTTP tests**

```python
def test_call_json_url_decodes_json_with_injected_opener():
    opener = FakeOpener(
        body=b'{"data":{"stock":8}}',
        status=200,
    )
    client = MallOrderHttpClient(
        sku="SKU-1",
        quantity=2,
        stock_api_url="https://test.invalid/stock/{sku}",
        order_status_api_url=None,
        mock_pay_success_url=None,
        opener=opener,
    )
    assert client.call_json_url(
        "https://test.invalid/stock/SKU-1"
    ) == {"data": {"stock": 8}}


def test_find_first_json_value_searches_nested_lists_and_dicts():
    data = {"items": [{"meta": {"availableStock": 7}}]}
    assert find_first_json_value(
        data,
        ("stock", "availableStock"),
    ) == 7


@pytest.mark.parametrize("body", [b"", b"not-json", b"[] trailing"])
def test_invalid_json_raises_boundary_error(body):
    client = make_client(FakeOpener(body=body, status=200))
    with pytest.raises(MallOrderHttpError, match="invalid JSON"):
        client.call_json_url("https://test.invalid/value")


@pytest.mark.parametrize(
    "error",
    [
        urllib.error.URLError("offline"),
        TimeoutError("timed out"),
    ],
)
def test_transport_failures_are_wrapped_without_network_io(error):
    client = make_client(
        FakeOpener(body=b"", status=0, error=error)
    )
    with pytest.raises(MallOrderHttpError, match="request failed"):
        client.call_json_url("https://test.invalid/value")
```

Use these test-only fakes so the tests never perform network I/O:

```python
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
    def __init__(self, *, body, status, error=None):
        self.body = body
        self.status = status
        self.error = error
        self.urls = []
        self.timeouts = []

    def __call__(self, url, *, timeout):
        self.urls.append(url)
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
```

- [x] **Step 2: Write failing stock and order-status tests**

```python
def test_read_stock_formats_sku_and_returns_integer():
    client = make_client(
        FakeOpener(body=b'{"inventory":{"stock":12}}', status=200),
        stock_api_url="https://test.invalid/stock/{sku}",
        sku="SKU A",
    )
    assert client.read_stock() == 12
    assert client.opener.urls == [
        "https://test.invalid/stock/SKU%20A"
    ]


def test_read_stock_rejects_configured_response_without_stock_field():
    client = make_client(
        FakeOpener(body=b'{"inventory":{}}', status=200),
        stock_api_url="https://test.invalid/stock/{sku}",
    )
    with pytest.raises(MallOrderHttpError, match="stock"):
        client.read_stock()


def test_order_status_must_reach_wait_ship_state():
    client = make_client(
        FakeOpener(body=b'{"statusText":"待发货"}', status=200),
        order_status_api_url="https://test.invalid/order/{order_no}",
    )
    client.assert_order_wait_ship("ORDER-1")
```

- [x] **Step 3: Run HTTP tests and verify RED**

```powershell
& '..\Scripts\python.exe' -m pytest testcases\test_mall_order_http.py -q
```

Expected: import failure for missing `flows.mall_order_http`; add only importable class/function skeletons if needed, then verify behavior assertions fail.

- [x] **Step 4: Implement the client**

```python
class MallOrderHttpError(RuntimeError):
    pass


@dataclass
class MallOrderHttpClient:
    sku: str
    quantity: int
    stock_api_url: Optional[str]
    order_status_api_url: Optional[str]
    mock_pay_success_url: Optional[str]
    opener: Callable[..., Any] = urllib.request.urlopen

    def call_json_url(
        self,
        url: str,
        *,
        timeout: float = 10.0,
    ) -> Any:
        try:
            with self.opener(url, timeout=timeout) as response:
                body = response.read()
        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
        ) as exc:
            raise MallOrderHttpError(
                f"request failed error_type={type(exc).__name__}"
            ) from exc
        try:
            return json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MallOrderHttpError("invalid JSON response") from exc
```

Implement recursive `find_first_json_value()`, URL placeholder quoting with `urllib.parse.quote`, `urllib.request.Request` construction that preserves the existing GET/POST and JSON-body contract, integer stock parsing, mock-payment URL formatting, and order-state validation using the existing accepted markers. If a stock URL is configured but its response has no recognized stock field, raise `MallOrderHttpError` rather than silently returning `None`.

- [x] **Step 5: Delegate from `MallOrderFlow` without breaking public names**

Create the client in `MallOrderFlow.__init__`:

```python
self.http = MallOrderHttpClient(
    sku=self.sku,
    quantity=self.quantity,
    stock_api_url=self.stock_api_url,
    order_status_api_url=self.order_status_api_url,
    mock_pay_success_url=self.mock_pay_success_url,
)
```

Keep compatibility wrappers:

```python
def read_stock_by_api(self) -> Optional[int]:
    return self.http.read_stock()


@staticmethod
def find_first_json_value(data, keys):
    return find_first_json_value(data, keys)
```

- [x] **Step 6: Run focused and full tests**

```powershell
& '..\Scripts\python.exe' -m pytest `
  testcases\test_mall_order_http.py `
  testcases\test_mall_order_cli.py `
  testcases\test_mall_order_safety.py -q
& '..\Scripts\python.exe' -m pytest -m 'not device' -q
```

- [x] **Step 7: Commit Task 2**

```powershell
git add -- flows/mall_order_http.py scripts/run_mall_order_flow.py testcases/test_mall_order_http.py
git diff --cached --check
git commit -m "refactor: extract mall HTTP boundary"
```

---

### Task 3: Cart Mixin and Add-Only Flow

**Files:**
- Create: `pages/mall_order_cart_mixin.py`
- Create: `testcases/test_mall_order_cart.py`
- Modify: `scripts/run_mall_order_flow.py:2260-2664`

**Interfaces:**
- Consumes: common click/read helpers on `MallOrderFlow`, `ProductSnapshot`, shop locator constants.
- Produces: `MallOrderCartMixin`, existing cart public methods, `run_add_to_cart_only(keyword: str) -> bool`.

- [x] **Step 1: Write failing add-only behavior tests**

```python
class RecordingCart(MallOrderCartMixin):
    def __init__(self):
        self.events = []

    def open_detail_and_snapshot(self, keyword):
        self.events.append(("detail", keyword))
        return ProductSnapshot(
            name="测试商品",
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
        return True


def test_add_to_cart_only_stops_after_cart_assertion():
    page = RecordingCart()
    assert page.run_add_to_cart_only("可乐")
    assert page.events == [
        ("detail", "可乐"),
        ("add", "SKU-1"),
        ("assert-cart", "测试商品"),
    ]
```

- [x] **Step 2: Write a failing compatibility surface test**

```python
@pytest.mark.parametrize(
    "name",
    [
        "open_cart_page",
        "cart_delete_by_manage",
        "cart_delete_by_minus",
        "cart_delete_by_swipe",
        "run_cart_delete_case",
        "add_cart_to_checkout_exact_specs",
        "run_cart_flow",
    ],
)
def test_cart_mixin_keeps_public_methods(name):
    assert callable(getattr(MallOrderCartMixin, name))
```

- [x] **Step 3: Run cart tests and verify RED**

```powershell
& '..\Scripts\python.exe' -m pytest testcases\test_mall_order_cart.py -q
```

Expected: import failure for missing `pages.mall_order_cart_mixin`, then missing-method failures after an importable skeleton exists.

- [x] **Step 4: Move the exact cart method set unchanged**

Create:

```python
class MallOrderCartMixin:
    """Mall cart actions; requires common helpers from MallOrderFlow."""
```

Move these existing methods without changing their bodies:

```text
cart_page_visible
cart_manage_mode_visible
open_cart_page
ensure_cart_normal_mode
enter_cart_manage_mode
cart_select_all_items
cart_select_first_item
cart_confirm_delete_popup
cart_assert_delete_without_selection_toast
cart_delete_by_manage
cart_delete_by_minus
cart_swipe_left_first_item
cart_delete_by_swipe
prepare_cart_delete_item
run_cart_delete_case
add_cart_to_checkout_exact_specs
run_cart_flow
```

Import the exact locator constants used by those bodies from `pages.shop_locators`.

- [x] **Step 5: Implement add-only helpers**

```python
def add_product_to_cart_exact_specs(
    self,
    product: ProductSnapshot,
) -> ProductSnapshot:
    if not self.click_by_id_or_label(
        SHOP_ID_MALL_ADD_SHOP_CAR,
        ("加入购物车", "加购物车"),
        desc="加入购物车",
        y_min_ratio=0.45,
        y_max_ratio=1.0,
    ):
        raise AssertionError("未找到加入购物车按钮")
    time.sleep(0.8)
    if self._login_like_screen_visible():
        raise AssertionError("加入购物车后进入登录页，前置条件不满足：用户未登录")
    selected_stock = self.select_specs_and_quantity()
    if product.stock_before is None and selected_stock is not None:
        product.stock_before = selected_stock
    if self.wait_page_contains_any(STOCKOUT_MARKERS, timeout=2.0):
        raise AssertionError("库存充足商品加入购物车时提示库存不足")
    return product


def run_add_to_cart_only(self, keyword: str) -> bool:
    product = self.open_detail_and_snapshot(keyword)
    product = self.add_product_to_cart_exact_specs(product)
    self.assert_cart_contains_product(product)
    return True
```

`assert_cart_contains_product()` opens the cart and requires the exact product name or configured expected-name fragment to be visible; it does not delete the item.

- [x] **Step 6: Compose the mixin and dispatch add-only**

```python
class MallOrderFlow(MallOrderCartMixin, ShopBusinessPage):
    ...
```

In `main()` before the normal flows:

```python
if args.add_to_cart_only:
    page.run_add_to_cart_only(args.keyword)
    ok = True
    return 0
```

- [x] **Step 7: Run focused and full tests**

```powershell
& '..\Scripts\python.exe' -m pytest `
  testcases\test_mall_order_cart.py `
  testcases\test_mall_order_safety.py -q
& '..\Scripts\python.exe' -m pytest -m 'not device' -q
```

- [x] **Step 8: Commit Task 3**

```powershell
git add -- pages/mall_order_cart_mixin.py scripts/run_mall_order_flow.py testcases/test_mall_order_cart.py
git diff --cached --check
git commit -m "refactor: extract mall cart flow"
```

---

### Task 4: Address Mixin

**Files:**
- Create: `pages/mall_order_address_mixin.py`
- Create: `testcases/test_mall_order_address.py`
- Modify: `scripts/run_mall_order_flow.py:148-217`
- Modify: `scripts/run_mall_order_flow.py:1597-2257`

**Interfaces:**
- Consumes: common driver/click/type helpers and address configuration attributes on `MallOrderFlow`.
- Produces: `MallOrderAddressMixin` with the complete existing address public surface.

- [x] **Step 1: Write a failing compatibility and read-only classification test**

```python
@pytest.mark.parametrize(
    "name",
    [
        "page_has_target_address",
        "is_address_search_page",
        "is_address_edit_form",
        "select_existing_target_address",
        "copy_target_address_in_current_parent",
        "edit_test_address_in_current_parent",
        "add_test_address",
        "ensure_test_address_from_checkout_flow",
        "ensure_test_address_from_my_page_flow",
    ],
)
def test_address_mixin_keeps_public_methods(name):
    assert callable(getattr(MallOrderAddressMixin, name))


def test_target_address_labels_ignore_empty_values():
    page = object.__new__(MallOrderAddressMixin)
    page.address_name = "Tester"
    page.address_phone = ""
    page.address_query = "Manila"
    page.address_detail = ""
    assert page.target_address_labels() == ("Tester", "Manila")
```

- [x] **Step 2: Run address tests and verify RED**

```powershell
& '..\Scripts\python.exe' -m pytest testcases\test_mall_order_address.py -q
```

- [x] **Step 3: Move address constants and methods unchanged**

Move the address marker tuples and the exact method range from `visible_edit_texts()` through `ensure_test_address_from_my_page_flow()` into:

```python
class MallOrderAddressMixin:
    """Address selection and mutation actions for MallOrderFlow."""
```

The complete method set is:

```text
visible_edit_texts
edit_text_value
type_text_element
tap_ratio
scroll_vertical
type_into_field_near_label
target_address_labels
page_has_target_address
is_address_search_page
wait_address_search_page
is_address_edit_form
wait_address_edit_form
click_bottom_my_tab
open_address_manage_from_my_page
open_address_sheet_from_checkout
select_existing_target_address
find_target_address_anchor
address_anchor_row_y_ratio
open_target_address_edit_form
copy_target_address_in_current_parent
finish_address_copy_parent
edit_test_address_in_current_parent
open_add_address_form
open_address_search_from_edit
type_into_address_map_search
search_and_select_address_location
fill_test_address_form
save_test_address_form
add_test_address
ensure_test_address_from_checkout_flow
ensure_test_address_from_my_page_flow
```

- [x] **Step 4: Compose the mixin**

```python
class MallOrderFlow(
    MallOrderAddressMixin,
    MallOrderCartMixin,
    ShopBusinessPage,
):
    ...
```

Do not change CLI address capability validation or any locator during this task.

- [x] **Step 5: Run focused and full tests**

```powershell
& '..\Scripts\python.exe' -m pytest `
  testcases\test_mall_order_address.py `
  testcases\test_mall_order_safety.py `
  testcases\test_mall_order_cli.py -q
& '..\Scripts\python.exe' -m pytest -m 'not device' -q
```

- [x] **Step 6: Commit Task 4**

```powershell
git add -- pages/mall_order_address_mixin.py scripts/run_mall_order_flow.py testcases/test_mall_order_address.py
git diff --cached --check
git commit -m "refactor: extract mall address flow"
```

---

### Task 5: Checkout Mixin, Amount Ceiling, Explicit Message, and Cancellation

**Files:**
- Create: `pages/mall_order_checkout_mixin.py`
- Create: `testcases/test_mall_order_checkout.py`
- Modify: `scripts/run_mall_order_flow.py:74-147`
- Modify: `scripts/run_mall_order_flow.py:656-1594`
- Modify: `scripts/run_mall_order_flow.py:2617-2640`

**Interfaces:**
- Consumes: `ProductSnapshot`, `AmountSnapshot`, `SubmitResult`, `MallOrderHttpClient`, common driver helpers.
- Produces: `MallOrderCheckoutMixin`, `assert_within_payable_limit(amounts: AmountSnapshot) -> None`, `cancel_created_order(submit: SubmitResult) -> None`, guarded `finish_checkout(...)`.

- [x] **Step 1: Write failing amount-ceiling tests**

```python
class CheckoutRecorder(MallOrderCheckoutMixin):
    def __init__(self, payable, max_payable):
        self.max_payable = max_payable
        self.payable = payable
        self.events = []
        self.ensure_test_address = False
        self.send_im_after_order = False
        self.cancel_after_order = False

    def dismiss_checkout_upsell_if_visible(self):
        pass

    def assert_checkout_matches_detail(self, product):
        return AmountSnapshot(10.0, 0.0, 0.0, self.payable)

    def apply_mall_platform_coupon_if_needed(self):
        return False

    def apply_checkout_preferences(self):
        pass

    def read_amounts(self, product):
        return AmountSnapshot(10.0, 0.0, 0.0, self.payable)

    def pick_tomorrow_random_preorder_time_if_needed(self):
        return None

    def submit_order(self, amounts):
        self.events.append("submit")
        return SubmitResult("ORDER-1", amounts.payable)

    def pay_and_assert(self, submit, product):
        self.events.append("pay")


def test_amount_equal_to_ceiling_can_submit(product):
    page = CheckoutRecorder(payable=20.0, max_payable=20.0)
    page.finish_checkout(product, submit_order=True)
    assert page.events == ["submit", "pay"]


def test_amount_above_ceiling_stops_before_submit(product):
    page = CheckoutRecorder(payable=20.01, max_payable=20.0)
    with pytest.raises(AssertionError, match="max-payable"):
        page.finish_checkout(product, submit_order=True)
    assert page.events == []
```

- [x] **Step 2: Write failing message-default and cancellation-order tests**

```python
def test_order_message_is_off_by_default(product):
    page = CheckoutRecorder(payable=10.0, max_payable=20.0)
    page.send_order_cancel_im_if_needed = lambda submit: page.events.append("im")
    page.finish_checkout(product, submit_order=True)
    assert "im" not in page.events


def test_explicit_cancellation_runs_after_order_assertions(product):
    page = CheckoutRecorder(payable=10.0, max_payable=20.0)
    page.cancel_after_order = True
    page.cancel_created_order = lambda submit: page.events.append(
        ("cancel", submit.order_no)
    )
    page.finish_checkout(product, submit_order=True)
    assert page.events == [
        "submit",
        "pay",
        ("cancel", "ORDER-1"),
    ]


def test_cancellation_stops_when_created_order_number_is_missing():
    page = object.__new__(MallOrderCheckoutMixin)
    page.ensure_order_detail_page = lambda: None
    page.click_labels = lambda *args, **kwargs: pytest.fail(
        "must not click cancellation without an order number"
    )
    submit = SubmitResult("", 10.0)
    with pytest.raises(AssertionError, match="订单号"):
        page.cancel_created_order(submit)
```

- [x] **Step 3: Run checkout tests and verify RED**

```powershell
& '..\Scripts\python.exe' -m pytest testcases\test_mall_order_checkout.py -q
```

- [x] **Step 4: Move checkout constants and methods**

Create:

```python
class MallOrderCheckoutMixin:
    """Checkout, payment, order assertion, and optional cleanup."""
```

Move the existing methods from the preorder-time section through the order-detail IM section:

```text
tomorrow_date_fragments
looks_like_time_slot_label
element_label
open_preorder_time_sheet
tap_tomorrow_in_time_sheet
collect_time_slot_elements
pick_random_time_slot
pick_tomorrow_random_preorder_time_if_needed
first_money_after
coupon_available_count
first_money_between_labels
read_platform_coupon_amount
click_first_coupon_candidate
apply_mall_platform_coupon_if_needed
find_checkout_anchor
scroll_checkout_until_visible
checkout_anchor_y_ratio
set_pickup_code_if_needed
set_notify_method_if_needed
fill_remark_if_needed
select_remark_quick_notes
apply_checkout_preferences
read_amounts
assert_checkout_matches_detail
drain_logcat
read_logcat_blob
extract_order_no
assert_preorder_api_called
submit_order
select_wechat_pay
select_cash_on_delivery_pay
call_json_url
find_first_json_value
mock_payment_success
assert_order_wait_ship
assert_stock_decremented
pay_and_assert
ensure_order_detail_page
order_no_from_detail_or_submit
open_im_from_order_detail
find_im_input
paste_and_send_im_message
send_order_cancel_im_if_needed
finish_checkout
```

Network wrappers delegate to `self.http`; do not duplicate urllib logic.

- [x] **Step 5: Add the amount ceiling and explicit side effects**

```python
def assert_within_payable_limit(
    self,
    amounts: AmountSnapshot,
) -> None:
    if self.max_payable is None or self.max_payable <= 0:
        raise AssertionError(
            "真实提交缺少正数 --max-payable"
        )
    if amounts.payable > self.max_payable:
        raise AssertionError(
            "确认页实付 %.2f 超过 --max-payable %.2f"
            % (amounts.payable, self.max_payable)
        )
```

In `finish_checkout()`:

```python
if not submit_order:
    logger.info("未授权真实提交，停止在确认订单页")
    return
self.assert_within_payable_limit(amounts)
submit = self.submit_order(amounts)
self.pay_and_assert(submit, product)
if self.send_im_after_order:
    self.send_order_cancel_im_if_needed(submit)
if self.cancel_after_order:
    self.cancel_created_order(submit)
```

- [x] **Step 6: Implement explicit order cancellation**

```python
def cancel_created_order(self, submit: SubmitResult) -> None:
    if not submit.order_no:
        raise AssertionError(
            "本次创建订单未解析到订单号，禁止自动取消；需要人工检查"
        )
    self.ensure_order_detail_page()
    if not self.click_labels(
        ("取消订单", "申请取消"),
        desc="取消本次测试订单",
        y_min_ratio=0.20,
        y_max_ratio=1.0,
    ):
        raise AssertionError(
            f"订单 {submit.order_no} 未找到取消入口，需要人工处理"
        )
    self.click_labels(
        ("测试订单", "不想要了", "其他"),
        desc="选择取消原因",
        y_min_ratio=0.15,
        y_max_ratio=1.0,
    )
    if not self.click_labels(
        ("确认取消", "确定", "提交"),
        desc="确认取消本次测试订单",
        y_min_ratio=0.40,
        y_max_ratio=1.0,
    ):
        raise AssertionError(
            f"订单 {submit.order_no} 取消确认失败，需要人工处理"
        )
    self.assert_page_contains_any(
        ("已取消", "取消成功", "订单关闭"),
        f"订单 {submit.order_no} 未确认取消成功，需要人工处理",
        timeout=20.0,
    )
```

The method never retries order submission.

- [x] **Step 7: Compose the final facade and constructor fields**

```python
class MallOrderFlow(
    MallOrderAddressMixin,
    MallOrderCartMixin,
    MallOrderCheckoutMixin,
    ShopBusinessPage,
):
    ...
```

Add keyword-only constructor inputs:

```python
max_payable: Optional[float],
cancel_after_order: bool,
send_im_after_order: bool,
```

Pass:

```python
max_payable=args.max_payable,
cancel_after_order=args.cancel_created_order,
send_im_after_order=args.send_order_im and not args.skip_order_im,
```

- [x] **Step 8: Run focused and full tests**

```powershell
& '..\Scripts\python.exe' -m pytest `
  testcases\test_mall_order_checkout.py `
  testcases\test_mall_order_http.py `
  testcases\test_mall_order_cart.py `
  testcases\test_mall_order_address.py `
  testcases\test_mall_order_safety.py `
  testcases\test_mall_order_cli.py `
  testcases\test_mall_order_types.py -q
& '..\Scripts\python.exe' -m pytest -m 'not device' -q
```

- [x] **Step 9: Commit Task 5**

```powershell
git add -- pages/mall_order_checkout_mixin.py scripts/run_mall_order_flow.py testcases/test_mall_order_checkout.py
git diff --cached --check
git commit -m "refactor: extract guarded mall checkout"
```

---

### Task 6: Static Verification, Read-Only Device Run, and Review Report

**Files:**
- Create: `docs/reviews/2026-07-27-mall-safe-decomposition-review.md`
- Verify: all Task 1-5 source and test files.

**Interfaces:**
- Consumes: completed CLI, facade, mixins, HTTP client, connected Android device, Appium 4723.
- Produces: reproducible offline evidence, strict zero-business-data device evidence, residual-risk counts.

- [x] **Step 1: Run all focused and full offline tests**

```powershell
$mallTests = Get-ChildItem testcases -Filter 'test_mall_order_*.py' |
    Select-Object -ExpandProperty FullName
& '..\Scripts\python.exe' -m pytest $mallTests -q
& '..\Scripts\python.exe' -m pytest -m 'not device' -q
```

Record exact pass/fail/deselected counts.

- [x] **Step 2: Compile all Python sources in memory**

```powershell
$compileCode = @'
from pathlib import Path
files = sorted(p for p in Path(".").rglob("*.py") if "__pycache__" not in p.parts)
for path in files:
    compile(path.read_text(encoding="utf-8-sig"), str(path), "exec")
print(f"compiled={len(files)}")
'@
& '..\Scripts\python.exe' -c $compileCode
```

- [x] **Step 3: Scan safety defaults and residual risks**

```powershell
rg -n 'send_im_after_order=True|max_payable\\s*=\\s*[0-9]|allow_.*=True' pages flows scripts --glob '*.py'
rg -n 'time\\.sleep\\(' pages flows scripts/run_mall_order_flow.py --glob 'mall_order_*.py'
rg -n 'except\\s+(Exception|BaseException)|except\\s*:' pages flows scripts/run_mall_order_flow.py --glob 'mall_order_*.py'
```

No fixed authorization defaults are allowed. Record wait and broad-exception counts rather than claiming they are all defects.

- [x] **Step 4: Reconfirm device and Appium**

```powershell
& 'C:\Users\18718\AppData\Local\Android\Sdk\platform-tools\adb.exe' devices -l
Invoke-RestMethod -Uri 'http://127.0.0.1:4723/status'
```

Expected: device `P7T4XC99CYAEYL4H` is `device`; Appium reports `ready: true`.

- [ ] **Step 5: Run only the strict navigation mode on the device**

```powershell
& '..\Scripts\python.exe' scripts\run_mall_order_flow.py `
  --verify-navigation-only `
  --product-source search `
  --keyword "可乐" `
  --session mall_navigation_verify `
  --start-mode activate `
  --quit-driver
```

Forbidden in this command: `--allow-cart-mutation`, `--submit-order`, address flags, `--run-cart-delete`, `--run-stockout`, `--run-network-exception`, message flags, or cancellation flags.

- [ ] **Step 6: Inspect evidence and device state**

Verify:

- exit code `0`;
- screenshot exists;
- page source exists and phone/code-like values are redacted;
- no new cart, address, order, payment, or message action appears in logs;
- device returns to a non-destructive mall/home state.

Do not infer checkout, address, cart, payment, or cancellation compatibility from this run.

- [ ] **Step 7: Write the review report**

The report must include:

- exact offline test and compile counts;
- device model, serial, Appium version, command, exit code, Activity, screenshot and sanitized XML paths;
- explicit statement that no cart mutation or order creation was authorized;
- before/after line counts for `scripts/run_mall_order_flow.py`;
- remaining fixed waits, broad exceptions, and files over 800 lines;
- sections marked not device-verified;
- the exact capability set required for future add-only and real-order runs.

- [ ] **Step 8: Commit the report**

```powershell
git add -- docs/reviews/2026-07-27-mall-safe-decomposition-review.md
git diff --cached --check
git commit -m "docs: record mall decomposition verification"
```
