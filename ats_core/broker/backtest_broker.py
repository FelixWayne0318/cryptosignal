# coding: utf-8
"""
Backtest Broker - 回测模拟执行

职责：
- 复用PaperBroker的执行逻辑
- 支持历史数据回放
- 批量运行和结果收集

与PaperBroker的关系：
- 共享相同的执行契约（订单成交、SL/TP监控、滑点/手续费）
- BacktestBroker = PaperBroker + 历史数据驱动

Version: v1.0.0
Standard: SYSTEM_ENHANCEMENT_STANDARD.md v3.3.0
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ats_core.broker.base import (
    Broker,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    AccountState,
    ExitReason,
)
from ats_core.broker.paper_broker import PaperBroker

logger = logging.getLogger(__name__)


class BacktestBroker(PaperBroker):
    """
    回测Broker

    继承PaperBroker，添加历史数据回放功能
    配置从config/params.json的backtest.engine读取
    """

    def __init__(self, config: Dict[str, Any], initial_equity: float = 100000.0):
        """
        初始化BacktestBroker

        Args:
            config: 回测执行配置（backtest.engine）
            initial_equity: 初始权益（USDT）
        """
        # 转换配置格式以匹配PaperBroker
        execution_config = {
            "taker_fee_rate": config.get("taker_fee_rate", 0.0005),
            "slippage_bps": config.get("slippage_bps", 2),
            "max_entry_minutes": config.get("max_entry_bars", 4) * 60,  # bars to minutes
            "max_holding_minutes": config.get("max_holding_bars", 48) * 60,  # bars to minutes
        }

        super().__init__(execution_config, initial_equity)

        # 回测特有配置
        self.max_entry_bars = config.get("max_entry_bars", 4)
        self.max_holding_bars = config.get("max_holding_bars", 48)

        # 统计信息
        self.total_signals = 0
        self.filled_signals = 0
        self.rejected_signals = 0

        logger.info(
            f"BacktestBroker初始化: "
            f"equity={initial_equity}, "
            f"max_entry_bars={self.max_entry_bars}, "
            f"max_holding_bars={self.max_holding_bars}"
        )

    def run_backtest(
        self,
        klines_by_symbol: Dict[str, List[Dict[str, Any]]],
        signals: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        运行回测

        Args:
            klines_by_symbol: K线数据 {symbol: [klines]}
            signals: 信号列表 [{timestamp, symbol, side, entry, sl, tp, ...}]

        Returns:
            回测结果
        """
        logger.info(f"开始回测: {len(signals)}个信号")

        # 按时间排序信号
        sorted_signals = sorted(signals, key=lambda s: s["timestamp"])

        # 构建时间线（所有K线时间点）
        all_timestamps = set()
        for symbol, klines in klines_by_symbol.items():
            for kline in klines:
                all_timestamps.add(kline["close_time"])

        timeline = sorted(all_timestamps)

        # 信号队列（按timestamp索引）
        signal_queue = {}
        for sig in sorted_signals:
            ts = sig["timestamp"]
            if ts not in signal_queue:
                signal_queue[ts] = []
            signal_queue[ts].append(sig)

        # 价格缓存（用于时间循环）
        price_cache: Dict[str, Dict[int, float]] = {}
        for symbol, klines in klines_by_symbol.items():
            price_cache[symbol] = {}
            for kline in klines:
                price_cache[symbol][kline["close_time"]] = kline["close"]

        # 时间循环
        for ts in timeline:
            # 1. 处理该时间点的信号
            if ts in signal_queue:
                for sig in signal_queue[ts]:
                    self._process_signal(sig, ts)

            # 2. 更新价格
            for symbol, prices in price_cache.items():
                if ts in prices:
                    self.on_price_update(symbol, prices[ts], ts)

            # 3. 更新时间（检查过期）
            self.on_time(ts)

        # 收集结果
        account = self.get_account_state()

        return {
            "initial_equity": self.initial_equity,
            "final_equity": account.equity,
            "total_pnl": account.realized_pnl,
            "total_fees": account.fees_paid,
            "total_signals": self.total_signals,
            "filled_signals": self.filled_signals,
            "rejected_signals": self.rejected_signals,
            "closed_positions": [p.to_dict() for p in account.closed_positions],
            "open_positions": [p.to_dict() for p in account.open_positions],
        }

    def _process_signal(self, signal: Dict[str, Any], timestamp: int) -> None:
        """
        处理信号

        Args:
            signal: 信号数据
            timestamp: 当前时间戳
        """
        self.total_signals += 1

        symbol = signal["symbol"]
        side = signal["side"]
        entry_price = signal.get("entry_price", 0)
        stop_loss = signal.get("stop_loss", 0)
        take_profit = signal.get("take_profit", 0)

        # 验证价格
        if not entry_price or not stop_loss or not take_profit:
            self.rejected_signals += 1
            logger.warning(f"信号价格无效: {symbol}")
            return

        # 计算数量（简化：固定100 USDT仓位）
        notional = 100.0
        quantity = notional / entry_price

        # 创建订单
        import uuid
        order_id = str(uuid.uuid4())[:8]

        # 入场过期时间（max_entry_bars后）
        expire_at = timestamp + (self.max_entry_bars * 3600 * 1000)

        order = Order(
            id=order_id,
            symbol=symbol,
            side=OrderSide.BUY if side.lower() == "long" else OrderSide.SELL,
            type=OrderType.LIMIT,
            price=entry_price,
            quantity=quantity,
            created_at=timestamp,
            expire_at=expire_at,
            tag="ENTRY",
            metadata={
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "step1_result": signal.get("step1_result", {}),
                "step2_result": signal.get("step2_result", {}),
                "step3_result": signal.get("step3_result", {}),
                "step4_result": signal.get("step4_result", {}),
                "factor_scores": signal.get("factor_scores", {}),
            }
        )

        self.submit_order(order)
        self.filled_signals += 1

        logger.debug(
            f"信号处理: {symbol} {side} "
            f"entry={entry_price:.2f} sl={stop_loss:.2f} tp={take_profit:.2f}"
        )

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        获取性能指标

        Returns:
            性能指标字典
        """
        account = self.get_account_state()
        closed = account.closed_positions

        if not closed:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "avg_pnl_pct": 0,
                "total_pnl": 0,
                "max_drawdown": 0,
            }

        # 计算指标
        wins = len([p for p in closed if p.realized_pnl and p.realized_pnl > 0])
        losses = len([p for p in closed if p.realized_pnl and p.realized_pnl <= 0])
        total = wins + losses

        pnl_list = [p.realized_pnl_pct for p in closed if p.realized_pnl_pct is not None]
        avg_pnl = sum(pnl_list) / len(pnl_list) if pnl_list else 0

        # 计算回撤
        equity_curve = [self.initial_equity]
        for p in closed:
            if p.realized_pnl:
                equity_curve.append(equity_curve[-1] + p.realized_pnl)

        peak = equity_curve[0]
        max_dd = 0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100
            if dd > max_dd:
                max_dd = dd

        return {
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": wins / total if total > 0 else 0,
            "avg_pnl_pct": avg_pnl,
            "total_pnl": account.realized_pnl,
            "max_drawdown": max_dd,
            "sharpe_ratio": 0,  # TODO: 实现
        }
