# coding: utf-8
from __future__ import annotations

from typing import Any, Mapping, Sequence, Optional


# ------------ 小工具（健壮取值 + 统一格式化）------------

def _get(obj: Any, key_or_path: Any, default: Any = None) -> Any:
    """
    安全取值：
    - key_or_path 是 str -> 从 dict 取
    - 是 list/tuple -> 按路径逐级深入
    - 否则 -> default
    """
    if obj is None:
        return default
    if isinstance(key_or_path, (list, tuple)):
        cur = obj
        for k in key_or_path:
            if isinstance(cur, Mapping) and k in cur:
                cur = cur[k]
            else:
                return default
        return cur
    if isinstance(key_or_path, str) and isinstance(obj, Mapping):
        return obj.get(key_or_path, default)
    return default


def _fmt_num(x: Any, digits: int = 2) -> str:
    try:
        return f"{float(x):.{digits}f}"
    except Exception:
        return "—"


def _fmt_pct(x: Any, digits: int = 2) -> str:
    try:
        return f"{float(x) * 100:.{digits}f}%"
    except Exception:
        return "—"


def _fmt_bool(x: Any) -> str:
    if isinstance(x, bool):
        return "✅" if x else "❌"
    return "—"


def _ttl_hours(r: Mapping[str, Any]) -> int:
    v = (
        _get(r, "ttl_h")
        or _get(r, "ttl_hours")
        or _get(_get(r, "publish", {}), "ttl_h")
        or 8
    )
    try:
        return int(v)
    except Exception:
        return 8


# ------------ 主渲染 ------------

def _render_body(r: Mapping[str, Any]) -> str:
    # 头部信息
    sym = _get(r, "symbol", "?")
    tag = _get(r, "tag") or "watch"

    # 趋势相关
    trendT = _get(r, ["trend", "T"]) or _get(r, "T")
    slope_atr = _get(r, ["trend", "slopeATR"]) or _get(r, "slopeATR")
    m15_ok = _get(r, ["trend", "m15_ok"])

    # 动量 / 量能
    dp1h = (
        _get(r, ["metrics", "dP1h_abs_pct"])
        or _get(r, "dP1h_abs_pct")
        or _get(r, "dP1h")
    )
    z1h = _get(r, ["metrics", "z_volume_1h"]) or _get(r, "z_volume_1h")
    v5v20 = _get(r, ["metrics", "v5_over_v20"]) or _get(r, "v5_over_v20")

    # OI / CVD
    oi_d1h = _get(r, ["oi", "d1h_pct"]) or _get(r, "oi_1h_pct")
    oi_z20 = _get(r, ["oi", "z20"]) or _get(r, "oi_z20")
    cvd_z20 = _get(r, ["cvd", "z20"]) or _get(r, "cvd_z20")
    cvd_mix = (
        _get(r, ["cvd", "mix_last"])
        or _get(r, "cvd_mix_last")
        or _get(r, "cvd_mix_z20")
    )

    # 质量 / 结构（有就打，没有就占位）
    quality = _get(r, ["prior", "q"]) or _get(r, "quality_factor")
    structure = _get(r, "structure")

    # 交易建议（可选）
    entry = _get(r, "entry")
    stop = _get(r, "stop")
    targets = _get(r, "targets")

    ttl = _ttl_hours(r)
    note = _get(r, "note") or _get(r, ["publish", "note"])

    lines = []
    lines.append(f"{'👀 观察' if tag == 'watch' else '🚀 正式'} · {sym}")

    # 指标块（固定骨架 + 有值写值 / 无值写占位）
    lines.append(
        "趋势："
        f"T {_fmt_num(trendT, 0)}｜斜率×ATR {_fmt_num(slope_atr, 2)}｜M15 {_fmt_bool(m15_ok)}"
    )
    lines.append(
        "动量："
        f"ΔP1h {_fmt_pct(dp1h)}｜成交 z1h {_fmt_num(z1h, 2)}｜v5/v20 {_fmt_num(v5v20, 2)}"
    )
    lines.append(
        "资金："
        f"OI Δ1h {_fmt_pct(oi_d1h)}｜OI z20 {_fmt_num(oi_z20, 2)}｜CVD z20 {_fmt_num(cvd_z20, 2)}"
    )
    lines.append(f"混合：CVD·OI·价 {_fmt_num(cvd_mix, 3)}")

    # 结构 / 质量（可选）
    if structure is not None:
        lines.append(f"结构：{structure}")
    if quality is not None:
        lines.append(f"质量：Q {_fmt_num(quality, 2)}")

    # 交易建议（可选）
    if any(v is not None for v in (entry, stop, targets)):
        tgs = ""
        if isinstance(targets, (list, tuple)) and targets:
            tgs = " / ".join(_fmt_num(x, 4) for x in targets[:4])
        lines.append(
            "建议：" +
            f"入 {_fmt_num(entry, 4)}；止 {_fmt_num(stop, 4)}" +
            (f"；目 {tgs}" if tgs else "")
        )

    # 备注 / TTL / 标签
    if note:
        lines.append(f"备注：{note}")
    lines.append(f"TTL ~{ttl}h")
    lines.append(f"#{tag} #{sym}")

    return "\n".join(lines)


def render_signal(r: Mapping[str, Any], is_watch: bool = False) -> str:
    # 兼容：外部传了 is_watch 我们覆盖 tag；否则用 r['tag']
    if is_watch:
        if isinstance(r, dict):
            r = dict(r)
            r["tag"] = "watch"
    else:
        if isinstance(r, dict) and r.get("tag") is None:
            r = dict(r)
            r["tag"] = "trade"
    return _render_body(r)


def render_watch(r: Mapping[str, Any]) -> str:
    return render_signal(r, is_watch=True)


def render_prime(r: Mapping[str, Any]) -> str:
    return render_signal(r, is_watch=False)