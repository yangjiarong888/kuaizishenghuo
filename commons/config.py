# commons/config.py
"""
配置文件管理 - 简化版本（不使用yaml）
"""
from dataclasses import dataclass
from appium.options.android import UiAutomator2Options


@dataclass
class DeviceConfig:
    """设备配置基类"""
    platform_name: str = "Android"
    automation_name: str = "UiAutomator2"
    device_name: str = "P7T4XC99CYAEYL4H"  # 默认设备
    no_reset: bool = True
    unicode_keyboard: bool = True
    reset_keyboard: bool = True
    new_command_timeout: int = 300
    
    # 基础URL
    @property
    def appium_server_url(self) -> str:
        return "http://localhost:4723"


@dataclass
class AppConfig(DeviceConfig):
    """App配置类"""
    app_package: str = "com.bs.feifubao"
    app_activity: str = "com.bs.feifubao.activity.MainActivity"
    
    def get_desired_caps(self) -> dict:
        """返回Desired Capabilities字典"""
        return {
            "platformName": self.platform_name,
            "deviceName": self.device_name,
            "appPackage": self.app_package,
            "appActivity": self.app_activity,
            "noReset": self.no_reset,
            "unicodeKeyboard": self.unicode_keyboard,
            "resetKeyboard": self.reset_keyboard,
            "automationName": self.automation_name,
            "newCommandTimeout": self.new_command_timeout
        }
    
    def get_uiautomator2_options(self) -> UiAutomator2Options:
        """返回UiAutomator2Options对象"""
        options = UiAutomator2Options()
        options.platform_name = self.platform_name
        options.device_name = self.device_name
        options.app_package = self.app_package
        options.app_activity = self.app_activity
        options.no_reset = self.no_reset
        options.unicode_keyboard = self.unicode_keyboard
        options.reset_keyboard = self.reset_keyboard
        options.automation_name = self.automation_name
        options.new_command_timeout = self.new_command_timeout
        options.set_capability("appium:chromedriverAutodownload", True)
        options.set_capability("appium:autoWebview", False)
        options.set_capability("appium:ensureWebviewsHavePages", True)
        
        return options


class ConfigManager:
    """配置管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance
    
    def get_default_config(self) -> AppConfig:
        """获取默认配置"""
        return AppConfig()
    
    def create_config(self, **kwargs) -> AppConfig:
        """动态创建配置"""
        config = AppConfig()
        
        # 更新参数
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        return config