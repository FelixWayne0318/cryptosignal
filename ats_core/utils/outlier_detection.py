# coding: utf-8
"""
异常值检测工具

提供IQR、MAD等方法检测和处理异常值
用于CVD、OI等指标的数据清洗
"""
from typing import List, Tuple
import math


def calculate_iqr(data: List[float]) -> Tuple[float, float, float]:
    """
    计算四分位距（IQR）

    Args:
        data: 数值序列

    Returns:
        (Q1, Q3, IQR)
    """
    if not data or len(data) < 4:
        return 0.0, 0.0, 0.0

    # 过滤有效值
    valid_data = [x for x in data if isinstance(x, (int, float)) and math.isfinite(x)]
    if len(valid_data) < 4:
        return 0.0, 0.0, 0.0

    # 排序
    sorted_data = sorted(valid_data)
    n = len(sorted_data)

    # 计算Q1和Q3
    q1_idx = int(0.25 * (n - 1))
    q3_idx = int(0.75 * (n - 1))

    q1 = sorted_data[q1_idx]
    q3 = sorted_data[q3_idx]
    iqr = q3 - q1

    return q1, q3, iqr


def detect_outliers_iqr(
    data: List[float],
    multiplier: float = 1.5
) -> List[bool]:
    """
    使用IQR方法检测异常值

    Args:
        data: 数值序列
        multiplier: IQR乘数（通常1.5为温和，3.0为极端）

    Returns:
        bool列表，True表示异常值

    方法:
        异常值定义为：
        - value < Q1 - multiplier * IQR
        - value > Q3 + multiplier * IQR
    """
    if not data:
        return []

    q1, q3, iqr = calculate_iqr(data)

    if iqr == 0:
        # IQR为0说明数据几乎相同，没有异常值
        return [False] * len(data)

    lower_bound = q1 - multiplier * iqr
    upper_bound = q3 + multiplier * iqr

    outliers = []
    for x in data:
        if not isinstance(x, (int, float)) or not math.isfinite(x):
            outliers.append(False)
        elif x < lower_bound or x > upper_bound:
            outliers.append(True)
        else:
            outliers.append(False)

    return outliers


def detect_volume_outliers(
    volumes: List[float],
    cvd_deltas: List[float],
    multiplier: float = 1.5
) -> List[bool]:
    """
    专门用于CVD的异常值检测

    检测成交量异常（巨量K线）

    Args:
        volumes: 成交量序列
        cvd_deltas: CVD delta序列（买入-卖出）
        multiplier: IQR乘数

    Returns:
        bool列表，True表示异常值
    """
    return detect_outliers_iqr(volumes, multiplier)


def apply_outlier_weights(
    values: List[float],
    outlier_mask: List[bool],
    outlier_weight: float = 0.5
) -> List[float]:
    """
    对异常值应用权重

    Args:
        values: 原始数值
        outlier_mask: 异常值标记
        outlier_weight: 异常值权重（0-1），默认0.5表示降低50%

    Returns:
        调整后的数值
    """
    if len(values) != len(outlier_mask):
        return values

    adjusted = []
    for i, val in enumerate(values):
        if outlier_mask[i]:
            adjusted.append(val * outlier_weight)
        else:
            adjusted.append(val)

    return adjusted


def calculate_mad(data: List[float]) -> float:
    """
    计算中位数绝对偏差（MAD）

    更鲁棒的离散度度量

    Args:
        data: 数值序列

    Returns:
        MAD值
    """
    if not data or len(data) < 2:
        return 0.0

    valid_data = [x for x in data if isinstance(x, (int, float)) and math.isfinite(x)]
    if len(valid_data) < 2:
        return 0.0

    # 计算中位数
    sorted_data = sorted(valid_data)
    n = len(sorted_data)
    median_idx = n // 2
    if n % 2 == 0:
        median = (sorted_data[median_idx - 1] + sorted_data[median_idx]) / 2
    else:
        median = sorted_data[median_idx]

    # 计算偏差的中位数
    deviations = [abs(x - median) for x in valid_data]
    sorted_dev = sorted(deviations)
    n_dev = len(sorted_dev)
    mad_idx = n_dev // 2
    if n_dev % 2 == 0:
        mad = (sorted_dev[mad_idx - 1] + sorted_dev[mad_idx]) / 2
    else:
        mad = sorted_dev[mad_idx]

    return mad


def detect_outliers_mad(
    data: List[float],
    threshold: float = 3.0
) -> List[bool]:
    """
    使用MAD方法检测异常值

    比IQR更鲁棒（对极端值不敏感）

    Args:
        data: 数值序列
        threshold: MAD阈值（通常3.0）

    Returns:
        bool列表，True表示异常值
    """
    if not data or len(data) < 2:
        return [False] * len(data)

    valid_data = [x for x in data if isinstance(x, (int, float)) and math.isfinite(x)]
    if len(valid_data) < 2:
        return [False] * len(data)

    # 计算中位数
    sorted_data = sorted(valid_data)
    n = len(sorted_data)
    median_idx = n // 2
    if n % 2 == 0:
        median = (sorted_data[median_idx - 1] + sorted_data[median_idx]) / 2
    else:
        median = sorted_data[median_idx]

    mad = calculate_mad(data)
    if mad == 0:
        return [False] * len(data)

    # 检测异常值
    outliers = []
    for x in data:
        if not isinstance(x, (int, float)) or not math.isfinite(x):
            outliers.append(False)
        else:
            deviation = abs(x - median) / mad
            outliers.append(deviation > threshold)

    return outliers


def get_outlier_stats(outlier_mask: List[bool]) -> dict:
    """
    获取异常值统计信息

    Args:
        outlier_mask: 异常值标记

    Returns:
        统计信息字典
    """
    if not outlier_mask:
        return {
            "total": 0,
            "outliers": 0,
            "outlier_rate": 0.0
        }

    total = len(outlier_mask)
    outliers = sum(outlier_mask)
    outlier_rate = outliers / total if total > 0 else 0.0

    return {
        "total": total,
        "outliers": outliers,
        "outlier_rate": round(outlier_rate, 3),
        "clean_data_points": total - outliers
    }
