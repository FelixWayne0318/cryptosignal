#!/usr/bin/env python3
# coding: utf-8
"""
回测执行脚本

一键运行完整回测流程：
1. 从数据库加载历史信号
2. 从币安API获取历史价格（带缓存）
3. 运行回测模拟
4. 计算性能指标
5. 生成并保存报告

使用方法：
    python3 tools/run_backtest.py                          # 回测最近30天
    python3 tools/run_backtest.py --days 7                 # 回测最近7天
    python3 tools/run_backtest.py --start 2024-01-01 --end 2024-01-31
    python3 tools/run_backtest.py --symbols BTCUSDT ETHUSDT --capital 20000
    python3 tools/run_backtest.py --min-prob 0.65          # 只回测高概率信号
    python3 tools/run_backtest.py --no-cache               # 不使用价格缓存

高级选项：
    --position-size 0.05       # 每单使用5%资金（默认2%）
    --max-trades 10            # 最大同时持仓（默认5）
    --ttl 12                   # 信号有效期（小时，默认8）
    --save-report              # 保存JSON报告到文件
    --export-csv               # 导出交易明细为CSV
"""
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ats_backtest import (
    BacktestEngine,
    BacktestDataLoader,
    calculate_metrics,
    format_metrics_report,
    generate_report,
    save_report
)
from ats_backtest.report import (
    print_full_report,
    export_trades_csv,
    generate_summary_text
)


def parse_args():
    """解析命令行参数"""
    import argparse

    parser = argparse.ArgumentParser(
        description='CryptoSignal Backtest Engine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 回测最近30天（默认）
  python3 tools/run_backtest.py

  # 回测最近7天
  python3 tools/run_backtest.py --days 7

  # 回测指定时间段
  python3 tools/run_backtest.py --start 2024-01-01 --end 2024-01-31

  # 只回测特定币种
  python3 tools/run_backtest.py --symbols BTCUSDT ETHUSDT

  # 回测高概率信号（>=65%）
  python3 tools/run_backtest.py --min-prob 0.65

  # 使用更大的仓位和更多并发持仓
  python3 tools/run_backtest.py --capital 20000 --position-size 0.05 --max-trades 10

  # 保存报告
  python3 tools/run_backtest.py --save-report --export-csv
        """
    )

    # 时间范围
    time_group = parser.add_mutually_exclusive_group()
    time_group.add_argument('--days', type=int, help='回测最近N天（默认30天）')
    time_group.add_argument('--start', type=str, help='开始日期 (YYYY-MM-DD)')

    parser.add_argument('--end', type=str, help='结束日期 (YYYY-MM-DD，配合--start使用)')

    # 过滤条件
    parser.add_argument('--symbols', nargs='+', help='指定币种列表')
    parser.add_argument('--min-prob', type=float, help='最小概率过滤（0-1）')

    # 回测参数
    parser.add_argument('--capital', type=float, default=10000, help='初始资金（默认10000）')
    parser.add_argument('--position-size', type=float, default=0.02, help='每单仓位比例（默认0.02=2%%）')
    parser.add_argument('--max-trades', type=int, default=5, help='最大同时持仓数（默认5）')
    parser.add_argument('--ttl', type=int, default=8, help='信号有效期小时数（默认8）')

    # 数据选项
    parser.add_argument('--no-cache', action='store_true', help='不使用价格数据缓存')

    # 输出选项
    parser.add_argument('--save-report', action='store_true', help='保存JSON报告到文件')
    parser.add_argument('--export-csv', action='store_true', help='导出交易明细为CSV')
    parser.add_argument('--quiet', action='store_true', help='简化输出（只显示摘要）')

    args = parser.parse_args()

    # 处理时间范围
    if args.start:
        args.start_time = datetime.strptime(args.start, '%Y-%m-%d')
        if args.end:
            args.end_time = datetime.strptime(args.end, '%Y-%m-%d')
        else:
            args.end_time = datetime.utcnow()
    else:
        days = args.days or 30
        args.end_time = datetime.utcnow()
        args.start_time = args.end_time - timedelta(days=days)

    return args


def main():
    """主函数"""
    args = parse_args()

    print()
    print("=" * 70)
    print("  CryptoSignal Backtest Engine")
    print("=" * 70)
    print()

    # 1. 准备数据
    print("📊 Step 1: Loading Data")
    print("-" * 70)

    loader = BacktestDataLoader()
    signals, price_data = loader.prepare_backtest_data(
        start_time=args.start_time,
        end_time=args.end_time,
        symbols=args.symbols,
        min_probability=args.min_prob,
        use_cache=not args.no_cache
    )

    if not signals:
        print("\n❌ No signals found for backtest. Exiting.")
        print()
        return

    if not price_data:
        print("\n❌ No price data loaded. Exiting.")
        print()
        return

    # 2. 运行回测
    print()
    print("🔄 Step 2: Running Backtest Simulation")
    print("-" * 70)

    engine = BacktestEngine(
        start_time=args.start_time,
        end_time=args.end_time,
        initial_capital=args.capital,
        position_size_pct=args.position_size,
        max_open_trades=args.max_trades,
        ttl_hours=args.ttl
    )

    backtest_result = engine.run_from_signals(signals, price_data)

    trades = backtest_result['trades']
    equity_curve = backtest_result['equity_curve']

    print(f"✅ Backtest completed")
    print(f"   Simulated {len(trades)} trades")
    print()

    # 3. 计算指标
    print("📈 Step 3: Calculating Metrics")
    print("-" * 70)

    metrics = calculate_metrics(trades, equity_curve, args.capital)

    print(f"✅ Metrics calculated")
    print()

    # 4. 生成报告
    print("📄 Step 4: Generating Report")
    print("-" * 70)

    config = {
        'start_time': args.start_time.isoformat(),
        'end_time': args.end_time.isoformat(),
        'initial_capital': args.capital,
        'position_size_pct': args.position_size,
        'max_open_trades': args.max_trades,
        'ttl_hours': args.ttl,
        'symbols': args.symbols,
        'min_probability': args.min_prob,
    }

    report = generate_report(
        trades=trades,
        metrics=metrics,
        config=config,
        include_trades=True
    )

    # 保存报告
    if args.save_report:
        report_path = save_report(report)
        print(f"✅ Report saved to: {report_path}")

    # 导出CSV
    if args.export_csv:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = f"data/backtest/reports/trades_{timestamp}.csv"
        Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
        export_trades_csv(trades, csv_path)

    print()

    # 5. 显示结果
    if args.quiet:
        # 简化模式：只显示摘要
        print()
        print(generate_summary_text(metrics))
        print()
    else:
        # 完整模式：显示详细报告
        print_full_report(trades, metrics, equity_curve)

    print()
    print("=" * 70)
    print("  Backtest Completed Successfully!")
    print("=" * 70)
    print()

    # 快速访问提示
    if args.save_report or args.export_csv:
        print("📁 Output files saved to: data/backtest/reports/")
        print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Backtest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
