# Shipping Business Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `package.py` and a maintainable Appium page object that starts from the Chopsticks Life home page, creates a real international-shipping order with a shared address and a future delivery slot, then handles balance payment, cash on delivery, or unpaid-payment cancellation safely.

**Architecture:** Keep `ShippingPage` as the public facade and split shared-address, delivery-slot, and payment-state behavior into focused mixins. Put date parsing, address validation, masking, and payment-state decisions in pure functions so the dangerous business rules are testable without Appium or real orders. The root `package.py` validates all CLI and secret inputs before creating a driver, then calls one `run_order_flow` facade method.

**Tech Stack:** Python 3.11, pytest, Appium Python Client, Selenium explicit waits, existing `DriverManager`, `commons.logger`, and `commons.diagnostics`.

## Global Constraints

- The executable filename is exactly `package.py` at the repository root.
- The flow must enter by clicking “国际货运” from the Chopsticks Life home page.
- The shipping home and “配送订单” tabs must support verified two-way switching.
- The delivery address uses the same public address book as takeout and supports selecting an existing address or adding a new one.
- The selected delivery date must be strictly later than the device date; today is never accepted.
- Real order submission is authorized.
- Balance payment performs a real charge; cash on delivery is also supported.
- Only an order explicitly verified as “待支付/待付款” may execute “取消支付”.
- Paid, cash-on-delivery, or unknown states must never execute “取消支付”.
- Do not automatically cancel a paid or cash-on-delivery order.
- Log navigation, address strategy, future-date selection, payment method, order number, status, and diagnostic paths.
- Never log the payment password, full phone number, or full detailed address.
- Use text/resource-id selectors first; fixed coordinates are fallback-only and must be followed by a page-state assertion.
- Preserve all unrelated user changes and untracked artifacts.

---

## File Structure

- Create `pages/shipping_types.py`: pure dataclasses, enums, date parsing, masking, and payment-state policy.
- Create `pages/shipping_address_mixin.py`: public address-book selection/addition and checkout-page verification.
- Create `pages/shipping_delivery_mixin.py`: delivery-picker discovery, earliest-future selection, and read-back validation.
- Create `pages/shipping_payment_mixin.py`: single-submit guard, balance/COD handling, order-state checks, and unpaid cancellation.
- Modify `pages/shipping_page.py`: reliable find/click helpers, home entry, tab navigation, diagnostics, and flow orchestration.
- Create `package.py`: CLI, environment-variable loading, preflight validation, driver lifecycle, and exit status.
- Create `testcases/test_shipping_types.py`: pure rule tests.
- Create `testcases/test_shipping_page.py`: fake-driver page-object tests.
- Create `testcases/test_package_cli.py`: CLI preflight and driver-boundary tests.

---

### Task 1: Pure Shipping Rules and Sensitive-Data Protection

**Files:**
- Create: `pages/shipping_types.py`
- Create: `testcases/test_shipping_types.py`

**Interfaces:**
- Produces: `AddressPolicy`, `PaymentMethod`, `OrderPaymentState`, `AddressData`, `parse_delivery_date(label, today)`, `earliest_future_label(labels, today)`, `classify_payment_state(text)`, `can_cancel_payment(state)`, and `mask_phone(value)`.
- Consumes: only Python standard-library `dataclasses`, `datetime`, `enum`, `re`, and typing primitives.

- [ ] **Step 1: Write failing tests for address validation and masking**

```python
from pages.shipping_types import AddressData, mask_phone


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
```

- [ ] **Step 2: Run the address tests and verify RED**

Run: `pytest -q testcases/test_shipping_types.py -k "address or mask"`

Expected: collection fails with `ModuleNotFoundError: No module named 'pages.shipping_types'`.

- [ ] **Step 3: Implement the address types and mask**

```python
from dataclasses import dataclass
from enum import Enum
import re


class AddressPolicy(str, Enum):
    AUTO = "auto"
    EXISTING = "existing"
    ADD = "add"


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
```

- [ ] **Step 4: Run the address tests and verify GREEN**

Run: `pytest -q testcases/test_shipping_types.py -k "address or mask"`

Expected: `2 passed`.

- [ ] **Step 5: Write failing tests for future-date selection**

```python
from datetime import date
import pytest

from pages.shipping_types import earliest_future_label, parse_delivery_date


@pytest.mark.parametrize("label", ("今天", "8月10日", "2026-08-10"))
def test_today_is_never_future(label):
    today = date(2026, 8, 10)
    assert parse_delivery_date(label, today) == today


def test_earliest_future_label_ignores_today_past_and_unparseable():
    today = date(2026, 8, 10)
    labels = ["请选择", "8月9日", "今天", "8月12日", "明天", "8月13日"]

    assert earliest_future_label(labels, today) == ("明天", date(2026, 8, 11))


def test_earliest_future_label_fails_when_only_today_exists():
    with pytest.raises(ValueError, match="未来配送日期"):
        earliest_future_label(["今天", "8月10日"], date(2026, 8, 10))
```

- [ ] **Step 6: Run the date tests and verify RED**

Run: `pytest -q testcases/test_shipping_types.py -k "future or today"`

Expected: tests fail because `parse_delivery_date` and `earliest_future_label` are missing.

- [ ] **Step 7: Implement explicit date parsing and strict future filtering**

```python
from datetime import date, timedelta


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
    month_day = re.search(r"(\d{1,2})月(\d{1,2})日?", text)
    if not month_day:
        return None
    month, day = (int(group) for group in month_day.groups())
    candidate = date(today.year, month, day)
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
```

- [ ] **Step 8: Write and implement payment-state policy tests**

```python
from pages.shipping_types import (
    OrderPaymentState,
    can_cancel_payment,
    classify_payment_state,
)


def test_only_pending_payment_can_cancel_payment():
    assert classify_payment_state("订单状态：待支付") is OrderPaymentState.PENDING
    assert can_cancel_payment(OrderPaymentState.PENDING) is True
    assert can_cancel_payment(OrderPaymentState.PAID) is False
    assert can_cancel_payment(OrderPaymentState.COD) is False
    assert can_cancel_payment(OrderPaymentState.UNKNOWN) is False
```

Implement:

```python
class PaymentMethod(str, Enum):
    BALANCE = "balance"
    COD = "cod"


class OrderPaymentState(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    COD = "cod"
    UNKNOWN = "unknown"


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
```

- [ ] **Step 9: Run all pure rule tests**

Run: `pytest -q testcases/test_shipping_types.py`

Expected: all tests pass with no warnings.

- [ ] **Step 10: Commit the pure rules**

```bash
git add pages/shipping_types.py testcases/test_shipping_types.py
git commit -m "test: define shipping order safety rules"
```

---

### Task 2: Home Entry, Shipping Tabs, and Diagnostics

**Files:**
- Modify: `pages/shipping_page.py:1-68`
- Create: `testcases/test_shipping_page.py`

**Interfaces:**
- Consumes: existing `AppConfig`, `commons.diagnostics.capture_failure`, Selenium waits, and Appium selectors.
- Produces: `ShippingPage.enter_from_app_home() -> bool`, `wait_for_shipping_home(timeout=None) -> bool`, `switch_to_shipping_home() -> bool`, `switch_to_delivery_orders() -> bool`, `page_blob() -> str`, `capture_shipping_failure(stage) -> None`.

- [ ] **Step 1: Write a fake driver and failing home-entry test**

```python
from pages.shipping_page import ShippingPage


class FakeElement:
    def __init__(self, driver, text="", on_click=None):
        self.driver = driver
        self.text = text
        self.on_click = on_click

    def is_displayed(self):
        return True

    def is_enabled(self):
        return True

    def click(self):
        self.driver.clicks.append(self.text)
        if self.on_click:
            self.on_click()


class FakeShippingDriver:
    def __init__(self):
        self.screen = "app_home"
        self.clicks = []
        self.page_source = "筷子生活 首页 国际货运"
        self.current_activity = "com.bs.feifubao.MainActivity"

    def find_elements(self, by, value):
        if self.screen == "app_home" and "国际货运" in value:
            return [FakeElement(self, "国际货运", self._show_shipping_home)]
        return []

    def _show_shipping_home(self):
        self.screen = "shipping_home"
        self.page_source = "国际货运 寄件菲律宾 寄件全球 配送订单"


def test_enter_from_app_home_clicks_international_shipping():
    driver = FakeShippingDriver()

    assert ShippingPage(driver).enter_from_app_home() is True
    assert driver.clicks == ["国际货运"]
    assert driver.screen == "shipping_home"
```

- [ ] **Step 2: Run the home-entry test and verify RED**

Run: `pytest -q testcases/test_shipping_page.py::test_enter_from_app_home_clicks_international_shipping`

Expected: fails with `AttributeError: 'ShippingPage' object has no attribute 'enter_from_app_home'`.

- [ ] **Step 3: Replace the mojibake skeleton with reliable helpers and home entry**

```python
def _first_displayed(self, by, value):
    for element in self.driver.find_elements(by, value):
        try:
            if element.is_displayed():
                return element
        except Exception:
            continue
    return None


def page_blob(self) -> str:
    try:
        return self.driver.page_source or ""
    except Exception:
        return ""


def enter_from_app_home(self) -> bool:
    if self.wait_for_shipping_home(timeout=1):
        return True
    entry = self._first_displayed(
        AppiumBy.XPATH,
        '//*[@text="国际货运" or @content-desc="国际货运" '
        'or contains(@content-desc,"国际货运")]',
    )
    if entry is None:
        logger.error("App 首页未找到国际货运入口")
        self.capture_shipping_failure("shipping_entry_missing")
        return False
    entry.click()
    return self.wait_for_shipping_home()
```

`wait_for_shipping_home` must require one title marker plus one service/tab marker, for example `国际货运` and one of `寄件菲律宾`, `寄件全球`, `配送订单`, rather than accepting any page containing “海运”.

- [ ] **Step 4: Run the home-entry test and verify GREEN**

Run: `pytest -q testcases/test_shipping_page.py::test_enter_from_app_home_clicks_international_shipping`

Expected: pass.

- [ ] **Step 5: Write failing tests for verified two-way tab switching**

```python
def test_shipping_tabs_switch_both_directions():
    driver = FakeShippingDriver()
    driver._show_shipping_home()
    page = ShippingPage(driver)

    assert page.switch_to_delivery_orders() is True
    assert driver.screen == "delivery_orders"
    assert page.switch_to_shipping_home() is True
    assert driver.screen == "shipping_home"
```

Extend the fake driver so clicking “配送订单” sets `page_source` to `配送订单 全部 待付款 待收货 已完成 已取消`, and clicking “国际货运” or “首页” returns to the shipping home markers.

- [ ] **Step 6: Implement tab methods with post-click assertions**

```python
def switch_to_delivery_orders(self) -> bool:
    if self._is_delivery_orders_page():
        return True
    if not self._click_text(("配送订单",)):
        return False
    return self._wait_until(self._is_delivery_orders_page)


def switch_to_shipping_home(self) -> bool:
    if self._is_shipping_home_page():
        return True
    if not self._click_text(("国际货运", "首页")):
        return False
    return self._wait_until(self._is_shipping_home_page)
```

The predicates must use marker combinations so an order card containing “配送订单” is not mistaken for the order-list tab.

- [ ] **Step 7: Add diagnostic capture without leaking secrets**

```python
from commons.diagnostics import capture_failure


def capture_shipping_failure(self, stage: str) -> None:
    safe_stage = re.sub(r"[^a-z0-9_-]+", "_", stage.lower())[:80]
    artifacts = capture_failure(self.driver, safe_stage, AppConfig.ARTIFACTS_DIR)
    logger.error(
        "海运流程失败 stage=%s screenshot=%s page_source=%s",
        safe_stage,
        artifacts.screenshot,
        artifacts.page_source,
    )
```

- [ ] **Step 8: Run navigation tests**

Run: `pytest -q testcases/test_shipping_page.py -k "home or tab"`

Expected: all selected tests pass.

- [ ] **Step 9: Commit navigation and diagnostics**

```bash
git add pages/shipping_page.py testcases/test_shipping_page.py
git commit -m "feat: navigate shipping home and order tabs"
```

---

### Task 3: Public Address Book Selection and Addition

**Files:**
- Create: `pages/shipping_address_mixin.py`
- Modify: `pages/shipping_page.py`
- Modify: `testcases/test_shipping_page.py`

**Interfaces:**
- Consumes: `AddressData`, `AddressPolicy`, facade helpers `_click_text`, `_first_displayed`, `_wait_until`, `page_blob`, and `_type_field`.
- Produces: `ensure_shipping_address(policy: AddressPolicy, data: AddressData) -> bool`, `select_existing_shipping_address(match: str) -> bool`, `add_shipping_address(data: AddressData) -> bool`, and `verify_shipping_address_applied(data: AddressData) -> bool`.

- [ ] **Step 1: Write failing tests for address-policy preconditions**

```python
import pytest

from pages.shipping_types import AddressData, AddressPolicy


def test_existing_policy_requires_match_before_clicking():
    driver = FakeShippingDriver()
    page = ShippingPage(driver)

    with pytest.raises(ValueError, match="SHIPPING_ADDRESS_MATCH"):
        page.ensure_shipping_address(AddressPolicy.EXISTING, AddressData())

    assert driver.clicks == []


def test_add_policy_requires_complete_fields_before_clicking():
    driver = FakeShippingDriver()
    page = ShippingPage(driver)
    incomplete = AddressData(name="Tester")

    with pytest.raises(ValueError, match="phone,country,city,detail,postcode"):
        page.ensure_shipping_address(AddressPolicy.ADD, incomplete)

    assert driver.clicks == []
```

- [ ] **Step 2: Run the precondition tests and verify RED**

Run: `pytest -q testcases/test_shipping_page.py -k "policy_requires"`

Expected: fails because `ensure_shipping_address` is missing.

- [ ] **Step 3: Implement preconditions before any address UI interaction**

```python
def ensure_shipping_address(self, policy, data):
    if policy is AddressPolicy.EXISTING and not data.match.strip():
        raise ValueError("existing 地址策略需要 SHIPPING_ADDRESS_MATCH")
    if policy is AddressPolicy.ADD:
        missing = data.missing_for_add()
        if missing:
            raise ValueError("新增地址缺少字段: " + ",".join(missing))
    if policy is AddressPolicy.AUTO and not data.match.strip():
        missing = data.missing_for_add()
        if missing:
            raise ValueError("auto 无匹配关键字且新增地址缺少字段: " + ",".join(missing))
    return self._ensure_shipping_address_ui(policy, data)
```

- [ ] **Step 4: Write failing tests for existing/auto/add decisions**

```python
def test_auto_selects_matching_existing_address_without_adding():
    driver = FakeShippingDriver.with_address_book(["Tester +63******0994 Manila"])
    page = ShippingPage(driver)
    data = complete_address(match="0994")

    assert page.ensure_shipping_address(AddressPolicy.AUTO, data) is True
    assert "新增地址" not in driver.clicks
    assert driver.selected_address == "Tester +63******0994 Manila"


def test_auto_adds_when_matching_address_is_absent():
    driver = FakeShippingDriver.with_address_book(["Other +63******0000 Cebu"])
    page = ShippingPage(driver)
    data = complete_address(match="0994")

    assert page.ensure_shipping_address(AddressPolicy.AUTO, data) is True
    assert "新增地址" in driver.clicks
    assert driver.address_form_values["phone"] == "+639621170994"
```

- [ ] **Step 5: Implement shared-address UI behavior**

Implement these concrete stages in `_ensure_shipping_address_ui`:

```python
def _ensure_shipping_address_ui(self, policy, data):
    if not self._click_text(("请选择收货地址", "收货地址", "配送地址")):
        raise AssertionError("提交订单页未打开公共地址簿")
    if policy is not AddressPolicy.ADD and data.match:
        if self.select_existing_shipping_address(data.match):
            return self.verify_shipping_address_applied(data)
        if policy is AddressPolicy.EXISTING:
            raise AssertionError("公共地址簿未找到匹配地址")
    self.add_shipping_address(data)
    if not self.select_existing_shipping_address(data.match or data.phone[-4:]):
        raise AssertionError("新增地址保存后未在公共地址簿中找到")
    return self.verify_shipping_address_applied(data)
```

`select_existing_shipping_address` scans displayed text/content-desc rows, scrolls the address-list container up to three times, and clicks only a row containing the requested match. `add_shipping_address` clicks “新增地址/添加地址”, selects country and city by exact visible text, fills labeled fields, saves once, and waits for either the address list or checkout markers. Every coordinate fallback must immediately assert the expected address form/list state.

- [ ] **Step 6: Add read-back verification and masked logging**

```python
def verify_shipping_address_applied(self, data):
    blob = self.page_blob()
    stable = [value for value in (data.name, data.phone[-4:], data.city) if value]
    matched = [value for value in stable if value in blob]
    if "请选择地址" in blob or len(matched) < 2:
        raise AssertionError("公共地址选择后未稳定回填到提交订单页")
    logger.info(
        "公共地址已应用 policy_match=%s phone=%s city=%s",
        bool(data.match),
        mask_phone(data.phone),
        data.city,
    )
    return True
```

- [ ] **Step 7: Run address tests**

Run: `pytest -q testcases/test_shipping_page.py -k "address"`

Expected: all selected tests pass and captured logs do not contain the full phone or detailed address.

- [ ] **Step 8: Commit address support**

```bash
git add pages/shipping_address_mixin.py pages/shipping_page.py testcases/test_shipping_page.py
git commit -m "feat: use public address book for shipping"
```

---

### Task 4: Earliest Future Delivery Slot

**Files:**
- Create: `pages/shipping_delivery_mixin.py`
- Modify: `pages/shipping_page.py`
- Modify: `testcases/test_shipping_page.py`

**Interfaces:**
- Consumes: `earliest_future_label`, `parse_delivery_date`, facade element helpers, and `page_blob`.
- Produces: `device_today() -> date`, `select_earliest_future_delivery(today: date | None = None) -> date`, and `verify_selected_delivery_date(selected: date, today: date) -> bool`.

- [ ] **Step 1: Write a failing interaction-order test**

```python
from datetime import date
import pytest


def test_device_today_uses_appium_device_clock():
    driver = FakeShippingDriver()
    driver.get_device_time = lambda: "2026-08-10T21:30:00+08:00"

    assert ShippingPage(driver).device_today() == date(2026, 8, 10)


def test_device_today_fails_closed_when_clock_is_unavailable():
    driver = FakeShippingDriver()
    driver.get_device_time = lambda: (_ for _ in ()).throw(RuntimeError("offline"))

    with pytest.raises(AssertionError, match="无法读取设备日期"):
        ShippingPage(driver).device_today()


def test_delivery_picker_selects_earliest_future_not_today():
    driver = FakeShippingDriver.with_delivery_dates(
        ["今天 19:15-19:45", "8月12日 20:15-20:45", "明天 19:45-20:15"]
    )
    page = ShippingPage(driver)

    selected = page.select_earliest_future_delivery(today=date(2026, 8, 10))

    assert selected == date(2026, 8, 11)
    assert "明天 19:45-20:15" in driver.clicks
    assert "今天 19:15-19:45" not in driver.clicks
```

- [ ] **Step 2: Run the delivery test and verify RED**

Run: `pytest -q testcases/test_shipping_page.py::test_delivery_picker_selects_earliest_future_not_today`

Expected: fails because `select_earliest_future_delivery` is missing.

- [ ] **Step 3: Implement device-date reading, picker discovery, strict filtering, and click**

```python
def device_today(self):
    try:
        raw = str(self.driver.get_device_time())
        return date.fromisoformat(raw[:10])
    except Exception as exc:
        raise AssertionError("无法读取设备日期，禁止选择配送时间") from exc


def select_earliest_future_delivery(self, today=None):
    base = today or self.device_today()
    if not self._click_text(("预约配送", "配送时间", "选择上门时间")):
        raise AssertionError("提交订单页未打开配送时间选择器")
    elements = self._delivery_candidate_elements()
    labels = [self._element_blob(element) for element in elements]
    chosen_label, chosen_date = earliest_future_label(labels, base)
    chosen = next(
        element for element in elements
        if self._element_blob(element) == chosen_label and self._element_enabled(element)
    )
    chosen.click()
    self._click_text(("确定", "确认"), required=False)
    self.verify_selected_delivery_date(chosen_date, base)
    logger.info("配送日期已选择 selected=%s today=%s", chosen_date, base)
    return chosen_date
```

`_delivery_candidate_elements` must reject `enabled=false`, `clickable=false`, and visible disabled styling markers before passing labels to the pure selector.

- [ ] **Step 4: Write failing tests for read-back rejection**

```python
import pytest


def test_delivery_readback_rejects_today_after_picker_click():
    driver = FakeShippingDriver.with_checkout_delivery_text("8月10日 19:15-19:45")

    with pytest.raises(AssertionError, match="严格晚于今天"):
        ShippingPage(driver).verify_selected_delivery_date(
            date(2026, 8, 10), date(2026, 8, 10)
        )


def test_delivery_readback_rejects_unparseable_text():
    driver = FakeShippingDriver.with_checkout_delivery_text("已预约")

    with pytest.raises(AssertionError, match="无法解析"):
        ShippingPage(driver).verify_selected_delivery_date(
            date(2026, 8, 11), date(2026, 8, 10)
        )
```

- [ ] **Step 5: Implement read-back verification**

```python
def verify_selected_delivery_date(self, selected, today):
    text = self._checkout_delivery_text()
    parsed = parse_delivery_date(text, today)
    if parsed is None:
        raise AssertionError("提交订单页配送时间无法解析")
    if parsed <= today:
        raise AssertionError("配送日期必须严格晚于今天")
    if parsed != selected:
        raise AssertionError(f"配送日期回读不一致 selected={selected} actual={parsed}")
    return True
```

- [ ] **Step 6: Run delivery tests**

Run: `pytest -q testcases/test_shipping_page.py -k "delivery"`

Expected: all selected tests pass.

- [ ] **Step 7: Commit delivery selection**

```bash
git add pages/shipping_delivery_mixin.py pages/shipping_page.py testcases/test_shipping_page.py
git commit -m "feat: require future shipping delivery slot"
```

---

### Task 5: Real Submission and Payment State Machine

**Files:**
- Create: `pages/shipping_payment_mixin.py`
- Modify: `pages/shipping_page.py`
- Modify: `testcases/test_shipping_page.py`

**Interfaces:**
- Consumes: `PaymentMethod`, `OrderPaymentState`, `classify_payment_state`, `can_cancel_payment`, selected address/date verification, and facade helpers.
- Produces: `submit_order_once() -> str | None`, `pay_balance(pay_password: str) -> bool`, `confirm_cash_on_delivery() -> bool`, `current_payment_state() -> OrderPaymentState`, `cancel_pending_payment() -> bool`, and `assert_payment_result(method) -> bool`.

- [ ] **Step 1: Write failing tests for single-submit behavior**

```python
def test_submit_order_clicks_once_even_if_button_remains_visible():
    driver = FakeShippingDriver.on_submit_page()
    driver.keep_submit_button_visible = True
    page = ShippingPage(driver)

    page.submit_order_once()
    page.submit_order_once()

    assert driver.clicks.count("提交订单") == 1
```

- [ ] **Step 2: Run the submit test and verify RED**

Run: `pytest -q testcases/test_shipping_page.py::test_submit_order_clicks_once_even_if_button_remains_visible`

Expected: fails because `submit_order_once` is missing.

- [ ] **Step 3: Implement an in-memory submit guard plus transition assertion**

```python
def submit_order_once(self):
    if getattr(self, "_shipping_order_submitted", False):
        logger.warning("已触发提交订单，阻止重复点击")
        return getattr(self, "_shipping_order_number", None)
    button = self._find_submit_order_button()
    if button is None:
        raise AssertionError("提交订单页未找到提交订单按钮")
    self._shipping_order_submitted = True
    button.click()
    if not self._wait_for_payment_or_order_detail():
        self.capture_shipping_failure("submit_transition_timeout")
        raise AssertionError("提交订单后未进入支付页或订单详情")
    self._shipping_order_number = self._read_order_number()
    logger.info("真实订单已提交 order_no=%s", self._shipping_order_number or "unavailable")
    return self._shipping_order_number
```

- [ ] **Step 4: Write failing tests for balance, COD, and unpaid cancellation**

```python
import pytest

from pages.shipping_types import OrderPaymentState, PaymentMethod


def test_balance_payment_requires_password_before_typing():
    driver = FakeShippingDriver.on_payment_page()
    with pytest.raises(ValueError, match="SHIPPING_PAY_PASSWORD"):
        ShippingPage(driver).pay_balance("")
    assert driver.sent_values == []


def test_paid_order_never_clicks_cancel_payment():
    driver = FakeShippingDriver.on_order_detail("已支付")
    page = ShippingPage(driver)

    assert page.current_payment_state() is OrderPaymentState.PAID
    assert page.cancel_pending_payment() is False
    assert "取消支付" not in driver.clicks


def test_pending_order_can_cancel_payment_and_verify_result():
    driver = FakeShippingDriver.on_order_detail("待支付")
    page = ShippingPage(driver)

    assert page.cancel_pending_payment() is True
    assert driver.clicks[-2:] == ["取消支付", "确定"]
    assert page.current_payment_state() is not OrderPaymentState.PENDING


def test_cod_does_not_type_password_or_cancel_payment():
    driver = FakeShippingDriver.on_payment_page()
    page = ShippingPage(driver)

    assert page.confirm_cash_on_delivery() is True
    assert driver.sent_values == []
    assert "取消支付" not in driver.clicks
```

- [ ] **Step 5: Implement balance and COD payment methods**

```python
def pay_balance(self, pay_password):
    if not pay_password:
        raise ValueError("余额支付需要 SHIPPING_PAY_PASSWORD")
    self._click_text(("余额支付", "余额"), required=True)
    self._click_text(("确认支付", "立即支付"), required=True)
    field = self._payment_password_field()
    if field is None:
        raise AssertionError("支付密码弹窗未找到输入框")
    field.send_keys(pay_password)
    self._click_text(("确定", "确认"), required=True)
    return self.assert_payment_result(PaymentMethod.BALANCE)


def confirm_cash_on_delivery(self):
    self._click_text(("货到付款",), required=True)
    self._click_text(("确认支付", "确认选择", "确定"), required=True)
    return self.assert_payment_result(PaymentMethod.COD)
```

Do not interpolate `pay_password` into any exception or log line. Payment logging is limited to `payment_method=balance password_configured=true`.

- [ ] **Step 6: Implement guarded unpaid cancellation**

```python
def cancel_pending_payment(self):
    state = self.current_payment_state()
    if not can_cancel_payment(state):
        logger.info("当前状态禁止取消支付 state=%s", state.value)
        return False
    self._click_text(("取消支付",), required=True)
    self._click_text(("确定", "确认取消"), required=True)
    if self.current_payment_state() is OrderPaymentState.PENDING:
        raise AssertionError("取消支付后订单仍为待支付")
    logger.info("待支付订单已取消支付")
    return True
```

- [ ] **Step 7: Add facade orchestration with explicit branch order**

```python
def run_order_flow(
    self,
    *,
    payment_method,
    cancel_unpaid,
    pay_password,
    address_policy,
    address_data,
):
    self.prevalidate_order_inputs(
        payment_method=payment_method,
        cancel_unpaid=cancel_unpaid,
        pay_password=pay_password,
        address_policy=address_policy,
        address_data=address_data,
    )
    if not self.enter_from_app_home():
        return False
    if not self.switch_to_delivery_orders():
        return False
    self.open_first_deliverable_package()
    self.ensure_shipping_address(address_policy, address_data)
    self.select_earliest_future_delivery()
    self.verify_checkout_ready()
    self.submit_order_once()
    if payment_method is PaymentMethod.COD:
        ok = self.confirm_cash_on_delivery()
    elif cancel_unpaid:
        self.leave_balance_payment_unconfirmed()
        ok = self.cancel_pending_payment()
    else:
        ok = self.pay_balance(pay_password)
    if ok:
        ok = self.switch_to_shipping_home() and self.switch_to_delivery_orders()
    return ok
```

`open_first_deliverable_package` must choose a package explicitly marked available for delivery/submit, not any historical order. `verify_checkout_ready` must assert applied address and a parseable future delivery date immediately before `submit_order_once`.

- [ ] **Step 8: Run all payment and page-flow tests**

Run: `pytest -q testcases/test_shipping_page.py`

Expected: all tests pass; no test creates a real Appium session.

- [ ] **Step 9: Commit the payment state machine**

```bash
git add pages/shipping_payment_mixin.py pages/shipping_page.py testcases/test_shipping_page.py
git commit -m "feat: handle shipping payment states safely"
```

---

### Task 6: Root `package.py` CLI and Preflight Boundary

**Files:**
- Create: `package.py`
- Create: `testcases/test_package_cli.py`

**Interfaces:**
- Consumes: `DriverManager`, `ShippingPage`, `AddressData`, `AddressPolicy`, and `PaymentMethod`.
- Produces: `build_parser()`, `read_address_data(environ)`, `read_pay_password(environ)`, `validate_args(args, address_data, pay_password)`, and `main(argv=None, environ=None) -> int`.

- [ ] **Step 1: Write failing parser and invalid-combination tests**

```python
import package


def test_cli_defaults_to_balance_and_auto_address():
    args = package.build_parser().parse_args([])
    assert args.payment_method == "balance"
    assert args.address_policy == "auto"
    assert args.cancel_unpaid is False


def test_cod_rejects_cancel_unpaid_before_driver_creation(monkeypatch):
    created = []
    monkeypatch.setattr(package, "DriverManager", lambda: created.append(True))

    code = package.main(
        ["--payment-method", "cod", "--cancel-unpaid"],
        environ={},
    )

    assert code == 2
    assert created == []
```

- [ ] **Step 2: Run CLI tests and verify RED**

Run: `pytest -q testcases/test_package_cli.py`

Expected: import fails because root `package.py` does not exist.

- [ ] **Step 3: Implement parser and environment readers**

```python
def build_parser():
    parser = argparse.ArgumentParser(description="国际货运真实订单自动化")
    parser.add_argument("--payment-method", choices=("balance", "cod"), default="balance")
    parser.add_argument("--cancel-unpaid", action="store_true")
    parser.add_argument("--address-policy", choices=("auto", "existing", "add"), default="auto")
    parser.add_argument("--session", default="shipping_business")
    parser.add_argument("--quit-driver", action="store_true")
    return parser


def read_address_data(environ):
    return AddressData(
        match=environ.get("SHIPPING_ADDRESS_MATCH", ""),
        name=environ.get("SHIPPING_ADDRESS_NAME", ""),
        phone=environ.get("SHIPPING_ADDRESS_PHONE", ""),
        country=environ.get("SHIPPING_ADDRESS_COUNTRY", ""),
        city=environ.get("SHIPPING_ADDRESS_CITY", ""),
        detail=environ.get("SHIPPING_ADDRESS_DETAIL", ""),
        postcode=environ.get("SHIPPING_ADDRESS_POSTCODE", ""),
    )
```

- [ ] **Step 4: Write failing preflight tests for every address/payment mode**

```python
import pytest


@pytest.mark.parametrize(
    ("argv", "environ", "error"),
    (
        (["--payment-method", "balance"], {}, "SHIPPING_PAY_PASSWORD"),
        (["--address-policy", "existing"], {"SHIPPING_PAY_PASSWORD": "secret"}, "SHIPPING_ADDRESS_MATCH"),
        (["--address-policy", "add"], {"SHIPPING_PAY_PASSWORD": "secret"}, "新增地址缺少字段"),
    ),
)
def test_preflight_failure_never_creates_driver(monkeypatch, argv, environ, error, caplog):
    created = []
    monkeypatch.setattr(package, "DriverManager", lambda: created.append(True))

    assert package.main(argv, environ=environ) == 2
    assert created == []
    assert error in caplog.text
```

- [ ] **Step 5: Implement preflight and main without secret logging**

```python
def validate_args(args, address_data, pay_password):
    method = PaymentMethod(args.payment_method)
    policy = AddressPolicy(args.address_policy)
    if args.cancel_unpaid and method is PaymentMethod.COD:
        raise ValueError("--cancel-unpaid 不能与 cod 组合")
    if method is PaymentMethod.BALANCE and not args.cancel_unpaid and not pay_password:
        raise ValueError("余额真实支付需要 SHIPPING_PAY_PASSWORD")
    if policy is AddressPolicy.EXISTING and not address_data.match.strip():
        raise ValueError("existing 地址策略需要 SHIPPING_ADDRESS_MATCH")
    if policy is AddressPolicy.ADD or (policy is AddressPolicy.AUTO and not address_data.match.strip()):
        missing = address_data.missing_for_add()
        if missing:
            raise ValueError("新增地址缺少字段: " + ",".join(missing))


def main(argv=None, environ=None):
    env = os.environ if environ is None else environ
    args = build_parser().parse_args(argv)
    address_data = read_address_data(env)
    pay_password = env.get("SHIPPING_PAY_PASSWORD", "")
    try:
        validate_args(args, address_data, pay_password)
    except ValueError as exc:
        logger.error("参数安全校验失败: %s", exc)
        return 2
    logger.info(
        "海运真实订单 payment_method=%s cancel_unpaid=%s address_policy=%s password_configured=%s",
        args.payment_method,
        args.cancel_unpaid,
        args.address_policy,
        bool(pay_password),
    )
    manager = DriverManager()
    try:
        driver = manager.get_driver(session_name=args.session)
        ok = ShippingPage(driver).run_order_flow(
            payment_method=PaymentMethod(args.payment_method),
            cancel_unpaid=args.cancel_unpaid,
            pay_password=pay_password,
            address_policy=AddressPolicy(args.address_policy),
            address_data=address_data,
        )
        return 0 if ok else 1
    finally:
        if args.quit_driver:
            manager.close_driver(session_name=args.session)
```

- [ ] **Step 6: Add a secret-redaction assertion**

```python
def test_cli_logs_never_contain_password_or_full_address(monkeypatch, caplog):
    env = complete_env(
        SHIPPING_PAY_PASSWORD="987654",
        SHIPPING_ADDRESS_DETAIL="Private Unit 123",
    )
    stub_successful_driver(monkeypatch)

    assert package.main([], environ=env) == 0
    assert "987654" not in caplog.text
    assert "Private Unit 123" not in caplog.text
```

- [ ] **Step 7: Run CLI tests**

Run: `pytest -q testcases/test_package_cli.py`

Expected: all tests pass and no real driver is created.

- [ ] **Step 8: Verify CLI help text**

Run: `python package.py --help`

Expected: exit code `0` and visible options for payment method, unpaid cancellation, address policy, session, and driver cleanup.

- [ ] **Step 9: Commit CLI**

```bash
git add package.py testcases/test_package_cli.py
git commit -m "feat: add shipping package command"
```

---

### Task 7: Regression, Static Safety Review, and Real-Device Preflight

**Files:**
- Modify only if a test exposes a shipping-scope defect: `pages/shipping_*.py`, `pages/shipping_page.py`, `package.py`, or their new tests.
- Do not modify unrelated application modules to silence failures.

**Interfaces:**
- Consumes: all interfaces produced by Tasks 1-6.
- Produces: fresh verification evidence, a clean shipping-scope diff, and a documented real-device readiness result.

- [ ] **Step 1: Run focused shipping tests**

Run: `pytest -q testcases/test_shipping_types.py testcases/test_shipping_page.py testcases/test_package_cli.py`

Expected: all focused tests pass with zero failures and zero errors.

- [ ] **Step 2: Run the complete regression suite**

Run: `pytest -q`

Expected: all repository tests pass. If an unrelated pre-existing failure occurs, record its exact test name and traceback; do not claim the suite is green.

- [ ] **Step 3: Compile every changed Python file**

Run: `python -m py_compile package.py pages/shipping_types.py pages/shipping_address_mixin.py pages/shipping_delivery_mixin.py pages/shipping_payment_mixin.py pages/shipping_page.py`

Expected: exit code `0` with no output.

- [ ] **Step 4: Scan changed code for secret leakage and fixed-coordinate primary selectors**

Run: `rg -n "pay_password|SHIPPING_PAY_PASSWORD|ADDRESS_DETAIL|clickGesture|tap\(" package.py pages/shipping_*.py`

Expected: password references only perform presence checks or `send_keys`; no log format includes the secret variable. Coordinate fallbacks are paired with page-state assertions and are not the first locator strategy.

- [ ] **Step 5: Inspect the final diff and scope**

Run: `git diff --check && git diff --stat && git status --short`

Expected: no whitespace errors; only planned shipping files/tests are modified by this implementation. Existing unrelated untracked files remain untouched.

- [ ] **Step 6: Run a non-mutating real-device preflight before any real order**

Run these checks without invoking `package.py`:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:4723/status
adb devices
python package.py --help
```

Expected: Appium reports ready, exactly one intended Android device is available or `ANDROID_DEVICE_NAME` identifies it, and CLI help succeeds. If Appium or address/payment environment data is missing, stop and report the concrete blocker before any order is created.

- [ ] **Step 7: Confirm required environment variables without printing values**

Run:

```powershell
$required = @('SHIPPING_ADDRESS_NAME','SHIPPING_ADDRESS_PHONE','SHIPPING_ADDRESS_COUNTRY','SHIPPING_ADDRESS_CITY','SHIPPING_ADDRESS_DETAIL','SHIPPING_ADDRESS_POSTCODE','SHIPPING_PAY_PASSWORD')
$required | ForEach-Object { [pscustomobject]@{ Name = $_; Configured = [bool](Get-Item "Env:$_" -ErrorAction SilentlyContinue) } }
```

Expected: every variable needed by the selected scenario reports `Configured=True`. The command must not print values.

- [ ] **Step 8: Execute exactly one user-authorized real scenario only when preflight is green**

Balance example:

```powershell
python package.py --payment-method balance --address-policy auto --quit-driver
```

COD example:

```powershell
python package.py --payment-method cod --address-policy existing --quit-driver
```

Unpaid-cancel example:

```powershell
python package.py --payment-method balance --cancel-unpaid --address-policy auto --quit-driver
```

Expected: run only one selected command, create at most one real order, and capture order number, selected future delivery time, payment method, final payment state, and diagnostic artifact paths. Never run all three examples as a batch.

- [ ] **Step 9: Re-run focused tests after any real-device locator adjustment**

Run: `pytest -q testcases/test_shipping_types.py testcases/test_shipping_page.py testcases/test_package_cli.py`

Expected: all focused tests pass after the final code state.

- [ ] **Step 10: Commit final shipping-scope adjustments**

```bash
git add package.py pages/shipping_types.py pages/shipping_address_mixin.py pages/shipping_delivery_mixin.py pages/shipping_payment_mixin.py pages/shipping_page.py testcases/test_shipping_types.py testcases/test_shipping_page.py testcases/test_package_cli.py
git commit -m "test: verify shipping business automation"
```

Skip this commit if Task 7 made no code or test changes.

---

## Completion Checklist

- [ ] Every new behavior was observed failing before its implementation was added.
- [ ] Focused shipping tests pass in the final code state.
- [ ] Full regression results are recorded accurately.
- [ ] Changed Python files compile.
- [ ] `package.py --help` succeeds.
- [ ] The flow starts from the App home page and clicks “国际货运”.
- [ ] Shipping home and delivery-order tabs switch both ways with state assertions.
- [ ] Existing and newly added public addresses are supported and verified after selection.
- [ ] The selected delivery date is strictly later than the device date and is re-read before submission.
- [ ] The submit button cannot be clicked twice in one page-object run.
- [ ] Balance, COD, and unpaid-cancel branches follow the explicit payment-state policy.
- [ ] Paid, COD, and unknown states never click “取消支付”.
- [ ] Logs contain required business evidence without secrets or full personal data.
- [ ] No paid or COD order is automatically cancelled.
- [ ] Any real-device run creates at most one user-authorized real order.
