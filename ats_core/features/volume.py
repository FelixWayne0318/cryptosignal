# coding: utf-8
"""
V（量能）评分 - 统一±100系统

改进：
- 放量 = 正分（好）
- 缩量 = 负分（差）
- 0 = 中性
"""
import math
from ats_core.features.scoring_utils import directional_score

def score_volume(vol, params=None):
    """
    V（量能）评分 - 统一±100系统

    核心逻辑：
    - vlevel = v5/v20，衡量近期量能相对均值
    - 1.0 = 中性（v5 = v20）→ 0分
    - > 1.0 = 放量 → 正分
    - < 1.0 = 缩量 → 负分

    Args:
        vol: 量能列表
        params: 参数配置

    Returns:
        (V分数 [-100, +100], 元数据)
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
        return 0, {"v5v20": 1.0, "vroc_abs": 0.0}

    v5 = sum(vol[-5:]) / 5.0
    v20 = sum(vol[-20:]) / 20.0
    vlevel = v5 / max(1e-12, v20)

    # vroc_abs: |ln(v/sma20) - ln(prev)|
    cur = math.log(max(1e-9, vol[-1] / max(1e-9, v20)))
    prv = math.log(max(1e-9, vol[-2] / max(1e-9, sum(vol[-21:-1]) / 20.0)))
    vroc_abs = abs(cur - prv)

    # 软映射评分（0-100）
    vlevel_score_raw = directional_score(vlevel, neutral=1.0, scale=p["vlevel_scale"])
    vroc_score_raw = directional_score(vroc_abs, neutral=0.0, scale=p["vroc_scale"])

    # 映射到 -100 到 +100
    vlevel_score = (vlevel_score_raw - 50) * 2
    vroc_score = (vroc_score_raw - 50) * 2

    # 加权平均
    V = p["vlevel_weight"] * vlevel_score + p["vroc_weight"] * vroc_score
    V = int(round(max(-100, min(100, V))))

    # 解释
    if V >= 40:
        interpretation = "强势放量"
    elif V >= 10:
        interpretation = "温和放量"
    elif V >= -10:
        interpretation = "量能平稳"
    elif V >= -40:
        interpretation = "温和缩量"
    else:
        interpretation = "大幅缩量"

    return V, {
        "v5v20": round(vlevel, 2),
        "vroc_abs": round(vroc_abs, 4),
        "vlevel_score": int(vlevel_score),
        "vroc_score": int(vroc_score),
        "interpretation": interpretation
    }
