# coding: utf-8
"""
Paper Broker - Paper Trading模拟执行

职责：
- 按执行契约维护订单生命周期（NEW → FILLED / EXPIRED）
- 维护持仓生命周期（OPEN → CLOSED）
- 计算账户权益（equity = balance + unrealized_pnl）
- 应用手续费和滑点

执行契约：
- Entry订单：限价单，检查价格是否触及
- SL/TP：Entry成交后自动创建子单
- 悲观假设：同时触发SL和TP时优先止损

Version: v1.0.0
Standard: SYSTEM_ENHANCEMENT_STANDARD.md v3.3.0
"""

from __future__ import annotations

import logging
import uuid
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

logger = logging.getLogger(__name__)


class PaperBroker(Broker):
    """
    Paper Trading模拟Broker

    配置从config/params.json的paper_trading.execution读取
    """

    def __init__(self, config: Dict[str, Any], initial_equity: float = 100000.0):
        """
        初始化PaperBroker

        Args:
            config: 执行配置（paper_trading.execution）
            initial_equity: 初始权益（USDT）
        """
        # 配置参数（从config读取，提供默认值）
        self.taker_fee_rate = config.get("taker_fee_rate", 0.0005)
        self.slippage_bps = config.get("slippage_bps", 2)
        self.max_entry_minutes = config.get("max_entry_minutes", 240)
        self.max_holding_minutes = config.get("max_holding_minutes", 2880)

        # 账户状态
        self.initial_equity = initial_equity
        self.balance = initial_equity
        self.realized_pnl = 0.0
        self.fees_paid = 0.0

        # 订单和持仓
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, Position] = {}
        self.closed_positions: List[Position] = []

        # 最新价格缓存
        self.last_prices: Dict[str, float] = {}

        logger.info(
            f"PaperBroker初始化: "
            f"equity={initial_equity}, "
            f"fee={self.taker_fee_rate*100:.3f}%, "
            f"slippage={self.slippage_bps}bps"
        )

    def get_account_state(self) -> AccountState:
        """获取账户状态"""
        # 计算未实现盈亏
        unrealized_pnl = self._calculate_unrealized_pnl()

        # 获取开仓持仓和订单
        open_positions = [p for p in self.positions.values() if p.is_open]
        open_orders = [o for o in self.orders.values() if o.status == OrderStatus.NEW]

        return AccountState(
            equity=self.balance + unrealized_pnl,
            balance=self.balance,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=self.realized_pnl,
            fees_paid=self.fees_paid,
            open_positions=open_positions,
            open_orders=open_orders,
            closed_positions=self.closed_positions,
        )

    def submit_order(self, order: Order) -> None:
        """提交订单"""
        if order.quantity <= 0:
            logger.warning(f"订单数量无效: {order.id} quantity={order.quantity}")
            return

        self.orders[order.id] = order
        logger.info(
            f"订单提交: {order.id} {order.symbol} {order.side.value} "
            f"{order.quantity}@{order.price} tag={order.tag}"
        )

    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        if order_id not in self.orders:
            return False

        order = self.orders[order_id]
        if order.status != OrderStatus.NEW:
            return False

        order.status = OrderStatus.CANCELED
        logger.info(f"订单取消: {order_id}")
        return True

    def on_price_update(self, symbol: str, price: float, timestamp: int) -> None:
        """
        价格更新回调

        检查：
        1. 待成交的Entry订单
        2. 活跃持仓的SL/TP
        """
        self.last_prices[symbol] = price

        # 1. 检查Entry订单成交
        self._check_entry_orders(symbol, price, timestamp)

        # 2. 检查持仓SL/TP
        self._check_position_exits(symbol, price, timestamp)

        # 3. 更新持仓MFE/MAE
        self._update_position_excursions(symbol, price)

    def on_time(self, now_ts: int) -> None:
        """
        时间更新回调

        处理：
        1. Entry订单过期
        2. 持仓超时强制平仓
        """
        # 1. 检查订单过期
        for order in list(self.orders.values()):
            if order.status != OrderStatus.NEW:
                continue
            if order.tag != "ENTRY":
                continue
            if order.expire_at and now_ts > order.expire_at:
                order.status = OrderStatus.EXPIRED
                logger.info(f"订单过期: {order.id} {order.symbol}")

        # 2. 检查持仓超时
        max_holding_ms = self.max_holding_minutes * 60 * 1000
        for position in list(self.positions.values()):
            if not position.is_open:
                continue
            if now_ts - position.open_time > max_holding_ms:
                price = self.last_prices.get(position.symbol, position.entry_price)
                self.close_position(position.id, price, ExitReason.TIME_EXIT)
                logger.info(f"持仓超时平仓: {position.id} {position.symbol}")

    def close_position(self, position_id: str, price: float, reason: ExitReason) -> bool:
        """平仓"""
        if position_id not in self.positions:
            return False

        position = self.positions[position_id]
        if not position.is_open:
            return False

        # 计算滑点后的平仓价格
        exit_price = self._apply_slippage(price, position.direction, is_entry=False)

        # 计算盈亏
        if position.direction == "LONG":
            pnl_pct = (exit_price - position.entry_price) / position.entry_price * 100
        else:
            pnl_pct = (position.entry_price - exit_price) / position.entry_price * 100

        notional = position.quantity * exit_price
        pnl_usdt = notional * pnl_pct / 100

        # 计算手续费（出场）
        exit_fee = notional * self.taker_fee_rate
        position.fees_paid += exit_fee
        self.fees_paid += exit_fee

        # 更新持仓
        position.close_time = self._get_current_timestamp()
        position.exit_price = exit_price
        position.exit_reason = reason
        position.realized_pnl = pnl_usdt - position.fees_paid
        position.realized_pnl_pct = pnl_pct

        # 更新账户
        self.balance += pnl_usdt - exit_fee
        self.realized_pnl += pnl_usdt - position.fees_paid

        # 移到已平仓列表
        self.closed_positions.append(position)

        # 取消相关的SL/TP子单
        self._cancel_child_orders(position_id)

        logger.info(
            f"平仓: {position.symbol} {position.direction} "
            f"PnL={position.realized_pnl:.2f} ({pnl_pct:+.2f}%) "
            f"reason={reason.value}"
        )

        return True

    def get_position(self, position_id: str) -> Optional[Position]:
        """获取持仓"""
        return self.positions.get(position_id)

    def get_order(self, order_id: str) -> Optional[Order]:
        """获取订单"""
        return self.orders.get(order_id)

    # ==================== 私有方法 ====================

    def _check_entry_orders(self, symbol: str, price: float, timestamp: int) -> None:
        """检查Entry订单是否成交"""
        for order in list(self.orders.values()):
            if order.status != OrderStatus.NEW:
                continue
            if order.tag != "ENTRY":
                continue
            if order.symbol != symbol:
                continue

            # 检查是否触价
            filled = False
            if order.side == OrderSide.BUY:
                # 多头：价格 <= 入场价则成交
                if price <= order.price:
                    filled = True
            else:
                # 空头：价格 >= 入场价则成交
                if price >= order.price:
                    filled = True

            if filled:
                self._fill_entry_order(order, price, timestamp)

    def _fill_entry_order(self, order: Order, price: float, timestamp: int) -> None:
        """Entry订单成交"""
        # 计算滑点后的成交价
        direction = "LONG" if order.side == OrderSide.BUY else "SHORT"
        fill_price = self._apply_slippage(price, direction, is_entry=True)

        # 更新订单状态
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.avg_fill_price = fill_price

        # 计算手续费（入场）
        notional = order.quantity * fill_price
        entry_fee = notional * self.taker_fee_rate
        self.fees_paid += entry_fee
        self.balance -= entry_fee

        # 创建持仓
        position_id = self._generate_id()
        position = Position(
            id=position_id,
            symbol=order.symbol,
            direction=direction,
            entry_price=fill_price,
            stop_loss=order.metadata.get("stop_loss", 0),
            take_profit=order.metadata.get("take_profit", 0),
            quantity=order.quantity,
            open_time=timestamp,
            fees_paid=entry_fee,
            step1_result=order.metadata.get("step1_result", {}),
            step2_result=order.metadata.get("step2_result", {}),
            step3_result=order.metadata.get("step3_result", {}),
            step4_result=order.metadata.get("step4_result", {}),
            factor_scores=order.metadata.get("factor_scores", {}),
        )
        self.positions[position_id] = position
        order.parent_position_id = position_id

        logger.info(
            f"Entry成交: {order.symbol} {direction} "
            f"{order.quantity}@{fill_price:.4f} "
            f"SL={position.stop_loss:.4f} TP={position.take_profit:.4f}"
        )

    def _check_position_exits(self, symbol: str, price: float, timestamp: int) -> None:
        """检查持仓SL/TP"""
        for position in list(self.positions.values()):
            if not position.is_open:
                continue
            if position.symbol != symbol:
                continue

            # 检查SL和TP
            sl_hit = False
            tp_hit = False

            if position.direction == "LONG":
                sl_hit = price <= position.stop_loss
                tp_hit = price >= position.take_profit
            else:
                sl_hit = price >= position.stop_loss
                tp_hit = price <= position.take_profit

            # 悲观假设：同时触发时优先止损
            if sl_hit and tp_hit:
                self.close_position(position.id, position.stop_loss, ExitReason.STOP_LOSS)
            elif sl_hit:
                self.close_position(position.id, position.stop_loss, ExitReason.STOP_LOSS)
            elif tp_hit:
                self.close_position(position.id, position.take_profit, ExitReason.TAKE_PROFIT)

    def _update_position_excursions(self, symbol: str, price: float) -> None:
        """更新持仓MFE/MAE"""
        for position in self.positions.values():
            if not position.is_open:
                continue
            if position.symbol != symbol:
                continue

            # 计算当前盈亏%
            if position.direction == "LONG":
                current_pnl_pct = (price - position.entry_price) / position.entry_price * 100
            else:
                current_pnl_pct = (position.entry_price - price) / position.entry_price * 100

            # 更新MFE/MAE
            if current_pnl_pct > 0:
                position.max_favorable_excursion = max(
                    position.max_favorable_excursion, current_pnl_pct
                )
            else:
                position.max_adverse_excursion = max(
                    position.max_adverse_excursion, abs(current_pnl_pct)
                )

    def _apply_slippage(self, price: float, direction: str, is_entry: bool) -> float:
        """
        应用滑点

        Args:
            price: 原始价格
            direction: "LONG" / "SHORT"
            is_entry: 是否为入场

        Returns:
            滑点后价格
        """
        slippage_pct = self.slippage_bps / 10000  # bps to %

        if direction == "LONG":
            if is_entry:
                # 多头入场：买贵
                return price * (1 + slippage_pct)
            else:
                # 多头出场：卖便宜
                return price * (1 - slippage_pct)
        else:
            if is_entry:
                # 空头入场：卖便宜
                return price * (1 - slippage_pct)
            else:
                # 空头出场：买贵
                return price * (1 + slippage_pct)

    def _calculate_unrealized_pnl(self) -> float:
        """计算未实现盈亏"""
        total_pnl = 0.0
        for position in self.positions.values():
            if not position.is_open:
                continue
            price = self.last_prices.get(position.symbol, position.entry_price)
            if position.direction == "LONG":
                pnl = (price - position.entry_price) * position.quantity
            else:
                pnl = (position.entry_price - price) * position.quantity
            total_pnl += pnl
        return total_pnl

    def _cancel_child_orders(self, position_id: str) -> None:
        """取消持仓相关的子单"""
        for order in self.orders.values():
            if order.parent_position_id == position_id and order.status == OrderStatus.NEW:
                order.status = OrderStatus.CANCELED

    def _generate_id(self) -> str:
        """生成唯一ID"""
        return str(uuid.uuid4())[:8]

    def _get_current_timestamp(self) -> int:
        """获取当前时间戳"""
        import time
        return int(time.time() * 1000)

    # ==================== 状态保存/恢复 ====================

    def save_state(self) -> Dict[str, Any]:
        """保存状态（用于重启恢复）"""
        return {
            "balance": self.balance,
            "realized_pnl": self.realized_pnl,
            "fees_paid": self.fees_paid,
            "orders": {k: v.to_dict() for k, v in self.orders.items()},
            "positions": {k: v.to_dict() for k, v in self.positions.items()},
            "closed_positions": [p.to_dict() for p in self.closed_positions],
            "last_prices": self.last_prices,
        }

    def load_state(self, state: Dict[str, Any]) -> None:
        """恢复状态"""
        self.balance = state.get("balance", self.initial_equity)
        self.realized_pnl = state.get("realized_pnl", 0.0)
        self.fees_paid = state.get("fees_paid", 0.0)
        self.last_prices = state.get("last_prices", {})
        # TODO: 恢复orders和positions需要反序列化
        logger.info(f"PaperBroker状态恢复: balance={self.balance}")
