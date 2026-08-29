#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同城跑腿业务：菜单往返巡检、下单流程或两者完整执行。

须在项目根目录执行，且 Appium 已启动、设备已连接、账号已登录。
默认不提交订单；只有显式传入 --submit-order 才会真实提交。

用法：
  python scripts/run_transfer_business.py --action menus
  python scripts/run_transfer_business.py --action order
  python scripts/run_transfer_business.py --action full
  python scripts/run_transfer_business.py --action order --submit-order --payment-method balance
  python scripts/run_transfer_business.py --action order --submit-order --payment-method maya --exercise-maya-return
  python scripts/run_transfer_business.py --action full --session transfer_demo --quit-driver

余额支付读取 TRANSFER_PAY_PASSWORD；Maya 流程读取 TRANSFER_MAYA_ACCOUNT 和
TRANSFER_MAYA_PASSWORD。
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from commons.driver import DriverManager
from commons.logger import setup_logger
from pages.transfer_page import TransferPage

logger = setup_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="同城跑腿业务自动化")
    parser.add_argument(
        "--action", choices=("menus", "order", "full"), default="full"
    )
    parser.add_argument("--submit-order", action="store_true")
    parser.add_argument(
        "--payment-method", choices=("balance", "maya"), default="balance"
    )
    parser.add_argument("--exercise-maya-return", action="store_true")
    parser.add_argument("--session", default="transfer_business")
    parser.add_argument("--quit-driver", action="store_true")
    return parser


def read_secrets() -> dict[str, str | None]:
    return {
        "maya_account": os.environ.get("TRANSFER_MAYA_ACCOUNT"),
        "maya_password": os.environ.get("TRANSFER_MAYA_PASSWORD"),
        "pay_password": os.environ.get("TRANSFER_PAY_PASSWORD"),
    }


def main() -> int:
    args = build_parser().parse_args()
    logger.info(
        "同城跑腿 action=%s submit_order=%s exercise_maya_return=%s",
        args.action,
        args.submit_order,
        args.exercise_maya_return,
    )
    manager = None
    ok = False
    try:
        manager = DriverManager()
        driver = manager.get_driver(session_name=args.session)
        page = TransferPage(driver)
        if args.action == "menus":
            ok = page.verify_menu_round_trips()
        elif args.action == "order":
            secrets = read_secrets()
            ok = page.run_order_flow(
                submit_order=args.submit_order,
                payment_method=args.payment_method,
                exercise_maya_return=args.exercise_maya_return,
                **secrets,
            )
        elif args.action == "full":
            ok = page.verify_menu_round_trips()
            if ok:
                secrets = read_secrets()
                ok = page.run_order_flow(
                    submit_order=args.submit_order,
                    payment_method=args.payment_method,
                    exercise_maya_return=args.exercise_maya_return,
                    **secrets,
                )
    except Exception as ex:
        logger.error("同城跑腿业务失败 error_type=%s", type(ex).__name__)
        ok = False
    finally:
        if args.quit_driver and manager is not None:
            try:
                manager.close_driver(session_name=args.session)
            except Exception as ex:
                logger.warning("close_driver 失败: %s", type(ex).__name__)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
