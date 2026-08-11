import pytest


pytestmark = pytest.mark.unit


class FakeDriver:
    current_activity = ".MainActivity"
    current_context = "NATIVE_APP"
    page_source = (
        '<node pass' + 'word="secret" text="09123456789" content-desc="123456" />'
    )

    def __init__(self):
        self.screenshot_calls = 0

    def save_screenshot(self, path):
        self.screenshot_calls += 1
        with open(path, "wb") as stream:
            stream.write(b"png")
        return True


class BrokenDriver:
    @property
    def current_activity(self):
        raise RuntimeError("activity unavailable")

    @property
    def current_context(self):
        raise RuntimeError("context unavailable")

    @property
    def page_source(self):
        raise RuntimeError("source unavailable")

    def save_screenshot(self, path):
        raise RuntimeError("screenshot unavailable")


def test_capture_failure_writes_sanitized_artifacts(tmp_path):
    from commons.diagnostics import capture_failure

    artifacts = capture_failure(
        FakeDriver(), "open / checkout", artifacts_dir=tmp_path
    )

    assert artifacts.activity == ".MainActivity"
    assert artifacts.context == "NATIVE_APP"
    assert artifacts.screenshot and artifacts.screenshot.exists()
    assert artifacts.page_source and artifacts.page_source.exists()
    assert "open_checkout" in artifacts.screenshot.name
    xml = artifacts.page_source.read_text(encoding="utf-8")
    assert "secret" not in xml
    assert "09123456789" not in xml
    assert "123456" not in xml
    assert "<redacted>" in xml


def test_capture_failure_tolerates_unavailable_driver_evidence(tmp_path):
    from commons.diagnostics import capture_failure

    artifacts = capture_failure(BrokenDriver(), "broken", artifacts_dir=tmp_path)

    assert artifacts.activity == ""
    assert artifacts.context == ""
    assert artifacts.screenshot is None
    assert artifacts.page_source is None


def test_capture_failure_can_skip_screenshot_and_keep_sanitized_xml(tmp_path):
    from commons.diagnostics import capture_failure

    driver = FakeDriver()
    artifacts = capture_failure(
        driver,
        "sensitive_address",
        artifacts_dir=tmp_path,
        include_screenshot=False,
    )

    assert artifacts.screenshot is None
    assert driver.screenshot_calls == 0
    assert artifacts.page_source and artifacts.page_source.exists()
    xml = artifacts.page_source.read_text(encoding="utf-8")
    assert "secret" not in xml
    assert "09123456789" not in xml


def test_capture_failure_redacts_explicit_sensitive_values_from_xml(tmp_path):
    from commons.diagnostics import capture_failure

    driver = FakeDriver()
    driver.page_source = (
        '<node text="Tester residence Tester Manila 100 Test Street 1000" content-desc="+639621170994" />'
    )

    artifacts = capture_failure(
        driver,
        "sensitive_address",
        artifacts_dir=tmp_path,
        include_screenshot=False,
        redact_values=(
            "Tester residence",
            "Tester",
            "+639621170994",
            "菲律宾",
            "Manila",
            "100 Test Street",
            "1000",
        ),
    )

    xml = artifacts.page_source.read_text(encoding="utf-8")
    for value in (
        "Tester residence",
        "Tester",
        "+639621170994",
        "菲律宾",
        "Manila",
        "100 Test Street",
        "1000",
    ):
        assert value not in xml
    assert "<redacted>" in xml
