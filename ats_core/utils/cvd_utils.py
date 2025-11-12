# coding: utf-8
"""
CVD工具函数模块

v7.2.34新增：沉淀CVD计算的通用工具函数
- align_klines_by_open_time: K线时间对齐（inner join）
- rolling_z: 滚动窗口Z-score标准化（无前视偏差）
- compute_cvd_delta: 计算CVD增量序列

v7.2.35增强：CVD专家复核修复
- _diff: 一阶差分计算（修复CVD增量bug）
- align_oi_to_klines: OI数据对齐到K线（修复OI对齐缺失）
- compute_dynamic_min_quote: 动态最小成交额阈值（小币友好）
- align_klines_by_open_time: 增加断言和自动降级
- compute_cvd_delta: 增加列数校验
"""

from typing import List, Tuple, Dict, Sequence
import math
from ats_core.logging import warn, error


def _diff(values: List[float]) -> List[float]:
    """
    计算一阶差分（ΔV = V[i] - V[i-1]）

    Args:
        values: 数值序列（如CVD累计量）

    Returns:
        差分序列（第一个元素为0）

    说明:
        - v7.2.35新增：修复CVD增量计算bug
        - 对于累计量（如CVD），应该使用diff而不是pct_change
        - pct_change在累计量接近0时会爆炸，且对负数没有意义
        - diff保持线性关系，适合后续Z标准化

    Example:
        >>> cvd = [100, 150, 120, 180]  # CVD累计量
        >>> delta_cvd = _diff(cvd)
        >>> # delta_cvd = [0, 50, -30, 60]
    """
    if not values:
        return []

    result = [0.0]  # 第一个点差分为0
    for i in range(1, len(values)):
        result.append(values[i] - values[i-1])

    return result


def align_oi_to_klines(
    oi_hist: Sequence[dict],
    klines: Sequence[Sequence]
) -> List[float]:
    """
    按closeTime对齐OI数据到K线

    Args:
        oi_hist: 持仓量历史数据 [{"timestamp": ms, "sumOpenInterest": value}, ...]
        klines: K线数据（Binance格式，12列）

    Returns:
        对齐后的OI值序列（与klines长度一致）

    说明:
        - v7.2.35新增：修复OI对齐缺失问题
        - OI数据的timestamp应该匹配K线的closeTime（第6列）
        - 使用inner join：只保留时间匹配的数据
        - 未匹配的K线OI值填充0（表示无数据）

    Example:
        >>> oi_hist = [
        ...     {"timestamp": 1700003599999, "sumOpenInterest": 10000},
        ...     {"timestamp": 1700007199999, "sumOpenInterest": 10500}
        ... ]
        >>> klines = [
        ...     [1700000000000, ..., 1700003599999, ...],  # closeTime: 1700003599999
        ...     [1700003600000, ..., 1700007199999, ...]   # closeTime: 1700007199999
        ... ]
        >>> oi_vals = align_oi_to_klines(oi_hist, klines)
        >>> # oi_vals = [10000, 10500]
    """
    if not klines:
        return []

    # 构建K线closeTime映射 (closeTime -> index)
    kline_close_times = {int(k[6]): i for i, k in enumerate(klines)}

    # 初始化结果（默认0）
    result = [0.0] * len(klines)

    # 对齐OI数据
    if isinstance(oi_hist, (list, tuple)):
        for oi_entry in oi_hist:
            if not isinstance(oi_entry, dict):
                continue

            ts = oi_entry.get("timestamp", 0)
            oi_value = oi_entry.get("sumOpenInterest") or \
                       oi_entry.get("sumOpenInterestValue") or \
                       oi_entry.get("openInterest") or 0.0

            # 查找对应的K线索引
            if ts in kline_close_times:
                idx = kline_close_times[ts]
                try:
                    result[idx] = float(oi_value)
                except (ValueError, TypeError):
                    result[idx] = 0.0

    return result


def compute_dynamic_min_quote(
    klines: Sequence[Sequence],
    window: int = 96,
    factor: float = 0.05,
    min_fallback: float = 10000
) -> float:
    """
    计算动态最小成交额阈值

    Args:
        klines: K线数据（Binance格式）
        window: 滚动窗口（96根1h K线 = 4天）
        factor: 系数（默认0.05 = 5%的中位数）
        min_fallback: 最小回退值（10k USDT）

    Returns:
        动态阈值（USDT）

    说明:
        - v7.2.35新增：小币友好的动态阈值
        - 基于最近N根K线的成交额中位数计算阈值
        - 动态阈值 = factor × median(成交额)
        - 不低于最小回退值（防止过低）

    Example:
        >>> # 大币（BTC）: 成交额中位数 10M USDT
        >>> # 动态阈值 = 0.05 × 10M = 500k USDT
        >>> # 小币（YFI）: 成交额中位数 50k USDT
        >>> # 动态阈值 = 0.05 × 50k = 2.5k USDT（使用回退值10k）
    """
    if not klines or len(klines) < 2:
        return min_fallback

    def _to_f(v):
        try:
            return float(v)
        except (ValueError, TypeError):
            return 0.0

    # 提取最近N根K线的成交额（第7列：quoteAssetVolume）
    recent_klines = klines[-window:] if len(klines) > window else klines
    quote_volumes = [_to_f(k[7]) for k in recent_klines]

    # 计算中位数
    sorted_vols = sorted(quote_volumes)
    median_vol = sorted_vols[len(sorted_vols) // 2]

    # 动态阈值 = factor × median
    dynamic_threshold = factor * median_vol

    # 不低于最小回退值
    return max(dynamic_threshold, min_fallback)


def align_klines_by_open_time(
    futures_klines: Sequence[Sequence],
    spot_klines: Sequence[Sequence],
    max_discard_ratio: float = 0.05
) -> Tuple[List[List], List[List], int, bool]:
    """
    基于openTime对齐现货和合约K线（inner join）

    Args:
        futures_klines: 合约K线数据（每根K线的第0列为openTime）
        spot_klines: 现货K线数据（每根K线的第0列为openTime）
        max_discard_ratio: 最大丢弃比例（默认5%），超过则降级

    Returns:
        (aligned_futures, aligned_spot, discarded_count, is_degraded)
        - aligned_futures: 对齐后的合约K线
        - aligned_spot: 对齐后的现货K线
        - discarded_count: 丢弃的K线数量
        - is_degraded: True表示丢弃率过高，建议降级为单侧CVD

    说明:
        - 使用inner join：只保留两边都有的时间戳
        - 返回按时间升序排列的K线
        - v7.2.35增强：添加断言和自动降级逻辑
        - 断言1：openTime严格递增
        - 断言2：两侧长度一致
        - 超过丢弃率阈值时，建议降级为单侧CVD

    Example:
        >>> futures = [[1700000000000, ...], [1700003600000, ...]]  # 00:00, 01:00
        >>> spot = [[1700003600000, ...], [1700007200000, ...]]     # 01:00, 02:00
        >>> aligned_f, aligned_s, discarded, is_degraded = align_klines_by_open_time(
        ...     futures, spot, max_discard_ratio=0.05
        ... )
        >>> len(aligned_f)  # 1 (只有01:00时刻的K线匹配)
        1
        >>> discarded  # 2 (00:00的合约K线 + 02:00的现货K线)
        2
        >>> is_degraded  # True if discard_ratio > 5%
    """
    if not futures_klines or not spot_klines:
        return [], [], 0, False

    # 提取openTime（第0列）-> K线映射
    f_times = {int(k[0]): list(k) for k in futures_klines}
    s_times = {int(k[0]): list(k) for k in spot_klines}

    # Inner join：只保留两边都有的时间戳
    common_times = sorted(set(f_times.keys()) & set(s_times.keys()))

    if not common_times:
        # 完全没有交集
        warn("⚠️  现货/合约K线时间完全不匹配，无法组合CVD")
        total = len(futures_klines) + len(spot_klines)
        return [], [], total, True

    # v7.2.35: 断言1 - openTime严格递增
    for i in range(1, len(common_times)):
        if common_times[i] <= common_times[i-1]:
            error(f"❌ openTime不单调递增: {common_times[i-1]} >= {common_times[i]}")
            raise ValueError(f"openTime不单调递增: {common_times[i-1]} >= {common_times[i]}")

    # 按时间升序对齐
    aligned_f = [f_times[t] for t in common_times]
    aligned_s = [s_times[t] for t in common_times]

    # v7.2.35: 断言2 - 两侧长度一致
    if len(aligned_f) != len(aligned_s):
        error(f"❌ 对齐后长度不一致: futures={len(aligned_f)}, spot={len(aligned_s)}")
        raise ValueError(f"对齐后长度不一致: futures={len(aligned_f)}, spot={len(aligned_s)}")

    # 计算丢弃的K线数和丢弃率
    discarded = len(futures_klines) + len(spot_klines) - 2 * len(common_times)
    total = len(futures_klines) + len(spot_klines)
    discard_ratio = discarded / total if total > 0 else 0

    # v7.2.35: 检查是否需要降级
    is_degraded = False
    if discard_ratio > max_discard_ratio:
        error(f"❌ K线对齐丢弃率过高 {discard_ratio:.2%} > {max_discard_ratio:.2%}，建议降级为单侧CVD")
        is_degraded = True
    elif discarded > 0:
        warn(f"⚠️  K线对齐丢弃{discarded}根（{discard_ratio:.2%}）")

    return aligned_f, aligned_s, discarded, is_degraded


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
        >>> # z[1] = (2.0 - mean([1.0, 2.0])) / std([1.0, 2.0])
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
    use_quote: bool = True,
    symbol: str = "UNKNOWN",
    interval: str = "1h"
) -> List[float]:
    """
    计算CVD增量序列（ΔC）

    Args:
        klines: K线数据（Binance格式，12列）
        use_quote: True=使用Quote CVD（USDT），False=使用Base CVD（币数量）
        symbol: 交易对名称（用于错误提示）
        interval: K线周期（用于错误提示）

    Returns:
        CVD增量序列 [delta_0, delta_1, ..., delta_n]

    Raises:
        ValueError: K线格式不正确时抛出

    说明:
        - Quote CVD: delta = 2 * takerBuyQuoteVolume - quoteAssetVolume
          * takerBuyQuoteVolume: 主动买入成交额（USDT）
          * quoteAssetVolume: 总成交额（USDT）
        - Base CVD: delta = 2 * takerBuyBaseVolume - volume
          * takerBuyBaseVolume: 主动买入量（币数量）
          * volume: 总成交量（币数量）
        - v7.2.35增强：添加列数校验（防御性编程）

    Example:
        >>> klines = [
        ...     [timestamp, open, high, low, close, volume, closeTime,
        ...      quoteVolume, trades, takerBuyBase, takerBuyQuote, ignore]
        ... ]
        >>> deltas = compute_cvd_delta(klines, use_quote=True, symbol="BTCUSDT")
        >>> # deltas[i] = 2*takerBuyQuote[i] - quoteVolume[i]
    """
    # v7.2.35: 防御性检查1 - K线数据不能为空
    if not klines:
        raise ValueError(f"K线数据为空 (symbol={symbol}, interval={interval})")

    # v7.2.35: 防御性检查2 - K线必须至少11列（Binance标准格式12列，索引0-11）
    if len(klines[0]) < 11:
        raise ValueError(
            f"K线格式错误: 期望至少11列，实际{len(klines[0])}列 "
            f"(symbol={symbol}, interval={interval})"
        )

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
    '_diff',
    'align_klines_by_open_time',
    'align_oi_to_klines',
    'rolling_z',
    'compute_cvd_delta',
    'compute_dynamic_min_quote',
]
