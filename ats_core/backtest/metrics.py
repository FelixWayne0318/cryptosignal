# coding: utf-8
"""
Backtest Framework v1.0 - Performance Metrics
回测框架 - 性能评估器

功能：
1. 信号级指标（胜率、平均RR、PnL统计）
2. 步骤级指标（Step1-4通过率）
3. 组合级指标（Sharpe、Sortino、最大回撤）
4. 分布分析（PnL直方图、持仓时长分布）
5. 报告生成（JSON/Markdown/CSV格式）

Standard: SYSTEM_ENHANCEMENT_STANDARD.md v3.3.0
Design: docs/BACKTEST_FRAMEWORK_v1.0_DESIGN.md
"""

from __future__ import annotations

import json
import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from statistics import mean, median, stdev
from typing import Dict, List, Optional

from ats_core.backtest.engine import BacktestResult, SimulatedSignal, RejectedAnalysis

logger = logging.getLogger(__name__)


@dataclass
class SignalMetrics:
    """信号级指标"""
    total_signals: int
    win_count: int
    loss_count: int
    win_rate: float  # %
    avg_pnl_percent: float
    median_pnl_percent: float
    max_pnl_percent: float
    min_pnl_percent: float
    std_pnl_percent: float
    avg_rr_ratio: float
    max_consecutive_wins: int
    max_consecutive_losses: int
    avg_holding_hours: float
    median_holding_hours: float


@dataclass
class StepMetrics:
    """步骤级指标（四步系统瓶颈分析）"""
    step1_pass_rate: float  # %
    step2_pass_rate: float  # %
    step3_pass_rate: float  # %
    step4_pass_rate: float  # %
    final_pass_rate: float  # %
    bottleneck_step: int  # 1-4，最低通过率的步骤


@dataclass
class PortfolioMetrics:
    """组合级指标"""
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_percent: float
    max_concurrent_positions: int
    avg_trades_per_day: float
    profit_factor: float  # gross_profit / gross_loss
    total_pnl_usdt: float
    total_pnl_percent: float


@dataclass
class DistributionMetrics:
    """分布分析指标"""
    pnl_histogram: Dict[str, int]  # {bin_label: count}
    holding_time_histogram: Dict[str, int]  # {bin_label: count}
    win_rate_by_direction: Dict[str, float]  # {long/short: win_rate}
    avg_pnl_by_direction: Dict[str, float]  # {long/short: avg_pnl}


@dataclass
class MetricsReport:
    """完整指标报告"""
    signal_metrics: SignalMetrics
    step_metrics: StepMetrics
    portfolio_metrics: PortfolioMetrics
    distribution_metrics: DistributionMetrics
    timestamp_generated: int


class BacktestMetrics:
    """
    回测性能评估器

    职责:
    - 计算信号级/步骤级/组合级/分布级指标
    - 生成人类可读报告（JSON/Markdown/CSV）

    配置驱动（config/params.json -> backtest.metrics）:
    - min_signals_for_stats: 最少信号数（用于统计）
    - confidence_level: 置信水平（统计检验）
    - risk_free_rate: 无风险利率（Sharpe比率）
    - pnl_histogram_bins: PnL直方图分箱
    - holding_time_bins_hours: 持仓时长分箱
    """

    def __init__(self, config: Dict):
        """
        初始化性能评估器

        Args:
            config: 配置字典（从params.json的backtest.metrics读取）
        """
        self.config = config

        # §6.2 函数签名演进：所有参数都有默认值（向后兼容）
        self.min_signals_for_stats = config.get("min_signals_for_stats", 10)
        self.confidence_level = config.get("confidence_level", 0.95)
        self.risk_free_rate = config.get("risk_free_rate", 0.03)  # 年化3%
        self.pnl_histogram_bins = config.get(
            "pnl_histogram_bins",
            [-10, -5, -2, 0, 2, 5, 10, 20]
        )
        self.holding_time_bins = config.get(
            "holding_time_bins_hours",
            [1, 6, 12, 24, 48, 72, 168]
        )

        logger.info(
            f"BacktestMetrics initialized: "
            f"min_signals={self.min_signals_for_stats}, "
            f"confidence={self.confidence_level}, "
            f"risk_free_rate={self.risk_free_rate}"
        )

    def calculate_all_metrics(self, backtest_result: BacktestResult) -> MetricsReport:
        """
        计算所有指标

        Args:
            backtest_result: 回测结果

        Returns:
            完整指标报告
        """
        signals = backtest_result.signals

        if len(signals) < self.min_signals_for_stats:
            logger.warning(
                f"信号数量不足（{len(signals)} < {self.min_signals_for_stats}），"
                f"统计指标可能不可靠"
            )

        # 计算各级指标
        signal_metrics = self.calculate_signal_metrics(signals)
        # v1.1增强：传递rejected_analyses以计算真实Step通过率
        step_metrics = self.calculate_step_metrics(signals, backtest_result.rejected_analyses)
        portfolio_metrics = self.calculate_portfolio_metrics(signals)
        distribution_metrics = self.calculate_distribution_metrics(signals)

        # 生成报告
        import time
        report = MetricsReport(
            signal_metrics=signal_metrics,
            step_metrics=step_metrics,
            portfolio_metrics=portfolio_metrics,
            distribution_metrics=distribution_metrics,
            timestamp_generated=int(time.time() * 1000)
        )

        logger.info("✅ 指标计算完成")
        return report

    def calculate_signal_metrics(self, signals: List[SimulatedSignal]) -> SignalMetrics:
        """
        计算信号级指标

        Args:
            signals: 信号列表

        Returns:
            信号级指标
        """
        if not signals:
            # 无信号：返回零值指标
            return SignalMetrics(
                total_signals=0,
                win_count=0,
                loss_count=0,
                win_rate=0.0,
                avg_pnl_percent=0.0,
                median_pnl_percent=0.0,
                max_pnl_percent=0.0,
                min_pnl_percent=0.0,
                std_pnl_percent=0.0,
                avg_rr_ratio=0.0,
                max_consecutive_wins=0,
                max_consecutive_losses=0,
                avg_holding_hours=0.0,
                median_holding_hours=0.0
            )

        # 基本统计
        total_signals = len(signals)
        pnl_list = [s.pnl_percent for s in signals]
        win_count = sum(1 for p in pnl_list if p > 0)
        loss_count = sum(1 for p in pnl_list if p < 0)
        win_rate = win_count / total_signals * 100 if total_signals > 0 else 0.0

        # PnL统计
        avg_pnl = mean(pnl_list) if pnl_list else 0.0
        median_pnl = median(pnl_list) if pnl_list else 0.0
        max_pnl = max(pnl_list) if pnl_list else 0.0
        min_pnl = min(pnl_list) if pnl_list else 0.0
        std_pnl = stdev(pnl_list) if len(pnl_list) > 1 else 0.0

        # 平均RR比率
        rr_ratios = []
        for s in signals:
            risk = abs(s.entry_price_actual - s.stop_loss_actual)
            if risk > 0 and s.pnl_percent > 0:
                reward = abs(s.exit_price - s.entry_price_actual)
                rr_ratios.append(reward / risk)
        avg_rr = mean(rr_ratios) if rr_ratios else 0.0

        # 最大连续盈亏
        max_consec_wins = self._calculate_max_consecutive(pnl_list, lambda p: p > 0)
        max_consec_losses = self._calculate_max_consecutive(pnl_list, lambda p: p < 0)

        # 持仓时长
        holding_times = [s.holding_hours for s in signals if s.holding_hours > 0]
        avg_holding = mean(holding_times) if holding_times else 0.0
        median_holding = median(holding_times) if holding_times else 0.0

        return SignalMetrics(
            total_signals=total_signals,
            win_count=win_count,
            loss_count=loss_count,
            win_rate=round(win_rate, 2),
            avg_pnl_percent=round(avg_pnl, 2),
            median_pnl_percent=round(median_pnl, 2),
            max_pnl_percent=round(max_pnl, 2),
            min_pnl_percent=round(min_pnl, 2),
            std_pnl_percent=round(std_pnl, 2),
            avg_rr_ratio=round(avg_rr, 2),
            max_consecutive_wins=max_consec_wins,
            max_consecutive_losses=max_consec_losses,
            avg_holding_hours=round(avg_holding, 2),
            median_holding_hours=round(median_holding, 2)
        )

    def calculate_step_metrics(
        self,
        signals: List[SimulatedSignal],
        rejected_analyses: List[RejectedAnalysis] = None
    ) -> StepMetrics:
        """
        计算步骤级指标（四步系统瓶颈分析）

        Args:
            signals: ACCEPT信号列表
            rejected_analyses: REJECT分析列表（v1.1新增）

        Returns:
            步骤级指标

        v1.1增强：使用ACCEPT信号和REJECT分析计算真实通过率
        - Step1通过率 = 通过Step1的数量 / 总分析数量
        - Step2通过率 = 通过Step2的数量 / 通过Step1的数量
        - Step3通过率 = 通过Step3的数量 / 通过Step2的数量
        - Step4通过率 = 通过Step4的数量 / 通过Step3的数量
        - 最终通过率 = ACCEPT数量 / 总分析数量
        """
        rejected_analyses = rejected_analyses or []

        # 总分析数量 = ACCEPT信号 + REJECT分析
        total_analyses = len(signals) + len(rejected_analyses)

        if total_analyses == 0:
            return StepMetrics(
                step1_pass_rate=0.0,
                step2_pass_rate=0.0,
                step3_pass_rate=0.0,
                step4_pass_rate=0.0,
                final_pass_rate=0.0,
                bottleneck_step=1
            )

        # 如果没有REJECT分析记录（v1.0模式或未启用记录），返回100%
        if not rejected_analyses:
            logger.info(
                "Step metrics: 无REJECT分析记录，使用v1.0模式（所有通过率100%）"
            )
            return StepMetrics(
                step1_pass_rate=100.0,
                step2_pass_rate=100.0,
                step3_pass_rate=100.0,
                step4_pass_rate=100.0,
                final_pass_rate=100.0,
                bottleneck_step=1
            )

        # v1.1真实通过率计算
        # ACCEPT信号默认所有步骤都通过
        accept_count = len(signals)

        # 统计各步骤的通过数量
        # Step1通过 = ACCEPT + 在Step2/3/4被拒绝的REJECT
        step1_pass_count = accept_count + sum(
            1 for r in rejected_analyses if r.step1_passed
        )

        # Step2通过 = ACCEPT + 在Step3/4被拒绝的REJECT
        step2_pass_count = accept_count + sum(
            1 for r in rejected_analyses if r.step2_passed
        )

        # Step3通过 = ACCEPT + 在Step4被拒绝的REJECT
        step3_pass_count = accept_count + sum(
            1 for r in rejected_analyses if r.step3_passed
        )

        # Step4通过 = ACCEPT
        step4_pass_count = accept_count + sum(
            1 for r in rejected_analyses if r.step4_passed
        )

        # 计算通过率（条件概率）
        step1_rate = (step1_pass_count / total_analyses * 100) if total_analyses > 0 else 0.0
        step2_rate = (step2_pass_count / step1_pass_count * 100) if step1_pass_count > 0 else 0.0
        step3_rate = (step3_pass_count / step2_pass_count * 100) if step2_pass_count > 0 else 0.0
        step4_rate = (step4_pass_count / step3_pass_count * 100) if step3_pass_count > 0 else 0.0
        final_rate = (accept_count / total_analyses * 100) if total_analyses > 0 else 0.0

        # 确定瓶颈步骤（通过率最低的步骤）
        rates = [
            (1, step1_rate),
            (2, step2_rate),
            (3, step3_rate),
            (4, step4_rate)
        ]
        bottleneck = min(rates, key=lambda x: x[1])[0]

        logger.info(
            f"Step metrics (v1.1): "
            f"total={total_analyses}, accept={accept_count}, "
            f"S1={step1_rate:.1f}%, S2={step2_rate:.1f}%, "
            f"S3={step3_rate:.1f}%, S4={step4_rate:.1f}%, "
            f"final={final_rate:.1f}%, bottleneck=Step{bottleneck}"
        )

        return StepMetrics(
            step1_pass_rate=round(step1_rate, 2),
            step2_pass_rate=round(step2_rate, 2),
            step3_pass_rate=round(step3_rate, 2),
            step4_pass_rate=round(step4_rate, 2),
            final_pass_rate=round(final_rate, 2),
            bottleneck_step=bottleneck
        )

    def calculate_portfolio_metrics(
        self,
        signals: List[SimulatedSignal]
    ) -> PortfolioMetrics:
        """
        计算组合级指标

        Args:
            signals: 信号列表

        Returns:
            组合级指标
        """
        if not signals:
            return PortfolioMetrics(
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                max_drawdown_percent=0.0,
                max_concurrent_positions=0,
                avg_trades_per_day=0.0,
                profit_factor=0.0,
                total_pnl_usdt=0.0,
                total_pnl_percent=0.0
            )

        # 总盈亏
        total_pnl_usdt = sum(s.pnl_usdt for s in signals)
        pnl_list = [s.pnl_percent for s in signals]
        avg_pnl_pct = mean(pnl_list) if pnl_list else 0.0

        # Sharpe比率（年化）
        sharpe = self._calculate_sharpe_ratio(pnl_list)

        # Sortino比率（年化，只考虑下行风险）
        sortino = self._calculate_sortino_ratio(pnl_list)

        # 最大回撤
        max_dd = self._calculate_max_drawdown([s.pnl_usdt for s in signals])

        # 最大并发头寸（需要按时间排序）
        max_concurrent = self._calculate_max_concurrent_positions(signals)

        # 平均每日交易数
        avg_trades_per_day = self._calculate_avg_trades_per_day(signals)

        # 盈亏因子（总盈利/总亏损）
        profit_factor = self._calculate_profit_factor(pnl_list)

        return PortfolioMetrics(
            sharpe_ratio=round(sharpe, 2),
            sortino_ratio=round(sortino, 2),
            max_drawdown_percent=round(max_dd, 2),
            max_concurrent_positions=max_concurrent,
            avg_trades_per_day=round(avg_trades_per_day, 2),
            profit_factor=round(profit_factor, 2),
            total_pnl_usdt=round(total_pnl_usdt, 2),
            total_pnl_percent=round(avg_pnl_pct, 2)
        )

    def calculate_distribution_metrics(
        self,
        signals: List[SimulatedSignal]
    ) -> DistributionMetrics:
        """
        计算分布分析指标

        Args:
            signals: 信号列表

        Returns:
            分布分析指标
        """
        if not signals:
            return DistributionMetrics(
                pnl_histogram={},
                holding_time_histogram={},
                win_rate_by_direction={},
                avg_pnl_by_direction={}
            )

        # PnL直方图
        pnl_hist = self._create_histogram(
            [s.pnl_percent for s in signals],
            self.pnl_histogram_bins,
            "%"
        )

        # 持仓时长直方图
        holding_hist = self._create_histogram(
            [s.holding_hours for s in signals if s.holding_hours > 0],
            self.holding_time_bins,
            "h"
        )

        # 按方向统计
        long_signals = [s for s in signals if s.side == "long"]
        short_signals = [s for s in signals if s.side == "short"]

        win_rate_by_dir = {
            "long": self._calculate_win_rate(long_signals),
            "short": self._calculate_win_rate(short_signals)
        }

        avg_pnl_by_dir = {
            "long": mean([s.pnl_percent for s in long_signals]) if long_signals else 0.0,
            "short": mean([s.pnl_percent for s in short_signals]) if short_signals else 0.0
        }

        return DistributionMetrics(
            pnl_histogram=pnl_hist,
            holding_time_histogram=holding_hist,
            win_rate_by_direction={k: round(v, 2) for k, v in win_rate_by_dir.items()},
            avg_pnl_by_direction={k: round(v, 2) for k, v in avg_pnl_by_dir.items()}
        )

    def generate_report(
        self,
        metrics_report: MetricsReport,
        output_format: str = "json"
    ) -> str:
        """
        生成人类可读报告

        Args:
            metrics_report: 指标报告
            output_format: 输出格式（"json" | "markdown" | "csv"）

        Returns:
            格式化报告字符串
        """
        if output_format == "json":
            return self._generate_json_report(metrics_report)
        elif output_format == "markdown":
            return self._generate_markdown_report(metrics_report)
        elif output_format == "csv":
            return self._generate_csv_report(metrics_report)
        else:
            raise ValueError(f"不支持的输出格式: {output_format}")

    # ==================== Private Methods ====================

    def _calculate_max_consecutive(self, values: List[float], condition) -> int:
        """计算最大连续满足条件的次数"""
        max_consec = 0
        current_consec = 0

        for v in values:
            if condition(v):
                current_consec += 1
                max_consec = max(max_consec, current_consec)
            else:
                current_consec = 0

        return max_consec

    def _calculate_sharpe_ratio(self, pnl_list: List[float]) -> float:
        """
        计算Sharpe比率（年化）

        Args:
            pnl_list: PnL百分比列表

        Returns:
            Sharpe比率

        公式: Sharpe = (mean_return - risk_free_rate) / std_return * sqrt(252)
              注意: 252是年交易日数，这里假设每笔交易独立
        """
        if not pnl_list or len(pnl_list) < 2:
            return 0.0

        mean_return = mean(pnl_list) / 100  # 转换为小数
        std_return = stdev(pnl_list) / 100

        if std_return == 0:
            return 0.0

        # 年化Sharpe
        # 假设每笔交易独立，年化因子 = sqrt(交易频率)
        # 这里简化为 sqrt(252)，实际应根据平均持仓时长调整
        sharpe = (mean_return - self.risk_free_rate / 252) / std_return * math.sqrt(252)
        return sharpe

    def _calculate_sortino_ratio(self, pnl_list: List[float]) -> float:
        """
        计算Sortino比率（年化，只考虑下行风险）

        Args:
            pnl_list: PnL百分比列表

        Returns:
            Sortino比率

        公式: Sortino = (mean_return - risk_free_rate) / downside_std * sqrt(252)
        """
        if not pnl_list or len(pnl_list) < 2:
            return 0.0

        mean_return = mean(pnl_list) / 100
        downside_returns = [p / 100 for p in pnl_list if p < 0]

        if not downside_returns:
            return 0.0

        downside_std = stdev(downside_returns) if len(downside_returns) > 1 else 0.0

        if downside_std == 0:
            return 0.0

        sortino = (mean_return - self.risk_free_rate / 252) / downside_std * math.sqrt(252)
        return sortino

    def _calculate_max_drawdown(self, pnl_usdt_list: List[float]) -> float:
        """
        计算最大回撤（百分比）

        Args:
            pnl_usdt_list: PnL USDT列表（累计）

        Returns:
            最大回撤百分比
        """
        if not pnl_usdt_list:
            return 0.0

        # 构建资金曲线（累计）
        initial_capital = 1000.0  # 假设初始资本1000 USDT
        equity_curve = [initial_capital]

        for pnl in pnl_usdt_list:
            equity_curve.append(equity_curve[-1] + pnl)

        # 计算回撤
        max_dd = 0.0
        peak = equity_curve[0]

        for equity in equity_curve:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak * 100 if peak > 0 else 0.0
            max_dd = max(max_dd, drawdown)

        return max_dd

    def _calculate_max_concurrent_positions(self, signals: List[SimulatedSignal]) -> int:
        """
        计算最大并发头寸数

        Args:
            signals: 信号列表

        Returns:
            最大并发头寸数
        """
        if not signals:
            return 0

        # 构建事件列表（entry/exit）
        events = []
        for s in signals:
            events.append((s.timestamp, 1))  # entry
            if s.exit_time > 0:
                events.append((s.exit_time, -1))  # exit

        # 按时间排序
        events.sort(key=lambda e: e[0])

        # 统计并发数
        max_concurrent = 0
        current_concurrent = 0

        for time, delta in events:
            current_concurrent += delta
            max_concurrent = max(max_concurrent, current_concurrent)

        return max_concurrent

    def _calculate_avg_trades_per_day(self, signals: List[SimulatedSignal]) -> float:
        """
        计算平均每日交易数

        Args:
            signals: 信号列表

        Returns:
            平均每日交易数
        """
        if not signals:
            return 0.0

        # 计算时间范围（天）
        timestamps = [s.timestamp for s in signals]
        min_time = min(timestamps)
        max_time = max(timestamps)
        duration_days = (max_time - min_time) / (1000 * 3600 * 24)

        if duration_days < 1:
            duration_days = 1  # 至少1天

        return len(signals) / duration_days

    def _calculate_profit_factor(self, pnl_list: List[float]) -> float:
        """
        计算盈亏因子（总盈利/总亏损）

        Args:
            pnl_list: PnL百分比列表

        Returns:
            盈亏因子（>1表示盈利大于亏损）
        """
        gross_profit = sum(p for p in pnl_list if p > 0)
        gross_loss = abs(sum(p for p in pnl_list if p < 0))

        if gross_loss == 0:
            return 0.0 if gross_profit == 0 else float('inf')

        return gross_profit / gross_loss

    def _calculate_win_rate(self, signals: List[SimulatedSignal]) -> float:
        """计算胜率"""
        if not signals:
            return 0.0

        win_count = sum(1 for s in signals if s.pnl_percent > 0)
        return win_count / len(signals) * 100

    def _create_histogram(
        self,
        values: List[float],
        bins: List[float],
        unit: str
    ) -> Dict[str, int]:
        """
        创建直方图

        Args:
            values: 数值列表
            bins: 分箱边界
            unit: 单位（用于标签）

        Returns:
            {bin_label: count}
        """
        if not values:
            return {}

        histogram = defaultdict(int)

        for v in values:
            # 找到对应的bin
            bin_label = self._find_bin_label(v, bins, unit)
            histogram[bin_label] += 1

        return dict(histogram)

    def _find_bin_label(self, value: float, bins: List[float], unit: str) -> str:
        """
        找到数值对应的bin标签

        Args:
            value: 数值
            bins: 分箱边界（升序）
            unit: 单位

        Returns:
            bin标签（如 "0-2%", ">20%"）
        """
        for i, bin_edge in enumerate(bins):
            if value < bin_edge:
                if i == 0:
                    return f"<{bin_edge}{unit}"
                else:
                    return f"{bins[i-1]}-{bin_edge}{unit}"

        # 超过最大bin
        return f">{bins[-1]}{unit}"

    def _generate_json_report(self, metrics_report: MetricsReport) -> str:
        """生成JSON格式报告"""
        report_dict = {
            "signal_metrics": asdict(metrics_report.signal_metrics),
            "step_metrics": asdict(metrics_report.step_metrics),
            "portfolio_metrics": asdict(metrics_report.portfolio_metrics),
            "distribution_metrics": asdict(metrics_report.distribution_metrics),
            "timestamp_generated": metrics_report.timestamp_generated
        }

        indent = self.config.get("output", {}).get("json_indent", 2)
        return json.dumps(report_dict, indent=indent, ensure_ascii=False)

    def _generate_markdown_report(self, metrics_report: MetricsReport) -> str:
        """生成Markdown格式报告"""
        sm = metrics_report.signal_metrics
        pm = metrics_report.portfolio_metrics
        dm = metrics_report.distribution_metrics

        md = []
        md.append("# Backtest Report")
        md.append("")
        md.append("## Signal Metrics")
        md.append(f"- Total Signals: **{sm.total_signals}**")
        md.append(f"- Win Rate: **{sm.win_rate:.2f}%** ({sm.win_count}W / {sm.loss_count}L)")
        md.append(f"- Avg PnL: **{sm.avg_pnl_percent:+.2f}%** (Median: {sm.median_pnl_percent:+.2f}%)")
        md.append(f"- Max PnL: **{sm.max_pnl_percent:+.2f}%** | Min: {sm.min_pnl_percent:+.2f}%")
        md.append(f"- Avg RR Ratio: **{sm.avg_rr_ratio:.2f}**")
        md.append(f"- Max Consecutive Wins: **{sm.max_consecutive_wins}** | Losses: {sm.max_consecutive_losses}")
        md.append(f"- Avg Holding: **{sm.avg_holding_hours:.1f}h** (Median: {sm.median_holding_hours:.1f}h)")
        md.append("")
        md.append("## Portfolio Metrics")
        md.append(f"- Sharpe Ratio: **{pm.sharpe_ratio:.2f}**")
        md.append(f"- Sortino Ratio: **{pm.sortino_ratio:.2f}**")
        md.append(f"- Max Drawdown: **{pm.max_drawdown_percent:.2f}%**")
        md.append(f"- Profit Factor: **{pm.profit_factor:.2f}**")
        md.append(f"- Total PnL: **{pm.total_pnl_usdt:+.2f} USDT**")
        md.append(f"- Max Concurrent Positions: **{pm.max_concurrent_positions}**")
        md.append(f"- Avg Trades/Day: **{pm.avg_trades_per_day:.2f}**")
        md.append("")
        md.append("## Distribution Analysis")
        md.append(f"- Win Rate by Direction: LONG={dm.win_rate_by_direction.get('long', 0):.2f}%, SHORT={dm.win_rate_by_direction.get('short', 0):.2f}%")
        md.append(f"- Avg PnL by Direction: LONG={dm.avg_pnl_by_direction.get('long', 0):+.2f}%, SHORT={dm.avg_pnl_by_direction.get('short', 0):+.2f}%")
        md.append("")

        return "\n".join(md)

    def _generate_csv_report(self, metrics_report: MetricsReport) -> str:
        """生成CSV格式报告（简化版）"""
        sm = metrics_report.signal_metrics
        pm = metrics_report.portfolio_metrics

        delimiter = self.config.get("output", {}).get("csv_delimiter", ",")
        lines = []
        lines.append(f"Metric{delimiter}Value")
        lines.append(f"Total Signals{delimiter}{sm.total_signals}")
        lines.append(f"Win Rate (%){delimiter}{sm.win_rate:.2f}")
        lines.append(f"Avg PnL (%){delimiter}{sm.avg_pnl_percent:.2f}")
        lines.append(f"Sharpe Ratio{delimiter}{pm.sharpe_ratio:.2f}")
        lines.append(f"Sortino Ratio{delimiter}{pm.sortino_ratio:.2f}")
        lines.append(f"Max Drawdown (%){delimiter}{pm.max_drawdown_percent:.2f}")
        lines.append(f"Profit Factor{delimiter}{pm.profit_factor:.2f}")
        lines.append(f"Total PnL (USDT){delimiter}{pm.total_pnl_usdt:.2f}")

        return "\n".join(lines)
