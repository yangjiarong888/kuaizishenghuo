import re

import pytest

from pages.charge_page import ChargePage


class FakeElement:
    def __init__(
        self,
        driver,
        *,
        text="",
        element_id="",
        enabled=True,
        attributes=None,
        toggle_checked=True,
        on_click=None,
    ):
        self.driver = driver
        self.text = text
        self.element_id = element_id
        self.enabled = enabled
        self.attributes = attributes or {}
        self.toggle_checked = toggle_checked
        self.on_click = on_click

    def click(self):
        self.driver.clicked.append(self.element_id or self.text)
        if self.toggle_checked and "checked" in self.attributes:
            checked = str(self.attributes["checked"]).lower() == "true"
            self.attributes["checked"] = "false" if checked else "true"
        if self.on_click:
            self.on_click()

    def clear(self):
        self.driver.values[self.element_id] = ""

    def send_keys(self, value):
        self.driver.values[self.element_id] = value

    def get_attribute(self, name):
        if name == "enabled":
            return "true" if self.enabled else "false"
        return self.attributes.get(name)

    def is_enabled(self):
        return self.enabled


class FakeDriver:
    def __init__(self):
        self.visible_texts = {
            "充值缴费": FakeElement(
                self,
                text="充值缴费",
                on_click=lambda: self.show_text("话费"),
            ),
            "话费": FakeElement(self, text="话费"),
            "+63": FakeElement(self, text="+63"),
        }
        self.visible_ids = {
            ChargePage.PHONE_INPUT_ID: FakeElement(
                self, element_id=ChargePage.PHONE_INPUT_ID
            ),
            ChargePage.CREATE_ORDER_ID: FakeElement(
                self, element_id=ChargePage.CREATE_ORDER_ID
            ),
            ChargePage.PHOTO_INPUT_ID: FakeElement(
                self, element_id=ChargePage.PHOTO_INPUT_ID
            ),
            ChargePage.SAVE_ACCOUNT_ID: FakeElement(
                self,
                element_id=ChargePage.SAVE_ACCOUNT_ID,
                attributes={"checked": "false"},
            ),
        }
        for element_id in ChargePage.FIELD_IDS.values():
            self.visible_ids[element_id] = FakeElement(self, element_id=element_id)
        self.coupons = []
        self.saved_providers = []
        self.clicked = []
        self.values = {}
        self.queries = []

    def show_text(self, *labels):
        for label in labels:
            self.visible_texts[label] = FakeElement(self, text=label)

    def find_elements(self, by, value):
        self.queries.append((by, value))
        if "ancestor::*" in value:
            labels = re.findall(r'@text="([^"]+)"', value)
            if labels and all(label in self.visible_texts for label in labels):
                return [self.visible_texts[labels[-1]]]
        if value == ChargePage.ACCOUNT_TYPE_ID:
            return getattr(self, "account_types", [])
        if value == ChargePage.SAVED_PROVIDER_ID:
            return self.saved_providers
        if value == ChargePage.COUPON_ITEM_ID:
            return self.coupons
        if value in self.visible_ids:
            return [self.visible_ids[value]]
        match = re.search(r'@text="([^"]+)"', value)
        if match and match.group(1) in self.visible_texts:
            return [self.visible_texts[match.group(1)]]
        return []


@pytest.fixture
def driver():
    return FakeDriver()


def test_wait_for_charge_home_requires_title_and_recharge_marker(driver):
    assert ChargePage(driver).wait_for_charge_home(timeout=0.01) is True
    driver.visible_texts.pop("话费")
    assert ChargePage(driver).wait_for_charge_home(timeout=0.01) is False


def test_enter_from_home_clicks_charge_entry(driver):
    driver.visible_texts.pop("话费")
    assert ChargePage(driver).enter_from_home() is True
    assert driver.clicked == ["充值缴费"]


def test_set_phone_number_normalizes_spaces_and_keeps_country_code(driver):
    page = ChargePage(driver)
    assert page.set_phone_number("0992 052 8426") is True
    assert driver.values[ChargePage.PHONE_INPUT_ID] == "09920528426"


@pytest.mark.parametrize("number", ("", "09ab1234567", "123456789"))
def test_set_phone_number_rejects_invalid_values_before_input(driver, number):
    with pytest.raises(ValueError, match="手机号"):
        ChargePage(driver).set_phone_number(number)
    assert driver.values == {}


@pytest.mark.parametrize(
    ("kind", "label"), (("airtime", "话费"), ("data", "流量"))
)
def test_switch_recharge_type_uses_supported_label(driver, kind, label):
    driver.show_text(label)
    assert ChargePage(driver).switch_recharge_type(kind) is True
    assert driver.clicked[-1] == label


def test_select_recharge_package_clicks_exact_package(driver):
    driver.show_text("60G无限时流量")
    assert ChargePage(driver).select_recharge_package("60G无限时流量") is True
    assert driver.clicked[-1] == "60G无限时流量"


def test_select_coupon_uses_first_enabled_coupon(driver):
    driver.show_text("优惠券")
    driver.coupons = [
        FakeElement(driver, element_id="expired", enabled=False),
        FakeElement(driver, element_id="available", enabled=True),
    ]
    assert ChargePage(driver).select_coupon() is True
    assert driver.clicked == ["优惠券", "available"]


def test_select_named_coupon_rejects_disabled_coupon(driver):
    driver.show_text("优惠券", "生活缴费优惠券")
    driver.visible_texts["生活缴费优惠券"].enabled = False
    assert ChargePage(driver).select_coupon("生活缴费优惠券") is False


@pytest.mark.parametrize(
    "label", ("套餐查询", "缴费客服", "充值必看", "充值记录")
)
def test_open_bottom_entry_supports_requirement_entries(driver, label):
    driver.show_text(label)
    assert ChargePage(driver).open_bottom_entry(label) is True


@pytest.mark.parametrize(
    ("kind", "label"),
    (
        ("electricity", "电费"),
        ("water", "水费"),
        ("internet", "网费"),
        ("photo", "拍照缴费"),
    ),
)
def test_enter_life_payment_tracks_selected_kind(driver, kind, label):
    driver.show_text(label)
    page = ChargePage(driver)
    assert page.enter_life_payment(kind) is True
    assert page.payment_kind == kind


def test_select_provider_rejects_provider_outside_current_business(driver):
    page = ChargePage(driver)
    page.payment_kind = "water"
    with pytest.raises(ValueError, match="供应商"):
        page.select_provider("Meralco")


def test_fill_billing_fields_inputs_supported_dynamic_fields(driver):
    page = ChargePage(driver)
    page.payment_kind = "water"
    page.selected_provider = "Manila Water"
    assert page.fill_billing_fields(
        {"账号": "12345678", "用户名": "Tester", "缴纳金额": "100"}
    ) is True
    assert page.filled_fields == {"账号", "用户名", "缴纳金额"}
    assert driver.values[ChargePage.FIELD_IDS["账号"]] == "12345678"


def test_fill_billing_fields_rejects_provider_field_before_partial_input(driver):
    page = ChargePage(driver)
    page.payment_kind = "electricity"
    page.selected_provider = "Meralco"
    with pytest.raises(ValueError, match="当前供应商"):
        page.fill_billing_fields({"账号": "1234567890", "用户名": "wrong"})
    assert driver.values == {}


@pytest.mark.parametrize(
    ("kind", "count", "should_raise"),
    (
        ("electricity", 1, False),
        ("electricity", 2, True),
        ("water", 2, True),
        ("internet", 1, True),
        ("photo", 2, False),
        ("photo", 3, True),
    ),
)
def test_add_bill_photos_enforces_business_limit(
    driver, kind, count, should_raise
):
    page = ChargePage(driver)
    page.payment_kind = kind
    paths = [f"bill-{index}.png" for index in range(count)]
    if should_raise:
        with pytest.raises(ValueError, match="图片"):
            page.add_bill_photos(paths)
    else:
        assert page.add_bill_photos(paths) is True
        assert page.photo_count == count


def test_set_save_account_clicks_only_when_state_changes(driver):
    page = ChargePage(driver)
    assert page.set_save_account(True) is True
    assert page.set_save_account(True) is True
    assert driver.clicked.count(ChargePage.SAVE_ACCOUNT_ID) == 1


def test_set_save_account_reads_checked_state_from_control(driver):
    driver.visible_ids[ChargePage.SAVE_ACCOUNT_ID].attributes["checked"] = "true"
    assert ChargePage(driver).set_save_account(True) is True
    assert ChargePage.SAVE_ACCOUNT_ID not in driver.clicked


def test_set_save_account_returns_false_when_control_state_does_not_change(driver):
    driver.visible_ids[ChargePage.SAVE_ACCOUNT_ID].toggle_checked = False
    assert ChargePage(driver, wait_sec=0.01).set_save_account(True) is False


def _valid_electricity_page(driver):
    page = ChargePage(driver)
    page.payment_kind = "electricity"
    page.selected_provider = "Meralco"
    page.filled_fields = {"账号", "缴纳金额"}
    page.photo_count = 1
    return page


def test_create_order_does_not_click_without_explicit_submit(driver):
    page = _valid_electricity_page(driver)
    assert page.create_order(submit=False) is True
    assert ChargePage.CREATE_ORDER_ID not in driver.clicked


def test_create_order_clicks_only_with_explicit_submit(driver):
    page = _valid_electricity_page(driver)
    assert page.create_order(submit=True) is True
    assert driver.clicked[-1] == ChargePage.CREATE_ORDER_ID


def test_create_order_rejects_duplicate_provider_when_saving_account(driver):
    driver.saved_providers = [FakeElement(driver, text="Meralco")]
    page = _valid_electricity_page(driver)
    page.save_account_enabled = True
    with pytest.raises(ValueError, match="供应商"):
        page.create_order()


def test_electricity_order_allows_optional_bill_photo_to_be_omitted(driver):
    page = _valid_electricity_page(driver)
    page.photo_count = 0
    assert page.create_order() is True


def test_internet_order_does_not_require_or_accept_bill_photo(driver):
    page = ChargePage(driver)
    page.payment_kind = "internet"
    page.selected_provider = "PLDT"
    page.filled_fields = {"账号", "缴纳金额"}
    assert page.create_order() is True


def test_photo_payment_requires_at_least_one_bill_photo(driver):
    page = ChargePage(driver)
    page.payment_kind = "photo"
    page.filled_fields = {"缴纳金额"}
    with pytest.raises(ValueError, match="账单图片"):
        page.create_order()


@pytest.mark.parametrize(
    ("action", "label"),
    (("copy", "复制"), ("edit", "编辑"), ("delete", "删除")),
)
def test_manage_saved_account_scopes_action_to_matching_card(driver, action, label):
    driver.show_text("23652824156", label)
    assert ChargePage(driver).manage_saved_account(action, "23652824156") is True
    assert driver.clicked == [label]
    assert any(
        "ancestor::*" in value and "23652824156" in value and label in value
        for _, value in driver.queries
    )


def test_verify_saved_account_order_accepts_electricity_water_internet(driver):
    driver.account_types = [
        FakeElement(driver, text="电费"),
        FakeElement(driver, text="水费"),
        FakeElement(driver, text="网费"),
    ]
    assert ChargePage(driver).verify_saved_account_order() is True


def test_verify_saved_account_order_rejects_out_of_order_cards(driver):
    driver.account_types = [
        FakeElement(driver, text="水费"),
        FakeElement(driver, text="电费"),
    ]
    assert ChargePage(driver).verify_saved_account_order() is False


def test_edit_saved_account_updates_fields_and_saves(driver):
    driver.show_text("23652824156", "编辑", "保存")
    page = ChargePage(driver)
    assert page.edit_saved_account(
        "23652824156", {"账号": "87654321", "用户名": "Tester"}
    ) is True
    assert driver.values[ChargePage.FIELD_IDS["账号"]] == "87654321"
    assert driver.clicked[-1] == "保存"


def test_edit_saved_account_rejects_unsupported_field_before_click(driver):
    driver.show_text("23652824156", "编辑", "保存")
    with pytest.raises(ValueError, match="仅支持"):
        ChargePage(driver).edit_saved_account(
            "23652824156", {"缴纳金额": "100"}
        )
    assert driver.clicked == []


def test_manage_payment_records_opens_record_directly(driver):
    driver.show_text("202503171933001")
    assert ChargePage(driver).manage_payment_records(
        "open", "202503171933001"
    ) is True
    assert driver.clicked == ["202503171933001"]


def test_manage_payment_records_selects_all_in_manage_mode(driver):
    driver.show_text("管理", "全选")
    assert ChargePage(driver).manage_payment_records("select_all") is True
    assert driver.clicked == ["管理", "全选"]


@pytest.mark.parametrize(
    ("kind", "label"),
    (
        ("mobile", "手机费"),
        ("electricity", "电费"),
        ("internet", "网费"),
        ("water", "水费"),
        ("photo", "拍照"),
    ),
)
def test_switch_payment_record_type_covers_five_tabs(driver, kind, label):
    driver.show_text(label)
    assert ChargePage(driver).switch_payment_record_type(kind) is True
    assert driver.clicked[-1] == label


def test_switch_payment_record_type_rejects_unknown_type(driver):
    with pytest.raises(ValueError, match="不受支持"):
        ChargePage(driver).switch_payment_record_type("gas")

def test_manage_payment_records_delete_requires_record_label(driver):
    with pytest.raises(ValueError, match="记录"):
        ChargePage(driver).manage_payment_records("delete")


def test_manage_payment_records_deletes_selected_record(driver):
    driver.show_text("管理", "09365568856", "删除")
    assert ChargePage(driver).manage_payment_records(
        "delete", "09365568856"
    ) is True
    assert driver.clicked == ["管理", "09365568856", "删除"]


def test_add_bill_photos_rejects_bare_string_path(driver):
    page = ChargePage(driver)
    page.payment_kind = "photo"
    with pytest.raises(ValueError, match="序列"):
        page.add_bill_photos("bill.png")


def test_xpath_literal_supports_double_quote_labels():
    xpath = ChargePage._text_xpath('套餐"A\'s')
    assert "concat(" in xpath
    assert '\\"' not in xpath
