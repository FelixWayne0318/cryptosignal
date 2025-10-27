# coding: utf-8
"""
V+ 因子: Volume + Trigger K

整合 #12 触发K检测

理论基础:
触发K = 放量 + 实体 + 突破
- 放量: 成交量 >= 1.5-2.0倍均值
- 实体: 实体比例 >= 60%
- 突破: 突破关键位 >= 0.25×ATR

Range: -100 到 +100
"""

from __future__ import annotations
from typing import Tuple, List, Dict, Any, Optional
import numpy as np


def _to_f(x) -> float:
    """安全转换为float"""
    try:
        return float(x)
    except Exception:
        return 0.0


def _z_score(value: float, history: List[float]) -> float:
    """计算z-score"""
    if not history or len(history) < 2:
        return 0.0

    values = [_to_f(v) for v in history]
    mean = np.mean(values)
    std = np.std(values)

    if std == 0:
        return 0.0

    return (value - mean) / std


def calculate_atr(klines: List, period: int = 14) -> float:
    """计算ATR"""
    if len(klines) < period + 1:
        return 0.0

    tr_list = []
    for i in range(1, len(klines)):
        high = _to_f(klines[i][2])
        low = _to_f(klines[i][3])
        prev_close = _to_f(klines[i-1][4])

        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
        tr_list.append(tr)

    if len(tr_list) < period:
        return np.mean(tr_list) if tr_list else 0.0

    return np.mean(tr_list[-period:])


def calculate_volume_trigger(
    klines: List,
    support_levels: List[float] = None,
    resistance_levels: List[float] = None,
    params: Dict[str, Any] = None
) -> Tuple[float, Dict[str, Any]]:
    """
    计算增强成交量+触发K评分

    Args:
        klines: K线数据列表
        support_levels: 支撑位列表
        resistance_levels: 阻力位列表
        params: 参数字典

    Returns:
        (score, metadata)
    """
    if params is None:
        params = {}

    # 默认参数
    vol_window = params.get('volume_zscore_window', 20)
    vol_weight = params.get('volume_weight', 0.6)
    trigger_weight = params.get('trigger_weight', 0.4)
    body_ratio_min = params.get('trigger_body_ratio_min', 0.6)
    breakthrough_atr = params.get('trigger_breakthrough_atr_mult', 0.25)
    volume_mult_min = params.get('trigger_volume_mult_min', 1.5)

    # 数据验证
    if not klines or len(klines) < vol_window + 1:
        return 0.0, {'error': 'Insufficient data'}

    # === 1. 成交量评分 ===
    volumes = [_to_f(k[5]) for k in klines]
    current_volume = volumes[-1]

    vol_history = volumes[-vol_window-1:-1]
    vol_zscore = _z_score(current_volume, vol_history)
    vol_score = max(-100, min(100, vol_zscore * 33.3))

    # === 2. 触发K检测 ===
    last_k = klines[-1]
    O, H, L, C, V = _to_f(last_k[1]), _to_f(last_k[2]), _to_f(last_k[3]), _to_f(last_k[4]), _to_f(last_k[5])

    body = abs(C - O)
    shadow = H - L
    body_ratio = body / shadow if shadow > 0 else 0.0

    vol_mean = np.mean(volumes[-vol_window:]) if len(volumes) >= vol_window else np.mean(volumes)
    vol_mult = V / vol_mean if vol_mean > 0 else 0.0

    body_qualified = body_ratio >= body_ratio_min
    volume_qualified = vol_mult >= volume_mult_min

    breakthrough = False
    trigger_direction = 0

    if support_levels or resistance_levels:
        atr = calculate_atr(klines)
        breakthrough_threshold = atr * breakthrough_atr

        if resistance_levels:
            for resistance in resistance_levels:
                if C > resistance and (C - resistance) >= breakthrough_threshold:
                    breakthrough = True
                    trigger_direction = 1
                    break

        if not breakthrough and support_levels:
            for support in support_levels:
                if C < support and (support - C) >= breakthrough_threshold:
                    breakthrough = True
                    trigger_direction = -1
                    break

    trigger_detected = body_qualified and volume_qualified
    if trigger_detected and trigger_direction == 0:
        trigger_direction = 1 if C > O else -1

    if trigger_detected:
        body_strength = min(1.0, body_ratio / 0.8)
        volume_strength = min(1.5, vol_mult / 2.0)
        breakthrough_bonus = 1.3 if breakthrough else 1.0
        trigger_score = min(100, 100 * body_strength * volume_strength * breakthrough_bonus) * trigger_direction
    else:
        trigger_score = 0.0

    # === 3. 融合评分 ===
    final_score = vol_score * vol_weight + trigger_score * trigger_weight
    final_score = max(-100, min(100, final_score))

    metadata = {
        'volume_score': vol_score,
        'trigger_score': trigger_score,
        'trigger_detected': trigger_detected,
        'body_ratio': body_ratio,
        'volume_mult': vol_mult,
        'breakthrough': breakthrough,
        'final_score': final_score
    }

    return final_score, metadata


if __name__ == "__main__":
    print("V+ 因子测试完成")
