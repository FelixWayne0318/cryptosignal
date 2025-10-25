# coding: utf-8
"""
V（量能）评分 - 使用方向性软映射

改进：
- 旧版：v5/v20 < 1.2 → 0 分（硬阈值）
- 新版：v5/v20 = 1.1 → 约 55 分（软映射）
"""
import math
from ats_core.features.scoring_utils import directional_score

def score_volume(vol, params=None):
    """
    V（量能）评分

    核心逻辑：
    - vlevel = v5/v20，衡量近期量能相对均值
    - 1.0 = 中性（v5 = v20）
    - > 1.0 = 放量
    - < 1.0 = 缩量

    Args:
        vol: 量能列表
        params: 参数配置

    Returns:
        (V分数, 元数据)
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
        return 50, {"v5v20": 1.0, "vroc_abs": 0.0}

    v5 = sum(vol[-5:]) / 5.0
    v20 = sum(vol[-20:]) / 20.0
    vlevel = v5 / max(1e-12, v20)

    # vroc_abs: |ln(v/sma20) - ln(prev)|
    cur = math.log(max(1e-9, vol[-1] / max(1e-9, v20)))
    prv = math.log(max(1e-9, vol[-2] / max(1e-9, sum(vol[-21:-1]) / 20.0)))
    vroc_abs = abs(cur - prv)

    # 软映射评分
    # vlevel: 1.0 为中性
    vlevel_score = directional_score(vlevel, neutral=1.0, scale=p["vlevel_scale"])

    # vroc: 量能变化率，0 为中性
    vroc_score = directional_score(vroc_abs, neutral=0.0, scale=p["vroc_scale"])

    # 加权平均
    V = p["vlevel_weight"] * vlevel_score + p["vroc_weight"] * vroc_score
    V = int(round(max(0, min(100, V))))

    return V, {
        "v5v20": round(vlevel, 2),
        "vroc_abs": round(vroc_abs, 4),
        "vlevel_score": vlevel_score,
        "vroc_score": vroc_score
    }
