# coding: utf-8
from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Union, Tuple
import math

Number = Union[int, float]


# ----------------------------
# 基础工具（健壮取值 / 取末值 / 安全四舍五入）
# ----------------------------
def _pick(d: Any, path: Iterable[Union[str, int]], default: Any = None) -> Any:
    """
    安全地取嵌套字段：
      _pick(r, ["trend", "score"], 50)
    """
    cur = d
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        elif isinstance(cur, (list, tuple)) and isinstance(key, int) and 0 <= key < len(cur):
            cur = cur[key]
        else:
            return default
    return cur


def _last(x: Any, default: Any = None) -> Any:
    """安全取末值（标量原样返回，序列取最后一个）"""
    if isinstance(x, (list, tuple)):
        return x[-1] if x else default
    return x if x is not None else default


def _round(x: Optional[Number], nd: int = 2, default: str = "—") -> str:
    if x is None:
        return default
    try:
        return f"{round(float(x), nd):.{nd}f}"
    except Exception:
        return default


# ----------------------------
# 视觉映射（颜色/emoji）
# ----------------------------
def _level_emoji(score: Optional[Number]) -> str:
    """
    分档：>=75 🟢、50~74 🟡、<50 🔴、None 灰
    """
    if score is None:
        return "⚪"
    s = float(score)
    if s >= 75:
        return "🟢"
    if s >= 50:
        return "🟡"
    return "🔴"


def _side_chip(side: Optional[str]) -> Tuple[str, str]:
    """
    方向徽标：做多=🟩 做空=🟥 中性=🟦
    """
    s = (side or "").lower()
    if s in ("long", "多", "bull", "buy"):
        return "🟩", "做多"
    if s in ("short", "空", "bear", "sell"):
        return "🟥", "做空"
    return "🟦", "中性"


def _head_chip(is_watch: bool, score: Optional[Number]) -> str:
    """
    顶部“观察/正式”的左侧圆点：按整体强度着色
    """
    if score is None:
        return "🟡 观察" if is_watch else "🔥 正式"
    em = _level_emoji(score)
    if is_watch:
        return f"{em} 观察"
    return f"{em} 正式"


# ----------------------------
# 六维打分（尽量兼容你现有的字段）
# 提示：如果缺字段，使用兜底逻辑估算，不抛错
# ----------------------------
def _score_trend(r: Dict[str, Any]) -> Tuple[Optional[Number], str]:
    # 直接取已有分数
    s = _pick(r, ["trend", "score"])
    if s is None:
        s = r.get("T")  # 你们早期把趋势计分命名成 T（0-100）
    # 文案
    if s is None:
        txt = "—"
    else:
        s = float(s)
        if s >= 75:
            txt = "趋势强劲/顺势"
        elif s >= 50:
            txt = "趋势尚可/震荡偏向"
        else:
            txt = "趋势弱/震荡"
    return s, txt


def _score_structure(r: Dict[str, Any]) -> Tuple[Optional[Number], str]:
    s = _pick(r, ["structure", "score"])
    if s is None:
        # 某些版本里 structure 可能只给了 fallback_score
        s = _pick(r, ["structure", "fallback_score"])
    if s is None:
        s = 50
    s = float(s)
    if s >= 75:
        txt = "结构清晰/多级联动"
    elif s >= 50:
        txt = "结构一般/级别分歧"
    else:
        txt = "结构杂乱/级别相抵"
    return s, txt


def _score_volume(r: Dict[str, Any]) -> Tuple[Optional[Number], str]:
    # 优先取 volume.score
    s = _pick(r, ["volume", "score"])
    if s is None:
        # 如果给了 v5_over_v20（常用强弱阈值 2.5）
        v = _pick(r, ["volume", "v5_over_v20"])
        if v is None:
            v = r.get("v5_over_v20")
        if isinstance(v, (int, float)):
            # 线性映射到 0-100，2.5 以上接近满分（上限 4.0）
            ratio = max(0.0, min(1.0, (float(v) - 1.0) / (2.5 - 1.0))) if 2.5 != 1.0 else 0.0
            s = 30 + 70 * ratio
        else:
            s = 50
    s = float(s)
    if s >= 75:
        txt = "量能充足/放量"
    elif s >= 50:
        txt = "量能中性"
    else:
        txt = "量能不足"
    return s, txt


def _score_accel(r: Dict[str, Any]) -> Tuple[Optional[Number], str]:
    # 优先取 accelerate.score
    s = _pick(r, ["accelerate", "score"])
    if s is None:
        # 用 1h 价格变化的绝对值（%）估算（示例阈值 0.6% / 1.2%）
        dP1h = _pick(r, ["momentum", "dP1h_abs_pct"])
        if dP1h is None:
            dP1h = r.get("dP1h_abs_pct")
        if isinstance(dP1h, (int, float)):
            x = abs(float(dP1h))
            if x >= 1.2:
                s = 85
            elif x >= 0.6:
                s = 65
            else:
                s = 30
        else:
            s = 50
    s = float(s)
    if s >= 75:
        txt = "加速明显/顺延概率高"
    elif s >= 50:
        txt = "加速一般"
    else:
        txt = "加速不足/有背离风险"
    return s, txt


def _score_oi(r: Dict[str, Any]) -> Tuple[Optional[Number], str]:
    # 优先取 oi.score
    s = _pick(r, ["oi", "score"])
    if s is None:
        # 用 z20 或 Δ1h 估算
        z = _pick(r, ["oi", "z20"])
        if not isinstance(z, (int, float)):
            z = _pick(r, ["oi", "zscore20"])
        d1h = _pick(r, ["oi", "d1h_pct"])
        base = 50.0
        if isinstance(z, (int, float)):
            # z=2 近似 80 分；z=-2 近似 20 分
            base = max(0.0, min(100.0, 50 + float(z) * 15))
        if isinstance(d1h, (int, float)):
            base += max(-10.0, min(10.0, float(d1h) * 500))  # 0.02 -> +10
        s = max(0.0, min(100.0, base))
    s = float(s)
    if s >= 75:
        txt = "OI显著变化"
    elif s >= 50:
        txt = "OI温和变化"
    else:
        txt = "OI下降/撤退"
    return s, txt


def _score_env(r: Dict[str, Any]) -> Tuple[Optional[Number], str]:
    # 优先取 env/quality/prior.score
    s = _pick(r, ["env", "score"])
    if s is None:
        s = _pick(r, ["quality", "score"])
    if s is None:
        s = _pick(r, ["prior", "score"])
    if s is None:
        # 用你们的 quality_factor 或 crowding 等估算
        qf = _pick(r, ["quality", "factor"])
        if isinstance(qf, (int, float)):
            # 0.0 ~ 1.0 -> 30 ~ 90
            s = 30 + max(0.0, min(1.0, float(qf))) * 60
        else:
            s = 50
    s = float(s)
    if s >= 75:
        txt = "环境良好/空间充足"
    elif s >= 50:
        txt = "环境一般/空间有限"
    else:
        txt = "环境不佳/拥挤"
    return s, txt


def _overall_strength(scores: Iterable[Number]) -> Optional[float]:
    xs = [float(s) for s in scores if isinstance(s, (int, float))]
    if not xs:
        return None
    return sum(xs) / len(xs)


# ----------------------------
# 头部/信息块渲染
# ----------------------------
def _extract_price(r: Dict[str, Any]) -> Optional[Number]:
    # 优先从 payload 的 price/last/close 取
    for k in ("price", "last", "close"):
        v = r.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    # 尝试从 c（收盘序列）取末值
    v = _last(r.get("c"))
    return float(v) if isinstance(v, (int, float)) else None


def _extract_ttl(r: Dict[str, Any], default_h: int = 8) -> int:
    ttl = _pick(r, ["publish", "ttl_h"])
    if not isinstance(ttl, (int, float)):
        ttl = r.get("ttl_h")
    try:
        return int(ttl) if ttl is not None else default_h
    except Exception:
        return default_h


def _extract_side_and_prob(r: Dict[str, Any]) -> Tuple[str, int]:
    # side
    side = r.get("side") or _pick(r, ["signal", "side"])
    chip, side_cn = _side_chip(side)

    # 胜率/把握度（优先取 prob/winrate/confidence）
    prob = None
    for k in ("prob", "winrate", "confidence"):
        v = r.get(k) or _pick(r, ["signal", k])
        if isinstance(v, (int, float)):
            prob = float(v)
            break
    if prob is None:
        # 用整体强度估算
        t, _ = _score_trend(r)
        st, _ = _score_structure(r)
        vo, _ = _score_volume(r)
        ac, _ = _score_accel(r)
        oi, _ = _score_oi(r)
        ev, _ = _score_env(r)
        ov = _overall_strength([t, st, vo, ac, oi, ev]) or 55.0
        prob = max(35.0, min(85.0, ov))  # 收敛到一个合理区间
    return f"{chip} {side_cn} {int(round(prob))}%", int(round(prob))


# ----------------------------
# 主渲染函数（统一模板）
# ----------------------------
def render_signal(r: Dict[str, Any], is_watch: bool = False) -> str:
    """
    统一模板：
      头部：🟡 观察 / 🔥 正式 · 🟥 做空 53% · 8h
      次行：🔹 BTCUSDT · 现价 107675.4
      正文：六维分析（趋势/结构/量能/加速/持仓/环境）
    """
    sym = r.get("symbol") or r.get("sym") or r.get("pair") or "—"

    # 六维评分
    s_tr, txt_tr = _score_trend(r)
    s_st, txt_st = _score_structure(r)
    s_vo, txt_vo = _score_volume(r)
    s_ac, txt_ac = _score_accel(r)
    s_oi, txt_oi = _score_oi(r)
    s_ev, txt_ev = _score_env(r)

    overall = _overall_strength([s_tr, s_st, s_vo, s_ac, s_oi, s_ev])
    head = _head_chip(is_watch, overall)

    side_str, prob_int = _extract_side_and_prob(r)
    ttl_h = _extract_ttl(r, default_h=8)
    price = _extract_price(r)

    # 备注（可选）
    note = r.get("note") or r.get("remark") or _pick(r, ["publish", "note"]) or ""

    # 按分数显示 emoji
    e_tr = _level_emoji(s_tr)
    e_st = _level_emoji(s_st)
    e_vo = _level_emoji(s_vo)
    e_ac = _level_emoji(s_ac)
    e_oi = _level_emoji(s_oi)
    e_ev = _level_emoji(s_ev)

    # 头两行
    lines = []
    lines.append(f"{head} · {side_str} · {ttl_h}h")
    p_show = f"{_round(price, nd=1)}" if price is not None else "—"
    lines.append(f"🔹 {sym} · 现价 {p_show}\n")

    # 六维
    def _fmt(name: str, emj: str, score: Optional[Number], txt: str) -> str:
        sc = "—" if score is None else str(int(round(float(score))))
        return f"• {name} {emj} {sc} —— {txt}"

    lines.append("六维分析")
    lines.append(_fmt("趋势", e_tr, s_tr, txt_tr))
    lines.append(_fmt("结构", e_st, s_st, txt_st))
    lines.append(_fmt("量能", e_vo, s_vo, txt_vo))
    lines.append(_fmt("加速", e_ac, s_ac, txt_ac))
    lines.append(_fmt("持仓", e_oi, s_oi, txt_oi))
    lines.append(_fmt("环境", e_ev, s_ev, txt_ev))

    # 备注 + 标签
    if note:
        lines.append(f"\n备注：{note}")
    lines.append(f"TTL ~{ttl_h}h")

    # 标签交由外层脚本 (--tag) 控制；这里不强塞 #watch/#trade，避免重复
    # 如果你希望模板内自带标签，可在此追加：
    # lines.append(f"#watch #{sym}")  或  lines.append(f"#trade #{sym}")

    return "\n".join(lines).strip()


# 兼容接口
def render_watch(r: Dict[str, Any]) -> str:
    return render_signal(r, is_watch=True)


def render_prime(r: Dict[str, Any]) -> str:
    # “prime=正式”的历史命名；有脚本/旧代码调用到时走正式模板
    return render_signal(r, is_watch=False)