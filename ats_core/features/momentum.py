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
"""
from typing import List, Tuple, Dict, Any
from .ta_core import ema, atr
from .scoring_utils import directional_score  # 保留用于内部计算
from ats_core.scoring.scoring_utils import StandardizationChain

# 模块级StandardizationChain实例（持久化EW状态）
_momentum_chain = StandardizationChain(alpha=0.15, tau=3.0, z0=2.5, zmax=6.0, lam=1.5)

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
    default_params = {
        "ema_fast": 3,             # P2.2新增：超短期EMA（vs T的EMA5）
        "ema_slow": 5,             # P2.2新增：短期EMA（vs T的EMA20）
        "slope_lookback": 6,       # P2.2修改：12→6，减少窗口长度
        "slope_scale": 1.00,       # 斜率scale（修复：0.01→0.30→1.00，避免过度饱和）
        "accel_scale": 1.00,       # 加速度scale（修复：0.005→0.30→1.00，避免过度饱和）
        "slope_weight": 0.6,       # 斜率权重
        "accel_weight": 0.4,       # 加速度权重
        "atr_period": 14,          # ATR周期
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

    # ========== 2. 归一化到真实ATR ==========
    # 使用真实ATR而非价格代理（修复：原来的atr_proxy导致M分数被低估50-70%）
    atr_values = atr(h, l, c, p["atr_period"])
    atr_val = atr_values[-1] if atr_values else 1.0
    slope_normalized = slope_now / max(1e-9, atr_val)
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
    # ⚠️ 2025-11-04紧急修复：禁用StandardizationChain，过度压缩导致信号丢失
    # M_pub, diagnostics = _momentum_chain.standardize(M_raw)
    M_pub = max(-100, min(100, M_raw))  # 直接使用原始值
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
    return M, {
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
        "ema_config": f"EMA{p['ema_fast']}/{p['ema_slow']}"  # EMA配置
    }
