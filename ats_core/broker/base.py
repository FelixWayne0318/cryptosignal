# coding: utf-8
"""
Broker Base Module - 基础类型定义和Broker接口

定义：
- 枚举类型：OrderSide, OrderType, OrderStatus, ExitReason
- 数据结构：Order, Position, AccountState
- 抽象接口：Broker

设计原则：
- 三种模式（Backtest/Paper/Live）共用相同数据结构
- 执行契约明确且可复现
- 支持MFE/MAE跟踪用于策略优化

Version: v1.0.0
Standard: SYSTEM_ENHANCEMENT_STANDARD.md v3.3.0
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ==================== 枚举类型 ====================

class OrderSide(str, Enum):
    """订单方向"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """订单类型"""
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class OrderStatus(str, Enum):
    """订单状态"""
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"


class ExitReason(str, Enum):
    """退出原因"""
    TAKE_PROFIT = "TAKE_PROFIT"
    STOP_LOSS = "STOP_LOSS"
    TIME_EXIT = "TIME_EXIT"
    MANUAL_EXIT = "MANUAL_EXIT"
    ENTRY_NOT_FILLED = "ENTRY_NOT_FILLED"


# ==================== 数据结构 ====================

@dataclass
class Order:
    """
    订单数据结构

    用于Entry订单和SL/TP子单
    """
    id: str
    symbol: str
    side: OrderSide
    type: OrderType
    price: float
    quantity: float
    created_at: int  # epoch ms
    expire_at: Optional[int] = None  # epoch ms, None表示不过期
    status: OrderStatus = OrderStatus.NEW
    filled_quantity: float = 0.0
    avg_fill_price: float = 0.0
    parent_position_id: Optional[str] = None  # SL/TP子单关联的持仓ID
    tag: Optional[str] = None  # "ENTRY" / "SL" / "TP"

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "side": self.side.value,
            "type": self.type.value,
            "price": self.price,
            "quantity": self.quantity,
            "created_at": self.created_at,
            "expire_at": self.expire_at,
            "status": self.status.value,
            "filled_quantity": self.filled_quantity,
            "avg_fill_price": self.avg_fill_price,
            "parent_position_id": self.parent_position_id,
            "tag": self.tag,
            "metadata": self.metadata,
        }


@dataclass
class Position:
    """
    持仓数据结构

    包含MFE/MAE跟踪用于策略优化分析
    """
    id: str
    symbol: str
    direction: str  # "LONG" / "SHORT"
    entry_price: float
    stop_loss: float
    take_profit: float
    quantity: float
    open_time: int  # epoch ms

    # 平仓信息（初始为None）
    close_time: Optional[int] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[ExitReason] = None

    # 盈亏信息
    realized_pnl: Optional[float] = None  # USDT
    realized_pnl_pct: Optional[float] = None  # %
    fees_paid: float = 0.0  # 已支付手续费

    # MFE/MAE跟踪（最大有利/不利偏移）
    max_favorable_excursion: float = 0.0  # 最大浮盈%
    max_adverse_excursion: float = 0.0  # 最大浮亏%

    # 四步系统元数据
    step1_result: Dict[str, Any] = field(default_factory=dict)
    step2_result: Dict[str, Any] = field(default_factory=dict)
    step3_result: Dict[str, Any] = field(default_factory=dict)
    step4_result: Dict[str, Any] = field(default_factory=dict)
    factor_scores: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "quantity": self.quantity,
            "open_time": self.open_time,
            "close_time": self.close_time,
            "exit_price": self.exit_price,
            "exit_reason": self.exit_reason.value if self.exit_reason else None,
            "realized_pnl": self.realized_pnl,
            "realized_pnl_pct": self.realized_pnl_pct,
            "fees_paid": self.fees_paid,
            "max_favorable_excursion": self.max_favorable_excursion,
            "max_adverse_excursion": self.max_adverse_excursion,
            "step1_result": self.step1_result,
            "step2_result": self.step2_result,
            "step3_result": self.step3_result,
            "step4_result": self.step4_result,
            "factor_scores": self.factor_scores,
        }

    @property
    def is_open(self) -> bool:
        """是否为开仓状态"""
        return self.close_time is None

    @property
    def holding_minutes(self) -> Optional[float]:
        """持仓时长（分钟）"""
        if self.close_time is None:
            return None
        return (self.close_time - self.open_time) / 60000


@dataclass
class AccountState:
    """
    账户状态数据结构

    包含权益、余额、持仓、订单等完整状态
    """
    equity: float  # 总权益 = balance + unrealized_pnl
    balance: float  # 可用余额
    unrealized_pnl: float  # 未实现盈亏
    realized_pnl: float  # 已实现盈亏（累计）
    fees_paid: float  # 已支付手续费（累计）

    open_positions: List[Position] = field(default_factory=list)
    open_orders: List[Order] = field(default_factory=list)
    closed_positions: List[Position] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "equity": self.equity,
            "balance": self.balance,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl,
            "fees_paid": self.fees_paid,
            "open_positions_count": len(self.open_positions),
            "open_orders_count": len(self.open_orders),
            "closed_positions_count": len(self.closed_positions),
        }


# ==================== Broker抽象接口 ====================

class Broker(ABC):
    """
    Broker抽象基类

    定义统一的订单和持仓管理接口，
    供PaperBroker、BacktestBroker、LiveBroker实现
    """

    @abstractmethod
    def get_account_state(self) -> AccountState:
        """
        获取当前账户状态

        Returns:
            AccountState: 包含权益、持仓、订单等完整状态
        """
        pass

    @abstractmethod
    def submit_order(self, order: Order) -> None:
        """
        提交订单

        Args:
            order: 订单对象

        Note:
            - Entry订单提交后进入待成交队列
            - SL/TP子单在Entry成交后自动创建
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """
        取消订单

        Args:
            order_id: 订单ID

        Returns:
            bool: 是否成功取消
        """
        pass

    @abstractmethod
    def on_price_update(self, symbol: str, price: float, timestamp: int) -> None:
        """
        价格更新回调

        用于检查订单成交和持仓止盈止损

        Args:
            symbol: 交易对
            price: 最新价格
            timestamp: 时间戳（毫秒）

        Note:
            - Paper模式：每1m bar调用一次
            - Live模式：每个tick调用一次
        """
        pass

    @abstractmethod
    def on_time(self, now_ts: int) -> None:
        """
        时间更新回调

        用于处理订单过期和持仓超时

        Args:
            now_ts: 当前时间戳（毫秒）
        """
        pass

    @abstractmethod
    def close_position(self, position_id: str, price: float, reason: ExitReason) -> bool:
        """
        手动平仓

        Args:
            position_id: 持仓ID
            price: 平仓价格
            reason: 退出原因

        Returns:
            bool: 是否成功平仓
        """
        pass

    @abstractmethod
    def get_position(self, position_id: str) -> Optional[Position]:
        """
        获取持仓

        Args:
            position_id: 持仓ID

        Returns:
            Position或None
        """
        pass

    @abstractmethod
    def get_order(self, order_id: str) -> Optional[Order]:
        """
        获取订单

        Args:
            order_id: 订单ID

        Returns:
            Order或None
        """
        pass
