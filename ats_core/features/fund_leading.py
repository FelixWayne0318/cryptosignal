# coding: utf-8
"""
F（资金领先性）维度

核心理念：
因果链：资金是因，价格是果
- 最佳入场点：资金强势流入，但价格还未充分反应（蓄势待发）
- 追高风险：价格已经大涨，但资金流入减弱或流出（派发阶段）

F 的定义：
F = f(资金动量 - 价格动量)
- F > 70：资金明显领先价格（最佳入场点）✅✅✅
- F = 50-70：资金略微领先（可以考虑）✅
- F = 30-50：资金价格同步（一般）
- F < 30：价格领先资金（追高风险）❌

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
    side_long: bool,
    params: Dict[str, Any]
) -> Tuple[int, Dict[str, Any]]:
    """
    F（资金领先性）评分

    Args:
        oi_change_pct: OI 24小时变化率（%），如 +3.5 表示上升 3.5%
        vol_ratio: v5/v20 量能比值，如 1.4 表示近期量能是均值的 1.4 倍
        cvd_change: CVD 6小时变化（归一化到价格），通常在 -0.05 ~ +0.05 范围
        price_change_pct: 价格 24小时变化率（%）
        price_slope: 价格斜率（EMA30 的斜率/ATR）
        side_long: 是否做多方向
        params: 参数配置

    Returns:
        (F分数, 元数据)
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

    # ========== 1. 资金动量 ==========
    # 做多时：希望 OI 上升、量能放大、CVD 流入
    # 做空时：希望 OI 下降、量能放大、CVD 流出

    if side_long:
        # 做多方向
        oi_score = directional_score(oi_change_pct, neutral=0.0, scale=p["oi_scale"])
        cvd_score = directional_score(cvd_change, neutral=0.0, scale=p["cvd_scale"])
    else:
        # 做空方向：OI下降好，CVD流出好
        oi_score = directional_score(-oi_change_pct, neutral=0.0, scale=p["oi_scale"])
        cvd_score = directional_score(-cvd_change, neutral=0.0, scale=p["cvd_scale"])

    # 量能：无论多空，量能放大都是好事
    vol_score = directional_score(vol_ratio, neutral=1.0, scale=p["vol_scale"])

    # 加权平均
    fund_momentum = (
        p["oi_weight"] * oi_score +
        p["vol_weight"] * vol_score +
        p["cvd_weight"] * cvd_score
    )

    # ========== 2. 价格动量 ==========
    # 做多时：价格上涨
    # 做空时：价格下跌

    if side_long:
        trend_score = directional_score(price_change_pct, neutral=0.0, scale=p["price_scale"])
        slope_score = directional_score(price_slope, neutral=0.0, scale=p["slope_scale"])
    else:
        trend_score = directional_score(-price_change_pct, neutral=0.0, scale=p["price_scale"])
        slope_score = directional_score(-price_slope, neutral=0.0, scale=p["slope_scale"])

    # 加权平均
    price_momentum = (
        p["trend_weight"] * trend_score +
        p["slope_weight"] * slope_score
    )

    # ========== 3. 资金领先性 ==========
    # leading = 资金动量 - 价格动量
    # leading > 0：资金强于价格（蓄势）
    # leading < 0：价格强于资金（追高）

    leading_raw = fund_momentum - price_momentum

    # 映射到 0-100
    # 使用 tanh 实现软映射
    F = 50 + 50 * math.tanh(leading_raw / p["leading_scale"])
    F = int(round(max(0.0, min(100.0, F))))

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
        F_score: F 维度分数 (0-100)

    Returns:
        中文解释
    """
    if F_score >= 75:
        return "资金强势领先/蓄势待发"
    elif F_score >= 60:
        return "资金略微领先/机会较好"
    elif F_score >= 40:
        return "资金价格同步/一般"
    elif F_score >= 25:
        return "价格略微领先/追高风险"
    else:
        return "价格大幅领先/风险较大"
