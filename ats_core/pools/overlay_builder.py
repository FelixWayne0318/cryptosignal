cat > ~/ats-analyzer/ats_core/pools/overlay_builder.py <<'PY'
# coding: utf-8
"""
Overlay candidate builder
- 依据 1h OI 相对变化率筛选（对 OI 中位数归一化）
- 大盘与非大盘采用不同阈值
- 返回 [{'symbol': 'BTCUSDT', 'oi1h': 0.0123}, ...]，oi1h 为比例（1% = 0.01）
"""

from __future__ import annotations
from typing import List, Dict, Any
from statistics import median

from ats_core.cfg import CFG
from ats_core.sources.oi import fetch_oi_hourly

def _oi_1h_pct(sym: str) -> float:
    """近 1 小时 OI 相对变化（相对最近期中位数）"""
    oi = fetch_oi_hourly(sym, 30)
    if len(oi) < 2:
        return 0.0
    den = median(oi)
    return (oi[-1] - oi[-2]) / max(1e-12, den)

def build() -> List[Dict[str, Any]]:
    """构建候选池：按 OI 变化率阈值过滤，并按变化率降序"""
    par = CFG.get("overlay", default={})
    th_big   = par.get("oi_1h_pct_big",   0.005)  # 大盘阈值，默认 0.5%
    th_small = par.get("oi_1h_pct_small", 0.020)  # 小盘阈值，默认 2%

    majors = set(CFG.get("majors",   default=["BTCUSDT","ETHUSDT"]))
    uni    = list(CFG.get("universe", default=list(majors)))

    out: List[Dict[str, Any]] = []
    for sym in uni:
        try:
            r1h = _oi_1h_pct(sym)
            is_big = sym in majors
            if (is_big and r1h >= th_big) or ((not is_big) and r1h >= th_small):
                out.append({"symbol": sym, "oi1h": r1h})
        except Exception:
            # 单个符号失败不影响整体
            pass

    out.sort(key=lambda x: x["oi1h"], reverse=True)
    return out

# 兼容可能的旧入口名
build_overlay     = build
build_candidates  = build
build_pool        = build

__all__ = ["build", "build_overlay", "build_candidates", "build_pool", "_oi_1h_pct"]
PY