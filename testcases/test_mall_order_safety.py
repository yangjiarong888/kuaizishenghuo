import pytest

import scripts.run_mall_order_flow as mall_cli
from flows.mall_order_types import AmountSnapshot, ProductSnapshot


pytestmark = pytest.mark.unit


def test_mall_safety_defaults_are_non_destructive():
    args = mall_cli.build_parser().parse_args([])

    assert args.flow == "buy_now"
    assert args.verify_navigation_only is False
    assert args.allow_cart_mutation is False
    assert args.add_to_cart_only is False
    assert args.allow_order_creation is False
    assert args.max_payable is None
    assert args.cancel_created_order is False
    assert args.allow_order_cancellation is False
    assert args.send_order_im is False
    assert args.allow_order_message is False


@pytest.mark.parametrize(
    "argv",
    [
        ["--flow", "cart"],
        ["--flow", "both"],
        ["--add-to-cart-only"],
        ["--run-cart-delete"],
        ["--cart-delete-prepare-item"],
    ],
)
def test_cart_mutation_requires_explicit_capability(argv):
    args = mall_cli.build_parser().parse_args(argv)

    with pytest.raises(ValueError, match="allow-cart-mutation"):
        mall_cli.validate_args(args)


@pytest.mark.parametrize(
    "argv",
    [
        ["--submit-order"],
        ["--submit-order", "--allow-order-creation"],
        [
            "--submit-order",
            "--allow-order-creation",
            "--max-payable",
            "0",
        ],
    ],
)
def test_submit_requires_order_capability_and_positive_limit(argv):
    args = mall_cli.build_parser().parse_args(argv)

    with pytest.raises(
        ValueError,
        match="max-payable|allow-order-creation",
    ):
        mall_cli.validate_args(args)


def test_add_only_rejects_submit_order():
    args = mall_cli.build_parser().parse_args(
        [
            "--add-to-cart-only",
            "--allow-cart-mutation",
            "--submit-order",
            "--allow-order-creation",
            "--max-payable",
            "20",
        ]
    )

    with pytest.raises(ValueError, match="add-to-cart-only"):
        mall_cli.validate_args(args)


def test_order_cancellation_requires_creation_and_its_own_capability():
    args = mall_cli.build_parser().parse_args(["--cancel-created-order"])

    with pytest.raises(ValueError, match="allow-order-cancellation"):
        mall_cli.validate_args(args)


def test_order_message_requires_submit_and_its_own_capability():
    args = mall_cli.build_parser().parse_args(["--send-order-im"])

    with pytest.raises(
        ValueError,
        match="submit-order|allow-order-message",
    ):
        mall_cli.validate_args(args)


@pytest.mark.parametrize(
    "extra",
    [
        ["--submit-order"],
        ["--allow-cart-mutation"],
        ["--allow-address-mutation"],
        ["--allow-order-creation"],
        ["--allow-order-cancellation"],
        ["--allow-order-message"],
        ["--add-to-cart-only"],
        ["--run-cart-delete"],
        ["--ensure-test-address"],
        ["--run-stockout"],
        ["--run-network-exception"],
        ["--send-order-im"],
    ],
)
def test_navigation_only_rejects_mutating_or_exception_modes(extra):
    args = mall_cli.build_parser().parse_args(
        ["--verify-navigation-only", *extra]
    )

    with pytest.raises(ValueError, match="navigation-only"):
        mall_cli.validate_args(args)


def test_invalid_cart_mode_returns_two_before_driver(monkeypatch):
    class ForbiddenManager:
        def __init__(self):
            raise AssertionError("Driver must not be created")

    monkeypatch.setattr(mall_cli, "DriverManager", ForbiddenManager)

    assert mall_cli.main(["--flow", "cart"]) == 2


def install_fake_driver_boundaries(monkeypatch, flow_class):
    class FakeManager:
        def get_driver(self, *, session_name):
            return object()

        def close_driver(self, *, session_name):
            raise AssertionError(
                "navigation test must not close the fake driver"
            )

    monkeypatch.setattr(mall_cli, "DriverManager", FakeManager)
    monkeypatch.setattr(mall_cli, "MallOrderFlow", flow_class)


def test_navigation_only_dispatches_no_mutating_flow(monkeypatch):
    events = []

    class FakeFlow:
        def __init__(self, driver, **kwargs):
            events.append(("init", kwargs["send_im_after_order"]))

        def run_navigation_verification(self, keyword):
            events.append(("navigation", keyword))
            return True

    install_fake_driver_boundaries(monkeypatch, FakeFlow)

    assert mall_cli.main(
        [
            "--verify-navigation-only",
            "--product-source",
            "search",
            "--keyword",
            "可乐",
        ]
    ) == 0
    assert events == [("init", False), ("navigation", "可乐")]


def test_add_only_dispatch_stops_before_checkout(monkeypatch):
    events = []

    class FakeFlow:
        def __init__(self, driver, **kwargs):
            events.append(("init", kwargs["send_im_after_order"]))

        def run_add_to_cart_only(self, keyword):
            events.append(("add-only", keyword))
            return True

    install_fake_driver_boundaries(monkeypatch, FakeFlow)

    assert mall_cli.main(
        [
            "--add-to-cart-only",
            "--allow-cart-mutation",
            "--product-source",
            "search",
            "--keyword",
            "可乐",
        ]
    ) == 0
    assert events == [("init", False), ("add-only", "可乐")]


def test_navigation_verification_reads_evidence_and_returns(monkeypatch):
    events = []
    page = object.__new__(mall_cli.MallOrderFlow)
    page.driver = object()
    page.open_detail_and_snapshot = lambda keyword: (
        events.append(("detail", keyword))
        or ProductSnapshot(
            name="可乐",
            specs=(),
            unit_price=10.0,
            quantity=1,
            sku="SKU-1",
        )
    )
    page.safe_back_to_mall = lambda: events.append(("back",))
    monkeypatch.setattr(
        mall_cli,
        "capture_failure",
        lambda driver, action: events.append(("evidence", action)),
        raising=False,
    )

    assert page.run_navigation_verification("可乐") is True
    assert events == [
        ("detail", "可乐"),
        ("evidence", "mall_navigation_verification"),
        ("back",),
    ]


@pytest.mark.parametrize("raise_during_detail", [False, True])
def test_navigation_verification_disables_mall_tab_coordinate_fallback_and_restores_it(
    monkeypatch, raise_during_detail
):
    """Strict navigation keeps the mall-tab fallback disabled during detail opening."""
    page = object.__new__(mall_cli.MallOrderFlow)
    page.driver = object()
    page._mall_tab_coordinate_fallback_disabled = False
    observed = []

    def open_detail_and_snapshot(keyword):
        observed.append((keyword, page._mall_tab_coordinate_fallback_disabled))
        if raise_during_detail:
            raise RuntimeError("detail opening failed")
        return ProductSnapshot(
            name="可乐",
            specs=(),
            unit_price=10.0,
            quantity=1,
            sku="SKU-1",
        )

    page.open_detail_and_snapshot = open_detail_and_snapshot
    page.safe_back_to_mall = lambda: None
    monkeypatch.setattr(mall_cli, "capture_failure", lambda *_args: None)

    if raise_during_detail:
        with pytest.raises(RuntimeError, match="detail opening failed"):
            page.run_navigation_verification("可乐")
    else:
        assert page.run_navigation_verification("可乐") is True

    assert observed == [("可乐", True)]
    assert page._mall_tab_coordinate_fallback_disabled is False


def test_payable_above_explicit_limit_stops_before_submit():
    events = []
    page = object.__new__(mall_cli.MallOrderFlow)
    page.max_payable = 20.0
    page.ensure_test_address = False
    page.send_im_after_order = False
    page.dismiss_checkout_upsell_if_visible = lambda: None
    page.assert_checkout_matches_detail = lambda product: AmountSnapshot(
        goods_total=20.01,
        coupon=0.0,
        freight=0.0,
        payable=20.01,
    )
    page.apply_mall_platform_coupon_if_needed = lambda: False
    page.apply_checkout_preferences = lambda: None
    page.read_amounts = lambda product: AmountSnapshot(
        goods_total=20.01,
        coupon=0.0,
        freight=0.0,
        payable=20.01,
    )
    page.pick_tomorrow_random_preorder_time_if_needed = lambda: None
    page.submit_order = lambda amounts: events.append("submit")
    product = ProductSnapshot(
        name="可乐",
        specs=(),
        unit_price=20.01,
        quantity=1,
        sku="SKU-1",
    )

    with pytest.raises(AssertionError, match="max-payable"):
        page.finish_checkout(product, submit_order=True)
    assert events == []


def test_search_goods_remains_bound_after_checkout_extraction():
    page = object.__new__(mall_cli.MallOrderFlow)

    assert page.search_goods("") is False
