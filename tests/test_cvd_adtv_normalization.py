#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试CVD ADTV_notional归一化方案

验证：
1. 高价高流动性币种（BTCUSDT）
2. 中等币种（ETHUSDT）
3. 低价币种（SHIBUSDT/PEPEUSDT）

对比旧方案（slope/price）和新方案（slope/ADTV_notional）
"""

import sys
sys.path.insert(0, '/home/user/cryptosignal')

from ats_core.features.cvd_flow import score_cvd_flow
from ats_core.sources.binance import get_klines
from ats_core.features.cvd import cvd_from_klines


def test_symbol(symbol: str):
    """测试单个币种的CVD归一化"""
    print(f"\n{'='*80}")
    print(f"测试币种: {symbol}")
    print(f"{'='*80}")

    # 获取数据
    klines = get_klines(symbol, "1h", 100)
    if not klines or len(klines) < 50:
        print(f"❌ 数据不足")
        return

    # 计算CVD
    cvd_series = cvd_from_klines(klines, use_taker_buy=True)
    c = [float(k[4]) for k in klines]  # 收盘价

    # 获取最近7根的CVD变化
    cvd_window = cvd_series[-7:]
    cvd_change = cvd_window[-1] - cvd_window[0]

    # 计算ADTV
    quote_volumes = [float(k[7]) for k in klines[-24:]]
    ADTV_notional = sum(quote_volumes) / len(quote_volumes)

    # 当前价格
    price = c[-1]

    print(f"\n📊 基础数据:")
    print(f"   当前价格: ${price:,.8f}")
    print(f"   6h CVD变化: {cvd_change:,.2f}")
    print(f"   ADTV (24h平均): ${ADTV_notional:,.2f}")

    # 旧方案：slope / price
    print(f"\n🔴 旧方案 (slope / price):")
    C_old, meta_old = score_cvd_flow(cvd_series, c, False, params=None, klines=None)  # 不传klines使用旧方案
    print(f"   归一化方法: {meta_old['normalization_method']}")
    print(f"   CVD6归一化: {meta_old['cvd6']:.6f}")
    print(f"   C因子得分: {C_old}")
    print(f"   CVD原始变化: {meta_old['cvd_raw']:.2f}")

    # 新方案：slope / ADTV_notional
    print(f"\n🟢 新方案 (slope / ADTV_notional):")
    C_new, meta_new = score_cvd_flow(cvd_series, c, False, params=None, klines=klines)  # 传入klines使用新方案
    print(f"   归一化方法: {meta_new['normalization_method']}")
    print(f"   CVD6归一化: {meta_new['cvd6']:.6f}")
    print(f"   C因子得分: {C_new}")
    print(f"   CVD原始变化: {meta_new['cvd_raw']:.2f}")
    if 'ADTV_notional' in meta_new:
        print(f"   ADTV_notional: ${meta_new['ADTV_notional']:,.2f}")

    # 对比
    print(f"\n📈 对比分析:")
    print(f"   价格归一化倍数: {abs(cvd_change / price):.8f}")
    print(f"   ADTV归一化倍数: {abs(cvd_change / ADTV_notional):.8f}")
    print(f"   得分变化: {C_old} → {C_new} ({C_new - C_old:+d})")

    # 判断
    if C_old == C_new:
        print(f"   ✅ 得分一致（说明都在合理范围）")
    elif abs(C_old) > 90 and abs(C_new) < 90:
        print(f"   ✅ 新方案解决饱和问题")
    elif abs(C_old) < 10 and abs(C_new) > 10:
        print(f"   ⚠️ 新方案提高了灵敏度")
    else:
        print(f"   📊 得分有差异，需进一步分析")


def compare_cross_coin():
    """跨币种可比性测试"""
    print(f"\n{'='*80}")
    print(f"跨币种可比性测试")
    print(f"{'='*80}\n")

    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    results = []
    for symbol in symbols:
        try:
            klines = get_klines(symbol, "1h", 100)
            if not klines or len(klines) < 50:
                continue

            cvd_series = cvd_from_klines(klines, use_taker_buy=True)
            c = [float(k[4]) for k in klines]

            # 旧方案
            C_old, meta_old = score_cvd_flow(cvd_series, c, False, params=None, klines=None)

            # 新方案
            C_new, meta_new = score_cvd_flow(cvd_series, c, False, params=None, klines=klines)

            results.append({
                "symbol": symbol,
                "price": c[-1],
                "ADTV": meta_new.get('ADTV_notional', 0),
                "C_old": C_old,
                "C_new": C_new,
                "cvd6_old": meta_old['cvd6'],
                "cvd6_new": meta_new['cvd6']
            })
        except Exception as e:
            print(f"⚠️ {symbol} 测试失败: {e}")

    # 打印对比表
    print(f"{'币种':<12} {'价格':<15} {'ADTV(USD)':<15} {'C旧':<6} {'C新':<6} {'归一化旧':<12} {'归一化新':<12}")
    print("-" * 95)
    for r in results:
        print(f"{r['symbol']:<12} ${r['price']:<14,.2f} ${r['ADTV']:<14,.0f} {r['C_old']:<6} {r['C_new']:<6} {r['cvd6_old']:<12.6f} {r['cvd6_new']:<12.6f}")

    print(f"\n💡 分析:")
    print(f"   - 新方案的归一化值（cvd6_new）应该在相近范围内")
    print(f"   - ADTV越大的币种，需要更大的CVD变化才能得高分")
    print(f"   - 这符合预期：高流动性币种对资金流入的敏感度应该更低")


if __name__ == "__main__":
    # 测试单个币种
    test_symbol("BTCUSDT")
    test_symbol("ETHUSDT")
    test_symbol("SOLUSDT")

    # 尝试测试低价币（如果可用）
    try:
        test_symbol("SHIBUSDT")
    except Exception as e:
        print(f"\n⚠️ SHIBUSDT测试跳过: {e}")

    # 跨币种对比
    compare_cross_coin()

    print(f"\n{'='*80}")
    print(f"✅ 测试完成")
    print(f"{'='*80}\n")
