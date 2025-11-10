#!/usr/bin/env python3
"""
深度诊断脚本 - 分析为什么53个基础信号变成0个电报信号

逐个检查信号在Gate1-5的通过情况

用法:
    python3 scripts/deep_gate_diagnosis.py
"""

import os
import sys
import asyncio
import json
from pathlib import Path

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from ats_core.pipeline.batch_scan_optimized import OptimizedBatchScanner
from ats_core.pipeline.analyze_symbol_v72 import analyze_with_v72_enhancements


async def main():
    print("=" * 80)
    print("🔬 深度Gate诊断工具")
    print("=" * 80)
    print()
    print("目标：找出为什么53个基础信号被Gate拒绝（0个电报信号）")
    print()

    # 1. 初始化扫描器
    print("📡 初始化扫描器...")
    scanner = OptimizedBatchScanner()
    await scanner.initialize()
    print("✅ 扫描器初始化完成")
    print()

    # 2. 执行扫描
    print("🔍 扫描币种（限制100个用于快速诊断）...")
    scan_result = await scanner.scan(max_symbols=100)
    results = scan_result.get('results', [])
    print(f"✅ 扫描完成：{len(results)} 个基础信号")
    print()

    if not results:
        print("❌ 没有基础信号，无法诊断")
        return

    # 3. 应用v7.2增强分析
    print("🔧 应用v7.2增强分析...")
    print("=" * 80)
    print()

    gate_stats = {
        'gate1_data_quality': {'pass': 0, 'fail': 0},
        'gate2_fund_support': {'pass': 0, 'fail': 0},
        'gate3_ev': {'pass': 0, 'fail': 0},
        'gate4_probability': {'pass': 0, 'fail': 0},
        'gate5_independence_market': {'pass': 0, 'fail': 0},
        'all_gates': {'pass': 0, 'fail': 0},
        'confidence_check': {'pass': 0, 'fail': 0},
    }

    failed_examples = {
        'gate1': [],
        'gate2': [],
        'gate3': [],
        'gate4': [],
        'gate5': [],
        'confidence': [],
    }

    for i, result in enumerate(results):
        symbol = result.get('symbol')
        klines = result.get('klines', [])
        oi_data = result.get('oi_data', [])
        cvd_series = result.get('cvd_series', [])
        atr = result.get('atr', 0)

        # 应用v7.2增强
        try:
            if len(klines) >= 100 and len(cvd_series) >= 10:
                v72_result = analyze_with_v72_enhancements(
                    original_result=result,
                    symbol=symbol,
                    klines=klines,
                    oi_data=oi_data,
                    cvd_series=cvd_series,
                    atr_now=atr
                )
            else:
                continue

            # 提取gate信息
            gates = v72_result.get('v72_enhancements', {}).get('gates', {})
            gate1 = gates.get('gates_data_quality', 0)
            gate2 = gates.get('gates_fund_support', 0)
            gate3 = gates.get('gates_ev', 0)
            gate4 = gates.get('gates_probability', 0)
            gate5 = gates.get('gates_independence_market', 0)
            all_pass = gates.get('pass_all', False)

            # 提取关键指标
            F_v2 = v72_result.get('v72_enhancements', {}).get('F_v2', 0)
            I_v2 = v72_result.get('v72_enhancements', {}).get('I_v2', 0)
            P_calibrated = v72_result.get('v72_enhancements', {}).get('P_calibrated', 0)
            EV_net = v72_result.get('v72_enhancements', {}).get('EV_net', 0)
            confidence = v72_result.get('v72_enhancements', {}).get('confidence_v72', 0)

            # 统计gate通过情况
            if gate1 > 0:
                gate_stats['gate1_data_quality']['pass'] += 1
            else:
                gate_stats['gate1_data_quality']['fail'] += 1
                if len(failed_examples['gate1']) < 3:
                    failed_examples['gate1'].append(f"{symbol}: klines={len(klines)}")

            if gate2 > 0:
                gate_stats['gate2_fund_support']['pass'] += 1
            else:
                gate_stats['gate2_fund_support']['fail'] += 1
                if len(failed_examples['gate2']) < 3:
                    failed_examples['gate2'].append(f"{symbol}: F={F_v2:.0f}")

            if gate3 > 0:
                gate_stats['gate3_ev']['pass'] += 1
            else:
                gate_stats['gate3_ev']['fail'] += 1
                if len(failed_examples['gate3']) < 3:
                    failed_examples['gate3'].append(f"{symbol}: EV={EV_net:.3f}")

            if gate4 > 0:
                gate_stats['gate4_probability']['pass'] += 1
            else:
                gate_stats['gate4_probability']['fail'] += 1
                if len(failed_examples['gate4']) < 3:
                    failed_examples['gate4'].append(f"{symbol}: P={P_calibrated:.3f}")

            if gate5 > 0:
                gate_stats['gate5_independence_market']['pass'] += 1
            else:
                gate_stats['gate5_independence_market']['fail'] += 1
                if len(failed_examples['gate5']) < 3:
                    failed_examples['gate5'].append(f"{symbol}: I={I_v2:.0f}")

            if all_pass:
                gate_stats['all_gates']['pass'] += 1
            else:
                gate_stats['all_gates']['fail'] += 1

            # 检查confidence（假设阈值是20）
            if confidence >= 20:
                gate_stats['confidence_check']['pass'] += 1
            else:
                gate_stats['confidence_check']['fail'] += 1
                if len(failed_examples['confidence']) < 3:
                    failed_examples['confidence'].append(f"{symbol}: conf={confidence:.1f}")

        except Exception as e:
            print(f"❌ {symbol} 增强分析失败: {e}")
            continue

    # 4. 输出诊断结果
    print()
    print("=" * 80)
    print("📊 Gate通过率统计")
    print("=" * 80)
    print()

    total = gate_stats['gate1_data_quality']['pass'] + gate_stats['gate1_data_quality']['fail']

    for gate_name, stats in gate_stats.items():
        pass_count = stats['pass']
        fail_count = stats['fail']
        total_count = pass_count + fail_count

        if total_count > 0:
            pass_rate = pass_count / total_count * 100
            fail_rate = fail_count / total_count * 100

            status = "✅" if pass_rate > 80 else "⚠️" if pass_rate > 50 else "❌"

            print(f"{status} {gate_name:30s}: {pass_count:3d}/{total_count:3d} 通过 ({pass_rate:5.1f}%)")

            # 如果失败率高，显示示例
            if fail_rate > 20:
                gate_key = gate_name.replace('gate', 'gate').replace('_', '').replace('dataqualit', '1').replace('fundsupport', '2').replace('ev', '3').replace('probability', '4').replace('independencemarket', '5').replace('allgates', 'all').replace('confidencecheck', 'confidence')
                examples_key = None
                if 'gate1' in gate_name:
                    examples_key = 'gate1'
                elif 'gate2' in gate_name:
                    examples_key = 'gate2'
                elif 'gate3' in gate_name:
                    examples_key = 'gate3'
                elif 'gate4' in gate_name:
                    examples_key = 'gate4'
                elif 'gate5' in gate_name:
                    examples_key = 'gate5'
                elif 'confidence' in gate_name:
                    examples_key = 'confidence'

                if examples_key and failed_examples.get(examples_key):
                    print(f"   失败示例: {', '.join(failed_examples[examples_key][:3])}")

    print()
    print("=" * 80)
    print("🎯 诊断结论")
    print("=" * 80)
    print()

    # 找出通过率最低的gate
    gate_pass_rates = {}
    for gate_name, stats in gate_stats.items():
        if gate_name in ['all_gates', 'confidence_check']:
            continue
        total_count = stats['pass'] + stats['fail']
        if total_count > 0:
            gate_pass_rates[gate_name] = stats['pass'] / total_count * 100

    if gate_pass_rates:
        worst_gate = min(gate_pass_rates, key=gate_pass_rates.get)
        worst_rate = gate_pass_rates[worst_gate]

        print(f"❌ **最大瓶颈**: {worst_gate} (通过率: {worst_rate:.1f}%)")
        print()

        # 根据最差的gate给出建议
        if 'gate2' in worst_gate:
            print("📋 诊断：F因子闸门（Gate2）拒绝了大量信号")
            print()
            print("可能原因:")
            print("  1. F_min=-50 太严格")
            print("  2. 当前市场资金流出严重（F<-50的币种多）")
            print()
            print("建议修复:")
            print("  方案A: 放宽F_min到-80")
            print('    修改 config/signal_thresholds.json:')
            print('    "gate2_fund_support": {')
            print('      "F_min": -80,  // 从-50放宽到-80')
            print('    }')
            print()
            print("  方案B: 检查F因子计算是否正确")
            print('    运行: python3 scripts/test_f_factor_fix.py')

        elif 'gate5' in worst_gate:
            print("📋 诊断：I因子闸门（Gate5）拒绝了大量信号")
            print()
            print("可能原因:")
            print("  1. I_min=10 仍然太高")
            print("  2. market_regime检查过严")
            print()
            print("建议修复:")
            print("  方案A: 进一步降低I_min到0或负数")
            print('    修改 config/signal_thresholds.json:')
            print('    "gate5_independence_market": {')
            print('      "I_min": 0,  // 从10降到0')
            print('    }')
            print()
            print("  方案B: 完全禁用Gate5（不推荐）")
            print('    "I_min": -100')

        elif 'gate4' in worst_gate:
            print("📋 诊断：概率闸门（Gate4）拒绝了大量信号")
            print()
            print("建议: 降低P_min从0.45到0.40")

        elif 'confidence' in worst_gate:
            print("📋 诊断：confidence阈值过高")
            print()
            print("建议: 降低扫描器的min_score参数")

    # 统计最终通过all_gates的信号
    final_pass = gate_stats['all_gates']['pass']
    print()
    print(f"🚀 最终结果: {final_pass} 个信号通过所有Gate")
    print()

    if final_pass == 0:
        print("❌ 0个信号通过 → 需要修复上述瓶颈gate")
    elif final_pass < 5:
        print("⚠️ 信号太少 → 可以适当放宽阈值")
    else:
        print("✅ 有足够信号 → 检查AntiJitter或Telegram配置")

    print()
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
