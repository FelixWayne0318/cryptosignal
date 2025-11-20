# coding: utf-8
"""
Backtest Framework v1.5 - Backtest Engine (P0 Fixes)
回测框架 - 回测引擎（生产级修复）

功能：
1. 时间循环模拟（按小时步进）
2. 调用四步系统生成信号
3. 模拟订单执行（限价单模型、滑点、手续费）
4. 头寸生命周期跟踪（悲观SL/TP监控）
5. 结果收集与返回

v1.5 P0修复（专家方案）:
- 限价单模型：信号t生成，t+1开始尝试成交，max_entry_bars有效期
- 手续费建模：双边Taker手续费（0.05%），从PnL扣除
- 悲观SL/TP假设：同bar触发时优先止损

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

    v1.5 P0修复：添加限价单模型字段
    - entry_attempt_time: 开始尝试入场的时间
    - entry_filled_time: 实际成交时间
    - entry_filled: 是否成功入场
    - fees_paid: 已支付的手续费

    设计原则（§6.2 函数签名演进）:
    - 所有字段初始化有默认值
    - 新增字段向后兼容
    """
    # 基本信息
    symbol: str
    timestamp: int  # 信号生成时间（决策时刻，bar close，毫秒）
    side: str  # "long" | "short"

    # 推荐价格（从Step3获取）
    entry_price_recommended: float
    stop_loss_recommended: float
    take_profit_1_recommended: float
    take_profit_2_recommended: float

    # v1.5 P0修复：入场执行信息（限价单模型）
    entry_attempt_time: int = 0  # 开始尝试入场的时间（timestamp + 1h，毫秒）
    entry_filled_time: int = 0   # 实际成交时间（0表示未成交）
    entry_filled: bool = False   # 是否成功入场

    # 实际执行价格（模拟滑点后）
    entry_price_actual: float = 0.0
    stop_loss_actual: float = 0.0
    take_profit_1_actual: float = 0.0
    take_profit_2_actual: float = 0.0

    # 退出信息
    exit_time: int = 0  # 退出时间（毫秒）
    exit_price: float = 0.0
    exit_reason: str = ""  # "SL_HIT" | "TP1_HIT" | "TP2_HIT" | "TIMEOUT" | "MANUAL" | "ENTRY_NOT_FILLED"

    # 盈亏信息
    pnl_percent: float = 0.0  # (exit - entry) / entry * 100
    pnl_usdt: float = 0.0  # 假设100 USDT仓位（v1.0简化版）

    # v1.5 P0修复：手续费信息
    fees_paid: float = 0.0  # 已支付的手续费（USDT）

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
class RejectedAnalysis:
    """
    v1.1增强：REJECT分析记录（用于计算真实Step通过率）

    记录四步系统分析过程中被拒绝的信号，包含：
    - 哪一步被拒绝
    - 各步骤的结果
    - 因子分数快照

    设计原则（§6.2 函数签名演进）:
    - 所有字段初始化有默认值
    - 新增字段向后兼容
    """
    # 基本信息
    symbol: str
    timestamp: int  # 分析时间（bar close，毫秒）

    # 拒绝信息
    rejection_step: int = 0  # 被拒绝的步骤（1-4），0表示未被分析
    rejection_reason: str = ""  # 拒绝原因

    # 各步骤通过状态
    step1_passed: bool = False
    step2_passed: bool = False
    step3_passed: bool = False
    step4_passed: bool = False

    # 四步系统元数据（可选，用于调试）
    step1_result: Dict = field(default_factory=dict)
    step2_result: Dict = field(default_factory=dict)
    step3_result: Dict = field(default_factory=dict)
    step4_result: Dict = field(default_factory=dict)

    # 因子分数快照（可选）
    factor_scores: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """转换为字典（用于JSON序列化）"""
        return asdict(self)


@dataclass
class BacktestResult:
    """
    回测执行结果

    包含:
    - signals: 所有模拟信号列表（ACCEPT）
    - rejected_analyses: 所有被拒绝的分析列表（REJECT）[v1.1新增]
    - metadata: 执行元数据（时间范围、符号、执行时长等）
    """
    signals: List[SimulatedSignal]
    metadata: Dict[str, Any]
    rejected_analyses: List[RejectedAnalysis] = field(default_factory=list)  # v1.1新增

    def to_dict(self) -> Dict:
        """转换为字典（用于JSON序列化）"""
        return {
            "signals": [s.to_dict() for s in self.signals],
            "rejected_analyses": [r.to_dict() for r in self.rejected_analyses],  # v1.1新增
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
    - max_entry_bars: 限价单有效期（1h bar数）[v1.5新增]
    - taker_fee_rate: Taker手续费率 [v1.5新增]
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

        # v1.5 P0修复：限价单模型配置
        self.max_entry_bars = config.get("max_entry_bars", 4)  # 默认4h有效期
        self.taker_fee_rate = config.get("taker_fee_rate", 0.0005)  # 默认0.05%手续费

        self.slippage_percent = config.get("slippage_percent", 0.02)  # v1.5调整：从0.1%降至0.02%
        self.slippage_range = config.get("slippage_range", 0.01)  # v1.5调整：从0.05%降至0.01%
        self.position_size_usdt = config.get("position_size_usdt", 100)
        self.max_holding_hours = config.get("max_holding_hours", 168)  # 7天
        self.enable_anti_jitter = config.get("enable_anti_jitter", True)

        # §6.4 分段逻辑配置：退出原因分类
        self.exit_classification = config.get("exit_classification", {
            "sl_hit": {"priority": 1, "label": "SL_HIT"},
            "tp1_hit": {"priority": 2, "label": "TP1_HIT"},
            "tp2_hit": {"priority": 3, "label": "TP2_HIT"},
            "max_holding_exceeded": {"priority": 4, "label": "TIMEOUT"},
            "manual_close": {"priority": 5, "label": "MANUAL"},
            "entry_not_filled": {"priority": 6, "label": "ENTRY_NOT_FILLED"}  # v1.5新增
        })

        # v1.1增强：REJECT信号记录配置
        self.record_reject_analyses = config.get("record_reject_analyses", False)
        reject_fields_config = config.get("reject_analysis_fields", {})
        self.reject_record_factor_scores = reject_fields_config.get("record_factor_scores", True)
        self.reject_record_step_results = reject_fields_config.get("record_step_results", True)
        self.reject_record_rejection_reason = reject_fields_config.get("record_rejection_reason", True)

        # 重载配置（确保使用最新配置）
        CFG.reload()

        logger.info(
            f"BacktestEngine initialized (v1.5/v1.1): "
            f"max_entry_bars={self.max_entry_bars}, "
            f"fee={self.taker_fee_rate*100:.3f}%, "
            f"slippage={self.slippage_percent}±{self.slippage_range}%, "
            f"cooldown={self.signal_cooldown_hours}h, "
            f"record_rejects={self.record_reject_analyses}"
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

        算法流程 (v1.5 限价单模型):
        1. For each timestamp in [start_time, end_time] (hourly step):
            2. Try to fill pending entry orders (limit order model)
            3. For each symbol:
                4. Fetch historical klines up to current timestamp
                5. Calculate factor scores via analyze_symbol_with_preloaded_klines()
                6. Check if signal generated (four_step_system.decision == ACCEPT)
                7. If signal:
                    8. Check cooldown (Anti-Jitter)
                    9. Add to pending_entries queue (entry attempt starts at t+1)
            10. For each active position:
                11. Monitor current candle for SL/TP hit (pessimistic assumption)
                12. If hit: close position, record signal
            13. Expire pending entries that exceed max_entry_bars
        14. Return BacktestResult with all signals and metadata
        """
        interval = interval or self.data_loader.default_interval
        interval_ms = self._interval_to_ms(interval)

        logger.info(
            f"开始回测 (v1.6一次性预加载): symbols={symbols}, "
            f"time_range={self._format_timestamp(start_time)}-{self._format_timestamp(end_time)}, "
            f"interval={interval}, max_entry_bars={self.max_entry_bars}"
        )

        # ==================== v1.6优化：一次性预加载所有数据 ====================
        # 优势：减少API调用次数，显著提升回测性能（10-50倍）
        preloaded_data = self.data_loader.preload_backtest_data(
            symbols=symbols,
            start_time=start_time,
            end_time=end_time,
            interval=interval,
            lookback_bars=300
        )
        # ====================================================================

        # 统计信息
        total_iterations = 0
        all_signals: List[SimulatedSignal] = []
        rejected_analyses: List[RejectedAnalysis] = []  # v1.1新增：被拒绝的分析记录
        active_positions: List[SimulatedSignal] = []
        pending_entries: List[SimulatedSignal] = []  # v1.5新增：待入场队列
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
                    f"active_positions={len(active_positions)}, "
                    f"pending_entries={len(pending_entries)}"
                )

            # ==================== v1.6优化：从预加载数据获取K线切片 ====================
            # 优势：无需每次迭代调用API/缓存，直接从内存切片
            # 用途：
            # 1. 限价单成交检查（_try_fill_pending_entry）
            # 2. 头寸监控（_monitor_active_positions）
            # 3. 信号生成（analyze_symbol）
            current_klines_cache = {}

            # 获取BTC K线切片（用于Step1 BTC对齐检测）
            btc_klines = self.data_loader.get_klines_slice(
                preloaded_data.get("BTCUSDT", []),
                current_timestamp,
                lookback_bars=300
            )

            # 获取所有symbol的K线切片（信号生成用）
            for symbol in symbols:
                klines = self.data_loader.get_klines_slice(
                    preloaded_data.get(symbol, []),
                    current_timestamp,
                    lookback_bars=300
                )
                current_klines_cache[symbol] = klines
            # ===============================================================

            # v1.5 P0修复：尝试成交待入场订单（限价单模型）
            filled_entries = []
            expired_entries = []

            for pending in pending_entries:
                # 检查是否到达入场尝试时间
                if current_timestamp < pending.entry_attempt_time:
                    continue  # 尚未到达入场时间

                # 尝试成交限价单（使用缓存的K线）
                filled, expired = self._try_fill_pending_entry(
                    pending, current_timestamp, interval_ms, current_klines_cache
                )

                if filled:
                    # 成交成功：添加到活跃头寸
                    active_positions.append(pending)
                    filled_entries.append(pending)
                    logger.info(
                        f"✅ 限价单成交: {pending.symbol} {pending.side.upper()} @ {pending.entry_price_actual:.4f} "
                        f"(delay={(current_timestamp - pending.timestamp) / 3600000:.1f}h)"
                    )
                elif expired:
                    # 超时未成交：标记为ENTRY_NOT_FILLED
                    expired_entries.append(pending)
                    logger.info(
                        f"⏱️ 限价单超时: {pending.symbol} {pending.side.upper()} "
                        f"(waited={(current_timestamp - pending.entry_attempt_time) / 3600000:.1f}h)"
                    )

            # 移除已成交和已超时的订单
            for entry in filled_entries + expired_entries:
                pending_entries.remove(entry)

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

                    # P0 Bugfix: 使用缓存的K线（避免重复API调用）
                    klines_1h = current_klines_cache.get(symbol, [])

                    if len(klines_1h) < 100:
                        # K线不足，跳过（避免噪声信号）
                        continue

                    # v1.5 P0 Bugfix: 直接传递字典格式（四步系统期望字典格式）
                    # data_loader.load_klines()已返回字典格式，不需要转换
                    # 移除_convert_to_binance_format()调用，避免Step2崩溃

                    # P0 Bugfix: 传递BTC K线（用于Step1 BTC对齐检测）
                    # 调用四步系统分析
                    analysis_result = analyze_symbol_with_preloaded_klines(
                        symbol=symbol,
                        k1h=klines_1h,  # 直接传递字典格式（从缓存读取）
                        k4h=[],  # 暂时不用4h K线（v1.0简化）
                        oi_data=None,
                        spot_k1h=None,
                        orderbook=None,
                        mark_price=None,
                        funding_rate=None,
                        spot_price=None,
                        btc_klines=btc_klines,  # P0 Bugfix: 传递BTC K线
                        eth_klines=None
                    )

                    # 检查是否生成信号
                    is_signal = analysis_result.get("is_prime", False)

                    # v1.1增强：记录REJECT分析结果
                    if not is_signal and self.record_reject_analyses:
                        four_step = analysis_result.get("four_step_decision", {})

                        # 提取各步骤结果
                        step1_result = four_step.get("step1", {})
                        step2_result = four_step.get("step2", {})
                        step3_result = four_step.get("step3", {})
                        step4_result = four_step.get("step4", {})

                        # 判断各步骤是否通过
                        step1_passed = step1_result.get("passed", False)
                        step2_passed = step2_result.get("passed", False)
                        step3_passed = step3_result.get("passed", False)
                        step4_passed = step4_result.get("passed", False)

                        # 确定拒绝步骤和原因
                        rejection_step = 0
                        rejection_reason = ""
                        if not step1_passed:
                            rejection_step = 1
                            rejection_reason = step1_result.get("reason", "Step1 REJECT")
                        elif not step2_passed:
                            rejection_step = 2
                            rejection_reason = step2_result.get("reason", "Step2 REJECT")
                        elif not step3_passed:
                            rejection_step = 3
                            rejection_reason = step3_result.get("reason", "Step3 REJECT")
                        elif not step4_passed:
                            rejection_step = 4
                            rejection_reason = step4_result.get("reason", "Step4 REJECT")
                        else:
                            # 未知原因（可能是数据不足等）
                            rejection_step = 0
                            rejection_reason = "Unknown (possibly insufficient data)"

                        # 创建RejectedAnalysis记录
                        rejected = RejectedAnalysis(
                            symbol=symbol,
                            timestamp=current_timestamp,
                            rejection_step=rejection_step,
                            rejection_reason=rejection_reason if self.reject_record_rejection_reason else "",
                            step1_passed=step1_passed,
                            step2_passed=step2_passed,
                            step3_passed=step3_passed,
                            step4_passed=step4_passed,
                            step1_result=step1_result if self.reject_record_step_results else {},
                            step2_result=step2_result if self.reject_record_step_results else {},
                            step3_result=step3_result if self.reject_record_step_results else {},
                            step4_result=step4_result if self.reject_record_step_results else {},
                            factor_scores=analysis_result.get("scores", {}) if self.reject_record_factor_scores else {}
                        )
                        rejected_analyses.append(rejected)

                    if not is_signal:
                        continue

                    # 提取信号信息
                    side_long = analysis_result.get("side_long", None)
                    if side_long is None:
                        continue

                    side = "long" if side_long else "short"

                    # ==================== P0修复：正确提取价格（融合模式 vs 旧系统） ====================
                    # 检查是否启用了融合模式（四步系统决策结果存在）
                    four_step = analysis_result.get("four_step_decision", {})
                    fusion_mode_enabled = (
                        four_step and
                        four_step.get("decision") == "ACCEPT"
                    )

                    if fusion_mode_enabled:
                        # 融合模式：四步系统直接提供浮点数价格
                        entry_price_rec = analysis_result.get("entry_price", 0.0)
                        stop_loss_rec = analysis_result.get("stop_loss", 0.0)
                        take_profit_1_rec = analysis_result.get("take_profit", 0.0)  # 注意：字段名是take_profit
                        take_profit_2_rec = 0.0  # 四步系统暂不支持TP2

                        logger.debug(
                            f"[融合模式] {symbol} Entry={entry_price_rec:.4f}, "
                            f"SL={stop_loss_rec:.4f}, TP={take_profit_1_rec:.4f}"
                        )
                    else:
                        # 旧系统：从字典结构提取价格
                        stop_loss_dict = analysis_result.get("stop_loss", {})
                        take_profit_dict = analysis_result.get("take_profit", {})

                        # 提取止损价格（从字典）
                        if isinstance(stop_loss_dict, dict):
                            stop_loss_rec = stop_loss_dict.get("stop_price", 0.0)
                        else:
                            logger.warning(f"{symbol} stop_loss格式异常: {type(stop_loss_dict)}")
                            stop_loss_rec = float(stop_loss_dict) if stop_loss_dict else 0.0

                        # 提取止盈价格（从字典）
                        if isinstance(take_profit_dict, dict):
                            take_profit_1_rec = take_profit_dict.get("price", 0.0)
                        else:
                            logger.warning(f"{symbol} take_profit格式异常: {type(take_profit_dict)}")
                            take_profit_1_rec = float(take_profit_dict) if take_profit_dict else 0.0

                        take_profit_2_rec = 0.0  # 旧系统也不支持TP2

                        # 入场价格：使用当前K线最后一根的收盘价
                        if klines_1h and len(klines_1h) > 0:
                            last_kline = klines_1h[-1]
                            if isinstance(last_kline, dict):
                                entry_price_rec = last_kline.get("close", 0.0)
                            else:
                                entry_price_rec = last_kline[4] if len(last_kline) > 4 else 0.0
                        else:
                            entry_price_rec = 0.0

                        logger.debug(
                            f"[旧系统] {symbol} Entry={entry_price_rec:.4f}(K线close), "
                            f"SL={stop_loss_rec:.4f}, TP={take_profit_1_rec:.4f}"
                        )

                    # 验证价格有效性
                    if entry_price_rec <= 0 or stop_loss_rec <= 0:
                        logger.warning(
                            f"信号价格无效: {symbol} entry={entry_price_rec} sl={stop_loss_rec}"
                        )
                        continue

                    # 验证止盈价格（允许为0，但记录警告并计算默认TP）
                    if take_profit_1_rec <= 0:
                        logger.warning(
                            f"止盈价格无效: {symbol} tp1={take_profit_1_rec}，使用2R作为默认TP"
                        )
                        # 计算默认TP（2倍风险回报）
                        risk_distance = abs(entry_price_rec - stop_loss_rec)
                        if side == "long":
                            take_profit_1_rec = entry_price_rec + (risk_distance * 2)
                        else:
                            take_profit_1_rec = entry_price_rec - (risk_distance * 2)
                    # =============================================================================

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

                    # v1.5 P0修复：不立即执行，加入待入场队列（限价单模型）
                    signal.entry_attempt_time = current_timestamp + interval_ms  # 下一个bar开始尝试
                    pending_entries.append(signal)
                    all_signals.append(signal)  # 记录信号（无论是否最终成交）

                    # 更新最后信号时间（Anti-Jitter）
                    last_signal_time_by_symbol[symbol] = current_timestamp

                    logger.info(
                        f"📊 信号生成: {symbol} {side.upper()} @ {entry_price_rec:.4f} "
                        f"(SL={stop_loss_rec:.4f}, TP1={take_profit_1_rec:.4f}) "
                        f"[pending entry attempt at {self._format_timestamp(signal.entry_attempt_time)}]"
                    )

                except Exception as e:
                    logger.error(f"分析失败: {symbol} at {current_timestamp} - {e}")

            # 监控活跃头寸（检查SL/TP触发，使用缓存的K线）
            active_positions = self._monitor_active_positions(
                active_positions, current_timestamp, interval_ms, current_klines_cache
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
            "total_rejected_analyses": len(rejected_analyses),  # v1.1新增
            "signals_by_symbol": {
                symbol: sum(1 for s in all_signals if s.symbol == symbol)
                for symbol in symbols
            },
            "rejected_by_symbol": {  # v1.1新增
                symbol: sum(1 for r in rejected_analyses if r.symbol == symbol)
                for symbol in symbols
            }
        }

        logger.info(
            f"✅ 回测完成: "
            f"{total_iterations} iterations, "
            f"{len(all_signals)} signals, "
            f"{len(rejected_analyses)} rejects, "
            f"{backtest_duration:.1f}秒"
        )

        return BacktestResult(
            signals=all_signals,
            metadata=metadata,
            rejected_analyses=rejected_analyses  # v1.1新增
        )

    def _try_fill_pending_entry(
        self,
        signal: SimulatedSignal,
        current_timestamp: int,
        interval_ms: int,
        klines_cache: Dict[str, List[Dict]]
    ) -> tuple[bool, bool]:
        """
        尝试成交待入场限价单（v1.5 P0修复）

        Args:
            signal: 待入场信号
            current_timestamp: 当前时间戳（毫秒）
            interval_ms: K线周期（毫秒）
            klines_cache: K线缓存字典 (P0 Bugfix: 避免重复API调用)

        Returns:
            (filled, expired): filled=是否成交, expired=是否超时

        限价单成交逻辑:
        - 检查当前bar的high/low是否覆盖推荐入场价
        - 做多：low <= entry_price_recommended <= high → 成交
        - 做空：同样逻辑
        - 如果成交：应用滑点、计算手续费、标记entry_filled=True
        - 如果超时（waited > max_entry_bars）：标记为ENTRY_NOT_FILLED
        """
        # 检查是否超时
        bars_waited = (current_timestamp - signal.entry_attempt_time) // interval_ms
        if bars_waited >= self.max_entry_bars:
            # 超时未成交
            signal.exit_reason = self.exit_classification["entry_not_filled"]["label"]
            signal.exit_time = current_timestamp
            return (False, True)

        # P0 Bugfix: 使用缓存的K线（避免重复API调用）
        try:
            current_klines = klines_cache.get(signal.symbol, [])

            if not current_klines:
                return (False, False)  # 无K线数据，继续等待

            current_kline = current_klines[-1]
            high = current_kline["high"]
            low = current_kline["low"]

            # 检查是否可以成交（推荐价格在当前bar的范围内）
            entry_rec = signal.entry_price_recommended
            can_fill = low <= entry_rec <= high

            if can_fill:
                # 成交！应用滑点模拟
                self._simulate_order_execution(signal)

                # 标记成交
                signal.entry_filled = True
                signal.entry_filled_time = current_timestamp

                # 计算入场手续费
                entry_fee = self._calculate_fees(signal.entry_price_actual, self.position_size_usdt)
                signal.fees_paid += entry_fee

                return (True, False)
            else:
                # 未成交，继续等待
                return (False, False)

        except Exception as e:
            logger.error(f"限价单成交检查失败: {signal.symbol} - {e}")
            return (False, False)

    def _simulate_order_execution(self, signal: SimulatedSignal) -> None:
        """
        模拟订单执行（滑点模拟）

        Args:
            signal: 待执行的信号（会修改actual价格字段）

        滑点模型（§6.1 Base + Range模式）:
        - slippage = slippage_percent ± random(slippage_range)
        - 例如: 0.02% ± 0.01% → [0.01%, 0.03%]
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

    def _calculate_fees(self, price: float, position_size_usdt: float) -> float:
        """
        计算交易手续费（v1.5 P0修复）

        Args:
            price: 成交价格
            position_size_usdt: 仓位大小（USDT）

        Returns:
            手续费（USDT）

        手续费模型:
        - Taker手续费率：0.05% (默认值，从配置读取)
        - 费用 = 名义价值 * 手续费率
        - 名义价值 = position_size_usdt (简化版，v1.0使用固定仓位)
        - 双边收费：入场 + 出场各收一次
        """
        notional_value = position_size_usdt
        fee = notional_value * self.taker_fee_rate
        return round(fee, 4)

    def _monitor_active_positions(
        self,
        active_positions: List[SimulatedSignal],
        current_timestamp: int,
        interval_ms: int,
        klines_cache: Dict[str, List[Dict]]
    ) -> List[SimulatedSignal]:
        """
        监控活跃头寸（检查SL/TP触发）

        Args:
            active_positions: 当前活跃头寸列表
            current_timestamp: 当前时间戳（毫秒）
            interval_ms: K线周期（毫秒）
            klines_cache: K线缓存字典 (P0 Bugfix: 避免重复API调用)

        Returns:
            仍然活跃的头寸列表（已平仓的会被移除）

        监控逻辑 (v1.5 P0修复 - 悲观假设):
        1. 从缓存读取当前K线（包含high/low价格）
        2. 检查SL触发：low ≤ SL (做多) 或 high ≥ SL (做空)
        3. 检查TP触发：high ≥ TP (做多) 或 low ≤ TP (做空)
        4. **悲观假设**：如果SL和TP同时触发，优先认为SL触发（先检查SL）
        5. 检查超时：holding_hours > max_holding_hours
        6. 如果触发任一条件，平仓并移除
        """
        still_active = []

        for position in active_positions:
            # 跳过已平仓的头寸
            if position.exit_time > 0:
                continue

            try:
                # P0 Bugfix: 使用缓存的K线（避免重复API调用）
                current_klines = klines_cache.get(position.symbol, [])

                if not current_klines:
                    # 无K线数据，保持头寸
                    still_active.append(position)
                    continue

                current_kline = current_klines[-1]
                high = current_kline["high"]
                low = current_kline["low"]

                # v1.5 P0修复：悲观假设 - 先检查SL，如果同时触发则优先SL
                sl_hit = self._check_stop_loss_hit(position, high, low)
                tp_hit, tp_level = self._check_take_profit_hit(position, high, low)

                if sl_hit and tp_hit:
                    # 同时触发：悲观假设，认为SL先触发
                    logger.debug(
                        f"⚠️ SL/TP同时触发（悲观假设）: {position.symbol} "
                        f"SL={position.stop_loss_actual:.4f}, TP={position.take_profit_1_actual:.4f}, "
                        f"bar_range=[{low:.4f}, {high:.4f}] → 优先SL"
                    )

                if sl_hit:
                    # 止损触发（或SL/TP同时触发时优先止损）
                    self._close_position(
                        position,
                        exit_time=current_timestamp,
                        exit_price=position.stop_loss_actual,
                        exit_reason=self.exit_classification["sl_hit"]["label"]
                    )
                    continue

                if tp_hit:
                    # 止盈触发（仅当SL未触发时）
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

        v1.5 P0修复:
        - 计算出场手续费
        - PnL减去总手续费（入场+出场）
        """
        position.exit_time = exit_time
        position.exit_price = exit_price
        position.exit_reason = exit_reason

        # v1.5 P0修复：计算出场手续费
        exit_fee = self._calculate_fees(exit_price, self.position_size_usdt)
        position.fees_paid += exit_fee

        # 计算盈亏（百分比）
        if position.side == "long":
            pnl_pct = (exit_price - position.entry_price_actual) / position.entry_price_actual * 100
        else:
            pnl_pct = (position.entry_price_actual - exit_price) / position.entry_price_actual * 100

        position.pnl_percent = round(pnl_pct, 2)

        # v1.5 P0修复：PnL减去手续费
        pnl_usdt_gross = self.position_size_usdt * pnl_pct / 100
        pnl_usdt_net = pnl_usdt_gross - position.fees_paid
        position.pnl_usdt = round(pnl_usdt_net, 2)

        # 计算持仓时长
        position.holding_hours = round(
            (exit_time - position.timestamp) / (3600 * 1000),
            2
        )

        logger.info(
            f"📉 平仓: {position.symbol} {position.side.upper()} "
            f"PnL={position.pnl_percent:+.2f}% ({position.pnl_usdt:+.2f} USDT net), "
            f"fees={position.fees_paid:.2f} USDT, "
            f"holding={position.holding_hours:.1f}h, "
            f"reason={exit_reason}"
        )

    def _convert_to_binance_format(self, klines_dict: List[Dict]) -> List[list]:
        """
        转换为Binance原始格式（已废弃 - v1.5 P0 Bugfix）

        DEPRECATED: 此方法已废弃，不再使用。

        原因：四步系统期望字典格式K线，而非Binance原始格式。
        data_loader.load_klines()已返回字典格式，直接传递即可。

        保留此方法仅用于代码历史参考，将来可能移除。

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
