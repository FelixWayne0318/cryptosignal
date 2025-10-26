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

# ---------- environment score (v2.0 对称版本) ----------
def environment_score(*args) -> Tuple[int, Dict[str, Any]]:
    """
    环境评分（v2.0 对称版本）

    Compatible with:
      1) environment_score(h, l, c, atr_now, params)
      2) environment_score(ch, room, params)

    Returns: (E -100..+100, meta)

    改进v2.0：
    - ✅ 分数范围：-100 到 +100（0为中性）
    - ✅ 方向判断：结合价格位置确定上升/下降空间
    - ✅ 对称设计：正值=上升空间大（靠近下轨），负值=下降空间大（靠近上轨）
    """
    # 处理两种调用方式
    if len(args) == 5 and isinstance(args[0], list):
        h, l, c, atr_now, params = args
        ch = _chop14_from_bars(h, l, c)
        room = _room_from_bars(h, l, c, atr_now)
        has_price_data = True
    elif len(args) == 3 and isinstance(args[0], (int, float)):
        ch, room, params = args
        h = l = c = None
        has_price_data = False
    else:
        raise TypeError("environment_score: unexpected signature")

    chop14_max = float(params.get("chop14_max", 52))
    room_min   = float(params.get("room_min_for_bonus", 0.5))

    # 计算环境质量（0-100）
    quality = 0
    quality += int(60 * _clamp((chop14_max - ch) / max(1e-9, chop14_max), 0.0, 1.0))
    quality += int(40 * _clamp(room / max(1e-9, room_min), 0.0, 1.0))

    # 如果没有价格数据，返回中性
    if not has_price_data:
        return 0, {"chop": round(ch, 1), "room": round(room, 2), "price_position": None}

    # 计算价格位置（确定方向）
    if len(c) >= 3 and len(h) >= 72 and len(l) >= 72:
        look = min(72, len(c))
        hh = max(h[-look:])
        ll = min(l[-look:])
        price = c[-1]

        # 价格在区间的相对位置（0-1）
        if hh > ll:
            price_position = (price - ll) / (hh - ll)
        else:
            price_position = 0.5  # 区间无效，返回中性

        # 导入对称评分函数
        from .scoring_utils import directional_score_symmetric

        # 价格位置转方向
        # 靠近下轨（0-0.3） → 上升空间大 → 正分
        # 靠近上轨（0.7-1.0） → 下降空间大 → 负分
        # 居中（0.3-0.7） → 空间均衡 → 接近中性
        #
        # 用 (0.5 - price_position) 作为输入
        direction_value = 0.5 - price_position  # 0.5→0, 0.2→0.3, 0.8→-0.3

        direction_score = directional_score_symmetric(
            direction_value,
            neutral=0.0,
            scale=0.15
        )  # -100 到 +100

        # 质量 × 方向强度
        direction_factor = direction_score / 100.0  # 归一化到-1到+1
        E = int(round(quality * direction_factor))
        E = max(-100, min(100, E))

        interpretation = "上升空间大" if E > 20 else ("下降空间大" if E < -20 else "空间均衡")
    else:
        # 数据不足，返回中性
        E = 0
        price_position = None
        interpretation = "数据不足"

    return E, {
        "chop": round(ch, 1),
        "room": round(room, 2),
        "price_position": round(price_position, 2) if price_position is not None else None,
        "quality": quality,
        "interpretation": interpretation
    }

