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

def _as_int_score(x: Any, default: int = 0, allow_negative: bool = True) -> int:
    """
    转换为整数分数（统一±100系统）

    Args:
        x: 分数值
        default: 默认值（0=中性）
        allow_negative: 是否允许负数（True=±100系统，False=0-100系统）
    """
    try:
        if x is None:
            return default
        if isinstance(x, (list, tuple)) and len(x) > 0:
            # allow last value fallback
            try:
                x = x[-1]
            except Exception:
                pass
        score = int(round(float(x)))
        # 统一±100系统：允许负数
        if allow_negative:
            return max(-100, min(100, score))
        else:
            # 兼容旧版0-100系统
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
    分数转emoji（统一±100系统，优化颜色方案）

    颜色方案（体现强度和方向）：
    - s >= 60:  🟢 绿色（强势正向）
    - 30-60:    🟡 黄色（中等正向）
    - -30到+30: 🔵 蓝色（中性）
    - -60到-30: 🟠 橙色（中等负向）
    - s <= -60: 🔴 红色（强势负向）

    注：颜色同时体现方向和强度
    """
    if s >= 60:
        return "🟢"  # 强势正向
    elif s >= 30:
        return "🟡"  # 中等正向
    elif s >= -30:
        return "🔵"  # 中性
    elif s >= -60:
        return "🟠"  # 中等负向
    else:  # s < -60
        return "🔴"  # 强势负向

def _desc_trend(s: int, Tm: int = None) -> str:
    """
    描述趋势（统一±100系统）

    Args:
        s: T 分数 (-100到+100，正数=上涨，负数=下跌)
        Tm: 趋势强度指标（保留用于额外信息）
    """
    # 基于符号的描述（±100系统）
    if s >= 80:
        desc = "强势上行"
    elif s >= 60:
        desc = "温和上行"
    elif s >= 30:
        desc = "偏多震荡"
    elif s >= -30:
        desc = "中性震荡"
    elif s >= -60:
        desc = "偏空震荡"
    elif s >= -80:
        desc = "温和下行"
    else:  # s < -80
        desc = "强势下行"

    # 附加趋势方向（如果有Tm）
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
    描述结构（统一±100系统）

    Args:
        s: S 分数 (-100到+100，正数=好，负数=差)
        theta: 结构一致性角度 (0.25-0.60)
    """
    # 基于符号的描述（±100系统）
    if s >= 60:
        desc = "结构清晰/多周期共振"
    elif s >= 30:
        desc = "结构尚可/回踩确认"
    elif s >= -30:
        desc = "结构一般/级别分歧"
    else:  # s < -30
        desc = "结构杂乱/级别相抵"

    # 附加结构角度
    if theta is not None:
        desc += f" (θ={theta:.2f})"

    return desc

def _desc_volume(s: int, v5v20: float = None) -> str:
    """
    描述量能（统一±100系统）

    Args:
        s: V 分数 (-100到+100，正数=放量，负数=缩量)
        v5v20: 短期/长期量能比率
    """
    # 基于符号的描述（±100系统）
    if s >= 60:
        desc = "放量明显/跟随积极"
    elif s >= 30:
        desc = "量能偏强/逐步释放"
    elif s >= -30:
        desc = "量能中性"
    else:  # s < -30
        desc = "量能不足/跟随意愿弱"

    # 附加量能比率
    if v5v20 is not None:
        desc += f" (v5/v20={v5v20:.2f})"

    return desc

def _desc_momentum(s: int, slope_now: float = None) -> str:
    """
    描述动量（统一±100系统）

    Args:
        s: M 分数 (-100到+100，正数=上行加速，负数=下行加速)
        slope_now: 当前动量斜率（可选）
    """
    # 基于符号的描述（±100系统）
    if s >= 60:
        desc = "强劲上行加速"
    elif s >= 30:
        desc = "温和上行加速"
    elif s >= -30:
        desc = "动量中性"
    elif s >= -60:
        desc = "温和下行加速"
    else:  # s < -60
        desc = "强劲下行加速"

    # 附加斜率信息（如果有）
    if slope_now is not None:
        desc += f" (斜率={slope_now:.2f})"

    return desc

def _desc_accel(s: int, is_long: bool = True, cvd6: float = None) -> str:
    """
    描述加速（旧版A维度，保留兼容性）

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

        # 数据异常检查：如果绝对值>1000%，说明数据异常，不显示
        if abs(cvd_pct) > 1000:
            desc += f" (CVD数据异常"
        elif cvd_pct >= 0:
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

def _desc_positions(s: int, oi24h_pct: float = None) -> str:
    """
    描述持仓（统一±100系统）

    Args:
        s: O 分数 (-100到+100，正数=增加，负数=减少)
        oi24h_pct: OI 24小时变化百分比
    """
    # 基于符号的描述（±100系统）
    if s >= 60:
        desc = "持仓显著增长/可能拥挤"
    elif s >= 30:
        desc = "持仓温和上升/活跃"
    elif s >= -30:
        desc = "持仓温和变化"
    else:  # s < -30
        desc = "持仓走弱/去杠杆"

    # 附加 OI 24h 变化
    if oi24h_pct is not None:
        if oi24h_pct >= 0:
            desc += f" (OI+{oi24h_pct:.1f}%)"
        else:
            desc += f" (OI{oi24h_pct:.1f}%)"

    return desc

def _desc_env(s: int, chop: float = None) -> str:
    """
    描述震荡（统一±100系统）

    Args:
        s: E 分数 (-100到+100，正数=震荡小空间大，负数=震荡大空间小)
        chop: Chop 指数 (0-100，越高越震荡)
    """
    # 基于符号的描述（±100系统）
    if s >= 60:
        desc = "趋势明确/空间充足"
    elif s >= 30:
        desc = "偏趋势/空间尚可"
    elif s >= -30:
        desc = "震荡偏强/空间有限"
    else:  # s < -30
        desc = "强烈震荡/空间狭窄"

    # 附加 Chop 指数
    if chop is not None:
        desc += f" (Chop={chop:.0f})"

    return desc

def _desc_fund_leading(s: int, leading_raw: float = None) -> str:
    """
    描述资金领先性（方案C：分开描述，去除程度修饰）

    Args:
        s: F 分数 (-100 到 +100)
        leading_raw: 真实的领先性数值（用于调试，可选）

    Returns:
        简洁描述（"资金领先价格" or "价格领先资金" or "资金价格同步"）
    """
    if s >= 10:
        desc = "资金领先价格"
    elif s >= -10:
        desc = "资金价格同步"
    else:
        desc = "价格领先资金"

    return desc

def _emoji_by_fund_leading(s: int) -> str:
    """
    F调节器质量标识（方案C：反映信号质量，不是方向）

    资金领先价格 (F>0) = ✅ 好信号（蓄势待发）
    价格领先资金 (F<0) = ⚠️ 风险（追涨/杀跌）

    Args:
        s: F 分数 (-100 到 +100)

    Returns:
        ✅ 或 ⚠️
    """
    if s >= 10:
        return "✅"  # 资金领先，质量好
    else:
        return "⚠️"  # 价格领先或同步，有风险

# ---------- extract scores robustly ----------

def _score_trend(r: Dict[str, Any]) -> int:
    # 优先使用顶层 T 字段（来自新版 analyze_symbol，±100系统）
    v = _get(r, "T")
    if v is None:
        v = _get(r, "trend.score")
    return _as_int_score(v, default=0, allow_negative=True)

def _score_structure(r: Dict[str, Any]) -> int:
    # 优先使用顶层 S 字段（来自新版 analyze_symbol，±100系统）
    v = _get(r, "S")
    if v is None:
        v = _get(r, "structure.score")
    if v is None:
        v = _get(r, "structure.fallback_score")
    if v is None:
        v = _get(r, "structure", {})
        if isinstance(v, dict) and "fallback_score" in v:
            v = v["fallback_score"]
    return _as_int_score(v, default=0, allow_negative=True)

def _score_volume(r: Dict[str, Any]) -> int:
    # 优先使用顶层 V 字段（来自新版 analyze_symbol，±100系统）
    v = _get(r, "V")
    if v is not None:
        return _as_int_score(v, default=0, allow_negative=True)

    # 兼容旧版：尝试从元数据计算
    z = _get(r, "volume.z1h") or _get(r, "z_volume_1h") or _get(r, "momentum.z1h")
    if isinstance(z, (int, float)):
        return _as_int_score(50 + 12 * float(z), default=50, allow_negative=False)
    ratio = _get(r, "volume.v5_over_v20") or _get(r, "v5_over_v20")
    if isinstance(ratio, (int, float)):
        return _as_int_score(50 + 30 * (float(ratio) - 1.0), default=50, allow_negative=False)
    return 0

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
    # 优先使用顶层 O 字段（来自新版 analyze_symbol，±100系统）
    v = _get(r, "O")
    if v is not None:
        return _as_int_score(v, default=0, allow_negative=True)

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
        return _as_int_score(50 + 12 * m, default=50, allow_negative=False)
    return 0

def _score_env(r: Dict[str, Any]) -> int:
    # 优先使用顶层 E 字段（来自新版 analyze_symbol，±100系统）
    v = _get(r, "E")
    if v is not None:
        return _as_int_score(v, default=0, allow_negative=True)

    # 兼容旧版：尝试从元数据计算
    atr_now = _get(r, "atr.now") or _get(r, "atr_now") or _get(r, "vol.atr_pct")
    if isinstance(atr_now, (int, float)):
        x = float(atr_now)
        if x <= 0:
            return -10
        import math as _m
        score = 60 - 20 * abs(_m.log10(x) - _m.log10(0.01))
        return _as_int_score(score, default=50, allow_negative=False)
    return 0

def _score_momentum(r: Dict[str, Any]) -> int:
    # 优先使用顶层 M 字段（来自新版 analyze_symbol，±100系统）
    v = _get(r, "M")
    return _as_int_score(v, default=0, allow_negative=True)

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
    # F调节器（±100系统）
    v = _get(r, "F_score") or _get(r, "F")
    return _as_int_score(v, default=0, allow_negative=True)

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
    line2 = f"{side_lbl} 概率{conv}% · 有效期{ttl_h}h"
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
    # 所有维度统一使用带符号显示（±100系统）
    lines.append(f"• 趋势 {_emoji_by_score(T)} {T:+4d} —— {_desc_trend(T, Tm)}")
    lines.append(f"• 动量 {_emoji_by_score(M)} {M:+4d} —— {_desc_momentum(M, slope)}")
    lines.append(f"• 资金 {_emoji_by_score(C)} {C:+4d} —— {_desc_cvd_flow(C, is_long, cvd6, cvd_consistency, cvd_is_consistent)}")
    lines.append(f"• 结构 {_emoji_by_score(S)} {S:+4d} —— {_desc_structure(S, theta)}")
    lines.append(f"• 成交 {_emoji_by_score(V)} {V:+4d} —— {_desc_volume(V, v5v20)}")
    lines.append(f"• 持仓 {_emoji_by_score(OI)} {OI:+4d} —— {_desc_positions(OI, oi24h_pct)}")
    lines.append(f"• 震荡 {_emoji_by_score(E)} {E:+4d} —— {_desc_env(E, chop)}")

    # 市场大盘趋势（BTC/ETH过滤器）
    market_regime = _get(r, "market_regime")
    market_meta = _get(r, "market_meta") or {}
    market_penalty = _get(r, "market_penalty")

    if market_regime is not None:
        regime_desc = market_meta.get("regime_desc", "未知")
        btc_trend = market_meta.get("btc_trend", 0)
        eth_trend = market_meta.get("eth_trend", 0)

        # 市场趋势emoji
        market_emoji = _emoji_by_score(market_regime)

        # 显示市场状态
        lines.append(f"\n📊 大盘趋势 {market_emoji} {regime_desc} (市场{market_regime:+d})")
        lines.append(f"   BTC{btc_trend:+d} · ETH{eth_trend:+d}")

        # 如果有逆势惩罚，显示警告
        if market_penalty:
            lines.append(f"   ⚠️ {market_penalty} → 概率和Prime已降低")

    # F调节器信息（所有信号都显示）
    F_adj = _get(r, "F_adjustment", 1.0)
    f_desc = _desc_fund_leading(F)
    f_emoji = _emoji_by_fund_leading(F)
    lines.append(f"\n⚡ F调节器 {f_emoji} {f_desc} (F{F:+d}) → 概率调整 ×{F_adj:.2f}")

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