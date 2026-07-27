# Login and Home Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the broken main CLI, make login/home code testable through driver injection, and route home session ownership and failure evidence through the shared foundation without changing business flows.

**Architecture:** Production CLI code must never import pytest modules. Login method dispatch lives in `scripts/run_login.py`; `scripts/main.py` only parses and dispatches. `LoginPage` and `ChopsticksTester` accept injected drivers for offline tests, while default construction preserves DriverManager-backed real-device behavior.

**Tech Stack:** Python 3.11.9, pytest 8.3.5, Appium-Python-Client 5.2.7, Selenium 4.41.0.

## Global Constraints

- Preserve existing import paths `pages.login_page.LoginPage` and `pages.Home.ChopsticksTester`.
- Default CLI and test paths must not submit orders, pay, send verification codes, or mutate business data.
- Never import functions from `testcases` into production code.
- Every behavior change starts with a failing offline test.
- Keep the complete offline suite green after each task.
- Git is unavailable; record modified files without claiming commits.

---

### Task 1: Reproduce and Repair Main CLI Import/Dispatch

**Files:**
- Create: `testcases/test_main_cli.py`
- Create: `scripts/run_login.py`
- Modify: `scripts/main.py`

**Interfaces:**
- Produces: `scripts.main.build_parser()`, `scripts.main.main(argv: list[str] | None = None) -> int`, `scripts.run_login.run_login_method(method: str, *, page=None, from_home: bool = True, session_name: str | None = None) -> bool`.

- [ ] Write tests proving `scripts.main` imports, smoke mode calls only smoke, login without `--method` returns `2`, and login with `--method wechat` calls `run_login_method('wechat')`.
- [ ] Run `python -m pytest testcases/test_main_cli.py -q`; verify RED from the current bad `testcases.test_login` import.
- [ ] Add `scripts/run_login.py` with an allowlist mapping for `wechat`, `qq`, `google`, `phone`, `customer_service`, `password`, and `forget_password`. When `page` is absent, construct `LoginPage`, optionally enter from home except for customer service, call the selected bound method, and close only the owned DriverManager session.
- [ ] Refactor `scripts/main.py` to remove all `testcases` imports, accept injected `argv`, return integer exit codes, require `--method` for `login`, `method`, and `all`, and route `quick` to the safe smoke function because the referenced `quick_start_app` does not exist.
- [ ] Run focused tests, `python -c "import scripts.main"`, and the complete offline suite.

---

### Task 2: Injectable LoginPage Driver

**Files:**
- Create: `testcases/test_login_page_unit.py`
- Modify: `pages/login/login_page.py`

**Interfaces:**
- Preserve: `LoginPage(session_name='login_test', data=None)`.
- Extend: `LoginPage(session_name='login_test', data=None, driver=None)`; injected drivers are not created or closed by the page.

- [ ] Write a failing test with a fake driver and a DriverManager stub that raises if called; verify an injected driver is retained, implicit wait becomes `0`, and `LoginData` defaults are created.
- [ ] Verify RED because `LoginPage` does not accept `driver`.
- [ ] Add the optional keyword while preserving argument order and current WebDriverWait/data initialization.
- [ ] Run focused and complete offline tests.

---

### Task 3: Home Driver Ownership and Shared Failure Evidence

**Files:**
- Create: `testcases/test_home.py`
- Modify: `pages/Home.py`

**Interfaces:**
- Preserve: `ChopsticksTester()`.
- Extend: `ChopsticksTester(driver=None, session_name='home_comprehensive')`.
- Preserve: `setup_driver() -> bool`, `cleanup()`, `save_screenshot(name)`.

- [ ] Write failing tests proving injected drivers bypass DriverManager, owned drivers are obtained once through `DriverManager.get_driver`, cleanup closes only owned sessions, and `save_screenshot` delegates to `capture_failure`.
- [ ] Verify RED because constructor injection and shared diagnostics do not exist.
- [ ] Replace the duplicate `webdriver.Remote` and launch implementation in `setup_driver` with DriverManager delegation. Keep the existing boolean return contract and log only exception type on failure.
- [ ] Make `cleanup` call `DriverManager.close_driver` only for owned sessions; injected drivers remain open.
- [ ] Make `save_screenshot` call `capture_failure(self.driver, name, AppConfig.ARTIFACTS_DIR)` and return its screenshot path or `None`.
- [ ] Run `test_home.py`, transfer CLI compatibility tests, and the complete offline suite.

---

### Task 4: Login/Home Static and Offline Verification

**Files:**
- Create: `docs/reviews/2026-07-22-login-home-review.md`
- Verify: `scripts/main.py`, `scripts/run_login.py`, `pages/login/login_page.py`, `pages/Home.py`.

**Interfaces:**
- Produces: importable production entry points, fresh offline test evidence, and residual login/home risk counts.

- [ ] Compile all Python sources in memory without creating bytecode.
- [ ] Run `python -m pytest -m "not device" -q`; require zero failures.
- [ ] Run `python -c "import scripts.main; import scripts.run_login; from pages.Home import ChopsticksTester; from pages.login_page import LoginPage"`.
- [ ] Count `time.sleep`, broad exceptions, and files over 800 lines within login/home scope; record them as later decomposition work rather than mechanically changing untested behavior.
- [ ] Write the review report with exact test counts, fixed defects, compatibility notes, and residual risks.
