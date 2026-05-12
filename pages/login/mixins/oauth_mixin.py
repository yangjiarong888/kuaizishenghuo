"""微信 / QQ / 谷歌 OAuth 与聚合页到手机号页等。"""
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

from pages.login.constants import (
    QQ_CLIENT_PACKAGES,
    QQ_OAUTH_BROWSER_PACKAGES,
    SMS_PAGE_SOURCE_SEND_MARKERS,
)
from pages.login.data import Locator

logger = setup_logger("pages.login")

class LoginOAuthMixin:
    # ============ 1) 微信/QQ/谷歌授权 ============
    def _hub_semantics_element_area_y(self, el) -> Tuple[int, int]:
        """Semantics 节点面积与顶部 y；FlutterBoost 下多节点时优先点「整行」大区域。"""
        try:
            w = int(el.size.get("width") or 0)
            h = int(el.size.get("height") or 0)
            y = int(el.location.get("y") or 0)
            return (max(0, w * h), y)
        except Exception:
            return (0, 0)

    def _collect_hub_semantics_elements(self, phrase: str) -> list:
        xps = (
            f'//*[@content-desc="{phrase}"]',
            f'//*[contains(@content-desc,"{phrase}")]',
            f'//*[contains(@text,"{phrase}")]',
        )
        seen = set()
        out = []
        for xp in xps:
            try:
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    try:
                        uid = el.id
                    except Exception:
                        uid = id(el)
                    if uid in seen:
                        continue
                    seen.add(uid)
                    out.append(el)
            except Exception:
                continue
        out.sort(key=lambda e: self._hub_semantics_element_area_y(e), reverse=True)
        return out

    def _element_center_in_visible_viewport(self, el, vertical_margin_ratio: float = 0.07) -> bool:
        """语义节点中心须在可视区内；树里常有屏外大节点，点中会无反应却判成功。"""
        try:
            win = self.driver.get_window_size()
            H = int(win.get("height") or 0)
            W = int(win.get("width") or 0)
            if H < 200 or W < 200:
                return True
            m = max(8, int(H * vertical_margin_ratio))
            loc = el.location
            sz = el.size
            top = int(loc.get("y", 0))
            left = int(loc.get("x", 0))
            bw = int(sz.get("width", 0))
            bh = int(sz.get("height", 0))
            cy = top + bh // 2
            cx = left + bw // 2
            return m <= cy <= H - m and 0 <= cx <= W
        except Exception:
            return True

    def _hub_semantics_viewport_candidates(self, phrase: str, channel: str) -> list:
        """优先返回中心在屏内的节点；若无则上滑列表再收集（登录页列表偏长）。"""
        candidates = self._collect_hub_semantics_elements(phrase)
        vis = [e for e in candidates if self._element_center_in_visible_viewport(e)]
        if vis:
            return vis
        if not candidates:
            return []
        logger.info(
            "%s：「%s」语义节点中心均不在可视区，上滑列表尝试露出入口",
            channel,
            phrase[:20],
        )
        for i in range(6):
            self._swipe_vertical(0.56, 0.22, 520)
            time.sleep(0.48)
            candidates = self._collect_hub_semantics_elements(phrase)
            vis = [e for e in candidates if self._element_center_in_visible_viewport(e)]
            if vis:
                logger.info("%s：第 %s 次上滑后入口已在可视区内", channel, i + 1)
                return vis
        return candidates

    def _snapshot_oauth_ambient(self) -> Tuple[str, str, int, int, bool]:
        """package / activity / context 数 / WebView 数 / 是否已有协议底栏（用于对比点击后是否新出现）。"""
        pkg = act = ""
        try:
            pkg = (getattr(self.driver, "current_package", None) or "").strip()
            act = (getattr(self.driver, "current_activity", None) or "").strip()
        except Exception:
            pass
        ctx_n = 0
        try:
            ctx_n = len(self.driver.contexts or ())
        except Exception:
            pass
        wv = 0
        try:
            wv = (self.driver.page_source or "").count("android.webkit.WebView")
        except Exception:
            pass
        prot = self._login_protocol_bottom_sheet_visible()
        return (pkg, act, ctx_n, wv, prot)

    def _oauth_ambient_changed_from(self, snap: Tuple[str, str, int, int, bool]) -> bool:
        pkg, act, ctx_n, wv, prot_before = snap
        time.sleep(1.55)
        try:
            p2 = (getattr(self.driver, "current_package", None) or "").strip()
            a2 = (getattr(self.driver, "current_activity", None) or "").strip()
            if p2 != pkg or a2 != act:
                return True
        except Exception:
            pass
        try:
            if len(self.driver.contexts or ()) > ctx_n:
                return True
        except Exception:
            pass
        try:
            w2 = (self.driver.page_source or "").count("android.webkit.WebView")
            if w2 > wv:
                return True
        except Exception:
            pass
        if self._page_hints_qq_oauth_layer():
            return True
        if self._page_hints_wechat_oauth_layer():
            return True
        prot_after = self._login_protocol_bottom_sheet_visible()
        if prot_after and not prot_before:
            logger.info(
                "第三方登录入口：检测到协议说明弹层刚出现（点击已生效，需先点「同意并注册/登录」）"
            )
            return True
        return False

    def _double_click_gesture_at_element_center(self, el) -> bool:
        """Flutter 偶现单次手势无效，对元素中心连点两次。"""
        if self._click_gesture_suppressed_for_post_login():
            return False
        try:
            loc = el.location
            size = el.size
            x = int(loc["x"] + size["width"] / 2)
            y = int(loc["y"] + size["height"] / 2)
            for _ in range(2):
                self.driver.execute_script("mobile: clickGesture", {"x": x, "y": y})
                time.sleep(0.38)
            return True
        except Exception:
            return False

    def _try_click_hub_uiautomator(
        self,
        sels: Tuple[str, ...],
        channel: str,
        *,
        post_click_verify_navigation: bool = False,
    ) -> bool:
        for sel in sels:
            try:
                el = self.driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, sel)
            except Exception:
                continue
            if not el:
                continue
            snap = self._snapshot_oauth_ambient()
            if not self._click_element(el):
                continue
            if post_click_verify_navigation:
                if self._oauth_ambient_changed_from(snap):
                    logger.info(
                        "%s 入口：UiAutomator 点击后已检测到跳转 %s",
                        channel,
                        sel[:72],
                    )
                    return True
                logger.warning(
                    "%s：UiAutomator 点击未触发跳转，换下一选择器: %s",
                    channel,
                    sel[:64],
                )
                continue
            logger.info("%s 入口：UiAutomator 已点击 %s", channel, sel[:72])
            return True
        return False

    def _click_semantics_hub_login_entry(
        self,
        *,
        channel: str,
        exact_label: str,
        strict_locs: Tuple[Locator, ...],
        uia_selectors: Tuple[str, ...],
        loose_locs: Tuple[Locator, ...],
        min_area_env_var: str,
        default_min_area: int = 400,
        post_click_verify_navigation: bool = False,
    ) -> bool:
        """
        微信 / QQ 共用：先按面积点语义行，再 XPath / UiAutomator / 双击。
        QQ 可设 post_click_verify_navigation：点击后若包名/WebView 无变化则换候选，避免假成功。
        """
        logger.info(
            "尝试点击「%s」（%s：可视区内优先 / 上滑露出 / UiAutomator / 双击%s）",
            exact_label,
            channel,
            "；QQ 校验点击是否真跳转" if post_click_verify_navigation else "",
        )
        try:
            raw = (os.environ.get(min_area_env_var) or str(default_min_area)).strip()
            min_area = max(200, int(raw))
        except ValueError:
            min_area = default_min_area

        candidates = self._hub_semantics_viewport_candidates(exact_label, channel)
        for el in candidates[:8]:
            aw, ay = self._hub_semantics_element_area_y(el)
            if aw < min_area:
                continue
            if not self._element_center_in_visible_viewport(el):
                continue
            snap = self._snapshot_oauth_ambient()
            if not self._click_element(el):
                continue
            if post_click_verify_navigation:
                if self._oauth_ambient_changed_from(snap):
                    logger.info(
                        "%s 入口：大面积节点点击后已跳转 area=%s y=%s",
                        channel,
                        aw,
                        ay,
                    )
                    return True
                logger.warning(
                    "%s：大面积点击 area=%s y=%s 未触发跳转，换下一候选",
                    channel,
                    aw,
                    ay,
                )
                continue
            logger.info(
                "%s 入口：大面积语义节点点击 area=%s y=%s（%s=%s）",
                channel,
                aw,
                ay,
                min_area_env_var,
                min_area,
            )
            return True

        per = 5
        for by, xp in strict_locs:
            el = self._find(by, xp, timeout=per)
            if not el:
                continue
            snap = self._snapshot_oauth_ambient()
            if not self._click_element(el):
                continue
            if post_click_verify_navigation:
                if self._oauth_ambient_changed_from(snap):
                    logger.info("已下发 %s 登录入口点击并确认变化: %s", channel, xp[:96])
                    return True
                logger.warning("%s：单节点点击未触发跳转: %s", channel, xp[:96])
                continue
            logger.info("已下发 %s 登录入口点击: %s", channel, xp[:96])
            return True

        if self._try_click_hub_uiautomator(
            uia_selectors,
            channel,
            post_click_verify_navigation=post_click_verify_navigation,
        ):
            return True

        for by, xp in loose_locs:
            el = self._find(by, xp, timeout=3)
            if not el:
                continue
            snap = self._snapshot_oauth_ambient()
            if not self._click_element(el):
                continue
            if post_click_verify_navigation:
                if self._oauth_ambient_changed_from(snap):
                    logger.warning(
                        "%s：宽规则命中并确认变化: %s",
                        channel,
                        xp[:96],
                    )
                    return True
                logger.warning("%s：宽规则点击未跳转: %s", channel, xp[:96])
                continue
            logger.warning(
                "%s：已通过较宽规则命中节点，若误触请收紧: %s",
                channel,
                xp[:96],
            )
            return True

        for el in candidates[:6]:
            aw, _ = self._hub_semantics_element_area_y(el)
            if aw < 80:
                continue
            snap = self._snapshot_oauth_ambient()
            if not self._click_element(el):
                continue
            if post_click_verify_navigation:
                if self._oauth_ambient_changed_from(snap):
                    logger.info("%s 入口：小阈值补点 area=%s 后已跳转", channel, aw)
                    return True
                continue
            logger.info("%s 入口：小阈值补点 area=%s", channel, aw)
            return True

        if candidates:
            top = candidates[0]
            snap = self._snapshot_oauth_ambient()
            if self._double_click_gesture_at_element_center(top):
                if post_click_verify_navigation:
                    if self._oauth_ambient_changed_from(snap):
                        logger.info("%s 入口：双击手势后已跳转", channel)
                        return True
                else:
                    logger.info("%s 入口：已对最大语义节点做中心双击手势", channel)
                    return True

        if post_click_verify_navigation and candidates:
            logger.error(
                "%s：多种点击后仍未检测到包名/WebView/授权层变化；若手动点 QQ 正常，请开发核对 QQ 开放平台 AppID/签名/包名",
                channel,
            )
        return False

    def _click_wechat_login_entry(self) -> bool:
        """与 QQ 同一套 Flutter 语义行策略（面积优先 + UiAutomator）。"""
        return self._click_semantics_hub_login_entry(
            channel="微信",
            exact_label="微信账号快捷登录",
            strict_locs=(
                (AppiumBy.ACCESSIBILITY_ID, "微信账号快捷登录"),
                (AppiumBy.XPATH, '//*[@content-desc="微信账号快捷登录"]'),
                (AppiumBy.XPATH, '//*[contains(@text,"微信账号快捷登录")]'),
            ),
            uia_selectors=(
                'new UiSelector().description("微信账号快捷登录")',
                'new UiSelector().descriptionContains("微信账号快捷登录")',
                'new UiSelector().textContains("微信账号快捷登录")',
            ),
            loose_locs=(
                (AppiumBy.XPATH, '//*[contains(@text,"微信账号登录")]'),
            ),
            min_area_env_var="WECHAT_LOGIN_MIN_SEMANTICS_AREA",
            default_min_area=400,
            post_click_verify_navigation=True,
        )

    def _click_wechat_login_entry_after_agree(self) -> bool:
        """点「同意」后一般会自启微信授权；仅轮询超时时兜底再点入口。"""
        return self._click_semantics_hub_login_entry(
            channel="微信(协议后)",
            exact_label="微信账号快捷登录",
            strict_locs=(
                (AppiumBy.ACCESSIBILITY_ID, "微信账号快捷登录"),
                (AppiumBy.XPATH, '//*[@content-desc="微信账号快捷登录"]'),
                (AppiumBy.XPATH, '//*[contains(@text,"微信账号快捷登录")]'),
            ),
            uia_selectors=(
                'new UiSelector().description("微信账号快捷登录")',
                'new UiSelector().descriptionContains("微信账号快捷登录")',
                'new UiSelector().textContains("微信账号快捷登录")',
            ),
            loose_locs=(
                (AppiumBy.XPATH, '//*[contains(@text,"微信账号登录")]'),
            ),
            min_area_env_var="WECHAT_LOGIN_MIN_SEMANTICS_AREA",
            default_min_area=400,
            post_click_verify_navigation=False,
        )

    def _log_oauth_webview_context_if_present(self, channel: str) -> None:
        """QQ 常在内嵌 WebView 授权，包名不变；有 WebView 上下文时打日志避免误判「没唤起」。"""
        try:
            ctxs = list(self.driver.contexts or ())
        except Exception:
            return
        wvs = [c for c in ctxs if "WEBVIEW" in c.upper()]
        if not wvs:
            return
        logger.info(
            "%s：当前存在 WebView 上下文 %s。互联授权可能在此页完成，前台包名仍可能是筷子生活。",
            channel,
            wvs[:4],
        )

    def login_by_wechat(self) -> bool:
        """点击微信登录 -> 协议 -> 检查是否安装 -> 授权登录。"""
        self._phone_sms_login_active = False
        wechat_pkg = "com.tencent.mm"
        if not self._is_app_installed(wechat_pkg):
            logger.error("[WARN] 微信未安装")
            return False

        self.handle_popup()
        # 入口列表偏下时可能需先上滑，与手机号分流一致
        self._swipe_vertical(0.62, 0.38, 450)
        time.sleep(0.45)
        self._try_agree_user_protocol_password_page()
        time.sleep(0.35)
        self._dismiss_password_login_protocol_sheet_if_present(total_wait_sec=4.0)
        self.handle_popup()

        if not self._click_wechat_login_entry():
            logger.error("未找到微信登录入口")
            return False

        time.sleep(0.55)
        self._log_oauth_webview_context_if_present("微信登录")
        self._dismiss_password_login_protocol_sheet_if_present(total_wait_sec=10.0)
        if self._login_protocol_bottom_sheet_visible():
            logger.warning("微信：协议层仍可见，再关一轮（含底部手势兜底）")
            self._dismiss_password_login_protocol_sheet_if_present(total_wait_sec=6.0)
        self.handle_popup()
        time.sleep(0.65)
        wechat_watch = tuple(
            dict.fromkeys([wechat_pkg] + list(QQ_OAUTH_BROWSER_PACKAGES))
        )
        wx_wait_primary = 24.0
        logger.info(
            "微信：与手动一致——点「同意」后一般由客户端自动拉起授权；"
            "先等待微信/浏览器或授权层（约 %.0fs），不立即二次点击入口",
            wx_wait_primary,
        )
        wx_probe = self._probe_feifubao_home_logged_in_after_oauth
        seen_wx, in_app_wx, wx_already_home = self._poll_oauth_after_protocol_agreed(
            wechat_watch, wx_wait_primary, oauth_kind="wechat", already_logged_in_probe=wx_probe
        )
        if not wx_already_home and not seen_wx and not in_app_wx:
            if self._probe_feifubao_home_logged_in_after_oauth():
                wx_already_home = True
        skip_wx_authorize_clicks = wx_already_home
        if wx_already_home:
            logger.info(
                "微信：已检测到主应用首页（协议同意后常静默完成登录），不补点入口、不依赖微信前台"
            )
        elif seen_wx and seen_wx in QQ_OAUTH_BROWSER_PACKAGES:
            logger.info(
                "已检测到浏览器前台 %s（微信互联可能走 Custom Tabs），继续尝试允许/同意",
                seen_wx,
            )
        elif seen_wx:
            logger.info("已检测到微信或浏览器前台: %s", seen_wx)
        elif in_app_wx:
            logger.info(
                "已检测到微信授权/WebView 迹象（同意协议后自动进入，与手动单点同意一致）"
            )
        else:
            logger.warning(
                "%.0fs 内未见微信前台与授权层，尝试补点一次「微信账号快捷登录」作兜底",
                wx_wait_primary,
            )
            self._dismiss_password_login_protocol_sheet_if_present(total_wait_sec=3.0)
            self.handle_popup()
            self._click_wechat_login_entry_after_agree()
            self.handle_popup()
            self._dismiss_password_login_protocol_sheet_if_present(total_wait_sec=4.0)
            seen_wx, in_app_wx, wx_already_home = self._poll_oauth_after_protocol_agreed(
                wechat_watch, 18.0, oauth_kind="wechat", already_logged_in_probe=wx_probe
            )
            if not wx_already_home and not seen_wx and not in_app_wx:
                if self._probe_feifubao_home_logged_in_after_oauth():
                    wx_already_home = True
            if wx_already_home:
                skip_wx_authorize_clicks = True
                logger.info("微信：已回到主应用首页，视为已登录，跳过授权页点击")
            elif seen_wx and seen_wx in QQ_OAUTH_BROWSER_PACKAGES:
                logger.info("兜底点击后已进入浏览器前台: %s", seen_wx)
            elif seen_wx:
                logger.info("兜底点击后已进入微信或浏览器前台: %s", seen_wx)
            elif in_app_wx:
                logger.info("兜底点击后已出现微信授权/WebView 迹象")
            elif not self._page_hints_wechat_oauth_layer():
                logger.warning(
                    "微信：仍未检测到授权层，将继续尝试授权按钮与登录断言（可能已切微信但未命中文案）"
                )

        wx_allow_locs: Tuple[Locator, ...] = (
            (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().text("允许")'),
            (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("允许")'),
            (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().descriptionContains("允许")'),
            (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().text("同意")'),
            (AppiumBy.ID, "com.tencent.mm:id/btn_allow"),
            (AppiumBy.XPATH, '//*[@content-desc="允许" or @content-desc="授权"]'),
            (AppiumBy.XPATH, '//*[contains(@text,"允许") or contains(@text,"授权") or contains(@text,"同意")]'),
            (AppiumBy.XPATH, '//*[contains(@text,"确认登录") or contains(@text,"允许登录")]'),
            (AppiumBy.XPATH, '//*[contains(@text,"同意登录")]'),
        )
        if not skip_wx_authorize_clicks:
            if seen_wx:
                self._oauth_bring_client_to_automation_foreground(seen_wx, "微信互联")
            elif in_app_wx:
                logger.info("微信：授权在宿主内 WebView，不执行 activate_app(微信)")
            else:
                self._oauth_bring_client_to_automation_foreground(wechat_pkg, "微信")
            wx_hint = (seen_wx or ("内嵌WebView" if in_app_wx else wechat_pkg) or "?")
            logger.info("微信：开始在授权页查找并点击「允许/同意」（XPath + UiAutomator，观测=%s）…", wx_hint)
            time.sleep(1.2)
            for by, xp in wx_allow_locs:
                el = self._find(by, xp, timeout=5)
                if el and self._click_element(el):
                    logger.info("已在微信授权相关页尝试点击: %s", xp[:88])
                    break
            else:
                self._click_any(wx_allow_locs, timeout=10)
            self._oauth_rescue_clicks_until_host(
                label="微信",
                client_pkgs=(wechat_pkg,),
                allow_locs=wx_allow_locs,
            )

        self._arm_post_login_click_gesture_suppress()
        if skip_wx_authorize_clicks:
            self._post_login_idle_wait_suppressing_headline(minimum_sec=1.25)
        else:
            self._post_login_idle_wait_suppressing_headline()
        return self._verify_logged_in()

    def _click_qq_login_entry(self) -> bool:
        return self._click_semantics_hub_login_entry(
            channel="QQ",
            exact_label="QQ账号快捷登录",
            strict_locs=(
                (AppiumBy.ACCESSIBILITY_ID, "QQ账号快捷登录"),
                (AppiumBy.XPATH, '//*[@content-desc="QQ账号快捷登录"]'),
                (AppiumBy.XPATH, '//*[contains(@text,"QQ账号快捷登录")]'),
            ),
            uia_selectors=(
                'new UiSelector().description("QQ账号快捷登录")',
                'new UiSelector().descriptionContains("QQ账号快捷登录")',
                'new UiSelector().textContains("QQ账号快捷登录")',
                'new UiSelector().className("android.view.View").descriptionContains("QQ账号")',
            ),
            loose_locs=(
                (AppiumBy.XPATH, '//*[contains(@text,"QQ账号登录")]'),
            ),
            min_area_env_var="QQ_LOGIN_MIN_SEMANTICS_AREA",
            default_min_area=400,
            post_click_verify_navigation=True,
        )

    def _click_qq_login_entry_after_agree(self) -> bool:
        """
        多数真机：点「同意」后客户端会自动继续 QQ 授权，**不必**再点 QQ。
        仅当轮询超时仍无 QQ/授权层时作兜底补点；不做「协议刚出现」校验。
        """
        return self._click_semantics_hub_login_entry(
            channel="QQ(协议后)",
            exact_label="QQ账号快捷登录",
            strict_locs=(
                (AppiumBy.ACCESSIBILITY_ID, "QQ账号快捷登录"),
                (AppiumBy.XPATH, '//*[@content-desc="QQ账号快捷登录"]'),
                (AppiumBy.XPATH, '//*[contains(@text,"QQ账号快捷登录")]'),
            ),
            uia_selectors=(
                'new UiSelector().description("QQ账号快捷登录")',
                'new UiSelector().descriptionContains("QQ账号快捷登录")',
                'new UiSelector().textContains("QQ账号快捷登录")',
                'new UiSelector().className("android.view.View").descriptionContains("QQ账号")',
            ),
            loose_locs=(
                (AppiumBy.XPATH, '//*[contains(@text,"QQ账号登录")]'),
            ),
            min_area_env_var="QQ_LOGIN_MIN_SEMANTICS_AREA",
            default_min_area=400,
            post_click_verify_navigation=False,
        )

    def _poll_oauth_after_protocol_agreed(
        self,
        watch_pkgs: Tuple[str, ...],
        timeout_sec: float,
        *,
        oauth_kind: str,
        already_logged_in_probe: Optional[Callable[[], bool]] = None,
    ) -> Tuple[Optional[str], bool, bool]:
        """
        点「同意并注册/登录」后 App 通常会自行调起 QQ/微信/浏览器/内嵌授权。
        oauth_kind: \"qq\" | \"wechat\"
        返回 (匹配 watch 的前台包名, 是否已见应用内授权或 WebView 上下文, 是否已探测到主应用静默登录成功)。
        """
        deadline = time.time() + max(1.0, float(timeout_sec))
        watch_set = frozenset(watch_pkgs)
        kind = (oauth_kind or "").strip().lower()
        while time.time() < deadline:
            if already_logged_in_probe is not None:
                try:
                    if already_logged_in_probe():
                        return (None, False, True)
                except Exception:
                    pass
            try:
                cur = (getattr(self.driver, "current_package", None) or "").strip()
                if cur in watch_set:
                    return (cur, False, False)
            except Exception:
                pass
            if kind == "qq" and self._page_hints_qq_oauth_layer():
                return (None, True, False)
            if kind == "wechat" and self._page_hints_wechat_oauth_layer():
                return (None, True, False)
            try:
                ctxs = list(self.driver.contexts or [])
                if len(ctxs) > 1 and any("WEBVIEW" in c.upper() for c in ctxs):
                    return (None, True, False)
            except Exception:
                pass
            time.sleep(0.45)
        return (None, False, False)

    def _oauth_bring_client_to_automation_foreground(self, package: str, label: str) -> None:
        """
        会话以筷子生活为 appPackage 启动时，微信/QQ 到前台后若不 activate，
        部分机型上 find/click 仍对着宿主进程，授权页「允许」点不到（拆 Mixin 前后逻辑相同，此处补显式切换）。
        """
        p = (package or "").strip()
        if not p:
            return
        try:
            self.driver.activate_app(p)
            logger.info("%s：已对 %s 执行 activate_app，便于驱动枚举当前授权页", label, p)
            time.sleep(0.95)
        except Exception as e:
            logger.warning("%s：activate_app(%s) 失败（若前台已是该包可忽略）: %s", label, p, e)

    def _oauth_rescue_clicks_until_host(
        self,
        *,
        label: str,
        client_pkgs: Tuple[str, ...],
        allow_locs: Tuple[Locator, ...],
        max_sec: float = 90.0,
    ) -> None:
        """
        检测到 QQ/微信/浏览器仍在前台时，仅一轮「允许」常点不到或页面未就绪。
        循环尝试授权定位并轮询 current_package，直到回到筷子生活（包名含 feifubao）或超时。
        """
        browsers = frozenset(QQ_OAUTH_BROWSER_PACKAGES)
        clients = frozenset(p for p in client_pkgs if (p or "").strip())
        deadline = time.time() + max(0.0, float(max_sec))
        last_info = 0.0
        while time.time() < deadline:
            try:
                cur = (getattr(self.driver, "current_package", None) or "").strip()
            except Exception:
                cur = ""
            cur_l = cur.lower()
            if "feifubao" in cur_l:
                logger.info("%s：已回到宿主应用 package=%s", label, cur)
                return
            if cur in clients or cur in browsers:
                try:
                    self.driver.activate_app(cur)
                    time.sleep(0.45)
                except Exception:
                    pass
                now = time.time()
                if now - last_info >= 5.5:
                    logger.info(
                        "%s：前台仍为第三方/浏览器（%s），持续尝试「允许/同意」并等待回切宿主…",
                        label,
                        cur,
                    )
                    last_info = now
                self._click_any(allow_locs, timeout=5)
                time.sleep(1.4)
                continue
            if not cur:
                time.sleep(0.5)
                continue
            time.sleep(0.7)

        try:
            tail = (getattr(self.driver, "current_package", None) or "").strip()
        except Exception:
            tail = ""
        if "feifubao" not in (tail or "").lower():
            logger.warning(
                "%s：%.0fs 内仍未回到筷子生活（当前 package=%s）。"
                "若仍停在微信/QQ 授权页，请在真机点「允许」后重试；或检查 Appium 是否仍能驱动当前前台。",
                label,
                max_sec,
                tail or "?",
            )

    def login_by_qq(self) -> bool:
        """点击QQ登录 -> 协议 -> 检查是否安装 -> 授权登录。"""
        self._phone_sms_login_active = False
        pkgs = QQ_CLIENT_PACKAGES
        installed = [p for p in pkgs if self._is_app_installed(p)]
        if not installed:
            logger.error("[WARN] 未检测到已安装的 QQ / TIM / QQ轻聊版")
            return False
        logger.info("检测到已安装的 QQ 类客户端: %s", "、".join(installed))

        watch_pkgs = tuple(
            dict.fromkeys(list(pkgs) + list(QQ_OAUTH_BROWSER_PACKAGES))
        )

        self.handle_popup()
        self._swipe_vertical(0.62, 0.38, 450)
        time.sleep(0.45)
        self._try_agree_user_protocol_password_page()
        time.sleep(0.35)
        self._dismiss_password_login_protocol_sheet_if_present(total_wait_sec=4.0)
        self.handle_popup()

        if not self._click_qq_login_entry():
            logger.error(
                "QQ 登录入口未找到，或已点击但未见授权/跳转（见上文 WARNING/ERROR；"
                "若手动可登请核对 QQ 开放平台与客户端配置）"
            )
            return False

        time.sleep(0.55)
        self._log_oauth_webview_context_if_present("QQ 登录")
        # 勿先调 handle_popup()：其内多个「同意」XPath 各等 3s，协议挡屏时会累加近一分钟
        self._dismiss_password_login_protocol_sheet_if_present(total_wait_sec=10.0)
        if self._login_protocol_bottom_sheet_visible():
            logger.warning("QQ：协议层仍可见，再关一轮（含底部手势兜底）")
            self._dismiss_password_login_protocol_sheet_if_present(total_wait_sec=6.0)
        self.handle_popup()
        time.sleep(0.65)
        qq_wait_primary = 24.0
        logger.info(
            "QQ：与手动一致——点「同意」后一般由客户端自动拉起授权；"
            "先等待 QQ/浏览器或授权层（约 %.0fs），不立即二次点击入口",
            qq_wait_primary,
        )
        probe = self._probe_feifubao_home_logged_in_after_oauth
        seen_pkg, in_app_oauth, already_home = self._poll_oauth_after_protocol_agreed(
            watch_pkgs, qq_wait_primary, oauth_kind="qq", already_logged_in_probe=probe
        )
        if not already_home and not seen_pkg and not in_app_oauth:
            if self._probe_feifubao_home_logged_in_after_oauth():
                already_home = True
        skip_qq_authorize_clicks = already_home
        if already_home:
            logger.info(
                "QQ：已检测到主应用首页（协议同意后常静默完成登录），不补点入口、不依赖 QQ 前台"
            )
        elif seen_pkg and seen_pkg in QQ_OAUTH_BROWSER_PACKAGES:
            logger.info(
                "已检测到浏览器前台 %s（多为 Custom Tabs / 系统浏览器打开 QQ 互联），继续尝试允许/同意",
                seen_pkg,
            )
        elif seen_pkg:
            logger.info("已检测到 QQ 类应用或浏览器前台: %s", seen_pkg)
        elif in_app_oauth:
            logger.info(
                "已检测到 QQ 互联/ WebView 迹象（同意协议后自动进入，与手动单点同意一致）"
            )
        else:
            logger.warning(
                "%.0fs 内未见 QQ 前台与授权层，尝试补点一次「QQ账号快捷登录」作兜底（部分 ROM 上自动化与手点路径不一致）",
                qq_wait_primary,
            )
            self._dismiss_password_login_protocol_sheet_if_present(total_wait_sec=3.0)
            self.handle_popup()
            self._click_qq_login_entry_after_agree()
            self.handle_popup()
            self._dismiss_password_login_protocol_sheet_if_present(total_wait_sec=4.0)
            seen_pkg, in_app_oauth, already_home = self._poll_oauth_after_protocol_agreed(
                watch_pkgs, 18.0, oauth_kind="qq", already_logged_in_probe=probe
            )
            if not already_home and not seen_pkg and not in_app_oauth:
                if self._probe_feifubao_home_logged_in_after_oauth():
                    already_home = True
            if already_home:
                skip_qq_authorize_clicks = True
                logger.info("QQ：已回到主应用首页，视为已登录，跳过授权页点击")
            elif seen_pkg and seen_pkg in QQ_OAUTH_BROWSER_PACKAGES:
                logger.info("兜底点击后已进入浏览器前台: %s", seen_pkg)
            elif seen_pkg:
                logger.info("兜底点击后已进入 QQ 类应用前台: %s", seen_pkg)
            elif in_app_oauth:
                logger.info("兜底点击后已出现授权/WebView 迹象")
            elif not self._page_hints_qq_oauth_layer():
                try:
                    cur = (getattr(self.driver, "current_package", "") or "").strip()
                    act = (getattr(self.driver, "current_activity", "") or "").strip()
                    act_l = (act or "").lower()
                    if "webviewcomprehensive" in act_l or "webviewh5news" in act_l:
                        logger.info(
                            "当前 package=%s activity=%s：多为 OAuth 完成后进入运营/H5 全屏壳，"
                            "不代表未登录；随后将点授权（若仍在前台）并退出壳再做「我的」断言",
                            cur,
                            act,
                        )
                    else:
                        logger.warning(
                            "仍未进入授权流程；当前 package=%s activity=%s。"
                            "可设 QQ_LOGIN_MIN_SEMANTICS_AREA=400 降低面积阈值重试；"
                            "或设 TRACE_CLICK_TO_WEBVIEW=1 对照点击后是否误进 WebView。"
                            "若本机只用 TIM 请确认已安装 com.tencent.tim。",
                            cur,
                            act,
                        )
                except Exception:
                    pass

        if not skip_qq_authorize_clicks:
            if seen_pkg:
                self._oauth_bring_client_to_automation_foreground(seen_pkg, "QQ 授权")
            elif in_app_oauth:
                logger.info("QQ：授权在宿主内 WebView，不执行 activate_app(QQ/TIM)")
            allow_locs: Tuple[Locator, ...] = (
                (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().text("允许")'),
                (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("允许")'),
                (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().descriptionContains("授权")'),
                (AppiumBy.ACCESSIBILITY_ID, "授权并登录"),
                (AppiumBy.XPATH, '//*[contains(@text,"允许") or contains(@text,"授权") or contains(@text,"同意")]'),
                (AppiumBy.XPATH, '//*[@content-desc="允许" or @content-desc="授权"]'),
                (
                    AppiumBy.XPATH,
                    '//*[contains(@text,"授权并登录") or contains(@text,"QQ登录") or contains(@text,"使用QQ登录")]',
                ),
                (AppiumBy.XPATH, '//*[contains(@text,"QQ授权登录")]'),
            )
            logger.info("QQ：开始在授权页查找并点击「允许/授权并登录」…")
            time.sleep(1.6)
            for by, xp in allow_locs:
                el = self._find(by, xp, timeout=4)
                if el and self._click_element(el):
                    logger.info("已在 QQ 授权相关页尝试点击: %s", xp[:88])
                    break
            else:
                self._click_any(allow_locs, timeout=8)
            self._oauth_rescue_clicks_until_host(
                label="QQ",
                client_pkgs=tuple(pkgs),
                allow_locs=allow_locs,
            )

        self._arm_post_login_click_gesture_suppress()
        # 与密码登录一致：等待期内轮询退出登录后进头条/H5 全屏壳，避免卡在 WebViewComprehensive 点不到「我的」
        if skip_qq_authorize_clicks:
            self._post_login_idle_wait_suppressing_headline(minimum_sec=1.25)
        else:
            self._post_login_idle_wait_suppressing_headline()
        return self._verify_logged_in()

    def login_by_google(self) -> bool:
        """点击谷歌登录 -> 协议 -> 检查是否安装 -> 登录授权。"""
        self._phone_sms_login_active = False
        ok = self._click_any(
            [
                (AppiumBy.ACCESSIBILITY_ID, "谷歌账号快捷登录"),
                (AppiumBy.XPATH, '//*[@content-desc="谷歌账号快捷登录"]'),
                (AppiumBy.XPATH, '//*[contains(@text,"谷歌账号快捷登录")]'),
                (AppiumBy.XPATH, '//*[contains(@text,"谷歌")]'),
                (AppiumBy.XPATH, '//*[contains(@text,"Google")]'),
            ],
            timeout=10,
        )
        if not ok:
            logger.error("未找到谷歌登录入口")
            return False

        self.handle_popup()

        # Google 登录通常依赖 Google Play services
        google_services_pkg = "com.google.android.gms"
        if not self._is_app_installed(google_services_pkg):
            logger.error("[WARN] Google Play services 未安装（无法登录）")
            return False

        allow_locs = [
            (AppiumBy.XPATH, '//*[contains(@text,"同意") or contains(@text,"允许") or contains(@text,"继续")]'),
            (AppiumBy.XPATH, '//*[@content-desc="允许" or @content-desc="同意"]'),
        ]
        time.sleep(2)
        self._click_any(allow_locs, timeout=12)

        time.sleep(self.POST_LOGIN_VERIFY_WAIT_SEC)
        # 若失败：页面通常会出现提示，这里只做“是否回到登录成功”判断
        ok2 = self._verify_logged_in()
        if not ok2:
            logger.error("[ERR] 谷歌登录失败（未检测到登录成功特征）")
        return ok2

    def _get_sms_verification_send_control_visible(self) -> bool:
        """树里是否存在「获取短信验证码」语义（可见优先；部分机型 View 节点 is_displayed 不可靠则看 page_source）。"""
        locs: Tuple[Locator, ...] = (
            # Inspector：Flutter 主按钮多为 android.view.View + content-desc（非 TextView）
            (AppiumBy.XPATH, '//android.view.View[@content-desc="获取短信验证码"]'),
            (AppiumBy.XPATH, '//android.view.View[contains(@content-desc,"获取短信验证码")]'),
            (AppiumBy.XPATH, '//*[@content-desc="获取短信验证码"]'),
            (AppiumBy.XPATH, '//*[contains(@content-desc,"获取短信验证码")]'),
            (AppiumBy.XPATH, '//*[contains(@text,"获取短信验证码")]'),
            (AppiumBy.XPATH, '//*[contains(@text,"获取验证码")]'),
            (AppiumBy.XPATH, '//*[contains(@text,"获取短信")]'),
        )
        for by, xp in locs:
            for el in self._find_all_now(by, xp):
                if self._is_displayed(el):
                    return True
        # View 在部分驱动上 is_displayed=false，但 bounds 有效仍可点击
        for by, xp in (
            (AppiumBy.XPATH, '//android.view.View[@content-desc="获取短信验证码"]'),
            (AppiumBy.XPATH, '//android.view.View[contains(@content-desc,"获取短信验证码")]'),
        ):
            for el in self._find_all_now(by, xp):
                try:
                    if el and el.size.get("width", 0) >= 80 and el.size.get("height", 0) >= 24:
                        return True
                except Exception:
                    continue
        try:
            src = self.driver.page_source or ""
        except Exception:
            src = ""
        if any(t in src for t in SMS_PAGE_SOURCE_SEND_MARKERS):
            return True
        return False

    def _raw_page_source(self) -> str:
        try:
            return self.driver.page_source or ""
        except Exception:
            return ""

    def _page_source_indicates_sms_captcha_login_panel(self) -> bool:
        """
        只要层级里已出现发码主按钮语义，即认为当前在「手机号 + 短信验证码」这条 UI 线上
        （与 is_displayed、是否在密码 Tab 的误判解耦）。
        """
        src = self._raw_page_source()
        if len(src) < 200:
            return False
        if not any(m in src for m in SMS_PAGE_SOURCE_SEND_MARKERS):
            return False
        if "EditText" in src or "android.widget.EditText" in src:
            return True
        if (
            "请输入手机号" in src
            or "et_phone" in src
            or "未注册的手机号" in src
        ):
            return True
        return False

    def _stabilize_sms_captcha_login_panel(self, total_sec: float = 14.0) -> None:
        """
        进入「手机号码登录/注册」内层后，轮询协议/弹窗、切验证码 Tab，
        直至 page_source 稳定出现「获取短信验证码」等发码语义。
        说明：此阶段在**输入手机号之前**执行；树上出现发码文案只表示当前为验证码 Tab/页面，非「已发码」。
        """
        if not self._phone_sms_login_active:
            return
        if self._page_source_indicates_sms_captcha_login_panel():
            logger.info(
                "手机号验证码流程：层级已含发码区语义（尚未输手机号，接着将输入手机号并点「获取短信验证码」）"
            )
            return
        end = time.time() + total_sec
        while time.time() < end:
            self.handle_popup()
            if self._phone_sms_login_active:
                self._try_agree_user_protocol_password_page(footer_only=True)
            else:
                self._try_agree_user_protocol_password_page()
            self.handle_popup()
            if self._page_source_indicates_sms_captcha_login_panel():
                logger.info(
                    "手机号验证码流程：已稳定到含发码语义的页面（尚未输手机号；下一步输入手机号后发码）"
                )
                return
            # 勿在「默认验证码 Tab、仅 page_source 无发码文案」时乱切 Tab：偏右坐标会点到「账号密码」分段
            if self._phone_sms_should_attempt_switch_to_captcha_tab():
                self._switch_to_sms_captcha_login_tab()
            time.sleep(0.35)
            if self._page_source_indicates_sms_captcha_login_panel():
                logger.info(
                    "手机号验证码流程：切 Tab 后层级已含发码语义（尚未输手机号；下一步输入手机号后发码）"
                )
                return
            # 不在此循环里上滑表单：易把底部「账号密码登录」滚进可点区域，配合后续手势会误切密码 Tab
            time.sleep(0.4)
        # 稳定阶段末再试一轮 bounds：部分机型分段 Tab 仅在协议/弹窗收起后才写入完整树
        if self._phone_sms_login_active and self._phone_sms_should_attempt_switch_to_captcha_tab():
            if self._click_sms_captcha_tab_by_page_source_bounds():
                logger.info(
                    "手机号验证码流程：稳定阶段末切 Tab 后出现发码语义（尚未输手机号；下一步输入手机号后发码）"
                )
            else:
                self._ensure_sms_captcha_login_tab()
        logger.warning(
            "[WARN] %.0fs 内 page_source 仍未出现发码类文案（获取/发送验证码等），将继续输号与发码尝试",
            total_sec,
        )
        self._log_sms_login_page_diagnosis()

    def _iter_tag_desc_bounds_pairs(
        self, src: str
    ) -> Iterable[Tuple[str, int, int, int, int]]:
        """遍历 page_source 里同时带 content-desc 与 bounds 的开标签（粗解析，供诊断与模糊发码区）。"""
        for m in re.finditer(r"<([^\s/>]+)([^>]+)>", src):
            body = m.group(2)
            if "content-desc=" not in body or "bounds=" not in body:
                continue
            dm = re.search(r'content-desc="([^"]*)"', body)
            bm = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', body)
            if not dm or not bm:
                continue
            desc = dm.group(1)
            x1, y1, x2, y2 = (int(bm.group(i)) for i in range(1, 5))
            yield desc, x1, y1, x2, y2

    def _log_sms_login_page_diagnosis(self) -> None:
        """发码失败或稳定超时时打日志，便于对照 Inspector 真机树差异。"""
        src = self._raw_page_source()
        if not src:
            logger.warning("短信登录诊断：page_source 为空")
            return
        n_et = len(self._visible_edittexts_top_to_bottom())
        bits = [
            ("len(src)", len(src)),
            ("可见EditText数", n_et),
            ("获取短信验证码字面", "获取短信验证码" in src),
            ("发送验证码字面", "发送验证码" in src),
            ("请输入密码", "请输入密码" in src),
            ("et_password", "et_password" in src),
            ("未注册的手机号", "未注册的手机号" in src),
        ]
        logger.warning("短信登录诊断：" + "；".join(f"{k}={v}" for k, v in bits))
        samples: list[str] = []
        for desc, *_ in self._iter_tag_desc_bounds_pairs(src):
            if not desc or len(desc) > 120:
                continue
            if any(
                x in desc
                for x in ("验证", "短信", "登录", "密码", "手机", "获取", "发送")
            ):
                samples.append(desc)
        uniq = list(dict.fromkeys(samples))[:12]
        if uniq:
            logger.warning(
                "content-desc 样本（与验证/发码相关，至多12条）: %s",
                " | ".join(uniq),
            )

    def _best_bounds_center_for_sms_cta_from_page_source(
        self, src: str
    ) -> Optional[Tuple[int, int]]:
        """
        当精确「获取短信验证码」不在 XML 中时，从所有节点的 content-desc + bounds 里
        挑最像主发码按钮的一块（面积大、纵坐标在手机号区下方、避开明显密码/账号文案）。
        """
        try:
            h = int(self.driver.get_window_size()["height"])
            w = int(self.driver.get_window_size()["width"])
        except Exception:
            return None
        y_lo = max(80, int(h * 0.26))
        y_hi = min(h - 80, self._sms_send_gesture_y_max(h, None) + 80)
        x_margin = max(8, int(w * 0.04))
        exact_order = (
            "获取短信验证码",
            "发送验证码",
            "获取验证码",
            "发送短信验证码",
            "免费获取验证码",
            "免费获取",
        )
        best: Optional[Tuple[int, int, int]] = None  # area, cx, cy

        def consider(desc: str, x1: int, y1: int, x2: int, y2: int) -> None:
            nonlocal best
            if "密码" in desc or "账号密码" in desc or "请输入" in desc:
                return
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            if cy < y_lo or cy > y_hi:
                return
            if cx < x_margin or cx > w - x_margin:
                return
            aw = max(1, x2 - x1)
            ah = max(1, y2 - y1)
            area = aw * ah
            if area < 800:  # 过滤过小命中区
                return
            if best is None or area > best[0]:
                best = (area, cx, cy)

        for d in exact_order:
            c = self._bounds_center_for_content_desc_in_page_source(src, d)
            if c:
                return c

        for desc, x1, y1, x2, y2 in self._iter_tag_desc_bounds_pairs(src):
            if desc in exact_order:
                consider(desc, x1, y1, x2, y2)
                continue
            if ("短信" in desc or "sms" in desc.lower()) and (
                "验证" in desc or "码" in desc
            ):
                if "密码" in desc:
                    continue
                consider(desc, x1, y1, x2, y2)
            elif ("获取" in desc or "发送" in desc) and (
                "验证" in desc or "码" in desc
            ):
                consider(desc, x1, y1, x2, y2)

        if best:
            return (best[1], best[2])
        return None

    def _sms_send_or_code_step_likely_active(self) -> bool:
        """
        点发码后或已在输验证码步骤时，page_source 常见片段。
        勿加入裸子串「短信验证码」：手机号页 Tab/标题里也有，会导致未点发码就误判成功。
        """
        try:
            src = self.driver.page_source or ""
        except Exception:
            src = ""
        if not src:
            return False
        markers = (
            "请输入验证码",
            "输入验证码",
            "验证码已发送",
            "已发送至",
            "重新获取",
            "秒后",
            "S后",
            "重新发送",
            "发送成功",
        )
        if any(m in src for m in markers):
            return True
        # 「已发送」单独出现太泛；仅在与发码/验证码语境并存时认作已离开「仅手机号+发码」主步骤
        if "已发送" in src and (
            "验证码" in src or "短信" in src or "重新" in src or "输入" in src
        ):
            return True
        return False

    def _sms_code_entry_or_sent_step_active(self) -> bool:
        """
        已在「填写验证码」或「已发短信、等输入」阶段。
        用于避免在验证码页仍轮询点击发码、或超时后又跑发码手势（与手动填码冲突）。
        """
        if self._sms_send_or_code_step_likely_active():
            return True
        strong = getattr(self, "_login_protocol_post_agree_strong_signal", None)
        if callable(strong) and strong():
            return True
        try:
            src = self.driver.page_source or ""
        except Exception:
            src = ""
        for needle in (
            "请输入短信验证码",
            "填写验证码",
            "输入短信验证码",
            "6位验证码",
            "6 位验证码",
        ):
            if needle in src:
                return True
        for xp in (
            '//*[@content-desc="请输入验证码"]',
            '//*[contains(@content-desc,"请输入验证码")]',
        ):
            try:
                for el in self.driver.find_elements(AppiumBy.XPATH, xp)[:8]:
                    if el and self._is_displayed(el):
                        return True
            except Exception:
                pass
        return False

    def _bounds_center_for_content_desc_in_page_source(
        self, src: str, exact_desc: str
    ) -> Optional[Tuple[int, int]]:
        """
        从 Appium page_source（层级 XML）中解析带指定 content-desc 的节点 bounds 中心点。
        与 Inspector 一致，例如 bounds=\"[48,871][1034,1038]\" -> 中心 (~541,954)。
        """
        needle = f'content-desc="{exact_desc}"'
        pos = 0
        while True:
            idx = src.find(needle, pos)
            if idx < 0:
                return None
            start = src.rfind("<", 0, idx)
            end = src.find(">", idx)
            if start >= 0 and end > start:
                tag = src[start : end + 1]
                m = re.search(
                    r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
                    tag,
                )
                if m:
                    x1, y1, x2, y2 = (int(m.group(i)) for i in range(1, 5))
                    return ((x1 + x2) // 2, (y1 + y2) // 2)
            pos = idx + len(needle)
        return None

    def _all_bounds_centers_for_content_desc_in_page_source(
        self, src: str, exact_desc: str
    ) -> list[Tuple[int, int, int, int, int, int]]:
        """
        同一 content-desc 在 Flutter 树里可能出现多处（例如底部文案与顶部分段重名）。
        返回 [(cx, cy, y1, y2, x1, x2), ...]，不排序。
        """
        needle = f'content-desc="{exact_desc}"'
        pos = 0
        out: list[Tuple[int, int, int, int, int, int]] = []
        while True:
            idx = src.find(needle, pos)
            if idx < 0:
                break
            start = src.rfind("<", 0, idx)
            end = src.find(">", idx)
            if start >= 0 and end > start:
                tag = src[start : end + 1]
                m = re.search(
                    r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
                    tag,
                )
                if m:
                    x1, y1, x2, y2 = (int(m.group(i)) for i in range(1, 5))
                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2
                    out.append((cx, cy, y1, y2, x1, x2))
            pos = idx + len(needle)
        return out

    def _pick_topmost_tab_like_bounds_center(
        self,
        src: str,
        exact_desc: str,
        screen_h: int,
    ) -> Optional[Tuple[int, int, str]]:
        """
        取该 desc 的 bounds 中**顶边最靠上**且落在「分段 Tab 带」的一条。
        - 严格：y1 < min(0.42*h, 1200)，适配常规顶栏。
        - 放宽：y1 < min(0.63*h+1, 1560)（覆盖 y1≈0.58h～0.62h 的筷子生活大标题页）。
        - 凡选用候选须 cy≤0.56h；过低的中心多为「验证码登录」宽语义块偏右，易等价于点「账号密码」。
        - singleton：仅一处且仍满足 cy≤0.56h。
        - 仍排除屏下半部同名节点。
        返回 (cx, cy, tier) 供日志；无合格候选返回 None。
        """
        if screen_h <= 0:
            return None
        rects = self._all_bounds_centers_for_content_desc_in_page_source(src, exact_desc)
        if not rects:
            return None
        rects.sort(key=lambda t: t[2])
        y_strict = min(int(screen_h * 0.42), 1200)
        # 大标题/插画占顶时 Tab 顶边可在 y1≈0.58h～0.62h；0.58*h 与 y1 相等时「<」仍会拒掉，故用 0.63*h
        y_loose = min(int(screen_h * 0.63) + 1, 1560)
        # 分段行中心不应低于 ~56% 屏高；曾误点 cy≈1455（≈60%）把宽语义右侧「账号密码」激活
        cy_max_tab = int(screen_h * 0.56)
        for cx, cy, y1, y2, x1, x2 in rects:
            if y1 < y_strict and cy <= cy_max_tab:
                return (cx, cy, "strict")
        for cx, cy, y1, y2, x1, x2 in rects:
            if y1 < y_loose and cy <= cy_max_tab:
                return (cx, cy, "loose")
        if len(rects) == 1:
            cx, cy, y1, y2, x1, x2 = rects[0]
            if y1 < int(screen_h * 0.78) and cy <= cy_max_tab:
                return (cx, cy, "singleton")
        logger.info(
            "验证码 Tab：%r 在 page_source 中共 %d 处带 bounds，"
            "顶边 y1 均 >= 放宽上限 %d（屏高 %d），跳过（避免屏下半部误匹配）",
            exact_desc,
            len(rects),
            y_loose,
            screen_h,
        )
        return None

    def _click_sms_captcha_tab_by_page_source_bounds(self) -> bool:
        """
        手机号内层顶部分段「验证码登录」在 Flutter 中常为 android.view.View，find_element 可命中但点击无效。
        用 page_source 里 content-desc 的 bounds 中心点击；须取**屏上靠上**的匹配，避免树里同名节点在屏下半部。
        """
        try:
            src = self.driver.page_source or ""
        except Exception:
            src = ""
        if not src:
            return False
        try:
            h = int(self.driver.get_window_size()["height"])
        except Exception:
            h = 0
        for desc in ("验证码登录", "短信验证码登录"):
            picked = self._pick_topmost_tab_like_bounds_center(src, desc, h)
            if not picked:
                continue
            cx, cy, tier = picked
            logger.info(
                "验证码 Tab：按 page_source bounds 点击中心 (%d,%d) content-desc=%r（tier=%s）",
                cx,
                cy,
                desc,
                tier,
            )
            self._tap_absolute_xy_fallbacks(cx, cy)
            time.sleep(0.75)
            self.handle_popup()
            if self._page_source_indicates_sms_captcha_login_panel():
                logger.info("验证码 Tab：bounds 点击后 page_source 已含发码类语义")
                return True
            if self._get_sms_verification_send_control_visible():
                logger.info("验证码 Tab：bounds 点击后已可见发码控件")
                return True
        # 中心点超 cy_max 未入选时：同一宽矩形内偏左点击（验证码一般在左半段）
        try:
            src2 = self.driver.page_source or ""
        except Exception:
            src2 = ""
        if src2 and h > 0:
            rects2 = self._all_bounds_centers_for_content_desc_in_page_source(
                src2, "验证码登录"
            )
            rects2.sort(key=lambda t: t[2])
            y_cap = min(int(h * 0.63) + 1, 1560)
            for _cx, cy, y1, y2, x1, x2 in rects2:
                if y1 >= y_cap:
                    continue
                spanx = max(8, x2 - x1)
                lx = max(8, x1 + min(int(spanx * 0.18), spanx // 4))
                # 中心偏下时改点矩形上沿附近，减少点到下半屏「密码」区
                if cy > int(h * 0.56):
                    ty = min(y2 - 6, y1 + max(10, (y2 - y1) // 6))
                else:
                    ty = cy
                logger.info(
                    "验证码 Tab：bounds 左侧偏置点击 (%d,%d)（避免宽语义中心落在账号密码侧）",
                    lx,
                    ty,
                )
                self._tap_absolute_xy_fallbacks(lx, ty)
                time.sleep(0.75)
                self.handle_popup()
                if self._page_source_indicates_sms_captcha_login_panel():
                    return True
                if self._get_sms_verification_send_control_visible():
                    return True
        return False

    def _tap_left_of_account_password_segment_via_page_source(self) -> bool:
        """
        顶部分段右侧为「账号密码」时，在其 bounds 左缘外点击，切回左侧「验证码登录」。
        排除底部 Button「账号密码登录」；依赖 page_source，与 Flutter 是否 export 可点节点无关。
        """
        if self._sms_captcha_tab_switch_verified():
            return True
        try:
            src = self.driver.page_source or ""
            w = int(self.driver.get_window_size()["width"])
            h = int(self.driver.get_window_size()["height"])
        except Exception:
            return False
        if not src or h <= 0:
            return False
        cy_max = int(h * 0.58)
        y_top_max = int(h * 0.62)
        candidates: list[Tuple[int, int, int, int, int]] = []
        for desc, x1, y1, x2, y2 in self._iter_tag_desc_bounds_pairs(src):
            if "账号密码登录" in desc:
                continue
            if desc == "账号密码":
                pass
            elif "账号密码" in desc and "登录" not in desc and len(desc) <= 10:
                pass
            else:
                continue
            cy = (y1 + y2) // 2
            if cy <= cy_max and y1 < y_top_max:
                candidates.append((x1, y1, x2, y2, cy))
        if not candidates:
            return False
        candidates.sort(key=lambda t: t[1])
        x1, y1, x2, y2, cy = candidates[0]
        tap_x = max(8, x1 - min(130, int(w * 0.20)))
        logger.info(
            "验证码 Tab：顶部分段「账号密码」左邻点击 (%d,%d) 以切回验证码侧",
            tap_x,
            cy,
        )
        self._tap_absolute_xy_fallbacks(tap_x, cy)
        time.sleep(0.72)
        self.handle_popup()
        return self._sms_captcha_tab_switch_verified()

    def _tap_absolute_xy_fallbacks(self, x: int, y: int) -> None:
        """部分环境 mobile: clickGesture 对 Flutter 无效；依次 Appium tap / W3C / gesture / adb。"""
        x = max(1, int(x))
        y = max(1, int(y))
        try:
            tap = getattr(self.driver, "tap", None)
            if callable(tap):
                tap([(x, y)], 150)
        except Exception:
            pass
        try:
            actions = ActionChains(self.driver)
            actions.w3c_actions = ActionBuilder(
                self.driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch")
            )
            actions.w3c_actions.pointer_action.move_to_location(x, y)
            actions.w3c_actions.pointer_action.pointer_down()
            actions.w3c_actions.pointer_action.pause(0.08)
            actions.w3c_actions.pointer_action.release()
            actions.perform()
        except Exception:
            pass
        try:
            self.driver.execute_script("mobile: clickGesture", {"x": x, "y": y})
        except Exception:
            pass
        try:
            caps = getattr(self.driver, "capabilities", None) or {}
            udid = caps.get("udid") or caps.get("deviceName")
            cmd = ["adb", "shell", "input", "tap", str(x), str(y)]
            if udid:
                cmd = ["adb", "-s", str(udid), "shell", "input", "tap", str(x), str(y)]
            subprocess.run(cmd, timeout=8, capture_output=True)
        except Exception:
            pass

    def _tap_single_xy_for_flutter_primary(self, x: int, y: int) -> None:
        """
        对同一坐标只投递一次触摸。
        发码按钮若用 _tap_absolute_xy_fallbacks：首击弹出协议层后，后续几击仍落原坐标易点在蒙层上，sheet 刚起即被关掉。
        """
        x = max(1, int(x))
        y = max(1, int(y))
        try:
            self.driver.execute_script("mobile: clickGesture", {"x": x, "y": y})
            return
        except Exception:
            pass
        try:
            tap = getattr(self.driver, "tap", None)
            if callable(tap):
                tap([(x, y)], 150)
                return
        except Exception:
            pass
        try:
            actions = ActionChains(self.driver)
            actions.w3c_actions = ActionBuilder(
                self.driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch")
            )
            actions.w3c_actions.pointer_action.move_to_location(x, y)
            actions.w3c_actions.pointer_action.pointer_down()
            actions.w3c_actions.pointer_action.pause(0.08)
            actions.w3c_actions.pointer_action.release()
            actions.perform()
            return
        except Exception:
            pass
        try:
            caps = getattr(self.driver, "capabilities", None) or {}
            udid = caps.get("udid") or caps.get("deviceName")
            cmd = ["adb", "shell", "input", "tap", str(x), str(y)]
            if udid:
                cmd = ["adb", "-s", str(udid), "shell", "input", "tap", str(x), str(y)]
            subprocess.run(cmd, timeout=8, capture_output=True)
        except Exception:
            pass

    def _handle_popup_after_sms_send_coordinate_tap(self) -> None:
        """
        发码坐标点击后的 handle_popup：协议层刚展开时，safe 版会点「同意/关闭」等，易与动画叠层冲突导致秒关。
        """
        try:
            if getattr(
                self, "_phone_sms_login_active", False
            ) and self._login_protocol_bottom_sheet_visible():
                logger.info(
                    "发码后已出现协议说明层，跳过本轮 handle_popup（避免刚展开时被误关）"
                )
                return
        except Exception:
            pass
        try:
            self.handle_popup()
        except Exception:
            pass

    def _tap_sms_send_cta_by_bounds_only(self) -> bool:
        """
        只按 bounds 点击发码主按钮，不校验是否已进入验证码页。
        用于：首次点「同意」仅收起协议层未真正提交时，再点一次发码让协议重新弹出。
        """
        try:
            src = self.driver.page_source or ""
        except Exception:
            src = ""
        center = self._bounds_center_for_content_desc_in_page_source(
            src, "获取短信验证码"
        )
        if not center:
            for alt in ("发送验证码", "获取验证码", "发送短信验证码", "免费获取验证码"):
                center = self._bounds_center_for_content_desc_in_page_source(src, alt)
                if center:
                    break
        if not center:
            m2 = re.search(
                r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]{0,800}?content-desc="获取短信验证码"',
                src,
                re.DOTALL,
            )
            if m2:
                x1, y1, x2, y2 = (int(m2.group(i)) for i in range(1, 5))
                center = ((x1 + x2) // 2, (y1 + y2) // 2)
        if not center:
            center = self._best_bounds_center_for_sms_cta_from_page_source(src)
        if not center:
            return False
        if self._sms_code_entry_or_sent_step_active():
            return False
        cx, cy = center
        try:
            h = int(self.driver.get_window_size()["height"])
            cy_cap = self._sms_send_gesture_y_max(h, None)
            if cy > cy_cap:
                cy = cy_cap
        except Exception:
            pass
        logger.info("发码：仅重触以再出协议层 bounds 点击 (%d,%d)", cx, cy)
        self._tap_single_xy_for_flutter_primary(cx, cy)
        time.sleep(0.65)
        self._handle_popup_after_sms_send_coordinate_tap()
        return True

    def _click_sms_send_using_page_source_bounds(self) -> bool:
        """用 XML 里的 bounds 中心点击「获取短信验证码」，不依赖元素 location API。"""
        if self._sms_code_entry_or_sent_step_active():
            logger.info("已在验证码相关步骤，跳过 bounds 发码点击")
            return True
        try:
            src = self.driver.page_source or ""
        except Exception:
            src = ""
        center = self._bounds_center_for_content_desc_in_page_source(
            src, "获取短信验证码"
        )
        if not center:
            for alt in ("发送验证码", "获取验证码", "发送短信验证码", "免费获取验证码"):
                center = self._bounds_center_for_content_desc_in_page_source(src, alt)
                if center:
                    break
        if not center:
            m2 = re.search(
                r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]{0,800}?content-desc="获取短信验证码"',
                src,
                re.DOTALL,
            )
            if m2:
                x1, y1, x2, y2 = (int(m2.group(i)) for i in range(1, 5))
                center = ((x1 + x2) // 2, (y1 + y2) // 2)
        if not center:
            center = self._best_bounds_center_for_sms_cta_from_page_source(src)
        if not center:
            return False
        cx, cy = center
        try:
            h = int(self.driver.get_window_size()["height"])
            cy_cap = self._sms_send_gesture_y_max(h, None)
            if cy > cy_cap:
                logger.info(
                    "发码：bounds 中心 y=%d 超过安全上限 %d，改为上限以免点到「账号密码登录」",
                    cy,
                    cy_cap,
                )
                cy = cy_cap
        except Exception:
            pass
        logger.info("发码：按 page_source 解析的 bounds 中心点击 (%d,%d)", cx, cy)
        self._tap_single_xy_for_flutter_primary(cx, cy)
        time.sleep(0.9)
        self._handle_popup_after_sms_send_coordinate_tap()
        # 进入验证码页或出现倒计时/「已发送」等才算成功（避免仅仍停在发码页误判）
        return self._sms_send_or_code_step_likely_active()

    def _sms_send_gesture_y_max(self, h: int, phone_field_bottom: Optional[int] = None) -> int:
        """
        发码紫钮多在屏高中部偏下；再往下是同屏底部的「账号密码登录」链。
        手势 Y 不得超过此上限，否则会误点密码入口（表现为「几秒后变成密码登录」）。
        """
        cap_ratio = int(h * 0.46)
        if phone_field_bottom is not None:
            # 手机号框下约 50–170dp 为主发码区；+200 易落到「账号密码登录」链（尤其长屏）
            cap_et = int(phone_field_bottom) + 168
            return max(120, min(cap_ratio, cap_et, h - 120))
        return max(120, min(cap_ratio, h - 120))

    def _gesture_try_sms_send_primary_cta(self) -> bool:
        """
        Flutter 主操作常为 android.view.View + Semantics，XPath 点不到时用 clickGesture。
        在首个可见手机号输入框下方多档 Y 试探，并用 _sms_send_or_code_step_likely_active 校验是否生效。
        """
        if self._sms_code_entry_or_sent_step_active():
            logger.info("已在验证码相关步骤，跳过发码手势试探")
            return True
        if self._click_sms_send_using_page_source_bounds():
            return True
        try:
            w = int(self.driver.get_window_size()["width"])
            h = int(self.driver.get_window_size()["height"])
        except Exception:
            return False
        cx = max(8, w // 2)
        y_candidates: list = []
        phone_bottom: Optional[int] = None
        vis = self._visible_edittexts_top_to_bottom()
        if vis:
            try:
                loc = vis[0].location
                sz = vis[0].size
                base = int(loc["y"] + sz["height"])
                phone_bottom = base
                for dy in (56, 92, 128, 162):
                    yy = base + dy
                    y_candidates.append(yy)
            except Exception:
                pass
        y_max = self._sms_send_gesture_y_max(h, phone_bottom)
        seen = set()
        for yr in (0.3975, 0.415, 0.432):
            yref = max(10, min(y_max, min(h - 10, int(h * yr))))
            if yref in seen:
                continue
            seen.add(yref)
            try:
                logger.info("发码手势：设计比例参考点 (%d,%d)", cx, yref)
                self._tap_single_xy_for_flutter_primary(cx, yref)
                time.sleep(0.45)
                self._handle_popup_after_sms_send_coordinate_tap()
                if self._sms_send_or_code_step_likely_active():
                    return True
                if self._get_sms_verification_send_control_visible():
                    return True
            except Exception:
                pass
        for y in y_candidates:
            y = max(10, min(y_max, min(h - 10, y)))
            if y in seen:
                continue
            seen.add(y)
            try:
                logger.info("发码手势兜底：主按钮候选区 (%d,%d)", cx, y)
                self._tap_single_xy_for_flutter_primary(cx, y)
                time.sleep(0.45)
                self._handle_popup_after_sms_send_coordinate_tap()
                if self._sms_send_or_code_step_likely_active():
                    return True
                if self._get_sms_verification_send_control_visible():
                    return True
            except Exception:
                continue
        return False

    def _is_default_sms_phone_entry_after_hub(self) -> bool:
        """
        点「手机号码登录/注册」后的**默认验证码入口页**（非先进入账号密码页）。
        Inspector：顶文案「未注册的手机号…」、主区 View content-desc「获取短信验证码」、底部「账号密码登录」。
        Flutter 常把未选中的「账号密码」侧文案留在同一棵树里，不能仅用「请输入密码」子串否定本页；
        仅当屏上已可见两个输入框（手机号+密码）时才视为真·账号密码表单。
        """
        try:
            src = self.driver.page_source or ""
        except Exception:
            src = ""
        if not src:
            return False
        n_vis_et = len(self._visible_edittexts_top_to_bottom())
        pwd_form_visible = n_vis_et >= 2

        if "未注册的手机号" in src:
            if "请输入密码" in src and pwd_form_visible:
                return False
            return True
        if "获取短信验证码" in src:
            if "请输入密码" in src and pwd_form_visible:
                return False
            return True
        if "获取验证码" in src and "获取短信验证码" not in src:
            if "请输入密码" in src and pwd_form_visible:
                return False
            return True
        if "发送验证码" in src or "发送短信验证码" in src:
            if "请输入密码" in src and pwd_form_visible:
                return False
            return True
        return False

    def _tap_left_of_account_password_tab_segment(self) -> bool:
        """
        双 Tab 常见排布：左侧「验证码/短信」、右侧「账号密码」。
        若默认停在账号密码，且文案类定位不到「验证码登录」，则在「账号密码」标签左侧点一掌位置切换。
        """
        xpaths = (
            '//*[@content-desc="账号密码登录"]',
            '//*[contains(@content-desc,"账号密码登录")]',
            '//android.widget.Button[@content-desc="账号密码登录"]',
            '//*[contains(@text,"账号密码登录")]',
            '//*[@text="账号密码"]',
            '//*[contains(@text,"账号密码") and not(contains(@text,"登录"))]',
        )
        for xp in xpaths:
            el = self._find(AppiumBy.XPATH, xp, timeout=2)
            if not el or not self._is_displayed(el):
                continue
            try:
                loc = el.location
                sz = el.size
                h = int(self.driver.get_window_size()["height"])
                cy = int(loc["y"] + sz["height"] / 2)
                # 仅偏上区域参与 Tab 几何切换（部分机型 Tab 在表单上方约一半屏内）
                if cy > int(h * 0.55):
                    continue
                w = int(self.driver.get_window_size()["width"])
                # 在标签矩形左缘再往左点（落在左侧 Tab 上）
                tap_x = max(8, int(loc["x"] - min(140, w * 0.24)))
                self.driver.execute_script("mobile: clickGesture", {"x": tap_x, "y": cy})
                logger.info(
                    "双 Tab 兜底：在「账号密码」标签左侧坐标点击 (%d,%d) 尝试切到验证码登录",
                    tap_x,
                    cy,
                )
                time.sleep(0.7)
                self.handle_popup()
                # 未输号时「获取验证码」可能仍不可见，不能以此判断失败
                return True
            except Exception:
                continue
        return False

    def _tap_right_of_account_password_tab_segment(self) -> bool:
        """若 Tab 排布为左「账号密码」、右「验证码」，在标签右侧点一掌切换。"""
        xpaths = (
            '//*[@content-desc="账号密码登录"]',
            '//*[contains(@content-desc,"账号密码登录")]',
            '//*[contains(@text,"账号密码登录")]',
            '//*[@text="账号密码"]',
        )
        for xp in xpaths:
            el = self._find(AppiumBy.XPATH, xp, timeout=2)
            if not el or not self._is_displayed(el):
                continue
            try:
                loc = el.location
                sz = el.size
                h = int(self.driver.get_window_size()["height"])
                cy = int(loc["y"] + sz["height"] / 2)
                if cy > int(h * 0.55):
                    continue
                w = int(self.driver.get_window_size()["width"])
                tap_x = min(w - 8, int(loc["x"] + sz["width"] + min(140, w * 0.24)))
                self.driver.execute_script("mobile: clickGesture", {"x": tap_x, "y": cy})
                logger.info(
                    "双 Tab 兜底：在「账号密码」标签右侧坐标点击 (%d,%d) 尝试切到验证码登录",
                    tap_x,
                    cy,
                )
                time.sleep(0.7)
                self.handle_popup()
                return True
            except Exception:
                continue
        return False

    def _sms_captcha_tab_switch_verified(self) -> bool:
        """点「验证码登录」等后须出现发码语义/控件，否则视为无效点击（继续兜底）。"""
        if self._page_source_indicates_sms_captcha_login_panel():
            return True
        if self._get_sms_verification_send_control_visible():
            return True
        return False

    def _tap_captcha_tab_in_upper_form(self) -> bool:
        """顶部 Tab 区短文案（避开长句「请输入验证码」）。"""
        try:
            h = int(self.driver.get_window_size()["height"])
            y_max = int(h * 0.48)
            xp = (
                '//*[(contains(@text,"验证码登录") or contains(@text,"短信登录")) '
                'and string-length(@text)<16]'
            )
            for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                if not self._is_displayed(el):
                    continue
                try:
                    if int(el.location.get("y", 9999)) > y_max:
                        continue
                except Exception:
                    continue
                if self._click_element(el):
                    time.sleep(0.65)
                    self.handle_popup()
                    if self._sms_captcha_tab_switch_verified():
                        return True
        except Exception:
            pass
        return False

    def _switch_to_sms_captcha_login_tab(self) -> bool:
        """
        少数版本/主题下手机号页为顶部分段 Tab；若在「账号密码」侧需切回验证码。
        筷子生活默认即验证码页，本方法多数时候因已有「获取短信验证码」而直接返回 True。
        """
        if self._page_source_indicates_sms_captcha_login_panel():
            return True
        if self._get_sms_verification_send_control_visible():
            return True
        locs: Tuple[Locator, ...] = (
            (AppiumBy.ACCESSIBILITY_ID, "验证码登录"),
            (AppiumBy.ACCESSIBILITY_ID, "短信验证码登录"),
            (AppiumBy.XPATH, '//*[@content-desc="验证码登录"]'),
            (AppiumBy.XPATH, '//*[@content-desc="短信验证码登录"]'),
            (AppiumBy.XPATH, '//android.widget.TextView[@text="验证码登录"]'),
            (AppiumBy.XPATH, '//android.widget.TextView[@text="短信验证码登录"]'),
            (AppiumBy.XPATH, '//*[contains(@text,"验证码登录") and not(contains(@text,"账号密码"))]'),
            (AppiumBy.XPATH, '//*[contains(@text,"短信验证码登录")]'),
            (AppiumBy.XPATH, '//*[contains(@text,"短信验证码") and not(contains(@text,"请输入"))]'),
            (AppiumBy.XPATH, '//*[contains(@text,"手机验证码")]'),
            (AppiumBy.XPATH, '//*[contains(@content-desc,"验证码登录")]'),
            (AppiumBy.XPATH, '//*[contains(@content-desc,"短信验证码")]'),
        )
        for by, xp in locs:
            el = self._find(by, xp, timeout=2)
            if el and self._is_displayed(el) and self._click_element(el):
                time.sleep(0.65)
                self.handle_popup()
                if self._sms_captcha_tab_switch_verified():
                    return True
        for sel in (
            'new UiSelector().text("验证码登录")',
            'new UiSelector().text("短信验证码登录")',
            'new UiSelector().textContains("验证码登录")',
            'new UiSelector().descriptionContains("验证码登录")',
            'new UiSelector().textContains("短信验证码")',
            'new UiSelector().descriptionContains("短信验证码")',
        ):
            try:
                e = self.driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, sel)
                if e and self._is_displayed(e) and self._click_element(e):
                    time.sleep(0.65)
                    self.handle_popup()
                    if self._sms_captcha_tab_switch_verified():
                        return True
            except Exception:
                pass
        if self._click_sms_captcha_tab_by_page_source_bounds():
            return True
        if self._tap_captcha_tab_in_upper_form():
            return True
        # 短信登录：先点「账号密码」分段左邻（比点「验证码登录」中心更不易误触右侧密码 Tab）
        if self._phone_sms_login_active:
            if self._tap_left_of_account_password_segment_via_page_source():
                return True
            return self._tap_likely_captcha_segment_tab_coordinate_fallback()
        if self._tap_left_of_account_password_tab_segment():
            return True
        if self._tap_right_of_account_password_tab_segment():
            return True
        return False

    def _tap_likely_captcha_segment_tab_coordinate_fallback(self) -> bool:
        """
        双 Tab 常见「验证码/短信」在左、「账号密码」在右。筷子生活等大标题页须**先**点屏高约 52%～58%、靠左热点，再扫 44%～62%，最后才扫顶区 8%～28%。
        仅在 login_by_phone_sms 流程中启用。禁止点右半屏以免命中「账号密码」分段。
        """
        if self._get_sms_verification_send_control_visible():
            return True
        try:
            w = int(self.driver.get_window_size()["width"])
            h = int(self.driver.get_window_size()["height"])
        except Exception:
            return False
        def _try_grid(
            y_rs: Tuple[float, ...],
            x_rs: Tuple[float, ...],
            x_cap: float,
            phase: str,
        ) -> bool:
            for yr in y_rs:
                y = max(8, int(h * yr))
                for rx in x_rs:
                    x = max(8, min(int(w * x_cap), int(w * rx)))
                    try:
                        self._tap_absolute_xy_fallbacks(x, y)
                        logger.info(
                            "验证码 Tab 坐标兜底 %s (%d,%d) y≈%.0f%% 屏高",
                            phase,
                            x,
                            y,
                            yr * 100.0,
                        )
                        time.sleep(0.45)
                        self.handle_popup()
                        if self._get_sms_verification_send_control_visible():
                            return True
                        if self._page_source_indicates_sms_captcha_login_panel():
                            return True
                    except Exception:
                        continue
            return False

        def _try_hotspots(phase: str, pairs: Tuple[Tuple[float, float], ...]) -> bool:
            for yr, xr in pairs:
                y = max(8, int(h * yr))
                x = max(8, min(w - 8, int(w * xr)))
                try:
                    self._tap_absolute_xy_fallbacks(x, y)
                    logger.info(
                        "验证码 Tab 坐标兜底 %s (%d,%d) y=%.0f%% x=%.0f%%",
                        phase,
                        x,
                        y,
                        yr * 100.0,
                        xr * 100.0,
                    )
                    time.sleep(0.45)
                    self.handle_popup()
                    if self._get_sms_verification_send_control_visible():
                        return True
                    if self._page_source_indicates_sms_captcha_login_panel():
                        return True
                except Exception:
                    continue
            return False

        # 零段：筷子生活常见——大标题下 Tab 约在 52%～58% 屏高、水平约 18%～26%（先于顶区网格，避免日志里长时间只在 y≈8%～30% 空点）
        if _try_hotspots(
            "（热点·大标题下左侧分段）",
            ((0.52, 0.20), (0.54, 0.22), (0.56, 0.18), (0.55, 0.26), (0.53, 0.24)),
        ):
            return True
        # 一段：屏高 44%～62% 左半密扫（与 bounds y1≈0.58h 一致）
        if _try_grid(
            (0.44, 0.47, 0.50, 0.53, 0.56, 0.59, 0.62),
            (0.14, 0.20, 0.26, 0.32),
            0.40,
            "（中段左半·大标题布局）",
        ):
            return True
        # 二段：传统顶栏 Tab（约 8%～28% 屏高，略减格点）
        return _try_grid(
            (0.08, 0.10, 0.12, 0.14, 0.16, 0.18, 0.21, 0.24, 0.27),
            (0.12, 0.18, 0.22, 0.28, 0.15, 0.32, 0.25),
            0.42,
            "（顶区左半）",
        )

    def _find_primary_sms_send_view_element(self):
        """Inspector：主按钮为 android.view.View[@content-desc=\"获取短信验证码\"]，取面积最大者避免误点小节点。"""
        try:
            els = self.driver.find_elements(
                AppiumBy.XPATH,
                '//android.view.View[@content-desc="获取短信验证码"]',
            )
        except Exception:
            els = []
        best = None
        best_area = 0
        for el in els:
            try:
                sz = el.size
                w, h = int(sz.get("width", 0)), int(sz.get("height", 0))
                a = w * h
                if a > best_area:
                    best_area = a
                    best = el
            except Exception:
                continue
        return best

    def _ensure_sms_captcha_login_tab(self) -> bool:
        """验证码登录流程用：切 Tab 后若仍无发送按钮，再试一轮（含几何兜底）。"""
        if self._switch_to_sms_captcha_login_tab():
            return True
        time.sleep(0.4)
        return self._switch_to_sms_captcha_login_tab()

    def _click_send_sms_code_button(self, total_wait_sec: float = 22.0) -> bool:
        """
        输入合法手机号后「获取验证码」才高亮：轮询点击，兼容文案/语义节点差异。
        Flutter 常见为 android.view.View + content-desc，需补充 XPath / 手势兜底。
        """
        send_locs: Tuple[Locator, ...] = (
            (AppiumBy.ACCESSIBILITY_ID, "获取短信验证码"),
            (AppiumBy.XPATH, '//android.view.View[@content-desc="获取短信验证码"]'),
            (AppiumBy.XPATH, '//android.view.View[contains(@content-desc,"获取短信验证码")]'),
            (AppiumBy.XPATH, '//*[@content-desc="获取短信验证码"]'),
            (
                AppiumBy.XPATH,
                '//*[contains(@text,"获取短信验证码") or contains(@text,"获取验证码") '
                'or contains(@text,"获取短信") or contains(@text,"发送验证码") '
                'or contains(@text,"免费获取验证码") or contains(@text,"重获验证码")]',
            ),
            (
                AppiumBy.XPATH,
                '//*[contains(@content-desc,"获取短信验证码") or contains(@content-desc,"获取验证码") '
                'or contains(@content-desc,"发送验证码") or contains(@content-desc,"免费获取")]',
            ),
            (
                AppiumBy.XPATH,
                '//*[@clickable="true" and contains(@content-desc,"获取") and contains(@content-desc,"验证")]',
            ),
            (
                AppiumBy.XPATH,
                '//*[@clickable="true" and contains(@content-desc,"短信") and contains(@content-desc,"验证")]',
            ),
            (
                AppiumBy.XPATH,
                '//android.view.View[@clickable="true" and contains(@content-desc,"验证")]',
            ),
            (
                AppiumBy.XPATH,
                '//*[@clickable="true" and (contains(@content-desc,"获取短信") or contains(@content-desc,"发送短信"))]',
            ),
            (
                AppiumBy.XPATH,
                '//*[contains(@resource-id,"feifubao") and contains(@resource-id,"sms") '
                'and (@clickable="true" or self::android.widget.Button or self::android.widget.TextView)]',
            ),
            (
                AppiumBy.XPATH,
                '//*[contains(@resource-id,"feifubao") and (contains(@resource-id,"code") or contains(@resource-id,"verify")) '
                'and (@clickable="true" or self::android.widget.Button)]',
            ),
            (
                AppiumBy.XPATH,
                '//*[@resource-id and contains(@resource-id,"sms") and (self::android.widget.Button or self::android.widget.TextView)]',
            ),
            (
                AppiumBy.XPATH,
                '//*[@resource-id and contains(@resource-id,"code") and contains(@resource-id,"send")]',
            ),
        )
        uia_sels = (
            'new UiSelector().className("android.view.View").description("获取短信验证码")',
            'new UiSelector().description("获取短信验证码")',
            'new UiSelector().descriptionContains("获取短信验证码")',
            'new UiSelector().descriptionContains("获取验证码")',
            'new UiSelector().textContains("获取短信验证码")',
            'new UiSelector().textContains("获取验证码")',
            'new UiSelector().textContains("发送验证码")',
            'new UiSelector().descriptionContains("发送验证码")',
            'new UiSelector().descriptionContains("短信验证")',
            'new UiSelector().textContains("短信验证")',
            'new UiSelector().className("android.view.View").descriptionContains("验证码")',
            'new UiSelector().clickable(true).descriptionContains("获取")',
        )
        if self._sms_code_entry_or_sent_step_active():
            logger.info("已在验证码相关步骤，跳过整段「获取短信验证码」轮询与手势")
            return True
        deadline = time.time() + total_wait_sec
        n = 0
        while time.time() < deadline:
            n += 1
            if self._sms_code_entry_or_sent_step_active():
                logger.info("发码轮询中检测到已进入验证码步骤，停止点击发码")
                return True
            if self._phone_sms_login_active:
                self._try_agree_user_protocol_password_page(footer_only=True)
            else:
                self._try_agree_user_protocol_password_page()
            self.handle_popup()
            if self._click_sms_send_using_page_source_bounds():
                return True
            pv = self._find_primary_sms_send_view_element()
            if pv and self._click_element(pv):
                return True
            for sel in uia_sels:
                try:
                    el = self.driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, sel)
                    if el and self._click_element(el):
                        return True
                except Exception:
                    pass
            for by, xp in send_locs:
                try:
                    for el in self._find_all_now(by, xp):
                        if self._is_displayed(el) and self._click_element(el):
                            return True
                    for el in self._find_all_now(by, xp):
                        if self._click_element(el):
                            return True
                except Exception:
                    pass
            if (
                self._phone_sms_login_active
                and n % 7 == 0
                and self._phone_sms_should_attempt_switch_to_captcha_tab()
            ):
                self._ensure_sms_captcha_login_tab()
                self._tap_likely_captcha_segment_tab_coordinate_fallback()
                time.sleep(0.35)
                self.handle_popup()
            time.sleep(0.45)
        if self._sms_code_entry_or_sent_step_active():
            logger.info("发码轮询结束：当前已在验证码相关步骤，不再做末尾手势兜底")
            return True
        if self._phone_sms_login_active:
            self._try_agree_user_protocol_password_page(footer_only=True)
        else:
            self._try_agree_user_protocol_password_page()
        self.handle_popup()
        if self._click_sms_send_using_page_source_bounds():
            return True
        if self._gesture_try_sms_send_primary_cta():
            return True
        self._log_sms_login_page_diagnosis()
        return False

    def _is_account_password_input_screen(self) -> bool:
        """
        账号密码登录页（手机号 + 密码两个输入区）。
        真机/混合渲染下占位常在 hint，不一定出现在 text/content-desc，需 page_source 与双 EditText 兜底。
        """
        try:
            src = self.driver.page_source or ""
        except Exception:
            src = ""
        if self._is_default_sms_phone_entry_after_hub():
            return False
        vis_n = len(self._visible_edittexts_top_to_bottom())
        send_markers = (
            "获取短信验证码",
            "获取验证码",
            "发送验证码",
            "发送短信验证码",
        )
        if vis_n < 2 and src and any(m in src for m in send_markers):
            # 树上仍有发码语义、屏上只有一个输入框：多为验证码 Tab，密码文案来自未展示侧
            return False
        if "请输入密码" in src and "请输入手机号" in src:
            # 双 Tab 时两提示常在同一棵树里：必须已可见双框才算账号密码表单，否则勿误判
            if vis_n >= 2:
                return True
            if any(m in src for m in send_markers):
                return False
            # 单框、无发码文案：交给下方「可见的请输入密码」判断
        if "请输入密码" in src and len(self._visible_edittexts_top_to_bottom()) >= 2:
            return True
        for xp in (
            '//*[contains(@text,"请输入密码")]',
            '//*[contains(@content-desc,"请输入密码")]',
            '//*[contains(@hint,"请输入密码")]',
        ):
            el = self._find(AppiumBy.XPATH, xp, timeout=1)
            if el and self._is_displayed(el):
                return True
        return False

    def _is_inner_layer_phone_login_screen(self) -> bool:
        """
        已离开登录聚合页、进入「手机号码登录/注册」后的内层（验证码/密码 Tab 同页）。
        与仅含微信/QQ/手机入口按钮的聚合页区分。
        """
        try:
            src = self.driver.page_source or ""
        except Exception:
            src = ""
        if not src or len(src) < 120:
            return False
        if self._page_source_indicates_sms_captcha_login_panel():
            return True
        if (
            "微信账号快捷登录" in src
            and "手机号码登录/注册" in src
            and "请输入手机号" not in src
            and "et_phone" not in src
            and "feifubao:id/et_phone" not in src
        ):
            return False
        if "请输入手机号" in src or "未注册的手机号" in src:
            return True
        if "et_phone" in src or "feifubao:id/et_phone" in src:
            return True
        if "账号密码登录" in src and "EditText" in src:
            return True
        return False

    def _is_phone_verification_entry_screen(self) -> bool:
        """
        手机号验证码登录表单页（非聚合页）：含「获取短信验证码」或底部「账号密码登录」入口。
        若已在密码输入页则不算此页。
        部分版本为 Flutter/custom 控件，优先 XPath，再用 page_source 兜底。
        """
        if self._is_default_sms_phone_entry_after_hub():
            return True
        if self._get_sms_verification_send_control_visible():
            return True
        if self._phone_sms_login_active and self._page_source_indicates_sms_captcha_login_panel():
            return True
        # 短信登录用例：内层页上可能默认停在「账号密码」Tab，树上仍有手机号区，不能先被 _is_account_password 短路掉
        if self._phone_sms_login_active and self._is_inner_layer_phone_login_screen():
            return True
        if self._is_account_password_input_screen():
            return False
        try:
            src = self.driver.page_source or ""
        except Exception:
            src = ""
        if not src:
            src = ""
        _send_in_src = any(
            x in src
            for x in (
                "获取短信验证码",
                "获取验证码",
                "发送验证码",
                "发送短信验证码",
            )
        )
        # 树上含「请输入密码」但上面已排除真·密码页：多为 Flutter 双 Tab 残留文案
        if "请输入密码" in src:
            if _send_in_src:
                return True
            vis_n2 = len(self._visible_edittexts_top_to_bottom())
            if vis_n2 < 2 and (
                "账号密码登录" in src
                or "请输入手机号" in src
                or "未注册的手机号" in src
            ):
                return True
        if "请输入密码" not in src:
            if _send_in_src:
                return True
            if "请输入手机号" in src:
                return True
            if "未注册的手机号" in src:
                return True
            if "账号密码登录" in src:
                return True
            if ("+86" in src or "+63" in src) and "EditText" in src:
                return True
            if "手机号码" in src and "EditText" in src:
                return True

        markers: Tuple[Locator, ...] = (
            (AppiumBy.XPATH, '//*[@content-desc="获取短信验证码"]'),
            (AppiumBy.XPATH, '//*[contains(@content-desc,"获取短信验证码")]'),
            (AppiumBy.XPATH, '//*[contains(@text,"获取短信验证码")]'),
            (AppiumBy.XPATH, '//*[contains(@text,"获取验证码")]'),
            (AppiumBy.XPATH, '//*[@content-desc="账号密码登录"]'),
            (AppiumBy.XPATH, '//*[contains(@content-desc,"未注册的手机号")]'),
            (AppiumBy.XPATH, '//*[contains(@content-desc,"自动注册")]'),
            (AppiumBy.XPATH, '//*[contains(@text,"请输入手机号")]'),
            (AppiumBy.XPATH, '//*[contains(@content-desc,"请输入手机号")]'),
            (AppiumBy.XPATH, '//*[contains(@resource-id,"phone") and @class="android.widget.EditText"]'),
            (AppiumBy.XPATH, '//*[contains(@resource-id,"et_phone")]'),
        )
        for by, xp in markers:
            el = self._find(by, xp, timeout=1)
            if el and self._is_displayed(el):
                return True
        return False

    def _navigate_login_hub_to_phone_entry_screen(self) -> bool:
        """
        登录方式分流：
        - 微信/QQ/谷歌：在登录聚合页直接点对应入口即可。
        - 手机号验证码：在聚合页点「手机号码登录/注册」进入本页。
        - 账号密码：必须先进入本页，再点「账号密码登录」（见 login_by_account_password）。

        若当前已在手机号表单页则直接成功。
        若已通过其它路径直接进入账号密码页，则无需再点「手机号码登录/注册」。
        """
        # 先认手机号内层/验证码页（含短信登录流程中停在密码 Tab 的情况）
        if self._is_phone_verification_entry_screen():
            return True
        if self._is_account_password_input_screen():
            logger.info("当前已在账号密码登录页，跳过「手机号码登录/注册」导航")
            return True

        # 聚合页底部「手机号码登录/注册」可能被挡在屏外，先略上滑再点
        self.handle_popup()
        self._swipe_vertical(0.62, 0.38, 450)
        time.sleep(0.45)
        # 聚合页底部「我已阅读并同意…」未勾选时，后续获取验证码会先弹协议层
        self._try_agree_user_protocol_password_page()
        time.sleep(0.35)
        self.handle_popup()

        phone_entry_locs: Tuple[Locator, ...] = (
            (AppiumBy.ACCESSIBILITY_ID, "手机号码登录/注册"),
            (AppiumBy.XPATH, '//*[@content-desc="手机号码登录/注册"]'),
            (AppiumBy.XPATH, '//android.widget.Button[@content-desc="手机号码登录/注册"]'),
            (AppiumBy.XPATH, '//android.widget.ImageView[@content-desc="手机号码登录/注册"]'),
            (AppiumBy.XPATH, '//*[contains(@text,"手机号码登录/注册")]'),
            (AppiumBy.XPATH, '//android.widget.TextView[contains(@text,"手机号码登录")]'),
            (AppiumBy.XPATH, '//*[contains(@text,"手机号码登录")]'),
        )

        def _try_click_phone_entry() -> bool:
            for by, xp in phone_entry_locs:
                el = self._find(by, xp, timeout=5)
                if el and self._is_displayed(el) and self._click_element(el):
                    return True
            try:
                el2 = self.driver.find_element(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    'new UiSelector().descriptionContains("手机号码登录")',
                )
                if el2 and self._click_element(el2):
                    return True
            except Exception:
                pass
            try:
                el3 = self.driver.find_element(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    'new UiSelector().textContains("手机号码登录")',
                )
                if el3 and self._click_element(el3):
                    return True
            except Exception:
                pass
            return False

        def _wait_until_phone_screen(total_sec: float) -> bool:
            """
            点击「手机号码登录/注册」后：筷子生活等包默认进**验证码登录页**；
            若用户或旧版落在账号密码表单，也视为导航成功以便后续分流。
            """
            end_t = time.time() + total_sec
            last_popup = 0.0
            while time.time() < end_t:
                if time.time() - last_popup >= 2.0:
                    self.handle_popup()
                    last_popup = time.time()
                if self._is_phone_verification_entry_screen():
                    if self._is_default_sms_phone_entry_after_hub():
                        logger.info(
                            "点击「手机号码登录/注册」后已进入默认「手机号验证码登录」页（接着脚本将输手机号并获取验证码）"
                        )
                    else:
                        logger.info(
                            "点击「手机号码登录/注册」后已进入手机号登录页（按验证码流程继续）"
                        )
                    return True
                if self._is_account_password_input_screen():
                    if self._phone_sms_login_active:
                        logger.info(
                            "点击「手机号码登录/注册」后已进入手机号登录内层页（短信登录将优先验证码侧）"
                        )
                    elif self._should_switch_from_password_to_sms_tab_for_captcha_login():
                        logger.info(
                            "点击「手机号码登录/注册」后检测到账号密码 Tab，短信流程将尝试切回验证码侧"
                        )
                    else:
                        logger.info(
                            "点击「手机号码登录/注册」后已进入手机号登录内层页（默认验证码流程，不切 Tab）"
                        )
                    return True
                time.sleep(0.4)
            return False

        if not _try_click_phone_entry():
            logger.error(
                "未找到「手机号码登录/注册」入口（应在登录聚合页点击，进入手机号页）"
            )
            return False

        self.handle_popup()
        time.sleep(1.2)
        if _wait_until_phone_screen(24):
            return True

        logger.warning(
            "[WARN] 首次进入手机号页超时（可能被协议/蒙层挡住），将再点一次并延长等待"
        )
        self.handle_popup()
        time.sleep(0.6)
        _try_click_phone_entry()
        self.handle_popup()
        time.sleep(1.0)
        if _wait_until_phone_screen(18):
            return True

        self._log_phone_verification_diagnostic()
        logger.error(
            "[ERR] 点击「手机号码登录/注册」后仍未识别到「手机号验证页」或「账号密码页」"
        )
        return False

    def _log_phone_verification_diagnostic(self) -> None:
        """识别失败时打 page_source 关键词，便于对照真机改版。"""
        try:
            src = self.driver.page_source or ""
        except Exception:
            src = ""
        keys = (
            "微信账号快捷登录",
            "手机号码登录",
            "获取短信验证码",
            "请输入手机号",
            "账号密码登录",
            "请输入密码",
            "未注册的手机号",
        )
        hits = [k for k in keys if k in src]
        logger.warning(
            "[诊断] 手机号页识别失败：page_source 命中关键词：%s，长度=%d",
            ", ".join(hits) if hits else "(无)",
            len(src),
        )

    def _phone_sms_should_attempt_switch_to_captcha_tab(self) -> bool:
        """
        短信登录专用：仅当较确定当前在「账号密码」Tab 时才执行切回验证码的点击/坐标兜底。
        默认验证码 Tab 若因 Flutter 未导出发码文案而误判，再切 Tab 会把用户推到密码侧。
        """
        if not self._phone_sms_login_active:
            return False
        return self._should_switch_from_password_to_sms_tab_for_captcha_login()

    def _should_switch_from_password_to_sms_tab_for_captcha_login(self) -> bool:
        """
        点「手机号码登录/注册」后产品默认即手机号验证码流程，不应凭树里残留文案去乱切 Tab。
        仅当屏上已明确出现密码输入区（双输入框或可见「请输入密码」）且仍无发码入口时，才尝试切回验证码侧。
        """
        if self._get_sms_verification_send_control_visible():
            return False
        if self._is_default_sms_phone_entry_after_hub():
            return False
        vis_n = len(self._visible_edittexts_top_to_bottom())
        pwd_field_visible = False
        if vis_n >= 2:
            pwd_field_visible = True
        else:
            for xp in (
                '//*[contains(@hint,"请输入密码")]',
                '//*[contains(@content-desc,"请输入密码")]',
                '//*[contains(@text,"请输入密码")]',
            ):
                el = self._find(AppiumBy.XPATH, xp, timeout=1)
                if el and self._is_displayed(el):
                    pwd_field_visible = True
                    break
        if not pwd_field_visible:
            return False
        return self._is_account_password_input_screen()

