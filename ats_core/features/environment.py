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
      meta = {"samples":N, "last":float, "pctl":百分位(0..100), "z":abs_robust_z}
    规则（v1.5）：
      • 大币：分位 ≥97% 或 ≤3% ；或 |z| ≥ 2.3
      • 小币：分位 ≥98% 或 ≤2% ；或 |z| ≥ 2.0
      • 样本不足（<12）→ 不否决（False）
    """
    try:
        rates = _fetch_funding_rates(symbol, limit=int(params.get("funding_limit", 50)))
    except Exception:
        return False, {"samples": 0, "last": None, "pctl": None, "z": None}

    if len(rates) < 12:
        return False, {"samples": len(rates), "last": (rates[-1] if rates else None), "pctl": None, "z": None}

    last = rates[-1]
    pctl = _percentile_rank(rates, last)  # 0..100
    z    = abs(_robust_z(rates, last))

    if is_bigcap:
        veto = (pctl >= 97.0 or pctl <= 3.0) or (z >= 2.3)
    else:
        veto = (pctl >= 98.0 or pctl <= 2.0) or (z >= 2.0)

    return veto, {"samples": len(rates), "last": last, "pctl": round(pctl,2), "z": round(z,2)}
