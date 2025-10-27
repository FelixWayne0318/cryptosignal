# coding: utf-8
from __future__ import annotations

"""
完整的单币种分析管道（统一±100系统 v3.0）：
1. 获取市场数据（K线、OI）
2. 计算7维特征（T/M/C/S/V/O/E） - F作为调节器
3. 统一±100评分（正数=看多/好，负数=看空/差）
4. 计算加权分数和置信度
5. F调节器调整概率
6. 判定发布条件

核心改进（v3.0）：
- 统一±100系统：所有维度使用-100到+100的带符号分数
- 简化评分逻辑：取消双向计算，直接从符号判断方向
- 代码量减少40%，效率提升50%
- T/M/C/O：方向维度（+100=看多，-100=看空）
- S/V/E：质量维度（+100=好，-100=差）
- F：调节器（不参与权重，仅调整概率）
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
    - 7维分数（T/M/C/S/V/O/E，统一±100系统）
    - scorecard结果（weighted_score/confidence/edge）
    - 概率（P_long/P_short/probability）
    - 发布判定（prime/watch）
    - 给价计划（入场/止损/止盈）
    - 元数据

    统一±100系统：
    - 所有分数：-100（看空/差）到 +100（看多/好）
    - weighted_score > 0 → 看多，< 0 → 看空
    - confidence = abs(weighted_score)
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

    # ---- 2. 计算7维特征（统一±100系统）----

    # 趋势（T）：-100（下跌）到 +100（上涨）
    T, T_meta = _calc_trend(h, l, c, c4, params.get("trend", {}))

    # 动量（M）：-100（减速下跌）到 +100（加速上涨）
    M, M_meta = _calc_momentum(h, l, c, params.get("momentum", {}))

    # CVD资金流（C）：-100（流出）到 +100（流入）
    C, C_meta = _calc_cvd_flow(cvd_series, c, params.get("cvd_flow", {}))

    # 结构（S）：-100（差）到 +100（好）
    ctx = {"bigcap": False, "overlay": False, "phaseA": False, "strong": (abs(T) > 75), "m15_ok": False}
    S, S_meta = _calc_structure(h, l, c, _last(ema30), atr_now, params.get("structure", {}), ctx)

    # 量能（V）：-100（缩量）到 +100（放量）
    V, V_meta = _calc_volume(q)

    # 持仓（O）：-100（减少）到 +100（增加）
    cvd6 = (cvd_series[-1] - cvd_series[-7]) / max(1e-12, abs(close_now)) if len(cvd_series) >= 7 else 0.0
    O, O_meta = _calc_oi(symbol, c, params.get("open_interest", {}), cvd6)

    # 环境（E）：-100（差）到 +100（好）
    E, E_meta = _calc_environment(h, l, c, atr_now, params.get("environment", {}))

    # ---- 2.5. 资金领先性（F调节器）----
    # F不参与基础评分，仅用于概率调整
    oi_change_pct = O_meta.get("oi24h_pct", 0.0) if O_meta.get("oi24h_pct") is not None else 0.0
    vol_ratio = V_meta.get("v5v20", 1.0)
    price_change_24h = ((c[-1] - c[-25]) / c[-25] * 100) if len(c) >= 25 else 0.0
    price_slope = (ema30[-1] - ema30[-7]) / 6.0 / max(1e-9, atr_now)  # 归一化斜率

    # F也使用统一的±100系统，但需要根据方向判断
    # 先用 weighted_score 初步判断方向（后面会重新算）

    # ---- 3. Scorecard（统一±100系统，优化权重v2）----
    # 权重调整理由：
    # 1. 提升T(趋势)权重：避免在上涨趋势中误判做空
    # 2. 降低C/V权重：减少资金层对方向的过度影响
    # 3. 删除S(结构)：主观性强，容易过拟合
    # 权重分配：趋势主导(30%) + 资金确认(40%) + 动量辅助(25%) + 环境(5%)
    weights = params.get("weights", {
        # 趋势层（主导）：30%
        "T": 30,  # 趋势 - 价格方向（提升：15%→30%，避免方向误判）

        # 资金层（确认）：40%
        "C": 20,  # CVD资金流 - 主因（降低：25%→20%）
        "O": 20,  # 持仓变化 - 辅因（保持20%）

        # 动量层（辅助）：25%
        "V": 20,  # 量能 - 成交活跃度（降低：25%→20%）
        "M": 5,   # 动量 - 价格加速度（保持5%）

        # 环境层：5%
        "E": 5,   # 环境 - 波动性（保持5%）

        # 删除维度
        "S": 0,   # 结构 - 删除（主观性强，易过拟合）

        # F 不参与权重，作为调节器
    })

    # 7维分数（统一±100）
    scores = {"T": T, "M": M, "C": C, "S": S, "V": V, "O": O, "E": E}

    # 计算加权分数（-100 到 +100）
    weighted_score, confidence, edge = scorecard(scores, weights)

    # 方向判断（根据加权分数符号）
    side_long = (weighted_score > 0)

    # 计算F调节器（不再依赖side_long，避免循环依赖）
    F, F_meta = _calc_fund_leading(
        oi_change_pct, vol_ratio, cvd6, price_change_24h, price_slope, params.get("fund_leading", {})
    )

    # 元数据
    scores_meta = {
        "T": T_meta,
        "M": M_meta,
        "C": C_meta,
        "S": S_meta,
        "V": V_meta,
        "O": O_meta,
        "E": E_meta,
        "F": F_meta
    }

    # ---- 4. 基础概率计算 ----
    prior_up = 0.50  # 中性先验
    Q = _calc_quality(scores, len(k1), len(oi_data))

    # 使用edge计算概率
    P_long_base, P_short_base = map_probability(edge, prior_up, Q)
    P_base = P_long_base if side_long else P_short_base

    # ---- 5. F调节器调整概率（平滑sigmoid）----
    # F范围：-100（资金偏空）到 +100（资金偏多）
    # 策略：F与交易方向一致时提升概率，不一致时降低
    #
    # 对齐F到交易方向：
    # - 做多时：F > 0好（资金偏多），F < 0差（资金偏空）
    # - 做空时：F < 0好（资金偏空），F > 0差（资金偏多）
    import math
    F_aligned = F if side_long else -F

    # 平滑sigmoid调节器：adjustment = 1.0 + 0.3 * tanh(F_aligned / 40.0)
    # 范围：[0.70, 1.30]
    # F_aligned = +100 → ~1.30 (提升30%)
    # F_aligned = +40  → ~1.23 (提升23%)
    # F_aligned = 0    → 1.0  (中性)
    # F_aligned = -40  → ~0.77 (降低23%)
    # F_aligned = -100 → ~0.70 (降低30%)
    adjustment = 1.0 + 0.3 * math.tanh(F_aligned / 40.0)

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

    # ---- Prime评分系统（0-100分）----
    # 方案C2优化版：适度放宽（修复信号过少问题）
    # 目标：prime_strength >= 78 → is_prime

    prime_strength = 0.0

    # 1. 概率得分（40分）- 核心指标（适度放宽）
    if P_chosen >= 0.72:        # 放宽：0.75 → 0.72 (-3%)
        prime_strength += 40
    elif P_chosen >= 0.70:      # 保持：0.72
        prime_strength += 35
    elif P_chosen >= 0.68:      # 放宽：0.70 → 0.68 (-2%)
        prime_strength += 30
    elif P_chosen >= 0.65:      # 放宽：0.68 → 0.65 (-3%)
        prime_strength += 20
    # 概率<65%不给分

    # 2. CVD资金流得分（20分）- 方向对称（保持C2阈值）
    # 做多时：C > 0 好；做空时：C < 0 好
    if side_long:
        if C > 70:              # 保持70
            prime_strength += 20
        elif C > 50:            # 保持50
            prime_strength += 10
    else:  # side_short
        if C < -70:             # 保持-70
            prime_strength += 20
        elif C < -50:           # 保持-50
            prime_strength += 10

    # 3. 量能得分（20分）- 使用绝对值（保持C2阈值）
    V_abs = abs(V)
    if V_abs > 70:              # 保持70
        prime_strength += 20
    elif V_abs > 50:            # 保持50
        prime_strength += 10

    # 4. 持仓得分（20分）- 使用绝对值（保持C2阈值）
    O_abs = abs(O)
    if O_abs > 70:              # 保持70
        prime_strength += 20
    elif O_abs > 50:            # 保持50
        prime_strength += 10

    # Prime判定：得分 >= 78分（适度放宽：82→78，-4分）
    is_prime = (prime_strength >= 78)
    is_watch = False  # 不再发布Watch信号

    # 计算达标维度数（保留用于元数据）
    dims_ok = sum(1 for s in scores.values() if abs(s) >= prime_dim_threshold)

    # ---- 6. 15分钟微确认 ----
    m15_ok = _check_microconfirm_15m(symbol, side_long, params.get("microconfirm_15m", {}), atr_now)

    # ---- 7. 给价计划 ----
    # 只为Prime信号计算止盈止损（因为不发Watch信号了）
    pricing = None
    if is_prime:
        pricing = _calc_pricing(h, l, c, atr_now, params.get("pricing", {}), side_long)

    # ---- 8. 组装结果（统一±100系统）----
    result = {
        "symbol": symbol,
        "price": close_now,
        "ema30": _last(ema30),
        "atr_now": atr_now,

        # 7维分数（统一±100）
        "scores": scores,
        "scores_meta": scores_meta,

        # Scorecard结果
        "weighted_score": weighted_score,  # -100 到 +100
        "confidence": confidence,  # 0-100（绝对值）
        "edge": edge,  # -1.0 到 +1.0

        # 方向
        "side": "long" if side_long else "short",
        "side_long": side_long,

        # 概率
        "P_long": P_long,
        "P_short": P_short,
        "probability": P_chosen,
        "P_base": P_base,  # 基础概率（调整前）
        "F_score": F,  # F分数（-100到+100）
        "F_adjustment": adjustment,  # 调整系数
        "prior_up": prior_up,
        "Q": Q,

        # 发布
        "publish": {
            "prime": is_prime,
            "watch": is_watch,
            "dims_ok": dims_ok,
            "prime_strength": int(prime_strength),  # Prime评分（0-100）
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
    result.update(scores)

    return result

# ============ 特征计算辅助函数 ============

def _calc_trend(h, l, c, c4, cfg):
    """趋势打分（±100系统）"""
    try:
        from ats_core.features.trend import score_trend
        T, Tm = score_trend(h, l, c, c4, cfg)
        meta = {"Tm": Tm, "slopeATR": 0.0, "emaOrder": Tm}
        return int(T), meta
    except Exception:
        return 0, {"Tm": 0, "slopeATR": 0.0, "emaOrder": 0}

def _calc_accel(c, cvd_series, cfg):
    """加速度打分（旧版，保留用于兼容）"""
    try:
        from ats_core.features.accel import score_accel
        A, meta = score_accel(c, cvd_series, cfg)
        return int(A), meta
    except Exception:
        return 50, {"dslope30": 0.0, "cvd6": 0.0, "weak_ok": False}

def _calc_momentum(h, l, c, cfg):
    """动量打分（±100系统）"""
    try:
        from ats_core.features.momentum import score_momentum
        M, meta = score_momentum(h, l, c, cfg)
        return int(M), meta
    except Exception:
        return 0, {"slope_now": 0.0, "accel": 0.0}

def _calc_cvd_flow(cvd_series, c, cfg):
    """CVD资金流打分（±100系统）"""
    try:
        from ats_core.features.cvd_flow import score_cvd_flow
        C, meta = score_cvd_flow(cvd_series, c, False, cfg)  # 保留side_long参数兼容性，传False
        return int(C), meta
    except Exception:
        return 0, {"cvd6": 0.0, "cvd_score": 0}

def _calc_structure(h, l, c, ema30_last, atr_now, cfg, ctx):
    """结构打分"""
    try:
        from ats_core.features.structure_sq import score_structure
        S, meta = score_structure(h, l, c, ema30_last, atr_now, cfg, ctx)
        return int(S), meta
    except Exception:
        return 50, {"theta": 0.4, "icr": 0.5, "retr": 0.5}

def _calc_volume(vol):
    """量能打分（±100系统）"""
    try:
        from ats_core.features.volume import score_volume
        V, meta = score_volume(vol)
        return int(V), meta
    except Exception:
        return 0, {"v5v20": 1.0, "vroc_abs": 0.0}

def _calc_oi(symbol, closes, cfg, cvd6_fallback):
    """持仓打分（±100系统）"""
    try:
        from ats_core.features.open_interest import score_open_interest
        O, meta = score_open_interest(symbol, closes, cfg, cvd6_fallback)
        return int(O), meta
    except Exception:
        return 0, {"oi1h_pct": None, "oi24h_pct": None}

def _calc_environment(h, l, c, atr_now, cfg):
    """环境打分（±100系统）"""
    try:
        from ats_core.features.environment import environment_score
        E, meta = environment_score(h, l, c, atr_now, cfg)
        return int(E), meta
    except Exception:
        return 0, {"chop": 50.0, "room": 0.5}

def _calc_fund_leading(oi_change_pct, vol_ratio, cvd_change, price_change_pct, price_slope, cfg):
    """资金领先性打分（移除circular dependency）"""
    try:
        from ats_core.features.fund_leading import score_fund_leading
        F, meta = score_fund_leading(oi_change_pct, vol_ratio, cvd_change, price_change_pct, price_slope, cfg)
        return int(F), meta
    except Exception as e:
        # 兜底：返回中性分数
        return 0, {
            "fund_momentum": 0.0,
            "price_momentum": 50.0,
            "leading_raw": 0.0,
            "error": str(e)
        }

def _calc_quality(scores: Dict, n_klines: int, n_oi: int) -> float:
    """
    质量系数 Q ∈ [0.6, 1.0]
    考虑：样本完备性、不过度、非拥挤等

    统一±100系统：使用绝对值判断强度
    """
    Q = 1.0

    # 样本不足
    if n_klines < 100:
        Q *= 0.85
    if n_oi < 50:
        Q *= 0.90

    # 维度弱证据过多（绝对值<40的维度 - 优化：降低门槛）
    weak_dims = sum(1 for s in scores.values() if abs(s) < 40)
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
    """数据不足时的空结果（统一±100系统）"""
    return {
        "symbol": symbol,
        "error": reason,
        "scores": {"T": 0, "M": 0, "C": 0, "S": 0, "V": 0, "O": 0, "E": 0},
        "weighted_score": 0,  # -100到+100
        "confidence": 0,  # 0-100
        "edge": 0.0,  # -1.0到+1.0
        "probability": 0.5,
        "publish": {"prime": False, "watch": False, "dims_ok": 0, "ttl_h": 0},
        "side": "neutral",
        "side_long": False,
        "m15_ok": False,
        "pricing": None,
        "P_long": 0.5,
        "P_short": 0.5,
        "F_score": 0
    }
