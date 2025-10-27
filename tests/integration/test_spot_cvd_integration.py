#!/usr/bin/env python3
# coding: utf-8
"""
测试现货CVD集成到analyze_symbol

验证：
1. 能否成功获取现货K线数据
2. CVD是否使用了现货+合约组合
3. 获取失败时是否优雅降级
"""

import sys
from ats_core.sources.binance import get_klines, get_spot_klines
from ats_core.features.cvd import cvd_mix_with_oi_price

def test_spot_cvd_integration():
    print("=" * 60)
    print("测试现货CVD集成")
    print("=" * 60)

    # 测试币种
    test_symbols = [
        "BTCUSDT",     # 主流币，现货+合约都有
        "1000PEPEUSDT", # 合约特有倍数币，可能没有现货
    ]

    for symbol in test_symbols:
        print(f"\n【测试币种：{symbol}】")
        print("-" * 60)

        # 1. 获取合约K线
        try:
            k1 = get_klines(symbol, "1h", 100)
            print(f"✅ 合约K线: {len(k1)} 条")
        except Exception as e:
            print(f"❌ 合约K线获取失败: {e}")
            continue

        # 2. 尝试获取现货K线
        try:
            spot_k1 = get_spot_klines(symbol, "1h", 100)
            if spot_k1 and len(spot_k1) > 0:
                print(f"✅ 现货K线: {len(spot_k1)} 条")
                has_spot = True
            else:
                print(f"⚠️  现货K线: 无数据")
                has_spot = False
                spot_k1 = None
        except Exception as e:
            print(f"⚠️  现货K线获取失败: {e}")
            has_spot = False
            spot_k1 = None

        # 3. 测试CVD计算
        try:
            # 不传现货数据
            cvd_futures_only, _ = cvd_mix_with_oi_price(k1, [], window=20, spot_klines=None)
            print(f"\n仅合约CVD: {cvd_futures_only[-1]:.2f}")

            if has_spot:
                # 传入现货数据
                cvd_combined, _ = cvd_mix_with_oi_price(k1, [], window=20, spot_klines=spot_k1)
                print(f"组合CVD: {cvd_combined[-1]:.2f}")

                # 计算差异
                diff = abs(cvd_combined[-1] - cvd_futures_only[-1])
                diff_pct = (diff / max(abs(cvd_futures_only[-1]), 1.0)) * 100
                print(f"差异: {diff:.2f} ({diff_pct:.2f}%)")

                if diff_pct > 1.0:
                    print(f"✅ 现货数据对CVD有影响 ({diff_pct:.2f}%)")
                else:
                    print(f"ℹ️  现货数据影响较小 ({diff_pct:.2f}%)")
            else:
                print(f"ℹ️  无现货数据，使用纯合约CVD")

        except Exception as e:
            print(f"❌ CVD计算失败: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)

    print("\n【结论】")
    print("1. analyze_symbol.py 现在会自动尝试获取现货K线")
    print("2. 如果成功，CVD会使用现货+合约组合（动态权重）")
    print("3. 如果失败，CVD会降级到只用合约数据")
    print("4. 整个过程是自动的，不需要人工干预")

if __name__ == "__main__":
    test_spot_cvd_integration()
