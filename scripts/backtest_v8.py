#!/usr/bin/env python3
# coding: utf-8
"""
V8 Backtest Script - V8架构回测脚本
使用CCXT + Cryptostore + CryptoSignal + Freqtrade

Usage:
    # 基本回测
    python scripts/backtest_v8.py --symbols BTCUSDT --start 2024-11-01 --end 2024-11-21

    # 多交易对回测
    python scripts/backtest_v8.py --symbols BTCUSDT,ETHUSDT --start 2024-11-01 --end 2024-11-21

    # 指定输出文件
    python scripts/backtest_v8.py --symbols BTCUSDT --start 2024-11-01 --end 2024-11-21 --output reports/v8_backtest.json

    # 使用Freqtrade引擎
    python scripts/backtest_v8.py --symbols BTCUSDT --start 2024-11-01 --end 2024-11-21 --engine freqtrade

Standard: SYSTEM_ENHANCEMENT_STANDARD.md v3.3.0
Architecture: V8 六层架构
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ats_core.pipeline.v8_backtest_pipeline import V8BacktestPipeline
from ats_core.backtest.metrics import MetricsReport

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="V8 Backtest - 使用CCXT+Cryptostore+Freqtrade",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # BTC 20天回测
  python scripts/backtest_v8.py --symbols BTCUSDT --start 2024-11-01 --end 2024-11-21

  # 多交易对回测
  python scripts/backtest_v8.py --symbols BTCUSDT,ETHUSDT --start 2024-11-01 --end 2024-11-21

  # 使用Freqtrade引擎
  python scripts/backtest_v8.py --symbols BTCUSDT --start 2024-11-01 --end 2024-11-21 --engine freqtrade
        """
    )

    parser.add_argument(
        "--symbols",
        required=True,
        help="交易对列表，逗号分隔 (e.g., BTCUSDT,ETHUSDT)"
    )
    parser.add_argument(
        "--start",
        required=True,
        help="开始日期 (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end",
        required=True,
        help="结束日期 (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="输出文件路径 (默认: reports/v8_backtest_<timestamp>.json)"
    )
    parser.add_argument(
        "--timeframe",
        default="1h",
        help="K线周期 (默认: 1h)"
    )
    parser.add_argument(
        "--engine",
        choices=["internal", "freqtrade"],
        default="internal",
        help="回测引擎 (默认: internal)"
    )
    parser.add_argument(
        "--exchange",
        default="binanceusdm",
        help="交易所ID (默认: binanceusdm)"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="禁用缓存"
    )

    return parser.parse_args()


def print_metrics_report(report: MetricsReport) -> None:
    """打印指标报告"""
    sm = report.signal_metrics
    pm = report.portfolio_metrics

    print("\n" + "=" * 70)
    print("V8 BACKTEST REPORT")
    print("=" * 70)

    print(json.dumps({
        "signal_metrics": {
            "total_signals": sm.total_signals,
            "win_count": sm.win_count,
            "loss_count": sm.loss_count,
            "win_rate": round(sm.win_rate, 2),
            "avg_pnl_percent": round(sm.avg_pnl_percent, 2),
            "median_pnl_percent": round(sm.median_pnl_percent, 2),
            "max_pnl_percent": round(sm.max_pnl_percent, 2),
            "min_pnl_percent": round(sm.min_pnl_percent, 2),
            "std_pnl_percent": round(sm.std_pnl_percent, 2),
            "avg_rr_ratio": round(sm.avg_rr_ratio, 2),
            "max_consecutive_wins": sm.max_consecutive_wins,
            "max_consecutive_losses": sm.max_consecutive_losses,
            "avg_holding_hours": round(sm.avg_holding_hours, 2),
            "median_holding_hours": round(sm.median_holding_hours, 2),
        },
        "portfolio_metrics": {
            "sharpe_ratio": round(pm.sharpe_ratio, 2),
            "sortino_ratio": round(pm.sortino_ratio, 2),
            "max_drawdown_percent": round(pm.max_drawdown_percent, 2),
            "max_concurrent_positions": pm.max_concurrent_positions,
            "avg_trades_per_day": round(pm.avg_trades_per_day, 2),
            "profit_factor": round(pm.profit_factor, 2),
            "total_pnl_usdt": round(pm.total_pnl_usdt, 2),
            "total_pnl_percent": round(pm.total_pnl_percent, 2),
        }
    }, indent=2))

    print("=" * 70)
    print("\nV8 BACKTEST SUMMARY")
    print("=" * 70)
    print(f"Total Signals:        {sm.total_signals}")
    print(f"Win Rate:             {sm.win_rate:.2f}% ({sm.win_count}W / {sm.loss_count}L)")
    print(f"Avg PnL:              {'+' if sm.avg_pnl_percent >= 0 else ''}{sm.avg_pnl_percent:.2f}%")
    print(f"Avg RR Ratio:         {sm.avg_rr_ratio:.2f}")
    print(f"Sharpe Ratio:         {pm.sharpe_ratio:.2f}")
    print(f"Sortino Ratio:        {pm.sortino_ratio:.2f}")
    print(f"Max Drawdown:         {pm.max_drawdown_percent:.2f}%")
    print(f"Profit Factor:        {pm.profit_factor:.2f}")
    print(f"Total PnL:            {'+' if pm.total_pnl_usdt >= 0 else ''}{pm.total_pnl_usdt:.2f} USDT")
    print(f"Max Concurrent:       {pm.max_concurrent_positions}")
    print(f"Avg Trades/Day:       {pm.avg_trades_per_day:.2f}")
    print("=" * 70)


def main():
    args = parse_arguments()

    # 解析参数
    symbols = [s.strip().upper() for s in args.symbols.split(",")]
    start_time = datetime.strptime(args.start, "%Y-%m-%d")
    end_time = datetime.strptime(args.end, "%Y-%m-%d")

    # 生成输出文件名
    if args.output:
        output_path = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = project_root / "reports" / f"v8_backtest_{timestamp}.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("V8 Backtest Framework")
    print("=" * 70)
    print(f"Symbols:      {symbols}")
    print(f"Time Range:   {args.start} ~ {args.end}")
    print(f"Timeframe:    {args.timeframe}")
    print(f"Engine:       {args.engine}")
    print(f"Exchange:     {args.exchange}")
    print(f"Cache:        {'Disabled' if args.no_cache else 'Enabled'}")
    print(f"Output:       {output_path}")
    print("=" * 70)
    print()

    # 构建配置覆盖
    config_override = {
        "data_source": {
            "exchange_id": args.exchange
        },
        "cache": {
            "enabled": not args.no_cache
        },
        "engine": {
            "type": args.engine,
            "default_timeframe": args.timeframe
        }
    }

    try:
        # 初始化V8回测管道
        logger.info("初始化V8回测管道...")
        pipeline = V8BacktestPipeline(config_override)

        # 显示状态
        status = pipeline.get_status()
        logger.info(f"管道状态: engine={status['engine_type']}, freqtrade={status['freqtrade_available']}")

        # 执行回测
        logger.info("开始执行V8回测...")
        result = pipeline.run(
            symbols=symbols,
            start_time=start_time,
            end_time=end_time,
            timeframe=args.timeframe
        )

        # 保存结果
        logger.info(f"保存结果到: {output_path}")

        # 将结果转换为可序列化格式
        output_data = {
            "metadata": {
                "symbols": symbols,
                "start_time": args.start,
                "end_time": args.end,
                "timeframe": args.timeframe,
                "engine": result["engine"],
                "data_source": result["data_source"],
                "timestamp": datetime.now().isoformat()
            },
            "signals": [
                {
                    "symbol": s.symbol,
                    "direction": s.direction,
                    "entry_time": s.entry_time.isoformat() if s.entry_time else None,
                    "exit_time": s.exit_time.isoformat() if s.exit_time else None,
                    "entry_price": s.entry_price,
                    "exit_price": s.exit_price,
                    "pnl_percent": s.pnl_percent,
                    "pnl_usdt": s.pnl_usdt,
                    "final_strength": s.final_strength,
                    "probability": s.probability
                }
                for s in result["result"].signals
            ],
            "metrics": {
                "signal_metrics": {
                    "total_signals": result["metrics"].signal_metrics.total_signals,
                    "win_rate": result["metrics"].signal_metrics.win_rate,
                    "avg_pnl_percent": result["metrics"].signal_metrics.avg_pnl_percent
                },
                "portfolio_metrics": {
                    "sharpe_ratio": result["metrics"].portfolio_metrics.sharpe_ratio,
                    "max_drawdown_percent": result["metrics"].portfolio_metrics.max_drawdown_percent,
                    "total_pnl_usdt": result["metrics"].portfolio_metrics.total_pnl_usdt
                }
            }
        }

        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2, default=str)

        # 打印报告
        print_metrics_report(result["metrics"])

        logger.info("V8回测完成!")
        return 0

    except Exception as e:
        logger.error(f"V8回测失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
