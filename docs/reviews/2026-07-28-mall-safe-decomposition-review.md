# 商城安全拆分验证报告

日期：2026-07-28

## 结论

商城下单脚本已拆分为 HTTP、购物车、地址和结算边界，并通过离线回归、内存编译及一次严格只读的真机导航验证。

本次真机命令只进入商城、搜索“可乐”、读取商品详情证据并返回。没有授权或执行加购、删购物车、创建/取消订单、支付、地址写入或订单消息发送。正常页面访问可能仍由 App 自身产生浏览历史或分析事件，这不属于脚本可控制的业务数据写入。

## 离线验证

- 商城聚焦测试：`86 passed`
- 全量非真机测试：`219 passed, 1 deselected`
- Python 内存编译：`compiled=93`
- `scripts/run_mall_order_flow.py`：基线 `3077` 行，当前 `1193` 行
- 授权默认值扫描：未发现商城业务能力被固定为开启；唯一命中 `allow_slow_legacy_xpath=True` 是外卖页面的定位策略开关，不是业务写入授权

执行命令：

```powershell
$tests = @(Get-ChildItem testcases -Filter 'test_mall_order_*.py' |
    Select-Object -ExpandProperty FullName) +
    (Resolve-Path testcases\test_shop_home_navigation.py).Path
..\Scripts\python.exe -m pytest -q $tests
..\Scripts\python.exe -m pytest -m 'not device' -q
..\Scripts\python.exe -c "from pathlib import Path; files=sorted(p for p in Path('.').rglob('*.py') if '__pycache__' not in p.parts); [compile(p.read_text(encoding='utf-8-sig'), str(p), 'exec') for p in files]; print(f'compiled={len(files)}')"
```

## 真机验证

- 设备：`21091116AC`
- 序列号：`P7T4XC99CYAEYL4H`
- Appium：`3.2.0`，验证前 `ready: true`
- App 包：`com.bs.feifubao`
- 验证结束 Activity：`.activity.MainActivity`
- 飞行模式：`1`；Wi-Fi：`2`，验证期间未修改
- 退出码：`0`
- 用时：`171.5s`

执行命令：

```powershell
..\Scripts\python.exe scripts\run_mall_order_flow.py `
  --verify-navigation-only `
  --product-source search `
  --keyword "可乐" `
  --session mall_navigation_verify_final `
  --start-mode activate `
  --quit-driver
```

证据：

- 截图：`logs/20260728_115709_437509_mall_navigation_verification.png`
- 脱敏 XML：`logs/20260728_115709_437509_mall_navigation_verification.xml`
- 运行日志：`logs/chopsticklife_20260728_115504.log`
- 商品快照：`T可口可乐(经典美味)330ml`，单价 `33.0`

截图和 XML 均显示商品详情页。XML 中密码类属性已脱敏，未观察到手机号或验证码泄露。日志只包含导航、搜索、详情读取和返回动作；没有出现加购、提交订单、支付、地址增删改、订单消息或取消订单动作。运行结束后 Driver 正常关闭，前台回到主 Activity。

验证期间还修复了首页无弹窗时的慢查询：旧实现会重复 8 轮、共 88 次探测；现在页面源码明确不存在关闭控件时不再发元素查询，确实关闭一层弹窗后才继续探测下一层。回归测试覆盖了该行为。

## 未经真机验证的范围

本次结果不能推断以下能力兼容：

- 加入购物车、购物车删除和购物车结算
- 创建订单、支付以及支付密码人工输入
- 地址新增、编辑、复制或选择
- 订单取消和订单 IM
- 库存不足、断网等异常路径
- 优惠券、预约时间、取件码、通知方式和备注

支付密码不保存在代码或环境默认值中；将来如获授权进入真实支付边界，应由测试人员在真机上手动输入并确认结果。

## 后续真机能力授权

仅加购需要：

```text
--add-to-cart-only --allow-cart-mutation
```

立即购买并真实创建订单至少需要：

```text
--submit-order --allow-order-creation --max-payable <正数上限>
```

购物车下单还需要：

```text
--flow cart --allow-cart-mutation
```

其他持久化动作分别需要：

- 地址写入：`--allow-address-mutation` 加对应地址动作参数
- 取消本次创建的订单：`--cancel-created-order --allow-order-cancellation`
- 发送订单消息：`--send-order-im --allow-order-message`

每次真机执行这些能力前都必须获得新的、明确的单次授权。

## 残余风险基线

扫描范围为 `pages/`、`flows/` 和 `scripts/run_mall_order_flow.py`：

- 固定等待 `time.sleep(...)`：`522` 处
- 宽泛异常捕获：`719` 处
- 超过 800 行的 Python 文件：`11` 个

超过 800 行的文件：

| 行数 | 文件 |
| ---: | --- |
| 2823 | `pages/takeout_checkout_mixin.py` |
| 2486 | `pages/login/mixins/oauth_mixin.py` |
| 1395 | `pages/shop_business_page.py` |
| 1296 | `pages/shop_home_page.py` |
| 1193 | `scripts/run_mall_order_flow.py` |
| 1085 | `pages/takeout_page.py` |
| 1085 | `pages/takeout_cancel_order_mixin.py` |
| 1067 | `pages/mall_order_checkout_mixin.py` |
| 985 | `pages/login/mixins/find_click_mixin.py` |
| 910 | `pages/login/mixins/navigation_postlogin_mixin.py` |
| 873 | `pages/Home.py` |

这些数字是后续分业务域治理的规模基线，不表示每一处都是缺陷。本轮仅修复真机验证实际暴露的商城首页弹窗探测问题。
