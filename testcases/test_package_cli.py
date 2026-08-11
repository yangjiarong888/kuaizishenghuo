import logging

import pytest

import package

from pages.shipping_types import AddressPolicy, PaymentMethod


@pytest.fixture(autouse=True)
def capture_package_logs(caplog):
    """Expose the CLI logger to caplog without changing production logging."""
    original_propagate = package.logger.propagate
    package.logger.propagate = True
    caplog.set_level(logging.INFO, logger=package.logger.name)
    try:
        yield
    finally:
        package.logger.propagate = original_propagate


def complete_env(**overrides):
    environ = {
        "SHIPPING_PAY_PASSWORD": "test-password",
        "SHIPPING_ADDRESS_MATCH": "Test Recipient",
        "SHIPPING_ADDRESS_NAME": "Test Recipient",
        "SHIPPING_ADDRESS_PHONE": "+639621170994",
        "SHIPPING_ADDRESS_COUNTRY": "Philippines",
        "SHIPPING_ADDRESS_CITY": "Manila",
        "SHIPPING_ADDRESS_DETAIL": "Unit 1",
        "SHIPPING_ADDRESS_POSTCODE": "1000",
    }
    environ.update(overrides)
    return environ


def test_cli_defaults_to_balance_and_auto_address():
    args = package.build_parser().parse_args([])

    assert args.payment_method == "balance"
    assert args.address_policy == "auto"
    assert args.cancel_unpaid is False


def test_cod_rejects_cancel_unpaid_before_driver_creation(monkeypatch):
    created = []
    monkeypatch.setattr(package, "DriverManager", lambda: created.append(True))

    code = package.main(
        ["--payment-method", "cod", "--cancel-unpaid"],
        environ={},
    )

    assert code == 2
    assert created == []


@pytest.mark.parametrize(
    ("argv", "environ", "error"),
    (
        (["--payment-method", "balance"], {}, "SHIPPING_PAY_PASSWORD"),
        (
            ["--address-policy", "existing"],
            {"SHIPPING_PAY_PASSWORD": "secret"},
            "SHIPPING_ADDRESS_MATCH",
        ),
        (
            ["--address-policy", "add"],
            {"SHIPPING_PAY_PASSWORD": "secret"},
            "新增地址缺少字段",
        ),
        (
            ["--address-policy", "auto"],
            {"SHIPPING_PAY_PASSWORD": "secret"},
            "新增地址缺少字段",
        ),
    ),
)
def test_preflight_failure_never_creates_driver(monkeypatch, argv, environ, error, caplog):
    created = []
    monkeypatch.setattr(package, "DriverManager", lambda: created.append(True))

    assert package.main(argv, environ=environ) == 2
    assert created == []
    assert error in caplog.text


@pytest.mark.parametrize(
    ("argv", "environ", "expected_method", "expected_policy", "expected_cancel"),
    (
        (
            ["--address-policy", "existing"],
            complete_env(
                SHIPPING_ADDRESS_NAME="",
                SHIPPING_ADDRESS_PHONE="",
                SHIPPING_ADDRESS_COUNTRY="",
                SHIPPING_ADDRESS_CITY="",
                SHIPPING_ADDRESS_DETAIL="",
                SHIPPING_ADDRESS_POSTCODE="",
            ),
            PaymentMethod.BALANCE,
            AddressPolicy.EXISTING,
            False,
        ),
        (
            ["--payment-method", "cod", "--address-policy", "add", "--quit-driver"],
            complete_env(SHIPPING_PAY_PASSWORD="", SHIPPING_ADDRESS_MATCH=""),
            PaymentMethod.COD,
            AddressPolicy.ADD,
            False,
        ),
        (
            ["--cancel-unpaid", "--address-policy", "auto"],
            complete_env(SHIPPING_PAY_PASSWORD="", SHIPPING_ADDRESS_MATCH=""),
            PaymentMethod.BALANCE,
            AddressPolicy.AUTO,
            True,
        ),
    ),
)
def test_main_runs_one_flow_with_validated_policy(
    monkeypatch,
    argv,
    environ,
    expected_method,
    expected_policy,
    expected_cancel,
):
    calls = []
    fake_driver = object()

    class FakeManager:
        def get_driver(self, *, session_name):
            calls.append(("get_driver", session_name))
            return fake_driver

        def close_driver(self, *, session_name):
            calls.append(("close_driver", session_name))

    class FakeShippingPage:
        def __init__(self, driver):
            assert driver is fake_driver

        def run_order_flow(self, **kwargs):
            calls.append(("run_order_flow", kwargs))
            return True

    monkeypatch.setattr(package, "DriverManager", FakeManager)
    monkeypatch.setattr(package, "ShippingPage", FakeShippingPage)

    assert package.main(argv, environ=environ) == 0
    assert calls[0] == ("get_driver", "shipping_business")
    assert calls[1][0] == "run_order_flow"
    assert calls[1][1]["payment_method"] is expected_method
    assert calls[1][1]["address_policy"] is expected_policy
    assert calls[1][1]["cancel_unpaid"] is expected_cancel
    received_address = calls[1][1]["address_data"]
    if expected_policy is AddressPolicy.EXISTING:
        assert received_address.match == "Test Recipient"
    else:
        assert received_address.missing_for_add() == ()
    if "--quit-driver" in argv:
        assert calls[-1] == ("close_driver", "shipping_business")
    else:
        assert all(call[0] != "close_driver" for call in calls)


def test_cli_logs_never_contain_password_or_full_address(monkeypatch, caplog):
    env = complete_env(
        SHIPPING_PAY_PASSWORD="987654",
        SHIPPING_ADDRESS_DETAIL="Private Unit 123",
    )

    class FakeManager:
        def get_driver(self, *, session_name):
            return object()

    class FakeShippingPage:
        def __init__(self, driver):
            pass

        def run_order_flow(self, **kwargs):
            return True

    monkeypatch.setattr(package, "DriverManager", FakeManager)
    monkeypatch.setattr(package, "ShippingPage", FakeShippingPage)

    assert package.main([], environ=env) == 0
    assert "987654" not in caplog.text
    assert "Private Unit 123" not in caplog.text
