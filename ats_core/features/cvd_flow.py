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
        return 0, {
            "cvd6": 0.0,
            "cvd_score": 0,
            "consistency": 0.0,
            "r_squared": 0.0,
            "is_consistent": False
        }

    # ========== 1. 计算 CVD 6小时变化 ==========
    # CVD归一化到价格（避免不同币种的CVD量级差异）
    price = max(1e-12, abs(c[-1]) + 1.0)
    cvd_window = cvd_series[-7:]  # 最近7个数据点（6小时）
    cvd6 = (cvd_window[-1] - cvd_window[0]) / price

    # ========== 2. 持续性分析（判断是否持续流入/流出） ==========
    # 2.1 计算线性回归斜率
    n = len(cvd_window)
    x_mean = (n - 1) / 2.0
    y_mean = sum(cvd_window) / n

    numerator = sum((i - x_mean) * (cvd_window[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    slope = numerator / denominator if denominator > 0 else 0

    # 2.2 计算一致性（上涨K线占比）
    up_count = sum(1 for i in range(1, n) if cvd_window[i] > cvd_window[i-1])
    consistency = up_count / (n - 1) if n > 1 else 0

    # 2.3 计算R²（拟合优度，0-1，越大越线性）
    y_pred = [slope * i + (y_mean - slope * x_mean) for i in range(n)]
    ss_res = sum((cvd_window[i] - y_pred[i]) ** 2 for i in range(n))
    ss_tot = sum((cvd_window[i] - y_mean) ** 2 for i in range(n))
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    # 2.4 综合判断持续性
    # 一致性 >= 60% + R² >= 0.7 = 持续性强
    is_consistent = (consistency >= 0.6 and r_squared >= 0.7)

    # ========== 3. 软映射评分（带符号，-100到+100） ==========
    # 直接映射CVD变化，不取反
    # 正数 = 买入压力（CVD上升）
    # 负数 = 卖出压力（CVD下降）
    # 使用 tanh 映射: cvd6 / scale → (-1, 1) → (-100, 100)
    normalized = math.tanh(cvd6 / p["cvd_scale"])
    cvd_score = 100.0 * normalized

    # ========== 4. 最终分数（保留符号） ==========
    C = int(round(max(-100, min(100, cvd_score))))

    # ========== 5. 返回元数据 ==========
    return C, {
        "cvd6": round(cvd6, 6),
        "cvd_raw": round(cvd_window[-1] - cvd_window[0], 2),
        "cvd_score": cvd_score,
        "consistency": round(consistency, 3),  # 一致性（0-1）
        "r_squared": round(r_squared, 3),      # R²拟合优度（0-1）
        "is_consistent": is_consistent          # 是否持续
    }
