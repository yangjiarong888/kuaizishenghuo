import subprocess
import sys
from pathlib import Path

from scripts import run_login


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_login_cli_parser_accepts_existing_method_and_credentials():
    args = run_login.build_parser().parse_args(
        [
            "--method",
            "PASSWORD",
            "--phone",
            "13800138000",
            "--password",
            "secret",
            "--no-from-home",
        ]
    )

    assert args.method == "password"
    assert args.phone == "13800138000"
    assert args.password == "secret"
    assert args.no_from_home is True


def test_login_cli_rejects_missing_password_before_page_creation(monkeypatch):
    monkeypatch.delenv("LOGIN_DEFAULT_PHONE", raising=False)
    monkeypatch.delenv("LOGIN_DEFAULT_PASSWORD", raising=False)
    created = []
    monkeypatch.setattr(run_login, "LoginPage", lambda **kwargs: created.append(kwargs))

    assert run_login.main(["--method", "password"]) == 2
    assert created == []


def test_login_cli_direct_help_runs_from_repository_root():
    result = subprocess.run(
        [sys.executable, "scripts/run_login.py", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "登录方式" in result.stdout
