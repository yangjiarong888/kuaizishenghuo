"""Shared takeout IM actions: text, one gallery photo, then one emoji."""

from __future__ import annotations

import time
from typing import Sequence

from appium.webdriver.common.appiumby import AppiumBy

from commons.logger import setup_logger


logger = setup_logger(__name__)
DEFAULT_TAKEOUT_IM_MESSAGE = "测试内容，请忽略"


class TakeoutIMMixin:
    def _im_source(self) -> str:
        try:
            return self.driver.page_source or ""
        except Exception:
            return ""

    def _im_click_labels(
        self, labels: Sequence[str], *, y_min_ratio: float = 0.0
    ) -> bool:
        try:
            height = int(self.driver.get_window_size().get("height", 1920))
        except Exception:
            height = 1920
        for raw in labels:
            safe = raw.replace('"', "").replace("'", "")[:48]
            xpath = (
                f'//*[contains(@text,"{safe}") or '
                f'contains(@content-desc,"{safe}")]'
            )
            try:
                elements = self.driver.find_elements(AppiumBy.XPATH, xpath)
            except Exception:
                elements = []
            for element in elements:
                try:
                    if not element.is_displayed() or not element.is_enabled():
                        continue
                    if int(element.location.get("y", 0)) < int(
                        height * y_min_ratio
                    ):
                        continue
                    target = self._nearest_clickable_ancestor(element)
                    target.click()
                    time.sleep(0.45)
                    return True
                except Exception:
                    continue
        return False

    def _send_takeout_im_text(self, message: str) -> bool:
        before = self._im_source().count(message)
        candidates = (
            '//android.widget.EditText[@text="输入消息"]',
            '//android.widget.EditText[contains(@content-desc,"输入")]',
            '//android.widget.EditText',
        )
        edit = None
        for xpath in candidates:
            try:
                edit = next(
                    (
                        el
                        for el in self.driver.find_elements(AppiumBy.XPATH, xpath)
                        if el.is_displayed() and el.is_enabled()
                    ),
                    None,
                )
            except Exception:
                edit = None
            if edit:
                break
        if not edit:
            return False
        try:
            edit.click()
            edit.clear()
            edit.send_keys(message)
        except Exception:
            return False
        if not self._im_click_labels(("发送",), y_min_ratio=0.55):
            try:
                self.driver.press_keycode(66)
            except Exception:
                return False
        self._takeout_im_text_before_count = before
        return True

    def _verify_takeout_im_text(self, message: str) -> bool:
        before = getattr(self, "_takeout_im_text_before_count", 0)
        end = time.monotonic() + 6.0
        while time.monotonic() < end:
            if self._im_source().count(message) > before:
                return True
            time.sleep(0.25)
        return False

    def _open_takeout_im_gallery(self) -> bool:
        self._takeout_im_photo_before = self._im_source().count("图片")
        return self._im_click_labels(("图片", "相册", "照片"), y_min_ratio=0.55)

    def _pick_first_non_camera_gallery_photo(self) -> bool:
        self._im_click_labels(("允许", "本次运行允许", "仅在使用中允许"))
        try:
            height = int(self.driver.get_window_size().get("height", 1920))
            width = int(self.driver.get_window_size().get("width", 1080))
        except Exception:
            width, height = 1080, 1920
        candidates = []
        for class_name in ("android.widget.ImageView", "android.view.View"):
            try:
                elements = self.driver.find_elements(AppiumBy.CLASS_NAME, class_name)
            except Exception:
                elements = []
            for element in elements:
                try:
                    if not element.is_displayed() or not element.is_enabled():
                        continue
                    blob = " ".join(
                        str(element.get_attribute(name) or "")
                        for name in ("text", "content-desc", "resource-id")
                    ).lower()
                    if any(word in blob for word in ("camera", "相机", "拍照", "跳过")):
                        continue
                    x = int(element.location.get("x", 0))
                    y = int(element.location.get("y", 0))
                    w = int(element.size.get("width", 0))
                    h = int(element.size.get("height", 0))
                    if w < width * 0.12 or h < height * 0.07:
                        continue
                    if y < height * 0.12 or y > height * 0.88:
                        continue
                    candidates.append((y, x, element))
                except Exception:
                    continue
        for _, _, element in sorted(candidates, key=lambda item: (item[0], item[1])):
            try:
                element.click()
                time.sleep(0.5)
                return True
            except Exception:
                continue
        return False

    def _send_selected_takeout_im_photo(self) -> bool:
        # Some galleries send on tile selection; others expose a confirmation.
        if self._im_click_labels(("发送", "完成", "确定"), y_min_ratio=0.55):
            return True
        return any(marker in self._im_source() for marker in ("输入消息", "表情"))

    def _verify_takeout_im_photo(self) -> bool:
        before = getattr(self, "_takeout_im_photo_before", 0)
        end = time.monotonic() + 7.0
        while time.monotonic() < end:
            source = self._im_source()
            if source.count("图片") > before or any(
                marker in source for marker in ("发送成功", "image_message", "消息图片")
            ):
                return True
            time.sleep(0.25)
        return False

    def _open_takeout_im_emoji(self) -> bool:
        self._takeout_im_emoji_before = self._im_source().count("表情消息")
        return self._im_click_labels(("表情", "emoji"), y_min_ratio=0.55)

    def _pick_first_takeout_im_emoji(self) -> bool:
        try:
            height = int(self.driver.get_window_size().get("height", 1920))
        except Exception:
            height = 1920
        try:
            elements = self.driver.find_elements(
                AppiumBy.XPATH,
                '//*[@clickable="true" and (contains(@content-desc,"表情") '
                'or contains(@resource-id,"emoji") or contains(@resource-id,"sticker"))]',
            )
        except Exception:
            elements = []
        for element in elements:
            try:
                y = int(element.location.get("y", 0))
                if element.is_displayed() and element.is_enabled() and y < height * 0.88:
                    element.click()
                    time.sleep(0.4)
                    return True
            except Exception:
                continue
        return False

    def _verify_takeout_im_emoji(self) -> bool:
        before = getattr(self, "_takeout_im_emoji_before", 0)
        end = time.monotonic() + 6.0
        while time.monotonic() < end:
            source = self._im_source()
            if source.count("表情消息") > before or any(
                marker in source for marker in ("sticker_message", "emoji_message")
            ):
                return True
            time.sleep(0.25)
        return False

    def send_takeout_im_bundle(
        self, message: str = DEFAULT_TAKEOUT_IM_MESSAGE
    ) -> bool:
        steps = (
            lambda: self._send_takeout_im_text(message),
            lambda: self._verify_takeout_im_text(message),
            self._open_takeout_im_gallery,
            self._pick_first_non_camera_gallery_photo,
            self._send_selected_takeout_im_photo,
            self._verify_takeout_im_photo,
            self._open_takeout_im_emoji,
            self._pick_first_takeout_im_emoji,
            self._verify_takeout_im_emoji,
        )
        return all(step() for step in steps)
