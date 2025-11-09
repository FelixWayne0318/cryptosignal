# coding: utf-8
"""
ATS Core Monitoring Package

提供系统监控和诊断功能。
"""

from .degradation_monitor import (
    DegradationMonitor,
    get_global_monitor,
    record_degradation,
    get_degradation_stats
)

__all__ = [
    'DegradationMonitor',
    'get_global_monitor',
    'record_degradation',
    'get_degradation_stats'
]
