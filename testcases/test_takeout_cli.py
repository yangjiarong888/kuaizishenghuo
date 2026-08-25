from __future__ import annotations

import pytest

from scripts import run_takeout_wangwang as script
from pages import takeout_address


ADDRESS_ENV = {
    "TAKEOUT_ADDRESS_CONTACT": "Automation Contact",
    "TAKEOUT_ADDRESS_PHONE": "09171234567",
    "TAKEOUT_ADDRESS_SEARCH": "Robinsons Place Manila",
    "TAKEOUT_ADDRESS_DETAIL": "Unit 8 test address",
}


def test_takeout_defaults_are_non_submitting() -> None:
    args = script.build_parser().parse_args([])

    assert args.checkout is False
    assert args.submit_order is False


def test_takeout_address_policy_defaults_to_existing() -> None:
    args = script.build_parser().parse_args([])

    assert args.address_policy == "existing"


def test_takeout_add_policy_rejects_missing_address_data_before_driver(
    monkeypatch,
    tmp_path,
) -> None:
    for key in ADDRESS_ENV:
        monkeypatch.delenv(key, raising=False)

    class ForbiddenManager:
        def __init__(self) -> None:
            raise AssertionError("DriverManager must not be created")

    monkeypatch.setattr(script, "DriverManager", ForbiddenManager)
    monkeypatch.setattr(script, "ROOT", tmp_path)

    assert script.main(["--checkout", "--address-policy", "add"]) == 2


def test_takeout_auto_policy_accepts_complete_environment() -> None:
    args = script.build_parser().parse_args(
        ["--checkout", "--address-policy", "auto"]
    )

    script.validate_args(args, environ=ADDRESS_ENV)


def test_takeout_real_submit_with_auto_address_does_not_require_existing_ordinal() -> None:
    args = script.build_parser().parse_args(
        [
            "--checkout",
            "--submit-order",
            "--max-payable",
            "500",
            "--address-policy",
            "auto",
            "--delivery-time-slot-ordinal",
            "1",
        ]
    )

    script.validate_args(args, environ=ADDRESS_ENV)


def test_takeout_address_data_can_be_loaded_from_local_dotenv(tmp_path) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "\n".join(f'{key}="{value}"' for key, value in ADDRESS_ENV.items()),
        encoding="utf-8",
    )

    loaded = takeout_address.load_takeout_address_environment({}, dotenv_path=dotenv)

    assert loaded == ADDRESS_ENV


def test_process_environment_overrides_local_dotenv(tmp_path) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "TAKEOUT_ADDRESS_CONTACT=File Contact\n",
        encoding="utf-8",
    )

    loaded = takeout_address.load_takeout_address_environment(
        {"TAKEOUT_ADDRESS_CONTACT": "Process Contact"},
        dotenv_path=dotenv,
    )

    assert loaded["TAKEOUT_ADDRESS_CONTACT"] == "Process Contact"


def test_shared_business_address_search_overrides_business_specific_values() -> None:
    environ = {
        "BUSINESS_ADDRESS_SEARCH": "Unified Address",
        "TAKEOUT_ADDRESS_SEARCH": "Old Takeout Address",
        "MALL_TEST_ADDRESS_QUERY": "Old Mall Address",
    }

    assert (
        takeout_address.resolve_business_address_search(
            environ, "TAKEOUT_ADDRESS_SEARCH"
        )
        == "Unified Address"
    )
    assert (
        takeout_address.resolve_business_address_search(
            environ, "MALL_TEST_ADDRESS_QUERY"
        )
        == "Unified Address"
    )


def test_shared_business_contact_overrides_takeout_specific_contact() -> None:
    data = takeout_address.load_takeout_address_data(
        {
            "BUSINESS_ADDRESS_CONTACT": "test",
            "TAKEOUT_ADDRESS_CONTACT": "Old Contact",
        }
    )

    assert data.contact == "test"


def test_takeout_cli_rejects_legacy_password_argument() -> None:
    parser = script.build_parser()

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--password", "do-not-accept-secrets"])

    assert exc_info.value.code == 2


def test_submit_order_requires_checkout() -> None:
    args = script.build_parser().parse_args(["--submit-order"])

    with pytest.raises(ValueError, match="--checkout"):
        script.validate_args(args)


def test_checkout_and_submit_order_is_an_explicit_valid_combination() -> None:
    args = script.build_parser().parse_args(
        [
            "--checkout",
            "--submit-order",
            "--max-payable",
            "500",
            "--address-ordinal",
            "1",
            "--delivery-time-slot-ordinal",
            "1",
        ]
    )

    script.validate_args(args)


def test_takeout_submit_requires_an_explicit_address_ordinal() -> None:
    args = script.build_parser().parse_args(
        [
            "--checkout",
            "--submit-order",
            "--max-payable",
            "500",
            "--delivery-time-slot-ordinal",
            "1",
        ]
    )

    with pytest.raises(ValueError, match="address-ordinal"):
        script.validate_args(args)


def test_takeout_rejects_non_positive_address_ordinal() -> None:
    args = script.build_parser().parse_args(
        [
            "--checkout",
            "--address-ordinal",
            "0",
        ]
    )

    with pytest.raises(ValueError, match="address-ordinal"):
        script.validate_args(args)


def test_takeout_submit_requires_an_explicit_delivery_slot() -> None:
    args = script.build_parser().parse_args(
        [
            "--checkout",
            "--submit-order",
            "--max-payable",
            "500",
            "--address-ordinal",
            "1",
        ]
    )

    with pytest.raises(ValueError, match="delivery"):
        script.validate_args(args)


def test_takeout_rejects_non_positive_delivery_ordinal() -> None:
    args = script.build_parser().parse_args(
        ["--checkout", "--delivery-time-slot-ordinal", "0"]
    )

    with pytest.raises(ValueError, match="delivery-time-slot-ordinal"):
        script.validate_args(args)


def test_takeout_keeps_the_explicit_default_free_text_remark() -> None:
    args = script.build_parser().parse_args([])

    assert args.remark_text == "test order"
    assert args.merchant_remark == ""


def test_takeout_submit_requires_positive_max_payable(monkeypatch):
    monkeypatch.setattr(
        script.DriverManager,
        "get_driver",
        lambda *a, **k: pytest.fail("driver"),
    )
    assert script.main(["--checkout", "--submit-order"]) == 2


def test_takeout_rounding_requires_cod(monkeypatch):
    monkeypatch.setattr(
        script.DriverManager,
        "get_driver",
        lambda *a, **k: pytest.fail("driver"),
    )
    assert script.main(["--checkout", "--rounding-payment", "--checkout-payment", "balance"]) == 2


@pytest.mark.parametrize("value", ["nan", "inf", "-inf", "0", "-1"])
def test_takeout_max_payable_must_be_finite_and_positive_before_driver(
    monkeypatch, value
) -> None:
    monkeypatch.setattr(
        script.DriverManager,
        "get_driver",
        lambda *a, **k: pytest.fail("driver"),
    )

    assert script.main([f"--max-payable={value}"]) == 2


@pytest.mark.parametrize("value", ["nan", "inf", "-inf"])
def test_takeout_rounding_amount_must_be_finite_before_driver(
    monkeypatch, value
) -> None:
    monkeypatch.setattr(
        script.DriverManager,
        "get_driver",
        lambda *a, **k: pytest.fail("driver"),
    )

    assert script.main(
        [
            "--checkout",
            "--checkout-payment",
            "cod",
            "--rounding-payment",
            f"--rounding-amount={value}",
        ]
    ) == 2


def test_takeout_rounding_amount_requires_rounding_payment(monkeypatch) -> None:
    monkeypatch.setattr(
        script.DriverManager,
        "get_driver",
        lambda *a, **k: pytest.fail("driver"),
    )

    assert script.main(["--rounding-amount", "500"]) == 2


def test_invalid_submit_combination_returns_two_before_driver_creation(
    monkeypatch,
) -> None:
    class ForbiddenManager:
        def __init__(self) -> None:
            raise AssertionError("DriverManager must not be created")

    monkeypatch.setattr(script, "DriverManager", ForbiddenManager)

    assert script.main(["--submit-order"]) == 2


@pytest.mark.parametrize(
    ("argv", "expected_submit_order"),
    [
        (["--checkout"], False),
        (["--checkout", "--submit-order", "--max-payable", "500"], True),
    ],
)
def test_checkout_passes_explicit_submit_intent_to_page_flow(
    monkeypatch,
    argv,
    expected_submit_order,
) -> None:
    received_submit_intents = []
    fake_driver = object()

    class FakeManager:
        def __init__(self):
            self.closed = []

        def get_driver(self, *, session_name, **kwargs):
            assert session_name == "takeout_wangwang"
            assert kwargs == {
                "unicode_keyboard": False,
                "reset_keyboard": False,
            }
            return fake_driver

        def close_driver(self, *, session_name):
            self.closed.append(session_name)

    class FakeTakeoutPage:
        def __init__(self, driver):
            assert driver is fake_driver

        def run_shop_checkout_pay_and_cancel_flow(self, **kwargs):
            received_submit_intents.append(kwargs.get("submit_order"))
            return True

    monkeypatch.setattr(script, "DriverManager", FakeManager)
    monkeypatch.setattr(script, "TakeoutPageBase", FakeTakeoutPage)
    monkeypatch.setattr(
        script,
        "open_wangwang_supermarket_from_takeout_home",
        lambda *args, **kwargs: True,
    )

    if expected_submit_order:
        argv.extend(
            [
                "--address-ordinal",
                "1",
                "--delivery-time-slot-ordinal",
                "1",
            ]
        )
    assert script.main(argv) == 0
    assert received_submit_intents == [expected_submit_order]


def test_checkout_passes_rounding_and_cap_to_page_flow(monkeypatch) -> None:
    received_kwargs = []
    fake_driver = object()

    class FakeManager:
        def __init__(self):
            self.closed = []

        def get_driver(self, *, session_name, **kwargs):
            assert kwargs == {
                "unicode_keyboard": False,
                "reset_keyboard": False,
            }
            return fake_driver

        def close_driver(self, *, session_name):
            self.closed.append(session_name)

    class FakeTakeoutPage:
        def __init__(self, driver):
            assert driver is fake_driver

        def run_shop_checkout_pay_and_cancel_flow(self, **kwargs):
            received_kwargs.append(kwargs)
            return True

    monkeypatch.setattr(script, "DriverManager", FakeManager)
    monkeypatch.setattr(script, "TakeoutPageBase", FakeTakeoutPage)
    monkeypatch.setattr(
        script,
        "open_wangwang_supermarket_from_takeout_home",
        lambda *args, **kwargs: True,
    )

    assert script.main(
        [
            "--checkout",
            "--checkout-payment",
            "cod",
            "--rounding-payment",
            "--rounding-amount",
            "500",
            "--max-payable",
            "500",
        ]
    ) == 0
    assert received_kwargs[0]["rounding_payment"] is True
    assert received_kwargs[0]["rounding_amount"] == 500.0
    assert received_kwargs[0]["max_payable"] == 500.0


def test_takeout_main_always_closes_driver_after_flow_failure(monkeypatch) -> None:
    calls = []
    fake_driver = object()

    class FakeManager:
        def get_driver(self, *, session_name, **kwargs):
            calls.append(("get", session_name))
            assert kwargs == {
                "unicode_keyboard": False,
                "reset_keyboard": False,
            }
            return fake_driver

        def close_driver(self, *, session_name):
            calls.append(("close", session_name))

    class FailingPage:
        def __init__(self, driver):
            assert driver is fake_driver

        def run_shop_checkout_pay_and_cancel_flow(self, **kwargs):
            raise AssertionError("checkout failed")

    monkeypatch.setattr(script, "DriverManager", FakeManager)
    monkeypatch.setattr(script, "TakeoutPageBase", FailingPage)
    monkeypatch.setattr(
        script,
        "open_wangwang_supermarket_from_takeout_home",
        lambda *args, **kwargs: True,
    )

    assert script.main(["--checkout"]) == 1
    assert calls[-1] == ("close", "takeout_wangwang")


def test_takeout_driver_never_switches_to_appium_unicode_keyboard(monkeypatch) -> None:
    received = []
    fake_driver = object()

    class FakeManager:
        def get_driver(
            self,
            *,
            session_name,
            unicode_keyboard,
            reset_keyboard,
        ):
            received.append(
                (session_name, unicode_keyboard, reset_keyboard)
            )
            return fake_driver

        def close_driver(self, *, session_name):
            pass

    monkeypatch.setattr(script, "DriverManager", FakeManager)
    monkeypatch.setattr(
        script,
        "open_wangwang_supermarket_from_takeout_home",
        lambda *args, **kwargs: True,
    )

    assert script.main([]) == 0
    assert received == [("takeout_wangwang", False, False)]
