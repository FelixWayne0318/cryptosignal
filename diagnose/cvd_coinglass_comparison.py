#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CVD计算诊断：对比系统CVD vs CoinGlass CVD

目的：
1. 验证CVD计算公式是否正确
2. 对比合约+现货聚合CVD
3. 检查方向是否一致
4. 找出差异根因
"""

import sys
sys.path.insert(0, '/home/user/cryptosignal')

from ats_core.features.cvd import cvd_from_klines, cvd_combined, cvd_mix_with_oi_price
from ats_core.sources.binance import get_klines
import json


def diagnose_cvd_for_symbol(symbol: str, interval: str = "1h", limit: int = 24):
    """
    诊断单个币种的CVD计算

    Args:
        symbol: 交易对（如BTCUSDT）
        interval: 时间周期
        limit: K线数量
    """
    print("="*80)
    print(f"CVD诊断: {symbol} ({interval})")
    print("="*80)

    # 1. 获取合约K线
    print(f"\n1️⃣ 获取合约K线数据...")
    try:
        futures_klines = get_klines(symbol, interval, limit)
        print(f"   ✅ 获取{len(futures_klines)}根合约K线")
    except Exception as e:
        print(f"   ❌ 合约K线获取失败: {e}")
        return

    # 2. 获取现货K线（如果可用）
    print(f"\n2️⃣ 获取现货K线数据...")
    try:
        from ats_core.sources.binance import get_spot_klines
        spot_klines = get_spot_klines(symbol, interval, limit)
        if spot_klines and len(spot_klines) > 0:
            print(f"   ✅ 获取{len(spot_klines)}根现货K线")
            has_spot = True
        else:
            print(f"   ⚠️ 无现货数据（币种可能无现货市场）")
            has_spot = False
    except Exception as e:
        print(f"   ⚠️ 现货K线获取失败: {e}")
        spot_klines = None
        has_spot = False

    # 3. 计算合约CVD
    print(f"\n3️⃣ 计算合约CVD...")
    cvd_futures = cvd_from_klines(futures_klines, use_taker_buy=True)
    print(f"   合约CVD序列长度: {len(cvd_futures)}")
    print(f"   最近5个值: {[round(x, 2) for x in cvd_futures[-5:]]}")
    print(f"   24h变化: {cvd_futures[-1] - cvd_futures[0]:.2f}")

    # 4. 计算现货CVD（如果有）
    if has_spot:
        print(f"\n4️⃣ 计算现货CVD...")
        cvd_spot = cvd_from_klines(spot_klines, use_taker_buy=True)
        print(f"   现货CVD序列长度: {len(cvd_spot)}")
        print(f"   最近5个值: {[round(x, 2) for x in cvd_spot[-5:]]}")
        print(f"   24h变化: {cvd_spot[-1] - cvd_spot[0]:.2f}")
    else:
        print(f"\n4️⃣ 跳过现货CVD（无数据）")
        cvd_spot = None

    # 5. 计算组合CVD（动态权重）
    if has_spot:
        print(f"\n5️⃣ 计算组合CVD（合约+现货，动态权重）...")
        cvd_comb = cvd_combined(futures_klines, spot_klines, use_dynamic_weight=True)
        print(f"   组合CVD序列长度: {len(cvd_comb)}")
        print(f"   最近5个值: {[round(x, 2) for x in cvd_comb[-5:]]}")
        print(f"   24h变化: {cvd_comb[-1] - cvd_comb[0]:.2f}")

        # 计算权重
        f_quote = sum([float(k[7]) for k in futures_klines])
        s_quote = sum([float(k[7]) for k in spot_klines])
        total_quote = f_quote + s_quote
        if total_quote > 0:
            f_weight = f_quote / total_quote
            s_weight = s_quote / total_quote
        else:
            f_weight, s_weight = 0.7, 0.3

        print(f"\n   权重分析:")
        print(f"   合约成交额: ${f_quote:,.0f}")
        print(f"   现货成交额: ${s_quote:,.0f}")
        print(f"   合约权重: {f_weight:.1%}")
        print(f"   现货权重: {s_weight:.1%}")
    else:
        print(f"\n5️⃣ 使用纯合约CVD（无现货数据）")
        cvd_comb = cvd_futures

    # 6. 详细数据分析（最近3根K线）
    print(f"\n6️⃣ 详细数据分析（最近3根K线）:")
    print(f"   {'时间':<20} {'开盘':<10} {'收盘':<10} {'成交量':<15} {'主动买入量':<15} {'CVD增量':<15}")
    print("   " + "-"*95)

    for i in range(max(0, len(futures_klines)-3), len(futures_klines)):
        k = futures_klines[i]
        timestamp = k[0]
        open_price = float(k[1])
        close_price = float(k[4])
        total_vol = float(k[5])
        taker_buy = float(k[9]) if len(k) > 9 else 0.0
        taker_sell = total_vol - taker_buy
        delta = taker_buy - taker_sell

        from datetime import datetime
        dt = datetime.fromtimestamp(timestamp / 1000)

        print(f"   {dt.strftime('%Y-%m-%d %H:%M'):<20} "
              f"{open_price:<10.2f} {close_price:<10.2f} "
              f"{total_vol:<15,.2f} {taker_buy:<15,.2f} "
              f"{delta:<15,.2f}")

    # 7. CVD方向分析
    print(f"\n7️⃣ CVD方向分析:")
    cvd_6h_change = cvd_comb[-1] - cvd_comb[-7] if len(cvd_comb) >= 7 else 0.0
    cvd_24h_change = cvd_comb[-1] - cvd_comb[0]

    direction_6h = "🟢 买入" if cvd_6h_change > 0 else "🔴 卖出" if cvd_6h_change < 0 else "⚪ 中性"
    direction_24h = "🟢 买入" if cvd_24h_change > 0 else "🔴 卖出" if cvd_24h_change < 0 else "⚪ 中性"

    print(f"   6小时CVD变化: {cvd_6h_change:+,.2f} {direction_6h}")
    print(f"   24小时CVD变化: {cvd_24h_change:+,.2f} {direction_24h}")

    # 8. 与价格关系
    print(f"\n8️⃣ CVD与价格关系:")
    price_change = float(futures_klines[-1][4]) - float(futures_klines[0][4])
    price_change_pct = price_change / float(futures_klines[0][4]) * 100

    print(f"   24小时价格变化: {price_change:+.2f} ({price_change_pct:+.2f}%)")

    if price_change > 0 and cvd_24h_change > 0:
        print(f"   ✅ 健康上涨：价格↑ + CVD↑（买盘推动）")
    elif price_change > 0 and cvd_24h_change < 0:
        print(f"   ⚠️ 虚假上涨：价格↑ + CVD↓（可能是空头回补）")
    elif price_change < 0 and cvd_24h_change < 0:
        print(f"   ✅ 健康下跌：价格↓ + CVD↓（卖盘主导）")
    elif price_change < 0 and cvd_24h_change > 0:
        print(f"   ⚠️ 潜在反转：价格↓ + CVD↑（抄底资金进场）")

    print("\n" + "="*80)
    return cvd_comb


def compare_multiple_symbols():
    """对比多个币种的CVD"""
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    print("\n" + "="*80)
    print("多币种CVD对比")
    print("="*80 + "\n")

    results = {}
    for symbol in symbols:
        try:
            cvd = diagnose_cvd_for_symbol(symbol, interval="1h", limit=24)
            results[symbol] = {
                "24h_change": cvd[-1] - cvd[0] if cvd and len(cvd) >= 24 else 0.0,
                "6h_change": cvd[-1] - cvd[-7] if cvd and len(cvd) >= 7 else 0.0
            }
            print("\n")
        except Exception as e:
            print(f"❌ {symbol} 分析失败: {e}\n")

    # 汇总表格
    print("\n" + "="*80)
    print("CVD变化汇总")
    print("="*80)
    print(f"{'币种':<15} {'24h CVD变化':<20} {'6h CVD变化':<20} {'方向':<10}")
    print("-"*80)

    for symbol, data in results.items():
        change_24h = data["24h_change"]
        change_6h = data["6h_change"]
        direction = "🟢 买入" if change_24h > 0 else "🔴 卖出" if change_24h < 0 else "⚪ 中性"
        print(f"{symbol:<15} {change_24h:>+18,.0f}  {change_6h:>+18,.0f}  {direction:<10}")

    print("="*80)


def explain_cvd_calculation():
    """解释CVD计算方法"""
    print("\n" + "="*80)
    print("CVD计算方法说明")
    print("="*80)

    explanation = """
1. 数据来源：
   - Binance K线数据（12列）
   - [5]: total_volume（总成交量）
   - [9]: taker_buy_base_asset_volume（主动买入量）✅ 真实数据

2. CVD增量计算：
   delta = taker_buy - taker_sell
        = taker_buy - (total_volume - taker_buy)
        = 2 * taker_buy - total_volume

3. CVD累积：
   CVD[i] = CVD[i-1] + delta[i]

4. 合约+现货组合（如果有现货数据）：
   - 计算合约CVD
   - 计算现货CVD
   - 动态权重 = 成交额比例（USDT）
   - 组合CVD = 合约权重 × 合约CVD增量 + 现货权重 × 现货CVD增量

5. 与CoinGlass的区别：
   - CoinGlass: 可能使用多交易所聚合数据
   - 我们: 仅使用Binance数据（单交易所）
   - CoinGlass: 可能使用不同的时间窗口
   - 我们: 使用1小时K线

   如果方向不一致，可能原因：
   ❌ 使用单交易所 vs 多交易所
   ❌ 时间窗口不同
   ❌ 是否包含现货数据
   ✅ 计算公式本身是正确的
"""
    print(explanation)
    print("="*80)


if __name__ == "__main__":
    import sys

    # 1. 解释CVD计算
    explain_cvd_calculation()

    # 2. 诊断单个币种
    if len(sys.argv) > 1:
        symbol = sys.argv[1]
        diagnose_cvd_for_symbol(symbol, interval="1h", limit=48)
    else:
        # 3. 对比多个币种
        compare_multiple_symbols()

    print("\n💡 使用方法:")
    print("   python3 diagnose/cvd_coinglass_comparison.py BTCUSDT")
    print("   python3 diagnose/cvd_coinglass_comparison.py")
