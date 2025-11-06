# coding: utf-8
"""
F（资金领先性）维度

核心理念：
因果链：资金是因，价格是果
- 最佳入场点：资金强势流入，但价格还未充分反应（蓄势待发）
- 追高风险：价格已经大涨，但资金流入减弱或流出（派发阶段）

F 的定义：
F = f(资金动量 - 价格动量)
范围：-100 到 +100（带符号）

- F >= +60：资金强势领先价格（蓄势待发）✅✅✅
- F >= +30：资金温和领先价格（机会较好）✅
- -30 < F < +30：资金价格同步（一般）
- F <= -30：价格温和领先资金（追高风险）⚠️
- F <= -60：价格强势领先资金（风险很大）❌

P0.4改进（crowding veto）：
- 检测市场过热（basis或funding极端）
- 在crowding时降低F因子分数（防止追高）
- 应用惩罚而非硬拒绝（保持连续性）

输入：
- oi_change_pct: OI 24小时变化率（%）
- vol_ratio: v5/v20 量能比值
- cvd_change: CVD 6小时变化（归一化）
- price_change_pct: 价格 24小时变化率（%）
- price_slope: 价格斜率（EMA30的斜率）
"""
from typing import Dict, Any, Tuple, Optional, List
from ats_core.features.scoring_utils import directional_score
import math
import numpy as np


def score_fund_leading(
    oi_change_pct: float,
    vol_ratio: float,
    cvd_change: float,
    price_change_pct: float,
    price_slope: float,
    params: Dict[str, Any],
    basis_history: Optional[List[float]] = None,
    funding_history: Optional[List[float]] = None
) -> Tuple[int, Dict[str, Any]]:
    """
    F（资金领先性）评分 - 移除circular dependency + P0.4 crowding veto

    计算资金动量与价格动量的差值（带符号）：
    - F > 0: 资金偏多（OI上升、CVD流入、价格上涨但不强）→ 看多信号
    - F < 0: 资金偏空（OI下降、CVD流出、价格下跌但不强）→ 看空信号

    P0.4新增：
    - 检测市场crowding（basis或funding极端）
    - 应用惩罚系数降低F分数（防止追高）

    Args:
        oi_change_pct: OI 24小时变化率（%），如 +3.5 表示上升 3.5%
        vol_ratio: v5/v20 量能比值，如 1.4 表示近期量能是均值的 1.4 倍
        cvd_change: CVD 6小时变化（归一化到价格），通常在 -0.05 ~ +0.05 范围
        price_change_pct: 价格 24小时变化率（%）
        price_slope: 价格斜率（EMA30 的斜率/ATR）
        params: 参数配置
        basis_history: 历史basis数据（bps），用于crowding检测（P0.4新增）
        funding_history: 历史funding rate数据，用于crowding检测（P0.4新增）

    Returns:
        (F分数 [-100, +100], 元数据)
    """
    # 默认参数
    default_params = {
        # 资金动量权重
        "oi_weight": 0.4,
        "vol_weight": 0.3,
        "cvd_weight": 0.3,
        # 价格动量权重
        "trend_weight": 0.6,
        "slope_weight": 0.4,
        # 评分参数
        "oi_scale": 3.0,        # OI 变化 3% 给约 69 分
        "vol_scale": 0.3,       # v5/v20 = 1.3 给约 69 分
        "cvd_scale": 0.02,      # CVD 变化 0.02 给约 69 分
        "price_scale": 3.0,     # 价格变化 3% 给约 69 分
        "slope_scale": 0.01,    # 斜率 0.01 给约 69 分
        "leading_scale": 200.0,  # P2.5++修复: 50→100→200，彻底解决饱和问题（leading_raw理论极限±200, tanh(1)≈0.76）
        # P0.4: Crowding veto参数
        "crowding_veto_enabled": True,   # 是否启用crowding veto
        "crowding_percentile": 90,        # 极端值判定百分位（90分位）
        "crowding_penalty": 0.5,          # 惩罚系数（0.5 = 50%折扣）
        "crowding_min_data": 100,         # 最少历史数据点
    }

    # 合并参数
    p = dict(default_params)
    if isinstance(params, dict):
        p.update(params)

    # ========== 1. 资金动量（绝对方向计算）==========
    # OI上升 → 正分，OI下降 → 负分
    # CVD流入 → 正分，CVD流出 → 负分
    # 量能放大 → 正分，量能萎缩 → 负分

    # P2.4修复：使用min_score=0确保对称映射（0-100而非10-100）
    oi_score = directional_score(oi_change_pct, neutral=0.0, scale=p["oi_scale"], min_score=0.0)
    cvd_score = directional_score(cvd_change, neutral=0.0, scale=p["cvd_scale"], min_score=0.0)
    vol_score = directional_score(vol_ratio, neutral=1.0, scale=p["vol_scale"], min_score=0.0)

    # 加权平均（返回 -100 到 +100 的带符号分数）
    # P2.4修复：映射 0-100 → -100到+100（对称映射，避免饱和）
    fund_momentum = (
        p["oi_weight"] * ((oi_score - 50) * 2) +
        p["vol_weight"] * ((vol_score - 50) * 2) +
        p["cvd_weight"] * ((cvd_score - 50) * 2)
    )

    # ========== 2. 价格动量（绝对方向计算）==========
    # 价格上涨 → 正分，价格下跌 → 负分
    # 斜率向上 → 正分，斜率向下 → 负分

    # P2.4修复：使用min_score=0确保对称映射
    trend_score = directional_score(price_change_pct, neutral=0.0, scale=p["price_scale"], min_score=0.0)
    slope_score = directional_score(price_slope, neutral=0.0, scale=p["slope_scale"], min_score=0.0)

    # 加权平均（返回 -100 到 +100 的带符号分数）
    # P2.4修复：映射 0-100 → -100到+100（对称映射，避免饱和）
    price_momentum = (
        p["trend_weight"] * ((trend_score - 50) * 2) +
        p["slope_weight"] * ((slope_score - 50) * 2)
    )

    # ========== 3. 资金领先性 ==========
    # leading = 资金动量 - 价格动量
    # leading > 0：资金强于价格（蓄势）✅
    # leading < 0：价格强于资金（追高）⚠️

    leading_raw = fund_momentum - price_momentum

    # 映射到 -100 到 +100（带符号）
    # 正数 = 资金领先价格（蓄势待发）
    # 负数 = 价格领先资金（追高风险）
    normalized = math.tanh(leading_raw / p["leading_scale"])
    F_raw = 100.0 * normalized

    # ========== 4. P0.4 Crowding Veto检测 ==========
    veto_penalty = 1.0
    veto_reasons = []
    veto_applied = False

    if p["crowding_veto_enabled"]:
        min_data = p["crowding_min_data"]
        percentile = p["crowding_percentile"]

        # Veto 1: Basis极端检测
        if basis_history and len(basis_history) >= min_data:
            basis_array = np.abs(basis_history)  # 使用绝对值
            basis_threshold = np.percentile(basis_array, percentile)
            current_basis = abs(basis_history[-1])

            if current_basis > basis_threshold:
                veto_penalty *= p["crowding_penalty"]
                veto_reasons.append(f"basis过热({current_basis:.1f} > q{percentile}={basis_threshold:.1f}bps)")
                veto_applied = True

        # Veto 2: Funding极端检测
        if funding_history and len(funding_history) >= min_data:
            funding_array = np.abs(funding_history)  # 使用绝对值
            funding_threshold = np.percentile(funding_array, percentile)
            current_funding = abs(funding_history[-1])

            if current_funding > funding_threshold:
                veto_penalty *= p["crowding_penalty"]
                veto_reasons.append(f"funding极端({current_funding:.4f} > q{percentile}={funding_threshold:.4f})")
                veto_applied = True

    # 应用veto惩罚
    F_final = F_raw * veto_penalty
    F = int(round(max(-100.0, min(100.0, F_final))))

    # ========== 5. 元数据 ==========
    meta = {
        "fund_momentum": round(fund_momentum, 1),
        "price_momentum": round(price_momentum, 1),
        "leading_raw": round(leading_raw, 1),
        "oi_score": oi_score,
        "vol_score": vol_score,
        "cvd_score": cvd_score,
        "trend_score": trend_score,
        "slope_score": slope_score,
        # 原始输入（便于调试）
        "oi_change_pct": round(oi_change_pct, 2),
        "vol_ratio": round(vol_ratio, 2),
        "cvd_change": round(cvd_change, 4),
        "price_change_pct": round(price_change_pct, 2),
        "price_slope": round(price_slope, 4),
        # P0.4: Crowding veto信息
        "F_raw": round(F_raw, 1),
        "veto_penalty": round(veto_penalty, 3),
        "veto_applied": veto_applied,
        "veto_reasons": veto_reasons if veto_reasons else None,
    }

    return F, meta


def interpret_F(F_score: int) -> str:
    """
    解释 F 分数的含义

    Args:
        F_score: F 维度分数 (-100 到 +100)

    Returns:
        中文解释
    """
    if F_score >= 60:
        return "资金强势领先价格 (蓄势待发)"
    elif F_score >= 30:
        return "资金温和领先价格 (机会较好)"
    elif F_score >= 10:
        return "资金略微领先 (同步偏好)"
    elif F_score >= -10:
        return "资金价格同步 (中性)"
    elif F_score >= -30:
        return "价格略微领先 (同步偏差)"
    elif F_score >= -60:
        return "价格温和领先资金 (追高风险)"
    else:
        return "价格强势领先资金 (风险很大)"
