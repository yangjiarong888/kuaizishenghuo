import pytest

import scripts.run_mall_order_flow as mall_cli


pytestmark = pytest.mark.unit


def test_mall_cli_defaults_are_non_mutating_and_have_no_personal_data():
    args = mall_cli.build_parser().parse_args([])

    assert args.submit_order is False
    assert args.ensure_test_address is False
    assert args.force_add_test_address is False
    assert args.edit_test_address is False
    assert args.copy_test_address is False
    assert args.add_test_address_only is False
    assert args.address_query == ""
    assert args.address_name == ""
    assert args.address_phone == ""
    assert args.address_wechat == ""
    assert args.address_detail == ""
    assert args.allow_address_mutation is False


@pytest.mark.parametrize(
    "flag",
    (
        "--ensure-test-address",
        "--force-add-test-address",
        "--edit-test-address",
        "--copy-test-address",
        "--add-test-address-only",
    ),
)
def test_address_mutation_flags_require_explicit_capability(flag):
    args = mall_cli.build_parser().parse_args([flag])

    with pytest.raises(ValueError, match="allow-address-mutation"):
        mall_cli.validate_args(args)


def test_address_mutation_capability_allows_explicit_action():
    args = mall_cli.build_parser().parse_args(
        ["--add-test-address-only", "--allow-address-mutation"]
    )

    mall_cli.validate_args(args)


def test_main_rejects_unsafe_address_action_before_driver_creation(monkeypatch):
    class UnexpectedDriverManager:
        def get_driver(self, **kwargs):
            raise AssertionError("driver must not be created for invalid args")

    monkeypatch.setattr(mall_cli, "DriverManager", UnexpectedDriverManager)

    assert mall_cli.main(["--add-test-address-only"]) == 2


@pytest.mark.parametrize(
    "argv",
    [
        ["--rounding-amount", "500"],
        ["--rounding-payment", "--payment-method", "wechat_mock"],
    ],
)
def test_rounding_invalid_combinations_return_two_before_driver(argv, monkeypatch):
    monkeypatch.setattr(
        mall_cli.DriverManager,
        "get_driver",
        lambda *args, **kwargs: pytest.fail("driver must not be created"),
    )

    assert mall_cli.main(argv) == 2
