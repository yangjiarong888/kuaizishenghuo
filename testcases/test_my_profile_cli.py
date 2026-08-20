import subprocess
import sys
from pathlib import Path

import pytest

from scripts import run_my_profile_navigation as script


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "flag",
    [
        "--include-privacy-reset",
        "--include-fingerprint-payment",
        "--include-payment-password-change",
        "--include-account-cancellation",
        "--include-login-password-change",
    ],
)
def test_cli_rejects_all_mutating_profile_flags(flag):
    with pytest.raises(SystemExit):
        script.build_parser().parse_args([flag])


def test_cli_closes_the_driver_session_it_creates(monkeypatch):
    events = []

    class FakeManager:
        def get_driver(self, session_name):
            events.append(("get", session_name))
            return object()

        def close_driver(self, session_name):
            events.append(("close", session_name))

    class FakePage:
        def __init__(self, driver):
            events.append(("page", driver))

        def run_navigation_smoke(self):
            return True

        def run_logged_out_navigation_smoke(self):
            raise AssertionError("wrong flow")

    monkeypatch.setattr(script, "DriverManager", FakeManager)
    monkeypatch.setattr(script, "MyProfilePage", FakePage)

    assert script.main(["--session", "profile-unit"]) == 0
    assert events[0] == ("get", "profile-unit")
    assert events[-1] == ("close", "profile-unit")


def test_cli_logged_out_uses_only_logged_out_smoke(monkeypatch):
    events = []

    class FakeManager:
        def get_driver(self, session_name):
            return object()

        def close_driver(self, session_name):
            events.append("closed")

    class FakePage:
        def __init__(self, driver):
            pass

        def run_navigation_smoke(self):
            raise AssertionError("wrong flow")

        def run_logged_out_navigation_smoke(self):
            events.append("logged-out")
            return True

    monkeypatch.setattr(script, "DriverManager", FakeManager)
    monkeypatch.setattr(script, "MyProfilePage", FakePage)

    assert script.main(["--logged-out"]) == 0
    assert events == ["logged-out", "closed"]


def test_direct_script_help_runs_from_repository_root():
    result = subprocess.run(
        [sys.executable, "scripts/run_my_profile_navigation.py", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "个人中心只读导航巡检" in result.stdout
