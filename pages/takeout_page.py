"""外卖首页进店与列表；店铺内下单见 takeout_shop_mixin，XPath/包名见 takeout_locators。

运行：python scripts/run_takeout_wangwang.py [--checkout ...]
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Optional, Sequence, Tuple

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from commons.logger import setup_logger
from pages.takeout_locators import (
    _PACKAGES,
    _merchant_list_rid,
    _name_xpath_exact,
    _row_tab_content_xpath_contains,
    _row_tab_content_xpath_exact,
    _row_xpath_contains_name,
    _row_xpath_exact_name,
    _scoped_row_tab_content_xpath_contains,
    _scoped_row_tab_content_xpath_exact,
    _scoped_row_xpath_contains_name,
    _scoped_row_xpath_exact_name,
    _scoped_shop_title_textview_contains,
    _scoped_shop_title_textview_exact,
    _scoped_tv_merchant_name_contains,
    _scoped_tv_merchant_name_exact,
)
from pages.takeout_shop_mixin import TakeoutShopMixin

logger = setup_logger(__name__)

# 挂在 WebDriver 实例上：同一死会话上新建 TakeoutPageBase 也能立刻短路，避免重复跑 Tab/等待
_UIA2_DEAD_ATTR = "_kzs_uia2_instrumentation_dead"


class TakeoutPageBase(TakeoutShopMixin):
    """外卖首页：城市、底栏、商家列表与进店。"""

    def __init__(self, driver: WebDriver, wait_sec: float = 20.0):
        """driver：Appium WebDriver；wait_sec：默认显式等待秒数。"""
        self.driver = driver
        self.wait_sec = wait_sec

    def _wait(self, timeout: Optional[float] = None) -> WebDriverWait:
        """WebDriverWait，timeout 默认 self.wait_sec。"""
        return WebDriverWait(self.driver, timeout or self.wait_sec)

    def _driver_uia2_mark_dead(self) -> None:
        """UiAutomator2 instrumentation 已不可用；标记在当前 driver 上直至换会话。"""
        try:
            setattr(self.driver, _UIA2_DEAD_ATTR, True)
        except Exception:
            pass

    def _driver_uia2_is_dead(self) -> bool:
        try:
            return bool(getattr(self.driver, _UIA2_DEAD_ATTR, False))
        except Exception:
            return False

    def _requires_new_driver_session(self, exc: BaseException) -> bool:
        """与 socket 类瞬时错误区分：此类须重建 Appium 会话 / driver。"""
        msg = (getattr(exc, "msg", None) or str(exc)).lower()
        return (
            "instrumentation process is not running" in msg
            or "cannot be proxied to uiautomator2" in msg
        )

    def _window_height(self) -> int:
        """窗口高度，失败时返回 1920。"""
        try:
            return int(self.driver.get_window_size()["height"])
        except Exception:
            return 1920

    def is_on_takeout_merchant_home(self) -> bool:
        """是否在外卖首页（可见 rv_merchant）。"""
        for pkg in _PACKAGES:
            rid = _merchant_list_rid(pkg)
            try:
                for el in self.driver.find_elements(AppiumBy.ID, rid):
                    try:
                        if el.is_displayed():
                            return True
                    except Exception:
                        continue
            except Exception:
                pass
        return False

    def _nearest_clickable_ancestor(self, el, max_hops: int = 8):
        """自 el 向上找可点击祖先（底栏 tab 文案常不可点）。"""
        cur = el
        for _ in range(max_hops):
            try:
                if (cur.get_attribute("clickable") or "").lower() == "true":
                    return cur
                cur = cur.find_element(AppiumBy.XPATH, "..")
            except Exception:
                break
        return el

    def _find_bottom_nav_takeout_element(self):
        """底部「外卖」Tab 可点击元素（排除屏上方同名文案）。"""
        h = self._window_height()
        # 部分机型底栏略高，0.72 过严会漏掉 Tab
        y_min = int(h * 0.68)
        for pkg in _PACKAGES:
            for label in ("外卖", "美食外卖"):
                xp = (
                    f'//android.widget.TextView[@resource-id="{pkg}:id/tab_text_tv" '
                    f'and @text="{label}"]'
                )
                try:
                    for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                        try:
                            if not el.is_displayed():
                                continue
                            if int(el.location.get("y", 0)) < y_min:
                                continue
                            return self._nearest_clickable_ancestor(el)
                        except Exception:
                            continue
                except Exception:
                    pass
        for pkg in _PACKAGES:
            try:
                els = self.driver.find_elements(
                    AppiumBy.ID, f"{pkg}:id/tab_icon_iv"
                )
                if len(els) >= 2:
                    el = els[1]
                    if el.is_displayed() and int(el.location.get("y", 0)) >= y_min:
                        return self._nearest_clickable_ancestor(el)
            except Exception:
                pass
        candidates: Tuple[Tuple[str, str], ...] = (
            (AppiumBy.XPATH, '//android.widget.TextView[@text="外卖"]'),
            (AppiumBy.XPATH, '//android.widget.TextView[@text="美食外卖"]'),
            (AppiumBy.XPATH, '//*[@content-desc="外卖"]'),
            (
                AppiumBy.XPATH,
                '//*[@clickable="true" and (@text="外卖" or @text="美食外卖")]',
            ),
        )
        for by, xp in candidates:
            try:
                for el in self.driver.find_elements(by, xp):
                    try:
                        if not el.is_displayed():
                            continue
                        y = int(el.location.get("y", 0))
                        if y >= y_min:
                            return self._nearest_clickable_ancestor(el)
                    except Exception:
                        continue
            except Exception:
                pass
        for text in ("外卖", "美食外卖"):
            uia = f'new UiSelector().text("{text}")'
            try:
                for el in self.driver.find_elements(
                    AppiumBy.ANDROID_UIAUTOMATOR, uia
                ):
                    try:
                        if not el.is_displayed():
                            continue
                        y = int(el.location.get("y", 0))
                        if y >= y_min:
                            return self._nearest_clickable_ancestor(el)
                    except Exception:
                        continue
            except Exception:
                pass
        for needle in ("外卖", "美食外卖"):
            esc = needle.replace('"', '\\"')
            for sel in (
                f'new UiSelector().descriptionContains("{esc}").clickable(true)',
                f'new UiSelector().description("{esc}")',
            ):
                try:
                    for el in self.driver.find_elements(
                        AppiumBy.ANDROID_UIAUTOMATOR, sel
                    ):
                        try:
                            if not el.is_displayed():
                                continue
                            y = int(el.location.get("y", 0))
                            if y >= y_min:
                                return self._nearest_clickable_ancestor(el)
                        except Exception:
                            continue
                except Exception:
                    pass
        return None

    def _tap_bottom_takeout_tab_geometry_fallback(self) -> bool:
        """底栏为纯图标/无 resource-id 时，按屏宽比例点常见「外卖」槽位（左起第 2 格）。"""
        try:
            win = self.driver.get_window_size()
            w, h = int(win["width"]), int(win["height"])
        except Exception:
            return False
        y = int(h * 0.935)
        for frac in (0.38, 0.30, 0.46, 0.22):
            x = max(24, int(w * frac))
            try:
                self.driver.execute_script(
                    "mobile: clickGesture",
                    {"x": x, "y": y},
                )
                logger.info("已尝试坐标点击底栏疑似外卖位 (%d,%d)", x, y)
                time.sleep(0.45)
                if self.is_on_takeout_merchant_home():
                    return True
            except Exception:
                continue
        return False

    def ensure_takeout_tab(
        self,
        settle_sec: float = 1.2,
        max_tab_clicks: int = 3,
        wait_list_timeout: Optional[float] = 12.0,
    ) -> bool:
        """不在外卖首页则点底栏「外卖」，直至出现 rv_merchant 或超时。"""
        if self._driver_uia2_is_dead():
            logger.error(
                "已跳过切换外卖 Tab：当前 WebDriver 上 UiAutomator2 instrumentation 已不可用"
                "（本会话先前已在控件查找中报 instrumentation 崩溃）。请重建 Appium 会话后再跑。"
            )
            return False
        try:
            if self.is_on_takeout_merchant_home():
                logger.info("已在外卖 Tab（检测到商家列表 rv_merchant）")
                return True
        except WebDriverException as ex:
            if self._requires_new_driver_session(ex):
                self._driver_uia2_mark_dead()
                logger.error("检测外卖首页失败（UiAutomator2 不可用）：%s", ex)
                return False
            raise

        logger.info("当前不在外卖首页，尝试切换到底部「外卖」Tab…")
        for i in range(max_tab_clicks):
            tab_el = self._find_bottom_nav_takeout_element()
            if tab_el:
                try:
                    tab_el.click()
                    logger.info("已点击底部外卖 Tab（第 %d 次）", i + 1)
                except Exception as ex:
                    logger.warning("点击外卖 Tab 失败: %s", ex)
            else:
                logger.warning("未定位到底部外卖 Tab（第 %d 次），可检查底部栏文案/结构", i + 1)
                if self._tap_bottom_takeout_tab_geometry_fallback():
                    logger.info("坐标兜底后已出现商家列表")
                    return True

            time.sleep(settle_sec)
            try:
                if self.is_on_takeout_merchant_home():
                    logger.info("已切换至外卖首页")
                    return True
            except WebDriverException as ex:
                if self._requires_new_driver_session(ex):
                    self._driver_uia2_mark_dead()
                    logger.error("切换 Tab 后检测首页失败（UiAutomator2 不可用）：%s", ex)
                    return False
                if self._is_transient_driver_error(ex):
                    logger.warning("检测外卖首页时驱动瞬时异常，继续重试: %s", ex)
                    time.sleep(0.8)
                    continue
                raise

        if wait_list_timeout and wait_list_timeout > 0:
            try:
                if self.wait_merchant_list_present(timeout=wait_list_timeout):
                    return True
            except WebDriverException as ex:
                if self._is_transient_driver_error(ex):
                    if self._requires_new_driver_session(ex):
                        self._driver_uia2_mark_dead()
                    logger.error(
                        "等待商家列表期间 instrumentation 崩溃：%s。请重建会话后重试。",
                        ex,
                    )
                    return False
                raise

        if getattr(self, "_last_merchant_wait_uia2_dead", False):
            self._last_merchant_wait_uia2_dead = False
            logger.error(
                "无法进入外卖首页：上文已报 UiAutomator2 instrumentation 崩溃，"
                "与「底部 Tab XPath」无关。请结束当前 Appium 会话并重启 driver；"
                "仍失败则重启手机或重装设备端 io.appium.uiautomator2.server。"
            )
            return False
        logger.error("无法确认已进入外卖首页（未见 rv_merchant），请 Inspector 核对底部 Tab 定位")
        return False

    def location_header_shows_manila(self) -> bool:
        """外卖顶栏 tv_location 是否已为马尼拉。"""
        for pkg in _PACKAGES:
            try:
                for el in self.driver.find_elements(
                    AppiumBy.ID, f"{pkg}:id/tv_location"
                ):
                    if not el.is_displayed():
                        continue
                    t = (el.text or "").strip()
                    if "马尼拉" in t or "manila" in t.lower():
                        return True
            except Exception:
                pass
        return False

    def _click_location_bar_entry(self) -> bool:
        """点击左上角定位区（优先 ll_location）。"""
        for pkg in _PACKAGES:
            ll = f"{pkg}:id/ll_location"
            try:
                for el in self.driver.find_elements(AppiumBy.ID, ll):
                    if el.is_displayed():
                        try:
                            el.click()
                            logger.info("已点击顶栏定位容器 %s", ll)
                            return True
                        except Exception:
                            pass
            except Exception:
                pass
        for pkg in _PACKAGES:
            tid = f"{pkg}:id/tv_location"
            try:
                for el in self.driver.find_elements(AppiumBy.ID, tid):
                    if el.is_displayed():
                        target = self._nearest_clickable_ancestor(el)
                        try:
                            target.click()
                            logger.info("已点击顶栏定位（可点击祖先）%s", tid)
                            return True
                        except Exception:
                            try:
                                el.click()
                                logger.info("已直接点击 %s", tid)
                                return True
                            except Exception:
                                pass
            except Exception:
                pass
        return False

    def _address_selection_screen_visible(self) -> bool:
        """page_source 是否像「选择地址 / 热门城市」页。"""
        try:
            src = self.driver.page_source or ""
        except Exception:
            src = ""
        if not src:
            return False
        needles = (
            "选择地址",
            "切换热门城市",
            "搜索收货地址",
            "tv_city_name",
            "gv_select_city",
        )
        return any(n in src for n in needles)

    def _click_manila_hot_city(self) -> bool:
        """「切换热门城市」里点马尼拉。"""
        for pkg in _PACKAGES:
            xp = (
                f'//android.widget.TextView[@resource-id="{pkg}:id/tv_city_name" '
                f'and @text="马尼拉"]'
            )
            try:
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    if not el.is_displayed():
                        continue
                    tap = self._nearest_clickable_ancestor(el)
                    try:
                        tap.click()
                    except Exception:
                        el.click()
                    logger.info("已选择热门城市「马尼拉」（%s）", pkg)
                    return True
            except Exception:
                pass
        try:
            h = self._window_height()
            for el in self.driver.find_elements(
                AppiumBy.XPATH, '//android.widget.TextView[@text="马尼拉"]'
            ):
                if not el.is_displayed():
                    continue
                if int(el.location.get("y", 0)) > int(h * 0.90):
                    continue
                try:
                    self._nearest_clickable_ancestor(el).click()
                except Exception:
                    el.click()
                logger.info("已点击文案「马尼拉」（泛化 XPath）")
                return True
        except Exception:
            pass
        try:
            el = self.driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().text("马尼拉")'
            )
            if el and el.is_displayed():
                self._nearest_clickable_ancestor(el).click()
                logger.info("已 UiAutomator 点击「马尼拉」")
                return True
        except Exception:
            pass
        return False

    def dismiss_keep_selected_location_popup(self, total_wait_sec: float = 14.0) -> bool:
        """点「保留已选定位」/ tv_cancel，勿点切换至当前定位。"""
        deadline = time.time() + total_wait_sec
        start = time.time()

        while time.time() < deadline:
            for xp in (
                '//android.widget.TextView[@text="保留已选定位"]',
                '//*[@text="保留已选定位"]',
            ):
                try:
                    for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                        if not el.is_displayed():
                            continue
                        try:
                            el.click()
                        except Exception:
                            self._nearest_clickable_ancestor(el).click()
                        logger.info("已点击「保留已选定位」")
                        time.sleep(0.9)
                        return True
                except Exception:
                    pass
            for pkg in _PACKAGES:
                cid = f"{pkg}:id/tv_cancel"
                try:
                    for el in self.driver.find_elements(AppiumBy.ID, cid):
                        if not el.is_displayed():
                            continue
                        tx = (el.text or "").strip()
                        if "保留" in tx or "已选" in tx:
                            el.click()
                            logger.info("已点击 tv_cancel（保留已选定位）%s", pkg)
                            time.sleep(0.9)
                            return True
                except Exception:
                    pass
            if time.time() - start > 2.8:
                try:
                    s = self.driver.page_source or ""
                except Exception:
                    s = ""
                if "保留已选定位" not in s and "距离较远" not in s:
                    return False
            time.sleep(0.35)
        return False

    def ensure_takeout_city_manila(
        self,
        skip_if_already_manila: bool = True,
    ) -> bool:
        """外卖城市切马尼拉并 dismiss 保留已选定位弹窗。"""
        if skip_if_already_manila and self.location_header_shows_manila():
            logger.info("顶栏已是马尼拉，尝试关闭可能残留的远近提示弹窗…")
            self.dismiss_keep_selected_location_popup(total_wait_sec=4.0)
            return True

        if not self.ensure_takeout_tab():
            logger.warning("未能进入外卖 Tab，无法切换城市")
            return False

        if not self._click_location_bar_entry():
            logger.error("未点到左上角定位入口（ll_location / tv_location）")
            return False

        time.sleep(0.9)
        if not self._address_selection_screen_visible():
            time.sleep(1.2)

        if not self._address_selection_screen_visible():
            logger.warning("未稳定识别「选择地址」页，仍尝试点击马尼拉…")

        if not self._click_manila_hot_city():
            logger.error("未点到热门城市「马尼拉」")
            return False

        time.sleep(1.8)
        if self._address_selection_screen_visible():
            try:
                self.driver.back()
                time.sleep(1.0)
            except Exception:
                pass

        self.dismiss_keep_selected_location_popup(total_wait_sec=15.0)
        self.ensure_takeout_tab(settle_sec=0.9, max_tab_clicks=2)

        if self.location_header_shows_manila():
            logger.info("外卖顶栏已显示马尼拉")
        else:
            logger.warning(
                "未从顶栏文案确认马尼拉；若列表已有菲方店铺可忽略本警告"
            )
        return True

    def _uia_scroll_into_view(
        self,
        list_resource_id: str,
        shop_name: str,
        use_contains: bool,
        max_search_swipes: int = 12,
    ) -> bool:
        """在指定 resourceId 列表内 UiScrollable.scrollIntoView 到店名。"""
        safe = shop_name.replace('"', '\\"')
        if use_contains:
            target = f'new UiSelector().textContains("{safe}")'
        else:
            target = f'new UiSelector().text("{safe}")'
        ms = max(5, min(int(max_search_swipes), 14))
        uia = (
            f'new UiScrollable(new UiSelector().resourceId("{list_resource_id}"))'
            f".setMaxSearchSwipes({ms}).scrollIntoView({target})"
        )
        try:
            self.driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, uia)
            return True
        except Exception:
            return False

    def _scroll_merchant_uia_then_verify_row(
        self,
        rid: str,
        uia_label: str,
        use_contains: bool,
        shop_name: str,
        log_hint: str,
    ) -> bool:
        """UiScrollable 后必须用 XPath 确认屏上可见可点击店行。"""
        logger.info("UiScrollable：在 %s 中 %s …", rid, log_hint)
        if not self._uia_scroll_into_view(rid, uia_label, use_contains):
            return False
        time.sleep(0.45)
        if self._find_visible_clickable_row(shop_name):
            logger.info(
                "UiScrollable 后已确认屏上可见可点击店行「%s」（%s）",
                shop_name,
                rid,
            )
            return True
        if self._uia_scroll_into_view(rid, uia_label, use_contains):
            time.sleep(0.35)
            if self._find_visible_clickable_row(shop_name):
                logger.info(
                    "UiScrollable 第二次后已确认可见「%s」（%s）",
                    shop_name,
                    rid,
                )
                return True
        logger.info(
            "UiScrollable 后仍未见可点击店行「%s」（%s），改用手势列表滑动",
            shop_name,
            rid,
        )
        return False

    def _try_scroll_merchant_list(self, shop_name: str) -> bool:
        """UiScrollable 多策略找店，成功以屏上 XPath 为准。"""
        for pkg in _PACKAGES:
            rid = _merchant_list_rid(pkg)
            if self._scroll_merchant_uia_then_verify_row(
                rid,
                shop_name,
                False,
                shop_name,
                f'查找「{shop_name}」（精确 text）',
            ):
                return True
            if self._scroll_merchant_uia_then_verify_row(
                rid,
                shop_name,
                True,
                shop_name,
                f'textContains「{shop_name}」',
            ):
                return True
        for pkg in _PACKAGES:
            rid = _merchant_list_rid(pkg)
            if self._scroll_merchant_uia_then_verify_row(
                rid,
                "旺旺超市",
                True,
                shop_name,
                'textContains「旺旺超市」',
            ):
                return True
        return False

    def _first_displayed(self, elements) -> Optional[object]:
        """元素列表中第一个 is_displayed 的项。"""
        for el in elements:
            try:
                if el.is_displayed():
                    return el
            except Exception:
                continue
        return None

    @contextmanager
    def _zero_implicit_wait(self):
        """列表页整页 XPath 很重；隐式等待会放大单次查找耗时，查找期间临时关闭。"""
        try:
            self.driver.implicitly_wait(0)
            yield
        finally:
            try:
                self.driver.implicitly_wait(1)
            except Exception:
                pass

    def _uia_find_tv_merchant_name_contains(self, pkg: str, needle: str) -> Optional[object]:
        """UiAutomator：tv_merchant_name + textContains，通常比整页 XPath 快。"""
        n = (needle or "").strip()
        if len(n) < 2:
            return None
        safe = n.replace("\\", "\\\\").replace('"', '\\"')
        uia = (
            f'new UiSelector().resourceId("{pkg}:id/tv_merchant_name")'
            f'.textContains("{safe}")'
        )
        try:
            for el in self.driver.find_elements(AppiumBy.ANDROID_UIAUTOMATOR, uia):
                try:
                    if el.is_displayed():
                        return el
                except Exception:
                    continue
        except Exception:
            return None
        return None

    def _is_transient_driver_error(self, exc: BaseException) -> bool:
        """是否为可重试的 Appium/UiAutomator2 瞬时连接类错误。"""
        msg = (getattr(exc, "msg", None) or str(exc)).lower()
        keys = (
            "socket hang up",
            "could not proxy",
            "cannot be proxied to uiautomator2",
            "broken pipe",
            "connection refused",
            "connection reset",
            "econnreset",
            "instrumentation process is not running",
            "session is either terminated",
        )
        return any(k in msg for k in keys)

    def _find_visible_clickable_row(
        self,
        shop_name: str,
        *,
        allow_slow_legacy_xpath: bool = False,
        find_budget_sec: float = 5.0,
    ) -> Optional[object]:
        """找店行可点击元素；默认限时且不走整页慢 XPath（避免数分钟卡住不滑动）。"""
        pause = 2.0
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                return self._find_visible_clickable_row_impl(
                    shop_name,
                    allow_slow_legacy_xpath=allow_slow_legacy_xpath,
                    find_budget_sec=find_budget_sec,
                )
            except WebDriverException as e:
                if attempt + 1 < max_attempts and self._is_transient_driver_error(e):
                    logger.warning(
                        "查找店铺行连接异常，%.1fs 后重试 (%d/%d): %s",
                        pause,
                        attempt + 1,
                        max_attempts,
                        e,
                    )
                    time.sleep(pause)
                    continue
                raise
        return None

    def _shop_row_click_target(self, el: Optional[object]) -> Optional[object]:
        """店名常为 TextView，可点击区域在父级行上。"""
        if el is None:
            return None
        return self._nearest_clickable_ancestor(el)

    @staticmethod
    def _shop_name_text_variants(shop_name: str) -> Tuple[str, ...]:
        raw = (
            shop_name.strip(),
            shop_name.replace(" WWCS", "wwcs").strip(),
            shop_name.replace(" ", "").strip(),
        )
        seen: set[str] = set()
        out: list[str] = []
        for t in raw:
            if t and t not in seen:
                seen.add(t)
                out.append(t)
        return tuple(out)

    def _find_visible_clickable_row_impl(
        self,
        shop_name: str,
        *,
        allow_slow_legacy_xpath: bool,
        find_budget_sec: float,
    ) -> Optional[object]:
        """UiAutomator + rv_merchant 内 XPath；整页 legacy 仅 allow_slow_legacy_xpath 时启用。"""
        t_end = time.monotonic() + max(0.8, float(find_budget_sec))

        def expired() -> bool:
            return time.monotonic() >= t_end

        texts = self._shop_name_text_variants(shop_name)
        if "WWCS" in shop_name.upper():
            sub_candidates: Tuple[str, ...] = ("WWCS", "旺旺超市")
        elif "旺旺" in shop_name:
            sub_candidates = ("旺旺超市",)
        else:
            sub_candidates = (shop_name[: min(6, len(shop_name))],)

        needles_uia: list[str] = []
        for s in sub_candidates:
            if s and s not in needles_uia:
                needles_uia.append(s)
        for t in texts:
            if t and t not in needles_uia:
                needles_uia.append(t)

        with self._zero_implicit_wait():
            for pkg in _PACKAGES:
                if expired():
                    break
                for needle in needles_uia:
                    if expired():
                        break
                    el = self._uia_find_tv_merchant_name_contains(pkg, needle)
                    if el:
                        hit = self._shop_row_click_target(el)
                        if hit:
                            return hit

            def _hit(xp: str) -> Optional[object]:
                if expired():
                    return None
                el = self._first_displayed(
                    self.driver.find_elements(AppiumBy.XPATH, xp)
                )
                return self._shop_row_click_target(el)

            for pkg in _PACKAGES:
                if expired():
                    break
                for text in texts:
                    for xp_fn in (
                        _scoped_tv_merchant_name_exact,
                        _scoped_row_tab_content_xpath_exact,
                        _scoped_row_xpath_exact_name,
                        _scoped_shop_title_textview_exact,
                    ):
                        if expired():
                            return None
                        hit = _hit(xp_fn(pkg, text))
                        if hit:
                            return hit
                for sub in sub_candidates:
                    if expired():
                        return None
                    for xp_fn in (
                        _scoped_tv_merchant_name_contains,
                        _scoped_row_tab_content_xpath_contains,
                        _scoped_row_xpath_contains_name,
                    ):
                        if expired():
                            return None
                        hit = _hit(xp_fn(pkg, sub))
                        if hit:
                            return hit
                    if len(sub) >= 4:
                        if expired():
                            return None
                        hit = _hit(_scoped_shop_title_textview_contains(pkg, sub))
                        if hit:
                            return hit

            if allow_slow_legacy_xpath and not expired():
                for pkg in _PACKAGES:
                    if expired():
                        break
                    for text in texts:
                        if expired():
                            return None
                        el = self._first_displayed(
                            self.driver.find_elements(
                                AppiumBy.XPATH,
                                _row_tab_content_xpath_exact(pkg, text),
                            )
                        )
                        if el:
                            return self._shop_row_click_target(el)
                for pkg in _PACKAGES:
                    if expired():
                        break
                    for text in texts:
                        if expired():
                            return None
                        el = self._first_displayed(
                            self.driver.find_elements(
                                AppiumBy.XPATH,
                                _row_xpath_exact_name(pkg, text),
                            )
                        )
                        if el:
                            return self._shop_row_click_target(el)
                for sub in sub_candidates:
                    for pkg in _PACKAGES:
                        if expired():
                            return None
                        el = self._first_displayed(
                            self.driver.find_elements(
                                AppiumBy.XPATH,
                                _row_tab_content_xpath_contains(pkg, sub),
                            )
                        )
                        if el:
                            return self._shop_row_click_target(el)
                    for pkg in _PACKAGES:
                        if expired():
                            return None
                        el = self._first_displayed(
                            self.driver.find_elements(
                                AppiumBy.XPATH,
                                _row_xpath_contains_name(pkg, sub),
                            )
                        )
                        if el:
                            return self._shop_row_click_target(el)
                for pkg in _PACKAGES:
                    if expired():
                        break
                    for text in texts:
                        if expired():
                            return None
                        el = self._first_displayed(
                            self.driver.find_elements(
                                AppiumBy.XPATH,
                                _name_xpath_exact(pkg, text),
                            )
                        )
                        if el:
                            return self._shop_row_click_target(el)
        return None

    def _swipe_merchant_list_once(self) -> None:
        """商家列表上滑一次（触点偏右，减轻误触下拉刷新）。"""
        try:
            win = self.driver.get_window_size()
            w, h = int(win["width"]), int(win["height"])
        except Exception:
            return
        x = max(24, int(w * 0.70))
        y1, y2 = int(h * 0.62), int(h * 0.30)
        try:
            self.driver.swipe(x, y1, x, y2, 600)
        except Exception:
            try:
                self.driver.execute_script(
                    "mobile: swipeGesture",
                    {
                        "left": x - 20,
                        "top": y2,
                        "width": 40,
                        "height": y1 - y2,
                        "direction": "up",
                        "percent": 0.75,
                    },
                )
            except Exception:
                pass

    def scroll_to_and_open_shop(
        self,
        shop_name: str = "旺旺超市 WWCS",
        max_swipes: int = 24,
        settle_sec: float = 0.6,
        ensure_takeout_tab_first: bool = True,
    ) -> bool:
        """外卖列表中滚到目标店并点击进入详情。"""
        logger.info("外卖首页：查找并进店「%s」", shop_name)

        if ensure_takeout_tab_first and not self.ensure_takeout_tab():
            return False

        _shop_find_budget = 5.0
        logger.info(
            "当前屏查找「%s」（限时约 %.0fs：UiAutomator + 列表内 XPath；"
            "超时后滑动列表，最后再尝试一次全页慢路径）…",
            shop_name,
            _shop_find_budget,
        )
        el = self._find_visible_clickable_row(
            shop_name, find_budget_sec=_shop_find_budget
        )
        if el:
            try:
                el.click()
                logger.info("已点击店铺行/店名（当前屏可见，未先滚列表），等待进入详情…")
                time.sleep(1.2)
                return True
            except Exception as ex:
                logger.warning("点击店铺元素失败: %s", ex)

        logger.info("当前屏未见目标店，先手势翻列表（避免易触发刷新的中线滑动）…")
        for pre_i in range(6):
            self._swipe_merchant_list_once()
            time.sleep(0.32)
            el = self._find_visible_clickable_row(
                shop_name, find_budget_sec=_shop_find_budget
            )
            if el:
                try:
                    el.click()
                    logger.info(
                        "已点击店铺行/店名（预滑动第 %d 次后可见），等待进入详情…",
                        pre_i + 1,
                    )
                    time.sleep(1.2)
                    return True
                except Exception as ex:
                    logger.warning("点击店铺元素失败: %s", ex)

        logger.info("预滑动未见店，再尝试 UiScrollable（次数已收紧）…")
        self._try_scroll_merchant_list(shop_name)
        time.sleep(settle_sec)

        el = self._find_visible_clickable_row(
            shop_name, find_budget_sec=_shop_find_budget
        )
        if el:
            try:
                el.click()
                logger.info("已点击店铺行/店名，等待进入详情…")
                time.sleep(1.2)
                return True
            except Exception as ex:
                logger.warning("点击店铺元素失败: %s", ex)

        for i in range(max_swipes):
            self._swipe_merchant_list_once()
            time.sleep(0.45)
            el = self._find_visible_clickable_row(
                shop_name, find_budget_sec=_shop_find_budget
            )
            if el:
                try:
                    el.click()
                    logger.info("兜底滑动第 %d 次后已点击店铺「%s」", i + 1, shop_name)
                    time.sleep(1.2)
                    return True
                except Exception:
                    pass

        logger.info(
            "快路径未命中「%s」，最后一次允许全页 XPath（限时约 25s）…",
            shop_name,
        )
        el = self._find_visible_clickable_row(
            shop_name,
            allow_slow_legacy_xpath=True,
            find_budget_sec=25.0,
        )
        if el:
            try:
                el.click()
                logger.info("全页慢路径命中后已点击店铺「%s」", shop_name)
                time.sleep(1.2)
                return True
            except Exception as ex:
                logger.warning("点击店铺元素失败: %s", ex)

        logger.error("未找到或未点到店铺「%s」，请确认已在外卖 Tab 且列表 id 仍为 rv_merchant", shop_name)
        return False

    def wait_merchant_list_present(self, timeout: Optional[float] = None) -> bool:
        """等待任一包名下的 rv_merchant 出现。"""
        if self._driver_uia2_is_dead():
            logger.error(
                "已跳过等待商家列表：本会话 UiAutomator2 instrumentation 已不可用。"
            )
            return False
        self._last_merchant_wait_uia2_dead = False
        rid_candidates: Sequence[str] = tuple(_merchant_list_rid(p) for p in _PACKAGES)
        for rid in rid_candidates:
            try:
                self._wait(timeout).until(
                    EC.presence_of_element_located((AppiumBy.ID, rid))
                )
                logger.info("已检测到商家列表 %s", rid)
                return True
            except TimeoutException:
                continue
            except WebDriverException as ex:
                if self._is_transient_driver_error(ex):
                    self._last_merchant_wait_uia2_dead = True
                    if self._requires_new_driver_session(ex):
                        self._driver_uia2_mark_dead()
                    logger.error(
                        "等待商家列表时 instrumentation 崩溃（rid=%s）：%s",
                        rid,
                        ex,
                    )
                    return False
                raise
        return False


class TakeoutPage(TakeoutPageBase):
    """Home 等引用：马尼拉定位后进旺旺店。"""

    def run_main_flow(self) -> bool:
        """马尼拉 → 外卖 Tab → 列表 → 进店。"""
        logger.info("TakeoutPage.run_main_flow：马尼拉定位 → 旺旺超市进店")
        if not self.ensure_takeout_city_manila():
            logger.warning("马尼拉切换未完全确认，仍继续尝试进店")
        if not self.ensure_takeout_tab():
            return False
        if not self.wait_merchant_list_present(timeout=18.0):
            logger.error("等待商家列表超时")
            return False
        return self.scroll_to_and_open_shop(ensure_takeout_tab_first=False)


def open_wangwang_supermarket_from_takeout_home(
    driver: WebDriver,
    shop_name: str = "旺旺超市 WWCS",
    ensure_manila_city: bool = True,
) -> bool:
    """可选先马尼拉定位，再进店 shop_name。"""
    page = TakeoutPageBase(driver)
    if ensure_manila_city and not page.ensure_takeout_city_manila():
        logger.warning("马尼拉定位流程告警，仍尝试找店…")
    if not page.ensure_takeout_tab():
        return False
    page.wait_merchant_list_present(timeout=15.0)
    return page.scroll_to_and_open_shop(
        shop_name=shop_name, ensure_takeout_tab_first=False
    )
