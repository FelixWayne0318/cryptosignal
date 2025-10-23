# coding: utf-8
from __future__ import annotations
from typing import List, Dict, Sequence, Tuple, Optional
import math

# --- 工具 ---

def _to_float(x) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0

def _last(x):
    """如果是标量直接返回；如果是序列，返回最后一个；其他情况返回原值。"""
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, Sequence) and len(x) > 0:
        return _to_float(x[-1])
    return x

def _zscore_last(arr: Sequence[float], window: int = 20) -> float:
    if not arr:
        return 0.0
    w = arr[-window:] if len(arr) >= window else list(arr)
    n = len(w)
    if n <= 1:
        return 0.0
    mean = sum(w) / n
    var = sum((v - mean) ** 2 for v in w) / (n - 1)
    std = math.sqrt(var) if var > 0 else 0.0
    if std <= 1e-12:
        return 0.0
    return (arr[-1] - mean) / std

def _zseries(seq: Sequence[float], window: int = 20) -> List[float]:
    """滚动 zscore（逐点）"""
    z: List[float] = []
    for i in range(len(seq)):
        w = seq[max(0, i - window + 1): i + 1]
        n = len(w)
        if n <= 1:
            z.append(0.0)
            continue
        mean = sum(w) / n
        var = sum((v - mean) ** 2 for v in w) / (n - 1)
        std = math.sqrt(var) if var > 0 else 0.0
        z.append((w[-1] - mean) / std if std > 1e-12 else 0.0)
    return z

def _diff_norm(seq: Sequence[float]) -> List[float]:
    """归一化差分：dx / max(1e-12, |prev|)"""
    out: List[float] = []
    prev: Optional[float] = None
    for v in seq:
        v = _to_float(v)
        if prev is None:
            out.append(0.0)
        else:
            base = abs(prev) if abs(prev) > 1e-12 else 1.0
            out.append((v - prev) / base)
        prev = v
    return out

# --- CVD ---

def cvd_from_klines(klines: List[Sequence]) -> List[float]:
    """
    以 1h K线计算 CVD（近似：上涨累加成交量、下跌减去成交量）。
    兼容 K 线为 list 的标准 FUTURES 返回：索引
      1=open, 2=high, 3=low, 4=close, 5=volume
    """
    cvd: List[float] = []
    if not klines:
        return cvd
    s = 0.0
    last_close: Optional[float] = None
    for r in klines:
        # Binance futures klines: [openTime, open, high, low, close, volume, ...]
        c = _to_float(r[4])
        v = _to_float(r[5])
        if last_close is None:
            s += 0.0  # 第一根不计方向
        else:
            if c > last_close:
                s += v
            elif c < last_close:
                s -= v
            else:
                s += 0.0
        cvd.append(s)
        last_close = c
    return cvd

def zscore_last(series: Sequence[float], window: int = 20) -> float:
    return _zscore_last(series, window)

def cvd_mix_with_oi_price(
    klines: List[Sequence],
    oi_list: List[Dict],
    window: int = 20
) -> Tuple[List[float], List[float]]:
    """
    生成两条序列：
      - z_cvd: CVD 的“差分滚动 zscore”
      - mix:   z_cvd + 0.5*z_oi + 0.5*z_price
    说明：
      price 使用 close 序列的归一化差分；
      oi 取 sumOpenInterestValue（若不存在则退化为 sumOpenInterest）。
    """
    if not klines:
        return [], []

    cvd = cvd_from_klines(klines)
    cvd_diff = [0.0] + [cvd[i] - cvd[i - 1] for i in range(1, len(cvd))]

    n = min(len(klines), len(oi_list), len(cvd_diff))
    if n <= 1:
        return [], []

    k2 = klines[-n:]
    o2 = oi_list[-n:]
    cvd2 = cvd_diff[-n:]

    closes = [_to_float(r[4]) for r in k2]
    price_dn = _diff_norm(closes)

    oi_raw: List[float] = []
    for d in o2:
        val = d.get("sumOpenInterestValue", None)
        if val is None:
            val = d.get("sumOpenInterest", 0.0)
        oi_raw.append(_to_float(val))
    oi_dn = _diff_norm(oi_raw)

    z_cvd = _zseries(cvd2, window)
    z_oi = _zseries(oi_dn, window)
    z_px = _zseries(price_dn, window)

    mix = [z_cvd[i] + 0.5 * z_oi[i] + 0.5 * z_px[i] for i in range(n)]
    return z_cvd, mix