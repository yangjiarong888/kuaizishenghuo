# Complete Takeout Business and Real COD Regression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one ordered takeout journey from the takeout home through paging, cart entry, filters, two full IM exchanges, two search matrices, Wangwang merchant behavior, one real COD order, and verified cancellation.

**Architecture:** Focused takeout mixins own home, IM, and merchant behavior; `TakeoutPageBase` composes them with the existing checkout mixin. A single orchestration method emits numbered stages, stops on the first failure, captures evidence, and delegates the existing checkout/cancel flow with fixed safe parameters.

**Tech Stack:** Python 3, Appium Python client, Selenium, pytest, existing takeout Page Object mixins, `commons.diagnostics`, and the shared search contract from `docs/superpowers/plans/2026-08-25-shared-search-foundation-home-mall.md`.

**Spec:** `docs/superpowers/specs/2026-08-25-takeout-full-business-shared-search-design.md`

## Global Constraints

- Complete `docs/superpowers/plans/2026-08-25-shared-search-foundation-home-mall.md` first.
- Work only on the current `main` branch; preserve unrelated uncommitted changes and stage exact files only.
- Start the complete journey at the takeout home and use one Appium session and one main log.
- Browse at least three changed merchant screens before using the back-to-top action.
- Send text `测试内容，请忽略`, the first valid gallery photo, and the first available emoji in both takeout IM contexts.
- Search all nine fixed keywords at both takeout search entrances; product browsing must never add to cart.
- Reuse a non-empty Wangwang cart; add exactly one item only when the cart is explicitly empty.
- Real checkout uses a phone-bearing address, COD, day after tomorrow, and the fifth available time slot; no tomorrow fallback and no slot override in full-business mode.
- New-address search text is `2515 Syquia, Santa Ana, Maynila, Kalakhang Maynila`; contact is `test` followed by U+0020 SPACE; address photos use the first valid gallery image.
- Retain any real address created by the flow; do not delete it automatically.
- A real run creates at most one order and must cancel it before any rerun.
- Any failed stage stops immediately, captures evidence, is fixed, and is rerun before moving forward.

---

### Task 1: Ordered Stage Runner and Evidence Boundary

**Files:**
- Create: `pages/takeout_business_stage.py`
- Create: `testcases/test_takeout_business_stage.py`

**Interfaces:**
- Consumes: `commons.diagnostics.capture_failure` and a page object's `driver`.
- Produces: `TakeoutStageError`, `TakeoutStageResult`, and `run_takeout_stage(page, number, name, action)`.

- [ ] **Step 1: Write failing stage tests**

```python
def test_stage_runner_logs_order_and_returns_value(caplog):
    page = SimpleNamespace(driver=object())
    result = run_takeout_stage(page, 1, "外卖首页分页", lambda: "three-pages")
    assert result == TakeoutStageResult(1, "外卖首页分页", "three-pages")


def test_stage_runner_captures_and_raises_on_false(monkeypatch):
    captured = []
    monkeypatch.setattr(stage_module, "capture_failure", lambda *args, **kwargs: captured.append(args))
    page = SimpleNamespace(driver=object())
    with pytest.raises(TakeoutStageError) as exc:
        run_takeout_stage(page, 2, "购物车入口", lambda: False)
    assert exc.value.number == 2
    assert exc.value.name == "购物车入口"
    assert len(captured) == 1


def test_stage_runner_preserves_original_exception(monkeypatch):
    monkeypatch.setattr(stage_module, "capture_failure", lambda *args, **kwargs: None)
    with pytest.raises(TakeoutStageError) as exc:
        run_takeout_stage(SimpleNamespace(driver=object()), 3, "回顶", lambda: 1 / 0)
    assert isinstance(exc.value.__cause__, ZeroDivisionError)
```

- [ ] **Step 2: Verify the tests fail**

Run: `pytest testcases/test_takeout_business_stage.py -q`

Expected: module import fails.

- [ ] **Step 3: Implement the stage runner**

```python
@dataclass(frozen=True)
class TakeoutStageResult:
    number: int
    name: str
    value: object


class TakeoutStageError(AssertionError):
    def __init__(self, number: int, name: str):
        super().__init__(f"takeout stage failed {number:02d}_{name}")
        self.number, self.name = number, name


def run_takeout_stage(page, number: int, name: str, action: Callable[[], object]):
    label = f"{number:02d}_{name}"
    logger.info("阶段开始 %s", label)
    try:
        value = action()
        if value is False or value is None:
            raise AssertionError(label)
    except Exception as exc:
        capture_failure(page.driver, label, "artifacts/takeout_full_business")
        logger.error("阶段失败 %s error=%s", label, type(exc).__name__)
        raise TakeoutStageError(number, name) from exc
    logger.info("阶段通过 %s", label)
    return TakeoutStageResult(number, name, value)
```

- [ ] **Step 4: Run stage tests**

Run: `pytest testcases/test_takeout_business_stage.py -q`

Expected: all pass.

- [ ] **Step 5: Commit the stage boundary**

```bash
git add pages/takeout_business_stage.py testcases/test_takeout_business_stage.py
git commit -m "feat: add ordered takeout business stages"
```

---

### Task 2: Takeout Home Paging, Cart, Back-to-Top, Filter, and Category

**Files:**
- Create: `pages/takeout_home_business_mixin.py`
- Modify: `pages/takeout_locators.py`
- Create: `testcases/test_takeout_home_business.py`

**Interfaces:**
- Consumes: host methods `ensure_takeout_tab()`, `wait_merchant_list_present()`, `driver`, and existing safe click helpers.
- Produces: `browse_takeout_merchant_pages(min_pages=3)`, `open_home_floating_cart_and_return()`, `return_takeout_list_to_top()`, `verify_discount_filter_cycle()`, `open_congee_category_and_return()`, and `open_takeout_home_service_im()`.

- [ ] **Step 1: Write failing behavior tests with a recording host**

```python
def test_paging_requires_three_changed_merchant_sets():
    page = HomeRecorder([
        ("shop-a", "shop-b"),
        ("shop-c", "shop-d"),
        ("shop-e", "shop-f"),
    ])
    assert page.browse_takeout_merchant_pages(min_pages=3) == [
        ("shop-a", "shop-b"), ("shop-c", "shop-d"), ("shop-e", "shop-f")
    ]


def test_paging_rejects_unchanged_screen():
    page = HomeRecorder([("shop-a",), ("shop-a",), ("shop-a",)])
    assert page.browse_takeout_merchant_pages(min_pages=3) is False


def test_discount_filter_is_enabled_asserted_and_disabled():
    page = FilterRecorder()
    assert page.verify_discount_filter_cycle()
    assert page.events == ["enable", "assert_count", "assert_labels", "disable"]
```

Add equivalent recorder tests for cart entry/return, back-to-top restoring the category grid, and “粥粉面饺” entering a selected category result then returning home.

- [ ] **Step 2: Verify focused tests fail**

Run: `pytest testcases/test_takeout_home_business.py -q`

Expected: mixin import fails.

- [ ] **Step 3: Implement merchant snapshot and paging**

Collect visible merchant-name semantics into a sorted tuple, excluding filter labels, bottom navigation, product names, and badges. Swipe the merchant list once between snapshots. Require three unique non-empty snapshots and log each merchant tuple.

- [ ] **Step 4: Implement the four home interactions**

- Floating cart: click the right-side cart, assert cart-page markers, press back, and assert merchant list.
- Back to top: click the separate upward-arrow control, then assert the category labels including `粥粉面饺`.
- Discount: enable `满减活动`, assert filter count `1` and at least one result discount tag, then disable and assert inactive state.
- Category: click the top `粥粉面饺` icon/label, assert selected category plus result merchants, then return to the takeout home.
- Home service IM: click the top headset, assert the `24小时客服` conversation with text, image, and emoji entrances, and leave message sending to `TakeoutIMMixin`.

Use semantic labels and bounded source-derived coordinates before fixed screen ratios. Keep the floating cart and back-to-top locators distinct.

- [ ] **Step 5: Run the home-business tests**

Run: `pytest testcases/test_takeout_home_business.py testcases/test_takeout_reliability.py -q`

Expected: all pass.

- [ ] **Step 6: Commit the home business module**

```bash
git add pages/takeout_home_business_mixin.py pages/takeout_locators.py testcases/test_takeout_home_business.py
git commit -m "feat: automate takeout home business coverage"
```

---

### Task 3: Unified Takeout IM Text, Gallery Photo, and Emoji

**Files:**
- Create: `pages/takeout_im_mixin.py`
- Create: `testcases/test_takeout_im.py`

**Interfaces:**
- Consumes: a page with `driver`, click helpers, and a valid IM conversation already open.
- Produces: `send_takeout_im_bundle(message="测试内容，请忽略") -> bool` plus private text/photo/emoji helpers.

- [ ] **Step 1: Write failing ordered-action tests**

```python
def test_im_bundle_sends_and_verifies_all_three_payloads():
    page = IMRecorder()
    assert page.send_takeout_im_bundle()
    assert page.events == [
        ("send_text", "测试内容，请忽略"), "verify_text",
        "open_gallery", "pick_first_non_camera", "send_photo", "verify_photo",
        "open_emoji", "pick_first_emoji", "verify_emoji",
    ]


@pytest.mark.parametrize("failed_event", ["verify_text", "verify_photo", "verify_emoji"])
def test_im_bundle_stops_at_failed_verification(failed_event):
    page = IMRecorder(failed_event=failed_event)
    assert page.send_takeout_im_bundle() is False
    failure_index = page.events.index(failed_event)
    assert page.events == page.expected_events[: failure_index + 1]
```

- [ ] **Step 2: Verify tests fail**

Run: `pytest testcases/test_takeout_im.py -q`

Expected: mixin import fails.

- [ ] **Step 3: Implement exact text sending and verification**

Use a visible text input, clear stale text, type `测试内容，请忽略`, send, hide the keyboard if needed, and require the new outgoing text bubble to appear.

- [ ] **Step 4: Implement gallery selection and photo verification**

Click the image entrance, handle media permission if shown, select the first visible gallery tile whose semantics/bounds do not identify a camera tile, confirm when required, and require a new outgoing image bubble or attachment count change. Never click “跳过”.

- [ ] **Step 5: Implement emoji selection and verification**

Click the emoji entrance, choose the first enabled visible emoji/sticker item above the keyboard/navigation band, send if the UI requires a separate send action, and require a new outgoing emoji/sticker bubble.

- [ ] **Step 6: Run IM and gallery regression tests**

Run: `pytest testcases/test_takeout_im.py testcases/test_takeout_reliability.py -q`

Expected: all pass, including existing address-gallery behavior.

- [ ] **Step 7: Commit the IM module**

```bash
git add pages/takeout_im_mixin.py testcases/test_takeout_im.py
git commit -m "feat: send complete takeout IM bundle"
```

---

### Task 4: Takeout Home and Wangwang Search Adapters

**Files:**
- Create: `pages/takeout_home_search_adapter.py`
- Create: `pages/takeout_merchant_search_adapter.py`
- Create: `scripts/run_takeout_search_matrix.py`
- Create: `testcases/test_takeout_search_adapters.py`
- Create: `testcases/test_takeout_search_matrix_cli.py`
- Modify: `commons/logger.py`
- Modify: `testcases/test_logger.py`

**Interfaces:**
- Consumes: `SearchMatrixAdapter`, `SearchProductSummary`, and the host takeout page.
- Produces: `TakeoutHomeSearchAdapter(page)`, `TakeoutMerchantSearchAdapter(page)`, and standalone `--scope home|wangwang` search commands.

- [ ] **Step 1: Write failing contract tests for both adapters**

```python
@pytest.mark.parametrize("adapter_type,source", [
    (TakeoutHomeSearchAdapter, "外卖首页搜索"),
    (TakeoutMerchantSearchAdapter, "旺旺店内搜索"),
])
def test_takeout_adapter_runs_search_product_readback_and_return(adapter_type, source):
    page = FakeTakeoutSearchPage()
    adapter = adapter_type(page)
    assert adapter.source_name == source
    assert adapter.open_search()
    assert adapter.search_keyword("DUDAO22.5W超级快充迷")
    assert adapter.prefer_goods_results()
    assert adapter.open_first_goods()
    assert adapter.read_goods_summary("DUDAO22.5W超级快充迷").name == "DUDAO charger"
    assert adapter.return_to_results()
    assert adapter.finish_search()
```

- [ ] **Step 2: Verify tests fail**

Run: `pytest testcases/test_takeout_search_adapters.py -q`

Expected: both adapter modules are missing.

- [ ] **Step 3: Implement the external takeout-home adapter**

Enter from the takeout-home top search box, assert the external takeout search page, clear and submit each exact keyword, choose “商品” if result types coexist, open the first product result, read visible name/price/specification, return to results, and leave to the takeout home after keyword nine.

- [ ] **Step 4: Implement the Wangwang merchant adapter**

Enter through the Wangwang merchant-home search control, keep all operations inside that merchant, open the first product result, read visible name/price/specification, return to store results, and finish on the merchant home. It must never click a plus/add-cart control.

- [ ] **Step 5: Run adapter and shared-contract tests**

Run: `pytest testcases/test_takeout_search_adapters.py testcases/test_business_search_spec.py -q`

Expected: all pass.

- [ ] **Step 6: Add the standalone takeout search-matrix command**

`scripts/run_takeout_search_matrix.py` accepts `--scope home|wangwang`, creates one driver session, ensures the takeout home, enters Wangwang only for merchant scope, runs the matching adapter, captures `SearchMatrixError` evidence, and returns `1` on failure. Add logger mappings:

```python
if script == "run_takeout_search_matrix":
    scope = value_after("--scope").lower()
    return _sanitize_log_file_tag(
        "旺旺店内搜索矩阵" if scope == "wangwang" else "外卖首页搜索矩阵"
    )
```

Add CLI tests that fake `DriverManager`, assert exactly one adapter is dispatched, and assert the driver session is closed once.

- [ ] **Step 7: Run adapter, CLI, logger, and shared-contract tests**

Run: `pytest testcases/test_takeout_search_adapters.py testcases/test_takeout_search_matrix_cli.py testcases/test_business_search_spec.py testcases/test_logger.py -q`

Expected: all pass.

- [ ] **Step 8: Commit the takeout search adapters and CLI**

```bash
git add pages/takeout_home_search_adapter.py pages/takeout_merchant_search_adapter.py scripts/run_takeout_search_matrix.py commons/logger.py testcases/test_takeout_search_adapters.py testcases/test_takeout_search_matrix_cli.py testcases/test_logger.py
git commit -m "feat: adapt shared search matrix to takeout"
```

---

### Task 5: Wangwang Favorite, Merchant IM Entrances, and Cart Invariants

**Files:**
- Create: `pages/takeout_merchant_business_mixin.py`
- Create: `testcases/test_takeout_merchant_business.py`

**Interfaces:**
- Consumes: `send_takeout_im_bundle`, `run_search_matrix`, `TakeoutMerchantSearchAdapter`, and existing `shop_cart_has_purchasable_items()`.
- Produces: `ensure_takeout_merchant_favorited()`, `run_wangwang_merchant_im()`, `run_wangwang_search_matrix()`, and `assert_cart_reuse_or_empty()`.

- [ ] **Step 1: Write failing favorite and cart tests**

```python
def test_already_favorited_does_not_click():
    page = MerchantRecorder(favorited=True)
    assert page.ensure_takeout_merchant_favorited()
    assert page.favorite_clicks == 0


def test_not_favorited_clicks_once_and_reads_back():
    page = MerchantRecorder(favorited=False)
    assert page.ensure_takeout_merchant_favorited()
    assert page.favorite_clicks == 1
    assert page.favorited is True


def test_non_empty_cart_is_reused_without_add():
    page = MerchantRecorder(cart_has_items=True)
    assert page.assert_cart_reuse_or_empty() == "reuse"
    assert page.add_calls == 0
```

Add delegation tests proving the merchant IM entry method calls `send_takeout_im_bundle()` once and the merchant matrix calls the shared runner once.

- [ ] **Step 2: Verify focused tests fail**

Run: `pytest testcases/test_takeout_merchant_business.py -q`

Expected: mixin import fails.

- [ ] **Step 3: Implement idempotent favorite and IM entry methods**

Read the visual/semantic selected state before clicking. After one click, require selected state or a success message. Implement separate homepage-headset and merchant-chat entry locators, but delegate the conversation actions to the same IM bundle.

- [ ] **Step 4: Implement merchant search and cart decision**

Delegate search to `run_search_matrix(TakeoutMerchantSearchAdapter(self))`. Return the string `reuse` for a non-empty cart and `empty` only when the cart explicitly reports zero; treat unknown cart state as failure, not as permission to add.

- [ ] **Step 5: Run merchant and checkout boundary tests**

Run: `pytest testcases/test_takeout_merchant_business.py testcases/test_takeout_checkout_boundary.py -q`

Expected: all pass.

- [ ] **Step 6: Commit merchant behavior**

```bash
git add pages/takeout_merchant_business_mixin.py testcases/test_takeout_merchant_business.py
git commit -m "feat: add idempotent Wangwang business actions"
```

---

### Task 6: Compose Mixins and Implement the Full Ordered Flow

**Files:**
- Modify: `pages/takeout_shop_mixin.py`
- Modify: `pages/takeout_page.py:43-50`
- Create: `testcases/test_takeout_full_business_flow.py`

**Interfaces:**
- Consumes: all modules from Tasks 1-5 plus existing `run_shop_checkout_pay_and_cancel_flow`.
- Produces: `TakeoutPageBase.run_full_takeout_business(*, shop_name, address_policy, address_data, address_ordinal, address_contains, max_payable, submit_order) -> bool`.

- [ ] **Step 1: Write the failing exact-order orchestration test**

```python
def test_full_takeout_business_runs_exact_stage_order(monkeypatch):
    page = FullFlowRecorder()
    assert page.run_full_takeout_business(
        shop_name="旺旺超市 WWCS",
        address_policy="auto",
        address_data=object(),
        address_ordinal=None,
        address_contains=None,
        max_payable=5000,
        submit_order=True,
    )
    assert page.stage_names == [
        "外卖首页分页", "购物车入口", "回顶", "满减筛选", "粥粉面饺分类",
        "外卖首页客服IM", "外卖首页搜索矩阵", "旺旺进店", "商家收藏",
        "旺旺商家IM", "旺旺店内搜索矩阵", "购物车复用或单次加购", "真实COD下单并取消",
    ]
    assert page.checkout_kwargs["checkout_payment"] == "cod"
    assert page.checkout_kwargs["delivery_time_slot_ordinal"] == 5
    assert page.checkout_kwargs["delivery_slot_contains"] is None
    assert page.checkout_kwargs["submit_order"] is True
```

Add a second test in which stage 6 fails and assert stages 7-13 are never called.

- [ ] **Step 2: Verify the orchestration test fails**

Run: `pytest testcases/test_takeout_full_business_flow.py -q`

Expected: method is missing.

- [ ] **Step 3: Compose the focused mixins**

Update `TakeoutShopMixin` to inherit the home-business, merchant-business, IM, and existing checkout mixins. Resolve any method collision explicitly; do not duplicate methods from `TakeoutCheckoutMixin`.

- [ ] **Step 4: Implement the exact stage sequence**

Use `run_takeout_stage` for every numbered stage. Ensure Manila before stage 1, use the shared home-search adapter at stage 7, enter Wangwang only at stage 8, and delegate checkout at the last stage with these fixed values:

```python
submit_order=submit_order
checkout_payment="cod"
delivery_time_slot_ordinal=5
delivery_slot_contains=None
remark_text="test order"
```

Pass through only address policy/data/selection, the explicit finite `max_payable`, and the required internal `submit_order` boolean. Existing checkout logic remains responsible for phone-address enforcement, gallery address photo, cart reuse/empty-cart single add, payable validation, real submission, and cancellation. The public real CLI always passes `True`; the diagnostic preview CLI passes `False` and therefore stops before order submission.

- [ ] **Step 5: Run orchestration and reliability tests**

Run: `pytest testcases/test_takeout_full_business_flow.py testcases/test_takeout_reliability.py testcases/test_takeout_checkout_boundary.py -q`

Expected: all pass.

- [ ] **Step 6: Commit composition and orchestration**

```bash
git add pages/takeout_shop_mixin.py pages/takeout_page.py testcases/test_takeout_full_business_flow.py
git commit -m "feat: orchestrate complete takeout business flow"
```

---

### Task 7: Full-Business CLI, Fixed Safety Rules, and Log Tag

**Files:**
- Modify: `scripts/run_takeout_wangwang.py`
- Modify: `commons/logger.py`
- Modify: `testcases/test_takeout_cli.py`
- Modify: `testcases/test_logger.py`

**Interfaces:**
- Consumes: `TakeoutPageBase.run_full_takeout_business`.
- Produces: `--full-business` real mode and `--full-business-preview` non-ordering mode. Real mode creates one `外卖完整业务_旺旺超市_真实COD下单_YYYYMMDD_HHMMSS.log`.

- [ ] **Step 1: Write failing CLI safety tests**

```python
def test_full_business_requires_positive_max_payable():
    args = script.build_parser().parse_args(["--full-business"])
    with pytest.raises(ValueError, match="max-payable"):
        script.validate_args(args, environ=complete_address_env())


def test_full_business_dispatches_one_page_flow(monkeypatch):
    calls = []
    install_fake_driver_and_page(monkeypatch, calls)
    exit_code = script.main([
        "--full-business", "--max-payable", "5000", "--address-policy", "auto"
    ])
    assert exit_code == 0
    assert calls == [("run_full_takeout_business", True)]


def test_full_business_rejects_delivery_slot_overrides():
    args = script.build_parser().parse_args([
        "--full-business", "--max-payable", "5000",
        "--delivery-time-slot-ordinal", "4",
    ])
    with pytest.raises(ValueError, match="固定选择后天第5个"):
        script.validate_args(args, environ=complete_address_env())


def test_full_business_preview_dispatches_without_submission(monkeypatch):
    calls = []
    install_fake_driver_and_page(monkeypatch, calls)
    assert script.main(["--full-business-preview", "--address-policy", "auto"]) == 0
    assert calls == [("run_full_takeout_business", False)]
```

Add a logger test mapping `run_takeout_wangwang.py --full-business` to `外卖完整业务_旺旺超市_真实COD下单`.

- [ ] **Step 2: Verify CLI and logger tests fail**

Run: `pytest testcases/test_takeout_cli.py testcases/test_logger.py -q`

Expected: `--full-business` is unknown.

- [ ] **Step 3: Add full-business parsing and validation**

Add mutually exclusive `--full-business` and `--full-business-preview`. Real mode requires a finite positive `--max-payable`; both modes require complete address data when policy is `auto` or `add`. Reject `--delivery-slot-contains`; reject a supplied ordinal other than `5`. Neither dispatcher passes user-controlled delivery selection into the page flow.

- [ ] **Step 4: Dispatch one page method and one driver lifecycle**

When either full-business mode is present, instantiate `TakeoutPageBase(driver)` once and call `run_full_takeout_business(...)`, passing `submit_order=True` only for `--full-business`. Do not call the legacy `open_wangwang_supermarket_from_takeout_home()` first, because the full flow must begin on the takeout home and perform its own ordered navigation.

- [ ] **Step 5: Add the full-business log mapping**

In `_log_file_tag_from_env_or_argv()`, return `外卖完整业务_旺旺超市_真实COD下单` for `--full-business` and `外卖完整业务_安全预览` for `--full-business-preview`, before the legacy takeout flag composition.

- [ ] **Step 6: Run CLI, logger, and orchestration tests**

Run: `pytest testcases/test_takeout_cli.py testcases/test_logger.py testcases/test_takeout_full_business_flow.py -q`

Expected: all pass and old CLI tests remain unchanged.

- [ ] **Step 7: Commit CLI and logging changes**

```bash
git add scripts/run_takeout_wangwang.py commons/logger.py testcases/test_takeout_cli.py testcases/test_logger.py
git commit -m "feat: expose safe full takeout business command"
```

---

### Task 8: Automated Regression Before Device Mutation

**Files:**
- Modify only the exact implementation and matching test files that fail.

**Interfaces:**
- Consumes: the complete implementation.
- Produces: green focused and full test suites before device-side IM or order mutation.

- [ ] **Step 1: Run all new focused tests**

Run: `pytest testcases/test_business_search_spec.py testcases/test_takeout_business_stage.py testcases/test_takeout_home_business.py testcases/test_takeout_im.py testcases/test_takeout_search_adapters.py testcases/test_takeout_merchant_business.py testcases/test_takeout_full_business_flow.py testcases/test_takeout_cli.py testcases/test_logger.py -q`

Expected: all pass.

- [ ] **Step 2: Run the full suite**

Run: `pytest -q`

Expected: all tests pass and the repository's intentional deselection remains the only deselected case.

- [ ] **Step 3: Review the final diff for scope and accidental cart mutations**

Run: `git diff --check`

Run: `rg -n "add_first|加购|submit_order|delivery_time_slot_ordinal" pages/takeout_* scripts/run_takeout_wangwang.py`

Expected: search adapters contain no add-cart calls; full-business orchestration fixes ordinal `5`; only checkout performs submission.

- [ ] **Step 4: Commit any test-driven corrections**

Stage only the implementation file and its matching test file for each correction, then commit with message `fix: satisfy full takeout business regression`.

---

### Task 9: Ordered Non-Submitting Device Diagnosis

**Files:**
- Modify only the failed page adapter/mixin and its matching tests if real UI evidence requires a fix.

**Interfaces:**
- Consumes: connected device `P7T4XC99CYAEYL4H` and running Appium.
- Produces: verified non-ordering coverage before any real submission.

- [ ] **Step 1: Run App-home and mall matrices from the foundation plan**

Run: `python scripts/run_home_search_matrix.py`

Run: `python scripts/run_shop_business.py --action search_matrix`

Expected: all nine keywords pass in each command. On failure, stop, inspect evidence, fix and test the failed adapter, then rerun the same command.

- [ ] **Step 2: Run takeout-home non-ordering stages on the device**

Run: `python scripts/run_takeout_wangwang.py --full-business-preview --address-policy auto`

This exact preview command runs paging, floating-cart entry/return, back-to-top, discount cycle, category entry/return, both IM bundles, both takeout search matrices, Wangwang favorite, and checkout preparation, but passes `submit_order=False` and stops before real order submission.

Expected: stages occur in the specification order and no product is added.

- [ ] **Step 3: Run Wangwang non-ordering stages**

Enter Wangwang, verify idempotent favorite, send the merchant IM bundle, run all nine merchant searches, and inspect the cart without adding when non-empty.

Expected: no duplicate cart item and no order submission.

- [ ] **Step 4: Fix each device failure before continuing**

For a failed stage, use the numbered log, screenshot, sanitized XML, and Activity. Add a failing unit test reproducing the evidence, implement the minimal locator/state fix, run focused tests, then rerun the exact failed device command. Do not continue to the next stage while the current one fails.

- [ ] **Step 5: Commit verified device-specific fixes**

Stage only the changed takeout mixin/adapter and matching test, then commit with message `fix: harden takeout full-business device navigation`.

---

### Task 10: One Real COD Order and Verified Cancellation

**Files:**
- Do not change code unless the run exposes a reproducible defect; any defect starts with a failing test in the matching test file.

**Interfaces:**
- Consumes: complete green automated suite, passing non-ordering device flow, valid `.env` address fields, and explicit payable cap.
- Produces: exactly one new COD order that is subsequently cancelled and evidenced in one ordered business log.

- [ ] **Step 1: Confirm real-run prerequisites without submitting**

Verify the connected device, Appium status, logged-in account, gallery contains at least one image, address data is complete, and no previous uncancelled regression order remains.

- [ ] **Step 2: Run the complete real flow once**

Run: `python scripts/run_takeout_wangwang.py --full-business --address-policy auto --max-payable 5000`

Expected: one `外卖完整业务_旺旺超市_真实COD下单_YYYYMMDD_HHMMSS.log`; every numbered stage passes; checkout selects a phone-bearing COD address, day after tomorrow, and the fifth available slot; exactly one order is created and cancelled.

- [ ] **Step 3: Stop and inspect order state on any post-submit failure**

If the log indicates the submit action may have occurred, inspect the current order/detail page and cancel the existing order before rerunning. Never rerun the command while the previous order may still be active.

- [ ] **Step 4: Diagnose, test, fix, and rerun the same command**

Capture the failed stage's screenshot/XML/Activity, add a failing test, implement the minimal fix, run focused and full suites, ensure the prior order is cancelled, then rerun the exact Step 2 command.

- [ ] **Step 5: Record final evidence**

Report the business log path, actual selected delivery time, order creation assertion, cancellation assertion, total pytest result, and any real data created such as a retained address. Do not print full phone numbers or detailed address values.
