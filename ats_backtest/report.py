# coding: utf-8
"""
回测报告生成器

功能：
1. 生成详细的回测报告
2. 导出交易列表
3. 保存报告到文件
4. 生成JSON格式数据
"""
import json
from typing import List, Dict
from datetime import datetime
from pathlib import Path


def generate_report(
    trades: List,
    metrics: Dict,
    config: Dict = None,
    include_trades: bool = True
) -> Dict:
    """
    生成完整的回测报告

    Args:
        trades: 交易列表
        metrics: 性能指标
        config: 回测配置（可选）
        include_trades: 是否包含交易明细

    Returns:
        报告字典
    """
    report = {
        'generated_at': datetime.utcnow().isoformat(),
        'backtest_config': config or {},
        'summary': metrics,
    }

    if include_trades:
        report['trades'] = _format_trades_for_export(trades)

    return report


def _format_trades_for_export(trades: List) -> List[Dict]:
    """
    格式化交易列表为可导出格式

    Args:
        trades: BacktestTrade对象列表

    Returns:
        交易字典列表
    """
    formatted_trades = []

    for trade in trades:
        formatted_trades.append({
            'symbol': trade.symbol,
            'side': trade.side,
            'entry_time': trade.entry_time.isoformat() if trade.entry_time else None,
            'entry_price': trade.entry_price,
            'exit_time': trade.exit_time.isoformat() if trade.exit_time else None,
            'exit_price': trade.exit_price,
            'exit_reason': trade.exit_reason,
            'stop_loss': trade.stop_loss,
            'take_profit_1': trade.take_profit_1,
            'take_profit_2': trade.take_profit_2,
            'position_size': trade.position_size,
            'pnl_percent': trade.pnl_percent,
            'pnl_amount': trade.pnl_amount,
            'signal_probability': trade.signal_probability,
            'signal_scores': trade.signal_scores,
        })

    return formatted_trades


def save_report(
    report: Dict,
    output_dir: str = None,
    filename: str = None
) -> str:
    """
    保存报告到文件

    Args:
        report: 报告字典
        output_dir: 输出目录（默认：data/backtest/reports）
        filename: 文件名（默认：backtest_YYYYMMDD_HHMMSS.json）

    Returns:
        保存的文件路径
    """
    # 确定输出目录
    if output_dir is None:
        project_root = Path(__file__).parent.parent
        output_dir = project_root / "data" / "backtest" / "reports"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # 确定文件名
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"backtest_{timestamp}.json"

    filepath = output_dir / filename

    # 保存JSON
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return str(filepath)


def print_trade_list(trades: List, limit: int = None):
    """
    打印交易列表

    Args:
        trades: 交易列表
        limit: 显示数量限制（默认全部）
    """
    if not trades:
        print("\n⚠️  No trades to display\n")
        return

    display_trades = trades[:limit] if limit else trades

    print()
    print("=" * 120)
    print("  TRADE LIST")
    print("=" * 120)
    print()

    # 表头
    header = (
        f"{'#':<4} {'Symbol':<12} {'Side':<6} {'Entry Time':<17} "
        f"{'Entry':<10} {'Exit':<10} {'Exit Reason':<12} {'PnL%':<8} {'Prob':<6}"
    )
    print(header)
    print("-" * 120)

    # 交易行
    for i, trade in enumerate(display_trades, 1):
        entry_time_str = trade.entry_time.strftime('%Y-%m-%d %H:%M') if trade.entry_time else '-'
        entry_price_str = f"{trade.entry_price:.4f}" if trade.entry_price else '-'
        exit_price_str = f"{trade.exit_price:.4f}" if trade.exit_price else '-'
        exit_reason_str = trade.exit_reason or '-'
        pnl_str = f"{trade.pnl_percent:+.2f}%" if trade.pnl_percent is not None else '-'
        prob_str = f"{trade.signal_probability*100:.0f}%" if trade.signal_probability else '-'

        # 颜色标记
        if trade.pnl_percent is not None:
            if trade.pnl_percent > 0:
                pnl_emoji = "✅"
            elif trade.pnl_percent < 0:
                pnl_emoji = "❌"
            else:
                pnl_emoji = "⚪"
        else:
            pnl_emoji = "🔵"

        side_emoji = "🟩" if trade.side == 'long' else "🟥"

        row = (
            f"{i:<4} {trade.symbol:<12} {side_emoji}{trade.side:<6} {entry_time_str:<17} "
            f"{entry_price_str:<10} {exit_price_str:<10} {exit_reason_str:<12} {pnl_emoji}{pnl_str:<8} {prob_str:<6}"
        )
        print(row)

    if limit and len(trades) > limit:
        print()
        print(f"... and {len(trades) - limit} more trades")

    print()
    print("=" * 120)
    print()


def print_equity_curve(equity_curve: List[tuple], sample_points: int = 20):
    """
    打印简化的权益曲线

    Args:
        equity_curve: 权益曲线 [(timestamp, equity), ...]
        sample_points: 采样点数量
    """
    if not equity_curve:
        print("\n⚠️  No equity curve data\n")
        return

    print()
    print("=" * 70)
    print("  EQUITY CURVE")
    print("=" * 70)
    print()

    # 采样
    if len(equity_curve) > sample_points:
        step = len(equity_curve) // sample_points
        sampled = equity_curve[::step]
    else:
        sampled = equity_curve

    # 打印
    print(f"{'Time':<20} {'Equity':<15} {'Change%':<10}")
    print("-" * 70)

    # 获取初始equity（支持dict和tuple格式）
    first_point = sampled[0]
    if isinstance(first_point, dict):
        prev_equity = first_point['equity']
    else:
        prev_equity = first_point[1]

    for point in sampled:
        # 支持dict格式（引擎输出）和tuple格式
        if isinstance(point, dict):
            timestamp = point['time']
            equity = point['equity']
        else:
            timestamp, equity = point

        time_str = timestamp.strftime('%Y-%m-%d %H:%M')
        equity_str = f"${equity:.2f}"
        change_pct = (equity - prev_equity) / prev_equity * 100 if prev_equity > 0 else 0
        change_str = f"{change_pct:+.2f}%" if change_pct != 0 else "-"

        print(f"{time_str:<20} {equity_str:<15} {change_str:<10}")
        prev_equity = equity

    print()
    print("=" * 70)
    print()


def generate_summary_text(metrics: Dict) -> str:
    """
    生成简短的摘要文本

    Args:
        metrics: 性能指标

    Returns:
        摘要文本
    """
    if 'error' in metrics:
        return f"⚠️  {metrics['error']}"

    lines = []
    lines.append("📊 BACKTEST SUMMARY")
    lines.append("")
    lines.append(f"Trades: {metrics['total_trades']} | Win Rate: {metrics['win_rate']*100:.1f}%")
    lines.append(f"Total Return: {metrics['total_return']*100:+.2f}% | Max DD: {metrics['max_drawdown_pct']*100:.2f}%")
    lines.append(f"Profit Factor: {metrics['profit_factor']:.2f} | Sharpe: {metrics['sharpe_ratio']:.2f}")
    lines.append(f"Final Capital: ${metrics['final_capital']:.2f}")

    return "\n".join(lines)


def export_trades_csv(trades: List, filepath: str):
    """
    导出交易列表为CSV

    Args:
        trades: 交易列表
        filepath: 输出文件路径
    """
    import csv

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # 写入表头
        writer.writerow([
            'Symbol', 'Side', 'Entry Time', 'Entry Price',
            'Exit Time', 'Exit Price', 'Exit Reason',
            'Stop Loss', 'Take Profit 1', 'Take Profit 2',
            'Position Size', 'PnL %', 'PnL Amount',
            'Signal Probability', 'Signal Scores'
        ])

        # 写入数据
        for trade in trades:
            writer.writerow([
                trade.symbol,
                trade.side,
                trade.entry_time.isoformat() if trade.entry_time else '',
                trade.entry_price or '',
                trade.exit_time.isoformat() if trade.exit_time else '',
                trade.exit_price or '',
                trade.exit_reason or '',
                trade.stop_loss or '',
                trade.take_profit_1 or '',
                trade.take_profit_2 or '',
                trade.position_size or '',
                trade.pnl_percent or '',
                trade.pnl_amount or '',
                trade.signal_probability or '',
                json.dumps(trade.signal_scores) if trade.signal_scores else ''
            ])

    print(f"✅ Trades exported to: {filepath}")


def print_full_report(trades: List, metrics: Dict, equity_curve: List[tuple] = None):
    """
    打印完整报告（包括所有部分）

    Args:
        trades: 交易列表
        metrics: 性能指标
        equity_curve: 权益曲线（可选）
    """
    from .metrics import format_metrics_report

    # 打印性能报告
    print(format_metrics_report(metrics))

    # 打印权益曲线
    if equity_curve:
        print_equity_curve(equity_curve)

    # 打印交易列表（最近20笔）
    print_trade_list(trades, limit=20)
