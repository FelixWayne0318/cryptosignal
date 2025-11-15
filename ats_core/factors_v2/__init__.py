# coding: utf-8
"""
统一因子系统 v7.2

v7.2精简版：
- 核心因子 (评分): T, M, C, V, O, B（在features/中实现）
- 调制器 (调节): L, S, F, I（在features/和modulators/中实现）
- factors_v2保留：B因子（基差+资金费）和I因子（独立性）

v7.2.43清理：
- 删除未使用模块：oi_regime, volume_trigger, liquidity, cvd_enhanced
- 这些功能已被features/模块替代或废弃
"""

from .basis_funding import score_basis_funding
from .independence import calculate_independence

__all__ = [
    'score_basis_funding',
    'calculate_independence',
]
