import pytest

import pages.takeout_merchant_business_mixin as merchant_module
from pages.takeout_merchant_business_mixin import TakeoutMerchantBusinessMixin


pytestmark = pytest.mark.unit


class MerchantRecorder(TakeoutMerchantBusinessMixin):
    driver = object()

    def __init__(self, *, favorited=False, cart_has_items=False, cart_count=None):
        self.favorited = favorited
        self.favorite_clicks = 0
        self.cart_has_items = cart_has_items
        self.cart_count = cart_count
        self.add_calls = 0
        self.events = []

    def _takeout_merchant_favorite_state(self):
        return self.favorited

    def _click_takeout_merchant_favorite(self):
        self.favorite_clicks += 1
        self.favorited = True
        return True

    def _explicit_shop_cart_count(self):
        return self.cart_count

    def shop_cart_has_purchasable_items(self):
        return self.cart_has_items

    def _open_takeout_merchant_im(self):
        self.events.append("open-im")
        return True

    def _takeout_merchant_im_visible(self):
        self.events.append("im-visible")
        return True

    def send_takeout_im_bundle(self):
        self.events.append("send-bundle")
        return True

    def _looks_inside_takeout_shop(self):
        self.events.append("merchant-home")
        return True


def test_already_favorited_does_not_click():
    page = MerchantRecorder(favorited=True)
    assert page.ensure_takeout_merchant_favorited()
    assert page.favorite_clicks == 0


def test_not_favorited_clicks_once_and_reads_back():
    page = MerchantRecorder(favorited=False)
    assert page.ensure_takeout_merchant_favorited()
    assert page.favorite_clicks == 1
    assert page.favorited is True


def test_non_empty_cart_is_reused_without_add():
    page = MerchantRecorder(cart_has_items=True)
    assert page.assert_cart_reuse_or_empty() == "reuse"
    assert page.add_calls == 0


def test_explicit_empty_cart_allows_one_later_add():
    page = MerchantRecorder(cart_count=0)
    assert page.assert_cart_reuse_or_empty() == "empty"


def test_unknown_cart_state_fails_instead_of_adding():
    page = MerchantRecorder(cart_has_items=False, cart_count=None)
    assert page.assert_cart_reuse_or_empty() is False
    assert page.add_calls == 0


def test_merchant_im_delegates_one_complete_bundle():
    page = MerchantRecorder()
    page.driver = type("D", (), {"back": lambda self: page.events.append("back")})()
    assert page.run_wangwang_merchant_im()
    assert page.events == [
        "open-im",
        "im-visible",
        "send-bundle",
        "back",
        "merchant-home",
    ]


def test_merchant_matrix_delegates_shared_runner_once(monkeypatch):
    page = MerchantRecorder()
    calls = []
    monkeypatch.setattr(
        merchant_module,
        "run_search_matrix",
        lambda adapter: calls.append(type(adapter).__name__) or ["ok"],
    )
    assert page.run_wangwang_search_matrix() == ["ok"]
    assert calls == ["TakeoutMerchantSearchAdapter"]
