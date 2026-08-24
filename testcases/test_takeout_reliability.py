from __future__ import annotations

from contextlib import nullcontext

from pages.takeout_checkout_mixin import TakeoutCheckoutMixin
from pages.takeout_cancel_order_mixin import TakeoutCancelOrderMixin
from pages.takeout_delivery_time_mixin import TakeoutDeliveryTimeMixin
from pages import takeout_page


class FakeElement:
    def __init__(self, blob: str, *, y: int = 500, x: int = 700) -> None:
        self.blob = blob
        self.location = {"x": x, "y": y}
        self.size = {"width": 200, "height": 80}

    def get_attribute(self, name: str):
        if name in ("content-desc", "text"):
            return self.blob
        return ""

    def is_displayed(self) -> bool:
        return True


class AddressPage(TakeoutCheckoutMixin):
    def __init__(self, candidates) -> None:
        self.candidates = candidates
        self.clicked = []

    def _window_size_safe(self):
        return 1080, 2200

    def _window_height(self):
        return 2200

    def _gather_address_sheet_candidates(self):
        return list(self.candidates)

    def _coord_tap_or_click(self, element, description):
        self.clicked.append(element.blob)
        return True

    def _checkout_page_has_any(self, labels):
        return any(label in self.clicked[-1] for label in labels) if self.clicked else False


class DelayedAddressReadbackPage(AddressPage):
    def __init__(self, candidates, readbacks) -> None:
        super().__init__(candidates)
        self.readbacks = list(readbacks)

    def _checkout_page_has_any(self, labels):
        if "选择支付方式" in labels or "当前地址未填写手机号" in labels:
            return False
        return self.readbacks.pop(0)


class PaymentSheetAfterAddressPage(AddressPage):
    def _checkout_page_has_any(self, labels):
        return "选择支付方式" in labels


class MissingPhoneAfterAddressPage(AddressPage):
    def __init__(self, candidates) -> None:
        super().__init__(candidates)
        self.confirmed_missing_phone = False

    def _checkout_page_has_any(self, labels):
        if "选择支付方式" in labels:
            return self.confirmed_missing_phone
        if "当前地址未填写手机号" in labels:
            return not self.confirmed_missing_phone
        return False

    def _tap_first_displayed(self, by, selector):
        if "确认并继续使用" not in selector:
            return False
        self.confirmed_missing_phone = True
        return True


class MissingRemarkPage(TakeoutCheckoutMixin):
    def _checkout_scroll_until_visible(self, labels, *, max_rounds):
        return False


class RemarkEntryDriver:
    def execute_script(self, *args, **kwargs):
        return None

    def hide_keyboard(self):
        return None


class RemarkEntryPage(TakeoutCheckoutMixin):
    def __init__(self) -> None:
        self.driver = RemarkEntryDriver()
        self.tap_selectors = []

    def _checkout_scroll_until_visible(self, labels, *, max_rounds):
        return True

    def _tap_first_displayed(self, by, selector):
        self.tap_selectors.append(selector)
        return "对骑手和商家有什么留言" in selector or "完成" in selector

    def _checkout_page_has_any(self, labels):
        return True

    def _type_checkout_text(self, text, desc, *, section_label=None):
        return True

    def _select_checkout_quick_note(self, label, desc, *, max_scrolls):
        return True


class SemanticRemarkElement(FakeElement):
    def is_displayed(self) -> bool:
        return True


class SemanticRemarkDriver:
    def __init__(self) -> None:
        self.clipboard = None
        self.keycodes = []

    def find_elements(self, by, selector):
        if "@hint" in selector and "对商家备注" in selector:
            return [SemanticRemarkElement("", y=500)]
        return []

    def set_clipboard_text(self, value):
        self.clipboard = value

    def press_keycode(self, keycode):
        self.keycodes.append(keycode)


class SemanticRemarkInputPage(TakeoutCheckoutMixin):
    def __init__(self) -> None:
        self.driver = SemanticRemarkDriver()

    def _visible_edit_texts_checkout(self):
        return []

    def _coord_tap_or_click(self, element, description):
        return True

    def _checkout_page_has_any(self, labels):
        return self.driver.clipboard in labels


class SubmitRemarkPage(TakeoutCheckoutMixin):
    def __init__(self) -> None:
        self.driver = RemarkEntryDriver()
        self.submitted = False
        self.readback_checks = 0
        self.text_section = None

    def _checkout_scroll_until_visible(self, labels, *, max_rounds):
        return True

    def _tap_first_displayed(self, by, selector):
        if "对骑手和商家有什么留言" in selector:
            return True
        if "提交" in selector:
            self.submitted = True
            return True
        return False

    def _checkout_page_has_any(self, labels):
        if self.submitted and "test order" in labels:
            self.readback_checks += 1
            return True
        return "添加备注" in labels

    def _type_checkout_text(self, text, desc, *, section_label=None):
        self.text_section = section_label
        return True

    def _select_checkout_quick_note(self, label, desc, *, max_scrolls):
        return True


def test_requested_remark_fails_when_the_remark_entry_is_missing() -> None:
    page = MissingRemarkPage()

    assert not page.shop_fill_remark(
        remark_text="test order",
        rider_remark="",
        merchant_remark="",
    )


def test_remark_entry_prefers_the_clickable_message_value(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = RemarkEntryPage()

    assert page.shop_fill_remark(
        remark_text="test order",
        rider_remark="",
        merchant_remark="",
    )
    assert "对骑手和商家有什么留言" in page.tap_selectors[0]


def test_remark_text_uses_the_focused_flutter_semantics_input(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = SemanticRemarkInputPage()

    assert page._type_checkout_text(
        "test order",
        "外卖备注文本",
        section_label="对商家备注",
    )
    assert page.driver.clipboard == "test order"
    assert page.driver.keycodes == [279]


def test_remark_submits_and_reads_the_text_back_on_checkout(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = SubmitRemarkPage()

    assert page.shop_fill_remark(
        remark_text="test order",
        rider_remark="",
        merchant_remark="",
    )
    assert page.submitted
    assert page.text_section == "对商家备注"
    assert page.readback_checks == 1


class CancelSubmitDriver:
    page_source = ""

    def __init__(self, page) -> None:
        self.page = page
        self.taps = []

    def find_elements(self, by, selector):
        return []

    def find_element(self, by, selector):
        raise RuntimeError("semantic submit unavailable")

    def execute_script(self, name, payload):
        self.taps.append((payload["x"], payload["y"]))
        if payload["y"] == int(2270 * 0.66):
            self.page.modal_visible = False


class CoordinateOnlyCancelSubmitPage(TakeoutCancelOrderMixin):
    def __init__(self) -> None:
        self.modal_visible = True
        self.driver = CancelSubmitDriver(self)

    def _window_size_safe(self):
        return 1080, 2270

    def _cancel_reason_modal_visible_for_submit(self):
        return self.modal_visible

    def _cancel_reason_modal_title_visible(self):
        return self.modal_visible


class PendingMerchantCancelDriver:
    contexts = ["NATIVE_APP"]
    current_context = "NATIVE_APP"
    page_source = "取消申请已提交，待商家处理"

    def find_elements(self, by, selector):
        return []


class PendingMerchantCancelPage(TakeoutCancelOrderMixin):
    def __init__(self) -> None:
        self.driver = PendingMerchantCancelDriver()

    def _window_size_safe(self):
        return 1080, 2270

    def _cancel_order_entry_still_visible(self):
        return False


class ProgressDetailCancelDriver:
    contexts = ["NATIVE_APP"]
    current_context = "NATIVE_APP"
    page_source = "订单详情 查看订单进度详情"

    def find_elements(self, by, selector):
        if "查看订单进度详情" in selector:
            return [FakeElement("查看订单进度详情")]
        return []


class ProgressDetailCancelPage(TakeoutCancelOrderMixin):
    def __init__(self) -> None:
        self.driver = ProgressDetailCancelDriver()

    def _window_size_safe(self):
        return 1080, 2270

    def _cancel_order_entry_still_visible(self):
        return False


class ActiveOrderProgressDetailPage(ProgressDetailCancelPage):
    def _cancel_order_entry_still_visible(self):
        return True


class OrdinaryOrderProgressDriver(ProgressDetailCancelDriver):
    page_source = "订单详情 订单进度详情"

    def find_elements(self, by, selector):
        if "订单进度详情" in selector and "查看订单进度详情" not in selector:
            return [FakeElement("订单进度详情")]
        return []


class OrdinaryOrderProgressPage(ProgressDetailCancelPage):
    def __init__(self) -> None:
        self.driver = OrdinaryOrderProgressDriver()


class ExtendedProgressLabelDriver(ProgressDetailCancelDriver):
    page_source = "订单详情 查看订单进度详情说明"

    def find_elements(self, by, selector):
        if "contains" in selector and "查看订单进度详情" in selector:
            return [FakeElement("查看订单进度详情说明")]
        return []


class ExtendedProgressLabelPage(ProgressDetailCancelPage):
    def __init__(self) -> None:
        self.driver = ExtendedProgressLabelDriver()


class MerchantExplanationCancelDriver(PendingMerchantCancelDriver):
    page_source = "取消说明：提交取消后将待商家处理"

    def find_elements(self, by, selector):
        if "contains" in selector and "待商家处理" in selector:
            return [FakeElement("取消说明：提交取消后将待商家处理")]
        return []


class MerchantExplanationCancelPage(PendingMerchantCancelPage):
    def __init__(self) -> None:
        self.driver = MerchantExplanationCancelDriver()

    def _cancel_order_entry_still_visible(self):
        return False


class MissingCancelActionWithoutStatusDriver(PendingMerchantCancelDriver):
    page_source = "订单详情"


class MissingCancelActionWithoutStatusPage(PendingMerchantCancelPage):
    def __init__(self) -> None:
        self.driver = MissingCancelActionWithoutStatusDriver()


class FailingNativeRestoreSwitch:
    def __init__(self, driver) -> None:
        self.driver = driver

    def context(self, context_name):
        if context_name == "NATIVE_APP" and self.driver.current_context != "NATIVE_APP":
            raise RuntimeError("native restore unavailable")
        self.driver.current_context = context_name


class WebviewProgressCancelDriver:
    contexts = ["NATIVE_APP", "WEBVIEW_takeout"]
    current_context = "NATIVE_APP"
    page_source = "订单详情"

    def __init__(self) -> None:
        self.switch_to = FailingNativeRestoreSwitch(self)

    def find_elements(self, by, selector):
        if self.current_context == "WEBVIEW_takeout" and "订单进度详情" in selector:
            return [FakeElement("订单进度详情")]
        return []


class WebviewProgressCancelPage(TakeoutCancelOrderMixin):
    def __init__(self) -> None:
        self.driver = WebviewProgressCancelDriver()

    def _cancel_order_entry_still_visible(self):
        return False


class SecondNativeRestoreFailsSwitch(FailingNativeRestoreSwitch):
    def __init__(self, driver) -> None:
        super().__init__(driver)
        self.native_restore_count = 0

    def context(self, context_name):
        if context_name == "NATIVE_APP" and self.driver.current_context != "NATIVE_APP":
            self.native_restore_count += 1
            if self.native_restore_count >= 2:
                raise RuntimeError("second native restore unavailable")
        self.driver.current_context = context_name


class LateRestoreFailureDriver(WebviewProgressCancelDriver):
    def __init__(self) -> None:
        self.switch_to = SecondNativeRestoreFailsSwitch(self)


class LateRestoreFailurePage(TakeoutCancelOrderMixin):
    def __init__(self) -> None:
        self.driver = LateRestoreFailureDriver()

    def _window_size_safe(self):
        return 1080, 2270


class CancelEntryQueryUnavailableDriver:
    contexts = []
    current_context = "WEBVIEW_takeout"
    page_source = "订单详情"

    def __init__(self) -> None:
        self.switch_to = FailingNativeRestoreSwitch(self)


class CancelEntryQueryUnavailablePage(TakeoutCancelOrderMixin):
    def __init__(self) -> None:
        self.driver = CancelEntryQueryUnavailableDriver()

    def _window_size_safe(self):
        return 1080, 2270


class CancelContextQueryUnavailableDriver:
    current_context = "NATIVE_APP"
    page_source = "订单详情"

    @property
    def contexts(self):
        raise RuntimeError("contexts unavailable")

    def find_elements(self, by, selector):
        return []


class CancelContextQueryUnavailablePage(TakeoutCancelOrderMixin):
    def __init__(self) -> None:
        self.driver = CancelContextQueryUnavailableDriver()

    def _window_size_safe(self):
        return 1080, 2270


def test_cancel_submit_uses_the_real_flutter_sheet_height_first(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_cancel_order_mixin.time.sleep", lambda _: None)
    page = CoordinateOnlyCancelSubmitPage()

    assert page._tap_native_submit_cancel_sheet()
    assert page.driver.taps[0] == (540, int(2270 * 0.66))


def test_cancel_result_accepts_pending_merchant_confirmation(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_cancel_order_mixin.time.sleep", lambda _: None)
    page = PendingMerchantCancelPage()

    assert page._wait_cancel_result_after_submit(timeout=1.0)


def test_cancel_result_rejects_pending_merchant_explanation(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_cancel_order_mixin.time.sleep", lambda _: None)
    page = MerchantExplanationCancelPage()

    assert not page._wait_cancel_result_after_submit(timeout=0.01)


def test_cancel_result_rejects_missing_action_without_explicit_status(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_cancel_order_mixin.time.sleep", lambda _: None)
    page = MissingCancelActionWithoutStatusPage()

    assert not page._wait_cancel_result_after_submit(timeout=0.01)


def test_cancel_result_accepts_order_progress_detail_entry(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_cancel_order_mixin.time.sleep", lambda _: None)
    page = ProgressDetailCancelPage()

    assert page._wait_cancel_result_after_submit(timeout=1.0)


def test_cancel_result_rejects_progress_detail_while_cancel_action_is_visible(
    monkeypatch,
) -> None:
    monkeypatch.setattr("pages.takeout_cancel_order_mixin.time.sleep", lambda _: None)
    page = ActiveOrderProgressDetailPage()

    assert not page._wait_cancel_result_after_submit(timeout=0.01)


def test_cancel_result_rejects_generic_order_progress_label(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_cancel_order_mixin.time.sleep", lambda _: None)
    page = OrdinaryOrderProgressPage()

    assert not page._wait_cancel_result_after_submit(timeout=0.01)


def test_cancel_result_requires_exact_progress_detail_label(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_cancel_order_mixin.time.sleep", lambda _: None)
    page = ExtendedProgressLabelPage()

    assert not page._wait_cancel_result_after_submit(timeout=0.01)


def test_cancel_result_rejects_webview_progress_when_native_restore_fails() -> None:
    page = WebviewProgressCancelPage()

    assert not page._cancel_progress_detail_entry_visible()


def test_cancel_result_rejects_progress_when_post_check_restore_fails() -> None:
    page = LateRestoreFailurePage()

    assert not page._cancel_progress_detail_entry_visible()


def test_cancel_action_query_failure_is_not_treated_as_absent() -> None:
    page = CancelEntryQueryUnavailablePage()

    assert page._cancel_order_entry_still_visible()


def test_cancel_context_query_failure_is_not_treated_as_absent() -> None:
    page = CancelContextQueryUnavailablePage()

    assert page._cancel_order_entry_still_visible()


def test_address_selection_supports_an_optional_match_guard(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = AddressPage(
        [
            FakeElement("Alice Manila 09123456789"),
            FakeElement("Accounting Support Manila 09621170994"),
        ]
    )

    assert page.shop_pick_address_in_sheet(
        address_ordinal=2,
        address_contains="70994",
    )
    assert page.clicked == ["Accounting Support Manila 09621170994"]


def test_address_selection_rejects_when_the_ordinal_fails_the_optional_guard(
    monkeypatch,
) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = AddressPage(
        [
            FakeElement("First Manila 09111111111"),
            FakeElement("Accounting Support Manila 09621170994"),
        ]
    )

    assert not page.shop_pick_address_in_sheet(
        address_ordinal=1,
        address_contains="70994",
    )
    assert page.clicked == []


def test_address_selection_retries_transiently_missing_readback(
    monkeypatch,
) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = DelayedAddressReadbackPage(
        [FakeElement("Accounting Support app 09621170994")],
        [False, True],
    )

    assert page.shop_pick_address_in_sheet(
        address_ordinal=1,
        address_contains="app 09621170994",
    )
    assert page.readbacks == []


def test_address_selection_accepts_the_automatic_payment_sheet_transition(
    monkeypatch,
) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = PaymentSheetAfterAddressPage(
        [FakeElement("First Manila 09111111111")]
    )

    assert page.shop_pick_address_in_sheet(address_ordinal=1)
    assert page.clicked == ["First Manila 09111111111"]


def test_address_selection_confirms_missing_phone_before_payment_sheet(
    monkeypatch,
) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = MissingPhoneAfterAddressPage(
        [FakeElement("First Manila 09111111111")]
    )

    assert page.shop_pick_address_in_sheet(address_ordinal=1)
    assert page.confirmed_missing_phone


def test_address_selection_uses_the_requested_one_based_ordinal(
    monkeypatch,
) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = AddressPage(
        [
            FakeElement("First Manila 09111111111", y=300),
            FakeElement("Second Manila 09222222222", y=500),
        ]
    )

    assert page.shop_pick_address_in_sheet(address_ordinal=2)
    assert page.clicked == ["Second Manila 09222222222"]


def test_address_selection_rejects_an_ordinal_beyond_the_existing_list(
    monkeypatch,
) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = AddressPage([FakeElement("Only Manila 09111111111")])

    assert not page.shop_pick_address_in_sheet(address_ordinal=2)
    assert page.clicked == []


def test_delivery_hint_never_falls_back_to_an_unmatched_slot() -> None:
    page = TakeoutDeliveryTimeMixin()
    slots = [FakeElement("00:40"), FakeElement("01:20", y=600)]

    picked, tag = page._pick_delivery_time_slot_element(
        slots,
        preferred_slot_contains="01:40",
        slot_ordinal_1based=None,
    )

    assert picked is None
    assert "01:40" in tag


class StrictDeliveryPage(TakeoutDeliveryTimeMixin):
    def __init__(self) -> None:
        self.fallback_labels = []

    def _window_size_safe(self):
        return 1080, 2200

    def _scroll_checkout_reveal_delivery_strong(self, w, h):
        return None

    def _scroll_checkout_form_reveal_delivery(self, w, h):
        return None

    def _open_delivery_time_picker_sheet(self, w, h, *, prefer_scheduled=False):
        return True

    def _maybe_zero_implicit_wait(self):
        return nullcontext()

    def _tap_day_after_tomorrow_date_in_sheet(self):
        return False

    def _tap_first_displayed(self, by, selector):
        self.fallback_labels.append(selector)
        return True


def test_delivery_selection_stops_when_day_after_tomorrow_is_missing(
    monkeypatch,
) -> None:
    monkeypatch.setattr("pages.takeout_delivery_time_mixin.time.sleep", lambda _: None)
    page = StrictDeliveryPage()

    assert not page.shop_open_delivery_time_and_pick_future_slot(
        preferred_slot_contains="01:40"
    )
    assert not any("明天" in selector or "今天" in selector for selector in page.fallback_labels)


def test_shop_opening_stops_when_required_manila_selection_fails(monkeypatch) -> None:
    calls = []

    class FakePage:
        def __init__(self, driver):
            pass

        def ensure_takeout_city_manila(self):
            calls.append("manila")
            return False

        def ensure_takeout_tab(self):
            calls.append("tab")
            return True

        def wait_merchant_list_present(self, timeout):
            calls.append("list")
            return True

        def scroll_to_and_open_shop(self, **kwargs):
            calls.append("shop")
            return True

    monkeypatch.setattr(takeout_page, "TakeoutPageBase", FakePage)

    assert not takeout_page.open_wangwang_supermarket_from_takeout_home(
        object(), ensure_manila_city=True
    )
    assert calls == ["manila"]


class ClickableText:
    def __init__(self) -> None:
        self.clicked = False

    def is_displayed(self) -> bool:
        return True

    def click(self) -> None:
        self.clicked = True


class LocationPermissionDriver:
    page_source = '<node text="定位权限未开启" />'

    def __init__(self) -> None:
        self.cancel = ClickableText()

    def find_elements(self, by, value):
        if value.endswith(":id/tv_cancel"):
            return [self.cancel]
        return []


def test_location_selection_dismisses_the_optional_permission_prompt(
    monkeypatch,
) -> None:
    monkeypatch.setattr("pages.takeout_page.time.sleep", lambda _: None)
    driver = LocationPermissionDriver()
    page = takeout_page.TakeoutPageBase(driver)

    assert page._dismiss_location_permission_prompt_if_present()
    assert driver.cancel.clicked
