import json, statistics, urllib.request, urllib.parse
from typing import List, Tuple, Dict, Any

# ---------- utils ----------
def _clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else (hi if x > hi else x)

def _http_json(url: str, params: dict = None, timeout: int = 12):
    if params:
        url += "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode())

def _percentile_rank(series: List[float], x: float) -> float:
    s = sorted(series)
    if not s:
        return 50.0
    idx = 0
    for i, v in enumerate(s):
        if x <= v:
            idx = i
            break
    else:
        idx = len(s) - 1
    return 100.0 * idx / max(1, len(s) - 1)

def _robust_z(series: List[float], x: float) -> float:
    if not series:
        return 0.0
    med = statistics.median(series)
    mad = statistics.median([abs(v - med) for v in series]) or 1e-9
    return (x - med) / (1.4826 * mad)

# ---------- derive env factors from bars ----------
def _chop14_from_bars(h: List[float], l: List[float], c: List[float]) -> float:
    if len(c) < 15:
        return 100.0
    tr = []
    for i in range(1, len(c)):
        tr.append(max(h[i] - l[i], abs(h[i] - c[i-1]), abs(l[i] - c[i-1])))
    tr14 = sum(tr[-14:])
    hh = max(h[-14:])
    ll = min(l[-14:])
    rng = max(1e-9, hh - ll)
    import math
    return 100.0 * (math.log10(tr14 / rng) / math.log10(14))

def _room_from_bars(h: List[float], l: List[float], c: List[float], atr_now: float) -> float:
    """
    Room (for env score only): lookback 72 highs/lows, pick the larger side gap to price, normalize by ATR.
    Direction-agnostic here; give-price will refine by side later.
    """
    if len(c) < 3:
        return 0.0
    look = min(72, len(c))
    hh = max(h[-look:])
    ll = min(l[-look:])
    price = c[-1]
    room_abs = max(hh - price, price - ll)
    return room_abs / max(1e-9, atr_now)

# ---------- environment score (dual-signature compatible) ----------
def environment_score(*args) -> Tuple[int, Dict[str, Any]]:
    """
    Compatible with:
      1) environment_score(h, l, c, atr_now, params)
      2) environment_score(ch, room, params)
    Returns: (E 0..100, meta={chop, room})
    """
    if len(args) == 5 and isinstance(args[0], list):
        h, l, c, atr_now, params = args
        ch = _chop14_from_bars(h, l, c)
        room = _room_from_bars(h, l, c, atr_now)
    elif len(args) == 3 and isinstance(args[0], (int, float)):
        ch, room, params = args
    else:
        raise TypeError("environment_score: unexpected signature")

    chop14_max = float(params.get("chop14_max", 52))
    room_min   = float(params.get("room_min_for_bonus", 0.5))

    s = 0
    s += int(60 * _clamp((chop14_max - ch) / max(1e-9, chop14_max), 0.0, 1.0))
    s += int(40 * _clamp(room / max(1e-9, room_min), 0.0, 1.0))
    s = max(0, min(100, s))
    return s, {"chop": round(ch, 1), "room": round(room, 2)}

# ---------- funding hard veto ----------
def _fetch_funding_rates(symbol: str, limit: int = 50) -> List[float]:
    rows = _http_json(
        "https://fapi.binance.com/fapi/v1/fundingRate",
        {"symbol": symbol, "limit": str(limit)}
    )
    rates = []
    for it in rows:
        try:
            rates.append(float(it.get("fundingRate", 0.0)))
        except Exception:
            pass
    return rates


def funding_hard_veto(symbol: str, is_bigcap: bool, params: dict):
    """
    返回 (veto: bool, meta: dict)
    meta={"samples":N,"last":rate,"abs_last":|rate|,"pctl":0..100,"z":abs_z,"reason":str}
    规则（v1.5稳健化）：
      • 样本 < min_samples → 不否决
      • |last| < min_abs   → 不否决（避免“很小的费率”被分位数误伤）
      • 其余按 (pctl 极端 或 |z| 极端) 判定（默认），阈值区分大/小币
    """
    lookback = int(params.get("lookback", 50))
    min_samples = int(params.get("min_samples", 12))
    min_abs = float(params.get("min_abs", 0.0002))  # 0.02%/8h
    mode = params.get("mode", "or-minabs")

    try:
        rates = _fetch_funding_rates(symbol, limit=lookback)
    except Exception:
        return False, {"samples":0,"last":None,"abs_last":None,"pctl":None,"z":None,"reason":"network"}

    if len(rates) < min_samples:
        last = rates[-1] if rates else None
        return False, {"samples":len(rates),"last":last,"abs_last":(abs(last) if last is not None else None),
                       "pctl":None,"z":None,"reason":"insufficient"}

    last = float(rates[-1])
    abs_last = abs(last)
    pctl = _percentile_rank(rates, last)
    z = abs(_robust_z(rates, last))

    if abs_last < min_abs:
        return False, {"samples":len(rates),"last":last,"abs_last":abs_last,"pctl":pctl,"z":z,"reason":"below_min_abs"}

    if is_bigcap:
        p_hi, p_lo, z_th = float(params.get("p_hi_big",97)), float(params.get("p_lo_big",3)), float(params.get("z_big",2.3))
    else:
        p_hi, p_lo, z_th = float(params.get("p_hi_small",98)), float(params.get("p_lo_small",2)), float(params.get("z_small",2.0))

    extreme_p = (pctl >= p_hi or pctl <= p_lo)
    extreme_z = (z >= z_th)

    if mode == "and":
        veto = (extreme_p and extreme_z)
    else:  # "or-minabs"（默认）
        veto = (extreme_p or extreme_z)

    return veto, {"samples":len(rates),"last":last,"abs_last":abs_last,
                  "pctl":round(pctl,2),"z":round(z,2),"reason":("extreme" if veto else "ok")}
