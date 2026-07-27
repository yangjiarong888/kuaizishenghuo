from __future__ import annotations

import pytest

from scripts import run_takeout_wangwang as takeout_cli


def test_takeout_defaults_are_non_submitting() -> None:
    args = takeout_cli.build_parser().parse_args([])

    assert args.checkout is False
    assert args.submit_order is False


def test_takeout_cli_rejects_legacy_password_argument() -> None:
    parser = takeout_cli.build_parser()

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--password", "do-not-accept-secrets"])

    assert exc_info.value.code == 2


def test_submit_order_requires_checkout() -> None:
    args = takeout_cli.build_parser().parse_args(["--submit-order"])

    with pytest.raises(ValueError, match="--checkout"):
        takeout_cli.validate_args(args)


def test_checkout_and_submit_order_is_an_explicit_valid_combination() -> None:
    args = takeout_cli.build_parser().parse_args(["--checkout", "--submit-order"])

    takeout_cli.validate_args(args)


def test_invalid_submit_combination_returns_two_before_driver_creation(
    monkeypatch,
) -> None:
    class ForbiddenManager:
        def __init__(self) -> None:
            raise AssertionError("DriverManager must not be created")

    monkeypatch.setattr(takeout_cli, "DriverManager", ForbiddenManager)

    assert takeout_cli.main(["--submit-order"]) == 2


@pytest.mark.parametrize(
    ("argv", "expected_submit_order"),
    [
        (["--checkout"], False),
        (["--checkout", "--submit-order"], True),
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
        def get_driver(self, *, session_name):
            assert session_name == "takeout_wangwang"
            return fake_driver

    class FakeTakeoutPage:
        def __init__(self, driver):
            assert driver is fake_driver

        def run_shop_checkout_pay_and_cancel_flow(self, **kwargs):
            received_submit_intents.append(kwargs.get("submit_order"))
            return True

    monkeypatch.setattr(takeout_cli, "DriverManager", FakeManager)
    monkeypatch.setattr(takeout_cli, "TakeoutPageBase", FakeTakeoutPage)
    monkeypatch.setattr(
        takeout_cli,
        "open_wangwang_supermarket_from_takeout_home",
        lambda *args, **kwargs: True,
    )

    assert takeout_cli.main(argv) == 0
    assert received_submit_intents == [expected_submit_order]
