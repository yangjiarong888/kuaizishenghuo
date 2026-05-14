"""账号密码登录与忘记密码流程。"""
from __future__ import annotations

import time
from typing import Optional, Tuple

from appium.webdriver.common.appiumby import AppiumBy

from commons.logger import setup_logger

from pages.login.data import Locator
from pages.login.env import _post_login_subpage_escape_enabled

logger = setup_logger("pages.login")


class LoginPasswordMixin:
    # ============ 4) 账号密码登录 ============
    def login_by_account_password_from_home(
        self, account: Optional[str] = None, password: Optional[str] = None
    ) -> bool:
        """首页点「立即登录」后走账号密码登录，成功则校验并完成「我的 -> 我的余额」链路。"""
        self._phone_sms_login_active = False
        if not self.open_login_from_home():
            return False
        return self.login_by_account_password(account=account, password=password)

    def _click_account_password_entry(self) -> bool:
        """
        「账号密码登录」在手机号验证页底部，Inspector 多为 Button + content-desc。
        需 presence + _click_element（避免仅用 element_to_be_clickable）。
        """
        locs: Tuple[Locator, ...] = (
            (AppiumBy.ACCESSIBILITY_ID, "账号密码登录"),
            (AppiumBy.XPATH, '//android.widget.Button[@content-desc="账号密码登录"]'),
            (AppiumBy.XPATH, '//*[@content-desc="账号密码登录"]'),
            (AppiumBy.XPATH, '//*[contains(@text,"账号密码登录")]'),
            (AppiumBy.XPATH, '//*[contains(@text,"账号密码") and contains(@text,"登录")]'),
            (AppiumBy.XPATH, '//android.widget.TextView[contains(@text,"账号密码登录")]'),
            (AppiumBy.XPATH, '//*[contains(@content-desc,"账号密码")]'),
        )
        for by, xp in locs:
            el = self._find(by, xp, timeout=5)
            if el and self._is_displayed(el) and self._click_element(el):
                return True
        for sel in (
            'new UiSelector().description("账号密码登录")',
            'new UiSelector().descriptionContains("账号密码登录")',
            'new UiSelector().textContains("账号密码登录")',
        ):
            try:
                el = self.driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, sel)
                if el and self._click_element(el):
                    return True
            except Exception:
                continue
        return False

    def _ensure_on_account_password_login_screen(self) -> bool:
        """
        进入账号密码登录表单页（可见「请输入密码」等）。
        与 `login_by_account_password`、`forget_password` 共用。
        「忘记密码」入口仅在此页，不在登录聚合页。
        """
        self.handle_popup()
        if self._is_account_password_input_screen():
            return True
        if not self._is_phone_verification_entry_screen() and not self.is_login_page_loaded():
            self.wait_for_login_landing_page(timeout=20)
        self.handle_popup()
        if self._is_account_password_input_screen():
            return True

        if not self._navigate_login_hub_to_phone_entry_screen():
            logger.error(
                "[ERR] 无法进入手机号登录页；账号密码/忘记密码入口需先点「手机号码登录/注册」"
            )
            return False
        time.sleep(0.9)
        self.handle_popup()

        if self._is_account_password_input_screen():
            return True

        if not self._click_account_password_entry():
            time.sleep(1.2)
            self.handle_popup()
            if not self._click_account_password_entry():
                logger.error(
                    "[ERR] 未找到「账号密码登录」入口（应在手机号页底部，content-desc 常为「账号密码登录」）"
                )
                return False
        time.sleep(0.9)
        self.handle_popup()

        deadline = time.time() + 14
        while time.time() < deadline:
            if self._is_account_password_input_screen():
                return True
            time.sleep(0.35)
        logger.error("[ERR] 未进入账号密码登录页（无「请输入密码」区域）")
        return False

    def _click_forgot_password_entry(self) -> bool:
        """忘记密码：仅在账号密码登录页，Inspector 多为 Button + content-desc。"""
        locs: Tuple[Locator, ...] = (
            (AppiumBy.ACCESSIBILITY_ID, "忘记密码"),
            (AppiumBy.XPATH, '//android.widget.Button[@content-desc="忘记密码"]'),
            (AppiumBy.XPATH, '//*[@content-desc="忘记密码"]'),
            (AppiumBy.XPATH, '//*[contains(@text,"忘记密码")]'),
        )
        for by, xp in locs:
            el = self._find(by, xp, timeout=5)
            if el and self._is_displayed(el) and self._click_element(el):
                return True
        try:
            el = self.driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                'new UiSelector().description("忘记密码")',
            )
            if el and self._click_element(el):
                return True
        except Exception:
            pass
        return False

    def login_by_account_password(self, account: Optional[str] = None, password: Optional[str] = None) -> bool:
        self._phone_sms_login_active = False
        account = self.data.resolved_phone(account)
        password = self.data.resolved_password(password)
        if not account or not password:
            logger.error(
                "[ERR] 缺少账号或密码：请传 --phone/--password，或设置 "
                "LOGIN_DEFAULT_PHONE / LOGIN_DEFAULT_PASSWORD"
            )
            return False

        if not self._ensure_on_account_password_login_screen():
            return False
        self.handle_popup()
        time.sleep(0.6)

        account_typed, pwd_typed = self._fill_password_login_form(account, password)
        if not account_typed or not pwd_typed:
            logger.error(
                "[ERR] 输入账号或密码失败（请用 Inspector 确认密码页 EditText 的 resource-id / content-desc）"
            )
            return False

        self._try_agree_user_protocol_password_page()
        self.handle_popup()
        time.sleep(0.55)
        if not self._click_password_page_login_button():
            logger.error(
                "[ERR] 未点到「登录」按钮（已尝试收起键盘、多轮滑动与显式 ID/XPath/UiSelector 定位）"
            )
            return False

        # 先处理协议底部弹层（未勾选时点「登录」会先出「同意并注册/登录」）
        self._dismiss_password_login_protocol_sheet_if_present()
        time.sleep(0.5)
        self._arm_post_login_click_gesture_suppress()
        stab = self._env_float_positive("POST_LOGIN_UI_STABILIZE_SEC")
        if stab > 0:
            logger.info("POST_LOGIN_UI_STABILIZE_SEC：登录提交后额外静候 %.1f 秒再进入后续流程", stab)
            time.sleep(stab)
        if _post_login_subpage_escape_enabled():
            self._post_login_prescape_subpages()
            logger.info(
                "子页预处理后，再统一等待 %.1f 秒并进入登录成功断言…",
                self.POST_LOGIN_VERIFY_WAIT_SEC,
            )
        else:
            self.handle_popup()
            logger.info(
                "登录提交后等待 %.1f 秒并进入断言（未启用 POST_LOGIN_SUBPAGE_ESCAPE 时不做汇率/活动通用预处理；"
                "等待期内若被拉进 WebViewH5News 会轮询并立即退回首页；彻底不要该跳转需 App 侧关闭）…",
                self.POST_LOGIN_VERIFY_WAIT_SEC,
            )
        self._post_login_idle_wait_suppressing_headline()
        self.handle_popup_strict_after_login()
        ok = self._verify_logged_in()
        if ok:
            logger.info(
                "登录成功：已通过「我的 -> 我的余额」链路校验"
            )
        else:
            logger.error(
                "登录成功断言未通过：请确认账号密码正确、协议已勾选，或「我的/我的余额」控件是否与脚本一致"
            )
        return ok

    def _probe_logged_in_within(self, max_sec: float) -> bool:
        """
        短窗口内轮询是否已登录（如验证码填完即自动登录）。
        仅用轻量「我的->余额」探测，不做完整 assert_home 以免拖慢。
        """
        deadline = time.time() + max(0.5, float(max_sec))
        while time.time() < deadline:
            self.handle_popup_strict_after_login()
            if _post_login_subpage_escape_enabled():
                self._leave_post_login_subpage_for_home_assert()
            if self._post_login_my_balance_smoke():
                return True
            time.sleep(0.65)
        return False

    def _verify_logged_in(self) -> bool:
        """登录成功后验证：完成「我的 -> 我的余额（账户余额）」链路。"""
        logger.info("开始登录成功断言「我的→我的余额」，含固定等待与轮询重试")
        deadline = time.time() + 55
        while time.time() < deadline:
            self.handle_popup_strict_after_login()
            if _post_login_subpage_escape_enabled():
                self._leave_post_login_subpage_for_home_assert()
            if self._post_login_my_balance_smoke():
                logger.info("断言通过：已完成「我的 -> 我的余额」链路")
                return True
            time.sleep(1.1)
        return self.assert_home_logged_in_features(timeout=18)

    # ============ 5) 忘记密码：验证码校验 -> 修改密码 -> 完成 ============
    def forget_password(self) -> bool:
        """
        忘记密码流程：
        0) 入口仅在「账号密码登录」页（与「验证码登录」并列），须先进入该页
        1) 点击忘记密码
        2) 获取验证码（短信/语音按 UI 自动处理）
        3) 跳转验证码校验页，填验证码
        4) 跳转密码修改页，输入新密码并二次确认
        5) 点击完成，校验“密码修改成功”
        """
        phone = self.data.resolved_phone()
        new_password = self.data.resolved_new_password()
        if not phone or not new_password:
            logger.error(
                "[ERR] 忘记密码流程缺少手机号或新密码：请设置 "
                "LOGIN_DEFAULT_PHONE / LOGIN_DEFAULT_NEW_PASSWORD，或补充 LoginData"
            )
            return False

        if not self._ensure_on_account_password_login_screen():
            logger.error("[ERR] 无法到达账号密码登录页，找不到「忘记密码」入口")
            return False

        if not self._click_forgot_password_entry():
            time.sleep(1.0)
            self.handle_popup()
            if not self._click_forgot_password_entry():
                logger.error("[ERR] 未找到「忘记密码」入口（应在账号密码登录页底部）")
                return False

        self.handle_popup()
        time.sleep(2)

        # 输入手机号（有些页面会复用当前手机号，有些需要输入）
        phone_inputs = [
            (AppiumBy.ID, "com.bs.feifubao:id/et_phone"),
            (AppiumBy.XPATH, '//*[@class="android.widget.EditText" and contains(@resource-id,"phone")]'),
            (AppiumBy.XPATH, '//android.widget.EditText'),
        ]
        typed = any(self._type(by, value, phone, timeout=10) for by, value in phone_inputs)
        if not typed:
            logger.warning("[WARN] 可能手机号已填写，无需输入")

        # 获取验证码（可能为 View + content-desc）
        get_code_locs: Tuple[Locator, ...] = (
            (AppiumBy.ACCESSIBILITY_ID, "获取短信验证码"),
            (AppiumBy.XPATH, '//*[@content-desc="获取短信验证码"]'),
            (AppiumBy.XPATH, '//*[contains(@text,"获取验证码") or contains(@text,"获取短信验证码") or contains(@text,"获取短信")]'),
        )
        got = False
        for by, xp in get_code_locs:
            el = self._find(by, xp, timeout=5)
            if el and self._is_displayed(el) and self._click_element(el):
                got = True
                break
        if not got and not self._click_any([get_code_locs[2]], timeout=6):
            logger.error("[ERR] 未找到获取验证码按钮")
            return False

        # 等待验证码输入页
        code_input = self._find(AppiumBy.XPATH, '//*[contains(@text,"请输入验证码")]/following::android.widget.EditText[1]', timeout=20)
        if not code_input:
            code_input = self._find(AppiumBy.CLASS_NAME, "android.widget.EditText", timeout=10)
        if not code_input:
            logger.error("[ERR] 未进入验证码输入页")
            return False

        code = self._require_code()
        try:
            code_input.clear()
            code_input.send_keys(code)
        except Exception:
            # 若输入框清空失败，重新找一次
            self._type(AppiumBy.CLASS_NAME, "android.widget.EditText", code, timeout=5)

        # 点击校验
        verify_locs = [
            (AppiumBy.XPATH, '//*[contains(@text,"下一步") or contains(@text,"验证") or contains(@text,"完成") or contains(@text,"提交")]'),
            (AppiumBy.ID, "com.bs.feifubao:id/btn_verify"),
        ]
        if not self._click_any(verify_locs, timeout=10):
            logger.error("[ERR] 未找到验证码校验按钮")
            return False

        time.sleep(3)

        # 密码修改页：输入两次新密码
        new_pwd_inputs = [
            (AppiumBy.ID, "com.bs.feifubao:id/et_new_password"),
            (AppiumBy.XPATH, '(//android.widget.EditText)[1]'),
        ]
        confirm_pwd_inputs = [
            (AppiumBy.ID, "com.bs.feifubao:id/et_confirm_password"),
            (AppiumBy.XPATH, '(//android.widget.EditText)[2]'),
        ]

        # 简化：找到前两个 EditText 依次填充
        all_edittexts = self._find_all_now(AppiumBy.CLASS_NAME, "android.widget.EditText")
        if len(all_edittexts) >= 2:
            try:
                all_edittexts[0].clear()
                all_edittexts[0].send_keys(new_password)
                all_edittexts[1].clear()
                all_edittexts[1].send_keys(new_password)
            except Exception:
                pass
        else:
            self._type(new_pwd_inputs[0][0], new_pwd_inputs[0][1], new_password, timeout=10)
            self._type(confirm_pwd_inputs[0][0], confirm_pwd_inputs[0][1], new_password, timeout=10)

        # 点击完成
        done_locs = [
            (AppiumBy.XPATH, '//*[contains(@text,"完成") or contains(@text,"确认") or contains(@text,"保存")]'),
            (AppiumBy.ID, "com.bs.feifubao:id/btn_done"),
        ]
        self._click_any(done_locs, timeout=10)

        time.sleep(2)

        # 校验“密码修改成功”
        success = self._find(AppiumBy.XPATH, '//*[contains(@text,"密码修改成功") or contains(@text,"修改成功")]', timeout=10)
        if success:
            return True

        logger.warning(
            "[WARN] 未检测到「密码修改成功」类提示；请核对文案或补充 XPath。流程未确认完成，返回失败。"
        )
        return False
