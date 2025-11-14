# coding: utf-8
"""
I 因子: Independence（独立性）

整合 #9 领涨回传β

理论基础:
通过Beta回归识别币种相对于BTC/ETH的独立性：
- 低Beta (<0.5): 高独立性，可能存在Alpha机会
- 中Beta (0.5-1.5): 正常相关性
- 高Beta (>1.5): 高相关性，需要BTC/ETH确认

计算方法:
alt_return = α + β_BTC * btc_return + β_ETH * eth_return
beta_sum = 0.6 * β_BTC + 0.4 * β_ETH
independence_score = 100 * (1 - min(1.0, beta_sum / 1.5))

Range: 0 到 100（质量维度，非方向）
"""

from __future__ import annotations
from typing import Tuple, List, Dict, Any
import numpy as np
from ats_core.scoring.scoring_utils import StandardizationChain

# 模块级StandardizationChain实例
_independence_chain = StandardizationChain(alpha=0.15, tau=3.0, z0=2.5, zmax=6.0, lam=1.5)


def _to_f(x) -> float:
    """安全转换为float"""
    try:
        return float(x)
    except Exception:
        return 0.0


def _calculate_returns(prices: List[float]) -> List[float]:
    """
    计算收益率序列

    Args:
        prices: 价格序列

    Returns:
        收益率列表（长度为len(prices)-1）
    """
    if len(prices) < 2:
        return []

    returns = []
    for i in range(1, len(prices)):
        prev_price = _to_f(prices[i-1])
        curr_price = _to_f(prices[i])

        if prev_price > 0:
            ret = (curr_price - prev_price) / prev_price
            returns.append(ret)
        else:
            returns.append(0.0)

    return returns


def _ols_regression(y: List[float], X: np.ndarray) -> Tuple[np.ndarray, float]:
    """
    OLS最小二乘回归

    Args:
        y: 因变量（alt returns）
        X: 自变量矩阵（BTC returns, ETH returns）

    Returns:
        (betas, r_squared)
        betas: [β_BTC, β_ETH]
        r_squared: R²决定系数
    """
    try:
        # 添加截距项
        X_with_intercept = np.column_stack([np.ones(len(X)), X])

        # OLS: β = (X'X)^-1 X'y
        XtX = np.dot(X_with_intercept.T, X_with_intercept)
        Xty = np.dot(X_with_intercept.T, y)

        # 求解
        betas_with_intercept = np.linalg.solve(XtX, Xty)

        # 提取β（不含截距）
        betas = betas_with_intercept[1:]

        # 计算R²
        y_pred = np.dot(X_with_intercept, betas_with_intercept)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)

        if ss_tot > 0:
            r_squared = 1 - (ss_res / ss_tot)
        else:
            r_squared = 0.0

        return betas, r_squared

    except Exception as e:
        # 回归失败，返回中性值
        return np.array([1.0, 0.0]), 0.0


def calculate_independence(
    alt_prices: List[float],
    btc_prices: List[float],
    eth_prices: List[float],
    params: Dict[str, Any] = None
) -> Tuple[float, float, Dict[str, Any]]:
    """
    计算独立性评分

    Args:
        alt_prices: 山寨币价格序列（最新值在最后）
        btc_prices: BTC价格序列
        eth_prices: ETH价格序列
        params: 参数字典，包含:
            - window_hours: 回归窗口（默认24小时）
            - beta_threshold_high: 高Beta阈值（默认1.5）
            - beta_threshold_low: 低Beta阈值（默认0.5）
            - btc_weight: BTC权重（默认0.6）
            - eth_weight: ETH权重（默认0.4）

    Returns:
        (independence_score, beta_sum, metadata)
        - independence_score: 0到100（越高越独立）
        - beta_sum: 加权Beta总和
        - metadata: 详细信息
    """
    if params is None:
        params = {}

    # 默认参数（v7.2.8修复：24小时窗口以适应当前数据量）
    window = params.get('window_hours', 24)  # v7.2.8: 48→24，避免数据不足导致全返回50
    beta_high = params.get('beta_threshold_high', 1.5)
    beta_low = params.get('beta_threshold_low', 0.5)
    btc_weight = params.get('btc_weight', 0.6)
    eth_weight = params.get('eth_weight', 0.4)

    # === 1. 数据验证 ===
    if (len(alt_prices) < window + 1 or
        len(btc_prices) < window + 1 or
        len(eth_prices) < window + 1):
        return 50.0, 1.0, {
            'error': 'Insufficient data',
            'alt_len': len(alt_prices),
            'btc_len': len(btc_prices),
            'eth_len': len(eth_prices),
            'required': window + 1
        }

    # === 2. 计算收益率 ===
    alt_returns = _calculate_returns(alt_prices[-window-1:])
    btc_returns = _calculate_returns(btc_prices[-window-1:])
    eth_returns = _calculate_returns(eth_prices[-window-1:])

    if len(alt_returns) < window or len(btc_returns) < window or len(eth_returns) < window:
        return 50.0, 1.0, {'error': 'Return calculation failed'}

    # === 2.5 异常值处理（P1.3新增：3-sigma过滤）===
    # 移除极端异常值（如闪崩、插针等），提高Beta稳定性
    def remove_outliers(returns_array):
        """移除3-sigma之外的异常值"""
        mean = np.mean(returns_array)
        std = np.std(returns_array)
        if std == 0:
            return returns_array
        # 3-sigma规则：保留 [mean-3*std, mean+3*std] 范围内的数据
        mask = np.abs(returns_array - mean) <= 3 * std
        return mask

    # 对所有序列应用相同的mask（保持时间对齐）
    alt_array = np.array(alt_returns)
    btc_array = np.array(btc_returns)
    eth_array = np.array(eth_returns)

    # 计算综合mask（任一序列有异常则该时间点标记为异常）
    mask_alt = remove_outliers(alt_array)
    mask_btc = remove_outliers(btc_array)
    mask_eth = remove_outliers(eth_array)
    mask_combined = mask_alt & mask_btc & mask_eth

    # 应用mask
    alt_clean = alt_array[mask_combined]
    btc_clean = btc_array[mask_combined]
    eth_clean = eth_array[mask_combined]

    outliers_removed = len(alt_array) - len(alt_clean)

    # 检查过滤后数据是否充足
    if len(alt_clean) < max(10, window * 0.5):  # 至少保留50%数据或10个点
        return 50.0, 1.0, {
            'error': 'Too many outliers removed',
            'outliers_removed': outliers_removed,
            'remaining': len(alt_clean)
        }

    # === 3. OLS回归（使用清洗后的数据）===
    y = alt_clean
    X = np.column_stack([btc_clean, eth_clean])

    betas, r_squared = _ols_regression(y, X)
    beta_btc = betas[0]
    beta_eth = betas[1]

    # === 4. 加权Beta ===
    beta_sum = btc_weight * abs(beta_btc) + eth_weight * abs(beta_eth)

    # === 5. 独立性评分 ===
    # beta_sum越低，独立性越高
    # beta_sum = 0.0 → score = 100（完全独立）
    # beta_sum = 1.5 → score = 0（完全相关）
    if beta_sum >= beta_high:
        raw_score = 0.0
    else:
        # 线性映射：beta_sum从0到1.5，score从100到0
        raw_score = 100.0 * (1.0 - min(1.0, beta_sum / beta_high))

    # v2.0合规：应用StandardizationChain
    score_pub, diagnostics = _independence_chain.standardize(raw_score)
    independence_score = int(round(score_pub))

    # === 6. 独立性等级 ===
    if beta_sum < beta_low:
        independence_level = 'high'  # 高独立性（Alpha机会）
        interpretation = 'High independence, potential alpha opportunity'
    elif beta_sum < 1.0:
        independence_level = 'moderate'  # 中等独立性
        interpretation = 'Moderate correlation with BTC/ETH'
    elif beta_sum < beta_high:
        independence_level = 'low'  # 低独立性
        interpretation = 'High correlation with BTC/ETH'
    else:
        independence_level = 'very_low'  # 极低独立性
        interpretation = 'Very high correlation, needs BTC/ETH confirmation'

    # === 7. 元数据（P1.3增强：添加诊断信息）===
    metadata = {
        'independence_score': independence_score,
        'beta_sum': beta_sum,
        'beta_btc': beta_btc,
        'beta_eth': beta_eth,
        'r_squared': r_squared,
        'independence_level': independence_level,
        'interpretation': interpretation,
        'window_hours': window,
        # P1.3新增：异常值处理诊断
        'outliers_removed': outliers_removed,
        'data_points_used': len(alt_clean),
        'data_quality': len(alt_clean) / len(alt_array) if len(alt_array) > 0 else 0,
        # P1.3新增：统计诊断
        'alt_volatility': float(np.std(alt_clean)) if len(alt_clean) > 0 else 0,
        'btc_volatility': float(np.std(btc_clean)) if len(btc_clean) > 0 else 0,
        'eth_volatility': float(np.std(eth_clean)) if len(eth_clean) > 0 else 0
    }

    return independence_score, beta_sum, metadata


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
    print("I 因子测试 - Independence（独立性）")
    print("=" * 60)

    # 模拟数据
    np.random.seed(42)

    # 场景1: 高独立性币种（低Beta）
    print("\n[场景1] 高独立性币种（Alpha机会）")
    btc_1 = [50000 + i * 100 + np.random.randn() * 200 for i in range(25)]
    eth_1 = [3000 + i * 10 + np.random.randn() * 30 for i in range(25)]
    alt_1 = [10 + np.random.randn() * 0.5 for i in range(25)]  # 几乎独立运动

    score_1, beta_sum_1, meta_1 = calculate_independence(alt_1, btc_1, eth_1)
    print(f"  独立性评分: {score_1:.1f}")
    print(f"  Beta总和: {beta_sum_1:.3f}")
    print(f"  Beta_BTC: {meta_1['beta_btc']:.3f}")
    print(f"  Beta_ETH: {meta_1['beta_eth']:.3f}")
    print(f"  R²: {meta_1['r_squared']:.3f}")
    print(f"  等级: {meta_1['independence_level']}")
    print(f"  解读: {meta_1['interpretation']}")

    # 场景2: 高相关性币种（高Beta）
    print("\n[场景2] 高相关性币种（需要BTC确认）")
    btc_2 = [50000 + i * 100 for i in range(25)]
    eth_2 = [3000 + i * 10 for i in range(25)]
    alt_2 = [10 + i * 0.05 + btc_2[i]/50000 * 0.1 for i in range(25)]  # 高度跟随BTC

    score_2, beta_sum_2, meta_2 = calculate_independence(alt_2, btc_2, eth_2)
    print(f"  独立性评分: {score_2:.1f}")
    print(f"  Beta总和: {beta_sum_2:.3f}")
    print(f"  Beta_BTC: {meta_2['beta_btc']:.3f}")
    print(f"  Beta_ETH: {meta_2['beta_eth']:.3f}")
    print(f"  R²: {meta_2['r_squared']:.3f}")
    print(f"  等级: {meta_2['independence_level']}")
    print(f"  解读: {meta_2['interpretation']}")

    # 场景3: 中等相关性币种（Beta≈1）
    print("\n[场景3] 中等相关性币种（正常市场）")
    btc_3 = [50000 + i * 100 + np.random.randn() * 200 for i in range(25)]
    eth_3 = [3000 + i * 10 + np.random.randn() * 30 for i in range(25)]

    # 模拟中等相关（Beta≈1）
    btc_returns = [(btc_3[i] - btc_3[i-1]) / btc_3[i-1] for i in range(1, 25)]
    alt_3 = [10]
    for ret in btc_returns:
        alt_3.append(alt_3[-1] * (1 + ret * 0.8 + np.random.randn() * 0.02))

    score_3, beta_sum_3, meta_3 = calculate_independence(alt_3, btc_3, eth_3)
    print(f"  独立性评分: {score_3:.1f}")
    print(f"  Beta总和: {beta_sum_3:.3f}")
    print(f"  Beta_BTC: {meta_3['beta_btc']:.3f}")
    print(f"  Beta_ETH: {meta_3['beta_eth']:.3f}")
    print(f"  R²: {meta_3['r_squared']:.3f}")
    print(f"  等级: {meta_3['independence_level']}")
    print(f"  解读: {meta_3['interpretation']}")

    print("\n" + "=" * 60)
    print("✅ Independence因子测试完成")
    print("=" * 60)
