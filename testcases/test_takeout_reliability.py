from __future__ import annotations

from contextlib import nullcontext

from pages.takeout_checkout_mixin import TakeoutCheckoutMixin
from pages.takeout_address import TakeoutAddressData
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


class CoordinateOnlyAddressDriver:
    def __init__(self) -> None:
        self.clicked = False
        self.element = FakeElement("保存", y=1900, x=100)

    def find_elements(self, by, selector):
        return [self.element] if "保存" in selector else []

    def execute_script(self, name, payload):
        self.clicked = True


class CoordinateOnlyAddressPage(TakeoutCheckoutMixin):
    def __init__(self) -> None:
        self.driver = CoordinateOnlyAddressDriver()

    def _window_height(self):
        return 2400


class RetrySavePage(TakeoutCheckoutMixin):
    def __init__(self) -> None:
        self.save_clicks = 0
        self.driver = self

    @property
    def page_source(self):
        if self.save_clicks >= 2:
            return "配送至 新增地址 保存成功"
        return "新增收货地址 地址图片 联系人姓名 联系人电话 保存"

    def hide_keyboard(self):
        return None

    def _shop_click_address_labels(self, labels):
        if "保存" in labels:
            self.save_clicks += 1
            return True
        return False


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


class PolicyAddressPage(TakeoutCheckoutMixin):
    def __init__(self, *, existing_result: bool, add_result: bool) -> None:
        self.existing_result = existing_result
        self.add_result = add_result
        self.events = []

    def shop_pick_address_in_sheet(self, **kwargs):
        self.events.append(("existing", kwargs))
        return self.existing_result

    def shop_add_address_from_sheet(self, data):
        self.events.append(("add", data))
        return self.add_result


class AddressCreatePage(TakeoutCheckoutMixin):
    def __init__(self, *, fail_stage: str | None = None) -> None:
        self.fail_stage = fail_stage
        self.events = []

    def _shop_open_add_address_form(self):
        self.events.append("open")
        return self.fail_stage != "open"

    def _shop_select_new_address_location(self, data):
        self.events.append("location")
        return self.fail_stage != "location"

    def _shop_fill_new_address_form(self, data):
        self.events.append("fill")
        return self.fail_stage != "fill"

    def _shop_upload_first_gallery_photo(self):
        self.events.append("photo")
        return self.fail_stage != "photo"

    def _shop_save_new_address(self):
        self.events.append("save")
        return self.fail_stage != "save"

    def _shop_verify_new_address(self, data):
        self.events.append("verify")
        return self.fail_stage != "verify"


class AddressUiElement:
    def __init__(self, driver, label, action=None, *, y=600) -> None:
        self.driver = driver
        self.label = label
        self.action = action
        self.location = {"x": 100, "y": y}
        self.size = {"width": 700, "height": 80}

    def is_displayed(self):
        return True

    def get_attribute(self, name):
        if name in ("text", "content-desc", "hint"):
            return self.label
        if name == "className":
            return "android.widget.EditText" if "input" in self.label else "android.view.View"
        return ""

    def click(self):
        if self.action:
            self.action()

    def clear(self):
        return None

    def send_keys(self, value):
        if self.driver.state == "search":
            self.driver.search_value = value
        elif self.driver.active_field:
            self.driver.values[self.driver.active_field] = value


class AddressUiDriver:
    def __init__(self, *, result_count=1) -> None:
        self.state = "sheet"
        self.result_count = result_count
        self.search_value = ""
        self.active_field = None
        self.values = {}
        self.save_clicked = False
        self.hide_keyboard_calls = 0

    @property
    def page_source(self):
        if self.state == "sheet":
            return "配送至 + 新增地址"
        if self.state == "search":
            return "定位地址 如有大厦、街道名称，请直接搜索"
        if self.state == "results":
            return "定位地址 " + " ".join(["Robinsons Place Manila"] * self.result_count)
        if self.state == "form":
            return "新增收货地址 联系人 手机号 详细地址 保存"
        if self.state == "address_list":
            return "配送至 + 新增地址 Automation Contact 09171234567 Unit 8 test address"
        return "选择支付方式 Automation Contact 09171234567"

    def get_window_size(self):
        return {"width": 1080, "height": 2200}

    def find_elements(self, by, selector):
        if self.state == "sheet" and "新增地址" in selector:
            return [AddressUiElement(self, "新增地址", lambda: setattr(self, "state", "search"))]
        if self.state == "search" and "EditText" in selector:
            return [AddressUiElement(self, "search input", y=180)]
        if self.state == "results" and "Robinsons Place Manila" in selector:
            return [
                AddressUiElement(
                    self,
                    f"Robinsons Place Manila result {index}",
                    lambda: setattr(self, "state", "form"),
                    y=500 + index * 120,
                )
                for index in range(self.result_count)
            ]
        if self.state == "form":
            fields = (
                (("联系人", "收货人", "姓名"), "contact"),
                (("手机号", "手机号码", "联系电话"), "phone"),
                (("详细地址", "地址详情", "门牌号"), "detail"),
            )
            for labels, field in fields:
                if any(label in selector for label in labels) and "EditText" in selector:
                    self.active_field = field
                    return [AddressUiElement(self, f"{field} input")]
            if "保存" in selector:
                def save():
                    self.save_clicked = True
                    self.state = "address_list"
                return [AddressUiElement(self, "保存", save)]
        if self.state == "address_list" and "4567" in selector:
            return [
                AddressUiElement(
                    self,
                    "Automation Contact 09171234567 Unit 8 test address",
                    lambda: setattr(self, "state", "payment"),
                )
            ]
        return []

    def press_keycode(self, keycode):
        if keycode == 66 and self.search_value:
            self.state = "results"

    def hide_keyboard(self):
        self.hide_keyboard_calls += 1


class RealAddressUiPage(TakeoutCheckoutMixin):
    def __init__(self, *, result_count=1) -> None:
        self.driver = AddressUiDriver(result_count=result_count)

    def _window_height(self):
        return 2200

    def _coord_tap_or_click(self, element, description):
        element.click()
        return True

    def _shop_upload_first_gallery_photo(self):
        return True


class GalleryUploadDriver:
    def __init__(self) -> None:
        self.state = "form"
        self.selected = []
        self.events = []
        self.photo_taps = []

    @property
    def current_package(self):
        return "com.bs.feifubao"

    @property
    def page_source(self):
        return {
            "form": "新增收货地址 地址图片 + 联系人姓名 联系人电话 保存",
            "custom_permission": "系统提示 允许筷子生活获取存储权限 以便于您选取照片 确定",
            "runtime_permission": "是否允许筷子生活访问设备上的照片和视频 拒绝 始终允许",
            "gallery": "Recent 最近 照片 相册",
            "preview": "选择",
            "selected_preview": "选择 确定 最多选取1项",
            "filled": "新增收货地址 地址图片 已上传图片 联系人姓名 联系人电话 保存",
        }[self.state]

    def find_elements(self, by, selector):
        if self.state == "form" and "地址图片" in selector:
            return [AddressUiElement(self, "地址图片", y=650)]
        if self.state == "custom_permission" and "确定" in selector:
            return [
                AddressUiElement(
                    self,
                    "确定",
                    lambda: self._advance("custom_permission", "runtime_permission"),
                )
            ]
        if self.state == "runtime_permission" and "始终允许" in selector:
            return [
                AddressUiElement(
                    self,
                    "始终允许",
                    lambda: self._advance("runtime_permission", "gallery"),
                )
            ]
        if self.state == "gallery" and selector == "android.widget.ImageView":
            return [
                AddressUiElement(self, "相机", y=500),
                AddressUiElement(
                    self,
                    "first gallery photo",
                    self._select_first,
                    y=500,
                    x=350,
                ),
                AddressUiElement(self, "second gallery photo", y=800, x=650),
            ]
        if self.state == "preview" and "选择" in selector:
            return [
                AddressUiElement(
                    self,
                    "选择",
                    lambda: self._advance("preview", "selected_preview"),
                )
            ]
        if self.state == "selected_preview" and "确定" in selector:
            return [
                AddressUiElement(
                    self,
                    "确定",
                    lambda: self._advance("selected_preview", "filled"),
                )
            ]
        return []

    def get_window_size(self):
        return {"width": 1080, "height": 2400}

    def execute_script(self, name, payload):
        if self.state == "form":
            self.events.append("plus")
            self.photo_taps.append((payload["x"], payload["y"]))
            self.state = "custom_permission"
        elif self.state == "gallery":
            self._select_first()

    def _advance(self, event, state):
        self.events.append(event)
        self.state = state

    def _select_first(self):
        self.selected.append("first")
        self.state = "preview"


class GalleryUploadPage(TakeoutCheckoutMixin):
    def __init__(self) -> None:
        self.driver = GalleryUploadDriver()

    def _window_height(self):
        return 2400

    def _coord_tap_or_click(self, element, description):
        element.click()
        return True


class ScrolledGalleryUploadDriver(GalleryUploadDriver):
    def find_elements(self, by, selector):
        if self.state == "form" and "地址图片" in selector:
            return []
        return super().find_elements(by, selector)

    def execute_script(self, name, payload):
        if self.state == "form":
            self.photo_taps.append((payload["x"], payload["y"]))
            if payload["y"] > 800:
                self.events.append("plus")
                self.state = "custom_permission"
            return
        super().execute_script(name, payload)


class ScrolledGalleryUploadPage(GalleryUploadPage):
    def __init__(self) -> None:
        self.driver = ScrolledGalleryUploadDriver()


class CompositeAddEntryDriver:
    def __init__(self) -> None:
        self.state = "sheet"
        self.taps = []

    @property
    def page_source(self):
        if self.state == "sheet":
            return "配送至\n新增地址"
        return "定位地址 如有大厦、街道名称，请直接搜索"

    def find_elements(self, by, selector):
        return []

    def get_window_size(self):
        return {"width": 1080, "height": 2270}

    def execute_script(self, name, payload):
        self.taps.append((payload["x"], payload["y"]))
        if payload["y"] >= 2000:
            self.state = "search"


class CompositeAddEntryPage(TakeoutCheckoutMixin):
    def __init__(self) -> None:
        self.driver = CompositeAddEntryDriver()

    def _window_height(self):
        return 2270


class DelayedCompositeAddEntryDriver(CompositeAddEntryDriver):
    def __init__(self) -> None:
        super().__init__()
        self.loading_reads_remaining = 20

    @property
    def page_source(self):
        if self.state == "sheet":
            return "配送至\n新增地址"
        if self.loading_reads_remaining > 0:
            self.loading_reads_remaining -= 1
            return "地图加载中"
        return "定位地址 如有大厦、街道名称，请直接搜索"


class DelayedCompositeAddEntryPage(TakeoutCheckoutMixin):
    def __init__(self) -> None:
        self.driver = DelayedCompositeAddEntryDriver()

    def _window_height(self):
        return 2270


class StickyCompositeAddEntryDriver(CompositeAddEntryDriver):
    def execute_script(self, name, payload):
        self.taps.append((payload["x"], payload["y"]))


class FocusRequiredSearchDriver(AddressUiDriver):
    def __init__(self) -> None:
        super().__init__()
        self.state = "search"
        self.search_focused = False
        self.taps = []

    def find_elements(self, by, selector):
        if self.state == "search" and "EditText" in selector and not self.search_focused:
            return []
        return super().find_elements(by, selector)

    def execute_script(self, name, payload):
        self.taps.append((payload["x"], payload["y"]))
        if payload["y"] < 500:
            self.search_focused = True

    def get_window_size(self):
        return {"width": 1080, "height": 2270}


class PartialAddressResultDriver:
    def __init__(self) -> None:
        self.match = FakeElement(
            "Feidu Consulting Services Inc 2515 Syquia St, Barangay 884"
        )

    def find_elements(self, by, selector):
        if "2515 Syquia" in selector:
            return [self.match]
        return []


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


class CoordinateCancelReasonDriver:
    contexts = []
    current_context = "NATIVE_APP"
    page_source = "取消订单"

    def __init__(self, page) -> None:
        self.page = page
        self.taps = []

    def find_elements(self, by, selector):
        return []

    def find_element(self, by, selector):
        raise RuntimeError("canvas has no semantic reason nodes")

    def execute_script(self, name, payload):
        tap = (payload["x"], payload["y"])
        self.taps.append(tap)
        if tap == (int(1080 * 0.824), int(2270 * 0.408)):
            self.page.reason_selected = True
        if tap == (540, int(2270 * 0.66)) and self.page.reason_selected:
            self.page.modal_visible = False


class CoordinateCancelReasonPage(TakeoutCancelOrderMixin):
    def __init__(self) -> None:
        self.modal_visible = True
        self.reason_selected = False
        self.driver = CoordinateCancelReasonDriver(self)

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


class ProgressDetailEntryElement(FakeElement):
    def __init__(self, driver) -> None:
        super().__init__("查看进度详情")
        self.driver = driver

    def click(self) -> None:
        self.driver.progress_opened = True
        self.driver.page_source = "订单跟踪 申请取消订单 原因:收货信息填错了"


class ProgressDetailCancelDriver:
    contexts = ["NATIVE_APP"]
    current_context = "NATIVE_APP"

    def __init__(self) -> None:
        self.page_source = "订单详情 查看进度详情"
        self.progress_opened = False

    def find_elements(self, by, selector):
        if "查看进度详情" in selector:
            return [ProgressDetailEntryElement(self)]
        if self.progress_opened and "申请取消订单" in selector:
            return [FakeElement("申请取消订单")]
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


class CanvasOrderDetailDriver:
    contexts = ["NATIVE_APP"]
    current_context = "NATIVE_APP"

    def __init__(self) -> None:
        self.page_source = "订单详情"
        self.taps = []

    def find_elements(self, by, selector):
        return []

    def execute_script(self, name, payload):
        self.taps.append((payload["x"], payload["y"]))
        if (payload["x"], payload["y"]) == (
            int(1080 * 0.60),
            int(2270 * 0.32),
        ):
            self.page_source = "取消订单 您确定取消该订单么 确定取消 点错了"


class CanvasOrderDetailCancelPage(TakeoutCancelOrderMixin):
    def __init__(self) -> None:
        self.driver = CanvasOrderDetailDriver()
        self.confirmed = False

    def _window_size_safe(self):
        return 1080, 2270

    def _log_contexts(self, stage=""):
        return None

    def _tap_first_displayed(self, by, selector):
        if "确定取消" in selector and "您确定取消该订单么" in self.driver.page_source:
            self.confirmed = True
            return True
        return False

    def _choose_cancel_reason_then_submit(self, reason):
        return self.confirmed

    def _cancel_reason_modal_title_visible(self):
        return False

    def _wait_cancel_result_after_submit(self, timeout=12.0):
        return self.confirmed


class BoundedMissingCategoryPage(TakeoutCheckoutMixin):
    def __init__(self) -> None:
        self.quick_scans = []
        self.category_attempts = []

    def _window_size_safe(self):
        return 1080, 2270

    def _try_tap_exact_sidebar_view_if_visible(self, category_desc, screen_w):
        return False

    def _reset_shop_category_sidebar_to_top(self, w, h, category_desc):
        return None

    def _left_sidebar_quick_scan_for_category(
        self, category_desc, left_max_x, w, h, *, max_steps=20
    ):
        self.quick_scans.append((category_desc, max_steps))
        return False

    def _try_sidebar_scrollview_scroll_into_then_tap(self, *args, **kwargs):
        raise AssertionError("bounded category lookup must not use blocking scrollIntoView")

    def _try_sidebar_category_ultralight(self, *args, **kwargs):
        raise AssertionError("bounded category lookup must not use blocking UiAutomator")

    def _try_tap_left_rail_uia_needle(self, *args, **kwargs):
        raise AssertionError("bounded category lookup must not use UiAutomator needles")

    def _uia_scroll_sidebar_scroll_into_view(self, *args, **kwargs):
        raise AssertionError("bounded category lookup must not use UiScrollable")

    def _shop_detail_scroll_to_category_once(self, category_desc, *, deep=True):
        self.category_attempts.append(category_desc)
        return super()._shop_detail_scroll_to_category_once(category_desc, deep=deep)


class BoundedSidebarScanPage(TakeoutCheckoutMixin):
    def __init__(self) -> None:
        self.source_checks = 0
        self.swipes = 0

    def _try_tap_sidebar_category_from_page_source(self, *args, **kwargs):
        self.source_checks += 1
        return False

    def _try_tap_sidebar_category_loose_xpath(self, *args, **kwargs):
        raise AssertionError("bounded category scan must not issue missing XPath queries")

    def _scroll_shop_category_sidebar_once(self, *args, **kwargs):
        self.swipes += 1

    def _try_sidebar_category_ultralight(self, *args, **kwargs):
        raise AssertionError("sidebar scan must not use blocking UiAutomator")

    def _try_tap_left_rail_uia_needle(self, *args, **kwargs):
        raise AssertionError("sidebar scan must not use UiAutomator needles")

    def _uia_scroll_sidebar_scroll_into_view(self, *args, **kwargs):
        raise AssertionError("sidebar scan must not use UiScrollable")


class CategorySourceDriver:
    page_source = (
        '<hierarchy>'
        '<android.view.View content-desc="健康粮油商品" text="" '
        'bounds="[260,400][1040,620]" />'
        '<android.view.View content-desc="米面粮油" text="" '
        'bounds="[0,520][160,660]" />'
        '</hierarchy>'
    )

    def __init__(self) -> None:
        self.taps = []

    def execute_script(self, name, payload):
        self.taps.append((payload["x"], payload["y"]))


class CategorySourcePage(TakeoutCheckoutMixin):
    def __init__(self) -> None:
        self.driver = CategorySourceDriver()


class MissingCheckoutPreferencesPage(TakeoutCheckoutMixin):
    def _checkout_scroll_until_visible(self, labels, *, max_rounds=6):
        return False


def test_cancel_submit_uses_the_real_flutter_sheet_height_first(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_cancel_order_mixin.time.sleep", lambda _: None)
    page = CoordinateOnlyCancelSubmitPage()

    assert page._tap_native_submit_cancel_sheet()
    assert page.driver.taps[0] == (540, int(2270 * 0.66))


def test_canvas_cancel_reason_taps_the_real_radio_before_submit(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_cancel_order_mixin.time.sleep", lambda _: None)
    page = CoordinateCancelReasonPage()

    assert page._choose_cancel_reason_then_submit("点多了/点错了/点少了")
    assert page.driver.taps[:2] == [
        (int(1080 * 0.824), int(2270 * 0.408)),
        (540, int(2270 * 0.66)),
    ]


def test_canvas_order_detail_falls_back_to_guarded_cancel_coordinate(
    monkeypatch,
) -> None:
    monkeypatch.setattr("pages.takeout_cancel_order_mixin.time.sleep", lambda _: None)
    page = CanvasOrderDetailCancelPage()

    assert page.shop_assert_order_detail_cancel_visible(timeout=0.01)
    assert page.shop_cancel_order_flow()
    assert page.driver.taps == [(int(1080 * 0.60), int(2270 * 0.32))]


def test_missing_category_uses_only_bounded_sidebar_scan(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = BoundedMissingCategoryPage()

    assert not page._shop_detail_scroll_to_category_once("健康粮油", deep=True)
    assert page.quick_scans == [("健康粮油", 12)]


def test_health_grain_category_does_not_repeat_implicit_alias_scans(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = BoundedMissingCategoryPage()

    assert not page.shop_detail_scroll_to_category("健康粮油")
    assert page.category_attempts == ["健康粮油"]


def test_sidebar_scan_avoids_blocking_uiautomator_queries(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = BoundedSidebarScanPage()

    assert not page._left_sidebar_quick_scan_for_category(
        "健康粮油", 475, 1080, 2270, max_steps=3
    )
    assert page.source_checks == 4
    assert page.swipes == 3


def test_category_source_scan_taps_left_grain_category_not_product(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = CategorySourcePage()

    assert page._try_tap_sidebar_category_from_page_source("健康粮油", 1080, 2270)
    assert page.driver.taps == [(80, 590)]


def test_explicit_checkout_preferences_fail_when_regions_are_missing() -> None:
    page = MissingCheckoutPreferencesPage()

    assert not page.shop_set_pickup_code("on")
    assert not page.shop_set_notify_method("phone")
    assert page.shop_set_pickup_code("keep")
    assert page.shop_set_notify_method("keep")


def test_phone_notification_requires_an_address_with_phone() -> None:
    page = TakeoutCheckoutMixin()

    assert page._checkout_requires_phone_address("balance", "phone")
    assert page._checkout_requires_phone_address("cod", "keep")
    assert not page._checkout_requires_phone_address("balance", "app")


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
    assert page.driver.progress_opened


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


def test_auto_address_adds_only_after_existing_selection_fails() -> None:
    data = TakeoutAddressData("Contact", "09171234567", "Place", "Unit 8")
    page = PolicyAddressPage(existing_result=False, add_result=True)

    assert page.shop_ensure_address_in_sheet(
        address_policy="auto",
        address_data=data,
        address_ordinal=1,
        address_contains=None,
        require_phone=True,
    )
    assert [event[0] for event in page.events] == ["existing", "add"]


def test_existing_address_policy_never_creates_persistent_address() -> None:
    data = TakeoutAddressData("Contact", "09171234567", "Place", "Unit 8")
    page = PolicyAddressPage(existing_result=False, add_result=True)

    assert not page.shop_ensure_address_in_sheet(
        address_policy="existing",
        address_data=data,
        address_ordinal=1,
        address_contains=None,
        require_phone=True,
    )
    assert [event[0] for event in page.events] == ["existing"]


def test_add_address_policy_skips_existing_address_selection() -> None:
    data = TakeoutAddressData("Contact", "09171234567", "Place", "Unit 8")
    page = PolicyAddressPage(existing_result=True, add_result=True)

    assert page.shop_ensure_address_in_sheet(
        address_policy="add",
        address_data=data,
        address_ordinal=1,
        address_contains=None,
        require_phone=True,
    )
    assert [event[0] for event in page.events] == ["add"]


def test_new_address_is_not_successful_until_saved_address_is_verified() -> None:
    data = TakeoutAddressData("Contact", "09171234567", "Place", "Unit 8")
    page = AddressCreatePage()

    assert page.shop_add_address_from_sheet(data)
    assert page.events == ["open", "location", "fill", "photo", "save", "verify"]


def test_new_address_stops_at_failed_location_selection() -> None:
    data = TakeoutAddressData("Contact", "09171234567", "Place", "Unit 8")
    page = AddressCreatePage(fail_stage="location")

    assert not page.shop_add_address_from_sheet(data)
    assert page.events == ["open", "location"]


def test_new_address_rejects_missing_data_before_opening_form() -> None:
    page = AddressCreatePage()

    assert not page.shop_add_address_from_sheet(TakeoutAddressData())
    assert page.events == []


def test_new_address_ui_fills_saves_and_reads_back_without_manual_steps(
    monkeypatch,
) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    data = TakeoutAddressData(
        "Automation Contact",
        "09171234567",
        "Robinsons Place Manila",
        "Unit 8 test address",
    )
    page = RealAddressUiPage()

    assert page.shop_add_address_from_sheet(data)
    assert page.driver.values == {
        "contact": "Automation Contact",
        "phone": "09171234567",
        "detail": "Unit 8 test address",
    }
    assert page.driver.save_clicked
    # Once after location search, once after each of the three form fields,
    # and once before Save.
    assert page.driver.hide_keyboard_calls == 5


def test_new_address_ui_rejects_ambiguous_location_results(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    data = TakeoutAddressData(
        "Automation Contact",
        "09171234567",
        "Robinsons Place Manila",
        "Unit 8 test address",
    )
    page = RealAddressUiPage(result_count=2)

    assert not page.shop_add_address_from_sheet(data)
    assert not page.driver.save_clicked


def test_address_photo_upload_selects_first_visible_gallery_image(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = GalleryUploadPage()

    assert page._shop_upload_first_gallery_photo()
    assert page.driver.selected == ["first"]
    assert page.driver.state == "filled"
    assert page.driver.photo_taps[0][1] > 700
    assert page.driver.events == [
        "plus",
        "custom_permission",
        "runtime_permission",
        "preview",
        "selected_preview",
    ]


def test_address_photo_retries_scrolled_plus_position_when_keyboard_state_lies(
    monkeypatch,
) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = ScrolledGalleryUploadPage()

    assert page._shop_upload_first_gallery_photo()
    assert [tap[1] for tap in page.driver.photo_taps[:2]] == [504, 936]


def test_address_label_click_uses_coordinate_for_flutter_button() -> None:
    page = CoordinateOnlyAddressPage()

    assert page._shop_click_address_labels(("保存",))
    assert page.driver.clicked


def test_address_save_retries_once_when_first_flutter_tap_has_no_effect(
    monkeypatch,
) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = RetrySavePage()

    assert page._shop_save_new_address()
    assert page.save_clicks == 2


def test_composite_flutter_address_sheet_uses_scoped_add_button_fallback(
    monkeypatch,
) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = CompositeAddEntryPage()

    assert page._shop_open_add_address_form()
    assert page.driver.taps == [(540, 2088)]


def test_add_address_entry_waits_for_slow_map_page(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = DelayedCompositeAddEntryPage()

    assert page._shop_open_add_address_form()


def test_composite_add_fallback_rejects_unchanged_address_sheet(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = CompositeAddEntryPage()
    page.driver = StickyCompositeAddEntryDriver()

    assert not page._shop_open_add_address_form()


def test_location_search_focuses_visual_search_bar_before_typing(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    data = TakeoutAddressData(
        "Automation Contact",
        "09171234567",
        "Robinsons Place Manila",
        "Unit 8 test address",
    )
    page = RealAddressUiPage()
    page.driver = FocusRequiredSearchDriver()

    assert page._shop_select_new_address_location(data)
    assert page.driver.taps == [(540, 295)]
    assert page.driver.search_value == "Robinsons Place Manila"


def test_location_result_uses_unique_house_and_street_fragment() -> None:
    page = TakeoutCheckoutMixin()
    page.driver = PartialAddressResultDriver()
    page._window_height = lambda: 2270

    result = page._shop_find_unique_location_result_for_query(
        "2515 Syquia, Santa Ana, Maynila, Kalakhang Maynila",
        attempts=1,
    )

    assert result is page.driver.match


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


def test_cod_address_selection_skips_addresses_without_phone(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_checkout_mixin.time.sleep", lambda _: None)
    page = PaymentSheetAfterAddressPage(
        [
            FakeElement("First address without phone", y=300),
            FakeElement("Second Manila 09222222222", y=500),
        ]
    )

    assert page.shop_pick_address_in_sheet(
        address_ordinal=1,
        require_phone=True,
    )
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
        self.date_calls = []

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
        self.date_calls.append("后天")
        return False

    def _tap_tomorrow_date_in_sheet(self):
        self.date_calls.append("明天")
        return True

    def _tap_first_displayed(self, by, selector):
        self.fallback_labels.append(selector)
        return True


def test_delivery_date_falls_back_from_day_after_tomorrow_to_tomorrow() -> None:
    page = StrictDeliveryPage()

    assert page._tap_allowed_delivery_date_in_sheet() == "明天"
    assert page.date_calls == ["后天", "明天"]


def test_delivery_date_prefers_day_after_tomorrow() -> None:
    page = StrictDeliveryPage()
    page._tap_day_after_tomorrow_date_in_sheet = lambda: True

    assert page._tap_allowed_delivery_date_in_sheet() == "后天"
    assert page.date_calls == []


def test_delivery_date_rejects_when_neither_tomorrow_nor_day_after_exists() -> None:
    page = StrictDeliveryPage()
    page._tap_tomorrow_date_in_sheet = lambda: False

    assert page._tap_allowed_delivery_date_in_sheet() is None
    assert page.date_calls == ["后天"]


def test_delivery_selection_never_queries_today(
    monkeypatch,
) -> None:
    monkeypatch.setattr("pages.takeout_delivery_time_mixin.time.sleep", lambda _: None)
    page = StrictDeliveryPage()

    assert not page.shop_open_delivery_time_and_pick_future_slot(
        preferred_slot_contains="01:40"
    )
    assert not any("今天" in selector for selector in page.fallback_labels)


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


class AddressEditorRecoveryDriver:
    def __init__(self) -> None:
        self.states = ["form", "address_sheet", "checkout", "home"]
        self.index = 0
        self.hide_keyboard_calls = 0
        self.geometry_taps = []

    @property
    def page_source(self):
        return {
            "form": "新增收货地址 地址图片 联系人姓名 联系人电话",
            "address_sheet": "配送至 + 新增地址",
            "checkout": "提交订单 确认支付",
            "home": "外卖 商家列表",
        }[self.states[self.index]]

    def hide_keyboard(self):
        self.hide_keyboard_calls += 1

    def back(self):
        self.index = min(self.index + 1, len(self.states) - 1)

    def get_window_size(self):
        return {"width": 1080, "height": 2400}

    def find_elements(self, by, selector):
        if self.states[self.index] == "home" and "rv_merchant" in selector:
            return [ClickableText()]
        return []

    def execute_script(self, name, payload):
        self.geometry_taps.append((payload["x"], payload["y"]))


class PermissionChoice(ClickableText):
    def __init__(self, label, callback) -> None:
        super().__init__()
        self.label = label
        self.callback = callback

    def click(self) -> None:
        super().click()
        self.callback()


class LocationPermissionDriver:
    def __init__(self, state="runtime") -> None:
        self.state = state
        self.clicked = []
        self.current_package = (
            "com.android.settings" if state == "custom" else "com.bs.feifubao"
        )

    @property
    def page_source(self):
        return {
            "runtime": "精确位置 仅在使用中允许",
            "custom": "系统提示 请前往设置中心打开定位权限 以便继续操作! 确定",
            "immediate": "定位权限未开启 允许筷子生活获取位置信息 立即开启",
            "settings": "应用权限 位置信息",
            "location": "精确位置 仅在使用中允许",
            "granted": "定位地址 搜索收货地址",
        }[self.state]

    def find_elements(self, by, value):
        labels = (
            "精确位置",
            "仅在使用中允许",
            "确定",
            "立即开启",
            "应用权限",
            "位置信息",
        )
        available = {
            "runtime": {"精确位置", "仅在使用中允许"},
            "custom": {"确定"},
            "immediate": {"立即开启"},
            "settings": {"应用权限", "位置信息"},
            "location": {"精确位置", "仅在使用中允许"},
            "granted": set(),
        }[self.state]
        for label in labels:
            if label not in value or label not in available:
                continue

            def advance(label=label):
                self.clicked.append(label)
                if label == "确定":
                    self.state = "settings"
                    self.current_package = "com.android.settings"
                elif label == "立即开启":
                    self.state = "runtime"
                elif label in ("应用权限", "位置信息"):
                    self.state = "location"
                elif label == "仅在使用中允许":
                    self.state = "granted"

            return [PermissionChoice(label, advance)]
        return []

    def back(self):
        self.current_package = "com.bs.feifubao"

    def activate_app(self, package):
        self.current_package = package


def test_location_selection_grants_runtime_precise_permission(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_page.time.sleep", lambda _: None)
    driver = LocationPermissionDriver()
    page = takeout_page.TakeoutPageBase(driver)

    assert page._ensure_location_permission_enabled()
    assert driver.state == "granted"
    assert "精确位置" in driver.clicked
    assert "仅在使用中允许" in driver.clicked


def test_takeout_tab_recovers_from_address_editor_before_geometry_fallback(
    monkeypatch,
) -> None:
    monkeypatch.setattr("pages.takeout_page.time.sleep", lambda _: None)
    driver = AddressEditorRecoveryDriver()
    page = takeout_page.TakeoutPageBase(driver)

    assert page.ensure_takeout_tab(
        settle_sec=0,
        max_tab_clicks=1,
        wait_list_timeout=0,
    )
    assert driver.hide_keyboard_calls == 1
    assert driver.states[driver.index] == "home"
    assert driver.geometry_taps == []


def test_takeout_tab_recovers_from_composite_address_sheet_before_geometry_fallback(
    monkeypatch,
) -> None:
    monkeypatch.setattr("pages.takeout_page.time.sleep", lambda _: None)
    driver = AddressEditorRecoveryDriver()
    driver.states = ["address_sheet", "address_sheet", "checkout", "home"]
    driver.index = 0
    page = takeout_page.TakeoutPageBase(driver)

    assert page.ensure_takeout_tab(
        settle_sec=0,
        max_tab_clicks=1,
        wait_list_timeout=0,
    )
    assert driver.states[driver.index] == "home"
    assert driver.geometry_taps == []


def test_location_selection_handles_custom_go_to_settings_prompt(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_page.time.sleep", lambda _: None)
    driver = LocationPermissionDriver(state="custom")
    page = takeout_page.TakeoutPageBase(driver)

    assert page._ensure_location_permission_enabled()
    assert driver.state == "granted"
    assert driver.current_package == "com.bs.feifubao"
    assert driver.clicked[0] == "确定"


def test_location_selection_handles_immediate_enable_prompt(monkeypatch) -> None:
    monkeypatch.setattr("pages.takeout_page.time.sleep", lambda _: None)
    driver = LocationPermissionDriver(state="immediate")
    page = takeout_page.TakeoutPageBase(driver)

    assert page._ensure_location_permission_enabled()
    assert driver.state == "granted"
    assert driver.clicked[0] == "立即开启"
