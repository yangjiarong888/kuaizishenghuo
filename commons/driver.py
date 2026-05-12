# commons/driver.py
"""
驱动管理 - 简化版本

会话建立后可选二次拉起（与 pages/Home.py 对齐），减轻 noReset 下仍回到上次栈顶
（活动页 / WebView 等）的问题：

  START_MODE=cold     默认：terminate_app + start_activity（推荐）
  START_MODE=activate 仅 activate_app
  START_MODE=off      跳过，完全依赖 Appium 首次拉起行为

包名与入口 Activity：优先环境变量 APP_PACKAGE / APP_ACTIVITY，否则用 ConfigManager 默认值；
未配置 APP_ACTIVITY 时尝试 adb resolve-activity。
"""
from __future__ import annotations

import os
import subprocess
import threading
from appium import webdriver
from .config import ConfigManager
from .logger import setup_logger  # 修复导入

logger = setup_logger(__name__)


def _detect_launchable_activity(app_package: str) -> str | None:
    """自动解析可启动 Activity；失败返回 None（与 pages/app_common.py 逻辑一致）。"""
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


def _post_session_android_launch(driver, config) -> None:
    """新建会话后按 START_MODE 再次拉起 App，与 Home.setup_driver 行为一致。"""
    start_mode = os.environ.get("START_MODE", "cold").strip().lower()
    if start_mode in ("off", "none", "skip", "0", "false", "no"):
        logger.info("START_MODE=%s，跳过会话后二次拉起", start_mode or "off")
        return

    app_package = os.environ.get("APP_PACKAGE", config.app_package)
    env_activity = os.environ.get("APP_ACTIVITY")
    launch_activity = (env_activity or "").strip() or config.app_activity
    if not launch_activity:
        launch_activity = _detect_launchable_activity(app_package)

    if start_mode == "activate":
        try:
            logger.info("START_MODE=activate，激活 App: %s", app_package)
            driver.activate_app(app_package)
        except Exception as e:
            logger.debug("activate_app 失败: %s", e)
        return

    if start_mode != "cold":
        logger.warning("未知 START_MODE=%s，按 cold 处理", start_mode)

    try:
        logger.info("START_MODE=cold，终止并冷启动 App: %s", app_package)
        try:
            driver.terminate_app(app_package)
        except Exception:
            pass
        if launch_activity:
            logger.info("start_activity: %s/%s", app_package, launch_activity)
            driver.start_activity(app_package, launch_activity)
        else:
            logger.warning("未解析到可启动 Activity，改用 activate_app")
            driver.activate_app(app_package)
    except Exception as e:
        logger.debug("cold 启动失败，尝试 activate_app: %s", e)
        try:
            driver.activate_app(app_package)
        except Exception:
            pass


class DriverManager:
    """驱动管理器（单例模式）"""
    
    _instance = None
    _lock = threading.Lock()
    _drivers = {}
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DriverManager, cls).__new__(cls)
        return cls._instance
    
    def get_driver(self, 
                  session_name: str = "default",
                  **kwargs):
        """
        获取或创建驱动实例
        """
        if session_name not in self._drivers or self._drivers[session_name] is None:
            logger.info(f"创建新的驱动实例: {session_name}")
            
            # 获取配置管理器
            config_manager = ConfigManager()
            
            if kwargs:
                # 动态创建配置
                config = config_manager.create_config(**kwargs)
            else:
                # 使用默认配置
                config = config_manager.get_default_config()
            
            try:
                # 创建驱动
                options = config.get_uiautomator2_options()
                driver = webdriver.Remote(
                    command_executor=config.appium_server_url,
                    options=options
                )

                _post_session_android_launch(driver, config)

                # 隐式等待过长会与 WebDriverWait 叠加，单次查找可达数十秒级；登录页脚本以显式等待为主
                driver.implicitly_wait(1)
                
                self._drivers[session_name] = driver
                logger.info(f"驱动实例 {session_name} 创建成功")
                
            except Exception as e:
                logger.error(f"创建驱动失败: {e}")
                raise
        
        return self._drivers[session_name]
    
    def close_driver(self, session_name: str = "default"):
        """关闭指定驱动"""
        if session_name in self._drivers and self._drivers[session_name]:
            try:
                self._drivers[session_name].quit()
                self._drivers[session_name] = None
                logger.info(f"驱动实例 {session_name} 已关闭")
            except Exception as e:
                logger.warning(f"关闭驱动时出错: {e}")
    
    def close_all_drivers(self):
        """关闭所有驱动"""
        for session_name in list(self._drivers.keys()):
            self.close_driver(session_name)