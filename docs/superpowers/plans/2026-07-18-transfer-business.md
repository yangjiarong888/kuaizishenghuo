# 同城跑腿业务自动化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增可从首页金刚区进入、覆盖菜单检查、完整下单、Maya 返回、余额支付和订单状态断言的同城跑腿自动化。

**Architecture:** `TransferPage` 负责 Appium 页面行为和跨页断言，命令行脚本负责参数、安全开关和会话生命周期，`Home.py` 只负责金刚区业务分发。真实提交和敏感凭据均在页面对象边界前校验，默认执行路径不创建订单。

**Tech Stack:** Python 3.11、Appium Python Client 5.2.7、Selenium 4.41.0、pytest 8.3.5、Android UiAutomator2

## Global Constraints

- 页面对象必须命名为 `pages/transfer_page.py`，类名必须为 `TransferPage`。
- 独立入口必须命名为 `scripts/run_transfer_business.py`。
- 首页真实入口文本为“同城跑腿”，目标 Activity 为 `RunnerHomeActivity`。
- 默认不得点击订单“提交”；只有 `submit_order=True` 才允许创建真实订单。
- Maya 账号、Maya 密码、余额支付密码只能从环境变量读取，禁止写入源码、配置、测试数据或日志。
- 找不到已有地址、可用送达时间或支付密码时必须失败，禁止自动新增或删除地址。
- 支付成功以订单详情状态不再是“待付款”为准。
- 当前环境没有 `git` 可执行程序；每个提交步骤记录预期命令，但本环境实施时不得伪称已提交。

---

### Task 1: TransferPage 基础定位与页面断言

**Files:**
- Create: `pages/transfer_page.py`
- Create: `testcases/test_transfer_page.py`

**Interfaces:**
- Consumes: Appium `WebDriver` 实例。
- Produces: `TransferPage(driver)`, `wait_for_runner_home(timeout: float = 10.0) -> bool`, `enter_from_home() -> bool`, `tap_back() -> bool`, `page_contains(text: str) -> bool`。

- [ ] **Step 1: 写失败测试**

```python
class FakeElement:
    def __init__(self, driver, *, text="", element_id=""):
        self.driver = driver
        self.text = text
        self.element_id = element_id

    def click(self):
        if self.text:
            self.driver.clicked_texts.append(self.text)
        if self.element_id:
            self.driver.clicked_ids.append(self.element_id)


class FakeDriver:
    def __init__(self):
        self.visible_ids = set()
        self.clicked_ids = []
        self.clicked_texts = []

    def find_elements(self, by, value):
        if value == '//*[@text="同城跑腿"]':
            return [FakeElement(self, text="同城跑腿")]
        if value in self.visible_ids:
            return [FakeElement(self, element_id=value)]
        return []


@pytest.fixture
def fake_driver():
    driver = FakeDriver()
    driver.visible_ids.add("com.bs.feifubao:id/tv_menu_service_info")
    return driver


from pages.transfer_page import TransferPage


def test_enter_from_home_clicks_exact_runner_label(fake_driver):
    page = TransferPage(fake_driver)
    assert page.enter_from_home() is True
    assert fake_driver.clicked_texts == ["同城跑腿"]


def test_wait_for_runner_home_requires_menu_marker(fake_driver):
    fake_driver.visible_ids.add("com.bs.feifubao:id/tv_menu_service_info")
    assert TransferPage(fake_driver).wait_for_runner_home(timeout=0.01) is True
```

- [ ] **Step 2: 运行测试并确认因模块缺失失败**

Run: `python -m pytest testcases/test_transfer_page.py -q`

Expected: FAIL，错误包含 `ModuleNotFoundError: No module named 'pages.transfer_page'`。

- [ ] **Step 3: 添加最小页面对象骨架**

```python
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait

PKG = "com.bs.feifubao"


class TransferPage:
    SERVICE_INFO_ID = f"{PKG}:id/tv_menu_service_info"

    def __init__(self, driver):
        self.driver = driver

    def _elements(self, by, value):
        try:
            return self.driver.find_elements(by, value)
        except Exception:
            return []

    def page_contains(self, text: str) -> bool:
        return bool(self._elements(AppiumBy.XPATH, f'//*[@text="{text}" or @content-desc="{text}"]'))

    def wait_for_runner_home(self, timeout: float = 10.0) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.find_elements(AppiumBy.ID, self.SERVICE_INFO_ID)
            )
            return True
        except Exception:
            return False

    def enter_from_home(self) -> bool:
        matches = self._elements(AppiumBy.XPATH, '//*[@text="同城跑腿"]')
        if not matches:
            return False
        matches[0].click()
        return self.wait_for_runner_home()

    def tap_back(self) -> bool:
        matches = self._elements(AppiumBy.ID, f"{PKG}:id/ll_back")
        if matches:
            matches[0].click()
        else:
            self.driver.back()
        return True
```

- [ ] **Step 4: 运行测试并确认通过**

Run: `python -m pytest testcases/test_transfer_page.py -q`

Expected: PASS。

- [ ] **Step 5: 记录提交**

```powershell
git add pages/transfer_page.py testcases/test_transfer_page.py
git commit -m "feat: add transfer page foundation"
```

本环境若仍无 `git`，记录“未提交：git 不可用”，继续保留工作区修改。

---

### Task 2: 顶部菜单与取收货表单流程

**Files:**
- Modify: `pages/transfer_page.py`
- Modify: `testcases/test_transfer_page.py`

**Interfaces:**
- Consumes: Task 1 的 `TransferPage`。
- Produces: `verify_menu_round_trips() -> bool`, `select_saved_address(trigger_id: str, expected_ids: tuple[str, ...]) -> bool`, `fill_pickup_from_saved_address() -> bool`, `fill_receive_from_saved_address() -> bool`, `select_first_delivery_time() -> bool`, `advance_to_checkout() -> bool`。

- [ ] **Step 1: 写菜单往返失败测试**

```python
def test_menu_round_trips_use_verified_ids(fake_driver):
    page = TransferPage(fake_driver)
    assert page.verify_menu_round_trips() is True
    assert fake_driver.clicked_ids[:3] == [
        "com.bs.feifubao:id/tv_menu_service_info",
        "com.bs.feifubao:id/ll_back",
        "com.bs.feifubao:id/tv_menu_address_manage",
    ]
```

- [ ] **Step 2: 运行单测并确认缺少方法**

Run: `python -m pytest testcases/test_transfer_page.py::test_menu_round_trips_use_verified_ids -q`

Expected: FAIL，错误包含 `AttributeError: 'TransferPage' object has no attribute 'verify_menu_round_trips'`。

- [ ] **Step 3: 实现三个菜单的进入、断言与返回**

```python
MENU_CASES = (
    ("tv_menu_service_info", ("同城跑腿服务说明",), "RunnerServiceInfoActivity"),
    ("tv_menu_address_manage", ("地址管理",), "FlutterBoostActivity"),
    ("tv_menu_order", ("跑腿订单",), "RunnerOrderActivity"),
)

def verify_menu_round_trips(self) -> bool:
    for suffix, markers, activity in self.MENU_CASES:
        if not self._click_id(suffix):
            return False
        if not self._wait_page(markers=markers, activity_contains=activity):
            return False
        self.tap_back()
        if not self.wait_for_runner_home():
            return False
    return True
```

- [ ] **Step 4: 写地址回填和时间选择失败测试**

```python
def test_order_form_selects_saved_pickup_receive_and_time(fake_driver):
    page = TransferPage(fake_driver)
    assert page.fill_pickup_from_saved_address() is True
    assert page.fill_receive_from_saved_address() is True
    assert page.select_first_delivery_time() is True
    assert "com.bs.feifubao:id/tv_select_get_address" in fake_driver.clicked_ids
    assert "com.bs.feifubao:id/tv_select_receive_address" in fake_driver.clicked_ids
    assert "com.bs.feifubao:id/item_canju_tv" in fake_driver.clicked_ids
```

- [ ] **Step 5: 运行测试并确认缺少表单方法**

Run: `python -m pytest testcases/test_transfer_page.py::test_order_form_selects_saved_pickup_receive_and_time -q`

Expected: FAIL，错误包含 `AttributeError`。

- [ ] **Step 6: 实现地址选择、回填断言和时间选择**

```python
PICKUP_FIELDS = ("et_get_user", "tv_get_address", "et_get_address_detail", "et_get_phone")
RECEIVE_FIELDS = (
    "et_receive_user",
    "tv_receive_address",
    "et_receive_address_detail",
    "et_receive_phone",
)

def select_saved_address(self, trigger_id: str, expected_ids: tuple[str, ...]) -> bool:
    if not self._click_id(trigger_id):
        return False
    addresses = self._elements(AppiumBy.ID, f"{PKG}:id/tv_address")
    if not addresses:
        return False
    addresses[0].click()
    return all(self._element_has_value(suffix) for suffix in expected_ids)

def select_first_delivery_time(self) -> bool:
    if not self._click_id("tv_receive_time"):
        return False
    slots = self._elements(AppiumBy.ID, f"{PKG}:id/item_canju_tv")
    if not slots:
        return False
    slots[0].click()
    return self._element_has_value("tv_receive_time", reject=("请选择收货时间",))
```

- [ ] **Step 7: 运行页面对象测试**

Run: `python -m pytest testcases/test_transfer_page.py -q`

Expected: PASS。

- [ ] **Step 8: 记录提交**

```powershell
git add pages/transfer_page.py testcases/test_transfer_page.py
git commit -m "feat: automate transfer menus and address forms"
```

---

### Task 3: 真实提交、Maya 返回与余额支付

**Files:**
- Modify: `pages/transfer_page.py`
- Modify: `testcases/test_transfer_page.py`

**Interfaces:**
- Consumes: Task 2 的表单流程。
- Produces: `submit_order(submit_order: bool) -> bool`, `exercise_maya_and_return(account: str, password: str) -> bool`, `pay_with_balance(pay_password: str) -> bool`, `assert_paid_order_detail() -> bool`, `run_order_flow(*, submit_order: bool, payment_method: str, exercise_maya_return: bool, maya_account: str | None, maya_password: str | None, pay_password: str | None) -> bool`。

- [ ] **Step 1: 写真实提交安全开关失败测试**

```python
def test_submit_order_is_noop_without_explicit_permission(fake_driver):
    page = TransferPage(fake_driver)
    assert page.submit_order(submit_order=False) is True
    assert "com.bs.feifubao:id/settlement" not in fake_driver.clicked_ids
```

- [ ] **Step 2: 运行测试并确认缺少方法**

Run: `python -m pytest testcases/test_transfer_page.py::test_submit_order_is_noop_without_explicit_permission -q`

Expected: FAIL，错误包含 `AttributeError`。

- [ ] **Step 3: 实现提交开关与支付页断言**

```python
def submit_order(self, submit_order: bool) -> bool:
    if not self._elements(AppiumBy.ID, f"{PKG}:id/settlement"):
        return False
    if not submit_order:
        return True
    if not self._click_id("settlement"):
        return False
    return self._wait_page(markers=("在线支付",), activity_contains="PayActivity")
```

- [ ] **Step 4: 写余额支付密码保护失败测试**

```python
import pytest


def test_balance_payment_rejects_missing_password(fake_driver):
    with pytest.raises(ValueError, match="TRANSFER_PAY_PASSWORD"):
        TransferPage(fake_driver).pay_with_balance("")
```

- [ ] **Step 5: 运行测试并确认缺少支付方法**

Run: `python -m pytest testcases/test_transfer_page.py::test_balance_payment_rejects_missing_password -q`

Expected: FAIL，错误包含 `AttributeError`。

- [ ] **Step 6: 实现 Maya 返回、余额支付和订单详情断言**

```python
def _select_payment_type(self, label: str) -> bool:
    types = self._elements(AppiumBy.ID, f"{PKG}:id/tv_type")
    match = next((element for element in types if element.text == label), None)
    if match is None:
        return False
    match.click()
    return True

def pay_with_balance(self, pay_password: str) -> bool:
    if not pay_password:
        raise ValueError("缺少 TRANSFER_PAY_PASSWORD")
    if not self._select_payment_type("余额") or not self._click_id("btn_pay"):
        return False
    inputs = self._elements(AppiumBy.CLASS_NAME, "android.widget.EditText")
    if not inputs:
        return False
    inputs[0].send_keys(pay_password)
    if not self._click_id("btn_comfirm"):
        return False
    return self.assert_paid_order_detail()

def exercise_maya_and_return(self, account: str, password: str) -> bool:
    if not account or not password:
        raise ValueError("缺少 TRANSFER_MAYA_ACCOUNT 或 TRANSFER_MAYA_PASSWORD")
    if not self._select_payment_type("Maya支付") or not self._click_id("btn_pay"):
        return False
    if not self._wait_page(markers=("Login | Maya",), activity_contains="WebViewActivity"):
        return False
    inputs = self._elements(AppiumBy.CLASS_NAME, "android.widget.EditText")
    if len(inputs) < 2:
        return False
    inputs[0].send_keys(account)
    inputs[1].send_keys(password)
    login_buttons = self._elements(AppiumBy.ID, "btnLogin")
    if not login_buttons:
        return False
    login_buttons[0].click()
    for _ in range(3):
        if "PayActivity" in (self.driver.current_activity or ""):
            return True
        self.driver.back()
    return "PayActivity" in (self.driver.current_activity or "")

def assert_paid_order_detail(self) -> bool:
    if not self._wait_page(markers=("订单详情",), activity_contains="RunnerOrderDetailActivity"):
        return False
    statuses = ("待接单", "待取货", "配送中", "已完成")
    return any(self.page_contains(status) for status in statuses) and not self.page_contains("待付款")
```

该方法不得记录账号或密码。

- [ ] **Step 7: 运行支付相关测试**

Run: `python -m pytest testcases/test_transfer_page.py -q`

Expected: PASS，且测试输出不包含任何凭据值。

- [ ] **Step 8: 记录提交**

```powershell
git add pages/transfer_page.py testcases/test_transfer_page.py
git commit -m "feat: add guarded transfer order payment"
```

---

### Task 4: 命令行入口与首页金刚区接入

**Files:**
- Create: `scripts/run_transfer_business.py`
- Modify: `pages/Home.py:18-20`
- Modify: `pages/Home.py:66-74`
- Modify: `pages/Home.py:679-687`
- Create: `testcases/test_transfer_cli.py`

**Interfaces:**
- Consumes: `TransferPage` 的菜单与完整订单接口、`DriverManager.get_driver(session_name=...)`。
- Produces: `build_parser() -> argparse.ArgumentParser`, `main() -> int`；首页 `GOLDEN_BUSINESS_MAP` 增加 `"同城跑腿": "transfer"` 和 `"跑腿": "transfer"`。

- [ ] **Step 1: 写 CLI 默认安全行为失败测试**

```python
from scripts.run_transfer_business import build_parser


def test_cli_defaults_do_not_submit_real_order():
    args = build_parser().parse_args([])
    assert args.action == "full"
    assert args.submit_order is False
    assert args.payment_method == "balance"
```

- [ ] **Step 2: 运行测试并确认脚本缺失**

Run: `python -m pytest testcases/test_transfer_cli.py -q`

Expected: FAIL，错误包含 `ModuleNotFoundError: No module named 'scripts.run_transfer_business'`。

- [ ] **Step 3: 实现 CLI 参数与敏感环境变量读取**

```python
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="同城跑腿业务自动化")
    parser.add_argument("--action", choices=("menus", "order", "full"), default="full")
    parser.add_argument("--submit-order", action="store_true")
    parser.add_argument("--payment-method", choices=("balance", "maya"), default="balance")
    parser.add_argument("--exercise-maya-return", action="store_true")
    parser.add_argument("--session", default="transfer_business")
    parser.add_argument("--quit-driver", action="store_true")
    return parser

def read_secrets() -> dict[str, str | None]:
    return {
        "maya_account": os.environ.get("TRANSFER_MAYA_ACCOUNT"),
        "maya_password": os.environ.get("TRANSFER_MAYA_PASSWORD"),
        "pay_password": os.environ.get("TRANSFER_PAY_PASSWORD"),
    }
```

`main()` 根据 action 调用 `verify_menu_round_trips` 或 `run_order_flow`，成功返回 `0`，失败返回 `1`；日志只记录参数布尔状态，不记录 `read_secrets()` 的值。

- [ ] **Step 4: 写首页映射失败测试**

```python
from pages.Home import ChopsticksTester


def test_home_maps_runner_to_transfer_business():
    assert ChopsticksTester.GOLDEN_BUSINESS_MAP["同城跑腿"] == "transfer"
```

- [ ] **Step 5: 运行测试并确认映射缺失**

Run: `python -m pytest testcases/test_transfer_cli.py::test_home_maps_runner_to_transfer_business -q`

Expected: FAIL，错误包含 `KeyError: '同城跑腿'`。

- [ ] **Step 6: 接入 Home.py**

```python
from .transfer_page import TransferPage

GOLDEN_BUSINESS_MAP = {
    "外卖": "takeout",
    "美食外卖": "takeout",
    "海运": "shipping",
    "海运物流": "shipping",
    "同城跑腿": "transfer",
    "跑腿": "transfer",
}

# test_golden_zone_enhanced 分发分支
elif biz_type == "transfer":
    logger.info("入口 '%s' 绑定业务：同城跑腿安全菜单检查", item_name)
    TransferPage(self.driver).verify_menu_round_trips()
```

- [ ] **Step 7: 运行 CLI 与首页接入测试**

Run: `python -m pytest testcases/test_transfer_cli.py -q`

Expected: PASS。

- [ ] **Step 8: 记录提交**

```powershell
git add scripts/run_transfer_business.py pages/Home.py testcases/test_transfer_cli.py
git commit -m "feat: expose transfer business runner"
```

---

### Task 5: 静态验证、单测与真机回归

**Files:**
- Verify: `pages/transfer_page.py`
- Verify: `scripts/run_transfer_business.py`
- Verify: `pages/Home.py`
- Verify: `testcases/test_transfer_page.py`
- Verify: `testcases/test_transfer_cli.py`

**Interfaces:**
- Consumes: Tasks 1-4 的完整实现。
- Produces: 可复现的无副作用回归结果，以及显式授权真实支付的订单状态证据。

- [ ] **Step 1: 编译检查**

Run: `python -m py_compile pages/transfer_page.py scripts/run_transfer_business.py pages/Home.py testcases/test_transfer_page.py testcases/test_transfer_cli.py`

Expected: exit code `0`，无输出。

- [ ] **Step 2: 运行新增单元测试**

Run: `python -m pytest testcases/test_transfer_page.py testcases/test_transfer_cli.py -q`

Expected: 全部 PASS，无 warning 和凭据输出。

- [ ] **Step 3: 运行现有测试回归**

Run: `python -m pytest testcases -q`

Expected: 全部 PASS；若环境性真机用例缺少前置条件，记录具体用例和原因，不修改断言掩盖失败。

- [ ] **Step 4: 真机执行无副作用菜单回归**

Run: `python scripts/run_transfer_business.py --action menus --session transfer_menus --quit-driver`

Expected: 服务说明、地址管理、我的订单均进入成功并返回跑腿首页，进程返回 `0`。

- [ ] **Step 5: 真机执行到提交前**

Run: `python scripts/run_transfer_business.py --action order --session transfer_checkout --quit-driver`

Expected: 完成取货、收货和时间选择，停在含“提交”的确认页，不创建新订单，进程返回 `0`。

- [ ] **Step 6: 在用户再次明确授权时执行真实支付**

```powershell
$securePayPassword = Read-Host '输入本次支付密码' -AsSecureString
$secretPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePayPassword)
$env:TRANSFER_PAY_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($secretPointer)
python scripts/run_transfer_business.py --action full --submit-order --payment-method balance --session transfer_real --quit-driver
Remove-Item Env:TRANSFER_PAY_PASSWORD
[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($secretPointer)
```

Expected: 进入订单详情，状态为“待接单”或后续有效状态，不再显示“待付款”。环境变量在命令结束后移除，日志中不出现密码。

- [ ] **Step 7: 最终差异检查**

Run: `rg -n 'TRANSFER_(MAYA_ACCOUNT|MAYA_PASSWORD|PAY_PASSWORD)\s*=\s*["''][^"'']+["'']|send_keys\(["''][0-9A-Za-z]{6,}["'']\)' pages scripts testcases docs`

Expected: 无匹配；设计和计划文档也不得包含用户真实凭据。

- [ ] **Step 8: 记录最终提交**

```powershell
git add pages/transfer_page.py scripts/run_transfer_business.py pages/Home.py testcases/test_transfer_page.py testcases/test_transfer_cli.py docs/superpowers
git commit -m "test: verify transfer business flow"
```

本环境若仍无 `git`，在交付说明中明确“未提交：git 不可用”。
