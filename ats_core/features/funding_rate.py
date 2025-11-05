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

P0.1改进（自适应阈值）：
- 基差和资金费阈值不再固定
- 根据历史分布的50/90分位数自适应调整
- 避免固定阈值在不同市场环境下失效
"""
from typing import Dict, Tuple, List
import math
import time
import numpy as np
from ats_core.scoring.scoring_utils import StandardizationChain

# 模块级StandardizationChain实例
_funding_chain = StandardizationChain(alpha=0.15, tau=3.0, z0=2.5, zmax=6.0, lam=1.5)


def get_adaptive_basis_thresholds(
    basis_history: List[float],
    neutral_percentile: int = 50,
    extreme_percentile: int = 90,
    min_neutral_bps: float = 20.0,
    max_neutral_bps: float = 200.0,
    min_extreme_bps: float = 50.0,
    max_extreme_bps: float = 300.0
) -> Tuple[float, float]:
    """
    计算自适应基差阈值（P0.1修复）

    Args:
        basis_history: 历史基差数据（bps）
        neutral_percentile: 中性阈值百分位数（默认50）
        extreme_percentile: 极端阈值百分位数（默认90）
        min_neutral_bps: 中性阈值下限（默认20bps）
        max_neutral_bps: 中性阈值上限（默认200bps）
        min_extreme_bps: 极端阈值下限（默认50bps）
        max_extreme_bps: 极端阈值上限（默认300bps）

    Returns:
        (neutral_threshold_bps, extreme_threshold_bps)
    """
    if len(basis_history) < 10:
        # 数据不足，返回固定值
        return 50.0, 100.0

    # 使用绝对值的百分位数
    abs_basis = np.abs(basis_history)

    neutral_threshold = float(np.percentile(abs_basis, neutral_percentile))
    extreme_threshold = float(np.percentile(abs_basis, extreme_percentile))

    # 边界保护
    neutral_threshold = np.clip(neutral_threshold, min_neutral_bps, max_neutral_bps)
    extreme_threshold = np.clip(extreme_threshold, min_extreme_bps, max_extreme_bps)

    return neutral_threshold, extreme_threshold


def get_adaptive_funding_thresholds(
    funding_history: List[float],
    neutral_percentile: int = 50,
    extreme_percentile: int = 90,
    min_neutral_rate: float = 0.0001,
    max_neutral_rate: float = 0.002,
    min_extreme_rate: float = 0.0005,
    max_extreme_rate: float = 0.003
) -> Tuple[float, float]:
    """
    计算自适应资金费率阈值（P0.1修复）

    Args:
        funding_history: 历史资金费率数据
        neutral_percentile: 中性阈值百分位数（默认50）
        extreme_percentile: 极端阈值百分位数（默认90）
        min_neutral_rate: 中性阈值下限
        max_neutral_rate: 中性阈值上限
        min_extreme_rate: 极端阈值下限
        max_extreme_rate: 极端阈值上限

    Returns:
        (neutral_threshold_rate, extreme_threshold_rate)
    """
    if len(funding_history) < 10:
        # 数据不足，返回固定值
        return 0.001, 0.002

    # 使用绝对值的百分位数
    abs_funding = np.abs(funding_history)

    neutral_threshold = float(np.percentile(abs_funding, neutral_percentile))
    extreme_threshold = float(np.percentile(abs_funding, extreme_percentile))

    # 边界保护
    neutral_threshold = np.clip(neutral_threshold, min_neutral_rate, max_neutral_rate)
    extreme_threshold = np.clip(extreme_threshold, min_extreme_rate, max_extreme_rate)

    return neutral_threshold, extreme_threshold


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
    params: dict = None,
    basis_history: List[float] = None,
    funding_history: List[float] = None
) -> Tuple[int, dict]:
    """
    F（资金费与基差）评分 - P0.1自适应阈值

    Args:
        mark_price: 永续合约标记价格
        spot_price: 现货价格
        funding_rate: 资金费率（8小时）
        params: 参数配置（可选）
        basis_history: 历史基差数据（bps），用于自适应阈值（P0.1新增）
        funding_history: 历史资金费率数据，用于自适应阈值（P0.1新增）

    Returns:
        (F分数 [-100, +100], 元数据)

    评分逻辑:
        1. 基差分数（60%权重）:
           - Basis (bps) = (永续 - 现货) / 现货 × 10000
           - Basis正 → 永续溢价 → 看多情绪 → 正分
           - P0.1: scale = 50th percentile of |basis_history|（自适应）

        2. 资金费分数（40%权重）:
           - Funding正 → 多头支付空头 → 过度看多 → 负分（反向指标）
           - Funding负 → 空头支付多头 → 过度看空 → 正分（反向指标）
           - P0.1: scale = 50th percentile of |funding_history|（自适应）

        3. 综合分数:
           F = 0.6 × 基差分数 + 0.4 × 资金费分数

    风险警告:
        - |funding_rate| > 极端阈值: 极端资金费警告
    """
    if params is None:
        params = {}

    # P0.1参数：自适应阈值配置
    adaptive_config = params.get('basis_funding_adaptive', {})
    adaptive_enabled = adaptive_config.get('enabled', True)
    adaptive_mode = params.get('adaptive_threshold_mode', 'hybrid')
    min_data_points = adaptive_config.get('lookback', 50)

    # 默认固定阈值（legacy模式）
    basis_scale = params.get('basis_scale', 50.0)  # 基差缩放系数（bps）
    funding_scale = params.get('funding_scale', 10.0)  # 资金费缩放系数（bps）
    threshold_source = 'legacy'

    # P0.1: 自适应阈值计算
    if adaptive_enabled and adaptive_mode != 'legacy':
        # Basis自适应阈值
        if basis_history and len(basis_history) >= min_data_points:
            neutral_bps, extreme_bps = get_adaptive_basis_thresholds(
                basis_history,
                neutral_percentile=adaptive_config.get('neutral_percentile', 50),
                extreme_percentile=adaptive_config.get('extreme_percentile', 90),
                min_neutral_bps=adaptive_config.get('neutral_min_bps', 20.0),
                max_neutral_bps=adaptive_config.get('neutral_max_bps', 200.0),
                min_extreme_bps=adaptive_config.get('extreme_min_bps', 50.0),
                max_extreme_bps=adaptive_config.get('extreme_max_bps', 300.0)
            )
            basis_scale = neutral_bps
            threshold_source = 'adaptive'

        # Funding自适应阈值
        if funding_history and len(funding_history) >= min_data_points:
            neutral_rate, extreme_rate = get_adaptive_funding_thresholds(
                funding_history,
                neutral_percentile=adaptive_config.get('neutral_percentile', 50),
                extreme_percentile=adaptive_config.get('extreme_percentile', 90),
                min_neutral_rate=adaptive_config.get('funding_neutral_rate', 0.001),
                max_neutral_rate=0.002,
                min_extreme_rate=adaptive_config.get('funding_extreme_rate', 0.002),
                max_extreme_rate=0.003
            )
            funding_scale = neutral_rate * 10000  # 转换为bps
            threshold_source = 'adaptive'

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

    # 3. 综合评分（60% 基差 + 40% 资金费）
    basis_weight = params.get('basis_weight', 0.6)
    funding_weight = params.get('funding_weight', 0.4)
    F_raw = basis_weight * basis_score + funding_weight * funding_score

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
        "extreme_funding": abs(funding_rate) > 0.0015,  # |funding| > 0.15%
        # P0.1: 自适应阈值信息
        "basis_scale": round(basis_scale, 2),
        "funding_scale": round(funding_scale, 2),
        "threshold_source": threshold_source,  # 'adaptive' or 'legacy'
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
