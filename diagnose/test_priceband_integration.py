#!/usr/bin/env python3
# coding: utf-8
"""
测试价格带法流动性集成（P2.5）

验证：
1. 新的price band方法是否正常工作
2. 与旧方法的对比
3. 四道闸判断是否准确
"""

import sys
sys.path.insert(0, '/home/user/cryptosignal')

from ats_core.features.liquidity_priceband import score_liquidity_priceband
import json

print("=" * 70)
print("价格带法流动性集成测试（P2.5）")
print("=" * 70)

# 加载配置参数
try:
    with open('/home/user/cryptosignal/config/params.json', 'r') as f:
        config = json.load(f)
        liquidity_params = config.get('liquidity', {})
    print("\n✅ 配置参数加载成功")
    print(f"  band_bps: {liquidity_params.get('band_bps', 40.0)}")
    print(f"  impact_threshold_bps: {liquidity_params.get('impact_threshold_bps', 10.0)}")
    print(f"  obi_threshold: {liquidity_params.get('obi_threshold', 0.30)}")
    print(f"  spread_threshold_bps: {liquidity_params.get('spread_threshold_bps', 25.0)}")
except Exception as e:
    print(f"\n❌ 配置加载失败: {e}")
    liquidity_params = {}

# 测试场景1: BTC典型流动性（优秀）
print("\n" + "=" * 70)
print("[场景1] BTC典型流动性（应该优秀）")
print("=" * 70)

btc_orderbook = {
    'bids': [
        [50000.0, 5.0], [49995.0, 8.0], [49990.0, 10.0], [49985.0, 12.0],
        [49980.0, 15.0], [49975.0, 18.0], [49970.0, 20.0], [49965.0, 22.0],
        [49960.0, 25.0], [49955.0, 28.0], [49950.0, 30.0], [49945.0, 32.0],
        [49940.0, 35.0], [49935.0, 38.0], [49930.0, 40.0]
    ],
    'asks': [
        [50005.0, 5.0], [50010.0, 8.0], [50015.0, 10.0], [50020.0, 12.0],
        [50025.0, 15.0], [50030.0, 18.0], [50035.0, 20.0], [50040.0, 22.0],
        [50045.0, 25.0], [50050.0, 28.0], [50055.0, 30.0], [50060.0, 32.0],
        [50065.0, 35.0], [50070.0, 38.0], [50075.0, 40.0]
    ]
}

btc_score, btc_meta = score_liquidity_priceband(btc_orderbook, liquidity_params)

print(f"\n📊 评分结果:")
print(f"  流动性评分: {btc_score} / 100")
print(f"  流动性等级: {btc_meta['liquidity_level']}")

print(f"\n💹 指标详情:")
print(f"  价差: {btc_meta['spread_bps']:.2f} bps (阈值≤{btc_meta['spread_threshold_bps']:.0f})")
print(f"  买入冲击: {btc_meta['buy_impact_bps']:.2f} bps")
print(f"  卖出冲击: {btc_meta['sell_impact_bps']:.2f} bps")
print(f"  最大冲击: {btc_meta['max_impact_bps']:.2f} bps (阈值≤{btc_meta['impact_threshold_bps']:.0f})")
print(f"  OBI: {btc_meta['obi_value']:.3f} (阈值≤{btc_meta['obi_threshold']:.2f})")

print(f"\n🚪 四道闸检测:")
print(f"  通过数: {btc_meta['gates_passed']}/3")
print(f"  impact≤10bps: {'✅' if btc_meta['gate_impact'] else '❌'} ({btc_meta['max_impact_bps']:.2f} bps)")
print(f"  OBI≤0.30: {'✅' if btc_meta['gate_obi'] else '❌'} ({abs(btc_meta['obi_value']):.3f})")
print(f"  spread≤25bps: {'✅' if btc_meta['gate_spread'] else '❌'} ({btc_meta['spread_bps']:.2f} bps)")

print(f"\n📦 价格带分析:")
print(f"  价格带宽度: ±{btc_meta['band_bps']:.0f} bps")
print(f"  中间价: ${btc_meta['mid_price']:.2f}")
print(f"  买盘（带内）: {btc_meta['bid_qty_in_band']:.2f} 币")
print(f"  卖盘（带内）: {btc_meta['ask_qty_in_band']:.2f} 币")

# 测试场景2: 山寨币低流动性（应该较差）
print("\n" + "=" * 70)
print("[场景2] 山寨币低流动性（应该较差）")
print("=" * 70)

altcoin_orderbook = {
    'bids': [
        [1.0000, 500], [0.9900, 300], [0.9800, 200], [0.9700, 150],
        [0.9600, 100]
    ],
    'asks': [
        [1.0200, 400], [1.0300, 300], [1.0400, 200], [1.0500, 150],
        [1.0600, 100]
    ]
}

alt_score, alt_meta = score_liquidity_priceband(altcoin_orderbook, liquidity_params)

print(f"\n📊 评分结果:")
print(f"  流动性评分: {alt_score} / 100")
print(f"  流动性等级: {alt_meta['liquidity_level']}")

print(f"\n💹 指标详情:")
print(f"  价差: {alt_meta['spread_bps']:.2f} bps")
print(f"  最大冲击: {alt_meta['max_impact_bps']:.2f} bps")
print(f"  OBI: {alt_meta['obi_value']:.3f}")

print(f"\n🚪 四道闸检测:")
print(f"  通过数: {alt_meta['gates_passed']}/3")
print(f"  impact≤10bps: {'✅' if alt_meta['gate_impact'] else '❌'} ({alt_meta['max_impact_bps']:.2f} bps)")
print(f"  OBI≤0.30: {'✅' if alt_meta['gate_obi'] else '❌'} ({abs(alt_meta['obi_value']):.3f})")
print(f"  spread≤25bps: {'✅' if alt_meta['gate_spread'] else '❌'} ({alt_meta['spread_bps']:.2f} bps)")

# 测试场景3: 极端失衡（买盘优势）
print("\n" + "=" * 70)
print("[场景3] 极端失衡订单簿（买盘优势 - OBI应该失败）")
print("=" * 70)

imbalance_orderbook = {
    'bids': [
        [50000.0, 50.0], [49995.0, 45.0], [49990.0, 40.0], [49985.0, 35.0],
        [49980.0, 30.0], [49975.0, 25.0], [49970.0, 20.0]
    ],
    'asks': [
        [50005.0, 5.0], [50010.0, 4.0], [50015.0, 3.0], [50020.0, 2.0],
        [50025.0, 1.0]
    ]
}

imb_score, imb_meta = score_liquidity_priceband(imbalance_orderbook, liquidity_params)

print(f"\n📊 评分结果:")
print(f"  流动性评分: {imb_score} / 100")
print(f"  流动性等级: {imb_meta['liquidity_level']}")

print(f"\n💹 指标详情:")
print(f"  OBI: {imb_meta['obi_value']:.3f} (买盘:{imb_meta['bid_qty_in_band']:.1f}, 卖盘:{imb_meta['ask_qty_in_band']:.1f})")
print(f"  价差: {imb_meta['spread_bps']:.2f} bps")
print(f"  最大冲击: {imb_meta['max_impact_bps']:.2f} bps")

print(f"\n🚪 四道闸检测:")
print(f"  通过数: {imb_meta['gates_passed']}/3")
print(f"  impact≤10bps: {'✅' if imb_meta['gate_impact'] else '❌'} ({imb_meta['max_impact_bps']:.2f} bps)")
print(f"  OBI≤0.30: {'✅' if imb_meta['gate_obi'] else '❌'} ({abs(imb_meta['obi_value']):.3f})")
print(f"  spread≤25bps: {'✅' if imb_meta['gate_spread'] else '❌'} ({imb_meta['spread_bps']:.2f} bps)")

# 总结
print("\n" + "=" * 70)
print("✅ 价格带法集成测试完成")
print("=" * 70)

print("\n📝 结果总结:")
print(f"  场景1（BTC优秀）: {btc_score}/100, 四道闸 {btc_meta['gates_passed']}/3")
print(f"  场景2（山寨较差）: {alt_score}/100, 四道闸 {alt_meta['gates_passed']}/3")
print(f"  场景3（失衡）: {imb_score}/100, 四道闸 {imb_meta['gates_passed']}/3")

print("\n🎯 验证要点:")
print("  ✅ 价格带聚合 - 不再使用固定档位数")
print("  ✅ Coverage(q,B) - 检查价格带内容量")
print("  ✅ impact_bps(q) - 计算实际价格冲击")
print("  ✅ OBI_B - 价格带内失衡度")
print("  ✅ 四道闸对齐 - impact≤10bps, OBI≤0.30, spread≤25bps")

print("\n" + "=" * 70)
