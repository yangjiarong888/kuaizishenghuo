from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait

PKG = "com.bs.feifubao"


class TransferPage:
    SERVICE_INFO_ID = f"{PKG}:id/tv_menu_service_info"

    def __init__(self, driver):
        self.driver = driver

    def _elements(self, by, value):
        try:
            return self.driver.find_elements(by, value)
        except Exception:
            return []

    def page_contains(self, text: str) -> bool:
        return bool(
            self._elements(
                AppiumBy.XPATH,
                f'//*[@text="{text}" or @content-desc="{text}"]',
            )
        )

    def wait_for_runner_home(self, timeout: float = 10.0) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda driver: str(
                    getattr(driver, "current_activity", "")
                ).endswith("RunnerHomeActivity")
                and driver.find_elements(AppiumBy.ID, self.SERVICE_INFO_ID)
            )
            return True
        except Exception:
            return False

    def enter_from_home(self) -> bool:
        matches = self._elements(AppiumBy.XPATH, '//*[@text="同城跑腿"]')
        if not matches:
            return False
        matches[0].click()
        return self.wait_for_runner_home()

    def tap_back(self) -> bool:
        matches = self._elements(AppiumBy.ID, f"{PKG}:id/ll_back")
        if matches:
            matches[0].click()
        else:
            self.driver.back()
        return True

    MENU_CASES = (
        ("tv_menu_service_info", ("同城跑腿服务说明",), "RunnerServiceInfoActivity"),
        ("tv_menu_address_manage", ("地址管理",), "FlutterBoostActivity"),
        ("tv_menu_order", ("跑腿订单",), "RunnerOrderActivity"),
    )
    PICKUP_FIELDS = ("et_get_user", "tv_get_address", "et_get_address_detail", "et_get_phone")
    RECEIVE_FIELDS = (
        "et_receive_user",
        "tv_receive_address",
        "et_receive_address_detail",
        "et_receive_phone",
    )
    FIELD_PLACEHOLDERS = {
        "et_get_user": ("请输入取货人姓名",),
        "tv_get_address": ("请选择取货地址",),
        "et_get_address_detail": ("请输入详细地址",),
        "et_get_phone": ("请输入取货人手机号",),
        "et_receive_user": ("请输入收货人姓名",),
        "tv_receive_address": ("请选择收货地址",),
        "et_receive_address_detail": ("请输入详细地址",),
        "et_receive_phone": ("请输入收货人手机号",),
    }

    def _click_id(self, suffix: str) -> bool:
        matches = self._elements(AppiumBy.ID, f"{PKG}:id/{suffix}")
        if not matches:
            return False
        matches[0].click()
        return True

    def _wait_page(
        self,
        *,
        markers: tuple[str, ...],
        activity_contains: str,
        timeout: float = 10.0,
    ) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda driver: activity_contains in str(
                    getattr(driver, "current_activity", "")
                )
                and all(self.page_contains(marker) for marker in markers)
            )
            return True
        except Exception:
            return False

    def _element_has_value(
        self, suffix: str, reject: tuple[str, ...] = ()
    ) -> bool:
        matches = self._elements(AppiumBy.ID, f"{PKG}:id/{suffix}")
        if not matches:
            return False
        element = matches[0]
        values = [getattr(element, "text", "")]
        for attribute in ("text", "value"):
            try:
                values.append(element.get_attribute(attribute))
            except Exception:
                pass
        return any(
            isinstance(value, str)
            and value.strip()
            and value.strip() not in reject
            for value in values
        )

    def verify_menu_round_trips(self) -> bool:
        for suffix, markers, activity in self.MENU_CASES:
            if not self._click_id(suffix):
                return False
            if not self._wait_page(markers=markers, activity_contains=activity):
                return False
            self.tap_back()
            if not self.wait_for_runner_home():
                return False
        return True

    def select_saved_address(
        self, trigger_id: str, expected_ids: tuple[str, ...]
    ) -> bool:
        if not self._click_id(trigger_id):
            return False
        addresses = self._elements(AppiumBy.ID, f"{PKG}:id/tv_address")
        if not addresses:
            return False
        addresses[0].click()
        return all(
            self._element_has_value(
                suffix, reject=self.FIELD_PLACEHOLDERS.get(suffix, ())
            )
            for suffix in expected_ids
        )

    def fill_pickup_from_saved_address(self) -> bool:
        return self.select_saved_address("tv_select_get_address", self.PICKUP_FIELDS)

    def fill_receive_from_saved_address(self) -> bool:
        return self.select_saved_address(
            "tv_select_receive_address", self.RECEIVE_FIELDS
        )

    def select_first_delivery_time(self) -> bool:
        if not self._click_id("tv_receive_time"):
            return False
        slots = self._elements(AppiumBy.ID, f"{PKG}:id/item_canju_tv")
        if not slots:
            return False
        slots[0].click()
        return self._element_has_value("tv_receive_time", reject=("请选择收货时间",))

    def advance_to_checkout(self) -> bool:
        if not self.fill_pickup_from_saved_address():
            return False
        if not self._click_id("tv_next"):
            return False
        if not self._elements(AppiumBy.ID, f"{PKG}:id/tv_select_receive_address"):
            return False
        if not self.fill_receive_from_saved_address():
            return False
        if not self.select_first_delivery_time():
            return False
        if not self._click_id("tv_next"):
            return False
        return bool(self._elements(AppiumBy.ID, f"{PKG}:id/settlement"))

    def submit_order(self, submit_order: bool) -> bool:
        if not self._elements(AppiumBy.ID, f"{PKG}:id/settlement"):
            return False
        if not submit_order:
            return True
        if not self._click_id("settlement"):
            return False
        return self._wait_page(
            markers=("在线支付",), activity_contains="PayActivity"
        )

    def _select_payment_type(self, label: str) -> bool:
        types = self._elements(AppiumBy.ID, f"{PKG}:id/tv_type")
        match = next((element for element in types if element.text == label), None)
        if match is None:
            return False
        match.click()
        return True

    def pay_with_balance(self, pay_password: str) -> bool:
        if not pay_password:
            raise ValueError("缺少 TRANSFER_PAY_PASSWORD")
        if not self._select_payment_type("余额") or not self._click_id("btn_pay"):
            return False
        inputs = self._elements(AppiumBy.CLASS_NAME, "android.widget.EditText")
        if not inputs:
            return False
        inputs[0].send_keys(pay_password)
        if not self._click_id("btn_comfirm"):
            return False
        return self.assert_paid_order_detail()

    def exercise_maya_and_return(self, account: str, password: str) -> bool:
        if not account or not password:
            raise ValueError(
                "缺少 TRANSFER_MAYA_ACCOUNT 或 TRANSFER_MAYA_PASSWORD"
            )
        if not self._select_payment_type("Maya支付") or not self._click_id("btn_pay"):
            return False
        if not self._wait_page(
            markers=("Login | Maya",), activity_contains="WebViewActivity"
        ):
            return False
        inputs = self._elements(AppiumBy.CLASS_NAME, "android.widget.EditText")
        if len(inputs) < 2:
            return False
        inputs[0].send_keys(account)
        inputs[1].send_keys(password)
        login_buttons = self._elements(AppiumBy.ID, "btnLogin")
        if not login_buttons:
            return False
        login_buttons[0].click()
        for _ in range(3):
            if "PayActivity" in (self.driver.current_activity or ""):
                return True
            self.driver.back()
        return "PayActivity" in (self.driver.current_activity or "")

    def assert_paid_order_detail(self) -> bool:
        if not self._wait_page(
            markers=("订单详情",),
            activity_contains="RunnerOrderDetailActivity",
        ):
            return False
        statuses = ("待接单", "待取货", "配送中", "已完成")
        return any(self.page_contains(status) for status in statuses) and not (
            self.page_contains("待付款")
        )

    def run_order_flow(
        self,
        *,
        submit_order: bool = False,
        payment_method: str = "balance",
        exercise_maya_return: bool = False,
        maya_account: str | None = None,
        maya_password: str | None = None,
        pay_password: str | None = None,
    ) -> bool:
        if payment_method not in ("balance", "maya"):
            raise ValueError("payment_method 必须是 balance 或 maya")
        if payment_method == "maya" or exercise_maya_return:
            if not maya_account:
                raise ValueError("缺少 TRANSFER_MAYA_ACCOUNT")
            if not maya_password:
                raise ValueError("缺少 TRANSFER_MAYA_PASSWORD")
        if submit_order and payment_method == "balance" and not pay_password:
            raise ValueError("缺少 TRANSFER_PAY_PASSWORD")

        if not self.advance_to_checkout() or not self.submit_order(submit_order):
            return False
        if not submit_order:
            return True
        if exercise_maya_return and not self.exercise_maya_and_return(
            maya_account or "", maya_password or ""
        ):
            return False
        if payment_method == "balance":
            return self.pay_with_balance(pay_password or "")
        if payment_method == "maya":
            if exercise_maya_return:
                return True
            return self.exercise_maya_and_return(
                maya_account or "", maya_password or ""
            )
        return False
