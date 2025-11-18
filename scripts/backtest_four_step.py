#!/usr/bin/env python3
# coding: utf-8
"""
Backtest Framework v1.0 - CLI Script
回测框架 - 命令行脚本

功能：
- 命令行接口执行回测
- 支持多符号、自定义时间范围
- 生成JSON/Markdown/CSV报告
- 配置覆盖支持

Usage:
    # Basic backtest (3 months on ETH)
    python scripts/backtest_four_step.py \\
        --symbols ETHUSDT \\
        --start 2024-08-01 \\
        --end 2024-11-01 \\
        --output reports/backtest_eth_3m.json

    # Multi-symbol backtest
    python scripts/backtest_four_step.py \\
        --symbols ETHUSDT,BTCUSDT,SOLUSDT \\
        --start 2024-01-01 \\
        --end 2024-06-01 \\
        --output reports/backtest_multi_6m.json

    # Generate markdown report
    python scripts/backtest_four_step.py \\
        --symbols ETHUSDT \\
        --start 2024-08-01 \\
        --end 2024-11-01 \\
        --output reports/backtest_eth.json \\
        --report-format markdown \\
        --report-output reports/backtest_eth.md

Standard: SYSTEM_ENHANCEMENT_STANDARD.md v3.3.0
Design: docs/BACKTEST_FRAMEWORK_v1.0_DESIGN.md
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

from ats_core.backtest import (
    HistoricalDataLoader,
    BacktestEngine,
    BacktestMetrics
)
from ats_core.cfg import CFG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def parse_arguments():
    """
    解析命令行参数

    Returns:
        argparse.Namespace: 解析后的参数
    """
    parser = argparse.ArgumentParser(
        description="CryptoSignal Backtest Framework v1.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic 3-month backtest on ETH
  python scripts/backtest_four_step.py --symbols ETHUSDT --start 2024-08-01 --end 2024-11-01 --output reports/eth_3m.json

  # Multi-symbol 6-month backtest
  python scripts/backtest_four_step.py --symbols ETHUSDT,BTCUSDT,SOLUSDT --start 2024-01-01 --end 2024-06-01 --output reports/multi_6m.json

  # Generate markdown report
  python scripts/backtest_four_step.py --symbols ETHUSDT --start 2024-08-01 --end 2024-11-01 --output reports/eth.json --report-format markdown --report-output reports/eth.md
        """
    )

    # Required arguments
    parser.add_argument(
        "--symbols",
        required=True,
        help="Comma-separated trading pairs (e.g., ETHUSDT,BTCUSDT)"
    )
    parser.add_argument(
        "--start",
        required=True,
        help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end",
        required=True,
        help="End date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output JSON file path (e.g., reports/backtest_results.json)"
    )

    # Optional arguments
    parser.add_argument(
        "--interval",
        default=None,
        help="Candle interval (default: from config, usually '1h')"
    )
    parser.add_argument(
        "--config-override",
        default=None,
        help="JSON string to override config (e.g., '{\"data_loader\": {\"cache_enabled\": false}}')"
    )
    parser.add_argument(
        "--report-format",
        choices=["json", "markdown", "csv"],
        default="json",
        help="Report format (default: json)"
    )
    parser.add_argument(
        "--report-output",
        default=None,
        help="Optional report output path (if not specified, report is printed to stdout)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level)"
    )

    return parser.parse_args()


def parse_date(date_str: str) -> int:
    """
    解析日期字符串为Unix时间戳（毫秒）

    Args:
        date_str: 日期字符串（YYYY-MM-DD）

    Returns:
        Unix时间戳（毫秒）
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return int(dt.timestamp() * 1000)
    except ValueError as e:
        logger.error(f"日期格式错误: {date_str} - {e}")
        sys.exit(1)


def load_config_with_override(override_json: str = None) -> dict:
    """
    加载配置（支持覆盖）

    Args:
        override_json: JSON字符串（覆盖配置）

    Returns:
        配置字典
    """
    # 重载配置（确保使用最新配置）
    CFG.reload()
    config = CFG.params

    if not config.get("backtest"):
        logger.error("配置文件缺少 'backtest' 配置块！请检查 config/params.json")
        sys.exit(1)

    # 应用覆盖（如果提供）
    if override_json:
        try:
            override_dict = json.loads(override_json)
            # 深度合并（简单实现，只支持2层）
            for key, value in override_dict.items():
                if isinstance(value, dict) and key in config.get("backtest", {}):
                    config["backtest"][key].update(value)
                else:
                    config["backtest"][key] = value
            logger.info(f"配置覆盖已应用: {override_json}")
        except json.JSONDecodeError as e:
            logger.error(f"配置覆盖JSON格式错误: {e}")
            sys.exit(1)

    return config


def main():
    """主函数"""
    args = parse_arguments()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Verbose模式已启用")

    # Print header
    print("=" * 70)
    print("CryptoSignal Backtest Framework v1.0")
    print("=" * 70)
    print()

    # Parse arguments
    symbols = [s.strip().upper() for s in args.symbols.split(",")]
    start_ts = parse_date(args.start)
    end_ts = parse_date(args.end)

    logger.info(f"回测参数:")
    logger.info(f"  - Symbols: {symbols}")
    logger.info(f"  - Time Range: {args.start} ~ {args.end}")
    logger.info(f"  - Interval: {args.interval or 'default (from config)'}")
    logger.info(f"  - Output: {args.output}")

    # Load configuration
    config = load_config_with_override(args.config_override)
    backtest_config = config.get("backtest", {})

    # Initialize components
    logger.info("初始化回测组件...")
    data_loader = HistoricalDataLoader(backtest_config.get("data_loader", {}))
    engine = BacktestEngine(backtest_config.get("engine", {}), data_loader)
    metrics_calculator = BacktestMetrics(backtest_config.get("metrics", {}))

    # Run backtest
    logger.info("开始执行回测...")
    print()
    print("Backtest Progress:")
    print("-" * 70)

    try:
        result = engine.run(
            symbols=symbols,
            start_time=start_ts,
            end_time=end_ts,
            interval=args.interval
        )
    except Exception as e:
        logger.error(f"回测执行失败: {e}", exc_info=True)
        sys.exit(1)

    print("-" * 70)
    print()

    # Save results
    logger.info("保存回测结果...")
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(output_path, 'w') as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info(f"✅ 回测结果已保存: {output_path}")
    except Exception as e:
        logger.error(f"保存回测结果失败: {e}")
        sys.exit(1)

    # Calculate metrics
    logger.info("计算性能指标...")
    try:
        metrics_report = metrics_calculator.calculate_all_metrics(result)
    except Exception as e:
        logger.error(f"指标计算失败: {e}", exc_info=True)
        sys.exit(1)

    # Generate report
    logger.info(f"生成{args.report_format.upper()}报告...")
    try:
        report_content = metrics_calculator.generate_report(
            metrics_report,
            args.report_format
        )

        # Save or print report
        if args.report_output:
            report_path = Path(args.report_output)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            with open(report_path, 'w') as f:
                f.write(report_content)
            logger.info(f"✅ 报告已保存: {report_path}")
        else:
            print()
            print("=" * 70)
            print("BACKTEST REPORT")
            print("=" * 70)
            print(report_content)
            print("=" * 70)

    except Exception as e:
        logger.error(f"报告生成失败: {e}", exc_info=True)
        sys.exit(1)

    # Print summary
    print()
    print("=" * 70)
    print("BACKTEST SUMMARY")
    print("=" * 70)
    sm = metrics_report.signal_metrics
    pm = metrics_report.portfolio_metrics
    print(f"Total Signals:        {sm.total_signals}")
    print(f"Win Rate:             {sm.win_rate:.2f}% ({sm.win_count}W / {sm.loss_count}L)")
    print(f"Avg PnL:              {sm.avg_pnl_percent:+.2f}%")
    print(f"Avg RR Ratio:         {sm.avg_rr_ratio:.2f}")
    print(f"Sharpe Ratio:         {pm.sharpe_ratio:.2f}")
    print(f"Sortino Ratio:        {pm.sortino_ratio:.2f}")
    print(f"Max Drawdown:         {pm.max_drawdown_percent:.2f}%")
    print(f"Profit Factor:        {pm.profit_factor:.2f}")
    print(f"Total PnL:            {pm.total_pnl_usdt:+.2f} USDT")
    print(f"Max Concurrent:       {pm.max_concurrent_positions}")
    print(f"Avg Trades/Day:       {pm.avg_trades_per_day:.2f}")
    print("=" * 70)

    logger.info("✅ 回测完成！")


if __name__ == "__main__":
    main()
