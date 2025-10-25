#!/usr/bin/env python3
# coding: utf-8
"""
查询统计脚本

快速查看信号统计、胜率、盈亏等信息

使用方法：
    python3 scripts/query_stats.py                  # 显示最近30天摘要
    python3 scripts/query_stats.py --days 7         # 显示最近7天
    python3 scripts/query_stats.py --recent 20      # 显示最近20个信号
    python3 scripts/query_stats.py --open           # 显示未平仓信号
"""
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ats_core.database.operations import (
    get_performance_summary,
    get_recent_signals,
    get_open_signals
)


def print_header(title):
    """打印标题"""
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_performance_summary(days=30):
    """打印性能摘要"""
    print_header(f"Performance Summary (Last {days} Days)")

    summary = get_performance_summary(days)

    if 'error' in summary:
        print(f"\n⚠️  {summary['error']}\n")
        return

    # 基本统计
    print(f"\n📊 Trading Statistics")
    print(f"  Total Trades:      {summary['total_trades']}")
    print(f"  Winning Trades:    {summary['winning_trades']} ({summary['win_rate']*100:.1f}%)")
    print(f"  Losing Trades:     {summary['losing_trades']} ({(1-summary['win_rate'])*100:.1f}%)")

    # 盈亏统计
    print(f"\n💰 P&L Statistics")
    print(f"  Total PnL:         {summary['total_pnl']:+.2f}%")
    print(f"  Average Win:       {summary['avg_win']:+.2f}%")
    print(f"  Average Loss:      {summary['avg_loss']:+.2f}%")
    print(f"  Profit Factor:     {summary['profit_factor']:.2f}")
    print(f"  Best Trade:        {summary['best_trade']:+.2f}%")
    print(f"  Worst Trade:       {summary['worst_trade']:+.2f}%")

    # 持仓时间
    print(f"\n⏱️  Trading Behavior")
    print(f"  Avg Holding Time:  {summary['avg_holding_hours']:.1f} hours")

    # 分方向统计
    print(f"\n📈 Direction Analysis")
    print(f"  Long Trades:       {summary['long_trades']} (Win Rate: {summary['long_win_rate']*100:.1f}%)")
    print(f"  Short Trades:      {summary['short_trades']} (Win Rate: {summary['short_win_rate']*100:.1f}%)")

    # 评级
    print(f"\n⭐ Performance Rating")
    if summary['win_rate'] >= 0.60:
        rating = "Excellent"
        emoji = "🎉"
    elif summary['win_rate'] >= 0.50:
        rating = "Good"
        emoji = "✅"
    elif summary['win_rate'] >= 0.40:
        rating = "Fair"
        emoji = "⚠️"
    else:
        rating = "Needs Improvement"
        emoji = "❌"

    print(f"  {emoji} {rating} (Win Rate: {summary['win_rate']*100:.1f}%)")

    print()


def print_recent_signals(limit=20):
    """打印最近的信号"""
    print_header(f"Recent Signals (Last {limit})")

    signals = get_recent_signals(limit=limit)

    if not signals:
        print("\n⚠️  No signals found\n")
        return

    print(f"\n{'ID':<6} {'Symbol':<12} {'Side':<6} {'Prob':<6} {'Status':<8} {'PnL%':<8} {'Time'}")
    print("-" * 70)

    for s in signals:
        pnl_str = f"{s.pnl_percent:+.2f}%" if s.pnl_percent else "-"

        # 颜色标记
        if s.status == 'open':
            status_emoji = "🔵"
        elif s.status == 'closed':
            status_emoji = "✅" if s.pnl_percent and s.pnl_percent > 0 else "❌"
        else:
            status_emoji = "⏰"

        side_emoji = "🟩" if s.side == 'long' else "🟥"

        time_str = s.timestamp.strftime("%m-%d %H:%M")

        print(f"{s.id:<6} {s.symbol:<12} {side_emoji}{s.side:<6} {s.probability*100:>5.1f}% {status_emoji}{s.status:<8} {pnl_str:<8} {time_str}")

    print()


def print_open_signals():
    """打印未平仓信号"""
    print_header("Open Signals")

    signals = get_open_signals()

    if not signals:
        print("\n✅ No open signals\n")
        return

    print(f"\n{'ID':<6} {'Symbol':<12} {'Side':<6} {'Prob':<6} {'Entry':<10} {'SL':<10} {'TP':<10} {'Age (h)'}")
    print("-" * 80)

    for s in signals:
        age_hours = (datetime.utcnow() - s.timestamp).total_seconds() / 3600
        side_emoji = "🟩" if s.side == 'long' else "🟥"

        entry_str = f"{s.entry_price:.4f}" if s.entry_price else "-"
        sl_str = f"{s.stop_loss:.4f}" if s.stop_loss else "-"
        tp_str = f"{s.take_profit_2 or s.take_profit_1:.4f}" if s.take_profit_2 or s.take_profit_1 else "-"

        print(f"{s.id:<6} {s.symbol:<12} {side_emoji}{s.side:<6} {s.probability*100:>5.1f}% {entry_str:<10} {sl_str:<10} {tp_str:<10} {age_hours:.1f}")

    print(f"\nTotal: {len(signals)} open positions")
    print()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='Query CryptoSignal Statistics')
    parser.add_argument('--days', type=int, default=30, help='Performance summary for last N days (default: 30)')
    parser.add_argument('--recent', type=int, help='Show recent N signals')
    parser.add_argument('--open', action='store_true', help='Show open signals')
    parser.add_argument('--all', action='store_true', help='Show all sections')

    args = parser.parse_args()

    print("\n" + "="*70)
    print("  CryptoSignal Database Statistics")
    print("="*70)

    # 如果没有指定任何选项，显示摘要
    if not (args.recent or args.open):
        args.all = True

    if args.all or (not args.recent and not args.open):
        print_performance_summary(days=args.days)

    if args.all or args.open:
        print_open_signals()

    if args.recent:
        print_recent_signals(limit=args.recent)

    print("="*70)
    print()


if __name__ == '__main__':
    main()
