"""商城首页 / 金刚区 / 购物车 等 resource-id 后缀与文案（多包名与 Inspector 对齐）。"""
from __future__ import annotations

from typing import Tuple

from pages.takeout_locators import _PACKAGES

# 含部分渠道包（如 com.bz.feifubao、com.bs.feifuban 等马甲/笔误包名），与 takeout 列表去重合并
_SHOP_EXTRA: Tuple[str, ...] = (
    "com.bz.feifubao",
    "com.bs.feifuban",
)
SHOP_PACKAGES: Tuple[str, ...] = tuple(dict.fromkeys(tuple(_PACKAGES) + _SHOP_EXTRA))

SHOP_KINGKONG_HOT_SNACKS: str = "爆款零食"
# 金刚区「全部分类」弹窗（GridView + tv_category）
SHOP_TEXT_ALL_CATEGORIES: str = "全部分类"
SHOP_TEXT_DAILY_BAIHUO: str = "日用百货"
SHOP_TEXT_SELECT_SPEC: str = "选规格"
SHOP_ID_POPUP_WIN: str = "popup_win"
SHOP_ID_GRIDVIEW_CATEGORY: str = "gridView"
SHOP_ID_TV_CATEGORY: str = "tv_category"
SHOP_TEXT_LIMITED_SPECIAL: str = "限时特价"
# 与「限时特价」同属活动条/筛选位，部分版本文案为「限时秒杀」
SHOP_TEXT_LIMITED_SPECIAL_ALT: str = "限时秒杀"
SHOP_TEXT_NEW_PRODUCT_PICK: str = "新品优选"
# 列表 Tab 上常带 emoji，Inspector 示例：``✨新品优选``，仍为 ``tv_title``
SHOP_TEXT_NEW_PRODUCT_PICK_EMOJI: str = "✨新品优选"

# resource-id 后缀（与包名拼接为 f"{pkg}:id/{suffix}"）
SHOP_ID_ACTIVITY_FILTER: str = "activity_filter"
SHOP_ID_TV_TITLE: str = "tv_title"
SHOP_ID_LL_ITEM: str = "ll_item"
SHOP_ID_RV_MENU: str = "rv_menu"
SHOP_ID_IV_ADD_CART: str = "iv_add_cart"
SHOP_ID_IV_BANNER: str = "iv_banner"
SHOP_ID_IV_SHOPPING_CART: str = "iv_shopping_cart"
SHOP_ID_IV_CART: str = "iv_cart"
SHOP_ID_RL_CART: str = "rl_cart"
SHOP_ID_RL_SHOPPING_CART: str = "rl_shopping_cart"
SHOP_ID_IV_UP_TO_TOP: str = "iv_up_to_top"
SHOP_ID_FLOAT_VIEW: str = "float_view"
SHOP_ID_CV_CART: str = "cv_cart"
SHOP_ID_BOTTOM_POPUP: str = "bottomPopupContainer"
SHOP_ID_CHOOSE_RECYCLER: str = "choose_recycler_view"
SHOP_ID_DIALOG_COMPLETE: str = "dialog_complete"
SHOP_ID_COUNT_TEXT: str = "count_text"
SHOP_ID_CHOOSE_SCROLL: str = "choose_scroll_view"
# 商城「爆款零食」等分类列表（Inspector）
SHOP_ID_RV_GOODS: str = "rv_goods"
SHOP_ID_GOODS_LIST_ITEM: str = "goodsListItemLayout"
SHOP_ID_MALL_CATEGORY_GOODS_NAME: str = "mall_category_goods_name"
SHOP_ID_TV_ADD_CART_MORE: str = "tv_add_cart_more"

SHOP_BACK_ID_SUFFIXES: Tuple[str, ...] = (
    "iv_menu_back",  # 商品详情等子页
    "iv_back_white",
    "iv_back",
    "iv_back_black",
)

# 商城首页主列表（新品优选等 Tab 下，Inspector：rv_content / clItemContainer）
SHOP_ID_RV_CONTENT: str = "rv_content"
SHOP_ID_CL_ITEM_CONTAINER: str = "clItemContainer"
SHOP_ID_IV_GOODS: str = "iv_goods"
SHOP_ID_TV_GOODS_NAME: str = "tv_goods_name"
SHOP_ID_TV_PRICE: str = "tv_price"
SHOP_ID_IMAGE: str = "image"

# 商品详情页（com.bs.feifubao / com.bs.feifuban 等）
SHOP_ID_MALL_DETAIL_VIEWPAGER: str = "mall_detail_viewpager"
SHOP_ID_MALL_ADD_SHOP_CAR: str = "mall_add_shop_car"
SHOP_ID_MALL_BUY_NOW: str = "mall_buy_now"
SHOP_ID_IV_COLLECT: str = "iv_collect"
SHOP_ID_MALL_KEFU: str = "mall_kefu"
SHOP_ID_MALL_SHOP_CAR_CONTAINER: str = "mall_shop_car_container"
SHOP_ID_DIALOG_CHOOSE_CONTAINER: str = "dialog_choose_container"
SHOP_ID_CHOOSE_SKU_CONTAINER: str = "choose_sku_container"
SHOP_ID_COUNT_ADD: str = "count_add"
SHOP_ID_COUNT_SUB: str = "count_sub"

SHOP_TEXT_FINISH_SPEC: str = "完成"
SHOP_TEXT_COLLECT_OK: str = "收藏成功"
SHOP_TEXT_KEFU_24: str = "24小时客服"
# 客服页/H5 常见文案（与「24小时客服」择一命中即可）
SHOP_TEXT_KEFU_PAGE_MARKERS: Tuple[str, ...] = (
    SHOP_TEXT_KEFU_24,
    "24小时",
    "在线客服",
    "客服中心",
    "联系客服",
    "智能客服",
    "人工客服",
    "常见问题",
    "意见反馈",
    "在线咨询",
    "专属客服",
)
SHOP_TEXT_MALL_CART_TITLE: str = "购物车"
