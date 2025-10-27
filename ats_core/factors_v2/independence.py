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

    # 默认参数
    window = params.get('window_hours', 24)
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

    # === 3. OLS回归 ===
    y = np.array(alt_returns)
    X = np.column_stack([btc_returns, eth_returns])

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
        independence_score = 0.0
    else:
        # 线性映射：beta_sum从0到1.5，score从100到0
        independence_score = 100.0 * (1.0 - min(1.0, beta_sum / beta_high))

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

    # === 7. 元数据 ===
    metadata = {
        'independence_score': independence_score,
        'beta_sum': beta_sum,
        'beta_btc': beta_btc,
        'beta_eth': beta_eth,
        'r_squared': r_squared,
        'independence_level': independence_level,
        'interpretation': interpretation,
        'window_hours': window
    }

    return independence_score, beta_sum, metadata


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
