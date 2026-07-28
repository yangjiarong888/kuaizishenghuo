# 商城搜索与详情只读能力拆分设计

日期：2026-07-28

## 背景

`pages/shop_business_page.py` 当前有 1395 行、59 个方法、52 处固定等待和
47 处宽泛异常捕获。它同时承载通用页面交互、搜索、商品发现、详情浏览、
随机加购、分享、客服 IM、结算和订单编排，职责边界过宽。

上一阶段已经完成商城订单脚本的安全能力开关、HTTP/购物车/地址/结算拆分，
并通过严格只读的真机导航验证。此次继续沿用同一安全边界，只拆分搜索和商品
详情的只读能力，不改变业务行为。

## 目标

- 将搜索与商品详情只读能力从 `ShopBusinessPage` 中机械迁移到两个专用 mixin。
- 保持 `ShopBusinessPage` 作为兼容门面，现有调用方无需修改。
- 保持方法名、签名、返回值、调用顺序、定位器、等待、重试和异常分支不变。
- 将 `pages/shop_business_page.py` 降至 650 行以内。
- 为方法绑定、搜索到详情的调用顺序和公共兼容面增加离线回归保护。
- 完成后执行严格只读真机验证，不改变购物车、地址、订单、支付或消息数据。

## 非目标

- 本轮不替换固定等待，不调整超时值或重试次数。
- 本轮不收窄宽泛异常捕获；迁移后只重新统计总量。
- 本轮不修改 XPath、resource-id、坐标或页面判定标志。
- 本轮不重写商城首页、分类页、规格弹层或购物车组件。
- 本轮不执行加购、分享、复制链接、发送 IM、结算、下单或支付。
- 本轮不改变 `ShopBusinessPage` 的外部构造方式。

## 方案选择

采用两个 mixin 的方案：

1. `MallBusinessSearchMixin`：通用交互、搜索入口、搜索落地页、筛选浏览和
   `search_goods()`。
2. `MallBusinessDetailMixin`：商品候选识别、搜索/分类结果进入详情和详情只读浏览。

未采用三个 mixin 的方案，因为单独增加通用交互 mixin 会引入额外 MRO 关系，
但本轮没有独立复用需求。未采用只拆详情的方案，因为它无法解除搜索与通用交互
对门面文件的主要体积压力。

## 文件与职责

### `pages/shop_business_search_mixin.py`

新文件，包含以下现有方法的原样实现：

- `_safe_text`
- `_safe_desc`
- `_clean_xpath_text`
- `_page_contains_any`
- `_wait_page_contains_any`
- `_click_element_center`
- `_click_first_text_or_desc`
- `_type_into_best_edit_text`
- `_press_enter_or_search`
- `_swipe_fraction`
- `tap_search_entry`
- `_search_page_visible`
- `open_search_page`
- `_bounds_from_tag`
- `_tap_chip_below_title`
- `_tap_first_chip_below_title`
- `browse_search_landing`
- `tap_search_result_filters`
- `_tap_sort_control`
- `tap_secondary_category_filters`
- `browse_special_deals_products`
- `browse_search_results`
- `search_goods`

该 mixin 依赖 `ShopHomePage` 提供的窗口、包名、元素查找和滚动能力，但不直接
继承或导入 `ShopHomePage`，避免循环依赖。

### `pages/shop_business_detail_mixin.py`

新文件，包含以下现有方法的原样实现：

- `_product_candidate_roots`
- `_tap_first_search_result_image_by_source_bounds`
- `_tap_first_search_grid_goods_by_source_bounds`
- `open_first_visible_goods_detail`
- `_category_goods_item_price`
- `_tap_category_goods_item`
- `_tap_first_category_goods_item`
- `open_goods_detail`
- `tap_detail_main_image`
- `swipe_detail_to_content`
- `tap_detail_activity_info_if_visible`
- `tap_view_more_goods_if_visible`
- `tap_detail_back_to_top`
- `browse_goods_detail`
- `open_and_browse_goods_detail`

该 mixin 通过门面的 MRO 使用 `search_goods()` 和通用交互方法，不导入搜索
mixin，也不形成继承链。

### `pages/shop_business_page.py`

修改为：

```python
class ShopBusinessPage(
    MallBusinessSearchMixin,
    MallBusinessDetailMixin,
    ShopHomePage,
):
    ...
```

门面继续保留以下职责：

- 当前 Activity、结算页和地址弹层判断
- 分类随机浏览以及随机加购
- 分享与复制链接
- 客服 IM
- 立即购买、提交订单和完整业务流编排

公共调用方仍只需要实例化 `ShopBusinessPage`。本轮不要求调用方直接实例化
两个 mixin。

### `testcases/test_shop_business_decomposition.py`

新增离线单元测试，覆盖：

- `ShopBusinessPage` 上搜索与详情公共方法仍可调用。
- `search_goods()` 保持实例方法绑定，防止再次出现 stray `@staticmethod`。
- `open_goods_detail(keyword)` 仍先执行搜索，再选择商品，并要求详情页判定成功。
- 搜索失败时不尝试点击商品。
- 详情打开失败时返回失败，不误报成功。
- 测试替身只替代 Driver 边界，不复制生产实现的判断逻辑。

## 调用与数据流

严格只读主路径保持为：

```text
run_mall_order_flow.py
  → MallOrderFlow.run_navigation_verification(keyword)
  → ShopBusinessPage.open_goods_detail(keyword)
  → MallBusinessSearchMixin.search_goods(keyword)
  → MallBusinessDetailMixin.open_first_visible_goods_detail()
  → 详情页状态判定
  → 读取商品名称、价格等证据
  → capture_failure()
  → safe_back_to_mall()
```

两个新 mixin 不持有独立状态，继续使用 `self.driver`、`self.wait_sec` 和门面已有
辅助能力。不会增加新的配置项、环境变量或 CLI 参数。

## 错误处理

- 迁移期间保留现有布尔返回和异常语义。
- 不把现有失败转换为成功，也不新增兜底点击。
- 缺少搜索关键字、未进入搜索页、未找到商品或未确认详情页时，继续按原逻辑失败。
- 导入错误、MRO 冲突、方法漏迁移和方法绑定错误由离线测试及内存编译拦截。
- 真机失败继续生成脱敏截图、页面 XML 和运行日志。

## 测试与验收

按 RED→GREEN 执行：

1. 先新增兼容面、方法绑定和搜索到详情顺序测试，并确认在 mixin 尚不存在时失败。
2. 创建最小可导入的 mixin，再逐组迁移原方法。
3. 每迁移一组后运行聚焦测试。
4. 运行全量 `-m "not device"` 离线测试。
5. 对全部 Python 文件执行内存编译。
6. 重新统计三个相关文件合计的固定等待和宽泛异常；机械拆分不应增加总量。
7. 运行严格只读真机命令：

```powershell
..\Scripts\python.exe scripts\run_mall_order_flow.py `
  --verify-navigation-only `
  --product-source search `
  --keyword "可乐" `
  --session mall_readonly_decomposition_verify `
  --start-mode activate `
  --quit-driver
```

验收条件：

- 所有聚焦测试和非真机测试零失败。
- 所有 Python 文件编译成功。
- `ShopBusinessPage` 的既有公共搜索与详情方法仍可调用。
- `pages/shop_business_page.py` 不超过 650 行。
- 三个相关文件合计的固定等待和宽泛异常数量不高于拆分前。
- 真机命令退出码为 0，生成详情截图和脱敏 XML，并正常关闭 Driver。
- 日志中没有加购、下单、支付、地址写入、订单消息或取消订单动作。

## 风险与控制

- **MRO 风险**：搜索 mixin 必须排在详情 mixin 前，使详情方法能解析到
  `search_goods()` 和通用交互方法；兼容面测试和真实门面实例测试负责拦截。
- **装饰器漂移风险**：迁移方法时可能遗留 `@staticmethod`；专门的方法绑定测试
  必须先红后绿。
- **导入遗漏风险**：每个 mixin 只导入自身方法实际使用的标准库、Appium 类型和
  locator 常量；内存编译和模块导入测试负责拦截。
- **副作用混入风险**：随机加购、分享、IM 和订单方法明确留在门面，本轮真机命令
  只允许 `--verify-navigation-only`。
- **行为漂移风险**：生产方法只做机械迁移；等待、定位器和分支优化进入后续独立
  计划。

## 后续治理

本设计完成后，再基于真机耗时证据单独治理搜索与详情中的固定等待和宽泛异常。
该后续工作需要新的设计与测试，不与机械拆分混在同一提交中。
