# Takeout Address Auto Create Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fail-closed external-data-driven takeout address creation flow that can select, automatically create, or force-create a delivery address before checkout continues.

**Architecture:** Keep the existing takeout checkout orchestration and address picker, add a small immutable address-data contract plus focused address-form helpers in the takeout checkout mixin. The CLI validates all mutating input before Driver creation and passes an explicit policy/data object to the checkout flow; UI success requires stable readback.

**Tech Stack:** Python 3, argparse, pytest, Appium UiAutomator2, existing page-object mixins.

**Spec:** `docs/superpowers/specs/2026-08-24-takeout-address-auto-create-design.md`

## Global Constraints

- Default address policy is `existing`; no new persistent account data is written unless `auto` or `add` is explicit.
- New address values come only from `TAKEOUT_ADDRESS_CONTACT`, `TAKEOUT_ADDRESS_PHONE`, `TAKEOUT_ADDRESS_SEARCH`, and `TAKEOUT_ADDRESS_DETAIL`.
- Complete contact, phone, search query, and detail values must not appear in logs or failure messages.
- COD and phone notification require an address containing a phone number.
- Every failure stops the current command before payment/order submission.

---

### Task 1: Address policy and CLI contract

**Files:**
- Create: `pages/takeout_address.py`
- Modify: `scripts/run_takeout_wangwang.py`
- Test: `testcases/test_takeout_cli.py`

**Interfaces:**
- Produces: `TakeoutAddressPolicy(str, Enum)`, `TakeoutAddressData`, `load_takeout_address_data(environ)`, and CLI arguments `--address-policy` plus existing `--address-ordinal`/`--address-contains`.
- Consumes: four `TAKEOUT_ADDRESS_*` environment variables.

- [ ] **Step 1: Write failing CLI tests**

```python
def test_takeout_address_policy_defaults_to_existing():
    assert script.build_parser().parse_args([]).address_policy == "existing"

def test_takeout_add_policy_rejects_missing_data_before_driver(monkeypatch):
    monkeypatch.delenv("TAKEOUT_ADDRESS_CONTACT", raising=False)
    assert script.main(["--checkout", "--address-policy", "add"]) == 2

def test_takeout_auto_policy_accepts_complete_environment(monkeypatch):
    for key, value in ADDRESS_ENV.items():
        monkeypatch.setenv(key, value)
    script.validate_args(script.build_parser().parse_args(["--checkout", "--address-policy", "auto"]))
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m pytest testcases/test_takeout_cli.py -q`

Expected: FAIL because `--address-policy` and `TakeoutAddressData` do not exist.

- [ ] **Step 3: Implement the minimal data and validation contract**

```python
class TakeoutAddressPolicy(str, Enum):
    EXISTING = "existing"
    AUTO = "auto"
    ADD = "add"

@dataclass(frozen=True)
class TakeoutAddressData:
    contact: str = ""
    phone: str = ""
    search: str = ""
    detail: str = ""

    def missing_for_add(self) -> tuple[str, ...]:
        return tuple(name for name in ("contact", "phone", "search", "detail") if not getattr(self, name).strip())
```

Validate `auto` and `add` before constructing `DriverManager`, then pass `address_policy` and `address_data` into `run_shop_checkout_pay_and_cancel_flow`.

- [ ] **Step 4: Run CLI tests and verify GREEN**

Run: `python -m pytest testcases/test_takeout_cli.py -q`

Expected: PASS.

### Task 2: Address creation page-object flow

**Files:**
- Modify: `pages/takeout_checkout_mixin.py`
- Test: `testcases/test_takeout_reliability.py`

**Interfaces:**
- Produces: `shop_add_address_from_sheet(data: TakeoutAddressData) -> bool` and `shop_ensure_address_in_sheet(..., address_policy: str, address_data: TakeoutAddressData) -> bool`.
- Consumes: existing `_ensure_location_permission_enabled`, `_tap_first_displayed`, address candidate/readback helpers, and Appium driver primitives.

- [ ] **Step 1: Write failing UI-state tests**

```python
def test_auto_address_adds_when_sheet_has_no_rows(address_page, address_data):
    assert address_page.shop_ensure_address_in_sheet(
        address_policy="auto", address_data=address_data, address_ordinal=1,
        address_contains=None, require_phone=True,
    )
    assert address_page.saved_address_phone_tail == address_data.phone[-4:]

def test_existing_address_never_clicks_add(address_page, address_data):
    assert not address_page.shop_ensure_address_in_sheet(
        address_policy="existing", address_data=address_data, address_ordinal=1,
        address_contains=None, require_phone=True,
    )
    assert "新增地址" not in address_page.clicked

def test_add_address_stops_when_location_result_is_ambiguous(address_page, address_data):
    address_page.location_results = ["A", "B"]
    assert not address_page.shop_add_address_from_sheet(address_data)
    assert "保存" not in address_page.clicked
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python -m pytest testcases/test_takeout_reliability.py -q -k "address and (auto or add or existing)"`

Expected: FAIL because the new methods do not exist.

- [ ] **Step 3: Implement the minimal guarded UI flow**

Implement semantic text/content-desc lookup for “新增地址”, “定位地址”, search input, exact single search-result selection, labeled contact/phone/detail fields, and “保存”. After save, accept only address-book or checkout markers and verify at least the phone tail plus one non-sensitive stable marker before returning success.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `python -m pytest testcases/test_takeout_reliability.py -q -k "address"`

Expected: PASS.

### Task 3: Checkout orchestration integration

**Files:**
- Modify: `pages/takeout_checkout_mixin.py`
- Modify: `scripts/run_takeout_wangwang.py`
- Test: `testcases/test_takeout_reliability.py`
- Test: `testcases/test_takeout_cli.py`

**Interfaces:**
- Consumes: Task 1 policy/data and Task 2 `shop_ensure_address_in_sheet`.
- Produces: checkout behavior in which address verification completes before payment selection and every downstream action.

- [ ] **Step 1: Write a failing workflow-order test**

```python
def test_checkout_creates_and_verifies_address_before_payment(flow_page, address_data):
    flow_page.run_shop_checkout_pay_and_cancel_flow(
        address_policy="auto", address_data=address_data,
    )
    assert flow_page.events.index("address_verified") < flow_page.events.index("payment_selected")
```

- [ ] **Step 2: Run the workflow test and verify RED**

Run: `python -m pytest testcases/test_takeout_reliability.py testcases/test_takeout_cli.py -q`

Expected: FAIL because the checkout method does not accept or route the new contract.

- [ ] **Step 3: Replace direct picker orchestration with the policy-aware method**

Pass `address_policy` and `address_data` from the CLI into checkout. Preserve the exact existing picker behavior for `existing`; for `auto`, retry via add only when no eligible existing address was selected; for `add`, skip existing candidates. Return false before payment selection on every creation/readback failure.

- [ ] **Step 4: Run takeout suites and verify GREEN**

Run: `python -m pytest testcases/test_takeout_cli.py testcases/test_takeout_reliability.py testcases/test_takeout_order_workflow.py -q`

Expected: PASS.

### Task 4: Static and real-device regression

**Files:**
- Modify only if a reproduced failure first receives a failing regression test.
- Evidence: `logs/` and `artifacts/takeout_live/`.

**Interfaces:**
- Consumes: completed Tasks 1–3 and locally supplied `TAKEOUT_ADDRESS_*` values.
- Produces: evidence that an empty real address sheet can create, verify, select, and continue checkout without leaking personal data.

- [ ] **Step 1: Run all relevant automated verification**

Run: `python -m pytest testcases/test_takeout_cli.py testcases/test_takeout_reliability.py testcases/test_takeout_checkout_boundary.py testcases/test_takeout_order_workflow.py -q`

Run: `python -m compileall pages scripts testcases`

Run: `git diff --check`

- [ ] **Step 2: Validate local real-address configuration without logging values**

Run: `python scripts/run_takeout_wangwang.py --checkout --address-policy auto --checkout-payment cod --delivery-time-slot-ordinal 1`

Expected: with all four environment variables set, the address is created or reused, selected, and checkout preview completes without submitting an order.

- [ ] **Step 3: Reproduce, test, fix, and rerun each real-device failure**

For each failure, first add a focused failing test using the captured UI state, verify RED, implement the smallest fix, verify GREEN, and rerun the same command before proceeding.

- [ ] **Step 4: Run one authorized real-order regression**

Run: `python scripts/run_takeout_wangwang.py --checkout --submit-order --max-payable 5000 --address-policy auto --address-ordinal 1 --delivery-time-slot-ordinal 1 --checkout-payment cod`

Expected: address verification precedes submission, the order is created, and the existing cancellation flow confirms the cancellation request.
