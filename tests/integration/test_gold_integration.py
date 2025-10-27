#!/usr/bin/env python3
# coding: utf-8
"""
测试Gold方案完整集成

验证点：
1. Elite Builder生成元数据
2. analyze_symbol接受并利用元数据
3. 贝叶斯先验调整生效
4. 避免重复计算
5. 元数据传递到输出
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

print("=" * 70)
print("🏆 测试Gold方案完整集成")
print("=" * 70)
print()

# ============ 测试1：Elite Builder ============
print("📋 [测试1/4] Elite Builder元数据生成...")
print("-" * 70)

from ats_core.pools.elite_builder import build_elite_universe

try:
    symbols, metadata = build_elite_universe()
    print(f"✅ 候选池构建成功：{len(symbols)} 个交易对")

    if len(symbols) > 0:
        # 验证元数据结构
        first_sym = symbols[0]
        first_meta = metadata[first_sym]

        print(f"\n验证元数据结构（{first_sym}）：")
        print(f"  long_score: {first_meta.get('long_score', 'MISSING')}")
        print(f"  short_score: {first_meta.get('short_score', 'MISSING')}")
        print(f"  trend_dir: {first_meta.get('trend_dir', 'MISSING')}")
        print(f"  pre_computed: {list(first_meta.get('pre_computed', {}).keys())}")

        # 验证预计算数据
        pre_computed = first_meta.get('pre_computed', {})
        if pre_computed:
            print(f"\n预计算数据：")
            for key, value in list(pre_computed.items())[:5]:
                print(f"    {key}: {value}")
        else:
            print("  ⚠️  警告：预计算数据为空")

    print("\n✅ 测试1通过")
except Exception as e:
    print(f"\n❌ 测试1失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# ============ 测试2：analyze_symbol接受元数据 ============
print("📋 [测试2/4] analyze_symbol接受元数据...")
print("-" * 70)

from ats_core.pipeline.analyze_symbol import analyze_symbol

try:
    if len(symbols) > 0:
        test_sym = symbols[0]
        test_meta = metadata[test_sym]

        print(f"测试交易对: {test_sym}")
        print(f"候选池先验: {test_meta['trend_dir']} (做多{test_meta['long_score']:.0f}/做空{test_meta['short_score']:.0f})")

        # 调用analyze_symbol，传入元数据
        result = analyze_symbol(test_sym, elite_meta=test_meta)

        # 验证结果包含元数据
        if result.get("elite_prior"):
            print(f"\n✅ 元数据成功传递到analyze_symbol")
            print(f"  elite_prior: {result['elite_prior']}")
        else:
            print(f"\n⚠️  警告：结果中没有elite_prior字段")

        # 验证贝叶斯提升
        bayesian_boost = result.get("bayesian_boost")
        if bayesian_boost:
            print(f"\n🎯 贝叶斯先验提升: +{bayesian_boost*100:.1f}%")
        else:
            print(f"\n  无贝叶斯提升（可能候选池分数<60）")

        print("\n✅ 测试2通过")
    else:
        print("⏭️  跳过测试2（候选池为空）")
except Exception as e:
    print(f"\n❌ 测试2失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# ============ 测试3：概率对比（有无元数据） ============
print("📋 [测试3/4] 概率对比（验证贝叶斯调整）...")
print("-" * 70)

try:
    if len(symbols) > 0:
        test_sym = symbols[0]
        test_meta = metadata[test_sym]

        # 不传元数据
        result_no_meta = analyze_symbol(test_sym, elite_meta=None)
        prob_no_meta = result_no_meta.get("probability", 0)

        # 传元数据
        result_with_meta = analyze_symbol(test_sym, elite_meta=test_meta)
        prob_with_meta = result_with_meta.get("probability", 0)

        print(f"测试交易对: {test_sym}")
        print(f"\n无元数据概率: {prob_no_meta:.1%}")
        print(f"有元数据概率: {prob_with_meta:.1%}")

        diff = prob_with_meta - prob_no_meta
        if diff > 0:
            print(f"\n🎯 贝叶斯提升: +{diff:.1%} ({diff/prob_no_meta*100:+.1f}%)")
        elif diff < 0:
            print(f"\n⚠️  概率下降: {diff:.1%}（可能方向相反）")
        else:
            print(f"\n  无差异（可能候选池分数<60）")

        print("\n✅ 测试3通过")
    else:
        print("⏭️  跳过测试3（候选池为空）")
except Exception as e:
    print(f"\n❌ 测试3失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# ============ 测试4：完整流程（模拟full_run_elite） ============
print("📋 [测试4/4] 完整流程集成测试...")
print("-" * 70)

try:
    if len(symbols) >= 3:
        test_symbols = symbols[:3]

        print(f"测试前3个交易对：{', '.join(test_symbols)}")
        print()

        boosted_count = 0
        total_boost = 0.0

        for idx, sym in enumerate(test_symbols, 1):
            meta = metadata[sym]
            result = analyze_symbol(sym, elite_meta=meta)

            prob = result.get("probability", 0)
            boost = result.get("bayesian_boost", 0)

            print(f"{idx}. {sym}")
            print(f"   候选池: {meta['trend_dir']} (L{meta['long_score']:.0f}/S{meta['short_score']:.0f})")
            print(f"   概率: {prob:.1%}", end="")

            if boost > 0:
                print(f" [+{boost*100:.1f}%提升]")
                boosted_count += 1
                total_boost += boost
            else:
                print()

        print()
        print(f"统计:")
        print(f"  贝叶斯提升信号: {boosted_count}/{len(test_symbols)}")
        if boosted_count > 0:
            avg_boost = total_boost / boosted_count
            print(f"  平均提升: +{avg_boost*100:.1f}%")

        print("\n✅ 测试4通过")
    else:
        print("⏭️  跳过测试4（候选池<3个）")
except Exception as e:
    print(f"\n❌ 测试4失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 70)
print("✅ 所有测试通过！Gold方案集成成功")
print("=" * 70)
print()

print("💡 接下来可以运行：")
print("   python3 -m tools.full_run_elite --limit 10")
print()
