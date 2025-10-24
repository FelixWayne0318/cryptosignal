# coding: utf-8
from __future__ import annotations

"""
完整的单币种分析管道：
1. 获取市场数据（K线、OI）
2. 计算6维特征（T/A/S/V/O/E）
3. 双向评分（long/short）
4. 计算概率和边缘
5. 判定发布条件
"""

from typing import Dict, Any, Tuple, List
from statistics import median

from ats_core.cfg import CFG
from ats_core.sources.binance import get_klines, get_open_interest_hist
from ats_core.features.cvd import cvd_from_klines, cvd_mix_with_oi_price
from ats_core.scoring.scorecard import scorecard
from ats_core.scoring.probability import map_probability

# ============ 工具函数 ============

def _to_f(x) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0

def _last(x):
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(x[-1])
    except Exception:
        return _to_f(x)

def _ema(seq: List[float], n: int) -> List[float]:
    out: List[float] = []
    if not seq or n <= 1: return [_to_f(v) for v in seq]
    k = 2.0/(n+1.0)
    e = None
    for v in seq:
        v = _to_f(v)
        e = v if e is None else (e + k*(v-e))
        out.append(e)
    return out

def _atr(h: List[float], l: List[float], c: List[float], period: int = 14) -> List[float]:
    n = min(len(h), len(l), len(c))
    if n == 0: return []
    tr: List[float] = []
    pc = _to_f(c[0])
    for i in range(n):
        hi = _to_f(h[i]); lo = _to_f(l[i]); ci = _to_f(c[i])
        tr.append(max(hi-lo, abs(hi-pc), abs(lo-pc)))
        pc = ci
    return _ema(tr, period)

def _safe_dict(obj: Any) -> Dict[str, Any]:
    return obj if isinstance(obj, dict) else {}

# ============ 主分析函数 ============

def analyze_symbol(symbol: str) -> Dict[str, Any]:
    """
    完整分析单个交易对，返回：
    - 6维分数（long/short两侧）
    - scorecard结果（UpScore/DownScore/Edge）
    - 概率（P_long/P_short）
    - 发布判定（prime/watch）
    - 给价计划（入场/止损/止盈）
    - 元数据
    """
    params = CFG.params or {}

    # ---- 1. 获取数据 ----
    k1 = get_klines(symbol, "1h", 300)
    k4 = get_klines(symbol, "4h", 200)
    oi_data = get_open_interest_hist(symbol, "1h", 300)

    if not k1 or len(k1) < 50:
        return _make_empty_result(symbol, "insufficient_data")

    h = [_to_f(r[2]) for r in k1]
    l = [_to_f(r[3]) for r in k1]
    c = [_to_f(r[4]) for r in k1]
    v = [_to_f(r[5]) for r in k1]  # base volume
    q = [_to_f(r[7]) for r in k1]  # quote volume
    c4 = [_to_f(r[4]) for r in k4] if k4 and len(k4) >= 30 else c

    # 基础指标
    ema30 = _ema(c, 30)
    atr_series = _atr(h, l, c, 14)
    atr_now = _last(atr_series)
    close_now = _last(c)

    # CVD
    cvd_series, cvd_mix = cvd_mix_with_oi_price(k1, oi_data, window=20)

    # ---- 2. 计算6维特征 ----

    # 趋势（T）- 方向对称
    T_long, T_meta = _calc_trend(h, l, c, c4, params.get("trend", {}))
    T_short = 100 - T_long

    # 加速度（A）- 方向对称
    A_long, A_meta = _calc_accel(c, cvd_series, params.get("accel", {}))
    A_short = 100 - A_long

    # 结构（S）- 需要双向计算
    ctx_long = {"bigcap": False, "overlay": False, "phaseA": False, "strong": (T_long > 75), "m15_ok": False}
    ctx_short = {"bigcap": False, "overlay": False, "phaseA": False, "strong": (T_short > 75), "m15_ok": False}
    S_long, S_meta_long = _calc_structure(h, l, c, _last(ema30), atr_now, params.get("structure", {}), ctx_long)
    S_short, S_meta_short = _calc_structure(h, l, c, _last(ema30), atr_now, params.get("structure", {}), ctx_short)

    # 量能（V）- 方向无关
    V, V_meta = _calc_volume(q)

    # 持仓（O）- 需要双向计算
    cvd6 = (cvd_series[-1] - cvd_series[-7]) / max(1e-12, abs(close_now)) if len(cvd_series) >= 7 else 0.0
    O_long, O_meta_long = _calc_oi(symbol, c, True, params.get("open_interest", {}), cvd6)
    O_short, O_meta_short = _calc_oi(symbol, c, False, params.get("open_interest", {}), cvd6)

    # 环境（E）- 方向无关
    E, E_meta = _calc_environment(h, l, c, atr_now, params.get("environment", {}))

    # ---- 3. Scorecard ----
    weights = params.get("weights", {"T": 25, "A": 15, "S": 15, "V": 20, "O": 15, "E": 10})

    long_scores = {"T": T_long, "A": A_long, "S": S_long, "V": V, "O": O_long, "E": E}
    short_scores = {"T": T_short, "A": A_short, "S": S_short, "V": V, "O": O_short, "E": E}

    UpScore, DownScore, edge = scorecard(long_scores, weights)
    _, _, edge_short = scorecard(short_scores, weights)

    # 选择占优方向
    side_long = (UpScore > DownScore)
    chosen_scores = long_scores if side_long else short_scores
    chosen_meta = {
        "T": T_meta,
        "A": A_meta,
        "S": S_meta_long if side_long else S_meta_short,
        "V": V_meta,
        "O": O_meta_long if side_long else O_meta_short,
        "E": E_meta
    }

    # ---- 4. 概率计算 ----
    prior_up = 0.50  # 中性先验，可以根据BTC/ETH环境调整
    Q = _calc_quality(chosen_scores, len(k1), len(oi_data))

    P_long, P_short = map_probability(edge, prior_up, Q)
    P_chosen = P_long if side_long else P_short

    # ---- 5. 发布判定 ----
    publish_cfg = params.get("publish", {})
    prime_prob_min = publish_cfg.get("prime_prob_min", 0.62)
    prime_dims_ok_min = publish_cfg.get("prime_dims_ok_min", 4)
    prime_dim_threshold = publish_cfg.get("prime_dim_threshold", 65)
    watch_prob_min = publish_cfg.get("watch_prob_min", 0.58)

    dims_ok = sum(1 for s in chosen_scores.values() if s >= prime_dim_threshold)
    is_prime = (P_chosen >= prime_prob_min) and (dims_ok >= prime_dims_ok_min)
    is_watch = (watch_prob_min <= P_chosen < prime_prob_min)

    # ---- 6. 15分钟微确认 ----
    m15_ok = _check_microconfirm_15m(symbol, side_long, params.get("microconfirm_15m", {}), atr_now)

    # ---- 7. 给价计划 ----
    pricing = None
    if is_prime:
        pricing = _calc_pricing(h, l, c, atr_now, params.get("pricing", {}), side_long)

    # ---- 8. 组装结果 ----
    return {
        "symbol": symbol,
        "price": close_now,
        "ema30": _last(ema30),
        "atr_now": atr_now,

        # 6维分数
        "scores": chosen_scores,
        "scores_long": long_scores,
        "scores_short": short_scores,
        "scores_meta": chosen_meta,

        # Scorecard
        "UpScore": UpScore,
        "DownScore": DownScore,
        "edge": edge,

        # 方向
        "side": "long" if side_long else "short",
        "side_long": side_long,

        # 概率
        "P_long": P_long,
        "P_short": P_short,
        "probability": P_chosen,
        "prior_up": prior_up,
        "Q": Q,

        # 发布
        "publish": {
            "prime": is_prime,
            "watch": is_watch,
            "dims_ok": dims_ok,
            "ttl_h": 8
        },

        # 微确认
        "m15_ok": m15_ok,

        # 给价
        "pricing": pricing,

        # CVD
        "cvd_z20": _zscore_last(cvd_series, 20) if cvd_series else 0.0,
        "cvd_mix_abs_per_h": abs(_last(cvd_mix)) if cvd_mix else 0.0,
    }

# ============ 特征计算辅助函数 ============

def _calc_trend(h, l, c, c4, cfg):
    """趋势打分"""
    try:
        from ats_core.features.trend import score_trend
        T, Tm = score_trend(h, l, c, c4, cfg)
        meta = {"Tm": Tm, "slopeATR": 0.0, "emaOrder": Tm}
        return int(T), meta
    except Exception:
        return 50, {"Tm": 0, "slopeATR": 0.0, "emaOrder": 0}

def _calc_accel(c, cvd_series, cfg):
    """加速度打分"""
    try:
        from ats_core.features.accel import score_accel
        A, meta = score_accel(c, cvd_series, cfg)
        return int(A), meta
    except Exception:
        return 50, {"dslope30": 0.0, "cvd6": 0.0, "weak_ok": False}

def _calc_structure(h, l, c, ema30_last, atr_now, cfg, ctx):
    """结构打分"""
    try:
        from ats_core.features.structure_sq import score_structure
        S, meta = score_structure(h, l, c, ema30_last, atr_now, cfg, ctx)
        return int(S), meta
    except Exception:
        return 50, {"theta": 0.4, "icr": 0.5, "retr": 0.5}

def _calc_volume(vol):
    """量能打分"""
    try:
        from ats_core.features.volume import score_volume
        V, meta = score_volume(vol)
        return int(V), meta
    except Exception:
        return 50, {"v5v20": 1.0, "vroc_abs": 0.0}

def _calc_oi(symbol, closes, side_long, cfg, cvd6_fallback):
    """持仓打分"""
    try:
        from ats_core.features.open_interest import score_open_interest
        O, meta = score_open_interest(symbol, closes, side_long, cfg, cvd6_fallback)
        return int(O), meta
    except Exception:
        return 50, {"oi1h_pct": None, "oi24h_pct": None}

def _calc_environment(h, l, c, atr_now, cfg):
    """环境打分"""
    try:
        from ats_core.features.environment import environment_score
        E, meta = environment_score(h, l, c, atr_now, cfg)
        return int(E), meta
    except Exception:
        return 50, {"chop": 50.0, "room": 0.5}

def _calc_quality(scores: Dict, n_klines: int, n_oi: int) -> float:
    """
    质量系数 Q ∈ [0.6, 1.0]
    考虑：样本完备性、不过度、非拥挤等
    """
    Q = 1.0

    # 样本不足
    if n_klines < 100:
        Q *= 0.85
    if n_oi < 50:
        Q *= 0.90

    # 维度弱证据过多（<65分的维度）
    weak_dims = sum(1 for s in scores.values() if s < 65)
    if weak_dims >= 3:
        Q *= 0.85

    return max(0.6, min(1.0, Q))

def _check_microconfirm_15m(symbol: str, side_long: bool, params: Dict, atr1h: float) -> bool:
    """15分钟微确认"""
    try:
        from ats_core.features.microconfirm_15m import check_microconfirm_15m
        result = check_microconfirm_15m(symbol, side_long, params, atr1h)
        return result.get("ok", False)
    except Exception:
        return False

def _calc_pricing(h, l, c, atr_now, cfg, side_long):
    """给价计划"""
    try:
        from ats_core.features.pricing import price_plan
        return price_plan(h, l, c, atr_now, cfg, side_long)
    except Exception:
        return None

def _zscore_last(series, window):
    """计算最后一个值的z-score"""
    if not series or len(series) < window:
        return 0.0
    tail = series[-window:]
    med = median(tail)
    mad = median([abs(x - med) for x in tail]) or 1e-9
    return (series[-1] - med) / (1.4826 * mad)

def _make_empty_result(symbol: str, reason: str):
    """数据不足时的空结果"""
    return {
        "symbol": symbol,
        "error": reason,
        "scores": {"T": 50, "A": 50, "S": 50, "V": 50, "O": 50, "E": 50},
        "UpScore": 50,
        "DownScore": 50,
        "edge": 0.0,
        "probability": 0.5,
        "publish": {"prime": False, "watch": False, "dims_ok": 0, "ttl_h": 0},
        "side": "neutral",
        "m15_ok": False,
        "pricing": None
    }
