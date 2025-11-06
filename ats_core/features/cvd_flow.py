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
from .scoring_utils import directional_score  # 保留用于内部计算
from ats_core.scoring.scoring_utils import StandardizationChain

# 模块级StandardizationChain实例
_cvd_chain = StandardizationChain(alpha=0.15, tau=3.0, z0=2.5, zmax=6.0, lam=1.5)

def score_cvd_flow(
    cvd_series: List[float],
    c: List[float],
    side_long: bool,
    params: Dict[str, Any] = None,
    klines: List[list] = None
) -> Tuple[int, Dict[str, Any]]:
    """
    C（CVD资金流）维度评分

    Args:
        cvd_series: CVD 序列
        c: 收盘价序列（用于归一化，旧方案）
        side_long: 是否做多
        params: 参数配置
        klines: K线数据（用于ADTV_notional归一化，推荐）

    Returns:
        (C分数, 元数据)

    改进（v2.1）：
        - 添加拥挤度检测（学习OI的95分位数逻辑）
        - 资金流过于拥挤时降权（避免追高）

    改进（v2.5++最终方案）：
        - 使用相对历史斜率归一化（方向+斜率判断）
        - 核心理念：CVD判断买卖压力方向和变化速度，与绝对量无关
        - 相对强度 = 当前斜率 / 历史平均斜率
        - 自动适应每个币种的历史特征，BTC和SHIB在同等相对强度下得分一致
        - 解决低价币过度放大问题，实现真正的跨币可比
    """
    # 默认参数
    default_params = {
        "lookback_hours": 6,       # CVD回看周期（小时）
        "cvd_scale": 0.15,         # P2.4修复: 0.02→0.15，避免饱和（CVD变化scale，7.5倍增加）
        "crowding_p95_penalty": 10,  # 拥挤度惩罚（百分比）
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
    cvd_window = cvd_series[-7:]  # 最近7个数据点（6小时）
    n = len(cvd_window)

    # ========== 2. 线性回归分析（判断持续性） ==========
    # 2.1 计算线性回归斜率（每小时平均变化）
    x_mean = (n - 1) / 2.0
    y_mean = sum(cvd_window) / n

    numerator = sum((i - x_mean) * (cvd_window[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    slope = numerator / denominator if denominator > 0 else 0

    # 2.2 计算R²（拟合优度，0-1，越大越线性）
    y_pred = [slope * i + (y_mean - slope * x_mean) for i in range(n)]
    ss_res = sum((cvd_window[i] - y_pred[i]) ** 2 for i in range(n))
    ss_tot = sum((cvd_window[i] - y_mean) ** 2 for i in range(n))
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    # 2.3 综合判断持续性
    # R² >= 0.7 = 持续性强（变化平稳，不被单根K线主导）
    is_consistent = (r_squared >= 0.7)

    # ========== 3. 软映射评分（带符号，-100到+100） ==========
    # v2.5++最终方案：相对历史斜率归一化（方向+斜率，无绝对量）
    # 核心理念：CVD判断方向和变化速度，与资金流入流出绝对量无关

    # 3.1 计算历史斜率分布（用于自适应归一化）
    use_historical_norm = (len(cvd_series) >= 30)  # 至少30个数据点
    if use_historical_norm:
        # 计算过去所有6小时窗口的斜率
        hist_slopes = []
        for i in range(6, len(cvd_series)):
            window = cvd_series[i-6:i+1]
            if len(window) == 7:
                # 线性回归计算斜率
                x_m = 3.0  # (7-1)/2
                y_m = sum(window) / 7
                num = sum((j - x_m) * (window[j] - y_m) for j in range(7))
                den = sum((j - x_m) ** 2 for j in range(7))
                if den > 0:
                    hist_slopes.append(num / den)

        # 计算历史斜率的平均绝对值（代表"正常"变化速度）
        if len(hist_slopes) >= 10:
            avg_abs_slope = sum(abs(s) for s in hist_slopes) / len(hist_slopes)
            avg_abs_slope = max(1e-8, avg_abs_slope)  # 防止除零
        else:
            avg_abs_slope = None
    else:
        avg_abs_slope = None

    # 3.2 归一化：相对强度（当前斜率 / 历史平均斜率）
    if avg_abs_slope is not None:
        # 相对强度 = 当前速度 / 历史平均速度（保留正负）
        relative_intensity = slope / avg_abs_slope
        # 使用相对强度映射（scale调大，因为relative_intensity通常在±0.5到±3范围）
        normalized = math.tanh(relative_intensity / 2.0)  # scale=2.0
        cvd_score = 100.0 * normalized
        normalization_method = "relative_historical"
    else:
        # 降级方案：使用固定scale（历史数据不足时）
        # 这时只能用绝对斜率 + 固定scale
        normalized = math.tanh(slope / 1000.0)  # 经验值，需要调整
        cvd_score = 100.0 * normalized
        normalization_method = "absolute_fallback"

    # 如果R²低（震荡），降低分数（震荡意味着不稳定）
    if not is_consistent:
        # 根据R²打折：R²=0.4→70%, R²=0.6→85%, R²=0.7→100%
        stability_factor = 0.7 + 0.3 * (r_squared / 0.7)
        cvd_score = cvd_score * min(1.0, stability_factor)

    # ========== 4. 拥挤度检测（新增v2.1，学习OI的95分位数逻辑） ==========
    # v2.5++：使用历史斜率的95分位数判断拥挤度
    crowding_warn = False
    p95_slope = None

    if use_historical_norm and avg_abs_slope is not None and len(hist_slopes) >= 20:
        # 使用历史斜率绝对值的95分位数
        abs_slopes = [abs(s) for s in hist_slopes]
        sorted_abs_slopes = sorted(abs_slopes)
        p95_idx = int(0.95 * (len(sorted_abs_slopes) - 1))
        p95_slope = sorted_abs_slopes[p95_idx]

        # 检测当前斜率是否超过95分位数（拥挤）
        crowding_warn = (abs(slope) >= p95_slope)

    # 如果资金流拥挤，降权（避免追高/杀跌）
    if crowding_warn:
        penalty_factor = (100 - p["crowding_p95_penalty"]) / 100.0
        cvd_score = cvd_score * penalty_factor

    # ========== 5. 最终分数（保留符号） ==========
    # v2.0合规：应用StandardizationChain
    # ⚠️ 2025-11-04紧急修复：禁用StandardizationChain，过度压缩导致信号丢失
    C_raw = cvd_score  # 保存原始值
    # C_pub, diagnostics = _cvd_chain.standardize(C_raw)
    C_pub = max(-100, min(100, C_raw))  # 直接使用原始值
    C = int(round(C_pub))

    # 计算cvd6用于显示（原始CVD变化，不归一化）
    cvd6_raw = cvd_window[-1] - cvd_window[0]

    # ========== 6. 返回元数据 ==========
    meta = {
        "cvd6_raw": round(cvd6_raw, 2),       # 原始CVD变化（用于显示）
        "cvd_slope": round(slope, 4),         # 斜率（原始值）
        "cvd_score": round(cvd_score, 2),     # CVD得分
        "r_squared": round(r_squared, 3),     # R²拟合优度（0-1）
        "is_consistent": is_consistent,       # 是否持续（R²>=0.7）
        # v2.1: 拥挤度检测
        "crowding_warn": crowding_warn,       # 是否拥挤
        # v2.5++: 相对历史归一化信息
        "normalization_method": normalization_method,
    }

    # 添加相对强度信息（如果使用历史归一化）
    if avg_abs_slope is not None:
        meta["avg_abs_slope"] = round(avg_abs_slope, 4)  # 历史平均斜率
        meta["relative_intensity"] = round(slope / avg_abs_slope, 3)  # 相对强度
        if p95_slope is not None:
            meta["p95_slope"] = round(p95_slope, 4)  # 95分位数阈值

    return C, meta
