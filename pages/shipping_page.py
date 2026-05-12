import time

from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from .app_common import logger, AppConfig


class ShippingPage:
    """海运业务页面对象（骨架版）

    这里先提供一个可运行的基础流程：
    1. 等待海运首页加载
    2. 简单执行一两个核心操作占位（根据你后续提供的具体流程再细化）
    """

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, AppConfig.WAIT_TIMEOUT)

    def _find(self, by, value, timeout=None):
        try:
            return WebDriverWait(self.driver, timeout or AppConfig.WAIT_TIMEOUT).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            return None

    def _click(self, by, value, timeout=None):
        try:
            el = WebDriverWait(self.driver, timeout or AppConfig.WAIT_TIMEOUT).until(
                EC.element_to_be_clickable((by, value))
            )
            el.click()
            return True
        except TimeoutException:
            return False

    def wait_for_shipping_home(self):
        """通过关键文案判断是否在海运首页"""
        logger.info("等待海运首页加载...")
        indicators = [
            (AppiumBy.XPATH, '//*[contains(@text, "海运")]'),
            (AppiumBy.XPATH, '//*[contains(@text, "海运物流")]'),
        ]
        for by, value in indicators:
            el = self._find(by, value, timeout=8)
            if el:
                logger.info("✅ 海运首页加载完成")
                return True
        logger.warning("⚠️ 未能确认海运首页，请检查定位器是否需要调整")
        return False

    def run_main_flow(self):
        """海运业务主流程占位：目前只做『页面可达 + 关键元素存在』校验"""
        if not self.wait_for_shipping_home():
            return False

        # TODO: 根据你后续的海运业务路径，补充具体操作，比如：
        # 选择出发/到达港口、选择货物类型、计算运费、提交运单等。
        logger.info("✅ 海运业务页面已打开（后续业务步骤可在 ShippingPage.run_main_flow 中继续完善）")
        time.sleep(1)
        return True

