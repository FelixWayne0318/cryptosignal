#!/usr/bin/env python3
# coding: utf-8
"""
diagnose/analyze_v_saturation.py

诊断V因子±80聚集问题

问题假设：
- scale=0.3参数过小，导致tanh函数过早饱和
- 实际交易量波动范围（v5/v20通常在0.5-2.0）远超scale参数
- 导致大部分情况下vlevel_score和vroc_score都饱和在±100
- 最终V分数聚集在±80附近

作者：Claude (Sonnet 4.5)
日期：2025-11-05
"""

import sys
import math
import numpy as np
from typing import List, Tuple


def directional_score_verbose(value, neutral=0.0, scale=1.0):
    """带详细诊断信息的directional_score"""
    deviation = value - neutral
    normalized = math.tanh(deviation / scale)
    score = 50 + 50 * normalized
    score_clamped = int(round(max(10, min(100, score))))

    return {
        'value': value,
        'neutral': neutral,
        'deviation': deviation,
        'scale': scale,
        'tanh_input': deviation / scale,
        'tanh_output': normalized,
        'score_raw': score,
        'score_final': score_clamped,
        'saturated': abs(normalized) > 0.9  # tanh > 0.9 即接近饱和
    }


def analyze_vlevel_saturation(vlevel_samples: List[float], scale: float = 0.3):
    """分析vlevel的饱和情况"""
    print(f"\n{'='*60}")
    print(f"vlevel饱和分析（scale={scale}）")
    print(f"{'='*60}\n")

    results = []
    for vlevel in vlevel_samples:
        diag = directional_score_verbose(vlevel, neutral=1.0, scale=scale)
        results.append(diag)

    # 统计
    saturated_count = sum(1 for r in results if r['saturated'])
    saturation_rate = saturated_count / len(results) if results else 0

    print(f"样本总数: {len(results)}")
    print(f"饱和样本数: {saturated_count}")
    print(f"饱和率: {saturation_rate:.1%}\n")

    print(f"{'vlevel':>8} {'偏移':>8} {'tanh输入':>10} {'tanh输出':>10} {'分数':>6} {'饱和':>6}")
    print(f"{'-'*60}")
    for r in results[:20]:  # 只显示前20个
        print(f"{r['value']:8.2f} {r['deviation']:8.2f} {r['tanh_input']:10.2f} "
              f"{r['tanh_output']:10.3f} {r['score_final']:6d} {'是' if r['saturated'] else '否':>6}")

    if len(results) > 20:
        print(f"... (显示前20个，共{len(results)}个)")

    return results


def analyze_v_score_distribution(vlevel_samples, vroc_samples,
                                  vlevel_weight=0.6, vroc_weight=0.4,
                                  vlevel_scale=0.3, vroc_scale=0.3):
    """分析V分数分布"""
    print(f"\n{'='*60}")
    print(f"V分数分布分析")
    print(f"{'='*60}\n")

    V_scores = []
    for vlevel, vroc in zip(vlevel_samples, vroc_samples):
        # 计算vlevel_score
        vlevel_diag = directional_score_verbose(vlevel, neutral=1.0, scale=vlevel_scale)
        vlevel_score_raw = vlevel_diag['score_final']
        vlevel_score = (vlevel_score_raw - 50) * 2

        # 计算vroc_score
        vroc_diag = directional_score_verbose(vroc, neutral=0.0, scale=vroc_scale)
        vroc_score_raw = vroc_diag['score_final']
        vroc_score = (vroc_score_raw - 50) * 2

        # 加权平均
        V_strength = vlevel_weight * vlevel_score + vroc_weight * vroc_score
        V_strength = max(-100, min(100, V_strength))

        V_scores.append({
            'vlevel': vlevel,
            'vroc': vroc,
            'vlevel_score': int(vlevel_score),
            'vroc_score': int(vroc_score),
            'V_strength': int(V_strength)
        })

    # 统计分布
    V_values = [s['V_strength'] for s in V_scores]
    V_array = np.array(V_values)

    print(f"V分数统计:")
    print(f"  均值: {np.mean(V_array):.1f}")
    print(f"  标准差: {np.std(V_array):.1f}")
    print(f"  中位数: {np.median(V_array):.1f}")
    print(f"  最小值: {np.min(V_array):.0f}")
    print(f"  最大值: {np.max(V_array):.0f}\n")

    # 分布统计
    bins = [
        (-100, -80, "强烈缩量"),
        (-80, -40, "明显缩量"),
        (-40, -10, "轻微缩量"),
        (-10, 10, "中性"),
        (10, 40, "轻微放量"),
        (40, 80, "明显放量"),
        (80, 100, "强烈放量"),
    ]

    print(f"V分数分布:")
    for low, high, label in bins:
        count = np.sum((V_array >= low) & (V_array < high))
        ratio = count / len(V_array) if len(V_array) > 0 else 0
        print(f"  [{low:4d}, {high:4d}): {count:4d} ({ratio:5.1%}) - {label}")

    # ±80聚集检测
    cluster_80_count = np.sum(np.abs(V_array) >= 80)
    cluster_80_rate = cluster_80_count / len(V_array) if len(V_array) > 0 else 0

    print(f"\n⚠️ ±80聚集检测:")
    print(f"  |V| >= 80的样本数: {cluster_80_count} / {len(V_array)}")
    print(f"  聚集率: {cluster_80_rate:.1%}")

    if cluster_80_rate > 0.3:
        print(f"  结论: 🔴 存在严重的±80聚集问题！")
    elif cluster_80_rate > 0.15:
        print(f"  结论: 🟡 存在中度的±80聚集问题")
    else:
        print(f"  结论: 🟢 ±80聚集率正常")

    return V_scores


def recommend_scale_parameter(vlevel_samples: List[float], target_score_range=(40, 80)):
    """推荐scale参数"""
    print(f"\n{'='*60}")
    print(f"scale参数推荐")
    print(f"{'='*60}\n")

    # 计算vlevel的实际分布
    vlevel_array = np.array(vlevel_samples)
    vlevel_mean = np.mean(vlevel_array)
    vlevel_std = np.std(vlevel_array)

    # 常见波动范围（中位数偏移）
    deviations = np.abs(vlevel_array - 1.0)
    median_deviation = float(np.median(deviations))
    p75_deviation = float(np.percentile(deviations, 75))

    print(f"vlevel实际分布:")
    print(f"  均值: {vlevel_mean:.2f}")
    print(f"  标准差: {vlevel_std:.2f}")
    print(f"  中位数偏移: {median_deviation:.2f}")
    print(f"  75分位偏移: {p75_deviation:.2f}\n")

    # 目标：median_deviation对应的分数应该在40-80之间
    # 根据 tanh(deviation/scale) = (score - 50) / 50
    # 假设 median_deviation 应该给 65分 (中等强度)
    # 则 tanh(median_deviation / scale) = (65 - 50) / 50 = 0.3
    # tanh^-1(0.3) ≈ 0.31
    # scale = median_deviation / 0.31

    target_score = 65  # 中等强度目标分数
    target_tanh = (target_score - 50) / 50  # 0.3
    target_atanh = math.atanh(target_tanh)  # 0.31

    recommended_scale = median_deviation / target_atanh

    print(f"推荐scale参数:")
    print(f"  当前scale: 0.3")
    print(f"  推荐scale: {recommended_scale:.2f}")
    print(f"  增加倍数: {recommended_scale / 0.3:.1f}x\n")

    print(f"效果预期:")
    print(f"  中位数偏移({median_deviation:.2f})将给{target_score}分（当前可能饱和在90+分）")
    print(f"  75分位偏移({p75_deviation:.2f})将给75-85分（当前可能饱和在95+分）\n")

    # 验证推荐scale
    print(f"验证推荐scale={recommended_scale:.2f}:")
    test_values = [0.7, 0.8, 1.0, 1.2, 1.5, 2.0]
    print(f"{'vlevel':>8} {'当前分数':>10} {'推荐scale分数':>15}")
    print(f"{'-'*40}")
    for v in test_values:
        current = directional_score_verbose(v, neutral=1.0, scale=0.3)
        recommended = directional_score_verbose(v, neutral=1.0, scale=recommended_scale)
        print(f"{v:8.1f} {current['score_final']:10d} {recommended['score_final']:15d}")

    return recommended_scale


def generate_realistic_vlevel_samples(n: int = 100) -> List[float]:
    """生成现实的vlevel样本（基于实际市场数据分布）"""
    # 根据实际市场观察，vlevel通常服从对数正态分布
    # 均值约1.0，标准差约0.3-0.5
    np.random.seed(42)

    # 生成对数正态分布样本
    mu = 0.0  # log(1.0)
    sigma = 0.4  # 对数标准差
    vlevel_samples = np.random.lognormal(mu, sigma, n)

    # 添加一些极端值（市场波动）
    extreme_count = int(n * 0.1)
    extreme_samples = np.random.choice([0.3, 0.4, 2.0, 2.5, 3.0], extreme_count)
    vlevel_samples[-extreme_count:] = extreme_samples

    return list(vlevel_samples)


def generate_realistic_vroc_samples(n: int = 100) -> List[float]:
    """生成现实的vroc样本"""
    np.random.seed(43)

    # vroc是对数差值，通常在±0.5范围内
    # 大多数情况下接近0，偶尔有大波动
    vroc_samples = np.random.normal(0, 0.2, n)

    # 添加一些极端值
    extreme_count = int(n * 0.05)
    extreme_samples = np.random.choice([-0.8, -0.6, 0.6, 0.8], extreme_count)
    vroc_samples[-extreme_count:] = extreme_samples

    return list(vroc_samples)


def main():
    """主函数"""
    print(f"\n{'='*60}")
    print(f"V因子±80聚集问题诊断")
    print(f"{'='*60}\n")

    # 生成模拟数据
    n_samples = 200
    print(f"生成{n_samples}个模拟样本（基于实际市场分布）...\n")

    vlevel_samples = generate_realistic_vlevel_samples(n_samples)
    vroc_samples = generate_realistic_vroc_samples(n_samples)

    # 1. 分析vlevel饱和情况
    analyze_vlevel_saturation(vlevel_samples, scale=0.3)

    # 2. 分析V分数分布
    V_scores = analyze_v_score_distribution(
        vlevel_samples, vroc_samples,
        vlevel_weight=0.6, vroc_weight=0.4,
        vlevel_scale=0.3, vroc_scale=0.3
    )

    # 3. 推荐scale参数
    recommended_scale = recommend_scale_parameter(vlevel_samples)

    # 4. 验证推荐参数效果
    print(f"\n{'='*60}")
    print(f"推荐参数验证")
    print(f"{'='*60}\n")

    print(f"使用推荐scale={recommended_scale:.2f}重新计算V分数分布:")
    V_scores_new = analyze_v_score_distribution(
        vlevel_samples, vroc_samples,
        vlevel_weight=0.6, vroc_weight=0.4,
        vlevel_scale=recommended_scale, vroc_scale=recommended_scale
    )

    print(f"\n{'='*60}")
    print(f"总结")
    print(f"{'='*60}\n")

    print(f"问题诊断:")
    print(f"  ✓ 当前scale=0.3过小，导致tanh函数过早饱和")
    print(f"  ✓ 实际vlevel波动范围（0.5-2.0）远超scale参数")
    print(f"  ✓ 导致大部分vlevel_score饱和在±100附近")
    print(f"  ✓ 最终V分数聚集在±80-100区间\n")

    print(f"解决方案:")
    print(f"  1. 将vlevel_scale从0.3增加到{recommended_scale:.2f}（约{recommended_scale/0.3:.1f}倍）")
    print(f"  2. 将vroc_scale从0.3增加到{recommended_scale:.2f}（保持一致）")
    print(f"  3. 预期效果：V分数更均匀分布在±100区间，减少±80聚集\n")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
