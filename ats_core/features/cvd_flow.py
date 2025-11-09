# coding: utf-8
"""
C（CVD资金流）维度 - 买卖压力分析
从原A（加速）中分离出CVD部分

核心指标：
- CVD（Cumulative Volume Delta）变化
- 买卖压力对比

v3.0配置管理（2025-11-09）：
- 移除硬编码参数，改为从配置文件读取
- 支持向后兼容（params参数优先级高于配置文件）
- 使用统一的数据质量检查阈值

v3.1数据质量优化（2025-11-09）：
- 添加CVD异常值检测和过滤（IQR方法）
- 降低巨鲸订单和闪崩对因子的影响
- 与O+因子保持一致的异常值处理策略
"""
import math
from typing import List, Tuple, Dict, Any, Optional
from .scoring_utils import directional_score  # 保留用于内部计算
from ats_core.scoring.scoring_utils import StandardizationChain
from ats_core.config.factor_config import get_factor_config
from ats_core.utils.outlier_detection import detect_outliers_iqr, apply_outlier_weights

# v3.0: 模块级StandardizationChain实例（延迟初始化）
_cvd_chain: Optional[StandardizationChain] = None


def _get_cvd_chain() -> StandardizationChain:
    """
    获取StandardizationChain实例（延迟初始化）

    v3.0改进：从配置文件读取参数，而非硬编码
    """
    global _cvd_chain

    if _cvd_chain is None:
        try:
            config = get_factor_config()
            std_params = config.get_standardization_params("C+")

            # 检查是否启用StandardizationChain
            if std_params.get('enabled', True):
                _cvd_chain = StandardizationChain(
                    alpha=std_params['alpha'],
                    tau=std_params['tau'],
                    z0=std_params['z0'],
                    zmax=std_params['zmax'],
                    lam=std_params['lam']
                )
            else:
                # 如果配置禁用，使用默认参数创建（向后兼容）
                _cvd_chain = StandardizationChain(
                    alpha=0.25, tau=5.0, z0=3.0, zmax=6.0, lam=1.5
                )
        except Exception as e:
            # 配置加载失败时使用默认参数（向后兼容）
            print(f"⚠️ C+因子StandardizationChain配置加载失败，使用默认参数: {e}")
            _cvd_chain = StandardizationChain(
                alpha=0.25, tau=5.0, z0=3.0, zmax=6.0, lam=1.5
            )

    return _cvd_chain

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
        cvd_series: CVD序列
        c: 收盘价列表
        side_long: 是否做多
        params: 参数配置（v3.0：可选，优先级高于配置文件）
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

    v3.0改进：
        - 从配置文件读取默认参数
        - 传入的params参数优先级高于配置文件（向后兼容）
        - 使用配置的数据质量检查阈值
    """
    # v3.0: 从配置文件读取默认参数
    try:
        config = get_factor_config()
        config_params = config.get_factor_params("C+")
        min_data_points = config.get_data_quality_threshold("C+", "min_data_points")
    except Exception as e:
        # 配置加载失败时使用硬编码默认值（向后兼容）
        print(f"⚠️ C+因子配置加载失败，使用默认值: {e}")
        config_params = {
            "lookback_hours": 6,
            "cvd_scale": 0.15,
            "crowding_p95_penalty": 10,
        }
        min_data_points = 7

    # 合并配置参数：配置文件 < 传入的params（向后兼容）
    p = dict(config_params)
    if isinstance(params, dict):
        p.update(params)

    # v3.0: 使用配置的数据质量阈值
    if len(cvd_series) < min_data_points or len(c) < min_data_points:
        return 0, {
            "cvd6": 0.0,
            "cvd_score": 0,
            "consistency": 0.0,
            "r_squared": 0.0,
            "is_consistent": False,
            # v3.1: 添加降级诊断信息（统一元数据结构）
            "degradation_reason": "insufficient_data",
            "min_data_required": min_data_points
        }

    # ========== 1. 计算 CVD 6小时变化 ==========
    cvd_window = cvd_series[-7:]  # 最近7个数据点（6小时）
    n = len(cvd_window)

    # ========== 1.5 异常值检测和处理（v3.1新增） ==========
    # 防止巨鲸订单、闪崩等极端事件污染CVD趋势分析
    # 使用IQR方法（与O+因子一致）
    outliers_filtered = 0
    cvd_window_original = cvd_window.copy()  # 保存原始值用于对比

    if len(cvd_window) >= 5:  # 至少5个点才做异常值检测
        try:
            # 检测异常值（multiplier=1.5，标准IQR阈值）
            outlier_mask = detect_outliers_iqr(cvd_window, multiplier=1.5)
            outliers_filtered = sum(outlier_mask)

            if outliers_filtered > 0:
                # 对异常值降权而非完全删除（保持序列长度不变）
                # CVD对异常值更敏感，使用更低的权重（0.3 vs O+的0.5）
                cvd_window = apply_outlier_weights(
                    cvd_window,
                    outlier_mask,
                    outlier_weight=0.3  # 异常值仅保留30%权重
                )
        except Exception as e:
            # 异常值检测失败时使用原始数据（向后兼容）
            outliers_filtered = 0

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
    # ✅ P0修复（2025-11-09）：重新启用StandardizationChain（参数已优化）
    # v3.0: 使用延迟初始化的StandardizationChain
    C_raw = cvd_score  # 保存原始值
    cvd_chain = _get_cvd_chain()
    C_pub, diagnostics = cvd_chain.standardize(C_raw)
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
        # v3.1: 异常值过滤信息
        "outliers_filtered": outliers_filtered,  # 检测到的异常值数量
        "outlier_filter_applied": (outliers_filtered > 0),  # 是否应用了异常值过滤
    }

    # 添加相对强度信息（如果使用历史归一化）
    if avg_abs_slope is not None:
        meta["avg_abs_slope"] = round(avg_abs_slope, 4)  # 历史平均斜率
        meta["relative_intensity"] = round(slope / avg_abs_slope, 3)  # 相对强度
        if p95_slope is not None:
            meta["p95_slope"] = round(p95_slope, 4)  # 95分位数阈值

    return C, meta
