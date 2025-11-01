# coding: utf-8
"""
A（加速）评分 - 使用方向性软映射

改进：
- 旧版：cvd6 < 0.01 → 0 分（硬阈值）
- 新版：cvd6 = 0.005 → 约 42 分（软映射）
"""
from ats_core.features.ta_core import ema
from ats_core.features.scoring_utils import directional_score  # 保留用于内部计算
from ats_core.scoring.scoring_utils import StandardizationChain

# 模块级StandardizationChain实例
_accel_chain = StandardizationChain(alpha=0.15, tau=3.0, z0=2.5, zmax=6.0, lam=1.5)

def score_accel(c, cvd_series, params=None):
    """
    A（加速）评分

    核心逻辑：
    - 价格加速度（斜率的变化）
    - CVD 6小时变化（资金流向）

    Args:
        c: 收盘价列表
        cvd_series: CVD 序列
        params: 参数配置

    Returns:
        (A分数, 元数据)
    """
    # 默认参数
    default_params = {
        "slope_scale": 0.01,      # 斜率 scale
        "cvd_scale": 0.02,        # CVD变化 scale
        "slope_weight": 0.6,      # 价格加速度权重
        "cvd_weight": 0.4,        # CVD 权重
    }

    p = dict(default_params)
    if isinstance(params, dict):
        p.update(params)

    # 计算 EMA30 斜率
    ema30 = ema(c, 30)
    slope_now = (ema30[-1] - ema30[-7]) / 6.0
    slope_prev = (ema30[-7] - ema30[-13]) / 6.0
    ds = slope_now - slope_prev

    # CVD 6小时变化（归一化到价格）
    cvd6 = (cvd_series[-1] - cvd_series[-7]) / max(1e-12, abs(c[-1]) * 0.0 + 1.0)

    # 软映射评分
    # 价格斜率：归一化到 ATR
    atr_proxy = (sum([abs(x) for x in c[-30:]]) / 30.0) / 1000.0
    slope_normalized = slope_now / max(1e-9, atr_proxy)

    slope_score = directional_score(
        slope_normalized,
        neutral=0.0,
        scale=p["slope_scale"]
    )

    cvd_score = directional_score(
        cvd6,
        neutral=0.0,
        scale=p["cvd_scale"]
    )

    # 加权平均
    A_raw = p["slope_weight"] * slope_score + p["cvd_weight"] * cvd_score

    # v2.0合规：应用StandardizationChain
    A_pub, diagnostics = _accel_chain.standardize(A_raw)
    A = int(round(max(0, min(100, A_pub))))

    # weak_gate: 保留原有逻辑（用于其他地方判断）
    weak_gate = (ds >= 0.02) or (cvd6 >= 0.02)

    return A, {
        "dslope30": round(ds, 6),
        "cvd6": round(cvd6, 6),
        "weak_ok": weak_gate,
        "slope_score": slope_score,
        "cvd_score": cvd_score,
        "slope_normalized": round(slope_normalized, 6)
    }
