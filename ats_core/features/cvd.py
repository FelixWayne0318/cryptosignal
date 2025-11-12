# coding: utf-8
from __future__ import annotations
from typing import List, Sequence, Tuple, Optional
import math
from ats_core.utils.outlier_detection import detect_volume_outliers, apply_outlier_weights

def _to_f(x) -> float:
    try:
        return float(x)
    except Exception:
        return float('nan')

def _col(kl: Sequence[Sequence], idx: int) -> List[float]:
    return [_to_f(r[idx]) for r in kl if isinstance(r, (list, tuple)) and len(r) > idx]

def _pct_change(arr: Sequence[float]) -> List[float]:
    out: List[float] = []
    prev = None
    for x in arr:
        x = _to_f(x)
        if not math.isfinite(x) or prev is None or prev == 0:
            out.append(0.0)
        else:
            out.append((x - prev) / prev)
        prev = x
    return out

def _z_all(a: Sequence[float]) -> List[float]:
    xs = [float(x) for x in a if isinstance(x, (int, float)) and math.isfinite(x)]
    if not xs:
        return [0.0] * len(a)
    m = sum(xs) / len(xs)
    var = sum((x - m) ** 2 for x in xs) / max(1, len(xs) - 1)
    std = math.sqrt(var) if var > 0 else 0.0
    if std == 0:
        return [0.0] * len(a)
    return [((float(v) - m) / std) if isinstance(v, (int, float)) and math.isfinite(v) else 0.0 for v in a]

def _close_prices(kl: Sequence[Sequence]) -> List[float]:
    # Binance futures klines: [0] openTime, [1] open, [2] high, [3] low, [4] close, [5] volume, ...
    return _col(kl, 4)

def cvd_from_klines(
    klines: Sequence[Sequence],
    use_taker_buy: bool = True,
    use_quote: bool = True,
    filter_outliers: bool = True,
    outlier_weight: float = 0.5
) -> List[float]:
    """
    计算CVD (Cumulative Volume Delta)

    Args:
        klines: Binance 期货 klines（12列）
            Quote CVD（use_quote=True）:
                [10]: takerBuyQuoteVolume（主动买入成交额，USDT）
                [7]: quoteAssetVolume（总成交额，USDT）
            Base CVD（use_quote=False）:
                [9]: takerBuyBaseVolume（主动买入量，币数量）
                [5]: volume（总成交量，币数量）
        use_taker_buy: 是否使用真实的taker buy volume
                      True: 使用真实数据（推荐）
                      False: 使用tick rule估算（兼容旧版）
        use_quote: 是否使用Quote CVD（v7.2.34新增）
                  True: 使用USDT单位（推荐，不受币价波动影响）
                  False: 使用币数量单位（兼容旧版）
        filter_outliers: 是否过滤异常值（巨量K线）
                        True: 对异常值降权（推荐）
                        False: 不处理异常值
        outlier_weight: 异常值权重（0-1），默认0.5表示降低50%

    Returns:
        CVD序列：Σ(买入量 - 卖出量)

    改进（v2.2）:
        - v7.2.34: 新增Quote CVD支持（USDT单位，更准确反映资金流）
        - v2.1: 添加IQR异常值检测
        - v2.1: 对巨量K线降权，避免被单笔大额交易误导
    """
    if use_taker_buy and klines and len(klines[0]) >= 11:
        # v7.2.34: 优化方法，支持Quote CVD和Base CVD
        if use_quote:
            # Quote CVD（USDT单位）- 更准确，不受币价波动影响
            taker_buy = _col(klines, 10)  # takerBuyQuoteVolume（主动买入成交额）
            total_vol = _col(klines, 7)   # quoteAssetVolume（总成交额）
        else:
            # Base CVD（币数量单位）- 兼容旧版
            taker_buy = _col(klines, 9)   # takerBuyBaseVolume（主动买入量）
            total_vol = _col(klines, 5)   # volume（总成交量）

        n = min(len(taker_buy), len(total_vol))

        # ========== 异常值检测（新增） ==========
        deltas: List[float] = []
        for i in range(n):
            buy = taker_buy[i]
            total = total_vol[i]
            if not (math.isfinite(buy) and math.isfinite(total)):
                deltas.append(0.0)
            else:
                delta = 2.0 * buy - total
                deltas.append(delta)

        # 检测成交量异常值
        if filter_outliers and n >= 20:
            outlier_mask = detect_volume_outliers(total_vol, deltas, multiplier=1.5)
            # 对异常值降权
            deltas = apply_outlier_weights(deltas, outlier_mask, outlier_weight)

        # 累积CVD
        s = 0.0
        cvd: List[float] = []
        for delta in deltas:
            s += delta
            cvd.append(s)

        return cvd
    else:
        # ⚠️ DEPRECATED: 旧方法Tick Rule估算（不准确，仅保留兼容性）
        # v7.2.32警告：此方法使用"阳线=买盘、阴线=卖盘"判断，会系统性误判！
        #
        # 问题：阳线（close>=open）≠买盘，阴线≠卖盘
        # 例如：主动买盘推高后回落形成阴线，但前期都是买盘
        #
        # 解决方案：确保K线数据包含takerBuyVolume（第9列），设置use_taker_buy=True
        #
        # 此分支将在未来版本中移除！
        import warnings
        warnings.warn(
            "CVD计算正在使用不准确的Tick Rule估算（阳线=买盘、阴线=卖盘）！"
            "\n这会导致系统性误判资金流向。"
            "\n请确保K线数据包含takerBuyVolume（第9列），并使用use_taker_buy=True。"
            "\n此方法将在未来版本中移除。",
            DeprecationWarning,
            stacklevel=2
        )
        o = _col(klines, 1)
        c = _col(klines, 4)
        v = _col(klines, 5)
        n = min(len(o), len(c), len(v))
        s = 0.0
        cvd: List[float] = []
        for i in range(n):
            oi, ci, vi = o[i], c[i], v[i]
            if not (math.isfinite(oi) and math.isfinite(ci) and math.isfinite(vi)):
                cvd.append(s)
                continue
            sign = 1.0 if ci >= oi else -1.0  # ⚠️ 错误：阳线≠买盘
            s += sign * vi
            cvd.append(s)
        return cvd

def zscore_last(xs: Sequence[float], window: int = 20) -> float:
    if not xs:
        return 0.0
    w = xs[-window:] if len(xs) >= window else list(xs)
    w = [float(x) for x in w if isinstance(x, (int, float)) and math.isfinite(x)]
    if len(w) < 2:
        return 0.0
    mean = sum(w) / len(w)
    var = sum((x - mean) ** 2 for x in w) / max(1, len(w) - 1)
    std = math.sqrt(var) if var > 0 else 0.0
    if std == 0:
        return 0.0
    return (w[-1] - mean) / std

def cvd_from_spot_klines(klines: Sequence[Sequence], use_quote: bool = True) -> List[float]:
    """
    计算现货CVD (使用真实taker buy volume)

    Args:
        klines: Binance 现货 klines（12列）
            Quote CVD（use_quote=True）:
                [10]: takerBuyQuoteVolume（主动买入成交额，USDT）
                [7]: quoteAssetVolume（总成交额，USDT）
            Base CVD（use_quote=False）:
                [9]: takerBuyBaseVolume（主动买入量，币数量）
                [5]: volume（总成交量，币数量）
        use_quote: 是否使用Quote CVD（v7.2.34新增）
                  True: 使用USDT单位（推荐）
                  False: 使用币数量单位（兼容旧版）

    Returns:
        现货CVD序列
    """
    # 现货数据格式与合约相同，直接调用
    return cvd_from_klines(klines, use_taker_buy=True, use_quote=use_quote)


def cvd_combined(
    futures_klines: Sequence[Sequence],
    spot_klines: Sequence[Sequence] = None,
    use_dynamic_weight: bool = True,
    use_quote: bool = True,
    min_total_quote: float = 100000,
    max_discard_ratio: float = 0.001
) -> List[float]:
    """
    组合现货+合约CVD（v7.2.34增强版）

    Args:
        futures_klines: 合约K线数据
        spot_klines: 现货K线数据（可选）
        use_dynamic_weight: 是否使用动态权重（按成交额比例）
                          True: 根据实际成交额动态计算权重（推荐）
                          False: 使用固定权重（70%合约 + 30%现货）
        use_quote: 是否使用Quote CVD（USDT单位）
                  True: 使用USDT单位（推荐）
                  False: 使用币数量单位（兼容旧版）
        min_total_quote: 最小成交额阈值（USDT），低于此值的K线降权或跳过
                        默认100000（10万USDT）
        max_discard_ratio: K线对齐最大丢弃比例（0.001 = 0.1%）
                          超过此值发出警告

    Returns:
        组合后的CVD序列

    改进（v7.2.34）：
        - P1-1: openTime对齐检查（防止现货/合约K线错位）
        - P2-4: 缺失/极值容错（成交额过小时处理）
        - P2-3: Quote CVD支持（USDT单位）

    说明：
        - 动态权重：根据合约和现货的实际成交额（USDT）比例计算权重
        - 这样能真实反映不同市场的资金流向权重
        - 例如：某币合约日成交10亿，现货1亿 → 权重自动为 90.9% : 9.1%
    """
    # 导入工具函数
    from ats_core.utils.cvd_utils import align_klines_by_open_time
    from ats_core.logging import warn

    # 计算合约CVD
    cvd_f = cvd_from_klines(futures_klines, use_taker_buy=True, use_quote=use_quote)

    if spot_klines is None or len(spot_klines) == 0:
        # 如果没有现货数据，只返回合约CVD
        return cvd_f

    # v7.2.34: P1-1 - openTime对齐检查
    aligned_f, aligned_s, discarded = align_klines_by_open_time(futures_klines, spot_klines)

    if not aligned_f:
        # 完全没有交集，只返回合约CVD
        warn("⚠️  现货/合约K线时间完全不匹配，只使用合约CVD")
        return cvd_f

    # 检查丢弃比例
    total_klines = len(futures_klines) + len(spot_klines)
    discard_ratio = discarded / total_klines if total_klines > 0 else 0
    if discard_ratio > max_discard_ratio:
        warn(f"⚠️  K线对齐丢弃{discarded}根（{discard_ratio:.2%}），超过阈值{max_discard_ratio:.2%}")

    # 计算对齐后的CVD
    cvd_f = cvd_from_klines(aligned_f, use_taker_buy=True, use_quote=use_quote)
    cvd_s = cvd_from_spot_klines(aligned_s, use_quote=use_quote)

    n = len(aligned_f)  # 对齐后长度必然相同

    # 计算权重
    if use_dynamic_weight:
        # 方法1：按成交额（USDT）比例动态计算权重
        # K线第7列：quoteAssetVolume（成交额，单位USDT）
        f_quote_volume = sum([_to_f(k[7]) for k in aligned_f])
        s_quote_volume = sum([_to_f(k[7]) for k in aligned_s])
        total_quote = f_quote_volume + s_quote_volume

        if total_quote > 0:
            futures_weight = f_quote_volume / total_quote
            spot_weight = s_quote_volume / total_quote
        else:
            # 降级到固定比例
            futures_weight = 0.7
            spot_weight = 0.3
    else:
        # 方法2：固定权重
        futures_weight = 0.7
        spot_weight = 0.3

    # v7.2.34: P2-4 - 加权组合CVD增量（成交额过小时处理）
    result: List[float] = []
    for i in range(n):
        # 获取当前K线的成交额
        f_quote = _to_f(aligned_f[i][7])
        s_quote = _to_f(aligned_s[i][7])
        total_quote_i = f_quote + s_quote

        # 计算每根K线的CVD增量
        if i == 0:
            delta_f = cvd_f[i]
            delta_s = cvd_s[i]
        else:
            delta_f = cvd_f[i] - cvd_f[i-1]
            delta_s = cvd_s[i] - cvd_s[i-1]

        # 成交额过小时处理
        if total_quote_i < min_total_quote:
            # 成交额过小，使用上一根CVD值（跳过组合）
            if i == 0:
                result.append(0.0)
            else:
                result.append(result[-1])
            continue

        # 加权混合增量
        combined_delta = futures_weight * delta_f + spot_weight * delta_s

        # 累加
        if i == 0:
            result.append(combined_delta)
        else:
            result.append(result[-1] + combined_delta)

    return result


def cvd_mix_with_oi_price(
    klines: Sequence[Sequence],
    oi_hist: Sequence[dict],
    window: int = 20,
    spot_klines: Sequence[Sequence] = None,
    use_quote: bool = True,
    rolling_window: int = 96,
    use_robust: bool = True
) -> Tuple[List[float], List[float]]:
    """
    组合信号：CVD（现货+合约）+ 价格收益 + OI 变化（v7.2.34增强版）

    Args:
        klines: 合约K线数据
        oi_hist: 持仓量历史数据
        window: 窗口大小（保留兼容，实际使用rolling_window）
        spot_klines: 现货K线数据（可选）
        use_quote: 是否使用Quote CVD（USDT单位）
                  True: 使用USDT单位（推荐）
                  False: 使用币数量单位（兼容旧版）
        rolling_window: 滚动窗口大小（96根1h K线 = 4天）
                       用于滚动Z标准化
        use_robust: 是否使用稳健Z-score（MAD）
                   True: 使用MAD（对异常值稳健）
                   False: 使用std（传统方法）

    Returns:
        (cvd_series, mix_series)
        - cvd_series: 组合后的CVD（如果有现货数据则为现货+合约）
        - mix_series: 综合强度（标准化），越大代表量价+OI同向越强

    改进（v7.2.34）：
        - P1-2: 滚动Z标准化（避免前视偏差）
        - 对增量（ΔC, ΔP, ΔOI）做标准化，而不是累计值
        - 使用rolling_z替代全局_z_all
    """
    # 导入工具函数
    from ats_core.utils.cvd_utils import rolling_z

    # 计算CVD（现货+合约组合，如果有现货数据）
    if spot_klines and len(spot_klines) > 0:
        cvd = cvd_combined(klines, spot_klines, use_quote=use_quote)
    else:
        cvd = cvd_from_klines(klines, use_taker_buy=True, use_quote=use_quote)

    closes = _close_prices(klines)
    ret_p = _pct_change(closes)

    oi_vals: List[float] = []
    if isinstance(oi_hist, (list, tuple)):
        for d in oi_hist:
            if not isinstance(d, dict):
                continue
            v = d.get("sumOpenInterest") or d.get("sumOpenInterestValue") or d.get("openInterest") or 0.0
            oi_vals.append(_to_f(v))

    if oi_vals:
        n = min(len(cvd), len(ret_p), len(oi_vals))
        cvd = cvd[-n:]
        ret_p = ret_p[-n:]
        oi_vals = oi_vals[-n:]
        d_oi = _pct_change(oi_vals)
    else:
        n = min(len(cvd), len(ret_p))
        cvd = cvd[-n:]
        ret_p = ret_p[-n:]
        d_oi = [0.0] * n

    # v7.2.34: P1-2 - 滚动Z标准化（对增量做标准化）
    # 计算CVD增量（而不是累计CVD）
    delta_cvd = _pct_change(cvd)  # CVD增量百分比

    # 使用滚动窗口Z-score标准化（无前视偏差）
    z_cvd = rolling_z(delta_cvd, window=rolling_window, robust=use_robust)
    z_p = rolling_z(ret_p, window=rolling_window, robust=use_robust)
    z_oi = rolling_z(d_oi, window=rolling_window, robust=use_robust)

    # 组合权重：CVD权重提升（更重要）
    mix = [1.2 * z_cvd[i] + 0.4 * z_p[i] + 0.4 * z_oi[i] for i in range(n)]
    return cvd, mix

__all__ = [
    "cvd_from_klines",
    "cvd_from_spot_klines",
    "cvd_combined",
    "cvd_mix_with_oi_price",
    "zscore_last"
]