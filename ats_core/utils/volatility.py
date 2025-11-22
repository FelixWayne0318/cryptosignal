"""
波动率计算工具模块

提供ATR等波动率相关的公共计算函数，避免代码重复。

Functions:
    - calculate_simple_atr(): 计算简单ATR (Average True Range)

Author: Claude Code
Version: v7.6.1
Created: 2025-11-21
"""

from typing import List, Dict, Any


def calculate_simple_atr(klines: List[Dict[str, Any]], period: int = 14) -> float:
    """
    计算简单ATR (Average True Range)

    ATR是衡量市场波动性的重要指标，用于：
    - Step2 TrendStage: 计算move_atr（累积ATR距离）
    - Step3 Risk: 计算止损距离

    Args:
        klines: K线数据列表，每个元素需包含 high, low, close 字段
        period: ATR周期（默认14）

    Returns:
        float: ATR值（如果数据不足返回0.0）

    Example:
        >>> klines = [{"high": 100, "low": 95, "close": 98}, ...]
        >>> atr = calculate_simple_atr(klines, period=14)
        >>> print(f"ATR = {atr:.2f}")
    """
    if len(klines) < period + 1:
        return 0.0

    trs = []
    for i in range(-period, 0):
        # 使用 .get() 方法安全获取数据，支持字典和类字典对象
        high = float(klines[i].get("high", 0) if hasattr(klines[i], 'get') else klines[i]["high"])
        low = float(klines[i].get("low", 0) if hasattr(klines[i], 'get') else klines[i]["low"])
        prev_close = float(klines[i-1].get("close", 0) if hasattr(klines[i-1], 'get') else klines[i-1]["close"])

        # True Range = max(H-L, |H-Prev_C|, |L-Prev_C|)
        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
        trs.append(tr)

    return sum(trs) / len(trs) if trs else 0.0
