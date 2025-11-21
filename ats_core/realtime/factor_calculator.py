# coding: utf-8
"""
V8实时因子计算器

将Cryptofeed实时数据流转换为CryptoSignal因子分数。

数据流：
    Cryptofeed(trades/orderbook) → RealtimeFactorCalculator → Factor Scores → Decision Engine

支持因子：
    - CVD (Cumulative Volume Delta): 从trades计算
    - OBI (Orderbook Imbalance): 从orderbook计算
    - LDI (Liquidity Distribution Index): 从orderbook计算
    - Trade Intensity: 从trades计算
    - VWAP: 从trades计算

Version: v8.0.0
Standard: SYSTEM_ENHANCEMENT_STANDARD.md v3.3.0
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from ats_core.config.threshold_config import get_thresholds

logger = logging.getLogger(__name__)


@dataclass
class TradeData:
    """单笔成交数据"""
    symbol: str
    timestamp: float
    price: float
    size: float
    side: str  # 'buy' or 'sell'


@dataclass
class OrderbookData:
    """订单簿快照"""
    symbol: str
    timestamp: float
    bids: List[List[float]]  # [[price, size], ...]
    asks: List[List[float]]


@dataclass
class RealtimeFactors:
    """实时因子计算结果"""
    symbol: str
    timestamp: float
    cvd: float = 0.0
    cvd_z: float = 0.0
    obi: float = 0.0
    ldi: float = 0.0
    trade_intensity: float = 0.0
    vwap: float = 0.0
    bid_depth: float = 0.0
    ask_depth: float = 0.0
    spread_bps: float = 0.0
    meta: Dict[str, Any] = field(default_factory=dict)


class RealtimeFactorCalculator:
    """
    V8实时因子计算器

    从Cryptofeed实时数据计算因子分数，为决策引擎提供输入。

    配置从config/signal_thresholds.json的v8_integration.realtime_factor读取。
    """

    def __init__(self, symbols: List[str], config: Optional[Dict[str, Any]] = None):
        """
        初始化计算器

        Args:
            symbols: 交易对列表
            config: 可选配置覆盖（默认从signal_thresholds.json读取）
        """
        # 加载配置
        thresholds = get_thresholds()
        v8_config = thresholds.get_all().get("v8_integration", {})
        factor_config = v8_config.get("realtime_factor", {})

        # 合并配置（传入的config优先）
        self.config = {**factor_config, **(config or {})}

        # 配置参数（从配置读取，提供默认值）
        self.cvd_window = self.config.get("cvd_window_trades", 500)
        self.obi_depth = self.config.get("obi_depth_levels", 20)
        self.ldi_threshold = self.config.get("ldi_imbalance_threshold", 0.3)
        self.smoothing_alpha = self.config.get("factor_smoothing_alpha", 0.1)
        self.min_trades_cvd = self.config.get("min_trades_for_cvd", 50)
        self.min_ob_updates = self.config.get("min_orderbook_updates", 10)

        # 验证配置参数
        assert 0 < self.cvd_window <= 10000, f"cvd_window={self.cvd_window} 超出范围"
        assert 0 < self.obi_depth <= 100, f"obi_depth={self.obi_depth} 超出范围"
        assert 0 < self.smoothing_alpha <= 1, f"smoothing_alpha={self.smoothing_alpha} 超出范围"

        # 初始化数据缓冲区
        self.symbols = [s.upper() for s in symbols]
        self.trade_buffers: Dict[str, deque] = {
            s: deque(maxlen=self.cvd_window) for s in self.symbols
        }
        self.orderbook_cache: Dict[str, OrderbookData] = {}
        self.ob_update_counts: Dict[str, int] = {s: 0 for s in self.symbols}

        # CVD累计值和历史（用于Z-score）
        self.cvd_cumulative: Dict[str, float] = {s: 0.0 for s in self.symbols}
        self.cvd_history: Dict[str, deque] = {
            s: deque(maxlen=100) for s in self.symbols
        }

        # 平滑后的因子值
        self.smoothed_factors: Dict[str, RealtimeFactors] = {}

        # 回调函数
        self._on_factors_callback: Optional[Callable[[RealtimeFactors], None]] = None

        logger.info(
            f"RealtimeFactorCalculator初始化: symbols={symbols}, "
            f"cvd_window={self.cvd_window}, obi_depth={self.obi_depth}"
        )

    def set_callback(self, on_factors: Callable[[RealtimeFactors], None]) -> None:
        """
        设置因子更新回调

        Args:
            on_factors: 因子计算完成回调 (RealtimeFactors) -> None
        """
        self._on_factors_callback = on_factors

    def on_trade(self, trade: TradeData) -> None:
        """
        处理新成交数据

        Args:
            trade: 成交数据
        """
        symbol = trade.symbol.upper()
        if symbol not in self.trade_buffers:
            return

        # 添加到缓冲区
        self.trade_buffers[symbol].append(trade)

        # 更新CVD累计值
        delta = trade.size if trade.side == 'buy' else -trade.size
        self.cvd_cumulative[symbol] += delta

        # 计算因子（如果有足够数据）
        if len(self.trade_buffers[symbol]) >= self.min_trades_cvd:
            self._calculate_and_emit(symbol)

    def on_orderbook(self, ob: OrderbookData) -> None:
        """
        处理订单簿更新

        Args:
            ob: 订单簿快照
        """
        symbol = ob.symbol.upper()
        if symbol not in self.symbols:
            return

        # 更新缓存
        self.orderbook_cache[symbol] = ob
        self.ob_update_counts[symbol] += 1

        # 计算因子（如果有足够数据）
        if self.ob_update_counts[symbol] >= self.min_ob_updates:
            self._calculate_and_emit(symbol)

    def _calculate_and_emit(self, symbol: str) -> None:
        """
        计算因子并触发回调

        Args:
            symbol: 交易对
        """
        factors = self.calculate_factors(symbol)
        if factors is None:
            return

        # 应用指数平滑
        if symbol in self.smoothed_factors:
            factors = self._apply_smoothing(symbol, factors)

        self.smoothed_factors[symbol] = factors

        # 触发回调
        if self._on_factors_callback:
            try:
                self._on_factors_callback(factors)
            except Exception as e:
                logger.error(f"因子回调异常: {e}")

    def calculate_factors(self, symbol: str) -> Optional[RealtimeFactors]:
        """
        计算指定交易对的所有实时因子

        Args:
            symbol: 交易对

        Returns:
            RealtimeFactors或None（数据不足时）
        """
        symbol = symbol.upper()
        if symbol not in self.symbols:
            return None

        ts = time.time()
        trades = list(self.trade_buffers.get(symbol, []))
        ob = self.orderbook_cache.get(symbol)

        # 计算CVD因子
        cvd, cvd_z = self._calc_cvd(symbol, trades)

        # 计算订单簿因子
        obi, ldi, bid_depth, ask_depth, spread_bps = self._calc_orderbook_factors(ob)

        # 计算交易强度
        trade_intensity = self._calc_trade_intensity(trades)

        # 计算VWAP
        vwap = self._calc_vwap(trades)

        return RealtimeFactors(
            symbol=symbol,
            timestamp=ts,
            cvd=cvd,
            cvd_z=cvd_z,
            obi=obi,
            ldi=ldi,
            trade_intensity=trade_intensity,
            vwap=vwap,
            bid_depth=bid_depth,
            ask_depth=ask_depth,
            spread_bps=spread_bps,
            meta={
                "trade_count": len(trades),
                "ob_updates": self.ob_update_counts.get(symbol, 0),
            }
        )

    def _calc_cvd(self, symbol: str, trades: List[TradeData]) -> Tuple[float, float]:
        """
        计算CVD和CVD Z-score

        Returns:
            (cvd_cumulative, cvd_z_score)
        """
        if not trades:
            return 0.0, 0.0

        # 当前CVD累计值
        cvd = self.cvd_cumulative.get(symbol, 0.0)

        # 添加到历史（用于Z-score）
        self.cvd_history[symbol].append(cvd)

        # 计算Z-score
        history = list(self.cvd_history[symbol])
        if len(history) < 10:
            return cvd, 0.0

        mean = sum(history) / len(history)
        variance = sum((x - mean) ** 2 for x in history) / len(history)
        std = variance ** 0.5 if variance > 0 else 1.0

        cvd_z = (cvd - mean) / std if std > 0 else 0.0

        # 限制Z-score范围
        cvd_z = max(-3.0, min(3.0, cvd_z))

        return cvd, cvd_z

    def _calc_orderbook_factors(
        self, ob: Optional[OrderbookData]
    ) -> Tuple[float, float, float, float, float]:
        """
        计算订单簿因子

        Returns:
            (obi, ldi, bid_depth, ask_depth, spread_bps)
        """
        if not ob or not ob.bids or not ob.asks:
            return 0.0, 0.0, 0.0, 0.0, 0.0

        # 取前N档
        bids = ob.bids[:self.obi_depth]
        asks = ob.asks[:self.obi_depth]

        # 计算深度
        bid_depth = sum(b[1] for b in bids) if bids else 0.0
        ask_depth = sum(a[1] for a in asks) if asks else 0.0

        # OBI (Orderbook Imbalance)
        total_depth = bid_depth + ask_depth
        obi = (bid_depth - ask_depth) / total_depth if total_depth > 0 else 0.0

        # LDI (Liquidity Distribution Index)
        # 计算深度在价格带上的分布不均匀性
        if len(bids) > 1 and len(asks) > 1:
            bid_sizes = [b[1] for b in bids]
            ask_sizes = [a[1] for a in asks]

            # 使用变异系数衡量分布不均
            bid_cv = self._coefficient_of_variation(bid_sizes)
            ask_cv = self._coefficient_of_variation(ask_sizes)
            ldi = (bid_cv + ask_cv) / 2
        else:
            ldi = 0.0

        # Spread (basis points)
        best_bid = bids[0][0] if bids else 0
        best_ask = asks[0][0] if asks else 0
        mid_price = (best_bid + best_ask) / 2 if best_bid and best_ask else 0
        spread_bps = ((best_ask - best_bid) / mid_price * 10000) if mid_price > 0 else 0.0

        return obi, ldi, bid_depth, ask_depth, spread_bps

    def _calc_trade_intensity(self, trades: List[TradeData]) -> float:
        """
        计算交易强度（单位时间成交量）
        """
        if len(trades) < 2:
            return 0.0

        # 时间跨度
        time_span = trades[-1].timestamp - trades[0].timestamp
        if time_span <= 0:
            return 0.0

        # 总成交量
        total_volume = sum(t.size for t in trades)

        # 每秒成交量
        return total_volume / time_span

    def _calc_vwap(self, trades: List[TradeData]) -> float:
        """
        计算成交量加权平均价格
        """
        if not trades:
            return 0.0

        total_value = sum(t.price * t.size for t in trades)
        total_volume = sum(t.size for t in trades)

        return total_value / total_volume if total_volume > 0 else 0.0

    def _coefficient_of_variation(self, values: List[float]) -> float:
        """计算变异系数 (std / mean)"""
        if not values or len(values) < 2:
            return 0.0

        mean = sum(values) / len(values)
        if mean == 0:
            return 0.0

        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std = variance ** 0.5

        return std / mean

    def _apply_smoothing(
        self, symbol: str, new_factors: RealtimeFactors
    ) -> RealtimeFactors:
        """
        应用指数移动平均平滑

        Args:
            symbol: 交易对
            new_factors: 新计算的因子

        Returns:
            平滑后的因子
        """
        old = self.smoothed_factors.get(symbol)
        if not old:
            return new_factors

        alpha = self.smoothing_alpha

        # EMA平滑各因子
        return RealtimeFactors(
            symbol=symbol,
            timestamp=new_factors.timestamp,
            cvd=new_factors.cvd,  # 累计值不平滑
            cvd_z=alpha * new_factors.cvd_z + (1 - alpha) * old.cvd_z,
            obi=alpha * new_factors.obi + (1 - alpha) * old.obi,
            ldi=alpha * new_factors.ldi + (1 - alpha) * old.ldi,
            trade_intensity=alpha * new_factors.trade_intensity + (1 - alpha) * old.trade_intensity,
            vwap=alpha * new_factors.vwap + (1 - alpha) * old.vwap,
            bid_depth=new_factors.bid_depth,  # 深度不平滑
            ask_depth=new_factors.ask_depth,
            spread_bps=alpha * new_factors.spread_bps + (1 - alpha) * old.spread_bps,
            meta=new_factors.meta
        )

    def get_factors(self, symbol: str) -> Optional[RealtimeFactors]:
        """
        获取指定交易对的最新因子值

        Args:
            symbol: 交易对

        Returns:
            最新因子值或None
        """
        return self.smoothed_factors.get(symbol.upper())

    def get_all_factors(self) -> Dict[str, RealtimeFactors]:
        """
        获取所有交易对的最新因子值

        Returns:
            {symbol: RealtimeFactors}
        """
        return self.smoothed_factors.copy()

    def reset(self, symbol: Optional[str] = None) -> None:
        """
        重置计算器状态

        Args:
            symbol: 指定交易对，None表示重置全部
        """
        if symbol:
            symbol = symbol.upper()
            if symbol in self.symbols:
                self.trade_buffers[symbol].clear()
                self.cvd_cumulative[symbol] = 0.0
                self.cvd_history[symbol].clear()
                self.ob_update_counts[symbol] = 0
                if symbol in self.orderbook_cache:
                    del self.orderbook_cache[symbol]
                if symbol in self.smoothed_factors:
                    del self.smoothed_factors[symbol]
        else:
            for s in self.symbols:
                self.reset(s)

        logger.info(f"RealtimeFactorCalculator重置: {symbol or 'all'}")
