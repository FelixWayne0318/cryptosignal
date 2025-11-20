#!/usr/bin/env python3
# coding: utf-8
"""
Paper Trading CLI脚本

使用Binance Mainnet实时数据运行Paper Trading

Usage:
    python3 scripts/paper_trader.py
    python3 scripts/paper_trader.py --symbols BNBUSDT ETHUSDT
    python3 scripts/paper_trader.py --equity 50000
    python3 scripts/paper_trader.py --reset  # 清除状态重新开始

Version: v1.0.0
Standard: SYSTEM_ENHANCEMENT_STANDARD.md v3.3.0
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ats_core.cfg import CFG
from ats_core.realtime.paper_trader import PaperTrader
from ats_core.realtime.state_manager import StateManager


def setup_logging(verbose: bool = False) -> None:
    """配置日志"""
    level = logging.DEBUG if verbose else logging.INFO

    # 配置根日志器
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 降低第三方库日志级别
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="CryptoSignal Paper Trading - 实时模拟交易",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 使用默认配置运行
    python3 scripts/paper_trader.py

    # 指定交易对
    python3 scripts/paper_trader.py --symbols BNBUSDT ETHUSDT

    # 设置初始资金
    python3 scripts/paper_trader.py --equity 50000

    # 清除状态重新开始
    python3 scripts/paper_trader.py --reset

    # 详细日志
    python3 scripts/paper_trader.py -v
        """
    )

    parser.add_argument(
        "--symbols",
        nargs="+",
        default=None,
        help="交易对列表（默认从config读取）"
    )

    parser.add_argument(
        "--equity",
        type=float,
        default=None,
        help="初始资金（USDT，默认从config读取）"
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="清除状态文件重新开始"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="显示详细日志"
    )

    return parser.parse_args()


async def main():
    """主函数"""
    args = parse_args()

    # 配置日志
    setup_logging(args.verbose)

    logger = logging.getLogger(__name__)

    # 打印横幅
    print("")
    print("=" * 60)
    print("  CryptoSignal Paper Trading v1.0.0")
    print("  Real-Time Paper Trading with Binance Mainnet Data")
    print("=" * 60)
    print("")

    # 加载配置
    config = CFG.params.get("paper_trading", {}).copy()

    # 覆盖命令行参数
    if args.symbols:
        config["symbols"] = args.symbols
        logger.info(f"使用命令行symbols: {args.symbols}")

    if args.equity:
        config["initial_equity"] = args.equity
        logger.info(f"使用命令行equity: {args.equity}")

    # 重置状态
    if args.reset:
        state_manager = StateManager(config.get("reporting", {}))
        state_manager.clear_state()
        logger.info("状态已重置")

    # 显示配置
    logger.info("配置:")
    logger.info(f"  Symbols: {config.get('symbols', ['BNBUSDT'])}")
    logger.info(f"  Initial Equity: ${config.get('initial_equity', 100000):.2f}")
    logger.info(f"  Interval: {config.get('interval', '1h')}")
    logger.info(f"  Max Positions: {config.get('risk', {}).get('max_concurrent_positions', 3)}")
    logger.info(f"  Per Trade Risk: {config.get('risk', {}).get('per_trade_risk_pct', 0.01)*100:.1f}%")
    print("")

    # 创建并运行PaperTrader
    try:
        trader = PaperTrader(config)
        await trader.start()
    except KeyboardInterrupt:
        logger.info("收到中断信号")
    except Exception as e:
        logger.error(f"运行异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
