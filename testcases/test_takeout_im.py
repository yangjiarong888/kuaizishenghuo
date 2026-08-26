import pytest

from pages.takeout_im_mixin import TakeoutIMMixin


pytestmark = pytest.mark.unit


class IMRecorder(TakeoutIMMixin):
    driver = object()
    expected_events = [
        ("send_text", "测试内容，请忽略"),
        "verify_text",
        "open_gallery",
        "pick_first_non_camera",
        "send_photo",
        "verify_photo",
        "open_emoji",
        "pick_first_emoji",
        "verify_emoji",
    ]

    def __init__(self, failed_event=None):
        self.events = []
        self.failed_event = failed_event

    def _record(self, event):
        self.events.append(event)
        return event != self.failed_event

    def _send_takeout_im_text(self, message):
        return self._record(("send_text", message))

    def _verify_takeout_im_text(self, _message):
        return self._record("verify_text")

    def _open_takeout_im_gallery(self):
        return self._record("open_gallery")

    def _pick_first_non_camera_gallery_photo(self):
        return self._record("pick_first_non_camera")

    def _send_selected_takeout_im_photo(self):
        return self._record("send_photo")

    def _verify_takeout_im_photo(self):
        return self._record("verify_photo")

    def _open_takeout_im_emoji(self):
        return self._record("open_emoji")

    def _pick_first_takeout_im_emoji(self):
        return self._record("pick_first_emoji")

    def _verify_takeout_im_emoji(self):
        return self._record("verify_emoji")


def test_im_bundle_sends_and_verifies_all_three_payloads():
    page = IMRecorder()
    assert page.send_takeout_im_bundle()
    assert page.events == page.expected_events


@pytest.mark.parametrize("failed_event", ["verify_text", "verify_photo", "verify_emoji"])
def test_im_bundle_stops_at_failed_verification(failed_event):
    page = IMRecorder(failed_event=failed_event)
    assert page.send_takeout_im_bundle() is False
    failure_index = page.expected_events.index(failed_event)
    assert page.events == page.expected_events[: failure_index + 1]


def test_gallery_picker_never_requests_skip_label():
    source = open("pages/takeout_im_mixin.py", encoding="utf-8").read()
    assert '_im_click_labels(("跳过"' not in source
