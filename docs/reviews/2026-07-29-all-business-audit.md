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
| 商城只读浏览 | `pages/shop_*`、`flows/shop_home_*`、`scripts/run_shop_home.py`、`scripts/run_shop_business.py` | `test_shop_home_navigation.py`（商城导航/严格模式）；`test_shop_business_decomposition.py`（搜索/详情拆分门面） | `2026-07-28-mall-safe-decomposition-review.md`；`2026-07-28-shop-business-readonly-decomposition-review.md` | 见第 5 节；均未开始/未执行。 |
| 商城订单边界 | `pages/mall_order_*`、`flows/mall_order_*`、`scripts/run_mall_order_flow.py` | `test_mall_order_address.py`（地址）；`test_mall_order_cart.py`（购物车）；`test_mall_order_checkout.py`（结算）；`test_mall_order_cli.py`（CLI/能力）；`test_mall_order_http.py`（HTTP）；`test_mall_order_safety.py`（安全边界）；`test_mall_order_types.py`（类型/金额） | `2026-07-22-mall-order-boundary-review.md`；`2026-07-28-mall-safe-decomposition-review.md` | 见第 5 节；均未开始/未执行。 |
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
| 登录与首页 | 未开始 | 未开始 | 未执行 | 未授权未执行 |
| 商城只读浏览 | 未开始 | 未开始 | 未执行 | 未授权未执行 |
| 商城订单边界 | 未开始 | 未开始 | 未执行 | 未授权未执行 |
| 外卖 | 未开始 | 未开始 | 未执行 | 未授权未执行 |
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

最新一次精确输出：`.....................                                                    [100%]`，`21 passed in 0.70s`（0 failed）。该结果确认当前已测行为，不反驳上述未覆盖的错误路径；也不构成 Appium、设备或网络兼容性结论。
