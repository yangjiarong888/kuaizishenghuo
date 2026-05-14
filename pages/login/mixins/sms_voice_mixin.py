"""手机短信验证码登录与客服语音验证码兜底。"""
from __future__ import annotations

import os
import re
import time
from typing import Iterable, Optional, Tuple

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from appium.webdriver.common.appiumby import AppiumBy

from commons.logger import setup_logger

from pages.login.data import Locator
from pages.login.env import _post_login_subpage_escape_enabled

logger = setup_logger("pages.login")

class LoginSmsVoiceMixin:
    # ============ 2) 手机号码登录/注册（默认验证码登录） ============
    def login_by_phone_sms(self, phone: Optional[str] = None) -> bool:
        phone = self.data.resolved_phone(phone)
        if not phone:
            logger.error(
                "[ERR] 缺少短信登录手机号：请传 --phone 或设置 LOGIN_DEFAULT_PHONE"
            )
            return False

        self._phone_sms_login_active = True
        if not self._navigate_login_hub_to_phone_entry_screen():
            self._phone_sms_login_active = False
            return False

        self.handle_popup()
        time.sleep(1.0)
        self.handle_popup()
        # 产品/动画可能先闪验证码再落密码 Tab；先尝试切回验证码侧再动协议，避免误触
        if self._phone_sms_should_attempt_switch_to_captcha_tab():
            self._switch_to_sms_captcha_login_tab()
            time.sleep(0.5)
            self.handle_popup()
        self._stabilize_sms_captcha_login_panel(14.0)
        self.handle_popup()
        self._recover_phone_login_if_no_edittext("手机号验证码流程·稳定阶段后")
        # 短信登录：仅当已识别为密码 Tab 时才切验证码侧，避免误点把默认验证码页切到密码
        if not self._page_source_indicates_sms_captcha_login_panel() and not self._get_sms_verification_send_control_visible():
            if self._phone_sms_should_attempt_switch_to_captcha_tab():
                if not self._ensure_sms_captcha_login_tab():
                    logger.warning(
                        "[WARN] 短信登录：密码 Tab 下未见发码语义，已尝试切回验证码侧（输号后将再试）"
                    )
        time.sleep(0.45)
        self.handle_popup()

        logger.info("手机号验证码流程：开始输入手机号（此前仅确认页面/发码区语义；尚未点击「获取短信验证码」）")
        # 输入手机号（Flutter 常为 hint/content-desc 在兄弟 View，text 为空）
        phone_inputs = [
            (AppiumBy.ID, "com.bs.feifubao:id/et_phone"),
            (AppiumBy.ID, "com.ba.feifubao:id/et_phone"),
            (
                AppiumBy.XPATH,
                '//*[@content-desc="请输入手机号"]/following::android.widget.EditText[1]',
            ),
            (
                AppiumBy.XPATH,
                '//*[contains(@content-desc,"请输入手机号")]/following::android.widget.EditText[1]',
            ),
            (AppiumBy.XPATH, '//*[contains(@resource-id,"phone") and (@class="android.widget.EditText")]'),
            (AppiumBy.XPATH, '//*[contains(@text,"请输入手机号")]/following::android.widget.EditText[1]'),
        ]

        typed = any(self._type(loc[0], loc[1], phone, timeout=10) for loc in phone_inputs)
        if not typed:
            # 兜底：把输入框当第一个 EditText
            el = self._find(AppiumBy.CLASS_NAME, "android.widget.EditText", timeout=6)
            if el:
                el.clear()
                el.send_keys(phone)
                typed = True
        if not typed:
            logger.error("[ERR] 未能输入手机号")
            self._phone_sms_login_active = False
            return False

        try:
            self.driver.hide_keyboard()
        except Exception:
            pass
        time.sleep(0.55)
        self.handle_popup()
        if not self._page_source_indicates_sms_captcha_login_panel() and not self._get_sms_verification_send_control_visible():
            if self._phone_sms_should_attempt_switch_to_captcha_tab():
                self._ensure_sms_captcha_login_tab()
                time.sleep(0.45)
                self.handle_popup()
                if not self._page_source_indicates_sms_captcha_login_panel() and not self._get_sms_verification_send_control_visible():
                    self._ensure_sms_captcha_login_tab()
                    time.sleep(0.45)
                    self.handle_popup()

        # 验证码页底部协议：先尽量勾选；未勾选时点「获取验证码」会先出「同意并注册/登录」层
        self._try_agree_user_protocol_password_page(footer_only=True)
        time.sleep(0.35)
        self.handle_popup()

        if not self._click_send_sms_code_button(total_wait_sec=32.0):
            logger.error("[ERR] 未找到或未点到「获取短信验证码」入口（请 Inspector 看该按钮 text/desc/id）")
            self._phone_sms_login_active = False
            return False

        # 未预勾选时：高亮「获取验证码」仍会先弹协议，点同意后才进短信校验页
        self._dismiss_password_login_protocol_sheet_if_present(total_wait_sec=8.0)
        time.sleep(0.45)
        self.handle_popup()
        if self._dismiss_password_login_protocol_sheet_if_present(total_wait_sec=2.0):
            time.sleep(0.45)
            self.handle_popup()

        # 跳转到验证码输入页（Flutter 标题多在兄弟节点的 content-desc，text 常为空）
        code_input = self._find(
            AppiumBy.XPATH,
            '//*[@content-desc="请输入验证码"]/following::android.widget.EditText[1]',
            timeout=8,
        )
        if not code_input:
            code_input = self._find(
                AppiumBy.XPATH,
                '//*[contains(@content-desc,"请输入验证码")]/following::android.widget.EditText[1]',
                timeout=8,
            )
        if not code_input:
            code_input = self._find(
                AppiumBy.XPATH,
                '//*[contains(@text,"验证码") or contains(@text,"请输入验证码")]/following::android.widget.EditText[1]',
                timeout=12,
            )
        time.sleep(1.2)
        if not code_input:
            code_input = self._find(
                AppiumBy.XPATH,
                '//android.widget.ScrollView//android.widget.EditText',
                timeout=5,
            )
        if not code_input:
            code_input = self._find(AppiumBy.CLASS_NAME, "android.widget.EditText", timeout=5)
        if not code_input:
            self._dismiss_password_login_protocol_sheet_if_present(total_wait_sec=5.0)
            time.sleep(0.5)
            code_input = self._find(
                AppiumBy.XPATH,
                '//*[@content-desc="请输入验证码"]/following::android.widget.EditText[1]',
                timeout=8,
            )
        if not code_input:
            code_input = self._find(
                AppiumBy.XPATH,
                '//*[contains(@text,"验证码") or contains(@text,"请输入验证码")]/following::android.widget.EditText[1]',
                timeout=8,
            )
        if not code_input:
            code_input = self._find(AppiumBy.CLASS_NAME, "android.widget.EditText", timeout=5)
        if not code_input:
            logger.error("[ERR] 未进入验证码输入页（找不到验证码输入框）")
            self._phone_sms_login_active = False
            return False

        self.handle_popup()

        # 优先 LoginData.verification_code；否则从页面猜；最后在终端 input() 手动输入
        code = self._require_code()
        try:
            code_input.click()
            time.sleep(0.2)
            code_input.clear()
            code_input.send_keys(code)
        except Exception:
            if not self._type_into_element(code_input, code):
                self._type(AppiumBy.CLASS_NAME, "android.widget.EditText", code, timeout=5)

        try:
            self.driver.hide_keyboard()
        except Exception:
            pass
        time.sleep(0.35)
        self.handle_popup()
        logger.info(
            "验证码已填入：多数包在验证码正确后**自动登录**，页上可无单独「登录」按钮；"
            "先静候并短轮询登录态，未成功再尝试点提交类控件"
        )
        time.sleep(2.2)
        self.handle_popup()

        submit_clicked = False
        sms_asserted_in_probe = self._probe_logged_in_within(10.0)
        if sms_asserted_in_probe:
            logger.info(
                "验证码流程：探测阶段已跑完「我的->我的余额」校验（等同登录成功断言）"
            )
        else:
            submit_locs: Tuple[Locator, ...] = (
                (AppiumBy.ID, "com.bs.feifubao:id/btn_login"),
                (AppiumBy.ID, "com.ba.feifubao:id/btn_login"),
                (AppiumBy.XPATH, '//*[contains(@resource-id,"btn_login")]'),
                (AppiumBy.ACCESSIBILITY_ID, "登录"),
                (AppiumBy.XPATH, '//android.view.View[@content-desc="登录"]'),
                (AppiumBy.XPATH, '//*[@content-desc="登录" and not(contains(@content-desc,"验证码"))]'),
                (AppiumBy.XPATH, '//*[@clickable="true" and @content-desc="登录"]'),
                (
                    AppiumBy.XPATH,
                    '//*[(self::android.widget.Button or self::android.widget.TextView) and contains(@text,"登录") '
                    'and not(contains(@text,"验证码登录")) and not(contains(@text,"账号密码"))]',
                ),
                (
                    AppiumBy.XPATH,
                    '//*[contains(@text,"下一步") or contains(@text,"提交") or contains(@text,"完成")]',
                ),
                (
                    AppiumBy.XPATH,
                    '//*[contains(@text,"验证") and string-length(@text)<8 '
                    'and not(contains(@text,"验证码登录")) and not(contains(@text,"请输入"))]',
                ),
            )
            submit_clicked = self._click_any(submit_locs, timeout=10)
            if not submit_clicked:
                for sel in (
                    'new UiSelector().description("登录")',
                    'new UiSelector().descriptionContains("登录").clickable(true)',
                    'new UiSelector().text("登录")',
                ):
                    try:
                        el = self.driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, sel)
                        if el and self._is_displayed(el) and self._click_element(el):
                            submit_clicked = True
                            break
                    except Exception:
                        pass
            if not submit_clicked:
                logger.warning(
                    "[WARN] 仍未点到「登录/下一步」；再等待 %.1f 秒后进入完整登录断言",
                    3.5,
                )
                time.sleep(3.5)
                self.handle_popup()

        self._dismiss_password_login_protocol_sheet_if_present()
        time.sleep(0.5)
        self._arm_post_login_click_gesture_suppress()
        stab = self._env_float_positive("POST_LOGIN_UI_STABILIZE_SEC")
        if stab > 0:
            logger.info("POST_LOGIN_UI_STABILIZE_SEC：验证码登录提交后额外静候 %.1f 秒", stab)
            time.sleep(stab)
        if sms_asserted_in_probe:
            logger.info(
                "验证码登录成功：自动登录（探测阶段已断言「我的->我的余额」），不再重复长等待与二次断言"
            )
            self._phone_sms_login_active = False
            return True

        if _post_login_subpage_escape_enabled():
            self._post_login_prescape_subpages()
            logger.info(
                "子页预处理后，再统一等待 %.1f 秒并进入登录成功断言…",
                self.POST_LOGIN_VERIFY_WAIT_SEC,
            )
        else:
            self.handle_popup()
            logger.info(
                "验证码登录提交后等待 %.1f 秒并进入断言…",
                self.POST_LOGIN_VERIFY_WAIT_SEC,
            )
        self._post_login_idle_wait_suppressing_headline()
        self.handle_popup_strict_after_login()
        ok = self._verify_logged_in()
        if ok:
            if not submit_clicked:
                logger.info("验证码登录成功：自动登录流程")
            else:
                logger.info("验证码登录成功：已通过「我的 -> 我的余额」链路校验")
        else:
            logger.error(
                "[ERR] 验证码登录未通过「我的->我的余额」断言；"
                "若 App 已显示成功，请核对首页/「我的」Tab 文案是否与脚本一致"
            )
        self._phone_sms_login_active = False
        return ok

    # ============ 3) 客服按钮：语音验证码回退 ============
    def customer_service_voice_captcha_flow(self) -> bool:
        """从验证码页点击客服，发送消息，点击收不到验证码 -> 接收语音验证码 -> 确定 -> 拨打电话。"""

        # 点击客服入口
        cs_entry_locs = [
            (AppiumBy.XPATH, '//*[contains(@text,"客服") or contains(@content-desc,"客服") or contains(@resource-id,"customer") or contains(@resource-id,"service")]'),
            (AppiumBy.XPATH, '//*[contains(@text,"联系客服")]'),
        ]
        if not self._click_any(cs_entry_locs, timeout=10):
            logger.error("[ERR] 未找到客服入口")
            return False

        # 等待聊天/消息页
        time.sleep(2)

        # 自动发送文案（输入框 + 发送按钮）
        input_locs = [
            (AppiumBy.ID, "com.bs.feifubao:id/et_chat_input"),
            (AppiumBy.XPATH, '//*[contains(@resource-id,"input") and @class="android.widget.EditText"]'),
            (AppiumBy.XPATH, '//*[@content-desc="输入消息" or contains(@text,"输入")]/following::android.widget.EditText[1]'),
        ]
        input_el = None
        for by, value in input_locs:
            input_el = self._find(by, value, timeout=6)
            if input_el:
                break
        if not input_el:
            logger.warning("[WARN] 未找到聊天输入框，可能无需发送或已默认文本")
        else:
            try:
                input_el.clear()
                input_el.send_keys(self.data.customer_service_text)
            except Exception:
                pass

        send_locs = [
            (AppiumBy.XPATH, '//*[contains(@text,"发送") or @content-desc="发送"]'),
            (AppiumBy.ID, "com.bs.feifubao:id/btn_send"),
        ]
        self._click_any(send_locs, timeout=8)
        time.sleep(2)

        # 收不到验证码 -> 接收语音验证码
        not_receive_locs = [
            (AppiumBy.XPATH, '//*[contains(@text,"收不到验证码") or contains(@text,"收不到") or contains(@text,"无法收到")]'),
        ]
        if not self._click_any(not_receive_locs, timeout=10):
            logger.warning("[WARN] 未找到‘收不到验证码’，继续尝试语音入口")

        voice_locs = [
            (AppiumBy.XPATH, '//*[contains(@text,"接收语音验证码") or contains(@text,"语音验证码") or contains(@text,"语音")]'),
        ]
        if not self._click_any(voice_locs, timeout=10):
            logger.error("[ERR] 未找到‘接收语音验证码’入口")
            return False

        # 确定拨打电话
        ok_locs = [
            (AppiumBy.XPATH, '//*[contains(@text,"确定") or contains(@text,"去拨打") or contains(@text,"确认")]'),
            (AppiumBy.ID, "android:id/button1"),
        ]
        self._click_any(ok_locs, timeout=10)

        # 通话通常会弹到拨号/通话界面，这里不做强校验，直接认为流程到达
        time.sleep(3)
        return True
