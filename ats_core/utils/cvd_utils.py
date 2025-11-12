# coding: utf-8
"""
CVD工具函数模块

v7.2.34新增：沉淀CVD计算的通用工具函数
- align_klines_by_open_time: K线时间对齐（inner join）
- rolling_z: 滚动窗口Z-score标准化（无前视偏差）
- compute_cvd_delta: 计算CVD增量序列
"""

from typing import List, Tuple, Dict, Sequence
import math
from ats_core.logging import warn


def align_klines_by_open_time(
    futures_klines: Sequence[Sequence],
    spot_klines: Sequence[Sequence]
) -> Tuple[List[List], List[List], int]:
    """
    基于openTime对齐现货和合约K线（inner join）

    Args:
        futures_klines: 合约K线数据（每根K线的第0列为openTime）
        spot_klines: 现货K线数据（每根K线的第0列为openTime）

    Returns:
        (aligned_futures, aligned_spot, discarded_count)
        - aligned_futures: 对齐后的合约K线
        - aligned_spot: 对齐后的现货K线
        - discarded_count: 丢弃的K线数量

    说明:
        - 使用inner join：只保留两边都有的时间戳
        - 返回按时间升序排列的K线
        - 如果现货/合约K线时间不同步，会丢弃不匹配的K线

    Example:
        >>> futures = [[1700000000000, ...], [1700003600000, ...]]  # 00:00, 01:00
        >>> spot = [[1700003600000, ...], [1700007200000, ...]]     # 01:00, 02:00
        >>> aligned_f, aligned_s, discarded = align_klines_by_open_time(futures, spot)
        >>> len(aligned_f)  # 1 (只有01:00时刻的K线匹配)
        1
        >>> discarded  # 2 (00:00的合约K线 + 02:00的现货K线)
        2
    """
    if not futures_klines or not spot_klines:
        return [], [], 0

    # 提取openTime（第0列）-> K线映射
    f_times = {int(k[0]): list(k) for k in futures_klines}
    s_times = {int(k[0]): list(k) for k in spot_klines}

    # Inner join：只保留两边都有的时间戳
    common_times = sorted(set(f_times.keys()) & set(s_times.keys()))

    if not common_times:
        # 完全没有交集
        warn("⚠️  现货/合约K线时间完全不匹配，无法组合CVD")
        total = len(futures_klines) + len(spot_klines)
        return [], [], total

    # 按时间升序对齐
    aligned_f = [f_times[t] for t in common_times]
    aligned_s = [s_times[t] for t in common_times]

    # 计算丢弃的K线数
    discarded = len(futures_klines) + len(spot_klines) - 2 * len(common_times)

    return aligned_f, aligned_s, discarded


def rolling_z(
    values: List[float],
    window: int = 96,
    robust: bool = True
) -> List[float]:
    """
    滚动窗口Z-score标准化（无前视偏差）

    Args:
        values: 数值序列（如CVD增量、价格收益、OI变化）
        window: 滚动窗口大小（96根1h K线 = 4天）
        robust: 是否使用稳健统计（MAD代替std，抗异常值）

    Returns:
        Z-score序列

    说明:
        - 只使用历史数据（i-window+1 到 i），避免前视偏差
        - robust=True时使用MAD（Median Absolute Deviation），对异常值更稳健
        - robust=False时使用标准差（传统方法）
        - 当窗口内数据不足或std=0时，返回0.0

    Example:
        >>> data = [1.0, 2.0, 1.5, 3.0, 2.5]
        >>> z = rolling_z(data, window=3, robust=False)
        >>> # z[0] = 0 (窗口不足)
        >>> # z[1] = 0 (窗口不足)
        >>> # z[2] = (1.5 - mean([1.0, 2.0, 1.5])) / std([1.0, 2.0, 1.5])
    """
    if not values:
        return []

    result = []
    for i in range(len(values)):
        # 只使用历史数据（i-window+1 到 i）
        start = max(0, i - window + 1)
        window_data = values[start:i+1]

        if len(window_data) < 2:
            # 窗口数据不足，无法计算标准差
            result.append(0.0)
            continue

        mean_val = sum(window_data) / len(window_data)

        if robust:
            # 稳健方法：使用MAD（Median Absolute Deviation）
            # MAD = median(|x_i - median(x)|)
            median_val = sorted(window_data)[len(window_data) // 2]
            abs_deviations = [abs(x - median_val) for x in window_data]
            mad = sorted(abs_deviations)[len(abs_deviations) // 2]
            # MAD to std conversion factor: 1.4826
            scale = mad * 1.4826 if mad > 0 else 0.0
        else:
            # 传统方法：使用标准差
            variance = sum((x - mean_val) ** 2 for x in window_data) / (len(window_data) - 1)
            scale = math.sqrt(variance) if variance > 0 else 0.0

        if scale == 0:
            # 窗口内所有值相同，无法标准化
            result.append(0.0)
        else:
            result.append((values[i] - mean_val) / scale)

    return result


def compute_cvd_delta(
    klines: Sequence[Sequence],
    use_quote: bool = True
) -> List[float]:
    """
    计算CVD增量序列（ΔC）

    Args:
        klines: K线数据（Binance格式，12列）
        use_quote: True=使用Quote CVD（USDT），False=使用Base CVD（币数量）

    Returns:
        CVD增量序列 [delta_0, delta_1, ..., delta_n]

    说明:
        - Quote CVD: delta = 2 * takerBuyQuoteVolume - quoteAssetVolume
          * takerBuyQuoteVolume: 主动买入成交额（USDT）
          * quoteAssetVolume: 总成交额（USDT）
        - Base CVD: delta = 2 * takerBuyBaseVolume - volume
          * takerBuyBaseVolume: 主动买入量（币数量）
          * volume: 总成交量（币数量）

    Example:
        >>> klines = [
        ...     [timestamp, open, high, low, close, volume, closeTime,
        ...      quoteVolume, trades, takerBuyBase, takerBuyQuote, ignore]
        ... ]
        >>> deltas = compute_cvd_delta(klines, use_quote=True)
        >>> # deltas[i] = 2*takerBuyQuote[i] - quoteVolume[i]
    """
    if not klines:
        return []

    def _to_f(v):
        try:
            return float(v)
        except (ValueError, TypeError):
            return 0.0

    if use_quote:
        # Quote CVD（USDT单位）
        # K线第10列：takerBuyQuoteVolume（主动买入成交额）
        # K线第7列：quoteAssetVolume（总成交额）
        taker_buy_quote = [_to_f(k[10]) for k in klines]
        quote_volume = [_to_f(k[7]) for k in klines]
        deltas = [2.0 * buy - total for buy, total in zip(taker_buy_quote, quote_volume)]
    else:
        # Base CVD（币数量单位）
        # K线第9列：takerBuyBaseVolume（主动买入量）
        # K线第5列：volume（总成交量）
        taker_buy_base = [_to_f(k[9]) for k in klines]
        total_volume = [_to_f(k[5]) for k in klines]
        deltas = [2.0 * buy - total for buy, total in zip(taker_buy_base, total_volume)]

    return deltas


__all__ = [
    'align_klines_by_open_time',
    'rolling_z',
    'compute_cvd_delta',
]
