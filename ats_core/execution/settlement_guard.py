#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结算窗口保护模块

功能：
- 资金费结算前后±5分钟不开新仓
- 避免"窗边被打"（结算时刻流动性骤变/滑点激增）

规范：
- 借鉴外部方案 settlement_guard 概念
- 符合风险控制最佳实践

使用：
    from ats_core.execution.settlement_guard import is_near_settlement

    if is_near_settlement(int(time.time())):
        log("⚠️  接近资金费结算窗口，跳过开仓")
        continue
"""
from __future__ import annotations
import time
from typing import Optional

# Binance 永续合约资金费率结算间隔（8小时 = 28800秒）
FUNDING_INTERVAL_SECONDS = 8 * 3600  # 28800

# 结算窗口保护时间（±5分钟 = 300秒）
SETTLEMENT_GUARD_WINDOW = 5 * 60  # 300


def is_near_settlement(
    now_ts: Optional[int] = None,
    funding_interval: int = FUNDING_INTERVAL_SECONDS,
    guard_window: int = SETTLEMENT_GUARD_WINDOW
) -> bool:
    """
    判断是否接近资金费结算时间窗口

    Args:
        now_ts: 当前时间戳（秒），None则使用当前时间
        funding_interval: 资金费结算间隔（秒），默认8小时
        guard_window: 保护窗口宽度（秒），默认5分钟

    Returns:
        True: 在结算窗口内（前后±5min），不应开新仓
        False: 在安全时段，可以开仓

    示例：
        # Binance 资金费结算时间: 00:00, 08:00, 16:00 UTC
        # 07:55 - 08:05 UTC: 返回 True（不开仓）
        # 08:10 UTC: 返回 False（可以开仓）
    """
    if now_ts is None:
        now_ts = int(time.time())

    # 计算距离上次结算的秒数
    seconds_since_last = now_ts % funding_interval

    # 计算距离下次结算的秒数
    seconds_to_next = funding_interval - seconds_since_last

    # 判断是否在结算窗口内
    # 1. 距离下次结算 ≤ guard_window（即将结算）
    # 2. 距离上次结算 ≤ guard_window（刚结算完）
    near_next = seconds_to_next <= guard_window
    near_last = seconds_since_last <= guard_window

    return near_next or near_last


def get_next_settlement_time(
    now_ts: Optional[int] = None,
    funding_interval: int = FUNDING_INTERVAL_SECONDS
) -> int:
    """
    获取下一次资金费结算时间戳

    Args:
        now_ts: 当前时间戳（秒），None则使用当前时间
        funding_interval: 资金费结算间隔（秒）

    Returns:
        下一次结算时间戳（秒）
    """
    if now_ts is None:
        now_ts = int(time.time())

    seconds_since_last = now_ts % funding_interval
    seconds_to_next = funding_interval - seconds_since_last

    return now_ts + seconds_to_next


def get_time_to_safe_zone(
    now_ts: Optional[int] = None,
    funding_interval: int = FUNDING_INTERVAL_SECONDS,
    guard_window: int = SETTLEMENT_GUARD_WINDOW
) -> int:
    """
    获取距离安全区域的剩余时间

    Args:
        now_ts: 当前时间戳（秒）
        funding_interval: 资金费结算间隔（秒）
        guard_window: 保护窗口宽度（秒）

    Returns:
        距离安全区域的秒数（0表示已在安全区域）
    """
    if now_ts is None:
        now_ts = int(time.time())

    if not is_near_settlement(now_ts, funding_interval, guard_window):
        return 0  # 已在安全区域

    seconds_since_last = now_ts % funding_interval
    seconds_to_next = funding_interval - seconds_since_last

    # 如果接近下次结算，等待到结算后 guard_window
    if seconds_to_next <= guard_window:
        return seconds_to_next + guard_window

    # 如果刚结算完，等待到 guard_window 结束
    if seconds_since_last <= guard_window:
        return guard_window - seconds_since_last

    return 0


def format_settlement_info(
    now_ts: Optional[int] = None,
    funding_interval: int = FUNDING_INTERVAL_SECONDS,
    guard_window: int = SETTLEMENT_GUARD_WINDOW
) -> str:
    """
    格式化结算窗口信息（用于日志）

    Returns:
        格式化的信息字符串
    """
    if now_ts is None:
        now_ts = int(time.time())

    near = is_near_settlement(now_ts, funding_interval, guard_window)
    next_settlement = get_next_settlement_time(now_ts, funding_interval)
    time_to_safe = get_time_to_safe_zone(now_ts, funding_interval, guard_window)

    from datetime import datetime
    next_time_str = datetime.utcfromtimestamp(next_settlement).strftime('%H:%M:%S UTC')

    if near:
        return f"⚠️  结算窗口内，{time_to_safe}秒后进入安全区（下次结算: {next_time_str}）"
    else:
        seconds_to_next = next_settlement - now_ts
        minutes_to_next = seconds_to_next // 60
        return f"✅ 安全区域，距下次结算 {minutes_to_next} 分钟（{next_time_str}）"


# 便捷函数：用于现有代码快速集成
def should_skip_trading() -> tuple[bool, str]:
    """
    判断是否应该跳过交易（结算窗口保护）

    Returns:
        (should_skip, reason):
            - should_skip: True表示应该跳过
            - reason: 跳过原因（用于日志）
    """
    if is_near_settlement():
        reason = format_settlement_info()
        return True, reason
    return False, ""
