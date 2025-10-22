# coding: utf-8
"""
Overlay candidate builder

- 按 1h OI 相对变化率（相对最近一段中位数归一化）筛选候选
- 大盘与非大盘使用不同阈值（从 CFG.overlay 读取；若缺失使用较稳健的默认值）
- 返回 [{'symbol': 'BTCUSDT', 'oi1h': 0.0123}, ...]，oi1h 为比例（1% = 0.01）
"""

from __future__ import annotations
from typing import List, Dict, Any
from statistics import median

from ats_core.cfg import CFG
from ats_core.sources.oi import fetch_oi_hourly


def _oi_1h_pct(sym: str) -> float:
    """近 1 小时 OI 相对变化（相对最近窗口中位数）"""
    oi = fetch_oi_hourly(sym, 30)
    if len(oi) < 2:
        return 0.0
    den = median(oi)
    return (oi[-1] - oi[-2]) / max(1e-12, den)


def build() -> List[Dict[str, Any]]:
    """
    构建候选池：按 OI 变化率阈值过滤，并按变化率降序
    阈值来自 CFG.overlay：
      - oi_1h_pct_big   (默认 0.003  = 0.3%)
      - oi_1h_pct_small (默认 0.010  = 1.0%)
    """
    par = CFG.get("overlay", default={})
    th_big   = float(par.get("oi_1h_pct_big",   0.003))  # 0.3%
    th_small = float(par.get("oi_1h_pct_small", 0.010))  # 1.0%

    majors = set(CFG.get("majors", default=["BTCUSDT", "ETHUSDT"]))
    uni    = CFG.get("universe", default=list(majors))
    if not isinstance(uni, (list, tuple)):
        uni = list(majors)
    else:
        # 只保留字符串符号，防御配置异常
        uni = [s for s in uni if isinstance(s, str)]

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