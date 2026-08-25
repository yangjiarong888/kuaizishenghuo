# Four-Entry Shared Search Foundation, App Home, and Mall Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the reusable nine-keyword search contract and apply it to the App home and mall-home search entrances without changing their existing single-search behavior.

**Architecture:** A locator-free runner owns keyword order, stop-on-failure semantics, and result records. Small adapters wrap the existing App-home and mall page objects; each adapter owns its own locators and navigation. CLIs expose matrix-only modes and business-specific log names.

**Tech Stack:** Python 3, Appium Python client, Selenium, pytest, existing page objects and `commons.diagnostics`.

**Spec:** `docs/superpowers/specs/2026-08-25-takeout-full-business-shared-search-design.md`

## Global Constraints

- Work only on the current `main` branch; do not create another branch.
- Preserve all pre-existing uncommitted work and stage only files named by each task.
- Keywords, in order: `旺仔牛奶`, `水`, `可乐`, `泡面`, `coffee`, `NVV床上`, `DUDAO22.5W超级快充迷`, `Adidas`, `Keep`.
- Strip only leading and trailing whitespace; preserve case, punctuation, digits, and mixed Chinese/English content.
- Every keyword must yield an openable product. Prefer the product result when product and merchant results coexist.
- Stop at the first failed keyword and capture sanitized evidence; never continue silently.
- Keep existing one-keyword commands compatible.
- Do not introduce third-party dependencies.

---

### Task 1: Locator-Free Search Matrix Contract

**Files:**
- Create: `pages/business_search_spec.py`
- Create: `testcases/test_business_search_spec.py`

**Interfaces:**
- Consumes: no page-specific code.
- Produces: `BUSINESS_SEARCH_KEYWORDS`, `SearchProductSummary`, `SearchMatrixAdapter`, `SearchMatrixError`, and `run_search_matrix(adapter, keywords=BUSINESS_SEARCH_KEYWORDS)`.

- [ ] **Step 1: Write failing keyword and runner tests**

```python
from pages.business_search_spec import (
    BUSINESS_SEARCH_KEYWORDS,
    SearchMatrixError,
    SearchProductSummary,
    run_search_matrix,
)


class RecordingAdapter:
    source_name = "recording"

    def __init__(self, fail_keyword=None):
        self.events = []
        self.fail_keyword = fail_keyword
        self.current = ""

    def open_search(self):
        self.events.append("open")
        return True

    def search_keyword(self, keyword):
        self.current = keyword
        self.events.append(("search", keyword))
        return keyword != self.fail_keyword

    def prefer_goods_results(self):
        self.events.append(("goods", self.current))
        return True

    def open_first_goods(self):
        self.events.append(("open_first", self.current))
        return True

    def read_goods_summary(self, keyword):
        self.events.append(("read", keyword))
        return SearchProductSummary(keyword, f"product-{keyword}", "₱1", "spec")

    def return_to_results(self):
        self.events.append(("back", self.current))
        return True

    def finish_search(self):
        self.events.append("finish")
        return True


def test_keywords_are_fixed_and_ordered():
    assert BUSINESS_SEARCH_KEYWORDS == (
        "旺仔牛奶", "水", "可乐", "泡面", "coffee", "NVV床上",
        "DUDAO22.5W超级快充迷", "Adidas", "Keep",
    )


def test_runner_visits_each_keyword_and_returns_summaries():
    adapter = RecordingAdapter()
    summaries = run_search_matrix(adapter)
    assert [item.keyword for item in summaries] == list(BUSINESS_SEARCH_KEYWORDS)
    assert adapter.events[0] == "open"
    assert adapter.events[-1] == "finish"


def test_runner_stops_at_first_failure():
    adapter = RecordingAdapter(fail_keyword="可乐")
    try:
        run_search_matrix(adapter)
    except SearchMatrixError as exc:
        assert exc.source == "recording"
        assert exc.keyword == "可乐"
        assert exc.stage == "search_keyword"
    else:
        raise AssertionError("SearchMatrixError not raised")
    assert ("search", "泡面") not in adapter.events
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `pytest testcases/test_business_search_spec.py -q`

Expected: collection fails because `pages.business_search_spec` does not exist.

- [ ] **Step 3: Implement the minimal contract and runner**

```python
from dataclasses import dataclass
from typing import Optional, Protocol, Sequence

BUSINESS_SEARCH_KEYWORDS = (
    "旺仔牛奶", "水", "可乐", "泡面", "coffee", "NVV床上",
    "DUDAO22.5W超级快充迷", "Adidas", "Keep",
)


@dataclass(frozen=True)
class SearchProductSummary:
    keyword: str
    name: str
    price: str = ""
    specification: str = ""


class SearchMatrixAdapter(Protocol):
    source_name: str
    def open_search(self) -> bool: ...
    def search_keyword(self, keyword: str) -> bool: ...
    def prefer_goods_results(self) -> bool: ...
    def open_first_goods(self) -> bool: ...
    def read_goods_summary(self, keyword: str) -> Optional[SearchProductSummary]: ...
    def return_to_results(self) -> bool: ...
    def finish_search(self) -> bool: ...


class SearchMatrixError(AssertionError):
    def __init__(self, source: str, stage: str, index: int, keyword: str):
        super().__init__(f"{source} search failed stage={stage} index={index} keyword={keyword!r}")
        self.source, self.stage, self.index, self.keyword = source, stage, index, keyword


def run_search_matrix(adapter: SearchMatrixAdapter, keywords: Sequence[str] = BUSINESS_SEARCH_KEYWORDS):
    normalized = tuple(value.strip() for value in keywords)
    if not adapter.open_search():
        raise SearchMatrixError(adapter.source_name, "open_search", 0, "")
    summaries = []
    for index, keyword in enumerate(normalized, 1):
        for stage, action in (
            ("search_keyword", lambda: adapter.search_keyword(keyword)),
            ("prefer_goods_results", adapter.prefer_goods_results),
            ("open_first_goods", adapter.open_first_goods),
        ):
            if not action():
                raise SearchMatrixError(adapter.source_name, stage, index, keyword)
        summary = adapter.read_goods_summary(keyword)
        if summary is None:
            raise SearchMatrixError(adapter.source_name, "read_goods_summary", index, keyword)
        summaries.append(summary)
        if not adapter.return_to_results():
            raise SearchMatrixError(adapter.source_name, "return_to_results", index, keyword)
    if not adapter.finish_search():
        raise SearchMatrixError(adapter.source_name, "finish_search", len(normalized), normalized[-1])
    return summaries
```

- [ ] **Step 4: Run the focused tests**

Run: `pytest testcases/test_business_search_spec.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit only the contract and tests**

```bash
git add pages/business_search_spec.py testcases/test_business_search_spec.py
git commit -m "feat: add shared business search matrix contract"
```

---

### Task 2: Business-Specific Unicode Log Names

**Files:**
- Modify: `commons/logger.py:21-75`
- Modify: `testcases/test_logger.py`

**Interfaces:**
- Consumes: script name plus `--action`, `--scope`, and `--full-business` from `sys.argv`.
- Produces: `_sanitize_log_file_tag(raw: str) -> str` that retains safe Chinese characters, `_log_file_tag_from_env_or_argv() -> str` mappings for matrix commands, and `_build_log_path()` using the business tag as the filename stem.

- [ ] **Step 1: Add failing log-tag tests**

```python
def test_log_tag_keeps_safe_chinese_business_name():
    assert logger_module._sanitize_log_file_tag("商城首页搜索矩阵") == "商城首页搜索矩阵"


def test_shop_search_matrix_uses_business_tag(monkeypatch):
    monkeypatch.delenv("CHOPSTICKLIFE_LOG_FILE_TAG", raising=False)
    monkeypatch.setattr(sys, "argv", ["scripts/run_shop_business.py", "--action", "search_matrix"])
    assert logger_module._log_file_tag_from_env_or_argv() == "商城首页搜索矩阵"


def test_home_search_matrix_uses_business_tag(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["scripts/run_home_search_matrix.py"])
    assert logger_module._log_file_tag_from_env_or_argv() == "App首页搜索矩阵"


def test_business_tag_replaces_generic_filename_stem(monkeypatch, tmp_path):
    monkeypatch.setenv("CHOPSTICKLIFE_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("CHOPSTICKLIFE_LOG_FILE_TAG", "商城首页搜索矩阵")
    assert logger_module._build_log_path().name.startswith("商城首页搜索矩阵_")
    assert not logger_module._build_log_path().name.startswith("chopsticklife_")
```

- [ ] **Step 2: Verify the tests fail**

Run: `pytest testcases/test_logger.py -q`

Expected: Chinese is stripped and matrix scripts do not map to business tags.

- [ ] **Step 3: Implement Windows-safe Unicode sanitization and script mappings**

Replace the ASCII-only expression with one that removes Windows-invalid filename characters and control characters while keeping Unicode letters. Move `value_after()` directly below the `argv`/`script` initialization so every script mapping can use it, then extend `_log_file_tag_from_env_or_argv()` before the takeout-specific branch:

```python
value = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", (raw or "").strip())
value = re.sub(r"\s+", "_", value).strip(" ._")

if script == "run_home_search_matrix":
    return _sanitize_log_file_tag("App首页搜索矩阵")
if script == "run_shop_business" and value_after("--action") == "search_matrix":
    return _sanitize_log_file_tag("商城首页搜索矩阵")
```

Update `_build_log_path()` so a non-empty tag replaces the generic stem:

```python
stem = tag or "chopsticklife"
return log_dir / f"{stem}_{timestamp}.log"
```

Keep secret redaction and existing takeout tag behavior unchanged.

- [ ] **Step 4: Run logger tests**

Run: `pytest testcases/test_logger.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit the logging change**

```bash
git add commons/logger.py testcases/test_logger.py
git commit -m "feat: name logs by search business"
```

---

### Task 3: Mall Search Matrix Adapter and CLI Mode

**Files:**
- Create: `pages/mall_search_matrix_adapter.py`
- Modify: `pages/shop_business_detail_mixin.py:379-401`
- Modify: `scripts/run_shop_business.py:36-130`
- Modify: `testcases/test_shop_business_decomposition.py`
- Create: `testcases/test_mall_search_matrix_adapter.py`

**Interfaces:**
- Consumes: `ShopBusinessPage`, `SearchProductSummary`, and `run_search_matrix`.
- Produces: `MallSearchMatrixAdapter(page)` implementing all `SearchMatrixAdapter` methods and CLI action `search_matrix`.

- [ ] **Step 1: Write adapter delegation and CLI dispatch tests**

```python
def test_mall_adapter_opens_reads_and_returns(monkeypatch):
    page = FakeMallPage()
    adapter = MallSearchMatrixAdapter(page)
    assert adapter.open_search()
    assert adapter.search_keyword("coffee")
    assert adapter.prefer_goods_results()
    assert adapter.open_first_goods()
    assert adapter.read_goods_summary("coffee").name == "Coffee Beans"
    assert adapter.return_to_results()


def test_search_matrix_action_dispatches_shared_runner(monkeypatch):
    calls = []
    monkeypatch.setattr(script, "run_search_matrix", lambda adapter: calls.append(adapter) or [])
    # Use the existing fake DriverManager/Page pattern in testcases/test_shop_business_decomposition.py.
    assert script.main(["--action", "search_matrix"]) == 0
    assert len(calls) == 1
```

Refactor `scripts/run_shop_business.main` to accept `argv: Optional[Sequence[str]] = None`, matching the existing takeout CLI test pattern.

- [ ] **Step 2: Run focused tests and verify failure**

Run: `pytest testcases/test_mall_search_matrix_adapter.py testcases/test_shop_business_decomposition.py -q`

Expected: adapter import and `search_matrix` action fail.

- [ ] **Step 3: Implement mall-specific navigation**

The adapter must:

- use `page.open_search_page()` once;
- clear and submit the existing mall search input for each keyword;
- click a visible “商品” tab only when present, otherwise accept a product-grid result page;
- call `page.open_first_visible_goods_detail()`;
- read name, price, and specification from visible detail semantics via a new `read_visible_goods_summary(keyword)` method;
- return once to the search results after each product and leave the search page after the ninth keyword.

Add this exact public helper to `MallBusinessDetailMixin`:

```python
def read_visible_goods_summary(self, keyword: str) -> Optional[SearchProductSummary]:
    if not self._is_mall_product_detail_visible():
        return None
    texts = self._visible_text_candidates_by_band(0.05, 0.90)
    name = next((text for text in texts if text and "₱" not in text), "")
    price = next((text for text in texts if "₱" in text), "")
    return SearchProductSummary(keyword=keyword, name=name, price=price)
```

Use the page's existing resource IDs and source-bound fallbacks; do not import takeout locators.

- [ ] **Step 4: Add the CLI action without changing existing actions**

Add `search_matrix` to `--action` choices and dispatch:

```python
elif args.action == "search_matrix":
    run_search_matrix(MallSearchMatrixAdapter(page))
    ok = True
```

Catch `SearchMatrixError`, call `capture_failure(driver, f"mall_search_{exc.index}_{exc.keyword}", "artifacts/mall_search")`, log source/stage/index/keyword, and return `1`.

- [ ] **Step 5: Run mall tests**

Run: `pytest testcases/test_mall_search_matrix_adapter.py testcases/test_shop_business_decomposition.py testcases/test_mall_order_cli.py -q`

Expected: all pass and pre-existing one-keyword behavior remains covered.

- [ ] **Step 6: Commit the mall adapter and CLI**

```bash
git add pages/mall_search_matrix_adapter.py pages/shop_business_detail_mixin.py scripts/run_shop_business.py testcases/test_mall_search_matrix_adapter.py testcases/test_shop_business_decomposition.py
git commit -m "feat: run shared search matrix from mall home"
```

---

### Task 4: App Home Search Matrix Adapter and Standalone Command

**Files:**
- Create: `pages/home_search_matrix_adapter.py`
- Modify: `pages/Home.py:464-503`
- Create: `scripts/run_home_search_matrix.py`
- Modify: `testcases/test_home.py`
- Create: `testcases/test_home_search_matrix_adapter.py`

**Interfaces:**
- Consumes: `ChopsticksTester`, `SearchProductSummary`, and `run_search_matrix`.
- Produces: `HomeSearchMatrixAdapter(tester)` and command `python scripts/run_home_search_matrix.py`.

- [ ] **Step 1: Write failing adapter tests**

```python
def test_home_adapter_prioritizes_goods_and_reads_first_product():
    tester = FakeHomeTester()
    adapter = HomeSearchMatrixAdapter(tester)
    assert adapter.open_search()
    assert adapter.search_keyword("Keep")
    assert adapter.prefer_goods_results()
    assert adapter.open_first_goods()
    assert adapter.read_goods_summary("Keep") == SearchProductSummary(
        keyword="Keep", name="Keep bottle", price="₱99", specification="500ml"
    )
    assert adapter.return_to_results()


def test_home_search_function_runs_full_matrix_when_requested(monkeypatch):
    tester = ChopsticksTester(driver=FakeDriver())
    called = []
    monkeypatch.setattr(home_module, "run_search_matrix", lambda adapter: called.append(adapter) or [])
    assert tester.run_home_search_matrix() == []
    assert len(called) == 1
```

- [ ] **Step 2: Verify focused tests fail**

Run: `pytest testcases/test_home_search_matrix_adapter.py testcases/test_home.py -q`

Expected: adapter and `run_home_search_matrix` are missing.

- [ ] **Step 3: Implement the App-home adapter**

Use only App-home/search-page selectors. The adapter must:

- call `tester.ensure_homepage()` and reuse `SEARCH_ELEMENTS` to enter search;
- locate `et_search`, clear it, type the exact keyword, and press search;
- choose “商品” when the result page exposes both products and merchants;
- open the first visible product card using its actual bounds;
- read visible product name, price, and specification;
- return to results after each detail and call `navigate_back_to_home_safe()` after all nine.

Add to `ChopsticksTester`:

```python
def run_home_search_matrix(self):
    return run_search_matrix(HomeSearchMatrixAdapter(self))
```

Keep `test_search_function_optimized()` for its existing light entry check; do not silently change callers that expect only entry verification.

- [ ] **Step 4: Add the standalone command with diagnostics**

The script must create session `home_search_matrix`, run the adapter, catch `SearchMatrixError`, call `capture_failure` under `artifacts/home_search`, return `1` on failure, and close only its owned session.

- [ ] **Step 5: Run home and diagnostic tests**

Run: `pytest testcases/test_home_search_matrix_adapter.py testcases/test_home.py testcases/test_diagnostics.py -q`

Expected: all pass.

- [ ] **Step 6: Commit the App-home implementation**

```bash
git add pages/home_search_matrix_adapter.py pages/Home.py scripts/run_home_search_matrix.py testcases/test_home.py testcases/test_home_search_matrix_adapter.py
git commit -m "feat: run shared search matrix from app home"
```

---

### Task 5: Foundation Regression and Non-Mutating Device Checks

**Files:**
- Modify only files from Tasks 1-4 if failures reveal defects.

**Interfaces:**
- Consumes: shared runner, mall adapter/CLI, and App-home adapter/CLI.
- Produces: a passing foundation ready for the takeout implementation plan.

- [ ] **Step 1: Run all focused unit tests**

Run: `pytest testcases/test_business_search_spec.py testcases/test_logger.py testcases/test_mall_search_matrix_adapter.py testcases/test_shop_business_decomposition.py testcases/test_home_search_matrix_adapter.py testcases/test_home.py -q`

Expected: all pass.

- [ ] **Step 2: Run the full unit suite**

Run: `pytest -q`

Expected: all existing tests pass; the repository's intentionally deselected test remains deselected.

- [ ] **Step 3: Run the App-home matrix on the connected device**

Run: `python scripts/run_home_search_matrix.py`

Expected: all nine searches open a product and return; one `App首页搜索矩阵_YYYYMMDD_HHMMSS.log` is created. This flow must not add goods or place an order.

- [ ] **Step 4: Diagnose before continuing if any keyword fails**

Inspect the generated screenshot, sanitized XML, Activity, and keyword stage. Fix the adapter, rerun its focused tests, then rerun the same command from Step 3. Do not proceed to mall until it passes.

- [ ] **Step 5: Run the mall matrix on the connected device**

Run: `python scripts/run_shop_business.py --action search_matrix`

Expected: all nine searches open a product and return; one `商城首页搜索矩阵_YYYYMMDD_HHMMSS.log` is created. No add-to-cart or order submission occurs.

- [ ] **Step 6: Diagnose and rerun the mall command on failure**

Use its evidence bundle, fix only the failed stage, rerun focused tests, then rerun the exact command from Step 5.

- [ ] **Step 7: Commit any verified device-specific locator fixes**

If the App-home adapter changed, run:

```bash
git add pages/home_search_matrix_adapter.py testcases/test_home_search_matrix_adapter.py
git commit -m "fix: harden app home search matrix locators"
```

If the mall adapter changed, run:

```bash
git add pages/mall_search_matrix_adapter.py testcases/test_mall_search_matrix_adapter.py
git commit -m "fix: harden mall search matrix locators"
```

Skip this step when no device-specific fix was needed. Do not stage unrelated dirty files.
