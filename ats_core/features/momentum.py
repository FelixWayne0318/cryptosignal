# coding: utf-8
"""
M（动量）维度 - 价格动量/加速度（±100系统）

核心指标：
- 价格斜率的变化（加速度）
- 短周期EMA差值（P2.2优化：EMA3-5，与T因子EMA5/20正交化）

返回范围：-100（强烈看空）~ 0（中性）~ +100（强烈看多）
v2.0合规：应用StandardizationChain（5步稳健化）

P2.2改进（2025-11-05）：
- 问题：T-M因子信息重叠度70.8%（P1.3分析结果）
- 方案C：M改用短窗口（EMA3/5），T保持长窗口（EMA5/20）
- 目标：降低重叠度至<50%，实现正交化

v2.5++最终方案（2025-11-05）：
- 使用相对历史归一化（与CVD一致）
- 核心理念：判断动量方向和变化速度，与绝对量无关
- 相对强度 = 当前斜率/加速度 / 历史平均值
- 自动适应每个币种的历史波动特征
- 解决不同波动率币种的跨币种可比性问题
"""
from typing import List, Tuple, Dict, Any
from .ta_core import ema, atr
from .scoring_utils import directional_score  # 保留用于内部计算
from ats_core.scoring.scoring_utils import StandardizationChain

# 模块级StandardizationChain实例（持久化EW状态）
# P0修复（2025-11-09）：使用新参数（alpha=0.25, tau=5.0, z0=3.0）
_momentum_chain = StandardizationChain(alpha=0.25, tau=5.0, z0=3.0, zmax=6.0, lam=1.5)

def score_momentum(
    h: List[float],
    l: List[float],
    c: List[float],
    params: Dict[str, Any] = None
) -> Tuple[int, Dict[str, Any]]:
    """
    M（动量）维度评分 - 统一±100系统

    不再需要side_long参数，直接返回带符号的分数：
    - 正值：看多（价格加速上涨）
    - 负值：看空（价格加速下跌）
    - 0：中性

    Args:
        h: 最高价列表
        l: 最低价列表
        c: 收盘价列表
        params: 参数配置

    Returns:
        (M分数 [-100, +100], 元数据)
    """
    # 默认参数
    # P2.2修改：使用短窗口EMA与T因子正交化
    # v2.5++: 相对历史归一化，scale需要调整（相对强度范围不同）
    default_params = {
        "ema_fast": 3,             # P2.2新增：超短期EMA（vs T的EMA5）
        "ema_slow": 5,             # P2.2新增：短期EMA（vs T的EMA20）
        "slope_lookback": 6,       # P2.2修改：12→6，减少窗口长度
        "slope_scale": 2.00,       # v2.5++修改：1.00→2.00（相对强度用更大scale）
        "accel_scale": 2.00,       # v2.5++修改：1.00→2.00（相对强度用更大scale）
        "slope_weight": 0.6,       # 斜率权重
        "accel_weight": 0.4,       # 加速度权重
        "atr_period": 14,          # ATR周期（降级方案使用）
    }

    p = dict(default_params)
    if isinstance(params, dict):
        p.update(params)

    if len(c) < 20:  # P2.2修改：30→20，短窗口需要更少数据
        return 0, {"slope_now": 0.0, "accel": 0.0, "slope_score": 0, "accel_score": 0}

    # ========== 1. P2.2改进：使用短周期EMA3/5计算动量 ==========
    # T因子用EMA5/20（大趋势），M因子用EMA3/5（快速动量）→ 正交化
    ema_fast_values = ema(c, p["ema_fast"])    # EMA3
    ema_slow_values = ema(c, p["ema_slow"])    # EMA5

    lookback = p["slope_lookback"]  # 6

    # 当前动量：EMA3 vs EMA5的差值（最近lookback根K线的平均差）
    # 使用差值作为动量指标，而不是单一EMA的斜率
    momentum_now = sum(ema_fast_values[-i] - ema_slow_values[-i]
                       for i in range(1, min(lookback + 1, len(c) + 1))) / lookback

    # 前一段动量（用于计算加速度）
    momentum_prev = sum(ema_fast_values[-i] - ema_slow_values[-i]
                        for i in range(lookback + 1, min(2 * lookback + 1, len(c) + 1))) / lookback

    # 斜率：使用EMA3的变化率（短期趋势）
    slope_now = (ema_fast_values[-1] - ema_fast_values[-lookback]) / (lookback - 1)
    slope_prev = (ema_fast_values[-lookback] - ema_fast_values[-2*lookback]) / (lookback - 1) if len(c) >= 2*lookback else 0.0

    # 加速度 = 动量的变化（EMA差值的变化）
    accel = momentum_now - momentum_prev

    # ========== 2. 归一化方案选择 ==========
    # v2.5++最终方案：相对历史归一化（与CVD一致）
    # 核心理念：判断动量方向和变化速度，与绝对量无关

    use_historical_norm = (len(c) >= 30)  # 至少30个数据点
    if use_historical_norm:
        # 2.1 计算历史所有slope和accel
        hist_slopes = []
        hist_accels = []

        for i in range(lookback * 2, len(ema_fast_values)):
            # 历史每个窗口的斜率
            s = (ema_fast_values[i] - ema_fast_values[i - lookback]) / (lookback - 1)
            hist_slopes.append(s)

            # 历史每个窗口的加速度（如果有足够数据）
            if i >= lookback * 3:
                # 当前动量
                mom_now = sum(ema_fast_values[i-j] - ema_slow_values[i-j]
                             for j in range(0, lookback)) / lookback
                # 前期动量
                mom_prev = sum(ema_fast_values[i-lookback-j] - ema_slow_values[i-lookback-j]
                              for j in range(0, lookback)) / lookback
                a = mom_now - mom_prev
                hist_accels.append(a)

        # 2.2 计算历史平均绝对值（代表"正常"变化速度）
        if len(hist_slopes) >= 10:
            avg_abs_slope = sum(abs(s) for s in hist_slopes) / len(hist_slopes)
            avg_abs_slope = max(1e-8, avg_abs_slope)
        else:
            avg_abs_slope = None

        if len(hist_accels) >= 10:
            avg_abs_accel = sum(abs(a) for a in hist_accels) / len(hist_accels)
            avg_abs_accel = max(1e-8, avg_abs_accel)
        else:
            avg_abs_accel = None
    else:
        avg_abs_slope = None
        avg_abs_accel = None

    # 2.3 归一化：相对强度 or ATR fallback
    if avg_abs_slope is not None:
        # 相对强度归一化
        slope_normalized = slope_now / avg_abs_slope
        normalization_method = "relative_historical"
    else:
        # 降级方案：ATR归一化（历史数据不足时）
        atr_values = atr(h, l, c, p["atr_period"])
        atr_val = atr_values[-1] if atr_values else 1.0
        slope_normalized = slope_now / max(1e-9, atr_val)
        normalization_method = "atr_fallback"

    if avg_abs_accel is not None:
        # 相对强度归一化
        accel_normalized = accel / avg_abs_accel
    else:
        # 降级方案：ATR归一化
        if normalization_method == "atr_fallback":
            atr_val = atr_values[-1] if atr_values else 1.0
        else:
            atr_values = atr(h, l, c, p["atr_period"])
            atr_val = atr_values[-1] if atr_values else 1.0
        accel_normalized = accel / max(1e-9, atr_val)

    # ========== 3. 软映射评分（±100系统）==========
    # directional_score 返回 10-100，需要映射到 -100到+100
    slope_score_raw = directional_score(
        slope_normalized,
        neutral=0.0,
        scale=p["slope_scale"]
    )
    accel_score_raw = directional_score(
        accel_normalized,
        neutral=0.0,
        scale=p["accel_scale"]
    )

    # 映射：10-100 → -100到+100
    # 公式：score_signed = (score_raw - 50) * 2
    slope_score = (slope_score_raw - 50) * 2
    accel_score = (accel_score_raw - 50) * 2

    # ========== 4. 加权平均（原始值）==========
    M_raw = p["slope_weight"] * slope_score + p["accel_weight"] * accel_score

    # v2.0合规：应用StandardizationChain
    # ✅ P0修复（2025-11-09）：重新启用StandardizationChain（参数已优化）
    M_pub, diagnostics = _momentum_chain.standardize(M_raw)
    M = int(round(M_pub))

    # ========== 5. 解释 ==========
    if M >= 60:
        interpretation = "强势上涨"
    elif M >= 20:
        interpretation = "温和上涨"
    elif M >= -20:
        interpretation = "中性"
    elif M >= -60:
        interpretation = "温和下跌"
    else:
        interpretation = "强势下跌"

    # ========== 6. 返回元数据 ==========
    meta = {
        "slope_now": round(slope_now, 6),
        "slope_prev": round(slope_prev, 6),
        "accel": round(accel, 6),
        "momentum_now": round(momentum_now, 6),      # P2.2新增：当前动量（EMA3-5差值）
        "momentum_prev": round(momentum_prev, 6),    # P2.2新增：前期动量
        "slope_normalized": round(slope_normalized, 6),
        "accel_normalized": round(accel_normalized, 6),
        "slope_score": int(slope_score),
        "accel_score": int(accel_score),
        "interpretation": interpretation,
        "p22_version": "short_window",               # P2.2版本标识
        "ema_config": f"EMA{p['ema_fast']}/{p['ema_slow']}",  # EMA配置
        # v2.5++: 相对历史归一化信息
        "normalization_method": normalization_method,
    }

    # 添加相对强度信息（如果使用历史归一化）
    if avg_abs_slope is not None:
        meta["avg_abs_slope"] = round(avg_abs_slope, 6)
        meta["relative_slope_intensity"] = round(slope_now / avg_abs_slope, 3)
    if avg_abs_accel is not None:
        meta["avg_abs_accel"] = round(avg_abs_accel, 6)
        meta["relative_accel_intensity"] = round(accel / avg_abs_accel, 3)

    return M, meta
