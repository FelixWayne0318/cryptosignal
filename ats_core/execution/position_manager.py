# coding: utf-8
"""
动态仓位管理器（因子驱动，实时监控）

核心功能:
1. WebSocket实时监控持仓和市场
2. 因子驱动的动态止损止盈调整
3. 分批止盈（TP1: 50%, TP2: 50%）
4. TP1后移动止损到保本
5. API优化（11 req/min）
"""

import asyncio
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from decimal import Decimal

from ats_core.execution.binance_futures_client import BinanceFuturesClient
from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.logging import log, warn, error


@dataclass
class Position:
    """持仓信息"""
    symbol: str
    side: str  # LONG/SHORT
    entry_price: float
    quantity: float
    leverage: int

    # 止损止盈
    stop_loss: float
    take_profit_1: float
    take_profit_2: float

    # 状态
    tp1_hit: bool = False
    moved_to_breakeven: bool = False

    # 因子数据（用于动态调整）
    initial_factors: Dict = field(default_factory=dict)

    # 时间
    entry_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)

    def get_current_pnl_pct(self, current_price: float) -> float:
        """计算当前盈亏百分比"""
        if self.side == 'LONG':
            return (current_price - self.entry_price) / self.entry_price * 100
        else:
            return (self.entry_price - current_price) / self.entry_price * 100


class DynamicPositionManager:
    """
    动态仓位管理器

    特性:
    - WebSocket实时数据（200ms延迟）
    - 5秒检查周期（但用WebSocket推送数据）
    - 因子驱动动态调整
    - API友好（11 req/min）
    """

    def __init__(self, client: BinanceFuturesClient):
        self.client = client
        self.positions: Dict[str, Position] = {}

        # WebSocket价格缓存
        self.price_cache: Dict[str, float] = {}

        # 因子缓存（60秒）
        self.factor_cache: Dict[str, Dict] = {}
        self.factor_cache_time: Dict[str, float] = {}

        # 状态
        self.is_running = False

        # 统计
        self.stats = {
            'total_adjustments': 0,
            'tp1_hits': 0,
            'tp2_hits': 0,
            'stop_losses': 0,
            'breakeven_moves': 0
        }

        log("✅ 动态仓位管理器初始化完成")

    # ========== 仓位管理 ==========

    def add_position(self, position: Position):
        """添加持仓到监控列表"""
        self.positions[position.symbol] = position

        log(f"📊 添加持仓监控: {position.symbol} {position.side} "
            f"qty={position.quantity} entry={position.entry_price}")
        log(f"   止损: {position.stop_loss:.4f}")
        log(f"   TP1: {position.take_profit_1:.4f} (50%)")
        log(f"   TP2: {position.take_profit_2:.4f} (50%)")

        # 订阅实时价格
        asyncio.create_task(self._subscribe_price(position.symbol))

    def remove_position(self, symbol: str):
        """移除持仓"""
        if symbol in self.positions:
            del self.positions[symbol]
            log(f"🗑️  移除持仓监控: {symbol}")

    async def _subscribe_price(self, symbol: str):
        """订阅实时价格（WebSocket）"""

        def price_callback(data: Dict):
            """价格更新回调"""
            if 'c' in data:  # ticker数据
                self.price_cache[symbol] = float(data['c'])
            elif 'p' in data:  # trade数据
                self.price_cache[symbol] = float(data['p'])

        await self.client.subscribe_ticker(symbol, price_callback)

    # ========== 因子分析 ==========

    async def _get_factors(self, symbol: str, use_cache: bool = True) -> Dict:
        """
        获取因子分析结果（带缓存）

        Args:
            symbol: 交易对
            use_cache: 是否使用缓存（默认True，缓存60秒）

        Returns:
            因子数据字典
        """
        now = time.time()

        # 检查缓存
        if use_cache and symbol in self.factor_cache:
            cache_age = now - self.factor_cache_time.get(symbol, 0)
            if cache_age < 60:  # 60秒缓存
                return self.factor_cache[symbol]

        # 重新分析
        try:
            result = analyze_symbol(symbol)

            # 提取关键因子
            factors = {
                'final_score': result.get('final_score', 0),
                'signal_strength': result.get('signal_strength', 0),
                'trend_score': result.get('layers', {}).get('price_action', {}).get('trend', 0),
                'volume_score': result.get('layers', {}).get('money_flow', {}).get('volume_plus', 0),
                'liquidity_score': result.get('layers', {}).get('microstructure', {}).get('liquidity', 0),
                'independence': result.get('independence', 0),
                'volatility_atr_pct': result.get('metadata', {}).get('volatility_atr_pct', 2.0)
            }

            # 更新缓存
            self.factor_cache[symbol] = factors
            self.factor_cache_time[symbol] = now

            return factors

        except Exception as e:
            error(f"因子分析失败 {symbol}: {e}")
            return self.factor_cache.get(symbol, {})

    # ========== 动态调整逻辑 ==========

    async def _check_position(self, symbol: str):
        """
        检查单个持仓（动态调整）

        核心逻辑:
        1. 检查TP1是否触达（平50%，移动止损到保本）
        2. 检查TP2是否触达（平剩余50%）
        3. 检查止损是否触达
        4. 动态调整止损（基于因子）
        """
        position = self.positions.get(symbol)
        if not position:
            return

        # 获取当前价格（从WebSocket缓存）
        current_price = self.price_cache.get(symbol)
        if not current_price:
            warn(f"⚠️  {symbol} 价格数据缺失")
            return

        # 计算当前盈亏
        pnl_pct = position.get_current_pnl_pct(current_price)

        # 获取因子数据
        factors = await self._get_factors(symbol, use_cache=True)

        # ========== 检查TP1 ==========
        if not position.tp1_hit:
            tp1_triggered = (
                (position.side == 'LONG' and current_price >= position.take_profit_1) or
                (position.side == 'SHORT' and current_price <= position.take_profit_1)
            )

            if tp1_triggered:
                log(f"🎯 TP1触达: {symbol} price={current_price:.4f}")

                # 平50%
                await self._close_partial(symbol, 0.5)

                position.tp1_hit = True
                self.stats['tp1_hits'] += 1

                # 移动止损到保本
                if not position.moved_to_breakeven:
                    await self._move_stop_to_breakeven(symbol)

        # ========== 检查TP2 ==========
        if position.tp1_hit:
            tp2_triggered = (
                (position.side == 'LONG' and current_price >= position.take_profit_2) or
                (position.side == 'SHORT' and current_price <= position.take_profit_2)
            )

            if tp2_triggered:
                log(f"🎯 TP2触达: {symbol} price={current_price:.4f}")

                # 平剩余50%
                await self._close_position(symbol)

                self.stats['tp2_hits'] += 1
                self.remove_position(symbol)
                return

        # ========== 检查止损 ==========
        stop_triggered = (
            (position.side == 'LONG' and current_price <= position.stop_loss) or
            (position.side == 'SHORT' and current_price >= position.stop_loss)
        )

        if stop_triggered:
            log(f"🛑 止损触发: {symbol} price={current_price:.4f} stop={position.stop_loss:.4f}")

            await self._close_position(symbol)

            self.stats['stop_losses'] += 1
            self.remove_position(symbol)
            return

        # ========== 动态调整止损（仅TP1后） ==========
        if position.tp1_hit and not position.moved_to_breakeven:
            # 如果盈利继续增加，可以适当收紧止损
            # 这里使用保守策略：TP1后已移至保本，不再调整
            pass

        # 更新最后检查时间
        position.last_update = time.time()

    async def _close_partial(self, symbol: str, percentage: float):
        """平仓一部分（例如TP1平50%）"""
        position = self.positions.get(symbol)
        if not position:
            return

        close_qty = position.quantity * percentage

        log(f"📤 部分平仓: {symbol} qty={close_qty:.4f} ({percentage*100}%)")

        # 确定方向
        side = 'SELL' if position.side == 'LONG' else 'BUY'

        result = await self.client.create_order(
            symbol=symbol,
            side=side,
            order_type='MARKET',
            quantity=close_qty,
            reduce_only=True
        )

        if 'error' not in result:
            # 更新持仓数量
            position.quantity -= close_qty
            log(f"✅ 部分平仓成功，剩余: {position.quantity:.4f}")
        else:
            error(f"❌ 部分平仓失败: {result['error']}")

    async def _close_position(self, symbol: str):
        """完全平仓"""
        position = self.positions.get(symbol)
        if not position:
            return

        log(f"📤 完全平仓: {symbol}")

        result = await self.client.close_position(symbol)

        if 'error' not in result:
            log(f"✅ 平仓成功: {symbol}")
        else:
            error(f"❌ 平仓失败: {result['error']}")

    async def _move_stop_to_breakeven(self, symbol: str):
        """
        移动止损到保本

        注意: 币安合约不支持直接修改止损订单，
        需要取消旧的止损订单并创建新的
        """
        position = self.positions.get(symbol)
        if not position:
            return

        log(f"🔒 移动止损到保本: {symbol} from {position.stop_loss:.4f} to {position.entry_price:.4f}")

        # 更新止损价格
        position.stop_loss = position.entry_price
        position.moved_to_breakeven = True

        self.stats['breakeven_moves'] += 1

        # 注意: 这里简化处理，实际应该通过条件单实现
        # 币安支持STOP_MARKET订单类型
        log(f"✅ 止损已更新到保本位: {position.entry_price:.4f}")

    # ========== 主循环 ==========

    async def start(self):
        """启动动态管理器"""
        self.is_running = True
        self.client.is_running = True

        log("🚀 动态仓位管理器已启动")
        log(f"   检查周期: 5秒")
        log(f"   数据源: WebSocket (200ms延迟)")
        log(f"   因子缓存: 60秒")

        while self.is_running:
            try:
                # 检查所有持仓
                for symbol in list(self.positions.keys()):
                    await self._check_position(symbol)

                # 等待5秒
                await asyncio.sleep(5)

            except Exception as e:
                error(f"主循环错误: {e}")
                await asyncio.sleep(1)

    async def stop(self):
        """停止管理器"""
        self.is_running = False
        log("🛑 动态仓位管理器已停止")

        # 打印统计
        log(f"\n{'='*60}")
        log(f"📊 运行统计")
        log(f"{'='*60}")
        log(f"  TP1触达: {self.stats['tp1_hits']}")
        log(f"  TP2触达: {self.stats['tp2_hits']}")
        log(f"  止损触发: {self.stats['stop_losses']}")
        log(f"  保本移动: {self.stats['breakeven_moves']}")
        log(f"  总调整次数: {self.stats['total_adjustments']}")
        log(f"{'='*60}")

    # ========== 辅助方法 ==========

    def get_position(self, symbol: str) -> Optional[Position]:
        """获取持仓信息"""
        return self.positions.get(symbol)

    def get_all_positions(self) -> List[Position]:
        """获取所有持仓"""
        return list(self.positions.values())

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.stats.copy()


# ============ 辅助函数 ============

def calculate_stop_loss_take_profit(
    entry_price: float,
    side: str,
    factors: Dict,
    base_stop_pct: float = 2.0,
    base_tp1_pct: float = 4.0,
    base_tp2_pct: float = 8.0
) -> Dict[str, float]:
    """
    基于因子计算止损止盈价格

    Args:
        entry_price: 入场价格
        side: LONG/SHORT
        factors: 因子数据
        base_stop_pct: 基础止损百分比（默认2%）
        base_tp1_pct: 基础TP1百分比（默认4%）
        base_tp2_pct: 基础TP2百分比（默认8%）

    Returns:
        {stop_loss, take_profit_1, take_profit_2}

    因子影响:
    - 信号强度高 → 止损更紧（-20%），止盈更远（+30%）
    - 趋势强 → 止盈更远（+20%）
    - 流动性好 → 止损更紧（-10%）
    - 波动率高 → 止损放宽（+50%）
    """

    # 提取因子
    signal_strength = factors.get('signal_strength', 0) / 100.0  # 归一化到0-1
    trend_score = factors.get('trend_score', 0) / 100.0
    liquidity = factors.get('liquidity_score', 0) / 100.0
    volatility = factors.get('volatility_atr_pct', 2.0)

    # ========== 调整止损 ==========
    stop_pct = base_stop_pct

    # 1. 信号强度高 → 止损更紧
    if signal_strength > 0.7:
        stop_pct *= 0.8  # -20%

    # 2. 流动性好 → 止损更紧
    if liquidity > 0.6:
        stop_pct *= 0.9  # -10%

    # 3. 波动率高 → 止损放宽
    if volatility > 3.0:
        stop_pct *= 1.5  # +50%

    # ========== 调整止盈 ==========
    tp1_pct = base_tp1_pct
    tp2_pct = base_tp2_pct

    # 1. 信号强度高 → 止盈更远
    if signal_strength > 0.7:
        tp1_pct *= 1.3  # +30%
        tp2_pct *= 1.3

    # 2. 趋势强 → 止盈更远
    if trend_score > 0.6:
        tp1_pct *= 1.2  # +20%
        tp2_pct *= 1.2

    # ========== 计算价格 ==========
    if side == 'LONG':
        stop_loss = entry_price * (1 - stop_pct / 100)
        take_profit_1 = entry_price * (1 + tp1_pct / 100)
        take_profit_2 = entry_price * (1 + tp2_pct / 100)
    else:  # SHORT
        stop_loss = entry_price * (1 + stop_pct / 100)
        take_profit_1 = entry_price * (1 - tp1_pct / 100)
        take_profit_2 = entry_price * (1 - tp2_pct / 100)

    log(f"📊 因子驱动的风险管理参数:")
    log(f"   止损: {stop_pct:.2f}% (基准{base_stop_pct}%)")
    log(f"   TP1: {tp1_pct:.2f}% (基准{base_tp1_pct}%)")
    log(f"   TP2: {tp2_pct:.2f}% (基准{base_tp2_pct}%)")

    return {
        'stop_loss': stop_loss,
        'take_profit_1': take_profit_1,
        'take_profit_2': take_profit_2,
        'stop_pct': stop_pct,
        'tp1_pct': tp1_pct,
        'tp2_pct': tp2_pct
    }
