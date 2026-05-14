"""店铺详情下单流程（TakeoutPageBase 混入）。"""
from __future__ import annotations

import random
import re
import time
from contextlib import nullcontext
from datetime import date, timedelta
import unicodedata
from typing import Any, List, Optional, Sequence, Set, Tuple

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from commons.logger import setup_logger
from pages.takeout_locators import (
    _WEB_REASON_FRAGMENTS,
    _WEB_XPATH_CANCEL_ORDER,
    _WEB_XPATH_CONFIRM_CANCEL,
    _WEB_XPATH_SUBMIT,
    _XPATH_DESC_CART,
    _XPATH_DESC_SELECT_ADDRESS,
    _XPATH_NATIVE_CANCEL_ORDER,
    _XPATH_NATIVE_CONFIRM_CANCEL,
    _XPATH_NATIVE_SUBMIT,
)

logger = setup_logger(__name__)



class TakeoutCancelOrderMixin:

    def _cancel_driver_query_unreliable(self, exc: BaseException) -> bool:
        msg = (getattr(exc, "msg", None) or str(exc)).lower()
        keys = (
            "instrumentation process is not running",
            "cannot be proxied to uiautomator2",
            "socket hang up",
            "could not proxy",
            "connection reset",
            "econnreset",
            "session is either terminated",
        )
        return any(k in msg for k in keys)

    def _switch_context_safe(self, context_name: str) -> bool:
        try:
            cur = getattr(self.driver, "current_context", None)
            if cur == context_name:
                return True
            self.driver.switch_to.context(context_name)
            return True
        except Exception as ex:
            logger.debug("switch_to.context(%s) 失败: %s", context_name, ex)
            return False
    

    def _iter_webview_contexts(self) -> List[str]:
        try:
            return [c for c in (self.driver.contexts or []) if "WEBVIEW" in c.upper()]
        except Exception:
            return []
    

    def _log_contexts(self, stage: str = "") -> None:
        """调试用：打印当前 context 与可用 context 列表。"""
        tag = f"[{stage}] " if stage else ""
        try:
            ctxs = list(self.driver.contexts or [])
        except Exception as ex:
            logger.warning("%s读取 driver.contexts 失败: %s", tag, ex)
            return
        cur = None
        try:
            cur = getattr(self.driver, "current_context", None)
        except Exception:
            cur = None
        webviews = [c for c in ctxs if "WEBVIEW" in str(c).upper()]
        logger.info("%sCONTEXT_CHECK current=%s", tag, cur)
        logger.info("%sCONTEXT_CHECK contexts=%s", tag, ctxs)
        logger.info("%sCONTEXT_CHECK webviews=%s count=%d", tag, webviews, len(webviews))
    

    def _h5_click_element(self, el: Any) -> bool:
        """嵌套 H5 常用：滚入视区 + 普通 click + JS 冒泡点击。"""
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center', behavior:'instant'});",
                el,
            )
            time.sleep(0.12)
        except Exception:
            pass
        try:
            if el.is_displayed():
                el.click()
                time.sleep(0.12)
                return True
        except Exception:
            pass
        try:
            self.driver.execute_script("arguments[0].click();", el)
            time.sleep(0.12)
            return True
        except Exception:
            return False
    

    def _webview_click_first_matching(self, xpaths: Sequence[str]) -> bool:
        for xp in xpaths:
            try:
                for el in self.driver.find_elements(By.XPATH, xp):
                    try:
                        if el.is_displayed() and self._h5_click_element(el):
                            return True
                    except Exception:
                        continue
            except Exception:
                continue
        return False
    

    def _webview_js_click_submit(self) -> bool:
        """
        XPath 点不到时，在 **当前 WebView** 的 document 上找「提交」
        （Vue/React 遮罩、底部 fixed 条等场景）。
        """
        js = r"""
        try {
          var paths = [
            "//button[contains(normalize-space(.),'提交')]",
            "//a[contains(normalize-space(.),'提交')]",
            "//*[normalize-space(.)='提交']"
          ];
          for (var p = 0; p < paths.length; p++) {
            var r = document.evaluate(paths[p], document, null,
              XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
            if (r) {
              r.scrollIntoView({block:'center', behavior:'instant'});
              r.click();
              return true;
            }
          }
        } catch (e) {}
        var tags = ['BUTTON', 'A'];
        for (var t = 0; t < tags.length; t++) {
          var els = document.getElementsByTagName(tags[t]);
          for (var i = 0; i < els.length; i++) {
            var el = els[i];
            var tx = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
            if (tx === '提交') {
              el.scrollIntoView({block: 'center'});
              el.click();
              return true;
            }
          }
        }
        return false;
        """
        try:
            return bool(self.driver.execute_script(js))
        except Exception:
            return False
    

    def _webview_try_submit_in_current_context(self) -> bool:
        if self._webview_click_first_matching(_WEB_XPATH_SUBMIT):
            return True
        if self._webview_js_click_submit():
            logger.info("已点击「提交」（WebView document.evaluate / 文案兜底）")
            return True
        return False
    

    def _tap_native_submit_cancel_sheet(self) -> bool:
        w, h = self._window_size_safe()
        # 底部橙色「提交」多在 ~0.55h 以下；上沿略抬高减少误点列表中部近义文案
        y_min = int(h * 0.55)
        y_max = int(h * 0.93)
        if not self._cancel_reason_modal_visible_for_submit():
            logger.warning("未检测到取消原因弹窗标题，跳过 Native 提交点击以避免误触蒙层")
            return False
        # 优先限定在弹窗语义范围内找提交，降低误点主页面/蒙层风险
        for xp in (
            '//*[contains(@text,"请选择取消订单原因")]/following::*[contains(@text,"提交")][1]',
            '//*[contains(@text,"请选择取消订单原因")]/following::*[contains(@content-desc,"提交")][1]',
            '//*[contains(@content-desc,"请选择取消订单原因")]/following::*[contains(@text,"提交")][1]',
        ):
            try:
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    try:
                        if not el.is_displayed():
                            continue
                        y = int(el.location.get("y", 0))
                        if y < y_min or y > y_max:
                            continue
                        if self._coord_tap_or_click(el, "已点取消弹窗提交（弹窗范围）"):
                            time.sleep(0.45)
                            if not self._cancel_reason_modal_title_visible():
                                return True
                            logger.warning(
                                "following 轴命中「提交」后原因弹层仍在，尝试其它路径"
                            )
                    except Exception:
                        continue
            except Exception:
                continue
        # 在「请选择取消订单原因」弹层内取 **最靠下** 的短文案「提交」节点（橙色主按钮），
        # 避免 following::[1] 命中列表里其它含「提交」的噪声。
        try:
            sheet_anchors = (
                '//*[contains(@text,"请选择取消订单原因")]',
                '//*[contains(@content-desc,"请选择取消订单原因")]',
            )
            anchor_y = -1
            for axp in sheet_anchors:
                for ael in self.driver.find_elements(AppiumBy.XPATH, axp):
                    try:
                        if ael.is_displayed():
                            anchor_y = max(anchor_y, int(ael.location.get("y", 0)))
                    except Exception:
                        continue
            submit_rows: List[Tuple[int, Any]] = []
            for el in self.driver.find_elements(
                AppiumBy.XPATH,
                '//*[contains(@text,"提交") or contains(@content-desc,"提交")]',
            ):
                try:
                    if not el.is_displayed():
                        continue
                    y = int(el.location.get("y", 0))
                    if y < y_min or y > y_max:
                        continue
                    tx = (el.get_attribute("text") or "").strip()
                    cd = (el.get_attribute("content-desc") or "").strip()
                    if "请选择取消订单原因" in tx or "请选择取消订单原因" in cd:
                        continue
                    if len(tx) > 16 or len(cd) > 120:
                        continue
                    if "提交" not in tx and "提交" not in cd:
                        continue
                    # 主按钮应在「请选择取消订单原因」标题下方
                    if anchor_y >= 0 and y <= anchor_y + int(h * 0.03):
                        continue
                    submit_rows.append((y, el))
                except Exception:
                    continue
            submit_rows.sort(key=lambda t: -t[0])
            for _, el in submit_rows[:4]:
                if self._coord_tap_or_click(el, "已点取消弹窗提交（取最下「提交」节点）"):
                    time.sleep(0.45)
                    if not self._cancel_reason_modal_title_visible():
                        return True
                    logger.warning(
                        "点「提交」节点后原因弹层仍在，尝试下一候选或坐标兜底"
                    )
        except Exception:
            pass
        for xp in _XPATH_NATIVE_SUBMIT:
            try:
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    try:
                        if not el.is_displayed():
                            continue
                        y = int(el.location.get("y", 0))
                        if y < y_min or y > y_max:
                            continue
                        if self._coord_tap_or_click(el, "已点取消弹窗提交（Native）"):
                            time.sleep(0.45)
                            if not self._cancel_reason_modal_title_visible():
                                return True
                            logger.warning(
                                "XPath 提交点击后原因弹层仍在，尝试其它路径"
                            )
                    except Exception:
                        continue
            except Exception:
                continue
        # 勿在此用「确认」「确定」泛匹配：易点到其它层按钮或直接关弹窗（用户反馈）。
        try:
            self.driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                'new UiSelector().text("提交").clickable(true)',
            ).click()
            time.sleep(0.45)
            if not self._cancel_reason_modal_title_visible():
                return True
        except Exception:
            pass
        try:
            self.driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                'new UiSelector().descriptionContains("提交").clickable(true)',
            ).click()
            time.sleep(0.45)
            if not self._cancel_reason_modal_title_visible():
                return True
        except Exception:
            pass
        # Appium 元素定位偶发拿不到 Flutter 语义节点时，从 page_source 的 bounds
        # 直接解析「提交」主按钮。实测取消原因弹层的提交按钮在 0.70h~0.78h。
        try:
            src = self.driver.page_source or ""
            bounds_hits: List[Tuple[int, int, int, int]] = []
            for m in re.finditer(r"<node\b[^>]*>", src):
                tag = m.group(0)
                if "提交" not in tag:
                    continue
                bm = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', tag)
                if not bm:
                    continue
                x1, y1, x2, y2 = (int(v) for v in bm.groups())
                bw, bh = x2 - x1, y2 - y1
                cy = (y1 + y2) // 2
                if not (int(h * 0.64) <= cy <= int(h * 0.82)):
                    continue
                if bw < int(w * 0.45) or bh < int(h * 0.025):
                    continue
                bounds_hits.append((x1, y1, x2, y2))
            bounds_hits.sort(key=lambda r: (-(r[2] - r[0]), r[1]))
            for x1, y1, x2, y2 in bounds_hits[:3]:
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                self.driver.execute_script(
                    "mobile: clickGesture", {"x": cx, "y": cy}
                )
                logger.info("取消弹窗提交 bounds 兜底 (%d,%d)", cx, cy)
                time.sleep(0.52)
                if not self._cancel_reason_modal_title_visible():
                    return True
        except Exception:
            pass
        # 坐标兜底：按取消原因弹层实际主按钮高度点，避免点到弹层下方。
        for xf, yf in (
            (0.50, 0.73),
            (0.50, 0.745),
            (0.50, 0.76),
            (0.48, 0.735),
            (0.52, 0.735),
            (0.46, 0.75),
            (0.54, 0.75),
            (0.50, 0.78),
        ):
            cx, cy = int(w * xf), int(h * yf)
            if not (int(w * 0.28) <= cx <= int(w * 0.72)):
                continue
            if not (int(h * 0.68) <= cy <= int(h * 0.84)):
                continue
            try:
                self.driver.execute_script(
                    "mobile: clickGesture", {"x": cx, "y": cy}
                )
                logger.info("取消弹窗提交坐标兜底 (%d,%d)", cx, cy)
                time.sleep(0.52)
                if not self._cancel_reason_modal_title_visible():
                    return True
                logger.warning(
                    "提交坐标 (%d,%d) 后原因弹层仍在，尝试下一坐标",
                    cx,
                    cy,
                )
            except Exception:
                continue
        return False


    def _cancel_reason_modal_visible_for_submit(self) -> bool:
        """提交取消原因前的宽松弹层检测；含标题和取消订单文案。"""
        for xp in (
            '//*[contains(@text,"请选择取消订单原因")]',
            '//*[contains(@content-desc,"请选择取消订单原因")]',
            '//*[contains(@text,"取消订单")]',
        ):
            try:
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    try:
                        if el.is_displayed():
                            return True
                    except Exception:
                        continue
            except Exception:
                pass
        return False
    

    def _tap_cancel_order_submit(
        self, reason_context: Optional[str] = None
    ) -> bool:
        """
        取消原因选完后点「提交」。若在 WebView 里选的原因，须先在同一 context 点提交，
        勿先切 NATIVE 否则找不到 H5 按钮。
        嵌套 H5 上 XPath 常失效，故在同一 context 内再执行 ``document`` 级脚本点击。
        """
        for attempt in range(3):
            if attempt:
                time.sleep(0.55)
            webviews = self._iter_webview_contexts()
            if not webviews:
                logger.debug("当前未发现 WEBVIEW context，提交将先走 Native 兜底")
            if reason_context and "WEBVIEW" in str(reason_context).upper():
                if self._switch_context_safe(reason_context):
                    if self._webview_try_submit_in_current_context():
                        logger.info("已点击「提交」（与原因同 WebView）")
                        self._switch_context_safe("NATIVE_APP")
                        return True
            for wctx in webviews:
                if self._switch_context_safe(wctx):
                    if self._webview_try_submit_in_current_context():
                        logger.info("已点击「提交」（WebView %s）", wctx)
                        self._switch_context_safe("NATIVE_APP")
                        return True
            self._switch_context_safe("NATIVE_APP")
            if self._tap_native_submit_cancel_sheet():
                logger.info("已点击「提交」（Native / UiAutomator）")
                return True
        self._switch_context_safe("NATIVE_APP")
        return False
    

    def _native_tap_cancel_reason_row_radio_best_effort(self, reason: str) -> bool:
        """
        取消原因弹窗为 Native 单选列表时，**未选中任一项则点「提交」无效**（空圈状态）。
        按含目标文案的节点 bounds 计算行中心，优先点击行右侧（单选圈），再试文案区。
        """
        w, h = self._window_size_safe()
        y_min, y_max = int(h * 0.14), int(h * 0.94)

        def _tap(cx: int, cy: int, tag: str) -> bool:
            if not (int(w * 0.06) <= cx <= int(w * 0.97)):
                return False
            if not (y_min <= cy <= y_max):
                return False
            try:
                self.driver.execute_script(
                    "mobile: clickGesture", {"x": cx, "y": cy}
                )
                logger.info("已点取消理由%s (%d,%d)", tag, cx, cy)
                return True
            except Exception:
                return False

        # 与 Inspector 常见写法一致：先精确 @text / @content-desc，再 contains，再「填错」模糊
        xps_ordered: List[str] = [
            f'//*[@text="{reason}"]',
            f'//*[@content-desc="{reason}"]',
            f'//*[contains(@text,"{reason}")]',
            f'//*[contains(@content-desc,"{reason}")]',
        ]
        if "填错" in reason:
            xps_ordered.extend(
                (
                    '//*[contains(@text,"填错")]',
                    '//*[contains(@content-desc,"填错")]',
                )
            )
        for xp in xps_ordered:
            try:
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    try:
                        if not el.is_displayed():
                            continue
                        loc = el.location
                        sz = el.size
                        y0 = int(loc.get("y", -1))
                        x0 = int(loc.get("x", 0))
                        bw = int(sz.get("width", 0))
                        bh = int(sz.get("height", 0))
                        if y0 < y_min or y0 > y_max:
                            continue
                        blob = (
                            (el.get_attribute("content-desc") or "")
                            + (el.get_attribute("text") or "")
                        )
                        if 'contains(@text,"填错")' in xp or 'contains(@content-desc,"填错")' in xp:
                            if not (
                                reason in blob
                                or ("收货信息" in blob and "填错" in blob)
                            ):
                                continue
                        elif reason not in blob:
                            continue
                        cy = y0 + max(bh // 2, 10)
                        if bw > 48:
                            cx_r = x0 + int(bw * 0.88)
                            cx_t = x0 + int(bw * 0.36)
                        else:
                            cx_r, cx_t = int(w * 0.86), int(w * 0.36)
                        if _tap(cx_r, cy, "行右侧单选区"):
                            return True
                        if _tap(cx_t, cy, "行文案区"):
                            return True
                    except Exception:
                        continue
            except Exception:
                pass
        short = reason[:22] if len(reason) > 22 else reason
        try:
            for el in self.driver.find_elements(
                AppiumBy.ANDROID_UIAUTOMATOR,
                f'new UiSelector().textContains("{short}")',
            ):
                try:
                    if not el.is_displayed():
                        continue
                    loc = el.location
                    sz = el.size
                    y0 = int(loc.get("y", -1))
                    x0 = int(loc.get("x", 0))
                    bw = int(sz.get("width", 0))
                    bh = int(sz.get("height", 0))
                    if y0 < y_min or y0 > y_max:
                        continue
                    cy = y0 + max(bh // 2, 10)
                    if bw > 48:
                        cx_r = x0 + int(bw * 0.88)
                        cx_t = x0 + int(bw * 0.36)
                    else:
                        cx_r, cx_t = int(w * 0.86), int(w * 0.36)
                    if _tap(cx_r, cy, "（UiAutomator 行右侧）"):
                        return True
                    if _tap(cx_t, cy, "（UiAutomator 文案区）"):
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        return False
    

    def _choose_cancel_reason_then_submit(
        self, prefer_reason: str = "收货信息填错了"
    ) -> bool:
        """
        参考用户给出的流程：
        1) 优先 WebView：选理由 -> 立即提交
        2) 回退 Native：选理由 -> 立即提交
        3) 最后再走通用 submit 兜底
        """
        time.sleep(2.0)
        reason = (prefer_reason or "收货信息填错了").strip()
        if '"' in reason:
            reason = reason.replace('"', "")
        if "'" in reason:
            reason = reason.replace("'", "")
        reason_xps = (
            f"//*[normalize-space(text())='{reason}']",
            f'//*[contains(normalize-space(.),"{reason}")]',
        )
        picked = False
        picked_context: Optional[str] = None
        # 1) 优先 WebView
        for wctx in self._iter_webview_contexts():
            if not self._switch_context_safe(wctx):
                continue
            if self._webview_click_first_matching(reason_xps):
                logger.info("已选择取消理由（WebView）: %s", reason)
                picked = True
                picked_context = wctx
                time.sleep(0.35)
                if self._webview_try_submit_in_current_context():
                    logger.info("已点击「提交」（WebView 同上下文）")
                    self._switch_context_safe("NATIVE_APP")
                    return True
                break
        # 2) fallback Native
        self._switch_context_safe("NATIVE_APP")
        w, h = self._window_size_safe()
        if self._native_tap_cancel_reason_row_radio_best_effort(reason):
            logger.info("已选择取消理由（Native 行内单选坐标）: %s", reason)
            picked = True
            picked_context = "NATIVE_APP"
            time.sleep(0.4)
            if self._tap_native_submit_cancel_sheet():
                logger.info("已点击「提交」（Native，行内单选后）")
                return True
        y_min = int(h * 0.15)
        y_max = int(h * 0.96)
        native_reason_xps: Tuple[str, ...] = (
            f'//*[@text="{reason}"]',
            f'//*[@content-desc="{reason}"]',
            f'//*[contains(@text,"{reason}")]',
            f'//*[contains(@content-desc,"{reason}")]',
        )
        if "填错" in reason:
            native_reason_xps = native_reason_xps + (
                '//*[contains(@text,"填错")]',
                '//*[contains(@content-desc,"填错")]',
            )
        if not picked:
            for xp in native_reason_xps:
                try:
                    for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                        try:
                            if not el.is_displayed():
                                continue
                            y = int(el.location.get("y", 0))
                            if y < y_min or y > y_max:
                                continue
                            if 'contains(@text,"填错")' in xp or 'contains(@content-desc,"填错")' in xp:
                                b = (
                                    (el.get_attribute("text") or "")
                                    + (el.get_attribute("content-desc") or "")
                                )
                                if not (
                                    reason in b
                                    or ("收货信息" in b and "填错" in b)
                                ):
                                    continue
                            if self._coord_tap_or_click(el, "已点取消理由（Native 精确）"):
                                logger.info("已选择取消理由（Native）: %s", reason)
                                picked = True
                                picked_context = "NATIVE_APP"
                                time.sleep(0.35)
                                if self._tap_native_submit_cancel_sheet():
                                    logger.info("已点击「提交」（Native 同上下文）")
                                    return True
                                break
                        except Exception:
                            continue
                except Exception:
                    pass
                if picked:
                    break
        if not picked:
            # 兼容弹窗理由文案变体：从已知理由片段中在 Native 树匹配可见行
            for frag in _WEB_REASON_FRAGMENTS:
                if "提交" in frag or "取消" in frag:
                    continue
                safe = frag.replace('"', "").replace("'", "")
                for xp in (
                    f'//*[contains(@text,"{safe}")]',
                    f'//*[contains(@content-desc,"{safe}")]',
                    f'//android.view.View[contains(@content-desc,"{safe}")]',
                    f'//android.view.View[contains(@text,"{safe}")]',
                ):
                    try:
                        for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                            try:
                                if not el.is_displayed():
                                    continue
                                y = int(el.location.get("y", 0))
                                if y < y_min or y > y_max:
                                    continue
                                blob = (
                                    (el.get_attribute("content-desc") or "")
                                    + " "
                                    + (el.get_attribute("text") or "")
                                ).strip()
                                if any(k in blob for k in ("提交", "取消订单", "确定取消")):
                                    continue
                                if self._coord_tap_or_click(
                                    el, f"已点取消理由（Native 含「{safe}」）"
                                ):
                                    logger.info("已选择取消理由（Native 片段）: %s", safe)
                                    picked = True
                                    picked_context = "NATIVE_APP"
                                    time.sleep(0.35)
                                    if self._tap_native_submit_cancel_sheet():
                                        logger.info("已点击「提交」（Native 同上下文）")
                                        return True
                                    break
                            except Exception:
                                continue
                    except Exception:
                        continue
                    if picked:
                        break
                if picked:
                    break
        if not picked:
            # 最后兜底：该弹窗是 Native 单选列表（右侧圆圈），文本节点偶发不可取。
            # 对「收货信息填错了」按第 3 行点位尝试（文字区 + 右侧单选区）。
            # 与常见「取消订单」弹窗 7 项列表一致：第 3 项「收货信息填错了」约在屏高中部略上
            if "收货信息" in reason or "填错" in reason:
                row_y = (
                    0.48,
                    0.50,
                    0.52,
                    0.46,
                    0.44,
                    0.54,
                    0.555,
                    0.545,
                    0.565,
                    0.575,
                )
            else:
                row_y = (0.555, 0.545, 0.565)
            # 勿在「文字区 + 提交失败」时 break 整组：Flutter 单选常须点右侧圆圈才生效，
            # 须继续尝试同 row 的「单选区」及下一组 row_y。
            for yf in row_y:
                for xf, tag in ((0.36, "文字区"), (0.86, "单选区"), (0.78, "单选区内侧")):
                    cx, cy = int(w * xf), int(h * yf)
                    try:
                        self.driver.execute_script(
                            "mobile: clickGesture", {"x": cx, "y": cy}
                        )
                        logger.info(
                            "已点取消理由坐标兜底（%s）(%d,%d)",
                            tag,
                            cx,
                            cy,
                        )
                        picked = True
                        picked_context = "NATIVE_APP"
                        time.sleep(0.30)
                        if self._tap_native_submit_cancel_sheet():
                            logger.info("已点击「提交」（Native 同上下文，坐标兜底后）")
                            return True
                    except Exception:
                        continue
        # 3) 只有“已选中理由”才允许走提交流程，避免误点关闭弹窗
        if not picked:
            logger.error("取消理由未选中：已阻止提交动作，避免误关取消弹窗")
            self._switch_context_safe("NATIVE_APP")
            return False
        return self._tap_cancel_order_submit(reason_context=picked_context or "NATIVE_APP")
    

    def _cancel_reason_modal_title_visible(self) -> bool:
        """与 ``_tap_native_submit_cancel_sheet`` 一致的「选择取消原因」弹层标题检测。"""
        for xp in (
            '//*[contains(@text,"请选择取消订单原因")]',
            '//*[contains(@content-desc,"请选择取消订单原因")]',
        ):
            try:
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    try:
                        if el.is_displayed():
                            return True
                    except Exception:
                        continue
            except Exception:
                continue
        return False
    

    def _tap_native_dismiss_blocking_sheet(self) -> bool:
        """取消后偶发「我知道了」「好的」等遮罩，不点则详情不刷新、仍见「取消订单」。"""
        _, h = self._window_size_safe()
        # 仅点偏下区域，避免误点顶栏/其它「确定」
        y_cut = int(h * 0.52)
        for txt in ("我知道了", "好的", "知道了", "确定", "完成", "查看", "查看订单"):
            for xp in (
                f'//*[@text="{txt}"]',
                f'//*[contains(@content-desc,"{txt}")]',
            ):
                try:
                    for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                        try:
                            if not el.is_displayed():
                                continue
                            if int(el.location.get("y", 0)) < y_cut:
                                continue
                            if self._coord_tap_or_click(el, f"已点「{txt}」关闭提示/遮罩"):
                                return True
                        except Exception:
                            continue
                except Exception:
                    continue
        return False
    

    def _cancel_order_entry_still_visible(self) -> bool:
        """
        提交后用于判定是否仍在可取消状态。
        Flutter 常把整屏语义塞进超长 ``content-desc``，若仅用 contains(取消订单)
        会误判「入口仍在」；此处要求 **可点** 或 **短文案的「取消订单」**。
        """
        w, h = self._window_size_safe()
        y_min, y_max = int(h * 0.18), int(h * 0.97)
        try:
            if self._switch_context_safe("NATIVE_APP"):
                for xp in _XPATH_NATIVE_CANCEL_ORDER:
                    for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                        try:
                            if not el.is_displayed():
                                continue
                            y = int(el.location.get("y", 0))
                            if not (y_min <= y <= y_max):
                                continue
                            clickable = (
                                (el.get_attribute("clickable") or "").lower() == "true"
                            )
                            tx = (el.get_attribute("text") or "").strip()
                            cd = (el.get_attribute("content-desc") or "").strip()
                            if clickable and ("取消订单" in tx or "取消订单" in cd):
                                return True
                            if tx == "取消订单" and len(cd) < 200:
                                return True
                        except WebDriverException as ex:
                            if self._cancel_driver_query_unreliable(ex):
                                logger.warning(
                                    "检查取消入口时驱动不可用，不能判定入口已消失: %s",
                                    ex,
                                )
                                return True
                            continue
                        except Exception:
                            continue
        except WebDriverException as ex:
            if self._cancel_driver_query_unreliable(ex):
                logger.warning("Native 检查取消入口失败，不能判定入口已消失: %s", ex)
                return True
        except Exception as ex:
            logger.debug("Native 检查取消入口异常，保守视为仍需确认: %s", ex)
            return True
        for wctx in self._iter_webview_contexts():
            try:
                if not self._switch_context_safe(wctx):
                    continue
                for xp in _WEB_XPATH_CANCEL_ORDER:
                    for el in self.driver.find_elements(By.XPATH, xp):
                        try:
                            if el.is_displayed():
                                return True
                        except WebDriverException as ex:
                            if self._cancel_driver_query_unreliable(ex):
                                logger.warning(
                                    "WebView 检查取消入口时驱动不可用，不能判定入口已消失: %s",
                                    ex,
                                )
                                self._switch_context_safe("NATIVE_APP")
                                return True
                            continue
                        except Exception:
                            continue
            except WebDriverException as ex:
                if self._cancel_driver_query_unreliable(ex):
                    logger.warning("WebView 检查取消入口失败，不能判定入口已消失: %s", ex)
                    self._switch_context_safe("NATIVE_APP")
                    return True
                continue
            except Exception:
                continue
        self._switch_context_safe("NATIVE_APP")
        return False
    

    def _wait_cancel_result_after_submit(self, timeout: float = 12.0) -> bool:
        """
        提交取消后等待结果：
        - 命中「已取消/取消成功」等成功信号 -> True
        - 或「取消订单」入口消失 -> True
        - 超时仍可见取消入口 -> False
        """
        ok_words = (
            "已取消",
            "取消成功",
            "订单已取消",
            "已申请取消",
            "取消中",
            "取消申请",
            "已发起取消",
            "申请成功",
            "提交成功",
            "退款",
            "已受理",
            "正在处理",
            "商家已收到",
            "待退款",
            "退款中",
            "订单关闭",
            "交易关闭",
            "已关闭",
            "作废",
            "待商家",
            "商家处理",
        )
        # page_source 用较长短语，降低误命中隐私/帮助长文
        ok_phrases_page_src = (
            "订单已取消",
            "取消成功",
            "已申请取消",
            "取消申请",
            "成功发起取消",
            "您的订单已取消",
            "待商家处理",
            "商家同意",
            "退款处理中",
        )
        end = time.time() + timeout
        it = 0
        cancel_entry_absent_count = 0
        while time.time() < end:
            it += 1
            try:
                if self._switch_context_safe("NATIVE_APP"):
                    self._tap_native_dismiss_blocking_sheet()
                    for wd in ok_words:
                        for xp in (
                            f'//*[contains(@text,"{wd}")]',
                            f'//*[contains(@content-desc,"{wd}")]',
                        ):
                            for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                                try:
                                    if el.is_displayed():
                                        logger.info("取消结果命中成功文案（Native）: %s", wd)
                                        return True
                                except Exception:
                                    continue
            except Exception:
                pass
            for wctx in self._iter_webview_contexts():
                try:
                    if not self._switch_context_safe(wctx):
                        continue
                    for wd in ok_words:
                        xp = f"//*[contains(normalize-space(string(.)),'{wd}')]"
                        for el in self.driver.find_elements(By.XPATH, xp):
                            try:
                                if el.is_displayed():
                                    logger.info(
                                        "取消结果命中成功文案（WebView %s）: %s",
                                        wctx,
                                        wd,
                                    )
                                    self._switch_context_safe("NATIVE_APP")
                                    return True
                            except Exception:
                                continue
                except Exception:
                    continue
            if not self._cancel_order_entry_still_visible():
                cancel_entry_absent_count += 1
                logger.info(
                    "取消结果校验：第 %d 次未见「取消订单」入口，继续确认",
                    cancel_entry_absent_count,
                )
                if cancel_entry_absent_count >= 3:
                    self._switch_context_safe("NATIVE_APP")
                    return True
            else:
                cancel_entry_absent_count = 0
            if it % 7 == 0:
                try:
                    src = (self.driver.page_source or "")
                    low = src.lower()
                    for ph in ok_phrases_page_src:
                        if ph.lower() in low:
                            logger.info(
                                "取消结果命中（page_source 短语）: %s",
                                ph,
                            )
                            self._switch_context_safe("NATIVE_APP")
                            return True
                except Exception:
                    pass
            if it % 12 == 0 and it >= 12:
                w, h = self._window_size_safe()
                x = int(w * 0.5)
                try:
                    self.driver.swipe(x, int(h * 0.28), x, int(h * 0.62), 400)
                except Exception:
                    try:
                        self.driver.execute_script(
                            "mobile: swipeGesture",
                            {
                                "left": int(w * 0.30),
                                "top": int(h * 0.22),
                                "width": int(w * 0.40),
                                "height": int(h * 0.48),
                                "direction": "down",
                                "percent": 0.38,
                            },
                        )
                    except Exception:
                        pass
                time.sleep(0.55)
            time.sleep(0.45)
        self._switch_context_safe("NATIVE_APP")
        logger.error("取消结果校验失败：超时仍未见成功文案，且「取消订单」入口仍存在")
        return False
    

    def shop_assert_order_detail_cancel_visible(self, timeout: float = 25.0) -> bool:
        self._last_order_detail_context = None
        end = time.time() + timeout
        while time.time() < end:
            try:
                if self._switch_context_safe("NATIVE_APP"):
                    for xp in _XPATH_NATIVE_CANCEL_ORDER:
                        for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                            if el.is_displayed():
                                self._last_order_detail_context = "NATIVE_APP"
                                logger.info("断言成功：Native 可见「取消订单」")
                                return True
            except Exception:
                pass
    
            for wctx in self._iter_webview_contexts():
                try:
                    if not self._switch_context_safe(wctx):
                        continue
                    for xp in _WEB_XPATH_CANCEL_ORDER:
                        for el in self.driver.find_elements(By.XPATH, xp):
                            try:
                                if el.is_displayed():
                                    self._last_order_detail_context = wctx
                                    logger.info(
                                        "断言成功：WebView 可见「取消订单」 context=%s",
                                        wctx,
                                    )
                                    return True
                            except Exception:
                                continue
                except Exception:
                    continue
    
            time.sleep(0.45)
    
        try:
            self._switch_context_safe("NATIVE_APP")
        except Exception:
            pass
        logger.error("超时：Native/WebView 均未见「取消订单」")
        return False
    

    def shop_cancel_order_flow(self) -> bool:
        self._log_contexts("取消流程开始")
        saved = getattr(self, "_last_order_detail_context", None)
        clicked = False
        if saved and "WEBVIEW" in str(saved).upper():
            if self._switch_context_safe(saved):
                clicked = self._webview_click_first_matching(_WEB_XPATH_CANCEL_ORDER)
        if not clicked:
            self._switch_context_safe("NATIVE_APP")
            for xp in _XPATH_NATIVE_CANCEL_ORDER:
                if self._tap_first_displayed(AppiumBy.XPATH, xp):
                    clicked = True
                    break
        if not clicked:
            for wctx in self._iter_webview_contexts():
                if self._switch_context_safe(wctx):
                    if self._webview_click_first_matching(_WEB_XPATH_CANCEL_ORDER):
                        clicked = True
                        break
            self._switch_context_safe("NATIVE_APP")
    
        time.sleep(0.9)
    
        self._switch_context_safe("NATIVE_APP")
        ok_confirm = False
        for xp in _XPATH_NATIVE_CONFIRM_CANCEL:
            if self._tap_first_displayed(AppiumBy.XPATH, xp):
                ok_confirm = True
                break
        if not ok_confirm:
            for wctx in self._iter_webview_contexts():
                if self._switch_context_safe(wctx):
                    if self._webview_click_first_matching(_WEB_XPATH_CONFIRM_CANCEL):
                        ok_confirm = True
                        logger.info("已点「确定取消」（WebView %s）", wctx)
                        break
            self._switch_context_safe("NATIVE_APP")
    
        time.sleep(0.9)
    
        time.sleep(0.65)
        self._log_contexts("提交前")
        submit_ok = self._choose_cancel_reason_then_submit("收货信息填错了")
        if not submit_ok:
            logger.error("取消订单未完成：未点到「提交」，请检查 H5/Native 提交按钮")
            self._switch_context_safe("NATIVE_APP")
            time.sleep(0.8)
            return False
        # 提交坐标命中但服务端未关单时，原因弹层仍可能停留；短重试提交
        self._switch_context_safe("NATIVE_APP")
        for retry in range(3):
            time.sleep(0.5)
            if not self._cancel_reason_modal_title_visible():
                break
            logger.warning(
                "取消原因弹层仍在（第 %d 次重试点击「提交」）",
                retry + 1,
            )
            self._tap_native_submit_cancel_sheet()
        result_ok = self._wait_cancel_result_after_submit(timeout=26.0)
        self._log_contexts("提交后")
        self._switch_context_safe("NATIVE_APP")
        time.sleep(0.8)
        return result_ok
