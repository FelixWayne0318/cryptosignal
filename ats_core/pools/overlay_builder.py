# coding: utf-8
"""
Overlay candidate builder

按 1h 持仓量（Open Interest, OI）的“相对变化率”筛选候选池：
- 以最近 30 个 1h OI 的中位数做归一化基准，计算 (OI[-1] - OI[-2]) / median(oi)
- 大盘/非大盘使用不同阈值（从 CFG.overlay 读取；有默认值）
- 返回形如：[{"symbol": "BTCUSDT", "oi1h": 0.0123}, ...]，oi1h 为比例（1% == 0.01）
"""

from __future__ import annotations
from typing import List, Dict, Any
from statistics import median

from ats_core.cfg import CFG
from ats_core.sources.oi import fetch_oi_hourly


def _oi_1h_pct(sym: str) -> float:
    """
    近 1 小时 OI 的相对变化率（相对最近样本的中位数）。
    若样本不足，返回 0.0。
    """
    oi = fetch_oi_hourly(sym, limit=30)
    if len(oi) < 2:
        return 0.0
    den = median(oi)
    return (oi[-1] - oi[-2]) / max(1e-12, den)


def build() -> List[Dict[str, Any]]:
    """
    构建候选池：按 OI 变化率阈值过滤，并按变化率降序返回。
    阈值来源：
      - CFG.overlay.oi_1h_pct_big   （默认 0.005 = 0.5%）
      - CFG.overlay.oi_1h_pct_small （默认 0.020 = 2%）
    大盘列表来源：
      - CFG.majors（默认 ["BTCUSDT", "ETHUSDT"]）
    宇宙（扫描范围）来源：
      - CFG.universe（若无则退化为 majors）
    """
    par = CFG.get("overlay", default={})
    th_big = float(par.get("oi_1h_pct_big", 0.005))     # 大盘阈值（0.5%）
    th_small = float(par.get("oi_1h_pct_small", 0.020)) # 小盘阈值（2%）

    majors = set(CFG.get("majors", default=["BTCUSDT", "ETHUSDT"]))
    uni = CFG.get("universe", default=None)
    if not isinstance(uni, (list, tuple)) or not uni:
        # 没配 universe 就只扫 majors，避免全市场扫太慢
        uni = list(majors)
    else:
        uni = list(uni)

    out: List[Dict[str, Any]] = []
    for sym in uni:
        try:
            r1h = _oi_1h_pct(sym)
            is_big = sym in majors
            if (is_big and r1h >= th_big) or ((not is_big) and r1h >= th_small):
                out.append({"symbol": sym, "oi1h": r1h})
        except Exception:
            # 单个符号失败不影响整体
            continue

    out.sort(key=lambda x: x["oi1h"], reverse=True)
    return out


# 向后兼容可能存在的旧入口名
build_overlay = build
build_candidates = build
build_pool = build

__all__ = ["build", "build_overlay", "build_candidates", "build_pool", "_oi_1h_pct"]