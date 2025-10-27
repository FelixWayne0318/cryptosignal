# coding: utf-8
"""
O+ 因子: OI四象限体制识别

理论基础:
OI（持仓量）与价格变化的组合可以识别市场体制：

1. up_up (价格↑ + OI↑): 多头加仓，强势看涨
2. up_dn (价格↑ + OI↓): 空头止损，弱势反弹
3. dn_up (价格↓ + OI↑): 空头加仓，强势看跌
4. dn_dn (价格↓ + OI↓): 多头止损，弱势下跌

Range: -100 到 +100
"""

from __future__ import annotations
from typing import Tuple, List, Dict, Any
import numpy as np


def _to_f(x) -> float:
    """安全转换为float"""
    try:
        return float(x)
    except Exception:
        return 0.0


def calculate_oi_regime(
    oi_hist: List[float],
    price_hist: List[float],
    params: Dict[str, Any] = None
) -> Tuple[float, str, Dict[str, Any]]:
    """
    计算OI四象限体制评分

    Args:
        oi_hist: OI历史序列（最新值在最后）
        price_hist: 价格历史序列
        params: 参数字典，包含:
            - regime_window_hours: 体制判定窗口（默认12小时）
            - delta_threshold_pct: OI变化阈值（默认5%）
            - oi_level_high_threshold: OI水平高阈值（默认1.3）
            - oi_level_window_hours: OI水平窗口（默认168小时）
            - regime_weights: 四象限权重
            - strength_multiplier: 强度放大系数

    Returns:
        (score, regime, metadata)
        - score: -100 到 +100
        - regime: 体制名称 (up_up, up_dn, dn_up, dn_dn)
        - metadata: 详细信息
    """
    if params is None:
        params = {}

    # 默认参数
    window_hours = params.get('regime_window_hours', 12)
    delta_threshold = params.get('delta_threshold_pct', 0.05)
    oi_level_high = params.get('oi_level_high_threshold', 1.3)
    oi_level_window = params.get('oi_level_window_hours', 168)
    regime_weights = params.get('regime_weights', {
        'up_up': 1.0,
        'up_dn': 0.3,
        'dn_up': -1.0,
        'dn_dn': -0.3
    })
    strength_mult = params.get('strength_multiplier', 1.5)

    # 数据验证
    if len(oi_hist) < window_hours + 1 or len(price_hist) < window_hours + 1:
        return 0.0, 'unknown', {
            'error': 'Insufficient data',
            'oi_len': len(oi_hist),
            'price_len': len(price_hist),
            'required': window_hours + 1
        }

    # === 1. 计算价格变化率（window_hours内）===
    price_start = _to_f(price_hist[-(window_hours + 1)])
    price_end = _to_f(price_hist[-1])

    if price_start == 0:
        delta_price_pct = 0.0
    else:
        delta_price_pct = (price_end - price_start) / price_start

    # === 2. 计算OI变化率（window_hours内）===
    oi_start = _to_f(oi_hist[-(window_hours + 1)])
    oi_end = _to_f(oi_hist[-1])

    if oi_start == 0:
        delta_oi_pct = 0.0
    else:
        delta_oi_pct = (oi_end - oi_start) / oi_start

    # === 3. 四象限判定 ===
    if delta_price_pct > 0 and delta_oi_pct > 0:
        # up_up: 多头加仓（强势）
        regime = 'up_up'
        base_score = 100
        # 强度：OI增长越大，评分越高
        strength = min(strength_mult, abs(delta_oi_pct) / delta_threshold)

    elif delta_price_pct > 0 and delta_oi_pct < 0:
        # up_dn: 空头止损（弱势反弹）
        regime = 'up_dn'
        base_score = 30  # 弱势信号
        strength = 1.0

    elif delta_price_pct < 0 and delta_oi_pct > 0:
        # dn_up: 空头加仓（强势）
        regime = 'dn_up'
        base_score = -100
        strength = min(strength_mult, abs(delta_oi_pct) / delta_threshold)

    else:
        # dn_dn: 多头止损（弱势下跌）
        regime = 'dn_dn'
        base_score = -30  # 弱势信号
        strength = 1.0

    # === 4. 应用体制权重 ===
    regime_weight = regime_weights.get(regime, 0.0)

    # 计算初步评分
    score = base_score * strength * abs(regime_weight)

    # 保持符号
    if regime_weight < 0:
        score = -abs(score)

    # === 5. OI绝对水平调整 ===
    # 如果OI过高（杠杆拥挤），降低评分可靠性
    if len(oi_hist) >= oi_level_window:
        oi_mean = np.mean([_to_f(v) for v in oi_hist[-oi_level_window:]])
        if oi_mean > 0:
            oi_level = oi_end / oi_mean
        else:
            oi_level = 1.0
    else:
        oi_level = 1.0

    # OI水平过高时降权
    if oi_level > oi_level_high:
        oi_penalty = 0.85  # 降权15%
        score *= oi_penalty
    else:
        oi_penalty = 1.0

    # === 6. 限制到±100 ===
    score = max(-100, min(100, score))

    # === 7. 元数据 ===
    metadata = {
        'regime': regime,
        'delta_price_pct': delta_price_pct,
        'delta_oi_pct': delta_oi_pct,
        'strength': strength,
        'regime_weight': regime_weight,
        'oi_level': oi_level,
        'oi_penalty': oi_penalty,
        'base_score': base_score,
        'final_score': score
    }

    return score, regime, metadata


# ========== 测试代码 ==========

if __name__ == "__main__":
    print("=" * 60)
    print("O+ 因子测试 - OI四象限体制识别")
    print("=" * 60)

    # 模拟数据
    # 场景1: up_up (多头加仓)
    print("\n[场景1] up_up - 价格上涨 + OI增加")
    price_1 = list(range(100, 112))  # 价格从100涨到111 (+11%)
    oi_1 = [1000 + i * 50 for i in range(12)]  # OI从1000涨到1550 (+55%)

    score_1, regime_1, meta_1 = calculate_oi_regime(oi_1, price_1)
    print(f"  体制: {regime_1}")
    print(f"  评分: {score_1:.1f}")
    print(f"  价格变化: {meta_1['delta_price_pct']:.2%}")
    print(f"  OI变化: {meta_1['delta_oi_pct']:.2%}")
    print(f"  强度: {meta_1['strength']:.2f}")

    # 场景2: up_dn (空头止损)
    print("\n[场景2] up_dn - 价格上涨 + OI减少")
    price_2 = list(range(100, 108))  # 价格从100涨到107 (+7%)
    oi_2 = [1000 - i * 20 for i in range(8)]  # OI从1000降到860 (-14%)

    score_2, regime_2, meta_2 = calculate_oi_regime(oi_2[::-1], price_2)
    print(f"  体制: {regime_2}")
    print(f"  评分: {score_2:.1f}")
    print(f"  价格变化: {meta_2['delta_price_pct']:.2%}")
    print(f"  OI变化: {meta_2['delta_oi_pct']:.2%}")

    # 场景3: dn_up (空头加仓)
    print("\n[场景3] dn_up - 价格下跌 + OI增加")
    price_3 = [100 - i * 0.8 for i in range(12)]  # 价格从100跌到91.2 (-8.8%)
    oi_3 = [1000 + i * 40 for i in range(12)]  # OI从1000涨到1440 (+44%)

    score_3, regime_3, meta_3 = calculate_oi_regime(oi_3, price_3)
    print(f"  体制: {regime_3}")
    print(f"  评分: {score_3:.1f}")
    print(f"  价格变化: {meta_3['delta_price_pct']:.2%}")
    print(f"  OI变化: {meta_3['delta_oi_pct']:.2%}")
    print(f"  强度: {meta_3['strength']:.2f}")

    # 场景4: dn_dn (多头止损)
    print("\n[场景4] dn_dn - 价格下跌 + OI减少")
    price_4 = [100 - i * 0.5 for i in range(12)]  # 价格从100跌到94.5 (-5.5%)
    oi_4 = [1000 - i * 15 for i in range(12)]  # OI从1000降到835 (-16.5%)

    score_4, regime_4, meta_4 = calculate_oi_regime(oi_4, price_4)
    print(f"  体制: {regime_4}")
    print(f"  评分: {score_4:.1f}")
    print(f"  价格变化: {meta_4['delta_price_pct']:.2%}")
    print(f"  OI变化: {meta_4['delta_oi_pct']:.2%}")

    print("\n" + "=" * 60)
    print("✅ OI四象限测试完成")
    print("=" * 60)
