#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
商城业务脚本：搜索、商品详情、下单、发送 IM 消息、分享。

用法示例：
  python scripts/run_shop_business.py --action search --keyword "牛奶"
  python scripts/run_shop_business.py --action detail --keyword "牛奶"  # 进入详情并浏览主图/详情/活动/更多商品/回顶部
  python scripts/run_shop_business.py --action share --keyword "牛奶" --share-target "复制链接"
  python scripts/run_shop_business.py --action im --keyword "牛奶" --message "你好，请问还有货吗？"
  python scripts/run_shop_business.py --action order --keyword "牛奶"
  python scripts/run_shop_business.py --action order --keyword "牛奶" --submit-order
  python scripts/run_shop_business.py --action full --keyword "牛奶" --message "你好，请问还有货吗？"

默认只会到「确认订单/提交订单」页；只有显式传入 --submit-order 才点击提交订单。
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
from pages.shop_business_page import ShopBusinessPage

logger = setup_logger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="商城业务：搜索/详情/下单/IM/分享")
    parser.add_argument(
        "--action",
        choices=("search", "detail", "order", "im", "share", "full"),
        default="full",
        help="要执行的商城业务动作",
    )
    parser.add_argument("--keyword", default="牛奶", help="商品搜索关键字")
    parser.add_argument(
        "--message",
        default="你好，请问这个商品还有货吗？",
        help="发送给客服/IM 的消息",
    )
    parser.add_argument(
        "--share-target",
        default="复制链接",
        help="分享面板目标，默认复制链接；传空字符串则只打开分享面板",
    )
    parser.add_argument(
        "--submit-order",
        action="store_true",
        help="真正点击「提交订单/确认订单」；默认不提交，避免误下单",
    )
    parser.add_argument("--session", default="shop_business", help="DriverManager 会话名")
    parser.add_argument("--cold", action="store_true", help="冷启动 App")
    parser.add_argument(
        "--start-mode",
        choices=("cold", "activate", "off"),
        default=None,
        help="覆盖 START_MODE（默认 activate，除非指定 --cold）",
    )
    parser.add_argument(
        "--quit-driver",
        action="store_true",
        help="流程结束后关闭 Appium 会话",
    )
    args = parser.parse_args()

    if args.cold:
        os.environ["START_MODE"] = "cold"
    elif args.start_mode is not None:
        os.environ["START_MODE"] = args.start_mode
    else:
        os.environ["START_MODE"] = "activate"

    share_target = args.share_target.strip()
    if share_target == "":
        share_target = None

    logger.info("获取驱动 session=%s …", args.session)
    driver = DriverManager().get_driver(session_name=args.session)
    page = ShopBusinessPage(driver)
    ok = False
    try:
        if args.action == "search":
            ok = page.search_goods(args.keyword)
        elif args.action == "detail":
            ok = page.open_and_browse_goods_detail(args.keyword)
        elif args.action == "share":
            ok = page.open_goods_detail(args.keyword) and page.tap_share_on_detail(
                share_target
            )
        elif args.action == "im":
            ok = page.open_goods_detail(args.keyword) and page.send_detail_im_message(
                args.message
            )
        elif args.action == "order":
            ok = page.run_order_flow(
                args.keyword,
                submit_order=args.submit_order,
            )
        elif args.action == "full":
            ok = page.run_full_business_flow(
                keyword=args.keyword,
                im_message=args.message,
                share_target=share_target,
                submit_order=args.submit_order,
            )
    finally:
        if args.quit_driver:
            try:
                DriverManager().close_driver(session_name=args.session)
            except Exception as ex:
                logger.warning("close_driver 失败: %s", ex)

    if ok:
        logger.info("商城业务动作 %s 执行通过", args.action)
        return 0
    logger.error("商城业务动作 %s 执行失败", args.action)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
