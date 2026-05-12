"""
冒烟测试 - 线性脚本
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from commons.driver import DriverManager
from commons.config import ConfigManager
from appium import webdriver
import time


def smoke_test():
    """冒烟测试 - 直接使用字典配置"""
    print("开始冒烟测试...")
    
    # 1. 准备Desired Capabilities字典
    desired_caps = {
        "platformName": "Android",
        "deviceName": "127.0.0.1:62001",  # 模拟器
        "platformVersion": "7.1",
        "appPackage": "com.bs.feifubao",
        "appActivity": "com.bs.feifubao.activity.MainActivity",
        "noReset": True,
        "unicodeKeyboard": True,
        "resetKeyboard": True,
        "automationName": "UiAutomator2"
    }
    
    # 2. 创建驱动
    try:
        print("启动Appium驱动...")
        driver = webdriver.Remote(
            'http://localhost:4723/wd/hub',
            desired_capabilities=desired_caps
        )
        driver.implicitly_wait(10)
        
        print("✅ 驱动启动成功")
        
        # 3. 简单的首页验证
        time.sleep(3)
        
        # 检查首页元素
        try:
            # 搜索框
            search_box = driver.find_element("id", "com.bs.feifubao:id/et_search")
            print("✅ 首页搜索框加载成功")
            
            # 底部导航
            home_tab = driver.find_element("xpath", '//android.widget.TextView[@text="首页"]')
            print(f"✅ 底部导航: {home_tab.text}")
            
            # 金刚区
            golden_items = driver.find_elements("id", "com.bs.feifubao:id/ll_menu")
            print(f"✅ 找到 {len(golden_items)} 个金刚区项目")
            
        except Exception as e:
            print(f"⚠️ 首页元素验证失败: {e}")
        
        # 4. 清理
        driver.quit()
        print("✅ 冒烟测试完成")
        
    except Exception as e:
        print(f"❌ 冒烟测试失败: {e}")


def test_with_dynamic_config():
    """使用动态配置的测试"""
    print("动态配置测试...")
    
    # 获取配置管理器
    config_manager = ConfigManager()
    
    # 测试不同的活动名
    test_cases = [
        ("首页测试", "com.bs.feifubao.activity.MainActivity"),
        ("登录测试", "com.bs.feifubao.activity.LoginActivity"),
        ("下单测试", "com.bs.feifubao.activity.OrderActivity"),
    ]
    
    for test_name, activity in test_cases:
        print(f"\n开始 {test_name}...")
        
        # 动态创建配置
        config = config_manager.create_config(
            app_activity=activity,
            device_name="P7T4XC99CYAEYL4H"  # 真实设备
        )
        
        try:
            # 创建驱动
            options = config.get_uiautomator2_options()
            driver = webdriver.Remote(
                command_executor=config.appium_server_url,
                options=options
            )
            
            print(f"✅ {test_name} - 启动成功")
            print(f"   Activity: {activity}")
            print(f"   设备: {config.device_name}")
            
            # 简单的等待和验证
            time.sleep(2)
            print(f"   当前Activity: {driver.current_activity}")
            
            # 关闭驱动
            driver.quit()
            print(f"✅ {test_name} - 完成")
            
        except Exception as e:
            print(f"❌ {test_name} - 失败: {e}")


if __name__ == "__main__":
    # 执行冒烟测试
    smoke_test()
    
    # 执行动态配置测试
    # test_with_dynamic_config()