# coding: utf-8
"""
F（资金领先性）维度（v2.0 ±100对称设计）

核心理念：
因果链：资金是因，价格是果
- 最佳入场点：资金强势流入，但价格还未充分反应（蓄势待发）
- 追高风险：价格已经大涨，但资金流入减弱或流出（派发阶段）

F 的定义（v2.0）：
F = f(资金动量 - 价格动量)  # 两者都是±100范围
- F > +60：资金强势领先价格（最佳入场点）✅✅✅
- F = +20 ~ +60：资金略微领先（可以考虑）✅
- F = -20 ~ +20：资金价格同步（中性）
- F = -60 ~ -20：价格略微领先（追高风险）⚠️
- F < -60：价格大幅领先资金（风险很大）❌

改进v2.0：
- ✅ F范围：-100 到 +100（0为中性）
- ✅ 资金/价格动量都使用对称评分
- ✅ 连续调节函数（平滑调整概率）
- ✅ 移除side_long参数

输入：
- oi_change_pct: OI 24小时变化率（%）
- vol_ratio: v5/v20 量能比值
- cvd_change: CVD 6小时变化（归一化）
- price_change_pct: 价格 24小时变化率（%）
- price_slope: 价格斜率（EMA30的斜率）
"""
from typing import Dict, Any, Tuple
from ats_core.features.scoring_utils import directional_score_symmetric
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
    F（资金领先性）评分（v2.0 对称版本）

    Args:
        oi_change_pct: OI 24小时变化率（%），如 +3.5 表示上升 3.5%
        vol_ratio: v5/v20 量能比值，如 1.4 表示近期量能是均值的 1.4 倍
        cvd_change: CVD 6小时变化（归一化到价格），通常在 -0.05 ~ +0.05 范围
        price_change_pct: 价格 24小时变化率（%）
        price_slope: 价格斜率（EMA30 的斜率/ATR）
        params: 参数配置

    Returns:
        (F分数 -100~+100, 元数据)
        - 正值：资金领先价格 → 蓄势待发（利好）
        - 负值：价格领先资金 → 追高风险（利空）
        - 0：资金价格同步 → 中性
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

    # ========== 1. 资金动量（对称评分） ==========
    # 使用对称评分：正值=流入/增加，负值=流出/减少

    # OI 变化评分
    oi_score = directional_score_symmetric(
        oi_change_pct,
        neutral=0.0,
        scale=p["oi_scale"]
    )  # -100 到 +100

    # CVD 变化评分
    cvd_score = directional_score_symmetric(
        cvd_change,
        neutral=0.0,
        scale=p["cvd_scale"]
    )  # -100 到 +100

    # 量能比值评分
    vol_score = directional_score_symmetric(
        vol_ratio,
        neutral=1.0,
        scale=p["vol_scale"]
    )  # -100 到 +100

    # 加权平均（保留符号）
    fund_momentum = (
        p["oi_weight"] * oi_score +
        p["vol_weight"] * vol_score +
        p["cvd_weight"] * cvd_score
    )  # -100 到 +100

    # ========== 2. 价格动量（对称评分） ==========
    # 使用对称评分：正值=上涨，负值=下跌

    # 价格变化评分
    trend_score = directional_score_symmetric(
        price_change_pct,
        neutral=0.0,
        scale=p["price_scale"]
    )  # -100 到 +100

    # 斜率评分
    slope_score = directional_score_symmetric(
        price_slope,
        neutral=0.0,
        scale=p["slope_scale"]
    )  # -100 到 +100

    # 加权平均（保留符号）
    price_momentum = (
        p["trend_weight"] * trend_score +
        p["slope_weight"] * slope_score
    )  # -100 到 +100

    # ========== 3. 资金领先性（对称） ==========
    # leading_raw = 资金动量 - 价格动量
    # 正值：资金强于价格（蓄势待发）
    # 负值：价格强于资金（追高风险）

    leading_raw = fund_momentum - price_momentum  # -200 到 +200

    # 映射到 -100 ~ +100
    # 使用 tanh 实现软映射
    F = 100 * math.tanh(leading_raw / p["leading_scale"])
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
    解释 F 分数的含义（v2.0 对称版本）

    Args:
        F_score: F 维度分数 (-100 到 +100)

    Returns:
        中文解释
    """
    if F_score >= 60:
        return "资金强势领先/蓄势待发"
    elif F_score >= 20:
        return "资金略微领先/机会较好"
    elif F_score >= -20:
        return "资金价格同步/中性"
    elif F_score >= -60:
        return "价格略微领先/追高风险"
    else:
        return "价格大幅领先/风险很大"


def calculate_F_adjustment(F: float) -> float:
    """
    F调节系数的连续函数（v2.0新增）

    使用平滑的tanh函数，避免硬阈值突变

    Args:
        F: F分数 (-100 到 +100)

    Returns:
        adjustment: 调节系数 (0.75 到 1.25)

    Examples:
        >>> calculate_F_adjustment(+60)
        1.19  # +19% 增强

        >>> calculate_F_adjustment(0)
        1.0   # 不调整

        >>> calculate_F_adjustment(-60)
        0.81  # -19% 削弱

    数学公式：
        adjustment = 1.0 + 0.25 × tanh(F / 40)

    特性：
        - 完全平滑，无突变点
        - F=±40 时调整约±19%
        - F=±60 时调整约±22%
        - F=±100 时调整约±25%（极限）
    """
    # 基准调节范围
    base = 1.0
    max_adjustment = 0.25  # ±25%

    # 敏感度参数（F=±40时调整约±19%）
    sensitivity = 40.0

    # tanh平滑映射
    normalized = math.tanh(F / sensitivity)
    adjustment = base + max_adjustment * normalized

    return adjustment
