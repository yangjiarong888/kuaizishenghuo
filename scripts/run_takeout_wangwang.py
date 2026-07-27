#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单独跑「外卖 →（可选）马尼拉定位 → 找店 → 进店」流程（pages/takeout_page.py）。

必须在项目根目录 kuaizishenghuo 下执行，且 Appium 已启动、设备已连接。

用法:
  python scripts/run_takeout_wangwang.py
  python scripts/run_takeout_wangwang.py --shop "旺旺超市 WWCS"
  python scripts/run_takeout_wangwang.py --session my_session
  python scripts/run_takeout_wangwang.py --no-manila
  python scripts/run_takeout_wangwang.py --checkout
  python scripts/run_takeout_wangwang.py --checkout --submit-order
  python scripts/run_takeout_wangwang.py --checkout --category "健康粮油"
  python scripts/run_takeout_wangwang.py --checkout --delivery-time-slot-ordinal 5
  python scripts/run_takeout_wangwang.py --checkout --delivery-slot-contains 01:40
  python scripts/run_takeout_wangwang.py --checkout --checkout-payment cod
  python scripts/run_takeout_wangwang.py --checkout --coupon-policy require
  python scripts/run_takeout_wangwang.py --checkout --pickup-code on --notify-method phone

默认 **不杀进程**（START_MODE=activate）：新建 Appium 会话后只 activate_app，再由脚本里
``ensure_takeout_tab()`` 从当前界面（首页/我的/消息等）**点击底栏「外卖」** 进列表。

需要每次干净冷启动时再显式指定::
  python scripts/run_takeout_wangwang.py --cold

要冷启动请用 ``--cold`` 或 ``--start-mode cold``；未指定时本脚本会强制 ``START_MODE=activate``，
不再沿用环境里误设的 ``START_MODE=cold``。

代码里任意时刻切到外卖首页：TakeoutPageBase(driver).ensure_takeout_tab()
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional, Sequence

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from commons.driver import DriverManager
from commons.logger import setup_logger
from pages.takeout_checkout_mixin import (
    DEFAULT_MERCHANT_REMARK,
    DEFAULT_REMARK_TEXT,
    DEFAULT_RIDER_REMARK,
)
from pages.takeout_page import TakeoutPageBase, open_wangwang_supermarket_from_takeout_home

logger = setup_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="外卖：旺旺店铺进店与安全结算预览")
    parser.add_argument(
        "--session",
        default="takeout_wangwang",
        help="DriverManager 会话名（与已有脚本共用会话时可改成相同名字）",
    )
    parser.add_argument("--shop", default="旺旺超市 WWCS", help="目标店铺名称")
    parser.add_argument(
        "--no-manila",
        action="store_true",
        help="跳过「顶栏定位→马尼拉→保留已选定位」",
    )
    parser.add_argument(
        "--checkout",
        action="store_true",
        help=(
            "进店后在店铺详情跑通：侧栏分类（默认「店内招牌」）→主区首个含价商品加购"
            "（多规格选价高）→结算→支付→断言→取消。不加本参数时进店后即结束。"
        ),
    )
    parser.add_argument(
        "--submit-order",
        action="store_true",
        help="真实创建订单；必须与 --checkout 同时使用",
    )
    parser.add_argument(
        "--category",
        default=None,
        help='店铺左侧分类 content-desc（默认脚本内为「店内招牌」）；显式传空则仍用默认。',
    )
    parser.add_argument(
        "--category-alias",
        action="append",
        default=[],
        metavar="TEXT",
        help="除默认/「--category」外额外尝试的侧栏文案，可多次传入。",
    )
    parser.add_argument(
        "--delivery-time-slot-ordinal",
        type=int,
        default=None,
        metavar="N",
        help=(
            "与 --checkout 配合：选「后天」后，右侧时段列表 **自上而下第 N 项**（1 起算，"
            "例如 5=第五个）。项数不足时会先上滑列表再重试。"
        ),
    )
    parser.add_argument(
        "--delivery-slot-contains",
        default=None,
        metavar="TEXT",
        help=(
            "时段文案需包含的子串（如 01:40）；可与 --delivery-time-slot-ordinal 联用："
            "先筛含该串的格子，再在其中取第 N 行。"
        ),
    )
    parser.add_argument(
        "--checkout-payment",
        choices=("balance", "cod"),
        default="balance",
        help="结账支付方式：balance 余额（默认）；cod 货到付款（不输入支付密码）。",
    )
    parser.add_argument(
        "--coupon-policy",
        choices=("auto", "skip", "require"),
        default="auto",
        help="外卖优惠券策略：auto 平台券/商家券有可用就选；skip 跳过；require 至少选中一类",
    )
    parser.add_argument(
        "--pickup-code",
        choices=("keep", "on", "off"),
        default="keep",
        help="取件码开关：keep 保持当前；on 开启；off 关闭",
    )
    parser.add_argument(
        "--notify-method",
        choices=("keep", "app", "phone"),
        default="keep",
        help="通知方式：keep 保持当前；app 选择 APP 联系；phone 选择电话联系",
    )
    parser.add_argument(
        "--remark-text",
        default=DEFAULT_REMARK_TEXT,
        help="备注自由输入文案；默认 test order，传空字符串可只选快捷备注",
    )
    parser.add_argument(
        "--rider-remark",
        default=DEFAULT_RIDER_REMARK,
        help="对骑手快捷备注；传空字符串可跳过",
    )
    parser.add_argument(
        "--merchant-remark",
        default=DEFAULT_MERCHANT_REMARK,
        help="对商家快捷备注；传空字符串可跳过",
    )
    parser.add_argument(
        "--cold",
        action="store_true",
        help="冷启动：杀进程并 start_activity（原 commons/driver 默认行为；与本脚本默认相反）",
    )
    parser.add_argument(
        "--reuse-app",
        action="store_true",
        help="显式指定不冷启动（等同 activate；本脚本已默认 activate，一般不必再写）",
    )
    parser.add_argument(
        "--start-mode",
        choices=("cold", "activate", "off"),
        default=None,
        help="直接指定 START_MODE（优先级高于默认，低于 --cold）",
    )
    return parser


def validate_args(args: argparse.Namespace) -> None:
    if args.submit_order and not args.checkout:
        raise ValueError("--submit-order requires --checkout")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        validate_args(args)
    except ValueError as exc:
        logger.error("参数安全校验失败: %s", exc)
        return 2

    if args.cold:
        os.environ["START_MODE"] = "cold"
    elif args.start_mode is not None:
        os.environ["START_MODE"] = args.start_mode
    else:
        # 无 --cold/--start-mode 时固定 activate，避免环境或 driver 文档里残留的 START_MODE=cold 导致每次杀进程
        os.environ["START_MODE"] = "activate"
    if args.reuse_app:
        os.environ["START_MODE"] = "activate"

    _sm = os.environ.get("START_MODE", "activate").strip().lower() or "activate"
    logger.info("新建会话时拉 App 策略 START_MODE=%s", _sm)
    if _sm == "activate":
        logger.info("将在前台继续当前 App；若不在外卖列表页，会自动点击底栏「外卖」")
    logger.info("获取驱动 session=%s …", args.session)
    driver = DriverManager().get_driver(session_name=args.session)
    ok = open_wangwang_supermarket_from_takeout_home(
        driver,
        shop_name=args.shop,
        ensure_manila_city=not args.no_manila,
    )
    if ok and not args.checkout:
        logger.info(
            "未加 --checkout：进店流程已完成，已跳过店内加购/结账演示。"
            " 完整下单请加：python scripts/run_takeout_wangwang.py --checkout …"
        )
    if ok and args.checkout:
        page = TakeoutPageBase(driver)
        ok = page.run_shop_checkout_pay_and_cancel_flow(
            submit_order=args.submit_order,
            category=args.category,
            category_aliases=args.category_alias or None,
            delivery_time_slot_ordinal=args.delivery_time_slot_ordinal,
            delivery_slot_contains=args.delivery_slot_contains,
            checkout_payment=args.checkout_payment,
            coupon_policy=args.coupon_policy,
            pickup_code=args.pickup_code,
            notify_method=args.notify_method,
            remark_text=args.remark_text,
            rider_remark=args.rider_remark,
            merchant_remark=args.merchant_remark,
        )
    if ok:
        completed = ""
        if args.checkout:
            completed = (
                "并完成真实下单/取消流程"
                if args.submit_order
                else "并完成结算预览（未提交订单）"
            )
        logger.info(
            "流程结束：已尝试进店「%s」%s",
            args.shop,
            completed,
        )
        return 0
    logger.error("流程失败，见上文日志")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
