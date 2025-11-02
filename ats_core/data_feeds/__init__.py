# coding: utf-8
"""
数据获取模块

提供多源数据获取功能：
- newcoin_data: 新币专用数据获取（1m/5m/15m粒度 + AVWAP）
- ws_newcoin: 新币WebSocket实时订阅
"""

from .newcoin_data import (
    quick_newcoin_check,
    fetch_newcoin_data,
    fetch_standard_data,
    calculate_avwap,
    get_bars_1h_count,
)

try:
    from .ws_newcoin import NewCoinWSFeed, test_newcoin_ws
    WS_AVAILABLE = True
except ImportError:
    WS_AVAILABLE = False

__all__ = [
    "quick_newcoin_check",
    "fetch_newcoin_data",
    "fetch_standard_data",
    "calculate_avwap",
    "get_bars_1h_count",
    "NewCoinWSFeed",
    "test_newcoin_ws",
    "WS_AVAILABLE",
]
