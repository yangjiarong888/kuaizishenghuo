"""Public address-book selection for the shipping checkout facade."""

import time

from appium.webdriver.common.appiumby import AppiumBy

from .app_common import logger
from .shipping_types import AddressData, AddressPolicy, mask_phone, xpath_literal


class ShippingAddressMixin:
    """Validate an address policy before making any UI interaction."""

    _ADDRESS_BOOK_ROOT_SELECTOR = (
        '//*[contains(@resource-id,"shipping_address_book") '
        'or @content-desc="公共地址簿"]'
    )
    _ADDRESS_FORM_ROOT_SELECTOR = (
        '//*[contains(@resource-id,"shipping_address_form") '
        'or @content-desc="配送地址表单"]'
    )
    _CHECKOUT_ROOT_SELECTOR = (
        '//*[contains(@resource-id,"shipping_checkout_root") '
        'or @content-desc="配送提交订单页"]'
    )
    _CHECKOUT_ADDRESS_SELECTOR = (
        '//*[contains(@resource-id,"shipping_checkout_address") '
        'or @content-desc="配送地址回填"]'
    )

    def ensure_shipping_address(self, policy: AddressPolicy, data: AddressData) -> bool:
        if policy is AddressPolicy.EXISTING and not data.match.strip():
            raise ValueError("现有地址策略需要 SHIPPING_ADDRESS_MATCH")
        if policy is AddressPolicy.ADD:
            missing = data.missing_for_add()
            if missing:
                raise ValueError("新增地址缺少字段: " + ",".join(missing))
        if policy is AddressPolicy.AUTO and not data.match.strip():
            missing = data.missing_for_add()
            if missing:
                raise ValueError("自动地址策略无匹配关键字且新增地址缺少字段: " + ",".join(missing))
        logger.info("shipping_address_strategy policy=%s", policy.value)
        result = self._ensure_shipping_address_ui(policy, data)
        self._shipping_address_data = data
        return result

    def _ensure_shipping_address_ui(self, policy: AddressPolicy, data: AddressData) -> bool:
        if not self._click_text(("请选择收货地址", "收货地址", "配送地址")):
            self._address_failure("shipping_address_entry_missing", "提交订单页未打开公共地址簿", data)
        if not self._wait_until(self._is_address_list):
            self._address_failure("shipping_address_book_unverified", "公共地址簿打开后未验证地址列表", data)
        if policy is not AddressPolicy.ADD and data.match:
            if self.select_existing_shipping_address(data.match, data=data):
                logger.info("shipping_address_selection source=existing result=success")
                return self.verify_shipping_address_applied(data)
            if policy is AddressPolicy.EXISTING:
                self._address_failure("shipping_address_match_missing", "公共地址簿未找到匹配地址", data)
        self.add_shipping_address(data)
        if self._is_checkout_page():
            logger.info("shipping_address_selection source=added result=success")
            return self.verify_shipping_address_applied(data)
        if not self.select_existing_shipping_address(
            data.match or data.phone[-4:], data=data
        ):
            self._address_failure("shipping_address_saved_missing", "新增地址保存后未在公共地址簿中找到", data)
        logger.info("shipping_address_selection source=added result=success")
        return self.verify_shipping_address_applied(data)

    def select_existing_shipping_address(
        self, match: str, *, data: AddressData | None = None
    ) -> bool:
        needle = match.strip()
        if not needle:
            return False
        failure_data = data or AddressData(match=needle)
        literal = xpath_literal(needle)
        selector = (
            '//*[contains(@resource-id,"shipping_address_row") '
            'or @content-desc="公共地址行"]'
            f'[contains(@text,{literal}) or contains(@content-desc,{literal})]'
        )
        for attempt in range(4):
            try:
                candidates = self.driver.find_elements(AppiumBy.XPATH, selector)
            except Exception as exc:
                logger.debug("Shipping address lookup failed error_type=%s", type(exc).__name__)
                self._address_failure(
                    "shipping_address_lookup_failed", "公共地址簿查找失败", failure_data
                )
            matching = []
            for candidate in candidates:
                try:
                    if not candidate.is_displayed() or not candidate.is_enabled():
                        continue
                    contents = " ".join(
                        (candidate.get_attribute(attr) or "")
                        for attr in ("text", "content-desc")
                    )
                    if needle in contents:
                        matching.append((candidate, contents))
                except Exception as exc:
                    logger.debug("Shipping address selection failed error_type=%s", type(exc).__name__)
                    self._address_failure(
                        "shipping_address_row_unreadable",
                        "公共地址簿匹配行无法验证",
                        failure_data,
                    )
            if len(matching) > 1:
                self._address_failure(
                    "shipping_address_match_ambiguous",
                    "公共地址簿匹配到多个地址，结果不唯一",
                    failure_data,
                )
            if matching:
                candidate, contents = matching[0]
                try:
                    candidate.click()
                except Exception as exc:
                    self._address_failure(
                        "shipping_address_click_failed",
                        "公共地址点击失败",
                        failure_data,
                    )
                if not self._wait_until(self._is_checkout_page):
                    self._address_failure(
                        "shipping_address_checkout_transition_failed",
                        "公共地址点击后未返回提交订单页",
                        failure_data,
                    )
                self._shipping_selected_address_match = needle
                self._shipping_selected_address_blob = contents
                return True
            if attempt < 3:
                if not self._scroll_address_list_once():
                    self._address_failure(
                        "shipping_address_scroll_failed",
                        "公共地址簿滚动查找失败",
                        failure_data,
                    )
        return False

    def add_shipping_address(self, data: AddressData) -> bool:
        missing = data.missing_for_add()
        if missing:
            raise ValueError("新增地址缺少字段: " + ",".join(missing))
        if not self._click_text(("新增地址", "添加地址")):
            self._address_failure("shipping_address_add_missing", "公共地址簿未提供新增地址入口", data)
        if not self._click_text((data.country,)):
            self._address_failure("shipping_address_country_missing", "地址表单未找到国家", data)
        if not self._click_text((data.city,)):
            self._address_failure("shipping_address_city_missing", "地址表单未找到城市", data)
        for labels, value in (
            (("联系人", "姓名"), data.name),
            (("手机号码", "手机号", "联系电话"), data.phone),
            (("详细地址", "地址详情"), data.detail),
            (("邮政编码", "邮编"), data.postcode),
        ):
            if not self._type_field(labels, value):
                self._address_failure("shipping_address_field_missing", "地址表单字段不可填写", data)
        if not self._click_text(("保存",)):
            self._address_failure("shipping_address_save_missing", "地址表单未提供保存入口", data)
        if not self._wait_until(self._is_address_list_or_checkout):
            self._address_failure("shipping_address_save_timeout", "地址表单保存后未返回地址簿或提交订单页", data)
        return True

    def verify_shipping_address_applied(self, data: AddressData) -> bool:
        if not self._is_checkout_page():
            self._address_failure("shipping_address_verify_failed", "公共地址选择后未稳定回填到提交订单页", data)
        address_blob = self._checkout_address_text()
        stable = list(
            dict.fromkeys(
                value
                for value in (data.match, data.name, data.phone[-4:], data.city)
                if value
            )
        )
        optional_stable = [value for value in (data.name, data.phone[-4:], data.city) if value]
        required = 2 if len(optional_stable) >= 2 else 1
        if not stable or sum(value in address_blob for value in stable) < required:
            self._address_failure("shipping_address_verify_failed", "公共地址选择后未稳定回填到提交订单页", data)
        logger.info(
            "公共地址已应用 policy_match=%s phone=%s city=%s",
            bool(data.match),
            mask_phone(data.phone),
            data.city,
        )
        return True

    def _is_address_list_or_checkout(self) -> bool:
        return self._is_address_list() or self._is_checkout_page()

    def _is_address_list(self) -> bool:
        return self._first_displayed(
            AppiumBy.XPATH, self._ADDRESS_BOOK_ROOT_SELECTOR
        ) is not None

    def _is_checkout_page(self) -> bool:
        return (
            self._first_displayed(AppiumBy.XPATH, self._CHECKOUT_ROOT_SELECTOR)
            is not None
            and not self._is_address_list()
        )

    def _checkout_address_text(self) -> str:
        address = self._first_displayed(
            AppiumBy.XPATH, self._CHECKOUT_ADDRESS_SELECTOR
        )
        if address is None:
            return ""
        return self._node_blob(address)

    def _scroll_address_list_once(self) -> bool:
        try:
            size = self.driver.get_window_size()
            self.driver.execute_script(
                "mobile: swipeGesture",
                {
                    "left": int(size["width"] * 0.2),
                    "top": int(size["height"] * 0.35),
                    "width": int(size["width"] * 0.6),
                    "height": int(size["height"] * 0.45),
                    "direction": "up",
                    "percent": 0.55,
                },
            )
        except Exception as exc:
            logger.debug("Shipping address list scroll failed error_type=%s", type(exc).__name__)
            return False
        time.sleep(0.1)
        return True

    def _address_failure(self, stage: str, message: str, data: AddressData) -> None:
        self.capture_shipping_failure(
            stage, sensitive=True, redact_values=self._address_redaction_values(data)
        )
        raise AssertionError(message)

    @staticmethod
    def _address_redaction_values(data: AddressData) -> tuple[str, ...]:
        return (
            data.match,
            data.name,
            data.phone,
            data.country,
            data.city,
            data.detail,
            data.postcode,
        )
