# coding: utf-8
"""
IC (Information Coefficient) 监控器

功能：
1. 计算因子IC值（预测能力）
2. 监控IC衰减（过拟合预警）
3. 追踪IR (Information Ratio)
4. 生成IC时间序列图表

理论基础：
IC (Information Coefficient):
- IC = Corr(Factor_Score, Future_Return)
- 衡量因子对未来收益的预测能力
- IC > 0.05: 显著预测能力
- IC > 0.10: 强预测能力
- IC < 0: 负向预测（需要反转）

IC衰减检测：
- 样本内IC vs 样本外IC差异 > 30% → 过拟合警告
- IC持续下降 → 因子失效警告

IR (Information Ratio):
- IR = IC_mean / IC_std
- 衡量因子稳定性
- IR > 0.5: 稳定
- IR > 1.0: 非常稳定
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
from collections import defaultdict, deque


class ICMonitor:
    """IC监控器"""

    def __init__(
        self,
        ic_threshold: float = 0.05,
        decay_threshold: float = 0.30,
        window_size: int = 50
    ):
        """
        初始化IC监控器

        Args:
            ic_threshold: IC阈值（默认0.05）
            decay_threshold: IC衰减阈值（默认30%）
            window_size: 滚动窗口大小（默认50）
        """
        self.ic_threshold = ic_threshold
        self.decay_threshold = decay_threshold
        self.window_size = window_size

        # 存储因子评分和未来收益
        self.factor_scores_history = defaultdict(lambda: deque(maxlen=window_size))
        self.future_returns_history = deque(maxlen=window_size)

        # 存储IC时间序列
        self.ic_timeseries = defaultdict(list)

        # 样本内/外划分点
        self.in_sample_size = None

    def add_observation(
        self,
        factor_scores: Dict[str, float],
        future_return: float
    ):
        """
        添加一次观测

        Args:
            factor_scores: 因子评分字典 {factor_name: score}
            future_return: 未来收益（如1h/4h/24h后的收益率）
        """
        for factor_name, score in factor_scores.items():
            self.factor_scores_history[factor_name].append(score)

        self.future_returns_history.append(future_return)

    def add_batch_observations(
        self,
        observations: List[Tuple[Dict[str, float], float]]
    ):
        """
        批量添加观测

        Args:
            observations: [(factor_scores, future_return), ...]
        """
        for factor_scores, future_return in observations:
            self.add_observation(factor_scores, future_return)

    def calculate_ic(
        self,
        factor_name: str,
        use_rank: bool = True
    ) -> Tuple[float, int]:
        """
        计算单个因子的IC

        Args:
            factor_name: 因子名称
            use_rank: 是否使用Spearman秩相关（默认True，更稳健）

        Returns:
            (ic_value, sample_size)
        """
        if factor_name not in self.factor_scores_history:
            return 0.0, 0

        factor_scores = list(self.factor_scores_history[factor_name])
        future_returns = list(self.future_returns_history)

        # 对齐长度
        min_length = min(len(factor_scores), len(future_returns))

        if min_length < 2:
            return 0.0, 0

        factor_scores = factor_scores[-min_length:]
        future_returns = future_returns[-min_length:]

        # 计算相关系数
        if use_rank:
            # Spearman秩相关（更稳健）
            factor_ranks = self._rank(factor_scores)
            return_ranks = self._rank(future_returns)
            ic = np.corrcoef(factor_ranks, return_ranks)[0, 1]
        else:
            # Pearson相关
            ic = np.corrcoef(factor_scores, future_returns)[0, 1]

        # 处理NaN
        if np.isnan(ic):
            ic = 0.0

        return ic, min_length

    def _rank(self, values: List[float]) -> List[float]:
        """计算秩"""
        sorted_indices = np.argsort(values)
        ranks = np.empty(len(values))
        ranks[sorted_indices] = np.arange(len(values))
        return ranks.tolist()

    def calculate_all_ic(self, use_rank: bool = True) -> Dict[str, Tuple[float, int]]:
        """
        计算所有因子的IC

        Args:
            use_rank: 是否使用秩相关

        Returns:
            {factor_name: (ic_value, sample_size), ...}
        """
        ic_results = {}

        for factor_name in self.factor_scores_history.keys():
            ic, sample_size = self.calculate_ic(factor_name, use_rank)
            ic_results[factor_name] = (ic, sample_size)

        return ic_results

    def calculate_ir(self, factor_name: str) -> Tuple[float, float, float]:
        """
        计算Information Ratio

        Args:
            factor_name: 因子名称

        Returns:
            (IR, IC_mean, IC_std)
        """
        if factor_name not in self.ic_timeseries or len(self.ic_timeseries[factor_name]) < 2:
            return 0.0, 0.0, 0.0

        ic_series = self.ic_timeseries[factor_name]

        ic_mean = np.mean(ic_series)
        ic_std = np.std(ic_series)

        if ic_std == 0:
            ir = 0.0
        else:
            ir = ic_mean / ic_std

        return ir, ic_mean, ic_std

    def detect_ic_decay(
        self,
        factor_name: str,
        in_sample_ratio: float = 0.8
    ) -> Dict[str, Any]:
        """
        检测IC衰减（过拟合检测）

        Args:
            factor_name: 因子名称
            in_sample_ratio: 样本内比例（默认80%）

        Returns:
            {
                "in_sample_ic": float,
                "out_sample_ic": float,
                "decay_pct": float,
                "is_overfitting": bool,
                "severity": str
            }
        """
        if factor_name not in self.factor_scores_history:
            return {"error": "Factor not found"}

        factor_scores = list(self.factor_scores_history[factor_name])
        future_returns = list(self.future_returns_history)

        min_length = min(len(factor_scores), len(future_returns))

        if min_length < 10:
            return {"error": "Insufficient data"}

        # 划分样本内/外
        split_point = int(min_length * in_sample_ratio)

        if split_point < 5 or (min_length - split_point) < 5:
            return {"error": "Insufficient data for train/test split"}

        # 样本内
        in_scores = factor_scores[:split_point]
        in_returns = future_returns[:split_point]
        in_ic = np.corrcoef(in_scores, in_returns)[0, 1]

        # 样本外
        out_scores = factor_scores[split_point:]
        out_returns = future_returns[split_point:]
        out_ic = np.corrcoef(out_scores, out_returns)[0, 1]

        # 处理NaN
        in_ic = 0.0 if np.isnan(in_ic) else in_ic
        out_ic = 0.0 if np.isnan(out_ic) else out_ic

        # 计算衰减百分比
        if abs(in_ic) < 1e-9:
            decay_pct = 0.0
        else:
            decay_pct = (in_ic - out_ic) / abs(in_ic)

        # 判断是否过拟合
        is_overfitting = decay_pct > self.decay_threshold

        # 严重程度
        if decay_pct > 0.5:
            severity = "severe"
        elif decay_pct > self.decay_threshold:
            severity = "moderate"
        elif decay_pct > 0.1:
            severity = "mild"
        else:
            severity = "none"

        return {
            "in_sample_ic": in_ic,
            "out_sample_ic": out_ic,
            "decay_pct": decay_pct,
            "is_overfitting": is_overfitting,
            "severity": severity,
            "in_sample_size": split_point,
            "out_sample_size": min_length - split_point
        }

    def update_ic_timeseries(self):
        """更新IC时间序列（用于追踪IC变化）"""
        ic_results = self.calculate_all_ic()

        for factor_name, (ic, _) in ic_results.items():
            self.ic_timeseries[factor_name].append(ic)

    def generate_report(self) -> str:
        """
        生成IC监控报告

        Returns:
            Markdown格式的报告
        """
        report = []
        report.append("# IC (Information Coefficient) Monitoring Report")
        report.append("")
        report.append(f"**IC Threshold**: {self.ic_threshold}")
        report.append(f"**Decay Threshold**: {self.decay_threshold * 100:.0f}%")
        report.append(f"**Sample Size**: {len(self.future_returns_history)}")
        report.append("")

        # 当前IC值
        ic_results = self.calculate_all_ic()

        report.append("## Current IC Values")
        report.append("")
        report.append("| Factor | IC | Sample Size | Significance |")
        report.append("|--------|-----|-------------|--------------|")

        for factor_name, (ic, sample_size) in sorted(ic_results.items(), key=lambda x: abs(x[1][0]), reverse=True):
            # 判断显著性
            if abs(ic) >= 0.10:
                sig = "🔥 Strong"
            elif abs(ic) >= self.ic_threshold:
                sig = "✅ Significant"
            elif abs(ic) > 0:
                sig = "⚠️ Weak"
            else:
                sig = "❌ None"

            report.append(f"| **{factor_name}** | {ic:.4f} | {sample_size} | {sig} |")

        report.append("")

        # IR (Information Ratio)
        report.append("## Information Ratio (IR)")
        report.append("")
        report.append("| Factor | IR | IC Mean | IC Std | Stability |")
        report.append("|--------|-----|---------|--------|-----------|")

        for factor_name in self.factor_scores_history.keys():
            ir, ic_mean, ic_std = self.calculate_ir(factor_name)

            # 判断稳定性
            if abs(ir) >= 1.0:
                stability = "🔥 Excellent"
            elif abs(ir) >= 0.5:
                stability = "✅ Good"
            elif abs(ir) > 0:
                stability = "⚠️ Fair"
            else:
                stability = "❌ Poor"

            report.append(f"| **{factor_name}** | {ir:.3f} | {ic_mean:.4f} | {ic_std:.4f} | {stability} |")

        report.append("")

        # IC衰减检测
        report.append("## IC Decay Detection (Overfitting Check)")
        report.append("")

        has_overfitting = False

        for factor_name in self.factor_scores_history.keys():
            decay_result = self.detect_ic_decay(factor_name)

            if "error" in decay_result:
                continue

            if decay_result["is_overfitting"]:
                has_overfitting = True

                report.append(f"### ⚠️ {factor_name} - Overfitting Detected")
                report.append("")
                report.append(f"- **In-Sample IC**: {decay_result['in_sample_ic']:.4f}")
                report.append(f"- **Out-Sample IC**: {decay_result['out_sample_ic']:.4f}")
                report.append(f"- **Decay**: {decay_result['decay_pct']*100:.1f}%")
                report.append(f"- **Severity**: {decay_result['severity'].upper()}")
                report.append("")

        if not has_overfitting:
            report.append("✅ **No overfitting detected** - All factors maintain consistent IC")
            report.append("")

        # 建议
        report.append("## Recommendations")
        report.append("")

        low_ic_factors = [name for name, (ic, _) in ic_results.items() if abs(ic) < self.ic_threshold]

        if low_ic_factors:
            report.append(f"⚠️ **Low IC factors** (IC < {self.ic_threshold}):")
            for factor_name in low_ic_factors:
                report.append(f"  - {factor_name}")
            report.append("")
            report.append("💡 Consider:")
            report.append("  1. Removing or transforming low-IC factors")
            report.append("  2. Investigating why these factors have weak predictive power")
            report.append("  3. Checking data quality and calculation logic")
            report.append("")

        if has_overfitting:
            report.append("⚠️ **Overfitting detected**:")
            report.append("")
            report.append("💡 Actions:")
            report.append("  1. Reduce model complexity (fewer factors or simpler transformations)")
            report.append("  2. Use regularization (L1/L2)")
            report.append("  3. Increase training data")
            report.append("  4. Re-validate factor logic on fresh data")
            report.append("")

        return "\n".join(report)

    def reset(self):
        """重置监控器"""
        self.factor_scores_history.clear()
        self.future_returns_history.clear()
        self.ic_timeseries.clear()


# ========== 测试代码 ==========

if __name__ == "__main__":
    print("=" * 70)
    print("IC监控器测试")
    print("=" * 70)

    # 创建监控器
    monitor = ICMonitor(ic_threshold=0.05, decay_threshold=0.30)

    # 模拟数据
    np.random.seed(42)

    print("\n[模拟数据] 生成100个观测...")

    for i in range(100):
        # 模拟未来收益（随机游走）
        future_return = np.random.randn() * 0.02  # ±2%

        # 模拟10个因子
        # T: 高预测能力 (IC≈0.15)
        T = future_return * 10 + np.random.randn() * 20

        # M: 中等预测能力 (IC≈0.08)
        M = future_return * 5 + np.random.randn() * 25

        # C+: 低预测能力 (IC≈0.03)
        C_plus = future_return * 2 + np.random.randn() * 30

        # S: 无预测能力 (IC≈0)
        S = np.random.uniform(0, 100)

        # V+: 负向预测 (IC≈-0.05)
        V_plus = -future_return * 3 + np.random.randn() * 20

        # 其他因子（随机）
        O_plus = np.random.randn() * 25
        L = np.random.uniform(0, 100)
        B = np.random.randn() * 25
        Q = np.random.randn() * 15
        I = np.random.uniform(0, 100)

        factor_scores = {
            "T": T,
            "M": M,
            "C+": C_plus,
            "S": S,
            "V+": V_plus,
            "O+": O_plus,
            "L": L,
            "B": B,
            "Q": Q,
            "I": I
        }

        monitor.add_observation(factor_scores, future_return)

    # 计算IC
    print("\n[计算IC值]")
    ic_results = monitor.calculate_all_ic()

    for factor_name, (ic, sample_size) in sorted(ic_results.items(), key=lambda x: abs(x[1][0]), reverse=True):
        sig = "Strong" if abs(ic) >= 0.10 else ("Significant" if abs(ic) >= 0.05 else "Weak")
        print(f"  {factor_name:5s}: IC = {ic:7.4f} ({sig})")

    # IC衰减检测
    print("\n[IC衰减检测]")
    for factor_name in ["T", "M", "C+"]:
        decay_result = monitor.detect_ic_decay(factor_name)

        if "error" not in decay_result:
            print(f"\n  {factor_name}:")
            print(f"    样本内IC:  {decay_result['in_sample_ic']:.4f}")
            print(f"    样本外IC:  {decay_result['out_sample_ic']:.4f}")
            print(f"    衰减:      {decay_result['decay_pct']*100:.1f}%")
            print(f"    过拟合:    {'Yes' if decay_result['is_overfitting'] else 'No'}")

    # 生成报告
    print("\n[生成报告]")
    report = monitor.generate_report()

    # 保存报告
    report_path = "/tmp/ic_monitoring_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"  报告已保存到: {report_path}")

    # 显示报告（前35行）
    print("\n[报告预览]")
    print("-" * 70)
    lines = report.split("\n")
    for line in lines[:35]:
        print(line)
    if len(lines) > 35:
        print(f"... ({len(lines) - 35} more lines)")

    print("\n" + "=" * 70)
    print("✅ IC监控器测试完成")
    print("=" * 70)
