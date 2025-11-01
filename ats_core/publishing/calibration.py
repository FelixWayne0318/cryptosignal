#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
概率分箱校准模块

功能：
- 将模型输出的S_total映射到真实胜率
- 通过分箱校准表修正模型偏差
- 支持动态更新校准表

规范：
- 借鉴外部方案的 platt_like 分箱校准思想
- 结合当前系统的 S_total 输出

校准流程：
1. 收集历史交易数据（S_total vs 实际胜负）
2. 按S_total分箱，计算每箱真实胜率
3. 生成校准表（threshold → calibrated_p）
4. 在线推理时查表映射

使用：
    from ats_core.publishing.calibration import calibrate_probability

    s_total = 45.2  # 模型输出
    p_calibrated = calibrate_probability(s_total)  # 校准后胜率
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import List, Tuple, Optional

# ==================== 默认校准表 ====================

# 占位校准表（需要用真实数据回填）
# 格式：[(S_total阈值, 真实胜率), ...]
# 说明：S_total ≤ threshold 时，使用对应的 calibrated_p
DEFAULT_CALIBRATION_TABLE: List[Tuple[float, float]] = [
    (-100.0, 0.30),  # S ≤ -100: 胜率30%
    (-50.0, 0.40),   # S ≤ -50: 胜率40%
    (-25.0, 0.45),   # S ≤ -25: 胜率45%
    (-10.0, 0.50),   # S ≤ -10: 胜率50%
    (0.0, 0.52),     # S ≤ 0: 胜率52%
    (10.0, 0.56),    # S ≤ 10: 胜率56%
    (25.0, 0.60),    # S ≤ 25: 胜率60%
    (50.0, 0.64),    # S ≤ 50: 胜率64%
    (100.0, 0.68),   # S ≤ 100: 胜率68%
]

# 校准表文件路径
CALIBRATION_TABLE_PATH = Path(__file__).parent.parent.parent / "configs" / "probability_calibration.json"


# ==================== 校准表管理 ====================

class CalibrationTable:
    """概率校准表管理器"""

    def __init__(self, table: Optional[List[Tuple[float, float]]] = None):
        """
        初始化校准表

        Args:
            table: 校准表 [(threshold, p), ...]，None则使用默认表
        """
        if table is None:
            table = DEFAULT_CALIBRATION_TABLE

        # 校验并排序
        self.table = sorted(table, key=lambda x: x[0])

        # 提取阈值和概率
        self.thresholds = [t for t, _ in self.table]
        self.probabilities = [p for _, p in self.table]

    def calibrate(self, s_total: float) -> float:
        """
        查表校准

        Args:
            s_total: 模型输出分数 [-100, 100]

        Returns:
            calibrated_p: 校准后胜率 [0, 1]
        """
        # 边界处理
        if s_total <= self.thresholds[0]:
            return self.probabilities[0]

        if s_total >= self.thresholds[-1]:
            return self.probabilities[-1]

        # 二分查找（找到第一个 threshold >= s_total）
        left, right = 0, len(self.thresholds) - 1
        while left < right:
            mid = (left + right) // 2
            if self.thresholds[mid] < s_total:
                left = mid + 1
            else:
                right = mid

        # 线性插值（可选，提高平滑度）
        if left > 0:
            t0, p0 = self.thresholds[left - 1], self.probabilities[left - 1]
            t1, p1 = self.thresholds[left], self.probabilities[left]

            # 插值权重
            if t1 - t0 > 1e-6:
                w = (s_total - t0) / (t1 - t0)
                return p0 + w * (p1 - p0)

        return self.probabilities[left]

    def save(self, path: Optional[Path] = None) -> None:
        """
        保存校准表到文件

        Args:
            path: 保存路径，None则使用默认路径
        """
        if path is None:
            path = CALIBRATION_TABLE_PATH

        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": "1.0",
            "description": "Probability calibration table (S_total → win_rate)",
            "table": [
                {"threshold": float(t), "probability": float(p)}
                for t, p in self.table
            ]
        }

        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> 'CalibrationTable':
        """
        从文件加载校准表

        Args:
            path: 文件路径，None则使用默认路径

        Returns:
            CalibrationTable实例
        """
        if path is None:
            path = CALIBRATION_TABLE_PATH

        if not path.exists():
            # 文件不存在，返回默认表
            return cls()

        with open(path, 'r') as f:
            data = json.load(f)

        table = [
            (item["threshold"], item["probability"])
            for item in data.get("table", [])
        ]

        return cls(table)


# ==================== 全局校准表实例 ====================

_calibration_table: Optional[CalibrationTable] = None


def get_calibration_table() -> CalibrationTable:
    """获取全局校准表实例（延迟加载）"""
    global _calibration_table
    if _calibration_table is None:
        _calibration_table = CalibrationTable.load()
    return _calibration_table


def reload_calibration_table() -> None:
    """重新加载校准表（用于动态更新）"""
    global _calibration_table
    _calibration_table = CalibrationTable.load()


# ==================== 便捷函数 ====================

def calibrate_probability(s_total: float) -> float:
    """
    校准概率（便捷函数）

    Args:
        s_total: 模型输出分数 [-100, 100]

    Returns:
        calibrated_p: 校准后胜率 [0, 1]

    示例：
        >>> calibrate_probability(45.2)
        0.62  # 插值结果

        >>> calibrate_probability(-15.0)
        0.47  # 插值结果
    """
    table = get_calibration_table()
    return table.calibrate(s_total)


def calibrate_probability_conservative(
    s_total: float,
    p_raw: Optional[float] = None
) -> float:
    """
    保守校准（取较小值）

    Args:
        s_total: 模型输出分数
        p_raw: 原始概率（如果提供），取 min(p_raw, p_calibrated)

    Returns:
        calibrated_p: 校准后胜率（保守）
    """
    p_calibrated = calibrate_probability(s_total)

    if p_raw is not None:
        return min(p_raw, p_calibrated)

    return p_calibrated


# ==================== 校准质量评估 ====================

def evaluate_calibration_quality(
    predictions: List[Tuple[float, bool]]
) -> dict:
    """
    评估校准表质量

    Args:
        predictions: [(s_total, actual_win), ...]
            - s_total: 模型输出分数
            - actual_win: 实际是否盈利 (True/False)

    Returns:
        metrics: {
            'mean_abs_error': 平均绝对误差,
            'brier_score': Brier分数,
            'samples_per_bin': 每箱样本数
        }

    说明：
        用于评估校准表的可靠性，MAE和Brier越小越好
    """
    table = get_calibration_table()

    # 按阈值分箱
    bins = {i: {'predicted': [], 'actual': []} for i in range(len(table.thresholds))}

    for s_total, actual_win in predictions:
        p_pred = table.calibrate(s_total)

        # 找到所属分箱
        bin_idx = 0
        for i, threshold in enumerate(table.thresholds):
            if s_total <= threshold:
                bin_idx = i
                break

        bins[bin_idx]['predicted'].append(p_pred)
        bins[bin_idx]['actual'].append(1.0 if actual_win else 0.0)

    # 计算指标
    total_abs_error = 0.0
    total_brier = 0.0
    total_samples = 0
    samples_per_bin = {}

    for bin_idx, data in bins.items():
        if not data['predicted']:
            samples_per_bin[bin_idx] = 0
            continue

        n = len(data['predicted'])
        samples_per_bin[bin_idx] = n

        # 平均预测概率 vs 实际胜率
        avg_pred = sum(data['predicted']) / n
        avg_actual = sum(data['actual']) / n

        # MAE
        abs_error = abs(avg_pred - avg_actual)
        total_abs_error += abs_error * n

        # Brier Score
        for p, a in zip(data['predicted'], data['actual']):
            total_brier += (p - a) ** 2

        total_samples += n

    mae = total_abs_error / total_samples if total_samples > 0 else 0.0
    brier = total_brier / total_samples if total_samples > 0 else 0.0

    return {
        'mean_abs_error': mae,
        'brier_score': brier,
        'samples_per_bin': samples_per_bin,
        'total_samples': total_samples
    }


# ==================== 默认表保存 ====================

def save_default_calibration_table() -> None:
    """保存默认校准表到文件（初始化用）"""
    table = CalibrationTable(DEFAULT_CALIBRATION_TABLE)
    table.save()
    print(f"✅ 默认校准表已保存到: {CALIBRATION_TABLE_PATH}")


if __name__ == '__main__':
    # 初始化：保存默认校准表
    save_default_calibration_table()

    # 测试校准
    test_scores = [-50, -10, 0, 10, 25, 50]
    print("\n校准测试：")
    for s in test_scores:
        p = calibrate_probability(s)
        print(f"  S_total={s:>6.1f} → P_win={p:.3f}")
