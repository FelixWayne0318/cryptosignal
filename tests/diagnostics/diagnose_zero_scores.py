#!/usr/bin/env python3
"""诊断M和C维度为0的问题"""
import sys
import os
sys.path.insert(0, '/home/user/cryptosignal')

from ats_core.pipeline.analyze_symbol import analyze_symbol

# 分析COAIUSDT
result = analyze_symbol("COAIUSDT")

print("="*60)
print("COAIUSDT 详细分析")
print("="*60)

# 基本信息
print(f"\nside: {result.get('side')}")
print(f"side_long: {result.get('side_long')}")
print(f"probability: {result.get('probability'):.1%}")

# 分数
scores = result.get('scores', {})
print(f"\n7维度分数:")
for dim in ['T', 'M', 'C', 'S', 'V', 'O', 'E']:
    print(f"  {dim}: {scores.get(dim, 'N/A')}")

# M维度元数据
print(f"\nM（动量）元数据:")
M_meta = result.get('scores_meta', {}).get('M', {})
for key, val in M_meta.items():
    print(f"  {key}: {val}")

# C维度元数据
print(f"\nC（资金流）元数据:")
C_meta = result.get('scores_meta', {}).get('C', {})
for key, val in C_meta.items():
    print(f"  {key}: {val}")

# F维度元数据
print(f"\nF（资金领先）元数据:")
F_meta = result.get('scores_meta', {}).get('F', {})
for key, val in F_meta.items():
    print(f"  {key}: {val}")

# 分析问题
print(f"\n问题分析:")
print(f"="*60)

if scores.get('M') == 0:
    print(f"⚠️  M=0，可能原因：")
    slope_norm = M_meta.get('slope_normalized', 0)
    accel_norm = M_meta.get('accel_normalized', 0)
    print(f"   slope_normalized={slope_norm:.6f}")
    print(f"   accel_normalized={accel_norm:.6f}")
    print(f"   如果这些值是负数（下跌），做多时会得0分")

if scores.get('C') == 0:
    print(f"⚠️  C=0，可能原因：")
    cvd6 = C_meta.get('cvd6', 0)
    print(f"   cvd6={cvd6:.6f}")
    print(f"   如果CVD是负数（卖压），做多时会得0分")

print(f"\nF分数很高（{result.get('F_score')}）说明资金面强，但M/C为0矛盾！")
print(f"这表明directional_score的scale参数设置有问题。")
