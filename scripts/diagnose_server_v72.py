# coding: utf-8
"""
服务器v7.2系统诊断脚本

用途：诊断为什么所有因子都显示0.0

运行方法：
cd ~/cryptosignal
python3 scripts/diagnose_server_v72.py
"""

import sys
from pathlib import Path

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 70)
print("🔍 v7.2系统诊断")
print("=" * 70)

# ===== 测试 1: 模块导入 =====
print("\n1️⃣  测试模块导入...")
try:
    from ats_core.pipeline.analyze_symbol import analyze_symbol
    print("   ✅ analyze_symbol 导入成功")
except Exception as e:
    print(f"   ❌ analyze_symbol 导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    from ats_core.pipeline.analyze_symbol_v72 import analyze_with_v72_enhancements
    print("   ✅ analyze_with_v72_enhancements 导入成功")
except Exception as e:
    print(f"   ❌ analyze_with_v72_enhancements 导入失败: {e}")
    sys.exit(1)

try:
    from ats_core.pipeline.batch_scan_optimized import OptimizedBatchScanner
    print("   ✅ OptimizedBatchScanner 导入成功")
except Exception as e:
    print(f"   ❌ OptimizedBatchScanner 导入失败: {e}")
    sys.exit(1)

# ===== 测试 2: Binance API连接 =====
print("\n2️⃣  测试Binance API连接...")
try:
    from ats_core.execution.binance_futures_client import get_binance_client
    import asyncio

    async def test_binance():
        client = get_binance_client()
        await client.initialize()
        ticker = await client.get_ticker("BTCUSDT")
        return ticker

    ticker = asyncio.run(test_binance())
    print(f"   ✅ Binance API连接成功")
    print(f"   BTC价格: {ticker.get('lastPrice')}")
except Exception as e:
    print(f"   ❌ Binance API连接失败: {e}")
    import traceback
    traceback.print_exc()

# ===== 测试 3: 单币种基础分析 =====
print("\n3️⃣  测试单币种基础分析 (BTCUSDT)...")
try:
    result = analyze_symbol("BTCUSDT")

    # 检查是否有错误
    if 'error' in result:
        print(f"   ❌ 分析返回错误: {result['error']}")
        if 'traceback' in result:
            print(f"   详细错误:\n{result['traceback']}")
    else:
        print(f"   ✅ 基础分析成功")

        # 显示因子分数
        T = result.get('T', 0)
        M = result.get('M', 0)
        C = result.get('C', 0)
        V = result.get('V', 0)
        O = result.get('O', 0)
        B = result.get('B', 0)

        # v6.6: 调制器在modulation字段中
        modulation = result.get('modulation', {})
        F = modulation.get('F', 0) if modulation else result.get('F', 0)
        L = modulation.get('L', 0) if modulation else result.get('L', 0)
        S = modulation.get('S', 0) if modulation else result.get('S', 0)
        I = modulation.get('I', 0) if modulation else result.get('I', 0)

        confidence = result.get('confidence', 0)

        print(f"\n   核心因子:")
        print(f"      T={T:.1f}, M={M:.1f}, C={C:.1f}")
        print(f"      V={V:.1f}, O={O:.1f}, B={B:.1f}")
        print(f"\n   调制器:")
        print(f"      F={F:.1f}, L={L:.1f}, S={S:.1f}, I={I:.1f}")
        print(f"\n   综合信心度: {confidence:.1f}")

        # 检查是否所有因子都是0
        all_zero = all([
            T == 0, M == 0, C == 0, V == 0, O == 0, B == 0,
            F == 0, L == 0, S == 0, I == 0
        ])

        if all_zero:
            print("\n   ⚠️  警告: 所有因子都是0！")
            print("   这通常意味着数据获取失败或计算出错")

            # 检查是否有rejection_reason
            publish_info = result.get('publish', {})
            rejection = publish_info.get('rejection_reason', [])
            if rejection:
                print(f"   拒绝原因: {rejection}")
        else:
            print(f"\n   ✅ 因子计算正常（至少有一个非零因子）")

except Exception as e:
    print(f"   ❌ 基础分析失败: {e}")
    import traceback
    traceback.print_exc()

# ===== 测试 4: v7.2增强分析 =====
print("\n4️⃣  测试v7.2增强分析 (BTCUSDT)...")
try:
    # 先获取基础结果
    result = analyze_symbol("BTCUSDT")

    if 'error' not in result:
        # 提取数据
        intermediate = result.get('intermediate_data', {})
        klines = intermediate.get('klines', [])
        oi_data = intermediate.get('oi_data', [])
        cvd_series = intermediate.get('cvd_series', [])
        atr = result.get('atr', 0)

        print(f"   数据可用性:")
        print(f"      klines: {len(klines)} 条")
        print(f"      oi_data: {len(oi_data)} 条")
        print(f"      cvd_series: {len(cvd_series)} 条")
        print(f"      atr: {atr}")

        if len(klines) >= 100 and len(cvd_series) >= 10:
            # 应用v7.2增强
            v72_result = analyze_with_v72_enhancements(
                original_result=result,
                symbol="BTCUSDT",
                klines=klines,
                oi_data=oi_data,
                cvd_series=cvd_series,
                atr_now=atr
            )

            print(f"\n   ✅ v7.2增强成功")

            # 检查v7.2字段
            v72_data = v72_result.get('v72_enhancements', {})
            if v72_data:
                F_v2 = v72_data.get('F_v2', 0)
                I_v2 = v72_data.get('I_v2', 0)
                P_calibrated = v72_data.get('P_calibrated', 0)
                EV_net = v72_data.get('EV_net', 0)

                print(f"\n   v7.2增强字段:")
                print(f"      F因子v2: {F_v2:.1f}")
                print(f"      I因子v2: {I_v2:.1f}")
                print(f"      校准概率: {P_calibrated:.3f}")
                print(f"      期望值: {EV_net:.4f}")

                # 检查闸门
                gates = v72_data.get('gates', {})
                pass_all = gates.get('pass_all', False)
                print(f"\n   五道闸门: {'✅ 全部通过' if pass_all else '❌ 未全部通过'}")
                if not pass_all:
                    print(f"   拒绝原因: {gates.get('reason', 'unknown')}")
            else:
                print(f"   ⚠️  警告: v72_enhancements字段不存在")
        else:
            print(f"   ⚠️  数据不足，无法应用v7.2增强")
            print(f"   需要: klines>=100, cvd>=10")

except Exception as e:
    print(f"   ❌ v7.2增强失败: {e}")
    import traceback
    traceback.print_exc()

# ===== 测试 5: 批量扫描 =====
print("\n5️⃣  测试批量扫描 (前3个币种)...")
try:
    import asyncio

    async def test_batch_scan():
        scanner = OptimizedBatchScanner()
        await scanner.initialize(enable_websocket=False)

        # 只扫描前3个币种进行测试
        scan_result = await scanner.scan(max_symbols=3, verbose=True)

        results = scan_result.get('results', [])
        errors = scan_result.get('errors', 0)

        return results, errors

    results, errors = asyncio.run(test_batch_scan())

    print(f"\n   扫描结果:")
    print(f"      信号数: {len(results)}")
    print(f"      错误数: {errors}")

    if results:
        print(f"\n   样例信号:")
        for r in results[:2]:
            symbol = r.get('symbol')
            confidence = r.get('confidence', 0)
            T = r.get('T', 0)
            M = r.get('M', 0)
            print(f"      {symbol}: confidence={confidence:.1f}, T={T:.1f}, M={M:.1f}")

    if errors > 0:
        print(f"   ⚠️  有 {errors} 个币种分析失败")

except Exception as e:
    print(f"   ❌ 批量扫描失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("✅ 诊断完成")
print("=" * 70)
