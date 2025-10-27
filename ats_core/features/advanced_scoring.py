# coding: utf-8
"""
高级评分系统（v2.1）

集成所有改进：
- 多周期EMA验证（金字塔）
- 趋势持续时间因子
- 指标权重自适应调整
- 动态参数调整
"""
from typing import Dict, List, Tuple, Optional
import math
from ats_core.utils.adaptive_params import (
    get_adaptive_params_bundle,
    calculate_historical_atr,
    should_be_conservative,
    get_conservative_weight_adjustment
)


def calculate_ema(data: List[float], period: int) -> List[float]:
    """
    计算EMA

    Args:
        data: 价格序列
        period: EMA周期

    Returns:
        EMA序列
    """
    if not data or period <= 0:
        return []

    alpha = 2.0 / (period + 1.0)
    ema_values = []
    ema = data[0]
    ema_values.append(ema)

    for i in range(1, len(data)):
        ema = alpha * data[i] + (1 - alpha) * ema
        ema_values.append(ema)

    return ema_values


def validate_multi_ema_pyramid(
    closes: List[float],
    ema_periods: List[int] = [5, 10, 20, 30, 50]
) -> Dict[str, any]:
    """
    多周期EMA金字塔验证

    Args:
        closes: 收盘价序列
        ema_periods: EMA周期列表（从短到长）

    Returns:
        验证结果字典

    逻辑:
        金字塔排列：EMA5 > EMA10 > EMA20 > EMA30 > EMA50 = 强多头
        逆金字塔：EMA5 < EMA10 < EMA20 < EMA30 < EMA50 = 强空头
    """
    if len(closes) < max(ema_periods):
        return {
            "is_bullish_pyramid": False,
            "is_bearish_pyramid": False,
            "alignment_score": 0,
            "aligned_count": 0
        }

    # 计算所有EMA
    emas = {}
    for period in ema_periods:
        emas[period] = calculate_ema(closes, period)

    # 检查最后一个时间点的EMA排列
    current_emas = {period: emas[period][-1] for period in ema_periods}

    # 检查是否形成金字塔（多头）或逆金字塔（空头）
    is_bullish_pyramid = True
    is_bearish_pyramid = True
    aligned_count = 0

    for i in range(len(ema_periods) - 1):
        short_period = ema_periods[i]
        long_period = ema_periods[i + 1]

        if current_emas[short_period] > current_emas[long_period]:
            aligned_count += 1  # 多头对齐
        else:
            is_bullish_pyramid = False

        if current_emas[short_period] < current_emas[long_period]:
            pass  # 空头对齐
        else:
            is_bearish_pyramid = False

    # 对齐分数（0-100）
    max_pairs = len(ema_periods) - 1
    alignment_score = int((aligned_count / max_pairs) * 100) if max_pairs > 0 else 0

    return {
        "is_bullish_pyramid": is_bullish_pyramid,
        "is_bearish_pyramid": is_bearish_pyramid,
        "alignment_score": alignment_score,  # 多头对齐分数
        "aligned_count": aligned_count,
        "total_pairs": max_pairs,
        "current_emas": current_emas
    }


def calculate_trend_duration(
    closes: List[float],
    ema_period: int = 20
) -> Tuple[int, str]:
    """
    计算趋势持续时间

    Args:
        closes: 收盘价序列
        ema_period: EMA周期（用于判断趋势）

    Returns:
        (持续时间, 趋势方向)

    逻辑:
        持续时间 = 价格连续位于EMA同一侧的K线数量
    """
    if len(closes) < ema_period + 1:
        return 0, "neutral"

    ema = calculate_ema(closes, ema_period)

    # 从最新K线向前追溯
    duration = 0
    current_side = None

    for i in range(len(closes) - 1, max(ema_period - 1, -1), -1):
        if i >= len(ema):
            break

        # 判断价格在EMA上方还是下方
        if closes[i] > ema[i]:
            side = "上方"
        elif closes[i] < ema[i]:
            side = "下方"
        else:
            side = "中性"

        if current_side is None:
            current_side = side
            duration = 1
        elif side == current_side:
            duration += 1
        else:
            break

    # 判断趋势方向
    if current_side == "上方":
        direction = "uptrend"
    elif current_side == "下方":
        direction = "downtrend"
    else:
        direction = "neutral"

    return duration, direction


def get_trend_age_factor(duration: int) -> float:
    """
    根据趋势持续时间计算年龄因子

    Args:
        duration: 趋势持续时间（K线数量）

    Returns:
        年龄因子（0.7-1.0）

    逻辑:
        - 新趋势（1-5根K线）: 100%权重（新鲜，可信）
        - 中期趋势（6-20根）: 95%权重
        - 老趋势（21-50根）: 85%权重
        - 末期趋势（>50根）: 70%权重（可能反转）
    """
    if duration <= 5:
        return 1.0   # 新趋势
    elif duration <= 20:
        return 0.95  # 中期趋势
    elif duration <= 50:
        return 0.85  # 老趋势
    else:
        return 0.70  # 末期趋势（警惕反转）


def get_adaptive_weights(
    base_weights: Dict[str, float],
    atr_percentile: float,
    cvd_crowding: bool = False,
    oi_crowding: bool = False,
    trend_age_factor: float = 1.0,
    ema_alignment_score: int = 0
) -> Dict[str, float]:
    """
    自适应调整指标权重

    Args:
        base_weights: 基础权重配置
        atr_percentile: ATR百分位
        cvd_crowding: CVD是否拥挤
        oi_crowding: OI是否拥挤
        trend_age_factor: 趋势年龄因子
        ema_alignment_score: EMA对齐分数（0-100）

    Returns:
        调整后的权重

    逻辑:
        1. 高波动：降低CVD/OI权重，提升趋势权重
        2. 拥挤：降低CVD/OI权重
        3. 老趋势：降低趋势权重
        4. EMA强对齐：提升趋势权重
    """
    adjusted = base_weights.copy()

    # 1. 高波动市场调整
    if atr_percentile >= 0.8:
        # 高波动：趋势更重要，CVD/OI次要
        adjusted["T"] = base_weights["T"] * 1.2
        adjusted["C"] = base_weights["C"] * 0.8
        adjusted["O"] = base_weights["O"] * 0.8

    # 2. 低波动市场调整
    elif atr_percentile <= 0.2:
        # 低波动：CVD/OI更重要，趋势可能假信号
        adjusted["T"] = base_weights["T"] * 0.9
        adjusted["C"] = base_weights["C"] * 1.1
        adjusted["O"] = base_weights["O"] * 1.1

    # 3. 拥挤度调整
    if cvd_crowding:
        adjusted["C"] = adjusted["C"] * 0.8

    if oi_crowding:
        adjusted["O"] = adjusted["O"] * 0.8

    # 4. 趋势年龄调整
    adjusted["T"] = adjusted["T"] * trend_age_factor
    adjusted["M"] = adjusted["M"] * trend_age_factor

    # 5. EMA对齐度调整
    if ema_alignment_score >= 80:
        # 强对齐：提升趋势权重
        adjusted["T"] = adjusted["T"] * 1.1
    elif ema_alignment_score <= 20:
        # 弱对齐：降低趋势权重
        adjusted["T"] = adjusted["T"] * 0.9

    # 归一化权重（保持总和不变）
    total = sum(adjusted.values())
    original_total = sum(base_weights.values())

    if total > 0:
        scale_factor = original_total / total
        for key in adjusted:
            adjusted[key] = adjusted[key] * scale_factor

    return adjusted


def get_advanced_scoring_context(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    base_weights: Dict[str, float],
    cvd_crowding: bool = False,
    oi_crowding: bool = False
) -> Dict[str, any]:
    """
    获取高级评分上下文（所有改进的综合）

    Args:
        highs: 最高价序列
        lows: 最低价序列
        closes: 收盘价序列
        base_weights: 基础权重配置
        cvd_crowding: CVD是否拥挤
        oi_crowding: OI是否拥挤

    Returns:
        高级评分上下文字典

    包含:
        - ATR百分位
        - 市场状态
        - 自适应参数
        - EMA金字塔验证
        - 趋势持续时间
        - 调整后权重
    """
    # 1. 计算ATR历史分布
    historical_atrs = calculate_historical_atr(highs, lows, closes, period=14)

    if not historical_atrs:
        # 数据不足，返回默认值
        return {
            "atr_percentile": 0.5,
            "market_regime": "normal",
            "adaptive_params": {},
            "ema_validation": {},
            "trend_duration": 0,
            "trend_direction": "neutral",
            "trend_age_factor": 1.0,
            "adjusted_weights": base_weights,
            "is_conservative": False
        }

    current_atr = historical_atrs[-1]

    # 2. 获取自适应参数
    adaptive_params = get_adaptive_params_bundle(current_atr, historical_atrs)

    # 3. EMA金字塔验证
    ema_validation = validate_multi_ema_pyramid(closes)

    # 4. 趋势持续时间
    trend_duration, trend_direction = calculate_trend_duration(closes, ema_period=20)
    trend_age_factor = get_trend_age_factor(trend_duration)

    # 5. 自适应权重调整
    adjusted_weights = get_adaptive_weights(
        base_weights=base_weights,
        atr_percentile=adaptive_params["atr_percentile"],
        cvd_crowding=cvd_crowding,
        oi_crowding=oi_crowding,
        trend_age_factor=trend_age_factor,
        ema_alignment_score=ema_validation["alignment_score"]
    )

    # 6. 判断是否应该保守
    is_conservative = should_be_conservative(
        atr_percentile=adaptive_params["atr_percentile"],
        cvd_crowding=cvd_crowding,
        oi_crowding=oi_crowding
    )

    return {
        "atr_percentile": adaptive_params["atr_percentile"],
        "market_regime": adaptive_params["market_regime"],
        "adaptive_params": adaptive_params,
        "ema_validation": ema_validation,
        "trend_duration": trend_duration,
        "trend_direction": trend_direction,
        "trend_age_factor": round(trend_age_factor, 3),
        "adjusted_weights": adjusted_weights,
        "is_conservative": is_conservative
    }
