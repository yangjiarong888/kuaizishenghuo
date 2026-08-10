import re

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait

from commons.diagnostics import capture_failure

from .app_common import AppConfig, logger


class ShippingPage:
    """Navigation and diagnostics facade for the international shipping flow."""

    SHIPPING_TITLE = "鍥介檯璐ц繍"
    SHIPPING_SERVICE_MARKERS = (
        "瀵勪欢鑿插緥瀹�",
        "瀵勪欢鍏ㄧ悆",
        "閰嶉€佽鍗�",
    )
    DELIVERY_ORDERS_TAB = "閰嶉€佽鍗�"
    DELIVERY_ORDER_MARKERS = (
        "鍏ㄩ儴",
        "寰呬粯娆�",
        "寰呮敹璐�",
        "宸插畬鎴�",
        "宸插彇娑�",
    )
    HOME_TAB = "棣栭〉"

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, AppConfig.WAIT_TIMEOUT)

    def _first_displayed(self, by, value):
        for element in self.driver.find_elements(by, value):
            try:
                if element.is_displayed():
                    return element
            except Exception:
                continue
        return None

    def _click_text(self, labels) -> bool:
        for label in labels:
            element = self._first_displayed(
                AppiumBy.XPATH,
                f'//*[@text="{label}" or @content-desc="{label}" '
                f'or contains(@content-desc,"{label}")]',
            )
            if element is None:
                continue
            try:
                if element.is_enabled():
                    element.click()
                    return True
            except Exception:
                continue
        return False

    def _wait_until(self, predicate, timeout=None) -> bool:
        try:
            return bool(
                WebDriverWait(
                    self.driver,
                    timeout if timeout is not None else AppConfig.WAIT_TIMEOUT,
                ).until(
                    lambda _driver: predicate()
                )
            )
        except TimeoutException:
            return False

    def page_blob(self) -> str:
        try:
            return self.driver.page_source or ""
        except Exception:
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
            '//*[@text="鍥介檯璐ц繍" or @content-desc="鍥介檯璐ц繍" '
            'or contains(@content-desc,"鍥介檯璐ц繍")]',
        )
        if entry is None:
            logger.error("App 棣栭〉鏈壘鍒板浗闄呰揣杩愬叆鍙�")
            self.capture_shipping_failure("shipping_entry_missing")
            return False
        entry.click()
        return self.wait_for_shipping_home()

    def switch_to_delivery_orders(self) -> bool:
        if self._is_delivery_orders_page():
            return True
        if not self._click_text((self.DELIVERY_ORDERS_TAB,)):
            return False
        return self._wait_until(self._is_delivery_orders_page)

    def switch_to_shipping_home(self) -> bool:
        if self._is_shipping_home_page():
            return True
        if not self._click_text((self.SHIPPING_TITLE, self.HOME_TAB)):
            return False
        return self._wait_until(self._is_shipping_home_page)

    def capture_shipping_failure(self, stage: str) -> None:
        safe_stage = re.sub(r"[^a-z0-9_-]+", "_", stage.lower())[:80]
        artifacts = capture_failure(self.driver, safe_stage, AppConfig.ARTIFACTS_DIR)
        logger.error(
            "Shipping flow failed stage=%s screenshot=%s page_source=%s",
            safe_stage,
            artifacts.screenshot,
            artifacts.page_source,
        )
