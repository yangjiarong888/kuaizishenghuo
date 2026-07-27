"""Thread-safe Appium driver session management."""

from __future__ import annotations

import threading

from appium import webdriver

from commons.android_runtime import (
    detect_launchable_activity,
    post_session_android_launch,
)
from commons.config import ConfigManager
from commons.logger import setup_logger


logger = setup_logger(__name__)

# Compatibility for existing imports and tests.
_detect_launchable_activity = detect_launchable_activity
_post_session_android_launch = post_session_android_launch


class DriverManager:
    """Cache Appium drivers by explicit session name."""

    _instance = None
    _lock = threading.Lock()
    _drivers: dict[str, object | None] = {}

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def get_driver(self, session_name: str = "default", **kwargs):
        existing = self._drivers.get(session_name)
        if existing is not None:
            return existing

        config_manager = ConfigManager()
        config = (
            config_manager.create_config(**kwargs)
            if kwargs
            else config_manager.get_default_config()
        )
        logger.info("创建新的驱动实例: %s", session_name)
        try:
            driver = webdriver.Remote(
                command_executor=config.appium_server_url,
                options=config.get_uiautomator2_options(),
            )
            post_session_android_launch(driver, config)
            driver.implicitly_wait(0)
        except Exception as exc:
            self._drivers.pop(session_name, None)
            logger.error(
                "创建驱动失败 session=%s error_type=%s",
                session_name,
                type(exc).__name__,
            )
            raise

        self._drivers[session_name] = driver
        logger.info("驱动实例 %s 创建成功", session_name)
        return driver

    def close_driver(self, session_name: str = "default") -> None:
        driver = self._drivers.get(session_name)
        if driver is None:
            return
        try:
            driver.quit()
            logger.info("驱动实例 %s 已关闭", session_name)
        except Exception as exc:
            logger.warning(
                "关闭驱动时出错 session=%s error_type=%s",
                session_name,
                type(exc).__name__,
            )
        finally:
            self._drivers[session_name] = None

    def close_all_drivers(self) -> None:
        for session_name in list(self._drivers):
            self.close_driver(session_name)
