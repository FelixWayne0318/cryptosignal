#!/usr/bin/env python3
"""
分析基础分析层的拒绝原因

读取 reports/latest/scan_detail.json
"""

import json
from collections import Counter

print("=" * 80)
print("🔬 基础分析层拒绝原因分析")
print("=" * 80)
print()

with open('reports/latest/scan_detail.json', 'r') as f:
    report = json.load(f)

symbols_data = report.get('symbols', [])
print(f"总信号数: {len(symbols_data)}")
print()

# 统计拒绝原因
rejection_counter = Counter()
confidence_values = []
edge_values = []
prime_strength_values = []

prime_count = 0
rejected_count = 0

for sig in symbols_data:
    symbol = sig.get('symbol')
    is_prime = sig.get('is_prime', False)
    rejection_reasons = sig.get('rejection_reason', [])

    confidence = sig.get('confidence', 0)
    edge = sig.get('edge', 0)
    prime_strength = sig.get('prime_strength', 0)

    confidence_values.append(confidence)
    edge_values.append(edge)
    prime_strength_values.append(prime_strength)

    if is_prime:
        prime_count += 1
    else:
        rejected_count += 1
        for reason in rejection_reasons:
            rejection_counter[reason] += 1

print(f"✅ Prime信号: {prime_count}")
print(f"❌ 被拒绝: {rejected_count}")
print()

# 显示拒绝原因Top 10
print("=" * 80)
print("❌ 拒绝原因统计 (Top 10)")
print("=" * 80)
print()

for reason, count in rejection_counter.most_common(10):
    percentage = count / rejected_count * 100
    print(f"{count:3d} ({percentage:5.1f}%) - {reason}")

print()

# 统计值分布
print("=" * 80)
print("📊 指标分布")
print("=" * 80)
print()

confidence_values.sort()
edge_values.sort()
prime_strength_values.sort()

n = len(confidence_values)

def get_percentiles(values):
    n = len(values)
    return {
        'min': values[0],
        'p25': values[int(n * 0.25)],
        'p50': values[int(n * 0.50)],
        'p75': values[int(n * 0.75)],
        'max': values[-1],
    }

conf_stats = get_percentiles(confidence_values)
edge_stats = get_percentiles(edge_values)
strength_stats = get_percentiles(prime_strength_values)

print(f"Confidence:")
print(f"  Min: {conf_stats['min']:.1f}")
print(f"  P25: {conf_stats['p25']:.1f}")
print(f"  中位: {conf_stats['p50']:.1f}")
print(f"  P75: {conf_stats['p75']:.1f}")
print(f"  Max: {conf_stats['max']:.1f}")
print(f"  ⚠️ >= 12的: {sum(1 for c in confidence_values if c >= 12)}/{n} ({sum(1 for c in confidence_values if c >= 12)/n*100:.1f}%)")
print()

print(f"Edge:")
print(f"  Min: {edge_stats['min']:.4f}")
print(f"  P25: {edge_stats['p25']:.4f}")
print(f"  中位: {edge_stats['p50']:.4f}")
print(f"  P75: {edge_stats['p75']:.4f}")
print(f"  Max: {edge_stats['max']:.4f}")
print(f"  ⚠️ >= 0.10的: {sum(1 for e in edge_values if e >= 0.10)}/{n} ({sum(1 for e in edge_values if e >= 0.10)/n*100:.1f}%)")
print()

print(f"Prime Strength:")
print(f"  Min: {strength_stats['min']:.1f}")
print(f"  P25: {strength_stats['p25']:.1f}")
print(f"  中位: {strength_stats['p50']:.1f}")
print(f"  P75: {strength_stats['p75']:.1f}")
print(f"  Max: {strength_stats['max']:.1f}")
print(f"  ⚠️ >= 35的: {sum(1 for s in prime_strength_values if s >= 35)}/{n} ({sum(1 for s in prime_strength_values if s >= 35)/n*100:.1f}%)")
print()

# 诊断结论
print("=" * 80)
print("🎯 诊断结论")
print("=" * 80)
print()

# 找出最大瓶颈
bottlenecks = []

conf_pass_rate = sum(1 for c in confidence_values if c >= 12) / n * 100
edge_pass_rate = sum(1 for e in edge_values if e >= 0.10) / n * 100
strength_pass_rate = sum(1 for s in prime_strength_values if s >= 35) / n * 100

if conf_pass_rate < 50:
    bottlenecks.append(('confidence', conf_pass_rate))
if edge_pass_rate < 50:
    bottlenecks.append(('edge', edge_pass_rate))
if strength_pass_rate < 50:
    bottlenecks.append(('prime_strength', strength_pass_rate))

if bottlenecks:
    bottlenecks.sort(key=lambda x: x[1])
    worst = bottlenecks[0]

    print(f"❌ **最大瓶颈**: {worst[0]} (通过率: {worst[1]:.1f}%)")
    print()

    if worst[0] == 'confidence':
        print("📋 诊断：Confidence太低")
        print()
        print(f"数据:")
        print(f"  - Confidence中位: {conf_stats['p50']:.1f}")
        print(f"  - Confidence Max: {conf_stats['max']:.1f}")
        print(f"  - 当前阈值: 12")
        print()
        print("问题根源:")
        print("  ⚠️ 当前市场信号质量普遍较低")
        print("  ⚠️ Confidence由10因子综合计算，大部分币种得分低")
        print()
        print("修复方案:")
        print("  方案A: 降低confidence_min到8")
        print(f"    - 预计通过率: {sum(1 for c in confidence_values if c >= 8)/n*100:.1f}%")
        print()
        print("  方案B: 降低到5（激进）")
        print(f"    - 预计通过率: {sum(1 for c in confidence_values if c >= 5)/n*100:.1f}%")
        print()
        print("  方案C: 等待更好的市场机会")
        print("    - 当前市场整体信号质量低")
        print("    - 不建议强行放宽到过低水平")

    elif worst[0] == 'edge':
        print("📋 诊断：Edge太低")
        print()
        print(f"数据:")
        print(f"  - Edge中位: {edge_stats['p50']:.4f}")
        print(f"  - Edge P75: {edge_stats['p75']:.4f}")
        print(f"  - 当前阈值: 0.10")
        print()
        print("修复方案:")
        print("  降低edge_min到0.05")
        print(f"    - 预计通过率: {sum(1 for e in edge_values if e >= 0.05)/n*100:.1f}%")

    elif worst[0] == 'prime_strength':
        print("📋 诊断：Prime Strength太低")
        print()
        print(f"数据:")
        print(f"  - Prime Strength中位: {strength_stats['p50']:.1f}")
        print(f"  - 当前阈值: 35")
        print()
        print("修复方案:")
        print("  降低prime_strength_min到30")
        print(f"    - 预计通过率: {sum(1 for s in prime_strength_values if s >= 30)/n*100:.1f}%")

else:
    print("✅ 所有指标通过率都 >= 50%，不是单一瓶颈问题")
    print()
    print("可能是多个条件组合导致的")

print()
print("=" * 80)
