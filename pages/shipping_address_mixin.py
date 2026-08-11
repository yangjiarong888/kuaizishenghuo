"""Public address-book selection for the shipping checkout facade."""

import time

from appium.webdriver.common.appiumby import AppiumBy

from .app_common import logger
from .shipping_types import AddressData, AddressPolicy, mask_phone


class ShippingAddressMixin:
    """Validate an address policy before making any UI interaction."""

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
        return self._ensure_shipping_address_ui(policy, data)

    def _ensure_shipping_address_ui(self, policy: AddressPolicy, data: AddressData) -> bool:
        if not self._click_text(("请选择收货地址", "收货地址", "配送地址")):
            self._address_failure("shipping_address_entry_missing", "提交订单页未打开公共地址簿")
        if policy is not AddressPolicy.ADD and data.match:
            if self.select_existing_shipping_address(data.match):
                return self.verify_shipping_address_applied(data)
            if policy is AddressPolicy.EXISTING:
                self._address_failure("shipping_address_match_missing", "公共地址簿未找到匹配地址")
        self.add_shipping_address(data)
        if not self.select_existing_shipping_address(data.match or data.phone[-4:]):
            self._address_failure("shipping_address_saved_missing", "新增地址保存后未在公共地址簿中找到")
        return self.verify_shipping_address_applied(data)

    def select_existing_shipping_address(self, match: str) -> bool:
        needle = match.strip()
        if not needle:
            return False
        selector = f'//*[contains(@text,"{needle}") or contains(@content-desc,"{needle}")]'
        for attempt in range(4):
            try:
                candidates = self.driver.find_elements(AppiumBy.XPATH, selector)
            except Exception as exc:
                logger.debug("Shipping address lookup failed error_type=%s", type(exc).__name__)
                candidates = []
            for candidate in candidates:
                try:
                    if not candidate.is_displayed() or not candidate.is_enabled():
                        continue
                    contents = " ".join(
                        (candidate.get_attribute(attr) or "")
                        for attr in ("text", "content-desc")
                    )
                    if needle in contents:
                        candidate.click()
                        return True
                except Exception as exc:
                    logger.debug("Shipping address selection failed error_type=%s", type(exc).__name__)
            if attempt < 3:
                self._scroll_address_list_once()
        return False

    def add_shipping_address(self, data: AddressData) -> bool:
        if not self._click_text(("新增地址", "添加地址")):
            self._address_failure("shipping_address_add_missing", "公共地址簿未提供新增地址入口")
        if not self._click_text((data.country,)):
            self._address_failure("shipping_address_country_missing", "地址表单未找到国家")
        if not self._click_text((data.city,)):
            self._address_failure("shipping_address_city_missing", "地址表单未找到城市")
        for labels, value in (
            (("联系人", "姓名"), data.name),
            (("手机号码", "手机号", "联系电话"), data.phone),
            (("详细地址", "地址详情"), data.detail),
            (("邮政编码", "邮编"), data.postcode),
        ):
            if not self._type_field(labels, value):
                self._address_failure("shipping_address_field_missing", "地址表单字段不可填写")
        if not self._click_text(("保存",)):
            self._address_failure("shipping_address_save_missing", "地址表单未提供保存入口")
        if not self._wait_until(self._is_address_list_or_checkout):
            self._address_failure("shipping_address_save_timeout", "地址表单保存后未返回地址簿或提交订单页")
        return True

    def verify_shipping_address_applied(self, data: AddressData) -> bool:
        blob = self.page_blob()
        stable = [value for value in (data.name, data.phone[-4:], data.city) if value]
        if any(marker in blob for marker in ("请选择地址", "请选择收货地址")) or sum(
            value in blob for value in stable
        ) < 2:
            self._address_failure("shipping_address_verify_failed", "公共地址选择后未稳定回填到提交订单页")
        logger.info(
            "公共地址已应用 policy_match=%s phone=%s city=%s",
            bool(data.match),
            mask_phone(data.phone),
            data.city,
        )
        return True

    def _is_address_list_or_checkout(self) -> bool:
        return any(marker in self.page_blob() for marker in ("选择收货地址", "新增地址", "提交订单"))

    def _scroll_address_list_once(self) -> None:
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
        time.sleep(0.1)

    def _address_failure(self, stage: str, message: str) -> None:
        self.capture_shipping_failure(stage, sensitive=True)
        raise AssertionError(message)
