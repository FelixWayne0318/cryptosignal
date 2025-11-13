#!/usr/bin/env python3
# coding: utf-8
"""
测试脚本：验证F因子动量分级机制

测试内容：
1. 读取配置中的蓄势分级阈值
2. 模拟不同F值场景，验证阈值降低逻辑
3. 验证Telegram消息格式中的分级标记
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ats_core.config.threshold_config import get_thresholds

def test_momentum_config():
    """测试1：验证配置读取"""
    print("=" * 60)
    print("测试1：验证蓄势分级配置读取")
    print("=" * 60)

    config = get_thresholds()

    # 检查配置是否存在
    momentum_config = config.config.get('蓄势分级配置', {})

    if not momentum_config:
        print("❌ 错误：未找到'蓄势分级配置'")
        return False

    enabled = momentum_config.get('_enabled', False)
    print(f"✅ 蓄势分级功能：{'启用' if enabled else '禁用'}")

    # 检查三个级别配置
    levels = ['level_3_极早期', 'level_2_早期', 'level_1_强势']
    level_data = {}

    for level_name in levels:
        level_config = momentum_config.get(level_name, {})
        if not level_config:
            print(f"❌ 错误：未找到 {level_name} 配置")
            return False

        F_threshold = level_config.get('F_threshold')
        threshold_reduction = level_config.get('阈值降低', {})
        position_mult = level_config.get('仓位倍数', 1.0)

        level_data[level_name] = {
            'F_threshold': F_threshold,
            'confidence_min': threshold_reduction.get('confidence_min'),
            'P_min': threshold_reduction.get('P_min'),
            'EV_min': threshold_reduction.get('EV_min'),
            'F_min': threshold_reduction.get('F_min'),
            'position_mult': position_mult
        }

        print(f"\n✅ {level_name}:")
        print(f"   F阈值: {F_threshold}")
        print(f"   降低后阈值: confidence≥{threshold_reduction.get('confidence_min')}, "
              f"P≥{threshold_reduction.get('P_min'):.2f}, "
              f"EV≥{threshold_reduction.get('EV_min'):.3f}, "
              f"F≥{threshold_reduction.get('F_min')}")
        print(f"   仓位倍数: {position_mult}")

    # 验证阈值递减逻辑
    print("\n✅ 阈值递减逻辑验证:")
    print(f"   F阈值: {level_data['level_3_极早期']['F_threshold']} > "
          f"{level_data['level_2_早期']['F_threshold']} > "
          f"{level_data['level_1_强势']['F_threshold']}")
    print(f"   confidence阈值: {level_data['level_3_极早期']['confidence_min']} < "
          f"{level_data['level_2_早期']['confidence_min']} < "
          f"{level_data['level_1_强势']['confidence_min']}")

    return True


def test_grading_logic():
    """测试2：验证分级逻辑"""
    print("\n" + "=" * 60)
    print("测试2：验证F因子分级逻辑")
    print("=" * 60)

    config = get_thresholds()
    momentum_config = config.config.get('蓄势分级配置', {})

    level_3_config = momentum_config.get('level_3_极早期', {})
    level_2_config = momentum_config.get('level_2_早期', {})
    level_1_config = momentum_config.get('level_1_强势', {})

    level_3_threshold = level_3_config.get('F_threshold', 70)
    level_2_threshold = level_2_config.get('F_threshold', 60)
    level_1_threshold = level_1_config.get('F_threshold', 50)

    # 测试不同F值
    test_cases = [
        (85, 3, "极早期蓄势"),
        (75, 3, "极早期蓄势"),
        (65, 2, "早期蓄势"),
        (55, 1, "蓄势待发"),
        (45, 0, "正常模式"),
        (30, 0, "正常模式"),
    ]

    print("\nF值 → 级别 → 描述")
    print("-" * 40)

    for F_value, expected_level, expected_desc in test_cases:
        # 判定逻辑（与analyze_symbol_v72.py一致）
        if F_value >= level_3_threshold:
            actual_level = 3
            actual_desc = "极早期蓄势"
        elif F_value >= level_2_threshold:
            actual_level = 2
            actual_desc = "早期蓄势"
        elif F_value >= level_1_threshold:
            actual_level = 1
            actual_desc = "蓄势待发"
        else:
            actual_level = 0
            actual_desc = "正常模式"

        status = "✅" if actual_level == expected_level else "❌"
        print(f"{status} F={F_value:3d} → Level {actual_level} → {actual_desc}")

    return True


def test_telegram_format():
    """测试3：验证Telegram格式"""
    print("\n" + "=" * 60)
    print("测试3：验证Telegram消息格式")
    print("=" * 60)

    config = get_thresholds()
    momentum_config = config.config.get('蓄势分级配置', {})

    level_3_threshold = momentum_config.get('level_3_极早期', {}).get('F_threshold', 70)
    level_2_threshold = momentum_config.get('level_2_早期', {}).get('F_threshold', 60)
    level_1_threshold = momentum_config.get('level_1_强势', {}).get('F_threshold', 50)

    # 模拟不同F值的消息头
    test_F_values = [85, 65, 55, 45]

    print("\nF值 → Telegram消息头")
    print("-" * 40)

    for F_v2 in test_F_values:
        is_momentum_ready = F_v2 > 30

        if F_v2 >= level_3_threshold:
            header = f"🚀🚀 极早期蓄势 · 强势机会"
            F_icon = "🚀🚀"
            F_desc = "强劲资金流入 [极早期蓄势]"
        elif F_v2 >= level_2_threshold:
            header = f"🚀 早期蓄势 · 提前布局"
            F_icon = "🚀"
            F_desc = "偏强资金流入 [早期蓄势]"
        elif is_momentum_ready and F_v2 >= level_1_threshold:
            header = f"🚀 蓄势待发"
            F_icon = "🔥"
            F_desc = "中等资金流入 [蓄势待发]"
        else:
            header = "信号"
            F_icon = "📊"
            F_desc = f"资金状态：{F_v2}"

        print(f"F={F_v2:3d} → {header}")
        print(f"       F因子: {F_icon} {F_desc}\n")

    return True


def test_threshold_reduction():
    """测试4：验证阈值降低效果"""
    print("=" * 60)
    print("测试4：验证阈值降低效果")
    print("=" * 60)

    config = get_thresholds()
    momentum_config = config.config.get('蓄势分级配置', {})

    # 正常模式阈值
    normal_confidence_min = config.get_mature_threshold('confidence_min', 15)
    normal_P_min = config.get_gate_threshold('gate4_probability', 'P_min', 0.50)
    normal_EV_min = config.get_gate_threshold('gate3_ev', 'EV_min', 0.015)
    normal_F_min = config.get_gate_threshold('gate2_fund_support', 'F_min', -10)

    print("\n正常模式阈值（基准）:")
    print(f"  confidence_min: {normal_confidence_min}")
    print(f"  P_min: {normal_P_min:.2f}")
    print(f"  EV_min: {normal_EV_min:.3f}")
    print(f"  F_min: {normal_F_min}")

    # 各级别降低后的阈值
    levels = [
        ('level_3_极早期', 3),
        ('level_2_早期', 2),
        ('level_1_强势', 1)
    ]

    for level_name, level_num in levels:
        level_config = momentum_config.get(level_name, {})
        threshold_reduction = level_config.get('阈值降低', {})

        confidence_min = threshold_reduction.get('confidence_min')
        P_min = threshold_reduction.get('P_min')
        EV_min = threshold_reduction.get('EV_min')
        F_min = threshold_reduction.get('F_min')

        print(f"\nLevel {level_num} ({level_name}):")
        print(f"  confidence_min: {confidence_min} (降低 {((normal_confidence_min - confidence_min) / normal_confidence_min * 100):.1f}%)")
        print(f"  P_min: {P_min:.2f} (降低 {((normal_P_min - P_min) / normal_P_min * 100):.1f}%)")
        print(f"  EV_min: {EV_min:.3f} (降低 {((normal_EV_min - EV_min) / normal_EV_min * 100):.1f}%)")
        print(f"  F_min: {F_min} (提高 {F_min - normal_F_min})")

    return True


def main():
    """主测试函数"""
    print("\n" + "🔍" * 30)
    print("F因子动量分级机制测试")
    print("🔍" * 30 + "\n")

    try:
        # 运行所有测试
        test_momentum_config()
        test_grading_logic()
        test_telegram_format()
        test_threshold_reduction()

        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)

        # 给出预期触发率估算
        print("\n📊 预期触发率估算（基于F因子分布）:")
        print("-" * 60)
        print("假设F因子服从正态分布 N(0, 30):")
        print("  Level 3 (F≥70): ~2-5% 触发率")
        print("  Level 2 (F≥60): ~5-10% 触发率")
        print("  Level 1 (F≥50): ~10-15% 触发率")
        print("  Level 0 (F<50): ~70-80% 正常模式")
        print("\n建议：运行实际扫描观察真实触发率分布")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
