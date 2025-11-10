#!/usr/bin/env python3
"""
简化版Gate测试 - 调试用

逐步检查每个环节
"""

import os
import sys
import asyncio

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

print("=" * 80)
print("🔧 简化版Gate测试（调试）")
print("=" * 80)
print()

# 1. 检查配置加载
print("1️⃣ 检查配置...")
try:
    from ats_core.config.threshold_config import ThresholdConfig
    config = ThresholdConfig()

    gate2_F_min = config.get_gate_threshold('gate2_fund_support', 'F_min', -50)
    gate5_I_min = config.get_gate_threshold('gate5_independence_market', 'I_min', 0)

    print(f"   Gate2 F_min: {gate2_F_min}")
    print(f"   Gate5 I_min: {gate5_I_min}")
    print("   ✅ 配置加载成功")
except Exception as e:
    print(f"   ❌ 配置加载失败: {e}")
    exit(1)

print()

# 2. 初始化扫描器
print("2️⃣ 初始化扫描器...")
try:
    from ats_core.pipeline.batch_scan_optimized import OptimizedBatchScanner

    async def test_scanner():
        scanner = OptimizedBatchScanner()
        print("   正在初始化...")
        await scanner.initialize()
        print("   ✅ 扫描器初始化成功")

        # 3. 扫描币种
        print()
        print("3️⃣ 扫描5个币种（测试）...")
        scan_result = await scanner.scan(max_symbols=5)
        results = scan_result.get('results', [])

        print(f"   扫描结果数量: {len(results)}")

        if not results:
            print("   ❌ 扫描返回空结果")
            return

        print("   ✅ 扫描成功")
        print()

        # 4. 检查第一个结果的数据
        print("4️⃣ 检查数据结构...")
        first = results[0]
        symbol = first.get('symbol', 'UNKNOWN')
        klines = first.get('klines', [])
        oi_data = first.get('oi_data', [])
        cvd_series = first.get('cvd_series', [])

        print(f"   币种: {symbol}")
        print(f"   K线数量: {len(klines)}")
        print(f"   OI数据: {len(oi_data)}")
        print(f"   CVD数据: {len(cvd_series)}")

        if len(klines) < 100:
            print(f"   ⚠️ K线数据不足（需要>=100）")
        if len(cvd_series) < 10:
            print(f"   ⚠️ CVD数据不足（需要>=10）")

        print()

        # 5. 尝试v7.2增强
        print("5️⃣ 测试v7.2增强分析...")
        try:
            from ats_core.pipeline.analyze_symbol_v72 import analyze_with_v72_enhancements

            if len(klines) >= 100 and len(cvd_series) >= 10:
                v72_result = analyze_with_v72_enhancements(
                    original_result=first,
                    symbol=symbol,
                    klines=klines,
                    oi_data=oi_data,
                    cvd_series=cvd_series,
                    atr_now=first.get('atr', 0)
                )

                v72 = v72_result.get('v72_enhancements', {})

                if v72:
                    print("   ✅ v7.2增强成功")

                    # 显示关键数据
                    gates = v72.get('gates', {})
                    F_v2 = v72.get('F_v2', 0)
                    I_v2 = v72.get('I_v2', 0)
                    confidence = v72.get('confidence_v72', 0)

                    print(f"   F因子: {F_v2}")
                    print(f"   I因子: {I_v2}")
                    print(f"   Confidence: {confidence}")
                    print()

                    print("   Gate状态:")
                    print(f"     Gate1: {gates.get('gates_data_quality', 0)}")
                    print(f"     Gate2: {gates.get('gates_fund_support', 0)}")
                    print(f"     Gate3: {gates.get('gates_ev', 0)}")
                    print(f"     Gate4: {gates.get('gates_probability', 0)}")
                    print(f"     Gate5: {gates.get('gates_independence_market', 0)}")
                    print(f"     All Pass: {gates.get('pass_all', False)}")
                else:
                    print("   ❌ v72_enhancements为空")
            else:
                print("   ⚠️ 数据不足，跳过v7.2增强")

        except Exception as e:
            print(f"   ❌ v7.2增强失败: {e}")
            import traceback
            traceback.print_exc()

        print()
        print("=" * 80)
        print("🎯 诊断完成")
        print("=" * 80)

    asyncio.run(test_scanner())

except Exception as e:
    print(f"   ❌ 失败: {e}")
    import traceback
    traceback.print_exc()
