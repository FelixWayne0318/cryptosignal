# coding: utf-8
"""
资金费率与基差指标（F指标）+ FWI风险过滤器

世界级微观结构指标：
- Funding Rate: 永续合约资金费率
- Basis: 永续-现货价差
- FWI (Funding Window Index): 资金费窗口挤兑指数

逻辑：
1. 基差 (Basis):
   - Basis > 0 → 永续溢价 → 市场看多情绪
   - Basis < 0 → 永续折价 → 市场看空情绪

2. 资金费率 (Funding Rate):
   - Funding > 0 → 多头支付空头 → 市场过度看多 → 反向指标（负分）
   - Funding < 0 → 空头支付多头 → 市场过度看空 → 反向指标（正分）

3. FWI (资金费窗口指数):
   - 在资金费结算前30分钟内检测挤兑风险
   - 如果价格、OI、资金费方向一致 → 警告
"""
from typing import Dict, Tuple
import math
import time
from ats_core.scoring.scoring_utils import StandardizationChain

# 模块级StandardizationChain实例
_funding_chain = StandardizationChain(alpha=0.15, tau=3.0, z0=2.5, zmax=6.0, lam=1.5)


def directional_score(
    value: float,
    neutral: float = 0.0,
    scale: float = 1.0
) -> float:
    """
    方向性评分函数

    Args:
        value: 输入值
        neutral: 中性点
        scale: 缩放系数

    Returns:
        -100 到 +100 的分数
    """
    normalized = (value - neutral) / scale

    # tanh压缩到(-1, 1)
    score = math.tanh(normalized) * 100

    return score


def score_funding_rate(
    mark_price: float,
    spot_price: float,
    funding_rate: float,
    params: dict = None
) -> Tuple[int, dict]:
    """
    F（资金费与基差）评分

    Args:
        mark_price: 永续合约标记价格
        spot_price: 现货价格
        funding_rate: 资金费率（8小时）
        params: 参数配置（可选）

    Returns:
        (F分数 [-100, +100], 元数据)

    评分逻辑:
        1. 基差分数（50%权重）:
           - Basis (bps) = (永续 - 现货) / 现货 × 10000
           - Basis正 → 永续溢价 → 看多情绪 → 正分
           - scale = 50bps（正常波动范围）

        2. 资金费分数（50%权重）:
           - Funding正 → 多头支付空头 → 过度看多 → 负分（反向指标）
           - Funding负 → 空头支付多头 → 过度看空 → 正分（反向指标）
           - scale = 0.01%（10bps，正常波动范围）

        3. 综合分数:
           F = 0.5 × 基差分数 + 0.5 × 资金费分数

    风险警告:
        - |funding_rate| > 0.15%: 极端资金费警告
    """
    if params is None:
        params = {}

    # 默认参数
    basis_scale = params.get('basis_scale', 50.0)  # 基差缩放系数（bps）
    funding_scale = params.get('funding_scale', 10.0)  # 资金费缩放系数（bps）

    # 1. 计算基差（bps）
    if spot_price > 0:
        basis_bps = (mark_price - spot_price) / spot_price * 10000
    else:
        basis_bps = 0.0

    # 基差分数（正向指标：正基差 → 正分）
    basis_score = directional_score(
        basis_bps,
        neutral=0.0,
        scale=basis_scale
    )

    # 2. 计算资金费（bps）
    funding_bps = funding_rate * 10000

    # 资金费分数（反向指标：正资金费 → 负分）
    funding_score = directional_score(
        -funding_bps,  # 注意负号
        neutral=0.0,
        scale=funding_scale
    )

    # 3. 综合评分（50% 基差 + 50% 资金费）
    F_raw = 0.5 * basis_score + 0.5 * funding_score

    # v2.0合规：应用StandardizationChain
    F_pub, diagnostics = _funding_chain.standardize(F_raw)
    F = int(round(F_pub))

    # 4. 元数据
    meta = {
        "basis_bps": round(basis_bps, 2),
        "funding_rate": round(funding_rate, 6),
        "funding_bps": round(funding_bps, 2),
        "basis_score": round(basis_score, 1),
        "funding_score": round(funding_score, 1),
        "mark_price": round(mark_price, 2),
        "spot_price": round(spot_price, 2),
        "extreme_funding": abs(funding_rate) > 0.0015  # |funding| > 0.15%
    }

    return F, meta


def calculate_fwi(
    funding_rate: float,
    next_funding_time: int,
    price_change_30m: float,
    oi_change_30m: float,
    current_time: int = None
) -> Tuple[float, dict]:
    """
    FWI（资金费窗口挤兑指数）

    Args:
        funding_rate: 当前资金费率（8小时）
        next_funding_time: 下次结算时间（Unix时间戳，毫秒）
        price_change_30m: 30分钟价格变化率
        oi_change_30m: 30分钟OI变化率
        current_time: 当前时间（Unix时间戳，秒），默认为当前时间

    Returns:
        (FWI值, 元数据)

    公式:
        FWI = sgn(funding) × |funding|/0.01% × g(m) × same_direction

        其中:
        - g(m) = exp(-(m/10)²)  # 窗口函数，m为到结算的分钟数
        - same_direction = 1 if sgn(funding) == sgn(ΔP) == sgn(ΔOI) else 0

    风险警告:
        - |FWI| > 2.0: 资金费窗口拥挤警告
    """
    if current_time is None:
        current_time = int(time.time())

    # 1. 计算到结算的时间（分钟）
    # next_funding_time是毫秒，需要转换为秒
    next_funding_sec = next_funding_time / 1000 if next_funding_time > 1e10 else next_funding_time
    minutes_to_funding = (next_funding_sec - current_time) / 60

    # 2. 窗口函数 g(m) = exp(-(m/10)²)
    # 只在[-30, +30]分钟窗口内有效
    if abs(minutes_to_funding) > 30:
        g = 0.0
    else:
        g = math.exp(-((minutes_to_funding / 10) ** 2))

    # 3. 方向一致性检测
    sgn_funding = 1 if funding_rate > 0 else -1 if funding_rate < 0 else 0
    sgn_price = 1 if price_change_30m > 0 else -1 if price_change_30m < 0 else 0
    sgn_oi = 1 if oi_change_30m > 0 else -1 if oi_change_30m < 0 else 0

    # 三者方向完全一致才触发警告
    if sgn_funding == sgn_price == sgn_oi and sgn_funding != 0:
        same_direction = 1
    else:
        same_direction = 0

    # 4. 计算FWI
    # |funding|/0.01% = funding率归一化
    fwi = sgn_funding * abs(funding_rate) / 0.0001 * g * same_direction

    # 5. 风险警告
    fwi_warning = abs(fwi) > 2.0

    # 6. 元数据
    meta = {
        "fwi": round(fwi, 3),
        "fwi_warning": fwi_warning,
        "minutes_to_funding": round(minutes_to_funding, 1),
        "window_factor": round(g, 3),
        "same_direction": bool(same_direction),
        "sgn_funding": sgn_funding,
        "sgn_price": sgn_price,
        "sgn_oi": sgn_oi
    }

    return fwi, meta


def get_basis_arbitrage_signal(
    basis_bps: float,
    funding_rate: float
) -> dict:
    """
    检测基差套利机会

    Args:
        basis_bps: 基差（基点）
        funding_rate: 资金费率

    Returns:
        套利信号字典

    逻辑:
        - 正向套利：基差 > 100bps 且 funding > 0.10%
        - 反向套利：基差 < -100bps 且 funding < -0.10%
    """
    positive_arb = basis_bps > 100 and funding_rate > 0.001
    negative_arb = basis_bps < -100 and funding_rate < -0.001

    if positive_arb:
        return {
            "has_arbitrage": True,
            "type": "正向套利",
            "description": "永续溢价过高，做空永续+做多现货",
            "basis_bps": basis_bps,
            "funding_rate": funding_rate
        }
    elif negative_arb:
        return {
            "has_arbitrage": True,
            "type": "反向套利",
            "description": "永续折价过高，做多永续+做空现货",
            "basis_bps": basis_bps,
            "funding_rate": funding_rate
        }
    else:
        return {
            "has_arbitrage": False,
            "type": None,
            "description": None
        }


def validate_funding_data(
    mark_price: float,
    spot_price: float,
    funding_rate: float
) -> bool:
    """
    验证资金费数据有效性

    Args:
        mark_price: 永续标记价格
        spot_price: 现货价格
        funding_rate: 资金费率

    Returns:
        True = 有效, False = 无效
    """
    # 1. 价格应该为正数
    if mark_price <= 0 or spot_price <= 0:
        return False

    # 2. 基差应该在合理范围内（±5%）
    basis_pct = abs(mark_price - spot_price) / spot_price
    if basis_pct > 0.05:
        return False

    # 3. 资金费率应该在合理范围内（±1%）
    if abs(funding_rate) > 0.01:
        return False

    return True
