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
    """Room: lookback 72 highs/lows, pick larger side gap to price, normalize by ATR"""
    if len(c) < 3:
        return 0.0
    look = min(72, len(c))
    hh = max(h[-look:])
    ll = min(l[-look:])
    price = c[-1]
    room_abs = max(hh - price, price - ll)
    return room_abs / max(1e-9, atr_now)

# ---------- environment score (±100 system) ----------
def environment_score(*args) -> Tuple[int, Dict[str, Any]]:
    """
    E（环境）评分 - 统一±100系统

    返回：
    - 正分：环境好（震荡低，空间大）
    - 负分：环境差（震荡高，空间小）
    - 0：中性

    Compatible with:
      1) environment_score(h, l, c, atr_now, params)
      2) environment_score(ch, room, params)
    """
    if len(args) == 5 and isinstance(args[0], list):
        h, l, c, atr_now, params = args
        ch = _chop14_from_bars(h, l, c)
        room = _room_from_bars(h, l, c, atr_now)
    elif len(args) == 3 and isinstance(args[0], (int, float)):
        ch, room, params = args
    else:
        raise TypeError("environment_score: unexpected signature")

    chop14_max = float(params.get("chop14_max", 70))  # 优化：52→70，更宽容震荡行情
    room_min   = float(params.get("room_min_for_bonus", 0.5))

    # 计算0-100分数
    s = 0
    s += int(60 * _clamp((chop14_max - ch) / max(1e-9, chop14_max), 0.0, 1.0))
    s += int(40 * _clamp(room / max(1e-9, room_min), 0.0, 1.0))
    s = max(0, min(100, s))

    # 映射到 -100 到 +100
    E = (s - 50) * 2
    E = max(-100, min(100, E))

    # 解释
    if E >= 40:
        interpretation = "环境优越"
    elif E >= 10:
        interpretation = "环境良好"
    elif E >= -10:
        interpretation = "环境一般"
    elif E >= -40:
        interpretation = "环境偏差"
    else:
        interpretation = "环境恶劣"

    return E, {
        "chop": round(ch, 1),
        "room": round(room, 2),
        "interpretation": interpretation
    }
