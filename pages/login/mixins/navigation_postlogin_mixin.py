"""首页→登录页导航、登录后头条/H5 逃逸与「我的→余额」断言。"""
from __future__ import annotations

import os
import re
import time
import subprocess
from typing import Callable, Iterable, Optional, Tuple

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.common.actions import interaction

from appium.webdriver.common.appiumby import AppiumBy

from commons.logger import setup_logger

from pages.login.data import Locator
from pages.login.env import _post_login_headline_h5_escape_enabled, _post_login_subpage_escape_enabled

logger = setup_logger("pages.login")

class LoginNavigationPostLoginMixin:
    # ============ 首页 -> 登录页 ============
    def _swipe_vertical(self, start_y_ratio: float, end_y_ratio: float, duration_ms: int = 500) -> None:
        try:
            win = self.driver.get_window_size()
            w, h = win["width"], win["height"]
            x = int(w * 0.5)
            y1 = int(h * start_y_ratio)
            y2 = int(h * end_y_ratio)
            self.driver.swipe(x, y1, x, y2, duration_ms)
        except Exception:
            pass

    def dismiss_unlogin_swipe_hint_overlay(self) -> bool:
        """
        未登录底部条外层 RelativeLayout：`cl_unlogin_tips` 上的「上滑查看更多推荐」
        会叠在「立即登录」(btn_unlogin_tips) 上面，导致点不到。
        按引导在首页内容上滑 2～3 次，通常可收起提示或消除遮挡。
        """
        hint_xpaths = [
            '//*[contains(@text,"上滑查看更多推荐")]',
            '//*[contains(@text,"上滑查看更多")]',
            '//*[contains(@text,"上滑查看")]',
            '//*[contains(@resource-id,"cl_unlogin_tips")]',
        ]
        found = False
        for xp in hint_xpaths:
            if self._find(AppiumBy.XPATH, xp, timeout=1):
                found = True
                break
        if not found:
            return False

        logger.info("检测到「上滑查看更多」浮层，先上滑首页内容区以消除对「立即登录」的遮挡")
        # 在中间偏下上滑，避开最底导航栏
        for _ in range(3):
            self._swipe_vertical(0.70, 0.32, 550)
            time.sleep(0.55)
        return True

    def _click_login_now_uiautomator(self) -> bool:
        """UiAutomator2 按文本/resourceId 查找，适配部分非标准层级。"""
        selectors = [
            # 包名可能是 com.bs.feifubao / com.ba.feifubao 等，用 resourceIdMatches
            'new UiSelector().resourceIdMatches(".*feifubao:id/btn_unlogin_tips")',
            'new UiSelector().resourceId("com.bs.feifubao:id/btn_unlogin_tips")',
            'new UiSelector().resourceId("com.ba.feifubao:id/btn_unlogin_tips")',
            'new UiSelector().text("立即登录")',
            'new UiSelector().textContains("立即登录")',
            'new UiSelector().descriptionContains("立即登录")',
        ]
        for sel in selectors:
            try:
                el = self.driver.find_element(
                    AppiumBy.ANDROID_UIAUTOMATOR, sel
                )
                if el and self._click_element(el):
                    return True
            except Exception:
                continue
        return False

    def _click_best_visible_immediate_login(self) -> bool:
        """
        收集所有文案含「立即登录」的节点，优先点击位置最靠下、且可见的一个
        （底部浮条可能被「上滑查看更多」叠层影响，多候选更稳）。
        """
        xpath = (
            '//*[contains(@text,"立即登录") or contains(@content-desc,"立即登录")]'
        )
        try:
            els = self.driver.find_elements(AppiumBy.XPATH, xpath)
        except Exception:
            els = []
        candidates = []
        for el in els:
            try:
                if not el.is_displayed():
                    continue
                loc = el.location
                size = el.size
                y = int(loc["y"] + size.get("height", 0) / 2)
                candidates.append((y, el))
            except Exception:
                continue
        if not candidates:
            return False
        # 取最靠下的（通常在底部浮条）
        candidates.sort(key=lambda t: t[0], reverse=True)
        for _, el in candidates[:3]:
            if self._click_element(el):
                return True
        return False

    def _click_immediate_login_like_home_py(self, timeout: int = 18) -> bool:
        """
        与 Home.py 中 check_login_status_smart 一致：
        find_element(XPATH, '//android.widget.TextView[@text="立即登录"]') + is_displayed。
        注意：该节点在 Inspector 里常为 clickable=false，不能用 element_to_be_clickable。
        """
        xpath = '//android.widget.TextView[@text="立即登录"]'
        try:
            el = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((AppiumBy.XPATH, xpath))
            )
            if el and self._is_displayed(el):
                return self._click_element(el)
        except Exception:
            pass
        # 兜底：与 Home.py LOGIN_INDICATORS 类似的宽松匹配
        try:
            el2 = WebDriverWait(self.driver, min(4, timeout)).until(
                EC.presence_of_element_located(
                    (AppiumBy.XPATH, '//*[contains(@text,"立即登录")]')
                )
            )
            if el2 and self._is_displayed(el2):
                return self._click_element(el2)
        except Exception:
            pass
        return False

    def wait_for_login_landing_page(self, timeout: int = 25) -> bool:
        """
        点击「立即登录」后：等待出现登录聚合页特征（含协议弹窗关闭后再识别）。
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            self.handle_popup()
            for by, xp in self.LOGIN_HUB_LOCS:
                el = self._find(by, xp, timeout=1)
                if el and self._is_displayed(el):
                    logger.info("已进入登录相关页面（检测到登录页特征）")
                    return True
            time.sleep(0.35)
        return False

    def _tap_login_now_coordinate_fallback(self) -> bool:
        """
        最后兜底：在底部浮条「立即登录」紫色按钮附近多点几次，并校验是否进入登录页。
        避免误点后仍返回 True（你日志里即属此类：点了坐标但未进登录页）。
        """
        try:
            win = self.driver.get_window_size()
            w, h = win["width"], win["height"]
        except Exception:
            return False

        # 多组相对坐标（竖屏底部偏右区域）
        ratios = [
            (0.82, 0.90),
            (0.88, 0.88),
            (0.76, 0.89),
            (0.85, 0.86),
        ]
        for rx, ry in ratios:
            x, y = int(w * rx), int(h * ry)
            try:
                self.driver.execute_script("mobile: clickGesture", {"x": x, "y": y})
            except Exception:
                try:
                    if hasattr(self.driver, "tap"):
                        self.driver.tap([(x, y)])
                except Exception:
                    continue
            time.sleep(1.2)
            self.handle_popup()
            if self.wait_for_login_landing_page(timeout=8):
                logger.info(f"坐标兜底点击后已进入登录页 (ratio=({rx},{ry}))")
                return True

        logger.warning("[WARN] 坐标兜底多次点击后仍未进入登录页")
        return False

    def open_login_from_home(self) -> bool:
        """
        未登录首页底部浮条：点击「立即登录」
        Resource-ID: *feifubao:id/btn_unlogin_tips（Inspector 上 TextView 可能 clickable=false）
        注意：cl_unlogin_tips 上的「上滑查看更多推荐」会遮挡，需先 dismiss_unlogin_swipe_hint_overlay。
        """
        self.handle_popup()
        time.sleep(0.6)

        # 活动/广告页会挡住首页「立即登录」；先回到首页再点 Tab
        if self.ensure_on_app_home_for_login():
            return True

        # 确保在底部「首页」Tab（有时启动落在其它 Tab）
        self._click_any(
            [(AppiumBy.XPATH, '//android.widget.TextView[@text="首页"]')],
            timeout=5,
        )
        time.sleep(0.8)

        # 先处理挡住「立即登录」的上滑引导浮层
        self.dismiss_unlogin_swipe_hint_overlay()
        time.sleep(0.6)

        def try_all_strategies() -> bool:
            # 0) 与 Home.py 相同写法（短超时 + 多轮重试，避免单次 15s+8s 堆成半小时）
            if self._click_immediate_login_like_home_py(timeout=6):
                return True

            # 1) resource-id（兼容 com.bs / com.ba 等包名）
            el = self._find(
                AppiumBy.XPATH,
                '//*[contains(@resource-id,"btn_unlogin_tips")]',
                timeout=4,
            )
            if el and self._click_element(el):
                return True

            el_bs = self._find(AppiumBy.ID, "com.bs.feifubao:id/btn_unlogin_tips", timeout=3)
            if el_bs and self._click_element(el_bs):
                return True

            el2 = self._find(
                AppiumBy.XPATH,
                '//android.widget.TextView[@resource-id="com.bs.feifubao:id/btn_unlogin_tips"]',
                timeout=3,
            )
            if el2 and self._click_element(el2):
                return True

            el_ba = self._find(
                AppiumBy.XPATH,
                '//android.widget.TextView[@resource-id="com.ba.feifubao:id/btn_unlogin_tips"]',
                timeout=3,
            )
            if el_ba and self._click_element(el_ba):
                return True

            # 2) Button 精确文案（presence + 点击，避免 _click_any 的 clickable 等待）
            btn = self._find(
                AppiumBy.XPATH, '//android.widget.Button[@text="立即登录"]', timeout=5
            )
            if btn and self._click_element(btn):
                return True

            # 3) 多候选 + 最靠下可见
            if self._click_best_visible_immediate_login():
                return True

            # 4) UiAutomator
            if self._click_login_now_uiautomator():
                return True

            return False

        # 第一轮：当前屏
        if try_all_strategies():
            time.sleep(1.5)
            self.handle_popup()
            if self.wait_for_login_landing_page(timeout=22):
                logger.info("已从首页点击「立即登录」")
                return True
            logger.warning("[WARN] 已点击立即登录但未检测到登录页，继续重试")

        # 第二轮：再次尝试消掉上滑引导层 + 轻微滑动
        self.dismiss_unlogin_swipe_hint_overlay()
        self._swipe_vertical(0.55, 0.72, 400)
        time.sleep(0.8)
        if try_all_strategies():
            time.sleep(1.5)
            self.handle_popup()
            if self.wait_for_login_landing_page(timeout=22):
                logger.info("已从首页点击「立即登录」（滑动后）")
                return True

        self._swipe_vertical(0.75, 0.55, 400)
        time.sleep(0.8)
        if try_all_strategies():
            time.sleep(1.5)
            self.handle_popup()
            if self.wait_for_login_landing_page(timeout=22):
                logger.info("已从首页点击「立即登录」（第二次滑动后）")
                return True

        # 第三轮：坐标兜底（仍找不到节点时），必须校验进入登录页
        if self._tap_login_now_coordinate_fallback():
            return True

        logger.error(
            "[ERR] 首页未找到「立即登录」入口；请确认：1) 未登录且浮条存在 "
            "2) 命令为 --method password（勿拼成 passwordghuo）3) 用 Appium Inspector 导出该按钮的 resource-id"
        )
        return False

    # 底部 Tab：优先 BottomNavigationItemView；勿用 tv_title（多为顶栏标题，非底栏）
    _MY_TAB_LOCS: Tuple[Locator, ...] = (
        (
            AppiumBy.XPATH,
            '//*[contains(@class,"BottomNavigationItemView")]'
            '[.//android.widget.TextView[@text="我的"]]',
        ),
        (
            AppiumBy.XPATH,
            '//*[contains(@class,"BottomNavigationItemView")][.//*[@text="我的"]]',
        ),
        (AppiumBy.XPATH, '//android.widget.TextView[@text="我的"]'),
        (AppiumBy.XPATH, '//*[@content-desc="我的"]'),
    )
    _HOME_TAB_LOCS: Tuple[Locator, ...] = (
        (AppiumBy.XPATH, '//android.widget.TextView[@text="首页"]'),
        (AppiumBy.XPATH, '//*[@content-desc="首页"]'),
    )
    # 仅匹配「账户」列表里的「我的余额」（Inspector：rv_menu_account + tv_menu + 文案）
    _MY_BALANCE_ENTRY_LOCS: Tuple[Locator, ...] = (
        (
            AppiumBy.XPATH,
            '//*[@resource-id="com.bs.feifubao:id/rv_menu_account"]'
            '//android.widget.TextView[@resource-id="com.bs.feifubao:id/tv_menu" and @text="我的余额"]',
        ),
        (
            AppiumBy.XPATH,
            '//*[@resource-id="com.ba.feifubao:id/rv_menu_account"]'
            '//android.widget.TextView[@resource-id="com.ba.feifubao:id/tv_menu" and @text="我的余额"]',
        ),
        (
            AppiumBy.XPATH,
            '//android.widget.TextView[@resource-id="com.bs.feifubao:id/tv_menu" and @text="我的余额"]',
        ),
        (
            AppiumBy.XPATH,
            '//android.widget.TextView[@resource-id="com.ba.feifubao:id/tv_menu" and @text="我的余额"]',
        ),
    )

    def _swipe_fraction(self, y_from: float, y_to: float, duration_ms: int = 600) -> None:
        try:
            win = self.driver.get_window_size()
            w, h = win["width"], win["height"]
            x = int(w * 0.5)
            self.driver.swipe(x, int(h * y_from), x, int(h * y_to), duration_ms)
        except Exception:
            pass

    _POST_LOGIN_BACK_LOCS: Tuple[Locator, ...] = (
        (AppiumBy.ID, "com.bs.feifubao:id/iv_back_white"),
        (AppiumBy.ID, "com.ba.feifubao:id/iv_back_white"),
        (AppiumBy.ID, "com.bs.feifubao:id/iv_back"),
        (AppiumBy.ID, "com.ba.feifubao:id/iv_back"),
        (AppiumBy.XPATH, '//*[contains(@resource-id,"iv_back_white")]'),
        (AppiumBy.XPATH, '//*[contains(@resource-id,"iv_back")]'),
        (AppiumBy.XPATH, '//*[@content-desc="返回"]'),
        # Material Toolbar / 系统文案（FestivalsDetail 等页常无 iv_back_*，诊断里 iv_back_white=False）
        (
            AppiumBy.XPATH,
            '//android.widget.ImageButton['
            'contains(@content-desc,"返回") or contains(@content-desc,"Navigate up") '
            'or contains(@content-desc,"转到上一层级") or contains(@content-desc,"向上导航") '
            'or contains(@content-desc,"Back")'
            ']',
        ),
        (
            AppiumBy.XPATH,
            '//*[contains(@resource-id,"toolbar")][.//android.widget.ImageButton][1]'
            '//android.widget.ImageButton[1]',
        ),
    )

    def _current_activity_lower(self) -> str:
        try:
            return (getattr(self.driver, "current_activity", "") or "").lower()
        except Exception:
            return ""

    @staticmethod
    def _page_source_looks_like_native_home_hub(src: str) -> bool:
        """首页底部 tab 常见特征（用于与登录页/H5 粗分）。"""
        return ("首页" in src and "我的" in src) and ("RecyclerView" in src or "ViewPager" in src)

    @staticmethod
    def _page_source_looks_like_login_flow(src: str) -> bool:
        """避免把登录聚合页等误判为「活动 H5」去乱点返回。"""
        return any(
            k in src
            for k in (
                "登录或注册",
                "账号密码登录",
                "微信账号快捷登录",
                "手机号码登录/注册",
            )
        )

    def _post_login_try_back_and_switch_home_tab(self) -> bool:
        """离开登录后的全屏子页：点标题栏返回（含白底返回键）或系统 back，再点底部「首页」Tab。"""
        clicked = False
        for by, xp in self._POST_LOGIN_BACK_LOCS:
            el = self._find(by, xp, timeout=2)
            if el and self._is_displayed(el) and self._click_element(el):
                clicked = True
                break
        if not clicked:
            try:
                self.driver.back()
                clicked = True
            except Exception:
                pass
        time.sleep(1.0)
        self.handle_popup_strict_after_login()
        self._click_any(list(self._HOME_TAB_LOCS), timeout=4)
        time.sleep(0.6)
        return clicked

    def _android_press_back(self) -> None:
        try:
            self.driver.press_keycode(4)
        except Exception:
            try:
                self.driver.back()
            except Exception:
                pass

    def _post_login_aggressive_escape_fullscreen_webview_activity(
        self, max_back_presses: int = 8
    ) -> bool:
        """
        WebViewComprehensiveActivity 等全屏 H5：树里常无 iv_back_*（你日志 iv_back_white=False），
        单次 back 往往只退网页 history。先点可见关闭/返回，再连续系统返回并间歇切「首页」Tab。
        """
        extra_locs: Tuple[Locator, ...] = (
            (AppiumBy.XPATH, '//*[contains(@resource-id,"iv_close")]'),
            (AppiumBy.XPATH, '//*[contains(@resource-id,"btn_close")]'),
            (AppiumBy.XPATH, '//*[contains(@resource-id,"img_back")]'),
            (AppiumBy.XPATH, '//*[contains(@resource-id,"toolbar")]//*[contains(@resource-id,"back")]'),
            (AppiumBy.XPATH, '//*[contains(@content-desc,"关闭") or contains(@content-desc,"返回")]'),
            (AppiumBy.XPATH, '//android.widget.ImageButton[contains(@content-desc,"Navigate")]'),
            # WebViewH5News / 活动页常见：标题栏 fl_title、action_bar 内 ImageView/ImageButton（com.ba / com.bs）
            (AppiumBy.XPATH, '//*[contains(@resource-id,"fl_title")]//android.widget.ImageButton'),
            (AppiumBy.XPATH, '//*[contains(@resource-id,"fl_title")]//android.widget.ImageView[@clickable="true"]'),
            (AppiumBy.XPATH, '//*[contains(@resource-id,"action_bar")]//android.widget.ImageButton'),
        )
        self._post_login_try_back_and_switch_home_tab()
        if self._home_logged_in_quick_check(loc_timeout=2):
            return True
        for by, xp in extra_locs:
            el = self._find(by, xp, timeout=1)
            if el and self._is_displayed(el) and self._click_element(el):
                time.sleep(0.9)
                if self._home_logged_in_quick_check(loc_timeout=2):
                    return True
                break
        for i in range(max_back_presses):
            if self._home_logged_in_quick_check(loc_timeout=1):
                return True
            self._android_press_back()
            time.sleep(0.75)
            if i % 2 == 1:
                self.handle_popup_strict_after_login()
                self._click_any(list(self._HOME_TAB_LOCS), timeout=2)
        self._click_any(list(self._HOME_TAB_LOCS), timeout=5)
        time.sleep(0.6)
        return True

    @staticmethod
    def _activity_is_headline_or_comprehensive_h5_shell(act_l: str) -> bool:
        """WebViewH5NewsActivity / WebViewComprehensiveActivity 等（activity 名小写）。"""
        return "webviewh5news" in act_l or "webviewcomprehensive" in act_l

    def _escape_chopstick_headline_fullscreen_if_needed(self) -> None:
        """
        App 若配置了登录后进 WebViewH5NewsActivity，脚本无法禁止跳转，只能检测到后立即退出，
        以便继续点底部「我的」。与 POST_LOGIN_SUBPAGE_ESCAPE 无关。

        重要：必须先按 **Activity** 判断。H5 控件树/WebView 内文案常含「首页」「我的」，
        若先执行 _home_logged_in_quick_check 会误判已回首页从而 **根本不执行退出**，导致一直卡在 H5 壳。
        """
        if not _post_login_headline_h5_escape_enabled():
            return
        act_l = self._current_activity_lower()
        if not self._activity_is_headline_or_comprehensive_h5_shell(act_l):
            return
        logger.info(
            "检测到头条/全屏 H5 壳 Activity（%s），强制返回首页（壳页内勿信控件树里的「首页」文案）",
            getattr(self.driver, "current_activity", "?"),
        )
        self._post_login_aggressive_escape_fullscreen_webview_activity(max_back_presses=20)
        act_after = self._current_activity_lower()
        if self._activity_is_headline_or_comprehensive_h5_shell(act_after):
            logger.warning(
                "头条/H5 壳仍在（当前 Activity=%s）。可设 POST_LOGIN_HEADLINE_HARD_RELAUNCH=1 并核对 APP_PACKAGE（如 com.ba.feifubao）",
                getattr(self.driver, "current_activity", "?"),
            )
            self._headline_stuck_relaunch_main_if_enabled()

    def _headline_stuck_relaunch_main_if_enabled(self) -> None:
        """
        连续返回仍卡在 H5 壳时，可选冷拉回 MainActivity（会打断当前栈）。
        开启：POST_LOGIN_HEADLINE_HARD_RELAUNCH=1
        包名/入口：APP_PACKAGE、APP_ACTIVITY（与 commons 配置一致，com.ba 包须自行设对）
        """
        v = os.environ.get("POST_LOGIN_HEADLINE_HARD_RELAUNCH", "0").strip().lower()
        if v not in ("1", "true", "yes", "on", "y"):
            return
        pkg = (os.environ.get("APP_PACKAGE") or "").strip()
        if not pkg:
            try:
                pkg = (getattr(self.driver, "current_package", "") or "").strip()
            except Exception:
                pkg = ""
        if not pkg:
            logger.warning("[WARN] HEADLINE_HARD_RELAUNCH：无法取得包名，跳过 start_activity")
            return
        main_act = (os.environ.get("APP_ACTIVITY") or "").strip()
        if not main_act:
            main_act = (
                "com.ba.feifubao.activity.MainActivity"
                if "com.ba.feifubao" in pkg
                else "com.bs.feifubao.activity.MainActivity"
            )
        act_only = main_act.split("/")[-1] if "/" in main_act else main_act
        try:
            logger.info(
                "HEADLINE_HARD_RELAUNCH：terminate_app + start_activity %s/%s",
                pkg,
                act_only,
            )
            try:
                self.driver.terminate_app(pkg)
            except Exception:
                pass
            time.sleep(0.35)
            self.driver.start_activity(pkg, act_only)
            time.sleep(1.2)
        except Exception as e:
            logger.warning("[WARN] HEADLINE_HARD_RELAUNCH 失败: %s", e)

    def _post_login_idle_wait_suppressing_headline(self, minimum_sec: Optional[float] = None) -> None:
        """
        原固定 sleep 期间若 App 弹出 WebViewH5News，会整段停在文章页。
        在等待窗口内轮询并调用 _escape_chopstick_headline_fullscreen_if_needed，尽量在刚跳转时即退出。

        minimum_sec：覆盖默认 POST_LOGIN_VERIFY_WAIT_SEC；QQ/微信「已回首页」静默登录时可缩短，减少日志与肉眼时间差。

        注意：此处**不要**高频调用 handle_popup()。其泛化「同意」/勾选规则会在首页误点运营位，
        反而被当成「脚本检测导致进 H5」；检测本身（page_source/find）不会打开新 Activity。
        """
        t0 = time.time()
        min_sec = (
            float(minimum_sec)
            if minimum_sec is not None
            else float(self.POST_LOGIN_VERIFY_WAIT_SEC)
        )
        min_sec = max(0.35, min_sec)
        while time.time() - t0 < min_sec:
            if _post_login_headline_h5_escape_enabled():
                self._escape_chopstick_headline_fullscreen_if_needed()
            time.sleep(0.45)

    def _leave_post_login_subpage_for_home_assert(self) -> bool:
        """
        登录成功后 App 常串行打开多个「全屏子页」，看不到首页金刚区/头条，需分别识别：

        - 工具页：如「汇率换算」（控件树文案）。
        - 活动页（原生）：独立 Activity，如 FestivalsDetailActivity（树里可无 WebView）。
        - 活动页（H5）：原生标题栏 + WebView 嵌网页（树里有 android.webkit.WebView）。

        每轮断言循环只处理一层；若先汇率再活动，需多轮依次退出。

        默认不执行本段；需要自动从子页/WebView 退回首页时设：POST_LOGIN_SUBPAGE_ESCAPE=on
        """
        if not _post_login_subpage_escape_enabled():
            return False

        if self._home_logged_in_quick_check(loc_timeout=1):
            return False

        try:
            src = self.driver.page_source or ""
        except Exception:
            src = ""
        act_l = self._current_activity_lower()

        # 1) 汇率换算（原逻辑）
        title_sub = self._find(
            AppiumBy.XPATH,
            '//*[contains(@text,"汇率换算") or contains(@content-desc,"汇率换算")]',
            timeout=1,
        )
        stuck_on_rate_tool = bool(
            (title_sub and self._is_displayed(title_sub))
            or ("汇率换算" in src and "充值缴费" not in src)
        )
        if not stuck_on_rate_tool and "汇率换算" in src:
            el_b = self._find(
                AppiumBy.XPATH, '//*[contains(@resource-id,"iv_back")]', timeout=1
            )
            if el_b and self._is_displayed(el_b):
                stuck_on_rate_tool = True

        if stuck_on_rate_tool:
            logger.info(
                "检测到登录后落在子页（如「汇率换算」），点击返回以便回到首页做登录断言"
            )
            return self._post_login_try_back_and_switch_home_tab()

        # 2) 节庆/活动类原生详情页（FestivalsDetailActivity 等：无 WebView，且常无 iv_back_white）
        _festival_act_markers = (
            "festivalsdetail",
            "festivaldetail",
            "promotiondetail",
            "activitydetail",
        )
        if any(m in act_l for m in _festival_act_markers):
            logger.info(
                "检测到登录后落在活动/节庆类子 Activity（%s），尝试返回并切回「首页」Tab",
                getattr(self.driver, "current_activity", "?"),
            )
            self._post_login_try_back_and_switch_home_tab()
            if self._home_logged_in_quick_check(loc_timeout=2):
                return True
            act_after = self._current_activity_lower()
            if any(m in act_after for m in _festival_act_markers) or not self._home_logged_in_quick_check(
                loc_timeout=1
            ):
                logger.info(
                    "节庆/活动页单次返回未回首页（当前 Activity=%s），启用连续系统返回 + 关闭类控件兜底",
                    getattr(self.driver, "current_activity", "?"),
                )
                self._post_login_aggressive_escape_fullscreen_webview_activity(
                    max_back_presses=12
                )
            return True

        # 3) 活动页（H5）：原生容器内嵌 WebView；Activity 名未必含 festival，故用「有 WebView 且不像首页/登录」推断
        webview_nodes = src.count("android.webkit.WebView")
        if (
            webview_nodes > 0
            and not self._page_source_looks_like_native_home_hub(src)
            and not self._page_source_looks_like_login_flow(src)
        ):
            if "webviewcomprehensive" in act_l:
                logger.info(
                    "检测到 WebViewComprehensiveActivity（全屏 H5，共 %s 个 WebView 节点），"
                    "扩展关闭/返回 + 连续系统返回（最多 8 次）并间歇切「首页」",
                    webview_nodes,
                )
                return self._post_login_aggressive_escape_fullscreen_webview_activity()
            logger.info(
                "检测到登录后落在含 WebView 的页面（可能为活动/H5，共 %s 个 WebView 节点），"
                "尝试原生返回键/系统返回并切回「首页」Tab",
                webview_nodes,
            )
            return self._post_login_try_back_and_switch_home_tab()

        return False

    def _post_login_prescape_subpages(
        self, rounds: int = 6, pause_sec: float = 0.5
    ) -> None:
        """
        登录提交后 App 仍可能按配置打开「汇率换算」等活动/工具全屏页；单纯加长 sleep 不会阻止跳转，
        只会推迟断言。在被动等待前多轮：弹窗处理 + 退出子页，尽量在树刚出现「汇率换算」时就 back/切 Tab。
        若已能探测首页特征则提前结束。

        默认跳过本预处理；开启请设：POST_LOGIN_SUBPAGE_ESCAPE=on
        """
        if not _post_login_subpage_escape_enabled():
            self.handle_popup()
            return

        for _ in range(rounds):
            self.handle_popup_strict_after_login()
            self._leave_post_login_subpage_for_home_assert()
            if self._home_logged_in_quick_check(loc_timeout=1):
                return
            time.sleep(pause_sec)

    def _pick_bottom_nav_mine_label(self):
        """
        选取底部导航栏上的「我的」文案节点。Material 底栏里 TextView 常 clickable=false，
        若用 element_to_be_clickable( TextView ) 会一直失败；几何上取屏幕下半区最靠下的「我的」避免顶栏同名。
        """
        try:
            win = self.driver.get_window_size()
            h = max(int(win.get("height", 800)), 400)
        except Exception:
            h = 800
        band_top = int(h * 0.60)
        try:
            els = self.driver.find_elements(AppiumBy.XPATH, '//*[@text="我的"]')
        except Exception:
            els = []
        candidates: list = []
        for e in els:
            if not self._is_displayed(e):
                continue
            try:
                cls = (e.get_attribute("className") or e.get_attribute("class") or "")
            except Exception:
                cls = ""
            if "TextView" not in cls:
                continue
            try:
                loc = e.location
                size = e.size
                cy = int(loc.get("y", 0)) + int(size.get("height", 0)) // 2
            except Exception:
                continue
            if cy >= band_top:
                candidates.append((cy, e))
        if not candidates:
            return None
        candidates.sort(key=lambda t: t[0], reverse=True)
        return candidates[0][1]

    def _home_logged_in_quick_check(self, loc_timeout: int = 2) -> bool:
        """探测首页：底部「首页」与「我的」tab 同时可见。"""
        home_tab = self._find_first(self._HOME_TAB_LOCS, timeout=loc_timeout)
        my_tab = self._pick_bottom_nav_mine_label()
        if not my_tab:
            my_tab = self._find_first(self._MY_TAB_LOCS, timeout=loc_timeout)
        return self._is_displayed(home_tab) and self._is_displayed(my_tab)

    def _probe_feifubao_home_logged_in_after_oauth(self) -> bool:
        """
        点「同意协议」后部分机型不拉起 QQ 前台即静默完成登录；轮询 QQ 前台时若已回主包且底栏可见，视为成功。
        若在 WebView 全屏壳内，限频尝试头条逃逸后再认首页，避免误报「未见 QQ 前台」。
        """
        try:
            cur = (getattr(self.driver, "current_package", "") or "").strip()
        except Exception:
            return False
        if "feifubao" not in cur.lower():
            return False
        if self._home_logged_in_quick_check(loc_timeout=1):
            return True
        try:
            act_l = (getattr(self.driver, "current_activity", "") or "").lower()
        except Exception:
            act_l = ""
        if "webviewcomprehensive" not in act_l and "webviewh5news" not in act_l:
            return False
        now = time.time()
        last = float(getattr(self, "_oauth_probe_escape_ts", 0.0) or 0.0)
        if now - last < 3.0:
            return False
        self._oauth_probe_escape_ts = now
        self._escape_chopstick_headline_fullscreen_if_needed()
        time.sleep(0.35)
        return self._home_logged_in_quick_check(loc_timeout=2)

    def _back_to_home_tab(self) -> None:
        back_locs: Tuple[Locator, ...] = (
            (AppiumBy.ID, "com.bs.feifubao:id/iv_back"),
            (AppiumBy.ID, "com.ba.feifubao:id/iv_back"),
            (AppiumBy.XPATH, '//*[contains(@resource-id,"iv_back")]'),
            (AppiumBy.XPATH, '//*[@content-desc="返回"]'),
        )
        clicked = False
        for by, xp in back_locs:
            el = self._find(by, xp, timeout=2)
            if el and self._is_displayed(el) and self._click_element(el):
                clicked = True
                break
        if not clicked:
            try:
                self.driver.back()
            except Exception:
                pass
        time.sleep(0.9)
        self.handle_popup_strict_after_login()
        self._click_any(
            [(AppiumBy.XPATH, '//android.widget.TextView[@text="首页"]')],
            timeout=5,
        )
        time.sleep(0.5)

    def _click_bottom_my_tab_like_home(self) -> bool:
        """
        点击底部「我的」Tab。Home.py 对「首页」用 element_to_be_clickable 可行；
        「我的」在 BottomNavigation 里经常是子 TextView 不可点，父 ItemView 可点，故增加 presence + _click_element 与下半屏几何兜底。
        """
        self.handle_popup_strict_after_login()
        if self._click_any(self._MY_TAB_LOCS, timeout=6):
            time.sleep(0.9)
            self.handle_popup_strict_after_login()
            return True
        for _ in range(4):
            self.handle_popup_strict_after_login()
            el = self._find_first(self._MY_TAB_LOCS, timeout=3)
            if el and self._click_element(el):
                time.sleep(0.9)
                self.handle_popup_strict_after_login()
                return True
            mine = self._pick_bottom_nav_mine_label()
            if mine and self._click_element(mine):
                time.sleep(0.9)
                self.handle_popup_strict_after_login()
                return True
            self._click_any(self._HOME_TAB_LOCS, timeout=3)
            time.sleep(0.45)
        logger.error("[ERR] 未点击到底部「我的」tab")
        return False

    def _is_my_balance_screen(self) -> bool:
        """识别「我的余额」业务页（账户余额）。"""
        try:
            src = self.driver.page_source or ""
        except Exception:
            src = ""
        if "账户余额" in src and "充值" in src:
            return True
        return bool(
            self._find(
                AppiumBy.XPATH,
                '//*[contains(@text,"账户余额") or contains(@content-desc,"账户余额")]',
                timeout=2,
            )
        )

    def _click_my_balance_entry(self) -> bool:
        """在「我的」页只点账户列表内 tv_menu=我的余额，避免误点其它含「余额」入口。"""
        uia_sels: Tuple[str, ...] = (
            'new UiSelector().resourceId("com.bs.feifubao:id/tv_menu").text("我的余额")',
            'new UiSelector().resourceId("com.ba.feifubao:id/tv_menu").text("我的余额")',
        )
        for _ in range(4):
            el = self._find_first(self._MY_BALANCE_ENTRY_LOCS, timeout=3)
            if el and self._click_element(el):
                return True
            for sel in uia_sels:
                try:
                    e2 = self.driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, sel)
                    if e2 and self._click_element(e2):
                        return True
                except Exception:
                    continue
            # 列表未滚到可见区时轻滑，仍不扩大点击范围
            self._swipe_fraction(0.58, 0.42, 420)
            time.sleep(0.35)
        return False

    def _post_login_my_balance_smoke(self) -> bool:
        """登录通过后：点击底部「我的」-> 点击「我的余额」-> 校验进入账户余额页。"""
        self.handle_popup_strict_after_login()
        if self._is_my_balance_screen():
            logger.info(
                "登录后链路完成：当前已在「我的余额（账户余额）」页（跳过重复点「我的」）"
            )
            return True
        # QQ/微信授权返回后常先进 WebViewComprehensiveActivity，单次 escape 不够，多轮直到离开壳或达上限
        for _ in range(5):
            self._escape_chopstick_headline_fullscreen_if_needed()
            act_l = self._current_activity_lower()
            if not self._activity_is_headline_or_comprehensive_h5_shell(act_l):
                break
            time.sleep(0.5)
        if not self._click_bottom_my_tab_like_home():
            return False
        if not self._click_my_balance_entry():
            logger.error("[ERR] 未点击到「我的余额」入口")
            return False
        time.sleep(1.0)
        self.handle_popup_strict_after_login()
        if not self._is_my_balance_screen():
            logger.error("[ERR] 未进入「我的余额/账户余额」页（请确认截图中的 resource-id / 文案）")
            self.log_current_screen_hybrid_diagnostics(
                "点击「我的余额」后未进入账户余额页，可能被弹层/H5 或路由拦截"
            )
            return False
        logger.info("登录后链路完成：已进入「我的余额（账户余额）」页")
        return True

    def assert_home_logged_in_features(self, timeout: int = 25) -> bool:
        """
        登录成功后：以「我的 -> 我的余额（账户余额）」链路作为断言。
        """
        end = time.time() + timeout
        while time.time() < end:
            if _post_login_subpage_escape_enabled():
                self._leave_post_login_subpage_for_home_assert()
            if self._post_login_my_balance_smoke():
                logger.info("断言通过：已完成「我的 -> 我的余额」链路")
                return True

            time.sleep(0.4)

        self.log_current_screen_hybrid_diagnostics(
            "登录成功断言失败：未完成「我的 -> 我的余额」链路（常见于登录后被拉到活动/H5 WebView）"
        )
        logger.error("[ERR] 登录成功断言失败：未进入「我的余额/账户余额」页")
        return False
