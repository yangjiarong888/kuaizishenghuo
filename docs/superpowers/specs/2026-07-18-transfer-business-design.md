# 同城跑腿业务自动化设计

## 目标

从首页金刚区进入“同城跑腿”，覆盖顶部菜单、取货信息、收货信息、订单提交、支付与订单结果校验。页面对象文件固定命名为 `pages/transfer_page.py`，类名为 `TransferPage`；独立运行入口为 `scripts/run_transfer_business.py`。

## 已验证真机链路

1. 首页金刚区点击“同城跑腿”，进入 `RunnerHomeActivity`。
2. 点击“服务说明”，进入 `RunnerServiceInfoActivity`，断言“同城跑腿服务说明”，点击返回后断言回到“同城跑腿”。
3. 点击“地址管理”，进入 Flutter 地址管理页，断言“地址管理”，返回跑腿首页。
4. 点击“我的订单”，进入 `RunnerOrderActivity`，断言“跑腿订单”，返回跑腿首页。
5. 取货信息从已有地址中选择安全可用的地址，断言联系人、地址、门牌号和手机号已回填。
6. 点击“下一步”进入收货信息；选择已有收货地址，并选择首个可用送达时间。
7. 点击“下一步”进入订单确认页，断言取货、收货、时间、金额和“提交”按钮。
8. 只有显式启用真实提交时才点击“提交”，进入在线支付页。
9. 可选执行 Maya 支付入口检查：选择 Maya、进入登录页并返回在线支付页。Maya 账号和密码只从环境变量读取。
10. 选择余额支付，点击“确认支付”，输入支付密码并确定。支付密码只从环境变量读取。
11. 断言进入订单详情且状态不再是“待付款”；本次真机验证结果为“待接单”。

## 结构

### `pages/transfer_page.py`

封装所有跑腿页面定位器、等待、点击、返回、地址选择、时间选择、提交与支付动作。定位优先级为：

1. `resource-id`
2. 精确文本或 content-desc
3. 已验证的相对结构
4. 仅首页金刚区允许使用屏幕比例坐标兜底

页面对象提供小粒度动作以及一个可组合的完整业务方法。每次跨页面操作后必须通过 Activity、标题或关键控件断言落地页面。

### `scripts/run_transfer_business.py`

提供可直接运行的命令行入口。默认只执行无副作用检查并走到提交前；真实订单和真实支付必须显式开启。

计划参数：

- `--action menus`：验证服务说明、地址管理、我的订单并返回。
- `--action order`：填写取货/收货信息并走到确认页。
- `--action full`：菜单检查加完整下单链路。
- `--submit-order`：允许创建真实跑腿订单。
- `--payment-method balance|maya`：选择支付方式。
- `--exercise-maya-return`：进入 Maya 登录页后返回，再改用指定支付方式。
- `--quit-driver`：结束后关闭 Appium 会话。

敏感信息通过 `TRANSFER_MAYA_ACCOUNT`、`TRANSFER_MAYA_PASSWORD`、`TRANSFER_PAY_PASSWORD` 环境变量提供，任何日志均不得打印其值。

### 首页接入

在 `pages/Home.py` 的金刚区业务映射中增加“同城跑腿”和“跑腿”到 `transfer`，业务分发时调用 `TransferPage`。综合首页测试默认只运行无真实提交的安全检查，避免重复创建订单。

## 关键真机定位器

- 服务说明：`com.bs.feifubao:id/tv_menu_service_info`
- 地址管理：`com.bs.feifubao:id/tv_menu_address_manage`
- 我的订单：`com.bs.feifubao:id/tv_menu_order`
- 取货地址选择：`com.bs.feifubao:id/tv_select_get_address`
- 取货联系人：`com.bs.feifubao:id/et_get_user`
- 取货地址：`com.bs.feifubao:id/tv_get_address`
- 取货门牌号：`com.bs.feifubao:id/et_get_address_detail`
- 取货手机号：`com.bs.feifubao:id/et_get_phone`
- 收货地址选择：`com.bs.feifubao:id/tv_select_receive_address`
- 收货时间：`com.bs.feifubao:id/tv_receive_time`
- 收货联系人：`com.bs.feifubao:id/et_receive_user`
- 收货地址：`com.bs.feifubao:id/tv_receive_address`
- 收货门牌号：`com.bs.feifubao:id/et_receive_address_detail`
- 收货手机号：`com.bs.feifubao:id/et_receive_phone`
- 上一步：`com.bs.feifubao:id/tv_prev`
- 下一步：`com.bs.feifubao:id/tv_next`
- 提交订单：`com.bs.feifubao:id/settlement`
- 支付方式文本：`com.bs.feifubao:id/tv_type`
- 确认支付：`com.bs.feifubao:id/btn_pay`
- 支付密码确认：`com.bs.feifubao:id/btn_comfirm`

## 错误处理与安全边界

- 任一页面断言失败立即终止当前业务，输出当前 Activity 和缺失标记。
- 找不到已有地址时不新增、不删除地址，而是明确失败。
- 找不到可用时间时不提交订单。
- 未传 `--submit-order` 时绝不点击“提交”。
- 未提供支付密码时停在支付页并明确报错。
- 不自动取消已成功支付的订单，不自动操作骑手接单后的状态。
- Maya 登录和余额支付密码不得写入源代码、配置、测试数据或日志。

## 测试与验收

先用替身驱动编写失败测试，覆盖：定位器调用、页面返回、已有地址选择、时间选择、真实提交开关、支付方式选择、支付密码缺失保护及状态断言。实现后运行单元测试，再在真机上执行：

1. 无副作用菜单回归。
2. 到提交前的订单流程。
3. 显式授权后的真实提交与余额支付。
4. 从“我的订单”确认最新订单状态不是“待付款”。

验收标准是脚本可从首页金刚区独立运行，所有跳转都有断言，默认不会产生订单，显式真实运行能够完成支付并进入有效订单详情状态。
