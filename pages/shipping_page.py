import re

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait

from commons.diagnostics import capture_failure

from .app_common import AppConfig, logger
from .shipping_address_mixin import ShippingAddressMixin


class ShippingPage(ShippingAddressMixin):
    """Navigation and diagnostics facade for the international shipping flow."""

    SHIPPING_TITLE = "国际货运"
    SHIPPING_SERVICE_MARKERS = ("寄件菲律宾", "寄件全球", "配送订单")
    DELIVERY_ORDERS_TAB = "配送订单"
    DELIVERY_ORDER_MARKERS = ("全部", "待付款", "待收货", "已完成", "已取消")
    HOME_TAB = "首页"
    _SECRET_STAGE_VALUE = re.compile(
        r"(?i)(?<![a-z0-9_])(pay_password|access_token|verification_code|"
        r"password|passwd|pwd|token|secret)(?:\s*[:=]\s*|\s+)[^\s/,&]+"
    )

    def __init__(self, driver):
        self.driver = driver

    def _first_displayed(self, by, value):
        try:
            elements = self.driver.find_elements(by, value)
        except Exception as exc:
            logger.debug(
                "Shipping element lookup failed error_type=%s", type(exc).__name__
            )
            return None
        for element in elements:
            try:
                if element.is_displayed():
                    return element
            except Exception as exc:
                logger.debug(
                    "Shipping element visibility check failed error_type=%s",
                    type(exc).__name__,
                )
        return None

    def _click_text(self, labels) -> bool:
        for label in labels:
            element = self._first_displayed(
                AppiumBy.XPATH,
                f'//*[@text="{label}" or @content-desc="{label}"]',
            )
            if element is None:
                continue
            try:
                if element.is_enabled():
                    element.click()
                    return True
            except Exception as exc:
                logger.debug(
                    "Shipping tab click failed error_type=%s", type(exc).__name__
                )
                return False
        return False

    def _wait_until(self, predicate, timeout=None) -> bool:
        try:
            return bool(
                WebDriverWait(
                    self.driver,
                    timeout if timeout is not None else AppConfig.WAIT_TIMEOUT,
                ).until(lambda _driver: predicate())
            )
        except TimeoutException:
            return False

    def _type_field(self, labels, value: str) -> bool:
        for label in labels:
            field = self._first_displayed(
                AppiumBy.XPATH,
                f'//*[@text="{label}" or @content-desc="{label}"]'
                "/following::android.widget.EditText[1]",
            )
            if field is None:
                continue
            try:
                field.click()
                try:
                    field.clear()
                except Exception:
                    pass
                field.send_keys(value)
                return True
            except Exception as exc:
                logger.debug("Shipping address field entry failed error_type=%s", type(exc).__name__)
        return False

    def page_blob(self) -> str:
        try:
            return self.driver.page_source or ""
        except Exception as exc:
            logger.debug("Shipping page source unavailable error_type=%s", type(exc).__name__)
            return ""

    def _is_shipping_home_page(self) -> bool:
        blob = self.page_blob()
        return self.SHIPPING_TITLE in blob and any(
            marker in blob for marker in self.SHIPPING_SERVICE_MARKERS
        )

    def _is_delivery_orders_page(self) -> bool:
        blob = self.page_blob()
        return self.DELIVERY_ORDERS_TAB in blob and any(
            marker in blob for marker in self.DELIVERY_ORDER_MARKERS
        )

    def wait_for_shipping_home(self, timeout=None) -> bool:
        """Wait until the shipping title and a service marker are both visible."""
        return self._wait_until(self._is_shipping_home_page, timeout)

    def enter_from_app_home(self) -> bool:
        if self.wait_for_shipping_home(timeout=1):
            return True
        entry = self._first_displayed(
            AppiumBy.XPATH,
            '//*[@text="国际货运" or @content-desc="国际货运"]',
        )
        if entry is None:
            logger.error("International shipping entry not found")
            self.capture_shipping_failure("shipping_entry_missing")
            return False
        try:
            entry.click()
        except Exception as exc:
            logger.error(
                "International shipping entry click failed error_type=%s",
                type(exc).__name__,
            )
            self.capture_shipping_failure("shipping_entry_click_failed")
            return False
        if self.wait_for_shipping_home():
            return True
        logger.error("International shipping entry destination timed out")
        self.capture_shipping_failure("shipping_entry_timeout")
        return False

    def switch_to_delivery_orders(self) -> bool:
        if self._is_delivery_orders_page():
            return True
        if not self._click_text((self.DELIVERY_ORDERS_TAB,)):
            logger.error("Shipping delivery-orders tab not available")
            self.capture_shipping_failure("shipping_delivery_tab_missing")
            return False
        if self._wait_until(self._is_delivery_orders_page):
            return True
        logger.error("Shipping delivery-orders tab destination timed out")
        self.capture_shipping_failure("shipping_delivery_tab_timeout")
        return False

    def switch_to_shipping_home(self) -> bool:
        if self._is_shipping_home_page():
            return True
        if not self._click_text((self.SHIPPING_TITLE, self.HOME_TAB)):
            logger.error("Shipping home tab not available")
            self.capture_shipping_failure("shipping_home_tab_missing")
            return False
        if self._wait_until(self._is_shipping_home_page):
            return True
        logger.error("Shipping home tab destination timed out")
        self.capture_shipping_failure("shipping_home_tab_timeout")
        return False

    @classmethod
    def _safe_failure_stage(cls, stage: str) -> str:
        redacted = cls._SECRET_STAGE_VALUE.sub(
            lambda match: f"{match.group(1)}_redacted", str(stage)
        )
        return re.sub(r"[^a-z0-9_-]+", "_", redacted.lower())[:80].strip("_") or "failure"

    def capture_shipping_failure(
        self, stage: str, sensitive: bool = False, redact_values=()
    ) -> None:
        safe_stage = self._safe_failure_stage(stage)
        artifacts = capture_failure(
            self.driver,
            safe_stage,
            AppConfig.ARTIFACTS_DIR,
            include_screenshot=not sensitive,
            redact_values=redact_values,
        )
        logger.error(
            "Shipping flow failed stage=%s screenshot=%s page_source=%s",
            safe_stage,
            artifacts.screenshot,
            artifacts.page_source,
        )
