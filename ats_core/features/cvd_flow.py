# coding: utf-8
"""
C（CVD资金流）维度 - 买卖压力分析
从原A（加速）中分离出CVD部分

核心指标：
- CVD（Cumulative Volume Delta）变化
- 买卖压力对比
"""
import math
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

    # ========== 2. 软映射评分（带符号，-100到+100） ==========
    # 直接映射CVD变化，不取反
    # 正数 = 买入压力（CVD上升）
    # 负数 = 卖出压力（CVD下降）
    # 使用 tanh 映射: cvd6 / scale → (-1, 1) → (-100, 100)
    normalized = math.tanh(cvd6 / p["cvd_scale"])
    cvd_score = 100.0 * normalized

    # ========== 3. 最终分数（保留符号） ==========
    C = int(round(max(-100, min(100, cvd_score))))

    # ========== 4. 返回元数据 ==========
    return C, {
        "cvd6": round(cvd6, 6),
        "cvd_raw": round(cvd_series[-1] - cvd_series[-7], 2),
        "cvd_score": cvd_score
    }
