#!/usr/bin/env python3
"""
分析扫描报告中的Gate拒绝原因

直接读取 reports/latest/scan_detail.json 分析

用法:
    python3 scripts/analyze_scan_report.py
"""

import json
import os
from collections import defaultdict

print("=" * 80)
print("🔬 扫描报告分析工具")
print("=" * 80)
print()

# 读取最新的扫描报告
report_path = "reports/latest/scan_detail.json"

if not os.path.exists(report_path):
    print(f"❌ 报告文件不存在: {report_path}")
    print("请先运行扫描器生成报告")
    exit(1)

with open(report_path, 'r') as f:
    report = json.load(f)

signals = report.get('signals', [])

if not signals:
    print("❌ 报告中没有信号数据")
    exit(1)

print(f"📊 分析 {len(signals)} 个信号")
print()

# 统计gate通过情况
gate_stats = {
    'data_quality': {'pass': 0, 'fail': 0},
    'fund_support': {'pass': 0, 'fail': 0},
    'ev': {'pass': 0, 'fail': 0},
    'probability': {'pass': 0, 'fail': 0},
    'independence_market': {'pass': 0, 'fail': 0},
    'all_gates': {'pass': 0, 'fail': 0},
}

# 统计拒绝原因
rejection_reasons = defaultdict(list)
confidence_values = []

for signal in signals:
    symbol = signal.get('symbol', 'UNKNOWN')

    # 提取v72增强数据
    v72 = signal.get('v72_enhancements', {})
    if not v72:
        continue

    # 提取gate信息
    gates = v72.get('gates', {})

    gate1 = gates.get('gates_data_quality', 0)
    gate2 = gates.get('gates_fund_support', 0)
    gate3 = gates.get('gates_ev', 0)
    gate4 = gates.get('gates_probability', 0)
    gate5 = gates.get('gates_independence_market', 0)
    all_pass = gates.get('pass_all', False)

    # 提取指标
    F_v2 = v72.get('F_v2', 0)
    I_v2 = v72.get('I_v2', 0)
    P_calibrated = v72.get('P_calibrated', 0)
    EV_net = v72.get('EV_net', 0)
    confidence = v72.get('confidence_v72', 0)
    side = signal.get('side', 'unknown')

    confidence_values.append(confidence)

    # 统计gate
    if gate1 > 0:
        gate_stats['data_quality']['pass'] += 1
    else:
        gate_stats['data_quality']['fail'] += 1
        rejection_reasons['gate1'].append(f"{symbol}")

    if gate2 > 0:
        gate_stats['fund_support']['pass'] += 1
    else:
        gate_stats['fund_support']['fail'] += 1
        rejection_reasons['gate2'].append(f"{symbol}: F={F_v2:.0f}")

    if gate3 > 0:
        gate_stats['ev']['pass'] += 1
    else:
        gate_stats['ev']['fail'] += 1
        rejection_reasons['gate3'].append(f"{symbol}: EV={EV_net:.3f}")

    if gate4 > 0:
        gate_stats['probability']['pass'] += 1
    else:
        gate_stats['probability']['fail'] += 1
        rejection_reasons['gate4'].append(f"{symbol}: P={P_calibrated:.3f}")

    if gate5 > 0:
        gate_stats['independence_market']['pass'] += 1
    else:
        gate_stats['independence_market']['fail'] += 1
        rejection_reasons['gate5'].append(f"{symbol}: I={I_v2:.0f}, side={side}")

    if all_pass:
        gate_stats['all_gates']['pass'] += 1
    else:
        gate_stats['all_gates']['fail'] += 1

# 输出统计
print("=" * 80)
print("📊 Gate通过率统计")
print("=" * 80)
print()

total = len(signals)

for gate_name, stats in gate_stats.items():
    pass_count = stats['pass']
    fail_count = stats['fail']

    if pass_count + fail_count > 0:
        pass_rate = pass_count / total * 100

        status = "✅" if pass_rate > 80 else "⚠️" if pass_rate > 50 else "❌"

        print(f"{status} {gate_name:25s}: {pass_count:3d}/{total:3d} 通过 ({pass_rate:5.1f}%)")

print()

# 显示失败示例
print("=" * 80)
print("❌ 失败示例（前3个）")
print("=" * 80)
print()

for gate, examples in rejection_reasons.items():
    if examples:
        print(f"{gate}:")
        for example in examples[:3]:
            print(f"  - {example}")
        if len(examples) > 3:
            print(f"  - ... 还有 {len(examples)-3} 个")
        print()

# Confidence分析
print("=" * 80)
print("🎯 Confidence分析")
print("=" * 80)
print()

if confidence_values:
    confidence_values.sort()
    n = len(confidence_values)

    min_conf = confidence_values[0]
    max_conf = confidence_values[-1]
    p25 = confidence_values[int(n * 0.25)]
    p50 = confidence_values[int(n * 0.50)]
    p75 = confidence_values[int(n * 0.75)]

    print(f"Confidence分布:")
    print(f"  Min: {min_conf:.1f}")
    print(f"  P25: {p25:.1f}")
    print(f"  中位: {p50:.1f}")
    print(f"  P75: {p75:.1f}")
    print(f"  Max: {max_conf:.1f}")
    print()

    # 检查扫描器阈值
    min_score = 12  # 当前设置
    above_threshold = sum(1 for c in confidence_values if c >= min_score)

    print(f"扫描器阈值检查:")
    print(f"  当前min_score: {min_score}")
    print(f"  confidence >= {min_score}: {above_threshold}/{n} ({above_threshold/n*100:.1f}%)")
    print()

# 诊断结论
print("=" * 80)
print("🎯 诊断结论")
print("=" * 80)
print()

# 找出通过率最低的gate
gate_pass_rates = {}
for gate_name, stats in gate_stats.items():
    if gate_name == 'all_gates':
        continue
    pass_rate = stats['pass'] / total * 100
    gate_pass_rates[gate_name] = pass_rate

if gate_pass_rates:
    worst_gate = min(gate_pass_rates, key=gate_pass_rates.get)
    worst_rate = gate_pass_rates[worst_gate]

    print(f"❌ **最大瓶颈**: {worst_gate} (通过率: {worst_rate:.1f}%)")
    print()

    # 给出建议
    if 'fund_support' in worst_gate or 'gate2' in worst_gate:
        print("📋 建议：Gate2 (F因子) 是瓶颈")
        print()
        print("可能原因：F_min=-50 太严格，很多币种F<-50")
        print()
        print("修复方案:")
        print("  方案A: 放宽F_min到-80")
        print('    "F_min": -80')
        print()
        print("  方案B: 接受现状（保持风控，等待更好的市场机会）")

    elif 'independence' in worst_gate or 'gate5' in worst_gate:
        print("📋 建议：Gate5 (I因子) 是瓶颈")
        print()
        print("可能原因：I_min=0 太严格，很多币种I<0")
        print()
        print("修复方案:")
        print("  方案A: 放宽I_min到-20或-30")
        print('    "I_min": -20  // 覆盖I的P25=-26')
        print()
        print("  ⚠️ 注意：仍保留market_regime检查")
        print("    - I<-20且逆势：仍会被拒绝（风控保护）")
        print("    - I<-20但顺势：可以通过")

    elif 'probability' in worst_gate or 'gate4' in worst_gate:
        print("📋 建议：Gate4 (概率) 是瓶颈")
        print()
        print("修复方案:")
        print('  降低P_min: 0.40 → 0.35')

# 最终通过情况
final_pass = gate_stats['all_gates']['pass']
print()
print(f"🚀 最终结果: {final_pass} 个信号通过所有Gate")
print()

if final_pass == 0:
    print("❌ 0个信号通过 → 需要放宽上述瓶颈gate")
elif final_pass < 5:
    print("⚠️ 信号太少 → 可以适当放宽阈值")
else:
    print("✅ 有足够信号")
    print()
    print("但如果仍然没有电报通知，检查:")
    print("  1. 扫描器的min_score阈值")
    print("  2. AntiJitter防抖动设置")
    print("  3. Telegram配置")

print()
print("=" * 80)
