#!/usr/bin/env python3
# coding: utf-8
"""
测试Elite Universe Builder（世界顶级候选池构建器）
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from ats_core.pools.elite_builder import build_elite_universe

print("=" * 70)
print("🏆 测试Elite Universe Builder")
print("=" * 70)
print()

# 构建候选池
symbols, metadata = build_elite_universe()

print()
print("=" * 70)
print("📊 候选池详细信息")
print("=" * 70)
print()

if len(symbols) == 0:
    print("⚠️  候选池为空")
    sys.exit(0)

# 显示前20个交易对的详细信息
print(f"{'排名':<6}{'交易对':<15}{'方向':<8}{'做多分':<10}{'做空分':<10}{'异常分':<10}{'流动性':<10}")
print("-" * 70)

for idx, sym in enumerate(symbols[:20], 1):
    meta = metadata[sym]
    print(f"{idx:<6}{sym:<15}{meta['trend_dir']:<8}{meta['long_score']:<10.0f}{meta['short_score']:<10.0f}{meta['anomaly_score']:<10.0f}{meta['liquidity_score']:<10.0f}")

print()
print("=" * 70)
print("📈 统计分析")
print("=" * 70)
print()

# 统计分析
longs = [s for s in symbols if metadata[s]["trend_dir"] == "LONG"]
shorts = [s for s in symbols if metadata[s]["trend_dir"] == "SHORT"]

print(f"总候选数: {len(symbols)}")
print(f"  做多机会: {len(longs)} ({len(longs)/len(symbols)*100:.1f}%)")
print(f"  做空机会: {len(shorts)} ({len(shorts)/len(symbols)*100:.1f}%)")
print()

# 平均分数
avg_long = sum(metadata[s]["long_score"] for s in symbols) / len(symbols)
avg_short = sum(metadata[s]["short_score"] for s in symbols) / len(symbols)
avg_anomaly = sum(metadata[s]["anomaly_score"] for s in symbols) / len(symbols)

print(f"平均分数:")
print(f"  做多分: {avg_long:.1f}")
print(f"  做空分: {avg_short:.1f}")
print(f"  异常分: {avg_anomaly:.1f}")
print()

# 分数分布
print("做多分数分布:")
long_80_plus = sum(1 for s in symbols if metadata[s]["long_score"] >= 80)
long_60_80 = sum(1 for s in symbols if 60 <= metadata[s]["long_score"] < 80)
long_below_60 = sum(1 for s in symbols if metadata[s]["long_score"] < 60)

print(f"  ≥80分: {long_80_plus} ({long_80_plus/len(symbols)*100:.1f}%)")
print(f"  60-80分: {long_60_80} ({long_60_80/len(symbols)*100:.1f}%)")
print(f"  <60分: {long_below_60} ({long_below_60/len(symbols)*100:.1f}%)")
print()

print("做空分数分布:")
short_80_plus = sum(1 for s in symbols if metadata[s]["short_score"] >= 80)
short_60_80 = sum(1 for s in symbols if 60 <= metadata[s]["short_score"] < 80)
short_below_60 = sum(1 for s in symbols if metadata[s]["short_score"] < 60)

print(f"  ≥80分: {short_80_plus} ({short_80_plus/len(symbols)*100:.1f}%)")
print(f"  60-80分: {short_60_80} ({short_60_80/len(symbols)*100:.1f}%)")
print(f"  <60分: {short_below_60} ({short_below_60/len(symbols)*100:.1f}%)")
print()

# 异常维度分析
print("=" * 70)
print("🔍 异常维度分析（前10个交易对）")
print("=" * 70)
print()

for idx, sym in enumerate(symbols[:10], 1):
    meta = metadata[sym]
    details = meta.get("anomaly_details", {})

    print(f"{idx}. {sym} (异常分={meta['anomaly_score']:.0f})")

    # 找出最强的3个异常维度
    sorted_dims = sorted(details.items(), key=lambda x: x[1], reverse=True)[:3]
    for dim_name, dim_score in sorted_dims:
        print(f"   • {dim_name}: {dim_score:.0f}")
    print()

print("=" * 70)
print("✅ 测试完成")
print("=" * 70)
