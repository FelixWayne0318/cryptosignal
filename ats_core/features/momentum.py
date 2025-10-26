# coding: utf-8
"""
M（动量）维度 - 价格动量/加速度（±100系统）

核心指标：
- 价格斜率的变化（加速度）
- EMA30斜率

返回范围：-100（强烈看空）~ 0（中性）~ +100（强烈看多）
"""
from typing import List, Tuple, Dict, Any
from .ta_core import ema, atr
from .scoring_utils import directional_score

def score_momentum(
    h: List[float],
    l: List[float],
    c: List[float],
    params: Dict[str, Any] = None
) -> Tuple[int, Dict[str, Any]]:
    """
    M（动量）维度评分 - 统一±100系统

    不再需要side_long参数，直接返回带符号的分数：
    - 正值：看多（价格加速上涨）
    - 负值：看空（价格加速下跌）
    - 0：中性

    Args:
        h: 最高价列表
        l: 最低价列表
        c: 收盘价列表
        params: 参数配置

    Returns:
        (M分数 [-100, +100], 元数据)
    """
    # 默认参数
    default_params = {
        "slope_lookback": 12,      # EMA周期（优化：30→12，更快响应）
        "slope_scale": 0.01,       # 斜率scale
        "accel_scale": 0.005,      # 加速度scale
        "slope_weight": 0.6,       # 斜率权重
        "accel_weight": 0.4,       # 加速度权重
        "atr_period": 14,          # ATR周期
    }

    p = dict(default_params)
    if isinstance(params, dict):
        p.update(params)

    if len(c) < 30:
        return 0, {"slope_now": 0.0, "accel": 0.0, "slope_score": 0, "accel_score": 0}

    # ========== 1. 计算 EMA30 斜率 ==========
    ema30 = ema(c, p["slope_lookback"])

    # 当前斜率（最近7根K线）
    slope_now = (ema30[-1] - ema30[-7]) / 6.0

    # 前一段斜率（用于计算加速度）
    slope_prev = (ema30[-7] - ema30[-13]) / 6.0

    # 加速度 = 斜率的变化
    accel = slope_now - slope_prev

    # ========== 2. 归一化到真实ATR ==========
    # 使用真实ATR而非价格代理（修复：原来的atr_proxy导致M分数被低估50-70%）
    atr_values = atr(h, l, c, p["atr_period"])
    atr_val = atr_values[-1] if atr_values else 1.0
    slope_normalized = slope_now / max(1e-9, atr_val)
    accel_normalized = accel / max(1e-9, atr_val)

    # ========== 3. 软映射评分（±100系统）==========
    # directional_score 返回 10-100，需要映射到 -100到+100
    slope_score_raw = directional_score(
        slope_normalized,
        neutral=0.0,
        scale=p["slope_scale"]
    )
    accel_score_raw = directional_score(
        accel_normalized,
        neutral=0.0,
        scale=p["accel_scale"]
    )

    # 映射：10-100 → -100到+100
    # 公式：score_signed = (score_raw - 50) * 2
    slope_score = (slope_score_raw - 50) * 2
    accel_score = (accel_score_raw - 50) * 2

    # ========== 4. 加权平均 ==========
    M = p["slope_weight"] * slope_score + p["accel_weight"] * accel_score
    M = int(round(max(-100, min(100, M))))

    # ========== 5. 解释 ==========
    if M >= 60:
        interpretation = "强势上涨"
    elif M >= 20:
        interpretation = "温和上涨"
    elif M >= -20:
        interpretation = "中性"
    elif M >= -60:
        interpretation = "温和下跌"
    else:
        interpretation = "强势下跌"

    # ========== 6. 返回元数据 ==========
    return M, {
        "slope_now": round(slope_now, 6),
        "slope_prev": round(slope_prev, 6),
        "accel": round(accel, 6),
        "slope_normalized": round(slope_normalized, 6),
        "accel_normalized": round(accel_normalized, 6),
        "slope_score": int(slope_score),
        "accel_score": int(accel_score),
        "interpretation": interpretation
    }
