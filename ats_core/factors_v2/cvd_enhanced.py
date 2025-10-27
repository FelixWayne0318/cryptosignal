# coding: utf-8
"""
C+ 因子: Enhanced CVD（增强累积成交量差）

整合 #1 动态权重CVD

理论基础:
1. 传统CVD: 累积买入量 - 累积卖出量
   - 上涨+放量 → 买入 (Taker buy)
   - 下跌+放量 → 卖出 (Taker sell)

2. 动态权重增强:
   - 现货CVD：反映散户情绪（零售流）
   - 永续CVD：反映鲸鱼情绪（机构流）
   - 动态权重：根据成交量领导权调整
     - 现货领先（散户主导）→ 提高现货权重
     - 永续领先（机构主导）→ 提高永续权重

3. EMA平滑：减少噪音，保留趋势

4. Z-score归一化：标准化到±100

Range: -100 到 +100（正值看涨，负值看跌）
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


def _calculate_cvd(klines: List) -> List[float]:
    """
    计算CVD序列（简化版：基于价格变化判断买卖）

    Args:
        klines: K线数据 [[timestamp, open, high, low, close, volume], ...]

    Returns:
        CVD序列
    """
    if not klines or len(klines) < 2:
        return []

    cvd_series = [0.0]  # 初始CVD为0

    for i in range(1, len(klines)):
        prev_close = _to_f(klines[i-1][4])
        curr_close = _to_f(klines[i][4])
        volume = _to_f(klines[i][5])

        # 简化判断：价格上涨 → 买入主导，价格下跌 → 卖出主导
        if curr_close > prev_close:
            # 上涨：买入量
            delta = volume
        elif curr_close < prev_close:
            # 下跌：卖出量（负）
            delta = -volume
        else:
            # 价格不变：中性
            delta = 0.0

        # 累积CVD
        cvd_series.append(cvd_series[-1] + delta)

    return cvd_series


def _ema(values: List[float], period: int) -> List[float]:
    """
    计算EMA（指数移动平均）

    Args:
        values: 数值序列
        period: EMA周期

    Returns:
        EMA序列
    """
    if not values or len(values) < period:
        return values

    ema_series = []
    alpha = 2.0 / (period + 1)

    # 初始EMA为前period个值的平均
    ema = np.mean(values[:period])
    ema_series.extend([ema] * period)

    # 计算后续EMA
    for i in range(period, len(values)):
        ema = alpha * values[i] + (1 - alpha) * ema
        ema_series.append(ema)

    return ema_series


def _z_score(value: float, history: List[float]) -> float:
    """计算z-score"""
    if not history or len(history) < 2:
        return 0.0

    mean = np.mean(history)
    std = np.std(history)

    if std == 0:
        return 0.0

    return (value - mean) / std


def calculate_cvd_enhanced(
    klines_perp: List,
    klines_spot: Optional[List] = None,
    params: Dict[str, Any] = None
) -> Tuple[float, Dict[str, Any]]:
    """
    计算增强CVD评分（含Basis校正）

    Args:
        klines_perp: 永续合约K线数据
        klines_spot: 现货K线数据（可选）
        params: 参数字典，包含:
            - ema_period: EMA周期（默认12）
            - zscore_window: z-score窗口（默认60）
            - dynamic_weight: 是否启用动态权重（默认True）
            - basis_correction: 是否启用basis校正（默认False，需主动启用）⭐新增
            - basis_threshold_bps: Basis阈值，超过此值触发校正（默认50bps）⭐新增
            - cross_exchange_enabled: 是否启用跨交易所增强（默认False）

    Returns:
        (score, metadata)
        - score: -100 到 +100（正值看涨，负值看跌）
        - metadata: 详细信息
    """
    if params is None:
        params = {}

    # 默认参数
    ema_period = params.get('ema_period', 12)
    zscore_window = params.get('zscore_window', 60)
    dynamic_weight = params.get('dynamic_weight', True)
    basis_correction = params.get('basis_correction', False)  # ⭐新增（默认关闭，需主动启用）
    basis_threshold_bps = params.get('basis_threshold_bps', 50.0)  # ⭐新增

    # === 1. 计算永续CVD ===
    if not klines_perp or len(klines_perp) < ema_period + zscore_window:
        return 0.0, {'error': 'Insufficient perpetual data'}

    cvd_perp = _calculate_cvd(klines_perp)

    if len(cvd_perp) < ema_period:
        return 0.0, {'error': 'Insufficient CVD data'}

    # EMA平滑
    cvd_perp_ema = _ema(cvd_perp, ema_period)

    # === 2. 计算现货CVD（如果可用）===
    if klines_spot and len(klines_spot) >= len(klines_perp):
        cvd_spot = _calculate_cvd(klines_spot)
        cvd_spot_ema = _ema(cvd_spot, ema_period)

        has_spot = True
    else:
        cvd_spot_ema = cvd_perp_ema  # 如果无现货数据，使用永续CVD
        has_spot = False

    # === 3. 动态权重计算 ===
    if dynamic_weight and has_spot:
        # 比较永续和现货的平均成交量（最近12根K线）
        perp_vol_avg = np.mean([_to_f(k[5]) for k in klines_perp[-ema_period:]])
        spot_vol_avg = np.mean([_to_f(k[5]) for k in klines_spot[-ema_period:]])

        total_vol = perp_vol_avg + spot_vol_avg

        if total_vol > 0:
            # 成交量占比决定权重
            w_perp = perp_vol_avg / total_vol
            w_spot = spot_vol_avg / total_vol
        else:
            w_perp = 0.6  # 默认永续60%
            w_spot = 0.4  # 默认现货40%
    else:
        # 静态权重
        w_perp = 1.0
        w_spot = 0.0

    # === 3.5. Basis校正（防止套利影响）⭐新增 ===
    basis_bps = 0.0
    basis_adjusted = False

    if basis_correction and has_spot and len(klines_perp) > 0 and len(klines_spot) > 0:
        # 计算期现价差（Basis）
        perp_price = _to_f(klines_perp[-1][4])  # 永续收盘价
        spot_price = _to_f(klines_spot[-1][4])  # 现货收盘价

        if spot_price > 0:
            # Basis（单位：bps，1bps = 0.01%）
            basis_pct = (perp_price - spot_price) / spot_price
            basis_bps = basis_pct * 10000  # 转换为bps

            # 如果Basis超过阈值，认为存在套利影响
            if abs(basis_bps) > basis_threshold_bps:
                # 计算校正因子
                # Basis越大，套利盘越活跃，CVD越失真
                # 校正策略：降低永续CVD权重
                excess_basis = abs(basis_bps) - basis_threshold_bps

                # 校正因子：每超过50bps，降低10%权重，最多降低50%
                correction_factor = min(0.5, excess_basis / 50.0 * 0.1)

                # 应用校正
                w_perp_original = w_perp
                w_perp = w_perp * (1.0 - correction_factor)
                w_spot = 1.0 - w_perp  # 重新归一化

                basis_adjusted = True
            else:
                basis_adjusted = False
        else:
            basis_adjusted = False
    else:
        basis_adjusted = False

    # === 4. 加权CVD ===
    if len(cvd_perp_ema) != len(cvd_spot_ema):
        # 长度不一致，只使用永续
        cvd_weighted = cvd_perp_ema
    else:
        cvd_weighted = [
            w_perp * cvd_perp_ema[i] + w_spot * cvd_spot_ema[i]
            for i in range(len(cvd_perp_ema))
        ]

    # === 5. Z-score归一化 ===
    current_cvd = cvd_weighted[-1]
    cvd_history = cvd_weighted[-(zscore_window+1):-1]

    cvd_zscore = _z_score(current_cvd, cvd_history)

    # 映射到±100（z-score一般在±3之间）
    cvd_score = max(-100, min(100, cvd_zscore * 33.3))

    # === 6. CVD方向和强度 ===
    # 比较最近CVD与前一时刻的变化
    if len(cvd_weighted) >= 2:
        cvd_delta = cvd_weighted[-1] - cvd_weighted[-2]
        if cvd_delta > 0:
            cvd_direction = 'bullish'
        elif cvd_delta < 0:
            cvd_direction = 'bearish'
        else:
            cvd_direction = 'neutral'
    else:
        cvd_direction = 'neutral'
        cvd_delta = 0.0

    # === 7. 元数据 ===
    metadata = {
        'cvd_perp_current': cvd_perp_ema[-1] if cvd_perp_ema else 0.0,
        'cvd_spot_current': cvd_spot_ema[-1] if has_spot else 0.0,
        'cvd_weighted_current': current_cvd,
        'cvd_delta': cvd_delta,
        'cvd_direction': cvd_direction,
        'cvd_zscore': cvd_zscore,
        'cvd_score': cvd_score,
        'w_perp': w_perp,
        'w_spot': w_spot,
        'has_spot_data': has_spot,
        # ⭐ Basis校正信息
        'basis_bps': basis_bps,
        'basis_adjusted': basis_adjusted,
        'basis_correction_enabled': basis_correction
    }

    return cvd_score, metadata


# ========== 测试代码 ==========

if __name__ == "__main__":
    print("=" * 60)
    print("C+ 因子测试 - Enhanced CVD（增强累积成交量差）")
    print("=" * 60)

    # 模拟K线数据
    np.random.seed(42)

    # 场景1: 持续买入（CVD持续上升）
    print("\n[场景1] 持续买入（CVD上升）")
    klines_1 = []
    base_price = 50000
    for i in range(80):
        # 上涨趋势：收盘价逐渐上升
        o = base_price + i * 50
        c = base_price + i * 50 + np.random.randint(10, 50)  # 上涨
        h = max(o, c) + np.random.randint(5, 20)
        l = min(o, c) - np.random.randint(0, 10)
        v = 1000 + np.random.randint(0, 500)
        klines_1.append([i * 3600000, o, h, l, c, v])

    score_1, meta_1 = calculate_cvd_enhanced(klines_1)
    print(f"  CVD评分: {score_1:.1f}")
    print(f"  CVD Z-score: {meta_1['cvd_zscore']:.2f}")
    print(f"  CVD Delta: {meta_1['cvd_delta']:.0f}")
    print(f"  方向: {meta_1['cvd_direction']}")

    # 场景2: 持续卖出（CVD持续下降）
    print("\n[场景2] 持续卖出（CVD下降）")
    klines_2 = []
    base_price = 50000
    for i in range(80):
        # 下跌趋势：收盘价逐渐下降
        o = base_price - i * 50
        c = base_price - i * 50 - np.random.randint(10, 50)  # 下跌
        h = max(o, c) + np.random.randint(0, 10)
        l = min(o, c) - np.random.randint(5, 20)
        v = 1000 + np.random.randint(0, 500)
        klines_2.append([i * 3600000, o, h, l, c, v])

    score_2, meta_2 = calculate_cvd_enhanced(klines_2)
    print(f"  CVD评分: {score_2:.1f}")
    print(f"  CVD Z-score: {meta_2['cvd_zscore']:.2f}")
    print(f"  CVD Delta: {meta_2['cvd_delta']:.0f}")
    print(f"  方向: {meta_2['cvd_direction']}")

    # 场景3: 震荡市场（CVD来回波动）
    print("\n[场景3] 震荡市场（CVD平稳）")
    klines_3 = []
    base_price = 50000
    for i in range(80):
        # 震荡：随机上下
        direction = 1 if np.random.rand() > 0.5 else -1
        o = base_price + np.random.randint(-50, 50)
        c = o + direction * np.random.randint(10, 30)
        h = max(o, c) + np.random.randint(5, 15)
        l = min(o, c) - np.random.randint(5, 15)
        v = 1000 + np.random.randint(0, 300)
        klines_3.append([i * 3600000, o, h, l, c, v])

    score_3, meta_3 = calculate_cvd_enhanced(klines_3)
    print(f"  CVD评分: {score_3:.1f}")
    print(f"  CVD Z-score: {meta_3['cvd_zscore']:.2f}")
    print(f"  CVD Delta: {meta_3['cvd_delta']:.0f}")
    print(f"  方向: {meta_3['cvd_direction']}")

    # 场景4: 动态权重（永续+现货）
    print("\n[场景4] 动态权重（永续+现货）")
    klines_perp_4 = []
    klines_spot_4 = []
    base_price = 50000
    for i in range(80):
        # 永续：上涨（大成交量）
        o_perp = base_price + i * 50
        c_perp = base_price + i * 50 + 30
        h_perp = c_perp + 10
        l_perp = o_perp - 5
        v_perp = 2000 + np.random.randint(0, 500)  # 大量
        klines_perp_4.append([i * 3600000, o_perp, h_perp, l_perp, c_perp, v_perp])

        # 现货：小幅上涨（小成交量）
        o_spot = base_price + i * 30
        c_spot = base_price + i * 30 + 15
        h_spot = c_spot + 5
        l_spot = o_spot - 3
        v_spot = 500 + np.random.randint(0, 200)  # 小量
        klines_spot_4.append([i * 3600000, o_spot, h_spot, l_spot, c_spot, v_spot])

    score_4, meta_4 = calculate_cvd_enhanced(klines_perp_4, klines_spot_4)
    print(f"  CVD评分: {score_4:.1f}")
    print(f"  永续权重: {meta_4['w_perp']:.2f}")
    print(f"  现货权重: {meta_4['w_spot']:.2f}")
    print(f"  永续CVD: {meta_4['cvd_perp_current']:.0f}")
    print(f"  现货CVD: {meta_4['cvd_spot_current']:.0f}")
    print(f"  加权CVD: {meta_4['cvd_weighted_current']:.0f}")

    print("\n" + "=" * 60)
    print("✅ Enhanced CVD因子测试完成")
    print("=" * 60)
