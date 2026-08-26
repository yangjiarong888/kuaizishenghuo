"""Composition entry for complete takeout business and checkout flows."""

from __future__ import annotations

from pages.business_search_spec import run_search_matrix
from pages.takeout_business_stage import run_takeout_stage
from pages.takeout_checkout_mixin import TakeoutCheckoutMixin
from pages.takeout_home_business_mixin import TakeoutHomeBusinessMixin
from pages.takeout_home_search_adapter import TakeoutHomeSearchAdapter
from pages.takeout_im_mixin import TakeoutIMMixin
from pages.takeout_merchant_business_mixin import TakeoutMerchantBusinessMixin


class TakeoutShopMixin(
    TakeoutMerchantBusinessMixin,
    TakeoutIMMixin,
    TakeoutHomeBusinessMixin,
    TakeoutCheckoutMixin,
):
    """Combine home, merchant, IM, search, checkout, and cancellation flows."""

    def _run_takeout_home_service_im_bundle(self) -> bool:
        if not self.open_takeout_home_service_im():
            return False
        if not self.send_takeout_im_bundle():
            return False
        try:
            self.driver.back()
        except Exception:
            return False
        return bool(self.wait_merchant_list_present(timeout=6.0))

    def run_takeout_home_search_matrix(self):
        return run_search_matrix(TakeoutHomeSearchAdapter(self))

    def _prepare_cart_for_full_business(self) -> bool:
        state = self.assert_cart_reuse_or_empty()
        if state == "reuse":
            return True
        if state != "empty":
            return False
        category = "店内招牌"
        if not self.shop_detail_scroll_to_category(category):
            return False
        return bool(self.shop_detail_add_first_visible_product_highest_spec(category))

    def run_full_takeout_business(
        self,
        *,
        shop_name: str,
        address_policy: str,
        address_data,
        address_ordinal,
        address_contains,
        max_payable,
        submit_order: bool,
    ) -> bool:
        if not self.ensure_takeout_city_manila():
            return False
        stages = (
            (1, "外卖首页分页", lambda: self.browse_takeout_merchant_pages(3)),
            (2, "购物车入口", self.open_home_floating_cart_and_return),
            (3, "回顶", self.return_takeout_list_to_top),
            (4, "满减筛选", self.verify_discount_filter_cycle),
            (5, "粥粉面饺分类", self.open_congee_category_and_return),
            (6, "外卖首页客服IM", self._run_takeout_home_service_im_bundle),
            (7, "外卖首页搜索矩阵", self.run_takeout_home_search_matrix),
            (8, "旺旺进店", lambda: self.scroll_to_and_open_shop(shop_name)),
            (9, "商家收藏", self.ensure_takeout_merchant_favorited),
            (10, "旺旺商家IM", self.run_wangwang_merchant_im),
            (11, "旺旺店内搜索矩阵", self.run_wangwang_search_matrix),
            (12, "购物车复用或单次加购", self._prepare_cart_for_full_business),
            (
                13,
                "真实COD下单并取消" if submit_order else "COD结算安全预览",
                lambda: self.run_shop_checkout_pay_and_cancel_flow(
                    submit_order=submit_order,
                    address_policy=address_policy,
                    address_data=address_data,
                    address_ordinal=address_ordinal,
                    address_contains=address_contains,
                    checkout_payment="cod",
                    delivery_time_slot_ordinal=5,
                    delivery_slot_contains=None,
                    require_day_after_tomorrow=True,
                    max_payable=max_payable,
                    remark_text="test order",
                ),
            ),
        )
        for number, name, action in stages:
            run_takeout_stage(self, number, name, action)
        return True
