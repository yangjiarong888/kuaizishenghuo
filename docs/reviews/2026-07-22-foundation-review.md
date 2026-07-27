# 公共基础层审查与重构报告

## 清理与恢复

- 备份文件：`C:\Users\18718\Desktop\appium_project\venv\backups\20260722_before_refactor.zip`
- SHA-256：`06FE46405A203C83D13CE43D76BBC36BD31E50CB108E211EAD7D78A8FF6B629B`
- 清单条目：113 个文件，已通过独立解压和逐文件 SHA-256 比对。
- 已删除：父目录旧 `test.py`、`generate_pay_testcases_xlsx.py`、历史 robust 日志、5 个缓存或误建目录、78 份过期日志。
- 已保留：`pyvenv.cfg`、`logs/shipping_new_user_guide.png`。
- 恢复方法：将 ZIP 解压到临时目录，依据其中的 `manifest.csv` 选择性恢复原路径。

## 离线验证

- Python：3.11.9。
- pytest：112 passed，0 failed，1 deselected。
- 语法验证：72 个 Python 文件编译成功。
- 依赖验证：`No broken requirements found.`
- Appium：3.2.0，`http://127.0.0.1:4723/status` 返回 `ready: true`。
- 敏感信息扫描：源码、测试和文档中未匹配到硬编码的密码、验证码、支付密码或 token 赋值。

## 已治理风险

- 配置来源统一为类型化 `AppConfig`，运行时环境变量优先，显式参数最后覆盖。
- ADB 设备识别、Activity 解析和 App 启动策略集中到 `commons/android_runtime.py`。
- `DriverManager` 在缓存前完成启动配置，失败会清除会话，隐式等待统一为 0。
- 日志处理器具备幂等管理、UTF-8 输出和带键敏感值脱敏。
- 新增可确定性测试的条件等待与必需元素异常接口。
- 新增截图和 page source 独立采集，page source 写盘前执行脱敏。

## 遗留风险

- 固定等待：529 处，主要集中在商城、外卖和登录模块。
- 宽泛异常：741 处；后续必须区分可选元素缺失、页面状态失败和外部驱动边界异常。
- 超过 800 行的文件：10 个。
- 最大文件为 `scripts/run_mall_order_flow.py`（3097 行）、`pages/takeout_checkout_mixin.py`（2857 行）和 `pages/login/mixins/oauth_mixin.py`（2396 行）。
- 本阶段未执行真机回归；真机无副作用验证安排在各业务域完成后统一执行。
- 当前系统无法定位 Git，可写工作区但无法提交；本报告不声称存在提交记录。

## 下一阶段入口条件

- 离线测试必须持续保持零失败。
- 先处理登录与首页，将公共等待和失败诊断接口接入真实 Page/Flow。
- 每个业务域使用独立计划、独立回归和独立真机证据。
- 未经逐次明确授权，不执行下单、支付、发送验证码或业务数据增删改。
