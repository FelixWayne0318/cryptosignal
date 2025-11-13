# coding: utf-8
"""
v7.2.36 CVD增强验证测试

验证6个必补条件的基础功能：
1. imbalance_ratio计算
2. 严格OI对齐（取前不取后）
3. IQR护栏增强
4. 降级标记
5. 未收盘K线过滤
6. 重复时间戳检测
"""
import sys
import time

def test_imports():
    """测试1: 验证所有新增函数可以导入"""
    print("=" * 60)
    print("测试1: 导入验证")
    print("=" * 60)

    try:
        from ats_core.utils.cvd_utils import (
            _diff,
            align_klines_by_open_time,
            align_oi_to_klines,
            align_oi_to_klines_strict,  # 新增
            rolling_z,
            compute_cvd_delta,
            compute_dynamic_min_quote,
            compute_dynamic_min_quote_enhanced,  # 新增
            filter_unclosed_klines,  # 新增
            apply_outlier_handling  # 新增
        )
        print("✅ cvd_utils导入成功（包括4个新函数）")

        from ats_core.features.cvd import (
            cvd_from_klines,
            cvd_combined,
            cvd_mix_with_oi_price
        )
        print("✅ cvd特征函数导入成功")

        return True
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False


def test_imbalance_ratio():
    """测试2: 条件1 - imbalance_ratio计算"""
    print("\n" + "=" * 60)
    print("测试2: imbalance_ratio计算（条件1）")
    print("=" * 60)

    try:
        from ats_core.features.cvd import cvd_from_klines

        # 构造测试K线数据（Binance 12列格式）
        test_klines = [
            # [openTime, open, high, low, close, volume, closeTime, quoteVol, trades, takerBuyBase, takerBuyQuote, ignore]
            [1700000000000, 100, 105, 95, 102, 1000, 1700003599999, 100000, 50, 600, 60000, 0],
            [1700003600000, 102, 108, 100, 105, 1200, 1700007199999, 120000, 60, 700, 70000, 0],
            [1700007200000, 105, 110, 103, 108, 1500, 1700010799999, 150000, 70, 800, 80000, 0],
        ]

        # 不使用expose_meta（兼容旧版）
        cvd_only = cvd_from_klines(test_klines, use_quote=True, expose_meta=False)
        assert isinstance(cvd_only, list), "expose_meta=False应返回list"
        assert len(cvd_only) == 3, f"CVD序列长度应为3，实际{len(cvd_only)}"
        print(f"✅ expose_meta=False: 返回CVD序列，长度={len(cvd_only)}")

        # 使用expose_meta（新功能）
        result = cvd_from_klines(test_klines, use_quote=True, expose_meta=True)
        assert isinstance(result, tuple), "expose_meta=True应返回tuple"
        assert len(result) == 2, "应返回(cvd, meta)两个元素"

        cvd, meta = result
        assert isinstance(cvd, list), "cvd应为list"
        assert isinstance(meta, dict), "meta应为dict"
        assert "imbalance_ratios" in meta, "meta应包含imbalance_ratios"

        imbalance_ratios = meta["imbalance_ratios"]
        assert len(imbalance_ratios) == 3, f"imbalance_ratios长度应为3，实际{len(imbalance_ratios)}"

        # 验证边界条件：|ratio| <= 1 + 1e-6
        for i, ratio in enumerate(imbalance_ratios):
            assert abs(ratio) <= 1.0 + 1e-6, \
                f"imbalance_ratio[{i}]={ratio}超出边界[-1, 1]"

        print(f"✅ expose_meta=True: 返回(cvd, meta)")
        print(f"   imbalance_ratios: {[f'{r:.4f}' for r in imbalance_ratios]}")
        print(f"   边界检查通过: 所有ratio ∈ [-1, 1]")

        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_strict_oi_alignment():
    """测试3: 条件2 - 严格OI对齐（取前不取后）"""
    print("\n" + "=" * 60)
    print("测试3: 严格OI对齐（条件2 - 取前不取后）")
    print("=" * 60)

    try:
        from ats_core.utils.cvd_utils import align_oi_to_klines_strict

        # 测试数据：OI时间戳略晚于closeTime
        klines = [
            [1700000000000, 100, 105, 95, 102, 1000, 1700003599999, 100000, 50, 600, 60000, 0],  # closeTime=01:00:00结束
            [1700003600000, 102, 108, 100, 105, 1200, 1700007199999, 120000, 60, 700, 70000, 0],  # closeTime=02:00:00结束
        ]

        oi_hist = [
            {"timestamp": 1700003599000, "sumOpenInterest": 1000.0},  # 稍早（01:00:00前1秒）
            {"timestamp": 1700003600500, "sumOpenInterest": 1100.0},  # 稍晚（01:00:00后0.5秒）
            {"timestamp": 1700007199000, "sumOpenInterest": 1200.0},  # 稍早（02:00:00前1秒）
        ]

        oi_vals, missing_ratio = align_oi_to_klines_strict(oi_hist, klines, tolerance_ms=5000)

        assert len(oi_vals) == 2, f"OI序列长度应为2，实际{len(oi_vals)}"
        assert oi_vals[0] == 1000.0, f"第一个OI应取前值1000.0，实际{oi_vals[0]}"
        assert oi_vals[1] == 1200.0, f"第二个OI应取前值1200.0，实际{oi_vals[1]}"
        assert missing_ratio == 0.0, f"缺失率应为0，实际{missing_ratio}"

        print(f"✅ 取前不取后规则验证通过")
        print(f"   OI对齐结果: {oi_vals}")
        print(f"   缺失率: {missing_ratio:.2%}")

        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_iqr_floor():
    """测试4: 条件3 - IQR护栏"""
    print("\n" + "=" * 60)
    print("测试4: IQR护栏（条件3）")
    print("=" * 60)

    try:
        from ats_core.utils.cvd_utils import compute_dynamic_min_quote_enhanced

        # 构造节假日低成交额场景
        holiday_klines = [
            [t, 100, 105, 95, 102, 100, t+3599999, 10000, 50, 60, 6000, 0]
            for t in range(1700000000000, 1700000000000 + 96 * 3600000, 3600000)
        ]

        # 不启用IQR护栏
        threshold_no_iqr = compute_dynamic_min_quote_enhanced(
            holiday_klines,
            window=96,
            factor=0.05,
            min_fallback=10000,
            enable_iqr_floor=False
        )

        # 启用IQR护栏
        threshold_with_iqr = compute_dynamic_min_quote_enhanced(
            holiday_klines,
            window=96,
            factor=0.05,
            min_fallback=10000,
            enable_iqr_floor=True
        )

        assert threshold_no_iqr >= 10000, f"无IQR护栏阈值应≥fallback"
        assert threshold_with_iqr >= 10000, f"有IQR护栏阈值应≥fallback"

        print(f"✅ IQR护栏验证通过")
        print(f"   无IQR护栏: {threshold_no_iqr:.0f} USDT")
        print(f"   有IQR护栏: {threshold_with_iqr:.0f} USDT")
        print(f"   均≥fallback(10000 USDT)")

        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_degraded_flag():
    """测试5: 条件4 - 降级标记"""
    print("\n" + "=" * 60)
    print("测试5: 降级标记（条件4）")
    print("=" * 60)

    try:
        from ats_core.features.cvd import cvd_combined

        # 构造测试数据
        futures_klines = [
            [t, 100, 105, 95, 102, 1000, t+3599999, 100000, 50, 600, 60000, 0]
            for t in range(1700000000000, 1700000000000 + 10 * 3600000, 3600000)
        ]

        # 测试1: 无现货数据（应该降级）
        result = cvd_combined(
            futures_klines,
            spot_klines=None,
            return_meta=True
        )
        assert isinstance(result, tuple), "return_meta=True应返回tuple"
        assert len(result) == 2, "应返回(cvd, meta)"

        cvd, meta = result
        assert meta["degraded"] == True, "无现货数据应触发degraded=True"
        assert meta["degrade_reason"] == "no_spot_data", f"降级原因应为'no_spot_data'，实际{meta['degrade_reason']}"

        print(f"✅ 降级标记验证通过")
        print(f"   degraded={meta['degraded']}")
        print(f"   degrade_reason='{meta['degrade_reason']}'")
        print(f"   futures_weight={meta['futures_weight']:.2%}")
        print(f"   spot_weight={meta['spot_weight']:.2%}")

        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_unclosed_filter():
    """测试6: 条件5 - 未收盘K线过滤"""
    print("\n" + "=" * 60)
    print("测试6: 未收盘K线过滤（条件5）")
    print("=" * 60)

    try:
        from ats_core.utils.cvd_utils import filter_unclosed_klines

        # 当前时间：01:00:05（刚过01:00）
        now_ms = 1700003605000

        klines = [
            [1699996800000, 100, 105, 95, 102, 1000, 1700000399999, 100000, 50, 600, 60000, 0],  # 00:00-01:00（已收盘）
            [1700000400000, 102, 108, 100, 105, 1200, 1700003999999, 120000, 60, 700, 70000, 0],  # 01:00-02:00（正在形成）
        ]

        filtered, filtered_count = filter_unclosed_klines(klines, now_ms, safety_lag_ms=5000)

        assert len(filtered) == 1, f"应过滤1根K线，保留1根，实际保留{len(filtered)}"
        assert filtered_count == 1, f"过滤计数应为1，实际{filtered_count}"
        assert filtered[0][0] == 1699996800000, "应保留第一根（已收盘）K线"

        print(f"✅ 未收盘K线过滤验证通过")
        print(f"   原始K线数: {len(klines)}")
        print(f"   过滤后: {len(filtered)}")
        print(f"   过滤数量: {filtered_count}")

        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_duplicate_timestamp():
    """测试7: 条件6 - 重复时间戳检测"""
    print("\n" + "=" * 60)
    print("测试7: 重复时间戳检测（条件6）")
    print("=" * 60)

    try:
        from ats_core.utils.cvd_utils import align_klines_by_open_time

        # 构造重复时间戳的K线
        futures_klines = [
            [1700000000000, 100, 105, 95, 102, 1000, 1700003599999, 100000, 50, 600, 60000, 0],
            [1700000000000, 102, 108, 100, 105, 1200, 1700007199999, 120000, 60, 700, 70000, 0],  # 重复！
        ]

        spot_klines = [
            [1700000000000, 100, 105, 95, 102, 1000, 1700003599999, 100000, 50, 600, 60000, 0],
        ]

        try:
            aligned_f, aligned_s, discarded, is_degraded = align_klines_by_open_time(
                futures_klines, spot_klines
            )
            print(f"❌ 重复时间戳未被检测到（应该抛出ValueError）")
            return False
        except ValueError as ve:
            if "重复openTime" in str(ve):
                print(f"✅ 重复时间戳检测验证通过")
                print(f"   正确抛出ValueError: {ve}")
                return True
            else:
                print(f"❌ 抛出了ValueError但原因不对: {ve}")
                return False

    except Exception as e:
        print(f"❌ 测试失败（非预期异常）: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("v7.2.36 CVD增强验证测试")
    print("=" * 60)
    print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    tests = [
        ("导入验证", test_imports),
        ("imbalance_ratio计算", test_imbalance_ratio),
        ("严格OI对齐", test_strict_oi_alignment),
        ("IQR护栏", test_iqr_floor),
        ("降级标记", test_degraded_flag),
        ("未收盘K线过滤", test_unclosed_filter),
        ("重复时间戳检测", test_duplicate_timestamp),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ 测试'{name}'执行失败: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")

    print(f"\n通过: {passed}/{total} ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n🎉 所有测试通过！v7.2.36基础功能验证成功")
        return 0
    else:
        print(f"\n⚠️  {total - passed}个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
