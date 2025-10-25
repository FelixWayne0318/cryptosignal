# coding: utf-8
"""
C（CVD资金流）维度 - 买卖压力分析
从原A（加速）中分离出CVD部分

核心指标：
- CVD（Cumulative Volume Delta）变化
- 买卖压力对比
"""
from typing import List, Tuple, Dict, Any
from .scoring_utils import directional_score

def score_cvd_flow(
    cvd_series: List[float],
    c: List[float],
    side_long: bool,
    params: Dict[str, Any] = None
) -> Tuple[int, Dict[str, Any]]:
    """
    C（CVD资金流）维度评分

    Args:
        cvd_series: CVD 序列
        c: 收盘价序列（用于归一化）
        side_long: 是否做多
        params: 参数配置

    Returns:
        (C分数, 元数据)
    """
    # 默认参数
    default_params = {
        "lookback_hours": 6,       # CVD回看周期（小时）
        "cvd_scale": 0.02,         # CVD变化scale
    }

    p = dict(default_params)
    if isinstance(params, dict):
        p.update(params)

    if len(cvd_series) < 7 or len(c) < 7:
        return 50, {"cvd6": 0.0, "cvd_score": 50}

    # ========== 1. 计算 CVD 6小时变化 ==========
    # CVD归一化到价格（避免不同币种的CVD量级差异）
    cvd6 = (cvd_series[-1] - cvd_series[-7]) / max(1e-12, abs(c[-1]) + 1.0)

    # ========== 2. 软映射评分（多空对称） ==========
    if side_long:
        # 做多：CVD上升（买压强）好
        cvd_score = directional_score(
            cvd6,
            neutral=0.0,
            scale=p["cvd_scale"]
        )
    else:
        # 做空：CVD下降（卖压强）好
        cvd_score = directional_score(
            -cvd6,  # 取反
            neutral=0.0,
            scale=p["cvd_scale"]
        )

    # ========== 3. 最终分数 ==========
    C = int(round(max(0, min(100, cvd_score))))

    # ========== 4. 返回元数据 ==========
    return C, {
        "cvd6": round(cvd6, 6),
        "cvd_raw": round(cvd_series[-1] - cvd_series[-7], 2),
        "cvd_score": cvd_score
    }
