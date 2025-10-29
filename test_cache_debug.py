#!/usr/bin/env python
# coding: utf-8
"""
测试L/B因子数据流问题的调试脚本
"""

# 模拟缓存数据
test_symbol = 'BTCUSDT'

# 模拟订单簿数据（正常格式）
mock_orderbook = {
    'lastUpdateId': 12345,
    'bids': [
        ['95000.00', '1.5'],
        ['94999.00', '2.0'],
        ['94998.00', '1.8']
    ],
    'asks': [
        ['95001.00', '1.2'],
        ['95002.00', '1.5'],
        ['95003.00', '2.0']
    ]
}

# 模拟mark_price, funding_rate, spot_price
mock_mark_price = 95000.5
mock_funding_rate = 0.0001
mock_spot_price = 95000.0

print("=" * 60)
print("测试1: 验证数据结构")
print("=" * 60)
print(f"orderbook: {mock_orderbook}")
print(f"  - bids数量: {len(mock_orderbook.get('bids', []))}")
print(f"  - asks数量: {len(mock_orderbook.get('asks', []))}")
print(f"mark_price: {mock_mark_price}")
print(f"funding_rate: {mock_funding_rate}")
print(f"spot_price: {mock_spot_price}")

print("\n" + "=" * 60)
print("测试2: 验证L因子计算")
print("=" * 60)

try:
    from ats_core.factors_v2.liquidity import calculate_liquidity

    L_raw, L_meta = calculate_liquidity(mock_orderbook, {})
    L = (L_raw - 50) * 2  # 归一化

    print(f"✅ L因子计算成功:")
    print(f"  - 原始分数: {L_raw}/100")
    print(f"  - 归一化分数: {L}/100")
    print(f"  - 元数据: {L_meta}")
except Exception as e:
    print(f"❌ L因子计算失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("测试3: 验证B因子计算")
print("=" * 60)

try:
    from ats_core.factors_v2.basis_funding import calculate_basis_funding

    B, B_meta = calculate_basis_funding(
        perp_price=mock_mark_price,
        spot_price=mock_spot_price,
        funding_rate=mock_funding_rate,
        params={}
    )

    print(f"✅ B因子计算成功:")
    print(f"  - 分数: {B}/100")
    print(f"  - 元数据: {B_meta}")
except Exception as e:
    print(f"❌ B因子计算失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("测试4: 模拟缓存传递")
print("=" * 60)

# 模拟缓存字典
cache = {
    'orderbook_cache': {test_symbol: mock_orderbook},
    'mark_price_cache': {test_symbol: mock_mark_price},
    'funding_rate_cache': {test_symbol: mock_funding_rate},
    'spot_price_cache': {test_symbol: mock_spot_price}
}

# 模拟从缓存获取数据（这是batch_scan_optimized.py的逻辑）
orderbook = cache['orderbook_cache'].get(test_symbol)
mark_price = cache['mark_price_cache'].get(test_symbol)
funding_rate = cache['funding_rate_cache'].get(test_symbol)
spot_price = cache['spot_price_cache'].get(test_symbol)

print(f"从缓存获取的数据:")
print(f"  orderbook: {'存在' if orderbook else 'None'}")
if orderbook:
    print(f"    - bids: {len(orderbook.get('bids', []))}")
    print(f"    - asks: {len(orderbook.get('asks', []))}")
print(f"  mark_price: {mark_price}")
print(f"  funding_rate: {funding_rate}")
print(f"  spot_price: {spot_price}")

print("\n" + "=" * 60)
print("测试5: 验证None判断逻辑")
print("=" * 60)

# 测试_analyze_symbol_core中的判断逻辑
if orderbook is not None:
    print("✅ orderbook is not None - L因子将会计算")
else:
    print("❌ orderbook is None - L因子将返回0")

if mark_price is not None and spot_price is not None and funding_rate is not None:
    print("✅ mark_price/spot_price/funding_rate都存在 - B因子将会计算")
else:
    print("❌ 缺少B因子所需数据 - B因子将返回0")
    if mark_price is None:
        print("  - mark_price is None")
    if spot_price is None:
        print("  - spot_price is None")
    if funding_rate is None:
        print("  - funding_rate is None")
