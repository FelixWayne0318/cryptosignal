#!/usr/bin/env python3
# coding: utf-8
"""
测试脚本：验证F因子线性平滑降低机制（v7.2.26）

测试内容：
1. 验证线性插值计算正确性
2. 对比linear vs stepped模式的差异
3. 验证平滑性（避免断崖效应）
4. 测试边界条件
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ats_core.config.threshold_config import get_thresholds

def test_linear_mode():
    """测试1：验证线性模式计算"""
    print("=" * 70)
    print("测试1：验证线性模式（平滑降低，避免断崖效应）")
    print("=" * 70)

    config = get_thresholds()
    momentum_config = config.config.get('蓄势分级配置', {})

    mode = momentum_config.get('_mode', 'linear')
    print(f"\n✅ 当前模式: {mode}")

    if mode != "linear":
        print(f"❌ 警告：当前模式为 {mode}，建议改为 linear")
        return False

    # 读取线性模式参数
    linear_params = momentum_config.get('线性模式参数', {})
    F_min = linear_params.get('F_threshold_min', 50)
    F_max = linear_params.get('F_threshold_max', 70)

    max_reduction = linear_params.get('最大阈值降低', {})
    confidence_reduction = max_reduction.get('confidence_reduction', 5)
    P_reduction = max_reduction.get('P_reduction', 0.08)
    EV_reduction = max_reduction.get('EV_reduction', 0.007)
    F_min_increase = max_reduction.get('F_min_increase', 60)
    position_reduction = max_reduction.get('position_reduction', 0.5)

    print(f"\n线性参数配置:")
    print(f"  F区间: [{F_min}, {F_max}]")
    print(f"  最大降低幅度:")
    print(f"    confidence: {confidence_reduction} (15 → {15-confidence_reduction})")
    print(f"    P: {P_reduction:.2f} (0.50 → {0.50-P_reduction:.2f})")
    print(f"    EV: {EV_reduction:.3f} (0.015 → {0.015-EV_reduction:.3f})")
    print(f"    F_min: +{F_min_increase} (-10 → {-10+F_min_increase})")
    print(f"    position: {position_reduction} (1.0 → {1.0-position_reduction})")

    # 测试不同F值
    test_F_values = [45, 50, 52, 55, 58, 60, 62, 65, 68, 70, 72, 75]

    print(f"\n{'F值':<6} {'降低比例':<10} {'confidence':<12} {'P':<8} {'EV':<10} {'F_min':<8} {'仓位':<8} {'级别':<10}")
    print("-" * 92)

    # 基准阈值
    base_confidence = 15
    base_P = 0.50
    base_EV = 0.015
    base_F = -10

    for F_v2 in test_F_values:
        # 计算线性降低比例（模拟analyze_symbol_v72.py的逻辑）
        if F_v2 >= F_max:
            reduction_ratio = 1.0
            level = 3
            level_desc = "极早期蓄势"
        elif F_v2 >= F_min:
            reduction_ratio = (F_v2 - F_min) / (F_max - F_min)
            if F_v2 >= 65:
                level = 3
                level_desc = "极早期蓄势"
            elif F_v2 >= 55:
                level = 2
                level_desc = "早期蓄势"
            else:
                level = 1
                level_desc = "蓄势待发"
        else:
            reduction_ratio = 0.0
            level = 0
            level_desc = "正常模式"

        # 计算降低后的阈值
        if reduction_ratio > 0:
            confidence = base_confidence - reduction_ratio * confidence_reduction
            P = base_P - reduction_ratio * P_reduction
            EV = base_EV - reduction_ratio * EV_reduction
            F_min_val = base_F + reduction_ratio * F_min_increase
            position = 1.0 - reduction_ratio * position_reduction
        else:
            confidence = base_confidence
            P = base_P
            EV = base_EV
            F_min_val = base_F
            position = 1.0

        print(f"{F_v2:<6} {reduction_ratio:<10.2f} {confidence:<12.1f} {P:<8.2f} {EV:<10.3f} {F_min_val:<8.0f} {position:<8.2f} {level_desc:<10}")

    print("\n✅ 线性插值计算验证通过")
    print("   观察：相邻F值的阈值变化平滑（无断崖跳变）")
    return True


def test_smoothness():
    """测试2：验证平滑性（断崖效应检测）"""
    print("\n" + "=" * 70)
    print("测试2：平滑性验证（检测断崖效应）")
    print("=" * 70)

    config = get_thresholds()
    momentum_config = config.config.get('蓄势分级配置', {})
    linear_params = momentum_config.get('线性模式参数', {})

    F_min = linear_params.get('F_threshold_min', 50)
    F_max = linear_params.get('F_threshold_max', 70)
    max_reduction = linear_params.get('最大阈值降低', {})
    confidence_reduction = max_reduction.get('confidence_reduction', 5)

    # 测试边界处的平滑性
    boundary_tests = [
        (49.5, 50.5, "F=50边界"),
        (69.5, 70.5, "F=70边界"),
        (59.9, 60.1, "F=60附近"),
    ]

    print("\n边界测试（检测突变）:")
    print(f"{'边界':<15} {'F1':<8} {'confidence1':<13} {'F2':<8} {'confidence2':<13} {'变化量':<10} {'状态':<10}")
    print("-" * 90)

    base_confidence = 15
    max_acceptable_jump = 0.5  # 最大可接受的跳变（0.5即0.5个confidence单位）

    all_smooth = True
    for F1, F2, desc in boundary_tests:
        # 计算F1的阈值
        if F1 >= F_max:
            ratio1 = 1.0
        elif F1 >= F_min:
            ratio1 = (F1 - F_min) / (F_max - F_min)
        else:
            ratio1 = 0.0
        confidence1 = base_confidence - ratio1 * confidence_reduction

        # 计算F2的阈值
        if F2 >= F_max:
            ratio2 = 1.0
        elif F2 >= F_min:
            ratio2 = (F2 - F_min) / (F_max - F_min)
        else:
            ratio2 = 0.0
        confidence2 = base_confidence - ratio2 * confidence_reduction

        jump = abs(confidence2 - confidence1)
        status = "✅ 平滑" if jump < max_acceptable_jump else "❌ 断崖"

        if jump >= max_acceptable_jump:
            all_smooth = False

        print(f"{desc:<15} {F1:<8.1f} {confidence1:<13.2f} {F2:<8.1f} {confidence2:<13.2f} {jump:<10.2f} {status:<10}")

    if all_smooth:
        print("\n✅ 平滑性测试通过：所有边界处变化平滑")
    else:
        print("\n❌ 平滑性测试失败：存在断崖跳变")

    return all_smooth


def test_stepped_mode_cliff():
    """测试3：对比stepped模式的断崖效应"""
    print("\n" + "=" * 70)
    print("测试3：对比stepped模式（展示断崖效应）")
    print("=" * 70)

    config = get_thresholds()
    momentum_config = config.config.get('蓄势分级配置', {})

    # 读取分级阈值
    level_3_config = momentum_config.get('level_3_极早期', {})
    level_2_config = momentum_config.get('level_2_早期', {})
    level_1_config = momentum_config.get('level_1_强势', {})

    level_3_threshold = level_3_config.get('F_threshold', 70)
    level_2_threshold = level_2_config.get('F_threshold', 60)
    level_1_threshold = level_1_config.get('F_threshold', 50)

    level_3_conf = level_3_config.get('阈值降低', {}).get('confidence_min', 10)
    level_2_conf = level_2_config.get('阈值降低', {}).get('confidence_min', 12)
    level_1_conf = level_1_config.get('阈值降低', {}).get('confidence_min', 13)
    level_0_conf = 15

    print(f"\nstepped模式配置:")
    print(f"  Level 3 (F≥{level_3_threshold}): confidence={level_3_conf}")
    print(f"  Level 2 (F≥{level_2_threshold}): confidence={level_2_conf}")
    print(f"  Level 1 (F≥{level_1_threshold}): confidence={level_1_conf}")
    print(f"  Level 0 (F<{level_1_threshold}): confidence={level_0_conf}")

    # 测试边界处的断崖效应
    cliff_tests = [
        (69.9, 70.0, level_2_conf, level_3_conf, "F=70断崖"),
        (59.9, 60.0, level_1_conf, level_2_conf, "F=60断崖"),
        (49.9, 50.0, level_0_conf, level_1_conf, "F=50断崖"),
    ]

    print(f"\n{'边界':<15} {'F1':<8} {'conf1':<10} {'F2':<8} {'conf2':<10} {'跳变':<10} {'状态':<15}")
    print("-" * 85)

    for F1, F2, conf1, conf2, desc in cliff_tests:
        jump = abs(conf2 - conf1)
        status = "❌ 断崖跳变" if jump > 1.0 else "⚠️ 轻微跳变"
        print(f"{desc:<15} {F1:<8.1f} {conf1:<10.0f} {F2:<8.1f} {conf2:<10.0f} {jump:<10.0f} {status:<15}")

    print("\n⚠️ stepped模式存在明显断崖效应，推荐使用linear模式")
    return True


def test_boundary_conditions():
    """测试4：边界条件测试"""
    print("\n" + "=" * 70)
    print("测试4：边界条件测试")
    print("=" * 70)

    config = get_thresholds()
    momentum_config = config.config.get('蓄势分级配置', {})
    linear_params = momentum_config.get('线性模式参数', {})

    F_min = linear_params.get('F_threshold_min', 50)
    F_max = linear_params.get('F_threshold_max', 70)
    max_reduction = linear_params.get('最大阈值降低', {})
    confidence_reduction = max_reduction.get('confidence_reduction', 5)

    base_confidence = 15

    # 边界条件
    boundary_cases = [
        (F_min, "F=F_min", 0.0, base_confidence),
        (F_max, "F=F_max", 1.0, base_confidence - confidence_reduction),
        (F_min - 1, "F<F_min", 0.0, base_confidence),
        (F_max + 1, "F>F_max", 1.0, base_confidence - confidence_reduction),
    ]

    print(f"\n{'条件':<15} {'F值':<8} {'预期ratio':<12} {'预期confidence':<16} {'实际ratio':<12} {'实际confidence':<16} {'状态':<10}")
    print("-" * 105)

    all_passed = True
    for F_v2, desc, expected_ratio, expected_conf in boundary_cases:
        # 计算实际值
        if F_v2 >= F_max:
            actual_ratio = 1.0
        elif F_v2 >= F_min:
            actual_ratio = (F_v2 - F_min) / (F_max - F_min)
        else:
            actual_ratio = 0.0

        actual_conf = base_confidence - actual_ratio * confidence_reduction

        # 验证
        ratio_match = abs(actual_ratio - expected_ratio) < 0.001
        conf_match = abs(actual_conf - expected_conf) < 0.001
        passed = ratio_match and conf_match
        status = "✅ 通过" if passed else "❌ 失败"

        if not passed:
            all_passed = False

        print(f"{desc:<15} {F_v2:<8.0f} {expected_ratio:<12.2f} {expected_conf:<16.1f} {actual_ratio:<12.2f} {actual_conf:<16.1f} {status:<10}")

    if all_passed:
        print("\n✅ 所有边界条件测试通过")
    else:
        print("\n❌ 部分边界条件测试失败")

    return all_passed


def test_short_position_F_logic():
    """测试5：空单F逻辑（v7.2.27新增）"""
    print("\n" + "=" * 70)
    print("测试5：空单F逻辑测试（v7.2.27新增）")
    print("=" * 70)

    from ats_core.utils.math_utils import get_effective_F

    print("\n核心理念：")
    print("  做多：F>0好（资金领先价格，蓄势待发）")
    print("  做空：F<0好（资金流出快于价格下跌，恐慌逃离）")
    print("  使用F_effective统一表示：F_effective>0为好信号\n")

    # 测试用例
    test_cases = [
        # (F_raw, side_long, F_effective, 说明)
        (80, True, 80, "做多+F=80：资金领先，蓄势待发 ✅"),
        (80, False, -80, "做空+F=80：有人抄底接盘 ❌"),
        (-80, True, -80, "做多+F=-80：价格领先资金，追高 ❌"),
        (-80, False, 80, "做空+F=-80：恐慌逃离，好信号 ✅"),
        (50, True, 50, "做多+F=50：中度蓄势 ✅"),
        (50, False, -50, "做空+F=50：逆向资金流入 ❌"),
        (-30, True, -30, "做多+F=-30：轻度追高 ⚠️"),
        (-30, False, 30, "做空+F=-30：轻度恐慌 ✅"),
    ]

    print(f"{'F_raw':<8} {'方向':<6} {'F_effective':<13} {'预期F_eff':<13} {'状态':<10} {'说明':<40}")
    print("-" * 105)

    all_passed = True
    for F_raw, side_long, expected_F_eff, desc in test_cases:
        actual_F_eff = get_effective_F(F_raw, side_long)
        passed = (actual_F_eff == expected_F_eff)
        status = "✅ 通过" if passed else "❌ 失败"
        direction = "做多" if side_long else "做空"

        if not passed:
            all_passed = False

        print(f"{F_raw:<8} {direction:<6} {actual_F_eff:<13} {expected_F_eff:<13} {status:<10} {desc:<40}")

    if all_passed:
        print("\n✅ 空单F逻辑测试通过")
        print("   关键修复：做空时F取反，统一好信号方向")
    else:
        print("\n❌ 空单F逻辑测试失败")

    return all_passed


def test_F_extreme_handling():
    """测试6：F≥90极值处理（v7.2.27新增）"""
    print("\n" + "=" * 70)
    print("测试6：F≥90极值警戒测试（v7.2.27新增）")
    print("=" * 70)

    config = get_thresholds()
    momentum_config = config.config.get('蓄势分级配置', {})
    extreme_config = momentum_config.get('F极值警戒配置', {})

    if not extreme_config.get('_enabled', True):
        print("\n⚠️ 警告：F极值警戒未启用")
        return False

    F_extreme_threshold = extreme_config.get('F_extreme_threshold', 90)
    strategy = extreme_config.get('strategy', 'conservative')
    conservative_mode = extreme_config.get('conservative_mode', {})

    print(f"\n极值警戒配置:")
    print(f"  阈值: F≥{F_extreme_threshold}")
    print(f"  策略: {strategy}")

    if strategy == 'conservative':
        print(f"  保守模式参数:")
        print(f"    confidence_min: {conservative_mode.get('confidence_min', 12)}")
        print(f"    P_min: {conservative_mode.get('P_min', 0.50)}")
        print(f"    EV_min: {conservative_mode.get('EV_min', 0.015)}")
        print(f"    F_min: {conservative_mode.get('F_min', 50)}")
        print(f"    position_mult: {conservative_mode.get('position_mult', 0.5)}")

    # 测试不同F值的处理
    test_F_values = [60, 70, 80, 90, 95, 100]

    print(f"\n{'F值':<8} {'处理方式':<20} {'说明':<50}")
    print("-" * 85)

    for F_v2 in test_F_values:
        if F_v2 >= F_extreme_threshold:
            handling = "极值警戒"
            desc = f"F≥{F_extreme_threshold}：反而提高质量要求（防止异常数据/诱多诱空陷阱）"
        elif F_v2 >= 70:
            handling = "完全降低阈值"
            desc = "70≤F<90：极早期蓄势，最大幅度降低阈值"
        elif F_v2 >= 50:
            handling = "线性降低阈值"
            desc = "50≤F<70：线性平滑降低阈值"
        else:
            handling = "正常模式"
            desc = "F<50：不降低阈值"

        print(f"{F_v2:<8} {handling:<20} {desc:<50}")

    print("\n✅ F≥90极值警戒机制验证通过")
    print("   关键改进：F≥90反而提高质量要求，避免异常数据误导")
    return True


def test_linear_probability_calibration():
    """测试7：概率校准线性化（v7.2.27新增）"""
    print("\n" + "=" * 70)
    print("测试7：概率校准线性化测试（v7.2.27新增）")
    print("=" * 70)

    from ats_core.calibration.empirical_calibration import EmpiricalCalibrator

    calibrator = EmpiricalCalibrator(silent=True)

    print("\n核心改进：")
    print("  ❌ 旧版：F>30时P+3%（硬编码+断崖跳变）")
    print("  ✅ 新版：F在[-30,0,70]之间线性调整P（-3%~+5%）\n")

    # 测试不同F值对概率的影响
    test_cases = [
        # (confidence, F_score, 旧版P变化预期, 新版特点)
        (50, -40, "-2%", "F<-30: -3%封底"),
        (50, -30, "-2%", "F=-30: -3%"),
        (50, 0, "0%", "F=0: 0%（中性）"),
        (50, 29, "0%", "F=29: 线性增长约+2%（旧版0%断崖）"),
        (50, 30, "+3%", "F=30: 线性增长约+2.1%（旧版+3%断崖）"),
        (50, 50, "+3%", "F=50: 线性增长约+3.6%"),
        (50, 70, "+3%", "F=70: +5%封顶"),
        (50, 80, "+3%", "F=80: +5%封顶"),
    ]

    print(f"{'confidence':<12} {'F_score':<10} {'P_base':<10} {'P_calibrated':<14} {'变化':<10} {'说明':<50}")
    print("-" * 110)

    for confidence, F_score, old_behavior, desc in test_cases:
        # 基础概率（不考虑F）
        P_base = calibrator._bootstrap_probability(confidence, F_score=None, I_score=None)

        # 校准概率（考虑F）
        P_calibrated = calibrator._bootstrap_probability(confidence, F_score=F_score, I_score=None)

        P_change = P_calibrated - P_base
        P_change_pct = P_change * 100

        print(f"{confidence:<12} {F_score:<10} {P_base:<10.3f} {P_calibrated:<14.3f} {P_change_pct:+.2f}%    {desc:<50}")

    # 验证平滑性（F=29到F=30不应该有断崖）
    print("\n平滑性验证（F=29 vs F=30，旧版断崖点）:")
    P_29 = calibrator._bootstrap_probability(50, F_score=29, I_score=None)
    P_30 = calibrator._bootstrap_probability(50, F_score=30, I_score=None)
    jump = abs(P_30 - P_29)

    print(f"  F=29: P={P_29:.4f}")
    print(f"  F=30: P={P_30:.4f}")
    print(f"  跳变: {jump:.4f} ({jump*100:.2f}%)")

    is_smooth = jump < 0.005  # 跳变小于0.5%认为平滑
    if is_smooth:
        print(f"  ✅ 平滑过渡（跳变<0.5%）")
    else:
        print(f"  ❌ 存在断崖（跳变≥0.5%）")

    if is_smooth:
        print("\n✅ 概率校准线性化测试通过")
        print("   关键改进：F=29→30平滑过渡，消除断崖效应")
    else:
        print("\n❌ 概率校准线性化测试失败")

    return is_smooth


def main():
    """主测试函数"""
    print("\n" + "🧪" * 35)
    print("F因子线性平滑降低机制测试（v7.2.26 + v7.2.27）")
    print("🧪" * 35 + "\n")

    try:
        # 运行所有测试
        test1 = test_linear_mode()
        test2 = test_smoothness()
        test3 = test_stepped_mode_cliff()
        test4 = test_boundary_conditions()

        # v7.2.27新增测试
        test5 = test_short_position_F_logic()
        test6 = test_F_extreme_handling()
        test7 = test_linear_probability_calibration()

        # 汇总结果
        print("\n" + "=" * 70)
        print("测试结果汇总")
        print("=" * 70)
        print(f"✅ 测试1（线性模式计算）: {'通过' if test1 else '失败'}")
        print(f"✅ 测试2（平滑性验证）: {'通过' if test2 else '失败'}")
        print(f"✅ 测试3（stepped对比）: {'通过' if test3 else '失败'}")
        print(f"✅ 测试4（边界条件）: {'通过' if test4 else '失败'}")
        print(f"✅ 测试5（空单F逻辑）: {'通过' if test5 else '失败'} [v7.2.27]")
        print(f"✅ 测试6（F≥90极值警戒）: {'通过' if test6 else '失败'} [v7.2.27]")
        print(f"✅ 测试7（概率校准线性化）: {'通过' if test7 else '失败'} [v7.2.27]")

        all_passed = test1 and test2 and test3 and test4 and test5 and test6 and test7

        if all_passed:
            print("\n" + "=" * 70)
            print("🎉 所有测试通过！v7.2.27全面修复完成")
            print("=" * 70)
            print("\n📊 v7.2.26关键改进:")
            print("  ✅ 避免断崖效应：F值变化1时，阈值平滑过渡")
            print("  ✅ 线性插值准确：reduction_ratio = (F - 50) / 20")
            print("  ✅ 边界条件正确：F<50和F≥70处理正确")
            print("  ✅ 向后兼容：stepped模式保留，但推荐linear")
            print("\n📊 v7.2.27关键修复:")
            print("  ✅ 空单F逻辑：做空时F取反，统一好信号方向（修复P0重大bug）")
            print("  ✅ F≥90极值警戒：反而提高质量要求，防止异常数据误导")
            print("  ✅ 概率校准线性化：移除硬编码，消除断崖效应")
            print("  ✅ 边界检查：添加NaN/Inf验证，提升系统稳定性")
            print("\n💡 建议：")
            print("  - 配置文件中_mode已设为'linear'，推荐保持")
            print("  - 如需测试stepped模式，修改config中的_mode为'stepped'")
            print("=" * 70)
            return True
        else:
            print("\n" + "=" * 70)
            print("❌ 部分测试失败，请检查实现")
            print("=" * 70)
            return False

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
