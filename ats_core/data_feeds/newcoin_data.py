# coding: utf-8
"""
新币数据获取模块 (Phase 2 - NEWCOIN_SPEC.md § 2)

提供新币专用的数据获取功能：
1. 快速预判（数据获取前判断是否为新币）
2. 多粒度K线获取（1m/5m/15m/1h）
3. AVWAP锚点计算（从listing开始的成交量加权平均价）

符合规范：newstandards/NEWCOIN_SPEC.md § 2
"""

from __future__ import annotations
import time
from typing import Dict, List, Optional, Tuple, Any

from ats_core.sources.binance import _get, get_klines
from ats_core.logging import log, warn


# ============ 阶段0: 快速预判（数据获取前） ============

def quick_newcoin_check(symbol: str) -> Tuple[bool, Optional[int], int]:
    """
    快速判断是否为新币（在数据获取之前）

    Args:
        symbol: 交易对符号（如 "BTCUSDT"）

    Returns:
        Tuple[is_new_coin, listing_time_ms, bars_1h_approx]:
        - is_new_coin: 是否为新币
        - listing_time_ms: 上币时间戳（毫秒），若无法获取则为None
        - bars_1h_approx: 预估的1h K线数量

    规范要求（NEWCOIN_SPEC.md § 1）:
    - 进入条件: bars_1h < 400 或 since_listing < 14d
    """
    try:
        # 获取交易对信息
        exchange_info = _get("/fapi/v1/exchangeInfo", timeout=5.0, retries=1)

        # 查找指定symbol
        symbol_info = None
        for s in exchange_info.get('symbols', []):
            if s.get('symbol') == symbol.upper():
                symbol_info = s
                break

        if not symbol_info:
            warn(f"快速预判: 未找到{symbol}交易对信息，默认为成熟币")
            return False, None, 400

        # 尝试获取上币时间
        # Binance可能在onboardDate字段提供（需验证）
        # 若无，则使用当前时间 - 估算值
        listing_time_ms = symbol_info.get('onboardDate')

        current_time_ms = int(time.time() * 1000)

        # 方法1: 如果有listing_time，直接计算时间差
        if listing_time_ms:
            hours_since_listing = (current_time_ms - listing_time_ms) / (1000 * 3600)
            days_since_listing = hours_since_listing / 24
            bars_1h_approx = int(hours_since_listing)

            is_new = (bars_1h_approx < 400) or (days_since_listing < 14)

            log(f"快速预判 {symbol}: listing={listing_time_ms}, bars_approx={bars_1h_approx}, "
                f"days={days_since_listing:.1f}, is_new={is_new}")

            return is_new, listing_time_ms, bars_1h_approx

        # 方法2: 尝试获取1h K线数量（最快速检测）
        # 获取少量K线快速判断（只要10根，快速失败）
        try:
            sample_klines = get_klines(symbol, "1h", limit=10)
            if sample_klines and len(sample_klines) > 0:
                first_ts = sample_klines[0][0]  # 第一根K线时间戳
                hours_since_first = (current_time_ms - first_ts) / (1000 * 3600)
                bars_1h_approx = int(hours_since_first)

                # 如果bars < 400，大概率是新币
                if bars_1h_approx < 400:
                    log(f"快速预判 {symbol}: 预估bars_1h={bars_1h_approx} < 400，判定为新币")
                    return True, first_ts, bars_1h_approx
        except Exception as e:
            warn(f"快速预判: 获取{symbol} K线失败: {e}")

        # 默认为成熟币（保守策略）
        log(f"快速预判 {symbol}: 无充分信息，默认成熟币")
        return False, None, 400

    except Exception as e:
        warn(f"快速预判: 获取{symbol}交易对信息失败: {e}，默认成熟币")
        return False, None, 400


# ============ 阶段1: 新币数据获取 ============

def fetch_newcoin_data(
    symbol: str,
    listing_time_ms: Optional[int] = None
) -> Dict[str, Any]:
    """
    获取新币专用数据（1m/5m/15m/1h粒度 + AVWAP锚点）

    Args:
        symbol: 交易对符号
        listing_time_ms: 上币时间戳（毫秒），若提供则用于计算精确AVWAP

    Returns:
        Dict包含:
        - k1m: 1分钟K线（List[list]）
        - k5m: 5分钟K线（List[list]）
        - k15m: 15分钟K线（List[list]）
        - k1h: 1小时K线（List[list]）
        - avwap: AVWAP锚点价格（float）
        - avwap_meta: AVWAP元数据（计算方法等）
        - listing_time: 上币时间戳（毫秒）
        - bars_1h: 实际1h K线数量

    规范要求（NEWCOIN_SPEC.md § 2）:
    - REST粒度: 1m/5m/15m/1h
    - 锚点: AVWAP_from_listing（从上币第一分钟开始）
    """
    symbol = symbol.upper()

    log(f"获取新币数据: {symbol}（1m/5m/15m/1h粒度）")

    # 如果没有提供listing_time，尝试快速获取
    if listing_time_ms is None:
        _, listing_time_ms, _ = quick_newcoin_check(symbol)

    # 获取多粒度K线数据
    # 规范: 新币使用1m/5m/15m数据，每个粒度获取足够历史（最多400根）

    # 1h K线: 最多400根（规范阈值）
    k1h = get_klines(symbol, "1h", limit=400)
    bars_1h = len(k1h) if k1h else 0

    # 根据bars_1h计算需要获取的分钟级数据量
    # 如果bars_1h < 24（1天），获取所有1m数据
    # 如果bars_1h < 168（7天），获取最近7天的1m数据
    # 否则获取最近400根（权衡数据量和覆盖范围）

    if bars_1h < 24:  # < 1天
        limit_1m = min(bars_1h * 60, 1500)  # Binance单次最多1500根
        limit_5m = min(bars_1h * 12, 1500)
        limit_15m = min(bars_1h * 4, 1500)
    elif bars_1h < 168:  # < 7天
        limit_1m = min(168 * 60, 1500)  # 最近7天的1m数据
        limit_5m = min(168 * 12, 1500)
        limit_15m = min(168 * 4, 1500)
    else:  # >= 7天，获取固定量
        limit_1m = 1440  # 24小时 = 1440分钟
        limit_5m = 1200  # 约100小时
        limit_15m = 1000  # 约250小时

    # 获取K线数据
    try:
        k1m = get_klines(symbol, "1m", limit=limit_1m)
    except Exception as e:
        warn(f"获取{symbol} 1m K线失败: {e}")
        k1m = []

    try:
        k5m = get_klines(symbol, "5m", limit=limit_5m)
    except Exception as e:
        warn(f"获取{symbol} 5m K线失败: {e}")
        k5m = []

    try:
        k15m = get_klines(symbol, "15m", limit=limit_15m)
    except Exception as e:
        warn(f"获取{symbol} 15m K线失败: {e}")
        k15m = []

    # 计算AVWAP锚点
    avwap, avwap_meta = calculate_avwap(k1m, listing_time_ms)

    log(f"{symbol} 数据获取完成: bars_1h={bars_1h}, "
        f"k1m={len(k1m)}, k5m={len(k5m)}, k15m={len(k15m)}, "
        f"AVWAP={avwap:.2f}")

    return {
        "k1m": k1m,
        "k5m": k5m,
        "k15m": k15m,
        "k1h": k1h,
        "avwap": avwap,
        "avwap_meta": avwap_meta,
        "listing_time": listing_time_ms,
        "bars_1h": bars_1h,
    }


def calculate_avwap(
    k1m: List[list],
    listing_time_ms: Optional[int] = None
) -> Tuple[float, Dict[str, Any]]:
    """
    计算AVWAP（Anchored Volume-Weighted Average Price）

    从上币时间（或首根K线）开始的累积成交量加权平均价

    Args:
        k1m: 1分钟K线数据
        listing_time_ms: 上币时间戳（毫秒），若为None则使用首根K线时间

    Returns:
        Tuple[avwap, metadata]:
        - avwap: AVWAP价格
        - metadata: 计算元数据（锚点时间、K线数量等）

    K线格式:
        [openTime, open, high, low, close, volume, closeTime,
         quoteVolume, trades, takerBuyBaseVolume, takerBuyQuoteVolume, ignore]

    AVWAP计算:
        AVWAP = Σ(price_i * volume_i) / Σ(volume_i)
        其中 price_i = (high + low + close) / 3  (典型价格)
    """
    if not k1m or len(k1m) == 0:
        return 0.0, {"method": "none", "reason": "no_data"}

    # 确定锚点时间
    anchor_time = listing_time_ms if listing_time_ms else k1m[0][0]

    # 过滤出锚点时间之后的K线
    valid_klines = [k for k in k1m if k[0] >= anchor_time]

    if not valid_klines:
        # 如果没有有效K线，使用最近一根的收盘价
        last_close = float(k1m[-1][4])
        return last_close, {
            "method": "fallback_last_close",
            "anchor_time": anchor_time,
            "reason": "no_klines_after_anchor"
        }

    # 计算AVWAP
    total_pv = 0.0  # price * volume
    total_v = 0.0   # volume

    for kline in valid_klines:
        high = float(kline[2])
        low = float(kline[3])
        close = float(kline[4])
        volume = float(kline[5])

        # 典型价格: (H+L+C)/3
        typical_price = (high + low + close) / 3.0

        total_pv += typical_price * volume
        total_v += volume

    if total_v == 0:
        # 成交量为0（极少见），使用最后收盘价
        last_close = float(valid_klines[-1][4])
        return last_close, {
            "method": "fallback_zero_volume",
            "anchor_time": anchor_time,
            "klines": len(valid_klines)
        }

    avwap = total_pv / total_v

    return avwap, {
        "method": "avwap_typical_price",
        "anchor_time": anchor_time,
        "klines": len(valid_klines),
        "total_volume": total_v,
    }


# ============ 阶段2: 成熟币数据获取（保持兼容） ============

def fetch_standard_data(symbol: str) -> Dict[str, Any]:
    """
    获取成熟币标准数据（1h/4h粒度）

    保持与现有analyze_symbol.py兼容的数据格式

    Returns:
        Dict包含:
        - k1h: 1小时K线
        - k4h: 4小时K线
        - bars_1h: 1h K线数量
    """
    symbol = symbol.upper()

    log(f"获取成熟币数据: {symbol}（1h/4h粒度）")

    k1h = get_klines(symbol, "1h", limit=300)
    k4h = get_klines(symbol, "4h", limit=200)

    return {
        "k1h": k1h,
        "k4h": k4h,
        "bars_1h": len(k1h) if k1h else 0,
    }


# ============ 工具函数 ============

def get_bars_1h_count(symbol: str) -> int:
    """
    快速获取1h K线数量（用于预判）

    只获取10根K线样本，通过时间戳差计算总数
    """
    try:
        sample = get_klines(symbol, "1h", limit=10)
        if not sample or len(sample) < 2:
            return 0

        first_ts = sample[0][0]
        current_ts = int(time.time() * 1000)
        hours_diff = (current_ts - first_ts) / (1000 * 3600)

        return int(hours_diff)
    except Exception as e:
        warn(f"快速计算{symbol} bars_1h失败: {e}")
        return 0
