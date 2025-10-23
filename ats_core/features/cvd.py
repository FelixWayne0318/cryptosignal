# coding: utf-8
from __future__ import annotations
from typing import List, Sequence, Dict, Tuple
import statistics as st

def _to_float(x) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0

def cvd_from_klines(klines: List[Sequence]) -> List[float]:
    """
    用 futures K 线直接计算 CVD（taker 买 - taker 卖 的累积）。
    kline字段: [openTime, open, high, low, close, volume, closeTime, quoteVol, trades, takerBuyBase, takerBuyQuote, ignore]
    返回: 与 klines 等长的 CVD 序列（同频）
    """
    cvd: List[float] = []
    s = 0.0
    for k in klines:
        vol  = _to_float(k[5])
        buy  = _to_float(k[9])
        sell = max(0.0, vol - buy)
        delta = buy - sell           # 本根K的买卖量差（base）
        s += delta
        cvd.append(s)
    return cvd

def zscore_last(xs: List[float], lookback: int = 20) -> float:
    """末值 zscore，样本不足时退化处理。"""
    if not xs:
        return 0.0
    tail = xs[-lookback:] if len(xs) >= lookback else xs
    mu = st.mean(tail)
    sigma = st.pstdev(tail) or 1.0
    return (xs[-1] - mu) / sigma

def cvd_mix_with_oi_price(
    klines: List[Sequence],
    oi_rows: List[Dict],
) -> Tuple[List[float], List[float]]:
    """
    结合 OI 和价格，对每根K的 CVD 进行“方向加权”：
      mix_t = delta_t * sign(ΔOI_t) * |ΔP_t|
    返回: (cvd序列, mix序列)；长度均为 min(len(klines), len(oi_rows))
    """
    K = min(len(klines), len(oi_rows))
    if K <= 1:
        return [], []

    # 先算每根K的 delta（非累积）
    deltas: List[float] = []
    for i in range(K):
        vol  = _to_float(klines[i][5])
        buy  = _to_float(klines[i][9])
        sell = max(0.0, vol - buy)
        deltas.append(buy - sell)

    # CVD（累积）
    cvd: List[float] = []
    s = 0.0
    for i in range(K):
        s += deltas[i]
        cvd.append(s)

    # 按 ΔOI 和 |ΔP| 加权
    mix: List[float] = []
    prev_c = _to_float(klines[0][4])
    prev_oi = _to_float(oi_rows[0].get("sumOpenInterest"))
    for i in range(1, K):
        c = _to_float(klines[i][4])
        dP = 0.0 if prev_c == 0 else (c - prev_c) / prev_c
        dOI = _to_float(oi_rows[i].get("sumOpenInterest")) - prev_oi
        w = (1.0 if dOI >= 0 else -1.0) * abs(dP)
        mix.append(deltas[i] * w)
        prev_c = c
        prev_oi = prev_oi + dOI

    return cvd, mix