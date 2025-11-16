# coding: utf-8
"""
IC (Information Coefficient) 监控器 - v7.3.47

功能:
- 计算因子与未来收益的相关性
- 检测因子失效/退化
- 生成因子健康度报告

理论依据:
- IC = Spearman秩相关系数(因子评分, 未来收益)
- IC > 0.05: 优秀因子
- IC > 0.03: 良好因子
- IC > 0.01: 警告（需要关注）
- IC < 0.01: 建议禁用

参考: 世界顶级量化基金标准 (Renaissance/Two Sigma)
"""

from typing import Dict, List, Tuple, Optional
import numpy as np
from scipy import stats
from ats_core.logging import warn, log


class ICMonitor:
    """信息系数监控器 - 检测因子失效"""

    def __init__(self, ic_threshold: float = 0.03, lookback_window: int = 100):
        """
        初始化IC监控器

        Args:
            ic_threshold: IC最小值阈值 (业界标准: 0.03)
            lookback_window: IC计算的回看窗口
        """
        self.ic_threshold = ic_threshold
        self.lookback_window = lookback_window
        self.factor_names = ['T', 'M', 'C', 'V', 'O', 'B']

        # IC历史记录 {factor_name: [ic_values]}
        self.ic_history: Dict[str, List[float]] = {f: [] for f in self.factor_names}

    def calculate_ic(
        self,
        factor_scores: Dict[str, List[float]],
        future_returns: List[float],
        method: str = 'spearman'
    ) -> Dict[str, float]:
        """
        计算每个因子的IC值

        Args:
            factor_scores: 因子评分字典 {'T': [score1, score2, ...], 'M': [...], ...}
            future_returns: 未来收益率列表 (长度应与因子评分一致)
            method: 相关系数计算方法 ('spearman' 或 'pearson')

        Returns:
            IC字典 {'T': ic_value, 'M': ic_value, ...}

        公式:
            IC = Spearman秩相关系数(factor_scores, future_returns)

        Notes:
            - Spearman秩相关更鲁棒,不受极端值影响
            - IC的正负号表示因子方向（正相关/负相关）
            - |IC| 表示预测能力强度
        """
        try:
            ic_dict = {}
            n_samples = len(future_returns)

            if n_samples < 10:
                warn(f"样本数({n_samples})不足,无法计算IC")
                return {}

            for factor_name in self.factor_names:
                if factor_name not in factor_scores:
                    continue

                scores = factor_scores[factor_name]

                if len(scores) != n_samples:
                    warn(f"{factor_name}因子评分长度({len(scores)})与收益长度({n_samples})不一致")
                    continue

                try:
                    # 移除NaN值
                    valid_indices = []
                    for i in range(n_samples):
                        if not (np.isnan(scores[i]) or np.isnan(future_returns[i])):
                            valid_indices.append(i)

                    if len(valid_indices) < 10:
                        warn(f"{factor_name}有效样本不足")
                        ic_dict[factor_name] = 0.0
                        continue

                    valid_scores = [scores[i] for i in valid_indices]
                    valid_returns = [future_returns[i] for i in valid_indices]

                    # 计算相关系数
                    if method == 'spearman':
                        ic, p_value = stats.spearmanr(valid_scores, valid_returns)
                    elif method == 'pearson':
                        ic, p_value = stats.pearsonr(valid_scores, valid_returns)
                    else:
                        raise ValueError(f"不支持的相关系数方法: {method}")

                    # 检查NaN
                    if np.isnan(ic):
                        ic = 0.0

                    ic_dict[factor_name] = float(ic)

                    # 记录IC历史
                    self.ic_history[factor_name].append(float(ic))

                    # 保持历史长度在合理范围
                    if len(self.ic_history[factor_name]) > 1000:
                        self.ic_history[factor_name] = self.ic_history[factor_name][-1000:]

                except Exception as e:
                    warn(f"计算{factor_name}因子IC失败: {e}")
                    ic_dict[factor_name] = 0.0

            return ic_dict

        except Exception as e:
            warn(f"IC计算失败: {e}")
            return {}

    def check_factor_health(
        self,
        factor_scores: Dict[str, List[float]],
        future_returns: List[float]
    ) -> Tuple[Dict[str, str], List[str]]:
        """
        检查因子健康度

        Args:
            factor_scores: 因子评分字典
            future_returns: 未来收益率列表

        Returns:
            (health_status, warnings)
            - health_status: 因子健康度字典 {'T': '优秀', 'M': '良好', ...}
            - warnings: 警告列表

        健康度等级:
            - 优秀: IC > 0.05
            - 良好: 0.03 < IC <= 0.05
            - 警告: 0.01 < IC <= 0.03
            - 禁用: IC <= 0.01
        """
        ic_dict = self.calculate_ic(factor_scores, future_returns)

        if not ic_dict:
            return {}, []

        health_status = {}
        warnings = []

        for factor, ic in ic_dict.items():
            # 取绝对值（只关注预测能力强度，不关注方向）
            abs_ic = abs(ic)

            if abs_ic > 0.05:
                health_status[factor] = '优秀'
            elif abs_ic > 0.03:
                health_status[factor] = '良好'
            elif abs_ic > 0.01:
                health_status[factor] = '警告'
                warnings.append(f"🟡 {factor} IC={ic:.4f} (低于阈值 {self.ic_threshold},需要关注)")
            else:
                health_status[factor] = '禁用'
                warnings.append(f"🔴 {factor} IC={ic:.4f} (因子失效,建议禁用)")

        # 输出结果
        if warnings:
            log("=" * 60)
            log("IC监控警告:")
            for w in warnings:
                warn(w)
            log("=" * 60)

        return health_status, warnings

    def get_ic_stats(self, factor_name: str, window: int = 20) -> Optional[Dict[str, float]]:
        """
        获取因子IC统计量 (均值、标准差、最近N期)

        Args:
            factor_name: 因子名称
            window: 统计窗口

        Returns:
            统计量字典 {'mean': ..., 'std': ..., 'recent_mean': ...}
        """
        if factor_name not in self.ic_history:
            return None

        history = self.ic_history[factor_name]

        if not history:
            return None

        try:
            # 全部历史统计
            ic_mean = float(np.mean(history))
            ic_std = float(np.std(history))

            # 最近N期统计
            recent_history = history[-window:] if len(history) >= window else history
            recent_mean = float(np.mean(recent_history))
            recent_std = float(np.std(recent_history))

            return {
                'mean': ic_mean,
                'std': ic_std,
                'recent_mean': recent_mean,
                'recent_std': recent_std,
                'n_samples': len(history),
                'n_recent_samples': len(recent_history)
            }

        except Exception as e:
            warn(f"IC统计量计算失败: {e}")
            return None

    def get_ic_trend(self, factor_name: str, window: int = 20) -> Optional[str]:
        """
        判断IC趋势 (上升/稳定/下降)

        Args:
            factor_name: 因子名称
            window: 趋势判断窗口

        Returns:
            '上升' / '稳定' / '下降' / None
        """
        if factor_name not in self.ic_history:
            return None

        history = self.ic_history[factor_name]

        if len(history) < window * 2:
            return None

        try:
            # 前半段均值 vs 后半段均值
            first_half = history[-window * 2:-window]
            second_half = history[-window:]

            first_mean = np.mean(first_half)
            second_mean = np.mean(second_half)

            diff = second_mean - first_mean

            # 阈值: 0.01
            if diff > 0.01:
                return '上升'
            elif diff < -0.01:
                return '下降'
            else:
                return '稳定'

        except Exception as e:
            warn(f"IC趋势计算失败: {e}")
            return None

    def generate_report(self, factor_scores: Dict[str, List[float]], future_returns: List[float]) -> str:
        """
        生成因子IC监控报告

        Args:
            factor_scores: 因子评分字典
            future_returns: 未来收益率列表

        Returns:
            报告字符串
        """
        health_status, warnings = self.check_factor_health(factor_scores, future_returns)

        report = []
        report.append("=" * 60)
        report.append("因子IC监控报告 (v7.3.47)")
        report.append("=" * 60)
        report.append("")

        # 因子健康度
        report.append("因子健康度:")
        ic_dict = self.calculate_ic(factor_scores, future_returns)

        for factor in self.factor_names:
            if factor in ic_dict and factor in health_status:
                ic = ic_dict[factor]
                status = health_status[factor]

                # 获取统计量
                stats_info = self.get_ic_stats(factor)
                if stats_info:
                    report.append(
                        f"  {factor}: IC={ic:.4f} [{status}] "
                        f"(均值={stats_info['mean']:.4f}, 标准差={stats_info['std']:.4f})"
                    )
                else:
                    report.append(f"  {factor}: IC={ic:.4f} [{status}]")

        report.append("")

        # IC趋势
        report.append("IC趋势 (最近20期):")
        for factor in self.factor_names:
            trend = self.get_ic_trend(factor)
            if trend:
                emoji = "📈" if trend == "上升" else "📉" if trend == "下降" else "➡️"
                report.append(f"  {factor}: {emoji} {trend}")

        report.append("")
        report.append("=" * 60)

        return "\n".join(report)


# 全局单例
_ic_monitor_instance = None


def get_ic_monitor(ic_threshold: float = 0.03, lookback_window: int = 100) -> ICMonitor:
    """
    获取IC监控器实例 (单例模式)

    Args:
        ic_threshold: IC最小值阈值
        lookback_window: 回看窗口

    Returns:
        ICMonitor实例
    """
    global _ic_monitor_instance
    if _ic_monitor_instance is None:
        _ic_monitor_instance = ICMonitor(ic_threshold, lookback_window)
    return _ic_monitor_instance


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("IC监控器测试")
    print("=" * 60)

    # 模拟数据
    import random
    n_samples = 100

    # Case 1: 强预测因子 (IC应该 > 0.5)
    base_signal = [random.gauss(0, 1) for _ in range(n_samples)]
    future_returns_case1 = [s + random.gauss(0, 0.3) for s in base_signal]  # 强相关

    factor_scores_case1 = {
        'T': base_signal,
        'M': [random.gauss(0, 1) for _ in range(n_samples)],  # 无关
        'C': [random.gauss(0, 1) for _ in range(n_samples)],  # 无关
    }

    # Case 2: 弱预测因子 (IC应该 < 0.1)
    factor_scores_case2 = {
        'T': [random.gauss(0, 1) for _ in range(n_samples)],
        'M': [random.gauss(0, 1) for _ in range(n_samples)],
        'C': [random.gauss(0, 1) for _ in range(n_samples)],
    }
    future_returns_case2 = [random.gauss(0, 1) for _ in range(n_samples)]  # 纯随机

    monitor = get_ic_monitor()

    print("\nCase 1: 强预测因子 (T应该有高IC)")
    ic1 = monitor.calculate_ic(factor_scores_case1, future_returns_case1)
    for f, v in ic1.items():
        print(f"  {f}: IC={v:.4f}")

    health1, warnings1 = monitor.check_factor_health(factor_scores_case1, future_returns_case1)
    for f, status in health1.items():
        print(f"  {f}: {status}")

    print("\nCase 2: 弱预测因子 (所有因子IC应该接近0)")
    ic2 = monitor.calculate_ic(factor_scores_case2, future_returns_case2)
    for f, v in ic2.items():
        print(f"  {f}: IC={v:.4f}")

    health2, warnings2 = monitor.check_factor_health(factor_scores_case2, future_returns_case2)
    for f, status in health2.items():
        print(f"  {f}: {status}")

    print("\n" + "=" * 60)
    print("✅ IC监控器测试完成")
