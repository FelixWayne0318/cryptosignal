# coding: utf-8
"""
VIF (Variance Inflation Factor) 监控器 - v7.3.47

功能:
- 检测因子间多重共线性
- 计算每个因子的VIF值
- 生成警告和建议

理论依据:
- VIF = 1 / (1 - R²)
- VIF > 3: 存在共线性
- VIF > 5: 严重共线性
- VIF > 10: 需要删除因子

参考: 世界顶级量化基金标准 (Renaissance/Two Sigma)
"""

from typing import Dict, List, Tuple
import numpy as np
from ats_core.logging import warn, log


class VIFMonitor:
    """方差膨胀因子监控器 - 检测多重共线性"""

    def __init__(self, vif_threshold: float = 3.0):
        """
        初始化VIF监控器

        Args:
            vif_threshold: VIF阈值,超过此值则警告 (业界标准: 3-5)
        """
        self.vif_threshold = vif_threshold
        self.factor_names = ['T', 'M', 'C', 'V', 'O', 'B']

    def calculate_vif(self, factor_scores: Dict[str, List[float]]) -> Dict[str, float]:
        """
        计算每个因子的VIF

        Args:
            factor_scores: 因子评分字典 {'T': [score1, score2, ...], 'M': [...], ...}

        Returns:
            VIF字典 {'T': vif_value, 'M': vif_value, ...}

        公式:
            VIF_i = 1 / (1 - R²_i)
            其中 R²_i 是因子i对其他所有因子回归的决定系数
        """
        # 转换为矩阵
        try:
            factor_list = [factor_scores[f] for f in self.factor_names if f in factor_scores]
            if not factor_list:
                return {}

            X = np.array(factor_list).T  # (n_samples, n_factors)
            n_samples, n_factors = X.shape

            if n_samples < n_factors + 1:
                warn(f"样本数({n_samples})不足,无法计算VIF")
                return {}

            vif_dict = {}

            for i, factor_name in enumerate(self.factor_names[:n_factors]):
                try:
                    # 因子i
                    y = X[:, i]

                    # 其他因子
                    X_others = np.delete(X, i, axis=1)

                    # 线性回归: y = X_others @ beta
                    # 使用正规方程: beta = (X'X)^(-1) X'y
                    XtX = X_others.T @ X_others
                    Xty = X_others.T @ y

                    # 求解
                    beta = np.linalg.solve(XtX, Xty)

                    # 预测值
                    y_pred = X_others @ beta

                    # R²
                    ss_res = np.sum((y - y_pred) ** 2)
                    ss_tot = np.sum((y - np.mean(y)) ** 2)
                    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

                    # VIF = 1 / (1 - R²)
                    vif = 1.0 / (1.0 - r2) if r2 < 0.9999 else 999.0

                    vif_dict[factor_name] = vif

                except np.linalg.LinAlgError:
                    # 矩阵奇异,无法求解
                    vif_dict[factor_name] = 999.0
                except Exception as e:
                    warn(f"计算{factor_name}因子VIF失败: {e}")
                    vif_dict[factor_name] = 0.0

            return vif_dict

        except Exception as e:
            warn(f"VIF计算失败: {e}")
            return {}

    def check_collinearity(self, factor_scores: Dict[str, List[float]]) -> Tuple[bool, List[str]]:
        """
        检查因子共线性

        Args:
            factor_scores: 因子评分字典

        Returns:
            (is_ok, warnings)
            - is_ok: True if VIF都合格, False if存在共线性
            - warnings: 警告列表
        """
        vif_dict = self.calculate_vif(factor_scores)

        if not vif_dict:
            return True, []

        warnings = []
        is_ok = True

        for factor, vif in vif_dict.items():
            if vif > 10.0:
                warnings.append(f"🔴 {factor} VIF={vif:.2f} > 10 (严重共线性,建议删除)")
                is_ok = False
            elif vif > 5.0:
                warnings.append(f"🟠 {factor} VIF={vif:.2f} > 5 (高度共线性,需注意)")
                is_ok = False
            elif vif > self.vif_threshold:
                warnings.append(f"🟡 {factor} VIF={vif:.2f} > {self.vif_threshold} (存在共线性)")
                is_ok = False

        # 输出结果
        if warnings:
            log("=" * 60)
            log("VIF监控警告:")
            for w in warnings:
                warn(w)
            log("=" * 60)

        return is_ok, warnings

    def get_correlation_matrix(self, factor_scores: Dict[str, List[float]]) -> Dict[str, Dict[str, float]]:
        """
        计算因子相关系数矩阵 (辅助诊断)

        Args:
            factor_scores: 因子评分字典

        Returns:
            相关系数矩阵 {'T': {'M': corr_TM, 'C': corr_TC, ...}, ...}
        """
        try:
            factor_list = [factor_scores[f] for f in self.factor_names if f in factor_scores]
            X = np.array(factor_list).T

            # 计算相关系数矩阵
            corr_matrix = np.corrcoef(X.T)

            # 转换为字典
            n_factors = len(factor_list)
            result = {}
            for i, f1 in enumerate(self.factor_names[:n_factors]):
                result[f1] = {}
                for j, f2 in enumerate(self.factor_names[:n_factors]):
                    if i != j:
                        result[f1][f2] = float(corr_matrix[i, j])

            return result

        except Exception as e:
            warn(f"相关系数矩阵计算失败: {e}")
            return {}


# 全局单例
_vif_monitor_instance = None


def get_vif_monitor(vif_threshold: float = 3.0) -> VIFMonitor:
    """
    获取VIF监控器实例 (单例模式)

    Args:
        vif_threshold: VIF阈值

    Returns:
        VIFMonitor实例
    """
    global _vif_monitor_instance
    if _vif_monitor_instance is None:
        _vif_monitor_instance = VIFMonitor(vif_threshold)
    return _vif_monitor_instance


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("VIF监控器测试")
    print("=" * 60)

    # 模拟因子评分数据
    import random
    n_samples = 100

    # Case 1: 独立因子 (VIF应该接近1)
    factor_scores_independent = {
        'T': [random.gauss(0, 1) for _ in range(n_samples)],
        'M': [random.gauss(0, 1) for _ in range(n_samples)],
        'C': [random.gauss(0, 1) for _ in range(n_samples)],
    }

    # Case 2: 高度相关因子 (T和M相关性0.9)
    base = [random.gauss(0, 1) for _ in range(n_samples)]
    factor_scores_correlated = {
        'T': [b + random.gauss(0, 0.1) for b in base],
        'M': [b + random.gauss(0, 0.1) for b in base],
        'C': [random.gauss(0, 1) for _ in range(n_samples)],
    }

    monitor = get_vif_monitor()

    print("\nCase 1: 独立因子")
    vif1 = monitor.calculate_vif(factor_scores_independent)
    for f, v in vif1.items():
        print(f"  {f}: VIF={v:.2f}")

    print("\nCase 2: 高度相关因子")
    vif2 = monitor.calculate_vif(factor_scores_correlated)
    for f, v in vif2.items():
        print(f"  {f}: VIF={v:.2f}")

    print("\n✅ VIF监控器测试完成")
