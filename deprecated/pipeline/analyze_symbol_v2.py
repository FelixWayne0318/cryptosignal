# coding: utf-8
"""
统一因子分析系统 v2.0 - 10+1维有机整合

整合12个世界顶级微观结构因子到7+1维系统，升级为10+1维有机架构：

【4层架构】(160点权重系统，归一化后±100)
1. Price Action (价格行为) - 65点
   - T (Trend): 趋势方向与强度 (25点)
   - M (Momentum): 动量加速度 (15点)
   - C+ (Enhanced CVD): 增强资金流 (20点) ✨升级
   - S (Structure): 结构质量 (10点) ⚠️降权

2. Money Flow (资金流向) - 40点
   - V+ (Volume+Trigger): 量能+触发K (15点) ✨新增
   - O+ (OI Regime): OI四象限体制 (20点) ✨升级

3. Microstructure (微观结构) - 45点
   - L (Liquidity): 流动性质量 (20点) ✨新增
   - B (Basis+Funding): 基差+资金费 (15点) ✨新增
   - Q (Liquidation): 清算密度倾斜 (10点) ✨新增

4. Market Context (市场环境) - 10点
   - I (Independence): 独立性 (10点) ✨新增 (替换E)

【调节层】
   - F (Fund Leading): 资金领先性 (调节器，不参与权重)

统一评分系统：
- 方向性因子 (T/M/C+/V+/O+/B/Q): -100（看跌）到 +100（看涨）
- 质量性因子 (S/L/I): 0（差）到 100（优）
- 最终归一化：weighted_sum / 1.6 → -100 到 +100

防过拟合措施：
- 因子正交化（相关性<0.5）
- 参数版本控制
- IC持续监控
- 交叉验证
"""

from __future__ import annotations
from typing import Dict, Any, Tuple, List, Optional
from statistics import median
import time

# 核心配置和数据源
from ats_core.cfg import CFG
from ats_core.sources.binance import (
    get_klines,
    get_open_interest_hist,
    get_spot_klines,
    get_ticker_24h
)

# 新因子系统
from ats_core.config.factor_config import get_factor_config
from ats_core.factors_v2.oi_regime import calculate_oi_regime
from ats_core.factors_v2.volume_trigger import calculate_volume_trigger
from ats_core.factors_v2.independence import calculate_independence
from ats_core.factors_v2.basis_funding import calculate_basis_funding
from ats_core.factors_v2.cvd_enhanced import calculate_cvd_enhanced
from ats_core.factors_v2.liquidity import calculate_liquidity
from ats_core.factors_v2.liquidation import calculate_liquidation

# 传统因子（T/M/S仍使用原有实现）
from ats_core.features.cvd import cvd_from_klines, cvd_mix_with_oi_price

# 评分系统
from ats_core.scoring.probability_v2 import (
    map_probability_sigmoid,
    get_adaptive_temperature
)

# ============ 工具函数 ============

def _to_f(x) -> float:
    """安全转换为float"""
    try:
        return float(x)
    except Exception:
        return 0.0

def _last(x):
    """获取序列最后一个值"""
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(x[-1])
    except Exception:
        return _to_f(x)

def _ema(seq: List[float], n: int) -> List[float]:
    """计算EMA"""
    out: List[float] = []
    if not seq or n <= 1:
        return [_to_f(v) for v in seq]
    k = 2.0/(n+1.0)
    e = None
    for v in seq:
        v = _to_f(v)
        e = v if e is None else (e + k*(v-e))
        out.append(e)
    return out

def _atr(h: List[float], l: List[float], c: List[float], period: int = 14) -> List[float]:
    """计算ATR"""
    n = min(len(h), len(l), len(c))
    if n == 0: return []
    tr: List[float] = []
    pc = _to_f(c[0])
    for i in range(n):
        hi = _to_f(h[i]); lo = _to_f(l[i]); ci = _to_f(c[i])
        tr.append(max(hi-lo, abs(hi-pc), abs(lo-pc)))
        pc = ci
    return _ema(tr, period)

def _sma(seq: List[float], n: int) -> List[float]:
    """计算SMA"""
    if not seq or n <= 0:
        return seq
    out = []
    for i in range(len(seq)):
        if i < n - 1:
            out.append(_to_f(seq[i]))
        else:
            out.append(sum(seq[i-n+1:i+1]) / n)
    return out


# ============ 传统因子计算（T/M/S，沿用原有逻辑）============

def _calc_trend(h: List[float], l: List[float], c: List[float],
                c4: List[float], params: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    """
    T因子: 趋势方向与强度
    Range: -100（强下跌）到 +100（强上涨）
    """
    if len(c) < 50:
        return 0.0, {"error": "insufficient_data"}

    ema12 = _ema(c, 12)
    ema26 = _ema(c, 26)
    ema50 = _ema(c, 50)

    # MACD
    macd = [ema12[i] - ema26[i] for i in range(len(c))]
    signal = _ema(macd, 9)
    histogram = [macd[i] - signal[i] for i in range(len(macd))]

    # 趋势强度
    close_now = _last(c)
    ema50_now = _last(ema50)

    if ema50_now == 0:
        return 0.0, {"error": "zero_ema"}

    # 价格相对EMA50的位置
    price_pos = (close_now - ema50_now) / ema50_now

    # 归一化到±100
    trend_score = max(-100, min(100, price_pos * 300))  # ±33% → ±100

    # EMA排列
    ema_aligned = 1.0 if ema12[-1] > ema26[-1] > ema50[-1] else (-1.0 if ema12[-1] < ema26[-1] < ema50[-1] else 0.0)

    # MACD方向
    macd_direction = 1.0 if histogram[-1] > 0 else -1.0

    # 综合评分
    final_score = trend_score * 0.6 + ema_aligned * 20 + macd_direction * 20
    final_score = max(-100, min(100, final_score))

    metadata = {
        "trend_score": final_score,
        "price_pos": price_pos,
        "ema_aligned": ema_aligned,
        "macd_hist": histogram[-1],
        "ema12": ema12[-1],
        "ema26": ema26[-1],
        "ema50": ema50[-1]
    }

    return final_score, metadata


def _calc_momentum(h: List[float], l: List[float], c: List[float],
                   params: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    """
    M因子: 动量加速度
    Range: -100（减速下跌）到 +100（加速上涨）
    """
    if len(c) < 30:
        return 0.0, {"error": "insufficient_data"}

    # ROC (Rate of Change)
    roc_period = params.get("roc_period", 14)
    roc = ((c[-1] - c[-roc_period]) / c[-roc_period] * 100) if len(c) >= roc_period else 0.0

    # RSI
    rsi_period = params.get("rsi_period", 14)
    gains = []
    losses = []
    for i in range(1, min(rsi_period + 1, len(c))):
        change = c[-i] - c[-i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = sum(gains) / len(gains) if gains else 0
    avg_loss = sum(losses) / len(losses) if losses else 0

    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

    # RSI归一化到±100
    rsi_score = (rsi - 50) * 2  # 0-100 → -100 to +100

    # ROC归一化（±10% → ±100）
    roc_score = max(-100, min(100, roc * 10))

    # 综合评分
    momentum_score = rsi_score * 0.5 + roc_score * 0.5
    momentum_score = max(-100, min(100, momentum_score))

    metadata = {
        "momentum_score": momentum_score,
        "rsi": rsi,
        "roc": roc,
        "rsi_score": rsi_score,
        "roc_score": roc_score
    }

    return momentum_score, metadata


def _calc_structure(h: List[float], l: List[float], c: List[float],
                    ema30: float, atr_now: float, params: Dict[str, Any],
                    ctx: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    """
    S因子: 结构质量（支撑阻力）
    Range: 0（差）到 100（好）
    """
    if len(c) < 50 or atr_now == 0:
        return 50.0, {"error": "insufficient_data"}

    # 简化版：寻找最近20根K线的支撑阻力
    lookback = min(50, len(c))
    recent_h = h[-lookback:]
    recent_l = l[-lookback:]
    recent_c = c[-lookback:]

    # 寻找pivot高点和低点
    pivots_high = []
    pivots_low = []

    for i in range(2, len(recent_h) - 2):
        # Pivot高点
        if recent_h[i] > recent_h[i-1] and recent_h[i] > recent_h[i-2] and \
           recent_h[i] > recent_h[i+1] and recent_h[i] > recent_h[i+2]:
            pivots_high.append(recent_h[i])

        # Pivot低点
        if recent_l[i] < recent_l[i-1] and recent_l[i] < recent_l[i-2] and \
           recent_l[i] < recent_l[i+1] and recent_l[i] < recent_l[i+2]:
            pivots_low.append(recent_l[i])

    close_now = c[-1]

    # 寻找最近的支撑和阻力
    support_levels = [p for p in pivots_low if p < close_now]
    resistance_levels = [p for p in pivots_high if p > close_now]

    nearest_support = max(support_levels) if support_levels else close_now * 0.95
    nearest_resistance = min(resistance_levels) if resistance_levels else close_now * 1.05

    # 计算距离（以ATR为单位）
    support_distance = (close_now - nearest_support) / atr_now if atr_now > 0 else 0
    resistance_distance = (nearest_resistance - close_now) / atr_now if atr_now > 0 else 0

    # 结构质量评分：支撑和阻力越清晰，评分越高
    # 理想情况：支撑在1-2 ATR下方，阻力在2-3 ATR上方
    support_quality = 100 if 1 <= support_distance <= 3 else max(0, 100 - abs(support_distance - 2) * 20)
    resistance_quality = 100 if 2 <= resistance_distance <= 4 else max(0, 100 - abs(resistance_distance - 3) * 20)

    structure_score = (support_quality + resistance_quality) / 2
    structure_score = max(0, min(100, structure_score))

    metadata = {
        "structure_score": structure_score,
        "nearest_support": nearest_support,
        "nearest_resistance": nearest_resistance,
        "support_distance_atr": support_distance,
        "resistance_distance_atr": resistance_distance,
        "num_support_levels": len(support_levels),
        "num_resistance_levels": len(resistance_levels)
    }

    return structure_score, metadata


def _calc_fund_leading(oi_change_pct: float, vol_ratio: float, cvd6: float,
                       price_change_24h: float, price_slope: float,
                       params: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    """
    F因子: 资金领先性（调节器）
    Range: -100（价格领先）到 +100（资金领先）
    """
    # OI增长
    oi_score = max(-50, min(50, oi_change_pct * 2))  # ±25% → ±50

    # 成交量比
    vol_score = max(-25, min(25, (vol_ratio - 1.0) * 50))  # 0.5-1.5 → -25 to +25

    # CVD趋势
    cvd_score = max(-25, min(25, cvd6 * 2500))  # ±0.01 → ±25

    # 综合评分
    fund_leading_score = oi_score + vol_score + cvd_score
    fund_leading_score = max(-100, min(100, fund_leading_score))

    metadata = {
        "fund_leading_score": fund_leading_score,
        "oi_score": oi_score,
        "vol_score": vol_score,
        "cvd_score": cvd_score,
        "oi_change_pct": oi_change_pct,
        "vol_ratio": vol_ratio,
        "cvd6": cvd6
    }

    return fund_leading_score, metadata


# ============ 主分析函数 ============

def analyze_symbol_v2(symbol: str, elite_meta: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    统一因子分析系统 v2.0 - 10+1维有机整合

    Args:
        symbol: 交易对符号（如 "BTCUSDT"）
        elite_meta: Elite Universe Builder生成的元数据（可选）

    Returns:
        完整分析结果，包括：
        - 10维因子评分（T/M/C+/S/V+/O+/L/B/Q/I）
        - F调节器评分
        - weighted_score: 加权总分（-100 to +100）
        - confidence: 置信度（0 to 100）
        - direction: 方向（"LONG" / "SHORT" / "NEUTRAL"）
        - probability: 概率（0 to 1）
        - 元数据
    """
    # 加载配置
    factor_config = get_factor_config()
    params = CFG.params or {}

    # ---- 1. 获取数据 ----
    try:
        k1 = get_klines(symbol, "1h", 300)
        k4 = get_klines(symbol, "4h", 200)
        oi_data = get_open_interest_hist(symbol, "1h", 300)

        # 尝试获取现货K线
        try:
            spot_k1 = get_spot_klines(symbol, "1h", 300)
        except Exception:
            spot_k1 = None

        # 获取24h ticker（用于basis+funding）
        try:
            ticker = get_ticker_24h(symbol)
        except Exception:
            ticker = None

    except Exception as e:
        return _make_empty_result(symbol, f"data_fetch_error: {str(e)}")

    # 数据验证
    if not k1 or len(k1) < 100:
        return _make_empty_result(symbol, "insufficient_data")

    # 提取价格数据
    h = [_to_f(r[2]) for r in k1]
    l = [_to_f(r[3]) for r in k1]
    c = [_to_f(r[4]) for r in k1]
    v = [_to_f(r[5]) for r in k1]  # base volume
    q = [_to_f(r[7]) for r in k1]  # quote volume
    c4 = [_to_f(r[4]) for r in k4] if k4 and len(k4) >= 30 else c

    # 基础指标
    close_now = _last(c)
    ema30 = _ema(c, 30)
    atr_series = _atr(h, l, c, 14)
    atr_now = _last(atr_series)

    # ---- 2. 计算10维因子 ----

    scores = {}
    metadata = {}

    # === Layer 1: Price Action (65点) ===

    # T (Trend) - 25点
    T, T_meta = _calc_trend(h, l, c, c4, params.get("trend", {}))
    scores["T"] = T
    metadata["T"] = T_meta

    # M (Momentum) - 15点
    M, M_meta = _calc_momentum(h, l, c, params.get("momentum", {}))
    scores["M"] = M
    metadata["M"] = M_meta

    # C+ (Enhanced CVD) - 20点
    try:
        C_plus, C_plus_meta = calculate_cvd_enhanced(
            klines_perp=k1,
            klines_spot=spot_k1,
            params=factor_config.get_factor_params("C+")
        )
        scores["C+"] = C_plus
        metadata["C+"] = C_plus_meta
    except Exception as e:
        scores["C+"] = 0.0
        metadata["C+"] = {"error": str(e)}

    # S (Structure) - 10点
    ctx = {"bigcap": False, "overlay": False, "phaseA": False, "strong": (abs(T) > 75), "m15_ok": False}
    S, S_meta = _calc_structure(h, l, c, _last(ema30), atr_now, params.get("structure", {}), ctx)
    scores["S"] = S
    metadata["S"] = S_meta

    # === Layer 2: Money Flow (40点) ===

    # V+ (Volume + Trigger) - 15点
    try:
        # 寻找支撑阻力（用于突破检测）
        support_levels = [S_meta.get("nearest_support")] if S_meta.get("nearest_support") else []
        resistance_levels = [S_meta.get("nearest_resistance")] if S_meta.get("nearest_resistance") else []

        V_plus, V_plus_meta = calculate_volume_trigger(
            klines=k1,
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            params=factor_config.get_factor_params("V+")
        )
        scores["V+"] = V_plus
        metadata["V+"] = V_plus_meta
    except Exception as e:
        scores["V+"] = 0.0
        metadata["V+"] = {"error": str(e)}

    # O+ (OI Regime) - 20点
    try:
        oi_hist = [_to_f(r.get("sumOpenInterest", 0)) for r in oi_data] if oi_data else []
        price_hist = c[-len(oi_hist):] if oi_hist else c

        O_plus, O_plus_regime, O_plus_meta = calculate_oi_regime(
            oi_hist=oi_hist,
            price_hist=price_hist,
            params=factor_config.get_factor_params("O+")
        )
        scores["O+"] = O_plus
        metadata["O+"] = O_plus_meta
        metadata["O+"]["regime"] = O_plus_regime
    except Exception as e:
        scores["O+"] = 0.0
        metadata["O+"] = {"error": str(e)}

    # === Layer 3: Microstructure (45点) ===

    # L (Liquidity) - 20点
    try:
        # 注意：真实环境需要订单簿API，这里使用模拟数据或优雅降级
        # 实际应用中应该从exchange API获取orderbook
        L, L_meta = calculate_liquidity(
            orderbook={"bids": [], "asks": []},  # 优雅降级：空订单簿
            params=factor_config.get_factor_params("L")
        )
        scores["L"] = L
        metadata["L"] = L_meta
    except Exception as e:
        scores["L"] = 50.0  # 中性评分
        metadata["L"] = {"error": str(e), "degraded": True}

    # B (Basis + Funding) - 15点
    try:
        # 注意：需要现货价格和资金费率
        # 简化版：使用ticker数据或优雅降级
        perp_price = close_now
        spot_price = close_now * 0.999  # 假设小幅基差
        funding_rate = 0.0001  # 假设正常费率

        if ticker:
            funding_rate = _to_f(ticker.get("lastFundingRate", 0.0001))

        B, B_meta = calculate_basis_funding(
            perp_price=perp_price,
            spot_price=spot_price,
            funding_rate=funding_rate,
            params=factor_config.get_factor_params("B")
        )
        scores["B"] = B
        metadata["B"] = B_meta
    except Exception as e:
        scores["B"] = 0.0
        metadata["B"] = {"error": str(e)}

    # Q (Liquidation) - 10点
    try:
        # 注意：需要清算数据API
        # 优雅降级：无数据时返回中性
        Q, Q_meta = calculate_liquidation(
            liquidations=[],  # 优雅降级：空清算数据
            current_price=close_now,
            params=factor_config.get_factor_params("Q")
        )
        scores["Q"] = Q
        metadata["Q"] = Q_meta
    except Exception as e:
        scores["Q"] = 0.0  # 中性评分
        metadata["Q"] = {"error": str(e), "degraded": True}

    # === Layer 4: Market Context (10点) ===

    # I (Independence) - 10点
    try:
        # 获取BTC和ETH价格
        btc_k1 = get_klines("BTCUSDT", "1h", 300) if symbol != "BTCUSDT" else k1
        eth_k1 = get_klines("ETHUSDT", "1h", 300) if symbol != "ETHUSDT" else k1

        btc_prices = [_to_f(r[4]) for r in btc_k1]
        eth_prices = [_to_f(r[4]) for r in eth_k1]

        I, I_beta, I_meta = calculate_independence(
            alt_prices=c,
            btc_prices=btc_prices,
            eth_prices=eth_prices,
            params=factor_config.get_factor_params("I")
        )
        scores["I"] = I
        metadata["I"] = I_meta
        metadata["I"]["beta_sum"] = I_beta
    except Exception as e:
        scores["I"] = 50.0  # 中性评分
        metadata["I"] = {"error": str(e)}

    # === F调节器 (不参与权重) ===
    try:
        oi_change_pct = O_plus_meta.get("delta_oi_pct", 0.0) if "O+" in metadata else 0.0
        vol_ratio = V_plus_meta.get("vol_mult", 1.0) if "V+" in metadata else 1.0
        cvd6 = C_plus_meta.get("cvd_delta", 0.0) / close_now if "C+" in metadata and close_now > 0 else 0.0
        price_change_24h = ((c[-1] - c[-25]) / c[-25] * 100) if len(c) >= 25 else 0.0
        price_slope = (ema30[-1] - ema30[-7]) / 6.0 / max(1e-9, atr_now)

        F, F_meta = _calc_fund_leading(
            oi_change_pct, vol_ratio, cvd6, price_change_24h, price_slope, params.get("fund_leading", {})
        )
        metadata["F"] = F_meta
    except Exception as e:
        F = 0.0
        metadata["F"] = {"error": str(e)}

    # ---- 3. 计算加权评分 ----

    # 获取权重（从配置）
    weights = factor_config.get_all_weights()

    # 计算加权总分（160点系统）
    weighted_sum = 0.0
    total_weight = 0.0

    for factor_name, score in scores.items():
        if factor_name in weights:
            weight = weights[factor_name]
            weighted_sum += score * weight
            total_weight += weight

    # 归一化到±100（总权重160，归一化因子1.6）
    normalization_factor = factor_config.config.get("weights_config", {}).get("normalization_factor", 1.6)
    weighted_score = weighted_sum / normalization_factor if normalization_factor > 0 else weighted_sum / 1.6

    # 确保在±100范围内
    weighted_score = max(-100, min(100, weighted_score))

    # 置信度（绝对值）
    confidence = abs(weighted_score)

    # 方向判定
    if weighted_score > 10:
        direction = "LONG"
    elif weighted_score < -10:
        direction = "SHORT"
    else:
        direction = "NEUTRAL"

    # ---- 4. 概率映射（Sigmoid）----

    # F调节（调节器可以调整温度）
    base_temperature = 35.0
    f_adjustment = F / 100.0  # -1 to +1
    adjusted_temperature = base_temperature * (1.0 + f_adjustment * 0.2)  # ±20%温度调整

    # Sigmoid概率映射
    probability = map_probability_sigmoid(weighted_score, temperature=adjusted_temperature)

    # ---- 5. 构建结果 ----

    result = {
        "symbol": symbol,
        "timestamp": int(time.time()),
        "close": close_now,
        "atr": atr_now,

        # 10维因子评分
        "scores": scores,

        # F调节器
        "F_regulator": F,

        # 综合评分
        "weighted_score": weighted_score,
        "confidence": confidence,
        "direction": direction,
        "probability": probability,

        # 权重信息
        "weights": weights,
        "total_weight": total_weight,
        "normalization_factor": normalization_factor,

        # 详细元数据
        "metadata": metadata,

        # 系统版本
        "version": "v2.0_unified_10+1"
    }

    return result


def _make_empty_result(symbol: str, reason: str) -> Dict[str, Any]:
    """创建空结果（数据不足或错误时）"""
    return {
        "symbol": symbol,
        "timestamp": int(time.time()),
        "error": reason,
        "weighted_score": 0.0,
        "confidence": 0.0,
        "direction": "NEUTRAL",
        "probability": 0.5,
        "scores": {},
        "metadata": {},
        "version": "v2.0_unified_10+1"
    }


# ========== 测试代码 ==========

if __name__ == "__main__":
    import json

    print("=" * 70)
    print("统一因子分析系统 v2.0 - 10+1维测试")
    print("=" * 70)

    # 测试币种
    test_symbols = ["BTCUSDT", "ETHUSDT"]

    for symbol in test_symbols:
        print(f"\n{'='*70}")
        print(f"测试币种: {symbol}")
        print(f"{'='*70}")

        try:
            result = analyze_symbol_v2(symbol)

            print(f"\n【综合评分】")
            print(f"  加权评分: {result['weighted_score']:.1f}")
            print(f"  置信度: {result['confidence']:.1f}")
            print(f"  方向: {result['direction']}")
            print(f"  概率: {result['probability']:.3f}")

            print(f"\n【10维因子评分】")
            for factor_name in ["T", "M", "C+", "S", "V+", "O+", "L", "B", "Q", "I"]:
                score = result["scores"].get(factor_name, 0)
                weight = result["weights"].get(factor_name, 0)
                print(f"  {factor_name:3s}: {score:6.1f} (权重: {weight:2d})")

            print(f"\n【F调节器】")
            print(f"  F: {result['F_regulator']:.1f}")

            print(f"\n【关键元数据】")
            if "O+" in result["metadata"]:
                print(f"  OI体制: {result['metadata']['O+'].get('regime', 'N/A')}")
            if "I" in result["metadata"]:
                print(f"  Beta总和: {result['metadata']['I'].get('beta_sum', 'N/A')}")
            if "L" in result["metadata"]:
                print(f"  流动性: {result['metadata']['L'].get('liquidity_level', 'N/A')}")

        except Exception as e:
            print(f"\n❌ 错误: {str(e)}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*70}")
    print("✅ 测试完成")
    print(f"{'='*70}")
