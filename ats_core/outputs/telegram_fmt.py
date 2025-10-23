# coding: utf-8
from __future__ import annotations
from typing import Any, Dict, Sequence
import math
import html

def _pick(d: Any, *args, default=None):
    """
    兼容写法：
      _pick(r, "ttl_h", "ttl_hours")
      _pick(r, "publish", {})
      _pick(r, "publish", default={})
      _pick(r, "publish", {}, default=8)
    规则：
      - 最后一个“非字符串”的位置参数，视为默认值（若 default 未显式传入）
      - 逐个键尝试命中；若 d 非 dict，或都未命中，返回默认值
    """
    _default = default
    keys = list(args)
    if keys and not isinstance(keys[-1], str):
        if _default is None:
            _default = keys[-1]
        keys = keys[:-1]
    if not isinstance(d, dict):
        return _default
    for k in keys:
        if isinstance(k, str) and k in d:
            return d.get(k)
    return _default

def _ttl_hours(r: Dict[str, Any]) -> int:
    v = _pick(r, "ttl_h", "ttl_hours")
    if isinstance(v, (int, float)) and math.isfinite(float(v)):
        return int(v)
    pub = _pick(r, "publish", default={})
    if isinstance(pub, dict):
        v2 = _pick(pub, "ttl_h", default=None)
        if isinstance(v2, (int, float)) and math.isfinite(float(v2)):
            return int(v2)
    return 8

def _fmt_pct(x) -> str:
    try:
        x = float(x)
        s = "+" if x >= 0 else ""
        return f"{s}{x * 100:.2f}%"
    except Exception:
        return "-"

def _fmt_price(x) -> str:
    try:
        return f"{float(x):.6g}"
    except Exception:
        return str(x)

def render_signal(r: Dict[str, Any], is_watch: bool = False) -> str:
    sym = _pick(r, "symbol", "sym", "pair", default="UNKNOWN")
    note = _pick(r, "note", "desc", "comment", default=None)
    ttl = _ttl_hours(r)
    tag = "👀 观察" if is_watch else "🚀 交易"
    header = f"<b>{tag}</b> · <b>{html.escape(str(sym))}</b>"
    lines = [header]

    # 计划：entry/tp/sl（可选）
    entry = _pick(r, "entry", "price", default=None)
    tp = _pick(r, "tp", "take_profit", "targets", default=None)
    sl = _pick(r, "sl", "stop", "stop_loss", default=None)
    if entry is not None or tp is not None or sl is not None:
        lines.append("<b>计划</b>")
        if entry is not None:
            lines.append(f"• 入场：<code>{_fmt_price(entry)}</code>")
        if tp is not None:
            if isinstance(tp, (list, tuple)):
                tp_str = ", ".join(_fmt_price(x) for x in tp[:5])
            else:
                tp_str = _fmt_price(tp)
            lines.append(f"• 止盈：<code>{tp_str}</code>")
        if sl is not None:
            lines.append(f"• 止损：<code>{_fmt_price(sl)}</code>")

    # 趋势（可选）
    trend = _pick(r, "trend", default=None)
    if isinstance(trend, dict):
        slope = _pick(trend, "slopeATR", "slope_atr", default=None)
        ema_ok = _pick(trend, "ema_order_ok", default=None)
        msgs = []
        if slope is not None:
            msgs.append(f"slopeATR={_fmt_price(slope)}")
        if ema_ok is not None:
            msgs.append(f"EMA序={'✓' if ema_ok else '×'}")
        if msgs:
            lines.append("<b>趋势</b>")
            lines.append("• " + " / ".join(msgs))

    # 量能（CVD & OI，均可选）
    cvd_info = _pick(r, "cvd", default=None)
    oi_info = _pick(r, "oi", default=None)
    sub = []
    if isinstance(cvd_info, dict):
        z = _pick(cvd_info, "z20", "zscore", "z", default=None)
        v = _pick(cvd_info, "last", "value", default=None)
        items = []
        if z is not None:
            items.append(f"z20={_fmt_price(z)}")
        if v is not None:
            items.append(f"ΣΔV={_fmt_price(v)}")
        if items:
            sub.append("CVD(" + ", ".join(items) + ")")
    if isinstance(oi_info, dict):
        o = _pick(oi_info, "d1h", "pct_1h", "change_1h", default=None)
        if o is not None:
            sub.append("OIΔ1h=" + _fmt_pct(o))
    if sub:
        lines.append("<b>量能</b>")
        lines.append("• " + " / ".join(sub))

    # 备注（可选）
    if isinstance(note, str) and note.strip():
        lines.append("<b>备注</b>")
        lines.append(html.escape(note.strip()))

    # TTL
    lines.append(f"<i>TTL ~{ttl}h</i>")
    return "\n".join(lines)

def render_watch(r: Dict[str, Any]) -> str:
    return render_signal(r, is_watch=True)

def render_prime(r: Dict[str, Any]) -> str:
    return render_signal(r, is_watch=False)

# 兼容：有些地方可能叫 render_base，这里直接复用
def render_base(r: Dict[str, Any]) -> str:
    return render_watch(r)