# coding: utf-8
"""
回测引擎核心

实现完整的回测逻辑：
- 历史信号生成
- 交易开平仓管理
- 止盈止损检查
- 权益曲线跟踪
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class BacktestTrade:
    """
    回测交易记录

    表示一个完整的交易，从开仓到平仓
    """
    # 基本信息
    symbol: str
    side: str  # 'long' or 'short'

    # 开仓信息
    entry_time: datetime
    entry_price: float

    # 给价计划
    stop_loss: float
    take_profit_1: Optional[float] = None
    take_profit_2: Optional[float] = None

    # 信号质量
    probability: float = 0.5
    scores: Dict[str, int] = field(default_factory=dict)

    # 平仓信息
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None  # 'tp1', 'tp2', 'sl', 'expired', 'force_close'

    # 盈亏
    pnl_percent: Optional[float] = None
    pnl_usdt: Optional[float] = None

    # 持仓时长
    holding_hours: Optional[float] = None

    @property
    def is_open(self) -> bool:
        """是否未平仓"""
        return self.exit_time is None

    @property
    def is_win(self) -> bool:
        """是否盈利"""
        return self.pnl_percent is not None and self.pnl_percent > 0

    def calculate_pnl(self, exit_price: float) -> float:
        """
        计算盈亏百分比

        Args:
            exit_price: 退出价格

        Returns:
            盈亏百分比
        """
        if self.side == 'long':
            return (exit_price - self.entry_price) / self.entry_price * 100
        else:  # short
            return (self.entry_price - exit_price) / self.entry_price * 100

    def close(self, exit_time: datetime, exit_price: float, reason: str, position_value: float = 100):
        """
        平仓

        Args:
            exit_time: 平仓时间
            exit_price: 平仓价格
            reason: 平仓原因
            position_value: 仓位价值（USDT）
        """
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.exit_reason = reason

        # 计算盈亏
        self.pnl_percent = self.calculate_pnl(exit_price)
        self.pnl_usdt = position_value * self.pnl_percent / 100

        # 计算持仓时长
        self.holding_hours = (exit_time - self.entry_time).total_seconds() / 3600


class BacktestEngine:
    """
    回测引擎

    核心功能：
    1. 逐K线遍历历史数据
    2. 生成历史信号（需要历史数据）
    3. 管理交易开平仓
    4. 跟踪权益曲线
    """

    def __init__(
        self,
        start_time: datetime,
        end_time: datetime,
        initial_capital: float = 10000,
        position_size_pct: float = 0.02,  # 每次2%仓位
        max_open_trades: int = 5,
        ttl_hours: int = 8,
        commission_rate: float = 0.0004  # 币安手续费0.04%
    ):
        """
        初始化回测引擎

        Args:
            start_time: 回测开始时间
            end_time: 回测结束时间
            initial_capital: 初始资金（USDT）
            position_size_pct: 每次开仓占资金百分比
            max_open_trades: 最大持仓数
            ttl_hours: 信号有效期（小时）
            commission_rate: 手续费率
        """
        self.start_time = start_time
        self.end_time = end_time
        self.initial_capital = initial_capital
        self.position_size_pct = position_size_pct
        self.max_open_trades = max_open_trades
        self.ttl_hours = ttl_hours
        self.commission_rate = commission_rate

        # 交易记录
        self.trades: List[BacktestTrade] = []

        # 权益跟踪
        self.current_capital = initial_capital
        self.equity_curve: List[Dict] = []

        # 统计
        self.total_signals = 0
        self.signals_taken = 0
        self.signals_skipped = 0

    def run_from_signals(self, signals: List[Dict], price_data: Dict[str, List]) -> Dict:
        """
        从已有信号列表运行回测

        这是最简单的回测方式：
        1. 使用数据库中记录的历史信号
        2. 模拟开平仓和盈亏

        Args:
            signals: 信号列表，每个信号包含symbol, timestamp, side, entry_price, sl, tp等
            price_data: 价格数据字典 {symbol: [(timestamp, open, high, low, close), ...]}

        Returns:
            回测结果字典
        """
        print(f"🚀 Starting backtest from signals")
        print(f"   Period: {self.start_time} to {self.end_time}")
        print(f"   Total signals: {len(signals)}")
        print(f"   Initial capital: ${self.initial_capital:,.0f}")
        print()

        # 按时间排序信号
        sorted_signals = sorted(signals, key=lambda s: s.get('timestamp', s.get('entry_time', datetime.min)))

        # 处理每个信号
        for signal in sorted_signals:
            self.total_signals += 1

            # 检查是否在回测时间范围内
            signal_time = signal.get('timestamp', signal.get('entry_time'))
            if signal_time < self.start_time or signal_time > self.end_time:
                continue

            # 检查是否达到最大持仓
            open_count = sum(1 for t in self.trades if t.is_open)
            if open_count >= self.max_open_trades:
                self.signals_skipped += 1
                continue

            # 开仓
            self._open_trade_from_signal(signal, price_data)

            # 检查所有持仓（使用该信号之后的价格数据）
            self._check_open_trades(signal_time, price_data)

        # 强制平仓所有未平仓交易
        self._close_all_trades(self.end_time, price_data, reason='backtest_end')

        # 计算最终指标
        return self._generate_results()

    def _open_trade_from_signal(self, signal: Dict, price_data: Dict[str, List]):
        """
        根据信号开仓

        Args:
            signal: 信号字典
            price_data: 价格数据字典
        """
        symbol = signal.get('symbol')
        entry_time = signal.get('timestamp', signal.get('entry_time'))

        # 获取入场价格
        entry_price = signal.get('entry_price', signal.get('current_price'))

        # 如果没有entry_price，从价格数据中获取
        if entry_price is None and symbol in price_data:
            # 找到信号时间点最近的K线
            symbol_prices = price_data[symbol]
            for price_bar in symbol_prices:
                bar_time = price_bar[0] if isinstance(price_bar[0], datetime) else datetime.fromtimestamp(price_bar[0] / 1000)
                # 使用信号时间点之后第一根K线的收盘价
                if bar_time >= entry_time:
                    entry_price = price_bar[4]  # close price
                    break

        # 如果还是没有价格，跳过这个信号
        if entry_price is None:
            print(f"⚠️  Skipping {symbol}: No entry price available")
            self.signals_skipped += 1
            return

        # 计算仓位大小
        position_value = self.current_capital * self.position_size_pct

        # 扣除手续费
        commission = position_value * self.commission_rate

        # 创建交易
        trade = BacktestTrade(
            symbol=symbol,
            side=signal.get('side'),
            entry_time=entry_time,
            entry_price=entry_price,
            stop_loss=signal.get('stop_loss', signal.get('sl')),
            take_profit_1=signal.get('take_profit_1', signal.get('tp1')),
            take_profit_2=signal.get('take_profit_2', signal.get('tp2')),
            probability=signal.get('probability', 0.5),
            scores=signal.get('scores', {})
        )

        self.trades.append(trade)
        self.signals_taken += 1

        # 记录权益点
        self._record_equity_point(trade.entry_time, position_value, commission)

        # 安全打印（处理None值）
        sl_str = f"{trade.stop_loss:.4f}" if trade.stop_loss else "N/A"
        tp_str = f"{(trade.take_profit_2 or trade.take_profit_1):.4f}" if (trade.take_profit_2 or trade.take_profit_1) else "N/A"

        print(f"📊 Open: {trade.symbol} {trade.side.upper()} @ {trade.entry_price:.4f} "
              f"(Prob: {trade.probability:.1%}, SL: {sl_str}, TP: {tp_str})")

    def _check_open_trades(self, current_time: datetime, price_data: Dict[str, List]):
        """
        检查并更新所有持仓

        Args:
            current_time: 当前时间
            price_data: 价格数据
        """
        for trade in self.trades:
            if not trade.is_open:
                continue

            # 获取该币种的价格数据
            symbol_prices = price_data.get(trade.symbol, [])
            if not symbol_prices:
                continue

            # 找到当前时间点之后的价格K线
            for price_bar in symbol_prices:
                bar_time = price_bar[0] if isinstance(price_bar[0], datetime) else datetime.fromtimestamp(price_bar[0] / 1000)

                # 只看开仓之后的K线
                if bar_time <= trade.entry_time:
                    continue

                # 只看当前时间之后一小段时间内的K线（比如接下来的ttl_hours）
                if bar_time > current_time + timedelta(hours=self.ttl_hours):
                    break

                # 获取OHLC
                _, open_price, high, low, close = price_bar[:5]

                # 检查止盈止损
                exit_price = None
                exit_reason = None

                if trade.side == 'long':
                    # 做多：检查止盈和止损
                    if trade.take_profit_2 and high >= trade.take_profit_2:
                        exit_price = trade.take_profit_2
                        exit_reason = 'tp2'
                    elif trade.take_profit_1 and high >= trade.take_profit_1:
                        exit_price = trade.take_profit_1
                        exit_reason = 'tp1'
                    elif trade.stop_loss and low <= trade.stop_loss:
                        exit_price = trade.stop_loss
                        exit_reason = 'sl'
                else:  # short
                    # 做空：检查止盈和止损
                    if trade.take_profit_2 and low <= trade.take_profit_2:
                        exit_price = trade.take_profit_2
                        exit_reason = 'tp2'
                    elif trade.take_profit_1 and low <= trade.take_profit_1:
                        exit_price = trade.take_profit_1
                        exit_reason = 'tp1'
                    elif trade.stop_loss and high >= trade.stop_loss:
                        exit_price = trade.stop_loss
                        exit_reason = 'sl'

                if exit_price:
                    # 平仓
                    position_value = self.initial_capital * self.position_size_pct
                    trade.close(bar_time, exit_price, exit_reason, position_value)

                    # 更新资金
                    commission = position_value * self.commission_rate
                    self.current_capital += trade.pnl_usdt - commission * 2  # 开仓+平仓手续费

                    emoji = "✅" if trade.is_win else "❌"
                    print(f"{emoji} Close: {trade.symbol} {trade.exit_reason.upper()} @ {exit_price:.4f}, "
                          f"PnL: {trade.pnl_percent:+.2f}% (${trade.pnl_usdt:+.2f})")

                    self._record_equity_point(bar_time, position_value, commission * 2)
                    break

            # 检查是否过期
            if trade.is_open and (current_time - trade.entry_time).total_seconds() / 3600 >= self.ttl_hours:
                # 使用最新价格平仓
                latest_price = self._get_latest_price(trade.symbol, current_time, price_data)
                if latest_price:
                    position_value = self.initial_capital * self.position_size_pct
                    trade.close(current_time, latest_price, 'expired', position_value)

                    commission = position_value * self.commission_rate
                    self.current_capital += trade.pnl_usdt - commission * 2

                    print(f"⏰ Expired: {trade.symbol} @ {latest_price:.4f}, PnL: {trade.pnl_percent:+.2f}%")

    def _close_all_trades(self, exit_time: datetime, price_data: Dict[str, List], reason: str):
        """
        强制平仓所有交易

        Args:
            exit_time: 平仓时间
            price_data: 价格数据
            reason: 平仓原因
        """
        for trade in self.trades:
            if trade.is_open:
                # 获取最新价格
                latest_price = self._get_latest_price(trade.symbol, exit_time, price_data)
                if latest_price:
                    position_value = self.initial_capital * self.position_size_pct
                    trade.close(exit_time, latest_price, reason, position_value)

                    commission = position_value * self.commission_rate
                    self.current_capital += trade.pnl_usdt - commission * 2

    def _get_latest_price(self, symbol: str, time: datetime, price_data: Dict[str, List]) -> Optional[float]:
        """
        获取指定时间点的最新价格

        Args:
            symbol: 币种
            time: 时间点
            price_data: 价格数据

        Returns:
            价格（close）
        """
        symbol_prices = price_data.get(symbol, [])

        # 找到时间点之前的最新K线
        latest_bar = None
        for bar in symbol_prices:
            bar_time = bar[0] if isinstance(bar[0], datetime) else datetime.fromtimestamp(bar[0] / 1000)
            if bar_time <= time:
                latest_bar = bar
            else:
                break

        if latest_bar:
            return float(latest_bar[4])  # close price
        return None

    def _record_equity_point(self, time: datetime, position_value: float, commission: float):
        """
        记录权益点

        Args:
            time: 时间
            position_value: 仓位价值
            commission: 手续费
        """
        open_count = sum(1 for t in self.trades if t.is_open)

        self.equity_curve.append({
            'time': time,
            'equity': self.current_capital,
            'open_trades': open_count,
            'position_value': position_value,
            'commission': commission
        })

    def _generate_results(self) -> Dict:
        """
        生成回测结果

        Returns:
            结果字典
        """
        closed_trades = [t for t in self.trades if not t.is_open]

        if not closed_trades:
            return {
                'error': 'No trades executed',
                'total_signals': self.total_signals,
                'signals_taken': self.signals_taken,
                'signals_skipped': self.signals_skipped
            }

        wins = [t for t in closed_trades if t.is_win]
        losses = [t for t in closed_trades if not t.is_win]

        total_pnl = sum(t.pnl_usdt for t in closed_trades if t.pnl_usdt)
        total_pnl_pct = (self.current_capital - self.initial_capital) / self.initial_capital * 100

        return {
            'summary': {
                'initial_capital': self.initial_capital,
                'final_capital': self.current_capital,
                'total_pnl': total_pnl,
                'total_pnl_pct': total_pnl_pct,

                'total_signals': self.total_signals,
                'signals_taken': self.signals_taken,
                'signals_skipped': self.signals_skipped,

                'total_trades': len(closed_trades),
                'winning_trades': len(wins),
                'losing_trades': len(losses),
                'win_rate': len(wins) / len(closed_trades) if closed_trades else 0,

                'avg_win_pct': sum(t.pnl_percent for t in wins) / len(wins) if wins else 0,
                'avg_loss_pct': sum(t.pnl_percent for t in losses) / len(losses) if losses else 0,
                'avg_win_usdt': sum(t.pnl_usdt for t in wins) / len(wins) if wins else 0,
                'avg_loss_usdt': sum(t.pnl_usdt for t in losses) / len(losses) if losses else 0,

                'profit_factor': abs(sum(t.pnl_usdt for t in wins) / sum(t.pnl_usdt for t in losses)) if losses and sum(t.pnl_usdt for t in losses) != 0 else float('inf'),

                'max_win': max(t.pnl_percent for t in wins) if wins else 0,
                'max_loss': min(t.pnl_percent for t in losses) if losses else 0,

                'avg_holding_hours': sum(t.holding_hours for t in closed_trades if t.holding_hours) / len([t for t in closed_trades if t.holding_hours]) if closed_trades else 0,

                'max_drawdown': self._calculate_max_drawdown(),
            },
            'trades': [
                {
                    'symbol': t.symbol,
                    'side': t.side,
                    'entry_time': t.entry_time.isoformat() if t.entry_time else None,
                    'entry_price': t.entry_price,
                    'exit_time': t.exit_time.isoformat() if t.exit_time else None,
                    'exit_price': t.exit_price,
                    'exit_reason': t.exit_reason,
                    'pnl_percent': t.pnl_percent,
                    'pnl_usdt': t.pnl_usdt,
                    'holding_hours': t.holding_hours,
                    'probability': t.probability,
                }
                for t in closed_trades
            ],
            'equity_curve': self.equity_curve
        }

    def _calculate_max_drawdown(self) -> float:
        """
        计算最大回撤

        Returns:
            最大回撤百分比
        """
        if not self.equity_curve:
            return 0.0

        peak = self.initial_capital
        max_dd = 0.0

        for point in self.equity_curve:
            equity = point['equity']
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak * 100
            if dd > max_dd:
                max_dd = dd

        return max_dd
