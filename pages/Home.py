#!/usr/bin/env python3
"""
筷子生活App首页自动化测试脚本
整合弹窗处理、搜索功能、客服按钮、金刚区点击测试等完整功能
"""

import time
import os
import subprocess
from datetime import datetime
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.common.exceptions import WebDriverException
from appium import webdriver
from appium.webdriver.appium_connection import AppiumConnection
from appium.webdriver.common.appiumby import AppiumBy

from .app_common import logger, AppConfig
from .takeout_page import TakeoutPage
from .shipping_page import ShippingPage

# ================ 核心测试类 ================
class ChopsticksTester:
    """筷子生活首页综合测试"""

    # 公共元素配置，避免在方法中重复定义，便于维护
    POPUP_TEXTS = ["新用户专享", "1888元大礼包", "立即注册领取"]
    POPUP_INDICATORS = [
        {"type": "text", "value": "新用户专享"},
        {"type": "text", "value": "1888元大礼包"},
        {"type": "text", "value": "立即注册领取"},
        {"type": "text", "value": "新用户"},
        {"type": "id", "value": "com.bs.feifubao:id/tv_popup_title"},
        {"type": "id", "value": "com.bs.feifubao:id/iv_close"},
    ]
    SEARCH_ELEMENTS = [
        {"by": AppiumBy.XPATH, "value": '//android.widget.TextView[@text="搜索商家或商品"]', "desc": "搜索提示文本"},
        {"by": AppiumBy.ID, "value": "com.bs.feifubao:id/et_search", "desc": "搜索输入框"},
        {"by": AppiumBy.ID, "value": "com.bs.feifubao:id/ll_search", "desc": "搜索布局容器"},
        {"by": AppiumBy.ID, "value": "com.bs.feifubao:id/iv_search", "desc": "搜索图标"},
    ]
    CUSTOMER_SERVICE_SELECTORS = [
        {"by": AppiumBy.ID, "value": "com.bs.feifubao:id/iv_user_chat", "desc": "用户-客服/聊天入口"},
        {"by": AppiumBy.XPATH, "value": '//android.widget.ImageView[@resource-id="com.bs.feifubao:id/iv_user_chat"]', "desc": "用户-客服入口xpath（）"},
        {"by": AppiumBy.ID, "value": "com.bs.feifubao:id/iv_customer_service", "desc": "客服按钮"},
        {"by": AppiumBy.ID, "value": "com.bs.feifubao:id/iv_chat", "desc": "聊天按钮"},
        {"by": AppiumBy.ID, "value": "com.bs.feifubao:id/iv_service", "desc": "服务按钮"},
        {"by": AppiumBy.XPATH, "value": '//android.widget.ImageView[@content-desc="客服"]', "desc": "客服图标"},
        {"by": AppiumBy.XPATH, "value": '//android.widget.TextView[@text="客服"]', "desc": "客服文本"},
    ]
    LOGIN_INDICATORS = [
        (AppiumBy.XPATH, '//*[contains(@text, "登录")]'),
        (AppiumBy.XPATH, '//android.widget.TextView[@text="立即登录"]'),
        (AppiumBy.XPATH, '//*[contains(@text, "登录或注册")]'),
        (AppiumBy.XPATH, '//*[contains(@text, "微信账号快捷登录")]'),
        (AppiumBy.XPATH, '//*[contains(@text, "QQ账号快捷登录")]'),
        (AppiumBy.XPATH, '//*[contains(@text, "手机号")]'),
    ]
    CHAT_INDICATORS = [
        (AppiumBy.XPATH, '//*[contains(@text, "客服")]'),
        (AppiumBy.XPATH, '//*[contains(@text, "在线")]'),
        (AppiumBy.XPATH, '//*[contains(@text, "消息")]'),
    ]

    # 金刚区业务入口映射：名称 -> 业务类型
    GOLDEN_BUSINESS_MAP = {
        "外卖": "takeout",
        "美食外卖": "takeout",
        "海运": "shipping",
        "海运物流": "shipping",
    }

    def __init__(self):
        self.driver = None

    def _wait(self, timeout=None):
        return WebDriverWait(self.driver, timeout or AppConfig.WAIT_TIMEOUT)

    def _find(self, by, value, timeout=None):
        """显式等待单个元素出现，失败返回 None"""
        try:
            return self._wait(timeout).until(EC.presence_of_element_located((by, value)))
        except TimeoutException:
            return None

    def _find_all_now(self, by, value):
        """不抛异常的多元素查找"""
        try:
            return self.driver.find_elements(by, value)
        except Exception:
            return []

    def _click_when_clickable(self, by, value, timeout=None):
        """等待可点击并点击，成功 True"""
        try:
            el = self._wait(timeout).until(EC.element_to_be_clickable((by, value)))
            el.click()
            return True
        except Exception:
            return False

    def _tap_xy(self, x, y):
        """点击屏幕坐标（带兼容回退）"""
        x_i, y_i = int(x), int(y)
        try:
            self.driver.execute_script("mobile: clickGesture", {"x": x_i, "y": y_i})
            return True
        except Exception:
            pass
        try:
            # 兼容旧版本 client（不保证存在）
            if hasattr(self.driver, "tap"):
                self.driver.tap([(x_i, y_i)])
                return True
        except Exception:
            pass
        return False

    def _is_uia2_instrumentation_down(self, err: Exception) -> bool:
        msg = str(err) or ""
        return "instrumentation process is not running" in msg.lower()
    
    def setup_driver(self):
        """初始化Appium驱动"""
        try:
            logger.info("🚀 启动Appium驱动...")
            options = AppConfig.get_android_options()
            app_package = os.environ.get("APP_PACKAGE", "com.bs.feifubao")
            app_activity = os.environ.get("APP_ACTIVITY")
            start_mode = os.environ.get("START_MODE", "cold").strip().lower()  # cold|activate
            # 注意：此环境下 `//session` 会 404，所以 remote_server_addr 不要以 `/` 结尾
            server_url = AppConfig.APPIUM_SERVER_URL.rstrip("/")
            last_error = None
            candidates = [server_url]
            if os.environ.get("USE_WD_HUB", "false").strip().lower() in ("1", "true", "yes", "y"):
                candidates.append(f"{server_url}/wd/hub")

            for url in candidates:
                try:
                    conn = AppiumConnection(remote_server_addr=url)
                    self.driver = webdriver.Remote(command_executor=conn, options=options)
                    break
                except Exception as e:
                    last_error = e
                    self.driver = None
            if not self.driver:
                raise last_error or RuntimeError("Failed to create Appium driver")
            # 避免 implicit wait 叠加导致 find_elements 卡顿；统一用显式等待更稳定可控
            self.driver.implicitly_wait(0)

            # 启动策略（稳定性优先）：默认 cold 启动，尽量落在入口页/首页
            if start_mode == "activate":
                try:
                    logger.info(f"启动模式=activate，激活 App: {app_package}")
                    self.driver.activate_app(app_package)
                except Exception as e:
                    logger.debug(f"activate_app 失败，回退 cold 启动: {e}")
                    start_mode = "cold"

            if start_mode == "cold":
                launch_activity = app_activity or AppConfig._detect_launchable_activity(app_package)
                try:
                    logger.info(f"启动模式=cold，终止并冷启动 App: {app_package}")
                    try:
                        self.driver.terminate_app(app_package)
                    except Exception:
                        pass
                    if launch_activity:
                        logger.info(f"start_activity: {app_package}/{launch_activity}")
                        self.driver.start_activity(app_package, launch_activity)
                    else:
                        logger.warning("⚠️ 未解析到可启动 Activity，改用 activate_app")
                        self.driver.activate_app(app_package)
                except Exception as e:
                    logger.debug(f"cold 启动失败，尝试 activate_app: {e}")
                    self.driver.activate_app(app_package)

            logger.info("✅ 驱动启动成功")
            return True
        except Exception as e:
            logger.error(f"❌ 驱动启动失败: {e}")
            return False

    def ensure_homepage(self, max_attempts=6):
        """尽量确保回到首页（处理启动落在 H5/Flutter 容器页等情况）"""
        logger.info("确保回到首页（稳定性兜底）...")
        if self.wait_for_homepage():
            return True

        for attempt in range(max_attempts):
            logger.info(f"回首页兜底尝试 {attempt+1}/{max_attempts}")

            # 优先点底部首页 tab
            if self._click_bottom_home_tab():
                return True

            # 再尝试返回
            try:
                self.driver.back()
            except Exception:
                pass

            if self.wait_for_homepage():
                return True

        logger.error("❌ 兜底后仍未回到首页")
        self._debug_current_page()
        return False
    
    def wait_for_homepage(self):
        """等待首页加载 - 多重验证策略"""
        logger.info("等待首页加载...")
        # 等待 App 稳定：优先等“首页”tab出现（比固定 sleep 稳定）
        self._find(AppiumBy.XPATH, '//android.widget.TextView[@text="首页"]', timeout=AppConfig.WAIT_TIMEOUT)
        
        # 基于首页部分功能按钮验证的首页元素
        verification_methods = [
            self._verify_by_bottom_nav,
            self._verify_by_search_box,
            self._verify_by_golden_zone,
            self._verify_by_ad_banner
        ]
        
        for method in verification_methods:
            try:
                if method():
                    return True
            except Exception as e:
                logger.debug(f"验证方法 {method.__name__} 失败: {e}")
                continue
        
        logger.error("❌ 首页加载失败，所有验证方法都失败")
        self._debug_current_page()
        return False
    
    def _verify_by_bottom_nav(self):
        """通过底部导航栏验证首页"""
        try:
            home_tab = self._find(AppiumBy.XPATH, '//android.widget.TextView[@text="首页"]', timeout=AppConfig.SHORT_WAIT)
            if home_tab and home_tab.is_displayed():
                logger.info(f"✅ 通过底部导航栏验证首页: {home_tab.text}")
                return True
        except Exception:
            return False
        return False
    
    def _verify_by_search_box(self):
        """通过搜索框验证首页"""
        try:
            search_box = self._find(AppiumBy.ID, "com.bs.feifubao:id/et_search", timeout=AppConfig.SHORT_WAIT)
            if search_box and search_box.is_displayed():
                logger.info("✅ 通过搜索框验证首页")
                return True
        except Exception:
            return False
        return False
    
    def _verify_by_golden_zone(self):
        """通过金刚区验证首页"""
        try:
            golden_items = self._find_all_now(
                AppiumBy.XPATH, "//android.widget.LinearLayout[@resource-id='com.bs.feifubao:id/ll_menu']"
            )
            if golden_items and len(golden_items) > 0:
                logger.info(f"✅ 通过金刚区验证首页: 找到 {len(golden_items)} 个项目")
                return True
        except Exception:
            return False
        return False
    
    def _verify_by_ad_banner(self):
        """通过广告横幅验证首页"""
        try:
            ad_banner = self._find(AppiumBy.XPATH, '//*[contains(@text, "放心好味道")]', timeout=AppConfig.SHORT_WAIT)
            if ad_banner and ad_banner.is_displayed():
                logger.info("✅ 通过广告横幅验证首页")
                return True
        except Exception:
            return False
        return False
    
    def handle_new_user_popup_smart(self):
        """智能处理新用户弹窗 - 只在出现时处理"""
        logger.info("智能检查新用户弹窗...")

        popup_detected = False
        for indicator in self.POPUP_INDICATORS:
            if indicator["type"] == "text":
                elements = self._find_all_now(
                    AppiumBy.XPATH, f'//*[contains(@text, "{indicator["value"]}")]'
                )
            else:  # type == "id"
                elements = self._find_all_now(AppiumBy.ID, indicator["value"])

            for el in elements:
                try:
                    if el and el.is_displayed():
                        logger.info(f"✅ 检测到弹窗特征: {indicator['value']}")
                        popup_detected = True
                        break
                except Exception:
                    continue
            if popup_detected:
                break
        
        if not popup_detected:
            logger.info("✅ 未检测到新用户弹窗")
            return True
        
        # 如果检测到弹窗，尝试关闭
        logger.info("尝试关闭新用户弹窗...")
        
        # 尝试多种关闭方式
        close_methods = [
            self._click_popup_close_button,
            self._tap_outside_popup_area,
            self._press_back_key_for_popup,
        ]
        
        for method in close_methods:
            try:
                if method():
                    logger.info(f"✅ 弹窗关闭方法成功: {method.__name__}")
                    
                    # 验证弹窗是否真的关闭了
                    time.sleep(1)
                    if not self._check_popup_still_exists():
                        logger.info("✅ 弹窗已成功关闭")
                        return True
            except Exception as e:
                logger.debug(f"弹窗关闭方法失败: {method.__name__} - {e}")
        
        logger.warning("⚠️ 弹窗可能未完全关闭，尝试继续测试")
        return False
    
    def _click_popup_close_button(self):
        """点击弹窗关闭按钮"""
        close_buttons = [
            (AppiumBy.ID, "com.bs.feifubao:id/iv_close"),
            (AppiumBy.XPATH, '//android.widget.ImageView[@content-desc="关闭"]'),
            (AppiumBy.XPATH, '//android.widget.ImageButton'),
            (AppiumBy.XPATH, '//android.widget.Button[@text="关闭"]'),
            (AppiumBy.XPATH, '//android.widget.Button[@text="取消"]'),
        ]
        
        for by, value in close_buttons:
            try:
                element = self._find(by, value, timeout=AppConfig.SHORT_WAIT)
                if element and element.is_displayed() and element.is_enabled():
                    element.click()
                    logger.info(f"✅ 点击关闭按钮: {value}")
                    time.sleep(1)
                    return True
            except Exception:
                continue
        return False
    
    def _tap_outside_popup_area(self):
        """点击弹窗外部区域"""
        try:
            window_size = self.driver.get_window_size()
            # 点击屏幕底部中间位置，通常不在弹窗内
            tap_x = window_size['width'] * 0.5
            tap_y = window_size['height'] * 0.8

            if not self._tap_xy(tap_x, tap_y):
                return False
            logger.info("✅ 点击弹窗外部区域")
            time.sleep(1)
            return True
        except Exception as e:
            logger.debug(f"点击外部区域失败: {e}")
            return False
    
    def _press_back_key_for_popup(self):
        """按返回键关闭弹窗"""
        self.driver.back()
        logger.info("✅ 按返回键尝试关闭弹窗")
        time.sleep(1)
        return True
    
    def _check_popup_still_exists(self):
        """检查弹窗是否仍然存在"""
        for text in self.POPUP_TEXTS:
            elements = self._find_all_now(AppiumBy.XPATH, f'//*[contains(@text, "{text}")]')
            for el in elements:
                try:
                    if el and el.is_displayed():
                        logger.warning(f"⚠️ 弹窗仍然存在，检测到文本: {text}")
                        return True
                except Exception:
                    continue
        
        return False
    
    def get_golden_zone_items(self):
        """获取金刚区项目 """
        logger.info("获取金刚区项目...")
        
        try:
            # 确认的金刚区容器定位器
            items = self.driver.find_elements(
                AppiumBy.XPATH, "//android.widget.LinearLayout[@resource-id='com.bs.feifubao:id/ll_menu']"
            )
            
            if items:
                logger.info(f"✅ 找到 {len(items)} 个金刚区项目")
                
                # 显示每个项目的文字
                for i, item in enumerate(items[:8]):  # 最多显示8个
                    try:
                        text_element = item.find_element(
                            AppiumBy.ID, "com.bs.feifubao:id/tv_title"
                        )
                        logger.info(f"  [{i+1}] {text_element.text}")
                    except Exception:
                        logger.info(f"  [{i+1}] 无法获取文字")
            
            return items
        except Exception as e:
            logger.error(f"❌ 获取金刚区项目失败: {e}")
            return []
    
    def click_golden_zone_item(self, index, items):
        """点击指定索引的金刚区项目"""
        if index >= len(items):
            logger.error(f"索引 {index} 超出范围，共有 {len(items)} 个项目")
            return False, f"项目{index+1}"
        
        try:
            item = items[index]
            
            # 获取项目名称
            try:
                text_element = item.find_element(
                    AppiumBy.ID, "com.bs.feifubao:id/tv_title"
                )
                item_name = text_element.text
            except Exception:
                item_name = f"项目{index+1}"
            
            logger.info(f"🖱️ 点击: {item_name}")
            item.click()
            time.sleep(3)  # 等待页面跳转
            
            return True, item_name
        except Exception as e:
            logger.error(f"❌ 点击第 {index+1} 个项目失败: {e}")
            return False, f"项目{index+1}"
    
    def navigate_back_by_item_type(self, item_name):
        """
        根据金刚区项目类型返回首页
        外卖和商城：点击底部首页tab返回
        其他金刚区（H5页面）：通过返回键返回
        """
        logger.info(f"根据项目类型返回首页: {item_name}")
        
        # 定义需要点击底部首页tab返回的项目
        bottom_tab_items = ["外卖", "商城", "美食外卖", "正品商城"]
        
        # 检查是否是需要点击底部tab返回的项目
        if item_name in bottom_tab_items:
            logger.info(f"{item_name} 需要点击底部首页tab返回")
            return self._click_bottom_home_tab()
        else:
            logger.info(f"{item_name} 是H5页面，使用返回键返回")
            return self._press_back_key()
    
    def _click_bottom_home_tab(self):
        """点击底部导航栏的首页tab"""
        try:
            logger.info("点击底部导航栏'首页'tab...")
            
            # 等待底部首页tab可点击
            if not self._click_when_clickable(AppiumBy.XPATH, '//android.widget.TextView[@text="首页"]', timeout=10):
                raise TimeoutException("Home tab not clickable")
            logger.info("✅ 已点击底部首页tab")
            
            # 等待首页加载完成
            return self.wait_for_homepage()
            
        except Exception as e:
            logger.error(f"❌ 点击底部首页tab失败: {e}")
            return False
    
    def _press_back_key(self):
        """按下返回键"""
        try:
            logger.info("按下返回键...")
            self.driver.back()
            time.sleep(2)
            
            # 检查是否返回首页
            if self._verify_by_bottom_nav() or self._verify_by_search_box():
                logger.info("✅ 已通过返回键回到首页")
                return True
            else:
                logger.warning("返回键后可能未回到首页，尝试再次返回")
                self.driver.back()
                time.sleep(2)
                return self.wait_for_homepage()
                
        except Exception as e:
            logger.error(f"❌ 返回键操作失败: {e}")
            return False
    
    def test_search_function_optimized(self):
        """优化的搜索功能测试"""
        logger.info("\n测试搜索功能（优化版）...")
        
        # 先处理可能的弹窗
        self.handle_new_user_popup_smart()
        
        for element_info in self.SEARCH_ELEMENTS:
            try:
                element = self._find(element_info["by"], element_info["value"], timeout=AppConfig.SHORT_WAIT)
                if element and element.is_displayed() and element.is_enabled():
                    logger.info(f"✅ 找到搜索入口: {element_info['desc']}")
                    element.click()

                    # 以“搜索页关键元素”判断是否进入（更稳定）
                    search_page_indicators = [
                        (AppiumBy.ID, "com.bs.feifubao:id/et_search"),
                        (AppiumBy.XPATH, '//*[contains(@text, "搜索")]'),
                        (AppiumBy.XPATH, '//android.widget.TextView[@text="取消"]'),
                    ]
                    entered = False
                    for by, value in search_page_indicators:
                        el = self._find(by, value, timeout=6)
                        if el:
                            entered = True
                            break

                    if entered:
                        logger.info("✅ 成功进入搜索页面（通过元素验证）")
                    else:
                        logger.warning("⚠️ 未能确认进入搜索页（继续尝试返回）")

                    self.navigate_back_to_home_safe()
                    return True
            except Exception as e:
                logger.debug(f"搜索入口点击失败: {element_info.get('desc')} - {e}")
                continue
        
        logger.warning("❌ 搜索功能测试失败")
        return False
    
    def test_customer_service_button_optimized(self):
        """优化的客服按钮测试"""
        logger.info("\n测试客服按钮功能（优化版）...")
        
        # 先处理可能的弹窗
        self.handle_new_user_popup_smart()
        
        # 检查登录状态
        is_logged_in = self.check_login_status_smart()
        logger.info(f"用户登录状态: {'已登录' if is_logged_in else '未登录'}")
        
        for selector in self.CUSTOMER_SERVICE_SELECTORS:
            try:
                element = self._find(selector["by"], selector["value"], timeout=AppConfig.SHORT_WAIT)
                if element and element.is_displayed() and element.is_enabled():
                    logger.info(f"✅ 找到客服按钮: {selector['desc']}")
                    element.click()
                    logger.info("✅ 已点击客服按钮")

                    if not is_logged_in:
                        confirmed = any(self._find(by, value, timeout=8) for by, value in self.LOGIN_INDICATORS)
                        if confirmed:
                            logger.info("✅ 未登录状态：已唤起登录页面（通过元素验证）")
                        else:
                            logger.warning("⚠️ 未登录状态：未能确认登录页（继续返回）")
                        self.driver.back()
                        time.sleep(1)
                        return True
                    else:
                        confirmed = any(self._find(by, value, timeout=8) for by, value in self.CHAT_INDICATORS)
                        if confirmed:
                            logger.info("✅ 已登录状态：疑似进入客服/聊天页面（通过元素验证）")
                        else:
                            logger.warning("⚠️ 已登录状态：未能确认客服页（继续返回）")
                        self.navigate_back_to_home_safe()
                        return True
            except Exception as e:
                logger.debug(f"客服入口处理失败: {selector.get('desc')} - {e}")
                continue
        
        logger.warning("❌ 未找到客服按钮")
        return False
    
    def check_login_status_smart(self):
        """智能检查用户登录状态"""
        logger.info("检查用户登录状态...")
        
        # 先处理可能的弹窗
        self.handle_new_user_popup_smart()
        
        # 方法1: 检查汇率模块
        try:
            exchange_element = self.driver.find_element(
                AppiumBy.ID, "com.bs.feifubao:id/ll_exchange_rate"
            )
            if exchange_element and exchange_element.is_displayed():
                logger.info("✅ 找到汇率模块，用户已登录")
                return True
        except Exception:
            pass
        
        # 方法2: 检查登录按钮
        try:
            login_button = self.driver.find_element(
                AppiumBy.XPATH, '//android.widget.TextView[@text="立即登录"]'
            )
            if login_button and login_button.is_displayed():
                logger.info("❌ 找到登录按钮，用户未登录")
                return False
        except Exception:
            pass
        
        # 方法3: 检查用户信息
        try:
            user_elements = self.driver.find_elements(
                AppiumBy.XPATH, '//android.widget.TextView[contains(@text, "用户")]'
            )
            for element in user_elements:
                if element.is_displayed():
                    logger.info(f"✅ 找到用户相关元素: {element.text}，可能已登录")
                    return True
        except Exception:
            pass
        
        logger.warning("⚠️ 无法确定登录状态")
        return False
    
    def test_golden_zone_enhanced(self):
        """增强版金刚区测试 - 根据项目类型执行不同的业务/返回方式"""
        logger.info("开始增强版金刚区测试（含业务分发）...")
        
        # 获取金刚区项目
        items = self.get_golden_zone_items()
        
        if not items:
            logger.error("❌ 未找到金刚区项目")
            return []
        
        # 确定测试数量
        test_count = min(len(items), 8)  # 最多测试8个
        logger.info(f"计划测试 {test_count} 个项目")
        
        successful_clicks = []
        
        for i in range(test_count):
            logger.info(f"\n" + "="*50)
            logger.info(f"测试第 {i+1}/{test_count} 个项目")
            logger.info("="*50)
            
            # 点击项目
            success, item_name = self.click_golden_zone_item(i, items)

            if not success:
                logger.warning(f"⚠️ 第 {i+1} 个项目点击失败")
                try:
                    self.driver.back()
                    time.sleep(2)
                except Exception:
                    pass
                continue

            successful_clicks.append((i, item_name))

            # 等待页面稳定
            logger.info(f"点击 '{item_name}' 后等待页面稳定...")
            time.sleep(2)

            # 判断是否有绑定业务流程
            biz_type = self.GOLDEN_BUSINESS_MAP.get(item_name)
            if biz_type == "takeout":
                logger.info(f"🎯 入口 '{item_name}' 绑定业务：外卖流程")
                TakeoutPage(self.driver).run_main_flow()
            elif biz_type == "shipping":
                logger.info(f"🎯 入口 '{item_name}' 绑定业务：海运流程")
                ShippingPage(self.driver).run_main_flow()
            else:
                logger.info(f"入口 '{item_name}' 暂未绑定具体业务流程，仅做可点击性验证")

            # 每次业务/跳转后，都尽量回到首页，确保下一个入口可测
            if not self.ensure_homepage():
                logger.error(f"❌ 点击 '{item_name}' 后无法返回首页，停止测试")
                break

            # 返回后重新获取金刚区项目
            logger.info("返回首页后重新获取金刚区项目...")
            items = self.get_golden_zone_items()
            if not items:
                logger.error("❌ 返回后找不到金刚区项目，停止测试")
                break

            # 等待首页完全加载
            time.sleep(2)
            logger.info(f"✅ 第 {i+1} 个项目测试完成")
        
        logger.info(f"\n金刚区测试完成，成功点击 {len(successful_clicks)}/{test_count} 个项目")
        return successful_clicks

    # ============ 业务级用例示例：外卖-旺旺超市wwcs ============
    def test_takeout_wangwang_flow(self):
        """
        外卖业务完整流程：
        进入外卖频道 -> 旺旺超市wwcs -> 凑配送金额 -> 选时间 -> 下单 -> 订单详情操作
        为避免影响现有金刚区测试，这里单独提供一个入口，你可以在 main 中按需调用。
        """
        logger.info("\n开始外卖『旺旺超市wwcs』完整业务流程测试...")

        # 确保在首页，并处理可能的弹窗
        self.handle_new_user_popup_smart()
        if not self.ensure_homepage():
            logger.error("❌ 无法回到首页，外卖流程停止")
            return False

        # 通过金刚区/底部入口进入外卖频道
        # 这里假设金刚区或底部导航存在『外卖』入口，你可根据实际 UI 调整定位方式
        entered = False
        try:
            # 1）优先尝试金刚区里的『外卖』
            items = self.get_golden_zone_items()
            for item in items:
                try:
                    title_el = item.find_element(AppiumBy.ID, "com.bs.feifubao:id/tv_title")
                    if title_el.text in ("外卖", "美食外卖"):
                        logger.info(f"点击金刚区入口: {title_el.text}")
                        item.click()
                        entered = True
                        break
                except Exception:
                    continue

            # 2）兜底：从底部 Tab 进入外卖（如果有的话）
            if not entered:
                entered = self._click_when_clickable(
                    AppiumBy.XPATH,
                    '//android.widget.TextView[@text="外卖" or @text="美食外卖"]',
                    timeout=10,
                )
        except Exception:
            entered = False

        if not entered:
            logger.error("❌ 未能从首页进入外卖频道，请检查外卖入口定位")
            return False

        time.sleep(2)
        page = TakeoutPage(self.driver)
        result = page.run_main_flow()

        # 主流程结束后，尝试回到首页，方便后续其它用例继续执行
        try:
            self.ensure_homepage()
        except Exception:
            pass

        return result
    
    def navigate_back_to_home_safe(self, max_attempts=3):
        """安全返回首页"""
        logger.info("尝试返回首页...")
        
        for attempt in range(max_attempts):
            # 尝试点击底部首页标签
            try:
                home_tab = self.driver.find_element(
                    AppiumBy.XPATH, '//android.widget.TextView[@text="首页"]'
                )
                if home_tab and home_tab.is_displayed() and home_tab.is_enabled():
                    home_tab.click()
                    logger.info("✅ 点击首页标签返回")
                    time.sleep(2)
                    return True
            except Exception:
                pass
            
            # 按返回键
            self.driver.back()
            logger.info(f"第{attempt+1}次按返回键")
            time.sleep(2)
        
        logger.error("❌ 无法返回首页")
        return False
    
    def _debug_current_page(self):
        """调试当前页面"""
        try:
            logger.info("\n" + "="*60)
            logger.info("调试页面信息")
            logger.info("="*60)
            
            # 获取当前Activity
            current_activity = self.driver.current_activity
            logger.info(f"当前Activity: {current_activity}")
            
            # 获取页面中所有TextView
            try:
                textviews = self.driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.TextView")
                visible_texts = []
                for tv in textviews[:20]:  # 只取前20个
                    try:
                        text = tv.text
                        if text and len(text.strip()) > 0:
                            visible_texts.append(text)
                    except Exception:
                        pass
                
                if visible_texts:
                    logger.info(f"可见文本: {', '.join(visible_texts[:10])}")
            except Exception:
                pass
                
        except Exception as e:
            logger.error(f"调试失败: {e}")
    
    def save_screenshot(self, name):
        """保存截图"""
        try:
            os.makedirs(AppConfig.ARTIFACTS_DIR, exist_ok=True)
            filename = os.path.join(
                AppConfig.ARTIFACTS_DIR,
                f"screenshot_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
            )
            self.driver.save_screenshot(filename)
            logger.info(f"截图已保存: {filename}")
        except Exception as e:
            logger.warning(f"⚠️ 截图保存失败: {e}")
    
    def cleanup(self):
        """清理资源"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("✅ 驱动已关闭")
            except Exception as e:
                logger.warning(f"⚠️ 关闭驱动时出错: {e}")
    
    def run_comprehensive_test(self):
        """运行综合测试套件"""
        logger.info("\n" + "="*60)
        logger.info("筷子生活App综合测试")
        logger.info("="*60)
        
        test_results = {}
        
        try:
            # instrumentation 偶发崩溃时，自动重建 driver 重试一次
            for attempt in range(2):
                if not self.setup_driver():
                    return test_results
                try:
                    # 0. 智能处理新用户弹窗
                    logger.info("\n0. 智能处理新用户弹窗")
                    self.handle_new_user_popup_smart()

                    # 1. 等待首页加载
                    if not self.ensure_homepage():
                        logger.error("❌ 首页加载失败，测试终止")
                        self.save_screenshot("homepage_failed")
                        return test_results

                    # 2. 测试搜索功能
                    logger.info("\n1. 测试搜索功能")
                    search_result = self.test_search_function_optimized()
                    test_results["search"] = search_result

                    # 3. 测试客服按钮
                    logger.info("\n2. 测试客服按钮")
                    cs_result = self.test_customer_service_button_optimized()
                    test_results["customer_service"] = cs_result

                    # 4. 增强版金刚区测试
                    logger.info("\n3. 增强版金刚区测试")
                    golden_results = self.test_golden_zone_enhanced()
                    test_results["golden_zone"] = golden_results

                    # 输出测试总结
                    logger.info("\n" + "="*60)
                    logger.info("测试结果总结")
                    logger.info("="*60)

                    logger.info(f"搜索功能测试: {'✅ 通过' if search_result else '❌ 失败'}")
                    logger.info(f"客服按钮测试: {'✅ 通过' if cs_result else '❌ 失败'}")
                    logger.info(f"金刚区测试: 成功点击 {len(golden_results)} 个项目")

                    if golden_results:
                        logger.info("成功点击的项目:")
                        for idx, name in golden_results:
                            logger.info(f"  [{idx+1}] {name}")

                    return test_results
                except WebDriverException as e:
                    if attempt == 0 and self._is_uia2_instrumentation_down(e):
                        logger.warning("⚠️ UiAutomator2 instrumentation 异常，重建 driver 重试一次…")
                        try:
                            self.cleanup()
                        except Exception:
                            pass
                        continue
                    raise
            
        except Exception as e:
            logger.error(f"测试执行异常: {e}")
            import traceback
            traceback.print_exc()
            return test_results
        finally:
            self.cleanup()

# ================ 主函数 ================
def main():
    """主测试流程"""
    tester = ChopsticksTester()
    results = tester.run_comprehensive_test()
    return results

if __name__ == "__main__":
    main()
