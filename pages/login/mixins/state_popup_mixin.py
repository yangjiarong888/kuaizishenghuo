"""登录页状态探测与通用/严格弹窗处理。"""
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

logger = setup_logger("pages.login")

class LoginStatePopupMixin:
    # ============ 登录页状态 ============
    def is_login_page_loaded(self) -> bool:
        """
        是否在登录相关页面：聚合页、手机号验证页，或账号密码登录页。
        「忘记密码」仅出现在账号密码页，聚合页无此入口。
        """
        if self._is_account_password_input_screen():
            return True
        if self._is_phone_verification_entry_screen():
            return True
        for by, value in self.LOGIN_HUB_LOCS:
            el = self._find(by, value, timeout=2)
            if el and self._is_displayed(el):
                return True
        fp = self._find(AppiumBy.XPATH, '//*[@content-desc="忘记密码"]', timeout=1)
        if fp and self._is_displayed(fp):
            return True
        fp2 = self._find(AppiumBy.XPATH, '//*[contains(@text,"忘记密码")]', timeout=1)
        if fp2 and self._is_displayed(fp2):
            return True
        return False

    def _looks_like_login_hub_fast(self) -> bool:
        """快速探测（find_elements，无长显式等待）。"""
        for by, xp in self.LOGIN_HUB_LOCS:
            try:
                for el in self._find_all_now(by, xp)[:8]:
                    if self._is_displayed(el):
                        return True
            except Exception:
                continue
        return False

    def _looks_like_home_login_bar_fast(self) -> bool:
        """未登录首页底部「立即登录」条。"""
        xps = [
            '//android.widget.TextView[@text="立即登录"]',
            '//*[contains(@resource-id,"btn_unlogin_tips")]',
        ]
        for xp in xps:
            try:
                for el in self._find_all_now(AppiumBy.XPATH, xp)[:6]:
                    if self._is_displayed(el):
                        return True
            except Exception:
                continue
        return False

    def ensure_on_app_home_for_login(self, max_steps: int = 10) -> bool:
        """
        冷启动常先弹活动/广告页，导致找不到「立即登录」。
        关闭/跳过/返回，直到出现首页特征或已落在登录聚合页。

        Returns:
            True  — 已在登录聚合页，调用方应跳过点击「立即登录」
            False — 已尽力回到首页/可继续点「立即登录」
        """
        for _ in range(max_steps):
            if self._looks_like_login_hub_fast():
                logger.info("当前已在登录聚合页，无需再从首页点「立即登录」")
                return True
            if self._looks_like_home_login_bar_fast():
                return False
            try:
                for el in self._find_all_now(
                    AppiumBy.XPATH, '//android.widget.TextView[@text="首页"]'
                )[:5]:
                    if self._is_displayed(el):
                        return False
            except Exception:
                pass

            self.handle_popup()
            skip_locs: Tuple[Locator, ...] = (
                (AppiumBy.XPATH, '//*[contains(@text,"跳过") or contains(@text,"暂不")]'),
                (AppiumBy.XPATH, '//*[contains(@text,"不感兴趣")]'),
                (AppiumBy.XPATH, '//*[contains(@text,"关闭") or @content-desc="关闭"]'),
                (AppiumBy.XPATH, '//*[contains(@text,"知道了") or contains(@text,"我知道了")]'),
            )
            if self._click_any(skip_locs, timeout=2):
                time.sleep(0.7)
                continue
            try:
                self.driver.back()
            except Exception:
                pass
            time.sleep(0.55)

        logger.warning(
            "[WARN] 多次尝试后仍可能未回到首页；若仍找不到「立即登录」，请手动关活动页后重跑"
        )
        return False

    def handle_popup_phone_sms_inner_safe(self) -> bool:
        """
        手机号验证码流程专用：禁止 handle_popup 里「任意 CheckBox」与泛化「同意」Button，
        否则会点到登录页中部协议勾选/分段附近控件，表现为刚进验证码页又变成密码登录。
        仅处理典型浮层文案（与 handle_popup_strict_after_login 同思路）。
        """
        locs: Tuple[Locator, ...] = (
            (AppiumBy.ACCESSIBILITY_ID, "同意并注册/登录"),
            (AppiumBy.XPATH, '//android.view.View[@content-desc="同意并注册/登录"]'),
            (AppiumBy.XPATH, '//*[contains(@text,"同意并注册") or contains(@text,"同意并登录")]'),
            (AppiumBy.XPATH, '//*[@content-desc="同意并注册/登录"]'),
            (AppiumBy.XPATH, '//*[contains(@text,"同意并继续")]'),
            (AppiumBy.XPATH, '//*[contains(@text,"我知道了")]'),
            (AppiumBy.XPATH, '//*[@content-desc="我知道了"]'),
            (AppiumBy.XPATH, '//*[@content-desc="关闭"]'),
            (AppiumBy.XPATH, '//*[contains(@resource-id,"iv_close") and @clickable="true"]'),
            (AppiumBy.XPATH, '//*[@content-desc="确定"]'),
            (AppiumBy.XPATH, '//*[contains(@text,"允许") and string-length(@text)<8]'),
        )
        return self._click_any(locs, timeout=2)

    def handle_popup(self) -> bool:
        """处理协议/新手/权限等通用弹窗，尽力点击‘同意/确认/关闭’。"""
        if self._phone_sms_login_active:
            return self.handle_popup_phone_sms_inner_safe()
        # 协议授权类弹窗（同意并继续）
        agreement_buttons = [
            (AppiumBy.ACCESSIBILITY_ID, "同意并注册/登录"),
            (AppiumBy.XPATH, '//android.view.View[@content-desc="同意并注册/登录"]'),
            (AppiumBy.XPATH, '//*[contains(@text,"同意并注册") or contains(@text,"同意并登录")]'),
            (AppiumBy.XPATH, '//*[@content-desc="同意并注册/登录"]'),
            (AppiumBy.XPATH, '//*[contains(@text,"同意并继续")]'),
            (AppiumBy.XPATH, '//*[contains(@text,"同意") and (self::android.widget.Button or self::android.widget.TextView)]'),
            (AppiumBy.XPATH, '//*[contains(@text,"确认") or @content-desc="确定"]'),
            (AppiumBy.XPATH, '//*[contains(@text,"关闭") or @content-desc="关闭"]'),
            (AppiumBy.XPATH, '//*[contains(@text,"我知道了")]'),
            (AppiumBy.XPATH, '//*[contains(@text,"取消")]'),
        ]

        # 有些弹窗还有勾选框
        checkbox_locs = [
            (AppiumBy.XPATH, '//*[@checked="false" or @checked="true"]'),
            (AppiumBy.XPATH, '//*[contains(@resource-id,"check") or contains(@resource-id,"agree") or contains(@text,"同意")]/following::*[1]'),
        ]

        for cb in checkbox_locs:
            try:
                els = self._find_all_now(cb[0], cb[1])
                for el in els[:3]:
                    if el.is_displayed() and el.is_enabled():
                        # 点击可能切换为同意
                        el.click()
                        break
            except Exception:
                continue

        clicked = self._click_any(agreement_buttons, timeout=3)
        return clicked

    def handle_popup_strict_after_login(self) -> bool:
        """
        登录后若已回到 MainActivity/首页，禁止使用 handle_popup 里过宽的「同意」与任意勾选框规则：
        那些会匹配到首页运营卡、半屏活动，误点进 WebViewComprehensive / 头条 H5。
        此处仅匹配明确的协议/系统式按钮（与 handle_popup 子集一致，无泛化 agree）。
        """
        locs: Tuple[Locator, ...] = (
            (AppiumBy.ACCESSIBILITY_ID, "同意并注册/登录"),
            (AppiumBy.XPATH, '//android.view.View[@content-desc="同意并注册/登录"]'),
            (AppiumBy.XPATH, '//*[contains(@text,"同意并注册") or contains(@text,"同意并登录")]'),
            (AppiumBy.XPATH, '//*[@content-desc="同意并注册/登录"]'),
            (AppiumBy.XPATH, '//*[contains(@text,"同意并继续")]'),
            (AppiumBy.XPATH, '//*[contains(@text,"我知道了")]'),
            (AppiumBy.XPATH, '//*[@content-desc="我知道了"]'),
            (AppiumBy.XPATH, '//*[@content-desc="关闭"]'),
            (AppiumBy.XPATH, '//*[contains(@resource-id,"iv_close") and @clickable="true"]'),
        )
        return self._click_any(locs, timeout=2)

