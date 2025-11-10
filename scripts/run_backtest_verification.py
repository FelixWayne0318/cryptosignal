#!/usr/bin/env python3
# coding: utf-8
"""
v7.2系统回测验证脚本

目的：
1. 从数据库加载历史信号
2. 使用真实价格数据回测信号表现
3. 计算关键绩效指标（胜率、夏普比率、最大回撤）
4. 生成完整的验证报告

要求（来自SYSTEM_REFACTOR_V72_AUDIT.md - P1.2）：
- 至少6个月的历史数据
- 关键指标：胜率、夏普比率、最大回撤、利润因子
- 分方向统计（做多/做空）
- 分时段统计（月度收益）
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3
import json

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ats_backtest import BacktestEngine, BacktestDataLoader, calculate_metrics, format_metrics_report
from ats_backtest.report import generate_report, save_report, print_full_report


def query_signals_from_db(db_path: str, start_time: datetime, end_time: datetime, min_probability: float = 0) -> list:
    """
    从cryptosignal.db的signals表加载历史信号

    Args:
        db_path: 数据库路径
        start_time: 开始时间
        end_time: 结束时间
        min_probability: 最小概率过滤

    Returns:
        信号列表（字典格式）
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 查询信号（时间戳存储为字符串）
    query = """
    SELECT
        id,
        symbol,
        timestamp,
        side,
        probability,
        entry_price,
        stop_loss,
        take_profit_1,
        take_profit_2,
        current_price,
        is_prime,
        scores
    FROM signals
    WHERE timestamp >= ? AND timestamp <= ?
        AND probability >= ?
        AND entry_price IS NOT NULL
        AND stop_loss IS NOT NULL
    ORDER BY timestamp ASC
    """

    # 时间戳格式化为字符串（数据库中存储为DATETIME字符串）
    start_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
    end_str = end_time.strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute(query, (start_str, end_str, min_probability))
    rows = cursor.fetchall()

    signals = []
    for row in rows:
        signal_id, symbol, ts_str, side, prob, entry_price, stop_loss, tp1, tp2, current_price, is_prime, scores_json = row

        # 解析时间戳
        try:
            # 尝试解析带小数的时间戳
            timestamp = datetime.strptime(ts_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
        except:
            # 如果解析失败，尝试其他格式
            try:
                timestamp = datetime.fromisoformat(ts_str)
            except:
                print(f"⚠️  Failed to parse timestamp: {ts_str}, skipping signal")
                continue

        # 解析scores JSON
        scores_dict = {}
        if scores_json:
            try:
                scores_dict = json.loads(scores_json)
            except:
                scores_dict = {}

        # 构建信号字典
        signals.append({
            'signal_id': str(signal_id),
            'timestamp': timestamp,
            'entry_time': timestamp,
            'symbol': symbol,
            'side': side.lower(),  # 转换为小写 (long/short)
            'entry_price': entry_price,
            'current_price': current_price or entry_price,
            'stop_loss': stop_loss,
            'sl': stop_loss,
            'take_profit_1': tp1,
            'tp1': tp1,
            'take_profit_2': tp2,
            'tp2': tp2,
            'probability': prob or 0.5,
            'scores': scores_dict or {},
            'is_prime': bool(is_prime),
        })

    conn.close()

    print(f"✅ Loaded {len(signals)} signals from database")
    print(f"   Period: {start_time.date()} to {end_time.date()}")
    if signals:
        symbols = set(s['symbol'] for s in signals)
        print(f"   Symbols: {len(symbols)} unique coins")

    return signals


def check_data_availability(db_path: str) -> dict:
    """
    检查数据库中的数据可用性

    Returns:
        数据统计字典
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 检查signals表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='signals'")
    if not cursor.fetchone():
        conn.close()
        return {'error': 'signals table not found'}

    # 统计信号数量
    cursor.execute("SELECT COUNT(*) FROM signals")
    total_signals = cursor.fetchone()[0]

    # 统计有效信号（有entry_price和stop_loss）
    cursor.execute("SELECT COUNT(*) FROM signals WHERE entry_price IS NOT NULL AND stop_loss IS NOT NULL")
    valid_signals = cursor.fetchone()[0]

    # 获取时间范围
    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM signals WHERE entry_price IS NOT NULL")
    min_ts_str, max_ts_str = cursor.fetchone()

    earliest = None
    latest = None
    if min_ts_str and max_ts_str:
        try:
            earliest = datetime.strptime(min_ts_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
            latest = datetime.strptime(max_ts_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
        except:
            # 尝试其他格式
            try:
                earliest = datetime.fromisoformat(min_ts_str)
                latest = datetime.fromisoformat(max_ts_str)
            except:
                pass

    # 统计币种数量
    cursor.execute("SELECT COUNT(DISTINCT symbol) FROM signals WHERE entry_price IS NOT NULL")
    unique_symbols = cursor.fetchone()[0]

    conn.close()

    # 计算数据跨度
    duration_days = 0
    if earliest and latest:
        duration_days = (latest - earliest).days

    return {
        'total_signals': total_signals,
        'valid_signals': valid_signals,
        'earliest_signal': earliest,
        'latest_signal': latest,
        'duration_days': duration_days,
        'unique_symbols': unique_symbols,
    }


def run_backtest_verification(
    start_time: datetime = None,
    end_time: datetime = None,
    initial_capital: float = 10000,
    min_confidence: float = 0,
    save_results: bool = True
):
    """
    运行完整的回测验证

    Args:
        start_time: 回测开始时间（默认：6个月前）
        end_time: 回测结束时间（默认：现在）
        initial_capital: 初始资金（USDT）
        min_confidence: 最小置信度过滤
        save_results: 是否保存结果到文件
    """
    print("=" * 80)
    print("  v7.2 System Backtest Verification")
    print("=" * 80)
    print()

    # 1. 确定数据库路径
    db_path = project_root / "data" / "database" / "cryptosignal.db"

    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        print("   Please run the system to generate historical signals first.")
        return None

    print(f"📂 Database: {db_path}")
    print()

    # 2. 检查数据可用性
    print("🔍 Checking data availability...")
    print()
    data_stats = check_data_availability(str(db_path))

    if 'error' in data_stats:
        print(f"❌ {data_stats['error']}")
        return None

    print(f"  Total signals in DB:       {data_stats['total_signals']}")
    print(f"  Valid signals:             {data_stats['valid_signals']}")
    print(f"  Unique symbols:            {data_stats['unique_symbols']}")
    print(f"  Earliest signal:           {data_stats['earliest_signal']}")
    print(f"  Latest signal:             {data_stats['latest_signal']}")
    print(f"  Data coverage:             {data_stats['duration_days']} days")
    print()

    # 检查是否有足够的数据
    if data_stats['valid_signals'] == 0:
        print("❌ No valid signals found in database.")
        print("   Please run the system to generate signals first.")
        return None

    if data_stats['duration_days'] < 7:
        print(f"⚠️  Warning: Only {data_stats['duration_days']} days of data available.")
        print("   For reliable backtest, at least 180 days (6 months) is recommended.")
        print()

    # 3. 确定回测时间范围
    if start_time is None:
        # 默认：使用所有可用数据，或最近6个月
        if data_stats['earliest_signal']:
            start_time = data_stats['earliest_signal']
        else:
            start_time = datetime.now() - timedelta(days=180)

    if end_time is None:
        # 默认：使用最新数据点
        if data_stats['latest_signal']:
            end_time = data_stats['latest_signal']
        else:
            end_time = datetime.now()

    print(f"📅 Backtest Period")
    print(f"   Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   End:   {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Duration: {(end_time - start_time).days} days")
    print()

    # 4. 加载信号数据
    print("📊 Loading signals from database...")
    signals = query_signals_from_db(
        db_path=str(db_path),
        start_time=start_time,
        end_time=end_time,
        min_probability=min_confidence
    )

    if not signals:
        print("❌ No signals found in the specified period.")
        return None

    print()

    # 5. 加载价格数据
    print("📈 Loading price data...")
    data_loader = BacktestDataLoader()

    # 提取所有涉及的币种
    symbols = list(set(s['symbol'] for s in signals))
    print(f"   Loading data for {len(symbols)} symbols...")

    price_data = data_loader.load_price_data(
        symbols=symbols,
        start_time=start_time,
        end_time=end_time + timedelta(days=7),  # 额外加载7天以跟踪退出
        interval='1h',
        use_cache=True
    )

    if not price_data:
        print("❌ Failed to load price data.")
        return None

    print()

    # 6. 运行回测
    print("🚀 Running backtest...")
    print()

    engine = BacktestEngine(
        start_time=start_time,
        end_time=end_time,
        initial_capital=initial_capital,
        position_size_pct=0.02,  # 每次2%仓位
        max_open_trades=5,       # 最多5个持仓
        ttl_hours=8,             # 信号有效期8小时
        commission_rate=0.0004   # 币安手续费0.04%
    )

    results = engine.run_from_signals(signals, price_data)

    if 'error' in results:
        print(f"❌ Backtest error: {results['error']}")
        return None

    print()
    print("=" * 80)
    print()

    # 7. 计算性能指标
    closed_trades = results['trades']
    equity_curve = results['equity_curve']

    metrics = calculate_metrics(
        trades=closed_trades,
        equity_curve=equity_curve,
        initial_capital=initial_capital
    )

    # 8. 打印完整报告
    print_full_report(closed_trades, metrics, equity_curve)

    # 9. 保存报告
    if save_results:
        report_data = generate_report(
            trades=closed_trades,
            metrics=metrics,
            config={
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'initial_capital': initial_capital,
                'position_size_pct': 0.02,
                'max_open_trades': 5,
                'ttl_hours': 8,
                'commission_rate': 0.0004,
                'min_confidence': min_confidence,
            },
            include_trades=True
        )

        # 保存JSON报告
        report_dir = project_root / "data" / "backtest" / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = save_report(report_data, output_dir=str(report_dir), filename=f"backtest_{timestamp}.json")

        print()
        print(f"💾 Report saved to: {report_file}")

        # 同时保存为Markdown格式的人类可读报告
        md_file = report_dir / f"backtest_{timestamp}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(generate_markdown_report(metrics, results['summary'], closed_trades))

        print(f"💾 Markdown report saved to: {md_file}")

    print()
    print("=" * 80)
    print("✅ Backtest verification completed!")
    print("=" * 80)

    return {
        'metrics': metrics,
        'trades': closed_trades,
        'equity_curve': equity_curve,
        'summary': results['summary']
    }


def generate_markdown_report(metrics: dict, summary: dict, trades: list) -> str:
    """
    生成Markdown格式的回测报告

    Args:
        metrics: 性能指标
        summary: 回测摘要
        trades: 交易列表

    Returns:
        Markdown文本
    """
    lines = []

    lines.append("# v7.2 System Backtest Verification Report")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 1. 执行摘要
    lines.append("## 1. Executive Summary")
    lines.append("")
    lines.append(f"- **Total Trades:** {metrics['total_trades']}")
    lines.append(f"- **Win Rate:** {metrics['win_rate']*100:.2f}%")
    lines.append(f"- **Total Return:** {metrics['total_return']*100:+.2f}%")
    lines.append(f"- **Profit Factor:** {metrics['profit_factor']:.2f}")
    lines.append(f"- **Sharpe Ratio:** {metrics['sharpe_ratio']:.2f}")
    lines.append(f"- **Max Drawdown:** {metrics['max_drawdown_pct']*100:.2f}%")
    lines.append("")

    # 2. 绩效评级
    wr = metrics['win_rate']
    if wr >= 0.60:
        rating = "Excellent (A)"
        assessment = "System performance exceeds industry standards."
    elif wr >= 0.50:
        rating = "Good (B)"
        assessment = "System performance meets professional standards."
    elif wr >= 0.40:
        rating = "Fair (C)"
        assessment = "System performance is acceptable but needs improvement."
    else:
        rating = "Needs Improvement (D)"
        assessment = "System requires significant optimization."

    lines.append("## 2. Performance Rating")
    lines.append("")
    lines.append(f"**Rating:** {rating}")
    lines.append("")
    lines.append(f"**Assessment:** {assessment}")
    lines.append("")

    # 3. 关键指标
    lines.append("## 3. Key Metrics")
    lines.append("")
    lines.append("### 3.1 Trading Statistics")
    lines.append("")
    lines.append(f"- Winning Trades: {metrics['winning_trades']} ({metrics['win_rate']*100:.1f}%)")
    lines.append(f"- Losing Trades: {metrics['losing_trades']}")
    lines.append(f"- Breakeven Trades: {metrics['breakeven_trades']}")
    lines.append(f"- Average Win: {metrics['avg_win']:+.2f}%")
    lines.append(f"- Average Loss: {metrics['avg_loss']:+.2f}%")
    lines.append(f"- Best Trade: {metrics['best_trade']:+.2f}%")
    lines.append(f"- Worst Trade: {metrics['worst_trade']:+.2f}%")
    lines.append("")

    lines.append("### 3.2 Risk Metrics")
    lines.append("")
    lines.append(f"- Maximum Drawdown: {metrics['max_drawdown_pct']*100:.2f}%")
    lines.append(f"- Drawdown Duration: {metrics['max_drawdown_duration_hours']:.1f} hours")
    lines.append(f"- Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    lines.append(f"- Sortino Ratio: {metrics['sortino_ratio']:.2f}")
    lines.append(f"- Calmar Ratio: {metrics['calmar_ratio']:.2f}")
    lines.append("")

    lines.append("### 3.3 Direction Analysis")
    lines.append("")
    lines.append(f"- Long Trades: {metrics['long_trades']} (Win Rate: {metrics['long_win_rate']*100:.1f}%)")
    lines.append(f"- Short Trades: {metrics['short_trades']} (Win Rate: {metrics['short_win_rate']*100:.1f}%)")
    lines.append("")

    # 4. 退出原因分析
    lines.append("## 4. Exit Reason Analysis")
    lines.append("")
    reasons = metrics['exit_reasons']
    total_exits = sum(reasons.values())
    if total_exits > 0:
        for reason, count in reasons.items():
            pct = count / total_exits * 100
            lines.append(f"- {reason.upper()}: {count} ({pct:.1f}%)")
    lines.append("")

    # 5. 月度收益
    if metrics.get('monthly_returns'):
        lines.append("## 5. Monthly Returns")
        lines.append("")
        lines.append("| Month | Return |")
        lines.append("|-------|--------|")
        for month, ret in sorted(metrics['monthly_returns'].items()):
            lines.append(f"| {month} | {ret:+.2f}% |")
        lines.append("")

    # 6. 结论和建议
    lines.append("## 6. Conclusions & Recommendations")
    lines.append("")

    # 基于指标给出建议
    recommendations = []

    if metrics['win_rate'] < 0.45:
        recommendations.append("- **Low Win Rate:** Consider tightening signal filters or adjusting entry criteria.")

    if metrics['max_drawdown_pct'] > 0.20:
        recommendations.append("- **High Drawdown:** Implement stricter position sizing or risk management rules.")

    if metrics['sharpe_ratio'] < 1.0:
        recommendations.append("- **Low Sharpe Ratio:** Focus on improving risk-adjusted returns through better trade selection.")

    if metrics['profit_factor'] < 1.5:
        recommendations.append("- **Low Profit Factor:** Optimize stop-loss and take-profit levels to improve win/loss ratio.")

    if metrics['avg_holding_hours'] > 6:
        recommendations.append("- **Long Holding Time:** Consider implementing tighter TTL or more aggressive profit-taking.")

    if not recommendations:
        recommendations.append("- System performance is within acceptable parameters. Continue monitoring and fine-tuning.")

    for rec in recommendations:
        lines.append(rec)

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*Report generated by v7.2 Backtest Verification System*")

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run v7.2 system backtest verification")
    parser.add_argument("--days", type=int, default=None, help="Number of days to backtest (default: all available)")
    parser.add_argument("--capital", type=float, default=10000, help="Initial capital in USDT (default: 10000)")
    parser.add_argument("--min-confidence", type=float, default=0, help="Minimum confidence filter (default: 0)")
    parser.add_argument("--no-save", action="store_true", help="Don't save results to file")

    args = parser.parse_args()

    # 确定时间范围
    end_time = datetime.now()
    start_time = None

    if args.days:
        start_time = end_time - timedelta(days=args.days)

    # 运行回测
    run_backtest_verification(
        start_time=start_time,
        end_time=end_time,
        initial_capital=args.capital,
        min_confidence=args.min_confidence,
        save_results=not args.no_save
    )
