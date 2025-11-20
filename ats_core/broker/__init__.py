# coding: utf-8
"""
Broker Module - 统一的订单和持仓管理

支持三种模式：
- PaperBroker: Paper Trading模拟执行
- BacktestBroker: 回测模拟执行（未来迁入）
- LiveBroker: 实盘执行（未来实现）

Version: v1.0.0
Standard: SYSTEM_ENHANCEMENT_STANDARD.md v3.3.0
"""

from ats_core.broker.base import (
    OrderSide,
    OrderType,
    OrderStatus,
    ExitReason,
    Order,
    Position,
    AccountState,
    Broker,
)
from ats_core.broker.paper_broker import PaperBroker
from ats_core.broker.backtest_broker import BacktestBroker

__all__ = [
    "OrderSide",
    "OrderType",
    "OrderStatus",
    "ExitReason",
    "Order",
    "Position",
    "AccountState",
    "Broker",
    "PaperBroker",
    "BacktestBroker",
]

__version__ = "1.0.0"
