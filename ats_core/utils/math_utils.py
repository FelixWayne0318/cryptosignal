# coding: utf-8
"""
数学工具函数（v7.3.47新增）

提供通用的数学计算函数，包括：
- 线性插值/降低函数
- F因子多空适配函数
- 边界检查函数
"""

from typing import Union
import math


def linear_reduce(
    x: float,
    x_min: float,
    x_max: float,
    value_at_min: float,
    value_at_max: float
) -> float:
    """
    线性插值函数：x在[x_min, x_max]区间时，值在[value_at_min, value_at_max]线性变化

    适用场景：
    - F因子蓄势分级阈值降低
    - 概率校准线性调整
    - 任何需要平滑过渡的场景

    公式：
        if x >= x_max:
            return value_at_max
        elif x >= x_min:
            ratio = (x - x_min) / (x_max - x_min)
            return value_at_min + ratio * (value_at_max - value_at_min)
        else:
            return value_at_min

    Args:
        x: 当前值（如F值、I值等）
        x_min: x的最小阈值（如F=50）
        x_max: x的最大阈值（如F=70）
        value_at_min: x=x_min时的目标值（如confidence=15）
        value_at_max: x=x_max时的目标值（如confidence=10）

    Returns:
        线性插值后的值

    Examples:
        >>> # F因子蓄势阈值降低
        >>> confidence = linear_reduce(F=60, 50, 70, 15, 10)
        >>> # F=60时，confidence从15线性降到12.5
        >>> print(confidence)  # 12.5

        >>> # 概率校准
        >>> P_bonus = linear_reduce(F=50, 0, 70, 0, 0.05)
        >>> # F=50时，胜率增加3.6%
        >>> print(P_bonus)  # 0.036

    注意：
        - 支持value_at_max > value_at_min（递增）或 value_at_max < value_at_min（递减）
        - x超出[x_min, x_max]区间时会自动封顶/封底
        - 边界值x=x_min和x=x_max会返回精确的value_at_min和value_at_max
    """
    if x >= x_max:
        return value_at_max
    elif x >= x_min:
        # 线性插值公式：y = y1 + (x - x1) / (x2 - x1) * (y2 - y1)
        ratio = (x - x_min) / (x_max - x_min)
        return value_at_min + ratio * (value_at_max - value_at_min)
    else:
        return value_at_min


def get_effective_F(F: float, side_long: bool) -> float:
    """
    获取有效的F值（考虑做多/做空方向）

    核心理念：
    - F = 资金动量 - 价格动量
    - 做多时：F > 0 好（资金领先价格，蓄势）
    - 做空时：F < 0 好（资金流出快于价格下跌，恐慌逃离）

    做空时F的正确理解：
    - 资金流出10%，价格跌5%：F = -10% - (-5%) = -5% < 0 ✅ 好（资金恐慌逃离）
    - 资金流出5%，价格跌10%：F = -5% - (-10%) = +5% > 0 ❌ 差（有人抄底接盘）

    因此：做空时需要将F取反，使得F > 0 表示好信号

    Args:
        F: 原始F值
        side_long: True=做多, False=做空

    Returns:
        有效F值
        - 做多时：返回F（F > 0 好）
        - 做空时：返回-F（F < 0 好 → 取反后 > 0）

    Examples:
        >>> # 做多 + F=80（资金领先，蓄势待发）
        >>> F_eff = get_effective_F(80, side_long=True)
        >>> print(F_eff)  # 80（好信号）

        >>> # 做空 + F=80（资金流入慢于价格下跌，有人抄底）
        >>> F_eff = get_effective_F(80, side_long=False)
        >>> print(F_eff)  # -80（坏信号，取反后为负）

        >>> # 做空 + F=-80（资金流出快于价格下跌，恐慌逃离）
        >>> F_eff = get_effective_F(-80, side_long=False)
        >>> print(F_eff)  # 80（好信号，取反后为正）

    使用场景：
        - 蓄势分级：if get_effective_F(F, side_long) >= 70: ...
        - Gate 2拦截：if get_effective_F(F, side_long) >= F_min: ...
        - 概率校准：P_bonus = linear_reduce(get_effective_F(F, side_long), ...)
    """
    if side_long:
        return F  # 做多时F > 0 好
    else:
        return -F  # 做空时F < 0 好，取反后F > 0 好


def is_valid_number(value: Union[int, float]) -> bool:
    """
    检查数值是否有效（非NaN、非Inf）

    Args:
        value: 待检查的数值

    Returns:
        True if valid, False otherwise

    Examples:
        >>> is_valid_number(50.5)
        True
        >>> is_valid_number(float('nan'))
        False
        >>> is_valid_number(float('inf'))
        False
    """
    if value is None:
        return False
    return not (math.isnan(value) or math.isinf(value))


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    安全除法（防止除零、NaN、Inf）

    Args:
        numerator: 分子
        denominator: 分母
        default: 分母为0或结果异常时的默认值

    Returns:
        安全的除法结果

    Examples:
        >>> safe_divide(10, 2)
        5.0
        >>> safe_divide(10, 0)
        0.0
        >>> safe_divide(10, 0, default=1.0)
        1.0
    """
    if denominator == 0 or not is_valid_number(denominator):
        return default

    result = numerator / denominator

    if not is_valid_number(result):
        return default

    return result


def clamp(value: float, min_val: float, max_val: float) -> float:
    """
    将值限制在[min_val, max_val]区间内

    Args:
        value: 待限制的值
        min_val: 最小值
        max_val: 最大值

    Returns:
        限制后的值

    Examples:
        >>> clamp(50, 0, 100)
        50
        >>> clamp(150, 0, 100)
        100
        >>> clamp(-10, 0, 100)
        0
    """
    return max(min_val, min(max_val, value))


# 公开API
__all__ = [
    'linear_reduce',
    'get_effective_F',
    'is_valid_number',
    'safe_divide',
    'clamp'
]
