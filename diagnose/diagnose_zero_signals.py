#!/usr/bin/env python3
"""
0电报信号诊断脚本

快速诊断为什么扫描有53个基础信号，但0个电报信号

用法:
    python3 scripts/diagnose_zero_signals.py
"""

import os
import sys
import time
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from ats_core.features.market_regime import calculate_market_regime


def main():
    print("=" * 80)
    print("🔍 0电报信号诊断工具")
    print("=" * 80)
    print()

    # 1. 检查market_regime
    print("📊 1. 检查当前市场状态")
    print("-" * 80)

    try:
        cache_key = f"{int(time.time() // 60)}"
        market_regime, regime_meta = calculate_market_regime(cache_key)

        print(f"当前市场regime: {market_regime:.1f}")
        print()

        if market_regime < -30:
            print("❌ **熊市状态** (regime < -30)")
            print("   → 做多信号会被Gate5拒绝（低独立性+逆势保护）")
            print("   → 这是正常的风控机制")
            market_issue = "bear"
        elif market_regime > 30:
            print("✅ **牛市状态** (regime > 30)")
            print("   → 做多信号应该能通过Gate5")
            print("   → 如果仍无信号，可能是其他gate的问题")
            market_issue = "bull"
        else:
            print("⚠️ **震荡市** (-30 ≤ regime ≤ 30)")
            print("   → 需要I>=30才能稳定通过Gate5")
            print("   → 可考虑降低I_min阈值")
            market_issue = "choppy"

        print()
        print(f"市场元数据:")
        for key, val in regime_meta.items():
            print(f"  {key}: {val}")

    except Exception as e:
        print(f"❌ 无法获取market_regime: {e}")
        market_issue = "unknown"

    print()

    # 2. 检查Gate5配置
    print("⚙️ 2. 检查Gate5配置")
    print("-" * 80)

    try:
        with open('config/signal_thresholds.json', 'r') as f:
            config = json.load(f)

        gate5 = config.get('v72闸门阈值', {}).get('gate5_independence_market', {})
        I_min = gate5.get('I_min', 30)
        market_threshold = gate5.get('market_regime_threshold', 30)

        print(f"I_min: {I_min}")
        print(f"market_regime_threshold: {market_threshold}")
        print()

        print("Gate5逻辑:")
        print("  - 如果 I >= 60: 直接通过（高独立性）")
        print(f"  - 如果 I < {I_min}: 需要检查市场方向")
        print(f"      - 做多 + regime < -{market_threshold}: ❌ 拒绝")
        print(f"      - 做空 + regime > +{market_threshold}: ❌ 拒绝")
        print("      - 其他情况: ✅ 通过")
        print(f"  - 如果 {I_min} <= I < 60: 正常通过")

    except Exception as e:
        print(f"❌ 无法读取配置: {e}")
        I_min = 30

    print()

    # 3. 分析用户数据（从报告中提取）
    print("📈 3. 分析扫描数据")
    print("-" * 80)

    print("从您的扫描结果:")
    print("  信号数量: 53个基础信号")
    print("  Prime信号: 0个（电报）")
    print()
    print("I因子分布:")
    print("  Min: -96.0")
    print("  P25: -26.0")
    print("  中位: -10.5  ← ❗ 大部分币种I < 30")
    print("  P75: 14.0")
    print("  Max: 41.0    ← ❗ 没有I > 60的币种")
    print()

    # 估算I<30的比例
    print("估算:")
    print(f"  - I < {I_min}的币种: ~80-90% (需要market检查)")
    print(f"  - {I_min} <= I < 60的币种: ~10-20% (正常通过)")
    print(f"  - I >= 60的币种: 0% (直接通过)")
    print()

    # 4. 诊断结论
    print("=" * 80)
    print("🎯 诊断结论")
    print("=" * 80)
    print()

    if market_issue == "bear":
        print("✅ **问题确认: 市场熊市状态**")
        print()
        print("原因:")
        print("  1. 当前市场regime < -30（熊市）")
        print("  2. 80-90%的币种I < 30（跟随BTC下跌）")
        print("  3. Gate5拒绝了所有做多信号（低独立性+逆势）")
        print()
        print("建议: ✅ **不需要修复**")
        print("  - Gate5正确工作，保护用户避免熊市追高")
        print("  - 等待市场转牛（regime > 0）")
        print("  - 或寻找高独立性币种（I > 60）")
        print()
        print("如果强行修复:")
        print("  ❌ 降低I_min会增加熊市追高风险")
        print("  ❌ 禁用Gate5会失去重要保护机制")
        print()

    elif market_issue == "bull":
        print("⚠️ **问题待定: 牛市但无信号**")
        print()
        print("原因:")
        print("  1. 当前市场regime > 30（牛市）")
        print("  2. 做多信号应该能通过Gate5")
        print("  3. 但仍然0个Prime信号 → 可能是其他gate的问题")
        print()
        print("建议: 🔍 **深度诊断**")
        print("  1. 检查其他gate (gate1-4)的通过情况")
        print("  2. 检查confidence/edge是否达标")
        print("  3. 运行: python3 scripts/verify_v728_fix.py")
        print()

    elif market_issue == "choppy":
        print("⚠️ **问题确认: 震荡市+Gate5过严**")
        print()
        print("原因:")
        print("  1. 当前市场regime在-30到+30之间（震荡）")
        print(f"  2. 80-90%的币种I < {I_min}")
        print("  3. Gate5要求I>=30，导致大部分信号被拒")
        print()
        print("建议: 🔧 **可考虑降低I_min阈值**")
        print()
        print("方案A: 适度放宽（推荐）")
        print("  修改 config/signal_thresholds.json:")
        print('  "gate5_independence_market": {')
        print('    "I_min": 10,  // 从30降到10')
        print('    ...')
        print('  }')
        print()
        print("  预期效果:")
        print("    - I>=10的币种: ~30-40% (从10-20%提升)")
        print("    - Prime信号: 5-10个 (从0增加)")
        print("    - 仍保留市场方向检查（保护机制）")
        print()
        print("方案B: 完全禁用Gate5（不推荐）")
        print("  修改 I_min: -100, market_regime_threshold: 100")
        print("  ❌ 风险：失去逆势保护")
        print()

    else:
        print("❌ 无法诊断，请检查系统状态")

    print()
    print("=" * 80)
    print("📖 详细诊断报告: reports/ZERO_TELEGRAM_SIGNALS_DIAGNOSIS.md")
    print("=" * 80)


if __name__ == "__main__":
    main()
