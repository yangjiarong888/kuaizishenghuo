#!/usr/bin/env python3
"""Run one prevalidated international-shipping order flow."""

from __future__ import annotations

import argparse
import os
from typing import Mapping, Sequence

from commons.driver import DriverManager
from commons.logger import setup_logger
from pages.shipping_page import ShippingPage
from pages.shipping_types import AddressData, AddressPolicy, PaymentMethod


logger = setup_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="国际货运真实订单自动化")
    parser.add_argument(
        "--payment-method",
        choices=(PaymentMethod.BALANCE.value, PaymentMethod.COD.value),
        default=PaymentMethod.BALANCE.value,
    )
    parser.add_argument("--cancel-unpaid", action="store_true")
    parser.add_argument(
        "--address-policy",
        choices=(
            AddressPolicy.AUTO.value,
            AddressPolicy.EXISTING.value,
            AddressPolicy.ADD.value,
        ),
        default=AddressPolicy.AUTO.value,
    )
    parser.add_argument("--session", default="shipping_business")
    parser.add_argument("--quit-driver", action="store_true")
    return parser


def read_address_data(environ: Mapping[str, str]) -> AddressData:
    return AddressData(
        match=environ.get("SHIPPING_ADDRESS_MATCH", ""),
        name=environ.get("SHIPPING_ADDRESS_NAME", ""),
        phone=environ.get("SHIPPING_ADDRESS_PHONE", ""),
        country=environ.get("SHIPPING_ADDRESS_COUNTRY", ""),
        city=environ.get("SHIPPING_ADDRESS_CITY", ""),
        detail=environ.get("SHIPPING_ADDRESS_DETAIL", ""),
        postcode=environ.get("SHIPPING_ADDRESS_POSTCODE", ""),
    )


def read_pay_password(environ: Mapping[str, str]) -> str:
    return environ.get("SHIPPING_PAY_PASSWORD", "")


def validate_args(
    args: argparse.Namespace, address_data: AddressData, pay_password: str
) -> None:
    method = PaymentMethod(args.payment_method)
    policy = AddressPolicy(args.address_policy)
    if args.cancel_unpaid and method is PaymentMethod.COD:
        raise ValueError("--cancel-unpaid 不能与 cod 组合")
    if method is PaymentMethod.BALANCE and not args.cancel_unpaid and not pay_password:
        raise ValueError("余额真实支付需要 SHIPPING_PAY_PASSWORD")
    if policy is AddressPolicy.EXISTING and not address_data.match.strip():
        raise ValueError("existing 地址策略需要 SHIPPING_ADDRESS_MATCH")
    if policy is AddressPolicy.ADD or (
        policy is AddressPolicy.AUTO and not address_data.match.strip()
    ):
        missing = address_data.missing_for_add()
        if missing:
            raise ValueError("新增地址缺少字段: " + ",".join(missing))


def main(
    argv: Sequence[str] | None = None, environ: Mapping[str, str] | None = None
) -> int:
    env = os.environ if environ is None else environ
    args = build_parser().parse_args(argv)
    address_data = read_address_data(env)
    pay_password = read_pay_password(env)
    try:
        validate_args(args, address_data, pay_password)
    except ValueError as exc:
        logger.error("参数安全校验失败: %s", exc)
        return 2

    logger.info(
        "海运真实订单 payment_method=%s cancel_unpaid=%s "
        "address_policy=%s password_configured=%s",
        args.payment_method,
        args.cancel_unpaid,
        args.address_policy,
        bool(pay_password),
    )
    manager = DriverManager()
    try:
        driver = manager.get_driver(session_name=args.session)
        ok = ShippingPage(driver).run_order_flow(
            payment_method=PaymentMethod(args.payment_method),
            cancel_unpaid=args.cancel_unpaid,
            pay_password=pay_password,
            address_policy=AddressPolicy(args.address_policy),
            address_data=address_data,
        )
        return 0 if ok else 1
    finally:
        if args.quit_driver:
            manager.close_driver(session_name=args.session)


if __name__ == "__main__":
    raise SystemExit(main())
