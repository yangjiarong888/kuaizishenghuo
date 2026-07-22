# ChargePage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增覆盖充值、生活缴费、账号管理和缴费记录的 `ChargePage`，并以 FakeDriver pytest 验证其业务行为与防误提交约束。

**Architecture:** 使用单一 `ChargePage` Page Object，对外提供按业务动作命名的方法；内部集中处理文本/ID 组合定位、点击、输入、属性读取和显式等待。供应商字段与图片限制通过常量配置驱动，测试使用 FakeDriver 模拟 Appium 元素交互，不依赖设备。

**Tech Stack:** Python 3、Appium-Python-Client 5.2.7、Selenium 4.41.0、pytest 8.3.5

## Global Constraints

- 仅新增 `pages/charge_page.py`、`testcases/test_charge_page.py` 和本计划文档，不修改现有业务页面对象。
- 默认不得点击“立即充值”或“创建订单”；只有显式 `submit=True` 才允许提交。
- 手机号使用 `+63` 默认区号，并在输入前移除空格。
- 电费、水费图片选填且最多一张；网费不上传图片；拍照缴费图片必填且最多两张。
- 不使用固定 `sleep`，不在日志或异常中输出手机号、账号及图片路径。
- 需求图没有真实页面 XML，资源 ID 采用集中常量并提供文案兜底；单元测试不宣称验证真实设备定位。

---

### Task 1: ChargePage 行为契约测试

**Files:**
- Create: `testcases/test_charge_page.py`
- Test: `testcases/test_charge_page.py`

**Interfaces:**
- Consumes: Appium `find_elements(by, value)` 风格驱动接口。
- Produces: `FakeDriver`、`FakeElement` 以及 `ChargePage` 首页、充值、生活缴费、安全提交、账号和记录管理行为测试。

- [ ] **Step 1: 编写失败测试**

创建 FakeDriver 状态模型，并编写以下独立断言：

```python
def test_set_phone_number_normalizes_spaces_and_keeps_country_code(driver):
    page = ChargePage(driver)
    assert page.set_phone_number("0992 052 8426") is True
    assert driver.values[ChargePage.PHONE_INPUT_ID] == "09920528426"

def test_create_order_does_not_click_without_explicit_submit(driver):
    page = ChargePage(driver)
    page.payment_kind = "electricity"
    page.selected_provider = "Meralco"
    page.filled_fields = {"账号": "1234567890", "缴纳金额": "100"}
    page.photo_count = 1
    assert page.create_order(submit=False) is True
    assert ChargePage.CREATE_ORDER_ID not in driver.clicked
```

其余测试分别覆盖入口、类型、套餐、优惠券、供应商、字段、图片限制、保存账号、账号管理和缴费记录。

- [ ] **Step 2: 运行测试并确认 RED**

Run: `python -m pytest testcases/test_charge_page.py -q`

Expected: collection 阶段失败，错误包含 `ModuleNotFoundError: No module named 'pages.charge_page'`。

---

### Task 2: ChargePage 基础交互与充值首页

**Files:**
- Create: `pages/charge_page.py`
- Test: `testcases/test_charge_page.py`

**Interfaces:**
- Consumes: driver 的 `find_elements`、元素的 `click/clear/send_keys/get_attribute/is_enabled`。
- Produces: `ChargePage(driver, wait_sec=10.0)`、`wait_for_charge_home()`、`enter_from_home()`、`set_phone_number(number)`、`switch_recharge_type(kind)`、`select_recharge_package(label)`、`select_coupon(label=None)`、`open_bottom_entry(label)`。

- [ ] **Step 1: 实现最小基础层**

实现 `_elements`、`_first`、`_click`、`_input`、`page_contains` 和 `wait_for_charge_home`；异常统一转换为 `False` 或空列表，参数错误保留 `ValueError`。

- [ ] **Step 2: 实现充值动作**

按 `话费/流量` 白名单切换；手机号仅接受 10–11 位数字；套餐按完整文案选择；优惠券只选择启用元素；底部入口限制为需求图中的四项。

- [ ] **Step 3: 运行相关测试并确认 GREEN**

Run: `python -m pytest testcases/test_charge_page.py -q -k "home or phone or recharge or coupon or bottom"`

Expected: selected tests PASS。

---

### Task 3: 生活缴费表单与安全提交

**Files:**
- Modify: `pages/charge_page.py`
- Test: `testcases/test_charge_page.py`

**Interfaces:**
- Consumes: Task 2 基础查找、点击和输入能力。
- Produces: `enter_life_payment(kind)`、`select_provider(name)`、`fill_billing_fields(values)`、`add_bill_photos(paths, limit=None)`、`set_save_account(enabled)`、`create_order(submit=False)`。

- [ ] **Step 1: 增加缴费类型和供应商配置**

定义四种缴费类型、支持供应商、动态必填字段与默认图片上限；拒绝不支持的业务类型、供应商和字段。

- [ ] **Step 2: 实现表单状态与交互**

操作成功后仅记录非敏感的完成状态：当前业务类型、供应商、已填写字段名、图片数量和保存账号开关，不保存图片路径到日志。

- [ ] **Step 3: 实现提交前校验**

`create_order` 检查业务类型、供应商、必填字段和图片；`submit=False` 只校验不点击；`submit=True` 点击创建订单。

- [ ] **Step 4: 运行相关测试并确认 GREEN**

Run: `python -m pytest testcases/test_charge_page.py -q -k "life or provider or billing or photo or save or order"`

Expected: selected tests PASS。

---

### Task 4: 账号管理与缴费记录

**Files:**
- Modify: `pages/charge_page.py`
- Test: `testcases/test_charge_page.py`

**Interfaces:**
- Consumes: Task 2 通用点击能力。
- Produces: `manage_saved_account(action, account_label)`、`verify_saved_account_order()`、`edit_saved_account(account_label, values)`、`switch_payment_record_type(kind)`、`manage_payment_records(action, record_label=None)`。

- [ ] **Step 1: 实现账号管理动作**

支持 `copy/edit/delete`，先定位账号卡片，再点击卡片内对应动作；不支持动作抛出 `ValueError`。

- [ ] **Step 2: 实现缴费记录动作**

支持五类记录切换和 `open/select/select_all/delete`；`select/delete` 必须提供记录标签，`delete` 必须先进入管理模式并选择记录。

- [ ] **Step 3: 运行相关测试并确认 GREEN**

Run: `python -m pytest testcases/test_charge_page.py -q -k "account or record"`

Expected: selected tests PASS。

---

### Task 5: 回归验证与交付检查

**Files:**
- Modify: `pages/charge_page.py`（仅在验证发现问题时）
- Modify: `testcases/test_charge_page.py`（仅在测试契约本身错误时）

**Interfaces:**
- Consumes: Tasks 1–4 的全部实现。
- Produces: 新增测试结果、全量回归结果和语法编译结果。

- [ ] **Step 1: 运行新增测试**

Run: `python -m pytest testcases/test_charge_page.py -q`

Expected: 全部 PASS，无 warning 和 error。

- [ ] **Step 2: 运行全量回归**

Run: `python -m pytest testcases -q`

Expected: 全部 PASS；若现有环境相关用例失败，逐条区分新增回归和原有外部依赖失败。

- [ ] **Step 3: 编译检查**

Run: `python -m py_compile pages/charge_page.py testcases/test_charge_page.py`

Expected: exit code 0，无输出。

- [ ] **Step 4: 检查防误提交与敏感信息**

Run: `rg -n "sleep\(|logger\..*(phone|account|path)|create_order\(submit=True\)" pages/charge_page.py testcases/test_charge_page.py`

Expected: 生产代码无固定 sleep、无敏感值日志；`submit=True` 只出现在明确测试中。

- [ ] **Step 5: 提交（环境允许时）**

```bash
git add pages/charge_page.py testcases/test_charge_page.py docs/superpowers/specs/2026-07-22-charge-page-design.md docs/superpowers/plans/2026-07-22-charge-page.md
git commit -m "feat: add charge payment page object"
```

当前环境若仍无 `git` 可执行程序，则跳过提交并在交付说明中明确记录。
