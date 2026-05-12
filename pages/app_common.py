"""共享配置与日志，避免 Home 与 takeout/shipping 循环导入。"""

import logging
import os
import subprocess
import sys
from datetime import datetime

from appium.options.android import UiAutomator2Options


def setup_logger(name=__name__):
    """配置日志系统"""
    logs_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_filename = os.path.join(
        logs_dir, f'chopsticks_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    )

    lg = logging.getLogger(name)
    lg.setLevel(logging.INFO)

    if not lg.handlers:
        try:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

        file_handler = logging.FileHandler(log_filename, encoding="utf-8")
        console_handler = logging.StreamHandler(sys.stdout)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        lg.addHandler(file_handler)
        lg.addHandler(console_handler)

    return lg


logger = setup_logger()


class AppConfig:
    """集中管理Appium配置参数"""

    APPIUM_SERVER_URL = os.environ.get("APPIUM_SERVER_URL", "http://localhost:4723")
    WAIT_TIMEOUT = 25
    SHORT_WAIT = 3
    ARTIFACTS_DIR = os.environ.get("ARTIFACTS_DIR", os.path.join(os.getcwd(), "logs"))

    @staticmethod
    def _detect_first_adb_device_id():
        """从 adb 获取第一台已连接设备 ID；失败返回 None"""
        try:
            cp = subprocess.run(
                ["adb", "devices"], capture_output=True, text=True, timeout=8
            )
            if cp.returncode != 0:
                return None
            lines = [ln.strip() for ln in cp.stdout.splitlines() if ln.strip()]
            for ln in lines[1:]:
                parts = ln.split()
                if len(parts) >= 2 and parts[1] == "device":
                    return parts[0]
            return None
        except Exception:
            return None

    @staticmethod
    def _detect_launchable_activity(app_package: str):
        """自动解析可启动 Activity；失败返回 None"""
        try:
            cp = subprocess.run(
                ["adb", "shell", "cmd", "package", "resolve-activity", "--brief", app_package],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if cp.returncode != 0:
                return None
            lines = [ln.strip() for ln in cp.stdout.splitlines() if ln.strip()]
            if not lines:
                return None
            component = lines[-1]
            if "/" not in component:
                return None
            pkg, act = component.split("/", 1)
            if not pkg or not act:
                return None
            if act.startswith("."):
                return f"{pkg}{act}"
            return act
        except Exception:
            return None

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
