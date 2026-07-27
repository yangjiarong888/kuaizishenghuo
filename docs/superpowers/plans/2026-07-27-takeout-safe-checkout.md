# Takeout Safe Checkout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make takeout checkout preview non-submitting by default, require explicit order submission, and replace automatic fixed-password entry with user-entered payment on the real device.

**Architecture:** CLI validation runs before Driver creation. `TakeoutCheckoutMixin` keeps the existing checkout preparation order but returns before the final confirmation unless `submit_order=True`; balance payment then waits for the user to complete payment on the device, while COD proceeds without a password.

**Tech Stack:** Python 3.11, argparse, pytest, Appium Page Object/Mixin code, existing `DriverManager`.

## Global Constraints

- Default execution must not create an order, submit payment, send a verification code, or mutate an address.
- `--checkout` may prepare the cart and checkout page but must stop before the final confirmation.
- Only `--checkout --submit-order` may perform the final submission.
- Balance payment must not accept, log, or automatically type a payment password.
- Real order creation requires fresh per-run user authorization and is excluded from the default device verification.
- Preserve current COD, order assertion, and cancellation order after explicit submission.
- Use RED→GREEN tests and run the complete offline suite after each production batch.

---

### Task 1: CLI Safety Boundary

**Files:**
- Create: `testcases/test_takeout_cli.py`
- Modify: `scripts/run_takeout_wangwang.py:1-224`

**Interfaces:**
- Consumes: `DriverManager`, `open_wangwang_supermarket_from_takeout_home()`.
- Produces: `build_parser() -> argparse.ArgumentParser`, `validate_args(args: argparse.Namespace) -> None`, `main(argv: Optional[Sequence[str]] = None) -> int`.

- [ ] **Step 1: Write failing parser-contract tests**

```python
from scripts.run_takeout_wangwang import build_parser, validate_args


def test_takeout_defaults_are_non_submitting_and_have_no_password():
    args = build_parser().parse_args([])
    assert args.checkout is False
    assert args.submit_order is False
    assert not hasattr(args, "password")


def test_submit_order_requires_checkout():
    args = build_parser().parse_args(["--submit-order"])
    with pytest.raises(ValueError, match="--checkout"):
        validate_args(args)


def test_checkout_and_submit_order_is_an_explicit_valid_combination():
    args = build_parser().parse_args(["--checkout", "--submit-order"])
    validate_args(args)
```

- [ ] **Step 2: Write a failing pre-Driver validation test**

```python
def test_invalid_submit_combination_returns_two_before_driver_creation(monkeypatch):
    class ForbiddenManager:
        def __init__(self):
            raise AssertionError("DriverManager must not be created")

    monkeypatch.setattr(run_takeout_wangwang, "DriverManager", ForbiddenManager)
    assert run_takeout_wangwang.main(["--submit-order"]) == 2
```

- [ ] **Step 3: Run the CLI tests and verify RED**

Run:

```powershell
& '..\Scripts\python.exe' -m pytest testcases\test_takeout_cli.py -q
```

Expected: collection/import failures for missing `build_parser`, `validate_args`, or `main(argv)`, then assertion failures after import scaffolding exists.

- [ ] **Step 4: Implement the minimal CLI contract**

Move parser construction out of `main()`:

```python
from typing import Optional, Sequence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="外卖：旺旺店铺进店与安全结算预览"
    )
    # Keep existing arguments.
    parser.add_argument("--checkout", action="store_true")
    parser.add_argument(
        "--submit-order",
        action="store_true",
        help="真实创建订单；必须与 --checkout 同时使用",
    )
    # Do not define --password.
    return parser


def validate_args(args: argparse.Namespace) -> None:
    if args.submit_order and not args.checkout:
        raise ValueError("--submit-order requires --checkout")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        validate_args(args)
    except ValueError as exc:
        logger.error("参数安全校验失败: %s", exc)
        return 2
    # Existing Driver and navigation flow follows only after validation.
```

Remove the `--password` example, parser option, default, help text, and `pay_password=args.password` call.

- [ ] **Step 5: Run focused and full offline tests**

Run:

```powershell
& '..\Scripts\python.exe' -m pytest testcases\test_takeout_cli.py -q
& '..\Scripts\python.exe' -m pytest -m 'not device' -q
```

Expected: all focused tests pass; full suite has zero failures.

- [ ] **Step 6: Commit only Task 1 files**

```powershell
git add -- scripts/run_takeout_wangwang.py testcases/test_takeout_cli.py
git diff --cached --check
git commit -m "fix: gate takeout order submission"
```

---

### Task 2: Checkout Preview and Manual Payment Boundary

**Files:**
- Create: `testcases/test_takeout_checkout_boundary.py`
- Modify: `pages/takeout_checkout_mixin.py:2694-2857`
- Modify: `scripts/run_takeout_wangwang.py:186-211`
- Modify: `testcases/test_takeout_cli.py`

**Interfaces:**
- Consumes: existing checkout preparation methods, `shop_assert_order_detail_cancel_visible(timeout: float) -> bool`, and `shop_cancel_order_flow() -> bool`.
- Produces: `run_shop_checkout_pay_and_cancel_flow(*, submit_order: bool = False, manual_payment_timeout: float = 120.0, ...) -> bool` and `shop_wait_for_manual_payment(timeout: float = 120.0) -> bool`.

- [ ] **Step 1: Write a recording checkout fake**

```python
from pages.takeout_checkout_mixin import TakeoutCheckoutMixin


class RecordingCheckout(TakeoutCheckoutMixin):
    def __init__(self):
        self.events = []
        self.confirm_count = 0

    def shop_detail_scroll_to_category(self, *args, **kwargs):
        self.events.append("category")
        return True

    def shop_detail_add_first_visible_product_highest_spec(self, *args, **kwargs):
        self.events.append("add")
        return True

    def shop_tap_bottom_cart_bar(self):
        self.events.append("cart")
        return True

    def shop_tap_go_checkout(self):
        self.events.append("checkout")
        return True

    def shop_tap_confirm_pay_bar(self):
        self.confirm_count += 1
        self.events.append(f"confirm-{self.confirm_count}")
        return True

    def shop_pick_random_address_in_sheet(self):
        self.events.append("address")
        return True

    def shop_apply_checkout_coupons(self, **kwargs):
        self.events.append("coupons")
        return True

    def shop_apply_checkout_preferences(self, **kwargs):
        self.events.append("preferences")
        return True

    def shop_select_balance_payment(self):
        self.events.append("balance")
        return True

    def shop_select_cash_on_delivery_payment(self):
        self.events.append("cod")
        return True

    def shop_open_delivery_time_and_pick_future_slot(self, **kwargs):
        self.events.append("delivery")
        return True

    def shop_wait_for_manual_payment(self, timeout=120.0):
        self.events.append(("manual-payment", timeout))
        return True

    def shop_assert_order_detail_cancel_visible(self, timeout=25.0):
        self.events.append(("order-detail", timeout))
        return True

    def shop_cancel_order_flow(self):
        self.events.append("cancel")
        return True
```

- [ ] **Step 2: Write failing preview and submission tests**

```python
def test_preview_stops_before_final_confirmation(monkeypatch):
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = RecordingCheckout()
    assert page.run_shop_checkout_pay_and_cancel_flow(submit_order=False)
    assert page.confirm_count == 1
    assert not any(
        event == "cancel"
        or isinstance(event, tuple) and event[0] in {"manual-payment", "order-detail"}
        for event in page.events
    )


def test_balance_submission_waits_for_manual_payment_then_cancels(monkeypatch):
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = RecordingCheckout()
    assert page.run_shop_checkout_pay_and_cancel_flow(
        submit_order=True,
        checkout_payment="balance",
        manual_payment_timeout=90.0,
    )
    assert page.confirm_count == 2
    assert ("manual-payment", 90.0) in page.events
    assert page.events[-1] == "cancel"


def test_cod_submission_skips_manual_payment(monkeypatch):
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = RecordingCheckout()
    assert page.run_shop_checkout_pay_and_cancel_flow(
        submit_order=True,
        checkout_payment="cod",
    )
    assert page.confirm_count == 2
    assert not any(
        isinstance(event, tuple) and event[0] == "manual-payment"
        for event in page.events
    )
    assert page.events[-1] == "cancel"
```

- [ ] **Step 3: Run boundary tests and verify RED**

Run:

```powershell
& '..\Scripts\python.exe' -m pytest testcases\test_takeout_checkout_boundary.py -q
```

Expected: failures because `submit_order` and `shop_wait_for_manual_payment` do not exist and the current flow always reaches final submission.

- [ ] **Step 4: Implement the preview return before final confirmation**

Update the flow signature:

```python
def run_shop_checkout_pay_and_cancel_flow(
    self,
    *,
    submit_order: bool = False,
    manual_payment_timeout: float = 120.0,
    category: Optional[str] = None,
    # Keep the remaining existing keyword arguments unchanged.
) -> bool:
```

Immediately before the existing second `shop_tap_confirm_pay_bar()`:

```python
if not submit_order:
    logger.info("结算预览完成：未授权 --submit-order，停止在最终确认前")
    return True
```

- [ ] **Step 5: Replace automatic password entry with manual waiting**

Delete `shop_enter_pay_password()`. Add:

```python
def shop_wait_for_manual_payment(self, timeout: float = 120.0) -> bool:
    logger.warning(
        "请在真机手动输入支付密码；脚本最多等待 %.0f 秒进入订单详情",
        timeout,
    )
    return self.shop_assert_order_detail_cancel_visible(timeout=timeout)
```

After the final confirmation:

```python
if pay_mode == "balance":
    if not self.shop_wait_for_manual_payment(timeout=manual_payment_timeout):
        logger.error("等待手动支付完成超时，未进入订单详情")
        return False
else:
    if not self.shop_assert_order_detail_cancel_visible():
        return False

if not self.shop_cancel_order_flow():
    logger.error("取消流程失败：未提交成功或取消结果校验未通过")
    return False
return True
```

Do not call `shop_assert_order_detail_cancel_visible()` twice on the balance path.

- [ ] **Step 6: Pass explicit submit intent from the CLI**

In `scripts/run_takeout_wangwang.py`:

```python
ok = page.run_shop_checkout_pay_and_cancel_flow(
    submit_order=args.submit_order,
    category=args.category,
    # Keep the remaining non-secret options.
)
```

Add an integration test using a fake `TakeoutPageBase` that records `submit_order`; assert `--checkout` records `False` and `--checkout --submit-order` records `True`.

- [ ] **Step 7: Run focused and full offline tests**

Run:

```powershell
& '..\Scripts\python.exe' -m pytest `
  testcases\test_takeout_cli.py `
  testcases\test_takeout_checkout_boundary.py -q
& '..\Scripts\python.exe' -m pytest -m 'not device' -q
```

Expected: all focused tests pass; full suite has zero failures.

- [ ] **Step 8: Commit only Task 2 files**

```powershell
git add -- pages/takeout_checkout_mixin.py scripts/run_takeout_wangwang.py testcases/test_takeout_cli.py testcases/test_takeout_checkout_boundary.py
git diff --cached --check
git commit -m "refactor: separate takeout preview from submission"
```

---

### Task 3: Verification and Review Report

**Files:**
- Create: `docs/reviews/2026-07-27-takeout-safe-checkout-review.md`

**Interfaces:**
- Consumes: Task 1 and Task 2 tests and production code.
- Produces: reproducible verification evidence and remaining takeout risks.

- [ ] **Step 1: Run focused and complete verification**

```powershell
& '..\Scripts\python.exe' -m pytest `
  testcases\test_takeout_cli.py `
  testcases\test_takeout_checkout_boundary.py -q
& '..\Scripts\python.exe' -m pytest -m 'not device' -q
```

Record exact pass, fail, and deselected counts.

- [ ] **Step 2: Compile every Python source in memory**

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

Expected: exit code `0` and a non-zero compiled file count.

- [ ] **Step 3: Scan production sources for fixed payment passwords**

```powershell
rg -n 'password.*123456|123456.*password|pay_password\\s*:\\s*str\\s*=|--password' pages scripts --glob '*.py'
```

Expected: no production default, automatic takeout password method, or takeout CLI password argument. Documentation of rejected legacy behavior may be reported separately.

- [ ] **Step 4: Record residual takeout risk**

Count and document:

```powershell
rg -n 'time\\.sleep\\(' pages/takeout*.py scripts/run_takeout_wangwang.py
rg -n 'except\\s+(Exception|BaseException)|except\\s*:' pages/takeout*.py scripts/run_takeout_wangwang.py
```

The report must distinguish verified defects from remaining refactoring risk and state that real submission was not executed.

- [ ] **Step 5: Write and commit the review report**

The report must include:

- changed safety contract;
- exact test and compile evidence;
- sensitive-value scan result;
- explicit statement that no real order/payment was executed;
- remaining fixed waits, broad exceptions, and oversized-file risk;
- final device-verification command/path using navigation only.

```powershell
git add -- docs/reviews/2026-07-27-takeout-safe-checkout-review.md
git diff --cached --check
git commit -m "docs: record takeout safety verification"
```
