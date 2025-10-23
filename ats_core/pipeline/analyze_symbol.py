# coding: utf-8
from __future__ import annotations

from typing import List, Dict, Any, Sequence, Optional
from statistics import mean

from ats_core.cfg import CFG
from ats_core.sources.binance import get_klines, get_open_interest_hist
from ats_core.features.cvd import cvd_from_klines, cvd_mix_with_oi_price, zscore_last

# ------------ 工具 ------------
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

def _ema(seq: Sequence[float], n: int) -> List[float]:
    out: List[float] = []
    if not seq or n <= 1: return [float(_to_f(v)) for v in seq]
    k = 2.0/(n+1.0)
    e = None
    for v in seq:
        v = _to_f(v)
        e = v if e is None else (e + k*(v-e))
        out.append(e)
    return out

def _atr(h: Sequence[float], l: Sequence[float], c: Sequence[float], period: int = 14) -> List[float]:
    n = min(len(h), len(l), len(c))
    if n == 0: return []
    tr: List[float] = []
    pc = _to_f(c[0])
    for i in range(n):
        hi = _to_f(h[i]); lo = _to_f(l[i]); ci = _to_f(c[i])
        tr.append(max(hi-lo, abs(hi-pc), abs(lo-pc)))
        pc = ci
    out: List[float] = []
    s = 0.0
    for i, v in enumerate(tr):
        s += v
        if i+1 < period:
            out.append(s/(i+1))
        else:
            if i+1 == period:
                out.append(s/period)
            else:
                s -= tr[i-period+1]
                out.append(s/period)
    return out

def _safe_dict(obj: Any) -> Dict[str, Any]:
    return obj if isinstance(obj, dict) else {}

# ------------ 趋势打分（兼容） ------------
def _score_trend(h, l, c, c4, trend_cfg):
    try:
        from ats_core.features.trend import score_trend
    except Exception:
        return 0, {"slopeATR": 0.0, "emaOrder": 0}
    T, Tm = score_trend(h, l, c, c4, trend_cfg)
    return T, Tm

def _norm_trend_meta(Tm: Any, ema30: Sequence[float], atr_now: float) -> Dict[str, Any]:
    if isinstance(Tm, dict):
        meta = dict(Tm)
    else:
        try:
            meta = {"slopeATR": float(Tm)}
        except Exception:
            meta = {"slopeATR": 0.0}
    if not isinstance(meta.get("emaOrder"), (int, float)):
        meta["emaOrder"] = 0
    if not isinstance(meta.get("slopeATR"), (int, float)):
        meta["slopeATR"] = 0.0
    if abs(meta["slopeATR"]) < 1e-12 and isinstance(ema30, Sequence) and len(ema30) >= 6:
        meta["slopeATR"] = ( _last(ema30) - float(ema30[-6]) ) / max(atr_now, 1e-9)
    meta["slopeATR"] = float(meta["slopeATR"])
    meta["emaOrder"] = int(meta["emaOrder"])
    return meta

# ------------ 主函数 ------------
def analyze_symbol(symbol: str) -> Dict[str, Any]:
    p: Dict[str, Any] = CFG.params or {}
    trend_cfg = _safe_dict(p.get("trend"))
    structure_cfg = _safe_dict(p.get("structure")) or {
        "ema_order_min_bars": int(trend_cfg.get("ema_order_min_bars", 6)),
        "slope_atr_min_long": float(trend_cfg.get("slope_atr_min_long", 0.30)),
        "slope_atr_min_short": float(trend_cfg.get("slope_atr_min_short", 0.20)),
    }

    # K 线与 OI
    k1 = get_klines(symbol, "1h", 300)
    k4 = get_klines(symbol, "4h", 200)
    oi = get_open_interest_hist(symbol, "1h", 300)

    if not k1 or len(k1) < 50:
        return {
            "T": 0, "T_meta": {"slopeATR": 0.0, "emaOrder": 0}, "strong": False, "m15_ok": False,
            "ema30": 0.0, "atr_now": 0.0, "close": 0.0, "structure": structure_cfg,
            # CVD 字段兜底
            "cvd_z20": 0.0, "cvd_mix_abs_per_h": 0.0,
        }

    h = [float(r[2]) for r in k1]
    l = [float(r[3]) for r in k1]
    c = [float(r[4]) for r in k1]
    c4 = ([float(r[4]) for r in k4] if k4 else list(c))

    ema30 = _ema(c, 30)
    atr_now = _last(_atr(h, l, c, int(trend_cfg.get("atr_period", 14))))

    # 趋势
    T, Tm = _score_trend(h, l, c, c4, trend_cfg)
    T_meta = _norm_trend_meta(Tm, ema30, atr_now)
    strong = T_meta.get("slopeATR", 0.0) >= float(trend_cfg.get("slope_atr_min_long", 0.30))

    # —— CVD 统一：来自 cvd.py ——
    cvd, mix = cvd_mix_with_oi_price(k1, oi, window=20)
    cvd_z20 = zscore_last(cvd, 20) if cvd else 0.0
    # 取“每小时混合动量”的末值绝对值（与 overlay 的 cvd_mix_abs_per_h 对齐）
    cvd_mix_abs_per_h = abs(_last(mix)) if mix else 0.0

    return {
        "T": int(T or 0),
        "T_meta": T_meta,
        "strong": bool(strong),
        "m15_ok": False,
        "ema30": _last(ema30),
        "atr_now": float(atr_now),
        "close": _last(c),
        "structure": structure_cfg,
        # CVD 相关（供渲染和 overlay/prime 使用）
        "cvd_z20": float(cvd_z20),
        "cvd_mix_abs_per_h": float(cvd_mix_abs_per_h),
    }