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
    返回 (veto: bool, meta: dict)。当 params.enabled 为 False 时，直接不否决。
    """
    try:
        enabled = params.get("enabled", True) if isinstance(params, dict) else True
    except Exception:
        enabled = True
    # 关掉：立刻返回，不打网
    if str(enabled).lower() in ("0","false","no","off"):
        return False, {"disabled": True}

    # ——以下保留极端判定（以防你以后重新打开）——
    def _get(*keys, default=None, cast=float):
        cfg = params or {}
        for k in keys:
            if k in cfg and cfg[k] is not None:
                try:
                    return cast(cfg[k])
                except Exception:
                    pass
        return default

    p_hi_big = _get("pctl_bigcap_hi", default=99.5)
    p_lo_big = _get("pctl_bigcap_lo", default=0.5)
    z_big    = _get("z_bigcap",       default=3.0)

    p_hi_small = _get("pctl_smallcap_hi", default=99.7)
    p_lo_small = _get("pctl_smallcap_lo", default=0.3)
    z_small    = _get("z_smallcap",       default=3.0)

    min_samples = int(_get("min_samples",    default=12, cast=int))
    limit       = int(_get("funding_limit",  default=50, cast=int))

    try:
        rates = _fetch_funding_rates(symbol, limit=limit)
    except Exception:
        return False, {"samples":0, "last":None, "pctl":None, "z":None}

    if len(rates) < min_samples:
        return False, {"samples":len(rates), "last":(rates[-1] if rates else None),
                       "pctl":None, "z":None}

    last = rates[-1]
    pctl = _percentile_rank(rates, last)
    z    = abs(_robust_z(rates, last))

    if is_bigcap:
        veto = (pctl >= p_hi_big or pctl <= p_lo_big) or (z >= z_big)
    else:
        veto = (pctl >= p_hi_small or pctl <= p_lo_small) or (z >= z_small)

    return veto, {"samples":len(rates), "last":last, "pctl":round(pctl,2), "z":round(z,2)}
