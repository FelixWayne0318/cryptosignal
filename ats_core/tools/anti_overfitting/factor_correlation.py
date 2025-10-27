# coding: utf-8
"""
因子相关性监控器

功能：
1. 计算因子之间的相关系数
2. 检测高度相关的因子对（阈值默认0.5）
3. 生成相关性矩阵和可视化报告
4. 给出因子正交化建议

理论基础：
- 高度相关的因子会导致多重共线性
- 降低模型稳定性和解释性
- 增加过拟合风险
- 建议保持因子间相关性 < 0.5
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Any
import numpy as np
from collections import defaultdict


class FactorCorrelationMonitor:
    """因子相关性监控器"""

    def __init__(self, correlation_threshold: float = 0.5):
        """
        初始化监控器

        Args:
            correlation_threshold: 相关性阈值（默认0.5）
        """
        self.correlation_threshold = correlation_threshold
        self.factor_history = defaultdict(list)  # {factor_name: [scores]}

    def add_observation(self, factor_scores: Dict[str, float]):
        """
        添加一次因子观测

        Args:
            factor_scores: 因子评分字典 {factor_name: score}
        """
        for factor_name, score in factor_scores.items():
            self.factor_history[factor_name].append(score)

    def add_batch_observations(self, observations: List[Dict[str, float]]):
        """
        批量添加观测

        Args:
            observations: 观测列表 [{factor_name: score}, ...]
        """
        for obs in observations:
            self.add_observation(obs)

    def calculate_correlation_matrix(self) -> Tuple[Dict[str, Dict[str, float]], List[str]]:
        """
        计算相关性矩阵

        Returns:
            (correlation_matrix, factor_names)
            - correlation_matrix: {factor1: {factor2: corr, ...}, ...}
            - factor_names: 因子名称列表
        """
        factor_names = list(self.factor_history.keys())

        if len(factor_names) < 2:
            return {}, factor_names

        # 检查数据长度
        min_length = min(len(scores) for scores in self.factor_history.values())

        if min_length < 2:
            return {}, factor_names

        # 构建数据矩阵（对齐长度）
        data_matrix = []
        for factor_name in factor_names:
            scores = self.factor_history[factor_name][-min_length:]
            data_matrix.append(scores)

        data_matrix = np.array(data_matrix)  # shape: (n_factors, n_observations)

        # 计算相关系数矩阵
        correlation_matrix = {}

        for i, factor1 in enumerate(factor_names):
            correlation_matrix[factor1] = {}
            for j, factor2 in enumerate(factor_names):
                if i == j:
                    correlation_matrix[factor1][factor2] = 1.0
                else:
                    # Pearson相关系数
                    corr = np.corrcoef(data_matrix[i], data_matrix[j])[0, 1]
                    # 处理NaN
                    if np.isnan(corr):
                        corr = 0.0
                    correlation_matrix[factor1][factor2] = corr

        return correlation_matrix, factor_names

    def detect_high_correlations(self) -> List[Tuple[str, str, float]]:
        """
        检测高度相关的因子对

        Returns:
            高相关因子对列表 [(factor1, factor2, correlation), ...]
            按相关系数绝对值降序排列
        """
        corr_matrix, factor_names = self.calculate_correlation_matrix()

        if not corr_matrix:
            return []

        high_corr_pairs = []

        for i, factor1 in enumerate(factor_names):
            for j, factor2 in enumerate(factor_names):
                if i < j:  # 只取上三角（避免重复）
                    corr = corr_matrix[factor1][factor2]
                    if abs(corr) >= self.correlation_threshold:
                        high_corr_pairs.append((factor1, factor2, corr))

        # 按相关系数绝对值降序排序
        high_corr_pairs.sort(key=lambda x: abs(x[2]), reverse=True)

        return high_corr_pairs

    def get_orthogonalization_suggestions(self) -> Dict[str, Any]:
        """
        获取因子正交化建议

        Returns:
            建议字典，包含：
            - high_corr_pairs: 高相关因子对
            - redundant_factors: 可能冗余的因子
            - suggestions: 具体建议
        """
        high_corr_pairs = self.detect_high_correlations()

        if not high_corr_pairs:
            return {
                "status": "good",
                "high_corr_pairs": [],
                "redundant_factors": [],
                "suggestions": ["All factors are well orthogonalized (correlation < threshold)"]
            }

        # 统计每个因子在高相关对中出现的次数
        factor_counts = defaultdict(int)
        for factor1, factor2, corr in high_corr_pairs:
            factor_counts[factor1] += 1
            factor_counts[factor2] += 1

        # 识别可能冗余的因子（出现次数最多的）
        redundant_factors = sorted(factor_counts.items(), key=lambda x: x[1], reverse=True)

        suggestions = []

        if high_corr_pairs:
            suggestions.append(f"⚠️ Detected {len(high_corr_pairs)} highly correlated factor pairs (threshold: {self.correlation_threshold})")

        for factor1, factor2, corr in high_corr_pairs[:5]:  # 只显示前5个
            suggestions.append(f"  • {factor1} ↔ {factor2}: {corr:.3f}")

        if redundant_factors:
            top_redundant = redundant_factors[0]
            suggestions.append(f"\n💡 Most redundant factor: {top_redundant[0]} (appears in {top_redundant[1]} pairs)")
            suggestions.append(f"   Consider removing or transforming this factor")

        suggestions.append("\n📋 Recommended actions:")
        suggestions.append("   1. Remove one factor from each highly correlated pair")
        suggestions.append("   2. Apply PCA or other dimensionality reduction")
        suggestions.append("   3. Transform factors to increase independence")

        return {
            "status": "warning",
            "high_corr_pairs": high_corr_pairs,
            "redundant_factors": [f[0] for f in redundant_factors],
            "suggestions": suggestions
        }

    def generate_report(self) -> str:
        """
        生成相关性监控报告

        Returns:
            Markdown格式的报告
        """
        corr_matrix, factor_names = self.calculate_correlation_matrix()

        if not corr_matrix:
            return "# Factor Correlation Report\n\n⚠️ Insufficient data for correlation analysis\n"

        report = []
        report.append("# Factor Correlation Report")
        report.append("")
        report.append(f"**Correlation Threshold**: {self.correlation_threshold}")
        report.append(f"**Number of Factors**: {len(factor_names)}")
        report.append(f"**Observations**: {min(len(scores) for scores in self.factor_history.values())}")
        report.append("")

        # 相关性矩阵表格
        report.append("## Correlation Matrix")
        report.append("")

        # 表头
        header = "| Factor | " + " | ".join(factor_names) + " |"
        separator = "|--------|" + "|".join(["--------"] * len(factor_names)) + "|"

        report.append(header)
        report.append(separator)

        # 数据行
        for factor1 in factor_names:
            row = f"| **{factor1}** |"
            for factor2 in factor_names:
                corr = corr_matrix[factor1][factor2]
                # 高亮高相关性
                if factor1 != factor2 and abs(corr) >= self.correlation_threshold:
                    row += f" **{corr:.3f}** |"
                else:
                    row += f" {corr:.3f} |"
            report.append(row)

        report.append("")

        # 高相关对
        high_corr_pairs = self.detect_high_correlations()

        if high_corr_pairs:
            report.append("## ⚠️ High Correlation Pairs")
            report.append("")

            for factor1, factor2, corr in high_corr_pairs:
                report.append(f"- **{factor1} ↔ {factor2}**: {corr:.3f}")

            report.append("")
        else:
            report.append("## ✅ No High Correlations Detected")
            report.append("")

        # 正交化建议
        suggestions = self.get_orthogonalization_suggestions()

        report.append("## Orthogonalization Suggestions")
        report.append("")

        for suggestion in suggestions["suggestions"]:
            report.append(suggestion)

        report.append("")

        return "\n".join(report)

    def reset(self):
        """重置监控器（清空历史数据）"""
        self.factor_history.clear()


# ========== 测试代码 ==========

if __name__ == "__main__":
    print("=" * 70)
    print("因子相关性监控器测试")
    print("=" * 70)

    # 创建监控器
    monitor = FactorCorrelationMonitor(correlation_threshold=0.5)

    # 模拟数据（100个观测）
    np.random.seed(42)

    print("\n[模拟数据] 生成100个观测...")

    for i in range(100):
        # 模拟10个因子
        # T和M高度相关（0.8）
        # C+和O+中度相关（0.6）
        # 其他因子独立

        base_trend = np.random.randn() * 30
        T = base_trend + np.random.randn() * 5
        M = base_trend * 0.8 + np.random.randn() * 10  # 高相关

        base_flow = np.random.randn() * 25
        C_plus = base_flow + np.random.randn() * 8
        O_plus = base_flow * 0.6 + np.random.randn() * 12  # 中度相关

        S = np.random.uniform(0, 100)
        V_plus = np.random.randn() * 20
        L = np.random.uniform(0, 100)
        B = np.random.randn() * 25
        Q = np.random.randn() * 15
        I = np.random.uniform(0, 100)

        observation = {
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

        monitor.add_observation(observation)

    # 检测高相关性
    print("\n[检测高相关性]")
    high_corr = monitor.detect_high_correlations()

    if high_corr:
        print(f"  检测到 {len(high_corr)} 个高相关因子对：")
        for factor1, factor2, corr in high_corr:
            print(f"    • {factor1} ↔ {factor2}: {corr:.3f}")
    else:
        print("  ✅ 未检测到高相关性")

    # 正交化建议
    print("\n[正交化建议]")
    suggestions = monitor.get_orthogonalization_suggestions()
    print(f"  状态: {suggestions['status']}")

    if suggestions['redundant_factors']:
        print(f"  冗余因子: {', '.join(suggestions['redundant_factors'][:3])}")

    # 生成报告
    print("\n[生成报告]")
    report = monitor.generate_report()

    # 保存报告
    report_path = "/tmp/factor_correlation_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"  报告已保存到: {report_path}")

    # 显示报告（前30行）
    print("\n[报告预览]")
    print("-" * 70)
    lines = report.split("\n")
    for line in lines[:30]:
        print(line)
    if len(lines) > 30:
        print(f"... ({len(lines) - 30} more lines)")

    print("\n" + "=" * 70)
    print("✅ 因子相关性监控器测试完成")
    print("=" * 70)
