# coding: utf-8
"""
Overlay candidate builder (多规则并集 + 排序 + 可选“只增不减”)
命中任一规则即入池：
  1) 新合约（K线历史较短）
  2) 量能：1h 成交量 Z 分数（相对近 24 根）
  3) z24 + 24h quote：价格 1h 变动的 z 分数（近 24 根）与 24h 累计成交额门槛
  4) OI：近 1h OI 相对变化率（相对最近期 OI 中位数）——大盘/非大盘不同阈值
  5) 三同向：|1h 涨跌幅|、V5/V20、|CVD 每小时强度| 同时达标

并根据“热度 hot”排序：
  hot = 0.5*max(0,zv) + 0.3*abs(dP1h_pct)/100 + 0.2*max(0,oi1h)
  （简洁直观，够用即可；若需可在配置里继续扩展权重）
"""

from __future__ import annotations
from typing import List, Dict, Any, Tuple
from statistics import mean, pstdev, median
import math, json, os, time

from ats_core.cfg import CFG
from ats_core.sources.klines import klines_1h, split_ohlcv
from ats_core.features.ta_core import cvd as cvd_series
from ats_core.sources.oi import fetch_oi_hourly


# -------------------------------
# 工具函数
# -------------------------------

def _zscore(x: float, mu: float, sigma: float) -> float:
    if sigma <= 1e-12:
        return 0.0
    return (x - mu) / sigma

def _pct(a: float, b: float) -> float:
    """百分比变化（返回“百分数”，例如 +1.5% -> 1.5）"""
    if abs(b) <= 1e-12:
        return 0.0
    return (a - b) / b * 100.0

def _safe_ratio(a: float, b: float) -> float:
    return a / b if abs(b) > 1e-12 else 0.0

def _now_ts() -> int:
    return int(time.time())

def _persist_path() -> str:
    repo = os.path.expanduser(CFG.get("repo_root", default="~/ats-analyzer"))
    return os.path.join(os.path.expanduser(repo), "data/cache/overlay_seen.json")

def _load_seen() -> set:
    try:
        with open(_persist_path(), "r", encoding="utf-8") as f:
            arr = json.load(f)
        if isinstance(arr, list):
            return set(s for s in arr if isinstance(s, str))
    except Exception:
        pass
    return set()

def _save_seen(seen: set):
    try:
        os.makedirs(os.path.dirname(_persist_path()), exist_ok=True)
        with open(_persist_path(), "w", encoding="utf-8") as f:
            json.dump(sorted(seen), f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# -------------------------------
# 各规则打标
# -------------------------------

def _rule_new_contract(tb: List[int], max_hours: int) -> Tuple[bool, str]:
    """新合约：K线历史不足 max_hours 小时；或首尾时间跨度小于 max_hours"""
    if not tb:
        return False, ""
    hours = (tb[-1] - tb[0]) / 3600.0
    if hours < max_hours:
        return True, f"new({hours:.1f}h)"
    # 根数很少也算新（兜底）
    if len(tb) < max_hours:
        return True, f"new_nbars({len(tb)})"
    return False, ""

def _rule_zvol_1h(v: List[float], lookback: int, z_th: float) -> Tuple[bool, float]:
    """量能：近 1h 成交量对近 lookback 根的 Z 分数"""
    if len(v) < lookback + 1:
        return False, 0.0
    base = v[-lookback-1:-1]
    mu, sig = mean(base), pstdev(base)
    zv = _zscore(v[-1], mu, sig)
    return (zv >= z_th), zv

def _rule_z24_and_quote(c: List[float], q: List[float], lookback: int, z_th: float, min_quote_24h: float) -> Tuple[bool, float, float]:
    """
    z24：把近 lookback 根的“1h 涨跌幅(%) 序列”做 z 分数，检测当前 1h 的 |z| 是否大于阈值
    同时要求 24h 累计 quote >= min_quote_24h
    """
    if len(c) < lookback + 1 or len(q) < 24:
        return False, 0.0, 0.0
    rets = [_pct(c[i], c[i-1]) for i in range(1, len(c))]
    base = rets[-lookback-1:-1]
    mu, sig = mean(base), pstdev(base)
    z_now = _zscore(rets[-1], mu, sig)
    quote24 = sum(q[-24:])
    ok = (abs(z_now) >= z_th) and (quote24 >= min_quote_24h)
    return ok, z_now, quote24

def _oi_1h_pct(sym: str) -> float:
    """近 1h OI 相对变化（相对最近期 OI 中位数），返回比例（1% = 0.01）"""
    oi = fetch_oi_hourly(sym, 30)
    if len(oi) < 2:
        return 0.0
    den = median(oi)
    return (oi[-1] - oi[-2]) / max(1e-12, den)

def _rule_oi_1h(sym: str, majors: set, th_big: float, th_small: float) -> Tuple[bool, float]:
    r1h = _oi_1h_pct(sym)
    is_big = (sym in majors)
    th = th_big if is_big else th_small
    return (r1h >= th), r1h

def _rule_triple_sync(c: List[float], v: List[float], tb: List[float], dP1h_abs_pct_th: float, v5_over_v20_th: float, cvd_abs_per_h_th: float) -> Tuple[bool, Dict[str, float]]:
    """
    三同向：
      - |1h 涨跌幅(%)| >= dP1h_abs_pct_th
      - V5 / V20 >= v5_over_v20_th
      - |CVD 每小时强度| >= cvd_abs_per_h_th
    其中 CVD 每小时强度：abs(cvd[-1] - cvd[-7]) / (6 小时)，再相对 6h 成交量归一
    """
    out = {"dP1h_pct": 0.0, "v5_over_v20": 0.0, "cvd_abs_per_h": 0.0}
    if len(c) < 25 or len(v) < 25 or len(tb) < 25:
        return False, out

    dP1h_pct = abs(_pct(c[-1], c[-2]))  # 百分数
    v5 = sum(v[-5:]) / 5.0
    v20 = sum(v[-20:]) / 20.0
    v_ratio = _safe_ratio(v5, v20)

    cv = cvd_series(v, tb)
    # 取近 6 小时报动强度（并按 6h 成交量归一）
    cvd_abs = abs(cv[-1] - cv[-7]) if len(cv) >= 8 else 0.0
    vol6 = sum(v[-6:]) if len(v) >= 6 else 0.0
    cvd_abs_per_h = _safe_ratio(cvd_abs, max(1e-12, vol6))  # 作为“占 6 小时成交量的比例/每小时”

    out["dP1h_pct"] = dP1h_pct
    out["v5_over_v20"] = v_ratio
    out["cvd_abs_per_h"] = cvd_abs_per_h

    ok = (dP1h_pct >= dP1h_abs_pct_th) and (v_ratio >= v5_over_v20_th) and (cvd_abs_per_h >= cvd_abs_per_h_th)
    return ok, out


# -------------------------------
# 主构建函数
# -------------------------------

def build() -> List[Dict[str, Any]]:
    """
    返回形如：
      [{'symbol': 'BTCUSDT', 'why': ['zv','oi','tri'], 'oi1h':0.012, 'zv':3.4, 'dP1h_pct':0.8, 'v5_over_v20':2.7, 'cvd_abs_per_h':0.13, 'z24':2.1, 'quote1h':..., 'quote24h':..., 'hot':0.42}, ...]
    """
    par = CFG.get("overlay", default={})

    # 阈值与参数（有默认值，亦可在 config.yaml 覆盖）
    lookback_zvol = par.get("zvol_lookback", 24)
    z_volume_1h_threshold = float(par.get("z_volume_1h_threshold", 3))

    min_hour_quote_usdt = float(par.get("min_hour_quote_usdt", 5_000_000))

    z24cfg = par.get("z24_and_24h_quote", {}) or {}
    z24_th = float(z24cfg.get("z24", 2))
    min_quote_24h = float(z24cfg.get("quote", 20_000_000))

    th_big   = float(par.get("oi_1h_pct_big",   0.003))  # 大盘 OI 1h 相对增幅（默认 0.3%）
    th_small = float(par.get("oi_1h_pct_small", 0.010))  # 小盘 OI 1h 相对增幅（默认 1.0%）

    tri = par.get("triple_sync", {}) or {}
    dP1h_abs_pct_th  = float(tri.get("dP1h_abs_pct",     0.50))  # 1h 涨跌幅阈值（百分数）；例 0.50 = 0.5%
    v5_over_v20_th   = float(tri.get("v5_over_v20",      2.0))
    cvd_abs_per_h_th = float(tri.get("cvd_mix_abs_per_h",0.10))  # 近 6h CVD 强度/成交量/每小时

    new_max_hours = int(par.get("new_contract_hours", 72))  # 72h 内视作“新合约”

    persist_add_only = bool(par.get("persist_add_only", False))

    hot_decay_hours = float(par.get("hot_decay_hours", 2))  # 目前未用于时间衰减（留作扩展）

    majors = set(CFG.get("majors", default=["BTCUSDT", "ETHUSDT"]))
    uni = list(CFG.get("universe", default=list(majors)))
    if not uni:
        uni = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","COAIUSDT","CLOUSDT","XPLUSDT"]

    seen = _load_seen() if persist_add_only else set()

    candidates: List[Dict[str, Any]] = []

    for sym in uni:
        try:
            # 1h K线
            k1 = klines_1h(sym, 300)
            if not k1 or len(k1) < 30:
                continue
            o,h,l,c,v,q,tb = split_ohlcv(k1)
            quote1h = q[-1] if q else 0.0
            if quote1h < min_hour_quote_usdt:
                # 直接按小时成交额过滤
                # 但如果“只增不减”且该符号已在 seen 中，可保留
                if (sym not in seen):
                    continue

            why: List[str] = []

            # R1: 新合约
            _is_new, tag_new = _rule_new_contract(tb, new_max_hours)
            if _is_new:
                why.append("new")

            # R2: 量能 zvol(1h)
            _zok, zv = _rule_zvol_1h(v, lookback_zvol, z_volume_1h_threshold)
            if _zok:
                why.append("zv")

            # R3: z24 + 24h quote
            _z24ok, z24, quote24 = _rule_z24_and_quote(c, q, 24, z24_th, min_quote_24h)
            if _z24ok:
                why.append("z24")

            # R4: OI 近 1h 相对变化（大盘/小盘阈值不同）
            _oiok, oi1h = _rule_oi_1h(sym, majors, th_big, th_small)
            if _oiok:
                why.append("oi")

            # R5: 三同向
            _triok, tri_meta = _rule_triple_sync(c, v, tb, dP1h_abs_pct_th, v5_over_v20_th, cvd_abs_per_h_th)
            if _triok:
                why.append("tri")

            # 任一命中 或 已在 seen（只增不减）
            if why or (persist_add_only and (sym in seen)):
                # 计算综合“热度”排序
                dP1h_pct = tri_meta.get("dP1h_pct", abs(_pct(c[-1], c[-2])))
                v_ratio  = tri_meta.get("v5_over_v20", _safe_ratio(sum(v[-5:])/5.0, sum(v[-20:])/20.0))
                cvd_h    = tri_meta.get("cvd_abs_per_h", 0.0)
                # 热度：简单组合（与之前 grep 到的思路一致）
                hot = 0.5*max(0.0, zv) + 0.3*abs(dP1h_pct)/100.0 + 0.2*max(0.0, oi1h)

                item = {
                    "symbol": sym,
                    "why": sorted(set(why)),
                    "oi1h": round(oi1h, 6),
                    "zv": round(zv, 3),
                    "dP1h_pct": round(dP1h_pct, 3),
                    "v5_over_v20": round(v_ratio, 3),
                    "cvd_abs_per_h": round(cvd_h, 4),
                    "z24": round(z24, 3) if _z24ok else 0.0,
                    "quote1h": float(quote1h),
                    "quote24h": float(quote24 if _z24ok else sum(q[-24:]) if len(q)>=24 else 0.0),
                    "hot": round(hot, 6),
                }
                candidates.append(item)
                seen.add(sym)

        except Exception:
            # 单个符号异常不影响整体
            continue

    # 排序（热度从高到低）
    candidates.sort(key=lambda x: (x.get("hot", 0.0), x.get("quote1h", 0.0)), reverse=True)

    if persist_add_only:
        _save_seen(seen)

    return candidates


# 兼容可能存在的旧入口名
build_overlay    = build
build_candidates = build
build_pool       = build

__all__ = ["build", "build_overlay", "build_candidates", "build_pool"]