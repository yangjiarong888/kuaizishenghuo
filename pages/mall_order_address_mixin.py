"""Mall address selection and explicitly authorized mutation actions."""

from __future__ import annotations

import time
from typing import List, Sequence, Tuple

from appium.webdriver.common.appiumby import AppiumBy

from commons.logger import setup_logger


logger = setup_logger(__name__)
CHECKOUT_MARKERS: Tuple[str, ...] = (
    "确认订单",
    "提交订单",
    "收货地址",
    "商品金额",
    "实付",
    "应付",
)


ADDRESS_LIST_MARKERS: Tuple[str, ...] = (
    "选择地址",
    "选择收货地址",
    "收货地址",
    "新增地址",
    "地址管理",
)
ADDRESS_EDIT_MARKERS: Tuple[str, ...] = (
    "新增收货地址",
    "编辑收货地址",
    "编辑地址",
    "地图地址",
    "地址详情",
    "联系人姓名",
    "联系人电话",
    "保存",
    "联系人",
    "收货人",
    "姓名",
    "手机号",
)
ADDRESS_SEARCH_MARKERS: Tuple[str, ...] = (
    "定位地址",
    "如有大厦",
    "街道名称",
    "请直接搜索",
    "搜索收货地址",
    "搜索地址",
    "搜索地点",
    "请输入地址",
    "选择地址",
)
ADDRESS_SEARCH_STRONG_MARKERS: Tuple[str, ...] = (
    "定位地址",
    "如有大厦",
    "街道名称",
    "请直接搜索",
    "搜索收货地址",
    "搜索地址",
    "搜索地点",
    "请输入地址",
    "搜索",
)
ADDRESS_MAP_ENTRY_LABELS: Tuple[str, ...] = (
    "地图地址",
    "请从地图上选择地址",
    "从地图上选择地址",
    "选择地图地址",
    "定位地址",
)
ADDRESS_CHECKOUT_ENTRY_LABELS: Tuple[str, ...] = (
    "请选择收货地址",
    "收货地址",
    "选择地址",
    "地址",
    "送货地址",
)
ADDRESS_ADD_LABELS: Tuple[str, ...] = (
    "新增地址",
    "添加地址",
    "新建地址",
    "新增收货地址",
    "+ 新增地址",
)

class MallOrderAddressMixin:
    """Address actions composed by the compatible order-flow facade."""

    def visible_edit_texts(
        self,
        *,
        y_min_ratio: float = 0.0,
        y_max_ratio: float = 1.0,
    ) -> List:
        h = self._window_size()[1]
        y_min, y_max = int(h * y_min_ratio), int(h * y_max_ratio)
        try:
            edits = self.driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.EditText")
        except Exception:
            edits = []
        visible = []
        for el in edits:
            try:
                if not el.is_displayed():
                    continue
                y = int(el.location.get("y", 0))
                if not (y_min <= y <= y_max):
                    continue
                x = int(el.location.get("x", 0))
                visible.append((y, x, el))
            except Exception:
                continue
        visible.sort(key=lambda item: (item[0], item[1]))
        return [item[2] for item in visible]

    def edit_text_value(self, el) -> str:
        values = []
        for attr in ("text", "content-desc", "hint"):
            try:
                val = el.text if attr == "text" else el.get_attribute(attr)
            except Exception:
                val = ""
            val = (val or "").strip()
            if val:
                values.append(val)
        return " ".join(dict.fromkeys(values)).strip()

    def type_text_element(self, el, text: str, desc: str) -> bool:
        try:
            el.click()
            time.sleep(0.15)
            try:
                el.clear()
            except Exception:
                pass
            el.send_keys(text)
            logger.info("已输入%s：%s", desc, text)
            return True
        except Exception as send_ex:
            try:
                el.click()
                time.sleep(0.15)
                try:
                    el.clear()
                except Exception:
                    pass
                self.driver.set_clipboard_text(text)
                self.driver.press_keycode(279)  # Android KEYCODE_PASTE
                logger.info("已通过剪贴板输入%s：%s", desc, text)
                return True
            except Exception:
                logger.debug("输入%s失败：%s", desc, send_ex)
                return False

    def tap_ratio(self, x_ratio: float, y_ratio: float, desc: str) -> bool:
        try:
            w, h = self._window_size()
            x, y = int(w * x_ratio), int(h * y_ratio)
            self.driver.execute_script("mobile: clickGesture", {"x": x, "y": y})
            logger.info("已点击%s（坐标 %d,%d）", desc, x, y)
            time.sleep(0.65)
            return True
        except Exception as ex:
            logger.debug("坐标点击%s失败：%s", desc, ex)
            return False

    def scroll_vertical(self, start_ratio: float, end_ratio: float, *, x_ratio: float = 0.50) -> None:
        try:
            w, h = self._window_size()
            self.driver.swipe(
                int(w * x_ratio),
                int(h * start_ratio),
                int(w * x_ratio),
                int(h * end_ratio),
                430,
            )
            time.sleep(0.45)
        except Exception:
            pass

    def type_into_field_near_label(
        self,
        labels: Sequence[str],
        text: str,
        desc: str,
    ) -> bool:
        for raw in labels:
            label = self._clean_xpath_text(raw)
            if not label:
                continue
            xpaths = (
                f'//*[contains(@text,"{label}")]/following::android.widget.EditText[1]',
                f'//*[contains(@content-desc,"{label}")]/following::android.widget.EditText[1]',
                f'//android.widget.EditText[contains(@text,"{label}") or '
                f'contains(@content-desc,"{label}") or contains(@hint,"{label}")]',
            )
            for xp in xpaths:
                try:
                    elements = self.driver.find_elements(AppiumBy.XPATH, xp)
                except Exception:
                    elements = []
                for el in elements:
                    try:
                        if not el.is_displayed():
                            continue
                    except Exception:
                        continue
                    if self.type_text_element(el, text, desc):
                        return True
        return False

    def target_address_labels(self) -> Tuple[str, ...]:
        labels = (
            self.address_name,
            self.address_phone,
            self.address_query,
            self.address_detail,
        )
        return tuple(dict.fromkeys(label for label in labels if label))

    def page_has_target_address(self) -> bool:
        blob = self.page_blob()
        labels = self.target_address_labels()
        return bool(labels) and all(label in blob for label in labels)

    def is_address_search_page(self) -> bool:
        blob = self.page_blob()
        if "定位地址" in blob and any(
            marker in blob for marker in ("如有大厦", "街道名称", "请直接搜索")
        ):
            return True
        if not any(marker in blob for marker in ADDRESS_SEARCH_STRONG_MARKERS):
            return False
        return bool(self.visible_edit_texts(y_min_ratio=0.0, y_max_ratio=0.42))

    def wait_address_search_page(self, timeout: float = 6.0) -> bool:
        end = time.time() + timeout
        while time.time() < end:
            if self.is_address_search_page():
                return True
            time.sleep(0.35)
        return False

    def is_address_edit_form(self) -> bool:
        blob = self.page_blob()
        strong = (
            "新增收货地址",
            "编辑收货地址",
            "地图地址",
            "地址详情",
            "联系人姓名",
            "联系人电话",
        )
        return any(marker in blob for marker in strong) and "保存" in blob

    def wait_address_edit_form(self, timeout: float = 6.0) -> bool:
        end = time.time() + timeout
        while time.time() < end:
            if self.is_address_edit_form():
                return True
            time.sleep(0.35)
        return False

    def click_bottom_my_tab(self) -> bool:
        h = self._window_size()[1]
        candidates = []
        for xp in ('//*[@text="我的"]', '//*[@content-desc="我的"]'):
            try:
                elements = self.driver.find_elements(AppiumBy.XPATH, xp)
            except Exception:
                elements = []
            for el in elements:
                try:
                    if not el.is_displayed():
                        continue
                    y = int(el.location.get("y", 0))
                    if y < int(h * 0.55):
                        continue
                    candidates.append((y, el))
                except Exception:
                    continue
        candidates.sort(key=lambda item: item[0], reverse=True)
        for _, el in candidates:
            if self._click_element_center(el, "底部我的 Tab"):
                time.sleep(1.2)
                return True
        return self.tap_ratio(0.88, 0.95, "底部我的 Tab 兜底")

    def open_address_manage_from_my_page(self) -> None:
        if not self.click_bottom_my_tab():
            raise AssertionError("未点击到底部「我的」Tab，无法从我的页面新增地址")
        for attempt in range(5):
            if self.click_labels(
                ("我的地址", "收货地址", "地址管理", "管理地址"),
                desc="我的地址入口",
                y_min_ratio=0.10,
                y_max_ratio=0.95,
            ):
                if self.wait_page_contains_any(ADDRESS_LIST_MARKERS + ADDRESS_EDIT_MARKERS, timeout=8.0):
                    logger.info("已进入我的地址/地址管理页")
                    return
            self.scroll_vertical(0.75, 0.34)
            logger.debug("我的页查找地址入口：%d/5", attempt + 1)
        raise AssertionError("我的页面未找到「我的地址/收货地址/地址管理」入口")

    def open_address_sheet_from_checkout(self) -> None:
        self.assert_page_contains_any(CHECKOUT_MARKERS, "当前不在订单确认页，无法点击收货地址", timeout=8.0)
        for attempt in range(4):
            if self.click_labels(
                ADDRESS_CHECKOUT_ENTRY_LABELS,
                desc="订单确认页地址入口",
                y_min_ratio=0.08,
                y_max_ratio=0.62,
            ):
                if self.wait_page_contains_any(ADDRESS_LIST_MARKERS + ADDRESS_EDIT_MARKERS, timeout=6.0):
                    logger.info("已从订单确认页打开地址弹窗/地址页")
                    return
            if attempt == 1:
                self.tap_ratio(0.50, 0.20, "订单确认页地址行兜底")
                if self.wait_page_contains_any(ADDRESS_LIST_MARKERS + ADDRESS_EDIT_MARKERS, timeout=5.0):
                    logger.info("已从订单确认页打开地址弹窗/地址页")
                    return
            self.scroll_vertical(0.30, 0.76)
        raise AssertionError("订单确认页未能打开收货地址弹窗/地址列表")

    def select_existing_target_address(self, *, expect_checkout: bool) -> bool:
        if not self.page_has_target_address():
            return False
        for label in self.target_address_labels():
            if self.click_labels(
                (label,),
                desc="选择已有测试地址",
                y_min_ratio=0.12,
                y_max_ratio=0.92,
            ):
                time.sleep(1.0)
                self.click_labels(
                    ("确定", "确认", "完成"),
                    desc="确认选择已有测试地址",
                    y_min_ratio=0.45,
                    y_max_ratio=1.0,
                )
                if expect_checkout:
                    if self.wait_page_contains_any(CHECKOUT_MARKERS, timeout=6.0):
                        logger.info("已选择已有测试地址并回到确认订单页")
                        return True
                else:
                    logger.info("已命中已有测试地址")
                    return True
        return False

    def find_target_address_anchor(self):
        h = self._window_size()[1]
        y_min, y_max = int(h * 0.12), int(h * 0.90)
        for raw in self.target_address_labels():
            label = self._clean_xpath_text(raw)
            if not label:
                continue
            xp = f'//*[contains(@text,"{label}") or contains(@content-desc,"{label}")]'
            try:
                elements = self.driver.find_elements(AppiumBy.XPATH, xp)
            except Exception:
                elements = []
            for el in elements:
                try:
                    if not el.is_displayed():
                        continue
                    y = int(el.location.get("y", 0))
                    if not (y_min <= y <= y_max):
                        continue
                    return el
                except Exception:
                    continue
        return None

    def address_anchor_row_y_ratio(self, anchor) -> float:
        try:
            loc = anchor.location
            size = anchor.size
            _, h = self._window_size()
            return (int(loc.get("y", 0)) + int(size.get("height", 0)) // 2) / max(h, 1)
        except Exception:
            return 0.42

    def open_target_address_edit_form(self) -> bool:
        anchor = self.find_target_address_anchor()
        if not anchor:
            logger.warning("当前地址列表/弹窗未找到目标地址，无法进入编辑")
            return False
        row_y_ratio = self.address_anchor_row_y_ratio(anchor)

        for x_ratio in (0.84, 0.88, 0.78):
            if self.tap_ratio(x_ratio, row_y_ratio, "目标地址右侧编辑按钮"):
                if self.wait_address_edit_form(timeout=7.0):
                    logger.info("已进入编辑收货地址页")
                    return True
        if self.click_labels(
            ("编辑", "修改"),
            desc="地址编辑按钮",
            y_min_ratio=max(0.10, row_y_ratio - 0.08),
            y_max_ratio=min(0.95, row_y_ratio + 0.08),
        ):
            if self.wait_address_edit_form(timeout=7.0):
                logger.info("已进入编辑收货地址页")
                return True
        logger.warning("已尝试点击目标地址编辑按钮，但未进入编辑收货地址页")
        return False

    def copy_target_address_in_current_parent(self, *, expect_checkout: bool) -> bool:
        anchor = self.find_target_address_anchor()
        if not anchor:
            logger.warning("当前地址列表/弹窗未找到目标地址，无法复制")
            return False
        row_y_ratio = self.address_anchor_row_y_ratio(anchor)
        x_candidates = (0.94, 0.92, 0.90) if expect_checkout else (0.66, 0.69, 0.72)
        for x_ratio in x_candidates:
            if not self.tap_ratio(x_ratio, row_y_ratio, "目标地址复制按钮"):
                continue
            time.sleep(0.8)
            self.click_labels(
                ("确认复制", "复制", "确定", "确认"),
                desc="复制地址确认",
                y_min_ratio=0.25,
                y_max_ratio=1.0,
            )
            if self.wait_address_search_page(timeout=2.0):
                self.search_and_select_address_location()
                self.fill_test_address_form()
                self.save_test_address_form()
                return self.finish_address_copy_parent(expect_checkout=expect_checkout)
            if self.wait_address_edit_form(timeout=3.0):
                if "请从地图上选择地址" in self.page_blob():
                    self.search_and_select_address_location()
                self.fill_test_address_form()
                self.save_test_address_form()
                return self.finish_address_copy_parent(expect_checkout=expect_checkout)
            if self.wait_page_contains_any(ADDRESS_LIST_MARKERS + CHECKOUT_MARKERS, timeout=3.0):
                return self.finish_address_copy_parent(expect_checkout=expect_checkout)
        logger.warning("已尝试点击目标地址复制按钮，但未识别到复制后的页面状态")
        return False

    def finish_address_copy_parent(self, *, expect_checkout: bool) -> bool:
        if expect_checkout:
            if self.wait_page_contains_any(CHECKOUT_MARKERS, timeout=3.0):
                logger.info("复制地址后已回到订单确认页")
                return True
            if self.select_existing_target_address(expect_checkout=True):
                logger.info("复制地址后已选择地址并回到订单确认页")
                return True
            self.tap_top_back()
            ok = self.wait_page_contains_any(CHECKOUT_MARKERS, timeout=5.0)
            if ok:
                logger.info("复制地址后通过返回回到订单确认页")
            return ok
        if self.wait_page_contains_any(ADDRESS_LIST_MARKERS, timeout=5.0):
            logger.info("复制地址后停留/返回地址管理页")
            return True
        return True

    def edit_test_address_in_current_parent(self, *, expect_checkout: bool) -> bool:
        if not self.open_target_address_edit_form():
            return False
        self.search_and_select_address_location()
        self.fill_test_address_form()
        self.save_test_address_form()
        if expect_checkout:
            if self.wait_page_contains_any(CHECKOUT_MARKERS, timeout=3.0):
                return True
            if self.select_existing_target_address(expect_checkout=True):
                return True
            self.tap_top_back()
            return self.wait_page_contains_any(CHECKOUT_MARKERS, timeout=5.0)
        return True

    def open_add_address_form(self) -> None:
        if self.wait_address_edit_form(timeout=1.0) or self.wait_address_search_page(timeout=1.0):
            return
        for attempt in range(4):
            if self.click_labels(
                ADDRESS_ADD_LABELS,
                desc="新增地址按钮",
                y_min_ratio=0.06,
                y_max_ratio=0.98,
            ):
                if self.wait_address_edit_form(timeout=8.0) or self.wait_address_search_page(timeout=2.0):
                    logger.info("已进入新增收货地址/定位地址页")
                    return
            if attempt == 1:
                self.tap_ratio(0.50, 0.92, "新增地址底部按钮兜底")
                if self.wait_address_edit_form(timeout=6.0) or self.wait_address_search_page(timeout=2.0):
                    logger.info("已进入新增收货地址/定位地址页")
                    return
            if attempt == 2:
                self.tap_ratio(0.92, 0.08, "新增地址右上角按钮兜底")
                if self.wait_address_edit_form(timeout=6.0) or self.wait_address_search_page(timeout=2.0):
                    logger.info("已进入新增收货地址/定位地址页")
                    return
            self.scroll_vertical(0.75, 0.34)
        raise AssertionError("地址列表/弹窗中未找到「新增地址」按钮")

    def open_address_search_from_edit(self) -> None:
        if self.wait_address_search_page(timeout=1.0):
            return
        self.assert_page_contains_any(ADDRESS_EDIT_MARKERS, "当前不在新增/编辑收货地址页，无法唤起地图", timeout=6.0)
        opener_groups = (
            ADDRESS_MAP_ENTRY_LABELS,
            ("请选择地址", "选择地址", "所在地址", "所在地区"),
        )
        for labels in opener_groups:
            if self.click_labels(
                labels,
                desc="新增/编辑页地图地址入口",
                y_min_ratio=0.08,
                y_max_ratio=0.38,
            ):
                if self.wait_address_search_page(timeout=6.0):
                    logger.info("已进入定位地址地图页")
                    return
        for y_ratio in (0.34, 0.28, 0.40):
            self.tap_ratio(0.55, y_ratio, "新增/编辑页地图地址入口兜底")
            if self.wait_address_search_page(timeout=5.0):
                logger.info("已进入定位地址地图页")
                return
        raise AssertionError("新增/编辑收货地址页未打开定位地址地图页")

    def type_into_address_map_search(self) -> bool:
        if self._type_into_best_edit_text(self.address_query, allow_open_search=False):
            return True
        if self.click_labels(
            ("如有大厦", "街道名称", "请直接搜索", "搜索"),
            desc="定位地址搜索框",
            y_min_ratio=0.05,
            y_max_ratio=0.22,
        ):
            if self._type_into_best_edit_text(self.address_query, allow_open_search=False):
                return True
        self.tap_ratio(0.45, 0.13, "定位地址搜索框兜底")
        return self._type_into_best_edit_text(self.address_query, allow_open_search=False)

    def address_search_result_labels(self) -> Tuple[str, ...]:
        labels = (
            self.address_query,
            self.address_query.split(",")[0].strip(),
        )
        return tuple(dict.fromkeys(label for label in labels if label))

    def search_and_select_address_location(self) -> None:
        self.open_address_search_from_edit()
        if not self.type_into_address_map_search():
            raise AssertionError("定位地址地图页未找到可输入的搜索框")
        self._press_enter_or_search()
        try:
            self.driver.hide_keyboard()
        except Exception:
            pass
        result_labels = self.address_search_result_labels()
        if not self.wait_page_contains_any(result_labels, timeout=8.0):
            logger.warning("地址搜索结果未明确出现目标文案，尝试点击首条结果")
        clicked = False
        for y_min in (0.20, 0.12):
            if self.click_labels(
                result_labels,
                desc="地址搜索结果",
                y_min_ratio=y_min,
                y_max_ratio=0.92,
            ):
                clicked = True
                break
        if not clicked:
            for y_ratio in (0.30, 0.58, 0.66):
                if self.tap_ratio(0.50, y_ratio, "定位地址搜索结果兜底"):
                    clicked = True
                    break
        if not clicked:
            raise AssertionError("地址搜索页未选中目标地址结果")
        time.sleep(1.0)
        self.click_labels(
            ("使用该地址", "选择该地址", "确认地址", "确定", "完成"),
            desc="确认地址搜索结果",
            y_min_ratio=0.42,
            y_max_ratio=1.0,
        )
        if not self.wait_address_edit_form(timeout=8.0):
            if self.wait_page_contains_any(ADDRESS_SEARCH_MARKERS, timeout=1.0):
                self.tap_top_back()
                time.sleep(0.8)
        if not self.wait_address_edit_form(timeout=6.0):
            raise AssertionError("地图地址选中后未回到新增/编辑收货地址页")
        logger.info("已搜索并选中地址：%s", self.address_query)

    def fill_test_address_form(self) -> None:
        if not self.wait_address_edit_form(timeout=8.0):
            raise AssertionError("当前不在新增/编辑收货地址页，无法填写地址表单")
        detail_ok = False
        name_ok = False
        phone_ok = False
        wechat_ok = False
        for attempt in range(3):
            if not detail_ok and self.address_detail:
                detail_ok = self.type_into_field_near_label(
                    ("地址详情", "详细地址", "门牌号", "楼层", "房间号", "补充地址"),
                    self.address_detail,
                    "详细地址",
                )
            if not name_ok:
                name_ok = self.type_into_field_near_label(
                    ("联系人姓名", "姓名", "收货人", "联系人", "名称"),
                    self.address_name,
                    "收货人姓名",
                )
            if not phone_ok:
                phone_ok = self.type_into_field_near_label(
                    ("联系人电话", "手机号", "手机号码", "联系电话", "电话"),
                    self.address_phone,
                    "手机号",
                )
            if not wechat_ok:
                wechat_ok = self.type_into_field_near_label(
                    ("微信号", "微信", "Wechat", "WeChat"),
                    self.address_wechat,
                    "微信号",
                )
            if name_ok and phone_ok and wechat_ok:
                break
            self.scroll_vertical(0.72, 0.36)
            logger.debug("地址表单按标签填写未完成，继续滚动查找：%d/3", attempt + 1)

        fallback_values = []
        if not name_ok:
            fallback_values.append((self.address_name, "收货人姓名"))
        if not phone_ok:
            fallback_values.append((self.address_phone, "手机号"))
        if not wechat_ok:
            fallback_values.append((self.address_wechat, "微信号"))
        used = set()
        for text, desc in fallback_values:
            typed = False
            for el in self.visible_edit_texts(y_min_ratio=0.12, y_max_ratio=0.92):
                key = id(el)
                if key in used:
                    continue
                current = self.edit_text_value(el)
                if text in current or self.address_query in current:
                    continue
                if self.type_text_element(el, text, f"{desc}(顺序兜底)"):
                    used.add(key)
                    typed = True
                    break
            if desc == "收货人姓名":
                name_ok = name_ok or typed
            elif desc == "手机号":
                phone_ok = phone_ok or typed
            elif desc == "微信号":
                wechat_ok = wechat_ok or typed

        if not (name_ok and phone_ok and wechat_ok):
            raise AssertionError(
                "地址编辑页未完成必填信息："
                f"name={name_ok}, phone={phone_ok}, wechat={wechat_ok}"
            )
        logger.info(
            "地址表单填写完成：name=%s phone=%s wechat=%s",
            self.address_name,
            self.address_phone,
            self.address_wechat,
        )

    def save_test_address_form(self) -> None:
        try:
            self.driver.hide_keyboard()
        except Exception:
            pass
        if not self.click_labels(
            ("保存", "完成", "确定", "提交"),
            desc="保存地址",
            y_min_ratio=0.42,
            y_max_ratio=1.0,
        ):
            if not self.tap_ratio(0.50, 0.92, "保存地址按钮兜底"):
                raise AssertionError("地址编辑页未找到保存/完成按钮")
        deadline = time.time() + 10.0
        while time.time() < deadline:
            blob = self.page_blob()
            if (
                any(marker in blob for marker in CHECKOUT_MARKERS + ADDRESS_LIST_MARKERS)
                and ("保存" not in blob or self.page_has_target_address())
            ):
                logger.info("地址保存后已返回上级页面")
                return
            time.sleep(0.4)
        logger.warning("地址保存后未明确返回上级页，继续由后续页面断言判断")

    def add_test_address(self) -> None:
        self.open_add_address_form()
        self.search_and_select_address_location()
        self.fill_test_address_form()
        self.save_test_address_form()

    def ensure_test_address_from_checkout_flow(self, *, force_add: bool = False) -> None:
        logger.info("开始在订单确认页处理测试收货地址")
        self.open_address_sheet_from_checkout()
        if self.copy_test_address and self.page_has_target_address():
            if self.copy_target_address_in_current_parent(expect_checkout=True):
                logger.info("订单确认页测试地址复制完成")
                return
            logger.warning("目标地址复制未完成，继续按编辑/新增/选择地址流程处理")
        if self.edit_test_address and self.page_has_target_address():
            if self.edit_test_address_in_current_parent(expect_checkout=True):
                logger.info("订单确认页测试地址编辑完成")
                return
            logger.warning("目标地址编辑未完成，继续按新增/选择地址流程处理")
        if not force_add and self.select_existing_target_address(expect_checkout=True):
            return
        self.add_test_address()
        if not self.wait_page_contains_any(CHECKOUT_MARKERS, timeout=5.0):
            blob = self.page_blob()
            if "保存" not in blob and self.select_existing_target_address(expect_checkout=True):
                return
            self.tap_top_back()
        self.assert_page_contains_any(CHECKOUT_MARKERS, "新增地址后未回到订单确认页", timeout=8.0)
        logger.info("订单确认页测试地址处理完成")

    def ensure_test_address_from_my_page_flow(self, *, force_add: bool = False) -> bool:
        logger.info("开始从我的页面处理测试收货地址")
        self.open_address_manage_from_my_page()
        if self.copy_test_address and self.page_has_target_address():
            if self.copy_target_address_in_current_parent(expect_checkout=False):
                logger.info("我的页面测试地址复制完成")
                return True
            logger.warning("目标地址复制未完成，继续按编辑/新增/选择地址流程处理")
        if self.edit_test_address and self.page_has_target_address():
            if self.edit_test_address_in_current_parent(expect_checkout=False):
                logger.info("我的页面测试地址编辑完成")
                return True
            logger.warning("目标地址编辑未完成，继续按新增/选择地址流程处理")
        if not force_add and self.select_existing_target_address(expect_checkout=False):
            return True
        self.add_test_address()
        if not self.wait_page_contains_any(ADDRESS_LIST_MARKERS, timeout=5.0):
            logger.warning("新增地址后未明确回到地址列表，当前页面将由日志辅助确认")
        if not self.page_has_target_address():
            logger.warning("地址列表未直接识别到目标地址，可能需要在真机确认保存结果")
        logger.info("我的页面测试地址处理完成")
        return True

    # ---------- 正常流 ----------
