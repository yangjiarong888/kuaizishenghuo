# 全业务自动化审查：基线、清单与证据矩阵

日期：2026-07-29
范围：`commons/`、`pages/`、`flows/`、`scripts/` 中的生产 Python 文件，以及 `testcases/test_*.py`。这是全量审查的清单、证据矩阵和最终结论文档；Task 1–10 已完成。

## 1. 当前审查基线

| 字段 | 值 |
| --- | --- |
| 分支 | `codex/mall-readonly-decomposition` |
| 审查 SHA | `c9bdb69596202d425935cc4dc5fe855e483fa582`（Task 10 收口基线） |
| 审查时工作区状态 | `?? logs/` |
| 运行时未跟踪目录 | `logs/` 是唯一预期的未跟踪运行时目录；不加入提交。 |
| 本报告的审查状态 | Task 1–10 已完成；仓库级结论为“条件性通过，仅限非真机离线门”。 |

Task 1 的基线盘点、指标更正与独立复审已经完成；Task 2–10 完成了各域审查、跨域去重、全量离线门与最终收口。计划文件中的未勾选 checkbox 是执行模板，不是权威进度记录，也不应据此推断任务未完成；本报告的状态、提交链和事实核对是 tracked 的最终进度依据，ignored SDD ledger 仅保留执行过程。

Task 10 收口基线的最近十个提交：

```text
c9bdb69 docs: record full offline audit gate
d9f8c7f docs: audit cross-domain security and coverage
c95a7b4 docs: reconcile audit progress status
6d8ac97 docs: audit transfer charge shipping domains
783c75e docs: correct takeout preview boundary
c36bf28 docs: audit takeout boundaries
d454425 docs: audit mall order boundaries
d5b3dc7 docs: audit mall read-only domain
c54dd3b docs: audit login and home domain
1324555 docs: clarify foundation audit evidence
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
| 配送辅助 | `pages/shipping_page.py` | 首页海运映射调用的页面可达性骨架；Task 7 已确认它是活跃入口，但不覆盖完整海运业务。 |
| 包入口 | `pages/__init__.py`, `scripts/__init__.py` | 页面与脚本包入口。 |

文件计数：公共基础 8、登录与首页 20、商城只读浏览 21、商城订单边界 6、外卖 8、跑腿 2、充值 1、配送辅助 1、包入口 2；合计 **69**。

## 3. 业务域入口、测试与历史证据映射

| 域 | 主要入口/生产区 | 当前测试文件（映射的生产区） | 历史报告 | 当前审查层状态 |
| --- | --- | --- | --- | --- |
| 公共基础 | `commons/*.py` | `test_android_runtime.py`（Android runtime）；`test_config.py`（配置）；`test_diagnostics.py`（诊断）；`test_driver.py`（Driver）；`test_logger.py`（日志）；`test_waits.py`（等待） | `2026-07-22-foundation-review.md` | Task 2 已完成静态审查并执行聚焦离线测试；证据与发现见第 9 节。 |
| 登录与首页 | `pages/Home.py`、`pages/app_common.py`、`pages/login*`、`scripts/main.py`、`scripts/run_login.py`、`scripts/password_login_standalone.py`、`scripts/smoke_test.py` | `test_home.py`（首页）；`test_login.py`、`test_login_page_unit.py`（登录）；`test_main_cli.py`（主 CLI） | `2026-07-22-login-home-review.md` | Task 3 已完成静态审查；安全等价离线子集 `10 passed, 1 deselected`，原样设备用例未运行，证据见第 10 节。 |
| 商城只读浏览 | `pages/shop_*`、`flows/shop_home_*`、`scripts/run_shop_home.py`、`scripts/run_shop_business.py` | `test_shop_home_navigation.py`（商城导航/严格模式）；`test_shop_business_decomposition.py`（搜索/详情拆分门面） | `2026-07-28-mall-safe-decomposition-review.md`；`2026-07-28-shop-business-readonly-decomposition-review.md` | Task 4 已完成静态审查与聚焦离线验证；证据、缺陷和风险见第 11 节。 |
| 商城订单边界 | `pages/mall_order_*`、`flows/mall_order_*`、`scripts/run_mall_order_flow.py` | `test_mall_order_address.py`（地址）；`test_mall_order_cart.py`（购物车）；`test_mall_order_checkout.py`（结算）；`test_mall_order_cli.py`（CLI/能力）；`test_mall_order_http.py`（HTTP）；`test_mall_order_safety.py`（安全边界）；`test_mall_order_types.py`（类型/金额） | `2026-07-22-mall-order-boundary-review.md`；`2026-07-28-mall-safe-decomposition-review.md` | Task 5 已完成静态审查与全部匹配离线测试；证据、缺陷和风险见第 12 节。 |
| 外卖 | `pages/takeout_*`、`scripts/run_takeout_wangwang.py` | `test_takeout_cli.py`（CLI 组合）；`test_takeout_checkout_boundary.py`（结算/提交边界） | `2026-07-27-takeout-safe-checkout-review.md` | Task 6 已完成静态审查；按增量规则跳过聚焦 pytest，设备未执行，证据见第 13 节。 |
| 跑腿 | `pages/transfer_page.py`、`scripts/run_transfer_business.py` | `test_transfer_page.py`（页面）；`test_transfer_cli.py`（CLI） | `2026-07-27-transfer-charge-review.md` | Task 7 已完成静态审查；按增量规则跳过聚焦测试，证据、缺陷和风险见第 14 节。 |
| 充值 | `pages/charge_page.py` | `test_charge_page.py`（页面/提交边界） | `2026-07-27-transfer-charge-review.md` | Task 7 已完成静态审查；当前仅页面对象和离线测试，无生产调用方或独立安全 CLI，见第 14 节。 |
| 配送辅助 | `pages/shipping_page.py` | 未发现匹配 `test_shipping_*.py` 的文件；首页调用链见第 14 节。 | 无独立报告 | Task 7 已完成静态审查；确认为首页活跃入口骨架，不代表完整海运业务覆盖。 |

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
| 公共基础 | 已完成（含 3 个确认缺陷、3 个风险） | 当前全量通过（全局 `280 passed, 1 deselected`）；域内历史 `21 passed` | 未执行 | 未授权未执行 |
| 登录与首页 | 已完成（新增 1 个 P0、2 个 P1；2 个 P2 风险、1 个 P3 风险） | 当前全量通过（全局 `280 passed, 1 deselected`，真实认证 device 用例排除）；域内历史 `10 passed, 1 deselected` | 未执行 | 未授权未执行 |
| 商城只读浏览 | 已完成（4 个确认缺陷、3 个风险） | 当前全量通过（全局 `280 passed, 1 deselected`）；域内历史 `55 passed` | 未执行（仅核对 `a63e281` 保留证据） | 未授权未执行 |
| 商城订单边界 | 已完成（3 个 P0、2 个 P1；4 类风险） | 当前全量通过（全局 `280 passed, 1 deselected`）；域内历史 `91 passed` | 未执行 | 未授权未执行 |
| 外卖 | 已完成（2 个 P0、5 个 P1；3 类风险） | 当前全量通过（全局 `280 passed, 1 deselected`）；Task 6 聚焦测试曾按增量规则跳过 | 未执行 | 未授权未执行 |
| 跑腿 | 已完成（1 个 P0、2 个 P1；3 类风险/缺口） | 当前全量通过（全局 `280 passed, 1 deselected`）；Task 7 聚焦测试曾按增量规则跳过 | 未执行 | 未授权未执行 |
| 充值 | 已完成（2 个 P1；4 类风险/缺口；仅页面对象可达） | 当前全量通过（全局 `280 passed, 1 deselected`）；Task 7 聚焦测试曾按增量规则跳过 | 未执行 | 未授权未执行 |
| 配送辅助 | 已完成（2 个 P1；3 类风险/缺口；活跃入口骨架） | 全量命令通过，但无独立测试；不能据此声明配送辅助已被动态覆盖 | 未执行 | 未授权未执行 |

特别说明：Task 2–7 的域内静态审查、Task 8 的跨域去重和 Task 9 的当前树全量非真机回归均已完成；各域的聚焦测试运行或增量跳过证据见第 9–14 节，跨域结论见第 15 节，当前全量证据与真机资格见第 16 节。历史离线计数仅为审查线索，不与 Task 9 的当前全量结果合并。

## 6. 历史证据继承与增量复审边界

“当前相关差异”按历史提交到当前 SHA 的 `git diff --name-status` 检查，且只列与该报告的域或其共享依赖相关的生产/测试路径。报告提交与报告中描述的实现/设备证据提交不同处，均在同一单元格显式注明。

| 历史报告 | 对应提交/证据边界 | 当前相关差异 | 继承判断 | 必须复审的文件/范围 |
| --- | --- | --- | --- | --- |
| `2026-07-22-foundation-review.md` | 报告引入：`9dbb62c`；该报告自身说明当时无法取得 Git 基线，未声称设备回归。 | `commons/android_runtime.py` 已修改；并出现后续各域新入口。 | 仅作历史设计/测试背景，不能作当前兼容性结论；须增量复审。 | Task 2：全部 `commons/*.py`，重点 `commons/android_runtime.py` 及其新调用链。 |
| `2026-07-22-login-home-review.md` | `fe1353a`（登录/首页/跑腿生命周期实现与报告）。 | 域内主登录/首页文件自此无直接修改；共享 `commons/android_runtime.py` 已变更。 | 未修改域内代码的历史结论只作线索；Task 3 已完成当前静态审查并运行安全等价离线子集（`10 passed, 1 deselected`），设备未执行，共享依赖按 Task 2/3 边界复审。 | Task 3 已完成：`pages/Home.py`、`pages/app_common.py`、`pages/login*`、相关 CLI/测试及 Android runtime 影响，详见第 10 节。 |
| `2026-07-22-mall-order-boundary-review.md` | `c9d2bec`（商城订单边界报告/实现）。 | `scripts/run_mall_order_flow.py` 已修改并拆分；新增 `flows/mall_order_http.py`、`pages/mall_order_{cart,address,checkout}_mixin.py`；商城导航与 `commons/android_runtime.py` 亦变更。 | 原结论不能直接继承为当前全域结论，必须增量复审。 | Task 5：全部商城订单边界文件、`flows/mall_order_types.py`、相关 CLI/安全测试；Task 4 复审相邻导航链。 |
| `2026-07-27-takeout-safe-checkout-review.md` | 实现：`3a10b81`；报告：`62b665d`。 | 外卖域文件及 `scripts/run_takeout_wangwang.py` 在此后无直接修改；公共基础层有修改。 | 外卖域内未变代码的离线/安全结论可作为可继承历史证据；不等于当前离线或设备兼容结论。 | Task 6：全部外卖文件、CLI、共享基础依赖；历史设备范围仍不继承。 |
| `2026-07-27-transfer-charge-review.md` | 报告：`410b508`；引用实现：`fe1353a`（跑腿）与 `180b320`（充值）。 | `pages/transfer_page.py`、`scripts/run_transfer_business.py`、`pages/charge_page.py` 在此后无直接修改；共享 `commons/android_runtime.py` 已变更。 | 域内未变代码只作历史线索；Task 7 已完成当前静态审查，聚焦 pytest 按增量与日志边界跳过，设备未执行。历史报告已明确未重新运行设备，仍不能宣称兼容。 | Task 7 已完成：跑腿、充值、`pages/shipping_page.py` 及共享 runtime 调用边界，详见第 14 节。 |
| `2026-07-28-mall-safe-decomposition-review.md` | 报告提交：`d12b6d5`/`92221a7`；报告内保留设备运行是当时的商城导航命令。 | 之后新增商城搜索/详情 mixin，且 `pages/shop_home_page.py`、`scripts/run_mall_order_flow.py`、导航安全测试已修改。 | 历史只读设备运行仅说明当次路径；因后续代码变化，不能继承为当前商城浏览或订单相关的设备兼容性。 | Task 4/5：商城首页、业务门面、搜索/详情 mixin、订单 CLI、导航与安全测试。 |
| `2026-07-28-shop-business-readonly-decomposition-review.md` | 报告最终提交：`a831d75`；保留设备运行：`a63e281`；报告明确 `e88173b`、`4224d71` 仅离线验证。 | 自 `a63e281` 起，`pages/shop_home_page.py`、`scripts/run_mall_order_flow.py`、`test_mall_order_safety.py`、`test_shop_business_decomposition.py`、`test_shop_home_navigation.py` 已变化；自最终报告 `a831d75` 到当前生产代码无差异。 | 最终报告的离线历史可作为当前树的背景；**设备证据不得提升为当前版本兼容性**，因为它早于 `e88173b`/`4224d71`，且未重跑设备。 | Task 4：严格只读导航、`pages/shop_home_page.py`、搜索/详情门面；Task 5：`scripts/run_mall_order_flow.py` 与能力边界。 |

## 7. 已知证据缺口（非缺陷结论）

- Task 1–10 已完成基线盘点、域内审查、跨域去重、文件/行号级证据固化、当前树全量 non-device 回归与最终 QA 收口。
- Task 9 当前全量结果为 `280 passed, 1 deselected in 3.86s`；各域历史聚焦通过数继续只作背景，不能与该全量计数相加。
- 本任务未启动 Appium、未连接/操作设备，未执行真实写入或可能写入业务数据的命令。
- 商城只读保留设备证据仅适用于提交 `a63e281` 的当次导航路径；后续 `e88173b` 和 `4224d71` 是离线验证，故不得声称当前设备兼容。
- 外卖历史 `--checkout` 会加购/准备结算，可能留下购物车数据；它不属于严格无副作用验收路径。
- 跑腿、充值的历史报告没有当前 App 版本设备兼容性结论；Task 7 已确认充值没有生产调用方或独立安全 CLI，因此不可直接真机验收创建订单、保存/编辑账号。
- `pages/shipping_page.py` 没有独立 `test_shipping_*.py` 映射；Task 7 已确认它由首页金刚区活跃调用，但只是页面可达性骨架，不覆盖港口、货物、运费、运单或提交业务。
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
- 严格导航由 `run_navigation_verification()` 在 `try/finally` 内设置并恢复 `_mall_tab_coordinate_fallback_disabled`（`scripts/run_mall_order_flow.py:587-603`）。该 guard 同时覆盖 `ensure_mall_tab()` 的直接/末次坐标路径、结构点击失败后的 `mobile: clickGesture` 和恢复末端的坐标重试（`pages/shop_home_page.py:179-237,807-858,884-921`）；六个 Fake Driver 用例覆盖严格禁用与默认兼容回退（`testcases/test_shop_home_navigation.py:44-204`）。这项 guard 只对 mall-tab 坐标回退 fail closed，不保证详情后的恢复结果、证据产物或 CLI 退出码端到端 fail closed；该独立缺陷列为 MR-04。
- 搜索/详情拆分测试覆盖方法表面、搜索和开详情的失败短路、价格 parser 以及 facade 重导出（`testcases/test_shop_business_decomposition.py:15-219`）。本次聚焦结果为 55 项全部通过。

### 确认缺陷

| 优先级 | 位置 | 证据、影响与后续修复方向 |
| --- | --- | --- |
| P0 | `scripts/run_shop_home.py:43-94`; `flows/shop_home_flow.py:83-141`; `flows/shop_home_phases/kingkong_daily_baihuo.py:12-22`; `flows/shop_home_phases/home_add_cart_badge.py:12-26`; `pages/shop_mall_product_detail_page.py:324-357` | CLI 无参时 `--skip-phase=[]`，转换为 `skip=None` 后默认执行全部四阶段；调用链包含分类选规格加购、详情加购与收藏、末次首页加购，且没有任何 `--allow-cart-mutation`/收藏授权。仅执行默认命令即可污染购物车和收藏状态。默认改为只读阶段；所有加购/收藏阶段必须同时要求具名动作和显式单次 capability，Driver 创建前拒绝缺失授权。 |
| P0 | `scripts/run_shop_business.py:36-69,93-135`; `pages/shop_business_page.py:278-316,340-393,395-469,493-514` | CLI 无参默认 `action=full`、非空 IM 消息和 `share_target=复制链接`；调用链会复制分享、发送客服消息并点击“立即购买”进入确认订单页。`--submit-order` 只保护最终提交，不保护前三种有副作用动作，也没有独立分享/IM/结算授权。默认改为 `search` 或显式必填 action；复制、IM、立即购买/结算分别增加 capability，并在建 Driver 前验证组合。 |
| P1 | `pages/shop_home_page.py:179-188,230-236,785-805` | 默认兼容路径把 ADB/Appium 坐标命令无异常直接当成商城 Tab 成功；尽管 `_tap_mall_bottom_tab_by_coordinate()` 文档称会由主列表标识校验，代码未调用该校验，`ensure_mall_tab()` 立即返回 `True`。布局变化或错误前台页会产生假阳性，并让后续默认写入流程在错误页面继续。每次坐标点击后必须等待 `_is_mall_home_main_list_visible()`；失败时继续语义/结构路径并最终 fail closed，增加“手势成功但目标状态未出现”用例。 |
| P1 | `scripts/run_mall_order_flow.py:264-276,587-603,1150-1153`; `testcases/test_mall_order_safety.py:148-170,199-262` | `safe_back_to_mall()` 忽略五次返回动作和最终 `ensure_mall_tab()` 的失败结果，也不确认恢复后的商城目标状态；`run_navigation_verification()` 不校验证据产物或恢复结果便固定返回 `True`；`main()` 又忽略该返回值并固定退出 0。现有测试把 evidence/recovery stub 成无返回值且只覆盖成功 dispatch/guard 恢复，没有失败传播反例。因此详情读取成功后即使证据缺失或未回到商城，CLI 仍可假报成功。治理时让 recovery/navigation 返回并逐层传播布尔结果，恢复后确认商城目标状态，证据失败不可吞，CLI 失败必须非零退出，并增加 evidence/recovery/navigation 返回 False 与目标状态未出现的负向测试。 |

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

> **历史报告勘误（脱离本报告阅读会误导）：** `2026-07-28-shop-business-readonly-decomposition-review.md` 的“38 passed 覆盖 safety/navigation/decomposition”不准确。`46c5df3` 版本原报告明确记载“全部 `test_mall_order_*.py` + navigation + decomposition”为 **139 passed**；`a831d75` 在未保留命令/控制台文本、且同一提交还新增一个 decomposition 用例时，将数字改为 **38 passed**。`a831d75` 中两份 navigation/decomposition 文件与当前完全相同，而本次仅这两份就收集并通过 **55** 项，故 38 不可能代表所称 navigation/decomposition 全集，更不能代表再含 safety 的集合。历史文件按计划保留不改，38 只能视为命令无法复原的历史子集数字；历史报告若被单独引用仍会误导，这是待治理的文档遗留，引用时必须同时链接本勘误。

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

两份指定测试经静态核对仅使用 `RecordingCheckout`/Fake Manager 和 monkeypatch，不实例化真实 `DriverManager`、不连接设备或网络，不产生业务写入（`testcases/test_takeout_cli.py:37-86`; `testcases/test_takeout_checkout_boundary.py:6-139`）。测试只能证明桩化编排事件，不证明通用底栏 helper 在真实 UI 中的阶段语义、guard 前点击后仍处于 pre-order 状态或未创建订单。域内生产/测试自可绑定的 `62b665d` 后没有变化，历史证据可绑定 SHA，且本缺陷由 helper 标签集合、坐标 fallback、调用位置和缺失状态断言直接证实、不需要复现，因此按增量规则跳过聚焦 pytest；随后由第 16 节的 Task 9 新鲜全量 non-device 测试兜底。

本 Task 的静态结论不证明真实 UI 定位、配送时间、余额/COD、订单详情、取消接口、Appium/ADB、设备、网络或当前 App 版本兼容性。真实写入保持“未授权未执行”。

## 14. Task 7：跑腿、充值和配送辅助业务审查

### 范围、继承边界与调用关系

- 审查基线：`783c75e27eb62776dbab9f5003cd5d80419630be`。逐行复审 `pages/transfer_page.py`、`scripts/run_transfer_business.py`、`pages/charge_page.py`、`pages/shipping_page.py` 和三份指定测试。
- 历史报告 `410b508eee5045bf24418a2a9f96229c2a9943ab` 可精确绑定跑腿实现 `fe1353a69d6cb21b6488ada251a5a268a7159d94` 与充值实现 `180b320dd381562ee0363cc50e309d65456b165d`。当前跑腿/充值三个生产文件和三份测试的 Git blob 均与 `410b508` 完全一致；`pages/shipping_page.py` 与初始提交 `821ce45e98fe9108a196a41b7c239d34c227e548` 完全一致。
- `410b508..783c75e` 的相关共享差异只有 `commons/android_runtime.py`。跑腿 CLI 创建 Driver、配送入口复用首页 Driver，均受当前 runtime/Driver 影响；共享层变化、历史离线计数和历史设备材料不能提升为当前设备或 App 兼容性结论。充值当前没有生产 Driver/入口调用。
- 全仓 Python 调用搜索确认：`TransferPage` 由首页安全菜单检查和独立 CLI 调用（`pages/Home.py:18-19,640-642`; `scripts/run_transfer_business.py:15-17,45-78`）；`ChargePage` 除自身外只被 `testcases/test_charge_page.py` 引用，没有生产调用方或独立安全 CLI；`ShippingPage` 由首页导入、将“海运/海运物流”映射为 `shipping` 并在金刚区点击后调用（`pages/Home.py:18,64-72,632-642`），因此是**活跃入口骨架**，不是孤儿代码，也不等于完整业务覆盖。
- 本 Task 未启动 Appium、ADB、真机或网络，未运行跑腿/充值脚本，未提交订单、支付、登录 Maya、保存/编辑账号或发送消息；既有 `logs/` 未读取、修改或纳入提交。

### 动作—授权—目标状态矩阵

| 域/动作 | 当前入口与默认值 | 当前授权/确认边界 | 静态结论 |
| --- | --- | --- | --- |
| 跑腿菜单往返 | `--action menus`；首页只调用 `verify_menu_round_trips()` | 无写 capability；逐项核对目标 Activity/标题并返回 Runner 首页 | 首页映射只执行三个菜单往返，不进入订单链（`pages/transfer_page.py:54-58,122-131`; `pages/Home.py:640-642`）。 |
| 跑腿表单/结算预览 | `--action order|full`；默认 `submit_order=False` | 选择首个已保存取/收地址和首个配送时间，无独立 preview capability | 八个地址字段必须存在、非空且不等于占位文案；第二步后要求 `settlement` 存在。`submit_order(False)` 不点击该控件（`pages/transfer_page.py:59-75,133-190,250-273`）。这是表单动作，不是纯页面只读。 |
| 跑腿创建订单 | `--submit-order` | 只有动作布尔值；无独立 order-creation capability、金额快照或最大实付 | 点击 `settlement` 后只要求 `PayActivity` 和“在线支付”，随后必然进入所选支付分支（`scripts/run_transfer_business.py:22-33,61-78`; `pages/transfer_page.py:181-190,270-285`）。创建与支付授权未分开。 |
| 跑腿余额支付 | `--submit-order --payment-method balance`，默认支付方式 | 密码来自 `TRANSFER_PAY_PASSWORD`；无独立 payment capability | 自动选余额、点支付、输入密码并确认；结果只核对订单详情和宽泛非待付款状态，未绑定订单号、金额或表单快照（`pages/transfer_page.py:192-211,239-248,267-280`）。 |
| 跑腿 Maya 登录/返回 | `--payment-method maya` 或 `--exercise-maya-return` | 账号/密码来自 `TRANSFER_MAYA_*`；无独立第三方认证/支付 capability | 点击 Maya 登录后最多三次返回，只要回到 `PayActivity` 就成功；没有 Maya 支付结果、订单身份或订单状态确认（`pages/transfer_page.py:213-237,262-285`）。 |
| 充值表单与保存账号开关 | 直接调用 `ChargePage`；无生产入口/CLI | 供应商 allowlist、必填字段集合、图片数量和 toggle 状态；无 action/capability 层 | `set_save_account()` 读取并等待控件状态；`create_order(False)` 校验后不点击创建按钮（`pages/charge_page.py:243-332,362-384`）。仅为页面对象静态边界。 |
| 充值创建订单 | `create_order(submit=True)` | 只有方法布尔值；无生产调用方、安全 CLI、金额上限或二次 capability | 页面对象会点击 `CREATE_ORDER_ID`；点击后没有订单号、金额或明确目标状态断言（`pages/charge_page.py:369-384`）。当前可达性限于直接调用页面对象，不能描述为现有生产 CLI 可达。 |
| 充值账号编辑/复制/删除 | 直接调用 `manage_saved_account()` / `edit_saved_account()` | 只有 action 字符串；无生产调用方、独立 capability 或结果确认 | helper 可点击复制/编辑/删除与保存，测试仅以 Fake Driver 覆盖点击序列（`pages/charge_page.py:386-429`; `testcases/test_charge_page.py:316-363`）。不可直接真机验收。 |
| 配送辅助可达性 | 首页金刚区点击“海运/海运物流”后自动调用 | 无独立 CLI；无业务 action/capability | `run_main_flow()` 只检查宽泛海运文案、固定等待 1 秒并返回；港口、货物、运费、运单和提交仍为 TODO（`pages/shipping_page.py:11-17,41-65`）。 |

### 已验证的正向行为

- 跑腿 CLI 默认 `action=full`、`submit_order=False`、`payment_method=balance`；页面默认 `run_order_flow(submit_order=False)`，在确认结算控件存在后直接返回，不点击创建订单（`scripts/run_transfer_business.py:22-33`; `pages/transfer_page.py:181-190,250-273`; `testcases/test_transfer_page.py:267-295,383-386`）。
- 跑腿页面对象在任何表单点击前校验支付方式及所需 Maya/余额凭据；CLI 只从三个 `TRANSFER_*` 环境变量读取凭据，运行日志只写动作布尔值和异常类型，不写环境值或异常消息（`pages/transfer_page.py:250-269`; `scripts/run_transfer_business.py:37-52,79-87`）。这不消除 Task 2 已确认的共享 logger/XML 脱敏缺口，也不是当前设备验证。
- 充值 `create_order(submit=False)` 对当前业务/供应商必填字段、拍照缴费图片和已启用的重复保存检查先 fail closed，且不点击创建订单；供应商和字段使用显式 allowlist（`pages/charge_page.py:64-96,243-283,346-384`）。生产文件未发现固定个人账号、手机号、支付密码或默认测试号。
- `ShippingPage` 有真实首页调用链，但文档和代码都明确它是“骨架版/占位”页面可达性检查；本审查不把该入口提升为海运业务流程覆盖。

### 确认缺陷

| 优先级 | 域与位置 | 证据、影响与修复方向 |
| --- | --- | --- |
| P0 | 跑腿：`scripts/run_transfer_business.py:22-33,45-78`; `pages/transfer_page.py:181-237,250-285` | 独立 CLI 的 `--submit-order` 同时授权创建订单及余额/Maya 支付路径；没有独立 order-creation/payment/Maya-auth capability，也没有有限正数最大实付。余额路径会自动输入密码确认，Maya 路径会输入第三方凭据并点击登录。拆分 form-preview、create-order、authenticate-Maya、pay-balance/pay-Maya 动作和一次性 capability；创建前核对订单快照与有限金额上限，无支付 capability 时停在创建后明确状态。 |
| P1 | 跑腿：`scripts/run_transfer_business.py:22-33,45-88`; `pages/transfer_page.py:260-269`; `testcases/test_transfer_cli.py:41-46,134-260` | CLI 没有 Driver 前语义校验：`menus` 可静默忽略提交/支付/Maya 参数；`payment-method=maya` 或 `exercise-maya-return` 在未提交时被忽略或在建 Driver 后才因缺凭据失败；提交缺凭据也在 Driver 创建后返回 `1`，不是无效组合要求的 `2`。增加纯 `validate_args()`，把所有孤立、冲突、缺 capability/凭据组合在 `DriverManager()` 前拒绝并补参数矩阵测试。 |
| P1 | 跑腿：`pages/transfer_page.py:213-237,274-285`; `testcases/test_transfer_page.py:389-405` | Maya helper 点击登录后主动后退，只要重新出现 `PayActivity` 就返回成功；测试也把“回到支付页”定义为成功。该状态既不是 Maya 支付成功，也不是本次订单已支付；CLI 可把未支付或认证失败报为成功。明确 action 是“仅认证往返”还是“支付”，分别断言 Maya 认证结果或本次订单号、金额和已支付状态。 |
| P1 | 充值（仅页面对象可达）：`pages/charge_page.py:255-283,362-384`; `testcases/test_charge_page.py:202-219,265-305` | “缴纳金额”只做非空字符串检查；负数、零、非数字、非有限值和任意大值都可进入 `filled_fields`，随后 `submit=True` 会点击创建订单。当前没有生产调用方/CLI，故不能称现有 CLI 可达，但直接复用该页面对象会缺少金额安全边界。使用 Decimal/最小货币单位、币种规则、有限正数范围和显式最大金额，提交前重新读取 UI 值核对。 |
| P1 | 充值（仅页面对象可达）：`pages/charge_page.py:369-384`; `testcases/test_charge_page.py:274-283` | `create_order(submit=True)` 只把创建按钮点击成功当作订单创建成功，没有等待订单号、金额、供应商/账号快照或明确成功/失败状态。调用方会得到假阳性；当前无生产调用降低了即时可达性。点击后必须等待并绑定本次表单的明确目标状态，失败 fail closed。 |
| P1 | 配送辅助：`pages/shipping_page.py:41-54`; `pages/Home.py:64-72,632-642` | 页面状态只用 `//*[contains(@text, "海运")]`；第二个“海运物流”条件还是前者子集。首页原入口或任何包含“海运”的残留文本即可让未跳转页面通过，没有 Activity、资源 ID 或多个独立标志。使用目的 Activity/URL、唯一资源 ID 与至少一个页面专属状态的组合等待，并增加“仍在首页”负向 Fake Driver 测试。 |
| P1 | 配送辅助：`pages/Home.py:607-649`; `pages/shipping_page.py:56-65` | 首页在调用业务骨架前已把点击记入 `successful_clicks`，随后忽略 `ShippingPage.run_main_flow()` 的返回值；即使可达性检查返回 `False`，总结仍报告该海运入口成功。只在业务返回和回首页均成功后记录；业务失败应保存脱敏证据并在结果中区分“入口点击”和“目的页确认”。 |

### 风险与覆盖缺口（非确认缺陷）

| 优先级 | 域与位置 | 风险依据与建议 |
| --- | --- | --- |
| P2 | 跑腿：`pages/transfer_page.py:102-179,192-211,239-248` | 地址必填只校验非空/非占位，未校验手机号格式、取收地址身份或表单快照；支付方式点击后未确认选中；余额结果用四个宽泛状态且未绑定订单号/金额。为每个阶段建立 typed snapshot，并逐步验证选择状态、订单身份、金额和最终支付状态。 |
| P2 | 跑腿测试：`testcases/test_transfer_page.py:302-379,389-432`; `testcases/test_transfer_cli.py:41-46,134-260` | 页面测试覆盖点击前凭据校验和宽泛结果，但 CLI 没有孤立/冲突/capability 参数矩阵，也没有“PayActivity 不是支付成功”的负向用例。补纯 parser/validator 测试和订单身份状态机测试。 |
| P3 | 跑腿与充值三个生产文件 | 当前共 831 物理行、0 个固定等待、18 个宽泛异常；宽泛异常会把元素/会话/状态故障统一压成 `False`。按 action/locator/state 分类错误并保留脱敏诊断；复杂度计数不是缺陷数量。 |
| P2 | 充值：`pages/charge_page.py:346-384`; `testcases/test_charge_page.py:286-291` | “重复账号”实际只比较供应商显示名，不读取当前账号值或已保存账号身份；测试也只覆盖同供应商。它可能误拒绝同供应商的不同账号，或无法证明真正重复账号被识别。先明确一供应商一账号还是账号值唯一规则，再用规范化 provider+account key 比较并补边界测试。 |
| P2 | 充值：`pages/charge_page.py:310-332,386-453` | 保存、编辑、复制、删除及记录删除都是可变更动作，但只有页面 helper，没有独立 action/capability、确认前后状态或生产编排；也没有“选择已保存账号进入表单”的方法/测试。按具体动作拆 capability，绑定账号身份并确认最终状态。 |
| P2 | 充值：`pages/charge_page.py:127-183,243-384` | 页面对象以内部 `filled_fields`/`selected_provider` 代表 UI 状态，输入后未回读字段，供应商点击后也未等待选中状态；静态证据不能证明 UI 拒绝输入或页面重载时不会使用陈旧状态。提交前从 UI 重建并核对完整快照。 |
| P2 | 充值入口与测试：`pages/charge_page.py:16-17`; `testcases/test_charge_page.py:1-423` | 全仓没有生产调用方或独立安全 CLI，只有 Fake Driver 页面测试；因此不可直接真机验收创建订单、保存/编辑账号，也没有当前设备定位证据。先建立默认无写入的入口，再为每个写动作增加显式 capability 和测试数据/清理计划。 |
| P2 | 配送辅助：`pages/shipping_page.py:11-17,56-65` | `run_main_flow()` 明确仍是 TODO，只证明宽泛页面文案；未覆盖港口、货物类型、运费、运单、提交或异常恢复。入口活跃不等于业务覆盖，应把覆盖状态保持为“骨架”。 |
| P2 | 配送辅助：`pages/shipping_page.py:23-39,41-65`; `pages/Home.py:632-649` | 只有超时返回值，无截图/XML/结构化失败原因；非 Timeout Driver 异常会传播，Home 又没有针对该调用的域内错误分类。接入共享脱敏诊断，区分 timeout/locator/session/state，并禁止把敏感表单写入证据。 |
| P3 | 配送辅助测试与实现 | 没有 `test_shipping_*.py` 或针对首页 shipping 分发的测试；实现 66 行、1 个固定等待、0 个宽泛异常。增加活跃分发、首页残留文案、业务失败不计成功、异常脱敏证据的 Fake Driver 测试；不以代码短小代替覆盖。 |

### 测试决策、日志边界与设备结论

按增量规则没有运行三份指定 pytest。跑腿/充值三个生产文件和三份测试自可绑定报告 `410b508` 后均无差异，本次确认发现都可由动作顺序、返回状态和缺失校验直接静态证实，无需复现；Shipping 没有匹配测试。指定集合中的 `testcases/test_transfer_cli.py` 还会导入已初始化文件日志的模块，并主动读取该文件（`scripts/run_transfer_business.py:15-19`; `testcases/test_transfer_cli.py:5-10,24-38`; `commons/logger.py:51-64,84-91`），原样运行会创建或追加 `logs/`，不满足本 Task 的“不修改 logs”限制。

因此本 Task 的 pytest 输出为“未运行；无输出”，随后由第 16 节的 Task 9 新鲜全量 non-device 回归兜底。历史报告中的 `36 passed`、`56 passed`、`157 passed, 1 deselected` 只属于 `410b508` 记录的当时离线证据，不是本次运行结果。

本 Task 不证明跑腿表单/支付、Maya、充值供应商/账号/金额、配送页面定位、Appium/ADB、设备、网络或当前 App 版本兼容性。跑腿/充值订单、支付、账号保存/编辑及其他真实写入保持“未授权未执行”；充值在独立安全 CLI 和逐动作 capability 建立前明确为“不可直接真机验收”。

## 15. Task 8：跨业务安全、数据污染、日志和覆盖缺口审查

### 基线、方法与计数边界

- 审查基线为 `c95a7b490724a159383f85897e0a49e8da153ada`。扫描范围是 69 个生产 Python 文件、24 个 `testcases/test_*.py`、`pytest.ini`和 `.gitignore`；根目录不存在 `.env.example`，故该项只能记为配置/示例缺口，不是生产凭据泄露证据。
- 只使用 `rg`、Git 只读命令和 Python AST 纯读取统计：扫描敏感命名/赋值、环境 fallback、CLI 默认值、长数字、6 位码、`allow_*`/动作授权、日志/异常/响应、screenshot/XML/page source、重复实现、全仓引用与测试函数表面。未读取 `logs/`，未运行 pytest、Appium、ADB、设备、网络或业务脚本。
- Task 2–7 原始计数保持不变。本节的“去重后主题数”为 **8**；“Task 8 新增确认生产缺陷”为 **0**。下表的确认项全部复用第 9–14 节，新扫描信号只按风险、数据/示例或覆盖缺口记录。

### 敏感默认值、日志与诊断分类

| 分类 | 扫描结果与精确证据 | 结论 |
| --- | --- | --- |
| 生产确认缺陷（复用） | logger 的空格分隔 secret 绕过与 XML 敏感片段绕过均见第 9 节 `commons/logger.py:15-18,36-48` 和 `commons/diagnostics.py:15-22,45-49,75-77`；商城地址原值与 mock 支付完整响应日志见第 12 节及 `pages/mall_order_address_mixin.py:592,662-668`、`pages/mall_order_checkout_mixin.py:802-819`。 | 不重复计数；共享 logger/XML 根因影响登录、首页、商城、外卖、跑腿和配送诊断。 |
| 生产风险/待确认 | `capture_failure()` 对 XML 调用 `sanitize_xml()`，但对 PNG 直接 `driver.save_screenshot()`（`commons/diagnostics.py:45-77`）；首页失败和商城导航会调用它（`pages/Home.py:780-815`; `scripts/run_mall_order_flow.py:587-603`）。静态证据证明截图没有像素级脱敏，但没有证明当时画面一定含凭据，故不升级为已发生泄露。多个域仍直接记录 `%s` 原始异常，例如 `scripts/run_mall_order_flow.py:718,1089,1189-1196`、`scripts/run_shop_home.py:99`和 `scripts/run_shop_business.py:141`；异常是否含敏感值需运行时证据。 | P1 诊断边界风险；截图应限定安全页面/遮罩敏感区，原始异常改为类型+白名单字段。 |
| 环境与 CLI 默认 | 登录、跑腿凭据及商城地址的环境 fallback 为空（`pages/login/data.py:10-38`; `scripts/run_transfer_business.py:37-41`; `scripts/run_mall_order_flow.py:101-105`）；未命中固定生产密码/token/手机号。未命中 `default=True` 的 CLI capability 或 `allow_*=True`；第 10–14 节已确认的问题是缺 capability、动作与 capability 聚合，而不是布尔默认真。 | 正向证据，不消除已有授权缺陷。`.env.example` 缺失使必需变量、敏感值不入库和安全默认无统一示例契约。 |
| 测试数据 | 10–13 位数字在生产文件命中 0；测试中有 5 个唯一长数字样例（`test_diagnostics.py:11,51`; `test_charge_page.py:130,218,321-322,348,406-410`）。6 位 `123456` 仅在 logger/diagnostics 脱敏测试（`test_logger.py:45-51`; `test_diagnostics.py:11,52`）；`legacy-default` 仅是外卖测试桩默认密码（`test_takeout_checkout_boundary.py:57-59,103-106`，第 13 节 P1）。 | 测试数据，不是生产泄露；legacy 密码仍应删除以防回流。 |
| 生产测试文案/数据污染 | 商城订单和外卖共同把 `DEFAULT_REMARK_TEXT = "test order"` 设为业务表单默认（`scripts/run_mall_order_flow.py:100,823-824`; `pages/takeout_checkout_mixin.py:34,2423-2487,2715-2773`; `scripts/run_takeout_wangwang.py:140-141`）。第 12 节确认商城会操作结算表单，第 13 节已将外卖默认备注和购物车/表单变更记入 P1。 | 确认“测试文案进入生产默认”，作为已有数据污染主题的跨域实例；不另计新生产缺陷，也不声称一定已持久化。 |
| 文档/示例与无害常量 | `.invalid` HTTP URL、logger 脱敏样例、充值 Fake Driver 号码/账号、定位器中“验证码/地址/账号”文案均没有生产凭据赋值或默认授权证据。 | 示例/测试/定位常量，禁止误报。 |

### 跨域去重主题与优先级

去重规则是“共享先决条件或相同失败机制为一个根因，域内实例保留”；不把同一个日志脱敏缺陷按受影响域数重复计数，也不把每个缺测试单元格计为生产故障。

| 主题 | 优先级 | 已确认的域内实例/章节 | 治理拆分 |
| --- | --- | --- | --- |
| T8-1 默认副作用与 capability 聚合 | P0 | 登录 device 用例默认可收集（第 10 节）；商城浏览默认加购/收藏/分享/IM/结算（第 11 节）；商城创建隐含支付（第 12 节）；外卖结算/提交/支付/取消聚合（第 13 节）；跑腿创建/余额支付/Maya 聚合（第 14 节）。 | 先建共享 action-capability 契约，再按 cart/address/create/pay/cancel/message/auth 拆一次性权能。 |
| T8-2 Driver 创建前的默认动作与参数语义 | P0 | 商城浏览无参即写入（第 11 节）；商城订单默认 `buy_now`和孤立子参数（第 12 节）；外卖 checkout-only 参数被静默忽略（第 13 节）；跑腿凭据/支付组合在 Driver 后才失败（第 14 节）。 | 共享纯 parser/validator 约束“显式 action—所属子参数—所需 capability”，无效组合统一在 Driver 前退出 2。 |
| T8-3 阶段、订单身份与目标状态未绑定 | P0/P1 | Home/商城坐标点击即成功（第 10–11 节）；商城 mock 支付任意 JSON/宽泛订单页即成功（第 12 节）；外卖旧订单取消入口可冒充手工支付（第 13 节）；跑腿 `PayActivity`、充值点击和配送宽文本假阳性（第 14 节）。 | 独立状态断言层；每步绑定 action、阶段、订单号、金额、商品/表单快照和明确最终状态。 |
| T8-4 日志、XML、screenshot 与原始异常的脱敏边界 | P1 | 第 9 节 logger/XML 确认缺陷；第 12 节地址/完整响应日志；本节确认 screenshot 未像素脱敏和多域原始异常的静态风险。 | 共享基础先修：结构化白名单日志、属性级 XML 改写、安全截图策略和敏感页面禁拍。 |
| T8-5 金额表示、有限上限与业务快照 | P1 | 商城 `NaN/Infinity`、float/币种/库存快照缺口（第 12 节）；外卖无最大实付与本次订单身份（第 13 节）；跑腿无金额快照、充值仅非空金额（第 14 节）。 | 共享 Decimal/最小货币单位 parser 先修，业务域再定义币种、范围和 snapshot schema。 |
| T8-6 坐标、ADB 与宽文本破坏性 fallback | P1 | OAuth/ADB 授权（第 10 节）；商城 Tab 坐标假阳性和领券风险（第 11 节）；外卖提交/配送/取消坐标与宽文本（第 13 节）；配送“海运”宽文本（第 14 节）。 | 只读导航与破坏性点击分层；后者未获具体 capability 时禁用坐标/ADB/宽文本。 |
| T8-7 测试文案、表单/购物车污染与清理 | P1 | 商城默认加购/收藏（第 11 节）；商城地址/备注（第 12 节）；外卖默认 `test order`、加菜、券、备注、配送时间（第 13 节）；跑腿首个已保存地址、充值账号管理（第 14 节）。 | 数据域单独治理：唯一命名、幂等 setup/cleanup、账号与订单身份绑定；没有可验证 cleanup 前不开放真实写入。 |
| T8-8 失败/冲突/安全边界与真机证据缺口 | P1 | 所有域均无当前真机证据；商城仅保留 `a63e281` 历史只读路径，且导航恢复/证据/CLI 失败未传播（第 11 节）。外卖/跑腿参数冲突、订单身份与失败矩阵不足；充值只有 Fake Driver；配送无独立测试（第 10–14 节）。 | 测试/证据治理；Task 9 当前树全量 non-device 结论见第 16 节，真机仅在默认无写入且逐动作授权后执行。 |

因此，去重后主题数为 **8**（P0 主导 3 项，P1 主导 5 项）；这个计数与第 9–14 节的域内原始缺陷/风险计数分开。

### 重复实现、孤儿与兼容入口

| 项目 | 全仓引用/调用链证据 | 判定 |
| --- | --- | --- |
| Driver lifecycle 双路实现 | 共享实现为 `commons/driver.py:38-88`，大多数 CLI 通过 `DriverManager()` 创建/关闭（例如 `scripts/run_mall_order_flow.py:1110,1194`）；`scripts/smoke_test.py:14-63,70-116` 两处直接 `webdriver.Remote()`/`quit()`，且活跃 `smoke_test()` 由 `scripts/main.py:9,39-43` 调用。 | 确认重复，且冒烟路径绕过共享 runtime/lifecycle；不是孤儿。 |
| ADB/坐标导航分散 | 共享 Activity/ADB 在 `commons/android_runtime.py:13-72`，商城 Tab 另有直接 ADB tap（`pages/shop_home_page.py:853-881`），登录 OAuth 另有两组 ADB tap（`pages/login/mixins/oauth_mixin.py:1432-1505`），外卖提交/取消则分布多组 `mobile: clickGesture`（第 13 节精确范围）。 | 确认重复 fallback 表面，但语义不同；不能因“重复”直接删除，应统一 capability/目标状态约束。 |
| 金额解析重复 | `flows/mall_order_types.py:35-70` 的 `parse_money()` 有商城订单生产/测试调用；`pages/shop_business_detail_mixin.py:174-204,402-409`、`pages/shop_mall_product_detail_page.py:171-192`和 `pages/takeout_checkout_mixin.py:1271-1313` 各自使用正则+`float`。 | 确认 4 个实现表面；都有生产调用，不是孤儿，合并前须保留币种/页面格式差异。 |
| 订单/支付状态重复 | 商城标志为 `pages/mall_order_checkout_mixin.py:55-60,752-840`，外卖以“取消订单”为支付/取消入口（`pages/takeout_checkout_mixin.py:2805-2822`; `pages/takeout_cancel_order_mixin.py:769-974`），跑腿使用 `PayActivity`/“订单详情”/非“待付款”（`pages/transfer_page.py:181-248`）。 | 确认跨域重复断言机制；当前为各域活跃链，不可直接删除。 |
| `ChargePage` | 全仓 Python 引用只命中定义 `pages/charge_page.py:16`和 `testcases/test_charge_page.py`；没有生产 import、CLI 或 Home 分发（第 14 节已确认）。 | 生产调用孤儿/只有 Fake Driver 测试；可能是待接入页面对象，“无调用方”不等于可删除。 |
| `test_with_dynamic_config()` | 全仓（排除 `logs/`、Git 内部和本计划 ledger）只命中 `scripts/smoke_test.py:70` 定义与 `scripts/smoke_test.py:122` 被注释的调用。 | 确认无直接生产/测试调用的 legacy 入口；仍保留手工 import/反射可能，不直接宣称可删除。 |
| `ShippingPage` | `pages/Home.py:18,64-72,632-642` 导入、映射并调用 `pages/shipping_page.py:11,56-65`。 | 活跃首页入口骨架，不是孤儿；TODO 不等于完整海运覆盖。 |
| `pages/login_page.py` | 是显式兼容重导出（`pages/login_page.py:1-8`）；`scripts/run_login.py:6`、`scripts/password_login_standalone.py:26`和 `testcases/test_login.py:8` 仍从该路径导入。 | 兼容包装有活跃调用方，不是孤儿，不应在未迁移调用方时删除。 |

### 公开动作覆盖矩阵

“有”只表示当前文件存在静态映射；“部分/缺失”是覆盖 finding，不是生产故障证明。截至 Task 8，历史数字、Task 2–7 当前聚焦证据和当时尚未运行的 Task 9 全量证据严格分开；随后全量结果见第 16 节。

| 域/主要公开动作 | 主路径测试 | 失败路径测试 | 参数冲突测试 | 安全边界测试 | 真机证据 |
| --- | --- | --- | --- | --- | --- |
| 公共基础：config/Driver/wait/diagnostics | 有：6 份单测，Task 2 聚焦 `21 passed` | 部分：Remote 创建失败、证据不可用、wait 超时；缺创建后失败/并发/quit 失败 | 缺失：未知 config override/空必需值 | 部分：只测 `key=value` 和部分 XML，缺空格 secret/敏感片段/截图 | 未执行 |
| 登录与首页：dispatch/密码/SMS/OAuth/Home | 部分：注入 Driver 和 dispatch，Task 3 `10 passed, 1 deselected` | 部分：缺 Home 目标/恢复失败、真实认证失败 | 部分：测显式 method，未覆盖发码/OAuth/破坏性授权矩阵 | 缺口：`device` 未默认排除，ADB/同意 fallback 无边界测试 | 未执行；真实改密用例已安全排除 |
| 商城只读：导航/搜索/分类/详情 | 有：导航+拆分 55 项聚焦通过 | 有：严格导航、搜索/开详情短路 | 缺失：两个 CLI 默认/动作冲突 | 缺失：只读 helper 写动作黑名单和领券负向 | 仅 `a63e281` 历史只读路径；当前未执行 |
| 商城订单：购物车/地址/结算/创建/支付/取消/消息/HTTP | 有：7 份测试、Task 5 `91 passed` | 部分：金额上限、订单号缺失、HTTP/JSON/状态失败 | 部分：既有 capability 矩阵；缺默认 `buy_now`、孤立子参数、`nan/inf` | 部分：导航/购物车/地址/创建边界；缺独立支付/网络 capability 和敏感日志 | 未执行 |
| 外卖：导航/加菜/结算/配送/提交/支付/取消 | 部分：两份 Fake 测试覆盖主编排 | 部分：手工支付超时；缺阶段控件、配送、订单身份和取消 fail-closed | 部分：只测 submit 依赖 checkout；checkout-only 子参数未测 | 缺口：无逐动作 capability/最大实付/坐标禁用边界 | 当前未执行；历史报告不提升为当前证据 |
| 跑腿：菜单/表单/创建/余额/Maya | 部分：菜单、表单、支付假 Driver 主路径 | 部分：占位地址、缺凭据、待付款拒绝 | 缺口：无 Driver 前孤立/冲突/capability 矩阵 | 部分：测日志不泄凭据；缺创建/支付/Maya 独立 capability、金额/订单身份 | 未执行 |
| 充值：充值/缴费/账号/记录/创建 | 有：36 个 Fake Driver 测试 | 部分：字段/照片/provider/toggle 失败；缺创建后业务状态 | 无生产 CLI，无法建立 CLI 冲突覆盖 | 缺口：金额边界、逐动作 capability、数据清理 | 未执行；无安全生产入口 |
| 配送辅助：首页海运可达性 | 缺失：无 `test_shipping_*.py`或 Home shipping 分发测试 | 缺失：无首页残留文案/业务返回 False/异常诊断负向 | 无业务 action/capability 表面 | 缺失：仅宽文本骨架，无提交边界 | 未执行 |

### P0/P1 修复顺序与后续治理计划

1. **P0，共享安全契约先行**：默认排除 device/真实认证；建立纯 `validate_args()` 与 action—capability 映射；在任何 Driver/网络/坐标动作前拒绝无 action、孤立参数、缺 capability 和非有限金额。
2. **P0，业务动作 capability 拆分**：按域分别拆分 cart/address/create/pay/cancel/message/OAuth/Maya；一个 capability 不再隐式授权下一阶段。
3. **P0/P1，状态断言层**：用 phase-specific control 和 typed snapshot 绑定 Activity/页面标识、订单号、商品/地址/表单、金额和最终状态；坐标或点击无异常不能代表成功。
4. **P1，共享基础治理**：修复 Driver 创建后泄漏，收敛冒烟直连 lifecycle；统一 Decimal/币种 parser；改用结构化脱敏日志、属性级 XML 清洗和安全截图策略。
5. **P1，数据污染与覆盖**：移除生产 `test order` 默认，为每个写动作建立唯一数据、身份绑定和可验证 cleanup；先补失败/冲突/安全边界 Fake 测试。Task 9 的当前树全量 non-device 回归已完成，见第 16 节。

### 限制与最终边界

- 本节是静态跨域审查；“缺失测试”、“无引用”、“原始异常可能含敏感值”和“截图未像素脱敏”均不表示已复现生产泄露或故障。
- 全仓文本引用搜索无法排除手工 import、反射、外部消费者或直接 CLI 调用；所以孤儿结论只说“仓内未见调用方”，不给出删除授权。
- 在本节执行时（Task 8）尚未运行 Task 9/10；随后完成的 Task 9 证据见第 16 节，最终收口见第 17–21 节。本节没有当前真机、Appium、ADB、网络、真实认证或业务写入结论，历史证据仍仅在第 6 节的绑定 SHA/路径内有效。

## 16. Task 9：全量离线回归、编译与安全真机资格门

### 当前树与完整命令

- 运行基线：`d9f8c7f9c226399466efc554909e6e76f825b9f5`。
- 本节只产生当前树的新鲜离线证据和逐域设备资格；未修改生产代码、测试或配置。
- `pytest` 允许自行创建或追加未跟踪 `logs/`；本 Task 未读取、手工修改、删除或暂存其中内容。

全量非真机回归的完整命令：

```powershell
& 'C:\Users\18718\Desktop\appium_project\venv\Scripts\python.exe' `
  -m pytest -m 'not device' -q
```

原始控制台摘要：

```text
........................................................................ [ 25%]
........................................................................ [ 51%]
........................................................................ [ 77%]
................................................................         [100%]
280 passed, 1 deselected in 3.86s
```

进程退出码为 `0`，失败数为 `0`。`1 deselected` 是被 `not device` 明确排除的设备用例；该结果不执行或证明真实认证和设备兼容性。

全部 Python 内存编译的完整命令：

```powershell
& 'C:\Users\18718\Desktop\appium_project\venv\Scripts\python.exe' -c `
  "from pathlib import Path; files=sorted(p for p in Path('.').rglob('*.py') if '__pycache__' not in p.parts); [compile(p.read_text(encoding='utf-8-sig'), str(p), 'exec') for p in files]; print(f'compiled={len(files)}')"
```

精确输出为 `compiled=96`，进程退出码为 `0`。该命令使用内存 `compile()`，没有用 `compileall` 或 `py_compile` 写入 `__pycache__`。

### 8 域真机资格矩阵

每域只选择一个允许值。这里的“入口”是被审查的候选入口，不表示已运行。

| 域 | 单一资格 | 候选入口 | 当前依据 | 禁止动作 | 重新开放条件 |
| --- | --- | --- | --- | --- | --- |
| 公共基础 | 无独立安全入口，禁止执行 | 共享 `DriverManager`、Android runtime、诊断与等待组件；无独立设备验收 CLI | Task 2 确认 Driver 创建后失败可能遗留 session，logger/XML 诊断存在敏感片段脱敏缺口；这些组件只能被业务入口间接触发 | 禁止为“验证基础层”而启动 Appium session、探测 ADB、启动 Activity 或采集真实页面诊断 | 建立只读、无业务导航的独立验收入口；修复 session 清理和诊断脱敏，并覆盖失败清理后再评估 |
| 登录与首页 | 静态审查发现门禁缺口，禁止执行 | `scripts/main.py`、`scripts/run_login.py`、`scripts/password_login_standalone.py`、`scripts/smoke_test.py` | Task 3 确认 device 改密用例可被默认收集、smoke 失败可报成功、Home 目标/恢复状态可假阳性；OAuth 还保留 ADB/“同意”授权 fallback | 禁止真实登录、短信/语音验证码、OAuth 授权、改密、客服消息、ADB 和宽泛同意点击 | 默认排除 device；按认证动作拆一次性授权；移除/显式授权 ADB fallback；补目标页与恢复状态 fail-closed 断言 |
| 商城只读 | 静态审查发现门禁缺口，禁止执行 | `python -m scripts.run_mall_order_flow --verify-navigation-only` | strict guard 只覆盖 mall-tab 的坐标/ADB fallback；搜索和详情路径仍含多处 `mobile: clickGesture` 坐标 fallback，且当前入口不传播证据/恢复失败或非零 CLI 退出，无法证明坐标/ADB fallback 已彻底关闭或端到端成功可信；`a63e281` 仅是历史单次设备证据 | 禁止加购、收藏、领券、复制分享、IM、结算、订单、支付、地址、取消，以及任何搜索/详情坐标 fallback | 用同一严格 guard 覆盖搜索、结果卡片、详情与回退的全部坐标/ADB 路径；传播 recovery/navigation 布尔结果、确认目标状态、令证据失败和 CLI 失败非零退出；增加只读 helper 写动作黑名单及负向测试后再申请 |
| 商城订单 | 静态审查发现门禁缺口，禁止执行 | `scripts/run_mall_order_flow.py` 的购物车、地址、结算、订单与异常流 | Task 5 确认创建 capability 隐含支付、断网异常流无订单/网络 capability 即尝试提交、`NaN/Infinity` 可绕过上限，默认 `buy_now` 和孤立参数还会创建 Driver | 禁止加购/删除购物车、选择/新增/编辑/复制地址、结算表单、创建/取消订单、支付、IM、网络切换和 HTTP 钩子 | 逐动作拆 capability；Driver 前拒绝无动作/孤立参数/非有限金额；绑定订单、金额和状态快照；异常流独立授权且验证网络恢复 |
| 外卖 | 静态审查发现门禁缺口，禁止执行 | `scripts/run_takeout_wangwang.py` | Task 6 确认 checkout guard 前的通用底栏 helper 可匹配提交/支付且有坐标 fallback；购物车、表单、创建、支付和取消授权聚合，订单身份未绑定 | 禁止加菜/购物车、券、备注、通知、配送时间、地址、提交/支付/取消、密码和任何破坏性坐标/宽文本 fallback | 拆分逐动作 capability 和有限金额上限；使用 phase-specific 控件；绑定本次订单身份；所有显式配送/取消条件 fail closed；未经授权彻底禁用坐标 fallback |
| 跑腿 | 无独立安全入口，禁止执行 | 仓库存在 `python -m scripts.run_transfer_business --action menus` CLI | `--action menus` 本身使用 ID/Activity 往返，但入口没有建立或校验 RunnerHome 初始状态的独立安全导航，也没有失败后的保证回退门禁；默认启动策略还可能把 App 带回 MainActivity | 禁止表单、已保存地址选择、创建订单、余额支付、支付密码、Maya 登录/支付；本 Task 也不运行菜单 CLI | 建立默认无写入的 RunnerHome 导航与初始状态断言；成功和每个失败分支都保证回退；Driver 前校验孤立/冲突参数并保持坐标/ADB fallback 关闭 |
| 充值 | 无独立安全入口，禁止执行 | 仅 `pages/charge_page.py` 页面对象和 Fake Driver 测试，无生产 CLI/调用方 | Task 7 确认无生产调用方或独立安全 CLI；金额仅非空校验，创建以点击成功当结果，保存账号等写动作无 capability/清理契约 | 禁止充值/缴费创建订单、保存/编辑/复制/删除账号、记录删除及任何真实账号/金额输入 | 先建立默认无写入的生产入口；为每个写动作增加 capability、有限金额/币种、页面回读、目标状态和可验证清理计划 |
| 配送辅助 | 静态审查发现门禁缺口，禁止执行 | Home 金刚区“海运/海运物流”映射到 `ShippingPage`；无独立 CLI | Task 7 确认仅为活跃骨架：宽文本可在首页残留时假阳性，Home 还忽略 `run_main_flow()` 的失败返回；无独立测试 | 禁止把点击入口当业务成功，禁止港口/货物/运费/运单/提交动作及坐标/宽文本破坏性 fallback | 增加独立只读入口、目的 Activity/唯一 ID/专属状态组合断言、Home 返回值传播、失败诊断和 Fake Driver 负向测试 |

没有域通过“可执行无副作用真机验证”闸；也没有域拥有可提升为当前版本证据的真机材料。因此未使用“已有当前版本证据，无需重复”和“需要用户对持久化动作单独授权”作为任何域的最终单一资格。持久化动作仍需单独授权，但现有静态门禁缺口必须先修，授权本身不能越过 fail-closed 要求。

### 设备决策、实际证据与限制

- 主控制器在收到离线结果和上述矩阵后明确同意本 Task 不执行设备命令。
- **本 Task 未执行设备命令**：没有运行 `adb`、Appium 状态/启动/重配置命令或任何业务脚本，也没有连接、点击或改变设备/App 状态。
- 未执行设备命令不是任务失败；原因是 8 个域均未达到“可执行无副作用真机验证”的完整安全门，而不是离线回归失败。
- 当前 `280 passed, 1 deselected` 与 `compiled=96` 只证明当前树已收集的非 device 测试和 Python 源码编译通过；不证明真实 UI 定位、Appium/ADB、设备、网络、认证或当前 App 版本兼容。
- 历史 `a63e281` 商城只读材料继续只绑定当次路径，不能升级为当前版本设备证据；Task 2–7 的历史聚焦计数也不能与本节 `280` 相加。
- `logs/` 保持未跟踪且不纳入提交；Task 10 的只读证据核对与最终结论见第 17–21 节。

## 17. Task 10：最终八域结论

本表只汇总第 9–16 节已经固化的证据，不把历史设备材料提升为当前版本证据，也不把“全量离线通过”改写成真机或写入通过。八域真机资格为 **0/8**。

| 域 | 静态结论 | 当前离线证据 | 真机资格 | 真实写入状态 | 当前阻塞项 | 重新开放条件 |
| --- | --- | --- | --- | --- | --- | --- |
| 公共基础 | 3 个确认 P1、3 个风险；Driver 清理和日志/XML 脱敏契约不完整（第 9 节） | Task 9 全量 `280 passed, 1 deselected`；Task 2 聚焦 `21 passed` 仅作域内证据 | 无独立安全入口，禁止执行 | 未授权未执行 | 创建后异常可能遗留 session；结构化日志/XML/screenshot 安全边界不足 | 建立无业务导航的只读验收入口；修复 session 生命周期与诊断脱敏并覆盖失败清理 |
| 登录/首页 | 1 个 P0、2 个 P1；另有 OAuth/ADB 与复杂度风险（第 10 节） | Task 9 全量通过但排除 device；Task 3 安全子集 `10 passed, 1 deselected` | 静态审查发现门禁缺口，禁止执行 | 未授权未执行；真实登录、发码、OAuth、改密均未执行 | device 用例默认可收集；smoke/Home 可假阳性；授权 fallback 无独立能力门 | 默认排除 device；按认证动作拆 capability；目标页/恢复状态 fail closed；移除或单独授权 ADB |
| 商城只读 | 2 个 P0、2 个 P1；默认 CLI 可写入，坐标及导航收口可假阳性（第 11 节） | Task 9 全量通过；Task 4 聚焦 `55 passed`；`a63e281` 仅为历史单次只读路径 | 静态审查发现门禁缺口，禁止执行 | 未授权未执行；本次未加购、收藏、分享/IM 或结算 | 默认副作用；strict guard 未覆盖搜索/详情全部坐标/ADB fallback，且不保证恢复、证据与 CLI 退出状态；只读 helper 黑名单缺失 | 默认仅只读；逐动作 capability；strict guard 覆盖完整链；传播布尔结果并确认目标状态；证据失败不可吞、CLI 失败非零退出；补负向与写动作黑名单测试 |
| 商城订单 | 3 个 P0、2 个 P1；创建/支付、网络异常流、金额与状态边界失守（第 12 节） | Task 9 全量通过；Task 5 七文件聚焦 `91 passed` | 静态审查发现门禁缺口，禁止执行 | 未授权未执行；购物车、地址、订单、支付、取消、消息和网络切换均未执行 | 创建授权隐含支付；异常流可无授权提交；非有限金额绕过；默认动作/状态假阳性 | 逐动作 capability；Driver 前拒绝孤立参数/非有限金额；绑定订单、金额、商品和最终状态；异常流独立授权 |
| 外卖 | 2 个 P0、5 个 P1；预览、提交、支付、取消阶段和订单身份未隔离（第 13 节） | Task 9 全量通过；Task 6 聚焦测试按增量规则跳过，不记为聚焦通过 | 静态审查发现门禁缺口，禁止执行 | 未授权未执行；购物车、表单、订单、支付、取消和密码均未执行 | guard 前通用破坏性 helper；能力聚合；配送/取消 fail-open；测试桩含 legacy 默认密码 | phase-specific 控件；逐动作 capability 与有限金额；绑定本次订单；显式条件全部 fail closed；删除测试默认密码 |
| 跑腿 | 1 个 P0、2 个 P1；创建/支付/Maya 聚合且 CLI 缺 Driver 前校验（第 14 节） | Task 9 全量通过；Task 7 聚焦测试按增量和日志边界跳过 | 无独立安全入口，禁止执行 | 未授权未执行；表单、已保存地址、订单、余额/Maya 均未执行 | RunnerHome 初始/回退门不足；创建和支付未拆；`PayActivity` 可假成功 | 建立默认无写入入口与回退保证；纯 validator；拆创建/认证/支付 capability；订单与金额状态绑定 |
| 充值 | 2 个 P1，均为页面对象静态可达；无生产调用方/安全 CLI（第 14 节） | Task 9 全量通过；Task 7 聚焦测试跳过；现有 Fake Driver 历史仅作背景 | 无独立安全入口，禁止执行 | 未授权未执行；订单和账号保存/编辑/复制/删除均未执行 | 金额只非空；点击即报创建成功；无入口、能力和清理契约 | 先建默认无写入入口；Decimal/币种/上限与 UI 回读；逐动作 capability；明确成功状态和可验证清理 |
| 配送辅助 | 2 个 P1；活跃首页入口骨架，不是完整海运业务（第 14 节） | Task 9 全量命令通过，但无独立测试，不能声明动态覆盖 | 静态审查发现门禁缺口，禁止执行 | 未授权未执行；港口、货物、运费、运单和提交均未执行 | 宽“海运”文本可假阳性；Home 忽略业务返回；无独立负向测试 | 独立只读入口；Activity/唯一 ID/专属状态组合；传播失败并补脱敏诊断和 Fake Driver 负向测试 |

## 18. 最终缺陷、风险与覆盖缺口清单

### 分类口径与复算

- **P0 确认缺陷**：默认路径、门禁或授权组合可触发未授权设备/业务副作用，或关键保护可被直接绕过，必须先于任何真机开放修复。
- **P1 确认缺陷**：可造成敏感数据泄露、业务状态假阳性、错误阶段/身份操作，或已证实的安全契约缺失；同样阻塞相关真机与写入开放。
- **P2 风险/覆盖缺口**：静态证据显示有现实失效可能，但没有足够证据证明已在生产路径复现；不得写成确认生产缺陷。
- **P3 风险/覆盖缺口**：复杂度、固定等待、宽异常、轻度校验或测试映射缺口；是治理信号，不是已复现故障。

逐项复算第 9–14 节的“确认缺陷”表，结果如下。风险表中的 P1/P2/P3 不进入确认缺陷计数；Task 8 的 8 个主题也不进入该计数。

| 原始域章节 | P0 | P1 | 小计 |
| --- | ---: | ---: | ---: |
| 第 9 节：公共基础 | 0 | 3 | 3 |
| 第 10 节：登录/首页 | 1 | 2 | 3 |
| 第 11 节：商城只读 | 2 | 2 | 4 |
| 第 12 节：商城订单 | 3 | 2 | 5 |
| 第 13 节：外卖 | 2 | 5 | 7 |
| 第 14 节：跑腿/充值/配送 | 1 | 6 | 7 |
| **合计** | **9** | **20** | **29** |

### 29 项确认缺陷索引

本索引只提供短标题和原始证据定位；完整影响、修复方向与风险边界仍以对应章节为准。

| ID | 级别 | 域 | 短标题 | 原始证据 |
| --- | --- | --- | --- | --- |
| F-01 | P1 | 公共基础 | Driver 创建后启动/隐式等待失败可遗留远端 session | 第 9 节，`commons/driver.py:50-64` |
| F-02 | P1 | 公共基础 | 空格分隔 password/code/token 绕过日志脱敏 | 第 9 节，`commons/logger.py:15-18,36-48` |
| F-03 | P1 | 公共基础 | XML 文本中的敏感片段绕过诊断清洗 | 第 9 节，`commons/diagnostics.py:15-22,45-49,75-77` |
| LH-01 | P0 | 登录/首页 | 默认 pytest 选择可收集真实设备改密流程 | 第 10 节，`pytest.ini:2-6`; `testcases/test_login.py:15-30` |
| LH-02 | P1 | 登录/首页 | smoke 异常返回 `None` 被调度器当成功 | 第 10 节，`scripts/smoke_test.py:20-66`; `scripts/main.py:38-45` |
| LH-03 | P1 | 登录/首页 | Home 未确认目标/恢复状态仍返回成功 | 第 10 节，`pages/Home.py:380-405,471-543` |
| MR-01 | P0 | 商城只读 | `run_shop_home` 默认执行加购/收藏且无 capability | 第 11 节，`scripts/run_shop_home.py:43-94`; `flows/shop_home_flow.py:83-141` |
| MR-02 | P0 | 商城只读 | `run_shop_business` 默认分享复制、IM 和进入结算 | 第 11 节，`scripts/run_shop_business.py:36-69,93-135` |
| MR-03 | P1 | 商城只读 | 坐标/ADB 点击无异常即被当成商城 Tab 成功 | 第 11 节，`pages/shop_home_page.py:179-188,230-236,785-805` |
| MR-04 | P1 | 商城只读 | 导航恢复/证据失败不传播且 CLI 固定退出成功 | 第 11 节，`scripts/run_mall_order_flow.py:264-276,587-603,1150-1153`; `testcases/test_mall_order_safety.py:148-170,199-262` |
| MO-01 | P0 | 商城订单 | 创建订单 capability 隐式授权支付 | 第 12 节，`scripts/run_mall_order_flow.py:896-925,1053-1061`; `pages/mall_order_checkout_mixin.py:735-870,1025-1027` |
| MO-02 | P0 | 商城订单 | 断网异常流无订单/网络 capability 仍尝试提交 | 第 12 节，`scripts/run_mall_order_flow.py:720-750,985,998-1081,1185-1186` |
| MO-03 | P0 | 商城订单 | `NaN/Infinity` 绕过最大实付保护 | 第 12 节，`scripts/run_mall_order_flow.py:912-915,1053-1061` |
| MO-04 | P1 | 商城订单 | 无参默认 `buy_now`，孤立子参数亦可创建 Driver | 第 12 节，`scripts/run_mall_order_flow.py:753-755,998-1081,1110,1169-1186` |
| MO-05 | P1 | 商城订单 | mock 任意 JSON/宽泛订单页可误报支付成功 | 第 12 节，`flows/mall_order_http.py:152-168`; `pages/mall_order_checkout_mixin.py:802-842` |
| TO-01 | P0 | 外卖 | checkout/submit/pay/cancel 授权聚合且 guard 前可点提交/支付 | 第 13 节，`scripts/run_takeout_wangwang.py:71-151,172-227`; `pages/takeout_checkout_mixin.py:1984-2055,2701-2823` |
| TO-02 | P0 | 外卖 | 宽“取消订单”可误报手工支付并取消未绑定订单 | 第 13 节，`pages/takeout_checkout_mixin.py:2693-2698,2805-2822` |
| TO-03 | P1 | 外卖 | checkout-only 孤立参数被静默忽略 | 第 13 节，`scripts/run_takeout_wangwang.py:83-151,172-184,200-227` |
| TO-04 | P1 | 外卖 | “结算预览”写购物车/表单并可能阶段漂移 | 第 13 节，`pages/takeout_checkout_mixin.py:1728-1804,1984-2055,2186-2239,2421-2491,2738-2804` |
| TO-05 | P1 | 外卖 | 配送弹层、hint 与序号选择 fail-open | 第 13 节，`pages/takeout_delivery_time_mixin.py:462-499,520-689` |
| TO-06 | P1 | 外卖 | 取消入口/结果未绑定订单且可 fail-open/假成功 | 第 13 节，`pages/takeout_cancel_order_mixin.py:842-1085` |
| TO-07 | P1 | 外卖测试安全 | 测试桩含固定默认支付密码 `legacy-default` | 第 13 节，`testcases/test_takeout_checkout_boundary.py:57-59,103-106`；仅测试缺陷，不是生产密码泄露 |
| TR-01 | P0 | 跑腿 | `--submit-order` 聚合创建、余额/Maya 认证和支付 | 第 14 节，`scripts/run_transfer_business.py:22-33,45-78`; `pages/transfer_page.py:181-237,250-285` |
| TR-02 | P1 | 跑腿 | CLI 缺 Driver 前语义/capability 校验 | 第 14 节，`scripts/run_transfer_business.py:22-33,45-88` |
| TR-03 | P1 | 跑腿 | 回到 `PayActivity` 被误当 Maya 成功 | 第 14 节，`pages/transfer_page.py:213-237,274-285` |
| CH-01 | P1 | 充值 | 缴纳金额仅非空校验，危险值可到提交 | 第 14 节，`pages/charge_page.py:255-283,362-384`；仅页面对象可达 |
| CH-02 | P1 | 充值 | 创建按钮点击成功即被当订单创建成功 | 第 14 节，`pages/charge_page.py:369-384`；仅页面对象可达 |
| SH-01 | P1 | 配送辅助 | 宽“海运”文本可把未跳转首页误报成功 | 第 14 节，`pages/shipping_page.py:41-54`; `pages/Home.py:64-72,632-642` |
| SH-02 | P1 | 配送辅助 | Home 先记成功并忽略业务骨架失败返回 | 第 14 节，`pages/Home.py:607-649`; `pages/shipping_page.py:56-65` |

### 与 Task 8 去重主题和风险表的边界

第 15 节 T8-1 至 T8-8 是 **8 个跨域根因主题**（3 个 P0 主导、5 个 P1 主导），用于规划共享治理；它们复用上述域内实例，新增确认生产缺陷为 0。终审补录的 MR-04 是此前漏记的独立 P1，不新增跨域主题。因此正确口径是“29 项域内确认缺陷，映射为 8 个去重根因主题”，不是 37 项。第 9–15 节所有 P1/P2/P3 风险、复杂度、覆盖缺口、无调用方和截图可能暴露等条目继续保持风险/缺口身份，不得改写为已复现生产缺陷。

## 19. 最终事实一致性核对

### 测试、编译和跳过事实

| 项目 | 最终核对值 | 边界 |
| --- | --- | --- |
| Task 9 全量非真机回归 | `280 passed, 1 deselected in 3.86s`，exit 0 | 当前树 `c9bdb69` 的 non-device 测试；不含真实认证/device |
| Task 9 内存编译 | `compiled=96`，exit 0 | 只证明 96 个 Python 文件可被内存 `compile()` |
| Task 2 聚焦 | `21 passed in 0.70s` | 公共基础六文件；不覆盖设备/Appium |
| Task 3 聚焦 | 文档原次 `10 passed, 1 deselected in 0.75s`；主控复核 `1.09s` | 原样集合因含 device 改密用例安全跳过；只运行 `-m 'not device'` |
| Task 4 聚焦 | `55 passed in 0.74s` | navigation + decomposition Fake Driver 集合 |
| Task 5 聚焦 | `91 passed in 1.06s`；实现者复核另为 `1.02s` | 7 个 `test_mall_order_*.py` 离线文件 |
| Task 6 聚焦 | 跳过，无本 Task 输出 | 域内文件自 `62b665d` 无变化、发现可静态确认；由 Task 9 新鲜 non-device 全量兜底 |
| Task 7 聚焦 | 跳过，无本 Task 输出 | 相关 blobs 无变化；`test_transfer_cli.py` 会写/读 `logs/`，Shipping 又无匹配测试；由 Task 9 兜底 |

### Task 2–9 提交链

| Task | 提交/范围 | 核对结论 |
| --- | --- | --- |
| 2 | `351dbf83a00e89010e37a5e7bc4c22ed7bcea8b1`、`1324555b9ba4d8f02218c70c4840da37ea6b5d8c` | 公共基础审查及证据措辞更正 |
| 3 | `c54dd3b0edec47b98d76f84a5d6b5fac7362d806` | 登录与首页审查 |
| 4 | `d5b3dc79e7063d9942f17346742305bbe4b96494` | 商城只读审查 |
| 5 | `d45442576edef7a3cddd00edf021f4fa4dd466cf` | 商城订单边界审查 |
| 6 | `c36bf289a82e93b9e48befdba9f603de3bf63f13`、`783c75e27eb62776dbab9f5003cd5d80419630be` | 外卖审查及 preview 边界更正 |
| 7 | `6d8ac974008c793a571df49b1ffc8659d04b10cc`、`c95a7b490724a159383f85897e0a49e8da153ada` | 跑腿/充值/配送审查及全局进度更正 |
| 8 | `d9f8c7f9c226399466efc554909e6e76f825b9f5` | 跨域安全、覆盖和 8 主题去重 |
| 9 | `c9bdb69596202d425935cc4dc5fe855e483fa582` | 当前树全量离线、编译及 0/8 真机资格门 |

历史边界复核无变化：`a63e281ff8e9c59069ee0f27be5cd4c8a9405955` 只绑定当次商城严格只读真机导航；`e88173bb08a46ab53f23833d94267ec303b61056` 和 `4224d7138eaddc3152855cf85ff434ddae8d301e` 只有离线验证，没有后续真机重跑。历史“38 passed 覆盖 safety/navigation/decomposition”不准确；当前可复核的对应聚焦事实仍是第 11 节的 55 项与第 12 节的 91 项。历史文件按计划保留不回写，但脱离本最终报告阅读会误导，作为文档治理遗留；任何后续引用必须同时附第 11 节的醒目勘误。

### 三份 retained evidence 只读核对

Task 10 仅对下列三个精确路径执行存在性和 SHA-256 核对，没有读取其他 `logs/` 内容。三份均存在，哈希与第 11 节记录一致。

| 路径 | 存在 | SHA-256 |
| --- | --- | --- |
| `logs/20260728_145117_683760_mall_navigation_verification.png` | 是 | `15F8E94C8060BE78E997CB660E3DA12E13BB3E5E05C5291695690E15551A7C2C` |
| `logs/20260728_145117_683760_mall_navigation_verification.xml` | 是 | `E9C1480634A307FF174635512954AB95C513EC3811C2050106CFE2DDEC74312F` |
| `logs/chopsticklife_20260728_144928.log` | 是 | `A4F437934BB5EF30D4FA577E872912D76C637CA5A340212FF66F5A01E661DA61` |

这些文件仍只证明 `a63e281` 的一次历史只读路径；存在与哈希一致不构成当前设备/App/网络兼容性证明。

## 20. 分批治理计划

治理按共享依赖和业务边界拆分，不做跨域机械批量替换。每一批都必须独立评审、独立验收；下一批不得借前一批 capability 扩权。

| 批次 | 前置依赖 | 目标 | 禁止混入项 | 验收证据 | 持久化动作用户授权 |
| --- | --- | --- | --- | --- | --- |
| G0 共享基础 | 无，最先执行 | 修 Driver 生命周期；结构化白名单日志、属性级 XML 与安全截图；统一纯 validator/capability 契约；建立 Decimal/最小货币单位和 typed 状态快照 | 不改任何具体域的业务默认、定位器或订单编排 | 失败清理、脱敏反例、validator 矩阵、金额 parser/snapshot 单测；全量 non-device 与内存编译 | 修复本身不需要；若验收采集真实页面/启动 session，须另获真机授权，且不得含写入 |
| G1 登录/首页 | G0 lifecycle、诊断和 validator | 默认排除 device；修 smoke/Home 目标状态；拆 SMS/语音/OAuth/改密能力；约束 ADB/同意 fallback | 不混商城、订单或通用批量 locator 替换 | parser/dispatch 冲突矩阵、Home 失败回退、provider 状态和敏感诊断单测 | 真实登录、发码、OAuth、改密均必须逐动作单独授权 |
| G2 商城浏览 | G0 validator/状态断言；G1 只需共享首页导航稳定 | 默认仅只读；strict guard 覆盖搜索/详情/回退全部坐标与 ADB；恢复/导航布尔结果逐层传播，证据失败不可吞且 CLI 失败非零退出；写 helper 黑名单 | 不混购物车、地址、订单、支付实现 | 两个 CLI 默认/冲突测试；只读调用黑名单；每步目标状态与失败回退；evidence/recovery/CLI 负向测试；离线全量 | 只读真机重开另批；加购/收藏/领券/分享/IM/结算各需单独授权 |
| G3 商城订单 | G0 capability、Decimal、snapshot；G2 安全导航 | 拆 cart/address/create/pay/cancel/message/network；有限金额；订单/商品/地址/状态绑定 | 不混外卖/跑腿订单状态机，不复用粗粒度 capability | Driver 前矩阵、`nan/inf`、HTTP schema、订单快照、失败短路与 cleanup 契约测试 | 任何购物车、地址、创建、支付、取消、消息、网络切换均逐动作授权 |
| G4 外卖 | G0 capability/Decimal/snapshot | phase-specific 控件；拆购物车/表单/创建/支付/取消；配送和取消 fail closed；删除测试默认密码 | 不混商城订单 helper 或坐标批量替换 | 阶段状态、订单身份、配送 hint/序号、取消失败、参数矩阵和密码黑名单测试 | 购物车、券/备注、配送、创建、支付、取消分别授权 |
| G5 跑腿 | G0 validator/snapshot | 建立 RunnerHome 安全入口；拆 preview/create/Maya-auth/pay；修 `PayActivity` 假成功 | 不混充值页面对象接入或首页配送 | Driver 前矩阵、初始/回退状态、金额/订单身份、余额/Maya 负向测试 | 地址选择、创建、密码、Maya 认证和支付分别授权 |
| G6 充值 | G0 Decimal/capability/snapshot | 建默认无写入口；金额/币种/上限和 UI 回读；逐动作账号能力；创建结果绑定 | 不混配送骨架或假定现有生产调用方 | Fake Driver 入口、金额边界、账号身份、创建状态、幂等清理测试 | 账号输入/保存/编辑/复制/删除、订单创建均分别授权 |
| G7 配送辅助 | G0 诊断/状态断言 | 独立只读入口；Activity/唯一 ID/专属状态；Home 传播业务返回 | 不实现港口/货物/运费/运单/提交等完整业务 | 首页残留文案、返回 False、异常诊断、成功回首页的 Fake Driver 测试 | 只读真机重开另批；任何未来提交动作需单独授权 |
| Q1 测试与数据清理 | G1–G7 各域相关修复完成 | 默认排除所有 device/破坏性标记；唯一测试数据、身份绑定、幂等 setup/cleanup；去除生产 `test order` 默认 | 不用清理脚本掩盖业务缺陷，不在单测中接触真实环境 | marker 收集证明、写动作黑名单、cleanup 幂等/失败恢复、全量 non-device | 任何真实数据 setup/cleanup 都需单独授权和明确目标 |
| Q2 真机资格重开 | G0、目标域批次与 Q1 全部验收 | 按域重新评审单一安全入口；先申请无副作用验证，再单独申请持久化动作 | 不把历史 evidence、离线通过或用户授权本身当安全门通过 | 新提交绑定的命令、控制台、脱敏截图/XML/log、设备/App/网络版本和回退状态 | 无副作用真机与每种持久化动作分别授权；未授权保持禁止 |

## 21. 仓库级 QA sign-off

最终状态：**CONDITIONAL / OFFLINE-ONLY（条件性通过，仅限非真机离线质量门）**。

| 决策面 | Sign-off | 精确边界 |
| --- | --- | --- |
| 当前非真机回归与编译 | **通过** | `c9bdb69` 上 `280 passed, 1 deselected in 3.86s`、`compiled=96`，均 exit 0；device 用例被排除 |
| 当前真机无副作用回归 | **不批准** | 0/8 域具备资格；3 域无独立安全入口，5 域存在静态门禁缺口 |
| 任何真实写入 | **不批准** | 29 项确认缺陷中含 9 个 P0、20 个 P1；购物车、账号、订单、支付、认证、消息、取消、网络变更等均未获授权且未执行 |
| 设备/App/网络兼容性 | **不包含** | Task 10 未运行 Appium、ADB、设备、网络或业务脚本；历史 `a63e281` 不代表当前版本 |

该 sign-off 不能表述为“全部通过”。它只批准把当前提交视为**非真机离线测试与源码编译门通过**；不批准当前版本的真机执行、真实认证、持久化业务动作或兼容性发布结论。重新开放必须按第 20 节逐批完成并重新评审，用户对持久化动作的授权是必要条件，但不能替代 fail-closed、状态绑定、数据清理和证据门。
