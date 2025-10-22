# coding: utf-8
"""
Unified Telegram template (prime & watch) — FORCE FULL 6-DIM OUTPUT
- 标题： [手动](可选) + 观察(可选) + 方向 + 概率% + TTL
- 第二行：🔹 符号 · 现价（动态小数位、去尾 0）
- 六维：恒显示（趋势/结构/量能/加速/持仓/环境），0 分也显示，并给出简短解释
- 不追加 UTC 有效期落款行；计划(入场/止损/TP)若有则显示
"""
import os, html
from typing import Any, Dict, Optional, Tuple

__TEMPLATE_SIG__ = "tmpl:force-6dims+show-zero@2025-10-22-11:05Z"

# ---------- 基础格式化 ----------

def _fmt_num(x: Any, nd: int = 3) -> str:
    try:
        f = float(x)
        if nd == 0:
            return str(int(round(f)))
        s = f"{f:.{nd}f}"
        return s.rstrip("0").rstrip(".")
    except Exception:
        return "—"

def _pick(d: Dict, *keys, default=None):
    for k in keys:
        if isinstance(d, dict) and k in d:
            return d[k]
    return default

def _fmt_prob_pct(p: Any) -> Optional[int]:
    try:
        f = float(p)
    except Exception:
        return None
    pct = f*100 if 0 <= f <= 1 else f
    try:
        return int(round(pct))
    except Exception:
        return None

def _dot(v: Any) -> str:
    try:
        v = float(v)
    except Exception:
        return "⚪"
    if v >= 80: return "🟢"
    if v >= 65: return "🟡"
    return "🔴"

# --- 动态小数位（含 config/meta.pricing） + 去尾 0 ---
def _decimals_from_pricing(r: Dict) -> Optional[int]:
    pr = (r.get("pricing") or {}) if isinstance(r, dict) else {}
    meta = r.get("meta") if isinstance(r, dict) else {}
    if isinstance(meta, dict):
        pr2 = meta.get("pricing") or {}
        if isinstance(pr2, dict):
            pr = {**pr2, **pr}
    for k in ("tick_decimals","price_decimals","decimals"):
        v = pr.get(k)
        if isinstance(v, int) and 0 <= v <= 12:
            return v
    return None

def _auto_decimals(f: float) -> int:
    a = abs(f)
    if a >= 1000: return 2
    if a >= 100:  return 3
    if a >= 1:    return 4
    if a >= 0.1:  return 5
    if a >= 0.01: return 6
    if a >= 0.001:return 7
    return 8

def _fmt_code_px(x, r=None):
    try:
        f = float(x)
    except Exception:
        return "<code>—</code>"
    nd = _decimals_from_pricing(r) if isinstance(r, dict) else None
    if nd is None:
        nd = _auto_decimals(f)
    s = f"{f:.{nd}f}".rstrip("0").rstrip(".")
    return f"<code>{s}</code>"

# ---------- 分数提取/解释 ----------

def _to_0_100(v: Any) -> Optional[float]:
    """把 0~1 小数统一为 0~100，其他值原样返回；非数值返回 None。"""
    try:
        f = float(v)
    except Exception:
        return None
    if 0.0 <= f <= 1.0:
        return f * 100.0
    return f

def _norm_score_value(v: Any):
    # 支持 dict/bool/数值
    if isinstance(v, dict):
        for k in ("score","value","v","s"):
            if k in v:
                out = _to_0_100(v[k])
                return out if out is not None else v[k]
        if "pass" in v:
            return bool(v["pass"])
        return None
    if isinstance(v, (int, float)):
        out = _to_0_100(v)
        return out if out is not None else v
    return v

def _score_lookup(r: Dict) -> Dict[str, Any]:
    """汇总各容器，并支持 T/A/S/V/O/E 别名。"""
    buckets = [
        r.get("scores"), r.get("dim_scores"), r.get("dimensions"),
        r.get("six"), r.get("evidence"), r.get("checks"), r.get("dims"),
        (r.get("analysis") or {}).get("scores") if isinstance(r.get("analysis"), dict) else None,
        (r.get("metrics")  or {}).get("scores") if isinstance(r.get("metrics"),  dict) else None,
        (r.get("features") or {}).get("scores") if isinstance(r.get("features"), dict) else None,
    ]
    sc: Dict[str, Any] = {}
    for b in buckets:
        if isinstance(b, dict): sc.update(b)
    for k in ("trend","trend_score","structure","struct","volume","vol",
              "accel","acceleration","oi","open_interest","env","environment",
              "T","A","S","V","O","E"):
        if k in r and k not in sc: sc[k]=r[k]
    mapping = {
        "趋势":  ("trend","trend_score","T"),
        "结构":  ("structure","struct","S"),
        "量能":  ("volume","vol","V"),
        "加速":  ("accel","acceleration","A"),
        "持仓":  ("oi","open_interest","O"),
        "环境":  ("env","environment","E"),
    }
    out: Dict[str, Any] = {}
    for name, alts in mapping.items():
        val=None
        for k in alts:
            if k in sc:
                val = _norm_score_value(sc[k])
                break
        out[name]=val
    return out

def _score_notes(r: Dict) -> Dict[str,str]:
    """六维解释：notes / scores_meta / analysis.notes"""
    buckets = [ r.get("notes"), r.get("scores_meta"),
                (r.get("analysis") or {}).get("notes") if isinstance(r.get("analysis"),dict) else None ]
    pool: Dict[str, Any] = {}
    for b in buckets:
        if isinstance(b, dict): pool.update(b)
    alias = {
        "趋势":("trend","T"),
        "结构":("structure","struct","S"),
        "量能":("volume","vol","V"),
        "加速":("accel","acceleration","A"),
        "持仓":("oi","open_interest","O"),
        "环境":("env","environment","E"),
    }
    out={}
    for name,keys in alias.items():
        for k in (name,)+keys:
            if k in pool:
                out[name]=html.escape(str(pool[k]), quote=False)
                break
    return out

def _auto_note(name: str, v: Any) -> str:
    """当上游没给 notes 时，按分值自动生成简短解释（0 分也给解释）。"""
    try:
        x = float(v if v is not None else 0.0)
    except Exception:
        x = 0.0
    if name == "趋势":
        if x >= 80: return "趋势强；多周期同侧"
        if x >= 65: return "趋势良好；回撤可控"
        return "趋势弱/震荡"
    if name == "结构":
        if x >= 80: return "结构连贯；高低点阶梯清晰"
        if x >= 65: return "结构尚可；关键位未被破坏"
        return "结构杂乱/级别相抵"
    if name == "量能":
        if x >= 80: return "放量明显；成交活跃"
        if x >= 65: return "量能温和提升"
        return "量能不足"
    if name == "加速":
        if x >= 80: return "动量强；加速度正向"
        if x >= 65: return "加速改善"
        return "加速不足/有背离风险"
    if name == "持仓":
        if x >= 80: return "OI显著增加；资金跟随"
        if x >= 65: return "OI温和变化"
        return "OI走弱/减仓"
    if name == "环境":
        if x >= 80: return "背景顺风；拥挤度低；空间充足"
        if x >= 65: return "环境中性偏顺"
        return "环境一般/拥挤或空间不足"
    return ""

def _is_zero_like(v):
    try: return float(v)==0.0
    except Exception: return False

# ---------- 交易计划/环境 ----------

def _entry_band(r: Dict) -> Tuple[Optional[Any],Optional[Any]]:
    band = _pick(r, "entry_zone","entry","band","ref_range","range","zone")
    lo = r.get("entry_lo"); hi = r.get("entry_hi")
    if lo is None or hi is None:
        if isinstance(band,(list,tuple)) and len(band)>=2:
            lo,hi = band[0],band[1]
        elif isinstance(band,dict):
            lo,hi = band.get("lo"),band.get("hi")
    return lo,hi

def _stop_loss(r: Dict, side: str):
    sl = _pick(r, "stop","stop_loss","sl")
    if sl is None:
        key = "support" if side in ("long","多") else "resist"
        sl = r.get(key)
    return sl

def _ttl_hours(r: Dict) -> int:
    return _pick(r, "ttl_h","ttl_hours") or _pick(_pick(r,"publish",{}),"ttl_h") or 8

def _env_hint(r: Dict) -> Optional[str]:
    env = _pick(r,"env","environment", default={}) or {}
    bias  = _pick(env,"market_bias","bias")
    crowd = _pick(env,"crowding","crowd","crowd_state")
    Q     = _pick(env,"Q","quality","score","q")
    bits=[]
    if bias: bits.append(str(bias))
    if crowd: bits.append(str(crowd))
    if Q is not None: bits.append(f"Q={_fmt_num(Q,2)}")
    return " · ".join(bits) if bits else None

# ---------- 主渲染 ----------

def render_signal(r: Dict, *, is_watch: bool=False) -> str:
    sym   = _pick(r,"symbol","sym","ticker","—")
    price = _pick(r,"last","price","close","px")

    pu    = _pick(r,"prob_up","probLong","prob")
    pd    = _pick(r,"prob_dn","probShort")
    side  = _pick(r,"side")
    if side not in ("long","short","多","空"):
        if pu is not None and pd is not None:
            side = "long" if float(pu) >= float(pd) else "short"
        elif pu is not None:
            side = "long" if float(pu) >= (0.5 if float(pu)<=1 else 50) else "short"
        else:
            side = "long"

    base = None
    if pu is not None or pd is not None:
        if side in ("long","多"):
            base = float(pu) if pu is not None else (1-float(pd) if float(pd)<=1 else None)
        else:
            base = float(pd) if pd is not None else (1-float(pu) if float(pu)<=1 else None)
    pct_int = _fmt_prob_pct(base if base is not None else pu)

    ttl   = _ttl_hours(r)
    icon  = "🟩" if side in ("long","多") else "🟥"
    word  = "做多" if side in ("long","多") else "做空"
    manual = "[手动] " if os.getenv("ATS_VIA")=="manual" else ""
    prefix = "🟡 观察 · " if is_watch else ""
    title  = f"<b>{manual}{prefix}{icon} {word} {pct_int if pct_int is not None else '—'}% · {ttl}h</b>"

    lines = [title]
    # 第二行：🔹 符号 · 现价
    sym_line = f"🔹 {sym}" + (f" · 现价 {_fmt_code_px(price, r)}" if price is not None else "")
    lines.append(sym_line)

    # 计划（可选）
    lo,hi = _entry_band(r)
    sl = _stop_loss(r, side)
    tp_line = None
    if lo is not None and hi is not None and sl is not None:
        tp_line = "TP1=+1R   TP2≤2.5R（靠近前高）"
    if lo or hi or sl or tp_line:
        lines.append("")
        lines.append("<b>计划</b>")
        if lo is not None and hi is not None:
            lines.append(f"入场 {_fmt_code_px(lo,r)} – {_fmt_code_px(hi,r)}")
        if sl is not None:
            lines.append(f"止损 {_fmt_code_px(sl,r)}")
        if tp_line:
            lines.append(f"止盈 <code>{tp_line}</code>")

    # 六维 ———— 恒显；若上游缺失则按 0 处理；始终有解释
    sc    = _score_lookup(r)
    notes = _score_notes(r)
    lines.append("")
    lines.append("<b>六维分析</b>")

    order = ("趋势","结构","量能","加速","持仓","环境")
    bullets=[]
    for name in order:
        raw_v = sc.get(name)
        # 缺失视作 0
        v = 0.0 if raw_v is None else raw_v
        # 解释：优先 notes，没有则自动生成（包含 0 分场景）
        explain = notes.get(name) if isinstance(notes, dict) else None
        if not explain or not str(explain).strip():
            explain = _auto_note(name, v)
        # 渲染
        if isinstance(v, bool):
            bullets.append(f"• {name} {'✅' if v else '❌'} —— {explain}")
        else:
            vv = 0.0
            try:
                vv = float(v)
            except Exception:
                vv = 0.0
            dot = _dot(vv)
            bullets.append(f"• {name} {dot} {_fmt_num(vv,0)} —— {explain}")

    lines.extend(bullets)

    # 环境/失效（可选）
    env_hint = _env_hint(r)
    if env_hint:
        lines.append("")
        lines.append(f"<b>环境</b> {env_hint}")
    invalid = _pick(r,"invalidations","fails","kill_switch")
    if invalid:
        if isinstance(invalid,(list,tuple)):
            invalid = "  ".join(map(str, invalid))
        lines.append(f"<b>失效</b> {invalid}")

    # 末尾追加一个极短签名，便于确认是否加载到了这份模板
    lines.append(f"\n<code>{__TEMPLATE_SIG__}</code>")

    return "\n".join(lines)

def render_prime(r: Dict) -> str:
    return render_signal(r, is_watch=False)

def render_watch(r: Dict) -> str:
    return render_signal(r, is_watch=True)