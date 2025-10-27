# coding: utf-8
from __future__ import annotations

"""
世界顶级候选池构建器（Elite Universe Builder）

核心哲学：
1. 方向中性：多空对称，不预判方向
2. 信息熵最大化：捕捉所有有效异常
3. 微观结构优先：订单流 > 价格
4. 因子独立性：避免冗余信号
5. 动态阈值：市场状态自适应

参考：Renaissance Technologies / Two Sigma / Citadel 思路
"""

import os
import json
import math
from typing import List, Dict, Any, Tuple
from statistics import median, stdev
from ats_core.cfg import CFG
from ats_core.sources.tickers import all_24h
from ats_core.sources.binance import get_klines, get_open_interest_hist
from ats_core.features.cvd import cvd_mix_with_oi_price
from ats_core.logging import log

DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data")
os.makedirs(DATA, exist_ok=True)

# ============ 工具函数 ============

def _to_f(x) -> float:
    try:
        return float(x)
    except:
        return 0.0

def _ema(seq: List[float], n: int) -> List[float]:
    if not seq or n <= 1:
        return [_to_f(v) for v in seq]
    k = 2.0 / (n + 1.0)
    e = None
    out = []
    for v in seq:
        v = _to_f(v)
        e = v if e is None else (e + k * (v - e))
        out.append(e)
    return out

def _robust_zscore(values: List[float]) -> float:
    """鲁棒Z分数（用MAD代替标准差，抗异常值）"""
    if len(values) < 3:
        return 0.0
    med = median(values)
    mad = median([abs(v - med) for v in values])
    if mad < 1e-12:
        return 0.0
    return (values[-1] - med) / (1.4826 * mad)

def _percentile_rank(value: float, values: List[float]) -> float:
    """百分位排名（0-100）"""
    if len(values) == 0:
        return 50.0
    sorted_vals = sorted(values)
    rank = sum(1 for v in sorted_vals if v < value)
    return 100.0 * rank / len(sorted_vals)

# ============ Layer 0: 宇宙过滤 ============

def _layer0_universe_filter(tickers: List[Dict]) -> List[Dict]:
    """
    Layer 0: 基础宇宙过滤
    目标：排除不可交易的垃圾币

    过滤条件：
    - USDT永续合约
    - 非黑名单
    """
    log("🌍 [Layer 0] 宇宙过滤...")
    blacklist = getattr(CFG, 'blacklist', []) or []

    universe = []
    for t in tickers:
        try:
            sym = t["symbol"]
            if not sym.endswith("USDT"):
                continue
            if sym in blacklist:
                continue
            universe.append(t)
        except:
            continue

    log(f"   ✅ {len(tickers)} → {len(universe)} 个USDT交易对")
    return universe

# ============ Layer 1: 流动性筛选 ============

def _layer1_liquidity_screen(universe: List[Dict], params: Dict) -> List[Dict]:
    """
    Layer 1: 流动性筛选
    目标：确保可执行性（滑点可控、深度充足）

    核心指标：
    1. 成交额（24h Quote Volume）
    2. 成交笔数（24h Trades Count）
    3. 点差估计（Price Change Velocity）

    顶级思维：流动性不是越高越好，而是"足够执行 + 有波动"
    """
    log("💧 [Layer 1] 流动性筛选...")

    min_quote = params.get("min_quote_volume", 5_000_000)  # 500万USDT
    min_trades = params.get("min_trades_24h", 10_000)      # 1万笔

    liquid = []
    for t in universe:
        try:
            quote_vol = _to_f(t.get("quoteVolume", 0))
            trades = _to_f(t.get("count", 0))

            # 流动性评分（0-100）
            vol_score = min(100, quote_vol / 50_000_000 * 100)  # 5000万=100分
            trade_score = min(100, trades / 100_000 * 100)      # 10万笔=100分
            liquidity_score = 0.7 * vol_score + 0.3 * trade_score

            if quote_vol >= min_quote and trades >= min_trades:
                t["_liquidity_score"] = liquidity_score
                liquid.append(t)
        except:
            continue

    log(f"   ✅ {len(universe)} → {len(liquid)} 个（流动性合格）")
    return liquid

# ============ Layer 2: 异常事件检测 ============

def _layer2_anomaly_detection(candidates: List[Dict], params: Dict) -> List[Dict]:
    """
    Layer 2: 异常事件检测（方向中性）
    目标：捕捉市场微观结构异常（不管涨跌）

    检测6个独立维度的异常：
    1. 价格异常（Price Anomaly）- z分数
    2. 量能异常（Volume Surge）- 相对放大
    3. 持仓异常（OI Jump）- 杠杆涌入
    4. 价-量背离（Price-Volume Divergence）
    5. 波动率突变（Volatility Spike）
    6. 资金流异常（Fund Flow Imbalance）

    顶级思维：异常 = 信息，方向由后续分析判断
    """
    log("🔍 [Layer 2] 异常事件检测（6维独立检测）...")

    anomalies = []
    processed = 0

    for idx, t in enumerate(candidates, 1):
        try:
            sym = t["symbol"]

            # 显示进度
            if idx % 10 == 0 or idx == 1 or idx == len(candidates):
                log(f"   [{idx}/{len(candidates)}] {sym}...")

            # 获取数据（轻量级，只要60根1h K线）
            k1 = get_klines(sym, "1h", 60)
            if not k1 or len(k1) < 30:
                continue

            oi = get_open_interest_hist(sym, "1h", 60)

            # 提取价格/量能数据
            closes = [_to_f(r[4]) for r in k1]
            volumes = [_to_f(r[7]) for r in k1]  # quote volume
            oi_values = [_to_f(r[5]) for r in oi] if oi and len(oi) >= 30 else [0] * len(k1)

            # === 1. 价格异常检测 ===
            # 计算24h收益率序列（用14天数据）
            returns_24h = []
            for i in range(24, min(len(closes), 14 * 24)):
                if closes[i - 24] > 0:
                    returns_24h.append(math.log(closes[i] / closes[i - 24]))

            price_z = _robust_zscore(returns_24h) if len(returns_24h) >= 20 else 0.0
            price_anomaly = abs(price_z)  # 异常强度（不看方向）

            # === 2. 量能异常检测 ===
            v5 = sum(volumes[-5:]) / 5 if len(volumes) >= 5 else 0
            v20 = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else 1
            volume_surge = (v5 / v20) if v20 > 0 else 1.0

            # === 3. 持仓异常检测 ===
            if len(oi_values) >= 24 and oi_values[-24] > 0:
                oi_change_24h = (oi_values[-1] - oi_values[-24]) / oi_values[-24]
                oi_anomaly = abs(oi_change_24h) * 100  # 转为百分比
            else:
                oi_anomaly = 0.0

            # === 4. 价-量背离检测 ===
            # 价格变化方向 vs 量能方向
            price_dir = 1 if closes[-1] > closes[-6] else -1
            vol_dir = 1 if v5 > v20 else -1
            pv_divergence = 1.0 if price_dir != vol_dir else 0.0  # 背离=1，一致=0

            # === 5. 波动率突变检测 ===
            # 最近5根vs前20根的波动率比值
            recent_vol = stdev(closes[-5:]) if len(closes) >= 5 else 0
            normal_vol = stdev(closes[-25:-5]) if len(closes) >= 25 else 1e-9
            volatility_spike = (recent_vol / normal_vol) if normal_vol > 1e-9 else 1.0

            # === 6. 资金流异常检测（简化版CVD）===
            # 用买卖成交量差异估算
            try:
                taker_buy_quote = [_to_f(r[10]) for r in k1]  # takerBuyQuoteVolume
                taker_sell_quote = [volumes[i] - taker_buy_quote[i] for i in range(len(volumes))]

                # 最近6h的资金净流入
                flow_6h = sum(taker_buy_quote[-6:]) - sum(taker_sell_quote[-6:])
                total_6h = sum(volumes[-6:])
                flow_imbalance = abs(flow_6h / total_6h) if total_6h > 0 else 0.0
            except:
                flow_imbalance = 0.0

            # === 综合异常评分（6维加权）===
            # 每个维度独立归一化到0-100
            scores = {
                "price_anomaly": min(100, price_anomaly * 20),        # Z>5 = 100分
                "volume_surge": min(100, (volume_surge - 1) * 50),    # v5/v20=3 = 100分
                "oi_anomaly": min(100, oi_anomaly * 5),                # 20%OI变化 = 100分
                "pv_divergence": pv_divergence * 30,                   # 背离 = 30分
                "volatility_spike": min(100, (volatility_spike - 1) * 30),  # 波动率3倍 = 60分
                "flow_imbalance": min(100, flow_imbalance * 200),      # 50%失衡 = 100分
            }

            # 取最强的3个异常维度（避免噪音）
            top3_scores = sorted(scores.values(), reverse=True)[:3]
            anomaly_score = sum(top3_scores) / 3  # 平均分

            # 阈值：异常分数 >= 40（至少有一个维度显著异常）
            min_anomaly_score = params.get("min_anomaly_score", 40)

            if anomaly_score >= min_anomaly_score:
                t["_anomaly_score"] = anomaly_score
                t["_anomaly_details"] = scores
                t["_price_z"] = price_z  # 保留方向信息（后续用）
                anomalies.append(t)

                # 显示检测到的异常
                top_dim = max(scores, key=scores.get)
                if idx % 10 != 0 and idx != 1:
                    log(f"   [{idx}/{len(candidates)}] {sym} ⚡ 异常 (分数={anomaly_score:.0f}, 主因={top_dim})")

            processed += 1

        except Exception as e:
            continue

    log(f"   ✅ {len(candidates)} → {len(anomalies)} 个（检测到异常）")
    return anomalies

# ============ Layer 3: 多因子评分 ============

def _layer3_multifactor_scoring(anomalies: List[Dict], params: Dict) -> List[Dict]:
    """
    Layer 3: 多因子质量评分（方向感知）
    目标：在异常币中，评估做多/做空的质量

    评分维度（与analyze_symbol对齐）：
    1. 趋势强度（Trend Strength）- 不看方向，只看强度
    2. 动量质量（Momentum Quality）
    3. 流动性状态（Liquidity State）
    4. 微观结构（Microstructure）

    输出：每个币的long_score和short_score（0-100）
    """
    log("📊 [Layer 3] 多因子质量评分...")

    scored = []

    for idx, t in enumerate(anomalies, 1):
        try:
            sym = t["symbol"]

            # 获取数据（已在Layer 2获取过，这里重新获取是为了计算更多指标）
            k1 = get_klines(sym, "1h", 60)
            if not k1 or len(k1) < 30:
                continue

            oi = get_open_interest_hist(sym, "1h", 60)

            closes = [_to_f(r[4]) for r in k1]
            volumes = [_to_f(r[7]) for r in k1]

            # === 1. 趋势强度评分 ===
            ema5 = _ema(closes, 5)
            ema20 = _ema(closes, 20)

            # 趋势方向（+1=多头，-1=空头）
            trend_dir = 1 if ema5[-1] > ema20[-1] else -1

            # 趋势强度（EMA排列一致性，0-100）
            ema_consistency = sum(1 for i in range(-6, 0) if (ema5[i] > ema20[i]) == (trend_dir > 0))
            trend_strength = ema_consistency / 6 * 100

            # === 2. 动量质量评分 ===
            # 斜率方向一致性
            slope_6h = (closes[-1] - closes[-7]) / 6 if len(closes) >= 7 else 0
            slope_dir = 1 if slope_6h > 0 else -1

            # 动量方向与趋势一致性
            momentum_quality = 100 if slope_dir == trend_dir else 30

            # === 3. 流动性状态评分 ===
            # 量能支持（v5/v20，1.0-3.0 = 0-100分）
            v5 = sum(volumes[-5:]) / 5
            v20 = sum(volumes[-20:]) / 20
            volume_support = min(100, (v5 / v20 - 1.0) * 50) if v20 > 0 else 0

            # === 4. 微观结构评分 ===
            # OI变化方向（与价格一致=好）
            if oi and len(oi) >= 7:
                oi_values = [_to_f(r[5]) for r in oi]
                oi_change_6h = (oi_values[-1] - oi_values[-7]) / oi_values[-7] if oi_values[-7] > 0 else 0
                oi_dir = 1 if oi_change_6h > 0 else -1

                # 微观结构得分（价格、OI同向=100，反向=0）
                microstructure_score = 100 if oi_dir == trend_dir else 20
            else:
                microstructure_score = 50  # 中性

            # === 综合评分 ===
            # 基础质量分（0-100）
            base_quality = (
                0.35 * trend_strength +
                0.25 * momentum_quality +
                0.20 * volume_support +
                0.20 * microstructure_score
            )

            # 做多/做空分数（根据趋势方向分配）
            if trend_dir > 0:
                long_score = base_quality
                short_score = max(0, 100 - base_quality)  # 反向分数
            else:
                short_score = base_quality
                long_score = max(0, 100 - base_quality)

            # 阈值：至少有一个方向分数 >= 60
            min_quality = params.get("min_quality_score", 60)

            if long_score >= min_quality or short_score >= min_quality:
                t["_long_score"] = long_score
                t["_short_score"] = short_score
                t["_trend_dir"] = "LONG" if trend_dir > 0 else "SHORT"
                scored.append(t)
        except:
            continue

    log(f"   ✅ {len(anomalies)} → {len(scored)} 个（质量合格）")
    return scored

# ============ Layer 4: 风险过滤 ============

def _layer4_risk_filter(scored: List[Dict], params: Dict) -> List[Dict]:
    """
    Layer 4: 风险过滤（排除陷阱）
    目标：排除高风险币（操纵、流动性枯竭、极端波动）

    风险检测：
    1. 极端波动（可能是操纵）
    2. 流动性枯竭（无法平仓）
    3. 价格距离极值过近（追高/追跌）
    """
    log("🛡️  [Layer 4] 风险过滤...")

    filtered = []

    for t in scored:
        try:
            sym = t["symbol"]

            # 获取数据
            k1 = get_klines(sym, "1h", 72)  # 72小时（3天）
            if not k1 or len(k1) < 72:
                filtered.append(t)  # 数据不足，保守通过
                continue

            highs = [_to_f(r[2]) for r in k1]
            lows = [_to_f(r[3]) for r in k1]
            closes = [_to_f(r[4]) for r in k1]
            volumes = [_to_f(r[7]) for r in k1]

            current_price = closes[-1]

            # === 风险1：极端波动检测 ===
            # 单根K线涨跌幅超过20%（可能是操纵或流动性差）
            max_1h_change = max(abs(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes)))
            if max_1h_change > 0.20:  # 20%
                log(f"   ⚠️  {sym} 过滤（极端波动：{max_1h_change:.1%}）")
                continue

            # === 风险2：流动性枯竭检测 ===
            # 最近6h成交量骤降（低于前66h平均的30%）
            vol_6h = sum(volumes[-6:])
            vol_66h_avg = sum(volumes[-72:-6]) / 66
            if vol_6h < vol_66h_avg * 6 * 0.30:  # 低于30%
                log(f"   ⚠️  {sym} 过滤（流动性枯竭）")
                continue

            # === 风险3：追高/追跌检测 ===
            # 距离72h高点/低点过近（<3%）
            hh_72 = max(highs)
            ll_72 = min(lows)

            dist_to_high = (hh_72 - current_price) / hh_72
            dist_to_low = (current_price - ll_72) / ll_72

            max_distance = params.get("anti_chase_distance", 0.03)  # 3%

            if dist_to_high < max_distance:
                log(f"   ⚠️  {sym} 过滤（距高点过近：{dist_to_high:.1%}）")
                continue

            if dist_to_low < max_distance:
                log(f"   ⚠️  {sym} 过滤（距低点过近：{dist_to_low:.1%}）")
                continue

            # 通过所有风险检测
            filtered.append(t)

        except:
            # 检测失败，保守通过
            filtered.append(t)
            continue

    log(f"   ✅ {len(scored)} → {len(filtered)} 个（风险检查通过）")
    return filtered

# ============ 主函数 ============

def build_elite_universe() -> Tuple[List[str], Dict[str, Any]]:
    """
    世界顶级候选池构建

    返回：
    - symbols: 最终候选池交易对列表
    - metadata: 每个交易对的元数据（分数、方向等）
    """
    log("=" * 60)
    log("🏆 Elite Universe Builder - 世界顶级候选池构建")
    log("=" * 60)

    params = CFG.get("elite_universe", {})

    # Layer 0: 宇宙过滤
    tickers = all_24h()
    universe = _layer0_universe_filter(tickers)

    # Layer 1: 流动性筛选
    liquid = _layer1_liquidity_screen(universe, params)

    # Layer 2: 异常事件检测
    anomalies = _layer2_anomaly_detection(liquid, params)

    # Layer 3: 多因子评分
    scored = _layer3_multifactor_scoring(anomalies, params)

    # Layer 4: 风险过滤
    final = _layer4_risk_filter(scored, params)

    # 按综合分数排序（取long_score和short_score的最大值）
    final_sorted = sorted(final, key=lambda x: max(x.get("_long_score", 0), x.get("_short_score", 0)), reverse=True)

    # 提取元数据
    metadata = {}
    symbols = []
    for t in final_sorted:
        sym = t["symbol"]
        symbols.append(sym)
        metadata[sym] = {
            "long_score": t.get("_long_score", 0),
            "short_score": t.get("_short_score", 0),
            "trend_dir": t.get("_trend_dir", "NEUTRAL"),
            "anomaly_score": t.get("_anomaly_score", 0),
            "anomaly_details": t.get("_anomaly_details", {}),
            "liquidity_score": t.get("_liquidity_score", 0),
        }

    # 保存结果
    with open(os.path.join(DATA, "elite_universe.json"), "w", encoding="utf-8") as f:
        json.dump({"symbols": symbols, "metadata": metadata}, f, ensure_ascii=False, indent=2)

    log("=" * 60)
    log(f"🎯 最终候选池：{len(symbols)} 个交易对")
    if len(symbols) > 0:
        log(f"   前10名: {', '.join(symbols[:10])}")

        # 统计多空分布
        longs = sum(1 for s in symbols if metadata[s]["trend_dir"] == "LONG")
        shorts = sum(1 for s in symbols if metadata[s]["trend_dir"] == "SHORT")
        log(f"   做多机会: {longs} 个 ({longs/len(symbols)*100:.0f}%)")
        log(f"   做空机会: {shorts} 个 ({shorts/len(symbols)*100:.0f}%)")
    log("=" * 60)

    return symbols, metadata
