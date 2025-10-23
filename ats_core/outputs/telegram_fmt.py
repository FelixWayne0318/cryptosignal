# coding: utf-8
from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple

"""
正式 / 观察 —— 统一模板（友好给小白，也保留专业关键信息）
改动：
- 第一行改为：🔹 BTCUSDT · 现价 ...
- 第二行改为：📣 正式 · 🟦 中性 48% · 8h（观察：👀 观察）
- 无有效分数的维度显示 “—”，不再强行用 50 占位
- 总评仅对有值维度求均值，过少则显示 “—”
"""

def _is_num(x: Any) -> bool:
    return isinstance(x, (int, float)) and (not math.isnan(float(x)))

def _fmt_price(p: Any) -> str:
    if not _is_num(p):
        return "—"
    # 粗略格式化：>1000 保留 1 位；否则 2 位
    p = float(p)
    if abs(p) >= 1000:
        return f"{p:,.1f}"
    return f"{p:,.2f}"

def _ttl_hours(r: Dict[str, Any]) -> str:
    # r["ttl_h"] / r["ttl_hours"] / r["publish"]["ttl_h"] / 默认 8
    ttl = None
    for k in ("ttl_h", "ttl_hours"):
        v = r.get(k)
        if _is_num(v):
            ttl = float(v)
            break
    if ttl is None:
        pub = r.get("publish") or {}
        v = pub.get("ttl_h")
        if _is_num(v):
            ttl = float(v)
    if ttl is None:
        ttl = 8.0
    return f"{ttl:.0f}h"

def _pick_price(r: Dict[str, Any]) -> Optional[float]:
    # 常见路径：r["price"] or r["lastPrice"] or r["c"] or r["close"]
    for k in ("price", "lastPrice", "c", "close"):
        v = r.get(k)
        if _is_num(v):
            return float(v)
    # 也可能有 r["prices"]["last"]
    prices = r.get("prices") or {}
    v = prices.get("last")
    if _is_num(v):
        return float(v)
    return None

def _score_from(r: Dict[str, Any], *paths: Tuple[str, ...]) -> Optional[float]:
    """
    从若干候选路径里找一个数值，找不到就 None
    例：
      _score_from(r, ("scores","trend"), ("trend","score"), ("T",))
    """
    for path in paths:
        cur: Any = r
        ok = True
        for p in path:
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            else:
                ok = False
                break
        if ok and _is_num(cur):
            return float(cur)
    return None

def _score_color(v: float) -> str:
    # 颜色：<40 红 🔴；40~59 蓝 🟦；>=60 绿 🟢
    if v < 40:
        return "🔴"
    if v >= 60:
        return "🟢"
    return "🟦"

def _score_word(v: float) -> str:
    if v < 30:
        return "偏弱"
    if v < 40:
        return "较弱"
    if v < 50:
        return "略弱"
    if v < 60:
        return "中性"
    if v < 70:
        return "偏强"
    return "较强"

def _line_dim(name: str, v: Optional[float], extra: str = "") -> str:
    if v is None:
        return f"• {name} —"
    return f"• {name} {_score_color(v)} {int(round(v))} —— {_score_word(v)}{(' · ' + extra) if extra else ''}"

def _overall(r: Dict[str, Any]) -> Optional[float]:
    # 候选路径：r["scores"]["overall"] / r["overall"]
    ov = _score_from(r, ("scores", "overall"), ("overall",))
    if _is_num(ov):
        return float(ov)
    # 否则由各维度均值
    dims = []
    for keypaths in (
        (("scores","trend"), ("trend","score"), ("T",)),
        (("scores","structure"), ("structure","score")),
        (("scores","volume"), ("volume","score")),
        (("scores","acceleration"), ("acceleration","score")),
        (("scores","oi"), ("oi","score"), ("open_interest","score")),
        (("scores","environment"), ("environment","score"), ("env","score")),
    ):
        v = _score_from(r, *keypaths)
        if v is not None:
            dims.append(v)
    if len(dims) >= 2:
        return sum(dims) / len(dims)
    return None

def _header_title(kind: str) -> str:
    # kind = "watch" | "trade"
    return "👀 观察" if kind == "watch" else "📣 正式"

def _header_line2(kind: str, overall: Optional[float], ttl: str) -> str:
    if overall is None:
        return f"{_header_title(kind)} · — · {ttl}"
    return f"{_header_title(kind)} · {_score_color(overall)} {_score_word(overall)} {int(round(overall))}% · {ttl}"

def _build_body(r: Dict[str, Any], kind: str) -> str:
    # 价格
    price = _fmt_price(_pick_price(r))

    # 六维分数（尽量“找得到就用”）
    trend = _score_from(r, ("scores","trend"), ("trend","score"), ("T",))
    structure = _score_from(r, ("scores","structure"), ("structure","score"))
    volume = _score_from(r, ("scores","volume"), ("volume","score"))
    accel = _score_from(r, ("scores","acceleration"), ("acceleration","score"))
    oi = _score_from(r, ("scores","oi"), ("oi","score"), ("open_interest","score"))
    env = _score_from(r, ("scores","environment"), ("environment","score"), ("env","score"))

    ttl = _ttl_hours(r)
    ov = _overall(r)

    sym = r.get("symbol") or r.get("sym") or r.get("ticker") or "—"

    # --- 输出 ---
    out = []
    out.append(f"🔹 {sym} · 现价 {price}")
    out.append(_header_line2(kind, ov, ttl))
    out.append("")
    out.append("六维分析")
    out.append(_line_dim("趋势", trend))
    out.append(_line_dim("结构", structure))
    out.append(_line_dim("量能", volume))
    out.append(_line_dim("加速", accel))
    out.append(_line_dim("持仓", oi))
    out.append(_line_dim("环境", env))

    # 备注
    note = ""
    # 自由字段：r["note"] / r["publish"]["note"]
    if isinstance(r.get("note"), str) and r["note"].strip():
        note = r["note"].strip()
    elif isinstance(r.get("publish"), dict):
        n2 = r["publish"].get("note")
        if isinstance(n2, str) and n2.strip():
            note = n2.strip()
    if note:
        out.append("")
        out.append(f"备注：{note}")

    return "\n".join(out)

def render_watch(r: Dict[str, Any]) -> str:
    return _build_body(r, kind="watch")

def render_trade(r: Dict[str, Any]) -> str:
    return _build_body(r, kind="trade")