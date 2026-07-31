# 全业务自动化审查：基线、清单与证据矩阵

日期：2026-07-29
范围：`commons/`、`pages/`、`flows/`、`scripts/` 中的生产 Python 文件，以及 `testcases/test_*.py`。这是全量审查的**清单和证据骨架**；不包含任何业务域的静态审查结论或缺陷结论。

## 1. 当前审查基线

| 字段 | 值 |
| --- | --- |
| 分支 | `codex/mall-readonly-decomposition` |
| 审查 SHA | `f4e37d8c6753729522ed2771095f859caf83b494` |
| 审查时工作区状态 | `?? logs/` |
| 运行时未跟踪目录 | `logs/` 是唯一预期的未跟踪运行时目录；不加入提交。 |
| 本报告的审查状态 | 基线与清单已建立；各域静态审查均尚未开始。 |

审查时最近十个提交：

```text
f4e37d8 docs: make business audit incremental
bed2de1 docs: plan all-business audit
a831d75 docs: finalize mall decomposition verification
4224d71 fix: preserve guarded mall recovery fallback
e88173b fix: close navigation-only safety gaps
46c5df3 docs: verify mall read-only decomposition
a63e281 fix: guard mall structural fallback
3832619 fix: fail closed in mall navigation verification
0d999ac refactor: extract mall business detail
26eab9a refactor: extract mall business search
```

## 2. 去重生产清单（69 个文件）

每个生产文件在本表只出现一次，并分配一个主要业务域；调用关系可能使其同时服务其他域，不能把本表的域小计相加为全局总数。

| 主要域 | 生产文件 | 主要职责/入口 |
| --- | --- | --- |
| 公共基础 | `commons/android_runtime.py`, `commons/base_page.py`, `commons/config.py`, `commons/diagnostics.py`, `commons/driver.py`, `commons/logger.py`, `commons/waits.py`, `commons/__init__.py` | 设备/Activity、页面基类、配置、诊断、Driver 生命周期、日志、等待与包入口。 |
| 登录与首页 | `pages/Home.py`, `pages/app_common.py`, `pages/login_page.py`, `pages/login/constants.py`, `pages/login/data.py`, `pages/login/env.py`, `pages/login/login_page.py`, `pages/login/__init__.py`, `pages/login/mixins/find_click_mixin.py`, `pages/login/mixins/navigation_postlogin_mixin.py`, `pages/login/mixins/oauth_mixin.py`, `pages/login/mixins/password_mixin.py`, `pages/login/mixins/semantics_mixin.py`, `pages/login/mixins/sms_voice_mixin.py`, `pages/login/mixins/state_popup_mixin.py`, `pages/login/mixins/__init__.py`, `scripts/main.py`, `scripts/password_login_standalone.py`, `scripts/run_login.py`, `scripts/smoke_test.py` | 首页入口、登录分发/方法、OAuth、密码、短信/语音、弹窗恢复与旧式冒烟入口。 |
| 商城只读浏览 | `pages/shop_home_page.py`, `pages/shop_business_page.py`, `pages/shop_business_search_mixin.py`, `pages/shop_business_detail_mixin.py`, `pages/shop_locators.py`, `pages/shop_mall_cart_badge.py`, `pages/shop_mall_category_page.py`, `pages/shop_mall_context.py`, `pages/shop_mall_home_chrome.py`, `pages/shop_mall_product_detail_page.py`, `pages/shop_mall_spec_sheet.py`, `flows/shop_home_flow.py`, `flows/shop_home_flow_types.py`, `flows/shop_home_phases/detail_cart_banner.py`, `flows/shop_home_phases/home_add_cart_badge.py`, `flows/shop_home_phases/home_list_filters.py`, `flows/shop_home_phases/kingkong_daily_baihuo.py`, `flows/shop_home_phases/__init__.py`, `flows/__init__.py`, `scripts/run_shop_home.py`, `scripts/run_shop_business.py` | 商城首页、分类/搜索、商品详情、只读导航流程与 CLI。 |
| 商城订单边界 | `pages/mall_order_cart_mixin.py`, `pages/mall_order_address_mixin.py`, `pages/mall_order_checkout_mixin.py`, `flows/mall_order_http.py`, `flows/mall_order_types.py`, `scripts/run_mall_order_flow.py` | 购物车、地址、结算、订单 HTTP/类型以及能力受控订单入口。 |
| 外卖 | `pages/takeout_page.py`, `pages/takeout_mixin.py`, `pages/takeout_shop_mixin.py`, `pages/takeout_checkout_mixin.py`, `pages/takeout_delivery_time_mixin.py`, `pages/takeout_cancel_order_mixin.py`, `pages/takeout_locators.py`, `scripts/run_takeout_wangwang.py` | 外卖导航、进店、结算预览、配送时间、取消边界与 CLI。 |
| 跑腿 | `pages/transfer_page.py`, `scripts/run_transfer_business.py` | 跑腿页面与显式提交控制的 CLI。 |
| 充值 | `pages/charge_page.py` | 充值表单、账号与创建订单边界。 |
| 配送辅助 | `pages/shipping_page.py` | 配送指引/辅助页面；调用方与活跃入口待 Task 7 复核。 |
| 包入口 | `pages/__init__.py`, `scripts/__init__.py` | 页面与脚本包入口。 |

文件计数：公共基础 8、登录与首页 20、商城只读浏览 21、商城订单边界 6、外卖 8、跑腿 2、充值 1、配送辅助 1、包入口 2；合计 **69**。

## 3. 业务域入口、测试与历史证据映射

| 域 | 主要入口/生产区 | 当前测试文件（映射的生产区） | 历史报告 | 当前审查层状态 |
| --- | --- | --- | --- | --- |
| 公共基础 | `commons/*.py` | `test_android_runtime.py`（Android runtime）；`test_config.py`（配置）；`test_diagnostics.py`（诊断）；`test_driver.py`（Driver）；`test_logger.py`（日志）；`test_waits.py`（等待） | `2026-07-22-foundation-review.md` | Task 2 已完成静态审查并执行聚焦离线测试；证据与发现见第 9 节。 |
| 登录与首页 | `pages/Home.py`、`pages/app_common.py`、`pages/login*`、`scripts/main.py`、`scripts/run_login.py`、`scripts/password_login_standalone.py`、`scripts/smoke_test.py` | `test_home.py`（首页）；`test_login.py`、`test_login_page_unit.py`（登录）；`test_main_cli.py`（主 CLI） | `2026-07-22-login-home-review.md` | 见第 5 节；均未开始/未执行。 |
| 商城只读浏览 | `pages/shop_*`、`flows/shop_home_*`、`scripts/run_shop_home.py`、`scripts/run_shop_business.py` | `test_shop_home_navigation.py`（商城导航/严格模式）；`test_shop_business_decomposition.py`（搜索/详情拆分门面） | `2026-07-28-mall-safe-decomposition-review.md`；`2026-07-28-shop-business-readonly-decomposition-review.md` | Task 4 已完成静态审查与聚焦离线验证；证据、缺陷和风险见第 11 节。 |
| 商城订单边界 | `pages/mall_order_*`、`flows/mall_order_*`、`scripts/run_mall_order_flow.py` | `test_mall_order_address.py`（地址）；`test_mall_order_cart.py`（购物车）；`test_mall_order_checkout.py`（结算）；`test_mall_order_cli.py`（CLI/能力）；`test_mall_order_http.py`（HTTP）；`test_mall_order_safety.py`（安全边界）；`test_mall_order_types.py`（类型/金额） | `2026-07-22-mall-order-boundary-review.md`；`2026-07-28-mall-safe-decomposition-review.md` | Task 5 已完成静态审查与全部匹配离线测试；证据、缺陷和风险见第 12 节。 |
| 外卖 | `pages/takeout_*`、`scripts/run_takeout_wangwang.py` | `test_takeout_cli.py`（CLI 组合）；`test_takeout_checkout_boundary.py`（结算/提交边界） | `2026-07-27-takeout-safe-checkout-review.md` | 见第 5 节；均未开始/未执行。 |
| 跑腿 | `pages/transfer_page.py`、`scripts/run_transfer_business.py` | `test_transfer_page.py`（页面）；`test_transfer_cli.py`（CLI） | `2026-07-27-transfer-charge-review.md` | 见第 5 节；均未开始/未执行。 |
| 充值 | `pages/charge_page.py` | `test_charge_page.py`（页面/提交边界） | `2026-07-27-transfer-charge-review.md` | 见第 5 节；均未开始/未执行。 |
| 配送辅助 | `pages/shipping_page.py` | 未发现匹配 `test_shipping_*.py` 的文件；调用方、活跃入口和覆盖关系待复核。 | 无独立报告 | 见第 5 节；均未开始/未执行。 |

测试文件总数为 **24**。上表将每个 `testcases/test_*.py` 文件映射到一个生产区域；“无独立测试”是覆盖缺口，不是生产缺陷结论。

## 4. 当前全局风险计数（去重文件）

扫描根为 `commons/`、`pages/`、`flows/`、`scripts/`，即上述 69 个唯一生产文件。方法刻意不使用 `Get-Content | Measure-Object`：它可能把空文件处理为没有对象。每个文件使用 .NET `ReadAllText` 读取：空文件计为 0 行；所有文件先计 `\r\n|\r|\n` 换行分隔符；仅当文件非空且内容不以换行结尾时再加 1。BOM 不影响计数。

| 指标 | 当前值 | 精确定义 |
| --- | ---: | --- |
| 唯一生产 Python 文件 | 69 | 一次递归枚举后排序，按完整路径去重。 |
| 物理行 | 23,666 | 上述空文件安全的换行计数方法。 |
| 固定等待 | 524 | 正则 `(?m)\btime\.sleep\s*\(` 的全部匹配。 |
| 宽泛异常 | 735 | 正则 `(?m)^\s*except\s*(?:Exception(?:\s+as\s+\w+)?\s*)?:\s*(?:#.*)?$` 的 `except Exception`（可带 `as`）及 bare `except:`。 |
| 超过 800 物理行的文件 | 10 | 按单个去重生产文件的物理行数，严格大于 800。 |

超过 800 行的文件：

| 物理行 | 文件 |
| ---: | --- |
| 2,823 | `pages/takeout_checkout_mixin.py` |
| 2,486 | `pages/login/mixins/oauth_mixin.py` |
| 1,308 | `pages/shop_home_page.py` |
| 1,206 | `scripts/run_mall_order_flow.py` |
| 1,085 | `pages/takeout_page.py` |
| 1,085 | `pages/takeout_cancel_order_mixin.py` |
| 1,067 | `pages/mall_order_checkout_mixin.py` |
| 985 | `pages/login/mixins/find_click_mixin.py` |
| 910 | `pages/login/mixins/navigation_postlogin_mixin.py` |
| 873 | `pages/Home.py` |

空文件（明确计入文件总数、计为 0 行）：`commons/__init__.py`、`commons/base_page.py`、`scripts/__init__.py`。域之间可能共享调用链，故域小计不得用于重算本节全局值。

## 5. 当前覆盖状态矩阵

以下每个单元只取允许值中的一个。Task 1 初始基线未执行测试、编译或设备/Appium 操作；Task 2 已执行公共基础聚焦离线 pytest（见第 9 节），但未执行设备/Appium 操作。保留的历史证据单独记录在第 6 节，不能转换为当前版本兼容性结论。

| 域 | 静态审查 | 离线验证 | 真机无副作用 | 真实写入 |
| --- | --- | --- | --- | --- |
| 公共基础 | 已完成（含 3 个确认缺陷、3 个风险） | 已通过（21 passed） | 未执行 | 未授权未执行 |
| 登录与首页 | 已完成（新增 1 个 P0、2 个 P1；2 个 P2 风险、1 个 P3 风险） | 10 passed，1 deselected（安全排除真实认证） | 未执行 | 未授权未执行 |
| 商城只读浏览 | 已完成（3 个确认缺陷、3 个风险） | 已通过（55 passed） | 未执行（仅核对 `a63e281` 保留证据） | 未授权未执行 |
| 商城订单边界 | 已完成（3 个 P0、2 个 P1；4 类风险） | 已通过（91 passed） | 未执行 | 未授权未执行 |
| 外卖 | 已完成（2 个 P0、5 个 P1；3 类风险） | 按增量规则跳过（Task 9 全量 non-device 兜底） | 未执行 | 未授权未执行 |
| 跑腿 | 未开始 | 未开始 | 未执行 | 未授权未执行 |
| 充值 | 未开始 | 未开始 | 未执行 | 未授权未执行 |
| 配送辅助 | 未开始 | 未开始 | 未执行 | 未授权未执行 |

特别说明：公共基础的 Task 2 静态审查与聚焦离线测试已完成，证据见第 9 节；其余业务域尚未完成静态审查。历史离线计数仅为审查线索；Task 9 的新鲜全量非真机回归才是当前树的最终离线结论。

## 6. 历史证据继承与增量复审边界

“当前相关差异”按历史提交到当前 SHA 的 `git diff --name-status` 检查，且只列与该报告的域或其共享依赖相关的生产/测试路径。报告提交与报告中描述的实现/设备证据提交不同处，均在同一单元格显式注明。

| 历史报告 | 对应提交/证据边界 | 当前相关差异 | 继承判断 | 必须复审的文件/范围 |
| --- | --- | --- | --- | --- |
| `2026-07-22-foundation-review.md` | 报告引入：`9dbb62c`；该报告自身说明当时无法取得 Git 基线，未声称设备回归。 | `commons/android_runtime.py` 已修改；并出现后续各域新入口。 | 仅作历史设计/测试背景，不能作当前兼容性结论；须增量复审。 | Task 2：全部 `commons/*.py`，重点 `commons/android_runtime.py` 及其新调用链。 |
| `2026-07-22-login-home-review.md` | `fe1353a`（登录/首页/跑腿生命周期实现与报告）。 | 域内主登录/首页文件自此无直接修改；共享 `commons/android_runtime.py` 已变更。 | 未修改登录/首页代码的历史结论可作为线索；当前静态结论仍待 Task 3，且共享依赖须复审。 | Task 3：`pages/Home.py`、`pages/app_common.py`、`pages/login*`、`scripts/main.py`、`scripts/run_login.py`、`scripts/password_login_standalone.py`、`scripts/smoke_test.py`；并检查 Android runtime 影响。 |
| `2026-07-22-mall-order-boundary-review.md` | `c9d2bec`（商城订单边界报告/实现）。 | `scripts/run_mall_order_flow.py` 已修改并拆分；新增 `flows/mall_order_http.py`、`pages/mall_order_{cart,address,checkout}_mixin.py`；商城导航与 `commons/android_runtime.py` 亦变更。 | 原结论不能直接继承为当前全域结论，必须增量复审。 | Task 5：全部商城订单边界文件、`flows/mall_order_types.py`、相关 CLI/安全测试；Task 4 复审相邻导航链。 |
| `2026-07-27-takeout-safe-checkout-review.md` | 实现：`3a10b81`；报告：`62b665d`。 | 外卖域文件及 `scripts/run_takeout_wangwang.py` 在此后无直接修改；公共基础层有修改。 | 外卖域内未变代码的离线/安全结论可作为可继承历史证据；不等于当前离线或设备兼容结论。 | Task 6：全部外卖文件、CLI、共享基础依赖；历史设备范围仍不继承。 |
| `2026-07-27-transfer-charge-review.md` | 报告：`410b508`；引用实现：`fe1353a`（跑腿）与 `180b320`（充值）。 | `pages/transfer_page.py`、`scripts/run_transfer_business.py`、`pages/charge_page.py` 在此后无直接修改；共享 `commons/android_runtime.py` 已变更。 | 域内未变代码可继承为历史线索；当前静态/离线/设备结论均待 Task 7。报告已明确未重新运行设备，不能宣称兼容。 | Task 7：跑腿、充值和 `pages/shipping_page.py`，另复核共享 Android runtime 调用关系。 |
| `2026-07-28-mall-safe-decomposition-review.md` | 报告提交：`d12b6d5`/`92221a7`；报告内保留设备运行是当时的商城导航命令。 | 之后新增商城搜索/详情 mixin，且 `pages/shop_home_page.py`、`scripts/run_mall_order_flow.py`、导航安全测试已修改。 | 历史只读设备运行仅说明当次路径；因后续代码变化，不能继承为当前商城浏览或订单相关的设备兼容性。 | Task 4/5：商城首页、业务门面、搜索/详情 mixin、订单 CLI、导航与安全测试。 |
| `2026-07-28-shop-business-readonly-decomposition-review.md` | 报告最终提交：`a831d75`；保留设备运行：`a63e281`；报告明确 `e88173b`、`4224d71` 仅离线验证。 | 自 `a63e281` 起，`pages/shop_home_page.py`、`scripts/run_mall_order_flow.py`、`test_mall_order_safety.py`、`test_shop_business_decomposition.py`、`test_shop_home_navigation.py` 已变化；自最终报告 `a831d75` 到当前生产代码无差异。 | 最终报告的离线历史可作为当前树的背景；**设备证据不得提升为当前版本兼容性**，因为它早于 `e88173b`/`4224d71`，且未重跑设备。 | Task 4：严格只读导航、`pages/shop_home_page.py`、搜索/详情门面；Task 5：`scripts/run_mall_order_flow.py` 与能力边界。 |

## 7. 已知证据缺口（非缺陷结论）

- 本任务未对任一域完成静态审查；因此尚无本次的文件/行号级缺陷结论。
- 本任务未执行离线 pytest、全量回归或编译；所有历史通过数仅作背景，不能替代 Task 9 的当前树全量非真机回归。
- 本任务未启动 Appium、未连接/操作设备，未执行真实写入或可能写入业务数据的命令。
- 商城只读保留设备证据仅适用于提交 `a63e281` 的当次导航路径；后续 `e88173b` 和 `4224d71` 是离线验证，故不得声称当前设备兼容。
- 外卖历史 `--checkout` 会加购/准备结算，可能留下购物车数据；它不属于严格无副作用验收路径。
- 跑腿、充值的历史报告没有当前 App 版本设备兼容性结论；充值当前也缺少独立安全 CLI 的已验证结论。
- `pages/shipping_page.py` 没有独立 `test_shipping_*.py` 映射，且其活跃入口/调用方尚待 Task 7 确认。
- 全局计数是规模/风险信号而非缺陷数量；域归属可能重叠，但全局计数只按唯一生产文件计算。

## 8. 后续更新约定

后续任务仅在完成相应域的静态审查、离线验证或获授权的安全设备验证后，更新第 5 节的单一状态值，并在本报告增加可复核的命令、输出、文件行号和证据边界。真实写入在获得单独、明确授权前始终保持“未授权未执行”。

## 9. Task 2：公共基础层、配置、Driver、等待与诊断审查

### 范围、基线与方法

- 审查对象：`commons/android_runtime.py`、`commons/config.py`、`commons/diagnostics.py`、`commons/driver.py`、`commons/logger.py`、`commons/waits.py`，以及对应六个单元测试；另追踪了 `pages/Home.py`、`pages/app_common.py` 和所有 `DriverManager`/`capture_failure` 的调用边界。
- 当前树：`dc81bda1aa1d557f402e9e0328d263caca1c5a06`；该提交只更正审查文档指标。生产基线仍为本报告的 `f4e37d8c6753729522ed2771095f859caf83b494`。
- 继承边界：历史基础报告由 `9dbb62c` 引入且明确无法取得可靠 Git 基线；`9dbb62c..HEAD` 中 `commons/android_runtime.py` 已变更（现代 Appium 的 `mobile: startActivity` 回退），故历史报告只作设计和测试背景，不能作为当前兼容性结论。
- 未执行 Appium、ADB、网络、真机或真实写入操作。`logs/` 为既有未跟踪运行时目录，未检查、编辑或纳入提交。

### 已验证的正向行为

- `AppConfig.from_env()` 对已支持字段采用默认值，再由环境覆盖；`ConfigManager.create_config()` 的已知显式参数最后覆盖环境值（`commons/config.py:49-66, 106-109`）。布尔值只接受显式 token，未知值回退默认值（`commons/config.py:15-24`）。
- Driver 仅在 Remote、启动策略与隐式等待均完成后写入缓存（`commons/driver.py:50-67`）；普通关闭对同一缓存对象至多调用一次 `quit()`（`commons/driver.py:70-84`）。
- 等待使用单调时钟、输入校验和可行动的必需元素错误（`commons/waits.py:17-38, 52-66`）；Driver 查找异常会传播，未被转换为“未找到”。
- 截图和 XML 采集彼此独立，且 XML 在写盘前调用 `sanitize_xml()`（`commons/diagnostics.py:65-83`）。这不覆盖下列脱敏绕过。

### 确认缺陷

| 优先级 | 位置 | 证据与影响 | 修复方向 |
| --- | --- | --- | --- |
| P1 | `commons/driver.py:50-64` | `webdriver.Remote()` 成功后，若 `post_session_android_launch()`（55 行）或 `implicitly_wait()`（56 行）抛异常，处理器只移除缓存键，未对局部 `driver` 调用 `quit()`。远端 Appium session 因而可能遗留，后续重试会创建额外 session。现有 `test_driver.py` 只覆盖 Remote 自身失败（46-55 行），未覆盖该路径。 | 预先置 `driver = None`；异常时若已创建则尽力 `quit()`，记录清理失败但保留原始异常；新增两项启动后失败测试。 |
| P1 | `commons/logger.py:15-18, 36-48` | `_SECRET_PATTERN` 仅匹配 `password|code|token` 后接 `:` 或 `=`。实际验证 `redact_text('password secret-value; verification code 123456; token abc')` 原样返回；这些值会写入文件和控制台处理器，违背“不得输出密码/验证码/token 值”的保证。现有测试只覆盖 `key=value` 形式（`test_logger.py:40-53`）。 | 优先让敏感字段走结构化、按字段名脱敏的日志 API；同时覆盖常见空格、引号、JSON、格式化参数和异常消息形式的红线测试。 |
| P1 | `commons/diagnostics.py:15-22, 45-49, 75-77` | XML 脱敏同样只识别命名属性或纯数字 `text/content-desc`。实际验证 `<node text='password secret-value' content-desc='token abc' />` 写入前仍原样保留两个值；失败证据 XML 可泄露敏感显示内容。现有测试仅覆盖 `password=`、手机号和纯数字验证码（`test_diagnostics.py:37-53`）。 | 以 XML 属性为单位解析/重写，按敏感 key、字段语义及 value 内的键值片段脱敏；补充上述反例和混合语言/JSON 值测试。 |

### 风险与覆盖缺口（非确认缺陷）

| 优先级 | 位置 | 风险依据 | 建议 |
| --- | --- | --- | --- |
| P2 | `commons/driver.py:38-67` | 缓存查询和写入未受锁保护；两个线程可同时看到缺失的 `session_name` 并各自创建一个 Remote session，最后一个覆盖缓存。仓库未提供并发调用证据，故列为风险而非已复现缺陷。 | 用每 session 锁/单飞机制覆盖整个“检查—创建—发布”临界区，并增加并发单例会话测试。 |
| P2 | `commons/driver.py:74-84` | `quit()` 抛异常后仍将缓存值设为 `None`，丢失可能仍存活的 session 引用；不能重试关闭，下一次获取会新建 session。异常是否表示远端已关闭取决于 Driver/Appium，当前离线证据无法确认。 | 失败时保留可重试引用或显式隔离为 closing/failed 状态，并规定重试/强制清理语义。 |
| P3 | `commons/config.py:52-66, 106-109` | 空 `APPIUM_SERVER_URL` 会成为空字符串而非拒绝或回退；未知显式参数被静默丢弃。已支持字段的优先级正确，但必需连接值与错误拼写缺少 fail-fast 反馈。 | 对 URL、包名和设备名做非空/格式校验；未知覆盖参数抛出明确异常；为两种失败模式补充单元测试。 |

### 离线验证与结论边界

因历史基础证据不能绑定可靠提交且 `commons/android_runtime.py` 后续变更，按增量规则执行了：

```powershell
& 'C:\Users\18718\Desktop\appium_project\venv\Scripts\python.exe' -m pytest -q `
  testcases\test_android_runtime.py `
  testcases\test_config.py `
  testcases\test_diagnostics.py `
  testcases\test_driver.py `
  testcases\test_logger.py `
  testcases\test_waits.py
```

## 10. Task 3：登录与首页审查

### 版本、范围与边界

- 当前审查 SHA：`1324555b9ba4d8f02218c70c4840da37ea6b5d8c`；历史登录/首页实现报告对应 `fe1353a`。对任务指定生产/测试及共享调用链执行差异检查，仅有 `commons/android_runtime.py` 变更；本域文件没有直接差异，但共享 runtime 已变，历史结论只作线索。
- 已逐一复审 20 个任务指定生产文件和 `test_home.py`、`test_login.py`、`test_login_page_unit.py`、`test_main_cli.py`，并核对 Task 2 的 Driver/runtime/logger/diagnostics 证据。没有读取、修改或提交 `logs/`。
- 未启动 Appium、ADB、设备或网络；未登录、发短信/语音验证码、发送客服消息、改密码或改变 OAuth 状态。因此不声明当前设备或 App 版本兼容性。

### 正向证据

- `run_login_method()` 在构造 `LoginPage` 前以 allowlist 拒绝未知方法；`main()` 对 `login`、`method`、`all` 要求显式 `--method`，一次只派发被选 provider（`scripts/run_login.py:12-45`，`scripts/main.py:32-47`）。
- 注入 Driver 不由 LoginPage/Home 关闭，自建 Driver 使用命名 session 关闭（`pages/login/login_page.py:40-59`，`pages/Home.py:74-78,787-791`）。离线用例覆盖该所有权边界。
- 默认手机号、密码与新密码均仅从环境读取且默认空；独立密码入口在建 Driver 前拒绝缺失凭据（`pages/login/data.py:10-48`，`scripts/password_login_standalone.py:46-65`）。验证码仅记录长度、输入过程不直接记录账号/密码值（`pages/login/mixins/semantics_mixin.py:154-172`，`find_click_mixin.py:275-402`）。Task 2 已确认的共享 logger/XML 脱敏 P1 仍适用。
- 登录入口优先 ID/文本/content-desc/UiSelector，坐标后备会复核登录页；首页 Tab 回退和登录后 H5 恢复均有状态检查（`navigation_postlogin_mixin.py:149-220,892-910`，`pages/Home.py:426-462`）。

### 确认缺陷

| 优先级 | 位置 | 证据、影响与修复方向 |
| --- | --- | --- |
| P0 | `pytest.ini:2-6`; `testcases/test_login.py:15-30`; `pages/login/mixins/password_mixin.py:223-350` | 指定 pytest 选择会收集 `device` 标记的 `test_forget_password`，但 pytest 没有默认排除该标记。fixture 会创建真实 Driver，且在提供环境凭据时流程会发码、输入新密码、点击完成。原样运行不是离线测试并会违反本任务边界。默认排除 device；改密/发码/OAuth 使用独立显式破坏性授权开关，未授权时 skip。 |
| P1 | `scripts/smoke_test.py:20-66`; `scripts/main.py:38-45` | 冒烟直接建 `webdriver.Remote()`，异常路径隐式返回 `None`；调度器以 `is not False` 判成功。因此默认 `smoke`、`quick`、`all` 可在真实冒烟失败后退出 0，且 `all` 会继续登录。显式返回 bool、失败非零退出，并将设备冒烟移出默认/quick。 |
| P1 | `pages/Home.py:380-405,471-543` | 搜索/客服点击后即使目标状态未确认、回首页失败仍返回 `True`；金刚区固定等待 3 秒后报告点击成功，未断言目的页。这会把定位、认证弹层或 Driver 故障转换为绿灯。只有目标和回退状态都通过才返回成功，改用显式等待并保留 action/locator 错误。 |

Task 2 的 3 个共享 P1（Driver 创建后失败可能遗留 session、logger 空格形式敏感值未脱敏、诊断 XML 文本敏感片段未脱敏）均影响本域登录凭据/验证码及失败证据；本节不重复计数，详见第 9 节。

### 风险与覆盖缺口

| 优先级 | 位置 | 风险依据与建议 |
| --- | --- | --- |
| P2 | `pages/login/mixins/oauth_mixin.py:2025-2155`; `pages/login/mixins/state_popup_mixin.py:136-172` | 发码路径使用宽泛“验证码/短信”定位、bounds/手势后备与轮询；通用弹窗还会勾选 checkbox 并点击“同意/确认”。`phone` 方法虽需显式选择，但无设备证据不能证明不会误点或产生认证副作用。将发码和协议确认拆为具名、状态受限、一次性步骤，并以模拟 Driver 覆盖。 |
| P2 | `pages/login/mixins/find_click_mixin.py:933-951`; `pages/login/mixins/oauth_mixin.py:423-916` | OAuth 在 Driver API 不可用时回退 ADB，随后自动点第三方“允许/同意/授权”。provider 不会串行混跑，但无法仅凭静态证据证明第三方屏语义唯一。删除或显式授权 ADB 后备，并以已验证 provider 包/授权页状态约束提交。 |
| P3 | 本域 20 个生产文件 | 6,894 物理行、154 个 `time.sleep(...)`、205 个宽泛 `except`；超 800 行的 `Home.py` (873)、`find_click_mixin.py` (985)、`navigation_postlogin_mixin.py` (910)、`oauth_mixin.py` (2,486)。这是复杂度风险而非单独缺陷；按状态机/登录方式拆分、统一显式等待和窄异常，并给后备路径补离线失败断言。 |

### 离线验证与安全结论

先以相同文件选择执行 `--collect-only`，结果为 `11 tests collected in 0.72s`，其中包含真实设备的 `TestLogin::test_forget_password`。所以没有运行任务简报的原样命令；这是安全跳过，不是通过/失败。运行的安全等价离线子集为：

```powershell
& 'C:\Users\18718\Desktop\appium_project\venv\Scripts\python.exe' -m pytest -q -m 'not device' `
  testcases\test_home.py `
  testcases\test_login.py `
  testcases\test_login_page_unit.py `
  testcases\test_main_cli.py
```

输出：`10 passed, 1 deselected in 0.75s`。它仅覆盖注入 Driver、dispatch allowlist 与离线 CLI 分支，不覆盖真实认证、SMS/语音、OAuth、UI 定位或设备兼容性。

### Task 2 原有离线结论

最新一次精确输出：`.....................                                                    [100%]`，`21 passed in 0.70s`（0 failed）。该结果确认当前已测行为，不反驳上述未覆盖的错误路径；也不构成 Appium、设备或网络兼容性结论。

## 11. Task 4：商城首页、搜索、分类和商品详情只读审查

### 范围、版本与安全边界

- 审查基线：`c54dd3b0edec47b98d76f84a5d6b5fac7362d806`。逐一静态核对 `pages/shop_home_page.py`、`pages/shop_business_page.py`、搜索/详情 mixin、全部 `pages/shop_mall_*.py`、`flows/shop_home_*`、四个 phase、两个商城 CLI 和两份指定测试。
- 本次只运行 Fake Driver 离线测试并只读核对 brief 指定的三份保留文件；未启动 Appium、ADB、设备或网络，未点击加购、立即购买、下单、地址、分享/复制、客服/IM、支付或其他写入控件。
- `ShopBusinessPage` 的 MRO 为 `MallBusinessSearchMixin → MallBusinessDetailMixin → ShopHomePage`，mixin 不定义 `__init__`，facade 的 `super().__init__(driver, wait_sec=...)` 落到 `ShopHomePage`（`pages/shop_business_page.py:30-57`）。与拆分前 `4bb07d4` 静态对照，38 个迁移方法签名差异为 0；`parse_price_text` 从详情 mixin 导入并由 facade 继续重导出（`pages/shop_business_page.py:12-16`、`pages/shop_business_detail_mixin.py:402-409`）。

### 已验证的正向行为

- `search_goods()` 只编排打开搜索页、输入/提交关键字、等待结果和浏览筛选；`open_goods_detail()` 只从搜索或商城首页打开商品；`browse_goods_detail()` 只调用主图、活动信息、详情滚动、更多商品和回顶方法。上述只读公开链未直接调用 facade 中的加购、订单、地址、IM、分享或支付助手（`pages/shop_business_search_mixin.py:472-493`，`pages/shop_business_detail_mixin.py:237-250,379-399`）；活动信息的宽泛定位风险另列如下。
- 严格导航由 `run_navigation_verification()` 在 `try/finally` 内设置并恢复 `_mall_tab_coordinate_fallback_disabled`（`scripts/run_mall_order_flow.py:587-603`）。该 guard 同时覆盖 `ensure_mall_tab()` 的直接/末次坐标路径、结构点击失败后的 `mobile: clickGesture` 和恢复末端的坐标重试（`pages/shop_home_page.py:179-237,807-858,884-921`）；六个 Fake Driver 用例覆盖严格禁用与默认兼容回退（`testcases/test_shop_home_navigation.py:44-204`）。
- 搜索/详情拆分测试覆盖方法表面、搜索和开详情的失败短路、价格 parser 以及 facade 重导出（`testcases/test_shop_business_decomposition.py:15-219`）。本次聚焦结果为 55 项全部通过。

### 确认缺陷

| 优先级 | 位置 | 证据、影响与后续修复方向 |
| --- | --- | --- |
| P0 | `scripts/run_shop_home.py:43-94`; `flows/shop_home_flow.py:83-141`; `flows/shop_home_phases/kingkong_daily_baihuo.py:12-22`; `flows/shop_home_phases/home_add_cart_badge.py:12-26`; `pages/shop_mall_product_detail_page.py:324-357` | CLI 无参时 `--skip-phase=[]`，转换为 `skip=None` 后默认执行全部四阶段；调用链包含分类选规格加购、详情加购与收藏、末次首页加购，且没有任何 `--allow-cart-mutation`/收藏授权。仅执行默认命令即可污染购物车和收藏状态。默认改为只读阶段；所有加购/收藏阶段必须同时要求具名动作和显式单次 capability，Driver 创建前拒绝缺失授权。 |
| P0 | `scripts/run_shop_business.py:36-69,93-135`; `pages/shop_business_page.py:278-316,340-393,395-469,493-514` | CLI 无参默认 `action=full`、非空 IM 消息和 `share_target=复制链接`；调用链会复制分享、发送客服消息并点击“立即购买”进入确认订单页。`--submit-order` 只保护最终提交，不保护前三种有副作用动作，也没有独立分享/IM/结算授权。默认改为 `search` 或显式必填 action；复制、IM、立即购买/结算分别增加 capability，并在建 Driver 前验证组合。 |
| P1 | `pages/shop_home_page.py:179-188,230-236,785-805` | 默认兼容路径把 ADB/Appium 坐标命令无异常直接当成商城 Tab 成功；尽管 `_tap_mall_bottom_tab_by_coordinate()` 文档称会由主列表标识校验，代码未调用该校验，`ensure_mall_tab()` 立即返回 `True`。布局变化或错误前台页会产生假阳性，并让后续默认写入流程在错误页面继续。每次坐标点击后必须等待 `_is_mall_home_main_list_visible()`；失败时继续语义/结构路径并最终 fail closed，增加“手势成功但目标状态未出现”用例。 |

### 风险与覆盖缺口（非确认缺陷）

| 优先级 | 位置 | 风险依据与建议 |
| --- | --- | --- |
| P2 | `pages/shop_business_search_mixin.py:76-112`; `pages/shop_business_detail_mixin.py:293-320,379-394` | 名为只读的详情浏览会用 `contains()` 匹配“活动/优惠/促销/领券/满减”并点击首个候选；静态证据不能确认线上“领券”是否只是打开面板还是直接领取，所以不升级为确认写入。改用已验证的活动信息容器 ID/状态 allowlist，排除领取/兑换/确认类控件，并加 Fake Driver 负向测试。 |
| P2 | `testcases/test_shop_home_navigation.py:34-204`; `testcases/test_shop_business_decomposition.py:15-219`; `scripts/run_shop_home.py:43-94`; `scripts/run_shop_business.py:36-135` | 两份指定测试覆盖导航 guard 和拆分兼容，但没有 CLI 默认值/dispatch 测试，也没有断言只读 action 永不调用加购、收藏、分享、IM、结算助手；因此两个 P0 默认入口长期未被回归阻断。为两个 parser/dispatcher 增加“默认只读、写能力缺授权在 Driver 前拒绝、只读 helper 调用黑名单”测试。 |
| P3 | Task 4 的 19 个生产文件 | 共 5,393 物理行、171 个 `time.sleep(...)`、222 个宽泛 `except`。这是定位/等待/错误可诊断性风险，不代表每一处均为缺陷。优先治理搜索、详情、Tab 恢复的固定等待与吞异常路径，并保持严格导航的失败断言。 |

### 离线验证与历史统计核对

执行的唯一 pytest 命令：

```powershell
& 'C:\Users\18718\Desktop\appium_project\venv\Scripts\python.exe' -m pytest -q `
  testcases\test_shop_home_navigation.py `
  testcases\test_shop_business_decomposition.py
```

精确输出：

```text
.......................................................                  [100%]
55 passed in 0.74s
```

该结果只证明当前 Fake Driver 覆盖的导航 guard、迁移表面、编排短路和 parser 行为；不覆盖真实 UI 定位、Appium/ADB、设备、网络或业务写入安全。

历史 `2026-07-28-shop-business-readonly-decomposition-review.md` 的“38 passed 覆盖 safety/navigation/decomposition”不能由保留证据支持：`46c5df3` 版本原报告明确记载“全部 `test_mall_order_*.py` + navigation + decomposition”为 **139 passed**；`a831d75` 在未保留命令/控制台文本、且同一提交还新增一个 decomposition 用例时，将数字改为 **38 passed**。`a831d75` 中两份 navigation/decomposition 文件与当前完全相同，而本次仅这两份就收集并通过 **55** 项，故 38 不可能代表所称 navigation/decomposition 全集，更不能代表再含 safety 的集合。历史文件不改写；38 仅保留为命令无法复原的历史子集数字。

### 保留设备证据与当前结论边界

- 三份文件只对应 `a63e281` 的当次严格导航：PNG SHA-256 `15F8E94C8060BE78E997CB660E3DA12E13BB3E5E05C5291695690E15551A7C2C`；XML `E9C1480634A307FF174635512954AB95C513EC3811C2050106CFE2DDEC74312F`；日志 `A4F437934BB5EF30D4FA577E872912D76C637CA5A340212FF66F5A01E661DA61`。
- 截图显示 ₱33.00 的“可口可乐(经典美味)330ml”详情页；加购、立即购买、客服、收藏和购物车仅为画面中的被动控件。XML 文本含同一商品、价格及一组加购/立即购买控件，54 个属性值被替换为 `<redacted>`，敏感 phone/code/password-like 字面量扫描为 0。
- XML 的 `<redacted>` 被原样写入属性值（例如 `password="<redacted>"`），因此不是 well-formed XML；本次只能做文本 token 核对，不能把它当作可解析层级证据。这是保留证据质量限制，不扩展为当前设备结论。
- 28 行日志记录底栏结构进入商城、输入/提交“可乐”、详情快照 `unit_price=33.0`、两次安全返回和 Driver 正常关闭；未发现执行加购、分享/复制、IM、结算、提交订单、支付、地址、取消订单或网络异常动作的日志。
- `e88173b` 与 `4224d71` 之后没有重跑真机；本 Task 也未运行设备。因此上述材料只能证明 `a63e281` 的单次只读路径，不能声明 `c54dd3b` 或当前 App/设备兼容，也不覆盖购物车、收藏、分享/复制、IM、结算、订单、支付、地址、取消、库存或异常网络流程。

## 12. Task 5：商城购物车、地址、结算和订单边界审查

### 范围、版本、历史与安全边界

- 审查基线：`d5b3dc79e7063d9942f17346742305bbe4b96494`。逐行复审 `scripts/run_mall_order_flow.py`、三个 `pages/mall_order_*_mixin.py`、`flows/mall_order_http.py`、`flows/mall_order_types.py` 和全部 7 个 `test_mall_order_*.py`。
- `2026-07-22-mall-order-boundary-review.md` 可绑定到 `c9d2bec`，但当前树新增 HTTP/三个 mixin/五份测试且订单脚本已重构，原结论不能直接继承。`a831d75..d5b3dc7` 的本 Task 生产文件和测试无差异，故 7 月 28 日最终报告的离线历史只作当前树背景；其中设备证据仍只属于更早的 `a63e281` 单次严格导航。
- 未启动 Appium、ADB、设备或网络，未运行商城脚本，未加购/删除购物车、未新增/编辑/复制地址、未提交/取消订单、未发送消息、未支付。既有 `logs/` 未读取、修改或纳入提交。

### 动作—独立 capability—Driver 前校验矩阵

| 动作 | 动作参数 | 当前 capability | Driver 前校验与实际边界 | 结论 |
| --- | --- | --- | --- | --- |
| 严格只读导航 | `--verify-navigation-only` | 不需要写 capability；反向拒绝全部 mutation capability | `validate_args()` 拒绝购物车、地址、创建、取消、消息 capability 及异常流，`main()` 随后才创建 Driver（`scripts/run_mall_order_flow.py:1009-1031,1084-1110`）。 | 正向通过；Fake Driver 覆盖该顺序。 |
| 进入结算页（立即购买） | `--flow buy_now` | 无独立 capability | `--flow` 默认就是 `buy_now`；无参也会建 Driver 并派发立即购买至结算（`scripts/run_mall_order_flow.py:753-755,1169-1173`）。未传 `--submit-order` 时在提交点前返回（`pages/mall_order_checkout_mixin.py:1000-1024`），不会创建订单或支付。 | “结算”与“提交”已在运行时分开，但“无动作返回 2”未满足，见 P1。 |
| 购物车加购/结算/删除 | `--flow cart|both`、`--add-to-cart-only`、`--run-cart-delete`、`--cart-delete-prepare-item` | 共用 `--allow-cart-mutation` | 校验在 Driver 前（`scripts/run_mall_order_flow.py:1038-1047`）；加购、删除和购物车结算分别可达（`pages/mall_order_cart_mixin.py:237-365`）。 | 缺 capability 会返回 2；同一粗粒度 capability 授权加与删，列为风险。 |
| 地址选择/新增/编辑/复制 | `--ensure-test-address`、`--force-add-test-address`、`--edit-test-address`、`--copy-test-address`、`--add-test-address-only` | 共用 `--allow-address-mutation` | 任一参数缺 capability 在 Driver 前拒绝（`scripts/run_mall_order_flow.py:1000-1008,1033-1036`）；新增、编辑、复制调用链分别位于 `pages/mall_order_address_mixin.py:463-476,696-724,726-747`。 | 缺 capability 会返回 2；新增/编辑/复制没有独立 capability，列为风险。 |
| 提交并创建订单 | `--submit-order` | `--allow-order-creation` + 正数 `--max-payable` | Driver 前检查动作、创建 capability 和表面正数上限（`scripts/run_mall_order_flow.py:1053-1061`）；运行时先核对限额再点击提交（`pages/mall_order_checkout_mixin.py:988-1027`）。 | 正向顺序正确；有限值校验可被非有限浮点绕过，见 P0。 |
| 支付/货到付款确认 | `--payment-method cod|wechat_mock`；由 `--submit-order` 后隐式触发 | **无独立支付 capability** | 创建订单后无条件调用 `pay_and_assert()`；COD/微信支付都会点击支付控件，微信测试钩子还会发 HTTP POST（`pages/mall_order_checkout_mixin.py:735-870,1025-1027`）。 | 创建 capability 被当成支付授权，见 P0。 |
| 取消本次订单 | `--cancel-created-order` | 独立 `--allow-order-cancellation`，并要求 `--submit-order` | Driver 前组合校验（`scripts/run_mall_order_flow.py:1063-1069`）；运行时还要求本次解析到订单号后才点取消（`pages/mall_order_checkout_mixin.py:1030-1067`）。 | 正向通过；不会默认取消。 |
| 订单消息 | `--send-order-im` | 独立 `--allow-order-message`，并要求 `--submit-order` | Driver 前校验 capability、提交依赖和与 `--skip-order-im` 的冲突（`scripts/run_mall_order_flow.py:1071-1081`）；默认不发送（`pages/mall_order_checkout_mixin.py:976-984,1028-1029`）。 | 正向通过；不会默认发送。 |
| 断网提交异常流 | `--run-network-exception` | **无提交/订单创建/网络变更 capability** | 参数被 navigation-only 拒绝，但普通模式没有 capability/限额校验；运行时切网络后直接点击“提交订单”（`scripts/run_mall_order_flow.py:720-750,985,1009-1031,1185-1186`）。 | 实际执行提交尝试，见 P0。 |

### 已验证的正向行为

- navigation-only 会拒绝所有现有 mutation capability、动作和两类异常流；`main()` 捕获 `ValueError` 后返回 `2`，且 Driver 创建位于完整校验之后（`scripts/run_mall_order_flow.py:998-1110`）。
- 正常结算在金额/商品信息核对后，未传 `--submit-order` 会于 `submit_order()` 和 `pay_and_assert()` 前返回；默认 `submit_order=False`、地址动作=False、取消=False、消息=False，所以不会默认创建地址、订单、支付、取消或发消息（`scripts/run_mall_order_flow.py:853-925,958-970`；`pages/mall_order_checkout_mixin.py:1000-1031`）。结算页仍会按默认策略处理优惠券、备注和预订时间，这是结算表单操作，不是本次已验证的持久化写入结论。
- 取消和消息各有独立 capability，均依赖本次显式提交；取消还要求已解析订单号。购物车、地址缺 capability 和 `--add-to-cart-only` 与提交冲突均在 Driver 前返回 `2`。
- 金额链会核对详情单价、确认页名称/规格/单价、商品金额减优惠加运费、收银台金额和显式上限（`pages/mall_order_checkout_mixin.py:586-643,695-733,988-1027`）；库存接口缺字段/非标量/非法整数以及订单状态非待发货均 fail closed（`flows/mall_order_http.py:124-150,170-196`）。
- HTTP 对 4xx/5xx、`HTTPError`、`URLError`、超时和非法 JSON 转为不含 URL/响应正文的 `MallOrderHttpError`（`flows/mall_order_http.py:71-122`）。这不覆盖下述未分类异常和业务响应结构风险。

### 确认缺陷

| 优先级 | 位置 | 证据、影响与后续修复方向 |
| --- | --- | --- |
| P0 | `scripts/run_mall_order_flow.py:896-925,1053-1061,1124-1129`; `pages/mall_order_checkout_mixin.py:735-870,1025-1027` | `--submit-order --allow-order-creation --max-payable <值>` 在创建订单后无条件执行支付；没有 `--pay-order`/`--allow-order-payment`。默认 COD 仍会选择货到付款并点击确认，`wechat_mock` 会发起支付并调用成功钩子。订单创建授权被扩张为支付授权。将“提交订单”和“支付”拆成两个动作，新增独立一次性支付 capability；无支付动作时停在收银台。 |
| P0 | `scripts/run_mall_order_flow.py:720-750,985,998-1081,1185-1186` | `--run-network-exception` 在普通模式不要求 `--submit-order`、订单创建 capability、金额上限或网络变更 capability，却会切断设备网络并点击“提交订单”。若网络切换报告成功但实际未生效，或请求在断网前后竞态送达，可能创建未授权订单；无论后端结果如何，脚本已执行未授权提交尝试。要求独立异常流动作和网络变更 capability，并复用创建订单/有限金额校验；切网后先验证离线状态，异常结束强校验恢复。 |
| P0 | `scripts/run_mall_order_flow.py:912-915,1053-1061`; `pages/mall_order_checkout_mixin.py:988-998` | `argparse type=float` 接受 `NaN`/`Infinity`；`NaN <= 0` 和 `payable > NaN` 都为 false，`Infinity` 则成为无限上限。因此显式创建动作可绕过“有限正数最大实付”保护。解析后先用 `math.isfinite()` 拒绝非有限值，金额改用 `Decimal`/最小货币单位并增加 `nan/inf/-inf` Driver 前返回 2 测试。 |
| P1 | `scripts/run_mall_order_flow.py:753-755,998-1081,1110,1169-1186` | 无参不是“无动作”：默认 `flow=buy_now`，会创建 Driver 并尝试进入结算，而不是返回 2；`--force-add-test-address --allow-address-mutation`、`--cart-delete-prepare-item --allow-cart-mutation` 等缺少父动作的组合也能通过校验，随后落入默认立即购买。默认改为显式 `action=None` 或严格只读；所有子参数必须绑定唯一父动作，孤立 capability/子参数在 Driver 前返回 2。 |
| P1 | `flows/mall_order_http.py:152-168`; `pages/mall_order_checkout_mixin.py:802-842` | 模拟支付成功接口只要返回任意合法 JSON（包括 `{"ok": false}`）就被当作钩子完成；完整响应还被写入日志。随后无状态 API时，页面只出现宽泛“订单详情”也可通过 `WAIT_SHIP_MARKERS`，没有要求“支付成功/待发货”。这可把业务失败响应和未支付订单详情误报为支付成功。定义严格成功 schema（布尔成功、订单号、金额/状态匹配），失败 fail closed；页面兜底必须出现明确支付成功/待发货状态，日志只记录允许字段。 |

### 风险与覆盖缺口（非确认缺陷）

| 优先级 | 位置 | 风险依据与建议 |
| --- | --- | --- |
| P1 | `scripts/run_mall_order_flow.py:762-880,1000-1047`; `pages/mall_order_cart_mixin.py:237-365`; `pages/mall_order_address_mixin.py:463-476,696-747` | `--allow-cart-mutation` 同时授权加购、数量减少和删除；`--allow-address-mutation` 同时授权选择、创建、编辑和复制。现有校验确实在 Driver 前，但不满足“一个具体动作对应一个独立 capability”的最小权限目标。拆分 add/delete/checkout-cart 及 address-select/create/edit/copy capability，并逐项补 action+capability 矩阵测试。 |
| P2 | `flows/mall_order_types.py:11-70`; `pages/mall_order_checkout_mixin.py:235-323,586-643,720-731` | 金额全部使用二进制 `float` 和固定 `0.02` 容差；`parse_money()` 盲删逗号，会接受畸形分组如 `₱1,2,3.45`，无明确币种的任意小数也可被解析。当前测试覆盖空值、三位小数和 `1.2.3`，未覆盖币种冲突、分组、超大值、非有限值和负 tolerance。改用 Decimal、严格币种/分组语法及按币种定义的最小单位。 |
| P2 | `pages/mall_order_checkout_mixin.py:586-643,695-733,830-870`; `flows/mall_order_http.py:124-150` | 详情到结算核对名称/规格/单价，但商品总价缺失时回退详情价×数量，未显式核对结算页数量；提交后仅核对订单号、金额和宽泛状态，没有再核对订单商品/规格/数量快照。库存允许负整数，且下单后只读一次，未考虑最终一致性。补完整 checkout/order snapshot、非负库存和有界轮询测试。 |
| P2 | `flows/mall_order_http.py:71-122`; `pages/mall_order_checkout_mixin.py:802-819`; `pages/mall_order_address_mixin.py:131-155,664-668` | HTTP 只拒绝 `status >= 400`，缺失 status 被当作 200，3xx/意外 opener 异常没有统一分类；未限制响应大小。mock 支付记录完整响应，地址输入还记录姓名、手机号、微信号原值，可能泄露敏感业务数据。严格只接收 2xx、限制响应大小、统一异常为脱敏边界错误，并改为字段级白名单日志。 |

### 离线验证与设备边界

先静态核对 7 个匹配文件及 pytest 配置：测试均标记 `unit` 或为纯值测试；Driver 路径使用 Fake Manager、对象桩或 monkeypatch，HTTP 使用注入 `FakeOpener` 和 `.invalid` URL；没有 `webdriver.Remote`、真实 `DriverManager()`、ADB、subprocess、socket、device marker 或 autouse fixture。

执行的唯一 pytest 命令：

```powershell
$mallTests = Get-ChildItem testcases -Filter 'test_mall_order_*.py' |
  Select-Object -ExpandProperty FullName
& 'C:\Users\18718\Desktop\appium_project\venv\Scripts\python.exe' -m pytest -q $mallTests
```

精确输出：

```text
........................................................................ [ 79%]
...................                                                      [100%]
91 passed in 1.06s
```

该结果只证明当前 Fake Driver/monkeypatch 覆盖的参数 guard、离线编排、金额 parser 和注入 HTTP 边界；不覆盖真实 UI 定位、Appium/ADB、设备、网络、商品/库存最终一致性或任何业务写入。历史 `38 passed` 不能代表其所称 safety/navigation/decomposition 集合，Task 4 的统计核对结论保持不变。

## 13. Task 6：外卖导航、结算预览、支付和取消边界审查

### 范围、继承边界与安全限制

- 审查基线：`d45442576edef7a3cddd00edf021f4fa4dd466cf`。逐行复审 8 个外卖生产文件、`scripts/run_takeout_wangwang.py`、`testcases/test_takeout_cli.py` 和 `testcases/test_takeout_checkout_boundary.py`。
- 历史实现 `3a10b81`、报告 `62b665d` 均可精确绑定；`3a10b81..d454425` 和 `62b665d..d454425` 中上述 10 个文件均无差异，仅共享 `commons/` 发生变化。因此“默认不提交、`--submit-order` 依赖 `--checkout`、生产路径不自动输入密码”的域内历史结论可作当前静态线索；共享 Driver/runtime 风险、历史离线计数和设备结果均不能提升为当前兼容性结论。
- 本 Task 未启动 Appium、ADB、真机或网络，未运行外卖脚本，未选菜/改购物车、未提交或取消订单、未输入支付密码、未支付、未发消息；既有 `logs/` 未读取、修改或纳入提交。

### 动作—授权—顺序矩阵

| 动作 | CLI/调用入口 | 当前授权或确认边界 | 顺序与静态结论 |
| --- | --- | --- | --- |
| 导航、定位、进店 | 默认执行；不带 `--checkout` | 无写 capability；默认只导航 | `main()` 只调用定位、外卖 Tab 和进店，随后在 `args.checkout=False` 时结束；不调用加购、购物车或结算门面（`scripts/run_takeout_wangwang.py:177-212`; `pages/takeout_page.py:1071-1085`）。定位选择会改变 App 内当前城市，但不属于购物车/订单写入。 |
| 选分类并加菜 | `--checkout` | 只有一个宽泛动作开关；无独立 cart-mutation capability | 先点分类，再打开首商品/规格并执行“加购”，明确写购物车（`pages/takeout_checkout_mixin.py:1728-1804,2734-2746`）。所以 checkout preview 不是只读，也不是无业务数据变化入口。 |
| 购物车与结算预览 | `--checkout` | 同一宽泛开关；无独立 checkout-preview capability | 加购后打开购物车、去结算，并在 `submit_order` guard 前调用通用底栏 helper；该 helper 可匹配“确认支付/提交订单/立即支付/去支付”且有坐标 fallback，点击后又没有 pre-order 状态或订单号断言（`pages/takeout_checkout_mixin.py:1861-2055,2747-2766`）。因此 `--checkout` 可能尝试提交/支付类破坏性控件，静态证据无法证明这次点击只执行阶段跳转或预览会停在创建订单前。 |
| 优惠券、备注、通知、支付方式、配送时间 | `--checkout`；各子参数 | 无逐项 capability；默认 `coupon-policy=auto`、余额支付和非空备注 | 预览阶段会自动选可用券、写备注/快捷备注、选支付方式和配送时段，然后才检查 `submit_order`（`scripts/run_takeout_wangwang.py:115-151`; `pages/takeout_checkout_mixin.py:2186-2239,2421-2491,2640-2690,2767-2804`）。这些是持久化或潜在持久化的结算表单动作，不是纯页面预览。 |
| 最终确认并创建订单 | `--checkout --submit-order` | 仅动作组合；无独立 order-creation capability、金额上限或二次确认 token | CLI 在 Driver 前拒绝孤立 `--submit-order`；guard 通过后会再次调用同一通用底栏 helper，再直接进入支付等待/订单详情/取消编排（`scripts/run_takeout_wangwang.py:172-184,201-227`; `pages/takeout_checkout_mixin.py:2802-2823`）。由于 guard 前已有一次同 helper 点击且两次均无阶段专属状态断言，静态证据不能把创建订单精确归因于所谓“第二次”点击。 |
| 余额支付 | `--checkout --submit-order`，默认 `--checkout-payment balance` | 密码输入由用户手工完成；无自动输入；无独立 payment capability 或人工完成确认信号 | guard 后再次调用通用底栏 helper，随后只等待页面出现“取消订单”，不会接收或记录密码（`pages/takeout_checkout_mixin.py:2693-2698,2805-2818`）。但 helper 的阶段语义未验证，页面标识又被直接当作手工支付完成，见 P0。 |
| 货到付款 | `--checkout --submit-order --checkout-payment cod` | 无独立 payment/COD capability | guard 后再次调用通用底栏 helper，随后跳过人工等待，只检查“取消订单”入口并继续取消（`pages/takeout_checkout_mixin.py:2783-2789,2805-2812`）；两次 helper 点击的阶段语义均无状态断言。 |
| 取消订单 | 提交链隐式自动执行；无 `--cancel-order` 参数 | 无 cancellation capability、无单独人工确认；只依赖任意可见取消入口 | 订单详情检查后无条件进入取消、选固定原因并提交（`pages/takeout_checkout_mixin.py:2811-2822`; `pages/takeout_cancel_order_mixin.py:978-1085`）。未绑定本次订单身份，且入口未点中也不立即终止。 |
| 订单消息 | 无入口 | 无 capability；当前编排不可达 | Task 6 范围内未发现发送订单消息的方法或 CLI 参数；本次没有执行消息动作。后续若新增必须使用独立 action + capability，并在 Driver 前校验。 |

### 已验证的正向行为

- `validate_args()` 在 `DriverManager()` 创建前执行；孤立 `--submit-order` 返回 `2`，且 `argparse` 自身会在未知参数/非法 choice 时以 `2` 退出（`scripts/run_takeout_wangwang.py:57-184,200-202`; `testcases/test_takeout_cli.py:15-46`）。
- 默认 `checkout=False`、`submit_order=False`；navigation-only 进店后结束，不触发店内下单门面（`scripts/run_takeout_wangwang.py:71-82,207-212`; `testcases/test_takeout_cli.py:8-13`）。
- 生产代码、CLI 和环境引用中未发现固定/默认支付密码、`--password` 或自动密码输入方法；余额路径只记录人工输入提示并等待，手工等待超时时不会继续取消（`pages/takeout_checkout_mixin.py:2693-2698,2813-2818`; `testcases/test_takeout_checkout_boundary.py:128-139`）。测试桩仍含固定默认密码字面量，单列 P1。
- 主编排的调用顺序是分类 → 加购 → 购物车 → 去结算 → 通用底栏 helper → 地址 → 券/偏好 → 支付方式 → 配送时间 → `submit_order` guard → 同一通用底栏 helper → 手工支付等待或 COD 详情检查 → 取消（`pages/takeout_checkout_mixin.py:2701-2823`）。预览用例只确认 guard 后的第二次 helper 调用、支付等待、订单详情和取消门面未执行（`testcases/test_takeout_checkout_boundary.py:74-86`）；测试桩把 helper 抽象成事件计数，不能证明 guard 前 helper 命中的真实控件、点击后的 pre-order 状态或未创建订单。

### 确认缺陷

| 优先级 | 位置 | 证据、影响与后续修复方向 |
| --- | --- | --- |
| P0 | `scripts/run_takeout_wangwang.py:71-151,172-227`; `pages/takeout_checkout_mixin.py:1984-2055,2701-2823` | `--checkout --submit-order` 同时授权购物车写入、创建订单、余额/COD 后续处理和自动取消；不存在独立 `allow-cart-mutation`、`allow-order-creation`、`allow-order-payment`、`allow-order-cancellation`，也没有最大实付上限。更严重的是 `submit_order` guard 前已调用可匹配“提交订单/立即支付/去支付”并带坐标 fallback 的通用底栏 helper，且点击后没有 pre-order 状态/订单号断言；即使没有 `--submit-order` 也可能尝试未授权提交或支付控件，静态证据无法证明阶段语义。拆为具名 action + 一次性 capability；创建订单增加有限正数金额上限；预览和最终提交使用 phase-specific control，并在每次点击后断言 pre-order/created-order 状态；无 creation/payment/cancel capability 时 fail closed。 |
| P0 | `pages/takeout_checkout_mixin.py:2693-2698,2805-2822`; `pages/takeout_cancel_order_mixin.py:978-1022` | 余额“手工支付完成”没有人工确认信号、支付状态或本次订单身份，只要 Native/任意 WebView 出现“取消订单”就返回成功，随后自动取消。未支付订单详情、旧订单详情或错误页面的取消入口都可能被误报为本次支付完成，并可能取消非本次订单。要求用户显式确认完成，再核对本次订单号、金额和已支付状态；取消必须绑定该订单身份。 |
| P1 | `scripts/run_takeout_wangwang.py:83-151,172-184,200-227`; `testcases/test_takeout_cli.py:24-86` | Driver 前语义校验只覆盖 `--submit-order` 依赖。`--category`、配送时段、支付方式、券、取件码、通知和备注等 checkout-only 参数在没有 `--checkout` 时被静默忽略，仍创建 Driver并以导航成功返回 0；测试也只覆盖 submit 组合。所有子参数必须绑定 `--checkout`，冲突/孤立参数在 Driver 前返回 `2`，并补参数矩阵测试。 |
| P1 | `pages/takeout_checkout_mixin.py:1728-1804,1984-2055,2186-2239,2421-2491,2738-2804`; `scripts/run_takeout_wangwang.py:71-151` | 名为“结算预览”的 `--checkout` 明确会加菜写购物车，并默认自动选券、输入 `test order` 备注、选择支付方式和配送时间；这些表单动作具有潜在持久化影响。guard 前通用底栏 helper 还可能尝试提交/支付控件，故不能声称预览只在创建订单前停止。默认预览应只读展示；加购、券、备注、通知、支付方式和配送时间分别要求明确动作/capability；通用 helper 改为 phase-specific control，并以点击后的 pre-order 状态断言阻断破坏性阶段漂移。 |
| P1 | `pages/takeout_delivery_time_mixin.py:462-499,520-689`; `scripts/run_takeout_wangwang.py:95-112` | 配送弹层四轮及坐标兜底均未确认打开时，代码没有 fail closed，仍扫描并点击日期/时段；指定 `--delivery-slot-contains` 无匹配时会保留全量池并把首项误标为匹配，序号 `0/负数` 则退化为随机选择，后天失败还会静默退到明天/今天。可在错误页面点击或用非请求时段继续下单。Driver 前校验正序号；弹层、日期和显式 hint 必须逐步确认，任何显式请求未满足即终止。 |
| P1 | `pages/takeout_cancel_order_mixin.py:842-975,1022-1085`; `pages/takeout_locators.py:132-150,165-177` | `shop_cancel_order_flow()` 未点到“取消订单”入口时没有返回失败，仍继续找“确定取消”、选理由和提交；取消结果又把“提交成功”“退款”“待商家”等宽泛文案或连续三次入口消失当成功，未绑定订单/弹层上下文。可能在错误页面继续破坏性点击并误报取消成功。入口、确认层、理由、提交和目标订单状态必须逐步 fail closed；成功只接受与订单号绑定的明确取消状态。 |
| P1 | `testcases/test_takeout_checkout_boundary.py:57-59,103-106`; `testcases/test_takeout_cli.py:15-21` | 测试桩仍定义 `shop_enter_pay_password(password="legacy-default")`。虽现有断言证明该桩不被调用、生产路径也无自动输入，但 Task 6 明确要求测试不得含固定/默认支付密码，因此历史“无密码”结论不能覆盖本次更严格扫描。删除带默认值的密码桩，改用若被访问即抛错的无秘密 sentinel/属性黑名单断言。 |

### 风险与覆盖缺口（非确认缺陷）

| 优先级 | 位置 | 风险依据与建议 |
| --- | --- | --- |
| P1 | `pages/takeout_checkout_mixin.py:1984-2055`; `pages/takeout_delivery_time_mixin.py:502-515`; `pages/takeout_cancel_order_mixin.py:126-175,672-713` | 提交、配送和取消链保留多组坐标/宽泛文案/JavaScript 点击兜底。部分已有弹层标题约束，但无法由静态证据证明所有 UI 版本语义唯一。每个破坏性点击前后都验证页面状态、目标订单和控件语义；未经单独 capability 禁用坐标兜底。 |
| P2 | `testcases/test_takeout_cli.py:8-86`; `testcases/test_takeout_checkout_boundary.py:6-139` | 两份测试只覆盖 submit/checkout 基础组合和主编排事件；`shop_tap_confirm_pay_bar()` 被桩化为计数，未覆盖真实 helper 可匹配提交/支付文案和坐标 fallback，也未断言 guard 前点击后的 pre-order 状态/订单号。此外未覆盖 checkout-only 孤立参数、配送显式 hint/序号 fail closed、订单身份、人工支付确认、取消入口缺失及取消成功状态。为 phase-specific control、动作—capability 矩阵和每个失败短路补 Fake Driver 状态断言。 |
| P3 | Task 6 的 8 个生产文件 | 当前共 6,123 物理行、151 个 `time.sleep(...)`、231 个宽泛异常；超过 800 行的 `takeout_checkout_mixin.py`、`takeout_page.py`、`takeout_cancel_order_mixin.py` 与历史风险一致。固定等待和吞异常可掩盖页面状态错误；优先治理提交、配送和取消状态机，不把复杂度计数当作缺陷数量。 |

### 测试决策与设备边界

两份指定测试经静态核对仅使用 `RecordingCheckout`/Fake Manager 和 monkeypatch，不实例化真实 `DriverManager`、不连接设备或网络，不产生业务写入（`testcases/test_takeout_cli.py:37-86`; `testcases/test_takeout_checkout_boundary.py:6-139`）。测试只能证明桩化编排事件，不证明通用底栏 helper 在真实 UI 中的阶段语义、guard 前点击后仍处于 pre-order 状态或未创建订单。域内生产/测试自可绑定的 `62b665d` 后没有变化，历史证据可绑定 SHA，且本缺陷由 helper 标签集合、坐标 fallback、调用位置和缺失状态断言直接证实、不需要复现，因此按增量规则跳过聚焦 pytest；由 Task 9 新鲜全量 non-device 测试兜底。

本 Task 的静态结论不证明真实 UI 定位、配送时间、余额/COD、订单详情、取消接口、Appium/ADB、设备、网络或当前 App 版本兼容性。真实写入保持“未授权未执行”。
