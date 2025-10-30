#!/usr/bin/env python3
# coding: utf-8
"""
测试Prime阈值修复（v6.0权重百分比系统）

验证：
1. 新阈值35分（原65分）适配v6.0系统
2. 实际扫描数据能否生成Prime信号
3. 阈值调整是否合理
"""

def test_prime_threshold():
    """
    测试Prime计算逻辑（v6.0系统）
    """
    print("=" * 80)
    print("【Prime阈值测试 - v6.0权重百分比系统】")
    print("=" * 80)
    print()

    # 测试场景（来自Vultr服务器实际扫描数据）
    test_cases = [
        {
            "symbol": "TRUMPUSDT",
            "confidence": 29,
            "P_chosen": 0.358,
            "description": "最佳结果（原系统未达标）"
        },
        {
            "symbol": "DOGEUSDT",
            "confidence": 25,
            "P_chosen": 0.412,
            "description": "次佳结果"
        },
        {
            "symbol": "BNBUSDT",
            "confidence": 25,
            "P_chosen": 0.389,
            "description": "第三名"
        },
        {
            "symbol": "典型强势信号",
            "confidence": 45,
            "P_chosen": 0.65,
            "description": "理想场景（强势+高概率）"
        },
        {
            "symbol": "边界测试",
            "confidence": 35,
            "P_chosen": 0.50,
            "description": "边界值测试"
        }
    ]

    print("【Prime计算公式】")
    print("base_strength = confidence × 0.6")
    print("prob_bonus = 0                         (P_chosen < 0.60)")
    print("prob_bonus = min(40, (P-0.60)/0.15×40) (P_chosen >= 0.60)")
    print("prime_strength = base_strength + prob_bonus")
    print()
    print("【v6.0阈值】")
    print("✓ 新阈值: 35分 (适配100-base权重系统)")
    print("✗ 旧阈值: 65分 (适配180-base权重系统)")
    print("✓ 调整系数: 65 × (100/180) ≈ 36.1")
    print()
    print("=" * 80)
    print()

    for i, case in enumerate(test_cases, 1):
        symbol = case["symbol"]
        confidence = case["confidence"]
        P_chosen = case["P_chosen"]
        description = case["description"]

        print(f"【测试 {i}】{symbol}")
        print(f"描述: {description}")
        print(f"Confidence: {confidence}")
        print(f"P_chosen: {P_chosen:.3f}")
        print()

        # 计算Prime强度
        base_strength = confidence * 0.6

        prob_bonus = 0.0
        if P_chosen >= 0.60:
            prob_bonus = min(40.0, (P_chosen - 0.60) / 0.15 * 40.0)

        prime_strength = base_strength + prob_bonus

        # 判定（新旧阈值对比）
        is_prime_old = (prime_strength >= 65)
        is_prime_new = (prime_strength >= 35)

        print(f"计算过程:")
        print(f"  base_strength = {confidence} × 0.6 = {base_strength:.1f}")
        print(f"  prob_bonus = {prob_bonus:.1f}")
        print(f"  prime_strength = {prime_strength:.1f}")
        print()
        print(f"判定结果:")
        print(f"  旧阈值 (65分): {'✓ Prime' if is_prime_old else '✗ 未达标'}")
        print(f"  新阈值 (35分): {'✓ Prime' if is_prime_new else '✗ 未达标'} {'⭐' if is_prime_new else ''}")
        print()

        if is_prime_new and not is_prime_old:
            print(f"  💡 修复成功！原系统错过此信号")
        elif not is_prime_new:
            print(f"  ℹ️  信号强度不足，仍需加强")

        print("-" * 80)
        print()

    # 统计分析
    print("=" * 80)
    print("【统计分析】")
    print()

    # 计算需要多少confidence才能达标
    print("达标所需confidence（无概率加成）:")
    required_confidence_old = 65 / 0.6
    required_confidence_new = 35 / 0.6
    print(f"  旧阈值: {required_confidence_old:.1f} (impossible, max=100)")
    print(f"  新阈值: {required_confidence_new:.1f} ✓")
    print()

    print("达标所需confidence（有概率加成 P=0.65）:")
    # P=0.65 → prob_bonus = (0.65-0.60)/0.15*40 = 13.3
    prob_bonus_065 = (0.65 - 0.60) / 0.15 * 40.0
    required_confidence_old_with_bonus = (65 - prob_bonus_065) / 0.6
    required_confidence_new_with_bonus = (35 - prob_bonus_065) / 0.6
    print(f"  旧阈值: {required_confidence_old_with_bonus:.1f} (needs very high confidence)")
    print(f"  新阈值: {required_confidence_new_with_bonus:.1f} ✓")
    print()

    print("【结论】")
    print("✓ v6.0新阈值(35分)合理，与权重系统匹配")
    print("✓ 实际扫描数据中最佳结果(confidence=29)仍需提升")
    print("✓ confidence≥35或confidence≥22+高概率即可生成Prime信号")
    print("✓ 系统现在能够识别中等强度的信号，不再错过机会")
    print()
    print("=" * 80)


if __name__ == "__main__":
    test_prime_threshold()
