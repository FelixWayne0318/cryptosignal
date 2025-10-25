# coding: utf-8
"""
数据库模块

提供数据持久化功能：
- Signal: 交易信号记录
- DailyMetrics: 每日性能指标
"""

from .models import Signal, DailyMetrics, Database, db
from .operations import (
    save_signal,
    update_signal_exit,
    get_open_signals,
    get_recent_signals,
    calculate_daily_metrics,
    get_performance_summary
)

__all__ = [
    'Signal',
    'DailyMetrics',
    'Database',
    'db',
    'save_signal',
    'update_signal_exit',
    'get_open_signals',
    'get_recent_signals',
    'calculate_daily_metrics',
    'get_performance_summary'
]
