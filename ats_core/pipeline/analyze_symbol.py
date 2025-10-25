# coding: utf-8
from __future__ import annotations

"""
完整的单币种分析管道（改进版v2.0）：
1. 获取市场数据（K线、OI）
2. 计算7维特征（T/M/C/S/V/O/E） - F作为调节器
3. 双向评分（long/short）
4. 计算基础概率
5. F调节器调整概率
6. 判定发布条件

改进点：
- T：软映射 + 多空对称
- M：从A分离出价格动量
- C：从A分离出CVD资金流
- F：从评分维度改为概率调节器
"""

from typing import Dict, Any, Tuple, List
from statistics import median

from ats_core.cfg import CFG
from ats_core.sources.binance import get_klines, get_open_interest_hist, get_spot_klines
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

    # 尝试获取现货K线（用于CVD组合计算）
    # 如果失败（某些币只有合约），cvd_mix_with_oi_price会自动降级到只用合约CVD
    try:
        spot_k1 = get_spot_klines(symbol, "1h", 300)
    except Exception:
        spot_k1 = None

    # ---- 新币检测（优先判断，决定数据要求）----
    new_coin_cfg = params.get("new_coin", {})
    coin_age_hours = len(k1) if k1 else 0
    coin_age_days = coin_age_hours / 24

    # 4级分级阈值
    ultra_new_hours = new_coin_cfg.get("ultra_new_hours", 24)  # 1-24小时：超新
    phaseA_days = new_coin_cfg.get("phaseA_days", 7)            # 1-7天：极度谨慎
    phaseB_days = new_coin_cfg.get("phaseB_days", 30)           # 7-30天：谨慎

    # 判断阶段
    is_ultra_new = coin_age_hours <= ultra_new_hours  # 1-24小时
    is_phaseA = coin_age_days <= phaseA_days and not is_ultra_new  # 1-7天
    is_phaseB = phaseA_days < coin_age_days <= phaseB_days  # 7-30天
    is_new_coin = coin_age_days <= phaseB_days

    if is_ultra_new:
        coin_phase = "ultra_new"  # 超新币（1-24小时）
        min_data = 10              # 至少10根1h K线
    elif is_phaseA:
        coin_phase = "phaseA"     # 阶段A（1-7天）
        min_data = 30
    elif is_phaseB:
        coin_phase = "phaseB"     # 阶段B（7-30天）
        min_data = 50
    else:
        coin_phase = "mature"     # 成熟币
        min_data = 50

    # 检查数据是否足够
    if not k1 or len(k1) < min_data:
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

    # CVD（现货+合约组合，如果有现货数据）
    cvd_series, cvd_mix = cvd_mix_with_oi_price(k1, oi_data, window=20, spot_klines=spot_k1)

    # ---- 2. 计算7维特征（改进版）----

    # 趋势（T）- 需要双向计算（新增side_long参数）
    T_long, T_meta_long = _calc_trend(h, l, c, c4, params.get("trend", {}), True)
    T_short, T_meta_short = _calc_trend(h, l, c, c4, params.get("trend", {}), False)

    # 动量（M）- 从A分离出来的价格动量
    M_long, M_meta_long = _calc_momentum(c, True, params.get("momentum", {}))
    M_short, M_meta_short = _calc_momentum(c, False, params.get("momentum", {}))

    # CVD资金流（C）- 从A分离出来的CVD
    C_long, C_meta_long = _calc_cvd_flow(cvd_series, c, True, params.get("cvd_flow", {}))
    C_short, C_meta_short = _calc_cvd_flow(cvd_series, c, False, params.get("cvd_flow", {}))

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

    # ---- 2.5. 资金领先性（F）- 需要双向计算 ----
    # F 需要的输入数据
    oi_change_pct = O_meta_long.get("oi24h_pct", 0.0) if O_meta_long.get("oi24h_pct") is not None else 0.0
    vol_ratio = V_meta.get("v5v20", 1.0)
    price_change_24h = ((c[-1] - c[-25]) / c[-25] * 100) if len(c) >= 25 else 0.0
    price_slope = (ema30[-1] - ema30[-7]) / 6.0 / max(1e-9, atr_now)  # 归一化斜率

    F_long, F_meta_long = _calc_fund_leading(
        oi_change_pct, vol_ratio, cvd6, price_change_24h, price_slope, True, params.get("fund_leading", {})
    )
    F_short, F_meta_short = _calc_fund_leading(
        oi_change_pct, vol_ratio, cvd6, price_change_24h, price_slope, False, params.get("fund_leading", {})
    )

    # ---- 3. Scorecard（改进版：7维基础评分，F作为调节器）----
    # 新权重：T、M、C、S、V、O、E（7维）
    weights = params.get("weights", {
        "T": 20,  # 趋势
        "M": 10,  # 动量（从A分离）
        "C": 10,  # CVD资金流（从A分离）
        "S": 10,  # 结构
        "V": 20,  # 量能
        "O": 15,  # 持仓
        "E": 15   # 环境
        # F 不参与权重，作为调节器
    })

    # 7维基础分数（不包含F）
    long_scores = {"T": T_long, "M": M_long, "C": C_long, "S": S_long, "V": V, "O": O_long, "E": E}
    short_scores = {"T": T_short, "M": M_short, "C": C_short, "S": S_short, "V": V, "O": O_short, "E": E}

    # 计算做多和做空的真实加权分数
    long_weighted, _, edge_long = scorecard(long_scores, weights)
    short_weighted, _, edge_short = scorecard(short_scores, weights)

    # **修复**：选择加权分数更高的方向（而不是简单的UpScore > DownScore）
    # 这样可以正确识别强势下跌趋势应该做空
    side_long = (long_weighted >= short_weighted)

    # 为了兼容旧逻辑，保留UpScore/DownScore
    UpScore = long_weighted
    DownScore = 100.0 - long_weighted
    edge = edge_long if side_long else edge_short
    chosen_scores = long_scores if side_long else short_scores
    chosen_meta = {
        "T": T_meta_long if side_long else T_meta_short,
        "M": M_meta_long if side_long else M_meta_short,
        "C": C_meta_long if side_long else C_meta_short,
        "S": S_meta_long if side_long else S_meta_short,
        "V": V_meta,
        "O": O_meta_long if side_long else O_meta_short,
        "E": E_meta,
        "F": F_meta_long if side_long else F_meta_short  # F保留用于显示
    }

    # ---- 4. 基础概率计算 ----
    prior_up = 0.50  # 中性先验，可以根据BTC/ETH环境调整
    Q = _calc_quality(chosen_scores, len(k1), len(oi_data))

    P_long_base, P_short_base = map_probability(edge, prior_up, Q)
    P_base = P_long_base if side_long else P_short_base

    # ---- 5. F调节器调整概率（改进版核心）----
    F_chosen = F_long if side_long else F_short

    # F作为调节器调整概率
    if F_chosen >= 70:
        # 资金领先价格，蓄势待发
        adjustment = 1.15  # 提升15%
    elif F_chosen >= 50:
        # 资金价格同步
        adjustment = 1.0
    elif F_chosen >= 30:
        # 价格略微领先
        adjustment = 0.9  # 降低10%
    else:
        # 价格远超资金，追高风险
        adjustment = 0.7  # 降低30%

    # 最终概率
    P_long = min(0.95, P_long_base * adjustment if side_long else P_long_base)
    P_short = min(0.95, P_short_base * adjustment if not side_long else P_short_base)
    P_chosen = P_long if side_long else P_short

    # ---- 6. 发布判定（4级分级标准）----
    publish_cfg = params.get("publish", {})

    # 新币特殊处理：应用分级标准
    if is_ultra_new:
        # 超新币（1-24小时）：超级谨慎
        prime_prob_min = new_coin_cfg.get("ultra_new_prime_prob_min", 0.70)
        prime_dims_ok_min = new_coin_cfg.get("ultra_new_dims_ok_min", 6)
        prime_dim_threshold = 70  # 提高单维度门槛
        watch_prob_min = 0.65  # 新币不发watch信号
    elif is_phaseA:
        # 阶段A（1-7天）：极度谨慎
        prime_prob_min = new_coin_cfg.get("phaseA_prime_prob_min", 0.65)
        prime_dims_ok_min = new_coin_cfg.get("phaseA_dims_ok_min", 5)
        prime_dim_threshold = publish_cfg.get("prime_dim_threshold", 65)
        watch_prob_min = 0.60
    elif is_phaseB:
        # 阶段B（7-30天）：谨慎
        prime_prob_min = new_coin_cfg.get("phaseB_prime_prob_min", 0.63)
        prime_dims_ok_min = new_coin_cfg.get("phaseB_dims_ok_min", 4)
        prime_dim_threshold = publish_cfg.get("prime_dim_threshold", 65)
        watch_prob_min = 0.60
    else:
        # 成熟币种：正常标准
        prime_prob_min = publish_cfg.get("prime_prob_min", 0.62)
        prime_dims_ok_min = publish_cfg.get("prime_dims_ok_min", 4)
        prime_dim_threshold = publish_cfg.get("prime_dim_threshold", 65)
        watch_prob_min = publish_cfg.get("watch_prob_min", 0.58)

    # 改进的Prime判定逻辑：
    # 1. 概率达标
    # 2. 原因指标（资金推动）全部达标：C（资金流）+ V（量能）+ O（持仓）
    #    这确保价格上涨/下跌是由真实资金推动的
    dims_ok = sum(1 for s in chosen_scores.values() if s >= prime_dim_threshold)

    # 原因指标（资金推动因素）
    # 注意：C现在是带符号的（-100到+100）
    # 做多：C >= 65（买入压力），做空：C <= -65（卖出压力）
    c_score = chosen_scores.get("C", 0)
    c_ok = (c_score >= 65) if side_long else (c_score <= -65)

    fund_dims_ok = all([
        c_ok,                                 # 资金流（带方向）
        chosen_scores.get("V", 0) >= 65,      # 量能
        chosen_scores.get("O", 0) >= 65       # 持仓
    ])

    is_prime = (P_chosen >= prime_prob_min) and fund_dims_ok
    is_watch = False  # 不再发布Watch信号，全部都是正式信号

    # ---- 6. 15分钟微确认 ----
    m15_ok = _check_microconfirm_15m(symbol, side_long, params.get("microconfirm_15m", {}), atr_now)

    # ---- 7. 给价计划 ----
    # 只为Prime信号计算止盈止损（因为不发Watch信号了）
    pricing = None
    if is_prime:
        pricing = _calc_pricing(h, l, c, atr_now, params.get("pricing", {}), side_long)

    # ---- 8. 组装结果（改进版）----
    result = {
        "symbol": symbol,
        "price": close_now,
        "ema30": _last(ema30),
        "atr_now": atr_now,

        # 7维分数（结构化）- T/M/C/S/V/O/E
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

        # 概率（改进版：包含调整信息）
        "P_long": P_long,
        "P_short": P_short,
        "probability": P_chosen,
        "P_base": P_base,  # 基础概率（调整前）
        "F_score": F_chosen,  # F分数
        "F_adjustment": adjustment,  # 调整系数
        "prior_up": prior_up,
        "Q": Q,

        # 发布
        "publish": {
            "prime": is_prime,
            "watch": is_watch,
            "dims_ok": dims_ok,
            "ttl_h": 8
        },

        # 新币信息
        "coin_age_days": round(coin_age_days, 1),
        "coin_phase": coin_phase,
        "is_new_coin": is_new_coin,

        # 微确认
        "m15_ok": m15_ok,

        # 给价
        "pricing": pricing,

        # CVD
        "cvd_z20": _zscore_last(cvd_series, 20) if cvd_series else 0.0,
        "cvd_mix_abs_per_h": abs(_last(cvd_mix)) if cvd_mix else 0.0,
    }

    # 兼容旧版 telegram_fmt.py：将分数直接放在顶层
    result.update(chosen_scores)

    return result

# ============ 特征计算辅助函数 ============

def _calc_trend(h, l, c, c4, cfg, side_long):
    """趋势打分（改进版：支持多空对称）"""
    try:
        from ats_core.features.trend import score_trend
        T, Tm = score_trend(h, l, c, c4, cfg, side_long)
        meta = {"Tm": Tm, "slopeATR": 0.0, "emaOrder": Tm}
        return int(T), meta
    except Exception:
        return 50, {"Tm": 0, "slopeATR": 0.0, "emaOrder": 0}

def _calc_accel(c, cvd_series, cfg):
    """加速度打分（旧版，保留用于兼容）"""
    try:
        from ats_core.features.accel import score_accel
        A, meta = score_accel(c, cvd_series, cfg)
        return int(A), meta
    except Exception:
        return 50, {"dslope30": 0.0, "cvd6": 0.0, "weak_ok": False}

def _calc_momentum(c, side_long, cfg):
    """动量打分（新版M维度）"""
    try:
        from ats_core.features.momentum import score_momentum
        M, meta = score_momentum(c, side_long, cfg)
        return int(M), meta
    except Exception:
        return 50, {"slope_now": 0.0, "accel": 0.0}

def _calc_cvd_flow(cvd_series, c, side_long, cfg):
    """CVD资金流打分（新版C维度）"""
    try:
        from ats_core.features.cvd_flow import score_cvd_flow
        C, meta = score_cvd_flow(cvd_series, c, side_long, cfg)
        return int(C), meta
    except Exception:
        return 50, {"cvd6": 0.0, "cvd_score": 50}

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

def _calc_fund_leading(oi_change_pct, vol_ratio, cvd_change, price_change_pct, price_slope, side_long, cfg):
    """资金领先性打分"""
    try:
        from ats_core.features.fund_leading import score_fund_leading
        F, meta = score_fund_leading(oi_change_pct, vol_ratio, cvd_change, price_change_pct, price_slope, side_long, cfg)
        return int(F), meta
    except Exception as e:
        # 兜底：返回中性分数
        return 50, {
            "fund_momentum": 50.0,
            "price_momentum": 50.0,
            "leading_raw": 0.0,
            "error": str(e)
        }

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
    except Exception as e:
        from ats_core.logging import warn
        warn(f"pricing计算失败: {e}, cfg={cfg}")
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
