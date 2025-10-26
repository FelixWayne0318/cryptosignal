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

输入：
- oi_change_pct: OI 24小时变化率（%）
- vol_ratio: v5/v20 量能比值
- cvd_change: CVD 6小时变化（归一化）
- price_change_pct: 价格 24小时变化率（%）
- price_slope: 价格斜率（EMA30的斜率）
"""
from typing import Dict, Any, Tuple
from ats_core.features.scoring_utils import directional_score
import math


def score_fund_leading(
    oi_change_pct: float,
    vol_ratio: float,
    cvd_change: float,
    price_change_pct: float,
    price_slope: float,
    params: Dict[str, Any]
) -> Tuple[int, Dict[str, Any]]:
    """
    F（资金领先性）评分 - 移除circular dependency

    计算资金动量与价格动量的差值（带符号）：
    - F > 0: 资金偏多（OI上升、CVD流入、价格上涨但不强）→ 看多信号
    - F < 0: 资金偏空（OI下降、CVD流出、价格下跌但不强）→ 看空信号

    Args:
        oi_change_pct: OI 24小时变化率（%），如 +3.5 表示上升 3.5%
        vol_ratio: v5/v20 量能比值，如 1.4 表示近期量能是均值的 1.4 倍
        cvd_change: CVD 6小时变化（归一化到价格），通常在 -0.05 ~ +0.05 范围
        price_change_pct: 价格 24小时变化率（%）
        price_slope: 价格斜率（EMA30 的斜率/ATR）
        params: 参数配置

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
        "leading_scale": 20.0,  # 领先性的缩放系数
    }

    # 合并参数
    p = dict(default_params)
    if isinstance(params, dict):
        p.update(params)

    # ========== 1. 资金动量（绝对方向计算）==========
    # OI上升 → 正分，OI下降 → 负分
    # CVD流入 → 正分，CVD流出 → 负分
    # 量能放大 → 正分，量能萎缩 → 负分

    oi_score = directional_score(oi_change_pct, neutral=0.0, scale=p["oi_scale"])
    cvd_score = directional_score(cvd_change, neutral=0.0, scale=p["cvd_scale"])
    vol_score = directional_score(vol_ratio, neutral=1.0, scale=p["vol_scale"])

    # 加权平均（返回 -100 到 +100 的带符号分数）
    # 映射：10-100 → -100到+100
    fund_momentum = (
        p["oi_weight"] * ((oi_score - 50) * 2) +
        p["vol_weight"] * ((vol_score - 50) * 2) +
        p["cvd_weight"] * ((cvd_score - 50) * 2)
    )

    # ========== 2. 价格动量（绝对方向计算）==========
    # 价格上涨 → 正分，价格下跌 → 负分
    # 斜率向上 → 正分，斜率向下 → 负分

    trend_score = directional_score(price_change_pct, neutral=0.0, scale=p["price_scale"])
    slope_score = directional_score(price_slope, neutral=0.0, scale=p["slope_scale"])

    # 加权平均（返回 -100 到 +100 的带符号分数）
    # 映射：10-100 → -100到+100
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
    F = 100.0 * normalized
    F = int(round(max(-100.0, min(100.0, F))))

    # ========== 4. 元数据 ==========
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
