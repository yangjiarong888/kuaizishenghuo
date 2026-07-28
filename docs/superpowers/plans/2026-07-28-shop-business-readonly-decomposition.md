# Mall Business Read-Only Decomposition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract mall search and product-detail read-only behavior from `ShopBusinessPage` into two testable mixins without changing its public API or business behavior.

**Architecture:** `ShopBusinessPage` remains the facade and composes `MallBusinessSearchMixin`, `MallBusinessDetailMixin`, and `ShopHomePage` in that order. Search owns shared interaction helpers and search-page behavior; detail owns product discovery and read-only detail browsing. Mutating cart, IM, checkout, and order methods remain in the facade.

**Tech Stack:** Python 3.11, pytest, Appium Python Client 5.2.7, Selenium, Android UiAutomator2.

## Global Constraints

- Preserve all existing public method names, signatures, return values, locator order, waits, retries, logs, and exception branches.
- Do not add or remove a click, swipe, key event, page transition, or fallback during mechanical extraction.
- Do not execute add-to-cart, share/copy-link, IM, checkout, order, payment, address, cancellation, stockout, or network-exception flows on the device.
- The only authorized device command is `--verify-navigation-only` with no mutation capability flags.
- Preserve `pages.shop_business_page.parse_price_text` as a re-export.
- `pages/shop_business_page.py` must finish at 650 lines or fewer.
- The three related production files combined must not exceed the baseline of 52 fixed sleeps and 47 broad exception handlers.
- Every production batch follows RED→GREEN, focused regression, full non-device regression, in-memory compilation, and a selective Git commit.
- Never stage `logs/`.

---

### Task 1: Extract Search and Shared Interaction Behavior

**Files:**
- Create: `pages/shop_business_search_mixin.py`
- Create: `testcases/test_shop_business_decomposition.py`
- Modify: `pages/shop_business_page.py:66-305`
- Modify: `pages/shop_business_page.py:361-590`
- Modify: `pages/shop_business_page.py:752-773`

**Interfaces:**
- Consumes: `self.driver`, `self._mall_ctx`, `self._window_size()`, `self._nearest_clickable_ancestor()`, `self._first_displayed_by_pkg_id()`, `self.ensure_mall_tab()`, `self.tap_top_back()`, and `self._current_activity_contains(name)`.
- Produces: `MallBusinessSearchMixin`; compatible `search_goods(keyword: str) -> bool` and the existing search/helper public surface on `ShopBusinessPage`.

- [ ] **Step 1: Write the failing search-mixin behavior tests**

Create `testcases/test_shop_business_decomposition.py`:

```python
import inspect

import pytest

from pages.shop_business_search_mixin import MallBusinessSearchMixin


pytestmark = pytest.mark.unit


SEARCH_METHODS = (
    "_safe_text",
    "_safe_desc",
    "_clean_xpath_text",
    "_page_contains_any",
    "_wait_page_contains_any",
    "_click_element_center",
    "_click_first_text_or_desc",
    "_type_into_best_edit_text",
    "_press_enter_or_search",
    "_swipe_fraction",
    "tap_search_entry",
    "_search_page_visible",
    "open_search_page",
    "_bounds_from_tag",
    "_tap_chip_below_title",
    "_tap_first_chip_below_title",
    "browse_search_landing",
    "tap_search_result_filters",
    "_tap_sort_control",
    "tap_secondary_category_filters",
    "browse_special_deals_products",
    "browse_search_results",
    "search_goods",
)


@pytest.mark.parametrize("name", SEARCH_METHODS)
def test_search_mixin_keeps_method_surface(name):
    assert callable(getattr(MallBusinessSearchMixin, name))


class SearchRecorder(MallBusinessSearchMixin):
    def __init__(self, *, open_ok=True, type_ok=True):
        self.open_ok = open_ok
        self.type_ok = type_ok
        self.events = []

    def open_search_page(self):
        self.events.append(("open",))
        return self.open_ok

    def browse_search_landing(self):
        self.events.append(("landing",))

    def _type_into_best_edit_text(self, text, *, allow_open_search=True):
        self.events.append(("type", text, allow_open_search))
        return self.type_ok

    def _press_enter_or_search(self):
        self.events.append(("submit",))

    def _wait_page_contains_any(self, markers, timeout=8.0):
        self.events.append(("wait", tuple(markers), timeout))
        return True

    def browse_search_results(self):
        self.events.append(("browse-results",))


def test_search_goods_keeps_bound_sequence(monkeypatch):
    from pages import shop_business_search_mixin

    monkeypatch.setattr(
        shop_business_search_mixin.time,
        "sleep",
        lambda _seconds: None,
    )
    page = SearchRecorder()

    assert inspect.ismethod(page.search_goods)
    assert page.search_goods(" 可乐 ") is True
    assert page.events == [
        ("open",),
        ("landing",),
        ("type", "可乐", True),
        ("submit",),
        (
            "wait",
            ("可乐", "综合", "销量", "价格", "商品", "搜索"),
            8.0,
        ),
        ("browse-results",),
    ]


def test_search_failure_stops_before_typing():
    page = SearchRecorder(open_ok=False)

    assert page.search_goods("可乐") is False
    assert page.events == [("open",)]


def test_empty_search_stops_before_page_navigation():
    page = SearchRecorder()

    assert page.search_goods("  ") is False
    assert page.events == []
```

- [ ] **Step 2: Run the new test and verify RED**

Run:

```powershell
..\Scripts\python.exe -m pytest -q testcases\test_shop_business_decomposition.py
```

Expected: collection fails with `ModuleNotFoundError: pages.shop_business_search_mixin`.

- [ ] **Step 3: Create the search mixin and move the exact methods**

Create `pages/shop_business_search_mixin.py` with these imports:

```python
"""Shared interaction and read-only search behavior for ShopBusinessPage."""
from __future__ import annotations

import re
import time
from typing import Iterable, Optional, Sequence, Tuple

from appium.webdriver.common.appiumby import AppiumBy

from commons.logger import setup_logger
from pages.shop_locators import (
    SHOP_SEARCH_ID_SUFFIXES,
    SHOP_TEXT_DAILY_BAIHUO,
)

logger = setup_logger(__name__)


class MallBusinessSearchMixin:
    """Search-page behavior; host supplies ShopHomePage capabilities."""
```

Move these methods from `ShopBusinessPage` without changing their bodies:

```text
_safe_text
_safe_desc
_clean_xpath_text
_page_contains_any
_wait_page_contains_any
_click_element_center
_click_first_text_or_desc
_type_into_best_edit_text
_press_enter_or_search
_swipe_fraction
tap_search_entry
_search_page_visible
open_search_page
_bounds_from_tag
_tap_chip_below_title
_tap_first_chip_below_title
browse_search_landing
tap_search_result_filters
_tap_sort_control
tap_secondary_category_filters
browse_special_deals_products
browse_search_results
search_goods
```

Do not move `_current_activity_contains`, checkout/address helpers, random category methods, random add-cart methods, or `run_category_and_activity_explore`.

- [ ] **Step 4: Compose the search mixin into the facade**

In `pages/shop_business_page.py`:

```python
from pages.shop_business_search_mixin import MallBusinessSearchMixin


class ShopBusinessPage(
    MallBusinessSearchMixin,
    ShopHomePage,
):
    """面向商城业务的高层自动化入口。"""
```

Remove only imports that are no longer used by the remaining facade. Keep `re` because the facade still owns `parse_price_text`, and keep `AppiumBy`, `random`, and `time` for remaining methods.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run:

```powershell
..\Scripts\python.exe -m pytest -q `
  testcases\test_shop_business_decomposition.py `
  testcases\test_shop_home_navigation.py `
  testcases\test_mall_order_safety.py
```

Expected: all selected tests pass.

- [ ] **Step 6: Compile and commit the search extraction**

Run:

```powershell
..\Scripts\python.exe -c "from pathlib import Path; files=sorted(p for p in Path('.').rglob('*.py') if '__pycache__' not in p.parts); [compile(p.read_text(encoding='utf-8-sig'), str(p), 'exec') for p in files]; print(f'compiled={len(files)}')"
git add -- pages/shop_business_search_mixin.py pages/shop_business_page.py testcases/test_shop_business_decomposition.py
git diff --cached --check
git commit -m "refactor: extract mall business search"
```

Expected: compilation succeeds and `logs/` is not staged.

---

### Task 2: Extract Product Discovery and Detail Browsing

**Files:**
- Create: `pages/shop_business_detail_mixin.py`
- Modify: `testcases/test_shop_business_decomposition.py`
- Modify: `pages/shop_business_page.py:775-1142`
- Modify: `pages/shop_business_page.py:1388-1395`

**Interfaces:**
- Consumes: `search_goods(keyword)`, shared interaction helpers from `MallBusinessSearchMixin`, and list/detail capabilities from `ShopHomePage`.
- Produces: `MallBusinessDetailMixin`; compatible `open_goods_detail(keyword: Optional[str] = None) -> bool`; `parse_price_text(raw: str) -> Optional[float]` in the detail module and re-exported from the facade.

- [ ] **Step 1: Add failing detail sequence and compatibility tests**

Append to `testcases/test_shop_business_decomposition.py`:

```python
from pages.shop_business_detail_mixin import (
    MallBusinessDetailMixin,
    parse_price_text,
)


DETAIL_METHODS = (
    "_product_candidate_roots",
    "_tap_first_search_result_image_by_source_bounds",
    "_tap_first_search_grid_goods_by_source_bounds",
    "open_first_visible_goods_detail",
    "_category_goods_item_price",
    "_tap_category_goods_item",
    "_tap_first_category_goods_item",
    "open_goods_detail",
    "tap_detail_main_image",
    "swipe_detail_to_content",
    "tap_detail_activity_info_if_visible",
    "tap_view_more_goods_if_visible",
    "tap_detail_back_to_top",
    "browse_goods_detail",
    "open_and_browse_goods_detail",
)


@pytest.mark.parametrize("name", DETAIL_METHODS)
def test_detail_mixin_keeps_method_surface(name):
    assert callable(getattr(MallBusinessDetailMixin, name))


class DetailRecorder(MallBusinessDetailMixin):
    def __init__(
        self,
        *,
        already_detail=False,
        search_ok=True,
        open_ok=True,
    ):
        self.already_detail = already_detail
        self.search_ok = search_ok
        self.open_ok = open_ok
        self.events = []

    def _is_mall_product_detail_visible(self):
        self.events.append(("is-detail",))
        return self.already_detail

    def search_goods(self, keyword):
        self.events.append(("search", keyword))
        return self.search_ok

    def ensure_mall_tab(self):
        self.events.append(("mall-tab",))
        return True

    def open_first_visible_goods_detail(self):
        self.events.append(("open-first",))
        return self.open_ok


def test_open_goods_detail_searches_before_opening_product():
    page = DetailRecorder()

    assert page.open_goods_detail("可乐") is True
    assert page.events == [
        ("is-detail",),
        ("search", "可乐"),
        ("open-first",),
    ]


def test_open_goods_detail_stops_when_search_fails():
    page = DetailRecorder(search_ok=False)

    assert page.open_goods_detail("可乐") is False
    assert page.events == [
        ("is-detail",),
        ("search", "可乐"),
    ]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("₱33.00", 33.0),
        ("P 12.5", 12.5),
        ("20", None),
        ("", None),
    ],
)
def test_detail_price_parser_keeps_behavior(raw, expected):
    assert parse_price_text(raw) == expected


def test_facade_reexports_price_parser():
    from pages.shop_business_page import (
        parse_price_text as facade_parse_price_text,
    )

    assert facade_parse_price_text("₱33.00") == 33.0
```

- [ ] **Step 2: Run the detail tests and verify RED**

Run:

```powershell
..\Scripts\python.exe -m pytest -q testcases\test_shop_business_decomposition.py
```

Expected: collection fails with `ModuleNotFoundError: pages.shop_business_detail_mixin`.

- [ ] **Step 3: Create the detail mixin and move the exact methods**

Create `pages/shop_business_detail_mixin.py`:

```python
"""Product discovery and read-only detail browsing for ShopBusinessPage."""
from __future__ import annotations

import re
import time
from typing import Optional

from appium.webdriver.common.appiumby import AppiumBy

from commons.logger import setup_logger
from pages.shop_locators import (
    SHOP_ID_CL_ITEM_CONTAINER,
    SHOP_ID_GOODS_LIST_ITEM,
    SHOP_ID_IMAGE,
    SHOP_ID_IV_GOODS,
    SHOP_ID_IV_UP_TO_TOP,
    SHOP_ID_MALL_ACTIVITY,
    SHOP_ID_MALL_ACTIVITY_INFO,
    SHOP_ID_MALL_DETAIL_MORE,
    SHOP_ID_MALL_DETAIL_VIEWPAGER,
    SHOP_ID_RV_CONTENT,
    SHOP_ID_RV_GOODS,
    SHOP_ID_TV_GOODS_NAME,
    SHOP_ID_TV_PRICE,
)

logger = setup_logger(__name__)


class MallBusinessDetailMixin:
    """Product/detail behavior; host supplies search and home capabilities."""
```

Move these methods without changing their bodies:

```text
_product_candidate_roots
_tap_first_search_result_image_by_source_bounds
_tap_first_search_grid_goods_by_source_bounds
open_first_visible_goods_detail
_category_goods_item_price
_tap_category_goods_item
_tap_first_category_goods_item
open_goods_detail
tap_detail_main_image
swipe_detail_to_content
tap_detail_activity_info_if_visible
tap_view_more_goods_if_visible
tap_detail_back_to_top
browse_goods_detail
open_and_browse_goods_detail
```

Move the existing module-level function unchanged below the class:

```python
def parse_price_text(raw: str) -> Optional[float]:
    text = (raw or "").replace(",", "").strip()
    m = re.search(
        r"(?:₱|P|￥|¥)?\s*(\d+(?:\.\d{1,2})?)",
        text,
        flags=re.I,
    )
    if not m:
        return None
    if (
        not any(mark in text for mark in ("₱", "P", "￥", "¥", "元"))
        and "." not in m.group(1)
    ):
        return None
    return float(m.group(1))
```

- [ ] **Step 4: Compose the detail mixin and preserve the parser export**

In `pages/shop_business_page.py`:

```python
from pages.shop_business_detail_mixin import (
    MallBusinessDetailMixin,
    parse_price_text,
)


class ShopBusinessPage(
    MallBusinessSearchMixin,
    MallBusinessDetailMixin,
    ShopHomePage,
):
    """面向商城业务的高层自动化入口。"""
```

Delete the old local `parse_price_text` definition. Remove only locator imports that no remaining facade method uses.

- [ ] **Step 5: Run focused and full non-device regression**

Run:

```powershell
..\Scripts\python.exe -m pytest -q `
  testcases\test_shop_business_decomposition.py `
  testcases\test_shop_home_navigation.py `
  testcases\test_mall_order_safety.py `
  testcases\test_mall_order_cli.py
..\Scripts\python.exe -m pytest -m "not device" -q
```

Expected: all focused and non-device tests pass with zero failures.

- [ ] **Step 6: Compile and commit the detail extraction**

Run:

```powershell
..\Scripts\python.exe -c "from pathlib import Path; files=sorted(p for p in Path('.').rglob('*.py') if '__pycache__' not in p.parts); [compile(p.read_text(encoding='utf-8-sig'), str(p), 'exec') for p in files]; print(f'compiled={len(files)}')"
git add -- pages/shop_business_detail_mixin.py pages/shop_business_page.py testcases/test_shop_business_decomposition.py
git diff --cached --check
git commit -m "refactor: extract mall business detail"
```

Expected: compilation succeeds and `logs/` remains untracked.

---

### Task 3: Static Compatibility and Safety Verification

**Files:**
- Verify: `pages/shop_business_search_mixin.py`
- Verify: `pages/shop_business_detail_mixin.py`
- Verify: `pages/shop_business_page.py`
- Verify: `scripts/run_mall_order_flow.py`
- Verify: `testcases/test_shop_business_decomposition.py`

**Interfaces:**
- Consumes: final facade and mixins from Tasks 1-2.
- Produces: exact offline evidence, size metrics, wait/exception counts, and proof that strict navigation rejects mutation flags.

- [ ] **Step 1: Run all mall-focused and full non-device tests**

Run:

```powershell
$tests = @(Get-ChildItem testcases -Filter 'test_mall_order_*.py' |
    Select-Object -ExpandProperty FullName) +
    (Resolve-Path testcases\test_shop_home_navigation.py).Path +
    (Resolve-Path testcases\test_shop_business_decomposition.py).Path
..\Scripts\python.exe -m pytest -q $tests
..\Scripts\python.exe -m pytest -m "not device" -q
```

Record exact pass and deselected counts.

- [ ] **Step 2: Compile all Python files in memory**

Run:

```powershell
..\Scripts\python.exe -c "from pathlib import Path; files=sorted(p for p in Path('.').rglob('*.py') if '__pycache__' not in p.parts); [compile(p.read_text(encoding='utf-8-sig'), str(p), 'exec') for p in files]; print(f'compiled={len(files)}')"
```

Record the exact compiled file count.

- [ ] **Step 3: Verify facade size and combined residual counts**

Run:

```powershell
(Get-Content -Encoding UTF8 pages\shop_business_page.py).Count
rg -n 'time\.sleep\(' `
  pages\shop_business_page.py `
  pages\shop_business_search_mixin.py `
  pages\shop_business_detail_mixin.py
rg -n 'except\s+(Exception|BaseException)|except\s*:' `
  pages\shop_business_page.py `
  pages\shop_business_search_mixin.py `
  pages\shop_business_detail_mixin.py
```

Acceptance:

- facade line count is at most `650`;
- fixed-wait count is at most `52`;
- broad-exception count is at most `47`.

- [ ] **Step 4: Verify imports, MRO, parser export, and navigation safety**

Run:

```powershell
..\Scripts\python.exe -c "from pages.shop_business_page import ShopBusinessPage, parse_price_text; from pages.shop_business_search_mixin import MallBusinessSearchMixin; from pages.shop_business_detail_mixin import MallBusinessDetailMixin; assert ShopBusinessPage.__mro__[1:4] == (MallBusinessSearchMixin, MallBusinessDetailMixin, __import__('pages.shop_home_page', fromlist=['ShopHomePage']).ShopHomePage); assert parse_price_text('₱33.00') == 33.0; print('compatibility=ok')"
..\Scripts\python.exe scripts\run_mall_order_flow.py `
  --verify-navigation-only `
  --allow-cart-mutation
```

Expected:

- compatibility command prints `compatibility=ok`;
- invalid CLI combination exits `2` before Driver creation and reports a navigation-only conflict.

- [ ] **Step 5: Review the final diff**

Run:

```powershell
git diff --check
git status --short
git diff --stat
```

Verify that only the planned files are modified and `logs/` is not staged.

---

### Task 4: Strict Read-Only Device Run and Review Report

**Files:**
- Create: `docs/reviews/2026-07-28-shop-business-readonly-decomposition-review.md`
- Modify: `docs/superpowers/plans/2026-07-28-shop-business-readonly-decomposition.md`

**Interfaces:**
- Consumes: connected Android device `P7T4XC99CYAEYL4H`, Appium on `127.0.0.1:4723`, and the verified strict navigation CLI.
- Produces: exit-code evidence, screenshot, sanitized XML, zero-mutation log review, residual-risk report, and completed plan checkboxes.

- [ ] **Step 1: Reconfirm device and Appium without changing settings**

Run:

```powershell
$adb = 'C:\Users\18718\AppData\Local\Android\Sdk\platform-tools\adb.exe'
& $adb devices -l
& $adb shell settings get global airplane_mode_on
& $adb shell settings get global wifi_on
Invoke-RestMethod -Uri 'http://127.0.0.1:4723/status'
```

Expected: the configured serial is `device`, Appium is ready, and no setting is changed.

- [ ] **Step 2: Run only strict navigation verification**

Run:

```powershell
..\Scripts\python.exe scripts\run_mall_order_flow.py `
  --verify-navigation-only `
  --product-source search `
  --keyword "可乐" `
  --session mall_readonly_decomposition_verify `
  --start-mode activate `
  --quit-driver
```

Forbidden flags include every `--allow-*` mutation capability, `--submit-order`, address actions, cart actions, exception modes, IM, and cancellation.

- [ ] **Step 3: Inspect evidence and confirm zero business-data mutation**

Verify:

- command exit code is `0`;
- Driver closes normally;
- latest `mall_navigation_verification.png` shows a product detail page;
- corresponding XML exists and sensitive phone/code/password-like values are redacted;
- log contains search, detail snapshot, and back navigation;
- log contains no executed add-cart, share, IM, checkout, submit, pay, address mutation, cancellation, stockout, or network-exception action.

Do not claim device compatibility for excluded flows.

- [ ] **Step 4: Write the review report**

Create `docs/reviews/2026-07-28-shop-business-readonly-decomposition-review.md` with:

- exact commits and changed files;
- before/after facade line count;
- focused/non-device test counts and compile count;
- combined wait and broad-exception counts;
- device serial/model, Appium version, command, exit code, duration, post-run Activity;
- screenshot, XML, and log paths;
- explicit zero-mutation statement;
- excluded device coverage;
- next recommended wait/exception governance batch.

- [ ] **Step 5: Mark the plan complete and commit the report**

Mark all completed checkboxes in this plan, then run:

```powershell
git add -- `
  docs/reviews/2026-07-28-shop-business-readonly-decomposition-review.md `
  docs/superpowers/plans/2026-07-28-shop-business-readonly-decomposition.md
git diff --cached --check
git commit -m "docs: verify mall read-only decomposition"
```

Expected: report and plan are committed; `logs/` remains local and untracked.
