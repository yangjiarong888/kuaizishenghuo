from types import SimpleNamespace

import pytest


pytestmark = pytest.mark.unit


def test_detect_first_adb_device_id_returns_first_ready_device():
    from commons.android_runtime import detect_first_adb_device_id

    def run(*args, **kwargs):
        return SimpleNamespace(
            returncode=0,
            stdout="List of devices attached\nserial-1 device\nserial-2 offline\n",
        )

    assert detect_first_adb_device_id(run=run) == "serial-1"


def test_detect_launchable_activity_expands_relative_activity():
    from commons.android_runtime import detect_launchable_activity

    def run(*args, **kwargs):
        return SimpleNamespace(
            returncode=0, stdout="com.example/.MainActivity\n"
        )

    assert (
        detect_launchable_activity("com.example", run=run)
        == "com.example.MainActivity"
    )


class RecordingDriver:
    def __init__(self):
        self.calls = []

    def terminate_app(self, package):
        self.calls.append(("terminate", package))

    def start_activity(self, package, activity):
        self.calls.append(("start", package, activity))

    def activate_app(self, package):
        self.calls.append(("activate", package))


def test_post_session_launch_cold_terminates_then_starts():
    from commons.android_runtime import post_session_android_launch
    from commons.config import AppConfig

    driver = RecordingDriver()

    mode = post_session_android_launch(driver, AppConfig(), start_mode="cold")

    assert mode == "cold"
    assert driver.calls == [
        ("terminate", "com.bs.feifubao"),
        (
            "start",
            "com.bs.feifubao",
            "com.bs.feifubao.activity.MainActivity",
        ),
    ]


def test_post_session_launch_off_has_no_side_effect():
    from commons.android_runtime import post_session_android_launch
    from commons.config import AppConfig

    driver = RecordingDriver()

    assert post_session_android_launch(driver, AppConfig(), start_mode="off") == "off"
    assert driver.calls == []
