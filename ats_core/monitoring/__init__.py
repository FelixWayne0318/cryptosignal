# coding: utf-8
"""
因子监控系统 (v7.4.0 - 四步决策系统)

模块:
- vif_monitor: 方差膨胀因子(VIF)监控 - 检测多重共线性
- ic_monitor: 信息系数(IC)监控 - 检测因子失效

用途:
- 实时监控因子质量
- 及时发现因子退化
- 避免过拟合风险
"""

__all__ = [
    'VIFMonitor',
    'ICMonitor'
]
