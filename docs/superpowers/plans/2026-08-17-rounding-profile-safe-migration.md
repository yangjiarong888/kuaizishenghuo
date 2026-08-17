# Rounding and Profile Safe Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate COD rounding, read-only profile navigation, and safe workflow results from the old branch without restoring monolithic checkout code, automatic password entry, or default real-order behavior.

**Architecture:** Extract new capabilities into focused modules and compose them with the current mall and takeout Mixins. All CLI validation occurs before Driver creation; order creation remains opt-in and bounded, while profile automation remains read-only. The old branch is a reference only and is never merged wholesale.

**Tech Stack:** Python 3.11, pytest, Appium Python client, Selenium, argparse, dataclasses.

## Global Constraints

- Work on `codex/rounding-profile-safe-migration` in the existing repository; do not create another worktree.
- Do not connect to a phone or emulator. Run only default/offline pytest suites.
- Never add a default payment password or an automatic balance-password input path.
- Mall and takeout default to no order submission.
- COD rounding requires explicit `--rounding-payment`; real submission additionally requires the existing order-creation gates and a positive maximum payable amount.
- Profile automation is read-only: no phone/profile/password/fingerprint/cancellation/privacy/cache mutations.
- Preserve the existing mall Mixins, takeout manual balance-payment wait, shipping flow, diagnostic redaction, and device-test exclusion.
- Use `apply_patch` for edits, TDD for every production behavior, and scoped commits after each task.

---

### Task 1: Shared COD Rounding Core

**Files:**
- Create: `pages/rounding_payment.py`
- Create: `testcases/test_rounding_payment.py`

**Interfaces:**
- Produces: `RoundingOption(amount: int, change: float)`.
- Produces: `compute_rounding_options(payable: float, limit: int = 3) -> list[RoundingOption]`.
- Produces: `parse_checkout_money(text: str) -> float | None`.
- Produces: `RoundingPaymentMixin.select_checkout_rounding_payment(*, payable: float | None = None, custom_amount: float | None = None) -> RoundingOption`.
- Requires host pages to expose `driver` and may use `page_texts`, `_checkout_page_texts`, `click_labels`, or `_coord_tap_or_click` when present.

- [ ] **Step 1: Write pure-domain failing tests**

```python
def test_rounding_options_for_370_are_strictly_higher_and_ordered():
    assert compute_rounding_options(370) == [
        RoundingOption(400, 30),
        RoundingOption(500, 130),
        RoundingOption(1000, 630),
    ]

def test_exact_thousand_has_no_rounding_options():
    assert compute_rounding_options(2000) == []

def test_non_positive_payable_has_no_rounding_options():
    assert compute_rounding_options(0) == []
```

- [ ] **Step 2: Run RED for the missing module**

Run: `python -m pytest -q testcases/test_rounding_payment.py`

Expected: collection fails with `ModuleNotFoundError: pages.rounding_payment`.

- [ ] **Step 3: Implement immutable value type and pure calculations**

```python
@dataclass(frozen=True)
class RoundingOption:
    amount: int
    change: float

def compute_rounding_options(payable: float, limit: int = 3) -> list[RoundingOption]:
    if payable <= 0 or (float(payable).is_integer() and int(payable) % 1000 == 0):
        return []
    # Return unique ascending integer candidates strictly greater than payable.
```

Implementation must reject `limit <= 0` with an empty list and must round `change` to two decimals.

- [ ] **Step 4: Add failing parsing and UI-contract tests**

```python
def test_parse_checkout_money_requires_a_money_or_total_hint():
    assert parse_checkout_money("应付 ₱1,450.25") == 1450.25
    assert parse_checkout_money("商品编号 1450") is None

def test_custom_rounding_rejects_decimal_or_non_increasing_amount():
    page = FakeRoundingPage(total=1450)
    with pytest.raises(AssertionError):
        page.select_checkout_rounding_payment(payable=1450, custom_amount=1450)
    with pytest.raises(AssertionError):
        page.select_checkout_rounding_payment(payable=1450, custom_amount=2500.5)

def test_selection_fails_when_readback_does_not_match():
    page = FakeRoundingPage(total=1450, never_updates=True)
    with pytest.raises(AssertionError, match="取整|回读"):
        page.select_checkout_rounding_payment(payable=1450)
```

- [ ] **Step 5: Implement the minimal fail-closed UI mixin**

The mixin must:

```python
def select_checkout_rounding_payment(
    self,
    *,
    payable: float | None = None,
    custom_amount: float | None = None,
) -> RoundingOption:
    resolved = payable if payable is not None else self.checkout_payable_amount()
    if resolved is None or resolved <= 0:
        raise AssertionError("无法确认取整前应付金额")
    option = self._resolve_rounding_option(resolved, custom_amount)
    self.assert_rounding_module_visible()
    self._click_unique_rounding_option(option)
    if not self._rounding_option_selected(option):
        raise AssertionError("取整金额或找零回读不一致")
    return option
```

All queries must return exactly one visible and enabled target. No coordinates may be used unless the target element itself has already been uniquely identified.

- [ ] **Step 6: Run GREEN and focused regression**

Run: `python -m pytest -q testcases/test_rounding_payment.py testcases/test_mall_order_types.py`

Expected: all selected tests pass.

- [ ] **Step 7: Commit Task 1**

```bash
git add pages/rounding_payment.py testcases/test_rounding_payment.py
git commit -m "feat: add safe COD rounding core"
```

### Task 2: Compose Rounding into Current Mall Mixins

**Files:**
- Modify: `scripts/run_mall_order_flow.py:50-170,753-1185`
- Modify: `pages/mall_order_checkout_mixin.py:986-1040`
- Modify: `testcases/test_mall_order_cli.py`
- Create: `testcases/test_mall_order_rounding.py`

**Interfaces:**
- Consumes: Task 1 `RoundingPaymentMixin` and `RoundingOption`.
- Produces: `MallOrderFlow(..., rounding_payment: bool, rounding_amount: float | None, ...)`.
- Produces CLI flags `--rounding-payment` and `--rounding-amount`.
- `finish_checkout` continues returning `None` and keeps `submit_order: bool` explicit.

- [ ] **Step 1: Write RED for CLI validation before Driver creation**

```python
@pytest.mark.parametrize("argv", [
    ["--rounding-amount", "500"],
    ["--rounding-payment", "--payment-method", "wechat_mock"],
])
def test_rounding_invalid_combinations_return_two_before_driver(argv, monkeypatch):
    monkeypatch.setattr(script.DriverManager, "get_driver", lambda *a, **k: pytest.fail("driver"))
    assert script.main(argv) == 2
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest -q testcases/test_mall_order_cli.py -k rounding`

Expected: tests fail because the arguments and validation do not exist.

- [ ] **Step 3: Add parser, constructor, and validation plumbing**

Add `RoundingPaymentMixin` to `MallOrderFlow` composition without copying old monolithic methods:

```python
class MallOrderFlow(
    MallOrderAddressMixin,
    MallOrderCartMixin,
    MallOrderCheckoutMixin,
    RoundingPaymentMixin,
    ShopBusinessPage,
):
    ...
```

Add constructor attributes and parser arguments. `validate_args` must reject:

```python
if args.rounding_amount is not None and not args.rounding_payment:
    raise ValueError("--rounding-amount requires --rounding-payment")
if args.rounding_payment and args.payment_method != "cod":
    raise ValueError("COD rounding requires --payment-method cod")
```

- [ ] **Step 4: Write RED for checkout sequencing and final payable limit**

```python
def test_mall_rounding_occurs_after_delivery_and_before_submit():
    page = FakeMallCheckout(rounding_payment=True, rounding_amount=500)
    page.finish_checkout(PRODUCT, submit_order=True)
    assert page.events == [
        "checkout", "address", "coupon", "preferences", "delivery",
        "rounding:500", "limit:500", "submit:500", "pay",
    ]

def test_rounded_amount_above_max_payable_stops_before_submit():
    page = FakeMallCheckout(rounding_payment=True, rounding_amount=500, max_payable=450)
    with pytest.raises(AssertionError, match="max-payable|超过"):
        page.finish_checkout(PRODUCT, submit_order=True)
    assert "submit:500" not in page.events
```

- [ ] **Step 5: Implement minimal checkout integration**

After delivery selection and amount refresh:

```python
selected_rounding = None
if self.rounding_payment:
    selected_rounding = self.select_checkout_rounding_payment(
        payable=amounts.payable,
        custom_amount=self.rounding_amount,
    )
    amounts = AmountSnapshot(
        goods_total=amounts.goods_total,
        coupon=amounts.coupon,
        freight=amounts.freight,
        payable=float(selected_rounding.amount),
    )
if not submit_order:
    return
self.assert_within_payable_limit(amounts)
```

After payment, verify the exact-order detail shows the expected change when a rounding option was selected. Do not relax order identity or cancellation gates.

- [ ] **Step 6: Run focused GREEN and mall regressions**

Run: `python -m pytest -q testcases/test_mall_order_rounding.py testcases/test_mall_order_cli.py testcases/test_mall_order_checkout.py testcases/test_mall_order_safety.py`

Expected: all selected tests pass.

- [ ] **Step 7: Commit Task 2**

```bash
git add scripts/run_mall_order_flow.py pages/mall_order_checkout_mixin.py testcases/test_mall_order_cli.py testcases/test_mall_order_rounding.py
git commit -m "feat: integrate safe mall COD rounding"
```

### Task 3: Compose Rounding into Current Takeout Checkout

**Files:**
- Modify: `pages/takeout_checkout_mixin.py:1-55,2690-2840`
- Modify: `scripts/run_takeout_wangwang.py:57-235`
- Modify: `testcases/test_takeout_cli.py`
- Create: `testcases/test_takeout_rounding.py`

**Interfaces:**
- Consumes: Task 1 `RoundingPaymentMixin`.
- Produces: `run_shop_checkout_pay_and_cancel_flow(..., rounding_payment: bool = False, rounding_amount: float | None = None, max_payable: float | None = None) -> bool`.
- Adds `--rounding-payment`, `--rounding-amount`, and `--max-payable` to the takeout CLI.

- [ ] **Step 1: Write RED for takeout safety validation**

```python
def test_takeout_submit_requires_positive_max_payable(monkeypatch):
    monkeypatch.setattr(script.DriverManager, "get_driver", lambda *a, **k: pytest.fail("driver"))
    assert script.main(["--checkout", "--submit-order"]) == 2

def test_takeout_rounding_requires_cod(monkeypatch):
    monkeypatch.setattr(script.DriverManager, "get_driver", lambda *a, **k: pytest.fail("driver"))
    assert script.main(["--checkout", "--rounding-payment", "--checkout-payment", "balance"]) == 2
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest -q testcases/test_takeout_cli.py -k "rounding or max_payable"`

Expected: tests fail because the arguments and guards do not exist.

- [ ] **Step 3: Add CLI and pre-Driver guards**

Validation must enforce:

```python
if args.submit_order and (args.max_payable is None or args.max_payable <= 0):
    raise ValueError("real takeout order requires positive --max-payable")
if args.rounding_amount is not None and not args.rounding_payment:
    raise ValueError("--rounding-amount requires --rounding-payment")
if args.rounding_payment and args.checkout_payment != "cod":
    raise ValueError("takeout rounding requires COD")
```

- [ ] **Step 4: Write RED for preview, submit marker, and manual balance boundary**

```python
def test_takeout_cod_rounding_is_selected_before_submit():
    page = FakeTakeoutCheckout()
    assert page.run_shop_checkout_pay_and_cancel_flow(
        submit_order=True,
        checkout_payment="cod",
        rounding_payment=True,
        rounding_amount=500,
        max_payable=500,
    ) is False
    assert page.events.index("rounding:500") < page.events.index("submit")
    assert page._takeout_order_submitted is True

def test_takeout_balance_never_calls_rounding_or_password_input():
    page = FakeTakeoutCheckout()
    page.run_shop_checkout_pay_and_cancel_flow(
        submit_order=False,
        checkout_payment="balance",
    )
    assert not any(event.startswith("rounding") for event in page.events)
    assert not hasattr(page, "shop_enter_pay_password")
```

- [ ] **Step 5: Implement current-Mixin integration**

Compose `RoundingPaymentMixin` into `TakeoutCheckoutMixin`. Select COD first, select delivery, then select and read back rounding. Before the second confirmation, compare the effective payable with `max_payable`. Set `_takeout_order_submitted = True` immediately after the confirmed submit click and before any order-detail/cancel assertion.

Keep `shop_wait_for_manual_payment` unchanged for balance payment. Do not add password parameters or ADB text input.

- [ ] **Step 6: Run focused GREEN and takeout regressions**

Run: `python -m pytest -q testcases/test_takeout_rounding.py testcases/test_takeout_cli.py testcases/test_takeout_checkout_boundary.py`

Expected: all selected tests pass.

- [ ] **Step 7: Commit Task 3**

```bash
git add pages/takeout_checkout_mixin.py scripts/run_takeout_wangwang.py testcases/test_takeout_cli.py testcases/test_takeout_rounding.py
git commit -m "feat: integrate safe takeout COD rounding"
```

### Task 4: Safe Workflow Result and Explicit Submission Gate

**Files:**
- Create: `workflows/__init__.py`
- Create: `workflows/result.py`
- Create: `workflows/login_workflow.py`
- Create: `workflows/takeout_order_workflow.py`
- Create: `testcases/test_workflow_result.py`
- Create: `testcases/test_login_workflow.py`
- Create: `testcases/test_takeout_order_workflow.py`

**Interfaces:**
- Produces: `WorkflowStatus`, `WorkflowStage`, and immutable `WorkflowResult` with `.ok`.
- Produces: tri-state `LoginState` and `ensure_logged_in(...) -> WorkflowResult`.
- Produces: `run_takeout_order_flow(*, login_page, driver=None, takeout_page=None, submit_order=False, checkout_kwargs=None) -> WorkflowResult`.

- [ ] **Step 1: Write RED for result invariants and default non-submission**

```python
def test_failure_rejects_success_status():
    with pytest.raises(ValueError):
        WorkflowResult.failure(
            status=WorkflowStatus.SUCCESS,
            stage=WorkflowStage.CHECKOUT,
            message="bad",
        )

def test_takeout_workflow_defaults_to_preview_without_submission():
    page = FakeTakeoutPage()
    result = run_takeout_order_flow(
        login_page=LoggedInPage(),
        takeout_page=page,
    )
    assert page.checkout_kwargs["submit_order"] is False
    assert result.ok is True
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest -q testcases/test_workflow_result.py testcases/test_login_workflow.py testcases/test_takeout_order_workflow.py`

Expected: collection fails because `workflows` does not exist.

- [ ] **Step 3: Implement result and login workflow**

Use enums for stable machine-readable status and stage values. Login detection must return `UNKNOWN` on probe errors and must not attempt login unless the state is explicitly `LOGGED_OUT` and a login action was supplied.

- [ ] **Step 4: Implement explicit takeout workflow**

```python
def run_takeout_order_flow(
    *,
    login_page: object,
    driver: object | None = None,
    takeout_page: object | None = None,
    submit_order: bool = False,
    checkout_kwargs: Mapping[str, Any] | None = None,
) -> WorkflowResult:
    options = dict(checkout_kwargs or {})
    options["submit_order"] = bool(submit_order)
    # Open shop, execute checkout, and distinguish cleanup failure after submission.
```

Do not call a function named `run_default_takeout_real_order_flow`; no workflow may imply or default to a real order.

- [ ] **Step 5: Add cleanup-state RED/GREEN coverage**

Test that `_takeout_order_submitted=True` plus a failed checkout returns `ORDER_PLACED_CLEANUP_FAILED` with `stage=CLEANUP`; a preview failure returns `CHECKOUT_FAILED`.

- [ ] **Step 6: Run focused GREEN**

Run: `python -m pytest -q testcases/test_workflow_result.py testcases/test_login_workflow.py testcases/test_takeout_order_workflow.py`

Expected: all selected tests pass.

- [ ] **Step 7: Commit Task 4**

```bash
git add workflows testcases/test_workflow_result.py testcases/test_login_workflow.py testcases/test_takeout_order_workflow.py
git commit -m "feat: add explicit safe automation workflows"
```

### Task 5: Read-Only Personal Center Navigation

**Files:**
- Create: `pages/my_profile_page.py`
- Create: `scripts/run_my_profile_navigation.py`
- Create: `testcases/test_my_profile_page.py`
- Create: `testcases/test_my_profile_cli.py`

**Interfaces:**
- Produces: immutable `ProfileTarget(section: str, label: str, marker_labels: tuple[str, ...])`.
- Produces: `MyProfilePage.run_navigation_smoke() -> bool` and `run_logged_out_navigation_smoke() -> bool`.
- Produces: `scripts.run_my_profile_navigation.main(argv: Sequence[str] | None = None) -> int`.

- [ ] **Step 1: Write RED for allow-list and forbidden API absence**

```python
def test_profile_targets_are_read_only_allow_list():
    labels = {target.label for target in MyProfilePage.default_targets()}
    assert {"我的订单", "优惠券", "我的余额", "积分", "收藏清单", "我的地址"} <= labels

@pytest.mark.parametrize("name", [
    "run_phone_change_flow",
    "run_payment_password_change_flow",
    "run_fingerprint_payment_flow",
    "run_account_cancellation_flow",
    "run_login_password_change_flow",
])
def test_sensitive_profile_mutation_api_is_not_migrated(name):
    assert not hasattr(MyProfilePage, name)
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest -q testcases/test_my_profile_page.py testcases/test_my_profile_cli.py`

Expected: collection fails because the page and CLI do not exist.

- [ ] **Step 3: Implement the minimal page object**

The page object must contain only:

- package and bottom-tab verification;
- unique visible/enabled text lookup;
- `open_my_tab`, `open_target`, target marker wait, and verified return;
- logged-in and logged-out read-only target lists;
- no environment-variable secrets, password fields, state toggles, or final confirmation clicks.

- [ ] **Step 4: Implement the safe CLI and lifecycle**

Parser arguments are limited to `--session`, `--logged-out`, `--cold`, and `--start-mode`. Driver ownership is local and the CLI closes its session in `finally` by default. There are no `--include-*` mutation flags.

- [ ] **Step 5: Add navigation failure-closed tests**

Cover wrong package, missing/duplicate “我的”, missing/duplicate target, target marker timeout, and return failure. Each test must assert no later target was clicked after the first uncertain transition.

- [ ] **Step 6: Run focused GREEN**

Run: `python -m pytest -q testcases/test_my_profile_page.py testcases/test_my_profile_cli.py testcases/test_driver.py`

Expected: all selected tests pass.

- [ ] **Step 7: Commit Task 5**

```bash
git add pages/my_profile_page.py scripts/run_my_profile_navigation.py testcases/test_my_profile_page.py testcases/test_my_profile_cli.py
git commit -m "feat: add read-only profile navigation"
```

### Task 6: Security Scan, Full Regression, Review, and Integration

**Files:**
- Modify only if a regression requires a scoped fix in files from Tasks 1-5.
- Verify: all changed Python and test files.

**Interfaces:**
- Consumes all Task 1-5 deliverables.
- Produces a branch ready to merge into `agent/charge-page`.

- [ ] **Step 1: Run forbidden-content and conflict-marker scans**

Run:

```powershell
rg -n "<<<<<<<|=======|>>>>>>>|shop_enter_pay_password|run_default_takeout_real_order_flow|MY_PROFILE_.*PASSWORD|123456" pages scripts workflows testcases
```

Expected: no migrated automatic-password/default-real-order symbols. Existing unrelated test fixtures must be reviewed individually rather than deleted by pattern alone.

- [ ] **Step 2: Run focused business regressions**

Run:

```powershell
python -m pytest -q `
  testcases/test_rounding_payment.py `
  testcases/test_mall_order_cli.py `
  testcases/test_mall_order_checkout.py `
  testcases/test_mall_order_safety.py `
  testcases/test_takeout_cli.py `
  testcases/test_takeout_checkout_boundary.py `
  testcases/test_workflow_result.py `
  testcases/test_login_workflow.py `
  testcases/test_takeout_order_workflow.py `
  testcases/test_my_profile_page.py `
  testcases/test_my_profile_cli.py
```

Expected: all selected tests pass without creating an Appium session.

- [ ] **Step 3: Run complete offline regression and static checks**

Run:

```powershell
python -m pytest -q
python -m py_compile pages/rounding_payment.py pages/my_profile_page.py workflows/result.py workflows/login_workflow.py workflows/takeout_order_workflow.py scripts/run_my_profile_navigation.py
python scripts/run_mall_order_flow.py --help
python scripts/run_takeout_wangwang.py --help
python scripts/run_my_profile_navigation.py --help
git diff --check agent/charge-page...HEAD
```

Expected: default pytest passes with the device test deselected; all other commands exit 0.

- [ ] **Step 4: Request independent code review and address only Critical/Important findings**

Review must verify CLI prevalidation, max-payable enforcement after rounding, absence of password automation, exact submission marker timing, workflow cleanup states, profile allow-listing, and Driver cleanup.

- [ ] **Step 5: Re-run Step 1-3 after review fixes**

Expected: the same commands remain green on the exact final tree.

- [ ] **Step 6: Commit any final scoped fixes**

```bash
git add -- pages/rounding_payment.py pages/my_profile_page.py \
  pages/mall_order_checkout_mixin.py pages/takeout_checkout_mixin.py \
  scripts/run_mall_order_flow.py scripts/run_takeout_wangwang.py \
  scripts/run_my_profile_navigation.py workflows testcases
git commit -m "fix: harden safe rounding profile migration"
```

If no review fix is needed, do not create an empty commit.

- [ ] **Step 7: Finish the branch**

Merge `codex/rounding-profile-safe-migration` into `agent/charge-page`, rerun `python -m pytest -q`, push `agent/charge-page`, then delete the migration branch. After the new implementation is safely merged, remove the old `agent/rounding-my-profile-scripts` worktree and local branch; do not force-delete either branch before the merge and remote push are verified.
