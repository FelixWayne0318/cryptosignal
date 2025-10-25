# coding: utf-8
"""
回测系统模块

提供完整的回测功能：
- BacktestEngine: 回测引擎核心
- BacktestDataLoader: 历史数据加载
- BacktestMetrics: 性能指标计算
- BacktestReport: 回测报告生成
"""

from .engine import BacktestEngine, BacktestTrade
from .data_loader import BacktestDataLoader
from .metrics import calculate_metrics, format_metrics_report
from .report import generate_report, save_report

__all__ = [
    'BacktestEngine',
    'BacktestTrade',
    'BacktestDataLoader',
    'calculate_metrics',
    'format_metrics_report',
    'generate_report',
    'save_report'
]
