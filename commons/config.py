"""Typed Appium configuration with environment overrides."""

from __future__ import annotations

import os
from dataclasses import dataclass, replace

from appium.options.android import UiAutomator2Options


TRUE_VALUES = frozenset({"1", "true", "yes", "y", "on"})
FALSE_VALUES = frozenset({"0", "false", "no", "n", "off"})


def parse_bool(value: str | None, *, default: bool) -> bool:
    """Parse common boolean tokens, falling back for unknown values."""
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return default


@dataclass(frozen=True)
class DeviceConfig:
    """Device and Appium server settings."""

    platform_name: str = "Android"
    automation_name: str = "UiAutomator2"
    device_name: str = "P7T4XC99CYAEYL4H"
    no_reset: bool = True
    unicode_keyboard: bool = True
    reset_keyboard: bool = True
    new_command_timeout: int = 300
    appium_server_url: str = "http://localhost:4723"


@dataclass(frozen=True)
class AppConfig(DeviceConfig):
    """Application settings with environment-aware construction."""

    app_package: str = "com.bs.feifubao"
    app_activity: str = "com.bs.feifubao.activity.MainActivity"

    @classmethod
    def from_env(cls) -> "AppConfig":
        defaults = cls()
        return cls(
            appium_server_url=os.environ.get(
                "APPIUM_SERVER_URL", defaults.appium_server_url
            ).rstrip("/"),
            device_name=os.environ.get(
                "ANDROID_DEVICE_NAME", defaults.device_name
            ).strip()
            or defaults.device_name,
            app_package=os.environ.get("APP_PACKAGE", defaults.app_package).strip()
            or defaults.app_package,
            app_activity=os.environ.get("APP_ACTIVITY", defaults.app_activity).strip()
            or defaults.app_activity,
            no_reset=parse_bool(
                os.environ.get("NO_RESET"), default=defaults.no_reset
            ),
        )

    def get_desired_caps(self) -> dict:
        """Return the legacy capabilities mapping for compatibility."""
        return {
            "platformName": self.platform_name,
            "deviceName": self.device_name,
            "appPackage": self.app_package,
            "appActivity": self.app_activity,
            "noReset": self.no_reset,
            "unicodeKeyboard": self.unicode_keyboard,
            "resetKeyboard": self.reset_keyboard,
            "automationName": self.automation_name,
            "newCommandTimeout": self.new_command_timeout,
        }

    def get_uiautomator2_options(self) -> UiAutomator2Options:
        """Build Appium 2/3-compatible UiAutomator2 options."""
        options = UiAutomator2Options()
        for key, value in self.get_desired_caps().items():
            options.set_capability(key, value)
        options.set_capability("appium:chromedriverAutodownload", True)
        options.set_capability("appium:autoWebview", False)
        options.set_capability("appium:ensureWebviewsHavePages", True)
        return options


class ConfigManager:
    """Compatibility singleton for configuration creation."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_default_config(self) -> AppConfig:
        return AppConfig.from_env()

    def create_config(self, **kwargs) -> AppConfig:
        config = self.get_default_config()
        known = {key: value for key, value in kwargs.items() if hasattr(config, key)}
        return replace(config, **known)
