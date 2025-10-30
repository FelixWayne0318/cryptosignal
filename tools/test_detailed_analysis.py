#!/usr/bin/env python3
# coding: utf-8
"""
详细调试版本 - 测试5个指定币种的完整分析流程

测试币种:
- BTCUSDT
- SOLUSDT
- BNBUSDT
- COAIUSDT
- XPLUSDT

输出内容:
1. 数据获取详情（每个API调用的结果）
2. 每个因子的详细参数和中间计算结果
3. 10维因子的评分过程
4. 最终概率映射和信号判定

使用方法:
    python3 tools/test_detailed_analysis.py
"""

import sys
import os
import asyncio
import time
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ats_core.cfg import CFG
from ats_core.sources.binance import (
    get_klines,
    get_open_interest_hist,
    get_spot_klines,
    get_ticker_24h
)
from ats_core.logging import log, warn, error


def print_header(title: str):
    """打印标题"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_section(title: str):
    """打印小节标题"""
    print("\n" + "-" * 80)
    print(f"  {title}")
    print("-" * 80)


def analyze_symbol_detailed(symbol: str):
    """
    详细分析单个币种（同步版本，方便调试）

    Args:
        symbol: 交易对符号

    Returns:
        分析结果字典
    """
    print_header(f"开始分析: {symbol}")

    start_time = time.time()

    # ========== 第1步: 数据获取 ==========
    print_section("第1步: 数据获取")

    try:
        # 1.1 K线数据
        print("\n1.1 获取K线数据...")
        k1_start = time.time()
        k1 = get_klines(symbol, "1h", 300)
        print(f"   ✅ 1h K线: {len(k1)}根，耗时: {time.time()-k1_start:.2f}秒")
        if k1:
            print(f"   最新K线: 时间={k1[-1][0]}, 收盘={k1[-1][4]}, 成交量={k1[-1][5]}")

        k4_start = time.time()
        k4 = get_klines(symbol, "4h", 200)
        print(f"   ✅ 4h K线: {len(k4)}根，耗时: {time.time()-k4_start:.2f}秒")

        k15m_start = time.time()
        k15m = get_klines(symbol, "15m", 100)
        print(f"   ✅ 15m K线: {len(k15m)}根，耗时: {time.time()-k15m_start:.2f}秒")

        # 1.2 持仓量数据
        print("\n1.2 获取持仓量数据...")
        oi_start = time.time()
        oi_data = get_open_interest_hist(symbol, "1h", 100)
        print(f"   ✅ OI历史: {len(oi_data)}条，耗时: {time.time()-oi_start:.2f}秒")
        if oi_data:
            print(f"   最新OI: {oi_data[-1]}")

        # 1.3 现货K线（用于基差计算）
        print("\n1.3 获取现货数据...")
        try:
            spot_start = time.time()
            spot_k1 = get_spot_klines(symbol, "1h", 100)
            print(f"   ✅ 现货K线: {len(spot_k1) if spot_k1 else 0}根，耗时: {time.time()-spot_start:.2f}秒")
        except Exception as e:
            print(f"   ⚠️  现货数据获取失败: {e}")
            spot_k1 = None

        # 1.4 24h行情（资金费率）
        print("\n1.4 获取24h行情...")
        try:
            ticker_start = time.time()
            ticker = get_ticker_24h(symbol)
            print(f"   ✅ 24h行情获取成功，耗时: {time.time()-ticker_start:.2f}秒")
            if ticker:
                print(f"   24h成交额: {float(ticker.get('quoteVolume', 0))/1e6:.2f}M USDT")
                print(f"   24h涨跌幅: {float(ticker.get('priceChangePercent', 0)):.2f}%")
                print(f"   最新价格: {ticker.get('lastPrice')}")
        except Exception as e:
            print(f"   ⚠️  24h行情获取失败: {e}")
            ticker = None

    except Exception as e:
        error(f"❌ 数据获取失败: {e}")
        import traceback
        traceback.print_exc()
        return None

    # 验证数据完整性
    if not k1 or len(k1) < 100:
        error(f"❌ {symbol} K线数据不足: {len(k1) if k1 else 0}根")
        return None

    print(f"\n✅ 数据获取完成，总耗时: {time.time()-start_time:.2f}秒")

    # ========== 第2步: 提取基础数据 ==========
    print_section("第2步: 提取基础数据")

    # 价格数据
    h = [float(r[2]) for r in k1]
    l = [float(r[3]) for r in k1]
    c = [float(r[4]) for r in k1]
    v = [float(r[5]) for r in k1]
    q = [float(r[7]) for r in k1]

    close_now = c[-1]

    print(f"   最新收盘价: {close_now}")
    print(f"   最近5根K线收盘价: {c[-5:]}")
    print(f"   最近5根K线成交量: {v[-5:]}")

    # 计算基础指标
    print("\n   计算基础指标...")

    # EMA
    def calc_ema(data, period):
        k = 2.0 / (period + 1.0)
        ema = []
        e = None
        for val in data:
            e = val if e is None else (e + k * (val - e))
            ema.append(e)
        return ema

    ema12 = calc_ema(c, 12)
    ema26 = calc_ema(c, 26)
    ema50 = calc_ema(c, 50)

    print(f"   EMA12: {ema12[-1]:.2f}")
    print(f"   EMA26: {ema26[-1]:.2f}")
    print(f"   EMA50: {ema50[-1]:.2f}")

    # ATR
    def calc_atr(h, l, c, period=14):
        tr = []
        pc = c[0]
        for i in range(len(c)):
            hi = h[i]
            lo = l[i]
            ci = c[i]
            tr.append(max(hi - lo, abs(hi - pc), abs(lo - pc)))
            pc = ci
        return calc_ema(tr, period)

    atr_series = calc_atr(h, l, c, 14)
    atr_now = atr_series[-1]

    print(f"   ATR: {atr_now:.4f}")
    print(f"   ATR占价格比: {atr_now/close_now*100:.2f}%")

    # ========== 第3步: 计算10维因子 ==========
    print_section("第3步: 10维因子计算")

    scores = {}
    metadata = {}

    # === T因子: 趋势 ===
    print("\n【T因子 - 趋势方向与强度】")
    print("   参数: EMA(12, 26, 50), MACD(12, 26, 9)")

    # MACD
    macd = [ema12[i] - ema26[i] for i in range(len(c))]
    signal = calc_ema(macd, 9)
    histogram = [macd[i] - signal[i] for i in range(len(macd))]

    print(f"   MACD线: {macd[-1]:.4f}")
    print(f"   信号线: {signal[-1]:.4f}")
    print(f"   柱状图: {histogram[-1]:.4f}")

    # 趋势强度
    price_pos = (close_now - ema50[-1]) / ema50[-1]
    trend_score_raw = price_pos * 300

    print(f"   价格相对EMA50位置: {price_pos*100:.2f}%")
    print(f"   趋势评分(原始): {trend_score_raw:.2f}")

    # EMA排列
    ema_aligned = 1.0 if ema12[-1] > ema26[-1] > ema50[-1] else (-1.0 if ema12[-1] < ema26[-1] < ema50[-1] else 0.0)
    print(f"   EMA排列: {'多头' if ema_aligned > 0 else ('空头' if ema_aligned < 0 else '混乱')}")

    # MACD方向
    macd_direction = 1.0 if histogram[-1] > 0 else -1.0
    print(f"   MACD方向: {'多头' if macd_direction > 0 else '空头'}")

    # 综合评分
    T_score = max(-100, min(100, trend_score_raw * 0.6 + ema_aligned * 20 + macd_direction * 20))
    scores["T"] = T_score
    print(f"   ✅ T因子评分: {T_score:.1f}")

    # === M因子: 动量 ===
    print("\n【M因子 - 动量加速度】")
    print("   参数: ROC(14), RSI(14)")

    # ROC
    roc_period = 14
    roc = ((c[-1] - c[-roc_period]) / c[-roc_period] * 100) if len(c) >= roc_period else 0.0
    print(f"   ROC(14): {roc:.2f}%")

    # RSI
    rsi_period = 14
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

    print(f"   RSI(14): {rsi:.2f}")

    # 归一化
    rsi_score = (rsi - 50) * 2
    roc_score = max(-100, min(100, roc * 10))

    M_score = max(-100, min(100, rsi_score * 0.5 + roc_score * 0.5))
    scores["M"] = M_score
    print(f"   ✅ M因子评分: {M_score:.1f}")

    # === C+因子: CVD增强 ===
    print("\n【C+因子 - 增强资金流】")
    print("   参数: takerBuyVolume, CVD累积差异")

    # 简化版CVD（使用takerBuyBaseAssetVolume）
    cvd = 0
    buy_volume_sum = 0
    sell_volume_sum = 0

    for i in range(max(0, len(k1) - 24), len(k1)):  # 最近24小时
        vol = float(k1[i][5])
        taker_buy_vol = float(k1[i][9])  # takerBuyBaseAssetVolume

        buy_volume_sum += taker_buy_vol
        sell_volume_sum += (vol - taker_buy_vol)

        cvd += (taker_buy_vol - (vol - taker_buy_vol))

    cvd_normalized = cvd / close_now if close_now > 0 else 0

    print(f"   买入成交量: {buy_volume_sum:.2f}")
    print(f"   卖出成交量: {sell_volume_sum:.2f}")
    print(f"   CVD累积: {cvd:.2f}")
    print(f"   CVD归一化: {cvd_normalized:.6f}")

    C_score = max(-100, min(100, cvd_normalized * 5000))
    scores["C+"] = C_score
    print(f"   ✅ C+因子评分: {C_score:.1f}")

    # === S因子: 结构 ===
    print("\n【S因子 - 结构质量】")
    print("   参数: 支撑阻力检测, Pivot点识别")

    # 简化版：寻找pivot高低点
    lookback = min(50, len(c))
    recent_h = h[-lookback:]
    recent_l = l[-lookback:]

    pivots_high = []
    pivots_low = []

    for i in range(2, len(recent_h) - 2):
        if (recent_h[i] > recent_h[i-1] and recent_h[i] > recent_h[i-2] and
            recent_h[i] > recent_h[i+1] and recent_h[i] > recent_h[i+2]):
            pivots_high.append(recent_h[i])

        if (recent_l[i] < recent_l[i-1] and recent_l[i] < recent_l[i-2] and
            recent_l[i] < recent_l[i+1] and recent_l[i] < recent_l[i+2]):
            pivots_low.append(recent_l[i])

    support_levels = [p for p in pivots_low if p < close_now]
    resistance_levels = [p for p in pivots_high if p > close_now]

    nearest_support = max(support_levels) if support_levels else close_now * 0.95
    nearest_resistance = min(resistance_levels) if resistance_levels else close_now * 1.05

    support_distance = (close_now - nearest_support) / atr_now if atr_now > 0 else 0
    resistance_distance = (nearest_resistance - close_now) / atr_now if atr_now > 0 else 0

    print(f"   Pivot高点数: {len(pivots_high)}")
    print(f"   Pivot低点数: {len(pivots_low)}")
    print(f"   最近支撑: {nearest_support:.2f} (距离{support_distance:.2f}ATR)")
    print(f"   最近阻力: {nearest_resistance:.2f} (距离{resistance_distance:.2f}ATR)")

    support_quality = 100 if 1 <= support_distance <= 3 else max(0, 100 - abs(support_distance - 2) * 20)
    resistance_quality = 100 if 2 <= resistance_distance <= 4 else max(0, 100 - abs(resistance_distance - 3) * 20)

    S_score = (support_quality + resistance_quality) / 2
    scores["S"] = S_score
    print(f"   ✅ S因子评分: {S_score:.1f}")

    # === V+因子: 成交量触发 ===
    print("\n【V+因子 - 成交量触发】")
    print("   参数: 成交量倍数, 突破检测")

    # 计算成交量平均值
    vol_avg_20 = sum(v[-20:]) / 20 if len(v) >= 20 else v[-1]
    vol_now = v[-1]
    vol_ratio = vol_now / vol_avg_20 if vol_avg_20 > 0 else 1.0

    print(f"   当前成交量: {vol_now:.2f}")
    print(f"   20周期平均: {vol_avg_20:.2f}")
    print(f"   成交量倍数: {vol_ratio:.2f}x")

    # 突破检测
    breakthrough = 0
    if close_now > nearest_resistance * 0.998:
        breakthrough = 1
        print(f"   检测到向上突破阻力位")
    elif close_now < nearest_support * 1.002:
        breakthrough = -1
        print(f"   检测到向下跌破支撑位")
    else:
        print(f"   未检测到突破")

    V_score = max(-100, min(100, (vol_ratio - 1.0) * 50 + breakthrough * 30))
    scores["V+"] = V_score
    print(f"   ✅ V+因子评分: {V_score:.1f}")

    # === O+因子: OI体制 ===
    print("\n【O+因子 - OI四象限体制】")
    print("   参数: OI变化率, 价格变化率, 四象限判定")

    if oi_data and len(oi_data) >= 24:
        oi_now = float(oi_data[-1].get('sumOpenInterest', 0))
        oi_24h_ago = float(oi_data[-24].get('sumOpenInterest', 0))
        oi_change_pct = ((oi_now - oi_24h_ago) / oi_24h_ago * 100) if oi_24h_ago > 0 else 0

        price_24h_ago = c[-24] if len(c) >= 24 else c[0]
        price_change_pct = ((close_now - price_24h_ago) / price_24h_ago * 100) if price_24h_ago > 0 else 0

        print(f"   当前OI: {oi_now:.2f}")
        print(f"   24h前OI: {oi_24h_ago:.2f}")
        print(f"   OI变化: {oi_change_pct:.2f}%")
        print(f"   价格变化: {price_change_pct:.2f}%")

        # 四象限判定
        if oi_change_pct > 0 and price_change_pct > 0:
            regime = "多头建仓"
            regime_score = 80
        elif oi_change_pct < 0 and price_change_pct < 0:
            regime = "空头平仓"
            regime_score = 80
        elif oi_change_pct > 0 and price_change_pct < 0:
            regime = "空头建仓"
            regime_score = -80
        elif oi_change_pct < 0 and price_change_pct > 0:
            regime = "多头平仓"
            regime_score = -80
        else:
            regime = "震荡"
            regime_score = 0

        print(f"   OI体制: {regime}")
        O_score = regime_score
    else:
        print(f"   ⚠️  OI数据不足")
        O_score = 0

    scores["O+"] = O_score
    print(f"   ✅ O+因子评分: {O_score:.1f}")

    # === L因子: 流动性 ===
    print("\n【L因子 - 流动性质量】")
    print("   说明: 需要订单簿数据，当前使用简化评估")

    # 简化版：基于24h成交额
    if ticker:
        quote_volume = float(ticker.get('quoteVolume', 0))
        print(f"   24h成交额: {quote_volume/1e6:.2f}M USDT")

        if quote_volume > 100e6:
            L_score = 90
        elif quote_volume > 50e6:
            L_score = 75
        elif quote_volume > 10e6:
            L_score = 60
        elif quote_volume > 3e6:
            L_score = 45
        else:
            L_score = 30
    else:
        L_score = 50

    scores["L"] = L_score
    print(f"   ✅ L因子评分: {L_score:.1f}")

    # === B因子: 基差+资金费 ===
    print("\n【B因子 - 基差+资金费率】")
    print("   参数: 现货-期货价差, 资金费率")

    # 基差
    if spot_k1 and len(spot_k1) > 0:
        spot_price = float(spot_k1[-1][4])
        basis_bps = ((close_now - spot_price) / spot_price * 10000) if spot_price > 0 else 0
        print(f"   现货价格: {spot_price:.2f}")
        print(f"   期货价格: {close_now:.2f}")
        print(f"   基差: {basis_bps:.2f}bps")
    else:
        basis_bps = 0
        print(f"   ⚠️  无现货数据")

    # 资金费率
    if ticker and 'lastFundingRate' in ticker:
        funding_rate = float(ticker.get('lastFundingRate', 0))
        print(f"   资金费率: {funding_rate*100:.4f}%")
    else:
        funding_rate = 0.0001
        print(f"   ⚠️  无资金费率数据，使用默认: {funding_rate*100:.4f}%")

    # 评分
    basis_score = max(-50, min(50, basis_bps / 2))
    funding_score = max(-50, min(50, funding_rate * 25000))

    B_score = basis_score * 0.6 + funding_score * 0.4
    scores["B"] = B_score
    print(f"   ✅ B因子评分: {B_score:.1f}")

    # === Q因子: 清算密度 ===
    print("\n【Q因子 - 清算密度】")
    print("   说明: 需要aggTrades数据，当前使用简化评估")

    # 简化版：基于价格波动
    price_std = (max(c[-24:]) - min(c[-24:])) / close_now if len(c) >= 24 else 0
    print(f"   24h价格波动率: {price_std*100:.2f}%")

    if price_std > 0.05:
        Q_score = -50  # 高波动，可能有清算
    else:
        Q_score = 0

    scores["Q"] = Q_score
    print(f"   ✅ Q因子评分: {Q_score:.1f}")

    # === I因子: 独立性 ===
    print("\n【I因子 - 独立性】")
    print("   说明: 需要BTC/ETH数据，当前使用简化评估")

    # 简化版：非BTC/ETH默认50分
    if symbol in ['BTCUSDT', 'ETHUSDT']:
        I_score = 100
        print(f"   {symbol}为基准币种，独立性最高")
    else:
        I_score = 50
        print(f"   默认中等独立性")

    scores["I"] = I_score
    print(f"   ✅ I因子评分: {I_score:.1f}")

    # === F调节器: 资金领先性 ===
    print("\n【F调节器 - 资金领先性】")
    print("   说明: 不参与加权，仅调节概率")

    F_score = 0  # 简化版
    print(f"   F调节器: {F_score:.1f}")

    # ========== 第4步: 加权评分 ==========
    print_section("第4步: 加权评分和概率映射")

    # 权重
    weights = {
        "T": 25,
        "M": 15,
        "C+": 20,
        "S": 10,
        "V+": 15,
        "O+": 20,
        "L": 20,
        "B": 15,
        "Q": 10,
        "I": 10
    }

    print("\n权重系统（160点归一化到±100）:")
    for factor, weight in weights.items():
        print(f"   {factor}: {weight}点")

    # 计算加权总分
    weighted_sum = 0
    total_weight = 0

    print("\n加权计算:")
    for factor, score in scores.items():
        if factor in weights:
            weight = weights[factor]
            contribution = score * weight
            weighted_sum += contribution
            total_weight += weight
            print(f"   {factor}: {score:6.1f} × {weight:2d} = {contribution:7.1f}")

    print(f"   {'─'*40}")
    print(f"   总和: {weighted_sum:7.1f} / 权重: {total_weight}")

    # 归一化到±100
    normalization_factor = 1.6
    weighted_score = weighted_sum / normalization_factor
    weighted_score = max(-100, min(100, weighted_score))

    print(f"   归一化(÷1.6): {weighted_score:.1f}")

    # 置信度
    confidence = abs(weighted_score)

    # 方向判定
    if weighted_score > 10:
        direction = "LONG"
        direction_emoji = "🟢"
    elif weighted_score < -10:
        direction = "SHORT"
        direction_emoji = "🔴"
    else:
        direction = "NEUTRAL"
        direction_emoji = "⚪"

    print(f"\n{direction_emoji} 方向: {direction}")
    print(f"   置信度: {confidence:.1f}")

    # ========== 第5步: 概率映射 ==========
    print_section("第5步: Sigmoid概率映射")

    # Sigmoid映射
    base_temperature = 35.0
    f_adjustment = F_score / 100.0
    adjusted_temperature = base_temperature * (1.0 + f_adjustment * 0.2)

    print(f"   基础温度: {base_temperature}")
    print(f"   F调节: {f_adjustment:+.2f}")
    print(f"   调整后温度: {adjusted_temperature:.2f}")

    # Sigmoid函数
    import math
    x = weighted_score / adjusted_temperature
    probability = 1 / (1 + math.exp(-x))

    # 映射到0.05-0.95
    probability = 0.05 + 0.9 * probability

    print(f"   Sigmoid输入: {x:.4f}")
    print(f"   原始概率: {probability:.4f}")
    print(f"   映射后概率: {probability:.4f}")

    # 信号判定
    if probability >= 0.62:
        tier = "PRIME"
        tier_emoji = "⭐"
    elif probability >= 0.58:
        tier = "WATCH"
        tier_emoji = "👁️"
    else:
        tier = "NONE"
        tier_emoji = "❌"

    print(f"\n{tier_emoji} 信号等级: {tier}")

    # ========== 结果总结 ==========
    print_header(f"{symbol} 分析结果总结")

    total_time = time.time() - start_time

    result = {
        "symbol": symbol,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "close": close_now,
        "atr": atr_now,
        "scores": scores,
        "weighted_score": weighted_score,
        "confidence": confidence,
        "direction": direction,
        "probability": probability,
        "tier": tier,
        "elapsed_seconds": total_time
    }

    print(f"\n币种: {symbol}")
    print(f"价格: {close_now:.4f} USDT")
    print(f"方向: {direction_emoji} {direction}")
    print(f"置信度: {confidence:.1f}")
    print(f"概率: {probability:.4f} ({probability*100:.2f}%)")
    print(f"信号: {tier_emoji} {tier}")
    print(f"\n10维因子评分:")
    for factor in ["T", "M", "C+", "S", "V+", "O+", "L", "B", "Q", "I"]:
        score = scores.get(factor, 0)
        print(f"   {factor:3s}: {score:6.1f}")

    print(f"\n分析耗时: {total_time:.2f}秒")
    print("=" * 80)

    return result


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("  CryptoSignal 详细调试测试")
    print("  测试币种: BTC, SOL, BNB, COAI, XPL")
    print("=" * 80)

    # 测试币种
    test_symbols = [
        "BTCUSDT",
        "SOLUSDT",
        "BNBUSDT",
        "COAIUSDT",
        "XPLUSDT"
    ]

    results = []

    print(f"\n开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试币种数: {len(test_symbols)}")

    overall_start = time.time()

    for i, symbol in enumerate(test_symbols, 1):
        print(f"\n\n{'#'*80}")
        print(f"# 进度: {i}/{len(test_symbols)}")
        print(f"{'#'*80}")

        try:
            result = analyze_symbol_detailed(symbol)
            if result:
                results.append(result)
            else:
                warn(f"⚠️  {symbol} 分析失败")
        except Exception as e:
            error(f"❌ {symbol} 分析异常: {e}")
            import traceback
            traceback.print_exc()

        # 延迟1秒，避免请求过快
        if i < len(test_symbols):
            time.sleep(1)

    overall_time = time.time() - overall_start

    # ========== 最终汇总 ==========
    print("\n\n" + "=" * 80)
    print("  最终汇总")
    print("=" * 80)

    print(f"\n总耗时: {overall_time:.2f}秒")
    print(f"成功分析: {len(results)}/{len(test_symbols)} 个币种")
    print(f"平均耗时: {overall_time/len(test_symbols):.2f}秒/币种")

    if results:
        print("\n结果汇总:")
        print(f"{'币种':<12} {'价格':<12} {'方向':<8} {'概率':<8} {'信号':<8} {'耗时':<8}")
        print("-" * 80)

        for r in results:
            direction_emoji = "🟢" if r['direction'] == "LONG" else ("🔴" if r['direction'] == "SHORT" else "⚪")
            tier_emoji = "⭐" if r['tier'] == "PRIME" else ("👁️" if r['tier'] == "WATCH" else "❌")

            print(f"{r['symbol']:<12} {r['close']:<12.4f} {direction_emoji}{r['direction']:<7} "
                  f"{r['probability']*100:<7.2f}% {tier_emoji}{r['tier']:<7} {r['elapsed_seconds']:<7.2f}s")

        # 统计
        prime_count = sum(1 for r in results if r['tier'] == 'PRIME')
        watch_count = sum(1 for r in results if r['tier'] == 'WATCH')
        long_count = sum(1 for r in results if r['direction'] == 'LONG')
        short_count = sum(1 for r in results if r['direction'] == 'SHORT')

        print(f"\n信号统计:")
        print(f"   ⭐ Prime信号: {prime_count}")
        print(f"   👁️  Watch信号: {watch_count}")
        print(f"   🟢 看多: {long_count}")
        print(f"   🔴 看空: {short_count}")

    print("\n" + "=" * 80)
    print("  ✅ 测试完成")
    print("=" * 80)


if __name__ == "__main__":
    main()
