#!/usr/bin/env python3
# coding: utf-8
"""
世界顶级优化方案 - 综合测试脚本

测试3个优化模块：
1. Sigmoid概率映射
2. Regime-Dependent Weights
3. 多时间框架协同
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.logging import log
import json


def test_single_symbol(symbol: str):
    """测试单个币种"""
    print("=" * 80)
    print(f"测试币种: {symbol}")
    print("=" * 80)

    try:
        # 调用分析函数（已集成所有优化）
        result = analyze_symbol(symbol)

        # 提取关键信息
        print(f"\n✅ 分析成功")
        print(f"   价格: {result['price']:.4f}")
        print(f"   方向: {result['side'].upper()}")
        print(f"   概率: {result['probability']:.1%}")
        print(f"   Prime: {'是' if result['publish']['prime'] else '否'}")

        # 显示7维分数
        print(f"\n📊 7维分数:")
        for dim in ['T', 'M', 'C', 'S', 'V', 'O', 'E']:
            score = result['scores'][dim]
            marker = "🟢" if score > 60 else "🔴" if score < -60 else "🟡"
            print(f"   {dim}: {score:+4d} {marker}")

        # 显示优化模块效果
        opt_meta = result.get('optimization_meta', {})
        if opt_meta:
            print(f"\n🚀 优化模块:")
            print(f"   概率方法: {opt_meta.get('probability_method', 'N/A')}")
            print(f"   温度参数: {opt_meta.get('temperature', 0):.2f}")
            print(f"   波动率: {opt_meta.get('volatility', 0):.3f}")
            print(f"   权重方法: {opt_meta.get('weights_method', 'N/A')}")
            print(f"   MTF一致性: {opt_meta.get('mtf_coherence', 0):.1f}%")

            # 显示权重变化
            base_w = opt_meta.get('base_weights', {})
            final_w = opt_meta.get('final_weights', {})
            if base_w and final_w:
                print(f"\n   权重调整:")
                for dim in ['T', 'M', 'C', 'V', 'O', 'F', 'S', 'E']:
                    base = base_w.get(dim, 0)
                    final = final_w.get(dim, 0)
                    change = final - base
                    if change != 0:
                        marker = "↑" if change > 0 else "↓"
                        print(f"     {dim}: {base:2d} → {final:2d} ({change:+2d}) {marker}")

        # 显示MTF详情
        mtf_result = opt_meta.get('mtf_result')
        if mtf_result:
            print(f"\n   MTF详情:")
            print(f"     一致性: {mtf_result['coherence_score']:.1f}%")
            print(f"     主导方向: {mtf_result['dominant_direction']}")
            print(f"     建议: {mtf_result['recommendation']}")

        return result

    except Exception as e:
        print(f"\n❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_module_standalone():
    """独立测试各个模块"""
    print("\n" + "=" * 80)
    print("📦 模块独立测试")
    print("=" * 80)

    # 测试1: Sigmoid概率映射
    print("\n1️⃣ 测试 Sigmoid概率映射")
    try:
        from ats_core.scoring.probability_v2 import map_probability_sigmoid
        p_long, p_short = map_probability_sigmoid(0.6, 0.5, 1.0, 3.0)
        print(f"   edge=0.6: P_long={p_long:.3f}, P_short={p_short:.3f} ✅")
    except Exception as e:
        print(f"   ❌ 失败: {e}")

    # 测试2: 自适应权重
    print("\n2️⃣ 测试 自适应权重")
    try:
        from ats_core.scoring.adaptive_weights import get_regime_weights
        weights = get_regime_weights(70, 0.015)
        print(f"   强势牛市权重: T={weights['T']}, C={weights['C']}, O={weights['O']} ✅")
    except Exception as e:
        print(f"   ❌ 失败: {e}")

    # 测试3: 多时间框架
    print("\n3️⃣ 测试 多时间框架协同")
    try:
        from ats_core.features.multi_timeframe import multi_timeframe_coherence
        result = multi_timeframe_coherence("BTCUSDT", verbose=False)
        print(f"   BTCUSDT一致性: {result['coherence_score']:.1f}% ✅")
    except Exception as e:
        print(f"   ❌ 失败: {e}")


def main():
    """主测试流程"""
    print("=" * 80)
    print("🌍 世界顶级优化方案 - 综合测试")
    print("=" * 80)

    # 独立测试各模块
    test_module_standalone()

    # 测试完整流程（集成测试）
    print("\n" + "=" * 80)
    print("🔗 集成测试")
    print("=" * 80)

    test_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    results = []
    for symbol in test_symbols:
        result = test_single_symbol(symbol)
        if result:
            results.append(result)
        print()  # 空行

    # 总结
    print("=" * 80)
    print("📊 测试总结")
    print("=" * 80)
    print(f"   测试币种数: {len(test_symbols)}")
    print(f"   成功数: {len(results)}")
    print(f"   失败数: {len(test_symbols) - len(results)}")

    if results:
        print(f"\n   优化效果:")
        avg_prob = sum(r['probability'] for r in results) / len(results)
        prime_count = sum(1 for r in results if r['publish']['prime'])
        print(f"     平均概率: {avg_prob:.1%}")
        print(f"     Prime数量: {prime_count}/{len(results)}")

        # MTF统计
        mtf_scores = [r['optimization_meta']['mtf_coherence'] for r in results
                      if 'optimization_meta' in r and 'mtf_coherence' in r['optimization_meta']]
        if mtf_scores:
            avg_mtf = sum(mtf_scores) / len(mtf_scores)
            print(f"     平均MTF一致性: {avg_mtf:.1f}%")

    print("\n" + "=" * 80)
    print("✅ 测试完成")
    print("=" * 80)


if __name__ == "__main__":
    main()
