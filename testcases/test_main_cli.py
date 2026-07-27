import importlib
import sys

import pytest


pytestmark = pytest.mark.unit


def load_main_module():
    sys.modules.pop("scripts.main", None)
    return importlib.import_module("scripts.main")


def test_main_module_imports_without_testcase_runtime_dependencies():
    module = load_main_module()

    assert callable(module.main)


def test_smoke_mode_only_runs_smoke(monkeypatch):
    module = load_main_module()
    calls = []
    monkeypatch.setattr(module, "smoke_test", lambda: calls.append("smoke") or True)
    monkeypatch.setattr(
        module,
        "run_login_method",
        lambda method: calls.append(("login", method)) or True,
    )

    assert module.main(["--mode", "smoke"]) == 0
    assert calls == ["smoke"]


def test_login_mode_requires_explicit_method():
    module = load_main_module()

    assert module.main(["--mode", "login"]) == 2


def test_login_mode_dispatches_selected_method(monkeypatch):
    module = load_main_module()
    calls = []
    monkeypatch.setattr(
        module,
        "run_login_method",
        lambda method: calls.append(method) or True,
    )

    assert module.main(["--mode", "login", "--method", "wechat"]) == 0
    assert calls == ["wechat"]


def test_run_login_method_dispatches_injected_page_without_owning_session():
    from scripts.run_login import run_login_method

    calls = []

    class FakePage:
        def open_login_from_home(self):
            calls.append("open")
            return True

        def login_by_account_password(self):
            calls.append("password")
            return True

    assert run_login_method("password", page=FakePage()) is True
    assert calls == ["open", "password"]


def test_run_login_method_rejects_unknown_method():
    from scripts.run_login import run_login_method

    with pytest.raises(ValueError, match="unsupported login method"):
        run_login_method("unknown", page=object())
