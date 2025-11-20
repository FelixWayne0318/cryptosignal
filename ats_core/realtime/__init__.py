# coding: utf-8
"""
Realtime Module - 实时交易组件

包含：
- DataFeed: Binance WebSocket数据接入
- StateManager: 状态持久化和恢复
- PaperTrader: Paper Trading控制器

Version: v1.0.0
Standard: SYSTEM_ENHANCEMENT_STANDARD.md v3.3.0
"""

from ats_core.realtime.data_feed import DataFeed, MockDataFeed
from ats_core.realtime.state_manager import StateManager
from ats_core.realtime.paper_trader import PaperTrader, run_paper_trader

__all__ = [
    "DataFeed",
    "MockDataFeed",
    "StateManager",
    "PaperTrader",
    "run_paper_trader",
]

__version__ = "1.0.0"
