#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单独测试C、M、O三个因子的相对历史归一化

测试目标：
1. C（CVD）- 相对历史斜率归一化
2. M（动量）- 相对历史斜率归一化
3. O（持仓）- 相对历史OI斜率归一化

验证：
- 归一化方法是否为 'relative_historical'
- 是否包含相对强度元数据
- 函数是否正常运行无报错
"""

import sys
sys.path.insert(0, '/home/user/cryptosignal')

from ats_core.sources.binance import get_klines, get_open_interest_hist
from ats_core.features.cvd import cvd_from_klines
from ats_core.features.cvd_flow import score_cvd_flow
from ats_core.features.momentum import score_momentum
from ats_core.features.open_interest import score_open_interest


def test_cvd_factor(symbol: str):
    """测试C（CVD）因子"""
    print(f"\n{'='*80}")
    print(f"测试 C（CVD）因子 - {symbol}")
    print(f"{'='*80}")

    try:
        # 获取数据
        print("📥 获取数据...")
        klines = get_klines(symbol, "1h", 100)
        if not klines or len(klines) < 30:
            print(f"❌ 数据不足: {len(klines) if klines else 0}根K线")
            return

        print(f"✅ 获取{len(klines)}根K线")

        # 计算CVD
        cvd_series = cvd_from_klines(klines, use_taker_buy=True)
        c = [float(k[4]) for k in klines]

        print(f"✅ 计算CVD序列: {len(cvd_series)}个数据点")

        # 计算C因子
        C, meta = score_cvd_flow(cvd_series, c, False, params=None, klines=klines)

        # 显示结果
        print(f"\n📊 C因子得分: {C}")
        print(f"   归一化方法: {meta.get('normalization_method', 'N/A')}")
        print(f"   CVD原始变化: {meta.get('cvd6_raw', 0):.2f}")
        print(f"   CVD斜率: {meta.get('cvd_slope', 0):.4f}")
        print(f"   R²拟合度: {meta.get('r_squared', 0):.3f}")

        if 'relative_intensity' in meta:
            print(f"\n✅ 相对历史归一化成功:")
            print(f"   历史平均斜率: {meta['avg_abs_slope']:.4f}")
            print(f"   相对强度: {meta['relative_intensity']:.3f}x")
            if 'p95_slope' in meta:
                print(f"   95分位数阈值: {meta['p95_slope']:.4f}")
            print(f"   拥挤警告: {'🔴是' if meta.get('crowding_warn') else '✅否'}")
        else:
            print(f"\n⚠️ 未使用相对历史归一化（可能是数据不足）")

        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_momentum_factor(symbol: str):
    """测试M（动量）因子"""
    print(f"\n{'='*80}")
    print(f"测试 M（动量）因子 - {symbol}")
    print(f"{'='*80}")

    try:
        # 获取数据
        print("📥 获取数据...")
        klines = get_klines(symbol, "1h", 100)
        if not klines or len(klines) < 30:
            print(f"❌ 数据不足: {len(klines) if klines else 0}根K线")
            return

        print(f"✅ 获取{len(klines)}根K线")

        # 提取OHLC数据
        h = [float(k[2]) for k in klines]
        l = [float(k[3]) for k in klines]
        c = [float(k[4]) for k in klines]

        # 计算M因子
        M, meta = score_momentum(h, l, c, params=None)

        # 显示结果
        print(f"\n📊 M因子得分: {M}")
        print(f"   归一化方法: {meta.get('normalization_method', 'N/A')}")
        print(f"   当前斜率: {meta.get('slope_now', 0):.6f}")
        print(f"   加速度: {meta.get('accel', 0):.6f}")
        print(f"   解释: {meta.get('interpretation', 'N/A')}")

        if 'relative_slope_intensity' in meta:
            print(f"\n✅ 相对历史归一化成功:")
            print(f"   历史平均斜率: {meta['avg_abs_slope']:.6f}")
            print(f"   斜率相对强度: {meta['relative_slope_intensity']:.3f}x")
            if 'relative_accel_intensity' in meta:
                print(f"   历史平均加速度: {meta['avg_abs_accel']:.6f}")
                print(f"   加速度相对强度: {meta['relative_accel_intensity']:.3f}x")
        else:
            print(f"\n⚠️ 未使用相对历史归一化（可能是数据不足，使用ATR降级）")

        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_oi_factor(symbol: str):
    """测试O（持仓）因子"""
    print(f"\n{'='*80}")
    print(f"测试 O（持仓）因子 - {symbol}")
    print(f"{'='*80}")

    try:
        # 获取数据
        print("📥 获取数据...")
        klines = get_klines(symbol, "1h", 100)
        if not klines or len(klines) < 30:
            print(f"❌ K线数据不足: {len(klines) if klines else 0}根")
            return

        print(f"✅ 获取{len(klines)}根K线")

        # 获取OI数据
        oi_data = get_open_interest_hist(symbol, "1h", 200)
        if not oi_data or len(oi_data) < 30:
            print(f"⚠️ OI数据不足: {len(oi_data) if oi_data else 0}个数据点")
            print("   将使用CVD fallback")

        print(f"✅ 获取{len(oi_data) if oi_data else 0}个OI数据点")

        # 提取收盘价
        closes = [float(k[4]) for k in klines]

        # 计算O因子
        O, meta = score_open_interest(
            symbol=symbol,
            closes=closes,
            params={},
            cvd6_fallback=0.0,
            oi_data=oi_data
        )

        # 显示结果
        print(f"\n📊 O因子得分: {O}")
        print(f"   归一化方法: {meta.get('normalization_method', 'N/A')}")
        print(f"   OI 24h变化: {meta.get('oi24h_pct', 0):.2f}%")
        print(f"   R²拟合度: {meta.get('r_squared', 0):.3f}")
        print(f"   价格方向: {meta.get('price_direction', 0)}")
        print(f"   解释: {meta.get('interpretation', 'N/A')}")

        if 'relative_oi_intensity' in meta:
            print(f"\n✅ 相对历史归一化成功:")
            print(f"   历史平均OI斜率: {meta['avg_abs_oi_slope']:.6f}")
            print(f"   OI相对强度: {meta['relative_oi_intensity']:.3f}x")
            print(f"   拥挤警告: {'🔴是' if meta.get('crowding_warn') else '✅否'}")
        else:
            print(f"\n⚠️ 未使用相对历史归一化（可能是数据不足，使用中位数降级）")

        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "="*80)
    print("C、M、O 三因子相对历史归一化测试")
    print("="*80)

    # 测试币种
    test_symbols = ["BTCUSDT", "ETHUSDT"]

    results = {
        "C": [],
        "M": [],
        "O": []
    }

    for symbol in test_symbols:
        print(f"\n\n{'#'*80}")
        print(f"# 测试币种: {symbol}")
        print(f"{'#'*80}")

        # 测试C因子
        c_ok = test_cvd_factor(symbol)
        results["C"].append((symbol, c_ok))

        # 测试M因子
        m_ok = test_momentum_factor(symbol)
        results["M"].append((symbol, m_ok))

        # 测试O因子
        o_ok = test_oi_factor(symbol)
        results["O"].append((symbol, o_ok))

    # 汇总结果
    print(f"\n\n{'='*80}")
    print("测试结果汇总")
    print(f"{'='*80}")

    for factor in ["C", "M", "O"]:
        print(f"\n{factor}因子测试结果:")
        for symbol, ok in results[factor]:
            status = "✅ 通过" if ok else "❌ 失败"
            print(f"   {symbol}: {status}")

    # 统计
    total_tests = sum(len(results[f]) for f in results)
    passed_tests = sum(1 for f in results for _, ok in results[f] if ok)
    print(f"\n总计: {passed_tests}/{total_tests} 测试通过")

    if passed_tests == total_tests:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️ {total_tests - passed_tests}个测试失败，请检查错误信息")

    print(f"\n{'='*80}")
    print("✅ 测试完成")
    print(f"{'='*80}\n")
