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

    def _visible_in_bottom_band(self, el, y_min: int) -> bool:
        try:
            return el.is_displayed() and int(el.location.get("y", 0)) >= y_min
        except Exception:
            return False

    def _first_bottom_band_click_target(self, by: str, value: str, y_min: int):
        try:
            for el in self.driver.find_elements(by, value):
                if self._visible_in_bottom_band(el, y_min):
                    return self._nearest_clickable_ancestor(el)
        except Exception:
            pass
        return None

    def _find_bottom_tab_by_label_resource_id(self, y_min: int):
        for pkg in _PACKAGES:
            for label in ("外卖", "美食外卖"):
                xp = (
                    f'//android.widget.TextView[@resource-id="{pkg}:id/tab_text_tv" '
                    f'and @text="{label}"]'
                )
                hit = self._first_bottom_band_click_target(
                    AppiumBy.XPATH, xp, y_min
                )
                if hit:
                    return hit
        return None

    def _find_bottom_tab_by_icon_slot(self, y_min: int):
        for pkg in _PACKAGES:
            try:
                els = self.driver.find_elements(
                    AppiumBy.ID, f"{pkg}:id/tab_icon_iv"
                )
                if len(els) >= 2 and self._visible_in_bottom_band(els[1], y_min):
                    return self._nearest_clickable_ancestor(els[1])
            except Exception:
                pass
        return None

    def _find_bottom_tab_by_xpath_candidates(self, y_min: int):
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
            hit = self._first_bottom_band_click_target(by, xp, y_min)
            if hit:
                return hit
        return None

    def _find_bottom_tab_by_uiautomator(self, y_min: int):
        for text in ("外卖", "美食外卖"):
            uia = f'new UiSelector().text("{text}")'
            hit = self._first_bottom_band_click_target(
                AppiumBy.ANDROID_UIAUTOMATOR, uia, y_min
            )
            if hit:
                return hit
        for needle in ("外卖", "美食外卖"):
            esc = needle.replace('"', '\\"')
            for sel in (
                f'new UiSelector().descriptionContains("{esc}").clickable(true)',
                f'new UiSelector().description("{esc}")',
            ):
                hit = self._first_bottom_band_click_target(
                    AppiumBy.ANDROID_UIAUTOMATOR, sel, y_min
                )
                if hit:
                    return hit
        return None

    def _find_bottom_nav_takeout_element(self):
        """底部「外卖」Tab 可点击元素（排除屏上方同名文案）。"""
        h = self._window_height()
        # 部分机型底栏略高，0.72 过严会漏掉 Tab
        y_min = int(h * 0.68)
        for finder in (
            self._find_bottom_tab_by_label_resource_id,
            self._find_bottom_tab_by_icon_slot,
            self._find_bottom_tab_by_xpath_candidates,
            self._find_bottom_tab_by_uiautomator,
        ):
            hit = finder(y_min)
            if hit:
                return hit
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

    def _backtrack_to_takeout_home(self, max_backs: int = 2) -> bool:
        """If currently inside a shop/detail page, go back until the merchant list is visible."""
        for i in range(max_backs):
            try:
                self.driver.back()
                logger.info("未见底栏外卖 Tab，先返回上一层（第 %d 次）", i + 1)
            except Exception as ex:
                logger.warning("返回上一层失败: %s", ex)
                return False
            time.sleep(0.8)
            try:
                if self.is_on_takeout_merchant_home():
                    logger.info("返回后已看到外卖商家列表")
                    return True
            except WebDriverException as ex:
                if self._requires_new_driver_session(ex):
                    self._driver_uia2_mark_dead()
                    logger.error("返回检测外卖首页失败（UiAutomator2 不可用）：%s", ex)
                    return False
                if not self._is_transient_driver_error(ex):
                    raise
        return False

    def _looks_inside_takeout_shop(self) -> bool:
        """Cheap page-source signal for shop/detail/cart pages where bottom tabs are hidden."""
        try:
            src = self.driver.page_source or ""
        except Exception:
            return False
        needles = ("购物车", "去结算", "起送", "配送费", "选规格", "加入购物车")
        return any(n in src for n in needles)

    def _looks_inside_takeout_address_flow(self) -> bool:
        """Recognize nested address pages where bottom-tab coordinate taps are unsafe."""
        try:
            src = self.driver.page_source or ""
        except Exception:
            return False
        strong = (
            "新增收货地址",
            "定位地址",
            "联系人电话",
            "地址图片",
            "请输入手机号",
        )
        if any(marker in src for marker in strong):
            return True
        if "温馨提示" in src and "上传图片" in src:
            return True
        return "配送至" in src and "新增地址" in src

    def _recover_from_takeout_address_flow(self, max_backs: int = 5) -> bool:
        try:
            self.driver.hide_keyboard()
            logger.info("地址流程恢复：已先收起输入法")
        except Exception:
            pass
        for index in range(max_backs):
            if self.is_on_takeout_merchant_home():
                return True
            try:
                self.driver.back()
                logger.info("地址流程恢复：返回上一层（第 %d 次）", index + 1)
            except Exception as exc:
                logger.warning("地址流程恢复返回失败: %s", type(exc).__name__)
                return False
            time.sleep(0.6)
            if self.is_on_takeout_merchant_home():
                logger.info("地址流程恢复：已回到外卖商家列表")
                return True
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

        if self._looks_inside_takeout_address_flow():
            logger.info("当前位于新增/定位地址流程，先收键盘并逐层返回")
            if self._recover_from_takeout_address_flow():
                return True
            if self._looks_inside_takeout_address_flow():
                logger.error("地址流程恢复失败，拒绝使用底栏坐标兜底以免误触表单")
                return False

        if self._looks_inside_takeout_shop():
            logger.info("当前像店铺详情/购物车页，先返回外卖商家列表")
            if self._backtrack_to_takeout_home():
                return True

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
                if i == 0 and self._backtrack_to_takeout_home():
                    return True
                tab_el = self._find_bottom_nav_takeout_element()
                if tab_el:
                    try:
                        tab_el.click()
                        logger.info("返回后已点击底部外卖 Tab")
                    except Exception as ex:
                        logger.warning("返回后点击外卖 Tab 失败: %s", ex)
                if self._tap_bottom_takeout_tab_geometry_fallback():
                    logger.info("坐标兜底后已出现商家列表")

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

    def _tap_location_permission_label(self, labels: Sequence[str]) -> bool:
        for label in labels:
            safe = label.replace('"', "")
            xp = (
                f'//*[@text="{safe}" or @content-desc="{safe}"]'
            )
            try:
                for element in self.driver.find_elements(AppiumBy.XPATH, xp):
                    if not element.is_displayed():
                        continue
                    element.click()
                    logger.info("定位授权流程已点击「%s」", label)
                    time.sleep(0.6)
                    return True
            except Exception:
                continue
        return False

    def _return_to_app_after_location_permission(self) -> None:
        for _ in range(3):
            try:
                if self.driver.current_package in _PACKAGES:
                    return
            except Exception:
                break
            try:
                self.driver.back()
                time.sleep(0.5)
            except Exception:
                break
        try:
            self.driver.activate_app(_PACKAGES[0])
            time.sleep(0.8)
        except Exception:
            pass

    def _ensure_location_permission_enabled(self) -> bool:
        """Grant precise foreground location via runtime dialog or app settings."""
        acted = False
        permission_needles = (
            "定位权限未开启",
            "请前往设置中心打开定位权限",
            "获取位置信息",
            "精确位置",
            "仅在使用中允许",
            "使用应用时允许",
            "本次运行允许",
            "应用权限",
        )
        for _ in range(12):
            try:
                src = self.driver.page_source or ""
            except Exception:
                src = ""
            if not any(needle in src for needle in permission_needles):
                if acted:
                    self._return_to_app_after_location_permission()
                    logger.info("定位权限流程完成")
                return True
            if (
                "请前往设置中心打开定位权限" in src
                or "定位权限未开启" in src
            ) and self._tap_location_permission_label(
                ("立即开启", "确定", "去设置", "前往设置")
            ):
                acted = True
                continue
            if "应用权限" in src and self._tap_location_permission_label(
                ("应用权限", "权限")
            ):
                acted = True
                continue
            if (
                "位置信息" in src
                and "仅在使用中允许" not in src
                and self._tap_location_permission_label(("位置信息", "位置"))
            ):
                acted = True
                continue
            if "精确位置" in src:
                if self._tap_location_permission_label(("精确位置",)):
                    acted = True
            if self._tap_location_permission_label(
                ("仅在使用中允许", "使用应用时允许")
            ):
                acted = True
                self._return_to_app_after_location_permission()
                logger.info("已开启精确的使用中定位权限")
                return True
            # 不选择“一次性允许”；自动化回归需要后续会话仍可使用定位。
            time.sleep(0.4)
        logger.error("定位权限提示存在，但未能完成精确的使用中授权")
        return False

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
        if not self._ensure_location_permission_enabled():
            logger.error("定位权限未开启，终止城市选择")
            return False
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
            return True
        else:
            logger.error("未从顶栏文案确认马尼拉")
            return False

    def _uia_scroll_into_view(
        self,
        list_resource_id: str,
        shop_name: str,
        use_contains: bool,
        max_search_swipes: int = 4,
    ) -> bool:
        """在指定 resourceId 列表内 UiScrollable.scrollIntoView 到店名。"""
        safe = shop_name.replace('"', '\\"')
        if use_contains:
            target = f'new UiSelector().textContains("{safe}")'
        else:
            target = f'new UiSelector().text("{safe}")'
        ms = max(1, min(int(max_search_swipes), 8))
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
        max_search_swipes: int = 4,
    ) -> bool:
        """UiScrollable 后必须用 XPath 确认屏上可见可点击店行。"""
        logger.info("UiScrollable：在 %s 中 %s …", rid, log_hint)
        if not self._uia_scroll_into_view(
            rid, uia_label, use_contains, max_search_swipes=max_search_swipes
        ):
            return False
        time.sleep(0.45)
        if self._find_visible_clickable_row(shop_name, find_budget_sec=1.5):
            logger.info(
                "UiScrollable 后已确认屏上可见可点击店行「%s」（%s）",
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

    def _active_package_candidates(self) -> Tuple[str, ...]:
        """Current package first; avoid expensive scans on inactive package flavors."""
        try:
            current = (self.driver.current_package or "").strip()
        except Exception:
            current = ""
        if current in _PACKAGES:
            return (current,)
        return (_PACKAGES[0],)

    def _try_scroll_merchant_list(self, shop_name: str) -> bool:
        """UiScrollable 多策略找店，成功以屏上 XPath 为准。"""
        for pkg in self._active_package_candidates():
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
        for pkg in self._active_package_candidates():
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

    def _shop_substring_candidates(self, shop_name: str) -> Tuple[str, ...]:
        if "WWCS" in shop_name.upper():
            return ("WWCS", "旺旺超市")
        if "旺旺" in shop_name:
            return ("旺旺超市",)
        return (shop_name[: min(6, len(shop_name))],)

    def _shop_search_needles(self, shop_name: str) -> Tuple[str, ...]:
        out: list[str] = []
        for text in self._shop_substring_candidates(shop_name) + self._shop_name_text_variants(
            shop_name
        ):
            if text and text not in out:
                out.append(text)
        return tuple(out)

    def _find_row_by_scoped_uia(self, needles: Sequence[str], expired) -> Optional[object]:
        for pkg in _PACKAGES:
            if expired():
                break
            for needle in needles:
                if expired():
                    break
                el = self._uia_find_tv_merchant_name_contains(pkg, needle)
                hit = self._shop_row_click_target(el) if el else None
                if hit:
                    return hit
        return None

    def _hit_row_xpath(self, xp: str, expired) -> Optional[object]:
        if expired():
            return None
        el = self._first_displayed(self.driver.find_elements(AppiumBy.XPATH, xp))
        return self._shop_row_click_target(el)

    def _find_row_by_scoped_xpath(
        self,
        texts: Sequence[str],
        sub_candidates: Sequence[str],
        expired,
    ) -> Optional[object]:
        exact_fns = (
            _scoped_tv_merchant_name_exact,
            _scoped_row_tab_content_xpath_exact,
            _scoped_row_xpath_exact_name,
            _scoped_shop_title_textview_exact,
        )
        contains_fns = (
            _scoped_tv_merchant_name_contains,
            _scoped_row_tab_content_xpath_contains,
            _scoped_row_xpath_contains_name,
        )
        for pkg in _PACKAGES:
            if expired():
                break
            for text in texts:
                for xp_fn in exact_fns:
                    hit = self._hit_row_xpath(xp_fn(pkg, text), expired)
                    if hit:
                        return hit
            for sub in sub_candidates:
                for xp_fn in contains_fns:
                    hit = self._hit_row_xpath(xp_fn(pkg, sub), expired)
                    if hit:
                        return hit
                if len(sub) >= 4:
                    hit = self._hit_row_xpath(
                        _scoped_shop_title_textview_contains(pkg, sub), expired
                    )
                    if hit:
                        return hit
        return None

    def _find_row_by_legacy_xpath(
        self,
        texts: Sequence[str],
        sub_candidates: Sequence[str],
        expired,
    ) -> Optional[object]:
        for xp_fn, values in (
            (_row_tab_content_xpath_exact, texts),
            (_row_xpath_exact_name, texts),
            (_row_tab_content_xpath_contains, sub_candidates),
            (_row_xpath_contains_name, sub_candidates),
            (_name_xpath_exact, texts),
        ):
            for value in values:
                for pkg in _PACKAGES:
                    hit = self._hit_row_xpath(xp_fn(pkg, value), expired)
                    if hit:
                        return hit
        return None

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
        sub_candidates = self._shop_substring_candidates(shop_name)
        needles_uia = self._shop_search_needles(shop_name)

        with self._zero_implicit_wait():
            hit = self._find_row_by_scoped_uia(needles_uia, expired)
            if hit:
                return hit
            hit = self._find_row_by_scoped_xpath(texts, sub_candidates, expired)
            if hit:
                return hit

            if allow_slow_legacy_xpath and not expired():
                return self._find_row_by_legacy_xpath(texts, sub_candidates, expired)
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

    def _click_shop_row_and_wait(self, el, success_log: str, *args) -> bool:
        if not el:
            return False
        try:
            el.click()
            logger.info(success_log, *args)
            time.sleep(1.2)
            return True
        except Exception as ex:
            logger.warning("点击店铺元素失败: %s", ex)
            return False

    def _find_and_click_shop_on_current_screen(
        self, shop_name: str, find_budget_sec: float, success_log: str, *args
    ) -> bool:
        el = self._find_visible_clickable_row(
            shop_name, find_budget_sec=find_budget_sec
        )
        return self._click_shop_row_and_wait(el, success_log, *args)

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

        _shop_find_budget = 3.0
        _shop_quick_budget = 1.2
        logger.info(
            "当前屏查找「%s」（限时约 %.0fs：UiAutomator + 列表内 XPath；"
            "超时后滑动列表，最后再尝试一次全页慢路径）…",
            shop_name,
            _shop_find_budget,
        )
        if self._find_and_click_shop_on_current_screen(
            shop_name,
            _shop_find_budget,
            "已点击店铺行/店名（当前屏可见，未先滚列表），等待进入详情…",
        ):
            return True

        logger.info("当前屏未见目标店，先手势翻列表（避免易触发刷新的中线滑动）…")
        for pre_i in range(10):
            self._swipe_merchant_list_once()
            time.sleep(0.20)
            if self._find_and_click_shop_on_current_screen(
                shop_name,
                _shop_quick_budget,
                "已点击店铺行/店名（预滑动第 %d 次后可见），等待进入详情…",
                pre_i + 1,
            ):
                return True

        logger.info("预滑动未见店，再尝试 UiScrollable（次数已收紧）…")
        self._try_scroll_merchant_list(shop_name)
        time.sleep(settle_sec)

        if self._find_and_click_shop_on_current_screen(
            shop_name,
            _shop_quick_budget,
            "已点击店铺行/店名，等待进入详情…",
        ):
            return True

        for i in range(max_swipes):
            self._swipe_merchant_list_once()
            time.sleep(0.22)
            if self._find_and_click_shop_on_current_screen(
                shop_name,
                _shop_quick_budget,
                "兜底滑动第 %d 次后已点击店铺「%s」",
                i + 1,
                shop_name,
            ):
                return True

        logger.info(
            "快路径未命中「%s」，最后一次允许全页 XPath（限时约 25s）…",
            shop_name,
        )
        el = self._find_visible_clickable_row(
            shop_name,
            allow_slow_legacy_xpath=True,
            find_budget_sec=25.0,
        )
        if self._click_shop_row_and_wait(
            el, "全页慢路径命中后已点击店铺「%s」", shop_name
        ):
            return True

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
        logger.error("马尼拉定位未确认，终止找店")
        return False
    if not page.ensure_takeout_tab():
        return False
    page.wait_merchant_list_present(timeout=15.0)
    return page.scroll_to_and_open_shop(
        shop_name=shop_name, ensure_takeout_tab_first=False
    )
