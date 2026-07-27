# 跑腿与充值域审查报告

## 审查结论

- 同城跑腿已经具备独立 `TransferPage`、CLI 入口、首页业务映射和离线测试。
- 跑腿默认 `submit_order=False`，未显式授权时只走到提交前，不点击订单提交。
- Maya 账号、Maya 密码和余额支付密码只从 `TRANSFER_*` 环境变量读取。
- 跑腿日志只记录异常类型，不记录环境变量值或异常消息中的敏感内容。
- 充值 `ChargePage.create_order(submit=False)` 默认只校验表单，不点击创建订单按钮。
- 充值保存账号、图片账单、供应商字段和记录管理已由现有页面对象测试覆盖。
- 本阶段没有执行真实跑腿订单、充值订单或支付。

## 验证证据

- 跑腿聚焦测试：`36 passed`。
- 充值聚焦测试：`56 passed`。
- 登录/首页与跑腿组合测试：`46 passed, 1 deselected`。
- 完整离线测试：`157 passed, 1 deselected`，零失败。
- Python 内存编译：`83` 个 `.py` 文件全部成功。
- 跑腿生产代码敏感赋值扫描：
  - 固定密码、token、API key：无命中；
  - 10 至 13 位固定长数字：无命中；
  - 凭据来源仅命中 `TRANSFER_MAYA_ACCOUNT`、`TRANSFER_MAYA_PASSWORD`、`TRANSFER_PAY_PASSWORD` 环境变量读取。
- 充值生产代码长数字与固定敏感值扫描：无命中。

## 安全边界

### 跑腿

- `submit_order(False)` 在确认存在提交按钮后直接返回，不点击按钮。
- 余额支付缺少 `TRANSFER_PAY_PASSWORD` 时明确失败。
- Maya 登录缺少账号或密码时明确失败。
- CLI 默认不带 `--submit-order`。
- 当前真实支付仍属于显式破坏性验证，最终默认真机回归不会执行。

### 充值

- `create_order()` 的默认参数为 `submit=False`。
- 缺少必填字段、图片账单没有图片、保存账号重复时均在创建订单前失败。
- 只有 `create_order(submit=True)` 才点击 `CREATE_ORDER_ID`。

## 剩余风险

- 本次统计的 `pages/transfer_page.py`、`scripts/run_transfer_business.py`、`pages/charge_page.py` 共 `0` 处固定 `time.sleep`，但仍有 `18` 处宽泛异常捕获。
- 文件规模：
  - `pages/transfer_page.py`：`286` 行；
  - `scripts/run_transfer_business.py`：`92` 行；
  - `pages/charge_page.py`：`450` 行。
- 宽泛异常主要位于 Driver/元素访问边界；后续应逐步区分元素不存在、页面超时和会话故障。
- 充值目前只有页面对象和离线测试，没有独立安全 CLI；真机验证入口与账号/供应商测试数据仍需在最终设备计划中明确。
- 跑腿设计文档包含历史真机链路描述，但本轮没有重新执行设备验证，因此本报告不据此声明当前 App 版本兼容。

## Git 记录

- 充值页面对象已有提交：`180b320 feat: add charge payment page object`。
- 登录/首页生命周期与跑腿接入提交：`fe1353a refactor: stabilize login home and transfer flows`。

## 最终真机策略

- 跑腿先执行无副作用菜单回归，不带 `--submit-order`：

```powershell
& '..\Scripts\python.exe' scripts\run_transfer_business.py `
  --action menus `
  --session transfer_menus `
  --quit-driver
```

- 充值真机验证只检查入口、页面字段和默认 `submit=False` 行为；在独立安全入口完成前，不执行创建订单。
