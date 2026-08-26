import pytest

import pages.takeout_shop_mixin as shop_module
from pages.takeout_shop_mixin import TakeoutShopMixin


pytestmark = pytest.mark.unit


class FullFlowRecorder(TakeoutShopMixin):
    driver = object()

    def __init__(self):
        self.stage_names = []
        self.checkout_kwargs = None

    def ensure_takeout_city_manila(self):
        return True

    def browse_takeout_merchant_pages(self, _count):
        return ["a", "b", "c"]

    def open_home_floating_cart_and_return(self):
        return True

    def return_takeout_list_to_top(self):
        return True

    def verify_discount_filter_cycle(self):
        return True

    def open_congee_category_and_return(self):
        return True

    def _run_takeout_home_service_im_bundle(self):
        return True

    def run_takeout_home_search_matrix(self):
        return ["home-search"]

    def scroll_to_and_open_shop(self, _shop_name):
        return True

    def ensure_takeout_merchant_favorited(self):
        return True

    def run_wangwang_merchant_im(self):
        return True

    def run_wangwang_search_matrix(self):
        return ["merchant-search"]

    def _prepare_cart_for_full_business(self):
        return True

    def run_shop_checkout_pay_and_cancel_flow(self, **kwargs):
        self.checkout_kwargs = kwargs
        return True


def _install_recording_stage_runner(monkeypatch):
    def recording_runner(page, _number, name, action):
        page.stage_names.append(name)
        value = action()
        if value is False or value is None:
            raise AssertionError(name)
        return value

    monkeypatch.setattr(shop_module, "run_takeout_stage", recording_runner)


def test_full_takeout_business_runs_exact_stage_order(monkeypatch):
    _install_recording_stage_runner(monkeypatch)
    page = FullFlowRecorder()
    assert page.run_full_takeout_business(
        shop_name="旺旺超市 WWCS",
        address_policy="auto",
        address_data=object(),
        address_ordinal=None,
        address_contains=None,
        max_payable=5000,
        submit_order=True,
    )
    assert page.stage_names == [
        "外卖首页分页",
        "购物车入口",
        "回顶",
        "满减筛选",
        "粥粉面饺分类",
        "外卖首页客服IM",
        "外卖首页搜索矩阵",
        "旺旺进店",
        "商家收藏",
        "旺旺商家IM",
        "旺旺店内搜索矩阵",
        "购物车复用或单次加购",
        "真实COD下单并取消",
    ]
    assert page.checkout_kwargs["checkout_payment"] == "cod"
    assert page.checkout_kwargs["delivery_time_slot_ordinal"] == 5
    assert page.checkout_kwargs["delivery_slot_contains"] is None
    assert page.checkout_kwargs["require_day_after_tomorrow"] is True
    assert page.checkout_kwargs["submit_order"] is True


def test_full_takeout_business_stops_after_failed_stage(monkeypatch):
    def stop_runner(page, number, name, action):
        page.stage_names.append(name)
        if number == 6:
            raise RuntimeError("stop")
        return action()

    monkeypatch.setattr(shop_module, "run_takeout_stage", stop_runner)
    page = FullFlowRecorder()
    with pytest.raises(RuntimeError, match="stop"):
        page.run_full_takeout_business(
            shop_name="旺旺超市 WWCS",
            address_policy="auto",
            address_data=object(),
            address_ordinal=None,
            address_contains=None,
            max_payable=5000,
            submit_order=False,
        )
    assert page.stage_names == [
        "外卖首页分页",
        "购物车入口",
        "回顶",
        "满减筛选",
        "粥粉面饺分类",
        "外卖首页客服IM",
    ]


def test_full_business_cart_adds_only_when_explicitly_empty():
    page = FullFlowRecorder()
    events = []
    page.assert_cart_reuse_or_empty = lambda: "empty"
    page.shop_detail_scroll_to_category = (
        lambda name: events.append(("category", name)) or True
    )
    page.shop_detail_add_first_visible_product_highest_spec = (
        lambda name: events.append(("add", name)) or True
    )
    assert TakeoutShopMixin._prepare_cart_for_full_business(page)
    assert events == [("category", "店内招牌"), ("add", "店内招牌")]


def test_full_business_does_not_add_when_cart_is_reused():
    page = FullFlowRecorder()
    page.assert_cart_reuse_or_empty = lambda: "reuse"
    page.shop_detail_add_first_visible_product_highest_spec = lambda _name: (
        (_ for _ in ()).throw(AssertionError("must not add"))
    )
    assert TakeoutShopMixin._prepare_cart_for_full_business(page)


def test_full_business_rejects_tomorrow_fallback():
    class DeliveryRecorder(TakeoutShopMixin):
        def _tap_day_after_tomorrow_date_in_sheet(self):
            return False

        def _tap_tomorrow_date_in_sheet(self):
            raise AssertionError("tomorrow fallback must not run")

    assert (
        DeliveryRecorder()._tap_allowed_delivery_date_in_sheet(
            require_day_after_tomorrow=True
        )
        is None
    )
