from xml.etree import ElementTree

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
    assert "[REDACTED]" in xml


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
    assert "[REDACTED]" in xml


def test_sanitize_xml_redacts_credential_attribute_name_variants():
    from commons.diagnostics import sanitize_xml

    source = (
        '<hierarchy><node data-token="RAW_TOKEN" '
        'user_password="RAW_PASSWORD" '
        'verification-code="RAW_CODE" '
        'pay-password="RAW_PAY_PASSWORD" /></hierarchy>'
    )

    sanitized = sanitize_xml(source)
    root = ElementTree.fromstring(sanitized)
    attributes = next(root.iter("node")).attrib

    assert attributes == {
        "data-token": "[REDACTED]",
        "user_password": "[REDACTED]",
        "verification-code": "[REDACTED]",
        "pay-password": "[REDACTED]",
    }
    for secret in ("RAW_TOKEN", "RAW_PASSWORD", "RAW_CODE", "RAW_PAY_PASSWORD"):
        assert secret not in sanitized


def test_capture_failure_redacts_mixed_xml_entity_encodings_without_corrupting_xml(
    tmp_path,
):
    from commons.diagnostics import capture_failure

    driver = FakeDriver()
    name = 'A&B<Name>"Quoted"\'Single\''
    detail = 'Unit & <One> "Two"\'Three\''
    match = 'Find & <Match> "Four"\'Five\''
    password = 'pw&<>"\''
    driver.page_source = (
        '<hierarchy><node '
        'text="A&amp;B&lt;Name&gt;&quot;Quoted&quot;&apos;Single&apos;" '
        'content-desc="Unit &#38; &#60;One&#62; &#34;Two&#34;&#39;Three&#39;" '
        'hint="Find &#x26; &#x3c;Match&#x3e; &#x22;Four&#x22;&#x27;Five&#x27;" '
        'password="pw&amp;&lt;&gt;&quot;&apos;" /></hierarchy>'
    )

    artifacts = capture_failure(
        driver,
        "encoded_pii",
        artifacts_dir=tmp_path,
        include_screenshot=False,
        redact_values=(name, detail, match, password),
    )

    xml = artifacts.page_source.read_text(encoding="utf-8")
    ElementTree.fromstring(xml)
    for fragment in (
        "A&amp;B",
        "Unit &#38;",
        "Find &#x26;",
        "pw&amp;",
        "Quoted",
        "Three",
        "Five",
    ):
        assert fragment not in xml
    assert xml.count("[REDACTED]") >= 4


def test_short_explicit_values_redact_only_xml_attribute_and_text_content(tmp_path):
    from commons.diagnostics import capture_failure

    driver = FakeDriver()
    driver.page_source = (
        '<hierarchy A="public"><node node="node" text="A">'
        'A node<child content-desc="node">A</child>'
        '</node></hierarchy>'
    )

    artifacts = capture_failure(
        driver,
        "short_pii",
        artifacts_dir=tmp_path,
        include_screenshot=False,
        redact_values=("A", "node"),
    )

    xml = artifacts.page_source.read_text(encoding="utf-8")
    root = ElementTree.fromstring(xml)
    node = root.find("node")
    child = node.find("child")
    assert root.tag == "hierarchy"
    assert root.attrib["A"] == "public"
    assert node.tag == "node"
    assert set(node.attrib) == {"node", "text"}
    assert node.attrib["node"] == "[REDACTED]"
    assert node.attrib["text"] == "[REDACTED]"
    assert node.text == "[REDACTED] [REDACTED]"
    assert child.attrib["content-desc"] == "[REDACTED]"
    assert child.text == "[REDACTED]"


def test_explicit_value_with_encoded_characters_is_redacted_from_attributes_and_text(
    tmp_path,
):
    from commons.diagnostics import capture_failure

    driver = FakeDriver()
    secret = 'A&B<Node>"Q"\'S\''
    driver.page_source = (
        '<hierarchy><node '
        'text="A&amp;B&lt;Node&gt;&quot;Q&quot;&apos;S&apos;">'
        'A&#38;B&#60;Node&#62;&#34;Q&#34;&#39;S&#39;'
        '</node></hierarchy>'
    )

    artifacts = capture_failure(
        driver,
        "encoded_attribute_and_text",
        artifacts_dir=tmp_path,
        include_screenshot=False,
        redact_values=(secret,),
    )

    xml = artifacts.page_source.read_text(encoding="utf-8")
    root = ElementTree.fromstring(xml)
    node = root.find("node")
    assert node.attrib["text"] == "[REDACTED]"
    assert node.text == "[REDACTED]"


def test_malformed_xml_uses_parseable_nonleaking_diagnostic_fallback(tmp_path):
    from commons.diagnostics import capture_failure

    driver = FakeDriver()
    driver.page_source = '<hierarchy><node text="PRIVATE-1234">Tester & broken'

    artifacts = capture_failure(
        driver,
        "malformed_sensitive_xml",
        artifacts_dir=tmp_path,
        include_screenshot=False,
        redact_values=("PRIVATE-1234", "Tester"),
    )

    xml = artifacts.page_source.read_text(encoding="utf-8")
    root = ElementTree.fromstring(xml)
    assert root.tag == "hierarchy"
    assert root.attrib == {
        "redaction": "fallback",
        "reason": "malformed_source",
    }
    assert "PRIVATE-1234" not in xml
    assert "Tester" not in xml
