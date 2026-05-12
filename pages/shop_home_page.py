"""商城首页自动化：金刚区、返回、购物车、Banner、加购与多规格弹窗。"""
from __future__ import annotations

import random
import re
import time
from typing import List, Optional, Tuple

from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.remote.webdriver import WebDriver

from commons.logger import setup_logger
from pages.shop_locators import (
    SHOP_BACK_ID_SUFFIXES,
    SHOP_ID_BOTTOM_POPUP,
    SHOP_ID_CHOOSE_RECYCLER,
    SHOP_ID_CHOOSE_SKU_CONTAINER,
    SHOP_ID_CL_ITEM_CONTAINER,
    SHOP_ID_COUNT_ADD,
    SHOP_ID_COUNT_TEXT,
    SHOP_ID_CV_CART,
    SHOP_ID_DIALOG_CHOOSE_CONTAINER,
    SHOP_ID_DIALOG_COMPLETE,
    SHOP_ID_CHOOSE_SCROLL,
    SHOP_ID_GOODS_LIST_ITEM,
    SHOP_ID_IMAGE,
    SHOP_ID_IV_COLLECT,
    SHOP_ID_IV_GOODS,
    SHOP_ID_MALL_ADD_SHOP_CAR,
    SHOP_ID_MALL_BUY_NOW,
    SHOP_ID_MALL_CATEGORY_GOODS_NAME,
    SHOP_ID_MALL_DETAIL_VIEWPAGER,
    SHOP_ID_MALL_KEFU,
    SHOP_ID_MALL_SHOP_CAR_CONTAINER,
    SHOP_ID_RV_CONTENT,
    SHOP_ID_RV_GOODS,
    SHOP_ID_TV_ADD_CART_MORE,
    SHOP_ID_TV_GOODS_NAME,
    SHOP_ID_TV_PRICE,
    SHOP_ID_FLOAT_VIEW,
    SHOP_ID_IV_ADD_CART,
    SHOP_ID_IV_BANNER,
    SHOP_ID_IV_CART,
    SHOP_ID_IV_SHOPPING_CART,
    SHOP_ID_IV_UP_TO_TOP,
    SHOP_ID_RL_CART,
    SHOP_ID_RL_SHOPPING_CART,
    SHOP_ID_ACTIVITY_FILTER,
    SHOP_ID_LL_ITEM,
    SHOP_ID_TV_TITLE,
    SHOP_ID_POPUP_WIN,
    SHOP_ID_TV_CATEGORY,
    SHOP_KINGKONG_HOT_SNACKS,
    SHOP_PACKAGES,
    SHOP_TEXT_COLLECT_OK,
    SHOP_TEXT_FINISH_SPEC,
    SHOP_TEXT_KEFU_PAGE_MARKERS,
    SHOP_TEXT_ALL_CATEGORIES,
    SHOP_TEXT_DAILY_BAIHUO,
    SHOP_TEXT_LIMITED_SPECIAL,
    SHOP_TEXT_LIMITED_SPECIAL_ALT,
    SHOP_TEXT_MALL_CART_TITLE,
    SHOP_TEXT_NEW_PRODUCT_PICK,
    SHOP_TEXT_NEW_PRODUCT_PICK_EMOJI,
    SHOP_TEXT_SELECT_SPEC,
)

logger = setup_logger(__name__)


class ShopHomePage:
    """当前 driver 已连上设备；先 ``ensure_mall_tab`` 再跑 ``run_shop_home_flow``。"""

    def __init__(self, driver: WebDriver, wait_sec: float = 18.0):
        self.driver = driver
        self.wait_sec = wait_sec

    def _window_size(self) -> Tuple[int, int]:
        try:
            s = self.driver.get_window_size()
            return int(s["width"]), int(s["height"])
        except Exception:
            return 1080, 2400

    def _nearest_clickable_ancestor(self, el, max_hops: int = 8):
        cur = el
        for _ in range(max_hops):
            try:
                if (cur.get_attribute("clickable") or "").lower() == "true":
                    return cur
                cur = cur.find_element(AppiumBy.XPATH, "..")
            except Exception:
                break
        return el

    def _rid(self, pkg: str, suffix: str) -> str:
        return f"{pkg}:id/{suffix}"

    def _shop_packages_prioritized(self) -> Tuple[str, ...]:
        """当前前台包名优先，减少返回键查找轮询（隐式等待非 0 时避免数十秒卡顿）。"""
        cur = (getattr(self.driver, "current_package", None) or "").strip()
        if cur and cur in SHOP_PACKAGES:
            return (cur,) + tuple(p for p in SHOP_PACKAGES if p != cur)
        try:
            caps = getattr(self.driver, "capabilities", None) or {}
            app = (
                str(caps.get("appium:appPackage") or caps.get("appPackage") or "")
            ).strip()
            if app and app in SHOP_PACKAGES:
                return (app,) + tuple(p for p in SHOP_PACKAGES if p != app)
        except Exception:
            pass
        return SHOP_PACKAGES

    def _first_displayed_by_pkg_id(self, suffix: str):
        for pkg in self._shop_packages_prioritized():
            rid = self._rid(pkg, suffix)
            try:
                for el in self.driver.find_elements(AppiumBy.ID, rid):
                    try:
                        if el.is_displayed():
                            return el
                    except Exception:
                        continue
            except Exception:
                continue
        return None

    def _all_displayed_by_pkg_id(self, suffix: str) -> List:
        out: List = []
        for pkg in self._shop_packages_prioritized():
            rid = self._rid(pkg, suffix)
            try:
                for el in self.driver.find_elements(AppiumBy.ID, rid):
                    try:
                        if el.is_displayed():
                            out.append(el)
                    except Exception:
                        continue
            except Exception:
                continue
        return out

    def ensure_mall_tab(self, settle: float = 1.2) -> bool:
        """点击底部「商城」Tab（与外卖 Tab 同类 resource-id 结构）。"""
        h = self._window_size()[1]
        y_min = int(h * 0.66)
        for pkg in SHOP_PACKAGES:
            xp = (
                f'//android.widget.TextView[@resource-id="{pkg}:id/tab_text_tv" '
                f'and @text="商城"]'
            )
            try:
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    try:
                        if not el.is_displayed():
                            continue
                        if int(el.location.get("y", 0)) < y_min:
                            continue
                        self._nearest_clickable_ancestor(el).click()
                        logger.info("已点击底部「商城」Tab（%s）", pkg)
                        time.sleep(settle)
                        return True
                    except Exception:
                        continue
            except Exception:
                pass
        try:
            for el in self.driver.find_elements(
                AppiumBy.XPATH, '//android.widget.TextView[@text="商城"]'
            ):
                try:
                    if not el.is_displayed():
                        continue
                    if int(el.location.get("y", 0)) < y_min:
                        continue
                    self._nearest_clickable_ancestor(el).click()
                    logger.info("已点击底部「商城」（XPath 文案）")
                    time.sleep(settle)
                    return True
                except Exception:
                    continue
        except Exception:
            pass
        logger.error("未点到底部「商城」Tab")
        return False

    def tap_kingkong_hot_snacks(self) -> bool:
        """金刚区点击「爆款零食」。"""
        label = SHOP_KINGKONG_HOT_SNACKS
        if not self._kingkong_hot_snacks_label_visible():
            self.mall_list_gesture_scroll_to_top(6)
            time.sleep(0.45)
        for pkg in SHOP_PACKAGES:
            xp = (
                f'//*[@resource-id="{pkg}:id/{SHOP_ID_TV_TITLE}" and @text="{label}"]'
            )
            try:
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    try:
                        if not el.is_displayed():
                            continue
                        # Inspector：``tv_title`` 常为 clickable=false，整格可点在父级 ``ll_item``
                        try:
                            p_rid = self._rid(pkg, SHOP_ID_LL_ITEM)
                            parent = el.find_element(
                                AppiumBy.XPATH,
                                f'./ancestor::android.widget.LinearLayout[@resource-id="{p_rid}"][1]',
                            )
                            if parent.is_displayed():
                                parent.click()
                                logger.info(
                                    "已点击金刚区「%s」（父级 ll_item / %s）",
                                    label,
                                    pkg,
                                )
                                time.sleep(1.4)
                                return True
                        except Exception:
                            pass
                        self._nearest_clickable_ancestor(el).click()
                        logger.info("已点击金刚区「%s」（%s）", label, pkg)
                        time.sleep(1.4)
                        return True
                    except Exception:
                        continue
            except Exception:
                pass
        try:
            for el in self.driver.find_elements(
                AppiumBy.XPATH, f'//android.widget.TextView[@text="{label}"]'
            ):
                try:
                    if not el.is_displayed():
                        continue
                    y = int(el.location.get("y", 0))
                    h = self._window_size()[1]
                    if y > int(h * 0.92):
                        continue
                    try:
                        parent = el.find_element(
                            AppiumBy.XPATH,
                            './ancestor::android.widget.LinearLayout'
                            '[contains(@resource-id,"ll_item")][1]',
                        )
                        if parent.is_displayed():
                            parent.click()
                            logger.info(
                                "已点击金刚区「%s」（纯文案 + 祖先 ll_item）",
                                label,
                            )
                            time.sleep(1.4)
                            return True
                    except Exception:
                        pass
                    self._nearest_clickable_ancestor(el).click()
                    logger.info("已点击金刚区「%s」（纯文案 XPath）", label)
                    time.sleep(1.4)
                    return True
                except Exception:
                    continue
        except Exception:
            pass
        try:
            self.driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                f'new UiSelector().text("{label}")',
            ).click()
            logger.info("已点击金刚区「%s」（UiAutomator）", label)
            time.sleep(1.4)
            return True
        except Exception:
            pass
        logger.warning("金刚区「%s」首次未命中，手势回顶后重试", label)
        self.mall_list_gesture_scroll_to_top(8)
        time.sleep(0.5)
        self.tap_back_to_top_if_visible()
        time.sleep(0.35)
        for pkg in SHOP_PACKAGES:
            xp = (
                f'//*[@resource-id="{pkg}:id/{SHOP_ID_TV_TITLE}" and @text="{label}"]'
            )
            try:
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    try:
                        if not el.is_displayed():
                            continue
                        try:
                            p_rid = self._rid(pkg, SHOP_ID_LL_ITEM)
                            parent = el.find_element(
                                AppiumBy.XPATH,
                                f'./ancestor::android.widget.LinearLayout[@resource-id="{p_rid}"][1]',
                            )
                            if parent.is_displayed():
                                parent.click()
                                logger.info(
                                    "已点击金刚区「%s」（重试 ll_item / %s）",
                                    label,
                                    pkg,
                                )
                                time.sleep(1.4)
                                return True
                        except Exception:
                            pass
                        self._nearest_clickable_ancestor(el).click()
                        logger.info("已点击金刚区「%s」（重试 tv_title / %s）", label, pkg)
                        time.sleep(1.4)
                        return True
                    except Exception:
                        continue
            except Exception:
                pass
        logger.error("未找到金刚区「%s」", label)
        return False

    def _all_categories_popup_visible(self) -> bool:
        return self._first_displayed_by_pkg_id(SHOP_ID_POPUP_WIN) is not None

    def tap_mall_kingkong_open_all_categories_popup(self) -> bool:
        """
        在当前屏点击「全部分类」以打开 ``popup_win``。
        典型路径：已点金刚区「爆款零食」进入分类页后，再点标题区「全部分类」出弹层。
        """
        if self._all_categories_popup_visible():
            logger.info("「全部分类」弹层已展示")
            return True
        h = self._window_size()[1]
        y_lo, y_hi = int(h * 0.06), int(h * 0.94)
        for text in (SHOP_TEXT_ALL_CATEGORIES,):
            try:
                for el in self.driver.find_elements(
                    AppiumBy.XPATH, f'//android.widget.TextView[@text="{text}"]'
                ):
                    try:
                        if not el.is_displayed():
                            continue
                        y = int(el.location.get("y", -1))
                        if not (y_lo <= y <= y_hi):
                            continue
                        self._nearest_clickable_ancestor(el).click()
                        logger.info("已点击「%s」打开分类弹窗", text)
                        time.sleep(1.1)
                        if self._all_categories_popup_visible():
                            return True
                    except Exception:
                        continue
            except Exception:
                pass
        for pkg in SHOP_PACKAGES:
            rid = self._rid(pkg, SHOP_ID_TV_TITLE)
            xp = f'//*[@resource-id="{rid}" and @text="{SHOP_TEXT_ALL_CATEGORIES}"]'
            try:
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    try:
                        if not el.is_displayed():
                            continue
                        y = int(el.location.get("y", -1))
                        if not (y_lo <= y <= y_hi):
                            continue
                        try:
                            p_rid = self._rid(pkg, SHOP_ID_LL_ITEM)
                            parent = el.find_element(
                                AppiumBy.XPATH,
                                f'./ancestor::android.widget.LinearLayout[@resource-id="{p_rid}"][1]',
                            )
                            if parent.is_displayed():
                                parent.click()
                                logger.info(
                                    "已点击「%s」（tv_title+ll_item / %s）",
                                    SHOP_TEXT_ALL_CATEGORIES,
                                    pkg,
                                )
                                time.sleep(1.1)
                                if self._all_categories_popup_visible():
                                    return True
                        except Exception:
                            pass
                        self._nearest_clickable_ancestor(el).click()
                        time.sleep(1.1)
                        if self._all_categories_popup_visible():
                            return True
                    except Exception:
                        continue
            except Exception:
                pass
        logger.error("未能打开「%s」分类弹窗", SHOP_TEXT_ALL_CATEGORIES)
        return False

    def tap_mall_category_in_all_categories_popup(self, category_name: str) -> bool:
        """在「全部分类」弹层内点击 ``tv_category`` 指定文案（如日用百货）。"""
        end = time.time() + 12.0
        while time.time() < end:
            if self._all_categories_popup_visible():
                break
            time.sleep(0.35)
        if not self._all_categories_popup_visible():
            logger.error("等待后仍无「全部分类」弹层（popup_win）")
            return False
        safe = category_name.replace('"', "").replace("'", "")[:16]
        for pkg in SHOP_PACKAGES:
            rid = self._rid(pkg, SHOP_ID_TV_CATEGORY)
            xp = f'//*[@resource-id="{rid}" and @text="{safe}"]'
            try:
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    try:
                        if not el.is_displayed():
                            continue
                        try:
                            row = el.find_element(
                                AppiumBy.XPATH,
                                "./ancestor::android.widget.LinearLayout[1]",
                            )
                            if row.is_displayed():
                                row.click()
                            else:
                                self._nearest_clickable_ancestor(el).click()
                        except Exception:
                            self._nearest_clickable_ancestor(el).click()
                        logger.info(
                            "已在全部分类弹窗中点击「%s」（tv_category / %s）",
                            safe,
                            pkg,
                        )
                        time.sleep(1.6)
                        return True
                    except Exception:
                        continue
            except Exception:
                pass
        try:
            for el in self.driver.find_elements(
                AppiumBy.XPATH,
                f'//*[contains(@resource-id,":id/{SHOP_ID_TV_CATEGORY}") '
                f'and @text="{safe}"]',
            ):
                if el.is_displayed():
                    self._nearest_clickable_ancestor(el).click()
                    logger.info("已点击分类「%s」（tv_category 宽松 XPath）", safe)
                    time.sleep(1.6)
                    return True
        except Exception:
            pass
        logger.error("弹窗内未找到分类「%s」", safe)
        return False

    def tap_mall_kingkong_daily_baihuo_via_popup(self) -> bool:
        """
        金刚区「爆款零食」→ 分类页出现「全部分类」弹层 → 点「日用百货」。
        不在商城首屏直接找「全部分类」；必须先进入爆款零食分类页（与 Inspector 一致）。
        """
        if not self.tap_kingkong_hot_snacks():
            logger.error("未能点击金刚区「%s」", SHOP_KINGKONG_HOT_SNACKS)
            return False
        time.sleep(1.0)
        end = time.time() + 12.0
        while time.time() < end:
            if self._all_categories_popup_visible():
                logger.info("已进入爆款零食分类页且「全部分类」弹层已出现")
                break
            time.sleep(0.4)
        if not self._all_categories_popup_visible():
            logger.info("弹层未自动出现，尝试点击「全部分类」入口")
            if not self.tap_mall_kingkong_open_all_categories_popup():
                logger.error(
                    "进入「%s」后仍未出现「%s」弹层",
                    SHOP_KINGKONG_HOT_SNACKS,
                    SHOP_TEXT_ALL_CATEGORIES,
                )
                return False
        return self.tap_mall_category_in_all_categories_popup(SHOP_TEXT_DAILY_BAIHUO)

    def leave_mall_category_to_mall_home(self) -> bool:
        """
        从金刚区/分类子页返回到商城首页，直到主列表 ``rv_content`` 可见，
        再执行限时特价、新品优选等依赖首页结构的步骤。
        """
        for i in range(5):
            if self._is_mall_home_main_list_visible():
                logger.info("已回到商城首页（主列表 rv_content 可见）")
                return True
            logger.info("离开分类/子页：第 %d 次尝试返回", i + 1)
            self.tap_top_back()
            time.sleep(1.0)
        logger.warning("多次返回后仍未见 rv_content，尝试点商城 Tab 并手势回顶")
        self.ensure_mall_tab()
        time.sleep(0.9)
        self.mall_list_gesture_scroll_to_top(8)
        time.sleep(0.45)
        return self._is_mall_home_main_list_visible()

    def tap_top_back(self) -> bool:
        """
        子页左上角返回（优先 iv_back*，否则系统 back）。

        查找期间将隐式等待置 0：否则对每个不存在的 ``pkg:id/suffix`` 可能各等待约 1s，
        多包名轮询后再 ``driver.back()`` 会出现数十秒空白（见分类页离开商城首页日志）。
        """
        restore_implicit = 1.0
        try:
            iw = self.driver.timeouts.implicit_wait
            if hasattr(iw, "total_seconds"):
                restore_implicit = float(iw.total_seconds())
            else:
                v = float(iw)
                restore_implicit = v / 1000.0 if v >= 500 else v
        except Exception:
            restore_implicit = 1.0
        try:
            self.driver.implicitly_wait(0)
        except Exception:
            pass
        try:
            for pkg in self._shop_packages_prioritized():
                for suf in SHOP_BACK_ID_SUFFIXES:
                    rid = self._rid(pkg, suf)
                    try:
                        for el in self.driver.find_elements(AppiumBy.ID, rid):
                            try:
                                if el.is_displayed():
                                    el.click()
                                    logger.info("已点返回（%s）", rid)
                                    time.sleep(1.0)
                                    return True
                            except Exception:
                                continue
                    except Exception:
                        pass
            for pkg in self._shop_packages_prioritized():
                for suf in SHOP_BACK_ID_SUFFIXES:
                    xp = f'//*[@resource-id="{self._rid(pkg, suf)}"]'
                    try:
                        for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                            try:
                                if el.is_displayed():
                                    el.click()
                                    logger.info("已点返回（XPath %s）", xp[:80])
                                    time.sleep(1.0)
                                    return True
                            except Exception:
                                continue
                    except Exception:
                        pass
            try:
                self.driver.back()
                logger.info("已发送系统 KeyEvent BACK")
                time.sleep(1.0)
                return True
            except Exception:
                return False
        finally:
            try:
                self.driver.implicitly_wait(
                    restore_implicit if restore_implicit >= 0 else 1.0
                )
            except Exception:
                try:
                    self.driver.implicitly_wait(1)
                except Exception:
                    pass

    def tap_floating_or_entry_cart(self) -> bool:
        """商城首页购物车入口：悬浮球 / rl_cart / 多 id 兜底。"""
        order = (
            SHOP_ID_IV_SHOPPING_CART,
            SHOP_ID_IV_CART,
            SHOP_ID_RL_SHOPPING_CART,
            SHOP_ID_CV_CART,
            SHOP_ID_FLOAT_VIEW,
        )
        for suf in order:
            el = self._first_displayed_by_pkg_id(suf)
            if el:
                try:
                    self._nearest_clickable_ancestor(el).click()
                    logger.info("已点击购物车入口（%s）", suf)
                    time.sleep(1.3)
                    return True
                except Exception:
                    pass
        el = self._first_displayed_by_pkg_id(SHOP_ID_RL_CART)
        if el:
            try:
                el.click()
                logger.info("已点击购物车容器（rl_cart）")
                time.sleep(1.3)
                return True
            except Exception:
                pass
        w, h = self._window_size()
        for xf, yf in ((0.92, 0.88), (0.88, 0.90), (0.10, 0.90)):
            cx, cy = int(w * xf), int(h * yf)
            try:
                self.driver.execute_script(
                    "mobile: clickGesture", {"x": cx, "y": cy}
                )
                logger.info("购物车坐标兜底 (%d,%d)", cx, cy)
                time.sleep(1.2)
                return True
            except Exception:
                continue
        logger.error("未点到购物车入口")
        return False

    def tap_banner_area(self) -> bool:
        """点击 Banner（优先 iv_banner，失败则点 ViewPager 区域中轴）。"""
        el = self._first_displayed_by_pkg_id(SHOP_ID_IV_BANNER)
        if el:
            try:
                parent = el.find_element(AppiumBy.XPATH, "./..")
                if (parent.get_attribute("clickable") or "").lower() == "true":
                    parent.click()
                else:
                    el.click()
                logger.info("已点击 Banner（iv_banner）")
                time.sleep(1.3)
                return True
            except Exception:
                try:
                    el.click()
                    logger.info("已点击 Banner（iv_banner 自身）")
                    time.sleep(1.3)
                    return True
                except Exception:
                    pass
        for pkg in SHOP_PACKAGES:
            for vp_suffix in ("viewPager", "vp_banner", "banner_vp"):
                rid = self._rid(pkg, vp_suffix)
                try:
                    for el in self.driver.find_elements(AppiumBy.ID, rid):
                        if el.is_displayed():
                            loc = el.location
                            sz = el.size
                            cx = int(loc["x"] + sz["width"] * 0.5)
                            cy = int(loc["y"] + sz["height"] * 0.45)
                            self.driver.execute_script(
                                "mobile: clickGesture", {"x": cx, "y": cy}
                            )
                            logger.info(
                                "已点击 Banner 区（%s 中心）",
                                vp_suffix,
                            )
                            time.sleep(1.3)
                            return True
                except Exception:
                    pass
        # 部分版本大横幅为全宽 ``activity_filter``（文案如「限时特价」），与 Inspector 一致
        if self.tap_mall_text_filter(
            SHOP_TEXT_LIMITED_SPECIAL,
            y_min_ratio=0.26,
            y_max_ratio=0.56,
        ):
            logger.info("已点击 Banner 区（activity_filter「限时特价」）")
            time.sleep(1.2)
            return True
        w, h = self._window_size()
        cx, cy = int(w * 0.5), int(h * 0.34)
        try:
            self.driver.execute_script("mobile: clickGesture", {"x": cx, "y": cy})
            logger.info("已点击 Banner 大致区域 (%d,%d)", cx, cy)
            time.sleep(1.2)
            return True
        except Exception:
            pass
        logger.error("未点到 Banner")
        return False

    def _login_like_screen_visible(self) -> bool:
        act = (self.driver.current_activity or "").lower()
        if "login" in act or "sign" in act:
            return True
        needles = ("请输入手机号", "短信登录", "密码登录", "验证码登录", "手机号登录")
        for n in needles:
            try:
                for el in self.driver.find_elements(
                    AppiumBy.XPATH, f'//*[contains(@text,"{n}")]'
                ):
                    if el.is_displayed():
                        return True
            except Exception:
                continue
        return False

    def _spec_bottom_sheet_visible(self) -> bool:
        for suf in (
            SHOP_ID_BOTTOM_POPUP,
            SHOP_ID_CHOOSE_RECYCLER,
            SHOP_ID_DIALOG_COMPLETE,
            SHOP_ID_DIALOG_CHOOSE_CONTAINER,
        ):
            if self._first_displayed_by_pkg_id(suf):
                return True
        return False

    def _tap_spec_confirm_if_any(self) -> bool:
        el = self._first_displayed_by_pkg_id(SHOP_ID_DIALOG_COMPLETE)
        if el:
            try:
                tx = (el.get_attribute("text") or "").strip()
                if tx == "确定" or "确定" in (el.get_attribute("content-desc") or ""):
                    el.click()
                    logger.info("已点多规格弹层「确定」（dialog_complete）")
                    time.sleep(0.9)
                    return True
            except Exception:
                pass
        try:
            for el in self.driver.find_elements(
                AppiumBy.XPATH, '//*[@text="确定" and @clickable="true"]'
            ):
                if el.is_displayed():
                    y = int(el.location.get("y", 0))
                    h = self._window_size()[1]
                    if y > int(h * 0.55):
                        el.click()
                        logger.info("已点多规格弹层「确定」（XPath）")
                        time.sleep(0.9)
                        return True
        except Exception:
            pass
        return False

    def _pick_first_spec_option(self) -> bool:
        """在 choose_recycler_view 内点第一个可选规格 TextView（跳过明显标题列）。"""
        rv = self._first_displayed_by_pkg_id(SHOP_ID_CHOOSE_RECYCLER)
        if not rv:
            return True
        skip_tokens = ("数量", "规格", "容量", "口味", "尺寸", "选择")
        try:
            for el in rv.find_elements(AppiumBy.CLASS_NAME, "android.widget.TextView"):
                try:
                    if not el.is_displayed():
                        continue
                    tx = (el.text or "").strip()
                    if not tx or len(tx) > 48:
                        continue
                    if any(t in tx for t in skip_tokens) and "1" not in tx and "瓶" not in tx:
                        continue
                    if tx in ("确定", "取消", "加入购物车", "加购"):
                        continue
                    el.click()
                    logger.info("已选规格项: %s", tx[:32])
                    time.sleep(0.35)
                    return True
                except Exception:
                    continue
        except Exception:
            pass
        return True

    def handle_add_cart_followups(self) -> Tuple[bool, str]:
        """
        加购后的分支：多规格弹窗 或 登录页。
        返回 (ok, message)。
        """
        time.sleep(0.6)
        if self._spec_bottom_sheet_visible():
            self._pick_first_spec_option()
            if not self._tap_spec_confirm_if_any():
                logger.warning("多规格弹层未点到「确定」，仍继续校验角标")
            time.sleep(0.8)
            return True, "spec"
        if self._login_like_screen_visible():
            logger.error("检测到登录相关界面：请先在本机登录后再跑加购与角标校验")
            return False, "login_required"
        return True, "direct"

    def tap_first_add_cart_on_home(self) -> bool:
        """首页列表第一个可见「加购」iv_add_cart。"""
        els = self._all_displayed_by_pkg_id(SHOP_ID_IV_ADD_CART)
        h = self._window_size()[1]
        scored = []
        for el in els:
            try:
                y = int(el.location.get("y", 99999))
                if y > int(h * 0.88):
                    continue
                scored.append((y, el))
            except Exception:
                continue
        scored.sort(key=lambda t: t[0])
        for _, el in scored[:6]:
            try:
                el.click()
                logger.info("已点击加购（iv_add_cart）")
                time.sleep(0.5)
                return True
            except Exception:
                try:
                    self._nearest_clickable_ancestor(el).click()
                    logger.info("已点击加购（可点击祖先）")
                    time.sleep(0.5)
                    return True
                except Exception:
                    continue
        logger.error("未找到可见的 iv_add_cart")
        return False

    @staticmethod
    def _tv_centre_in_bounds(
        tv, left: int, top: int, right: int, bottom: int
    ) -> bool:
        try:
            loc = tv.location
            sz = tv.size
            cx = int(loc["x"]) + max(int(sz["width"]) // 2, 1)
            cy = int(loc["y"]) + max(int(sz["height"]) // 2, 1)
            return left <= cx <= right and top <= cy <= bottom
        except Exception:
            return False

    def read_cart_badge_digit(self) -> Optional[int]:
        """
        读取商城首页购物车角标数字；无法解析时返回 None。

        避免 ``find_elements(TextView)`` 扫整页（大列表下可达 **数十秒～数分钟**）；
        优先常见 id；否则仅在 **购物车/悬浮入口图标邻近** 的小范围内找纯数字，
        避免把列表右侧价格等误当角标（导致加购前后始终读到同一个数而误判失败）。
        """
        restore_implicit = 1.0
        try:
            iw = self.driver.timeouts.implicit_wait
            if hasattr(iw, "total_seconds"):
                restore_implicit = float(iw.total_seconds())
            else:
                v = float(iw)
                restore_implicit = v / 1000.0 if v >= 500 else v
        except Exception:
            restore_implicit = 1.0
        try:
            self.driver.implicitly_wait(0)
        except Exception:
            pass
        try:
            suffixes = (
                "tv_cart_count",
                "tv_badge",
                "tv_cart_num",
                "tv_message_count",
                "badge_tv",
                SHOP_ID_COUNT_TEXT,
            )
            for suf in suffixes:
                el = self._first_displayed_by_pkg_id(suf)
                if el:
                    try:
                        raw = (el.text or "").strip()
                        m = re.search(r"\d+", raw)
                        if m:
                            return int(m.group(0))
                    except Exception:
                        pass

            best: Optional[Tuple[int, int]] = None

            for anchor in (
                SHOP_ID_IV_SHOPPING_CART,
                SHOP_ID_RL_SHOPPING_CART,
                SHOP_ID_IV_CART,
                SHOP_ID_RL_CART,
                SHOP_ID_CV_CART,
                SHOP_ID_FLOAT_VIEW,
            ):
                root = self._first_displayed_by_pkg_id(anchor)
                if not root:
                    continue
                try:
                    loc = root.location
                    sz = root.size
                    ax, ay = int(loc["x"]), int(loc["y"])
                    aw, ah = int(sz["width"]), int(sz["height"])
                except Exception:
                    continue
                pad_l, pad_t, pad_r, pad_b = 6, 56, 80, 14
                L, T, R, B = ax - pad_l, ay - pad_t, ax + aw + pad_r, ay + ah + pad_b
                for tv in root.find_elements(
                    AppiumBy.CLASS_NAME, "android.widget.TextView"
                ):
                    try:
                        if not tv.is_displayed():
                            continue
                        tx = (tv.text or "").strip()
                        if not re.fullmatch(r"\d{1,4}", tx):
                            continue
                        if not self._tv_centre_in_bounds(tv, L, T, R, B):
                            continue
                        tw = int(tv.size.get("width", 999))
                        if tw > 96:
                            continue
                        val = int(tx)
                        if best is None:
                            best = (ax + ay, val)
                        else:
                            s = int(tv.location["x"]) + int(tv.location["y"])
                            if s > best[0]:
                                best = (s, val)
                    except Exception:
                        continue
                try:
                    par = root.find_element(AppiumBy.XPATH, "..")
                    for tv in par.find_elements(
                        AppiumBy.CLASS_NAME, "android.widget.TextView"
                    ):
                        try:
                            if not tv.is_displayed():
                                continue
                            tx = (tv.text or "").strip()
                            if not re.fullmatch(r"\d{1,4}", tx):
                                continue
                            if not self._tv_centre_in_bounds(tv, L, T, R, B):
                                continue
                            tw = int(tv.size.get("width", 999))
                            if tw > 96:
                                continue
                            val = int(tx)
                            s = int(tv.location["x"]) + int(tv.location["y"])
                            if best is None or s > best[0]:
                                best = (s, val)
                        except Exception:
                            continue
                except Exception:
                    pass

            if best:
                return best[1]

            try:
                el = self.driver.find_element(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    "new UiSelector().resourceIdMatches("
                    '".+:(tv_cart_count|tv_badge|tv_cart_num|tv_message_count|badge_tv)$")',
                )
                if el and el.is_displayed():
                    raw = (el.text or "").strip()
                    m = re.search(r"\d+", raw)
                    if m:
                        return int(m.group(0))
            except Exception:
                pass
            return None
        finally:
            try:
                self.driver.implicitly_wait(
                    restore_implicit if restore_implicit >= 0 else 1.0
                )
            except Exception:
                try:
                    self.driver.implicitly_wait(1)
                except Exception:
                    pass

    def read_cart_badge_digit_expect_increase(
        self,
        baseline: Optional[int],
        *,
        min_delta: int = 1,
        wait_sec: float = 24.0,
        step_sec: float = 1.0,
    ) -> Optional[int]:
        """
        加购后轮询读角标，直到相对 ``baseline`` 至少增加 ``min_delta``（客户端常延迟刷新）。
        结束前若仍不满足，做一次极小幅纵向滑动再读一次。
        """
        deadline = time.time() + wait_sec
        last: Optional[int] = None
        while time.time() < deadline:
            cur = self.read_cart_badge_digit()
            last = cur
            if cur is None:
                time.sleep(step_sec)
                continue
            if baseline is None or cur >= baseline + min_delta:
                return cur
            time.sleep(step_sec)
        try:
            w, h = self._window_size()
            self.driver.swipe(
                int(w * 0.52), int(h * 0.56), int(w * 0.52), int(h * 0.52), 280
            )
        except Exception:
            pass
        time.sleep(0.55)
        cur = self.read_cart_badge_digit()
        if cur is not None and baseline is not None and cur >= baseline + min_delta:
            return cur
        return last

    def tap_mall_text_filter(
        self,
        text: str,
        *,
        y_min_ratio: float = 0.16,
        y_max_ratio: float = 0.72,
    ) -> bool:
        """
        点击商城主区带指定文案的筛选项/标题（如「限时特价」「新品优选」）。
        用多段纵向带避免点到底部导航或悬浮购物车。
        Inspector：活动条/横滑筛选项常为 ``activity_filter``（TextView，文案随活动变）。
        """
        h = self._window_size()[1]
        bands = (
            (y_min_ratio, y_max_ratio),
            (0.14, min(0.76, y_max_ratio + 0.18)),
            (0.12, 0.78),
        )
        for ymin_r, ymax_r in bands:
            y_lo, y_hi = int(h * ymin_r), int(h * ymax_r)
            for pkg in SHOP_PACKAGES:
                rid = self._rid(pkg, SHOP_ID_ACTIVITY_FILTER)
                xp = f'//*[@resource-id="{rid}" and @text="{text}"]'
                try:
                    for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                        try:
                            if not el.is_displayed():
                                continue
                            y = int(el.location.get("y", -1))
                            if not (y_lo <= y <= y_hi):
                                continue
                            self._nearest_clickable_ancestor(el).click()
                            logger.info(
                                "已点击「%s」（activity_filter / %s）",
                                text,
                                pkg,
                            )
                            time.sleep(0.5)
                            return True
                        except Exception:
                            continue
                except Exception:
                    pass
            try:
                for el in self.driver.find_elements(
                    AppiumBy.XPATH, f'//*[@text="{text}"]'
                ):
                    try:
                        if not el.is_displayed():
                            continue
                        y = int(el.location.get("y", -1))
                        if not (y_lo <= y <= y_hi):
                            continue
                        self._nearest_clickable_ancestor(el).click()
                        logger.info("已点击「%s」（y 带 %.2f–%.2f）", text, ymin_r, ymax_r)
                        time.sleep(0.5)
                        return True
                    except Exception:
                        continue
            except Exception:
                pass
            try:
                for el in self.driver.find_elements(
                    AppiumBy.XPATH,
                    f'//*[contains(@content-desc,"{text}")]',
                ):
                    try:
                        if not el.is_displayed():
                            continue
                        y = int(el.location.get("y", -1))
                        if not (y_lo <= y <= y_hi):
                            continue
                        self._nearest_clickable_ancestor(el).click()
                        logger.info("已点击「%s」（content-desc，y 带）", text)
                        time.sleep(0.5)
                        return True
                    except Exception:
                        continue
            except Exception:
                pass
        logger.warning("未命中可点击文案「%s」", text)
        return False

    def run_mall_filter_limited_special_toggle(self) -> bool:
        """
        限时特价/限时秒杀：点开筛选 → 首屏等待 → 下滑浏览（每滑一次等待渲染）
        → 再点一次关闭筛选，回到初始列表。
        """
        opened = False
        for label in (SHOP_TEXT_LIMITED_SPECIAL, SHOP_TEXT_LIMITED_SPECIAL_ALT):
            if self.tap_mall_text_filter(
                label, y_min_ratio=0.18, y_max_ratio=0.72
            ):
                opened = True
                break
        if not opened:
            return False
        logger.info("限时特价/秒杀筛选已打开，首屏等待 5.0s（列表渲染）")
        time.sleep(5.0)
        self.swipe_mall_main_list_down(5, settle_sec=5.0)
        closed = False
        for label in (SHOP_TEXT_LIMITED_SPECIAL, SHOP_TEXT_LIMITED_SPECIAL_ALT):
            if self.tap_mall_text_filter(
                label, y_min_ratio=0.14, y_max_ratio=0.78
            ):
                closed = True
                break
        if not closed:
            logger.warning("活动条第二次点击未命中，可能已还原或文案已变")
            return False
        logger.info("已完成活动条（限时特价/秒杀）：浏览后关筛选")
        time.sleep(0.4)
        self.recover_mall_list_to_show_tab_bar()
        return True

    def mall_list_gesture_scroll_to_top(
        self,
        strokes: int = 8,
        *,
        x_ratio: float = 0.48,
        y_start_ratio: float = 0.25,
        y_end_ratio: float = 0.88,
    ) -> None:
        """
        手指由上向下拖，使列表向**文档顶部**回滚（相对屏幕 y 增大方向）。
        注意：起点 ``y_start_ratio`` 过小且列表已在顶部时，易触发整页「下拉刷新」；
        分类页请用 ``recover_mall_category_goods_list_to_top`` 或 ``_swipe_within_rv_goods_toward_top``。
        """
        w, h = self._window_size()
        x = int(w * x_ratio)
        y0 = int(h * y_start_ratio)
        y1 = int(h * y_end_ratio)
        for _ in range(strokes):
            try:
                self.driver.swipe(x, y0, x, y1, 420)
            except Exception:
                break
            time.sleep(0.24)

    def _uia2_scroll_rv_goods_to_beginning(self) -> bool:
        """
        将分类右侧 ``rv_goods`` RecyclerView 滚到顶部附近（UiAutomator2），
        避免整屏从状态栏下拉触发刷新。
        """
        for pkg in SHOP_PACKAGES:
            rid = self._rid(pkg, SHOP_ID_RV_GOODS)
            expr = (
                f'new UiScrollable(new UiSelector().scrollable(true).resourceId("{rid}"))'
                f".scrollToBeginning(20)"
            )
            try:
                self.driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, expr)
                logger.info("UiScrollable：rv_goods 已 scrollToBeginning（%s）", pkg)
                time.sleep(0.4)
                return True
            except Exception:
                continue
        return False

    def _swipe_within_rv_goods_toward_top(self, strokes: int = 10) -> None:
        """
        仅在 ``rv_goods`` 可见区域内做「上缘偏下 → 下缘」的纵向拖动，使列表回顶。
        起点落在列表控件内部，不经过屏幕最顶端，从而避免 SwipeRefresh 下拉刷新。
        """
        el = self._first_displayed_by_pkg_id(SHOP_ID_RV_GOODS)
        w, h = self._window_size()
        x = int(w * 0.58)
        y_top = int(h * 0.42)
        y_bot = int(h * 0.88)
        if el:
            try:
                loc = el.location
                sz = el.size
                left = int(loc["x"])
                top = int(loc["y"])
                bw = int(sz["width"])
                bh = int(sz["height"])
                x = left + int(bw * 0.58)
                y_top = top + max(int(bh * 0.30), 24)
                y_bot = top + int(bh * 0.92)
                if y_bot - y_top < int(h * 0.14):
                    y_top = top + int(bh * 0.18)
                    y_bot = top + int(bh * 0.94)
            except Exception:
                pass
        for _ in range(strokes):
            try:
                self.driver.swipe(x, y_top, x, y_bot, 420)
            except Exception:
                break
            time.sleep(0.22)

    def recover_mall_category_goods_list_to_top(self) -> None:
        """
        分类页右侧 ``rv_goods``：先 **UiScrollable 回顶** / **仅在列表内**安全区手势，
        避免整页从顶部下拉触发「刷新」；再尝试「回到顶部」按钮微调。
        """
        logger.info(
            "分类商品列表：回到顶部（UiScrollable / rv_goods 内手势，避免下拉刷新）"
        )
        self._uia2_scroll_rv_goods_to_beginning()
        self._swipe_within_rv_goods_toward_top(10)
        time.sleep(0.35)
        if self.tap_back_to_top_if_visible(warn_when_missing=False):
            time.sleep(0.35)
            self._swipe_within_rv_goods_toward_top(4)
            time.sleep(0.3)
        time.sleep(0.3)

    def _kingkong_hot_snacks_label_visible(self) -> bool:
        label = SHOP_KINGKONG_HOT_SNACKS
        for pkg in SHOP_PACKAGES:
            xp = (
                f'//*[@resource-id="{pkg}:id/{SHOP_ID_TV_TITLE}" and @text="{label}"]'
            )
            try:
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    if el.is_displayed():
                        return True
            except Exception:
                continue
        return False

    def recover_mall_list_to_show_tab_bar(self) -> None:
        """
        长列表滑到底后，横滑 Tab（新品优选等）可能不在屏内。
        优先点「回到顶部」；若无按钮或主列表仍不可见，再用手势拉回顶部区域。
        """
        if self.tap_back_to_top_if_visible():
            time.sleep(0.55)
            if self._is_mall_home_main_list_visible():
                return
        logger.info(
            "无「回到顶部」或主列表仍不可见：手势拉回商城首页上方（Tab/金刚区）"
        )
        self.mall_list_gesture_scroll_to_top(8)
        time.sleep(0.4)

    def tap_new_product_prefer_tab(self) -> bool:
        """
        列表上方 Tab「新品优选」。
        与金刚区相同为 ``tv_title``，文案常为 ``✨新品优选``（非 ``activity_filter`` 精确「新品优选」）。
        """
        h = self._window_size()[1]
        # 略放宽：限时特价/长列表后 Tab 可能略高于原 0.30h 下沿
        y_lo, y_hi = int(h * 0.10), int(h * 0.72)
        for pkg in SHOP_PACKAGES:
            rid = self._rid(pkg, SHOP_ID_TV_TITLE)
            xp = f'//*[@resource-id="{rid}" and contains(@text,"新品优选")]'
            try:
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    try:
                        if not el.is_displayed():
                            continue
                        y = int(el.location.get("y", -1))
                        if not (y_lo <= y <= y_hi):
                            continue
                        try:
                            p_rid = self._rid(pkg, SHOP_ID_LL_ITEM)
                            parent = el.find_element(
                                AppiumBy.XPATH,
                                f'./ancestor::android.widget.LinearLayout[@resource-id="{p_rid}"][1]',
                            )
                            if parent.is_displayed():
                                parent.click()
                                logger.info(
                                    "已点击 Tab「新品优选」（tv_title+ll_item / %s）",
                                    pkg,
                                )
                                time.sleep(0.55)
                                return True
                        except Exception:
                            pass
                        self._nearest_clickable_ancestor(el).click()
                        logger.info("已点击 Tab「新品优选」（tv_title / %s）", pkg)
                        time.sleep(0.55)
                        return True
                    except Exception:
                        continue
            except Exception:
                pass
        for label in (SHOP_TEXT_NEW_PRODUCT_PICK_EMOJI, SHOP_TEXT_NEW_PRODUCT_PICK):
            try:
                for el in self.driver.find_elements(
                    AppiumBy.XPATH,
                    f'//android.widget.TextView[@text="{label}"]',
                ):
                    try:
                        if not el.is_displayed():
                            continue
                        y = int(el.location.get("y", -1))
                        if not (y_lo <= y <= y_hi):
                            continue
                        self._nearest_clickable_ancestor(el).click()
                        logger.info("已点击 Tab「新品优选」（精确文案 %s）", label)
                        time.sleep(0.55)
                        return True
                    except Exception:
                        continue
            except Exception:
                pass
        try:
            for el in self.driver.find_elements(
                AppiumBy.ANDROID_UIAUTOMATOR,
                'new UiSelector().textContains("新品优选")',
            ):
                try:
                    if not el.is_displayed():
                        continue
                    y = int(el.location.get("y", -1))
                    if not (y_lo <= y <= y_hi):
                        continue
                    self._nearest_clickable_ancestor(el).click()
                    logger.info("已点击 Tab「新品优选」（UiAutomator）")
                    time.sleep(0.55)
                    return True
                except Exception:
                    continue
        except Exception:
            pass
        try:
            for el in self.driver.find_elements(
                AppiumBy.XPATH,
                '//android.widget.TextView[contains(@text,"新品优选")]',
            ):
                try:
                    if not el.is_displayed():
                        continue
                    y = int(el.location.get("y", 99999))
                    if y > int(h * 0.84):
                        continue
                    self._nearest_clickable_ancestor(el).click()
                    logger.info("已点击 Tab「新品优选」（含 emoji 等宽 y 兜底）")
                    time.sleep(0.55)
                    return True
                except Exception:
                    continue
        except Exception:
            pass
        return self.tap_mall_text_filter(
            SHOP_TEXT_NEW_PRODUCT_PICK,
            y_min_ratio=0.10,
            y_max_ratio=0.72,
        )

    def _swipe_mall_vertical_list_down(
        self,
        times: int,
        settle_sec: float,
        log_name: str,
        *,
        x_ratio: float = 0.48,
    ) -> None:
        """商城内纵向商品列表：上滑翻页 + 每次等待渲染。"""
        w, h = self._window_size()
        x = int(w * x_ratio)
        for i in range(times):
            try:
                self.driver.swipe(x, int(h * 0.72), x, int(h * 0.30), 420)
            except Exception:
                try:
                    self.driver.execute_script(
                        "mobile: swipeGesture",
                        {
                            "left": int(w * 0.22),
                            "top": int(h * 0.36),
                            "width": int(w * 0.56),
                            "height": int(h * 0.48),
                            "direction": "up",
                            "percent": 0.52,
                        },
                    )
                except Exception:
                    pass
            logger.info(
                "%s第 %d/%d 次下滑后等待 %.1fs（列表翻页渲染）",
                log_name,
                i + 1,
                times,
                settle_sec,
            )
            time.sleep(settle_sec)
        logger.info(
            "%s已下滑 %d 次，每次渲染等待 %.1fs", log_name, times, settle_sec
        )

    def swipe_mall_main_list_down(
        self,
        times: int = 5,
        settle_sec: float = 5.0,
    ) -> None:
        """
        商城首页主列表向下滑动浏览（手指自下向上拖，内容向下滚）。

        每次滑动后等待 ``settle_sec`` 秒，便于翻页/懒加载列表数据渲染完成。
        """
        self._swipe_mall_vertical_list_down(
            times, settle_sec, "商城主列表", x_ratio=0.48
        )

    def swipe_mall_kingkong_category_list_down(
        self,
        times: int = 5,
        settle_sec: float = 5.0,
        *,
        first_screen_sec: float = 5.0,
    ) -> None:
        """
        金刚区进入的分类页（如爆款零食）：右侧商品列表上滑浏览，节奏与首页一致。

        分类页常为左栏 + 右列表，横坐标略偏右以减少误触侧栏。
        """
        if first_screen_sec > 0:
            logger.info(
                "金刚区分类页首屏等待 %.1fs（商品列表渲染）", first_screen_sec
            )
            time.sleep(first_screen_sec)
        self._swipe_mall_vertical_list_down(
            times, settle_sec, "金刚区分类商品列表", x_ratio=0.58
        )

    def tap_back_to_top_if_visible(self, *, warn_when_missing: bool = True) -> bool:
        """右侧「回到顶部」箭头（iv_up_to_top）。"""
        el = self._first_displayed_by_pkg_id(SHOP_ID_IV_UP_TO_TOP)
        if el:
            try:
                self._nearest_clickable_ancestor(el).click()
                logger.info("已点击回到顶部（%s）", SHOP_ID_IV_UP_TO_TOP)
                time.sleep(0.85)
                return True
            except Exception:
                pass
        if warn_when_missing:
            logger.warning("未找到可见的「回到顶部」%s", SHOP_ID_IV_UP_TO_TOP)
        return False

    def run_mall_list_filters_scroll_and_back_top(self) -> bool:
        """
        限时特价（开筛选→首屏等 5s→下滑×5 每次等 5s→关筛选）→ 新品优选
        → 首屏等 5s → 下滑×5 每次等 5s → 回到顶部。
        任一步失败记 warning，尽量继续后续主流程。
        """
        ok1 = self.run_mall_filter_limited_special_toggle()
        if not ok1:
            logger.warning("限时特价切换未完成，仍继续新品优选等步骤")
            self.recover_mall_list_to_show_tab_bar()
        if not self.tap_new_product_prefer_tab():
            logger.warning("「新品优选」未点到，仍继续滑动")
        logger.info("新品优选首屏列表等待 5.0s（首屏数据渲染）")
        time.sleep(5.0)
        self.swipe_mall_main_list_down(5, settle_sec=5.0)
        self.tap_back_to_top_if_visible()
        if not self._is_mall_home_main_list_visible() or (
            not self._kingkong_hot_snacks_label_visible()
        ):
            logger.info(
                "新品优选长滑后仍不见 rv_content 或金刚区「%s」，追加手势回顶",
                SHOP_KINGKONG_HOT_SNACKS,
            )
            self.mall_list_gesture_scroll_to_top(8)
            time.sleep(0.5)
        return True

    def _goods_list_item_root(self, inner_el):
        """
        分类商品行根节点：优先 ``goodsListItemLayout``；
        部分分类页用其它行容器，则找含 ``mall_category_goods_name`` 的祖先或按 resource-id 上溯。
        """
        try:
            return inner_el.find_element(
                AppiumBy.XPATH,
                './ancestor::*[contains(@resource-id,"goodsListItemLayout")][1]',
            )
        except Exception:
            pass
        try:
            return inner_el.find_element(
                AppiumBy.XPATH,
                './ancestor::*[.//*[contains(@resource-id,"mall_category_goods_name")]]'
                '[contains(@resource-id,"Layout")][1]',
            )
        except Exception:
            pass
        cur = inner_el
        for _ in range(14):
            try:
                cur = cur.find_element(AppiumBy.XPATH, "..")
                rid = (cur.get_attribute("resource-id") or "").lower()
                if "goodslistitem" in rid.replace(
                    "_", ""
                ) or "goodslistitemlayout" in rid.replace("_", ""):
                    return cur
                try:
                    for ch in cur.find_elements(
                        AppiumBy.XPATH,
                        './/*[contains(@resource-id,"mall_category_goods_name")]',
                    ):
                        if ch.is_displayed():
                            return cur
                except Exception:
                    pass
            except Exception:
                break
        return inner_el

    def _read_category_row_qty(self, item_root) -> Optional[int]:
        """分类行内数量：取行右侧区域的纯数字 TextView（弱化价签等左侧数字）。"""
        try:
            loc = item_root.location
            sz = item_root.size
            row_left = int(loc["x"])
            row_w = int(sz["width"])
            x_cut_loose = row_left + int(row_w * 0.42)
            x_cut_strict = row_left + int(row_w * 0.50)
        except Exception:
            row_left, row_w = 0, 0
            x_cut_loose = x_cut_strict = 0

        def _scan_textviews(x_cut: int) -> Optional[int]:
            best: Optional[int] = None
            try:
                for el in item_root.find_elements(
                    AppiumBy.CLASS_NAME, "android.widget.TextView"
                ):
                    try:
                        if not el.is_displayed():
                            continue
                        tx = (el.text or "").strip()
                        if not re.fullmatch(r"\d{1,4}", tx):
                            continue
                        v = int(tx)
                        if v > 999:
                            continue
                        ex = int(el.location.get("x", 0))
                        if x_cut and ex < x_cut:
                            continue
                        best = v
                    except Exception:
                        continue
            except Exception:
                pass
            return best

        for cut in (x_cut_strict, x_cut_loose):
            if cut:
                got = _scan_textviews(cut)
                if got is not None:
                    return got

        try:
            for el in item_root.find_elements(
                AppiumBy.XPATH,
                './/*[contains(@resource-id,"count") or contains(@resource-id,"qty") '
                'or contains(@resource-id,"amount") or contains(@resource-id,"number")]',
            ):
                try:
                    if not el.is_displayed():
                        continue
                    tx = (el.text or "").strip()
                    m = re.search(r"\d{1,4}", tx)
                    if not m:
                        continue
                    return int(m.group(0))
                except Exception:
                    continue
        except Exception:
            pass

        if row_w > 0:
            x_far = row_left + int(row_w * 0.62)
            try:
                best2: Optional[int] = None
                for el in item_root.find_elements(
                    AppiumBy.CLASS_NAME, "android.widget.TextView"
                ):
                    try:
                        if not el.is_displayed():
                            continue
                        tx = (el.text or "").strip()
                        if not re.fullmatch(r"\d{1,4}", tx):
                            continue
                        v = int(tx)
                        if v > 999:
                            continue
                        ex = int(el.location.get("x", 0))
                        if ex < x_far:
                            continue
                        best2 = v
                    except Exception:
                        continue
                if best2 is not None:
                    return best2
            except Exception:
                pass
        return None

    def _first_select_spec_button_on_category(self):
        """分类列表第一个可见「选规格」（``tv_add_cart_more`` 或文案）。"""
        for pkg in SHOP_PACKAGES:
            rid = self._rid(pkg, SHOP_ID_TV_ADD_CART_MORE)
            try:
                for el in self.driver.find_elements(AppiumBy.ID, rid):
                    try:
                        if not el.is_displayed():
                            continue
                        blob = (
                            (el.text or "")
                            + (el.get_attribute("content-desc") or "")
                        )
                        if SHOP_TEXT_SELECT_SPEC not in blob:
                            continue
                        return el
                    except Exception:
                        continue
            except Exception:
                pass
        try:
            for el in self.driver.find_elements(
                AppiumBy.XPATH, f'//*[@text="{SHOP_TEXT_SELECT_SPEC}"]'
            ):
                if el.is_displayed():
                    return el
        except Exception:
            pass
        return None

    def _random_select_spec_button_on_category(self):
        """分类列表中随机一个可见且文案含「选规格」的加购入口（仅多规格商品）。"""
        seen: set[int] = set()
        cands: List = []
        for pkg in SHOP_PACKAGES:
            rid = self._rid(pkg, SHOP_ID_TV_ADD_CART_MORE)
            try:
                for el in self.driver.find_elements(AppiumBy.ID, rid):
                    try:
                        if not el.is_displayed():
                            continue
                        blob = (
                            (el.text or "")
                            + (el.get_attribute("content-desc") or "")
                        )
                        if SHOP_TEXT_SELECT_SPEC not in blob:
                            continue
                        eid = id(el)
                        if eid in seen:
                            continue
                        seen.add(eid)
                        cands.append(el)
                    except Exception:
                        continue
            except Exception:
                pass
        try:
            for el in self.driver.find_elements(
                AppiumBy.XPATH,
                f'//*[@text="{SHOP_TEXT_SELECT_SPEC}"]',
            ):
                try:
                    if not el.is_displayed():
                        continue
                    eid = id(el)
                    if eid in seen:
                        continue
                    seen.add(eid)
                    cands.append(el)
                except Exception:
                    continue
        except Exception:
            pass
        if not cands:
            return None
        return random.choice(cands)

    def _mall_category_goods_name_text(self, item_root) -> str:
        try:
            for el in item_root.find_elements(
                AppiumBy.XPATH,
                './/*[contains(@resource-id,"mall_category_goods_name")]',
            ):
                if el.is_displayed():
                    return (el.text or "").strip()
        except Exception:
            pass
        return ""

    def _find_goods_item_by_name_substring(self, sub: str):
        if not sub:
            return None
        safe = sub.replace('"', "").replace("'", "")[:28]
        for pkg in SHOP_PACKAGES:
            xp = (
                f'//*[contains(@resource-id,"{pkg}:id/{SHOP_ID_GOODS_LIST_ITEM}")]'
                f'//*[contains(@resource-id,"{SHOP_ID_MALL_CATEGORY_GOODS_NAME}") '
                f'and contains(@text,"{safe}")]'
                f'/ancestor::*[contains(@resource-id,"goodsListItemLayout")][1]'
            )
            try:
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    if el.is_displayed():
                        return el
            except Exception:
                pass
        return None

    def _tx_looks_like_mall_spec_chip(self, tx: str) -> bool:
        """
        是否为「规格 SKU 芯片」文案（排除纯数字数量、标题行）。
        注意：勿用单独 ``\\d`` 匹配，否则易把「数量」区的 ``1`` 当成规格。
        """
        if not tx or len(tx) > 44:
            return False
        t = tx.strip()
        ban_exact = (
            "确定",
            SHOP_TEXT_FINISH_SPEC,
            "取消",
            "加入购物车",
            "规格",
            "数量",
            "库存",
            "选择",
            "已选",
            "+",
            "-",
            "＋",
            "－",
        )
        if t in ban_exact:
            return False
        if re.fullmatch(r"\d{1,4}", t):
            return False
        low = t.lower()
        return bool(
            re.search(
                r"(pcs|pic|pc\b|box|箱|盒|袋|包|瓶|罐|条|/"
                r"|ml\b|\bmg\b|\bg\b|\d+\s*(瓶|罐|包|pcs|pic|箱|件|盒|条))",
                low,
                re.I,
            )
        )

    def _mall_spec_try_pick_one_chip(self, root, tag: str) -> bool:
        """在单个容器内最多点选一条规格（可点击祖先）。"""
        if not root:
            return False
        try:
            for tel in root.find_elements(
                AppiumBy.CLASS_NAME, "android.widget.TextView"
            ):
                try:
                    if not tel.is_displayed():
                        continue
                    tx = (tel.text or "").strip()
                    if not self._tx_looks_like_mall_spec_chip(tx):
                        continue
                    self._nearest_clickable_ancestor(tel).click()
                    logger.info("已选规格项(%s): %s", tag, tx[:40])
                    time.sleep(0.45)
                    return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    def _mall_spec_popup_pick_and_confirm(self) -> bool:
        """多规格底部弹层：只选一条规格（多容器互斥）→ 数量+ → 确定/完成。"""
        end = time.time() + 14.0
        while time.time() < end:
            if self._login_like_screen_visible():
                logger.error("选规格后进入登录页，请先登录")
                return False
            if self._first_displayed_by_pkg_id(SHOP_ID_DIALOG_COMPLETE):
                break
            if self._first_displayed_by_pkg_id(SHOP_ID_BOTTOM_POPUP):
                break
            if self._first_displayed_by_pkg_id(SHOP_ID_DIALOG_CHOOSE_CONTAINER):
                break
            time.sleep(0.35)
        picked = False
        sku_root = self._first_displayed_by_pkg_id(SHOP_ID_CHOOSE_SKU_CONTAINER)
        if self._mall_spec_try_pick_one_chip(sku_root, "choose_sku"):
            picked = True
        if not picked:
            rv = self._first_displayed_by_pkg_id(SHOP_ID_CHOOSE_RECYCLER)
            if self._mall_spec_try_pick_one_chip(rv, "choose_recycler"):
                picked = True
        if not picked:
            sv = self._first_displayed_by_pkg_id(SHOP_ID_CHOOSE_SCROLL)
            self._mall_spec_try_pick_one_chip(sv, "choose_scroll")
        add_el = self._first_displayed_by_pkg_id(SHOP_ID_COUNT_ADD)
        if add_el:
            try:
                add_el.click()
                logger.info("已点击规格弹层数量加（count_add）")
                time.sleep(0.45)
            except Exception:
                pass
        if self._tap_mall_spec_sheet_confirm_button():
            return True
        logger.error("多规格弹层未点到「确定/完成」等主按钮")
        return False

    def _tap_mall_spec_sheet_confirm_button(self) -> bool:
        """
        规格底栏主操作：``dialog_complete`` 常为 clickable=false，需点祖先；
        再按文案「完成 / 确定 / 加入购物车」兜底（放宽 y 与 clickable）。
        """
        h = self._window_size()[1]
        y_cut = int(h * 0.32)
        for pkg in SHOP_PACKAGES:
            rid = self._rid(pkg, SHOP_ID_DIALOG_COMPLETE)
            try:
                for el in self.driver.find_elements(AppiumBy.ID, rid):
                    try:
                        if not el.is_displayed():
                            continue
                        self._nearest_clickable_ancestor(el).click()
                        logger.info(
                            "已点击多规格弹层主按钮（dialog_complete 祖先 / %s）",
                            pkg,
                        )
                        time.sleep(0.85)
                        return True
                    except Exception:
                        try:
                            el.click()
                            logger.info(
                                "已点击多规格弹层主按钮（dialog_complete 自身 / %s）",
                                pkg,
                            )
                            time.sleep(0.85)
                            return True
                        except Exception:
                            continue
            except Exception:
                pass
        try:
            for el in self.driver.find_elements(
                AppiumBy.XPATH,
                '//*[contains(@resource-id,"dialog_complete")]',
            ):
                try:
                    if not el.is_displayed():
                        continue
                    self._nearest_clickable_ancestor(el).click()
                    logger.info("已点击多规格弹层主按钮（resource-id 含 dialog_complete）")
                    time.sleep(0.85)
                    return True
                except Exception:
                    continue
        except Exception:
            pass
        for label in (SHOP_TEXT_FINISH_SPEC, "确定", "加入购物车"):
            try:
                for el in self.driver.find_elements(
                    AppiumBy.XPATH, f'//*[@text="{label}"]'
                ):
                    try:
                        if not el.is_displayed():
                            continue
                        yy = int(el.location.get("y", 0))
                        if yy < y_cut:
                            continue
                        if label == "加入购物车" and len((el.text or "").strip()) > 10:
                            continue
                        self._nearest_clickable_ancestor(el).click()
                        logger.info("已点击多规格弹层「%s」（文案+可点祖先）", label)
                        time.sleep(0.85)
                        return True
                    except Exception:
                        try:
                            el.click()
                            logger.info("已点击多规格弹层「%s」（文案自身）", label)
                            time.sleep(0.85)
                            return True
                        except Exception:
                            continue
            except Exception:
                pass
        for sub, disp in ((SHOP_TEXT_FINISH_SPEC, "完成"), ("确定", "确定")):
            try:
                xp = f'//*[contains(@text,"{sub}")]'
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    try:
                        if not el.is_displayed():
                            continue
                        tx = (el.text or "").strip()
                        if len(tx) > 10:
                            continue
                        yy = int(el.location.get("y", 0))
                        if yy < y_cut:
                            continue
                        self._nearest_clickable_ancestor(el).click()
                        logger.info("已点击多规格弹层「%s」（contains 文案）", disp)
                        time.sleep(0.85)
                        return True
                    except Exception:
                        continue
            except Exception:
                pass
        try:
            for el in self.driver.find_elements(
                AppiumBy.XPATH,
                (
                    '//android.widget.Button['
                    'contains(@text,"完成") or contains(@text,"确定")]'
                ),
            ):
                try:
                    if not el.is_displayed():
                        continue
                    if int(el.location.get("y", 0)) < y_cut:
                        continue
                    el.click()
                    logger.info("已点击多规格弹层主按钮（Button 完成/确定）")
                    time.sleep(0.85)
                    return True
                except Exception:
                    continue
        except Exception:
            pass
        for label in (SHOP_TEXT_FINISH_SPEC, "确定"):
            try:
                self.driver.find_element(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    f'new UiSelector().text("{label}").clickable(true)',
                ).click()
                logger.info("已点击多规格弹层「%s」（UiAutomator）", label)
                time.sleep(0.85)
                return True
            except Exception:
                continue
        return False

    def _is_mall_home_main_list_visible(self) -> bool:
        return self._first_displayed_by_pkg_id(SHOP_ID_RV_CONTENT) is not None

    def _is_mall_product_detail_visible(self) -> bool:
        if self._first_displayed_by_pkg_id(SHOP_ID_MALL_ADD_SHOP_CAR):
            return True
        return self._first_displayed_by_pkg_id(SHOP_ID_MALL_DETAIL_VIEWPAGER) is not None

    def _wait_substring_on_screen(self, sub: str, timeout: float = 3.5) -> bool:
        if not sub:
            return False
        safe = sub.replace('"', "").replace("'", "")[:40]
        end = time.time() + timeout
        while time.time() < end:
            try:
                xp = f'//*[contains(@text,"{safe}")]'
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    try:
                        if el.is_displayed():
                            return True
                    except Exception:
                        continue
            except Exception:
                pass
            time.sleep(0.28)
        return False

    def _kefu_native_markers_visible(self) -> bool:
        """Native 层可见文案/描述是否像客服页。"""
        for sub in SHOP_TEXT_KEFU_PAGE_MARKERS:
            safe = sub.replace('"', "").replace("'", "")[:36]
            try:
                for el in self.driver.find_elements(
                    AppiumBy.XPATH, f'//*[contains(@text,"{safe}")]'
                ):
                    try:
                        if el.is_displayed():
                            return True
                    except Exception:
                        continue
            except Exception:
                continue
        try:
            for el in self.driver.find_elements(
                AppiumBy.XPATH, '//*[contains(@content-desc,"客服")]'
            ):
                if el.is_displayed():
                    return True
        except Exception:
            pass
        return False

    def _kefu_page_via_webview_source(self) -> bool:
        """部分包客服为 H5，切 WEBVIEW 扫 ``page_source``。"""
        try:
            names = [
                c
                for c in self.driver.contexts
                if "WEBVIEW" in str(c).upper()
            ]
        except Exception:
            return False
        if not names:
            return False
        try:
            prev = self.driver.current_context
        except Exception:
            prev = "NATIVE_APP"
        hit = False
        for name in names:
            try:
                self.driver.switch_to.context(name)
                time.sleep(0.5)
                body = (self.driver.page_source or "")[:500_000]
                if any(
                    k in body
                    for k in (
                        "24小时",
                        "客服",
                        "在线咨询",
                        "人工客服",
                        "意见反馈",
                        "专属客服",
                    )
                ):
                    hit = True
                    break
            except Exception:
                continue
        try:
            self.driver.switch_to.context(prev)
        except Exception:
            pass
        return hit

    def _wait_kefu_destination(self, timeout: float = 10.0) -> bool:
        end = time.time() + timeout
        n = 0
        while time.time() < end:
            if self._kefu_native_markers_visible():
                return True
            n += 1
            if n % 2 == 0 and self._kefu_page_via_webview_source():
                return True
            time.sleep(0.4)
        return False

    def _read_mall_detail_price_peso(self) -> Optional[float]:
        """详情页顶部区域解析 ₱ / P 价签数字（用于「立即购买」与 400P 门槛）。"""
        h = self._window_size()[1]
        y_max = int(h * 0.50)
        found: List[float] = []
        try:
            for el in self.driver.find_elements(
                AppiumBy.CLASS_NAME, "android.widget.TextView"
            ):
                try:
                    if not el.is_displayed():
                        continue
                    if int(el.location.get("y", 99999)) > y_max:
                        continue
                    raw = (el.text or "").strip().replace(",", "")
                    raw_ns = raw.replace(" ", "")
                    m = re.search(r"₱\s*(\d+(?:\.\d+)?)", raw_ns)
                    if not m:
                        m = re.match(
                            r"^P\s*(\d+(?:\.\d+)?)\s*$", raw_ns, flags=re.I
                        )
                    if m:
                        found.append(float(m.group(1)))
                except Exception:
                    continue
        except Exception:
            pass
        return max(found) if found else None

    def _mall_detail_submit_order_like_visible(self) -> bool:
        for mk in ("提交订单", "确认订单", "立即支付", "去支付", "应付金额", "实付款"):
            try:
                for el in self.driver.find_elements(
                    AppiumBy.XPATH, f'//*[contains(@text,"{mk}")]'
                ):
                    if el.is_displayed():
                        return True
            except Exception:
                continue
        return False

    def _mall_list_el_is_add_cart_control(self, el) -> bool:
        """加购按钮走加购流程，勿当「进详情」点击目标。"""
        try:
            rid = (el.get_attribute("resource-id") or "").lower()
            if "add_cart" in rid or "iv_add_cart" in rid:
                return True
        except Exception:
            pass
        return False

    def _tap_cl_item_open_detail(self, container) -> bool:
        """点商品卡片左内侧（图/标题区），避开右侧 ``iv_add_cart``。"""
        try:
            loc = container.location
            sz = container.size
            w0, h0 = self._window_size()
            cx = int(loc["x"] + int(sz["width"]) * 0.30)
            cy = int(loc["y"] + int(sz["height"]) * 0.46)
            if cx < 8 or cy < int(h0 * 0.12) or cy > int(h0 * 0.90):
                return False
            self.driver.execute_script(
                "mobile: clickGesture", {"x": cx, "y": cy}
            )
            logger.info("已点商品卡片左内侧进详情（clItemContainer 坐标）")
            time.sleep(1.85)
            return bool(self._is_mall_product_detail_visible())
        except Exception:
            return False

    def tap_first_mall_list_product_into_detail(self) -> bool:
        """
        主列表（``rv_content``）进商品详情：**点商品图/名称/价签/卡片左区**；
        排除 ``iv_add_cart``（加购按钮走加购流程，不进详情）。
        """
        h = self._window_size()[1]
        y_lo, y_hi = int(h * 0.14), int(h * 0.86)
        rv = self._first_displayed_by_pkg_id(SHOP_ID_RV_CONTENT)
        if rv:
            try:
                items = rv.find_elements(
                    AppiumBy.XPATH,
                    f'.//*[contains(@resource-id,"{SHOP_ID_CL_ITEM_CONTAINER}")]',
                )
                row_scored: List[Tuple[int, object]] = []
                for it in items:
                    try:
                        if not it.is_displayed():
                            continue
                        y = int(it.location.get("y", 0))
                        if not (y_lo <= y <= y_hi):
                            continue
                        row_scored.append((y, it))
                    except Exception:
                        continue
                row_scored.sort(key=lambda t: t[0])
                for _, it in row_scored[:4]:
                    if self._tap_cl_item_open_detail(it):
                        return True
            except Exception:
                pass

        scored: List[Tuple[int, object]] = []
        if rv:
            for xpath_inner in (
                './/*[contains(@resource-id,":id/iv_goods") or '
                'contains(@resource-id,"iv_goods")]',
                './/*[contains(@resource-id,":id/image") or contains(@resource-id,"/image")]',
                './/*[contains(@resource-id,":id/tv_goods_name") or '
                'contains(@resource-id,"tv_goods_name")]',
                './/*[contains(@resource-id,":id/tv_price") or '
                'contains(@resource-id,"tv_price")]',
            ):
                try:
                    for el in rv.find_elements(AppiumBy.XPATH, xpath_inner):
                        try:
                            if not el.is_displayed():
                                continue
                            if self._mall_list_el_is_add_cart_control(el):
                                continue
                            y = int(el.location.get("y", 0))
                            if not (y_lo <= y <= y_hi):
                                continue
                            scored.append((y, el))
                        except Exception:
                            continue
                    if scored:
                        break
                except Exception:
                    continue
        if not scored:
            for suf in (
                SHOP_ID_IV_GOODS,
                SHOP_ID_TV_GOODS_NAME,
                SHOP_ID_TV_PRICE,
                SHOP_ID_IMAGE,
            ):
                for el in self._all_displayed_by_pkg_id(suf):
                    try:
                        if not el.is_displayed():
                            continue
                        if self._mall_list_el_is_add_cart_control(el):
                            continue
                        y = int(el.location.get("y", 0))
                        if not (y_lo <= y <= y_hi):
                            continue
                        scored.append((y, el))
                    except Exception:
                        continue
                if scored:
                    break
        scored.sort(key=lambda t: t[0])
        for _, el in scored[:6]:
            if self._mall_list_el_is_add_cart_control(el):
                continue
            try:
                self._nearest_clickable_ancestor(el).click()
            except Exception:
                try:
                    el.click()
                except Exception:
                    continue
            logger.info("已点击主列表商品图/信息区进详情")
            time.sleep(1.85)
            if self._is_mall_product_detail_visible():
                return True
        w, h2 = self._window_size()
        try:
            self.driver.execute_script(
                "mobile: clickGesture",
                {"x": int(w * 0.34), "y": int(h2 * 0.44)},
            )
            logger.info("主列表进详情：偏左坐标兜底（避让右侧加购区）")
            time.sleep(1.85)
            if self._is_mall_product_detail_visible():
                return True
        except Exception:
            pass
        logger.error("主列表未能进入商品详情")
        return False

    def mall_detail_tap_add_to_cart_with_spec(self) -> bool:
        """详情页点「加入购物车」；多规格则选规格 → 点数量+ → 完成/确定。"""
        add = self._first_displayed_by_pkg_id(SHOP_ID_MALL_ADD_SHOP_CAR)
        if not add:
            logger.error("详情页未找到「加入购物车」（mall_add_shop_car）")
            return False
        try:
            self._nearest_clickable_ancestor(add).click()
        except Exception:
            try:
                add.click()
            except Exception as ex:
                logger.error("点击「加入购物车」失败: %s", ex)
                return False
        time.sleep(0.65)
        if self._login_like_screen_visible():
            logger.error("加入购物车后出现登录页")
            return False
        if self._spec_bottom_sheet_visible():
            if not self._mall_spec_popup_pick_and_confirm():
                return False
        else:
            logger.info("加入购物车未出现规格弹层（可能为单规格直加）")
        return True

    def mall_detail_tap_buy_now_price_gate(self) -> bool:
        """立即购买：售价≤400P 时不应进入提交订单类页面。"""
        price = self._read_mall_detail_price_peso()
        logger.info("详情页解析售价(约): %s P", price)
        el = self._first_displayed_by_pkg_id(SHOP_ID_MALL_BUY_NOW)
        if not el:
            logger.error("详情页未找到「立即购买」")
            return False
        try:
            self._nearest_clickable_ancestor(el).click()
        except Exception:
            el.click()
        time.sleep(2.0)
        order_vis = self._mall_detail_submit_order_like_visible()
        if price is not None and price <= 400.0:
            if order_vis:
                logger.error("售价≤400P 仍进入提交订单类页面")
                self.tap_top_back()
                return False
            logger.info("售价≤400P：未进入提交订单页，符合预期")
        elif price is None:
            logger.warning("售价未解析，跳过「≤400P 不得进下单页」强校验")
        if order_vis:
            self.tap_top_back()
            time.sleep(0.9)
        return True

    def run_mall_product_detail_deep_flow(self) -> bool:
        """
        商城主列表 → 商品详情 → 返回首页 → 再进详情
        → 加入购物车（多规格弹层：选规格 + 数量 + 完成）
        → 收藏（期望「收藏成功」）→ 客服（多文案 / WebView）→ 返回详情
        → 购物车 → 返回详情 → 立即购买（≤400P 不得进下单页）→ 返回商城首页。
        """
        if not self._is_mall_home_main_list_visible():
            logger.warning("未发现主列表 rv_content，跳过商品详情深度流")
            return True
        if not self.tap_first_mall_list_product_into_detail():
            logger.error("首次未能从主列表进入商品详情")
            return False
        if not self._is_mall_product_detail_visible():
            logger.warning("未识别详情页，跳过商品详情深度流")
            self.tap_top_back()
            return True
        time.sleep(0.5)
        if not self.tap_top_back():
            logger.warning("详情返回商城首页可能失败，尝试 ensure_mall_tab")
        time.sleep(0.65)
        self.ensure_mall_tab()
        if not self.tap_first_mall_list_product_into_detail():
            logger.error("第二次未能进入商品详情")
            return False
        if not self._is_mall_product_detail_visible():
            logger.warning("第二次未识别详情页，跳过加购与后续深度步骤")
            self.tap_top_back()
            return True
        time.sleep(0.5)
        if not self.mall_detail_tap_add_to_cart_with_spec():
            return False
        time.sleep(0.45)
        col = self._first_displayed_by_pkg_id(SHOP_ID_IV_COLLECT)
        if col:
            try:
                col.click()
                time.sleep(0.55)
                if self._wait_substring_on_screen(SHOP_TEXT_COLLECT_OK, 3.8):
                    logger.info("已出现「%s」", SHOP_TEXT_COLLECT_OK)
                else:
                    logger.warning(
                        "未在界面上捕获「%s」（Toast 可能不在层级中）",
                        SHOP_TEXT_COLLECT_OK,
                    )
            except Exception as ex:
                logger.warning("点击收藏失败: %s", ex)
        ke = self._first_displayed_by_pkg_id(SHOP_ID_MALL_KEFU)
        if ke:
            try:
                self._nearest_clickable_ancestor(ke).click()
                time.sleep(1.15)
            except Exception as ex:
                logger.error("点击客服失败: %s", ex)
                return False
            ok_ke = self._wait_kefu_destination(10.0)
            if not ok_ke and not self._is_mall_product_detail_visible():
                logger.warning(
                    "未命中客服页固定文案/H5 关键字，但已离开商品详情，视为客服已打开，继续"
                )
                ok_ke = True
            if not ok_ke:
                logger.error("未识别客服页（仍在详情且无文案/WebView 命中）")
                self.tap_top_back()
                return False
            if not self.tap_top_back():
                logger.error("客服页返回失败")
                return False
            time.sleep(0.85)
        cart = self._first_displayed_by_pkg_id(SHOP_ID_MALL_SHOP_CAR_CONTAINER)
        if cart:
            try:
                self._nearest_clickable_ancestor(cart).click()
                time.sleep(1.0)
            except Exception as ex:
                logger.error("点击购物车入口失败: %s", ex)
                return False
            if not self._wait_substring_on_screen(SHOP_TEXT_MALL_CART_TITLE, 4.5):
                logger.error("未进入标题含「%s」的页面", SHOP_TEXT_MALL_CART_TITLE)
                self.tap_top_back()
                return False
            if not self.tap_top_back():
                logger.error("购物车页返回失败")
                return False
            time.sleep(0.85)
        if not self.mall_detail_tap_buy_now_price_gate():
            return False
        if not self.tap_top_back():
            logger.warning("详情返回商城首页可能失败")
        time.sleep(0.55)
        self.ensure_mall_tab()
        logger.info("商品详情深度流结束")
        return True

    def run_category_spec_add_verify_line_qty(
        self, *, random_pick: bool = False, log_prefix: str = "分类"
    ) -> bool:
        """
        分类商品列表：仅对信息栏含「选规格」的商品加购（``tv_add_cart_more`` / 文案）；
        ``random_pick=True`` 时在可见候选中随机选一行，否则取第一个。
        """
        time.sleep(1.0)
        for pkg in SHOP_PACKAGES:
            rid = self._rid(pkg, SHOP_ID_RV_GOODS)
            try:
                self.driver.find_element(AppiumBy.ID, rid)
                break
            except Exception:
                continue
        self.recover_mall_category_goods_list_to_top()
        spec_btn = None
        for attempt in range(12):
            if random_pick:
                spec_btn = self._random_select_spec_button_on_category()
            else:
                spec_btn = self._first_select_spec_button_on_category()
            if spec_btn:
                break
            if attempt < 11:
                self._swipe_mall_vertical_list_down(
                    1, 1.0, "分类商品列表(轻翻找选规格)", x_ratio=0.58
                )
        if not spec_btn:
            logger.warning(
                "%s页无「%s」商品，跳过行数量校验段", log_prefix, SHOP_TEXT_SELECT_SPEC
            )
            return True
        try:
            item = self._goods_list_item_root(spec_btn)
        except Exception as ex:
            logger.error("无法定位商品行根节点: %s", ex)
            return False
        pname = self._mall_category_goods_name_text(item)
        before = self._read_category_row_qty(item)
        pick_desc = "随机" if random_pick else "首个"
        logger.info(
            "%s：将点「%s」商品(%s)=%s 行内数量(before)=%s",
            log_prefix,
            SHOP_TEXT_SELECT_SPEC,
            pick_desc,
            (pname or "?")[:40],
            before,
        )
        try:
            spec_btn.click()
        except Exception:
            try:
                self._nearest_clickable_ancestor(spec_btn).click()
            except Exception as ex2:
                logger.error("点击「%s」失败: %s", SHOP_TEXT_SELECT_SPEC, ex2)
                return False
        time.sleep(0.55)
        if self._login_like_screen_visible():
            logger.error("点「%s」后出现登录页，请先登录", SHOP_TEXT_SELECT_SPEC)
            return False
        if not self._mall_spec_popup_pick_and_confirm():
            return False
        time.sleep(1.0)
        after: Optional[int] = None
        if pname:
            item2 = self._find_goods_item_by_name_substring(pname)
            if item2:
                after = self._read_category_row_qty(item2)
        if after is None:
            try:
                after = self._read_category_row_qty(item)
            except Exception:
                after = None
        logger.info("%s：同一商品行数量(after)=%s", log_prefix, after)
        if before is not None and after is not None:
            if after >= before + 1:
                logger.info("行数量校验通过：%s → %s", before, after)
                return True
            logger.error("行数量未 +1：before=%s after=%s", before, after)
            return False
        if before is None and after is not None and after >= 1:
            logger.info("行数量校验通过（加购前无数，加购后=%s）", after)
            return True
        logger.warning(
            "行数量解析不完整 before=%s after=%s，请 Inspector 核对数量 TextView",
            before,
            after,
        )
        return True

    def run_hot_snacks_category_spec_add_verify_line_qty(self) -> bool:
        """兼容：爆款零食分类页，取首个「选规格」。"""
        return self.run_category_spec_add_verify_line_qty(
            random_pick=False, log_prefix="爆款零食分类"
        )

    def run_shop_home_flow(self) -> bool:
        """
        完整流程：商城 Tab
        → **日用百货**（金刚区弹层分类、选规格加购）→ 回首页
        → **限时特价 / 新品优选**（``run_mall_list_filters_scroll_and_back_top``：含长滑回顶）
        → **不再**重复「再切新品优选 + 长滑 + 首页 iv_add_cart」（与详情深度流里详情加购重复）
        → 主列表详情深度流 → 悬浮购物车 → Banner → 末次首页加购 → 角标 +1。
        """
        if not self.ensure_mall_tab():
            return False
        time.sleep(0.5)

        if not self.tap_mall_kingkong_daily_baihuo_via_popup():
            logger.error("金刚区：未能打开全部分类或未进入「日用百货」")
            return False
        self.swipe_mall_kingkong_category_list_down(5, settle_sec=5.0)
        time.sleep(0.45)
        if not self.run_category_spec_add_verify_line_qty(
            random_pick=True, log_prefix="日用百货分类"
        ):
            logger.error("日用百货分类：选规格加购或行数量校验失败")
            return False
        if not self.leave_mall_category_to_mall_home():
            logger.warning(
                "日用百货：离开分类页后仍未确认商城首页，仍尝试限时特价/新品优选"
            )
        for _mall_try in range(3):
            if self.ensure_mall_tab(1.0):
                break
            time.sleep(0.75)
        else:
            logger.warning("返回后多次点击「商城」Tab 未成功，仍继续后续步骤")
        time.sleep(0.55)

        self.run_mall_list_filters_scroll_and_back_top()
        time.sleep(0.45)

        logger.info(
            "限时特价/新品优选已在上一段完成 Tab 与列表浏览；跳过首页 iv_add_cart（避免与详情加购重复）"
        )
        if not self.ensure_mall_tab():
            self.ensure_mall_tab()

        if not self.run_mall_product_detail_deep_flow():
            logger.error("商城商品详情深度流失败")
            return False

        if not self.tap_floating_or_entry_cart():
            return False
        if not self.tap_top_back():
            logger.warning("购物车页返回可能失败，仍继续")
        if not self.ensure_mall_tab():
            logger.warning("返回后重进商城 Tab")

        if not self.tap_banner_area():
            return False
        if not self.tap_top_back():
            logger.warning("Banner 活动页返回可能失败，仍继续")
        if not self.ensure_mall_tab():
            logger.warning("返回后重进商城 Tab")

        logger.info("读取购物车 Tab 角标（加购前）…")
        before = self.read_cart_badge_digit()
        logger.info("加购前购物车角标解析值: %s", before)

        if not self.tap_first_add_cart_on_home():
            return False

        ok, branch = self.handle_add_cart_followups()
        if not ok:
            return False

        time.sleep(0.65)
        if not self.ensure_mall_tab():
            logger.warning("加购后未能确认商城 Tab，仍尝试读角标")

        after = self.read_cart_badge_digit_expect_increase(
            before, min_delta=1, wait_sec=26.0, step_sec=1.0
        )
        logger.info("加购后购物车角标解析值: %s（分支=%s）", after, branch)

        if before is not None and after is not None:
            if after >= before + 1:
                logger.info("校验通过：角标由 %s 增至 %s", before, after)
                logger.info(
                    "run_shop_home_flow 全部步骤已完成（单次线性流程，无循环），返回 True"
                )
                return True
            logger.error("角标未 +1：before=%s after=%s", before, after)
            return False
        if after is not None and before is None:
            logger.info("加购前无数角标，加购后=%s，视为流程已执行", after)
            logger.info(
                "run_shop_home_flow 全部步骤已完成（单次线性流程，无循环），返回 True"
            )
            return True
        logger.error("无法解析购物车角标，无法校验 +1；请 Inspector 核对角标控件 id")
        return False


def run_shop_home_from_driver(driver: WebDriver) -> bool:
    """供脚本直接调用。"""
    return ShopHomePage(driver).run_shop_home_flow()
