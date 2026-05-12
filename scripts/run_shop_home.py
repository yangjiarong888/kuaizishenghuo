#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
商城首页流程（pages/shop_home_page.py）：

  底部「商城」→ **日用百货**（金刚区弹层、选规格加购）→ 回首页
  → **限时特价 / 新品优选**（长滑回顶）→ **不再**重复首页 ``iv_add_cart``（与详情加购重复）
  → 商品详情深度流 → 悬浮购物车 → Banner → 末次首页加购 → 角标 +1

须在项目根目录 kuaizishenghuo 下执行，且 Appium 已启动、设备已连接。

用法:
  python scripts/run_shop_home.py
  python scripts/run_shop_home.py --session shop_home_demo
  python scripts/run_shop_home.py --quit-driver

说明：流程内含多段「列表滑动 ×5、每次等待约 5s」等，**整段常需数分钟**；执行完会 **正常退出进程**。
默认 **不会** ``driver.quit()``（便于同一会话继续跑别的脚本）；需要连 Appium 会话一起关掉时加 ``--quit-driver``。

未登录时脚本会检测登录界面并 **失败退出**（需先手动登录或使用现有登录脚本）。
默认 START_MODE 与 run_takeout_wangwang 一致为 activate，可用 --cold 冷启动。
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
from pages.shop_home_page import ShopHomePage

logger = setup_logger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="商城首页：金刚区/购物车/Banner/加购 演示")
    parser.add_argument(
        "--session",
        default="shop_home",
        help="DriverManager 会话名",
    )
    parser.add_argument(
        "--cold",
        action="store_true",
        help="冷启动：terminate + start_activity",
    )
    parser.add_argument(
        "--start-mode",
        choices=("cold", "activate", "off"),
        default=None,
        help="覆盖 START_MODE（默认 activate，除非指定 --cold）",
    )
    parser.add_argument(
        "--quit-driver",
        action="store_true",
        help="流程结束后对该 session 执行 driver.quit（释放 Appium 会话）",
    )
    args = parser.parse_args()

    if args.cold:
        os.environ["START_MODE"] = "cold"
    elif args.start_mode is not None:
        os.environ["START_MODE"] = args.start_mode
    else:
        os.environ["START_MODE"] = "activate"

    logger.info("获取驱动 session=%s …", args.session)
    driver = DriverManager().get_driver(session_name=args.session)
    ok = ShopHomePage(driver).run_shop_home_flow()
    if args.quit_driver:
        try:
            DriverManager().close_driver(session_name=args.session)
        except Exception as ex:
            logger.warning("close_driver 失败: %s", ex)
    if ok:
        logger.info("shop_home 流程结束：通过；脚本即将退出（exit 0）")
        return 0
    logger.error("shop_home 流程失败，见上文日志；脚本即将退出（exit 1）")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
