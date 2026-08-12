import re

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait

from commons.diagnostics import capture_failure, redact_explicit_values

from .app_common import AppConfig, logger
from .shipping_address_mixin import ShippingAddressMixin
from .shipping_delivery_mixin import ShippingDeliveryMixin
from .shipping_payment_mixin import ShippingPaymentMixin
from .shipping_types import xpath_literal


class ShippingPage(ShippingPaymentMixin, ShippingDeliveryMixin, ShippingAddressMixin):
    """Navigation and diagnostics facade for the international shipping flow."""

    SHIPPING_TITLE = "国际货运"
    SHIPPING_SERVICE_MARKERS = ("寄件菲律宾", "寄件全球")
    DELIVERY_ORDERS_TAB = "配送订单"
    DELIVERY_ORDER_MARKERS = ("全部", "待付款", "待收货", "已完成", "已取消")
    HOME_TAB = "首页"
    _APP_HOME_ROOT_SELECTOR = (
        '//*[contains(@resource-id,"app_home_root") '
        'or @content-desc="筷子生活首页"]'
    )
    _SHIPPING_HOME_ROOT_SELECTOR = (
        '//*[contains(@resource-id,"shipping_home_content") '
        'or @content-desc="国际货运首页内容"]'
    )
    _DELIVERY_ORDERS_ROOT_SELECTOR = (
        '//*[contains(@resource-id,"delivery_order_list") '
        'or @content-desc="配送订单列表"]'
    )
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
            literal = xpath_literal(label)
            element = self._first_displayed(
                AppiumBy.XPATH,
                f'//*[@text={literal} or @content-desc={literal}]',
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
            literal = xpath_literal(label)
            field = self._first_displayed(
                AppiumBy.XPATH,
                f'//*[@text={literal} or @content-desc={literal}]'
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

    @staticmethod
    def _node_blob(node) -> str:
        values = []
        try:
            values.append(str(node.text or ""))
        except Exception:
            pass
        for attribute in ("text", "content-desc", "resource-id"):
            try:
                values.append(str(node.get_attribute(attribute) or ""))
            except Exception:
                pass
        return " ".join(dict.fromkeys(value.strip() for value in values if value.strip()))

    def _valid_identity_root(
        self,
        selector: str,
        required: tuple[str, ...],
        alternatives: tuple[str, ...] = (),
    ):
        try:
            candidates = self.driver.find_elements(AppiumBy.XPATH, selector)
        except Exception as exc:
            logger.debug(
                "Shipping identity lookup failed error_type=%s", type(exc).__name__
            )
            return None
        valid = []
        for candidate in candidates:
            try:
                if not candidate.is_displayed():
                    continue
            except Exception:
                continue
            blob = self._node_blob(candidate)
            if all(marker in blob for marker in required) and (
                not alternatives or any(marker in blob for marker in alternatives)
            ):
                valid.append(candidate)
        return valid[0] if len(valid) == 1 else None

    def _active_navigation_identity(self) -> str | None:
        identities = []
        if self._valid_identity_root(
            self._APP_HOME_ROOT_SELECTOR, ("筷子生活", "首页")
        ) is not None:
            identities.append("app_home")
        if self._valid_identity_root(
            self._SHIPPING_HOME_ROOT_SELECTOR,
            (self.SHIPPING_TITLE,),
            self.SHIPPING_SERVICE_MARKERS,
        ) is not None:
            identities.append("shipping_home")
        if self._valid_identity_root(
            self._DELIVERY_ORDERS_ROOT_SELECTOR,
            (self.DELIVERY_ORDERS_TAB,),
            self.DELIVERY_ORDER_MARKERS,
        ) is not None:
            identities.append("delivery_orders")
        return identities[0] if len(identities) == 1 else None

    def _is_app_home_page(self) -> bool:
        return self._active_navigation_identity() == "app_home"

    def _is_shipping_home_page(self) -> bool:
        return self._active_navigation_identity() == "shipping_home"

    def _is_delivery_orders_page(self) -> bool:
        return self._active_navigation_identity() == "delivery_orders"

    def wait_for_shipping_home(self, timeout=None) -> bool:
        """Wait until the shipping title and a service marker are both visible."""
        return self._wait_until(self._is_shipping_home_page, timeout)

    def enter_from_app_home(self) -> bool:
        if not self._is_app_home_page():
            logger.error("Chopsticks Life app home context not verified")
            self.capture_shipping_failure("shipping_app_home_unverified")
            return False
        literal = xpath_literal(self.SHIPPING_TITLE)
        entry = self._first_displayed(
            AppiumBy.XPATH,
            f'//*[@text={literal} or @content-desc={literal}]',
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
            logger.info(
                "shipping_navigation route=app_home_to_shipping entry=国际货运 result=success"
            )
            return True
        logger.error("International shipping entry destination timed out")
        self.capture_shipping_failure("shipping_entry_timeout")
        return False

    def switch_to_delivery_orders(self) -> bool:
        identity = self._active_navigation_identity()
        if identity == "delivery_orders":
            return True
        if identity != "shipping_home":
            logger.error("Shipping home context not verified before delivery tab switch")
            self.capture_shipping_failure("shipping_home_context_unverified")
            return False
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
        identity = self._active_navigation_identity()
        if identity == "shipping_home":
            return True
        if identity != "delivery_orders":
            logger.error("Shipping order-list context not verified before home tab switch")
            self.capture_shipping_failure("shipping_orders_context_unverified")
            return False
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
    def _safe_failure_stage(cls, stage: str, redact_values=()) -> str:
        explicit_redacted = redact_explicit_values(
            str(stage), redact_values, replacement="redacted"
        )
        redacted = cls._SECRET_STAGE_VALUE.sub(
            lambda match: f"{match.group(1)}_redacted", explicit_redacted
        )
        return re.sub(r"[^a-z0-9_-]+", "_", redacted.lower())[:80].strip("_") or "failure"

    def _context_redaction_values(self) -> tuple[str, ...]:
        try:
            return tuple(self._payment_redaction_values())
        except Exception:
            return ()

    def _is_sensitive_page_context(self) -> bool:
        blob = self.page_blob()
        if any(
            marker in blob
            for marker in (
                "提交订单",
                "选择收货地址",
                "请选择收货地址",
                "新增地址",
                "详细地址",
                "支付方式",
                "支付密码",
                "订单详情",
                "确认取消支付",
            )
        ):
            return True
        sensitive_roots = (
            self._CHECKOUT_ROOT_SELECTOR,
            self._ADDRESS_BOOK_ROOT_SELECTOR,
            self._ADDRESS_FORM_ROOT_SELECTOR,
            self._PAYMENT_PAGE_ROOT_SELECTOR,
            self._PAYMENT_PASSWORD_ROOT_SELECTOR,
            self._ORDER_DETAIL_ROOT_SELECTOR,
            self._CANCEL_DIALOG_ROOT_SELECTOR,
        )
        return any(
            self._first_displayed(AppiumBy.XPATH, selector) is not None
            for selector in sensitive_roots
        )

    def capture_shipping_failure(
        self,
        stage: str,
        sensitive: bool = False,
        redact_values=(),
        *,
        allow_nonsensitive_screenshot: bool = False,
    ) -> None:
        all_redact_values = tuple(
            dict.fromkeys((*self._context_redaction_values(), *tuple(redact_values)))
        )
        safe_stage = self._safe_failure_stage(stage, all_redact_values)
        hide_screenshot = (
            sensitive
            or self._is_sensitive_page_context()
            or (
                self._active_navigation_identity() is None
                and not allow_nonsensitive_screenshot
            )
        )
        artifacts = capture_failure(
            self.driver,
            safe_stage,
            AppConfig.ARTIFACTS_DIR,
            include_screenshot=not hide_screenshot,
            redact_values=all_redact_values,
        )
        logger.error(
            "Shipping flow failed stage=%s screenshot=%s page_source=%s",
            safe_stage,
            artifacts.screenshot,
            artifacts.page_source,
        )
