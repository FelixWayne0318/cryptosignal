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
    """
    分数转emoji（支持负数）

    对于正常指标（0-100）：
    - >= 60: 🟢 (强)
    - 40-60: 🟡 (中)
    - < 40: 🔴 (弱)

    对于带符号指标（-100到+100，如CVD）：
    - >= 60: 🟢 (强买入压力)
    - 20~60: 🟡 (中等买入)
    - -20~20: 🟡 (均衡)
    - -60~-20: 🟡 (中等卖出)
    - <= -60: 🔴 (强卖出压力)
    """
    # 处理带符号指标（CVD）
    if s < 0:
        if s <= -60:
            return "🔴"  # 强烈卖出压力
        else:
            return "🟡"  # 中等/轻微卖出或均衡

    # 处理正数
    if s >= 60:
        return "🟢"  # 强买入压力或强指标
    else:
        return "🟡"  # 中等/轻微或均衡

def _desc_trend(s: int, is_long: bool = True, Tm: int = None) -> str:
    """
    描述趋势

    Args:
        s: T 分数 (0-100)
        is_long: 是否做多
        Tm: 趋势方向 (-1=空头, 0=震荡, 1=多头)
    """
    if is_long:
        # 做多视角
        if s >= 80: desc = "强势/上行倾向"
        elif s >= 60: desc = "温和上行或多头占优"
        elif s >= 40: desc = "中性/震荡"
        else: desc = "趋势弱/震荡或下行倾向"
    else:
        # 做空视角
        if s >= 80: desc = "强势/下行倾向"
        elif s >= 60: desc = "温和下行或空头占优"
        elif s >= 40: desc = "中性/震荡"
        else: desc = "趋势弱/震荡或上行倾向"

    # 附加趋势方向
    if Tm is not None:
        if Tm > 0:
            desc += " [多头]"
        elif Tm < 0:
            desc += " [空头]"
        else:
            desc += " [震荡]"

    return desc

def _desc_structure(s: int, theta: float = None) -> str:
    """
    描述结构

    Args:
        s: S 分数 (0-100)
        theta: 结构一致性角度 (0.25-0.60)
    """
    if s >= 80: desc = "结构清晰/多周期共振"
    elif s >= 60: desc = "结构尚可/回踩确认"
    elif s >= 40: desc = "结构一般/级别分歧"
    else: desc = "结构杂乱/级别相抵"

    # 附加结构角度
    if theta is not None:
        desc += f" (θ={theta:.2f})"

    return desc

def _desc_volume(s: int, v5v20: float = None) -> str:
    """
    描述量能

    Args:
        s: V 分数 (0-100)
        v5v20: 短期/长期量能比率
    """
    if s >= 80: desc = "放量明显/跟随积极"
    elif s >= 60: desc = "量能偏强/逐步释放"
    elif s >= 40: desc = "量能中性"
    else: desc = "量能不足/跟随意愿弱"

    # 附加量能比率
    if v5v20 is not None:
        desc += f" (v5/v20={v5v20:.2f})"

    return desc

def _desc_accel(s: int, is_long: bool = True, cvd6: float = None) -> str:
    """
    描述加速

    Args:
        s: A 分数 (0-100)
        is_long: 是否做多
        cvd6: CVD 6小时变化百分比
    """
    direction = "上行" if is_long else "下行"
    if s >= 80: desc = f"{direction}加速强/持续性好"
    elif s >= 60: desc = f"{direction}加速偏强/待确认"
    elif s >= 40: desc = "加速一般"
    else: desc = "加速不足/有背离风险"

    # 附加 CVD 变化
    if cvd6 is not None:
        cvd_pct = cvd6 * 100
        if cvd_pct >= 0:
            desc += f" (CVD+{cvd_pct:.1f}%)"
        else:
            desc += f" (CVD{cvd_pct:.1f}%)"

    return desc

def _desc_cvd_flow(s: int, is_long: bool = True, cvd6: float = None,
                   consistency: float = None, is_consistent: bool = None) -> str:
    """
    描述CVD资金流（明确买入/卖出方向 + 持续性）

    Args:
        s: C 分数 (-100到+100，带符号！)
        is_long: 是否做多（已弃用，仅保留兼容性）
        cvd6: CVD 6小时变化（已归一化到价格）
        consistency: （已弃用，保留参数兼容性）
        is_consistent: 是否持续（R²>=0.7，变化平稳）

    分数对称映射：
        ≥ +80: 强劲资金流入
        ≥ +60: 偏强资金流入
        ≥ +40: 中等资金流入
        ≥ +20: 轻微资金流入
        -20~+20: 资金流平衡
        ≤ -20: 轻微资金流出
        ≤ -40: 中等资金流出
        ≤ -60: 偏强资金流出
        ≤ -80: 强劲资金流出
    """
    # 根据分数正负和强度确定资金流方向
    # 正数 = 资金流入，负数 = 资金流出
    if s >= 80:
        desc = "强劲资金流入"
    elif s >= 60:
        desc = "偏强资金流入"
    elif s >= 40:
        desc = "中等资金流入"
    elif s >= 20:
        desc = "轻微资金流入"
    elif s >= -20:
        desc = "资金流平衡"
    elif s >= -40:
        desc = "轻微资金流出"
    elif s >= -60:
        desc = "中等资金流出"
    elif s >= -80:
        desc = "偏强资金流出"
    else:  # s < -80
        desc = "强劲资金流出"

    # 附加 CVD 6小时变化百分比（归一化到价格）
    if cvd6 is not None:
        cvd_pct = cvd6 * 100
        if cvd_pct >= 0:
            desc += f" (CVD+{cvd_pct:.1f}%"
        else:
            desc += f" (CVD{cvd_pct:.1f}%"

        # 附加持续性标注（基于R²拟合优度）
        if is_consistent is not None:
            if is_consistent:
                desc += ", 持续✓"  # R²>=0.7，变化平稳
            else:
                desc += ", 震荡"    # R²<0.7，波动大

        desc += ")"

    return desc

def _desc_positions(s: int, is_long: bool = True, oi24h_pct: float = None) -> str:
    """
    描述持仓

    Args:
        s: O 分数 (0-100)
        is_long: 是否做多
        oi24h_pct: OI 24小时变化百分比
    """
    side = "多头" if is_long else "空头"
    if s >= 80: desc = f"{side}持仓显著增长/可能拥挤"
    elif s >= 60: desc = f"{side}持仓温和上升/活跃"
    elif s >= 40: desc = "持仓温和变化"
    else: desc = f"{side}持仓走弱/去杠杆"

    # 附加 OI 24h 变化
    if oi24h_pct is not None:
        if oi24h_pct >= 0:
            desc += f" (OI+{oi24h_pct:.1f}%)"
        else:
            desc += f" (OI{oi24h_pct:.1f}%)"

    return desc

def _desc_env(s: int, chop: float = None) -> str:
    """
    描述环境

    Args:
        s: E 分数 (0-100)
        chop: Chop 指数 (0-100，越高越震荡)
    """
    if s >= 80: desc = "环境友好/空间充足"
    elif s >= 60: desc = "环境偏友好"
    elif s >= 40: desc = "环境一般/空间有限"
    else: desc = "环境不佳/波动或流动性掣肘"

    # 附加 Chop 指数
    if chop is not None:
        desc += f" (Chop={chop:.0f})"

    return desc

def _desc_fund_leading(s: int, leading_raw: float = None) -> str:
    """
    描述资金领先性

    Args:
        s: F 分数 (-100 到 +100)
        leading_raw: 真实的领先性数值（用于调试，可选）
    """
    # 带符号的描述体系（-100 到 +100）
    if s >= 60:
        desc = "资金强势领先价格 (蓄势待发)"
    elif s >= 30:
        desc = "资金温和领先价格 (机会较好)"
    elif s >= 10:
        desc = "资金略微领先 (同步偏好)"
    elif s >= -10:
        desc = "资金价格同步 (中性)"
    elif s >= -30:
        desc = "价格略微领先 (同步偏差)"
    elif s >= -60:
        desc = "价格温和领先资金 (追高风险)"
    else:
        desc = "价格强势领先资金 (风险很大)"

    return desc

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

def _score_momentum(r: Dict[str, Any]) -> int:
    v = _get(r, "M")
    return _as_int_score(v, 50)

def _score_cvd_flow(r: Dict[str, Any]) -> int:
    """
    获取CVD分数（支持负数：-100到+100）

    注意：CVD现在是带符号的，正数=买入压力，负数=卖出压力
    """
    v = _get(r, "C")
    if v is None:
        return 0  # 默认0=中性
    try:
        # 直接转换，不做0-100限制
        score = int(round(float(v)))
        # 限制在-100到+100
        return max(-100, min(100, score))
    except Exception:
        return 0

def _score_fund_leading(r: Dict[str, Any]) -> int:
    v = _get(r, "F_score") or _get(r, "F")
    return _as_int_score(v, 50)

def _six_scores(r: Dict[str, Any]) -> Tuple[int,int,int,int,int,int,int]:
    """兼容：返回T/S/V/M/C/O/E/F（实际8维）"""
    T  = _score_trend(r)
    S  = _score_structure(r)
    V  = _score_volume(r)
    M  = _score_momentum(r)
    C  = _score_cvd_flow(r)
    OI = _score_positions(r)
    E  = _score_env(r)
    F  = _score_fund_leading(r)
    return T, S, V, M, OI, E, F  # 返回7维+F（去掉C保持兼容）

def _conviction_and_side(r: Dict[str, Any], seven: Tuple[int,int,int,int,int,int,int]) -> Tuple[int, str]:
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
    # 不再区分观察/正式，统一为正式信号
    line2 = f"{side_lbl} {conv}% · 有效期{ttl_h}h"
    return line1, line2

def _six_block(r: Dict[str, Any]) -> str:
    T, S, V, M, OI, E, F = _six_scores(r)
    C = _score_cvd_flow(r)  # 单独获取C

    # 获取方向
    side = (_get(r, "side") or "").lower()
    is_long = side in ("long", "buy", "bull", "多", "做多")

    # 获取各维度的真实数据
    T_meta = _get(r, "scores_meta.T") or {}
    S_meta = _get(r, "scores_meta.S") or {}
    V_meta = _get(r, "scores_meta.V") or {}
    M_meta = _get(r, "scores_meta.M") or {}
    C_meta = _get(r, "scores_meta.C") or {}
    O_meta = _get(r, "scores_meta.O") or {}
    E_meta = _get(r, "scores_meta.E") or {}
    F_meta = _get(r, "scores_meta.F") or {}

    # 提取具体指标
    Tm = T_meta.get("Tm")
    theta = S_meta.get("theta")
    v5v20 = V_meta.get("v5v20")
    slope = M_meta.get("slope_now")
    cvd6 = C_meta.get("cvd6")
    cvd_consistency = C_meta.get("consistency")
    cvd_is_consistent = C_meta.get("is_consistent")
    oi24h_pct = O_meta.get("oi24h_pct")
    chop = E_meta.get("chop")
    leading_raw = F_meta.get("leading_raw")

    lines = []
    lines.append(f"• 趋势 {_emoji_by_score(T)} {T:>2d} —— {_desc_trend(T, is_long, Tm)}")
    lines.append(f"• 动量 {_emoji_by_score(M)} {M:>2d} —— 价格动量")
    lines.append(f"• 资金流 {_emoji_by_score(C)} {C:+4d} —— {_desc_cvd_flow(C, is_long, cvd6, cvd_consistency, cvd_is_consistent)}")  # 带符号显示+持续性
    lines.append(f"• 结构 {_emoji_by_score(S)} {S:>2d} —— {_desc_structure(S, theta)}")
    lines.append(f"• 量能 {_emoji_by_score(V)} {V:>2d} —— {_desc_volume(V, v5v20)}")
    lines.append(f"• 持仓 {_emoji_by_score(OI)} {OI:>2d} —— {_desc_positions(OI, is_long, oi24h_pct)}")
    lines.append(f"• 环境 {_emoji_by_score(E)} {E:>2d} —— {_desc_env(E, chop)}")

    # F调节器信息（所有信号都显示）
    F_adj = _get(r, "F_adjustment", 1.0)
    f_desc = _desc_fund_leading(F)
    lines.append(f"\n⚡ {f_desc} (F={F:+d}) → 概率调整 ×{F_adj:.2f}")

    return "\n".join(lines)

def _pricing_block(r: Dict[str, Any]) -> str:
    """生成价格信息块（入场、止损、止盈）"""
    pricing = _get(r, "pricing") or {}
    if not pricing:
        return ""

    lines = []

    # 入场区间
    entry_lo = pricing.get("entry_lo")
    entry_hi = pricing.get("entry_hi")
    if entry_lo is not None and entry_hi is not None:
        if abs(entry_lo - entry_hi) < 0.0001:
            lines.append(f"📍 入场价: {_fmt_price(entry_lo)}")
        else:
            lines.append(f"📍 入场区间: {_fmt_price(entry_lo)} - {_fmt_price(entry_hi)}")

    # 止损
    sl = pricing.get("sl")
    if sl is not None:
        lines.append(f"🛑 止损: {_fmt_price(sl)}")

    # 止盈
    tp1 = pricing.get("tp1")
    tp2 = pricing.get("tp2")
    if tp1 is not None:
        lines.append(f"🎯 止盈1: {_fmt_price(tp1)}")
    if tp2 is not None:
        lines.append(f"🎯 止盈2: {_fmt_price(tp2)}")

    if lines:
        return "\n" + "\n".join(lines)
    return ""

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
    pricing = _pricing_block(r)
    # 价格信息放在七维分析前面（入场区间前空一行）
    body = f"{l1}\n{l2}\n{pricing}\n\n七维分析\n{six}\n\n{_note_and_tags(r, is_watch)}"
    return body

def render_watch(r: Dict[str, Any]) -> str:
    return render_signal(r, is_watch=True)

def render_trade(r: Dict[str, Any]) -> str:
    return render_signal(r, is_watch=False)