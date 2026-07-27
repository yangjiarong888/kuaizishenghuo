"""Mall cart behavior composed by the compatible order-flow facade."""

from __future__ import annotations

import time
from typing import Optional

from commons.logger import setup_logger
from flows.mall_order_types import ProductSnapshot
from pages.shop_locators import (
    SHOP_ID_COUNT_SUB,
    SHOP_ID_MALL_ADD_SHOP_CAR,
    SHOP_ID_MALL_SHOP_CAR_CONTAINER,
)


logger = setup_logger(__name__)
STOCKOUT_MARKERS = (
    "库存不足",
    "库存不够",
    "已售罄",
    "补货中",
)
CHECKOUT_MARKERS = (
    "确认订单",
    "提交订单",
    "收货地址",
    "商品金额",
    "实付",
    "应付",
)


class MallOrderCartMixin:
    """Cart mutation boundaries that rely on common facade helpers."""

    def cart_page_visible(self) -> bool:
        blob = self.page_blob()
        return "购物车" in blob and any(
            marker in blob for marker in ("管理", "完成", "去结算", "结算", "全选", "删除")
        )

    def cart_manage_mode_visible(self) -> bool:
        blob = self.page_blob()
        return "购物车" in blob and "完成" in blob and "删除" in blob

    def open_cart_page(self) -> None:
        if self.cart_page_visible():
            return
        opened = False
        detail_cart = self._first_displayed_by_pkg_id(SHOP_ID_MALL_SHOP_CAR_CONTAINER)
        if detail_cart:
            opened = self._click_element_center(detail_cart, "详情页购物车入口")
        if not opened:
            self.ensure_mall_tab()
            opened = self.tap_floating_or_entry_cart()
        if not opened:
            raise AssertionError("未能打开购物车")
        self.assert_page_contains_any(("购物车", "管理", "去结算", "结算"), "未进入购物车页", timeout=8.0)

    def ensure_cart_normal_mode(self) -> None:
        if self.cart_manage_mode_visible():
            if not self.click_labels(
                ("完成",),
                desc="退出购物车管理模式",
                y_min_ratio=0.0,
                y_max_ratio=0.18,
                exact=True,
            ):
                self.tap_ratio(0.93, 0.09, "退出购物车管理模式坐标")
            self.assert_page_contains_any(("管理", "去结算", "结算"), "购物车未退出管理模式", timeout=5.0)

    def enter_cart_manage_mode(self) -> None:
        self.open_cart_page()
        if self.cart_manage_mode_visible():
            return
        if not self.click_labels(
            ("管理",),
            desc="进入购物车管理模式",
            y_min_ratio=0.0,
            y_max_ratio=0.20,
            exact=True,
        ):
            if not self.tap_ratio(0.93, 0.09, "进入购物车管理模式坐标"):
                raise AssertionError("购物车页未找到「管理」按钮")
        self.assert_page_contains_any(("完成", "删除", "全选"), "进入购物车管理模式失败", timeout=6.0)

    def cart_select_all_items(self) -> None:
        if not self.click_labels(
            ("全选",),
            desc="购物车全选",
            y_min_ratio=0.68,
            y_max_ratio=1.0,
            exact=False,
        ):
            if not self.tap_ratio(0.10, 0.92, "购物车全选坐标"):
                raise AssertionError("购物车管理模式未找到「全选」")
        time.sleep(0.5)

    def cart_select_first_item(self) -> None:
        for y_ratio in (0.38, 0.46, 0.54, 0.62):
            if self.tap_ratio(0.08, y_ratio, "购物车部分选择首个商品"):
                time.sleep(0.35)
                return
        raise AssertionError("购物车管理模式未能选择首个商品")

    def cart_confirm_delete_popup(self, *, required: bool = True) -> bool:
        markers = ("是否要删除", "删除已选", "确认删除", "确定删除")
        if not self.wait_page_contains_any(markers, timeout=3.0):
            if required:
                raise AssertionError("点击删除后未出现二次确认弹窗")
            return False
        if not self.click_labels(
            ("删除", "确定", "确认"),
            desc="二次确认删除",
            y_min_ratio=0.42,
            y_max_ratio=0.72,
            exact=True,
        ):
            if not self.tap_ratio(0.70, 0.59, "二次确认删除坐标"):
                raise AssertionError("删除二次确认弹窗未找到确认按钮")
        time.sleep(1.0)
        if self.wait_page_contains_any(markers, timeout=1.0):
            raise AssertionError("点击二次确认删除后弹窗未关闭")
        logger.info("购物车删除二次确认弹窗处理完成")
        return True

    def cart_assert_delete_without_selection_toast(self) -> None:
        self.enter_cart_manage_mode()
        if not self.click_labels(
            ("删除",),
            desc="购物车未选商品删除",
            y_min_ratio=0.68,
            y_max_ratio=1.0,
            exact=True,
        ):
            if not self.tap_ratio(0.82, 0.92, "购物车未选商品删除坐标"):
                raise AssertionError("购物车管理模式未找到底部「删除」按钮")
        if self.wait_page_contains_any(("还没有选择任何商品", "没有选择任何商品", "请选择商品"), timeout=4.0):
            logger.info("购物车未选商品删除提示断言通过")
            return
        if self.wait_page_contains_any(("是否要删除", "删除已选"), timeout=0.8):
            self.click_labels(("取消",), desc="未选删除误触弹窗取消", y_min_ratio=0.42, y_max_ratio=0.72, exact=True)
        raise AssertionError("未选择商品点击删除后未出现「还没有选择任何商品」提示")

    def cart_delete_by_manage(self, *, all_items: bool) -> None:
        self.enter_cart_manage_mode()
        if all_items:
            self.cart_select_all_items()
        else:
            self.cart_select_first_item()
        if not self.click_labels(
            ("删除",),
            desc="购物车管理删除",
            y_min_ratio=0.68,
            y_max_ratio=1.0,
            exact=True,
        ):
            if not self.tap_ratio(0.82, 0.92, "购物车管理删除坐标"):
                raise AssertionError("购物车管理模式未找到底部「删除」按钮")
        self.cart_confirm_delete_popup(required=True)
        self.assert_page_contains_any(("购物车", "管理", "完成", "去结算", "结算"), "删除后未停留在购物车页", timeout=6.0)
        logger.info("购物车管理模式%s删除流程通过", "全选" if all_items else "部分选择")

    def cart_delete_by_minus(self) -> None:
        self.open_cart_page()
        self.ensure_cart_normal_mode()
        clicked = False
        for idx in range(5):
            if not self.click_first_by_id_in_band(
                SHOP_ID_COUNT_SUB,
                f"购物车商品数量减号{idx + 1}",
                x_min_ratio=0.48,
                x_max_ratio=0.92,
                y_min_ratio=0.24,
                y_max_ratio=0.78,
            ):
                if idx == 0:
                    clicked = self.tap_ratio(0.78, 0.47, "购物车商品数量减号坐标")
                else:
                    clicked = False
            else:
                clicked = True
            if not clicked:
                break
            if self.cart_confirm_delete_popup(required=False):
                self.assert_page_contains_any(("购物车", "管理", "去结算", "结算"), "减号删除后未停留在购物车页", timeout=6.0)
                logger.info("购物车减号删除流程通过")
                return
            time.sleep(0.4)
        raise AssertionError("点击购物车数量减号后未触发删除确认；请确认当前商品数量可减到 0")

    def cart_swipe_left_first_item(self) -> None:
        self.open_cart_page()
        self.ensure_cart_normal_mode()
        w, h = self._window_size()
        for y_ratio in (0.42, 0.50, 0.58):
            try:
                self.driver.swipe(
                    int(w * 0.86),
                    int(h * y_ratio),
                    int(w * 0.34),
                    int(h * y_ratio),
                    520,
                )
                logger.info("已左滑购物车商品行 y=%.2f", y_ratio)
                time.sleep(0.7)
                if self.wait_page_contains_any(("找相似", "收藏", "删除"), timeout=1.2):
                    return
            except Exception:
                continue
        raise AssertionError("购物车商品左滑后未出现「删除/收藏/找相似」菜单")

    def cart_delete_by_swipe(self) -> None:
        self.cart_swipe_left_first_item()
        if not self.click_first_by_id_in_band(
            "tv_delete",
            "购物车左滑删除",
            x_min_ratio=0.58,
            x_max_ratio=1.0,
            y_min_ratio=0.20,
            y_max_ratio=0.78,
        ):
            if not self.click_labels(
                ("删除",),
                desc="购物车左滑删除",
                y_min_ratio=0.20,
                y_max_ratio=0.78,
                exact=True,
            ):
                if not self.tap_ratio(0.93, 0.42, "购物车左滑删除坐标"):
                    raise AssertionError("购物车左滑菜单未找到「删除」")
        self.cart_confirm_delete_popup(required=True)
        self.assert_page_contains_any(("购物车", "管理", "去结算", "结算"), "左滑删除后未停留在购物车页", timeout=6.0)
        logger.info("购物车左滑删除流程通过")

    def prepare_cart_delete_item(self, keyword: str) -> None:
        logger.info("准备购物车删除测试商品：%s", keyword)
        product = self.open_detail_and_snapshot(keyword)
        if not self.click_by_id_or_label(
            SHOP_ID_MALL_ADD_SHOP_CAR,
            ("加入购物车", "加购"),
            desc="删除用例-加入购物车",
            y_min_ratio=0.52,
            y_max_ratio=1.0,
        ):
            raise AssertionError("商品详情页未找到「加入购物车」")
        time.sleep(0.8)
        self.select_specs_and_quantity()
        if self.wait_page_contains_any(STOCKOUT_MARKERS, timeout=2.0):
            raise AssertionError("删除用例准备商品时提示库存不足")
        self.open_cart_page()
        blob = self.page_blob()
        if product.name and product.name not in blob:
            logger.warning("准备删除商品后购物车未直接出现商品名：%s", product.name)

    def run_cart_delete_case(self, mode: str, *, prepare_keyword: Optional[str] = None) -> bool:
        if prepare_keyword:
            self.prepare_cart_delete_item(prepare_keyword)
        else:
            self.open_cart_page()
        if mode == "manage_all":
            self.cart_delete_by_manage(all_items=True)
        elif mode == "manage_partial":
            self.cart_delete_by_manage(all_items=False)
        elif mode == "manage_none":
            self.cart_assert_delete_without_selection_toast()
        elif mode == "minus":
            self.cart_delete_by_minus()
        elif mode == "swipe":
            self.cart_delete_by_swipe()
        else:
            raise AssertionError(f"未知购物车删除模式：{mode}")
        return True

    def add_product_to_cart_exact_specs(
        self,
        product: ProductSnapshot,
    ) -> ProductSnapshot:
        if not self.click_by_id_or_label(
            SHOP_ID_MALL_ADD_SHOP_CAR,
            ("加入购物车", "加购"),
            desc="加入购物车",
            y_min_ratio=0.52,
            y_max_ratio=1.0,
        ):
            raise AssertionError("商品详情页未找到「加入购物车」")
        time.sleep(0.8)
        if self._login_like_screen_visible():
            raise AssertionError(
                "加入购物车后进入登录页，前置条件不满足：用户未登录"
            )
        sheet_stock = self.select_specs_and_quantity()
        if product.stock_before is None and sheet_stock is not None:
            product.stock_before = sheet_stock
        if self.wait_page_contains_any(
            STOCKOUT_MARKERS,
            timeout=2.0,
        ):
            raise AssertionError("库存充足商品加入购物车时提示库存不足")
        return product

    def assert_cart_contains_product(
        self,
        product: ProductSnapshot,
    ) -> None:
        self.open_cart_page()
        blob = self.page_blob()
        if product.name and product.name not in blob:
            raise AssertionError(
                f"购物车未出现目标商品：{product.name}"
            )

    def run_add_to_cart_only(self, keyword: str) -> bool:
        product = self.open_detail_and_snapshot(keyword)
        product = self.add_product_to_cart_exact_specs(product)
        self.assert_cart_contains_product(product)
        logger.info("仅加购路径通过，未进入结算")
        return True

    def add_cart_to_checkout_exact_specs(self, product: ProductSnapshot) -> ProductSnapshot:
        if not self.click_by_id_or_label(
            SHOP_ID_MALL_ADD_SHOP_CAR,
            ("加入购物车", "加购"),
            desc="加入购物车",
            y_min_ratio=0.52,
            y_max_ratio=1.0,
        ):
            raise AssertionError("商品详情页未找到「加入购物车」")
        time.sleep(0.8)
        if self._login_like_screen_visible():
            raise AssertionError("加入购物车后进入登录页，前置条件不满足：用户未登录")
        sheet_stock = self.select_specs_and_quantity()
        if product.stock_before is None and sheet_stock is not None:
            product.stock_before = sheet_stock
        if self.wait_page_contains_any(STOCKOUT_MARKERS, timeout=2.0):
            raise AssertionError("库存充足商品加入购物车时提示库存不足")
        detail_cart = self._first_displayed_by_pkg_id(SHOP_ID_MALL_SHOP_CAR_CONTAINER)
        opened_cart = False
        if detail_cart:
            opened_cart = self._click_element_center(detail_cart, "详情页购物车入口")
        if not opened_cart and not self.tap_floating_or_entry_cart():
            raise AssertionError("未能打开购物车")
        self.assert_page_contains_any(("购物车", "结算", "去结算"), "未进入购物车页", timeout=8.0)
        blob = self.page_blob()
        if product.name and product.name not in blob:
            logger.warning("购物车页未直接出现商品名：%s，继续尝试结算", product.name)
        self.click_labels(("全选", "选择"), desc="购物车勾选", y_min_ratio=0.30, y_max_ratio=1.0)
        if not self.click_labels(
            ("去结算", "结算", "提交订单"),
            desc="购物车结算",
            y_min_ratio=0.52,
            y_max_ratio=1.0,
        ):
            raise AssertionError("购物车页未找到「去结算/结算」按钮")
        self.assert_page_contains_any(CHECKOUT_MARKERS, "购物车结算后未跳转至订单确认页", timeout=10.0)
        logger.info("购物车路径：已跳转至订单确认页")
        return product

    def run_cart_flow(self, keyword: str, *, submit_order: bool) -> bool:
        logger.info("开始购物车提交订单路径")
        product = self.open_detail_and_snapshot(keyword)
        product = self.add_cart_to_checkout_exact_specs(product)
        self.finish_checkout(product, submit_order=submit_order)
        logger.info("购物车提交订单路径通过")
        return True
