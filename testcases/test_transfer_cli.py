import sys
from pathlib import Path

import pytest
import commons.driver as driver_module
import pages.Home as home_module
import scripts.run_transfer_business as runner
from commons.driver import DriverManager
from pages.Home import ChopsticksTester
from scripts.run_transfer_business import build_parser, read_secrets


@pytest.fixture
def isolated_driver_manager():
    original_drivers = DriverManager._drivers
    DriverManager._drivers = {}
    try:
        yield DriverManager()
    finally:
        DriverManager._drivers.clear()
        DriverManager._drivers = original_drivers


def _driver_log_checkpoint():
    file_handler = next(
        handler
        for handler in driver_module.logger.handlers
        if hasattr(handler, "baseFilename")
    )
    file_handler.flush()
    path = Path(file_handler.baseFilename)
    return file_handler, path, path.stat().st_size


def _driver_log_since(checkpoint) -> str:
    file_handler, path, offset = checkpoint
    file_handler.flush()
    return path.read_bytes()[offset:].decode("utf-8")


def test_cli_defaults_do_not_submit_real_order():
    args = build_parser().parse_args([])
    assert args.action == "full"
    assert args.submit_order is False
    assert args.payment_method == "balance"


def test_driver_manager_create_failure_logs_type_without_secret(
    monkeypatch, caplog, capsys, isolated_driver_manager
):
    secret_value = "fake-sensitive-remote-create-message"
    checkpoint = _driver_log_checkpoint()

    def fail_remote(*args, **kwargs):
        raise RuntimeError(secret_value)

    monkeypatch.setattr(driver_module.webdriver, "Remote", fail_remote)

    with pytest.raises(RuntimeError, match=secret_value):
        isolated_driver_manager.get_driver(session_name="create-log-test")

    captured = capsys.readouterr()
    output = captured.out + captured.err + caplog.text + _driver_log_since(checkpoint)
    assert secret_value not in output
    assert "RuntimeError" in output


def test_driver_manager_close_failure_logs_type_without_secret(
    caplog, capsys, isolated_driver_manager
):
    secret_value = "fake-sensitive-driver-quit-message"
    checkpoint = _driver_log_checkpoint()

    class FailingDriver:
        def quit(self):
            raise RuntimeError(secret_value)

    isolated_driver_manager._drivers["close-log-test"] = FailingDriver()

    isolated_driver_manager.close_driver(session_name="close-log-test")

    captured = capsys.readouterr()
    output = captured.out + captured.err + caplog.text + _driver_log_since(checkpoint)
    assert secret_value not in output
    assert "RuntimeError" in output


def test_home_maps_runner_to_transfer_business():
    assert ChopsticksTester.GOLDEN_BUSINESS_MAP["同城跑腿"] == "transfer"


def test_home_runner_dispatch_only_checks_menu_round_trips(monkeypatch):
    calls = []

    class FakeTransferPage:
        def __init__(self, driver):
            calls.append(("page", driver))

        def verify_menu_round_trips(self):
            calls.append(("menus",))
            return True

        def run_order_flow(self, **kwargs):
            raise AssertionError("home runner dispatch must never run an order flow")

    tester = ChopsticksTester()
    tester.driver = "driver"
    monkeypatch.setattr(tester, "get_golden_zone_items", lambda: [object()])
    monkeypatch.setattr(
        tester,
        "click_golden_zone_item",
        lambda index, items: (True, "同城跑腿"),
    )
    monkeypatch.setattr(tester, "ensure_homepage", lambda: True)
    monkeypatch.setattr(home_module, "TransferPage", FakeTransferPage)
    monkeypatch.setattr(home_module.time, "sleep", lambda seconds: None)

    assert tester.test_golden_zone_enhanced() == [(0, "同城跑腿")]
    assert calls == [("page", "driver"), ("menus",)]


def test_read_secrets_only_uses_transfer_environment(monkeypatch):
    monkeypatch.setenv("TRANSFER_MAYA_ACCOUNT", "maya-account-from-env")
    monkeypatch.setenv("TRANSFER_MAYA_PASSWORD", "maya-password-from-env")
    monkeypatch.setenv("TRANSFER_PAY_PASSWORD", "pay-password-from-env")

    assert read_secrets() == {
        "maya_account": "maya-account-from-env",
        "maya_password": "maya-password-from-env",
        "pay_password": "pay-password-from-env",
    }


def test_menus_action_only_runs_menu_round_trips(monkeypatch):
    calls = []

    class FakeDriverManager:
        def get_driver(self, *, session_name):
            calls.append(("get_driver", session_name))
            return object()

    class FakeTransferPage:
        def __init__(self, driver):
            calls.append(("page", driver))

        def verify_menu_round_trips(self):
            calls.append(("menus",))
            return True

        def run_order_flow(self, **kwargs):
            calls.append(("order", kwargs))
            return True

    monkeypatch.setattr(runner, "DriverManager", FakeDriverManager, raising=False)
    monkeypatch.setattr(runner, "TransferPage", FakeTransferPage, raising=False)
    monkeypatch.setattr(sys, "argv", ["run_transfer_business.py", "--action", "menus"])

    assert runner.main() == 0
    assert [call[0] for call in calls] == ["get_driver", "page", "menus"]


def test_order_action_reuses_order_flow_with_safe_defaults(monkeypatch):
    captured = {}

    class FakeDriverManager:
        def get_driver(self, *, session_name):
            captured["session"] = session_name
            return object()

    class FakeTransferPage:
        def __init__(self, driver):
            captured["driver"] = driver

        def verify_menu_round_trips(self):
            raise AssertionError("order action must not run menu checks")

        def run_order_flow(self, **kwargs):
            captured["order_kwargs"] = kwargs
            return True

    monkeypatch.setenv("TRANSFER_MAYA_ACCOUNT", "maya-account-from-env")
    monkeypatch.setenv("TRANSFER_MAYA_PASSWORD", "maya-password-from-env")
    monkeypatch.setenv("TRANSFER_PAY_PASSWORD", "pay-password-from-env")
    monkeypatch.setattr(runner, "DriverManager", FakeDriverManager)
    monkeypatch.setattr(runner, "TransferPage", FakeTransferPage)
    monkeypatch.setattr(sys, "argv", ["run_transfer_business.py", "--action", "order"])

    assert runner.main() == 0
    assert captured["session"] == "transfer_business"
    assert captured["order_kwargs"] == {
        "submit_order": False,
        "payment_method": "balance",
        "exercise_maya_return": False,
        "maya_account": "maya-account-from-env",
        "maya_password": "maya-password-from-env",
        "pay_password": "pay-password-from-env",
    }


def test_full_action_runs_menus_then_order_and_can_close_driver(monkeypatch):
    calls = []

    class FakeDriverManager:
        def get_driver(self, *, session_name):
            calls.append(("get_driver", session_name))
            return "driver"

        def close_driver(self, *, session_name):
            calls.append(("close_driver", session_name))

    class FakeTransferPage:
        def __init__(self, driver):
            calls.append(("page", driver))

        def verify_menu_round_trips(self):
            calls.append(("menus",))
            return True

        def run_order_flow(self, **kwargs):
            calls.append(("order", kwargs))
            return True

    monkeypatch.setenv("TRANSFER_MAYA_ACCOUNT", "maya-account-from-env")
    monkeypatch.setenv("TRANSFER_MAYA_PASSWORD", "maya-password-from-env")
    monkeypatch.setenv("TRANSFER_PAY_PASSWORD", "pay-password-from-env")
    monkeypatch.setattr(runner, "DriverManager", FakeDriverManager)
    monkeypatch.setattr(runner, "TransferPage", FakeTransferPage)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_transfer_business.py",
            "--submit-order",
            "--payment-method",
            "maya",
            "--exercise-maya-return",
            "--session",
            "transfer-test",
            "--quit-driver",
        ],
    )

    assert runner.main() == 0
    assert calls == [
        ("get_driver", "transfer-test"),
        ("page", "driver"),
        ("menus",),
        (
            "order",
            {
                "submit_order": True,
                "payment_method": "maya",
                "exercise_maya_return": True,
                "maya_account": "maya-account-from-env",
                "maya_password": "maya-password-from-env",
                "pay_password": "pay-password-from-env",
            },
        ),
        ("close_driver", "transfer-test"),
    ]


def test_main_returns_one_without_logging_secret_values_on_flow_error(
    monkeypatch, caplog
):
    secret_value = "unique-secret-from-environment"

    class FakeDriverManager:
        def get_driver(self, *, session_name):
            return object()

    class FakeTransferPage:
        def __init__(self, driver):
            pass

        def run_order_flow(self, **kwargs):
            raise ValueError(secret_value)

    monkeypatch.setenv("TRANSFER_PAY_PASSWORD", secret_value)
    monkeypatch.setattr(runner, "DriverManager", FakeDriverManager)
    monkeypatch.setattr(runner, "TransferPage", FakeTransferPage)
    monkeypatch.setattr(sys, "argv", ["run_transfer_business.py", "--action", "order"])

    assert runner.main() == 1
    assert secret_value not in caplog.text


def test_driver_initialization_error_returns_one_without_leaking_secrets(
    monkeypatch, caplog, capsys
):
    init_secret = "fake-sensitive-driver-init-message"
    close_secret = "fake-sensitive-driver-close-message"
    calls = []

    class FakeDriverManager:
        def get_driver(self, *, session_name):
            calls.append(("get_driver", session_name))
            raise RuntimeError(init_secret)

        def close_driver(self, *, session_name):
            calls.append(("close_driver", session_name))
            raise RuntimeError(close_secret)

    monkeypatch.setattr(runner, "DriverManager", FakeDriverManager)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_transfer_business.py",
            "--action",
            "menus",
            "--session",
            "driver-init-test",
            "--quit-driver",
        ],
    )

    assert runner.main() == 1
    captured = capsys.readouterr()
    output = captured.out + captured.err + caplog.text
    assert init_secret not in output
    assert close_secret not in output
    assert calls == [
        ("get_driver", "driver-init-test"),
        ("close_driver", "driver-init-test"),
    ]
