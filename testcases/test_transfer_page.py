import pytest

from pages.transfer_page import TransferPage


class FakeElement:
    def __init__(
        self, driver, *, text="", element_id="", attributes=None, on_click=None
    ):
        self.driver = driver
        self.text = text
        self.element_id = element_id
        self.attributes = attributes or {}
        self.on_click = on_click

    def click(self):
        if self.text:
            self.driver.clicked_texts.append(self.text)
        if self.element_id:
            self.driver.clicked_ids.append(self.element_id)
        if self.on_click:
            self.on_click()

    def get_attribute(self, name):
        return self.attributes.get(name)

    def send_keys(self, value):
        self.driver.sent_values.append(value)


class FakeDriver:
    def __init__(self):
        self.current_activity = "com.bs.feifubao.RunnerHomeActivity"
        self.visible_ids = set()
        self.visible_texts = set()
        self.field_values = {}
        self.field_attributes = {}
        self.address_field_ids = ()
        self.clicked_ids = []
        self.clicked_texts = []
        self.sent_values = []
        self.back_calls = 0
        self.selected_payment_type = None
        self.order_status = "待接单"

    def _show_home(self):
        self.current_activity = "com.bs.feifubao.RunnerHomeActivity"
        self.visible_texts = set()
        self.visible_ids.update(
            {
                "com.bs.feifubao:id/tv_menu_service_info",
                "com.bs.feifubao:id/tv_menu_address_manage",
                "com.bs.feifubao:id/tv_menu_order",
            }
        )

    def _open_activity(self, activity):
        self.current_activity = f"com.bs.feifubao.{activity}"
        title = {
            "RunnerServiceInfoActivity": "\u540c\u57ce\u8dd1\u817f\u670d\u52a1\u8bf4\u660e",
            "FlutterBoostActivity": "\u5730\u5740\u7ba1\u7406",
            "RunnerOrderActivity": "\u8dd1\u817f\u8ba2\u5355",
        }[activity]
        self.visible_texts = {title}
        self.visible_ids.add("com.bs.feifubao:id/ll_back")

    def _begin_address_selection(self, field_ids):
        self.address_field_ids = field_ids
        self.visible_ids.add("com.bs.feifubao:id/tv_address")

    def _select_address(self, field_ids):
        self.visible_ids.discard("com.bs.feifubao:id/tv_address")
        self.field_values.update(
            {
                f"com.bs.feifubao:id/{field_id}": self.field_values.get(
                    f"com.bs.feifubao:id/{field_id}", "filled"
                )
                for field_id in field_ids
            }
        )

    def _advance_form(self):
        next_id = "com.bs.feifubao:id/tv_next"
        if self.clicked_ids.count(next_id) == 1:
            self.visible_ids.add("com.bs.feifubao:id/tv_select_receive_address")
        elif self.clicked_ids.count(next_id) == 2:
            self.visible_ids.add("com.bs.feifubao:id/settlement")

    def _show_payment_page(self):
        self.current_activity = "com.bs.feifubao.PayActivity"
        self.visible_texts = {"在线支付"}
        self.visible_ids.update(
            {
                "com.bs.feifubao:id/tv_type",
                "com.bs.feifubao:id/btn_pay",
            }
        )

    def _open_selected_payment(self):
        if self.selected_payment_type == "Maya支付":
            self.current_activity = "com.bs.feifubao.WebViewActivity"
            self.visible_texts = {"Login | Maya"}
            self.visible_ids.add("btnLogin")
        elif self.selected_payment_type == "余额":
            self.visible_ids.add("com.bs.feifubao:id/btn_comfirm")

    def _complete_balance_payment(self):
        self.current_activity = "com.bs.feifubao.RunnerOrderDetailActivity"
        self.visible_texts = {"订单详情", self.order_status}

    def back(self):
        self.back_calls += 1
        if "WebViewActivity" in self.current_activity:
            self._show_payment_page()

    def _click_action(self, element_id):
        actions = {
            "com.bs.feifubao:id/tv_menu_service_info": lambda: self._open_activity(
                "RunnerServiceInfoActivity"
            ),
            "com.bs.feifubao:id/tv_menu_address_manage": lambda: self._open_activity(
                "FlutterBoostActivity"
            ),
            "com.bs.feifubao:id/tv_menu_order": lambda: self._open_activity(
                "RunnerOrderActivity"
            ),
            "com.bs.feifubao:id/ll_back": self._show_home,
            "com.bs.feifubao:id/tv_select_get_address": lambda: self._begin_address_selection(
                ("et_get_user", "tv_get_address", "et_get_address_detail", "et_get_phone")
            ),
            "com.bs.feifubao:id/tv_select_receive_address": lambda: self._begin_address_selection(
                (
                    "et_receive_user",
                    "tv_receive_address",
                    "et_receive_address_detail",
                    "et_receive_phone",
                )
            ),
            "com.bs.feifubao:id/tv_receive_time": lambda: self.visible_ids.add(
                "com.bs.feifubao:id/item_canju_tv"
            ),
            "com.bs.feifubao:id/item_canju_tv": lambda: self.field_values.update(
                {
                    "com.bs.feifubao:id/tv_receive_time": self.field_values.get(
                        "com.bs.feifubao:id/tv_receive_time", "today 12:00"
                    )
                }
            ),
            "com.bs.feifubao:id/tv_next": self._advance_form,
            "com.bs.feifubao:id/settlement": self._show_payment_page,
            "com.bs.feifubao:id/btn_pay": self._open_selected_payment,
            "com.bs.feifubao:id/btn_comfirm": self._complete_balance_payment,
        }
        return actions.get(element_id)

    def find_elements(self, by, value):
        if value == '//*[@text="同城跑腿"]':
            return [FakeElement(self, text="同城跑腿")]
        if value.startswith('//*[@text="') and value.split('"')[1] in self.visible_texts:
            return [FakeElement(self)]
        if value == "com.bs.feifubao:id/tv_type" and value in self.visible_ids:
            return [
                FakeElement(
                    self,
                    text=label,
                    element_id=value,
                    on_click=lambda label=label: setattr(
                        self, "selected_payment_type", label
                    ),
                )
                for label in ("Maya支付", "余额")
            ]
        if value == "android.widget.EditText":
            if "WebViewActivity" in self.current_activity:
                return [FakeElement(self), FakeElement(self)]
            if "com.bs.feifubao:id/btn_comfirm" in self.visible_ids:
                return [FakeElement(self)]
        if value in self.field_values:
            return [
                FakeElement(
                    self,
                    text=self.field_values[value],
                    element_id=value,
                    attributes=self.field_attributes.get(value),
                    on_click=self._click_action(value),
                )
            ]
        if value in self.visible_ids:
            if value == "com.bs.feifubao:id/tv_address":
                return [
                    FakeElement(
                        self,
                        element_id=value,
                        on_click=lambda: self._select_address(self.address_field_ids),
                    )
                ]
            return [
                FakeElement(
                    self,
                    element_id=value,
                    on_click=self._click_action(value),
                )
            ]
        return []


@pytest.fixture
def fake_driver():
    driver = FakeDriver()
    driver.visible_ids.update(
        {
            "com.bs.feifubao:id/tv_menu_service_info",
            "com.bs.feifubao:id/tv_select_get_address",
            "com.bs.feifubao:id/tv_select_receive_address",
            "com.bs.feifubao:id/tv_receive_time",
            "com.bs.feifubao:id/tv_next",
        }
    )
    return driver


def test_enter_from_home_clicks_exact_runner_label(fake_driver):
    page = TransferPage(fake_driver)

    assert page.enter_from_home() is True
    assert fake_driver.clicked_texts == ["同城跑腿"]


def test_wait_for_runner_home_succeeds_with_runner_activity_and_menu_marker(fake_driver):
    assert TransferPage(fake_driver).wait_for_runner_home(timeout=0.01) is True


def test_wait_for_runner_home_rejects_non_runner_activity(fake_driver):
    fake_driver.current_activity = "com.bs.feifubao.OtherActivity"

    assert TransferPage(fake_driver).wait_for_runner_home(timeout=0.01) is False


def test_wait_for_runner_home_requires_menu_marker():
    driver = FakeDriver()

    assert TransferPage(driver).wait_for_runner_home(timeout=0.01) is False


def test_menu_round_trips_use_verified_ids(fake_driver):
    page = TransferPage(fake_driver)

    assert page.verify_menu_round_trips() is True
    assert fake_driver.clicked_ids[:3] == [
        "com.bs.feifubao:id/tv_menu_service_info",
        "com.bs.feifubao:id/ll_back",
        "com.bs.feifubao:id/tv_menu_address_manage",
    ]


def test_order_form_selects_saved_pickup_receive_and_time(fake_driver):
    page = TransferPage(fake_driver)

    assert page.fill_pickup_from_saved_address() is True
    assert page.fill_receive_from_saved_address() is True
    assert page.select_first_delivery_time() is True
    assert "com.bs.feifubao:id/tv_select_get_address" in fake_driver.clicked_ids
    assert "com.bs.feifubao:id/tv_select_receive_address" in fake_driver.clicked_ids
    assert "com.bs.feifubao:id/item_canju_tv" in fake_driver.clicked_ids


def test_advance_to_checkout_stops_before_settlement(fake_driver):
    page = TransferPage(fake_driver)

    assert page.advance_to_checkout() is True
    key_ids = {
        "com.bs.feifubao:id/tv_select_get_address",
        "com.bs.feifubao:id/tv_next",
        "com.bs.feifubao:id/tv_select_receive_address",
        "com.bs.feifubao:id/tv_receive_time",
        "com.bs.feifubao:id/item_canju_tv",
    }
    assert [element_id for element_id in fake_driver.clicked_ids if element_id in key_ids] == [
        "com.bs.feifubao:id/tv_select_get_address",
        "com.bs.feifubao:id/tv_next",
        "com.bs.feifubao:id/tv_select_receive_address",
        "com.bs.feifubao:id/tv_receive_time",
        "com.bs.feifubao:id/item_canju_tv",
        "com.bs.feifubao:id/tv_next",
    ]
    assert "com.bs.feifubao:id/settlement" not in fake_driver.clicked_ids


def test_submit_order_is_noop_without_explicit_permission(fake_driver):
    fake_driver.visible_ids.add("com.bs.feifubao:id/settlement")
    page = TransferPage(fake_driver)

    assert page.submit_order(submit_order=False) is True
    assert "com.bs.feifubao:id/settlement" not in fake_driver.clicked_ids


def test_balance_payment_rejects_missing_password(fake_driver):
    with pytest.raises(ValueError, match="TRANSFER_PAY_PASSWORD"):
        TransferPage(fake_driver).pay_with_balance("")


@pytest.mark.parametrize(
    ("flow_kwargs", "error_name"),
    (
        (
            {
                "submit_order": True,
                "payment_method": "card",
                "exercise_maya_return": False,
                "maya_account": "maya-user",
                "maya_password": "maya-secret",
                "pay_password": "pay-secret",
            },
            "payment_method",
        ),
        (
            {
                "submit_order": True,
                "payment_method": "balance",
                "exercise_maya_return": False,
                "maya_account": None,
                "maya_password": None,
                "pay_password": None,
            },
            "TRANSFER_PAY_PASSWORD",
        ),
        (
            {
                "submit_order": True,
                "payment_method": "maya",
                "exercise_maya_return": False,
                "maya_account": None,
                "maya_password": "maya-secret",
                "pay_password": None,
            },
            "TRANSFER_MAYA_ACCOUNT",
        ),
        (
            {
                "submit_order": True,
                "payment_method": "maya",
                "exercise_maya_return": False,
                "maya_account": "maya-user",
                "maya_password": None,
                "pay_password": None,
            },
            "TRANSFER_MAYA_PASSWORD",
        ),
        (
            {
                "submit_order": True,
                "payment_method": "balance",
                "exercise_maya_return": True,
                "maya_account": None,
                "maya_password": "maya-secret",
                "pay_password": "pay-secret",
            },
            "TRANSFER_MAYA_ACCOUNT",
        ),
        (
            {
                "submit_order": True,
                "payment_method": "balance",
                "exercise_maya_return": True,
                "maya_account": "maya-user",
                "maya_password": None,
                "pay_password": "pay-secret",
            },
            "TRANSFER_MAYA_PASSWORD",
        ),
    ),
)
def test_run_order_flow_prevalidates_before_any_click(
    fake_driver, flow_kwargs, error_name
):
    with pytest.raises(ValueError, match=error_name):
        TransferPage(fake_driver).run_order_flow(**flow_kwargs)

    assert fake_driver.clicked_ids == []
    assert fake_driver.clicked_texts == []


def test_run_order_flow_defaults_to_checkout_without_submission(fake_driver):
    assert TransferPage(fake_driver).run_order_flow() is True
    assert "com.bs.feifubao:id/settlement" in fake_driver.visible_ids
    assert "com.bs.feifubao:id/settlement" not in fake_driver.clicked_ids


def test_maya_payment_enters_login_and_returns_to_pay_activity(fake_driver):
    fake_driver._show_payment_page()

    assert (
        TransferPage(fake_driver).exercise_maya_and_return(
            "maya-user", "maya-secret"
        )
        is True
    )
    assert fake_driver.sent_values == ["maya-user", "maya-secret"]
    assert fake_driver.clicked_ids == [
        "com.bs.feifubao:id/tv_type",
        "com.bs.feifubao:id/btn_pay",
        "btnLogin",
    ]
    assert fake_driver.back_calls == 1
    assert fake_driver.current_activity.endswith("PayActivity")


def test_balance_payment_enters_password_and_confirms(fake_driver):
    fake_driver._show_payment_page()

    assert TransferPage(fake_driver).pay_with_balance("pay-secret") is True
    assert fake_driver.sent_values == ["pay-secret"]
    assert fake_driver.clicked_ids == [
        "com.bs.feifubao:id/tv_type",
        "com.bs.feifubao:id/btn_pay",
        "com.bs.feifubao:id/btn_comfirm",
    ]


@pytest.mark.parametrize("status", ("待接单", "待取货", "配送中", "已完成"))
def test_paid_order_detail_accepts_valid_statuses(fake_driver, status):
    fake_driver.current_activity = "com.bs.feifubao.RunnerOrderDetailActivity"
    fake_driver.visible_texts = {"订单详情", status}

    assert TransferPage(fake_driver).assert_paid_order_detail() is True


def test_paid_order_detail_rejects_pending_payment(fake_driver):
    fake_driver.current_activity = "com.bs.feifubao.RunnerOrderDetailActivity"
    fake_driver.visible_texts = {"订单详情", "待接单", "待付款"}

    assert TransferPage(fake_driver).assert_paid_order_detail() is False


def test_saved_address_rejects_placeholder_text_with_content_desc(fake_driver):
    placeholders = {
        "et_get_user": "请输入取货人姓名",
        "tv_get_address": "请选择取货地址",
        "et_get_address_detail": "请输入详细地址",
        "et_get_phone": "请输入取货人手机号",
    }
    for suffix, placeholder in placeholders.items():
        element_id = f"com.bs.feifubao:id/{suffix}"
        fake_driver.field_values[element_id] = placeholder
        fake_driver.field_attributes[element_id] = {"content-desc": suffix}

    assert TransferPage(fake_driver).fill_pickup_from_saved_address() is False


def test_delivery_time_rejects_placeholder_text_with_content_desc(fake_driver):
    element_id = "com.bs.feifubao:id/tv_receive_time"
    fake_driver.field_values[element_id] = "请选择收货时间"
    fake_driver.field_attributes[element_id] = {"content-desc": "delivery time"}

    assert TransferPage(fake_driver).select_first_delivery_time() is False
