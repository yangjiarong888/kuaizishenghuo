"""外卖页 XPath / 包名常量（供 takeout_page、takeout_shop_mixin 共用）。"""
from __future__ import annotations

from typing import Tuple

# 多渠道/马甲包名（与 Inspector 一致）
_PACKAGES: Tuple[str, ...] = (
    "com.bs.feifubao",
    "com.ba.feifubao",
    "com.bx.feifubao",
    "com.hu.feifubao",
)

TAKEOUT_HOME_CART_LABELS: Tuple[str, ...] = ("购物车", "外卖购物车")
TAKEOUT_HOME_TOP_LABELS: Tuple[str, ...] = ("回到顶部", "返回顶部", "顶部")
TAKEOUT_DISCOUNT_LABEL = "满减活动"
TAKEOUT_CONGEE_CATEGORY_LABEL = "粥粉面饺"
TAKEOUT_SERVICE_LABELS: Tuple[str, ...] = ("客服", "24小时客服")


def _merchant_list_rid(pkg: str) -> str:
    return f"{pkg}:id/rv_merchant"


def _merchant_list_root_xpath(pkg: str) -> str:
    """商家 RecyclerView 根，用于缩小 XPath 范围（整页 // 扫描在大列表上极慢）。"""
    rid = _merchant_list_rid(pkg)
    return f'//*[@resource-id="{rid}"]'


def _scoped_tv_merchant_name_exact(pkg: str, text: str) -> str:
    return (
        f"{_merchant_list_root_xpath(pkg)}"
        f'//android.widget.TextView[@resource-id="{pkg}:id/tv_merchant_name" '
        f'and @text="{text}"]'
    )


def _scoped_tv_merchant_name_contains(pkg: str, shop_substring: str) -> str:
    return (
        f"{_merchant_list_root_xpath(pkg)}"
        f'//android.widget.TextView[@resource-id="{pkg}:id/tv_merchant_name" '
        f'and contains(@text,"{shop_substring}")]'
    )


def _scoped_row_tab_content_xpath_exact(pkg: str, text: str) -> str:
    return (
        f"{_merchant_list_root_xpath(pkg)}"
        f'//android.widget.RelativeLayout[@resource-id="{pkg}:id/ll_tab_content"]'
        f'[.//android.widget.TextView[@resource-id="{pkg}:id/tv_merchant_name" '
        f'and @text="{text}"]]'
    )


def _scoped_row_tab_content_xpath_contains(pkg: str, shop_substring: str) -> str:
    return (
        f"{_merchant_list_root_xpath(pkg)}"
        f'//android.widget.RelativeLayout[@resource-id="{pkg}:id/ll_tab_content"]'
        f'[.//android.widget.TextView[@resource-id="{pkg}:id/tv_merchant_name" '
        f'and contains(@text,"{shop_substring}")]]'
    )


def _scoped_row_xpath_exact_name(pkg: str, text: str) -> str:
    return (
        f"{_merchant_list_root_xpath(pkg)}"
        f'//android.widget.LinearLayout[@resource-id="{pkg}:id/ll_merchant"]'
        f'[.//android.widget.TextView[@resource-id="{pkg}:id/tv_merchant_name" '
        f'and @text="{text}"]]'
    )


def _scoped_row_xpath_contains_name(pkg: str, shop_substring: str) -> str:
    return (
        f"{_merchant_list_root_xpath(pkg)}"
        f'//android.widget.LinearLayout[@resource-id="{pkg}:id/ll_merchant"]'
        f'[.//android.widget.TextView[@resource-id="{pkg}:id/tv_merchant_name" '
        f'and contains(@text,"{shop_substring}")]]'
    )


def _scoped_shop_title_textview_exact(pkg: str, text: str) -> str:
    """列表内任意 TextView 精确店名（兼容 tv_merchant_name 被去掉或换父级的情况）。"""
    return (
        f"{_merchant_list_root_xpath(pkg)}"
        f'//android.widget.TextView[@text="{text}"]'
    )


def _scoped_shop_title_textview_contains(pkg: str, shop_substring: str) -> str:
    """列表内任意 TextView 含子串（子串建议 ≥4 字符，降低误点「距离」等短文案）。"""
    return (
        f"{_merchant_list_root_xpath(pkg)}"
        f'//android.widget.TextView[contains(@text,"{shop_substring}")]'
    )


def _row_xpath_exact_name(pkg: str, text: str) -> str:
    return (
        f'//android.widget.LinearLayout[@resource-id="{pkg}:id/ll_merchant"]'
        f'[.//android.widget.TextView[@resource-id="{pkg}:id/tv_merchant_name" '
        f'and @text="{text}"]]'
    )


def _row_xpath_contains_name(pkg: str, shop_substring: str) -> str:
    return (
        f'//android.widget.LinearLayout[@resource-id="{pkg}:id/ll_merchant"]'
        f'[.//android.widget.TextView[@resource-id="{pkg}:id/tv_merchant_name" '
        f'and contains(@text,"{shop_substring}")]]'
    )


def _name_xpath_exact(pkg: str, text: str) -> str:
    return (
        f'//android.widget.TextView[@resource-id="{pkg}:id/tv_merchant_name" '
        f'and @text="{text}"]'
    )


def _row_tab_content_xpath_exact(pkg: str, text: str) -> str:
    return (
        f'//android.widget.RelativeLayout[@resource-id="{pkg}:id/ll_tab_content"]'
        f'[.//android.widget.TextView[@resource-id="{pkg}:id/tv_merchant_name" '
        f'and @text="{text}"]]'
    )


def _row_tab_content_xpath_contains(pkg: str, shop_substring: str) -> str:
    return (
        f'//android.widget.RelativeLayout[@resource-id="{pkg}:id/ll_tab_content"]'
        f'[.//android.widget.TextView[@resource-id="{pkg}:id/tv_merchant_name" '
        f'and contains(@text,"{shop_substring}")]]'
    )


_WEB_XPATH_CANCEL_ORDER: Tuple[str, ...] = (
    "//button[contains(normalize-space(.),'取消订单')]",
    "//a[contains(normalize-space(.),'取消订单')]",
    "//*[self::div or self::span or self::p][contains(normalize-space(.),'取消订单')]",
    "//*[contains(normalize-space(string(.)),'取消订单')]",
)
_WEB_XPATH_CONFIRM_CANCEL: Tuple[str, ...] = (
    "//button[contains(normalize-space(.),'确定取消')]",
    "//a[contains(normalize-space(.),'确定取消')]",
    "//*[self::div or self::span][contains(normalize-space(.),'确定取消')]",
    "//*[contains(normalize-space(string(.)),'确定取消')]",
)
_WEB_XPATH_SUBMIT: Tuple[str, ...] = (
    "//button[contains(normalize-space(.),'提交')]",
    "//a[contains(normalize-space(.),'提交')]",
    "//*[self::button or self::a][normalize-space(.)='提交']",
    "//*[self::div or self::span][normalize-space(.)='提交']",
    "//*[contains(normalize-space(string(.)),'提交')]",
    "//input[@type='submit' or @value='提交']",
)
_WEB_REASON_FRAGMENTS: Tuple[str, ...] = (
    "不想要了",
    "临时有事",
    "点多了",
    "点错了",
    "收货信息填错了",
    "送达时间选错了",
    "其他",
)

# Native（店铺 Flutter / 弹层）重复用到的 XPath，避免多处硬编码同串
_XPATH_DESC_CART = '//*[contains(@content-desc,"购物车")]'
_XPATH_DESC_SELECT_ADDRESS = '//*[contains(@content-desc,"请选择收货地址")]'
_XPATH_NATIVE_CANCEL_ORDER: Tuple[str, ...] = (
    '//*[@text="取消订单"]',
    '//*[contains(@content-desc,"取消订单")]',
)
_XPATH_NATIVE_CONFIRM_CANCEL: Tuple[str, ...] = (
    '//android.widget.TextView[@text="确定取消"]',
    '//*[@text="确定取消"]',
)
_XPATH_NATIVE_SUBMIT: Tuple[str, ...] = (
    '//*[@text="提交"]',
    '//*[contains(@content-desc,"提交")]',
    '//android.widget.Button[@text="提交"]',
    '//android.widget.TextView[@text="提交"]',
)
