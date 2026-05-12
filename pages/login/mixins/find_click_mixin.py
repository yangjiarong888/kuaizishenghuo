"""查找、点击、输入、协议层与密码页主按钮等（依赖 LoginSemanticsMixin 提供 _get_page_source）。"""
from __future__ import annotations

import os
import re
import time
import subprocess
from typing import Iterable, Optional, Tuple

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.common.actions import interaction

from appium.webdriver.common.appiumby import AppiumBy

from commons.logger import setup_logger

from pages.login.constants import HOME_H5_TRAP_RES_ID_MARKERS
from pages.login.data import Locator

logger = setup_logger("pages.login")

class LoginFindClickMixin:

    @staticmethod
    def _resource_id_looks_like_home_h5_trap(rid: Optional[str]) -> bool:
        if not rid:
            return False
        r = rid.lower()
        return any(m in r for m in HOME_H5_TRAP_RES_ID_MARKERS)

    def _element_in_home_h5_trap_zone(self, el) -> bool:
        """元素自身或任意祖先 resource-id 命中 Banner / 今日汇率容器时视为易进 H5 区。"""
        try:
            rid = el.get_attribute("resource-id") or ""
        except Exception:
            rid = ""
        if self._resource_id_looks_like_home_h5_trap(rid):
            return True
        try:
            anc = el.find_elements(
                AppiumBy.XPATH,
                "./ancestor::*[contains(@resource-id,'banner_middle') or "
                "contains(@resource-id,'ll_exchange_rate')]",
            )
            return len(anc) > 0
        except Exception:
            return False

    # ============ 通用工具 ============
    def _find(self, by: str, value: str, timeout: Optional[int] = None):
        try:
            return WebDriverWait(self.driver, timeout or 20).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            return None
        except WebDriverException as e:
            # 设备 offline、USB 断开、UiAutomator2 代理 8201 拒绝等会抛此类异常，
            # 若只捕获 TimeoutException 会导致整脚本 Traceback 退出。
            msg = (getattr(e, "msg", None) or str(e))[:240]
            if any(
                k in msg
                for k in (
                    "ECONNREFUSED",
                    "device offline",
                    "not running",
                    "socket hang up",
                    "Could not proxy command",
                )
            ):
                logger.warning(
                    "WebDriver 已断开或设备不可用（%s）。请：重插 USB / 无线调试重连；"
                    "执行 adb kill-server && adb start-server && adb devices；"
                    "确认 Appium 与手机端 UiAutomator2 正常。",
                    msg,
                )
            return None

    def _find_all_now(self, by: str, value: str) -> list:
        try:
            return self.driver.find_elements(by, value)
        except Exception:
            return []

    def _click(self, loc: Locator, timeout: Optional[int] = None) -> bool:
        by, value = loc
        try:
            el = WebDriverWait(self.driver, timeout or 20).until(
                EC.element_to_be_clickable((by, value))
            )
            el.click()
            return True
        except Exception:
            return False

    def _click_any(self, locs: Iterable[Locator], timeout: Optional[int] = None) -> bool:
        for loc in locs:
            if self._click(loc, timeout=timeout):
                return True
        return False

    @staticmethod
    def _is_displayed(el) -> bool:
        try:
            return el is not None and el.is_displayed()
        except Exception:
            return False

    def _find_first(self, locs: Iterable[Locator], timeout: Optional[int] = None):
        """按顺序尝试多个定位器，返回第一个出现的元素。"""
        for by, value in locs:
            el = self._find(by, value, timeout=timeout)
            if el:
                return el
        return None

    @staticmethod
    def _env_float_positive(name: str) -> float:
        raw = (os.environ.get(name) or "").strip()
        if not raw:
            return 0.0
        try:
            return max(0.0, float(raw))
        except ValueError:
            return 0.0

    def _arm_post_login_click_gesture_suppress(self) -> None:
        sec = self._env_float_positive("POST_LOGIN_SUPPRESS_CLICKGESTURE_SEC")
        if sec <= 0:
            self._suppress_click_gesture_until = 0.0
            return
        self._suppress_click_gesture_until = time.time() + sec
        logger.info(
            "POST_LOGIN_SUPPRESS_CLICKGESTURE_SEC=%.1f：至该时刻前 _click_element 不使用 clickGesture 坐标兜底（仍保留 click/父节点）",
            sec,
        )

    def _click_gesture_suppressed_for_post_login(self) -> bool:
        return time.time() < float(getattr(self, "_suppress_click_gesture_until", 0.0) or 0.0)

    def _click_element(self, el) -> bool:
        """
        对可能 clickable=false 的节点尝试点击（含父级、元素中心手势）。

        为了定位「误点 Banner 进入 H5/WebView」：
        - 设环境变量 TRACE_CLICK_TO_WEBVIEW=1：若一次点击后 Activity 切到 webview* 或 page_source 出现大量 WebView，
          会把被点击元素的 class/resource-id/content-desc/text/rect 打到日志中，方便精确锁定是哪一次点击触发。
        """
        if not el:
            return False
        allow_trap = os.environ.get("ALLOW_HOME_H5_TRAP_CLICKS", "").strip().lower() in (
            "1",
            "true",
            "yes",
            "y",
        )
        if not allow_trap and self._element_in_home_h5_trap_zone(el):
            try:
                trap_rid = el.get_attribute("resource-id")
            except Exception:
                trap_rid = "?"
            logger.warning(
                "[SKIP] 不点击首页易进 H5 区域（新店专享 Banner / 今日汇率等）：resource-id=%s；"
                "确有需要可设 ALLOW_HOME_H5_TRAP_CLICKS=1",
                trap_rid,
            )
            return False
        trace = os.environ.get("TRACE_CLICK_TO_WEBVIEW", "").strip().lower() in (
            "1",
            "true",
            "yes",
            "y",
        )
        before_act = ""
        if trace:
            try:
                before_act = (getattr(self.driver, "current_activity", "") or "")
            except Exception:
                before_act = ""

        def _after_click_trace() -> None:
            if not trace:
                return
            try:
                after_act = (getattr(self.driver, "current_activity", "") or "")
            except Exception:
                after_act = ""
            try:
                src = self.driver.page_source or ""
            except Exception:
                src = ""
            wv_n = src.count("android.webkit.WebView")
            act_l = (after_act or "").lower()
            if ("webview" in act_l) or (wv_n >= 2):
                try:
                    rid = el.get_attribute("resource-id")
                except Exception:
                    rid = None
                try:
                    cd = el.get_attribute("content-desc")
                except Exception:
                    cd = None
                try:
                    txt = el.text
                except Exception:
                    txt = None
                try:
                    cls = el.get_attribute("className") or el.get_attribute("class")
                except Exception:
                    cls = None
                try:
                    r = el.rect
                except Exception:
                    r = None
                logger.warning(
                    "[TRACE_CLICK_TO_WEBVIEW] 点击后疑似进入 WebView/H5：%s -> %s | WebView节点=%s | "
                    "class=%s resource-id=%s content-desc=%s text=%s rect=%s",
                    before_act,
                    after_act,
                    wv_n,
                    cls,
                    rid,
                    cd,
                    txt,
                    r,
                )
        try:
            el.click()
            time.sleep(0.25)
            _after_click_trace()
            return True
        except Exception:
            pass
        try:
            parent = el.find_element(AppiumBy.XPATH, "..")
            if parent:
                if not allow_trap and self._element_in_home_h5_trap_zone(parent):
                    try:
                        prid = parent.get_attribute("resource-id")
                    except Exception:
                        prid = "?"
                    logger.warning(
                        "[SKIP] 不点击父节点：落在首页易进 H5 区域（Banner/今日汇率）resource-id=%s",
                        prid,
                    )
                else:
                    parent.click()
                    time.sleep(0.25)
                    _after_click_trace()
                    return True
        except Exception:
            pass
        if self._click_gesture_suppressed_for_post_login():
            logger.debug(
                "[SKIP] POST_LOGIN 抑制窗口内跳过 clickGesture（POST_LOGIN_SUPPRESS_CLICKGESTURE_SEC）"
            )
            return False
        try:
            loc = el.location
            size = el.size
            x = int(loc["x"] + size["width"] / 2)
            y = int(loc["y"] + size["height"] / 2)
            self.driver.execute_script("mobile: clickGesture", {"x": x, "y": y})
            time.sleep(0.25)
            _after_click_trace()
            return True
        except Exception:
            return False

    def _type(self, by: str, value: str, text: str, timeout: Optional[int] = None) -> bool:
        try:
            el = self._find(by, value, timeout=timeout)
            if not el:
                return False
            try:
                el.click()
            except Exception:
                pass
            time.sleep(0.2)
            try:
                el.clear()
            except Exception:
                pass
            el.send_keys(text)
            return True
        except Exception:
            return False

    def _type_into_element(self, el, text: str) -> bool:
        """对已拿到的元素输入（不依赖 XPath 二次查找）。"""
        if not el:
            return False
        try:
            try:
                el.click()
            except Exception:
                pass
            time.sleep(0.25)
            try:
                el.clear()
            except Exception:
                pass
            el.send_keys(text)
            return True
        except Exception:
            return False

    def _visible_edittexts_top_to_bottom(self) -> list:
        """当前屏可见的 EditText，按从上到下排序（密码页多为第 1 个手机号、第 2 个密码）。"""
        try:
            els = self.driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.EditText")
        except Exception:
            return []
        scored = []
        for e in els:
            try:
                if not self._is_displayed(e):
                    continue
                loc = e.location
                scored.append((int(loc.get("y", 0)), e))
            except Exception:
                continue
        scored.sort(key=lambda t: t[0])
        return [t[1] for t in scored]

    def _fill_password_login_form(self, account: str, password: str) -> Tuple[bool, bool]:
        """
        账号密码登录页输入。Flutter 页优先按可见 EditText 顺序；
        失败再短超时遍历 resource-id（避免每个定位器 8s 串行拖成数分钟）。
        """
        account_locs: Tuple[Locator, ...] = (
            (AppiumBy.ID, "com.bs.feifubao:id/et_phone"),
            (AppiumBy.ID, "com.ba.feifubao:id/et_phone"),
            (AppiumBy.ID, "com.bs.feifubao:id/et_account"),
            (AppiumBy.ID, "com.ba.feifubao:id/et_account"),
            (AppiumBy.XPATH, '//*[contains(@resource-id,"et_phone") and @class="android.widget.EditText"]'),
            (AppiumBy.XPATH, '//*[contains(@resource-id,"et_account") and @class="android.widget.EditText"]'),
            (AppiumBy.XPATH, '//*[contains(@resource-id,"phone") and @class="android.widget.EditText"]'),
            (AppiumBy.XPATH, '//*[contains(@content-desc,"请输入手机号")]'),
            (AppiumBy.XPATH, '//*[contains(@text,"请输入手机号")]/following::android.widget.EditText[1]'),
            (AppiumBy.XPATH, '(//android.widget.EditText)[1]'),
        )
        pwd_locs: Tuple[Locator, ...] = (
            (AppiumBy.ID, "com.bs.feifubao:id/et_password"),
            (AppiumBy.ID, "com.ba.feifubao:id/et_password"),
            (AppiumBy.XPATH, '//*[contains(@resource-id,"et_password") and @class="android.widget.EditText"]'),
            (AppiumBy.XPATH, '//*[contains(@resource-id,"password") and @class="android.widget.EditText"]'),
            (AppiumBy.XPATH, '//*[contains(@content-desc,"请输入密码")]'),
            (AppiumBy.XPATH, '//*[contains(@text,"请输入密码")]/following::android.widget.EditText[1]'),
            (AppiumBy.XPATH, '(//android.widget.EditText)[2]'),
        )

        account_ok = False
        pwd_ok = False
        vis = self._visible_edittexts_top_to_bottom()
        if len(vis) >= 2:
            account_ok = self._type_into_element(vis[0], account)
            pwd_ok = self._type_into_element(vis[1], password)
        elif len(vis) == 1:
            account_ok = self._type_into_element(vis[0], account)
            time.sleep(0.35)
            vis2 = self._visible_edittexts_top_to_bottom()
            if len(vis2) >= 2:
                pwd_ok = self._type_into_element(vis2[1], password)

        short_wait = 2
        if not account_ok:
            account_ok = any(
                self._type(by, xp, account, timeout=short_wait)
                for by, xp in account_locs
            )
        if not pwd_ok:
            pwd_ok = any(
                self._type(by, xp, password, timeout=short_wait) for by, xp in pwd_locs
            )

        if not account_ok or not pwd_ok:
            vis3 = self._visible_edittexts_top_to_bottom()
            logger.info(
                "密码页兜底：按可见 EditText 再试（共 %d 个）",
                len(vis3),
            )
            if len(vis3) >= 1 and not account_ok:
                account_ok = self._type_into_element(vis3[0], account)
            if len(vis3) >= 2 and not pwd_ok:
                pwd_ok = self._type_into_element(vis3[1], password)
            elif len(vis3) == 1 and account_ok and not pwd_ok:
                time.sleep(0.5)
                vis4 = self._visible_edittexts_top_to_bottom()
                if len(vis4) >= 2:
                    pwd_ok = self._type_into_element(vis4[1], password)

        if account_ok:
            logger.info("已写入手机号/账号输入框")
        if pwd_ok:
            logger.info("已写入密码输入框")
        return account_ok, pwd_ok

    def _hide_keyboard_soft(self) -> None:
        """点「登录」前收起键盘，避免挡住主按钮或导致树不可见。"""
        try:
            if hasattr(self.driver, "hide_keyboard"):
                self.driver.hide_keyboard()
        except Exception:
            pass
        try:
            self.driver.execute_script("mobile: hideKeyboard", {})
        except Exception:
            pass

    def _recover_phone_login_if_no_edittext(self, ctx: str) -> None:
        """坐标兜底误触系统 UI/全屏蒙层时，树里可能仍有「登录」但可见 EditText=0。"""
        if len(self._visible_edittexts_top_to_bottom()) > 0:
            return
        src = self._get_page_source()
        if len(src) < 400:
            return
        if "手机号" not in src and "请输入手机号" not in src and "登录" not in src:
            return
        logger.warning(
            "%s：可见 EditText=0，尝试收起键盘并关闭浮层",
            ctx,
        )
        self._hide_keyboard_soft()
        time.sleep(0.35)
        self.handle_popup()
        time.sleep(0.3)
        self.handle_popup()

    def _try_agree_user_protocol_password_page(self, *, footer_only: bool = False) -> None:
        """
        尽量预先勾选协议（登录聚合页底栏、验证码页底栏、账号密码页等）。
        若未勾选，点「登录」或「获取短信验证码」会先出底部说明层，见
        `_dismiss_password_login_protocol_sheet_if_present`。

        footer_only=True：仅处理屏高约 58% 以下的节点。手机号内层页上若全屏点含「同意」的 CheckBox，
        易误点中部分段/Tab，表现为「刚进验证码页又变成密码登录」。
        """
        try:
            h_win = int(self.driver.get_window_size()["height"])
        except Exception:
            h_win = 0
        y_footer = int(h_win * 0.58) if h_win > 0 else 0
        locs: Tuple[Locator, ...] = (
            (AppiumBy.XPATH, '//android.view.View[contains(@content-desc,"我已阅读并同意")]'),
            (AppiumBy.XPATH, '//*[contains(@content-desc,"我已阅读并同意筷子生活")]'),
            (AppiumBy.XPATH, '//*[contains(@text,"我已阅读") or contains(@text,"同意")]'),
            (AppiumBy.XPATH, '//*[contains(@content-desc,"我已阅读") or contains(@content-desc,"同意")]'),
            (AppiumBy.XPATH, '//android.widget.CheckBox'),
            (AppiumBy.XPATH, '//*[contains(@resource-id,"check") or contains(@resource-id,"agree") or contains(@resource-id,"protocol")]'),
        )
        for by, xp in locs:
            try:
                for el in self._find_all_now(by, xp)[:6]:
                    if not self._is_displayed(el):
                        continue
                    if footer_only and h_win > 0:
                        try:
                            ey = int(el.location.get("y", 0))
                        except Exception:
                            ey = 0
                        if ey < y_footer:
                            continue
                    self._click_element(el)
                    time.sleep(0.2)
            except Exception:
                continue

    def _login_protocol_post_agree_strong_signal(self) -> bool:
        """
        协议点「同意」后的成功判定：勿用 _sms_send_or_code_step_likely_active。
        手机号页发码按钮倒计时里也会出现「秒后」「重新获取」等子串，会误判为已进入验证码步骤。
        """
        if self._login_protocol_bottom_sheet_visible():
            return False
        try:
            src = self.driver.page_source or ""
        except Exception:
            src = ""
        if not src:
            return False
        markers = (
            "请输入验证码",
            "输入验证码",
            "填写验证码",
            "验证码已发送",
            "已发送至",
            "短信验证码已发送",
        )
        if any(m in src for m in markers):
            return True
        if "已发送" in src and ("验证码" in src or "短信验证码" in src):
            return True
        return False

    def _login_protocol_agree_transition_observed(
        self, max_wait_sec: float = 3.2
    ) -> bool:
        """
        仅「弹层消失」不够：点在蒙层/空白会收起 sheet 但未真正同意。
        仅用强 page_source 特征轮询，避免与发码倒计时文案冲突。
        """
        deadline = time.time() + max_wait_sec
        while time.time() < deadline:
            if self._login_protocol_post_agree_strong_signal():
                return True
            time.sleep(0.28)
        return False

    def _maybe_reopen_protocol_after_bad_dismiss(self) -> bool:
        """
        产品侧常见：第一次点协议主按钮只收起底部 sheet，未真正「同意并继续」；
        第二次再点同意才进验证码页。此时协议文案已不在树上，需再点一次「获取验证码」弹出协议。
        """
        if self._login_protocol_bottom_sheet_visible():
            return False
        if self._login_protocol_post_agree_strong_signal():
            return False
        tap_fn = getattr(self, "_tap_sms_send_cta_by_bounds_only", None)
        if not callable(tap_fn) or not tap_fn():
            return False
        time.sleep(0.45)
        hp = getattr(self, "handle_popup", None)
        if callable(hp):
            hp()
        if self._login_protocol_bottom_sheet_visible():
            logger.info(
                "协议层误关后已重触发码，协议再次显示，将再点「同意并注册/登录」"
            )
            return True
        return False

    def _dismiss_password_login_protocol_sheet_if_present(
        self, total_wait_sec: float = 3.5
    ) -> bool:
        """
        未勾选用户协议时点「登录」或「获取短信验证码」会弹出底部说明（保障合法权益…），
        需点「同意并注册/登录」才会继续；已同意则无此层。
        """
        locs: Tuple[Locator, ...] = (
            (AppiumBy.ACCESSIBILITY_ID, "同意并注册/登录"),
            (AppiumBy.XPATH, '//android.view.View[@content-desc="同意并注册/登录"]'),
            (AppiumBy.XPATH, '//*[@content-desc="同意并注册/登录"]'),
            (AppiumBy.XPATH, '//*[contains(@content-desc,"同意并注册")]'),
        )
        uia_sels = (
            'new UiSelector().description("同意并注册/登录")',
            'new UiSelector().descriptionContains("同意并注册")',
        )
        deadline = time.time() + total_wait_sec
        tried_bounds_agree_tap = False
        reopen_count = 0
        max_reopen = 4
        while time.time() < deadline:
            misclosed_agree_no_transition = False
            if not tried_bounds_agree_tap and self._login_protocol_bottom_sheet_visible():
                all_rects_fn = getattr(
                    self, "_all_bounds_centers_for_content_desc_in_page_source", None
                )
                bounds_fn = getattr(
                    self, "_bounds_center_for_content_desc_in_page_source", None
                )
                did_bounds_agree = False
                if callable(all_rects_fn):
                    try:
                        src0 = self.driver.page_source or ""
                        rects = all_rects_fn(src0, "同意并注册/登录")
                        if rects:
                            rects.sort(key=lambda t: t[2], reverse=True)
                            _cx, _cy, y1, y2, x1, x2 = rects[0]
                            cx = (x1 + x2) // 2
                            cy_tap = y1 + max(1, int((y2 - y1) * 0.72))
                            tried_bounds_agree_tap = True
                            did_bounds_agree = True
                            self.driver.execute_script(
                                "mobile: clickGesture", {"x": cx, "y": cy_tap}
                            )
                            logger.info(
                                "协议同意：按 bounds 偏下点击（约按钮高 72%%）(%s,%s)",
                                cx,
                                cy_tap,
                            )
                            time.sleep(0.55)
                            if self._login_protocol_agree_transition_observed():
                                return True
                            misclosed_agree_no_transition = True
                            logger.warning(
                                "协议 bounds 点击后未出现强验证码/已发送特征，将尝试其它定位方式"
                            )
                    except Exception:
                        pass
                if not did_bounds_agree and callable(bounds_fn):
                    try:
                        src0 = self.driver.page_source or ""
                        center = bounds_fn(src0, "同意并注册/登录")
                        if center:
                            tried_bounds_agree_tap = True
                            cx, cy = center
                            self.driver.execute_script(
                                "mobile: clickGesture", {"x": cx, "y": cy}
                            )
                            logger.info(
                                "协议同意：按 page_source bounds 中心点击 (%s,%s)",
                                cx,
                                cy,
                            )
                            time.sleep(0.55)
                            if self._login_protocol_agree_transition_observed():
                                return True
                            misclosed_agree_no_transition = True
                            logger.warning(
                                "协议 bounds 点击后未出现强验证码/已发送特征，将尝试其它定位方式"
                            )
                    except Exception:
                        pass
            for sel in uia_sels:
                try:
                    el = self.driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, sel)
                    if el and self._click_element(el):
                        logger.info(
                            "已点击协议弹窗「同意并注册/登录」（获取验证码/登录前未勾选协议时）"
                        )
                        time.sleep(0.55)
                        if self._login_protocol_agree_transition_observed():
                            return True
                        misclosed_agree_no_transition = True
                        logger.warning(
                            "协议弹层点击后未出现发码/验证码页特征，可能点在非主按钮或仅收起弹层，将重试"
                        )
                except Exception:
                    pass
            for by, xp in locs:
                for el in self._find_all_now(by, xp):
                    if self._click_element(el):
                        logger.info(
                            "已点击协议弹窗「同意并注册/登录」（获取验证码/登录前未勾选协议时）"
                        )
                        time.sleep(0.55)
                        if self._login_protocol_agree_transition_observed():
                            return True
                        misclosed_agree_no_transition = True
                        logger.warning(
                            "协议弹层点击后未出现发码/验证码页特征，可能点在非主按钮或仅收起弹层，将重试"
                        )
            if (
                reopen_count < max_reopen
                and misclosed_agree_no_transition
                and not self._login_protocol_bottom_sheet_visible()
                and not self._login_protocol_post_agree_strong_signal()
            ):
                if self._maybe_reopen_protocol_after_bad_dismiss():
                    reopen_count += 1
                    tried_bounds_agree_tap = False
                    continue
            time.sleep(0.35)
        if self._login_protocol_bottom_sheet_visible():
            logger.info("协议弹层仍在，尝试底部主按钮区点击手势（Flutter View 偶发 el.click 无效）")
            try:
                win = self.driver.get_window_size()
                w, h = int(win["width"]), int(win["height"])
            except Exception:
                w = h = 0
            if w > 100 and h > 100:
                for ry in (0.905, 0.875, 0.84, 0.92):
                    try:
                        x, y = int(w * 0.5), int(h * ry)
                        self.driver.execute_script("mobile: clickGesture", {"x": x, "y": y})
                        time.sleep(0.55)
                        if not self._login_protocol_bottom_sheet_visible():
                            if self._login_protocol_agree_transition_observed():
                                logger.info(
                                    "手势兜底已关闭协议弹层（屏心 x=%s y_ratio=%.3f）",
                                    x,
                                    ry,
                                )
                                return True
                            logger.warning(
                                "手势后弹层消失但未进入发码/验证码步骤，可能点在蒙层空白，继续尝试其它 y"
                            )
                    except Exception:
                        continue
        return False

    def _login_protocol_bottom_sheet_visible(self) -> bool:
        """
        点 QQ/微信等第三方登录前若未勾选协议，会出现底部说明层（保障合法权益… + 同意并注册/登录）。
        与包名/WebView 无关，但说明「入口点击已生效」。
        """
        try:
            src = self.driver.page_source or ""
        except Exception:
            src = ""
        if len(src) < 80:
            return False
        if "为保障您的合法权益" in src:
            return True
        if "不同意" in src and ("同意并注册" in src or "同意并登录" in src):
            return True
        try:
            for el in self.driver.find_elements(
                AppiumBy.XPATH, '//*[@content-desc="同意并注册/登录"]'
            )[:5]:
                if el and self._is_displayed(el):
                    return True
        except Exception:
            pass
        try:
            e2 = self.driver.find_element(AppiumBy.ACCESSIBILITY_ID, "同意并注册/登录")
            if e2 and self._is_displayed(e2):
                return True
        except Exception:
            pass
        return False

    def _try_click_password_login_element(self, el) -> bool:
        """Flutter 等混合渲染下节点常在树里但 is_displayed=False，仍应尝试点击。"""
        if not el:
            return False
        return self._click_element(el)

    def _password_login_button_candidates_by_y(self, by: str, value: str) -> list:
        """同一 XPath 可能命中多个「登录」语义节点，优先点屏幕偏下的主按钮。"""
        try:
            els = self.driver.find_elements(by, value)
        except Exception:
            return []
        scored = []
        for e in els:
            try:
                y = int(e.location.get("y", 0))
                scored.append((y, e))
            except Exception:
                scored.append((0, e))
        scored.sort(key=lambda t: t[0], reverse=True)
        return [t[1] for t in scored]

    def _password_login_interstitial_masquerades_as_left_password(self) -> bool:
        """
        误触运营/H5 等全屏页时，密码表单也会从树里消失，若仅判断「已离开密码页」会误判为「登录已提交」。
        这些 Activity 与手点真·登录后进首页的路径不一致，不得当作登录成功信号。
        """
        act = self._current_activity_lower()
        return any(
            m in act
            for m in (
                "webviewcomprehensive",
                "webviewh5news",
                "festivalsdetail",
                "festivaldetail",
                "promotiondetail",
                "activitydetail",
            )
        )

    def _password_login_submit_effect_detected(self) -> bool:
        """
        真机/Flutter 下偶现：手势或 click 已生效，但 WebDriver 抛错或 _click_element 返回 False。

        运营 H5 常**晚一拍**才切到 WebViewComprehensiveActivity：首帧「离开密码表单」不足以认定登录成功，
        否则会误判并带着全屏 WebView 去做首页断言。

        仅当：已见首页「充值缴费+头条」，或离开密码页后经短等待确认 MainActivity / 首页特征，
        且**不是**已知 H5 壳、**不是**「满屏 WebView 却无金刚区」时，才视为登录已提交。
        """
        # 先看正向信号：首页特征命中才可直接判定
        if self._home_logged_in_quick_check(loc_timeout=2):
            return True

        # 已知运营/H5 壳：直接判定为未成功触发登录
        if self._password_login_interstitial_masquerades_as_left_password():
            logger.info(
                "密码页：当前 Activity=%s 为运营/H5 类壳页，不视作「已触发登录」，继续尝试显式点击登录",
                getattr(self.driver, "current_activity", "?"),
            )
            return False

        # 过去“离开密码页就算成功”会误判。现在改为：离开后等待并只认可强正向信号。
        if self._is_account_password_input_screen():
            return False

        time.sleep(2.2)
        if self._password_login_interstitial_masquerades_as_left_password():
            logger.info(
                "密码页：短暂等待后 Activity=%s 为运营/H5 壳页，不视作「已触发登录」",
                getattr(self.driver, "current_activity", "?"),
            )
            return False

        try:
            src = self.driver.page_source or ""
        except Exception:
            src = ""
        wv_n = src.count("android.webkit.WebView")
        if wv_n >= 2 and "充值缴费" not in src:
            logger.info(
                "密码页：离开后树内 WebView=%s 且无「充值缴费」，疑 H5 壳页，不视作「已触发登录」",
                wv_n,
            )
            return False

        if self._home_logged_in_quick_check(loc_timeout=3):
            return True

        act = self._current_activity_lower()
        if "mainactivity" in act and ("充值缴费" in src or "头条" in src):
            return True

        logger.info(
            "密码页：已离开密码表单，但未命中首页强特征且 Activity=%s，不视作「已触发登录」",
            getattr(self.driver, "current_activity", "?"),
        )
        return False

    def _click_password_page_login_button(self) -> bool:
        """
        密码页主按钮：优先 resource-id（btn_login），再 content-desc / 文案 / UiSelector。
        多轮滑动把底部按钮滚入安全点击区；不依赖「全屏盲坐标」。
        Flutter 下常见 is_displayed=False，故对命中节点一律尝试 _click_element（内含父节点与元素中心手势）。
        若你肉眼看到脚本已点在「登录」上但本函数仍走到底，多半属于 WebDriver 返回值不可靠——
        下方会在每轮后根据页面是否已离开密码表单做兜底判定。
        """
        self._hide_keyboard_soft()
        time.sleep(0.35)

        id_locs: Tuple[Locator, ...] = (
            (AppiumBy.ID, "com.bs.feifubao:id/btn_login"),
            (AppiumBy.ID, "com.ba.feifubao:id/btn_login"),
        )
        xpath_locs: Tuple[Locator, ...] = (
            (AppiumBy.XPATH, '//*[contains(@resource-id,"btn_login")]'),
            (
                AppiumBy.XPATH,
                '//*[@content-desc="登录" and not(contains(@content-desc,"验证码"))]',
            ),
            (AppiumBy.XPATH, '//android.view.View[@content-desc="登录"]'),
            (
                AppiumBy.XPATH,
                '//*[contains(@content-desc,"登录") and not(contains(@content-desc,"验证码"))]',
            ),
            (
                AppiumBy.XPATH,
                '//*[(self::android.widget.Button or self::android.widget.TextView) and @text="登录"]',
            ),
        )
        uia_sels: Tuple[str, ...] = (
            'new UiSelector().resourceId("com.bs.feifubao:id/btn_login")',
            'new UiSelector().resourceId("com.ba.feifubao:id/btn_login")',
            'new UiSelector().description("登录")',
            'new UiSelector().text("登录")',
        )

        swipe_rounds = (
            (0.58, 0.42, 320),
            (0.72, 0.38, 420),
            (0.48, 0.75, 380),
            (0.62, 0.45, 300),
        )

        for round_i, (y0, y1, dur) in enumerate(swipe_rounds):
            self._swipe_vertical(y0, y1, dur)
            time.sleep(0.35 if round_i else 0.22)

            for by, val in id_locs:
                if round_i == 0:
                    try:
                        el = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((by, val))
                        )
                        if self._try_click_password_login_element(el):
                            logger.info(
                                "已点击密码页「登录」（element_to_be_clickable + %s）", val
                            )
                            return True
                    except Exception:
                        pass
                for el in self._password_login_button_candidates_by_y(by, val):
                    if self._try_click_password_login_element(el):
                        logger.info("已点击密码页「登录」（find_elements + %s）", val)
                        return True

            for by, val in xpath_locs:
                for el in self._password_login_button_candidates_by_y(by, val):
                    if self._try_click_password_login_element(el):
                        logger.info("已点击密码页「登录」（XPath 多候选）")
                        return True
                el = self._find(by, val, timeout=2)
                if self._try_click_password_login_element(el):
                    logger.info("已点击密码页「登录」（XPath 单候选）")
                    return True

            try:
                el = self._find(AppiumBy.ACCESSIBILITY_ID, "登录", timeout=2)
                if self._try_click_password_login_element(el):
                    logger.info("已点击密码页「登录」（ACCESSIBILITY_ID）")
                    return True
            except Exception:
                pass

            for sel in uia_sels:
                try:
                    el = self.driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, sel)
                    if self._try_click_password_login_element(el):
                        logger.info("已点击密码页「登录」（UiSelector）")
                        return True
                except Exception:
                    continue

            time.sleep(0.75)
            if self._password_login_submit_effect_detected():
                logger.info(
                    "密码页：本轮已下发点击动作，页面已离开账号密码表单或出现首页特征，"
                    "视作已触发「登录」（避免仅因 WebDriver 未返回成功而判失败）"
                )
                return True

        time.sleep(1.0)
        if self._password_login_submit_effect_detected():
            logger.info(
                "密码页：多轮尝试后页面已跳转，视作已触发「登录」（点击可能已生效但驱动未明确返回成功）"
            )
            return True

        logger.warning(
            "[WARN] 密码页未命中可点击的「登录」控件；请 Inspector 确认 btn_login / content-desc 是否与脚本一致"
        )
        return False

    def _is_app_installed(self, package_name: str) -> bool:
        # Appium python client 通常支持 is_app_installed，但不同版本可能没有
        try:
            if hasattr(self.driver, "is_app_installed"):
                return bool(self.driver.is_app_installed(package_name))
        except Exception:
            pass

        # fallback: adb
        try:
            cp = subprocess.run(
                ["adb", "shell", "pm", "list", "packages", package_name],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return package_name in (cp.stdout or "")
        except Exception:
            return False

    def _wait_foreground_package(self, package_name: str, timeout: float = 12.0) -> bool:
        """轮询当前前台包名（第三方授权前是否已切到微信/QQ 等）。"""
        deadline = time.time() + max(0.5, float(timeout))
        want = (package_name or "").strip()
        if not want:
            return False
        while time.time() < deadline:
            try:
                cur = (getattr(self.driver, "current_package", None) or "").strip()
                if cur == want:
                    return True
            except Exception:
                pass
            time.sleep(0.4)
        return False

    def _wait_foreground_any_package(
        self, package_names: Tuple[str, ...], timeout: float = 12.0
    ) -> Optional[str]:
        """任一包名进入前台即返回该包名，否则返回 None。"""
        deadline = time.time() + max(0.5, float(timeout))
        want = frozenset((p or "").strip() for p in package_names if (p or "").strip())
        if not want:
            return None
        while time.time() < deadline:
            try:
                cur = (getattr(self.driver, "current_package", None) or "").strip()
                if cur in want:
                    return cur
            except Exception:
                pass
            time.sleep(0.4)
        return None
