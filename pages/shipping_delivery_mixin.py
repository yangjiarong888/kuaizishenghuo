"""Delivery-slot selection safeguards for the shipping checkout."""

from datetime import date
import re

from appium.webdriver.common.appiumby import AppiumBy

from .app_common import logger
from .shipping_types import earliest_future_label, parse_delivery_date


class ShippingDeliveryMixin:
    """Select and verify a delivery date that is strictly in the future."""

    _DELIVERY_OPENERS = ("预约配送", "配送时间", "选择上门时间", "选择配送时间")
    _DELIVERY_DISABLED_MARKERS = ("disabled", "不可用", "禁用", "已满", "灰色")
    _PICKER_MARKERS = ("选择上门时间", "选择配送时间", "配送时间选择")
    _PICKER_SLOT_SELECTOR = (
        '//*[contains(@resource-id,"delivery_slot") '
        'or contains(@resource-id,"appointment_slot") '
        'or contains(@resource-id,"delivery_date_picker") '
        'or contains(@resource-id,"delivery_time_picker") '
        'or contains(@resource-id,"time_slot") '
        'or @content-desc="配送日期选择" '
        'or @content-desc="配送时段选择"]'
    )
    _CHECKOUT_DELIVERY_FIELD_SELECTOR = (
        '//*[contains(@resource-id,"delivery_time") '
        'or contains(@resource-id,"appointment_time") '
        'or @content-desc="配送时间" '
        'or @content-desc="预约配送" '
        'or @text="配送时间" '
        'or @text="预约配送"]'
    )
    _TIME_RANGE = re.compile(
        r"(?:[01]?\d|2[0-3]):[0-5]\d\s*[-~至]\s*(?:[01]?\d|2[0-3]):[0-5]\d"
    )
    _DELIVERY_TRANSITION_TIMEOUT = 1

    def device_today(self) -> date:
        """Read the device clock without ever falling back to the host clock."""
        try:
            raw = str(self.driver.get_device_time())
            return date.fromisoformat(raw[:10])
        except Exception as exc:
            raise AssertionError("无法读取设备日期，禁止选择配送时间") from exc

    def select_earliest_future_delivery(self, today: date | None = None) -> date:
        """Choose the earliest enabled delivery slot after ``today`` and read it back."""
        base = today if today is not None else self.device_today()
        if not self._click_text(self._DELIVERY_OPENERS):
            raise AssertionError("提交订单页未打开配送时间选择器")
        if not self._wait_until(
            self._is_delivery_picker_open, timeout=self._DELIVERY_TRANSITION_TIMEOUT
        ):
            raise AssertionError("配送时间选择器未打开")

        elements = self._picker_slot_elements()
        combined = [
            element
            for element in elements
            if self._is_combined_slot(self._element_blob(element))
        ]
        if combined:
            chosen_date = self._select_earliest_future_date(combined, base)
        else:
            date_controls = [
                element
                for element in elements
                if parse_delivery_date(self._element_blob(element), base) is not None
                and not self._is_time_range(self._element_blob(element))
            ]
            chosen_date = self._select_earliest_future_date(date_controls, base)
            time_control = self._wait_for_enabled_time_slot()
            self._click_delivery_element(time_control, "配送时段")
        self._confirm_or_verify_picker_auto_closed()
        self.verify_selected_delivery_date(chosen_date, base)
        logger.info("配送日期已选择 selected=%s today=%s", chosen_date, base)
        return chosen_date

    def verify_selected_delivery_date(self, selected: date, today: date) -> bool:
        """Fail closed unless checkout displays exactly the future date selected."""
        parsed = parse_delivery_date(self._checkout_delivery_text(), today)
        if parsed is None:
            raise AssertionError("提交订单页配送时间无法解析")
        if parsed <= today:
            raise AssertionError("配送日期必须严格晚于今天")
        if parsed != selected:
            raise AssertionError(
                f"配送日期回读不一致 selected={selected} actual={parsed}"
            )
        return True

    def _select_earliest_future_date(self, elements: list, today: date) -> date:
        labels = [self._element_blob(element) for element in elements]
        try:
            chosen_label, chosen_date = earliest_future_label(labels, today)
        except ValueError as exc:
            raise AssertionError("未找到严格晚于今天的可选配送日期") from exc
        chosen = next(
            (
                element
                for element in elements
                if self._element_blob(element) == chosen_label
                and self._element_enabled(element)
            ),
            None,
        )
        if chosen is None:
            raise AssertionError("未来配送日期选项不可点击")
        self._click_delivery_element(chosen, "未来配送日期")
        return chosen_date

    def _click_delivery_element(self, element, label: str) -> None:
        try:
            element.click()
        except Exception as exc:
            raise AssertionError(f"{label}点击失败") from exc

    def _picker_slot_elements(self) -> list:
        """Return eligible controls with an explicit delivery-slot identity."""
        try:
            elements = self.driver.find_elements(
                AppiumBy.XPATH, self._PICKER_SLOT_SELECTOR
            )
        except Exception as exc:
            logger.debug(
                "Shipping delivery candidate lookup failed error_type=%s",
                type(exc).__name__,
            )
            return []
        return [element for element in elements if self._element_enabled(element)]

    def _is_delivery_picker_open(self) -> bool:
        return any(marker in self.page_blob() for marker in self._PICKER_MARKERS) and bool(
            self._picker_slot_elements()
        )

    def _is_checkout_rendered(self) -> bool:
        blob = self.page_blob()
        return "提交订单" in blob and not any(
            marker in blob for marker in self._PICKER_MARKERS
        )

    def _confirm_or_verify_picker_auto_closed(self) -> None:
        if self._wait_until(
            self._is_checkout_rendered, timeout=self._DELIVERY_TRANSITION_TIMEOUT
        ):
            return
        if not self._click_text(("确定", "确认")):
            raise AssertionError("未找到配送时间确认按钮")
        if not self._wait_until(
            self._is_checkout_rendered, timeout=self._DELIVERY_TRANSITION_TIMEOUT
        ):
            raise AssertionError("确认后未返回提交订单页")

    def _wait_for_enabled_time_slot(self):
        time_control = None

        def time_slot_ready():
            nonlocal time_control
            time_control = self._first_enabled_time_slot()
            return time_control is not None

        if self._wait_until(time_slot_ready, timeout=self._DELIVERY_TRANSITION_TIMEOUT):
            return time_control
        if not self._is_delivery_picker_open():
            raise AssertionError("选择日期后配送时间选择器已关闭")
        raise AssertionError("选择日期后未出现可选配送时段")

    def _first_enabled_time_slot(self):
        return next(
            (
                element
                for element in self._picker_slot_elements()
                if self._is_time_range(self._element_blob(element))
                and self._element_enabled(element)
            ),
            None,
        )

    def _element_enabled(self, element) -> bool:
        try:
            if not element.is_displayed() or not element.is_enabled():
                return False
        except Exception:
            return False
        attributes = []
        for name in ("enabled", "clickable", "class", "style", "resource-id", "content-desc"):
            try:
                value = element.get_attribute(name)
                attributes.append("" if value is None else str(value).lower())
            except Exception:
                continue
        if any(value in {"false", "0", "no"} for value in attributes[:2]):
            return False
        visible_blob = self._element_blob(element).lower()
        return not any(
            marker in value
            for value in (*attributes, visible_blob)
            for marker in self._DELIVERY_DISABLED_MARKERS
        )

    @staticmethod
    def _element_blob(element) -> str:
        values = []
        try:
            values.append(str(element.text or ""))
        except Exception:
            pass
        for name in ("text", "content-desc"):
            try:
                values.append(str(element.get_attribute(name) or ""))
            except Exception:
                pass
        return " ".join(dict.fromkeys(value.strip() for value in values if value.strip()))

    def _checkout_delivery_text(self) -> str:
        try:
            elements = self.driver.find_elements(
                AppiumBy.XPATH, self._CHECKOUT_DELIVERY_FIELD_SELECTOR
            )
        except Exception as exc:
            logger.debug(
                "Shipping checkout delivery field lookup failed error_type=%s",
                type(exc).__name__,
            )
            elements = []
        for element in elements:
            try:
                if element.is_displayed():
                    text = self._element_blob(element)
                    if text:
                        return text
            except Exception:
                continue
        raise AssertionError("提交订单页未找到配送时间回读字段")

    @classmethod
    def _is_time_range(cls, label: str) -> bool:
        return bool(cls._TIME_RANGE.search(label))

    @classmethod
    def _is_combined_slot(cls, label: str) -> bool:
        return cls._is_time_range(label) and any(
            marker in label for marker in ("今天", "明天", "后天", "月", "年")
        )
