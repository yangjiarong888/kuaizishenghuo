# 登录与首页审查及第一轮重构报告

## 已修复问题

- `scripts/main.py` 原先从 `testcases/test_login.py` 导入不存在的 `run_login_tests` 和 `test_specific_login_method`，导致生产入口无法导入。现已移除生产代码对测试模块的依赖。
- 新增 `scripts/run_login.py`，统一显式登录方式分发；未知方式直接拒绝，只有创建者负责关闭 Driver 会话。
- `scripts/main.py` 现在提供可测试的 `build_parser()` 与 `main(argv)`，登录相关模式必须显式传入 `--method`，避免默认触发多种第三方登录或验证码流程。
- `LoginPage` 支持注入 Driver，默认构造方式和原参数顺序保持兼容。
- `ChopsticksTester` 支持注入 Driver，并通过 `DriverManager` 获取和关闭自有会话；删除了首页内重复的 Remote 创建、冷启动和关闭实现。
- 首页失败截图已接入共享脱敏诊断，能够同时产生截图和脱敏 page source。

## 验证证据

- 离线测试：122 passed，0 failed，1 deselected。
- Python 内存编译：76 个文件成功。
- 导入检查：`scripts.main`、`scripts.run_login`、`ChopsticksTester`、`LoginPage` 全部成功。
- 兼容验证：跑腿 CLI 与首页分发测试保持通过。
- 真机测试仍按总设计留到业务域完成后的无副作用回归阶段。

## 剩余风险

- 登录与首页范围仍有 152 处固定等待、202 处宽泛异常。
- 超过 800 行的文件仍有 4 个：
  - `pages/login/mixins/oauth_mixin.py`：2396 行。
  - `pages/login/mixins/find_click_mixin.py`：951 行。
  - `pages/login/mixins/navigation_postlogin_mixin.py`：860 行。
  - `pages/Home.py`：840 行。
- 这些剩余项包含第三方 OAuth、Flutter 坐标兜底和设备断线恢复，不能无测试地机械替换。后续需要依据真机页面状态分别拆分。
- `scripts/smoke_test.py` 仍是旧式线性脚本，包含硬编码设备、固定等待和旧 Appium 调用；将在入口收口阶段单独替换。
- Git 仍不可用，本轮不声称已提交。

## 后续顺序

1. 商城：先拆分 3097 行订单入口并建立 Flow 离线测试。
2. 外卖：治理结算、配送时间和取消订单职责。
3. 跑腿与充值：复核安全开关、状态断言和敏感数据边界。
4. 登录 OAuth 与首页剩余大文件：结合真机证据继续小步拆分。
5. 统一执行真机无副作用回归。
