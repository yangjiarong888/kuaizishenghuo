"""充值缴费页面对象。

覆盖话费/流量充值、生活缴费、账号管理和缴费记录。需求图没有提供
真实页面 XML，因此资源 ID 集中在类常量中，并为关键入口保留文案定位兜底。
真实设备接入后只需校准常量，不应改变公开业务方法。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait


class ChargePage:
    """充值缴费 Page Object；默认只校验订单，不执行真实提交。"""

    PKG = "com.bs.feifubao"

    PHONE_INPUT_ID = f"{PKG}:id/et_phone"
    COUPON_ITEM_ID = f"{PKG}:id/item_coupon"
    PHOTO_INPUT_ID = f"{PKG}:id/iv_add_bill_photo"
    SAVE_ACCOUNT_ID = f"{PKG}:id/cb_save_account"
    CREATE_ORDER_ID = f"{PKG}:id/btn_create_order"
    ACCOUNT_TYPE_ID = f"{PKG}:id/tv_payment_type"
    SAVED_PROVIDER_ID = f"{PKG}:id/tv_provider_name"

    FIELD_IDS = {
        "账号": f"{PKG}:id/et_account",
        "账单号": f"{PKG}:id/et_bill_number",
        "服务ID": f"{PKG}:id/et_service_id",
        "用户名": f"{PKG}:id/et_account_name",
        "手机号": f"{PKG}:id/et_mobile_number",
        "缴纳金额": f"{PKG}:id/et_amount",
    }

    RECHARGE_TYPES = {"airtime": "话费", "data": "流量"}
    LIFE_PAYMENT_TYPES = {
        "electricity": "电费",
        "water": "水费",
        "internet": "网费",
        "photo": "拍照缴费",
    }
    BOTTOM_ENTRIES = {
        "套餐查询",
        "缴费客服",
        "充值客服",
        "充值必看",
        "缴费必看",
        "充值记录",
        "缴费记录",
        "账号管理",
    }
    RECORD_TYPES = {
        "mobile": "手机费",
        "electricity": "电费",
        "internet": "网费",
        "water": "水费",
        "photo": "拍照",
    }
    ACCOUNT_TYPE_ORDER = ("电费", "水费", "网费")

    PROVIDERS = {
        "electricity": {
            "Meralco": frozenset(("账号", "缴纳金额")),
            "Meralco kuryente load": frozenset(("服务ID", "缴纳金额")),
        },
        "water": {
            "Manila Water": frozenset(("账号", "用户名", "缴纳金额")),
            "Maynilad": frozenset(("账号", "缴纳金额")),
            "Prime Water": frozenset(("账号", "用户名", "缴纳金额")),
        },
        "internet": {
            "PLDT": frozenset(("账号", "缴纳金额")),
            "Globe at home": frozenset(("账号", "缴纳金额")),
            "Converge ICT": frozenset(("账号", "用户名", "缴纳金额")),
            "Woofy": frozenset(("账号", "用户名", "缴纳金额")),
            "Sky cable": frozenset(("账号", "缴纳金额")),
            "Sky broadband": frozenset(("账号", "缴纳金额")),
            "Cablelink": frozenset(("账号", "用户名", "缴纳金额")),
            "Globe Telecom (Postpaid)": frozenset(("账号", "缴纳金额")),
            "Smart communications Inc. (Postpaid)": frozenset(
                ("账号", "手机号", "缴纳金额")
            ),
            "Sun Cellular (Postpaid)": frozenset(
                ("账号", "手机号", "缴纳金额")
            ),
        },
    }
    PHOTO_LIMITS = {
        "electricity": 1,
        "water": 1,
        "internet": 0,
        "photo": 2,
    }

    def __init__(self, driver, wait_sec: float = 10.0):
        self.driver = driver
        self.wait_sec = wait_sec
        self.payment_kind: str | None = None
        self.selected_provider: str | None = None
        self.filled_fields: set[str] = set()
        self.photo_count = 0
        self.save_account_enabled = False

    @staticmethod
    def _xpath_literal(text: str) -> str:
        if '"' not in text:
            return f'"{text}"'
        if "'" not in text:
            return f"'{text}'"
        parts = text.split('"')
        expressions = []
        for index, part in enumerate(parts):
            if part:
                expressions.append(f'"{part}"')
            if index < len(parts) - 1:
                expressions.append("'\"'")
        return f"concat({', '.join(expressions)})"

    @classmethod
    def _text_xpath(cls, text: str) -> str:
        literal = cls._xpath_literal(text)
        return f"//*[@text={literal} or @content-desc={literal}]"

    def _elements(self, by: str, value: str):
        try:
            return self.driver.find_elements(by, value)
        except Exception:
            return []

    def _first(self, by: str, value: str):
        elements = self._elements(by, value)
        return elements[0] if elements else None

    @staticmethod
    def _is_enabled(element) -> bool:
        try:
            return bool(element.is_enabled())
        except Exception:
            try:
                return str(element.get_attribute("enabled")).lower() != "false"
            except Exception:
                return False

    def _click(self, by: str, value: str) -> bool:
        element = self._first(by, value)
        if element is None or not self._is_enabled(element):
            return False
        try:
            element.click()
            return True
        except Exception:
            return False

    def _click_text(self, text: str) -> bool:
        return self._click(AppiumBy.XPATH, self._text_xpath(text))

    def _input(self, element_id: str, value: str) -> bool:
        element = self._first(AppiumBy.ID, element_id)
        if element is None:
            return False
        try:
            element.clear()
            element.send_keys(value)
            return True
        except Exception:
            return False

    def page_contains(self, text: str) -> bool:
        return bool(self._elements(AppiumBy.XPATH, self._text_xpath(text)))

    def wait_for_charge_home(self, timeout: float | None = None) -> bool:
        try:
            wait_timeout = self.wait_sec if timeout is None else timeout
            WebDriverWait(self.driver, wait_timeout).until(
                lambda _: self.page_contains("充值缴费")
                and self.page_contains("话费")
            )
            return True
        except Exception:
            return False

    def enter_from_home(self) -> bool:
        return self._click_text("充值缴费") and self.wait_for_charge_home()

    def set_phone_number(self, number: str) -> bool:
        normalized = "".join(str(number).split())
        if not normalized.isdigit() or len(normalized) not in (10, 11):
            raise ValueError("手机号必须为 10 或 11 位数字")
        if not self.page_contains("+63"):
            return False
        return self._input(self.PHONE_INPUT_ID, normalized)

    def switch_recharge_type(self, kind: str) -> bool:
        if kind not in self.RECHARGE_TYPES:
            raise ValueError("充值类型必须是 airtime 或 data")
        return self._click_text(self.RECHARGE_TYPES[kind])

    def select_recharge_package(self, label: str) -> bool:
        if not str(label).strip():
            raise ValueError("套餐文案不能为空")
        return self._click_text(label)

    def select_coupon(self, label: str | None = None) -> bool:
        if not self._click_text("优惠券"):
            return False
        if label is not None:
            element = self._first(AppiumBy.XPATH, self._text_xpath(label))
            if element is None or not self._is_enabled(element):
                return False
            try:
                element.click()
                return True
            except Exception:
                return False
        for element in self._elements(AppiumBy.ID, self.COUPON_ITEM_ID):
            if self._is_enabled(element):
                try:
                    element.click()
                    return True
                except Exception:
                    return False
        return False

    def open_bottom_entry(self, label: str) -> bool:
        if label not in self.BOTTOM_ENTRIES:
            raise ValueError("不支持的充值缴费底部入口")
        return self._click_text(label)

    def enter_life_payment(self, kind: str) -> bool:
        if kind not in self.LIFE_PAYMENT_TYPES:
            raise ValueError("生活缴费类型必须是 electricity、water、internet 或 photo")
        if not self._click_text(self.LIFE_PAYMENT_TYPES[kind]):
            return False
        self.payment_kind = kind
        self.selected_provider = None
        self.filled_fields.clear()
        self.photo_count = 0
        return True

    def select_provider(self, name: str) -> bool:
        if self.payment_kind not in self.PROVIDERS:
            raise ValueError("当前缴费类型不支持选择供应商")
        if name not in self.PROVIDERS[self.payment_kind]:
            raise ValueError("当前业务不支持该供应商")
        if not self._click_text(name):
            return False
        self.selected_provider = name
        self.filled_fields.clear()
        self.photo_count = 0
        return True

    def fill_billing_fields(self, values: Mapping[str, object]) -> bool:
        if self.payment_kind is None:
            raise ValueError("请先选择缴费类型")
        if self.payment_kind != "photo" and self.selected_provider is None:
            raise ValueError("请先选择供应商")
        if not values:
            raise ValueError("缴费字段不能为空")
        unsupported = set(values) - set(self.FIELD_IDS)
        if unsupported:
            raise ValueError("包含不支持的缴费字段")
        if self.payment_kind == "photo":
            allowed_fields = frozenset(("缴纳金额",))
        else:
            allowed_fields = self.PROVIDERS[self.payment_kind][
                self.selected_provider
            ]
        if set(values) - allowed_fields:
            raise ValueError("包含当前供应商不支持的缴费字段")
        normalized_values = {}
        for label, raw_value in values.items():
            value = str(raw_value).strip()
            if not value:
                raise ValueError(f"{label}不能为空")
            normalized_values[label] = value
        for label, value in normalized_values.items():
            if not self._input(self.FIELD_IDS[label], value):
                return False
            self.filled_fields.add(label)
        return True

    def add_bill_photos(
        self, paths: Sequence[str], limit: int | None = None
    ) -> bool:
        if self.payment_kind not in self.PHOTO_LIMITS:
            raise ValueError("请先选择缴费类型")
        if isinstance(paths, (str, bytes)):
            raise ValueError("图片路径必须使用列表或元组序列")
        paths = tuple(paths)
        if not paths or any(not str(path).strip() for path in paths):
            raise ValueError("账单图片不能为空")
        business_limit = self.PHOTO_LIMITS[self.payment_kind]
        effective_limit = business_limit if limit is None else min(limit, business_limit)
        if len(paths) > effective_limit:
            raise ValueError(f"当前业务最多上传 {effective_limit} 张图片")
        element = self._first(AppiumBy.ID, self.PHOTO_INPUT_ID)
        if element is None:
            return False
        try:
            for path in paths:
                element.send_keys(str(path))
            self.photo_count = len(paths)
            return True
        except Exception:
            return False

    def set_save_account(self, enabled: bool) -> bool:
        enabled = bool(enabled)
        element = self._first(AppiumBy.ID, self.SAVE_ACCOUNT_ID)
        if element is None:
            return False
        current = self._toggle_state(element)
        if current is None:
            return False
        if enabled == current:
            self.save_account_enabled = current
            return True
        try:
            element.click()
        except Exception:
            return False
        try:
            WebDriverWait(self.driver, self.wait_sec).until(
                lambda _: self._toggle_state(element) == enabled
            )
        except Exception:
            return False
        self.save_account_enabled = enabled
        return True

    @staticmethod
    def _toggle_state(element) -> bool | None:
        try:
            checked = element.get_attribute("checked")
            selected = element.get_attribute("selected")
        except Exception:
            return None
        state_value = checked if checked is not None else selected
        if state_value is None:
            return None
        return str(state_value).lower() == "true"

    def is_provider_account_unique(
        self, provider: str, current_provider: str | None = None
    ) -> bool:
        supported = {
            name for providers in self.PROVIDERS.values() for name in providers
        }
        if provider not in supported:
            raise ValueError("不支持的供应商")
        if current_provider == provider:
            return True
        saved = {
            str(getattr(element, "text", "")).strip()
            for element in self._elements(AppiumBy.ID, self.SAVED_PROVIDER_ID)
        }
        return provider not in saved

    def _required_fields(self) -> frozenset[str]:
        if self.payment_kind == "photo":
            return frozenset(("缴纳金额",))
        if self.payment_kind not in self.PROVIDERS or self.selected_provider is None:
            raise ValueError("请先选择缴费类型和供应商")
        return self.PROVIDERS[self.payment_kind][self.selected_provider]

    def create_order(self, submit: bool = False) -> bool:
        required = self._required_fields()
        missing = required - self.filled_fields
        if missing:
            raise ValueError("缺少必填缴费字段")
        if self.payment_kind == "photo" and self.photo_count < 1:
            raise ValueError("请至少上传一张账单图片")
        if (
            self.save_account_enabled
            and self.selected_provider is not None
            and not self.is_provider_account_unique(self.selected_provider)
        ):
            raise ValueError("该供应商已保存账号，不能重复保存")
        if not submit:
            return True
        return self._click(AppiumBy.ID, self.CREATE_ORDER_ID)

    def manage_saved_account(self, action: str, account_label: str) -> bool:
        labels = {"copy": "复制", "edit": "编辑", "delete": "删除"}
        if action not in labels:
            raise ValueError("账号操作必须是 copy、edit 或 delete")
        if not str(account_label).strip():
            raise ValueError("账号标签不能为空")
        account = self._xpath_literal(account_label)
        action_label = self._xpath_literal(labels[action])
        xpath = (
            f"//*[@text={account} or @content-desc={account}]"
            "/ancestor::*[self::android.view.ViewGroup "
            "or self::android.widget.LinearLayout][1]"
            f"//*[@text={action_label} or @content-desc={action_label}]"
        )
        return self._click(AppiumBy.XPATH, xpath)

    def verify_saved_account_order(self) -> bool:
        elements = self._elements(AppiumBy.ID, self.ACCOUNT_TYPE_ID)
        labels = [str(getattr(element, "text", "")).strip() for element in elements]
        if not labels or any(label not in self.ACCOUNT_TYPE_ORDER for label in labels):
            return False
        ranks = [self.ACCOUNT_TYPE_ORDER.index(label) for label in labels]
        return ranks == sorted(ranks)

    def edit_saved_account(
        self, account_label: str, values: Mapping[str, object]
    ) -> bool:
        if not values:
            raise ValueError("账号编辑字段不能为空")
        allowed = {"账号", "用户名"}
        if set(values) - allowed:
            raise ValueError("账号编辑仅支持账号和用户名")
        normalized_values = {}
        for label, raw_value in values.items():
            value = str(raw_value).strip()
            if not value:
                raise ValueError(f"{label}不能为空")
            normalized_values[label] = value
        if not self.manage_saved_account("edit", account_label):
            return False
        for label, value in normalized_values.items():
            if not self._input(self.FIELD_IDS[label], value):
                return False
        return self._click_text("保存")

    def switch_payment_record_type(self, kind: str) -> bool:
        if kind not in self.RECORD_TYPES:
            raise ValueError("缴费记录类型不受支持")
        return self._click_text(self.RECORD_TYPES[kind])

    def manage_payment_records(
        self, action: str, record_label: str | None = None
    ) -> bool:
        if action not in {"open", "select", "select_all", "delete"}:
            raise ValueError("记录操作必须是 open、select、select_all 或 delete")
        if action in {"open", "select", "delete"} and not record_label:
            raise ValueError("该操作必须提供缴费记录标签")
        if action == "open":
            return self._click_text(record_label or "")
        if not self._click_text("管理"):
            return False
        if action == "select_all":
            return self._click_text("全选")
        if not self._click_text(record_label or ""):
            return False
        if action == "select":
            return True
        return self._click_text("删除")
