#!/usr/bin/env python
# coding: utf-8
"""
测试L/B因子是否正常工作
"""
import sys

print("=" * 60)
print("测试analyze_symbol()是否正确获取L/B因子数据")
print("=" * 60)

try:
    from ats_core.pipeline.analyze_symbol import analyze_symbol

    # 测试BTCUSDT
    symbol = 'BTCUSDT'
    print(f"\n正在分析 {symbol}...")

    result = analyze_symbol(symbol)

    # 提取10维因子分数
    factors = result.get('factors', {})
    L = factors.get('L', 0)
    B = factors.get('B', 0)

    # 提取元数据
    meta = result.get('meta', {})
    L_meta = meta.get('L', {})
    B_meta = meta.get('B', {})

    print(f"\n✅ 分析完成")
    print(f"\nL因子（流动性）: {L:+.1f}/100")
    if L_meta:
        print(f"  元数据: {L_meta}")

    print(f"\nB因子（基差+资金费）: {B:+.1f}/100")
    if B_meta:
        print(f"  元数据: {B_meta}")

    # 判断是否成功
    if L == 0 and L_meta.get('note') == '无订单簿数据':
        print(f"\n❌ L因子失败：没有订单簿数据")
        sys.exit(1)
    elif L == 0 and 'error' in L_meta:
        print(f"\n❌ L因子失败：{L_meta['error']}")
        sys.exit(1)
    else:
        print(f"\n✅ L因子成功计算")

    if B == 0 and 'note' in B_meta:
        print(f"❌ B因子失败：{B_meta['note']}")
        sys.exit(1)
    elif B == 0 and 'error' in B_meta:
        print(f"❌ B因子失败：{B_meta['error']}")
        sys.exit(1)
    else:
        print(f"✅ B因子成功计算")

    print(f"\n{'=' * 60}")
    print(f"🎉 测试通过！L和B因子都成功计算")
    print(f"{'=' * 60}")

except Exception as e:
    print(f"\n❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
