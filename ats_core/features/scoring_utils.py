# coding: utf-8
"""
统一的评分工具函数

核心哲学：
- 50 分 = 中性基准
- 方向性评分：向上/增强 → 50-100，向下/减弱 → 0-50
- 使用软映射（tanh/sigmoid）而不是硬阈值
- 避免 0 分陷阱，所有指标都有区分度
"""
import math
from typing import Union

def directional_score(
    value: float,
    neutral: float = 0.0,
    scale: float = 1.0,
    max_bonus: float = 50.0,
    min_score: float = 10.0
) -> int:
    """
    方向性评分：50分为中性，正向加分，负向减分

    核心逻辑：
    - 不关注绝对值，只关注相对于中性点的偏移
    - 使用 tanh 实现平滑的软映射
    - 连续、有界、中心对称
    - **避免0分陷阱**：设置最低分（默认10分）保留区分度

    Args:
        value: 指标值（变化率、比值等）
        neutral: 中性点（默认 0）
            - 对于变化率：neutral = 0（不变为中性）
            - 对于比值：neutral = 1.0（1倍为中性）
        scale: 缩放系数（调整灵敏度）
            - scale 越小，映射越陡峭（对小变化更敏感）
            - scale 越大，映射越平缓（需要大变化才能拉开差距）
            - 一般取值：abs(value) 在 scale 附近时，得分约在 60-70 之间
        max_bonus: 最大加分/减分（默认 ±50）
            - 通常设为 50，使得分数范围为 [min_score, 100]
        min_score: 最低分（默认 10）
            - 避免0分陷阱，即使完全反向也保留区分度
            - 设为0可恢复旧行为

    Returns:
        min_score ~ 100 的分数（默认10-100）

    Examples:
        # OI 变化率评分（neutral=0, scale=3.0）
        >>> directional_score(0.0, neutral=0, scale=3.0)
        50  # 0% 变化 → 中性

        >>> directional_score(3.0, neutral=0, scale=3.0)
        69  # +3% 变化 → 明显利好

        >>> directional_score(-3.0, neutral=0, scale=3.0)
        31  # -3% 变化 → 明显不利

        >>> directional_score(-100.0, neutral=0, scale=3.0)
        10  # 极端反向 → 最低分（而非0分）

        # 量能比值评分（neutral=1.0, scale=0.3）
        >>> directional_score(1.0, neutral=1.0, scale=0.3)
        50  # v5 = v20 → 中性

        >>> directional_score(1.3, neutral=1.0, scale=0.3)
        69  # v5 = 1.3*v20 → 放量

        >>> directional_score(0.7, neutral=1.0, scale=0.3)
        31  # v5 = 0.7*v20 → 缩量
    """
    # 计算相对于中性点的偏移
    deviation = value - neutral

    # tanh 映射：(-∞, +∞) → (-1, +1)
    # tanh(x) 特性：
    #   x = 0    → 0
    #   x = 1    → 0.76
    #   x = 2    → 0.96
    #   x → +∞   → 1
    normalized = math.tanh(deviation / scale)

    # 映射到 [min_score, 100]
    score = 50 + max_bonus * normalized

    # 截断到 [min_score, 100]（避免0分陷阱）
    return int(round(max(min_score, min(100.0, score))))


def sigmoid_score(
    value: float,
    center: float = 0.0,
    steepness: float = 1.0
) -> int:
    """
    Sigmoid 评分：另一种软映射方式

    相比 tanh，sigmoid 的曲线更陡峭，适合需要明确区分的场景

    Args:
        value: 指标值
        center: 中心点（50分对应的值）
        steepness: 陡峭度（越大曲线越陡）

    Returns:
        0-100 的分数
    """
    exponent = -steepness * (value - center)

    # 防止溢出
    if exponent > 20:
        return 0
    if exponent < -20:
        return 100

    score = 100 / (1 + math.exp(exponent))

    return int(round(max(0.0, min(100.0, score))))


def linear_clamped_score(
    value: float,
    min_val: float,
    max_val: float,
    min_score: float = 0.0,
    max_score: float = 100.0
) -> int:
    """
    线性映射评分（带截断）

    适用于有明确上下界的指标

    Args:
        value: 指标值
        min_val: 最小值（对应 min_score）
        max_val: 最大值（对应 max_score）
        min_score: 最低分（默认 0）
        max_score: 最高分（默认 100）

    Returns:
        min_score ~ max_score 的分数
    """
    if max_val == min_val:
        return int((min_score + max_score) / 2)

    # 线性插值
    ratio = (value - min_val) / (max_val - min_val)
    score = min_score + ratio * (max_score - min_score)

    # 截断
    return int(round(max(min_score, min(max_score, score))))
