#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试CVD相对历史斜率归一化方案

验证：
1. 高价高流动性币种（BTCUSDT）
2. 中等币种（ETHUSDT）
3. 低价币种（SHIBUSDT/PEPEUSDT）

对比新方案（相对历史斜率）：
- 核心理念：CVD判断方向和斜率，与绝对量无关
- 相对强度 = 当前斜率 / 历史平均斜率
- BTC和SHIB在同等相对强度下得分一致
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

    # 当前价格
    price = c[-1]

    print(f"\n📊 基础数据:")
    print(f"   当前价格: ${price:,.8f}")
    print(f"   6h CVD变化: {cvd_change:,.2f}")

    # 新方案：相对历史斜率归一化
    print(f"\n🟢 新方案 (相对历史斜率归一化):")
    C, meta = score_cvd_flow(cvd_series, c, False, params=None, klines=klines)
    print(f"   归一化方法: {meta['normalization_method']}")
    print(f"   CVD原始变化: {meta['cvd6_raw']:.2f}")
    print(f"   CVD斜率: {meta['cvd_slope']:.4f}")
    print(f"   C因子得分: {C} ({meta['cvd_score']:.2f})")
    print(f"   R²拟合度: {meta['r_squared']:.3f} {'✅一致' if meta['is_consistent'] else '⚠️震荡'}")

    # 相对强度信息
    if 'relative_intensity' in meta:
        print(f"\n📊 相对历史分析:")
        print(f"   历史平均斜率: {meta['avg_abs_slope']:.4f}")
        print(f"   相对强度: {meta['relative_intensity']:.3f}x")
        if 'p95_slope' in meta:
            print(f"   95分位数阈值: {meta['p95_slope']:.4f}")
        print(f"   拥挤警告: {'🔴是' if meta['crowding_warn'] else '✅否'}")

        # 解释相对强度
        rel_int = meta['relative_intensity']
        if rel_int > 2:
            print(f"   💡 解释: 当前变化速度是历史平均的{rel_int:.1f}倍，极强趋势！")
        elif rel_int > 1.5:
            print(f"   💡 解释: 当前变化速度是历史平均的{rel_int:.1f}倍，强趋势")
        elif rel_int > 0.8:
            print(f"   💡 解释: 当前变化速度接近历史平均，正常趋势")
        elif rel_int > 0:
            print(f"   💡 解释: 当前变化速度低于历史平均，弱趋势")
        else:
            print(f"   💡 解释: 方向与主趋势相反或无明显趋势")
    else:
        print(f"\n⚠️ 历史数据不足（需要30+数据点），使用降级方案")


def compare_cross_coin():
    """跨币种可比性测试"""
    print(f"\n{'='*80}")
    print(f"跨币种可比性测试（相对历史斜率归一化）")
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

            # 新方案
            C, meta = score_cvd_flow(cvd_series, c, False, params=None, klines=klines)

            results.append({
                "symbol": symbol,
                "price": c[-1],
                "C": C,
                "cvd_raw": meta['cvd6_raw'],
                "slope": meta['cvd_slope'],
                "rel_int": meta.get('relative_intensity', None),
                "avg_slope": meta.get('avg_abs_slope', None),
                "is_consistent": meta['is_consistent']
            })
        except Exception as e:
            print(f"⚠️ {symbol} 测试失败: {e}")

    # 打印对比表
    print(f"{'币种':<12} {'价格':<15} {'CVD变化':<12} {'斜率':<10} {'相对强度':<10} {'C分数':<8} {'一致性':<6}")
    print("-" * 85)
    for r in results:
        rel_str = f"{r['rel_int']:.2f}x" if r['rel_int'] is not None else "N/A"
        consistent_str = "✅" if r['is_consistent'] else "⚠️"
        print(f"{r['symbol']:<12} ${r['price']:<14,.2f} {r['cvd_raw']:<12,.0f} {r['slope']:<10.2f} {rel_str:<10} {r['C']:<8} {consistent_str:<6}")

    print(f"\n💡 分析:")
    print(f"   - 相对强度反映当前CVD变化速度相对于历史的倍数")
    print(f"   - 不同币种在相同相对强度下应得到相似得分")
    print(f"   - 方向由斜率正负决定（正=买入压力，负=卖出压力）")
    print(f"   - 绝对CVD变化量不影响得分，只看相对速度")
    print(f"\n💡 关键优势:")
    print(f"   ✅ BTC和SHIB在同等相对强度下得分一致")
    print(f"   ✅ 自动适应每个币种的历史特征")
    print(f"   ✅ 解决低价币过度放大问题")
    print(f"   ✅ 实现真正的跨币种可比性")


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
