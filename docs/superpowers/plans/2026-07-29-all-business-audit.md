# 全业务自动化审查执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 对当前仓库的公共基础、登录/首页、商城浏览、商城订单、外卖、跑腿、充值和配送业务完成一次有证据、可复核、默认无副作用的全量审查。

**Architecture:** 审查采用“业务域报告 + 全仓汇总报告”两层结构。每个业务域独立核对入口、页面对象、业务顺序、安全授权、定位器、等待、异常、日志、测试数据和覆盖；最后统一运行非真机回归并形成跨域风险矩阵。审查阶段不修改生产行为，发现的代码问题进入后续独立修复计划。

**Tech Stack:** Python 3.11、pytest、Appium Python Client、Selenium、Android UiAutomator2、PowerShell、Git。

## Global Constraints

- 审查基线为分支 `codex/mall-readonly-decomposition` 当前提交；报告必须记录实际审查 SHA。
- 采用“历史证据继承 + 增量复审”：先核对历史报告对应 SHA 与当前差异；未变化代码继承已批准结论，变化文件及受影响调用链重新审查。
- 历史测试数字只作为背景，不代替当前最终树的一次全量非真机回归；业务域聚焦测试仅在该域发生变化、历史证据缺失或需复现发现时执行。
- 不执行真实加购、购物车删除、结算、下单、支付、地址新增/编辑/复制、订单取消、订单消息、验证码发送或其他持久化业务动作。
- 真机步骤必须先通过静态安全门禁审查；没有独立安全入口的业务域只记录“不可执行”，不得用坐标盲点代替。
- 登录审查不得触发短信/语音验证码，不得改变第三方 OAuth 授权状态，不得记录账号、密码、验证码、支付密码或 token。
- 每条缺陷必须给出文件与行号、业务影响、证据、严重级别和建议修复方向；证据不足时标记“待确认”，不得推断为已复现缺陷。
- 每个业务域分别区分：静态已审查、离线已验证、真机无副作用已验证、真实写入未验证。
- `logs/` 始终保持未跟踪，不提交截图、XML、运行日志或敏感运行数据。
- 生产代码变更不属于本计划；修复必须另建计划并执行 RED→GREEN、回归、独立复审。
- 全量非真机回归必须保持零失败；任何失败先停止汇总结论并定位原因。
- 当前风险基线：生产文件 69 个、固定等待 524 处、宽泛异常 735 处、超过 800 行文件 10 个。

---

### Task 1: 建立全业务覆盖矩阵与审查基线

**Files:**
- Create: `docs/reviews/2026-07-29-all-business-audit.md`
- Verify: `commons/**/*.py`
- Verify: `pages/**/*.py`
- Verify: `flows/**/*.py`
- Verify: `scripts/**/*.py`
- Verify: `testcases/test_*.py`
- Verify: `docs/reviews/*.md`

**Interfaces:**
- Consumes: 当前 Git SHA、生产文件清单、测试清单、历史审查报告。
- Produces: 业务域清单、入口映射、测试映射、历史证据与未验证范围矩阵。

- [ ] **Step 1: 记录审查基线**

Run:

```powershell
git rev-parse HEAD
git status --short
git log -10 --oneline
```

Record the exact SHA and confirm that `logs/` is the only expected untracked runtime directory.

- [ ] **Step 2: 生成业务文件与测试映射**

Run:

```powershell
Get-ChildItem commons,pages,flows,scripts -Recurse -File -Filter *.py
Get-ChildItem testcases -File -Filter 'test_*.py'
rg -n "class\s+\w+(Page|Flow|Mixin|Tester)|def\s+main\(" pages flows scripts -g '*.py'
```

Map every production entry to at least one business domain and every test file to the production area it covers.

- [ ] **Step 3: 复核全仓风险计数**

Count physical lines, `time.sleep(...)`, broad `except Exception`/bare `except`, and files over 800 physical lines across `commons/`, `pages/`, `flows/`, and `scripts/`.

Acceptance:

- the method is written in the report;
- empty `__init__.py` files do not cause counting errors;
- domain subtotals may overlap, but the global total must deduplicate files.

- [ ] **Step 4: 建立覆盖状态表**

For each domain record exactly one status for each layer:

```text
静态审查：未开始 / 完成
离线验证：未开始 / 通过 / 失败
真机无副作用：未执行 / 通过 / 失败 / 无安全入口
真实写入：未授权未执行 / 已授权已执行
```

Do not convert historical evidence into current-version compatibility without checking its commit boundary.

For every historical report, record:

```text
报告对应提交 / 当前是否有相关差异 / 结论可继承或必须复审 / 复审文件
```

---

### Task 2: 公共基础层、配置、Driver、等待与诊断审查

**Files:**
- Verify: `commons/android_runtime.py`
- Verify: `commons/config.py`
- Verify: `commons/diagnostics.py`
- Verify: `commons/driver.py`
- Verify: `commons/logger.py`
- Verify: `commons/waits.py`
- Test: `testcases/test_android_runtime.py`
- Test: `testcases/test_config.py`
- Test: `testcases/test_diagnostics.py`
- Test: `testcases/test_driver.py`
- Test: `testcases/test_logger.py`
- Test: `testcases/test_waits.py`

**Interfaces:**
- Consumes: environment variables, ADB/Appium boundaries, Driver session ownership.
- Produces: every business domain’s configuration, session lifecycle, wait behavior, sanitized evidence and logging guarantees.

- [ ] **Step 1: 审查配置优先级和敏感信息边界**

Verify typed parsing, explicit override order, missing-required-value behavior, and that log formatting never emits password/code/token values.

- [ ] **Step 2: 审查 Driver 生命周期**

Trace Driver creation, cache insertion, startup failure cleanup, owned/unowned session close behavior, and duplicate-session handling.

- [ ] **Step 3: 审查等待与诊断**

Verify explicit waits expose failure reasons, screenshot and XML capture are independent, XML is sanitized before disk write, and diagnostics do not convert Driver faults into success.

- [ ] **Step 4: 运行基础层离线测试**

Run:

```powershell
& 'C:\Users\18718\Desktop\appium_project\venv\Scripts\python.exe' -m pytest -q `
  testcases\test_android_runtime.py `
  testcases\test_config.py `
  testcases\test_diagnostics.py `
  testcases\test_driver.py `
  testcases\test_logger.py `
  testcases\test_waits.py
```

Record exact passed/failed counts.

---

### Task 3: 登录与首页业务审查

**Files:**
- Verify: `pages/Home.py`
- Verify: `pages/app_common.py`
- Verify: `pages/login_page.py`
- Verify: `pages/login/**/*.py`
- Verify: `scripts/main.py`
- Verify: `scripts/run_login.py`
- Verify: `scripts/password_login_standalone.py`
- Verify: `scripts/smoke_test.py`
- Test: `testcases/test_home.py`
- Test: `testcases/test_login.py`
- Test: `testcases/test_login_page_unit.py`
- Test: `testcases/test_main_cli.py`

**Interfaces:**
- Consumes: shared Driver/config/diagnostics.
- Produces: home entry, password login, OAuth login, SMS/voice flow, popup recovery and post-login navigation.

- [ ] **Step 1: 审查登录方式分发与 Driver 所有权**

Verify method allowlisting, missing/unknown method rejection before Driver creation, injected Driver ownership, and `all`/`quick` mode behavior.

- [ ] **Step 2: 审查密码、验证码和 OAuth 安全**

Trace account/password/code inputs from source to click/send boundary. Confirm no default credential, automatic payment password, code logging, or unintended multi-provider execution.

- [ ] **Step 3: 审查首页导航和恢复**

Review text/id/semantic locators before coordinates, state checks after navigation, popup handling, back behavior, and whether broad exceptions hide authentication or Driver failures.

- [ ] **Step 4: 运行登录/首页离线测试**

Run:

```powershell
& 'C:\Users\18718\Desktop\appium_project\venv\Scripts\python.exe' -m pytest -q `
  testcases\test_home.py `
  testcases\test_login.py `
  testcases\test_login_page_unit.py `
  testcases\test_main_cli.py
```

Do not run a real login method during this task.

---

### Task 4: 商城首页、搜索、分类和商品详情审查

**Files:**
- Verify: `pages/shop_home_page.py`
- Verify: `pages/shop_business_page.py`
- Verify: `pages/shop_business_search_mixin.py`
- Verify: `pages/shop_business_detail_mixin.py`
- Verify: `pages/shop_mall_*.py`
- Verify: `flows/shop_home_flow.py`
- Verify: `flows/shop_home_flow_types.py`
- Verify: `flows/shop_home_phases/*.py`
- Verify: `scripts/run_shop_home.py`
- Verify: `scripts/run_shop_business.py`
- Test: `testcases/test_shop_home_navigation.py`
- Test: `testcases/test_shop_business_decomposition.py`

**Interfaces:**
- Consumes: home state, semantic/structural navigation, product search results.
- Produces: read-only mall home browsing, filters, category navigation, search and product-detail snapshot.

- [ ] **Step 1: 审查页面职责和 MRO**

Verify facade compatibility, mixin order, parser re-export, moved method signatures, and that read-only methods do not call cart/order/address mutation helpers.

- [ ] **Step 2: 审查定位器、等待和回退**

Trace mall-tab direct, structural and recovery fallbacks. Confirm strict navigation disables every coordinate fallback while default flows preserve their documented compatibility.

- [ ] **Step 3: 运行商城浏览离线测试**

Run:

```powershell
& 'C:\Users\18718\Desktop\appium_project\venv\Scripts\python.exe' -m pytest -q `
  testcases\test_shop_home_navigation.py `
  testcases\test_shop_business_decomposition.py
```

- [ ] **Step 4: 核对保留的真机证据边界**

Inspect the retained screenshot, sanitized XML and log for commit `a63e281`. Record that later safety fixes were offline-only and do not claim device compatibility for excluded flows.

---

### Task 5: 商城购物车、地址、结算和订单边界审查

**Files:**
- Verify: `scripts/run_mall_order_flow.py`
- Verify: `pages/mall_order_cart_mixin.py`
- Verify: `pages/mall_order_address_mixin.py`
- Verify: `pages/mall_order_checkout_mixin.py`
- Verify: `flows/mall_order_http.py`
- Verify: `flows/mall_order_types.py`
- Test: `testcases/test_mall_order_*.py`

**Interfaces:**
- Consumes: product snapshot and explicit CLI capability flags.
- Produces: guarded cart, address, checkout, order creation, cancellation, order message and exception-flow entry points.

- [ ] **Step 1: 建立动作—能力矩阵**

For every mutating action verify:

```text
动作参数 + 独立 --allow-* capability + Driver 创建前校验
```

Cover cart mutation, address mutation, order creation, order cancellation and order message separately.

- [ ] **Step 2: 审查默认路径与冲突参数**

Verify navigation-only rejects all mutation capabilities, checkout without submit does not create an order, invalid combinations exit `2`, and no Driver is constructed before validation.

- [ ] **Step 3: 审查金额、库存、订单快照与 HTTP 边界**

Check parsing precision, tolerance, empty/malformed input, snapshot consistency, response validation, sensitive response logging and exception classification.

- [ ] **Step 4: 运行全部商城订单离线测试**

Run:

```powershell
$mallTests = Get-ChildItem testcases -Filter 'test_mall_order_*.py' |
  Select-Object -ExpandProperty FullName
& 'C:\Users\18718\Desktop\appium_project\venv\Scripts\python.exe' -m pytest -q $mallTests
```

No cart/order/address mutation is executed on a device.

---

### Task 6: 外卖导航、结算预览、支付和取消边界审查

**Files:**
- Verify: `pages/takeout_page.py`
- Verify: `pages/takeout_mixin.py`
- Verify: `pages/takeout_shop_mixin.py`
- Verify: `pages/takeout_checkout_mixin.py`
- Verify: `pages/takeout_delivery_time_mixin.py`
- Verify: `pages/takeout_cancel_order_mixin.py`
- Verify: `pages/takeout_locators.py`
- Verify: `scripts/run_takeout_wangwang.py`
- Test: `testcases/test_takeout_cli.py`
- Test: `testcases/test_takeout_checkout_boundary.py`

**Interfaces:**
- Consumes: shop navigation, checkout and payment-method selection.
- Produces: navigation-only flow, checkout preview, explicit order submission, manual password wait and cancellation boundary.

- [ ] **Step 1: 审查 CLI 安全组合**

Verify `--submit-order` requires `--checkout`, invalid combinations fail before Driver creation, and navigation-only does not add items or enter checkout.

- [ ] **Step 2: 审查支付密码与订单创建边界**

Confirm CLI and production code contain no fixed/default payment password, no automatic password keystrokes, and balance payment only waits for manual completion after explicit submission.

- [ ] **Step 3: 审查预览、配送时间和取消顺序**

Trace add-item, checkout preview, final confirmation, delivery-time selection, order-detail detection and cancellation. Mark every persistent action and its authorization gate.

- [ ] **Step 4: 运行外卖离线测试**

Run:

```powershell
& 'C:\Users\18718\Desktop\appium_project\venv\Scripts\python.exe' -m pytest -q `
  testcases\test_takeout_cli.py `
  testcases\test_takeout_checkout_boundary.py
```

Do not run `--checkout` on the device during this task because it may mutate the cart.

---

### Task 7: 跑腿、充值和配送辅助业务审查

**Files:**
- Verify: `pages/transfer_page.py`
- Verify: `scripts/run_transfer_business.py`
- Verify: `pages/charge_page.py`
- Verify: `pages/shipping_page.py`
- Test: `testcases/test_transfer_page.py`
- Test: `testcases/test_transfer_cli.py`
- Test: `testcases/test_charge_page.py`

**Interfaces:**
- Consumes: home navigation, form data, explicit submit controls and external account credentials.
- Produces: transfer form/submit/payment, charge form/create-order, shipping guide state.

- [ ] **Step 1: 审查跑腿默认非提交路径**

Verify default `submit_order=False`, required field validation, Maya/balance credential sources, payment selection, state assertions and error logging.

- [ ] **Step 2: 审查充值创建订单边界**

Verify `create_order(submit=False)` cannot click the create button, required fields fail before submission, duplicate saved accounts are handled, and no fixed personal account/test number exists in production.

- [ ] **Step 3: 审查配送辅助页面**

Determine whether `ShippingPage` is an active business entry or an orphan helper. Check its locator, wait, screenshot and exception behavior and map any caller.

- [ ] **Step 4: 运行跑腿与充值离线测试**

Run:

```powershell
& 'C:\Users\18718\Desktop\appium_project\venv\Scripts\python.exe' -m pytest -q `
  testcases\test_transfer_page.py `
  testcases\test_transfer_cli.py `
  testcases\test_charge_page.py
```

Record that charge currently has no independent safe CLI unless the review proves otherwise.

---

### Task 8: 跨业务安全、数据污染、日志和覆盖缺口审查

**Files:**
- Verify: all production and test Python files.
- Verify: `.env.example`
- Verify: `pytest.ini`
- Verify: `.gitignore`

**Interfaces:**
- Consumes: findings and evidence from Tasks 2–7.
- Produces: cross-domain security findings, duplicate patterns, orphan code, coverage gaps and remediation priority.

- [ ] **Step 1: 扫描敏感默认值和授权默认开启**

Search password/code/token/address/account assignments, long numeric literals, CLI defaults and `allow_* = True`. Classify each hit by production/test/documentation context.

- [ ] **Step 2: 审查日志与诊断数据**

Verify exception logging does not expose raw user data, screenshots/XML are sanitized where required, and test fixtures do not leak into production defaults.

- [ ] **Step 3: 审查重复实现与孤儿入口**

Identify duplicate Driver lifecycle, duplicate navigation helpers, unreferenced scripts/pages, stale compatibility wrappers and methods with no production caller or test.

- [ ] **Step 4: 审查覆盖缺口**

For every public business action map:

```text
主路径测试 / 失败路径测试 / 参数冲突测试 / 安全边界测试 / 真机证据
```

Missing coverage is a finding; it is not proof that production behavior is broken.

---

### Task 9: 全量离线回归、编译与安全真机资格门

**Files:**
- Verify: entire repository Python test suite.
- Modify: `docs/reviews/2026-07-29-all-business-audit.md`

**Interfaces:**
- Consumes: all domain findings and test selections.
- Produces: final fresh regression evidence and a per-domain safe-device eligibility decision.

- [ ] **Step 1: 运行全量非真机测试**

Run:

```powershell
& 'C:\Users\18718\Desktop\appium_project\venv\Scripts\python.exe' `
  -m pytest -m 'not device' -q
```

Acceptance: zero failures; record exact passed/deselected counts.

- [ ] **Step 2: 编译全部 Python 文件**

Run:

```powershell
& 'C:\Users\18718\Desktop\appium_project\venv\Scripts\python.exe' -c `
  "from pathlib import Path; files=sorted(p for p in Path('.').rglob('*.py') if '__pycache__' not in p.parts); [compile(p.read_text(encoding='utf-8-sig'), str(p), 'exec') for p in files]; print(f'compiled={len(files)}')"
```

- [ ] **Step 3: 判定真机资格**

For each domain choose one:

```text
可执行无副作用真机验证
已有当前版本证据，无需重复
无独立安全入口，禁止执行
静态审查发现门禁缺口，禁止执行
需要用户对持久化动作单独授权
```

- [ ] **Step 4: 仅执行通过资格门的无副作用命令**

Before each command, record exact CLI, expected clicks/state transitions, forbidden actions, timeout, device/app version and rollback behavior. Stop immediately if the initial page state is unexpected or a coordinate fallback could overlap a mutation control.

---

### Task 10: 汇总全业务审查结论

**Files:**
- Modify: `docs/reviews/2026-07-29-all-business-audit.md`

**Interfaces:**
- Consumes: Tasks 1–9 findings and evidence.
- Produces: repository-wide QA sign-off status and prioritized follow-up plans.

- [ ] **Step 1: 编写业务域结论表**

Include foundation, login/home, shop read-only, mall order, takeout, transfer, charge and shipping with static/offline/device/write-flow status.

- [ ] **Step 2: 编写缺陷清单**

Classify:

```text
P0/Critical：凭据泄露、默认真实支付/下单、不可逆数据风险
P1/Important：安全门禁旁路、失败被报告为成功、主流程错误
P2/Moderate：定位/等待/异常导致明显不稳定或不可诊断
P3/Minor：结构、命名、报告与非阻塞覆盖问题
```

- [ ] **Step 3: 形成后续治理批次**

Group fixes by business domain and dependency. Do not mix unrelated domains or mechanical bulk replacements in one batch.

- [ ] **Step 4: 终审报告事实一致性**

Check every test count, commit SHA, device evidence boundary, screenshot/XML/log path and “未验证” statement against retained evidence. Run:

```powershell
git diff --check
git status --short
```

Expected: report is the only planned review artifact; `logs/` remains untracked.
