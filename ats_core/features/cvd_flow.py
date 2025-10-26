# coding: utf-8
"""
C（CVD资金流）维度 - 买卖压力分析（v2.0 ±100对称设计）
从原A（加速）中分离出CVD部分

核心指标：
- CVD（Cumulative Volume Delta）变化
- 买卖压力对比

改进v2.0：
- ✅ 分数范围：-100 到 +100（0为中性）
- ✅ 方向自包含：正值=资金流入，负值=资金流出
- ✅ 移除side_long：不再需要多空参数
- ✅ 使用对称评分函数
"""
from typing import List, Tuple, Dict, Any
from .scoring_utils import directional_score_symmetric

def score_cvd_flow(
    cvd_series: List[float],
    c: List[float],
    params: Dict[str, Any] = None
) -> Tuple[int, Dict[str, Any]]:
    """
    C（CVD资金流）维度评分（v2.0 对称版本）

    Args:
        cvd_series: CVD 序列
        c: 收盘价序列（用于归一化）
        params: 参数配置

    Returns:
        (C分数 -100~+100, 元数据)
        - 正值：资金流入（买压强）→ 适合做多
        - 负值：资金流出（卖压强）→ 适合做空
        - 0：无明显资金流向 → 中性
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
        return 0, {"cvd6": 0.0, "cvd_score": 0, "insufficient_data": True}

    # ========== 1. 计算 CVD 6小时变化 ==========
    # CVD归一化到价格（避免不同币种的CVD量级差异）
    cvd6 = (cvd_series[-1] - cvd_series[-7]) / max(1e-12, abs(c[-1]) + 1.0)

    # ========== 2. 对称评分（无需side_long） ==========
    # 正值 = 流入 = 买压强 = 利多
    # 负值 = 流出 = 卖压强 = 利空
    cvd_score = directional_score_symmetric(
        cvd6,
        neutral=0.0,
        scale=p["cvd_scale"]
    )  # -100 到 +100

    # ========== 3. 最终分数 ==========
    C = int(round(max(-100, min(100, cvd_score))))

    # ========== 4. 返回元数据 ==========
    return C, {
        "cvd6": round(cvd6, 6),
        "cvd_raw": round(cvd_series[-1] - cvd_series[-7], 2),
        "cvd_score": cvd_score,
        "interpretation": "流入" if C > 20 else ("流出" if C < -20 else "中性")
    }
