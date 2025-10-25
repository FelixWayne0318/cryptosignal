# coding: utf-8
"""
回测性能指标计算

功能：
1. 计算标准绩效指标（胜率、盈亏比等）
2. 计算风险调整指标（夏普、索提诺等）
3. 计算回撤相关指标
4. 格式化输出报告
"""
import math
from typing import List, Dict
from datetime import datetime, timedelta


def calculate_metrics(trades: List, equity_curve: List[tuple], initial_capital: float) -> Dict:
    """
    计算完整的回测性能指标

    Args:
        trades: 交易列表（BacktestTrade对象）
        equity_curve: 权益曲线 [(timestamp, equity), ...]
        initial_capital: 初始资金

    Returns:
        性能指标字典
    """
    if not trades:
        return {
            'error': 'No trades to analyze',
            'total_trades': 0
        }

    # 基本统计
    total_trades = len(trades)
    winning_trades = [t for t in trades if t.pnl_percent and t.pnl_percent > 0]
    losing_trades = [t for t in trades if t.pnl_percent and t.pnl_percent < 0]
    breakeven_trades = [t for t in trades if t.pnl_percent and t.pnl_percent == 0]

    num_wins = len(winning_trades)
    num_losses = len(losing_trades)
    num_breakeven = len(breakeven_trades)

    win_rate = num_wins / total_trades if total_trades > 0 else 0

    # 盈亏统计
    total_pnl_pct = sum(t.pnl_percent for t in trades if t.pnl_percent)
    total_pnl_amount = sum(t.pnl_amount for t in trades if t.pnl_amount)

    avg_win = sum(t.pnl_percent for t in winning_trades) / num_wins if num_wins > 0 else 0
    avg_loss = sum(t.pnl_percent for t in losing_trades) / num_losses if num_losses > 0 else 0

    best_trade = max((t.pnl_percent for t in trades if t.pnl_percent), default=0)
    worst_trade = min((t.pnl_percent for t in trades if t.pnl_percent), default=0)

    # 盈亏比和利润因子
    profit_factor = abs(sum(t.pnl_percent for t in winning_trades) / sum(t.pnl_percent for t in losing_trades)) if num_losses > 0 else float('inf')

    # 持仓时间分析
    holding_times = []
    for t in trades:
        if t.exit_time:
            holding_hours = (t.exit_time - t.entry_time).total_seconds() / 3600
            holding_times.append(holding_hours)

    avg_holding_hours = sum(holding_times) / len(holding_times) if holding_times else 0

    # 分方向统计
    long_trades = [t for t in trades if t.side == 'long']
    short_trades = [t for t in trades if t.side == 'short']

    long_wins = len([t for t in long_trades if t.pnl_percent and t.pnl_percent > 0])
    short_wins = len([t for t in short_trades if t.pnl_percent and t.pnl_percent > 0])

    long_win_rate = long_wins / len(long_trades) if long_trades else 0
    short_win_rate = short_wins / len(short_trades) if short_trades else 0

    # 计算回撤
    max_drawdown_pct, max_drawdown_duration = _calculate_drawdown(equity_curve, initial_capital)

    # 计算夏普比率
    sharpe_ratio = _calculate_sharpe_ratio(trades, equity_curve)

    # 计算索提诺比率（只考虑下行波动）
    sortino_ratio = _calculate_sortino_ratio(trades, equity_curve)

    # 计算卡玛比率（收益/最大回撤）
    final_equity = equity_curve[-1][1] if equity_curve else initial_capital
    total_return = (final_equity - initial_capital) / initial_capital
    calmar_ratio = total_return / abs(max_drawdown_pct) if max_drawdown_pct != 0 else 0

    # 连胜连败分析
    win_streak, loss_streak = _calculate_streaks(trades)

    # 月度收益分析
    monthly_returns = _calculate_monthly_returns(equity_curve, initial_capital)

    # 分时段统计
    exit_reasons = {
        'tp1': len([t for t in trades if t.exit_reason == 'TP1']),
        'tp2': len([t for t in trades if t.exit_reason == 'TP2']),
        'sl': len([t for t in trades if t.exit_reason == 'SL']),
        'expired': len([t for t in trades if t.exit_reason == 'Expired']),
    }

    return {
        # 基本统计
        'total_trades': total_trades,
        'winning_trades': num_wins,
        'losing_trades': num_losses,
        'breakeven_trades': num_breakeven,
        'win_rate': win_rate,

        # 盈亏统计
        'total_pnl_pct': total_pnl_pct,
        'total_pnl_amount': total_pnl_amount,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'best_trade': best_trade,
        'worst_trade': worst_trade,
        'profit_factor': profit_factor,

        # 资金统计
        'initial_capital': initial_capital,
        'final_capital': final_equity,
        'total_return': total_return,

        # 持仓分析
        'avg_holding_hours': avg_holding_hours,

        # 方向分析
        'long_trades': len(long_trades),
        'short_trades': len(short_trades),
        'long_win_rate': long_win_rate,
        'short_win_rate': short_win_rate,

        # 风险指标
        'max_drawdown_pct': max_drawdown_pct,
        'max_drawdown_duration_hours': max_drawdown_duration,
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'calmar_ratio': calmar_ratio,

        # 连续性分析
        'max_win_streak': win_streak,
        'max_loss_streak': loss_streak,

        # 出场原因
        'exit_reasons': exit_reasons,

        # 月度收益
        'monthly_returns': monthly_returns,
    }


def _calculate_drawdown(equity_curve: List[tuple], initial_capital: float) -> tuple:
    """
    计算最大回撤

    Args:
        equity_curve: 权益曲线
        initial_capital: 初始资金

    Returns:
        (最大回撤百分比, 回撤持续时间小时数)
    """
    if not equity_curve:
        return 0, 0

    max_drawdown = 0
    max_drawdown_duration = 0
    peak_equity = initial_capital
    peak_time = None
    drawdown_start = None

    for timestamp, equity in equity_curve:
        if equity > peak_equity:
            peak_equity = equity
            peak_time = timestamp
            drawdown_start = None
        else:
            drawdown = (peak_equity - equity) / peak_equity
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                if drawdown_start is None:
                    drawdown_start = peak_time
                if drawdown_start:
                    duration = (timestamp - drawdown_start).total_seconds() / 3600
                    max_drawdown_duration = max(max_drawdown_duration, duration)

    return max_drawdown, max_drawdown_duration


def _calculate_sharpe_ratio(trades: List, equity_curve: List[tuple], risk_free_rate: float = 0.0) -> float:
    """
    计算夏普比率

    Args:
        trades: 交易列表
        equity_curve: 权益曲线
        risk_free_rate: 无风险利率（年化）

    Returns:
        夏普比率
    """
    if not trades or len(trades) < 2:
        return 0

    # 使用每笔交易的收益率计算
    returns = [t.pnl_percent / 100 for t in trades if t.pnl_percent is not None]

    if not returns:
        return 0

    avg_return = sum(returns) / len(returns)

    # 计算标准差
    variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
    std_dev = math.sqrt(variance)

    if std_dev == 0:
        return 0

    # 年化夏普比率（假设每天1笔交易）
    # 这里简化处理，实际应根据交易频率调整
    sharpe = (avg_return - risk_free_rate) / std_dev

    # 年化因子（假设每年250个交易日）
    # annualization_factor = math.sqrt(250)
    # sharpe_annualized = sharpe * annualization_factor

    return sharpe


def _calculate_sortino_ratio(trades: List, equity_curve: List[tuple], risk_free_rate: float = 0.0) -> float:
    """
    计算索提诺比率（只考虑下行波动）

    Args:
        trades: 交易列表
        equity_curve: 权益曲线
        risk_free_rate: 无风险利率

    Returns:
        索提诺比率
    """
    if not trades or len(trades) < 2:
        return 0

    returns = [t.pnl_percent / 100 for t in trades if t.pnl_percent is not None]

    if not returns:
        return 0

    avg_return = sum(returns) / len(returns)

    # 只计算负收益的标准差
    downside_returns = [r for r in returns if r < 0]

    if not downside_returns:
        return float('inf')  # 没有负收益，索提诺比率无穷大

    downside_variance = sum(r ** 2 for r in downside_returns) / len(downside_returns)
    downside_std = math.sqrt(downside_variance)

    if downside_std == 0:
        return 0

    sortino = (avg_return - risk_free_rate) / downside_std

    return sortino


def _calculate_streaks(trades: List) -> tuple:
    """
    计算最大连胜和连败次数

    Args:
        trades: 交易列表

    Returns:
        (最大连胜, 最大连败)
    """
    if not trades:
        return 0, 0

    max_win_streak = 0
    max_loss_streak = 0
    current_win_streak = 0
    current_loss_streak = 0

    for trade in trades:
        if trade.pnl_percent is None:
            continue

        if trade.pnl_percent > 0:
            current_win_streak += 1
            current_loss_streak = 0
            max_win_streak = max(max_win_streak, current_win_streak)
        elif trade.pnl_percent < 0:
            current_loss_streak += 1
            current_win_streak = 0
            max_loss_streak = max(max_loss_streak, current_loss_streak)
        else:
            current_win_streak = 0
            current_loss_streak = 0

    return max_win_streak, max_loss_streak


def _calculate_monthly_returns(equity_curve: List[tuple], initial_capital: float) -> Dict:
    """
    计算月度收益

    Args:
        equity_curve: 权益曲线
        initial_capital: 初始资金

    Returns:
        月度收益字典 {year-month: return_pct}
    """
    if not equity_curve:
        return {}

    monthly_equity = {}

    for timestamp, equity in equity_curve:
        month_key = timestamp.strftime('%Y-%m')
        monthly_equity[month_key] = equity

    # 计算每月收益率
    monthly_returns = {}
    prev_equity = initial_capital
    prev_month = None

    for month_key in sorted(monthly_equity.keys()):
        equity = monthly_equity[month_key]
        if prev_month is not None:
            return_pct = (equity - prev_equity) / prev_equity * 100
            monthly_returns[month_key] = return_pct
        prev_equity = equity
        prev_month = month_key

    return monthly_returns


def format_metrics_report(metrics: Dict) -> str:
    """
    格式化性能指标为可读报告

    Args:
        metrics: 性能指标字典

    Returns:
        格式化的文本报告
    """
    if 'error' in metrics:
        return f"⚠️  {metrics['error']}"

    lines = []
    lines.append("=" * 70)
    lines.append("  BACKTEST PERFORMANCE REPORT")
    lines.append("=" * 70)
    lines.append("")

    # 基本统计
    lines.append("📊 TRADING STATISTICS")
    lines.append(f"  Total Trades:          {metrics['total_trades']}")
    lines.append(f"  Winning Trades:        {metrics['winning_trades']} ({metrics['win_rate']*100:.1f}%)")
    lines.append(f"  Losing Trades:         {metrics['losing_trades']} ({(metrics['losing_trades']/metrics['total_trades']*100) if metrics['total_trades'] > 0 else 0:.1f}%)")
    lines.append(f"  Breakeven Trades:      {metrics['breakeven_trades']}")
    lines.append("")

    # 盈亏统计
    lines.append("💰 P&L STATISTICS")
    lines.append(f"  Total Return:          {metrics['total_return']*100:+.2f}%")
    lines.append(f"  Total PnL (Amount):    ${metrics['total_pnl_amount']:+.2f}")
    lines.append(f"  Average Win:           {metrics['avg_win']:+.2f}%")
    lines.append(f"  Average Loss:          {metrics['avg_loss']:+.2f}%")
    lines.append(f"  Best Trade:            {metrics['best_trade']:+.2f}%")
    lines.append(f"  Worst Trade:           {metrics['worst_trade']:+.2f}%")

    pf = metrics['profit_factor']
    pf_str = f"{pf:.2f}" if pf != float('inf') else "∞"
    lines.append(f"  Profit Factor:         {pf_str}")
    lines.append("")

    # 资金统计
    lines.append("💵 CAPITAL")
    lines.append(f"  Initial Capital:       ${metrics['initial_capital']:.2f}")
    lines.append(f"  Final Capital:         ${metrics['final_capital']:.2f}")
    lines.append(f"  Net Profit:            ${metrics['final_capital'] - metrics['initial_capital']:+.2f}")
    lines.append("")

    # 风险指标
    lines.append("📉 RISK METRICS")
    lines.append(f"  Max Drawdown:          {metrics['max_drawdown_pct']*100:.2f}%")
    lines.append(f"  Max DD Duration:       {metrics['max_drawdown_duration_hours']:.1f} hours")
    lines.append(f"  Sharpe Ratio:          {metrics['sharpe_ratio']:.2f}")
    lines.append(f"  Sortino Ratio:         {metrics['sortino_ratio']:.2f}")
    lines.append(f"  Calmar Ratio:          {metrics['calmar_ratio']:.2f}")
    lines.append("")

    # 持仓分析
    lines.append("⏱️  POSITION BEHAVIOR")
    lines.append(f"  Avg Holding Time:      {metrics['avg_holding_hours']:.1f} hours")
    lines.append(f"  Max Win Streak:        {metrics['max_win_streak']}")
    lines.append(f"  Max Loss Streak:       {metrics['max_loss_streak']}")
    lines.append("")

    # 方向分析
    lines.append("📈 DIRECTION ANALYSIS")
    lines.append(f"  Long Trades:           {metrics['long_trades']} (Win Rate: {metrics['long_win_rate']*100:.1f}%)")
    lines.append(f"  Short Trades:          {metrics['short_trades']} (Win Rate: {metrics['short_win_rate']*100:.1f}%)")
    lines.append("")

    # 出场原因
    lines.append("🎯 EXIT REASONS")
    reasons = metrics['exit_reasons']
    lines.append(f"  Take Profit 1:         {reasons['tp1']}")
    lines.append(f"  Take Profit 2:         {reasons['tp2']}")
    lines.append(f"  Stop Loss:             {reasons['sl']}")
    lines.append(f"  Expired (TTL):         {reasons['expired']}")
    lines.append("")

    # 月度收益
    if metrics['monthly_returns']:
        lines.append("📅 MONTHLY RETURNS")
        for month, ret in sorted(metrics['monthly_returns'].items()):
            lines.append(f"  {month}:                {ret:+.2f}%")
        lines.append("")

    # 评级
    lines.append("⭐ PERFORMANCE RATING")
    wr = metrics['win_rate']
    if wr >= 0.60:
        rating = "Excellent"
        emoji = "🎉"
    elif wr >= 0.50:
        rating = "Good"
        emoji = "✅"
    elif wr >= 0.40:
        rating = "Fair"
        emoji = "⚠️"
    else:
        rating = "Needs Improvement"
        emoji = "❌"

    lines.append(f"  {emoji} {rating} (Win Rate: {wr*100:.1f}%)")
    lines.append("")

    lines.append("=" * 70)

    return "\n".join(lines)
