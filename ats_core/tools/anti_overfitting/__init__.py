# coding: utf-8
"""
Anti-Overfitting Tools

防过拟合工具集，包括：
1. 因子相关性监控
2. IC（Information Coefficient）监控
3. 时间序列交叉验证
"""

from .factor_correlation import FactorCorrelationMonitor
from .ic_monitor import ICMonitor
from .cross_validator import TimeSeriesCrossValidator

__all__ = [
    "FactorCorrelationMonitor",
    "ICMonitor",
    "TimeSeriesCrossValidator"
]
