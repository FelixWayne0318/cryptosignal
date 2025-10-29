# coding: utf-8
from __future__ import annotations

"""
完整的单币种分析管道（统一±100系统 v4.0 - 10维因子）：
1. 获取市场数据（K线、OI、订单簿、资金费率）
2. 计算10维特征（T/M/C/S/V/O/L/B/Q/I） + F调节器
3. 统一±100评分（正数=看多/好，负数=看空/差）
4. 计算加权分数和置信度（总权重160分，自动归一化到±100）
5. F调节器调整概率
6. 判定发布条件

核心改进（v4.0 - 10维因子系统）：
- 新增4个因子：L（流动性）、B（基差+资金费）、Q（清算）、I（独立性）
- 权重体系升级：100分 → 160分（4层架构）
- L/I因子自动归一化：0-100 → ±100（消除系统偏差）
- 方向因子：T/M/C/V/O/B/Q（±100）
- 质量因子转为方向：S/E/L/I（±100，归一化后）
- F调节器：不参与权重，仅调整概率

架构分层（160分总权重）：
- Layer 1（价格行为）：T(25) + M(15) + S(10) + V(15) = 65分
- Layer 2（资金流）：C(20) + O(20) = 40分
- Layer 3（微观结构）：L(20) + B(15) + Q(10) = 45分
- Layer 4（市场环境）：I(10) = 10分
"""

from typing import Dict, Any, Tuple, List
from statistics import median

from ats_core.cfg import CFG
from ats_core.sources.binance import get_klines, get_open_interest_hist, get_spot_klines
from ats_core.features.cvd import cvd_from_klines, cvd_mix_with_oi_price
from ats_core.scoring.scorecard import scorecard
from ats_core.scoring.probability import map_probability

# ========== 世界顶级优化模块 ==========
from ats_core.scoring.probability_v2 import (
    map_probability_sigmoid,
    get_adaptive_temperature
)
from ats_core.scoring.adaptive_weights import (
    get_regime_weights,
    blend_weights
)
from ats_core.features.multi_timeframe import multi_timeframe_coherence

# ========== 10维因子系统 ==========
from ats_core.factors_v2.liquidity import calculate_liquidity
from ats_core.factors_v2.basis_funding import calculate_basis_funding
from ats_core.factors_v2.liquidation import calculate_liquidation
from ats_core.factors_v2.independence import calculate_independence

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

def _analyze_symbol_core(
    symbol: str,
    k1: List,
    k4: List,
    oi_data: List,
    spot_k1: List = None,
    elite_meta: Dict[str, Any] = None,  # 保留参数兼容性，但不再使用
    k15m: List = None,  # MTF优化：15分钟K线
    k1d: List = None,   # MTF优化：1天K线
    orderbook: Dict = None,     # 10维因子：订单簿数据（L）
    mark_price: float = None,   # 10维因子：标记价格（B）
    funding_rate: float = None, # 10维因子：资金费率（B）
    spot_price: float = None,   # 10维因子：现货价格（B）
    liquidations: List = None,  # 10维因子：清算数据（Q）
    btc_klines: List = None,    # 10维因子：BTC K线（I）
    eth_klines: List = None     # 10维因子：ETH K线（I）
) -> Dict[str, Any]:
    """
    核心分析逻辑（使用已获取的K线数据）

    此函数包含完整的10维因子分析逻辑，但不负责获取数据。
    由analyze_symbol()和analyze_symbol_with_preloaded_klines()调用。

    Args:
        symbol: 交易对符号
        k1: 1小时K线数据
        k4: 4小时K线数据
        oi_data: OI数据
        spot_k1: 现货K线（可选）
        elite_meta: 已废弃，保留仅为兼容性
        k15m: 15分钟K线（可选，用于MTF）
        k1d: 1天K线（可选，用于MTF）
        orderbook: 订单簿数据（可选，用于L因子）
        mark_price: 标记价格（可选，用于B因子）
        funding_rate: 资金费率（可选，用于B因子）
        spot_price: 现货价格（可选，用于B因子）
        liquidations: 清算数据列表（可选，用于Q因子）
        btc_klines: BTC K线数据（可选，用于I因子）
        eth_klines: ETH K线数据（可选，用于I因子）

    Returns:
        分析结果字典
    """
    # DEBUG: 打印前3个币种的数据接收情况
    if symbol in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']:
        from ats_core.logging import log
        log(f"  [DEBUG] _analyze_symbol_core收到 {symbol}:")
        if orderbook:
            bids_count = len(orderbook.get('bids', []))
            asks_count = len(orderbook.get('asks', []))
            log(f"      orderbook: 存在 (bids={bids_count} asks={asks_count})")
        else:
            log(f"      orderbook: None")
        log(f"      mark_price: {mark_price}")
        log(f"      funding_rate: {funding_rate}")
        log(f"      spot_price: {spot_price}")
        log(f"      liquidations: {len(liquidations) if liquidations else 0}条")
        log(f"      btc_klines: {len(btc_klines) if btc_klines else 0}根")
        log(f"      eth_klines: {len(eth_klines) if eth_klines else 0}根")

    params = CFG.params or {}

    # 移除候选池先验逻辑（已废弃）
    elite_prior = {}
    bayesian_boost = 0.0  # 不再使用贝叶斯先验

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

    # 性能监控
    import time
    perf = {}

    # 基础指标
    t0 = time.time()
    ema30 = _ema(c, 30)
    atr_series = _atr(h, l, c, 14)
    atr_now = _last(atr_series)
    close_now = _last(c)
    perf['基础指标'] = time.time() - t0

    # CVD（现货+合约组合，如果有现货数据）
    t0 = time.time()
    cvd_series, cvd_mix = cvd_mix_with_oi_price(k1, oi_data, window=20, spot_klines=spot_k1)
    perf['CVD计算'] = time.time() - t0

    # ---- 2. 计算7维特征（统一±100系统）----

    # 趋势（T）：-100（下跌）到 +100（上涨）
    t0 = time.time()
    T, T_meta = _calc_trend(h, l, c, c4, params.get("trend", {}))
    perf['T趋势'] = time.time() - t0

    # 动量（M）：-100（减速下跌）到 +100（加速上涨）
    t0 = time.time()
    M, M_meta = _calc_momentum(h, l, c, params.get("momentum", {}))
    perf['M动量'] = time.time() - t0

    # CVD资金流（C）：-100（流出）到 +100（流入）
    t0 = time.time()
    C, C_meta = _calc_cvd_flow(cvd_series, c, params.get("cvd_flow", {}))
    perf['C资金流'] = time.time() - t0

    # 结构（S）：-100（差）到 +100（好）
    t0 = time.time()
    ctx = {"bigcap": False, "overlay": False, "phaseA": False, "strong": (abs(T) > 75), "m15_ok": False}
    S, S_meta = _calc_structure(h, l, c, _last(ema30), atr_now, params.get("structure", {}), ctx)
    perf['S结构'] = time.time() - t0

    # 量能（V）：-100（缩量）到 +100（放量）
    t0 = time.time()
    V, V_meta = _calc_volume(q)
    perf['V量能'] = time.time() - t0

    # 持仓（O）：-100（减少）到 +100（增加）
    t0 = time.time()
    cvd6 = (cvd_series[-1] - cvd_series[-7]) / max(1e-12, abs(close_now)) if len(cvd_series) >= 7 else 0.0
    O, O_meta = _calc_oi(symbol, c, params.get("open_interest", {}), cvd6)
    perf['O持仓'] = time.time() - t0

    # 环境（E）：-100（差）到 +100（好）
    t0 = time.time()
    E, E_meta = _calc_environment(h, l, c, atr_now, params.get("environment", {}))
    perf['E环境'] = time.time() - t0

    # ---- 2.1. 10维因子系统：新增因子 ----

    # 流动性（L）：0（差）到 100（好）→ 归一化到 ±100
    t0 = time.time()
    if orderbook is not None:
        try:
            L_raw, L_meta = calculate_liquidity(orderbook, params.get("liquidity", {}))
            # 归一化：0-100 → -100到+100（中性值50→0）
            # 低流动性（<50）→负分（不适合交易），高流动性（>50）→正分（适合交易）
            L = (L_raw - 50) * 2
            L_meta['raw_score'] = L_raw
            L_meta['normalized_score'] = L
        except Exception as e:
            from ats_core.logging import warn
            warn(f"L因子计算失败: {e}")
            L, L_meta = 0, {"error": str(e)}
    else:
        L, L_meta = 0, {"note": "无订单簿数据"}
    perf['L流动性'] = time.time() - t0

    # 基差+资金费（B）：-100（看跌）到 +100（看涨）- 方向维度
    t0 = time.time()
    if mark_price is not None and spot_price is not None and funding_rate is not None:
        try:
            B, B_meta = calculate_basis_funding(
                perp_price=mark_price,
                spot_price=spot_price,
                funding_rate=funding_rate,
                params=params.get("basis_funding", {})
            )
        except Exception as e:
            from ats_core.logging import warn
            warn(f"B因子计算失败: {e}")
            B, B_meta = 0, {"error": str(e)}
    else:
        B, B_meta = 0, {"note": "缺少mark_price/spot_price/funding_rate数据"}
    perf['B基差资金费'] = time.time() - t0

    # 清算密度（Q）：-100（空单密集清算，超涨回调，看空）到 +100（多单密集清算，超跌反弹，看多）
    # 逻辑：大量多单清算后抛压减轻可能反弹，大量空单清算后买压减轻可能回调
    t0 = time.time()
    if liquidations is not None and len(liquidations) > 0:
        try:
            Q, Q_meta = calculate_liquidation(
                liquidations=liquidations,
                current_price=close_now,
                liquidation_map=None,
                params=params.get("liquidation", {})
            )
        except Exception as e:
            from ats_core.logging import warn
            warn(f"Q因子计算失败: {e}")
            Q, Q_meta = 0, {"error": str(e)}
    else:
        Q, Q_meta = 0, {"note": "无清算数据"}
    perf['Q清算密度'] = time.time() - t0

    # 独立性（I）：0（完全相关）到 100（完全独立）→ 归一化到 ±100
    # 越独立越好，所以高分=正分，低分=负分
    t0 = time.time()
    if btc_klines and eth_klines and len(c) >= 25:  # 至少需要25个点（默认window=24）
        try:
            # 提取价格数据，确保三个序列长度一致
            # 使用最小长度来避免长度不匹配
            min_len = min(len(c), len(btc_klines), len(eth_klines))
            # 建议使用48小时数据，但至少需要25小时
            use_len = min(min_len, 48) if min_len >= 25 else 0

            if use_len >= 25:
                alt_prices = c[-use_len:]
                btc_prices = [_to_f(k[4]) for k in btc_klines[-use_len:]]  # Close prices
                eth_prices = [_to_f(k[4]) for k in eth_klines[-use_len:]]  # Close prices

                # 计算独立性分数（0-100）
                I_raw, beta_sum, I_meta = calculate_independence(
                    alt_prices=alt_prices,
                    btc_prices=btc_prices,
                    eth_prices=eth_prices,
                    params=params.get("independence", {})
                )

                # 归一化：0-100 → -100到+100（中性值50→0）
                # 低独立性（<50）→负分（跟随大盘），高独立性（>50）→正分（独立走势）
                I = (I_raw - 50) * 2
                I_meta['raw_score'] = I_raw
                I_meta['normalized_score'] = I
                I_meta['beta_sum'] = beta_sum
                I_meta['data_points'] = use_len
            else:
                I, I_meta = 0, {"note": f"数据不足（需要25小时，实际{min_len}小时）"}
        except Exception as e:
            from ats_core.logging import warn
            warn(f"I因子计算失败: {e}")
            I, I_meta = 0, {"error": str(e)}
    else:
        I, I_meta = 0, {"note": "缺少BTC/ETH K线数据"}
    perf['I独立性'] = time.time() - t0

    # ---- 2.5. 资金领先性（F调节器）----
    # F不参与基础评分，仅用于概率调整
    oi_change_pct = O_meta.get("oi24h_pct", 0.0) if O_meta.get("oi24h_pct") is not None else 0.0
    vol_ratio = V_meta.get("v5v20", 1.0)
    price_change_24h = ((c[-1] - c[-25]) / c[-25] * 100) if len(c) >= 25 else 0.0
    price_slope = (ema30[-1] - ema30[-7]) / 6.0 / max(1e-9, atr_now)  # 归一化斜率

    # ---- 2.5. 计算F调节器（提前计算，让F参与方向判断）----
    # F本身是带符号的（+表示资金领先，-表示价格领先），不需要依赖side_long
    F, F_meta = _calc_fund_leading(
        oi_change_pct, vol_ratio, cvd6, price_change_24h, price_slope, params.get("fund_leading", {})
    )

    # ---- 3. Scorecard（10维统一±100系统 + F调节器）----
    # 🚀 世界顶级优化：10维因子系统
    # 基础权重（从配置读取，10维系统：总权重160，归一化到±100）
    base_weights = params.get("weights", {
        # Layer 1: 价格行为层（65分）
        "T": 25,   # 趋势
        "M": 15,   # 动量
        "S": 10,   # 结构
        "V": 15,   # 量能（已包含触发K）
        # Layer 2: 资金流层（40分）
        "C": 20,   # CVD
        "O": 20,   # OI持仓
        # Layer 3: 微观结构层（45分）
        "L": 20,   # 流动性（新增）
        "B": 15,   # 基差+资金费（新增）
        "Q": 10,   # 清算密度（新增，待实现）
        # Layer 4: 市场环境层（10分）
        "I": 10,   # 独立性（新增，待实现）
        # 保留旧因子以兼容
        "E": 0,    # 环境（已废弃，权重0）
        "F": 0     # F现在是调节器，不参与权重
    })

    # 尝试提前获取市场状态（用于自适应权重）
    try:
        import time
        from ats_core.features.market_regime import calculate_market_regime
        cache_key = f"{int(time.time() // 60)}"
        market_regime_early, _ = calculate_market_regime(cache_key)
    except Exception:
        # 如果获取失败，使用中性值
        market_regime_early = 0

    # 计算当前波动率
    current_volatility = atr_now / close_now if close_now > 0 else 0.02

    # 获取自适应权重
    regime_weights = get_regime_weights(market_regime_early, current_volatility)

    # 平滑混合（70%自适应 + 30%基础）
    weights = blend_weights(regime_weights, base_weights, blend_ratio=0.7)

    # 10维分数（统一±100）+ F调节器
    scores = {
        # 8个旧因子
        "T": T, "M": M, "C": C, "S": S, "V": V, "O": O, "E": E,
        # 4个新因子
        "L": L, "B": B, "Q": Q, "I": I,
        # F调节器
        "F": F
    }

    # 计算加权分数（scorecard内部已归一化到±100）
    # 注意：scorecard函数通过 total/weight_sum 自动归一化，无需再除以1.6
    weighted_score, confidence, edge = scorecard(scores, weights)

    # 方向判断（根据加权分数符号）
    side_long = (weighted_score > 0)

    # 元数据
    scores_meta = {
        # 旧因子
        "T": T_meta,
        "M": M_meta,
        "C": C_meta,
        "S": S_meta,
        "V": V_meta,
        "O": O_meta,
        "E": E_meta,
        # 新因子
        "L": L_meta,
        "B": B_meta,
        "Q": Q_meta,
        "I": I_meta,
        # 调节器
        "F": F_meta
    }

    # ---- 4. 基础概率计算（🚀 世界顶级优化：Sigmoid映射）----
    prior_up = 0.50  # 中性先验
    quality_score = _calc_quality(scores, len(k1), len(oi_data))

    # 自适应温度参数
    temperature = get_adaptive_temperature(market_regime_early, current_volatility)

    # 使用Sigmoid概率映射（替代线性映射）
    P_long_base, P_short_base = map_probability_sigmoid(edge, prior_up, quality_score, temperature)
    P_base = P_long_base if side_long else P_short_base

    # 移除贝叶斯先验调整（已废弃候选池机制）

    # ---- 5. F调节器调整概率（平滑sigmoid + 极端值否决）----
    # F现在参与了加权（7%），但仍需作为概率调整器进行微调
    #
    # 改进：添加F极端值否决机制
    # - F极端反对（F_aligned < -70）→ 严厉惩罚（×0.6）
    # - F正常范围 → 平滑调整（[0.70, 1.30]）
    #
    # 对齐F到交易方向：
    # - 做多时：F > 0好（资金领先），F < 0差（价格领先）
    # - 做空时：F < 0好（资金领先空），F > 0差（价格领先多）
    import math
    F_aligned = F if side_long else -F

    # F极端值否决机制
    f_veto_warning = None
    if F_aligned < -70:
        # F强烈反对当前方向（资金/价格严重背离）
        adjustment = 0.60  # 严厉惩罚
        f_veto_warning = "⚠️ F极端反对（资金/价格严重背离）"
    else:
        # 正常平滑调整：adjustment = 1.0 + 0.3 * tanh(F_aligned / 40.0)
        # 范围：[0.70, 1.30]
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

    # ---- Prime评分系统（v4.0 - 基于10维因子系统）----
    # 重大改进：使用10维综合评分替代4维独立评分
    #
    # 旧逻辑问题：
    # - 只用了概率(40) + C(20) + V(20) + O(20) = 100分
    # - 新增的L（流动性）和B（基差+资金费）完全没有参与
    # - 导致低流动性或极端资金费的币种仍能获得高分
    #
    # 新逻辑：
    # - 基础强度（60分）= confidence（10维加权分数的绝对值）× 0.6
    # - 概率加成（40分）= 基于P_chosen的额外奖励
    # - 总分 0-100，所有10维因子都参与
    #
    # 目标：prime_strength >= 65 → is_prime

    prime_strength = 0.0

    # 1. 基础强度：基于10维综合评分（60分）
    # confidence = abs(weighted_score)，已包含T/M/C/S/V/O/L/B/Q/I全部因子
    # 范围：0-100 → 映射到 0-60分
    base_strength = confidence * 0.6
    prime_strength += base_strength

    # 2. 概率加成（40分）- 保持原逻辑
    # 60%→0分, 75%→40分, >75%截断
    prob_bonus = 0.0
    if P_chosen >= 0.60:
        prob_bonus = min(40.0, (P_chosen - 0.60) / 0.15 * 40.0)
        prime_strength += prob_bonus

    # 记录各部分得分（用于调试）
    prime_breakdown = {
        'base_strength': round(base_strength, 1),
        'prob_bonus': round(prob_bonus, 1),
        'confidence': confidence,
        'P_chosen': round(P_chosen, 4)
    }

    # ---- 🚀 世界顶级优化：多时间框架协同验证（缓存版，零API调用）----
    # 性能优化：使用预加载的K线数据，零API调用
    # 从20-40秒/币种 降至 <0.01秒/币种
    mtf_result = None
    mtf_coherence = 100.0  # 默认值

    try:
        from ats_core.features.multi_timeframe import multi_timeframe_coherence_cached

        # 使用缓存版MTF（零API调用）
        mtf_result = multi_timeframe_coherence_cached(
            symbol=symbol,
            k15m=k15m,  # 预加载的15m K线
            k1h=k1,     # 预加载的1h K线
            k4h=k4,     # 预加载的4h K线
            k1d=k1d,    # 预加载的1d K线
            verbose=False
        )
        mtf_coherence = mtf_result['coherence_score']

        # 一致性过滤: <60分惩罚
        if mtf_coherence < 60:
            # 时间框架不一致，降低概率和Prime评分
            P_chosen *= 0.85  # 惩罚15%
            prime_strength *= 0.90  # Prime评分降低10%

            # 更新对应方向的概率
            if side_long:
                P_long = P_chosen
            else:
                P_short = P_chosen
    except Exception as e:
        # MTF验证失败，不影响主流程
        from ats_core.logging import warn
        warn(f"[MTF-Cached] {symbol}: 多时间框架验证失败 - {e}")

    # Prime判定：得分 >= 65分（放宽阈值以发现更多信号）
    is_prime = (prime_strength >= 65)
    is_watch = False  # 不再发布Watch信号

    # 计算达标维度数（保留用于元数据）
    dims_ok = sum(1 for s in scores.values() if abs(s) >= prime_dim_threshold)

    # ---- 6. BTC/ETH市场过滤器（方案B - 独立过滤 + 避免双重惩罚）----
    # 计算市场大盘趋势，避免逆势做单
    import time
    cache_key = f"{int(time.time() // 60)}"  # 按分钟缓存

    try:
        from ats_core.features.market_regime import calculate_market_regime, apply_market_filter

        # 计算市场趋势
        market_regime, market_meta = calculate_market_regime(cache_key)

        # 应用市场过滤（逆势惩罚）
        P_chosen_filtered, prime_strength_filtered, market_adjustment_reason = apply_market_filter(
            "long" if side_long else "short",
            P_chosen,
            prime_strength,
            market_regime
        )

        # 改进：避免双重惩罚（F调节器 + 市场过滤器）
        # 策略：只应用更严格的一个惩罚
        if market_adjustment_reason:
            # 计算市场过滤器的乘数
            market_multiplier = P_chosen_filtered / P_chosen if P_chosen > 0 else 1.0

            # 比较F调节器和市场过滤器的惩罚
            # adjustment来自F调节器，market_multiplier来自市场过滤器
            # 取两者中更小的（更严格的惩罚）
            if adjustment < 1.0 and market_multiplier < 1.0:
                # 两个都是惩罚，取更严格的
                combined_multiplier = min(adjustment, market_multiplier)
                # 重新计算概率（避免叠加惩罚）
                P_chosen = P_base * combined_multiplier
                # 更新对应方向的概率
                if side_long:
                    P_long = P_chosen
                else:
                    P_short = P_chosen
                # 添加合并惩罚的说明
                if combined_multiplier == adjustment:
                    market_adjustment_reason = f"（F调节器惩罚更严：×{adjustment:.2f}）"
                else:
                    market_adjustment_reason = market_adjustment_reason + f"（已合并F惩罚）"
            else:
                # 正常应用市场过滤（奖励或单一惩罚）
                P_chosen = P_chosen_filtered

            prime_strength = prime_strength_filtered
            is_prime = (prime_strength >= 65)  # 重新判定Prime

        penalty_reason = market_adjustment_reason

    except Exception as e:
        # 市场过滤器失败时不影响主流程
        market_regime = 0
        market_meta = {"error": str(e), "btc_trend": 0, "eth_trend": 0, "regime_desc": "计算失败"}
        penalty_reason = ""

    # ---- 7. 15分钟微确认 ----
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

        # 性能分析（用于调试）
        "perf": perf,

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
        "quality_score": quality_score,  # 质量系数（0.6-1.0）

        # 发布
        "publish": {
            "prime": is_prime,
            "watch": is_watch,
            "dims_ok": dims_ok,
            "prime_strength": int(prime_strength),  # Prime评分（0-100）
            "prime_breakdown": prime_breakdown,  # Prime评分详细分解（v4.0新增）
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

        # 市场过滤器（BTC/ETH大盘趋势）
        "market_regime": market_regime,
        "market_meta": market_meta,
        "market_penalty": penalty_reason if penalty_reason else None,

        # F调节器否决警告
        "f_veto_warning": f_veto_warning,

        # 🚀 世界顶级优化模块元数据
        "optimization_meta": {
            # Sigmoid概率映射
            "probability_method": "sigmoid",
            "temperature": temperature,
            "volatility": current_volatility,

            # 自适应权重
            "weights_method": "regime_dependent",
            "base_weights": base_weights,
            "regime_weights": regime_weights,
            "final_weights": weights,
            "blend_ratio": 0.7,

            # 多时间框架
            "mtf_coherence": mtf_coherence,
            "mtf_result": mtf_result,
        },
    }

    # 兼容旧版 telegram_fmt.py：将分数直接放在顶层
    result.update(scores)

    return result


def analyze_symbol(symbol: str) -> Dict[str, Any]:
    """
    完整分析单个交易对（数据获取 + 分析）

    此函数负责：
    1. 从API获取K线和OI数据
    2. 调用_analyze_symbol_core()进行分析

    返回：
    - 8维分数（T/M/C/S/V/O/E/F，统一±100系统）
    - scorecard结果（weighted_score/confidence/edge）
    - 概率（P_long/P_short/probability）
    - 发布判定（prime/watch）
    - 给价计划（入场/止损/止盈）
    - 元数据

    统一±100系统：
    - 所有分数：-100（看空/差）到 +100（看多/好）
    - weighted_score > 0 → 看多，< 0 → 看空
    - confidence = abs(weighted_score)

    Args:
        symbol: 交易对符号
    """
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

    # 10维因子系统：获取L/B因子所需数据
    from ats_core.sources.binance import (
        get_orderbook_snapshot,
        get_mark_price,
        get_funding_rate,
        get_spot_price
    )

    # 获取订单簿数据（L因子）
    try:
        orderbook = get_orderbook_snapshot(symbol, limit=20)
    except Exception as e:
        from ats_core.logging import warn
        warn(f"获取{symbol}订单簿失败: {e}")
        orderbook = None

    # 获取标记价格（B因子）
    try:
        mark_price = get_mark_price(symbol)
    except Exception as e:
        from ats_core.logging import warn
        warn(f"获取{symbol}标记价格失败: {e}")
        mark_price = None

    # 获取资金费率（B因子）
    try:
        funding_rate = get_funding_rate(symbol)
    except Exception as e:
        from ats_core.logging import warn
        warn(f"获取{symbol}资金费率失败: {e}")
        funding_rate = None

    # 获取现货价格（B因子）
    try:
        spot_price = get_spot_price(symbol)
    except Exception as e:
        from ats_core.logging import warn
        warn(f"获取{symbol}现货价格失败: {e}")
        spot_price = None

    # ---- 2. 调用核心分析函数 ----
    return _analyze_symbol_core(
        symbol=symbol,
        k1=k1,
        k4=k4,
        oi_data=oi_data,
        spot_k1=spot_k1,
        elite_meta=None,  # 不再使用候选池元数据
        orderbook=orderbook,         # L（流动性）
        mark_price=mark_price,       # B（基差+资金费）
        funding_rate=funding_rate,   # B（基差+资金费）
        spot_price=spot_price        # B（基差+资金费）
    )


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


# ============ 批量扫描优化：支持预加载K线 ============

def analyze_symbol_with_preloaded_klines(
    symbol: str,
    k1h: List,
    k4h: List,
    oi_data: List = None,
    spot_k1h: List = None,
    elite_meta: Dict = None,
    k15m: List = None,  # MTF优化：15分钟K线
    k1d: List = None,   # MTF优化：1天K线
    orderbook: Dict = None,     # 10维因子：订单簿数据（L）
    mark_price: float = None,   # 10维因子：标记价格（B）
    funding_rate: float = None, # 10维因子：资金费率（B）
    spot_price: float = None,   # 10维因子：现货价格（B）
    liquidations: List = None,  # 10维因子：清算数据（Q）
    btc_klines: List = None,    # 10维因子：BTC K线（I）
    eth_klines: List = None     # 10维因子：ETH K线（I）
) -> Dict[str, Any]:
    """
    使用预加载的K线数据分析币种（用于批量扫描优化）

    Args:
        symbol: 交易对符号
        k1h: 1小时K线数据（300根）
        k4h: 4小时K线数据（200根）
        oi_data: OI数据（可选）
        spot_k1h: 现货1小时K线（可选，用于CVD）
        elite_meta: Elite Universe元数据（可选）
        k15m: 15分钟K线（可选，用于MTF）
        k1d: 1天K线（可选，用于MTF）
        orderbook: 订单簿数据（可选，用于L因子）
        mark_price: 标记价格（可选，用于B因子）
        funding_rate: 资金费率（可选，用于B因子）
        spot_price: 现货价格（可选，用于B因子）
        liquidations: 清算数据列表（可选，用于Q因子）
        btc_klines: BTC K线数据（可选，用于I因子）
        eth_klines: ETH K线数据（可选，用于I因子）

    Returns:
        分析结果字典（格式与analyze_symbol相同）

    使用场景:
        批量扫描时从WebSocket缓存读取K线，避免重复API调用

    注意:
        这个函数不会自动获取K线数据，调用者必须提供
    """
    # 🔧 修复：使用预加载的数据调用核心分析函数
    # 如果oi_data为None，使用空列表避免NoneType错误
    return _analyze_symbol_core(
        symbol=symbol,
        k1=k1h,
        k4=k4h,
        oi_data=oi_data if oi_data is not None else [],
        spot_k1=spot_k1h,
        elite_meta=elite_meta,
        k15m=k15m,  # 传递15m K线
        k1d=k1d,    # 传递1d K线
        orderbook=orderbook,         # 传递订单簿（L）
        mark_price=mark_price,       # 传递标记价格（B）
        funding_rate=funding_rate,   # 传递资金费率（B）
        spot_price=spot_price,       # 传递现货价格（B）
        liquidations=liquidations,   # 传递清算数据（Q）
        btc_klines=btc_klines,       # 传递BTC K线（I）
        eth_klines=eth_klines        # 传递ETH K线（I）
    )
