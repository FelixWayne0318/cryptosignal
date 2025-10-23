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

def cvd_from_klines(klines: Sequence[Sequence]) -> List[float]:
    """
    以“tick rule”估算买卖方向：close >= open 记为 +1，否则 -1；CVD = Σ(sign * volume)
    输入为 Binance 期货 klines（12 列）。
    """
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

def cvd_mix_with_oi_price(
    klines: Sequence[Sequence],
    oi_hist: Sequence[dict],
    window: int = 20
) -> Tuple[List[float], List[float]]:
    """
    组合信号示例：标准化后的 CVD + 价格收益 + OI 变化三者合成。
    返回：(cvd_series, mix_series)
    - mix_series 为每根 K 的综合强度（已标准化），越大代表量价+OI 同向越强。
    """
    cvd = cvd_from_klines(klines)
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

    mix = [1.0 * z_cvd[i] + 0.5 * z_p[i] + 0.5 * z_oi[i] for i in range(n)]
    return cvd, mix

__all__ = ["cvd_from_klines", "cvd_mix_with_oi_price", "zscore_last"]