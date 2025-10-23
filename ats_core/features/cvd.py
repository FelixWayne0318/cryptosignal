# coding: utf-8
from __future__ import annotations

"""
CVD 统一实现：
- 优先使用 Binance K 线中的 takerBuyBaseVolume（第 10 列索引 9）来估算主动买卖量差，
  即 signed = buy_base - sell_base = (2 * taker_buy_base - volume)；
- 若无 taker 字段，则回退为 sign(close - open) * volume；
- 提供 cvd 累积、zscore、与 OI/价格的标准化混合信号。
"""

from typing import List, Sequence, Tuple, Dict, Any
import math
from statistics import mean, pstdev

from ats_core.cfg import CFG

# ---- 工具 ----
def _to_f(x) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0

def _last(x):
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(x[-1])
    except Exception:
        return _to_f(x)

def _pct_series(xs: Sequence[float]) -> List[float]:
    out: List[float] = []
    prev = None
    for v in xs:
        v = _to_f(v)
        if prev is None or prev == 0:
            out.append(0.0)
        else:
            out.append((v / prev) - 1.0)
        prev = v
    return out

def _zscore_series(xs: Sequence[float], n: int) -> List[float]:
    if not xs:
        return []
    out: List[float] = []
    q: List[float] = []
    for v in xs:
        q.append(_to_f(v))
        if len(q) > n:
            q.pop(0)
        if len(q) < 2:
            out.append(0.0)
        else:
            mu = mean(q)
            sd = pstdev(q) or 1e-9
            out.append((v - mu) / sd)
    return out

def zscore_last(xs: Sequence[float], n: int) -> float:
    zs = _zscore_series(xs, n)
    return _last(zs) if zs else 0.0

# ---- CVD 主体 ----
def cvd_from_klines(klines: Sequence[Sequence[Any]], use_taker: bool = True) -> List[float]:
    """
    Binance kline 列表： [openTime, open, high, low, close, volume, closeTime,
                         quoteVol, trades, takerBuyBase, takerBuyQuote, ignore]
    返回逐根累加的 CVD（基于基准币数量）。
    """
    cvd: List[float] = []
    acc = 0.0
    for r in klines:
        try:
            o = _to_f(r[1]); c = _to_f(r[4]); v = _to_f(r[5])
            taker_buy_base = _to_f(r[9]) if (use_taker and len(r) > 9) else None
            if taker_buy_base is not None and taker_buy_base > 0.0:
                signed = 2.0 * taker_buy_base - v
            else:
                # 回退：用价格方向给体积加符号
                sgn = 1.0 if (c - o) >= 0 else -1.0
                signed = sgn * v
            acc += signed
        except Exception:
            # 异常行跳过
            acc += 0.0
        cvd.append(acc)
    return cvd

def cvd_mix_with_oi_price(
    klines: Sequence[Sequence[Any]],
    oi_hist: Sequence[Dict[str, Any]],
    window: int = 20,
    weights: Dict[str, float] | None = None,
) -> Tuple[List[float], List[float]]:
    """
    生成两条序列：
      - cvd: 上述累加 CVD
      - mix: 把 CVD 一阶变化、OI 百分比变化、价格百分比变化，各自做 rolling zscore 后线性加权的“合成动量”
    """
    if weights is None:
        wcfg = CFG.get("cvd", default={"w_cvd": 0.5, "w_oi": 0.3, "w_px": 0.2})
    else:
        wcfg = dict(weights)
    w_cvd = float(wcfg.get("w_cvd", 0.5))
    w_oi  = float(wcfg.get("w_oi", 0.3))
    w_px  = float(wcfg.get("w_px", 0.2))

    # 价格序列
    close = [_to_f(r[4]) for r in klines]
    cvd = cvd_from_klines(klines, use_taker=True)

    # OI 序列（sumOpenInterest）
    oi_vals = []
    for o in oi_hist or []:
        v = _to_f(o.get("sumOpenInterest"))
        oi_vals.append(v)

    # 对齐长度
    n = min(len(close), len(cvd), len(oi_vals)) if oi_vals else min(len(close), len(cvd))
    if n <= 3:
        return cvd, []

    close = close[-n:]
    cvd = cvd[-n:]
    if oi_vals:
        oi_vals = oi_vals[-n:]

    # 一阶变化 / 百分比
    cvd_diff = [0.0] + [cvd[i]-cvd[i-1] for i in range(1, n)]
    px_pct  = _pct_series(close)
    if oi_vals:
        oi_pct = _pct_series(oi_vals)
    else:
        oi_pct = [0.0]*n

    # 滚动 zscore
    z_cvd = _zscore_series(cvd_diff, window)
    z_px  = _zscore_series(px_pct, window)
    z_oi  = _zscore_series(oi_pct, window)

    # 线性混合
    mix = [w_cvd*z_cvd[i] + w_oi*z_oi[i] + w_px*z_px[i] for i in range(n)]
    return cvd, mix