#!/usr/bin/env python3
"""
快速配置验证脚本 - 确认阈值是否正确加载

用法:
    python3 scripts/verify_config.py
"""

import os
import sys
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from ats_core.config.threshold_config import ThresholdConfig

print("=" * 80)
print("🔍 配置验证工具")
print("=" * 80)
print()

# 1. 检查配置文件
print("📋 1. 检查配置文件内容")
print("-" * 80)

with open('config/signal_thresholds.json', 'r') as f:
    config_file = json.load(f)

mature = config_file['基础分析阈值']['mature_coin']
gates = config_file['v72闸门阈值']

print(f"基础阈值 (mature_coin):")
print(f"  confidence_min: {mature['confidence_min']}")
print(f"  edge_min: {mature['edge_min']}")
print(f"  prime_prob_min: {mature['prime_prob_min']}")
print(f"  prime_strength_min: {mature['prime_strength_min']}")
print()

print(f"Gate阈值:")
print(f"  Gate2 F_min: {gates['gate2_fund_support']['F_min']}")
print(f"  Gate4 P_min: {gates['gate4_probability']['P_min']}")
print(f"  Gate5 I_min: {gates['gate5_independence_market']['I_min']}")
print()

# 2. 检查ThresholdConfig加载
print("📋 2. 检查ThresholdConfig加载")
print("-" * 80)

config = ThresholdConfig()
mature_loaded = config.get_mature_thresholds()
gate2_F_min = config.get_gate_threshold('gate2_fund_support', 'F_min', -50)
gate4_P_min = config.get_gate_threshold('gate4_probability', 'P_min', 0.45)
gate5_I_min = config.get_gate_threshold('gate5_independence_market', 'I_min', 30)

print(f"加载的阈值:")
print(f"  confidence_min: {mature_loaded.get('confidence_min', '未找到')}")
print(f"  edge_min: {mature_loaded.get('edge_min', '未找到')}")
print(f"  Gate2 F_min: {gate2_F_min}")
print(f"  Gate4 P_min: {gate4_P_min}")
print(f"  Gate5 I_min: {gate5_I_min}")
print()

# 3. 检查扫描器min_score
print("📋 3. 检查扫描器min_score")
print("-" * 80)

with open('scripts/realtime_signal_scanner.py', 'r') as f:
    scanner_code = f.read()

import re
match = re.search(r'min_score:\s*int\s*=\s*(\d+)', scanner_code)
if match:
    min_score = int(match.group(1))
    print(f"扫描器min_score: {min_score}")
else:
    print("❌ 未找到min_score定义")
print()

# 4. 验证结果
print("=" * 80)
print("✅ 验证结果")
print("=" * 80)
print()

issues = []

# 检查是否正确修改
if mature['confidence_min'] != 12:
    issues.append(f"❌ confidence_min应该是12，实际是{mature['confidence_min']}")
else:
    print(f"✅ confidence_min = 12")

if mature['edge_min'] != 0.10:
    issues.append(f"❌ edge_min应该是0.10，实际是{mature['edge_min']}")
else:
    print(f"✅ edge_min = 0.10")

if gates['gate2_fund_support']['F_min'] != -50:
    issues.append(f"❌ F_min应该是-50，实际是{gates['gate2_fund_support']['F_min']}")
else:
    print(f"✅ Gate2 F_min = -50")

if gates['gate4_probability']['P_min'] != 0.40:
    issues.append(f"❌ P_min应该是0.40，实际是{gates['gate4_probability']['P_min']}")
else:
    print(f"✅ Gate4 P_min = 0.40")

if gates['gate5_independence_market']['I_min'] != 0:
    issues.append(f"❌ I_min应该是0，实际是{gates['gate5_independence_market']['I_min']}")
else:
    print(f"✅ Gate5 I_min = 0")

if match and min_score != 12:
    issues.append(f"❌ 扫描器min_score应该是12，实际是{min_score}")
else:
    print(f"✅ 扫描器min_score = 12")

print()

if issues:
    print("⚠️ 发现问题:")
    for issue in issues:
        print(f"  {issue}")
    print()
    print("请运行: git pull origin claude/system-refactor-v7.2-011CUyBts14z3AdVhv9BSubr")
else:
    print("✅ 所有配置正确！")
    print()
    print("配置正确但仍然0个信号，可能原因:")
    print("  1. F因子分布：大部分币种F < -50（被Gate2拒绝）")
    print("  2. I因子分布：大部分币种I < 0（被Gate5拒绝）")
    print("  3. 多个Gate组合效应（每个Gate都拒绝一部分）")
    print()
    print("建议运行深度诊断:")
    print("  python3 scripts/deep_gate_diagnosis.py")
    print()
    print("或者尝试进一步放宽:")
    print("  - 将I_min从0降到-20（允许更多跟随市场的币种）")
    print("  - 但保持market_regime检查（逆势保护）")

print()
print("=" * 80)
