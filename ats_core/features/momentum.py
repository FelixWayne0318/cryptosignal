# coding: utf-8
"""
M（动量）维度 - 价格动量/加速度（v2.0 ±100对称设计）
从原A（加速）中分离出价格部分，不包含CVD

核心指标：
- 价格斜率的变化（加速度）
- EMA30斜率

改进v2.0：
- ✅ 分数范围：-100 到 +100（0为中性）
- ✅ 方向自包含：正值=向上动量，负值=向下动量
- ✅ 移除side_long：不再需要多空参数
- ✅ 使用对称评分函数
"""
from typing import List, Tuple, Dict, Any
from .ta_core import ema
from .scoring_utils import directional_score_symmetric

def score_momentum(
    c: List[float],
    params: Dict[str, Any] = None
) -> Tuple[int, Dict[str, Any]]:
    """
    M（动量）维度评分（v2.0 对称版本）

    Args:
        c: 收盘价列表
        params: 参数配置

    Returns:
        (M分数 -100~+100, 元数据)
        - 正值：向上动量（价格加速上涨）→ 适合做多
        - 负值：向下动量（价格加速下跌）→ 适合做空
        - 0：无明显动量 → 中性
    """
    # 默认参数
    default_params = {
        "slope_lookback": 30,      # EMA周期
        "slope_scale": 0.01,       # 斜率scale
        "accel_scale": 0.005,      # 加速度scale
        "slope_weight": 0.6,       # 斜率权重
        "accel_weight": 0.4,       # 加速度权重
    }

    p = dict(default_params)
    if isinstance(params, dict):
        p.update(params)

    if len(c) < 30:
        return 0, {
            "slope_now": 0.0,
            "accel": 0.0,
            "slope_score": 0,
            "accel_score": 0,
            "insufficient_data": True
        }

    # ========== 1. 计算 EMA30 斜率 ==========
    ema30 = ema(c, p["slope_lookback"])

    # 当前斜率（最近7根K线）
    slope_now = (ema30[-1] - ema30[-7]) / 6.0

    # 前一段斜率（用于计算加速度）
    slope_prev = (ema30[-7] - ema30[-13]) / 6.0

    # 加速度 = 斜率的变化
    accel = slope_now - slope_prev

    # ========== 2. 归一化到ATR代理 ==========
    # 使用价格的平均绝对值作为ATR代理
    atr_proxy = (sum([abs(x) for x in c[-30:]]) / 30.0) / 1000.0
    slope_normalized = slope_now / max(1e-9, atr_proxy)
    accel_normalized = accel / max(1e-9, atr_proxy)

    # ========== 3. 对称评分（无需side_long） ==========
    # 正值 = 上涨 = 利多
    # 负值 = 下跌 = 利空
    slope_score = directional_score_symmetric(
        slope_normalized,
        neutral=0.0,
        scale=p["slope_scale"]
    )  # -100 到 +100

    accel_score = directional_score_symmetric(
        accel_normalized,
        neutral=0.0,
        scale=p["accel_scale"]
    )  # -100 到 +100

    # ========== 4. 加权平均 ==========
    M = p["slope_weight"] * slope_score + p["accel_weight"] * accel_score
    M = int(round(max(-100, min(100, M))))

    # ========== 5. 返回元数据 ==========
    return M, {
        "slope_now": round(slope_now, 6),
        "slope_prev": round(slope_prev, 6),
        "accel": round(accel, 6),
        "slope_normalized": round(slope_normalized, 6),
        "accel_normalized": round(accel_normalized, 6),
        "slope_score": slope_score,
        "accel_score": accel_score,
        "interpretation": "向上" if M > 20 else ("向下" if M < -20 else "中性")
    }
