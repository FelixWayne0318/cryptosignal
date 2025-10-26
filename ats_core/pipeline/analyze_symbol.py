# coding: utf-8
from __future__ import annotations

"""
完整的单币种分析管道（v3.0 ±100对称设计）：
1. 获取市场数据（K线、OI）
2. 计算7维特征（T/M/C/S/V/O/E）- 每个维度返回±100
3. 加权评分（单次计算，方向自动判定）
4. 计算基础概率
5. F连续调节器调整概率
6. 判定发布条件

改进v3.0（±100对称重构）：
- ✅ 所有维度改为±100范围（0为中性，符号表示方向）
- ✅ 单次计算（不再分long/short两次）
- ✅ 方向自动判定（根据加权分正负）
- ✅ F连续调节函数（平滑调整，无硬阈值）
- ✅ 代码简化约30%
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

    # ---- 2. 计算7维特征（v3.0：单次计算，返回±100）----

    # 趋势（T）- 单次计算，返回±100
    T, T_meta = _calc_trend(h, l, c, c4, params.get("trend", {}))

    # 动量（M）- 价格动量，返回±100
    M, M_meta = _calc_momentum(c, params.get("momentum", {}))

    # CVD资金流（C）- 资金流，返回±100
    C, C_meta = _calc_cvd_flow(cvd_series, c, params.get("cvd_flow", {}))

    # 结构（S）- 单次计算，返回±100
    # ctx的strong判断改为绝对值（T的强度）
    ctx = {
        "bigcap": False,
        "overlay": False,
        "phaseA": False,
        "strong": (abs(T) > 75),  # 使用绝对值判断强度
        "m15_ok": False
    }
    S, S_meta = _calc_structure(h, l, c, _last(ema30), atr_now, params.get("structure", {}), ctx)

    # 量能（V）- 返回±100
    V, V_meta = _calc_volume(q)

    # 持仓（O）- 单次计算，返回±100
    cvd6 = (cvd_series[-1] - cvd_series[-7]) / max(1e-12, abs(close_now)) if len(cvd_series) >= 7 else 0.0
    O, O_meta = _calc_oi(symbol, c, params.get("open_interest", {}), cvd6)

    # 环境（E）- 返回±100
    E, E_meta = _calc_environment(h, l, c, atr_now, params.get("environment", {}))

    # ---- 2.5. 资金领先性（F）- 单次计算，返回±100 ----
    # F 需要的输入数据
    oi_change_pct = O_meta.get("oi24h_pct", 0.0) if O_meta.get("oi24h_pct") is not None else 0.0
    vol_ratio = V_meta.get("v5v20", 1.0)
    price_change_24h = ((c[-1] - c[-25]) / c[-25] * 100) if len(c) >= 25 else 0.0
    price_slope = (ema30[-1] - ema30[-7]) / 6.0 / max(1e-9, atr_now)  # 归一化斜率

    F, F_meta = _calc_fund_leading(
        oi_change_pct, vol_ratio, cvd6, price_change_24h, price_slope, params.get("fund_leading", {})
    )

    # ---- 3. Scorecard（v3.0：单次加权，方向自动判定）----
    # 权重：T、M、C、S、V、O、E（7维）
    weights = params.get("weights", {
        "T": 20,  # 趋势
        "M": 10,  # 动量
        "C": 10,  # CVD资金流
        "S": 10,  # 结构
        "V": 20,  # 量能
        "O": 15,  # 持仓
        "E": 15   # 环境
        # F 不参与权重，作为调节器
    })

    # 7维基础分数（每个都是±100）
    scores = {
        "T": T,
        "M": M,
        "C": C,
        "S": S,
        "V": V,
        "O": O,
        "E": E
    }

    # 加权求和（保留符号）
    # weighted_score = Σ(score[i] * weight[i] / 100)
    # 范围：-100 到 +100
    weighted_score = sum(scores[dim] * weights[dim] / 100.0 for dim in scores)

    # ---- 4. 方向自动判定（v3.0核心改进）----
    # 根据加权分的正负自动确定方向
    side_long = (weighted_score >= 0)
    confidence = abs(weighted_score)  # 置信度 = 加权分的绝对值（0-100）

    # 元数据
    meta = {
        "T": T_meta,
        "M": M_meta,
        "C": C_meta,
        "S": S_meta,
        "V": V_meta,
        "O": O_meta,
        "E": E_meta,
        "F": F_meta
    }

    # ---- 5. 基础概率计算（v3.0：使用confidence）----
    prior_up = 0.50  # 中性先验
    Q = _calc_quality(scores, len(k1), len(oi_data))

    # 使用confidence作为edge
    # edge范围：0-100，表示偏离中性的程度
    edge = confidence

    # 计算基础概率
    P_long_base, P_short_base = map_probability(edge, prior_up, Q)
    P_base = P_long_base if side_long else P_short_base

    # ---- 6. F连续调节器（v3.0：平滑调整）----
    # 导入F连续调节函数
    from ats_core.features.fund_leading import calculate_F_adjustment

    # 使用连续函数计算调节系数
    # F: -100~+100 → adjustment: 0.75~1.25
    F_adjustment = calculate_F_adjustment(F)

    # 最终概率
    P_final = min(0.95, P_base * F_adjustment)

    # 兼容性字段
    P_long = P_final if side_long else (1 - P_final)
    P_short = P_final if not side_long else (1 - P_final)

    # ---- 7. 发布判定（v3.0：适配±100）----
    publish_cfg = params.get("publish", {})
    prime_prob_min = publish_cfg.get("prime_prob_min", 0.62)
    prime_dims_ok_min = publish_cfg.get("prime_dims_ok_min", 4)
    prime_dim_threshold = publish_cfg.get("prime_dim_threshold", 65)  # 绝对值阈值
    watch_prob_min = publish_cfg.get("watch_prob_min", 0.58)

    # dims_ok：使用绝对值判断（±65都算好）
    dims_ok = sum(1 for s in scores.values() if abs(s) >= prime_dim_threshold)

    is_prime = (P_final >= prime_prob_min) and (dims_ok >= prime_dims_ok_min)
    is_watch = (watch_prob_min <= P_final < prime_prob_min)

    # ---- 6. 15分钟微确认 ----
    m15_ok = _check_microconfirm_15m(symbol, side_long, params.get("microconfirm_15m", {}), atr_now)

    # ---- 7. 给价计划 ----
    pricing = None
    if is_prime:
        pricing = _calc_pricing(h, l, c, atr_now, params.get("pricing", {}), side_long)

    # ---- 8. 组装结果（v3.0）----
    result = {
        "symbol": symbol,
        "price": close_now,
        "ema30": _last(ema30),
        "atr_now": atr_now,

        # 7维分数（±100，单次计算）
        "scores": scores,
        "scores_meta": meta,
        "weighted_score": weighted_score,  # 新增：加权分数

        # 兼容性字段（保留）
        "UpScore": (weighted_score + 100) / 2,  # 映射到0-100
        "DownScore": (100 - weighted_score) / 2,  # 映射到0-100
        "edge": edge,

        # 方向（自动判定）
        "side": "long" if side_long else "short",
        "side_long": side_long,
        "confidence": confidence,  # 新增：置信度

        # 概率（v3.0：包含F连续调整）
        "P_long": P_long,
        "P_short": P_short,
        "probability": P_final,
        "P_base": P_base,  # 基础概率（调整前）
        "F_score": F,  # F分数（±100）
        "F_adjustment": F_adjustment,  # 调整系数（连续函数）
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

    # 兼容旧版 telegram_fmt.py：将分数直接放在顶层
    result.update(scores)

    return result

# ============ 特征计算辅助函数（v3.0：移除side_long）============

def _calc_trend(h, l, c, c4, cfg):
    """趋势打分（v3.0：返回±100）"""
    try:
        from ats_core.features.trend import score_trend
        T, Tm = score_trend(h, l, c, c4, cfg)
        meta = {"Tm": Tm, "slopeATR": 0.0, "emaOrder": Tm}
        return int(T), meta
    except Exception:
        return 0, {"Tm": 0, "slopeATR": 0.0, "emaOrder": 0}

def _calc_momentum(c, cfg):
    """动量打分（v3.0：返回±100）"""
    try:
        from ats_core.features.momentum import score_momentum
        M, meta = score_momentum(c, cfg)
        return int(M), meta
    except Exception:
        return 0, {"slope_now": 0.0, "accel": 0.0}

def _calc_cvd_flow(cvd_series, c, cfg):
    """CVD资金流打分（v3.0：返回±100）"""
    try:
        from ats_core.features.cvd_flow import score_cvd_flow
        C, meta = score_cvd_flow(cvd_series, c, cfg)
        return int(C), meta
    except Exception:
        return 0, {"cvd6": 0.0, "cvd_score": 0}

def _calc_structure(h, l, c, ema30_last, atr_now, cfg, ctx):
    """结构打分（v3.0：返回±100）"""
    try:
        from ats_core.features.structure_sq import score_structure
        S, meta = score_structure(h, l, c, ema30_last, atr_now, cfg, ctx)
        return int(S), meta
    except Exception:
        return 0, {"theta": 0.4, "icr": 0.5, "retr": 0.5}

def _calc_volume(vol):
    """量能打分（v3.0：返回±100）"""
    try:
        from ats_core.features.volume import score_volume
        V, meta = score_volume(vol)
        return int(V), meta
    except Exception:
        return 0, {"v5v20": 1.0, "vroc_abs": 0.0}

def _calc_oi(symbol, closes, cfg, cvd6_fallback):
    """持仓打分（v3.0：返回±100，移除side_long）"""
    try:
        from ats_core.features.open_interest import score_open_interest
        O, meta = score_open_interest(symbol, closes, cfg, cvd6_fallback)
        return int(O), meta
    except Exception:
        return 0, {"oi1h_pct": None, "oi24h_pct": None}

def _calc_environment(h, l, c, atr_now, cfg):
    """环境打分（v3.0：返回±100）"""
    try:
        from ats_core.features.environment import environment_score
        E, meta = environment_score(h, l, c, atr_now, cfg)
        return int(E), meta
    except Exception:
        return 0, {"chop": 50.0, "room": 0.5}

def _calc_fund_leading(oi_change_pct, vol_ratio, cvd_change, price_change_pct, price_slope, cfg):
    """资金领先性打分（v3.0：返回±100，移除side_long）"""
    try:
        from ats_core.features.fund_leading import score_fund_leading
        F, meta = score_fund_leading(oi_change_pct, vol_ratio, cvd_change, price_change_pct, price_slope, cfg)
        return int(F), meta
    except Exception as e:
        # 兜底：返回中性分数
        return 0, {
            "fund_momentum": 0.0,
            "price_momentum": 0.0,
            "leading_raw": 0.0,
            "error": str(e)
        }

def _calc_quality(scores: Dict, n_klines: int, n_oi: int) -> float:
    """
    质量系数 Q ∈ [0.6, 1.0]（v3.0：适配±100）
    考虑：样本完备性、不过度、非拥挤等
    """
    Q = 1.0

    # 样本不足
    if n_klines < 100:
        Q *= 0.85
    if n_oi < 50:
        Q *= 0.90

    # 维度弱证据过多（绝对值<65的维度）
    weak_dims = sum(1 for s in scores.values() if abs(s) < 65)
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
