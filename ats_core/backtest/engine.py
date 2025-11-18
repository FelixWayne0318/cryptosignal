# coding: utf-8
"""
Backtest Framework v1.0 - Backtest Engine
回测框架 - 回测引擎

功能：
1. 时间循环模拟（按小时步进）
2. 调用四步系统生成信号
3. 模拟订单执行（滑点、手续费）
4. 头寸生命周期跟踪（SL/TP监控）
5. 结果收集与返回

Standard: SYSTEM_ENHANCEMENT_STANDARD.md v3.3.0
Design: docs/BACKTEST_FRAMEWORK_v1.0_DESIGN.md
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any

from ats_core.backtest.data_loader import HistoricalDataLoader
from ats_core.pipeline.analyze_symbol import analyze_symbol_with_preloaded_klines
from ats_core.cfg import CFG

logger = logging.getLogger(__name__)


@dataclass
class SimulatedSignal:
    """
    回测模拟信号（包含完整执行结果）

    设计原则（§6.2 函数签名演进）:
    - 所有字段初始化有默认值
    - 新增字段向后兼容
    """
    # 基本信息
    symbol: str
    timestamp: int  # 信号生成时间（毫秒）
    side: str  # "long" | "short"

    # 推荐价格（从Step3获取）
    entry_price_recommended: float
    stop_loss_recommended: float
    take_profit_1_recommended: float
    take_profit_2_recommended: float

    # 实际执行价格（模拟滑点后）
    entry_price_actual: float = 0.0
    stop_loss_actual: float = 0.0
    take_profit_1_actual: float = 0.0
    take_profit_2_actual: float = 0.0

    # 退出信息
    exit_time: int = 0  # 退出时间（毫秒）
    exit_price: float = 0.0
    exit_reason: str = ""  # "SL_HIT" | "TP1_HIT" | "TP2_HIT" | "TIMEOUT" | "MANUAL"

    # 盈亏信息
    pnl_percent: float = 0.0  # (exit - entry) / entry * 100
    pnl_usdt: float = 0.0  # 假设100 USDT仓位

    # 持仓时长
    holding_hours: float = 0.0

    # 四步系统元数据
    step1_result: Dict = field(default_factory=dict)
    step2_result: Dict = field(default_factory=dict)
    step3_result: Dict = field(default_factory=dict)
    step4_result: Dict = field(default_factory=dict)

    # 因子分数快照
    factor_scores: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """转换为字典（用于JSON序列化）"""
        return asdict(self)


@dataclass
class BacktestResult:
    """
    回测执行结果

    包含:
    - signals: 所有模拟信号列表
    - metadata: 执行元数据（时间范围、符号、执行时长等）
    """
    signals: List[SimulatedSignal]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict:
        """转换为字典（用于JSON序列化）"""
        return {
            "signals": [s.to_dict() for s in self.signals],
            "metadata": self.metadata
        }


class BacktestEngine:
    """
    回测引擎

    职责:
    - 编排回测执行流程
    - 时间循环模拟（按小时步进）
    - 调用四步系统生成信号
    - 模拟订单执行（滑点模拟）
    - 头寸生命周期跟踪（SL/TP监控）

    配置驱动（config/params.json -> backtest.engine）:
    - batch_size: 批次大小（暂时不用，v1.0单线程）
    - progress_log_interval: 进度日志间隔（每N次迭代）
    - signal_cooldown_hours: 信号冷却期（小时）
    - slippage_percent: 滑点百分比
    - slippage_range: 滑点随机范围
    - position_size_usdt: 仓位大小（USDT）
    - max_holding_hours: 最大持仓时长（小时）
    - enable_anti_jitter: 是否启用Anti-Jitter（2小时冷却）
    - exit_classification: 退出原因分类配置
    """

    def __init__(self, config: Dict, data_loader: HistoricalDataLoader):
        """
        初始化回测引擎

        Args:
            config: 配置字典（从params.json的backtest.engine读取）
            data_loader: 历史数据加载器实例
        """
        self.config = config
        self.data_loader = data_loader

        # §6.2 函数签名演进：所有参数都有默认值（向后兼容）
        self.batch_size = config.get("batch_size", 1)
        self.progress_log_interval = config.get("progress_log_interval", 100)
        self.signal_cooldown_hours = config.get("signal_cooldown_hours", 2)
        self.slippage_percent = config.get("slippage_percent", 0.1)
        self.slippage_range = config.get("slippage_range", 0.05)
        self.position_size_usdt = config.get("position_size_usdt", 100)
        self.max_holding_hours = config.get("max_holding_hours", 168)  # 7天
        self.enable_anti_jitter = config.get("enable_anti_jitter", True)

        # §6.4 分段逻辑配置：退出原因分类
        self.exit_classification = config.get("exit_classification", {
            "sl_hit": {"priority": 1, "label": "SL_HIT"},
            "tp1_hit": {"priority": 2, "label": "TP1_HIT"},
            "tp2_hit": {"priority": 3, "label": "TP2_HIT"},
            "max_holding_exceeded": {"priority": 4, "label": "TIMEOUT"},
            "manual_close": {"priority": 5, "label": "MANUAL"}
        })

        # 重载配置（确保使用最新配置）
        CFG.reload()

        logger.info(
            f"BacktestEngine initialized: "
            f"slippage={self.slippage_percent}±{self.slippage_range}%, "
            f"cooldown={self.signal_cooldown_hours}h, "
            f"max_holding={self.max_holding_hours}h"
        )

    def run(
        self,
        symbols: List[str],
        start_time: int,
        end_time: int,
        interval: Optional[str] = None
    ) -> BacktestResult:
        """
        执行回测

        Args:
            symbols: 交易对列表（如 ["ETHUSDT", "BTCUSDT"]）
            start_time: 开始时间（Unix时间戳，毫秒）
            end_time: 结束时间（Unix时间戳，毫秒）
            interval: K线周期（默认使用data_loader配置）

        Returns:
            BacktestResult: 回测结果（包含所有信号和元数据）

        算法流程:
        1. For each timestamp in [start_time, end_time] (hourly step):
            2. For each symbol:
                3. Fetch historical klines up to current timestamp
                4. Calculate factor scores via analyze_symbol_with_preloaded_klines()
                5. Check if signal generated (four_step_system.decision == ACCEPT)
                6. If signal:
                    7. Check cooldown (Anti-Jitter)
                    8. Simulate order execution (entry price ± slippage)
                    9. Add to active positions
            10. For each active position:
                11. Monitor current candle for SL/TP hit
                12. If hit: close position, record signal
        13. Return BacktestResult with all signals and metadata
        """
        interval = interval or self.data_loader.default_interval
        interval_ms = self._interval_to_ms(interval)

        logger.info(
            f"开始回测: symbols={symbols}, "
            f"time_range={self._format_timestamp(start_time)}-{self._format_timestamp(end_time)}, "
            f"interval={interval}"
        )

        # 统计信息
        total_iterations = 0
        all_signals: List[SimulatedSignal] = []
        active_positions: List[SimulatedSignal] = []
        last_signal_time_by_symbol: Dict[str, int] = {}

        # 开始计时
        backtest_start_time = time.time()

        # 时间循环（按小时步进）
        current_timestamp = start_time

        while current_timestamp <= end_time:
            total_iterations += 1

            # 进度日志
            if total_iterations % self.progress_log_interval == 0:
                logger.info(
                    f"回测进度: {total_iterations} iterations, "
                    f"timestamp={self._format_timestamp(current_timestamp)}, "
                    f"signals={len(all_signals)}, "
                    f"active_positions={len(active_positions)}"
                )

            # 遍历所有符号
            for symbol in symbols:
                try:
                    # 检查冷却期（Anti-Jitter）
                    if self.enable_anti_jitter:
                        last_signal_time = last_signal_time_by_symbol.get(symbol, 0)
                        cooldown_ms = self.signal_cooldown_hours * 3600 * 1000
                        if current_timestamp - last_signal_time < cooldown_ms:
                            # 仍在冷却期，跳过
                            continue

                    # 加载历史K线（up to current_timestamp）
                    # 注意：这里使用current_timestamp - interval_ms作为end_time
                    # 确保不包含当前正在进行的K线（防止未来数据泄漏）
                    klines_1h = self.data_loader.load_klines(
                        symbol,
                        start_time=current_timestamp - 300 * interval_ms,  # 300根K线
                        end_time=current_timestamp - interval_ms,
                        interval=interval
                    )

                    if len(klines_1h) < 100:
                        # K线不足，跳过（避免噪声信号）
                        continue

                    # 转换为Binance原始格式（analyze_symbol_with_preloaded_klines需要）
                    klines_1h_raw = self._convert_to_binance_format(klines_1h)

                    # 调用四步系统分析
                    analysis_result = analyze_symbol_with_preloaded_klines(
                        symbol=symbol,
                        k1h=klines_1h_raw,
                        k4h=[],  # 暂时不用4h K线（v1.0简化）
                        oi_data=None,
                        spot_k1h=None,
                        orderbook=None,
                        mark_price=None,
                        funding_rate=None,
                        spot_price=None,
                        btc_klines=None,
                        eth_klines=None
                    )

                    # 检查是否生成信号
                    is_signal = analysis_result.get("is_prime", False)
                    if not is_signal:
                        continue

                    # 提取信号信息
                    side_long = analysis_result.get("side_long", None)
                    if side_long is None:
                        continue

                    side = "long" if side_long else "short"
                    entry_price_rec = analysis_result.get("entry_price", 0.0)
                    stop_loss_rec = analysis_result.get("stop_loss", 0.0)
                    take_profit_1_rec = analysis_result.get("take_profit_1", 0.0)
                    take_profit_2_rec = analysis_result.get("take_profit_2", 0.0)

                    # 验证价格有效性
                    if entry_price_rec <= 0 or stop_loss_rec <= 0:
                        logger.warning(
                            f"信号价格无效: {symbol} entry={entry_price_rec} sl={stop_loss_rec}"
                        )
                        continue

                    # 创建模拟信号
                    signal = SimulatedSignal(
                        symbol=symbol,
                        timestamp=current_timestamp,
                        side=side,
                        entry_price_recommended=entry_price_rec,
                        stop_loss_recommended=stop_loss_rec,
                        take_profit_1_recommended=take_profit_1_rec,
                        take_profit_2_recommended=take_profit_2_rec,
                        factor_scores=analysis_result.get("scores", {}),
                        step1_result=analysis_result.get("four_step_decision", {}).get("step1", {}),
                        step2_result=analysis_result.get("four_step_decision", {}).get("step2", {}),
                        step3_result=analysis_result.get("four_step_decision", {}).get("step3", {}),
                        step4_result=analysis_result.get("four_step_decision", {}).get("step4", {})
                    )

                    # 模拟订单执行（滑点）
                    self._simulate_order_execution(signal)

                    # 添加到活跃头寸
                    active_positions.append(signal)
                    all_signals.append(signal)

                    # 更新最后信号时间（Anti-Jitter）
                    last_signal_time_by_symbol[symbol] = current_timestamp

                    logger.info(
                        f"📊 信号生成: {symbol} {side.upper()} @ {entry_price_rec:.4f} "
                        f"(SL={stop_loss_rec:.4f}, TP1={take_profit_1_rec:.4f})"
                    )

                except Exception as e:
                    logger.error(f"分析失败: {symbol} at {current_timestamp} - {e}")

            # 监控活跃头寸（检查SL/TP触发）
            active_positions = self._monitor_active_positions(
                active_positions, current_timestamp, interval_ms
            )

            # 移动到下一个时间步
            current_timestamp += interval_ms

        # 回测结束：强制平掉所有未平仓头寸
        for position in active_positions:
            if position.exit_time == 0:
                self._close_position(
                    position,
                    exit_time=end_time,
                    exit_price=position.entry_price_actual,  # 以入场价平仓（无盈亏）
                    exit_reason=self.exit_classification["manual_close"]["label"]
                )

        # 计算执行时长
        backtest_duration = time.time() - backtest_start_time

        # 构建元数据
        metadata = {
            "start_time": start_time,
            "end_time": end_time,
            "symbols": symbols,
            "interval": interval,
            "total_iterations": total_iterations,
            "execution_time_seconds": round(backtest_duration, 2),
            "config_snapshot": self.config,
            "total_signals": len(all_signals),
            "signals_by_symbol": {
                symbol: sum(1 for s in all_signals if s.symbol == symbol)
                for symbol in symbols
            }
        }

        logger.info(
            f"✅ 回测完成: "
            f"{total_iterations} iterations, "
            f"{len(all_signals)} signals, "
            f"{backtest_duration:.1f}秒"
        )

        return BacktestResult(signals=all_signals, metadata=metadata)

    def _simulate_order_execution(self, signal: SimulatedSignal) -> None:
        """
        模拟订单执行（滑点模拟）

        Args:
            signal: 待执行的信号（会修改actual价格字段）

        滑点模型（§6.1 Base + Range模式）:
        - slippage = slippage_percent ± random(slippage_range)
        - 例如: 0.1% ± 0.05% → [0.05%, 0.15%]
        - 做多：entry_actual = entry_rec * (1 + slippage)（稍高买入）
        - 做空：entry_actual = entry_rec * (1 - slippage)（稍低卖出）
        """
        # 计算随机滑点
        slippage = self.slippage_percent + random.uniform(
            -self.slippage_range,
            self.slippage_range
        )
        slippage = max(0.0, slippage)  # 滑点不能为负

        # 计算实际执行价格
        if signal.side == "long":
            # 做多：买入价稍高
            signal.entry_price_actual = signal.entry_price_recommended * (1 + slippage / 100)
            signal.stop_loss_actual = signal.stop_loss_recommended
            signal.take_profit_1_actual = signal.take_profit_1_recommended
            signal.take_profit_2_actual = signal.take_profit_2_recommended
        else:
            # 做空：卖出价稍低
            signal.entry_price_actual = signal.entry_price_recommended * (1 - slippage / 100)
            signal.stop_loss_actual = signal.stop_loss_recommended
            signal.take_profit_1_actual = signal.take_profit_1_recommended
            signal.take_profit_2_actual = signal.take_profit_2_recommended

    def _monitor_active_positions(
        self,
        active_positions: List[SimulatedSignal],
        current_timestamp: int,
        interval_ms: int
    ) -> List[SimulatedSignal]:
        """
        监控活跃头寸（检查SL/TP触发）

        Args:
            active_positions: 当前活跃头寸列表
            current_timestamp: 当前时间戳（毫秒）
            interval_ms: K线周期（毫秒）

        Returns:
            仍然活跃的头寸列表（已平仓的会被移除）

        监控逻辑:
        1. 加载当前K线（包含high/low价格）
        2. 检查SL触发：low ≤ SL (做多) 或 high ≥ SL (做空)
        3. 检查TP触发：high ≥ TP (做多) 或 low ≤ TP (做空)
        4. 检查超时：holding_hours > max_holding_hours
        5. 如果触发任一条件，平仓并移除
        """
        still_active = []

        for position in active_positions:
            # 跳过已平仓的头寸
            if position.exit_time > 0:
                continue

            try:
                # 加载当前K线（仅需1根）
                current_klines = self.data_loader.load_klines(
                    position.symbol,
                    start_time=current_timestamp - interval_ms,
                    end_time=current_timestamp,
                    interval=self.data_loader.default_interval
                )

                if not current_klines:
                    # 无K线数据，保持头寸
                    still_active.append(position)
                    continue

                current_kline = current_klines[-1]
                high = current_kline["high"]
                low = current_kline["low"]

                # 检查止损触发
                sl_hit = self._check_stop_loss_hit(position, high, low)
                if sl_hit:
                    self._close_position(
                        position,
                        exit_time=current_timestamp,
                        exit_price=position.stop_loss_actual,
                        exit_reason=self.exit_classification["sl_hit"]["label"]
                    )
                    continue

                # 检查止盈触发
                tp_hit, tp_level = self._check_take_profit_hit(position, high, low)
                if tp_hit:
                    tp_price = (
                        position.take_profit_1_actual if tp_level == 1
                        else position.take_profit_2_actual
                    )
                    exit_label = self.exit_classification[f"tp{tp_level}_hit"]["label"]
                    self._close_position(
                        position,
                        exit_time=current_timestamp,
                        exit_price=tp_price,
                        exit_reason=exit_label
                    )
                    continue

                # 检查超时
                holding_hours = (current_timestamp - position.timestamp) / (3600 * 1000)
                if holding_hours > self.max_holding_hours:
                    # 超时强平：使用当前价格（近似）
                    exit_price = (high + low) / 2
                    self._close_position(
                        position,
                        exit_time=current_timestamp,
                        exit_price=exit_price,
                        exit_reason=self.exit_classification["max_holding_exceeded"]["label"]
                    )
                    continue

                # 仍然活跃
                still_active.append(position)

            except Exception as e:
                logger.error(f"头寸监控失败: {position.symbol} - {e}")
                still_active.append(position)

        return still_active

    def _check_stop_loss_hit(
        self,
        position: SimulatedSignal,
        high: float,
        low: float
    ) -> bool:
        """
        检查止损是否触发

        Args:
            position: 头寸
            high: 当前K线最高价
            low: 当前K线最低价

        Returns:
            True=止损触发，False=未触发
        """
        if position.side == "long":
            # 做多：最低价 ≤ 止损价
            return low <= position.stop_loss_actual
        else:
            # 做空：最高价 ≥ 止损价
            return high >= position.stop_loss_actual

    def _check_take_profit_hit(
        self,
        position: SimulatedSignal,
        high: float,
        low: float
    ) -> tuple[bool, int]:
        """
        检查止盈是否触发

        Args:
            position: 头寸
            high: 当前K线最高价
            low: 当前K线最低价

        Returns:
            (hit, tp_level): hit=是否触发, tp_level=触发的TP级别(1或2)

        止盈优先级:
        - TP2优先级高于TP1（如果两者都触发，认为触发TP2）
        """
        if position.side == "long":
            # 做多：最高价 ≥ 止盈价
            if position.take_profit_2_actual > 0 and high >= position.take_profit_2_actual:
                return (True, 2)
            elif position.take_profit_1_actual > 0 and high >= position.take_profit_1_actual:
                return (True, 1)
        else:
            # 做空：最低价 ≤ 止盈价
            if position.take_profit_2_actual > 0 and low <= position.take_profit_2_actual:
                return (True, 2)
            elif position.take_profit_1_actual > 0 and low <= position.take_profit_1_actual:
                return (True, 1)

        return (False, 0)

    def _close_position(
        self,
        position: SimulatedSignal,
        exit_time: int,
        exit_price: float,
        exit_reason: str
    ) -> None:
        """
        平仓（更新头寸信息）

        Args:
            position: 头寸（会修改exit字段）
            exit_time: 退出时间（毫秒）
            exit_price: 退出价格
            exit_reason: 退出原因
        """
        position.exit_time = exit_time
        position.exit_price = exit_price
        position.exit_reason = exit_reason

        # 计算盈亏
        if position.side == "long":
            pnl_pct = (exit_price - position.entry_price_actual) / position.entry_price_actual * 100
        else:
            pnl_pct = (position.entry_price_actual - exit_price) / position.entry_price_actual * 100

        position.pnl_percent = round(pnl_pct, 2)
        position.pnl_usdt = round(self.position_size_usdt * pnl_pct / 100, 2)

        # 计算持仓时长
        position.holding_hours = round(
            (exit_time - position.timestamp) / (3600 * 1000),
            2
        )

        logger.info(
            f"📉 平仓: {position.symbol} {position.side.upper()} "
            f"PnL={position.pnl_percent:+.2f}% ({position.pnl_usdt:+.2f} USDT), "
            f"holding={position.holding_hours:.1f}h, "
            f"reason={exit_reason}"
        )

    def _convert_to_binance_format(self, klines_dict: List[Dict]) -> List[list]:
        """
        转换为Binance原始格式（analyze_symbol_with_preloaded_klines需要）

        Args:
            klines_dict: 字典格式K线

        Returns:
            Binance原始格式K线（二维数组）
        """
        klines_raw = []
        for k in klines_dict:
            klines_raw.append([
                k["timestamp"],
                k["open"],
                k["high"],
                k["low"],
                k["close"],
                k["volume"],
                k["close_time"],
                k["quote_volume"],
                k["trades"],
                k["taker_buy_base"],
                k["taker_buy_quote"],
                0  # ignore field
            ])
        return klines_raw

    def _interval_to_ms(self, interval: str) -> int:
        """
        将K线周期转换为毫秒

        Args:
            interval: K线周期（如 "1m", "1h", "1d"）

        Returns:
            毫秒数
        """
        unit = interval[-1]
        value = int(interval[:-1])

        if unit == 'm':
            return value * 60 * 1000
        elif unit == 'h':
            return value * 60 * 60 * 1000
        elif unit == 'd':
            return value * 24 * 60 * 60 * 1000
        elif unit == 'w':
            return value * 7 * 24 * 60 * 60 * 1000
        elif unit == 'M':
            return value * 30 * 24 * 60 * 60 * 1000
        else:
            raise ValueError(f"不支持的K线周期: {interval}")

    def _format_timestamp(self, timestamp_ms: int) -> str:
        """
        格式化时间戳（用于日志）

        Args:
            timestamp_ms: 时间戳（毫秒）

        Returns:
            格式化字符串（如 "2024-08-01 00:00:00"）
        """
        from datetime import datetime
        dt = datetime.fromtimestamp(timestamp_ms / 1000)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
