# coding: utf-8
"""
V（量能）评分 - 使用方向性软映射（v2.0 ±100对称设计）

改进v2.0：
- ✅ 分数范围：-100 到 +100（0为中性）
- ✅ 方向自包含：正值=放量，负值=缩量
- ✅ 使用对称评分函数
- ✅ 量能本身具有方向性（放量/缩量）
"""
import math
from ats_core.features.scoring_utils import directional_score_symmetric

def score_volume(vol, params=None):
    """
    V（量能）评分（v2.0 对称版本）

    核心逻辑：
    - vlevel = v5/v20，衡量近期量能相对均值
    - 1.0 = 中性（v5 = v20）
    - > 1.0 = 放量 → 正分（通常利于趋势）
    - < 1.0 = 缩量 → 负分（通常趋势减弱）

    Args:
        vol: 量能列表
        params: 参数配置

    Returns:
        (V分数 -100~+100, 元数据)
        - 正值：放量 → 趋势可能增强
        - 负值：缩量 → 趋势可能减弱
        - 0：量能中性
    """
    # 默认参数
    default_params = {
        "vlevel_scale": 0.3,      # v5/v20 = 1.3 给约 69 分
        "vroc_scale": 0.3,        # vroc_abs = 0.3 给约 69 分
        "vlevel_weight": 0.6,     # vlevel 权重
        "vroc_weight": 0.4,       # vroc 权重
    }

    p = dict(default_params)
    if isinstance(params, dict):
        p.update(params)

    if len(vol) < 25:
        return 0, {"v5v20": 1.0, "vroc_abs": 0.0, "insufficient_data": True}

    v5 = sum(vol[-5:]) / 5.0
    v20 = sum(vol[-20:]) / 20.0
    vlevel = v5 / max(1e-12, v20)

    # vroc_abs: |ln(v/sma20) - ln(prev)|
    cur = math.log(max(1e-9, vol[-1] / max(1e-9, v20)))
    prv = math.log(max(1e-9, vol[-2] / max(1e-9, sum(vol[-21:-1]) / 20.0)))
    vroc_abs = abs(cur - prv)

    # 对称评分
    # vlevel: 1.0 为中性，>1.0 放量（正分），<1.0 缩量（负分）
    vlevel_score = directional_score_symmetric(
        vlevel,
        neutral=1.0,
        scale=p["vlevel_scale"]
    )  # -100 到 +100

    # vroc: 量能变化率，绝对值越大越好（放量）
    # 将绝对值转为对称指标（暂时保持正向，因为放量通常好）
    vroc_score = directional_score_symmetric(
        vroc_abs,
        neutral=0.0,
        scale=p["vroc_scale"]
    )  # -100 到 +100

    # 加权平均
    V = p["vlevel_weight"] * vlevel_score + p["vroc_weight"] * vroc_score
    V = int(round(max(-100, min(100, V))))

    return V, {
        "v5v20": round(vlevel, 2),
        "vroc_abs": round(vroc_abs, 4),
        "vlevel_score": vlevel_score,
        "vroc_score": vroc_score,
        "interpretation": "放量" if V > 20 else ("缩量" if V < -20 else "中性")
    }
