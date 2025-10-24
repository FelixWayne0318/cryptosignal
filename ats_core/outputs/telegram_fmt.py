# coding: utf-8
"""
Telegram message formatting (unified "formal" six-dimension template)
- Both watch and trade use the same professional & readable template.
- Always shows 6 dimensions with score and plain-language notes.
- Robust to missing fields: falls back to neutral 50 with explanation.
- Header order: line1 = symbol & price, line2 = status (watch/trade + side + conviction + ttl).
"""

from __future__ import annotations
from typing import Any, Dict, Optional, Tuple, List
import math

# ---------- small utils ----------

def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    try:
        v = float(x)
    except Exception:
        return 50.0
    return max(lo, min(hi, v))

def _as_int_score(x: Any, default: int = 50) -> int:
    try:
        if x is None:
            return default
        if isinstance(x, (list, tuple)) and len(x) > 0:
            # allow last value fallback
            try:
                x = x[-1]
            except Exception:
                pass
        return int(round(_clamp(float(x))))
    except Exception:
        return default

def _get(d: Any, key: str, default: Any = None) -> Any:
    """safe dict get with dotted path support, tolerant of non-dicts."""
    if d is None:
        return default
    if not isinstance(key, str) or key == "":
        return default
    cur = d
    for part in key.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur

def _fmt_price(x: Any) -> str:
    try:
        v = float(x)
        # pick decimals based on magnitude
        if v >= 10000:
            return f"{v:,.0f}"
        if v >= 1000:
            return f"{v:,.1f}"
        if v >= 1:
            return f"{v:,.2f}"
        # small prices keep more decimals
        return f"{v:,.6f}".rstrip("0").rstrip(".")
    except Exception:
        return "-"

def _ttl_hours(r: Dict[str, Any]) -> int:
    # try r['ttl_h'] or r['ttl_hours'] or r['publish']['ttl_h'] else 8
    return (
        _get(r, "ttl_h")
        or _get(r, "ttl_hours")
        or _get(r, "publish.ttl_h")
        or 8
    )

# ---------- score → emoji / description ----------

def _emoji_by_score(s: int) -> str:
    if s >= 60:
        return "🟢"
    if s >= 40:
        return "🟡"
    return "🔴"

def _desc_trend(s: int, is_long: bool = True) -> str:
    if is_long:
        # 做多视角
        if s >= 80: return "强势/上行倾向"
        if s >= 60: return "温和上行或多头占优"
        if s >= 40: return "中性/震荡"
        return "趋势弱/震荡或下行倾向"
    else:
        # 做空视角
        if s >= 80: return "强势/下行倾向"
        if s >= 60: return "温和下行或空头占优"
        if s >= 40: return "中性/震荡"
        return "趋势弱/震荡或上行倾向"

def _desc_structure(s: int) -> str:
    if s >= 80: return "结构清晰/多周期共振"
    if s >= 60: return "结构尚可/回踩确认"
    if s >= 40: return "结构一般/级别分歧"
    return "结构杂乱/级别相抵"

def _desc_volume(s: int) -> str:
    if s >= 80: return "放量明显/跟随积极"
    if s >= 60: return "量能偏强/逐步释放"
    if s >= 40: return "量能中性"
    return "量能不足/跟随意愿弱"

def _desc_accel(s: int, is_long: bool = True) -> str:
    direction = "上行" if is_long else "下行"
    if s >= 80: return f"{direction}加速强/持续性好"
    if s >= 60: return f"{direction}加速偏强/待确认"
    if s >= 40: return "加速一般"
    return "加速不足/有背离风险"

def _desc_positions(s: int, is_long: bool = True) -> str:
    side = "多头" if is_long else "空头"
    if s >= 80: return f"{side}持仓显著增长/可能拥挤"
    if s >= 60: return f"{side}持仓温和上升/活跃"
    if s >= 40: return "持仓温和变化"
    return f"{side}持仓走弱/去杠杆"

def _desc_env(s: int) -> str:
    if s >= 80: return "环境友好/空间充足"
    if s >= 60: return "环境偏友好"
    if s >= 40: return "环境一般/空间有限"
    return "环境不佳/波动或流动性掣肘"

# ---------- extract scores robustly ----------

def _score_trend(r: Dict[str, Any]) -> int:
    # 优先使用顶层 T 字段（来自新版 analyze_symbol）
    v = _get(r, "T")
    if v is None:
        v = _get(r, "trend.score")
    return _as_int_score(v, 50)

def _score_structure(r: Dict[str, Any]) -> int:
    # 优先使用顶层 S 字段（来自新版 analyze_symbol）
    v = _get(r, "S")
    if v is None:
        v = _get(r, "structure.score")
    if v is None:
        v = _get(r, "structure.fallback_score")
    if v is None:
        v = _get(r, "structure", {})
        if isinstance(v, dict) and "fallback_score" in v:
            v = v["fallback_score"]
    return _as_int_score(v, 50)

def _score_volume(r: Dict[str, Any]) -> int:
    # 优先使用顶层 V 字段（来自新版 analyze_symbol）
    v = _get(r, "V")
    if v is not None:
        return _as_int_score(v, 50)

    # 兼容旧版：尝试从元数据计算
    z = _get(r, "volume.z1h") or _get(r, "z_volume_1h") or _get(r, "momentum.z1h")
    if isinstance(z, (int, float)):
        return _as_int_score(50 + 12 * float(z), 50)
    ratio = _get(r, "volume.v5_over_v20") or _get(r, "v5_over_v20")
    if isinstance(ratio, (int, float)):
        return _as_int_score(50 + 30 * (float(ratio) - 1.0), 50)
    return 50

def _score_accel(r: Dict[str, Any]) -> int:
    # 优先使用顶层 A 字段（来自新版 analyze_symbol）
    v = _get(r, "A")
    if v is not None:
        return _as_int_score(v, 50)

    # 兼容旧版：尝试从元数据计算
    slope_atr = _get(r, "trend.slopeATR") or _get(r, "Tm.slopeATR")
    if isinstance(slope_atr, (int, float)):
        return _as_int_score(200 * float(slope_atr), 50)
    dP1h = _get(r, "momentum.dP1h_abs_pct") or _get(r, "dP1h_abs_pct")
    if isinstance(dP1h, (int, float)):
        return _as_int_score(40 + 40 * min(1.0, float(dP1h) / 0.01), 50)
    return 50

def _score_positions(r: Dict[str, Any]) -> int:
    # 优先使用顶层 O 字段（来自新版 analyze_symbol）
    v = _get(r, "O")
    if v is not None:
        return _as_int_score(v, 50)

    # 兼容旧版：尝试从元数据计算
    oi_z = _get(r, "oi.z20") or _get(r, "oi_z20")
    cvd_z = _get(r, "cvd.z20") or _get(r, "cvd_z20")
    vals: List[float] = []
    if isinstance(oi_z, (int, float)):
        vals.append(float(oi_z))
    if isinstance(cvd_z, (int, float)):
        vals.append(float(cvd_z))
    if vals:
        m = sum(vals) / len(vals)
        return _as_int_score(50 + 12 * m, 50)
    return 50

def _score_env(r: Dict[str, Any]) -> int:
    # 优先使用顶层 E 字段（来自新版 analyze_symbol）
    v = _get(r, "E")
    if v is not None:
        return _as_int_score(v, 50)

    # 兼容旧版：尝试从元数据计算
    atr_now = _get(r, "atr.now") or _get(r, "atr_now") or _get(r, "vol.atr_pct")
    if isinstance(atr_now, (int, float)):
        x = float(atr_now)
        if x <= 0:
            return 40
        import math as _m
        score = 60 - 20 * abs(_m.log10(x) - _m.log10(0.01))
        return _as_int_score(score, 50)
    return 50

def _six_scores(r: Dict[str, Any]) -> Tuple[int,int,int,int,int,int]:
    T  = _score_trend(r)
    S  = _score_structure(r)
    V  = _score_volume(r)
    A  = _score_accel(r)
    OI = _score_positions(r)
    E  = _score_env(r)
    return T, S, V, A, OI, E

def _conviction_and_side(r: Dict[str, Any], six: Tuple[int,int,int,int,int,int]) -> Tuple[int, str]:
    # 优先使用概率 P（转换为百分比）
    prob = _get(r, "probability")
    if isinstance(prob, (int, float)):
        conv = int(round(prob * 100))
    else:
        # 兜底：使用六维平均分
        conv = int(round(sum(six) / 6))

    side = (_get(r, "side") or _get(r, "publish.side") or "").lower()
    # normalize side label
    if side in ("long", "buy", "bull", "多", "做多"):
        side_lbl = "🟩 做多"
    elif side in ("short", "sell", "bear", "空", "做空"):
        side_lbl = "🟥 做空"
    else:
        side_lbl = "🟦 中性"
    return conv, side_lbl

# ---------- main render ----------

def _header_lines(r: Dict[str, Any], is_watch: bool) -> Tuple[str, str]:
    sym = _get(r, "symbol") or _get(r, "ticker") or _get(r, "sym") or "—"
    price = (
        _get(r, "price")
        or _get(r, "last")
        or _get(r, "one_24h.lastPrice")
        or _get(r, "quote.last")
    )
    price_s = _fmt_price(price)

    ttl_h = int(_ttl_hours(r))
    # compute six + conviction/side
    six = _six_scores(r)
    conv, side_lbl = _conviction_and_side(r, six)

    line1 = f"🔹 {sym} · 现价 {price_s}"
    tag = "观察" if is_watch else "正式"
    icon = "👀" if is_watch else "📣"
    line2 = f"{icon} {tag} · {side_lbl} {conv}% · 有效期{ttl_h}h"
    return line1, line2

def _six_block(r: Dict[str, Any]) -> str:
    T, S, V, A, OI, E = _six_scores(r)

    # 获取方向
    side = (_get(r, "side") or "").lower()
    is_long = side in ("long", "buy", "bull", "多", "做多")

    lines = []
    lines.append(f"• 趋势 {_emoji_by_score(T)} {T:>2d} —— {_desc_trend(T, is_long)}")
    lines.append(f"• 结构 {_emoji_by_score(S)} {S:>2d} —— {_desc_structure(S)}")
    lines.append(f"• 量能 {_emoji_by_score(V)} {V:>2d} —— {_desc_volume(V)}")
    lines.append(f"• 加速 {_emoji_by_score(A)} {A:>2d} —— {_desc_accel(A, is_long)}")
    lines.append(f"• 持仓 {_emoji_by_score(OI)} {OI:>2d} —— {_desc_positions(OI, is_long)}")
    lines.append(f"• 环境 {_emoji_by_score(E)} {E:>2d} —— {_desc_env(E)}")
    return "\n".join(lines)

def _note_and_tags(r: Dict[str, Any], is_watch: bool) -> str:
    note = _get(r, "note") or _get(r, "publish.note") or ""
    tag = "#watch" if is_watch else "#trade"
    sym = _get(r, "symbol")
    symtag = f" #{sym}" if isinstance(sym, str) and sym else ""
    tail = ""
    if note:
        tail += f"备注：{note}\n"
    tail += f"{tag}{symtag}"
    return tail

def render_signal(r: Dict[str, Any], is_watch: bool = False) -> str:
    """Unified template for both watch and trade."""
    l1, l2 = _header_lines(r, is_watch)
    six = _six_block(r)
    body = f"{l1}\n{l2}\n\n六维分析\n{six}\n\n{_note_and_tags(r, is_watch)}"
    return body

def render_watch(r: Dict[str, Any]) -> str:
    return render_signal(r, is_watch=True)

def render_trade(r: Dict[str, Any]) -> str:
    return render_signal(r, is_watch=False)