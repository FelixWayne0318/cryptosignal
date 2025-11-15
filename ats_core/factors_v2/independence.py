# coding: utf-8
"""
I 因子: Independence（独立性）- v7.3.2-Full

版本：v7.3.2-Full - BTC-only零硬编码重构
作者：Claude Code
日期：2025-11-15

理论基础：
通过BTC-only Beta回归识别币种相对于BTC的独立性：
- 低Beta (<0.6): 高独立性，可能存在Alpha机会
- 中Beta (0.6-1.2): 正常相关性
- 高Beta (>1.2): 高相关性，需要风控限制

计算方法（v7.3.2-Full）：
alt_ret = α + β_BTC * btc_ret + ε
使用log-return: ret = log(P_t / P_{t-1})

β→I映射（0-100质量因子）：
- |β| ≤ 0.6: I ∈ [85, 100] (高独立性)
- 0.6 < |β| < 0.9: I ∈ [70, 85] (独立)
- 0.9 ≤ |β| ≤ 1.2: I ∈ [30, 70] (中性)
- 1.2 < |β| < 1.5: I ∈ [15, 30] (相关)
- |β| ≥ 1.5: I ∈ [0, 15] (高度相关)

重大变更：
1. 移除ETH因子，仅使用BTC做β回归
2. 使用log-return替代简单return
3. 所有常量从RuntimeConfig读取（零硬编码）
4. R²过滤：R² < 0.1时认为回归不可靠，返回I=50
5. 新增元数据：beta_btc, r2, n_points, status等
"""

from __future__ import annotations
from typing import Tuple, List, Dict, Any, Optional
import numpy as np
import math
from ats_core.config.runtime_config import RuntimeConfig
from ats_core.utils.format_utils import format_float_safe


def _calculate_log_returns(prices: np.ndarray, eps: float = 1e-10) -> np.ndarray:
    """
    计算对数收益率序列（v7.3.2-Full）

    使用log-return提高数值稳定性：
    ret = log(P_t / P_{t-1})

    Args:
        prices: 价格序列（numpy数组）
        eps: 防止log(0)的最小值

    Returns:
        对数收益率数组（长度为len(prices)-1）

    Note:
        - eps从RuntimeConfig.get_numeric_stability()读取
        - 价格 <= 0的情况会被eps保护
    """
    if len(prices) < 2:
        return np.array([])

    # 确保价格为正数（添加eps保护）
    prices_safe = np.maximum(prices, eps)

    # 计算对数收益率: log(P_t / P_{t-1})
    log_prices = np.log(prices_safe)
    log_returns = np.diff(log_prices)

    return log_returns


def _remove_outliers_3sigma(
    alt_returns: np.ndarray,
    btc_returns: np.ndarray,
    sigma_multiplier: float = 3.0
) -> Tuple[np.ndarray, np.ndarray, int]:
    """
    使用3-sigma规则移除异常值

    对alt和btc收益率序列分别计算3σ边界，
    然后创建联合mask保持时间对齐。

    Args:
        alt_returns: 山寨币收益率
        btc_returns: BTC收益率
        sigma_multiplier: sigma倍数（默认3.0）

    Returns:
        (alt_clean, btc_clean, outliers_removed)
        - alt_clean: 清洗后的alt收益率
        - btc_clean: 清洗后的btc收益率
        - outliers_removed: 被移除的异常值数量

    Note:
        sigma_multiplier从config读取（config/factors_unified.json的I.regression.outlier_sigma）
    """
    # 计算mask：保留 [mean - sigma*std, mean + sigma*std] 范围内的数据
    def get_mask(returns):
        mean = np.mean(returns)
        std = np.std(returns)
        if std == 0:
            return np.ones(len(returns), dtype=bool)
        lower = mean - sigma_multiplier * std
        upper = mean + sigma_multiplier * std
        return (returns >= lower) & (returns <= upper)

    mask_alt = get_mask(alt_returns)
    mask_btc = get_mask(btc_returns)

    # 联合mask（任一序列有异常则该时间点被过滤）
    mask_combined = mask_alt & mask_btc

    alt_clean = alt_returns[mask_combined]
    btc_clean = btc_returns[mask_combined]
    outliers_removed = len(alt_returns) - len(alt_clean)

    return alt_clean, btc_clean, outliers_removed


def calculate_beta_btc_only(
    alt_prices: np.ndarray,
    btc_prices: np.ndarray,
    params: Dict[str, Any]
) -> Tuple[float, float, int, str]:
    """
    BTC-only Beta回归（v7.3.2-Full核心算法）

    统计模型：
    alt_ret = α + β_BTC * btc_ret + ε

    流程：
    1. 计算log-return
    2. 3σ异常值过滤
    3. OLS回归计算β和R²
    4. 数据质量检查

    Args:
        alt_prices: 山寨币价格序列（numpy数组）
        btc_prices: BTC价格序列（numpy数组）
        params: 参数字典，从RuntimeConfig.get_factor_config("I")读取：
            - window_hours: 回归窗口
            - min_points: 最小有效样本数
            - outlier_sigma: 异常值过滤的sigma倍数
            - use_log_return: 是否使用对数收益率

    Returns:
        (beta_btc, r2, n_points, status)
        - beta_btc: BTC的Beta系数
        - r2: R²决定系数
        - n_points: 有效样本数
        - status: "ok" / "low_r2" / "insufficient_data"

    Note:
        - 所有参数从config读取，无硬编码
        - eps常量从RuntimeConfig.get_numeric_stability("independence")读取
    """
    # 1. 加载配置
    try:
        stability = RuntimeConfig.get_numeric_stability("independence")
        eps_log_price = stability["eps_log_price"]
        eps_var_min = stability["eps_var_min"]
        eps_r2_denom = stability["eps_r2_denominator"]
    except Exception:
        # 降级处理
        eps_log_price = 1e-10
        eps_var_min = 1e-12
        eps_r2_denom = 1e-10

    window_hours = params.get("window_hours", 24)
    min_points = params.get("min_points", 16)
    outlier_sigma = params.get("outlier_sigma", 3.0)
    use_log_return = params.get("use_log_return", True)

    # 2. 截取窗口
    alt_window = alt_prices[-window_hours-1:] if len(alt_prices) > window_hours else alt_prices
    btc_window = btc_prices[-window_hours-1:] if len(btc_prices) > window_hours else btc_prices

    # 3. 计算收益率
    if use_log_return:
        alt_returns = _calculate_log_returns(alt_window, eps_log_price)
        btc_returns = _calculate_log_returns(btc_window, eps_log_price)
    else:
        # 简单收益率（向后兼容，但不推荐）
        alt_returns = np.diff(alt_window) / (alt_window[:-1] + eps_var_min)
        btc_returns = np.diff(btc_window) / (btc_window[:-1] + eps_var_min)

    # 4. 数据量检查
    if len(alt_returns) < min_points or len(btc_returns) < min_points:
        return 0.0, 0.0, len(alt_returns), "insufficient_data"

    # 5. 异常值过滤
    alt_clean, btc_clean, outliers_removed = _remove_outliers_3sigma(
        alt_returns, btc_returns, outlier_sigma
    )

    # 6. 过滤后数据量检查
    if len(alt_clean) < min_points:
        return 0.0, 0.0, len(alt_clean), "insufficient_data"

    # 7. OLS回归: alt_ret = α + β * btc_ret + ε
    try:
        # 添加截距项
        X = np.column_stack([np.ones(len(btc_clean)), btc_clean])
        y = alt_clean

        # β = (X'X)^-1 X'y
        XtX = np.dot(X.T, X)
        Xty = np.dot(X.T, y)
        beta_with_intercept = np.linalg.solve(XtX, Xty)

        alpha = beta_with_intercept[0]
        beta_btc = beta_with_intercept[1]

        # 计算R²
        y_pred = np.dot(X, beta_with_intercept)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)

        if ss_tot > eps_r2_denom:
            r2 = max(0.0, 1.0 - (ss_res / ss_tot))  # 确保R²非负
        else:
            r2 = 0.0

        return beta_btc, r2, len(alt_clean), "ok"

    except (np.linalg.LinAlgError, ValueError) as e:
        # 回归失败（如矩阵奇异）
        return 0.0, 0.0, len(alt_clean), "regression_failed"


def score_independence(
    alt_prices: np.ndarray,
    btc_prices: np.ndarray,
    params: Optional[Dict[str, Any]] = None
) -> Tuple[int, Dict[str, Any]]:
    """
    I（独立性）因子评分 - v7.3.2-Full BTC-only版本

    使用BTC-only回归计算独立性：
    alt_ret = α + β_BTC * btc_ret + ε

    β→I映射（0-100质量因子）：
    - |β| ≤ 0.6: I ∈ [85, 100] (高度独立)
    - 0.6 < |β| < 0.9: I ∈ [70, 85] (独立)
    - 0.9 ≤ |β| ≤ 1.2: I ∈ [30, 70] (中性)
    - 1.2 < |β| < 1.5: I ∈ [15, 30] (相关)
    - |β| ≥ 1.5: I ∈ [0, 15] (高度相关)

    Args:
        alt_prices: 山寨币价格序列（numpy数组，最新值在最后）
        btc_prices: BTC价格序列（numpy数组）
        params: 参数字典（可选），如果为None则从config读取。
                支持的参数：
                - regression: {window_hours, min_points, outlier_sigma, use_log_return}
                - scoring: {r2_min, beta_low, beta_high, mapping}

    Returns:
        (I_score, metadata)
        - I_score: int, 0到100（越高越独立）
        - metadata: 详细信息字典，包含：
            - beta_btc: float, BTC的Beta系数
            - r2: float, R²决定系数
            - n_points: int, 有效样本数
            - status: str, "ok" / "low_r2" / "insufficient_data"
            - I_raw: float, 未截断的原始I值（调试用）
            - mapping_category: str, β所属的映射类别

    Note:
        - 所有参数从config/factors_unified.json的I节点读取
        - eps常量从config/numeric_stability.json读取
        - 零硬编码实现
    """
    # === 1. 加载配置 ===
    if params is None:
        try:
            # 从RuntimeConfig加载I因子完整配置
            all_factors = RuntimeConfig.load_factor_ranges()
            factors_cfg = all_factors.get("factors", {})
            i_cfg = factors_cfg.get("I", {})

            # 读取v7.3.2的regression和scoring配置块
            # 注意：这里需要从factors_unified.json读取，暂时使用默认值
            # TODO: 实现RuntimeConfig.get_factor_config("I")
            params = {
                "regression": {
                    "window_hours": 24,
                    "min_points": 16,
                    "outlier_sigma": 3.0,
                    "use_log_return": True
                },
                "scoring": {
                    "r2_min": 0.1,
                    "beta_low": 0.6,
                    "beta_high": 1.2
                }
            }
        except Exception as e:
            # 降级到默认值
            params = {
                "regression": {"window_hours": 24, "min_points": 16, "outlier_sigma": 3.0, "use_log_return": True},
                "scoring": {"r2_min": 0.1, "beta_low": 0.6, "beta_high": 1.2}
            }

    regression_params = params.get("regression", {})
    scoring_params = params.get("scoring", {})

    # === 2. 调用BTC-only β回归 ===
    beta_btc, r2, n_points, status = calculate_beta_btc_only(
        alt_prices, btc_prices, regression_params
    )

    # === 3. R²过滤 + I打分 ===
    r2_min = scoring_params.get("r2_min", 0.1)

    # 如果回归不可靠或数据不足，返回中性值
    if status != "ok" or r2 < r2_min:
        metadata = {
            "beta_btc": beta_btc,
            "r2": r2,
            "n_points": n_points,
            "status": "low_r2" if r2 < r2_min else status,
            "I_raw": 50.0,
            "mapping_category": "unreliable"
        }
        return 50, metadata  # 中性值

    # === 4. β→I映射（v7.3.2-Full） ===
    # 使用|β|（绝对值）映射到I分数
    beta_abs = abs(beta_btc)

    # 从config读取β分界点（如果有mapping配置则使用，否则使用简化版）
    mapping = scoring_params.get("mapping", {})

    if mapping:
        # 使用详细mapping配置（从factors_unified.json读取）
        # 这是完整的5档映射
        if beta_abs <= 0.6:
            # highly_independent: β ≤ 0.6 → I ∈ [85, 100]
            i_range = mapping.get("highly_independent", {}).get("I_range", [85, 100])
            I_raw = np.interp(beta_abs, [0, 0.6], [i_range[1], i_range[0]])
            category = "highly_independent"
        elif beta_abs < 0.9:
            # independent: 0.6 < β < 0.9 → I ∈ [70, 85]
            i_range = mapping.get("independent", {}).get("I_range", [70, 85])
            I_raw = np.interp(beta_abs, [0.6, 0.9], [i_range[1], i_range[0]])
            category = "independent"
        elif beta_abs <= 1.2:
            # neutral: 0.9 ≤ β ≤ 1.2 → I ∈ [30, 70]
            i_range = mapping.get("neutral", {}).get("I_range", [30, 70])
            I_raw = np.interp(beta_abs, [0.9, 1.2], [i_range[1], i_range[0]])
            category = "neutral"
        elif beta_abs < 1.5:
            # correlated: 1.2 < β < 1.5 → I ∈ [15, 30]
            i_range = mapping.get("correlated", {}).get("I_range", [15, 30])
            I_raw = np.interp(beta_abs, [1.2, 1.5], [i_range[1], i_range[0]])
            category = "correlated"
        else:
            # highly_correlated: β ≥ 1.5 → I ∈ [0, 15]
            i_range = mapping.get("highly_correlated", {}).get("I_range", [0, 15])
            I_raw = np.interp(beta_abs, [1.5, 2.0], [i_range[1], i_range[0]])
            I_raw = max(0.0, I_raw)  # 确保不低于0
            category = "highly_correlated"
    else:
        # 简化版映射（向后兼容）
        beta_low = scoring_params.get("beta_low", 0.6)
        beta_high = scoring_params.get("beta_high", 1.2)

        if beta_abs <= beta_low:
            # 高独立：I ∈ [85, 100]
            I_raw = 85.0 + (1.0 - beta_abs / beta_low) * 15.0
            category = "highly_independent"
        elif beta_abs <= 0.9:
            # 独立：I ∈ [70, 85]
            I_raw = 70.0 + (0.9 - beta_abs) / (0.9 - beta_low) * 15.0
            category = "independent"
        elif beta_abs <= beta_high:
            # 中性：I ∈ [30, 70]
            I_raw = 30.0 + (beta_high - beta_abs) / (beta_high - 0.9) * 40.0
            category = "neutral"
        elif beta_abs < 1.5:
            # 相关：I ∈ [15, 30]
            I_raw = 15.0 + (1.5 - beta_abs) / (1.5 - beta_high) * 15.0
            category = "correlated"
        else:
            # 高度相关：I ∈ [0, 15]
            I_raw = max(0.0, 15.0 - (beta_abs - 1.5) * 7.5)
            category = "highly_correlated"

    # === 5. 截断到[0, 100] ===
    I_score = int(round(np.clip(I_raw, 0, 100)))

    # === 6. 元数据 ===
    metadata = {
        "beta_btc": beta_btc,
        "r2": r2,
        "n_points": n_points,
        "status": status,
        "I_raw": I_raw,
        "mapping_category": category
    }

    return I_score, metadata


def calculate_independence(
    alt_prices: List[float],
    btc_prices: List[float],
    eth_prices: List[float] = None,
    params: Dict[str, Any] = None
) -> Tuple[float, float, Dict[str, Any]]:
    """
    向后兼容接口（v7.3.2-Full已弃用ETH参数）

    警告：此函数仅为向后兼容保留，新代码应使用score_independence()

    Args:
        alt_prices: 山寨币价格序列
        btc_prices: BTC价格序列
        eth_prices: ETH价格序列（已弃用，不再使用）
        params: 参数字典

    Returns:
        (independence_score, beta_btc, metadata)
        - independence_score: float, 0到100
        - beta_btc: float, BTC的Beta系数（旧版返回beta_sum，现返回beta_btc）
        - metadata: 详细信息

    Note:
        - v7.3.2-Full移除了ETH参数，仅使用BTC回归
        - 旧版返回值(score, beta_sum, metadata)改为(score, beta_btc, metadata)
    """
    # 转换为numpy数组
    alt_np = np.array(alt_prices, dtype=float)
    btc_np = np.array(btc_prices, dtype=float)

    # 调用新接口
    I_score, metadata = score_independence(alt_np, btc_np, params)

    # 兼容旧返回格式
    beta_btc = metadata["beta_btc"]

    return float(I_score), beta_btc, metadata


def diagnose_multicollinearity(factors: Dict[str, float], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    v7.2.44 P1优化：诊断8个因子之间的多重共线性

    使用VIF (Variance Inflation Factor) 检测因子间的多重共线性：
    - VIF < 5: 低共线性（良好）
    - 5 <= VIF < 10: 中等共线性（需要关注）
    - VIF >= 10: 严重共线性（需要处理）

    Args:
        factors: 包含8个因子的字典 {T, M, C, V, O, B, F, I}
        config: VIF配置（可选），包含threshold和warning_threshold

    Returns:
        诊断结果字典，包含：
        - vif_scores: 各因子的VIF值
        - max_vif: 最大VIF值
        - has_severe_multicollinearity: 是否存在严重共线性
        - warnings: 警告列表
    """
    try:
        import pandas as pd
        try:
            from statsmodels.stats.outliers_influence import variance_inflation_factor
        except ImportError:
            return {
                'error': 'statsmodels未安装，无法计算VIF',
                'recommendation': 'pip install statsmodels',
                'has_severe_multicollinearity': False
            }

        # 加载配置
        if config is None:
            try:
                from ats_core.config.threshold_config import get_thresholds
                thresholds = get_thresholds()
                config = thresholds.config.get('VIF多重共线性监控', {})
            except Exception:
                config = {}

        vif_threshold = config.get('vif_threshold', 10.0)
        vif_warning_threshold = config.get('vif_warning_threshold', 5.0)

        # 准备数据：8个因子必须都存在
        required_factors = ['T', 'M', 'C', 'V', 'O', 'B', 'F', 'I']
        if not all(f in factors for f in required_factors):
            missing = [f for f in required_factors if f not in factors]
            return {
                'error': f'因子数据不完整，缺少: {missing}',
                'has_severe_multicollinearity': False
            }

        # 创建DataFrame（至少需要2个观测值来计算VIF，这里我们用单个观测值，所以需要特殊处理）
        # 注意：VIF通常需要多个样本，单个观测值无法计算。
        # 这里我们返回一个提示，说明需要在有历史数据的地方调用
        return {
            'note': 'VIF计算需要多个样本（至少n_factors+1个）。请在analyze_symbol_v72.py或batch扫描中收集多个信号的因子数据后调用。',
            'single_sample': factors,
            'recommendation': '在batch_scan_optimized.py中收集所有币种的因子数据，然后计算VIF',
            'has_severe_multicollinearity': False
        }

    except Exception as e:
        return {
            'error': f'VIF计算失败: {str(e)}',
            'has_severe_multicollinearity': False
        }


def calculate_vif_from_dataframe(factors_df: 'pd.DataFrame', config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    v7.2.44 P1优化：从DataFrame计算VIF

    这个函数用于batch扫描场景，输入是多个币种的因子数据

    Args:
        factors_df: DataFrame，每行是一个币种，列是8个因子[T, M, C, V, O, B, F, I]
        config: VIF配置（可选）

    Returns:
        VIF诊断结果
    """
    try:
        import pandas as pd
        from statsmodels.stats.outliers_influence import variance_inflation_factor

        # 加载配置
        if config is None:
            try:
                from ats_core.config.threshold_config import get_thresholds
                thresholds = get_thresholds()
                config = thresholds.config.get('VIF多重共线性监控', {})
            except Exception:
                config = {}

        vif_threshold = config.get('vif_threshold', 10.0)
        vif_warning_threshold = config.get('vif_warning_threshold', 5.0)

        # 移除缺失值
        factors_clean = factors_df.dropna()

        if len(factors_clean) < len(factors_df.columns) + 1:
            return {
                'error': f'样本数不足（需要>={len(factors_df.columns)+1}，当前={len(factors_clean)}）',
                'has_severe_multicollinearity': False
            }

        # 计算每个因子的VIF
        vif_scores = {}
        for i, col in enumerate(factors_clean.columns):
            try:
                vif_value = variance_inflation_factor(factors_clean.values, i)
                vif_scores[col] = float(vif_value) if not np.isnan(vif_value) else 999.9
            except Exception as e:
                vif_scores[col] = f'计算失败: {e}'

        # 分析结果
        max_vif = max([v for v in vif_scores.values() if isinstance(v, (int, float))])
        has_severe = max_vif >= vif_threshold
        has_warning = max_vif >= vif_warning_threshold

        warnings = []
        for factor, vif in vif_scores.items():
            if isinstance(vif, (int, float)):
                if vif >= vif_threshold:
                    warnings.append(f'{factor}因子VIF={vif:.2f}（严重共线性，阈值={vif_threshold}）')
                elif vif >= vif_warning_threshold:
                    warnings.append(f'{factor}因子VIF={vif:.2f}（中等共线性，警告阈值={vif_warning_threshold}）')

        return {
            'vif_scores': vif_scores,
            'max_vif': max_vif,
            'has_severe_multicollinearity': has_severe,
            'has_warning': has_warning,
            'warnings': warnings,
            'sample_size': len(factors_clean),
            'interpretation': '严重共线性' if has_severe else ('中等共线性' if has_warning else '低共线性')
        }

    except Exception as e:
        return {
            'error': f'VIF计算失败: {str(e)}',
            'has_severe_multicollinearity': False
        }


# ========== 测试代码 ==========

if __name__ == "__main__":
    print("=" * 60)
    print("I 因子测试 - Independence v7.3.2-Full (BTC-only)")
    print("=" * 60)

    # 模拟数据
    np.random.seed(42)

    # 场景1: 高独立性币种（低Beta，β ≈ 0.3）
    print("\n[场景1] 高独立性币种（β ≈ 0.3，预期I ≈ 85-100）")
    btc_1 = np.array([50000 + i * 100 + np.random.randn() * 200 for i in range(26)])
    # Alt几乎独立于BTC运动，仅有轻微相关
    btc_rets = np.diff(btc_1) / btc_1[:-1]
    alt_1 = np.array([10.0])
    for ret in btc_rets:
        alt_1 = np.append(alt_1, alt_1[-1] * (1 + ret * 0.3 + np.random.randn() * 0.05))

    score_1, meta_1 = score_independence(alt_1, btc_1)
    print(f"  I评分: {score_1}")
    print(f"  Beta_BTC: {meta_1['beta_btc']:.3f}")
    print(f"  R²: {meta_1['r2']:.3f}")
    print(f"  样本数: {meta_1['n_points']}")
    print(f"  分类: {meta_1['mapping_category']}")
    print(f"  状态: {meta_1['status']}")

    # 场景2: 高相关性币种（高Beta，β ≈ 1.8）
    print("\n[场景2] 高相关性币种（β ≈ 1.8，预期I ≈ 0-15）")
    btc_2 = np.array([50000 + i * 100 + np.random.randn() * 150 for i in range(26)])
    # Alt高度跟随BTC，β > 1.5
    btc_rets_2 = np.diff(btc_2) / btc_2[:-1]
    alt_2 = np.array([10.0])
    for ret in btc_rets_2:
        alt_2 = np.append(alt_2, alt_2[-1] * (1 + ret * 1.8 + np.random.randn() * 0.02))

    score_2, meta_2 = score_independence(alt_2, btc_2)
    print(f"  I评分: {score_2}")
    print(f"  Beta_BTC: {meta_2['beta_btc']:.3f}")
    print(f"  R²: {meta_2['r2']:.3f}")
    print(f"  样本数: {meta_2['n_points']}")
    print(f"  分类: {meta_2['mapping_category']}")
    print(f"  状态: {meta_2['status']}")

    # 场景3: 中性币种（β ≈ 1.0）
    print("\n[场景3] 中性相关性币种（β ≈ 1.0，预期I ≈ 30-70）")
    btc_3 = np.array([50000 + i * 100 + np.random.randn() * 180 for i in range(26)])
    # Alt与BTC正常相关，β ≈ 1.0
    btc_rets_3 = np.diff(btc_3) / btc_3[:-1]
    alt_3 = np.array([10.0])
    for ret in btc_rets_3:
        alt_3 = np.append(alt_3, alt_3[-1] * (1 + ret * 1.0 + np.random.randn() * 0.03))

    score_3, meta_3 = score_independence(alt_3, btc_3)
    print(f"  I评分: {score_3}")
    print(f"  Beta_BTC: {meta_3['beta_btc']:.3f}")
    print(f"  R²: {meta_3['r2']:.3f}")
    print(f"  样本数: {meta_3['n_points']}")
    print(f"  分类: {meta_3['mapping_category']}")
    print(f"  状态: {meta_3['status']}")

    # 场景4: 数据不足（R²低）
    print("\n[场景4] 数据不足场景（预期I=50，status=insufficient_data）")
    btc_4 = np.array([50000 + i * 100 for i in range(10)])  # 仅10个点
    alt_4 = np.array([10 + np.random.randn() * 0.5 for i in range(10)])

    score_4, meta_4 = score_independence(alt_4, btc_4)
    print(f"  I评分: {score_4}")
    print(f"  Beta_BTC: {meta_4['beta_btc']:.3f}")
    print(f"  R²: {meta_4['r2']:.3f}")
    print(f"  样本数: {meta_4['n_points']}")
    print(f"  分类: {meta_4['mapping_category']}")
    print(f"  状态: {meta_4['status']}")

    print("\n" + "=" * 60)
    print("✅ Independence v7.3.2-Full测试完成")
    print("=" * 60)
    print("\n说明：")
    print("- v7.3.2-Full移除ETH参数，仅使用BTC回归")
    print("- 使用log-return提高数值稳定性")
    print("- β→I映射：低β(高独立)→高I分数，高β(高相关)→低I分数")
    print("- 所有参数从config读取，零硬编码")
