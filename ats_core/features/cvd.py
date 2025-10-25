# coding: utf-8
from __future__ import annotations
from typing import List, Sequence, Tuple
import math

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

def cvd_from_klines(klines: Sequence[Sequence], use_taker_buy: bool = True) -> List[float]:
    """
    计算CVD (Cumulative Volume Delta)

    Args:
        klines: Binance 期货 klines（12列）
            [9]: takerBuyBaseVolume（主动买入量）
            [5]: volume（总成交量）
        use_taker_buy: 是否使用真实的taker buy volume
                      True: 使用真实数据（推荐）
                      False: 使用tick rule估算（兼容旧版）

    Returns:
        CVD序列：Σ(买入量 - 卖出量)
    """
    if use_taker_buy and klines and len(klines[0]) >= 10:
        # 优化方法：使用真实的taker buy volume
        taker_buy = _col(klines, 9)  # 主动买入量
        total_vol = _col(klines, 5)  # 总成交量
        n = min(len(taker_buy), len(total_vol))

        s = 0.0
        cvd: List[float] = []
        for i in range(n):
            buy = taker_buy[i]
            total = total_vol[i]
            if not (math.isfinite(buy) and math.isfinite(total)):
                cvd.append(s)
                continue
            # CVD delta = (买入量 - 卖出量)
            # = buy - (total - buy)
            # = 2 * buy - total
            delta = 2.0 * buy - total
            s += delta
            cvd.append(s)
        return cvd
    else:
        # 旧方法：Tick Rule估算（兼容性）
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
            sign = 1.0 if ci >= oi else -1.0
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

def cvd_from_spot_klines(klines: Sequence[Sequence]) -> List[float]:
    """
    计算现货CVD (使用真实taker buy volume)

    Args:
        klines: Binance 现货 klines（12列）
            [9]: takerBuyBaseVolume（主动买入量）
            [5]: volume（总成交量）

    Returns:
        现货CVD序列
    """
    # 现货数据格式与合约相同，直接调用
    return cvd_from_klines(klines, use_taker_buy=True)


def cvd_combined(
    futures_klines: Sequence[Sequence],
    spot_klines: Sequence[Sequence] = None,
    use_dynamic_weight: bool = True
) -> List[float]:
    """
    组合现货+合约CVD

    Args:
        futures_klines: 合约K线数据
        spot_klines: 现货K线数据（可选）
        use_dynamic_weight: 是否使用动态权重（按成交额比例）
                          True: 根据实际成交额动态计算权重（推荐）
                          False: 使用固定权重（70%合约 + 30%现货）

    Returns:
        组合后的CVD序列

    说明：
        - 动态权重：根据合约和现货的实际成交额（USDT）比例计算权重
        - 这样能真实反映不同市场的资金流向权重
        - 例如：某币合约日成交10亿，现货1亿 → 权重自动为 90.9% : 9.1%
    """
    cvd_f = cvd_from_klines(futures_klines, use_taker_buy=True)

    if spot_klines is None or len(spot_klines) == 0:
        # 如果没有现货数据，只返回合约CVD
        return cvd_f

    cvd_s = cvd_from_spot_klines(spot_klines)

    # 对齐长度
    n = min(len(cvd_f), len(cvd_s), len(futures_klines), len(spot_klines))
    cvd_f = cvd_f[-n:]
    cvd_s = cvd_s[-n:]
    f_klines = futures_klines[-n:]
    s_klines = spot_klines[-n:]

    # 计算权重
    if use_dynamic_weight:
        # 方法1：按成交额（USDT）比例动态计算权重
        # K线第7列：quoteAssetVolume（成交额，单位USDT）
        f_quote_volume = sum([_to_f(k[7]) for k in f_klines])
        s_quote_volume = sum([_to_f(k[7]) for k in s_klines])
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

    # 加权组合CVD增量（而不是标准化）
    result: List[float] = []
    for i in range(n):
        # 计算每根K线的CVD增量
        if i == 0:
            delta_f = cvd_f[i]
            delta_s = cvd_s[i]
        else:
            delta_f = cvd_f[i] - cvd_f[i-1]
            delta_s = cvd_s[i] - cvd_s[i-1]

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
    spot_klines: Sequence[Sequence] = None
) -> Tuple[List[float], List[float]]:
    """
    组合信号：CVD（现货+合约）+ 价格收益 + OI 变化

    Args:
        klines: 合约K线数据
        oi_hist: 持仓量历史数据
        window: 窗口大小
        spot_klines: 现货K线数据（可选）

    Returns:
        (cvd_series, mix_series)
        - cvd_series: 组合后的CVD（如果有现货数据则为现货+合约）
        - mix_series: 综合强度（标准化），越大代表量价+OI同向越强
    """
    # 计算CVD（现货+合约组合，如果有现货数据）
    if spot_klines and len(spot_klines) > 0:
        cvd = cvd_combined(klines, spot_klines)
    else:
        cvd = cvd_from_klines(klines, use_taker_buy=True)

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

    # 标准化
    z_cvd = _z_all(cvd)
    z_p = _z_all(ret_p)
    z_oi = _z_all(d_oi)

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