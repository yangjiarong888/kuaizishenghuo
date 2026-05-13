"""金刚区分类弹层、日用百货列表、选规格加购与回首页。"""
from __future__ import annotations

import random
import re
import time
from typing import List, Optional

from appium.webdriver.common.appiumby import AppiumBy

from commons.logger import setup_logger
from pages.shop_locators import (
    SHOP_ID_GOODS_LIST_ITEM,
    SHOP_ID_LL_ITEM,
    SHOP_ID_MALL_CATEGORY_GOODS_NAME,
    SHOP_ID_POPUP_WIN,
    SHOP_ID_RV_GOODS,
    SHOP_ID_TV_ADD_CART_MORE,
    SHOP_ID_TV_CATEGORY,
    SHOP_ID_TV_TITLE,
    SHOP_KINGKONG_HOT_SNACKS,
    SHOP_PACKAGES,
    SHOP_TEXT_ALL_CATEGORIES,
    SHOP_TEXT_DAILY_BAIHUO,
    SHOP_TEXT_SELECT_SPEC,
)

logger = setup_logger(__name__)


class MallCategoryPage:
    """分类全弹层、``rv_goods`` 列表与「选规格」行校验；依赖 ``ShopHomePage`` 的导航与滑动。"""

    def __init__(self, owner) -> None:
        self._o = owner

    def all_categories_popup_visible(self) -> bool:
        return self._o._first_displayed_by_pkg_id(SHOP_ID_POPUP_WIN) is not None

    def tap_mall_kingkong_open_all_categories_popup(self) -> bool:
        if self.all_categories_popup_visible():
            logger.info("「全部分类」弹层已展示")
            return True
        h = self._o._window_size()[1]
        y_lo, y_hi = int(h * 0.06), int(h * 0.94)
        for text in (SHOP_TEXT_ALL_CATEGORIES,):
            try:
                for el in self._o.driver.find_elements(
                    AppiumBy.XPATH, f'//android.widget.TextView[@text="{text}"]'
                ):
                    try:
                        if not el.is_displayed():
                            continue
                        y = int(el.location.get("y", -1))
                        if not (y_lo <= y <= y_hi):
                            continue
                        self._o._nearest_clickable_ancestor(el).click()
                        logger.info("已点击「%s」打开分类弹窗", text)
                        time.sleep(1.1)
                        if self.all_categories_popup_visible():
                            return True
                    except Exception:
                        continue
            except Exception:
                pass
        for pkg in SHOP_PACKAGES:
            rid = self._o._rid(pkg, SHOP_ID_TV_TITLE)
            xp = f'//*[@resource-id="{rid}" and @text="{SHOP_TEXT_ALL_CATEGORIES}"]'
            try:
                for el in self._o.driver.find_elements(AppiumBy.XPATH, xp):
                    try:
                        if not el.is_displayed():
                            continue
                        y = int(el.location.get("y", -1))
                        if not (y_lo <= y <= y_hi):
                            continue
                        try:
                            p_rid = self._o._rid(pkg, SHOP_ID_LL_ITEM)
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
                                if self.all_categories_popup_visible():
                                    return True
                        except Exception:
                            pass
                        self._o._nearest_clickable_ancestor(el).click()
                        time.sleep(1.1)
                        if self.all_categories_popup_visible():
                            return True
                    except Exception:
                        continue
            except Exception:
                pass
        logger.error("未能打开「%s」分类弹窗", SHOP_TEXT_ALL_CATEGORIES)
        return False

    def tap_mall_category_in_all_categories_popup(self, category_name: str) -> bool:
        end = time.time() + 12.0
        while time.time() < end:
            if self.all_categories_popup_visible():
                break
            time.sleep(0.35)
        if not self.all_categories_popup_visible():
            logger.error("等待后仍无「全部分类」弹层（popup_win）")
            return False
        safe = category_name.replace('"', "").replace("'", "")[:16]
        for pkg in SHOP_PACKAGES:
            rid = self._o._rid(pkg, SHOP_ID_TV_CATEGORY)
            xp = f'//*[@resource-id="{rid}" and @text="{safe}"]'
            try:
                for el in self._o.driver.find_elements(AppiumBy.XPATH, xp):
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
                                self._o._nearest_clickable_ancestor(el).click()
                        except Exception:
                            self._o._nearest_clickable_ancestor(el).click()
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
            for el in self._o.driver.find_elements(
                AppiumBy.XPATH,
                f'//*[contains(@resource-id,":id/{SHOP_ID_TV_CATEGORY}") '
                f'and @text="{safe}"]',
            ):
                if el.is_displayed():
                    self._o._nearest_clickable_ancestor(el).click()
                    logger.info("已点击分类「%s」（tv_category 宽松 XPath）", safe)
                    time.sleep(1.6)
                    return True
        except Exception:
            pass
        logger.error("弹窗内未找到分类「%s」", safe)
        return False

    def tap_mall_kingkong_daily_baihuo_via_popup(self) -> bool:
        if not self._o.tap_kingkong_hot_snacks():
            logger.error("未能点击金刚区「%s」", SHOP_KINGKONG_HOT_SNACKS)
            return False
        time.sleep(1.0)
        end = time.time() + 12.0
        while time.time() < end:
            if self.all_categories_popup_visible():
                logger.info("已进入爆款零食分类页且「全部分类」弹层已出现")
                break
            time.sleep(0.4)
        if not self.all_categories_popup_visible():
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
        for i in range(5):
            if self._o._is_mall_home_main_list_visible():
                logger.info("已回到商城首页（主列表 rv_content 可见）")
                return True
            logger.info("离开分类/子页：第 %d 次尝试返回", i + 1)
            self._o.tap_top_back()
            time.sleep(1.0)
        logger.warning("多次返回后仍未见 rv_content，尝试点商城 Tab 并手势回顶")
        self._o.ensure_mall_tab()
        time.sleep(0.9)
        self._o.mall_list_gesture_scroll_to_top(8)
        time.sleep(0.45)
        return self._o._is_mall_home_main_list_visible()

    def uia2_scroll_rv_goods_to_beginning(self) -> bool:
        for pkg in SHOP_PACKAGES:
            rid = self._o._rid(pkg, SHOP_ID_RV_GOODS)
            expr = (
                f'new UiScrollable(new UiSelector().scrollable(true).resourceId("{rid}"))'
                f".scrollToBeginning(20)"
            )
            try:
                self._o.driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, expr)
                logger.info("UiScrollable：rv_goods 已 scrollToBeginning（%s）", pkg)
                time.sleep(0.4)
                return True
            except Exception:
                continue
        return False

    def swipe_within_rv_goods_toward_top(self, strokes: int = 10) -> None:
        el = self._o._first_displayed_by_pkg_id(SHOP_ID_RV_GOODS)
        w, h = self._o._window_size()
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
                self._o.driver.swipe(x, y_top, x, y_bot, 420)
            except Exception:
                break
            time.sleep(0.22)

    def recover_mall_category_goods_list_to_top(self) -> None:
        logger.info(
            "分类商品列表：回到顶部（UiScrollable / rv_goods 内手势，避免下拉刷新）"
        )
        self.uia2_scroll_rv_goods_to_beginning()
        self.swipe_within_rv_goods_toward_top(10)
        time.sleep(0.35)
        if self._o.tap_back_to_top_if_visible(warn_when_missing=False):
            time.sleep(0.35)
            self.swipe_within_rv_goods_toward_top(4)
            time.sleep(0.3)
        time.sleep(0.3)

    def goods_list_item_root(self, inner_el):
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

    @staticmethod
    def _parse_small_int_text(tx: str) -> Optional[int]:
        if not re.fullmatch(r"\d{1,4}", (tx or "").strip()):
            return None
        val = int(tx.strip())
        return val if val <= 999 else None

    def _scan_row_textview_qty(self, item_root, x_cut: int) -> Optional[int]:
        best: Optional[int] = None
        try:
            textviews = item_root.find_elements(
                AppiumBy.CLASS_NAME, "android.widget.TextView"
            )
        except Exception:
            return None
        for el in textviews:
            try:
                if not el.is_displayed():
                    continue
                val = self._parse_small_int_text(el.text or "")
                if val is None:
                    continue
                if x_cut and int(el.location.get("x", 0)) < x_cut:
                    continue
                best = val
            except Exception:
                continue
        return best

    def _read_qty_by_named_resource(self, item_root) -> Optional[int]:
        try:
            elements = item_root.find_elements(
                AppiumBy.XPATH,
                './/*[contains(@resource-id,"count") or contains(@resource-id,"qty") '
                'or contains(@resource-id,"amount") or contains(@resource-id,"number")]',
            )
        except Exception:
            return None
        for el in elements:
            try:
                if not el.is_displayed():
                    continue
                m = re.search(r"\d{1,4}", (el.text or "").strip())
                if m:
                    return int(m.group(0))
            except Exception:
                continue
        return None

    def read_category_row_qty(self, item_root) -> Optional[int]:
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

        for cut in (x_cut_strict, x_cut_loose):
            if cut:
                got = self._scan_row_textview_qty(item_root, cut)
                if got is not None:
                    return got

        got = self._read_qty_by_named_resource(item_root)
        if got is not None:
            return got

        if row_w > 0:
            x_far = row_left + int(row_w * 0.62)
            return self._scan_row_textview_qty(item_root, x_far)
        return None

    def first_select_spec_button_on_category(self):
        for pkg in SHOP_PACKAGES:
            rid = self._o._rid(pkg, SHOP_ID_TV_ADD_CART_MORE)
            try:
                for el in self._o.driver.find_elements(AppiumBy.ID, rid):
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
            for el in self._o.driver.find_elements(
                AppiumBy.XPATH, f'//*[@text="{SHOP_TEXT_SELECT_SPEC}"]'
            ):
                if el.is_displayed():
                    return el
        except Exception:
            pass
        return None

    def random_select_spec_button_on_category(self):
        seen: set[int] = set()
        cands: List = []
        for pkg in SHOP_PACKAGES:
            rid = self._o._rid(pkg, SHOP_ID_TV_ADD_CART_MORE)
            try:
                for el in self._o.driver.find_elements(AppiumBy.ID, rid):
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
            for el in self._o.driver.find_elements(
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

    def mall_category_goods_name_text(self, item_root) -> str:
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

    def find_goods_item_by_name_substring(self, sub: str):
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
                for el in self._o.driver.find_elements(AppiumBy.XPATH, xp):
                    if el.is_displayed():
                        return el
            except Exception:
                pass
        return None

    def _find_select_spec_button_with_scroll(self, random_pick: bool):
        spec_btn = None
        for attempt in range(12):
            spec_btn = (
                self.random_select_spec_button_on_category()
                if random_pick
                else self.first_select_spec_button_on_category()
            )
            if spec_btn:
                break
            if attempt < 11:
                self._o._swipe_mall_vertical_list_down(
                    1, 1.0, "分类商品列表(轻翻找选规格)", x_ratio=0.58
                )
        return spec_btn

    def _tap_category_spec_button_and_confirm(self, spec_btn) -> bool:
        try:
            spec_btn.click()
        except Exception:
            try:
                self._o._nearest_clickable_ancestor(spec_btn).click()
            except Exception as ex:
                logger.error("点击「%s」失败: %s", SHOP_TEXT_SELECT_SPEC, ex)
                return False
        time.sleep(0.55)
        if self._o._login_like_screen_visible():
            logger.error("点「%s」后出现登录页，请先登录", SHOP_TEXT_SELECT_SPEC)
            return False
        return self._o._mall_spec_popup_pick_and_confirm()

    def _read_after_qty_for_same_item(self, item, pname: str) -> Optional[int]:
        if pname:
            item2 = self.find_goods_item_by_name_substring(pname)
            if item2:
                return self.read_category_row_qty(item2)
        try:
            return self.read_category_row_qty(item)
        except Exception:
            return None

    @staticmethod
    def _line_qty_increased(before: Optional[int], after: Optional[int]) -> bool:
        if before is not None and after is not None:
            return after >= before + 1
        return before is None and after is not None and after >= 1

    def run_category_spec_add_verify_line_qty(
        self, *, random_pick: bool = False, log_prefix: str = "分类"
    ) -> bool:
        time.sleep(1.0)
        for pkg in SHOP_PACKAGES:
            rid = self._o._rid(pkg, SHOP_ID_RV_GOODS)
            try:
                self._o.driver.find_element(AppiumBy.ID, rid)
                break
            except Exception:
                continue
        self.recover_mall_category_goods_list_to_top()
        spec_btn = self._find_select_spec_button_with_scroll(random_pick)
        if not spec_btn:
            logger.warning(
                "%s页无「%s」商品，跳过行数量校验段", log_prefix, SHOP_TEXT_SELECT_SPEC
            )
            return True
        try:
            item = self.goods_list_item_root(spec_btn)
        except Exception as ex:
            logger.error("无法定位商品行根节点: %s", ex)
            return False
        pname = self.mall_category_goods_name_text(item)
        before = self.read_category_row_qty(item)
        pick_desc = "随机" if random_pick else "首个"
        logger.info(
            "%s：将点「%s」商品(%s)=%s 行内数量(before)=%s",
            log_prefix,
            SHOP_TEXT_SELECT_SPEC,
            pick_desc,
            (pname or "?")[:40],
            before,
        )
        if not self._tap_category_spec_button_and_confirm(spec_btn):
            return False
        time.sleep(1.0)
        after = self._read_after_qty_for_same_item(item, pname)
        logger.info("%s：同一商品行数量(after)=%s", log_prefix, after)
        if self._line_qty_increased(before, after):
            logger.info("行数量校验通过：%s → %s", before, after)
            return True
        if before is not None and after is not None:
            logger.error("行数量未 +1：before=%s after=%s", before, after)
            return False
        logger.warning(
            "行数量解析不完整 before=%s after=%s，请 Inspector 核对数量 TextView",
            before,
            after,
        )
        return True
