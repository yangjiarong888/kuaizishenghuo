"""共享配置与日志，避免 Home 与 takeout/shipping 循环导入。"""

import os

from appium.options.android import UiAutomator2Options

from commons.android_runtime import (
    detect_first_adb_device_id,
    detect_launchable_activity,
)
from commons.logger import setup_logger


logger = setup_logger()


class AppConfig:
    """集中管理Appium配置参数"""

    APPIUM_SERVER_URL = os.environ.get("APPIUM_SERVER_URL", "http://localhost:4723")
    WAIT_TIMEOUT = 25
    SHORT_WAIT = 3
    ARTIFACTS_DIR = os.environ.get("ARTIFACTS_DIR", os.path.join(os.getcwd(), "logs"))

    _detect_first_adb_device_id = staticmethod(detect_first_adb_device_id)
    _detect_launchable_activity = staticmethod(detect_launchable_activity)

    @staticmethod
    def get_android_options():
        options = UiAutomator2Options()
        options.platform_name = "Android"
        device_name = os.environ.get("ANDROID_DEVICE_NAME")
        if not device_name:
            device_name = AppConfig._detect_first_adb_device_id() or "P7T4XC99CYAEYL4H"
        options.device_name = device_name
        app_package = os.environ.get("APP_PACKAGE", "com.bs.feifubao")
        options.app_package = app_package
        app_activity = os.environ.get("APP_ACTIVITY")
        if not app_activity:
            app_activity = AppConfig._detect_launchable_activity(app_package)
        if app_activity:
            options.app_activity = app_activity
        else:
            logger.warning("⚠️ 未能自动识别启动 Activity；可通过环境变量 APP_ACTIVITY 指定")
        options.automation_name = "UiAutomator2"
        options.no_reset = os.environ.get("NO_RESET", "true").strip().lower() in (
            "1",
            "true",
            "yes",
            "y",
        )
        options.unicode_keyboard = True
        options.reset_keyboard = True
        options.set_capability("appium:chromedriverAutodownload", True)
        options.set_capability("appium:autoWebview", False)
        options.set_capability("appium:ensureWebviewsHavePages", True)
        return options
