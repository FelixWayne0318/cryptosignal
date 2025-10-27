# coding: utf-8
"""
统一因子系统 v2.0

10+1维因子体系:
- Layer 1 (价格行为): T, M, S, V+
- Layer 2 (资金流): C+, O+, F
- Layer 3 (微观结构): L, B, Q
- Layer 4 (市场环境): I
"""

from .oi_regime import calculate_oi_regime
from .volume_trigger import calculate_volume_trigger
from .liquidity import calculate_liquidity
from .basis_funding import calculate_basis_funding
from .liquidation import calculate_liquidation
from .independence import calculate_independence
from .cvd_enhanced import calculate_cvd_enhanced

__all__ = [
    'calculate_oi_regime',
    'calculate_volume_trigger',
    'calculate_liquidity',
    'calculate_basis_funding',
    'calculate_liquidation',
    'calculate_independence',
    'calculate_cvd_enhanced',
]
