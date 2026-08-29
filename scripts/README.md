# 业务脚本执行命令

以下命令均在项目根目录 `kuaizishenghuo` 中执行。运行真机业务前，请先启动 Appium、连接设备并按业务要求登录。每个入口也可执行 `python scripts/脚本名.py --help` 查看实时参数。

## 搜索业务

App 首页九关键词搜索矩阵（搜索按钮与联想词两条路径）：

```powershell
python scripts/run_home_search_matrix.py
python scripts/run_home_search_matrix.py --cold
```

外卖首页搜索（含热搜、榜单、左滑、可选历史搜索和九关键词）：

```powershell
python scripts/run_takeout_search_matrix.py --scope home
```

旺旺商家主页内九关键词搜索：

```powershell
python scripts/run_takeout_search_matrix.py --scope wangwang --shop "旺旺超市 WWCS"
```

商城九关键词搜索属于商城业务入口：

```powershell
python scripts/run_shop_business.py --action search_matrix
```

## 外卖业务

进入旺旺店铺（默认会执行马尼拉定位）：

```powershell
python scripts/run_takeout_wangwang.py
python scripts/run_takeout_wangwang.py --shop "旺旺超市 WWCS"
python scripts/run_takeout_wangwang.py --no-manila
```

结算预览与真实下单：

```powershell
python scripts/run_takeout_wangwang.py --checkout
python scripts/run_takeout_wangwang.py --checkout --submit-order --max-payable 5000 --address-ordinal 1 --delivery-time-slot-ordinal 1
```

## 商城业务

商城搜索、详情、IM、分享、下单及完整业务：

```powershell
python scripts/run_shop_business.py --action search --keyword "牛奶"
python scripts/run_shop_business.py --action detail --keyword "牛奶"
python scripts/run_shop_business.py --action im --keyword "牛奶" --message "测试内容，请忽略"
python scripts/run_shop_business.py --action full --keyword "牛奶"
python scripts/run_shop_business.py --action order --keyword "牛奶" --submit-order
```

商城首页完整浏览业务：

```powershell
python scripts/run_shop_home.py
python scripts/run_shop_home.py --cold --quit-driver
```

商城立即购买/购物车订单 E2E：

```powershell
python scripts/run_mall_order_flow.py --flow buy_now --keyword "可乐"
python scripts/run_mall_order_flow.py --flow cart --keyword "可乐"
python scripts/run_mall_order_flow.py --flow both --keyword "可乐" --submit-order --payment-method cod
```

## 登录与个人中心

登录业务：

```powershell
python scripts/run_login.py --method wechat
python scripts/run_login.py --method phone --phone "手机号" --code "验证码"
python scripts/run_login.py --method password --phone "手机号" --password "密码"
```

个人中心只读巡检：

```powershell
python scripts/run_my_profile_navigation.py
python scripts/run_my_profile_navigation.py --logged-out
```

## 国际货运

该入口执行真实订单；余额支付所需密码和地址字段见脚本顶部说明。

```powershell
python scripts/run_shipping_business.py --payment-method cod --address-policy existing
python scripts/run_shipping_business.py --payment-method balance --cancel-unpaid
```

## 同城跑腿

默认不提交订单，传入 `--submit-order` 才会真实提交。

```powershell
python scripts/run_transfer_business.py --action menus
python scripts/run_transfer_business.py --action full
python scripts/run_transfer_business.py --action order --submit-order --payment-method balance
```

## 新增脚本规范

新增 `scripts/run_*.py` 时必须同时满足：

- 文件顶部说明业务范围和前置条件。
- 至少提供一条可复制的 `python scripts/run_xxx.py` 命令。
- 明确默认是否会提交真实订单、付款或修改业务数据。
- 在本索引中增加对应业务和常用命令。
- 执行 `python -m pytest testcases/test_script_command_docs.py -q`，确认入口说明与索引没有遗漏。
