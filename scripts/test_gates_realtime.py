#!/usr/bin/env python3
"""
实时Gate通过率测试 - 扫描并分析各道门槛

实时扫描20个币种，分析每个Gate的拒绝情况
"""

import os
import sys
import asyncio
from collections import Counter

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from ats_core.pipeline.batch_scan_optimized import OptimizedBatchScanner
from ats_core.pipeline.analyze_symbol_v72 import analyze_with_v72_enhancements


async def test_gates():
    print("=" * 80)
    print("🔬 实时Gate通过率测试")
    print("=" * 80)
    print()
    print("正在扫描20个币种，分析各道门槛...")
    print()

    # 初始化扫描器
    scanner = OptimizedBatchScanner()
    await scanner.initialize()

    # 扫描20个币种（快速测试）
    scan_result = await scanner.scan(max_symbols=20)
    results = scan_result.get('results', [])

    print(f"✅ 扫描完成：{len(results)} 个币种")
    print()

    # 统计数据
    stats = {
        'total': 0,
        'gate1_pass': 0,
        'gate2_pass': 0,
        'gate3_pass': 0,
        'gate4_pass': 0,
        'gate5_pass': 0,
        'all_gates_pass': 0,
        'confidence_pass': 0,
    }

    gate_failures = {
        'gate1': [],
        'gate2': [],
        'gate3': [],
        'gate4': [],
        'gate5': [],
        'confidence': [],
    }

    confidence_values = []
    f_values = []
    i_values = []
    p_values = []

    print("=" * 80)
    print("🔍 逐个分析币种")
    print("=" * 80)
    print()

    for result in results:
        symbol = result.get('symbol')
        klines = result.get('klines', [])
        oi_data = result.get('oi_data', [])
        cvd_series = result.get('cvd_series', [])
        atr = result.get('atr', 0)

        if len(klines) < 100 or len(cvd_series) < 10:
            continue

        try:
            # 应用v7.2增强
            v72_result = analyze_with_v72_enhancements(
                original_result=result,
                symbol=symbol,
                klines=klines,
                oi_data=oi_data,
                cvd_series=cvd_series,
                atr_now=atr
            )

            v72 = v72_result.get('v72_enhancements', {})
            gates = v72.get('gates', {})

            # 提取gate状态
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
            side = v72_result.get('side', 'unknown')

            stats['total'] += 1
            confidence_values.append(confidence)
            f_values.append(F_v2)
            i_values.append(I_v2)
            p_values.append(P_calibrated)

            # 统计通过情况
            gate_status = []

            if gate1 > 0:
                stats['gate1_pass'] += 1
                gate_status.append("✅G1")
            else:
                gate_status.append("❌G1")
                gate_failures['gate1'].append(symbol)

            if gate2 > 0:
                stats['gate2_pass'] += 1
                gate_status.append("✅G2")
            else:
                gate_status.append("❌G2")
                gate_failures['gate2'].append(f"{symbol}(F={F_v2:.0f})")

            if gate3 > 0:
                stats['gate3_pass'] += 1
                gate_status.append("✅G3")
            else:
                gate_status.append("❌G3")
                gate_failures['gate3'].append(f"{symbol}(EV={EV_net:.2f})")

            if gate4 > 0:
                stats['gate4_pass'] += 1
                gate_status.append("✅G4")
            else:
                gate_status.append("❌G4")
                gate_failures['gate4'].append(f"{symbol}(P={P_calibrated:.2f})")

            if gate5 > 0:
                stats['gate5_pass'] += 1
                gate_status.append("✅G5")
            else:
                gate_status.append("❌G5")
                gate_failures['gate5'].append(f"{symbol}(I={I_v2:.0f},{side})")

            if all_pass:
                stats['all_gates_pass'] += 1

            # 检查confidence（扫描器阈值=8）
            if confidence >= 8:
                stats['confidence_pass'] += 1
                gate_status.append("✅Conf")
            else:
                gate_status.append("❌Conf")
                gate_failures['confidence'].append(f"{symbol}(conf={confidence:.0f})")

            # 显示结果
            status_str = " ".join(gate_status)
            final_status = "✅PASS" if all_pass and confidence >= 8 else "❌FAIL"
            print(f"{symbol:12s} {final_status} | {status_str} | F={F_v2:3.0f} I={I_v2:3.0f} Conf={confidence:2.0f}")

        except Exception as e:
            print(f"❌ {symbol:12s} 分析失败: {e}")
            continue

    # 输出统计
    print()
    print("=" * 80)
    print("📊 Gate通过率统计")
    print("=" * 80)
    print()

    total = stats['total']
    if total == 0:
        print("❌ 没有有效数据")
        return

    gate_names = [
        ('Gate1 (数据质量)', 'gate1_pass'),
        ('Gate2 (F因子)', 'gate2_pass'),
        ('Gate3 (EV)', 'gate3_pass'),
        ('Gate4 (概率)', 'gate4_pass'),
        ('Gate5 (I+Market)', 'gate5_pass'),
        ('All Gates', 'all_gates_pass'),
        ('Confidence>=8', 'confidence_pass'),
    ]

    for name, key in gate_names:
        pass_count = stats[key]
        pass_rate = pass_count / total * 100
        status = "✅" if pass_rate > 80 else "⚠️" if pass_rate > 50 else "❌"
        print(f"{status} {name:20s}: {pass_count:2d}/{total:2d} ({pass_rate:5.1f}%)")

    # 显示失败示例
    print()
    print("=" * 80)
    print("❌ 失败示例")
    print("=" * 80)
    print()

    for gate, examples in gate_failures.items():
        if examples:
            print(f"{gate}: {', '.join(examples[:3])}")
            if len(examples) > 3:
                print(f"  ... 还有 {len(examples)-3} 个")

    # 指标分布
    print()
    print("=" * 80)
    print("📈 指标分布")
    print("=" * 80)
    print()

    if confidence_values:
        confidence_values.sort()
        f_values.sort()
        i_values.sort()
        p_values.sort()

        n = len(confidence_values)

        print(f"Confidence: Min={confidence_values[0]:.0f}, "
              f"中位={confidence_values[n//2]:.0f}, "
              f"Max={confidence_values[-1]:.0f}")

        print(f"F因子:      Min={f_values[0]:.0f}, "
              f"中位={f_values[n//2]:.0f}, "
              f"Max={f_values[-1]:.0f}")

        print(f"I因子:      Min={i_values[0]:.0f}, "
              f"中位={i_values[n//2]:.0f}, "
              f"Max={i_values[-1]:.0f}")

        print(f"P概率:      Min={p_values[0]:.2f}, "
              f"中位={p_values[n//2]:.2f}, "
              f"Max={p_values[-1]:.2f}")

    # 诊断结论
    print()
    print("=" * 80)
    print("🎯 诊断结论")
    print("=" * 80)
    print()

    # 找出通过率最低的
    pass_rates = []
    for name, key in gate_names[:-2]:  # 不包括All Gates和Confidence
        pass_rate = stats[key] / total * 100
        pass_rates.append((name, pass_rate, key))

    pass_rates.sort(key=lambda x: x[1])

    if pass_rates:
        worst = pass_rates[0]
        print(f"❌ **最大瓶颈**: {worst[0]} (通过率: {worst[1]:.1f}%)")
        print()

        if 'Gate2' in worst[0]:
            print("建议：放宽F_min从-50到-80")
            f_below_50 = sum(1 for f in f_values if f < -50)
            print(f"  当前F<-50的币种: {f_below_50}/{total} ({f_below_50/total*100:.1f}%)")

        elif 'Gate5' in worst[0]:
            print("建议：放宽I_min从0到-20")
            i_below_0 = sum(1 for i in i_values if i < 0)
            print(f"  当前I<0的币种: {i_below_0}/{total} ({i_below_0/total*100:.1f}%)")

        elif 'Gate4' in worst[0]:
            print("建议：放宽P_min从0.40到0.35")

    # 最终通过
    final_pass = stats['all_gates_pass']
    final_with_conf = sum(1 for i in range(total) if i < stats['all_gates_pass'] and confidence_values[i] >= 8)

    print()
    print(f"🚀 最终结果:")
    print(f"  通过All Gates: {final_pass}/{total}")
    print(f"  通过All Gates + Confidence>=8: ？（需要交叉分析）")
    print()

    if final_pass == 0:
        print("❌ 0个信号通过所有Gate → 需要放宽瓶颈Gate")
    elif final_pass < 3:
        print("⚠️ 信号太少 → 可以适当放宽")
    else:
        print("✅ 有信号通过，检查为什么没有电报通知")

    print()
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_gates())
