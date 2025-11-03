# coding: utf-8
"""
统一因子系统 v6.6

6因子系统 + 4调制器:
- 核心因子 (评分): T, M, C, V, O, B
- 调制器 (调节): L, S, F, I

v6.6 变更:
- 移除Q因子（清算密度）- 数据不可靠
- L/S移至调制器层（不参与评分）
- F/I继续作为调制器
"""

from .oi_regime import calculate_oi_regime
from .volume_trigger import calculate_volume_trigger
from .liquidity import calculate_liquidity
from .basis_funding import calculate_basis_funding
from .independence import calculate_independence
from .cvd_enhanced import calculate_cvd_enhanced

__all__ = [
    'calculate_oi_regime',
    'calculate_volume_trigger',
    'calculate_liquidity',
    'calculate_basis_funding',
    'calculate_independence',
    'calculate_cvd_enhanced',
]
