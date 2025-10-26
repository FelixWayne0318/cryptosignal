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

def _clamp(x: float, lo: float = -100.0, hi: float = 100.0) -> float:
    """v3.0: 支持±100范围"""
    try:
        v = float(x)
    except Exception:
        return 0.0  # 中性改为0
    return max(lo, min(hi, v))

def _as_int_score(x: Any, default: int = 0) -> int:
    """v3.0: 支持±100范围，默认值改为0（中性）"""
    try:
        if x is None:
            return default
        if isinstance(x, (list, tuple)) and len(x) > 0:
            # allow last value fallback
            try:
                x = x[-1]
            except Exception:
                pass
        return int(round(_clamp(float(x), -100.0, 100.0)))
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

# ---------- score → emoji / description （v3.0：支持±100）----------

def _emoji_by_score(s: int) -> str:
    """
    根据分数返回emoji（v3.0：支持±100）

    使用绝对值判断强度：
    - |s| >= 60: 🟢 强
    - |s| >= 20: 🟡 中
    - |s| < 20: ⚪ 弱/中性
    """
    abs_s = abs(s)
    if abs_s >= 60:
        return "🟢"  # 强信号（无论正负）
    if abs_s >= 20:
        return "🟡"  # 中等信号
    return "⚪"  # 弱信号/中性

def _desc_trend(s: int, is_long: bool = True, Tm: int = None) -> str:
    """
    描述趋势（v3.0：支持±100对称设计）

    Args:
        s: T 分数 (-100~+100)
        is_long: 是否做多（已弃用，保留兼容性）
        Tm: 趋势方向 (-1=空头, 0=震荡, 1=多头)
    """
    # v3.0：使用分数符号判断方向，绝对值判断强度
    abs_s = abs(s)

    if s > 0:
        # 正分：上升趋势
        if abs_s >= 80: desc = "强势上行"
        elif abs_s >= 60: desc = "温和上行或多头占优"
        elif abs_s >= 20: desc = "偏多/震荡上行"
        else: desc = "中性/震荡"
    elif s < 0:
        # 负分：下降趋势
        if abs_s >= 80: desc = "强势下行"
        elif abs_s >= 60: desc = "温和下行或空头占优"
        elif abs_s >= 20: desc = "偏空/震荡下行"
        else: desc = "中性/震荡"
    else:
        # 0分：完全中性
        desc = "中性/震荡"

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
    描述结构（v3.0：支持±100对称设计）

    Args:
        s: S 分数 (-100~+100)
        theta: 结构一致性角度 (0.25-0.60)
    """
    # v3.0：使用绝对值判断质量，符号判断方向
    abs_s = abs(s)

    # 质量描述
    if abs_s >= 80: quality = "结构清晰/多周期共振"
    elif abs_s >= 60: quality = "结构尚可/回踩确认"
    elif abs_s >= 20: quality = "结构一般/级别分歧"
    else: quality = "结构杂乱/级别相抵"

    # 方向描述
    if s > 20:
        desc = f"{quality} [上升]"
    elif s < -20:
        desc = f"{quality} [下降]"
    else:
        desc = quality  # 中性，不标注方向

    # 附加结构角度
    if theta is not None:
        desc += f" (θ={theta:.2f})"

    return desc

def _desc_volume(s: int, v5v20: float = None) -> str:
    """
    描述量能（v3.0：支持±100对称设计）

    Args:
        s: V 分数 (-100~+100)
        v5v20: 短期/长期量能比率
    """
    # v3.0：正=放量，负=缩量，绝对值=强度
    abs_s = abs(s)

    if s > 0:
        # 正分：放量
        if abs_s >= 80: desc = "放量明显/跟随积极"
        elif abs_s >= 60: desc = "量能偏强/逐步释放"
        elif abs_s >= 20: desc = "量能略强"
        else: desc = "量能中性"
    elif s < 0:
        # 负分：缩量
        if abs_s >= 80: desc = "缩量明显/跟随意愿弱"
        elif abs_s >= 60: desc = "量能偏弱/逐步萎缩"
        elif abs_s >= 20: desc = "量能略弱"
        else: desc = "量能中性"
    else:
        desc = "量能中性"

    # 附加量能比率
    if v5v20 is not None:
        desc += f" (v5/v20={v5v20:.2f})"

    return desc

def _desc_accel(s: int, is_long: bool = True, cvd6: float = None) -> str:
    """
    描述加速/动量（v3.0：支持±100对称设计，M和C维度）

    Args:
        s: M/C 分数 (-100~+100)
        is_long: 是否做多（已弃用，保留兼容性）
        cvd6: CVD 6小时变化百分比
    """
    # v3.0：使用符号判断方向，绝对值判断强度
    abs_s = abs(s)

    if s > 0:
        # 正分：上行动量
        if abs_s >= 80: desc = "上行加速强/持续性好"
        elif abs_s >= 60: desc = "上行加速偏强/待确认"
        elif abs_s >= 20: desc = "上行加速一般"
        else: desc = "加速中性"
    elif s < 0:
        # 负分：下行动量
        if abs_s >= 80: desc = "下行加速强/持续性好"
        elif abs_s >= 60: desc = "下行加速偏强/待确认"
        elif abs_s >= 20: desc = "下行加速一般"
        else: desc = "加速中性"
    else:
        desc = "加速中性"

    # 附加 CVD 变化
    if cvd6 is not None:
        cvd_pct = cvd6 * 100
        if cvd_pct >= 0:
            desc += f" (CVD+{cvd_pct:.1f}%)"
        else:
            desc += f" (CVD{cvd_pct:.1f}%)"

    return desc

def _desc_positions(s: int, is_long: bool = True, oi24h_pct: float = None) -> str:
    """
    描述持仓（v3.0：支持±100对称设计）

    Args:
        s: O 分数 (-100~+100)
        is_long: 是否做多（已弃用，保留兼容性）
        oi24h_pct: OI 24小时变化百分比
    """
    # v3.0：正=OI上升（多头增持），负=OI下降（空头减仓）
    abs_s = abs(s)

    if s > 0:
        # 正分：OI上升
        if abs_s >= 80: desc = "持仓显著增长/多头活跃/可能拥挤"
        elif abs_s >= 60: desc = "持仓温和上升/活跃"
        elif abs_s >= 20: desc = "持仓略微上升"
        else: desc = "持仓平稳"
    elif s < 0:
        # 负分：OI下降
        if abs_s >= 80: desc = "持仓显著下降/去杠杆明显"
        elif abs_s >= 60: desc = "持仓温和下降/减仓"
        elif abs_s >= 20: desc = "持仓略微下降"
        else: desc = "持仓平稳"
    else:
        desc = "持仓平稳"

    # 附加 OI 24h 变化
    if oi24h_pct is not None:
        if oi24h_pct >= 0:
            desc += f" (OI+{oi24h_pct:.1f}%)"
        else:
            desc += f" (OI{oi24h_pct:.1f}%)"

    return desc

def _desc_env(s: int, chop: float = None) -> str:
    """
    描述环境（v3.0：支持±100对称设计）

    Args:
        s: E 分数 (-100~+100)
        chop: Chop 指数 (0-100，越高越震荡)
    """
    # v3.0：正=上升空间大（靠近下轨），负=下降空间大（靠近上轨）
    abs_s = abs(s)

    if s > 0:
        # 正分：上升空间大
        if abs_s >= 80: desc = "环境友好/上升空间充足"
        elif abs_s >= 60: desc = "环境偏友好/偏向上行"
        elif abs_s >= 20: desc = "环境一般/略偏上行"
        else: desc = "环境中性"
    elif s < 0:
        # 负分：下降空间大
        if abs_s >= 80: desc = "环境友好/下降空间充足"
        elif abs_s >= 60: desc = "环境偏友好/偏向下行"
        elif abs_s >= 20: desc = "环境一般/略偏下行"
        else: desc = "环境中性"
    else:
        desc = "环境中性"

    # 附加 Chop 指数
    if chop is not None:
        desc += f" (Chop={chop:.0f})"

    return desc

def _desc_fund_leading(s: int, leading_raw: float = None) -> str:
    """
    描述资金领先性（v3.0：支持±100对称设计）

    Args:
        s: F 分数 (-100~+100)
        leading_raw: 真实的领先性数值（可以是负数）
    """
    # v3.0：正=资金领先，负=价格领先，绝对值=强度
    if s >= 60:
        desc = "资金强势领先/蓄势待发"
    elif s >= 20:
        desc = "资金略微领先/机会较好"
    elif s >= -20:
        desc = "资金价格同步/中性"
    elif s >= -60:
        desc = "价格略微领先/追高风险"
    else:
        desc = "价格大幅领先/风险很大"

    # 如果有真实数值，附加显示
    if leading_raw is not None:
        leading_int = int(round(leading_raw))
        if leading_raw >= 0:
            return f"{desc} (资金领先+{leading_int})"
        else:
            return f"{desc} (价格领先{leading_int})"

    return desc

# ---------- extract scores robustly ----------

def _score_trend(r: Dict[str, Any]) -> int:
    # 优先使用顶层 T 字段（来自新版 analyze_symbol）
    v = _get(r, "T")
    if v is None:
        v = _get(r, "trend.score")
    return _as_int_score(v, 0)  # v3.0: 中性改为0

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
    return _as_int_score(v, 0)  # v3.0: 中性改为0

def _score_volume(r: Dict[str, Any]) -> int:
    # 优先使用顶层 V 字段（来自新版 analyze_symbol）
    v = _get(r, "V")
    if v is not None:
        return _as_int_score(v, 0)  # v3.0: 中性改为0

    # 兼容旧版：尝试从元数据计算（v3.0：改为±100对称）
    z = _get(r, "volume.z1h") or _get(r, "z_volume_1h") or _get(r, "momentum.z1h")
    if isinstance(z, (int, float)):
        return _as_int_score(12 * float(z), 0)  # z-score本身对称
    ratio = _get(r, "volume.v5_over_v20") or _get(r, "v5_over_v20")
    if isinstance(ratio, (int, float)):
        return _as_int_score(30 * (float(ratio) - 1.0), 0)  # ratio=1为中性
    return 0  # v3.0: 中性改为0

def _score_accel(r: Dict[str, Any]) -> int:
    # 优先使用顶层 A 字段（来自新版 analyze_symbol）
    v = _get(r, "A")
    if v is not None:
        return _as_int_score(v, 0)  # v3.0: 中性改为0

    # 兼容旧版：尝试从元数据计算（v3.0：改为±100对称）
    slope_atr = _get(r, "trend.slopeATR") or _get(r, "Tm.slopeATR")
    if isinstance(slope_atr, (int, float)):
        return _as_int_score(200 * float(slope_atr), 0)  # slope对称
    dP1h = _get(r, "momentum.dP1h_abs_pct") or _get(r, "dP1h_abs_pct")
    if isinstance(dP1h, (int, float)):
        # 注意：dP1h是绝对值，需要保留符号信息
        return _as_int_score(80 * min(1.0, float(dP1h) / 0.01), 0)
    return 0  # v3.0: 中性改为0

def _score_positions(r: Dict[str, Any]) -> int:
    # 优先使用顶层 O 字段（来自新版 analyze_symbol）
    v = _get(r, "O")
    if v is not None:
        return _as_int_score(v, 0)  # v3.0: 中性改为0

    # 兼容旧版：尝试从元数据计算（v3.0：改为±100对称）
    oi_z = _get(r, "oi.z20") or _get(r, "oi_z20")
    cvd_z = _get(r, "cvd.z20") or _get(r, "cvd_z20")
    vals: List[float] = []
    if isinstance(oi_z, (int, float)):
        vals.append(float(oi_z))
    if isinstance(cvd_z, (int, float)):
        vals.append(float(cvd_z))
    if vals:
        m = sum(vals) / len(vals)
        return _as_int_score(12 * m, 0)  # z-score本身对称
    return 0  # v3.0: 中性改为0

def _score_env(r: Dict[str, Any]) -> int:
    # 优先使用顶层 E 字段（来自新版 analyze_symbol）
    v = _get(r, "E")
    if v is not None:
        return _as_int_score(v, 0)  # v3.0: 中性改为0

    # 兼容旧版：尝试从元数据计算（v3.0：改为±100对称）
    # 注意：环境分数本身不具备方向性，旧版逻辑无法映射到±100
    # 这里保持简单的fallback
    atr_now = _get(r, "atr.now") or _get(r, "atr_now") or _get(r, "vol.atr_pct")
    if isinstance(atr_now, (int, float)):
        x = float(atr_now)
        if x <= 0:
            return 0  # v3.0: 中性改为0
        import math as _m
        # 简化逻辑：ATR越接近理想值（0.01）分数越高
        deviation = abs(_m.log10(x) - _m.log10(0.01))
        score = max(0, 80 - 40 * deviation)  # 0-80范围，正值表示环境好
        return _as_int_score(score, 0)
    return 0  # v3.0: 中性改为0

def _score_momentum(r: Dict[str, Any]) -> int:
    v = _get(r, "M")
    return _as_int_score(v, 0)  # v3.0: 中性改为0

def _score_cvd_flow(r: Dict[str, Any]) -> int:
    v = _get(r, "C")
    return _as_int_score(v, 0)  # v3.0: 中性改为0

def _score_fund_leading(r: Dict[str, Any]) -> int:
    v = _get(r, "F_score") or _get(r, "F")
    return _as_int_score(v, 0)  # v3.0: 中性改为0

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
    tag = "观察" if is_watch else "正式"
    icon = "👀" if is_watch else "📣"
    line2 = f"{icon} {tag} · {side_lbl} {conv}% · 有效期{ttl_h}h"
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
    oi24h_pct = O_meta.get("oi24h_pct")
    chop = E_meta.get("chop")
    leading_raw = F_meta.get("leading_raw")

    lines = []
    lines.append(f"• 趋势 {_emoji_by_score(T)} {T:>2d} —— {_desc_trend(T, is_long, Tm)}")
    lines.append(f"• 动量 {_emoji_by_score(M)} {M:>2d} —— 价格动量")
    lines.append(f"• 资金流 {_emoji_by_score(C)} {C:>2d} —— CVD变化")
    lines.append(f"• 结构 {_emoji_by_score(S)} {S:>2d} —— {_desc_structure(S, theta)}")
    lines.append(f"• 量能 {_emoji_by_score(V)} {V:>2d} —— {_desc_volume(V, v5v20)}")
    lines.append(f"• 持仓 {_emoji_by_score(OI)} {OI:>2d} —— {_desc_positions(OI, is_long, oi24h_pct)}")
    lines.append(f"• 环境 {_emoji_by_score(E)} {E:>2d} —— {_desc_env(E, chop)}")

    # F调节器信息
    F_adj = _get(r, "F_adjustment", 1.0)
    P_base = _get(r, "P_base")
    if P_base and F_adj != 1.0:
        lines.append(f"\n⚡ 资金领先 {F:>2d} → 概率调整 ×{F_adj:.2f}")

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