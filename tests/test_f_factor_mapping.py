#!/usr/bin/env python3
# coding: utf-8
"""
F因子数值映射验证测试

目的：验证 fund_leading.py 中的 directional_score 映射逻辑是否正确

验证点：
1. directional_score 返回值范围（0-100，50为中性）
2. (score - 50) * 2 映射到 -100 到 +100 是否对称
3. fund_momentum 和 price_momentum 的范围
4. leading_raw 的范围
5. 最终F因子的范围（-100 到 +100）

预期结果：
- 所有映射应该是对称的（中性点为0）
- 正向和负向应该产生对称的结果
- 边界情况应该被正确处理
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ats_core.features.scoring_utils import directional_score
from ats_core.features.fund_leading import score_fund_leading
import math


def test_directional_score_basic():
    """测试 directional_score 的基本行为"""
    print("=" * 60)
    print("测试1: directional_score 基本行为")
    print("=" * 60)

    # 测试用例：OI变化率评分（neutral=0, scale=3.0）
    # 注意：tanh(1.0) ≈ 0.76，所以 scale=3.0 时，value=3.0 → score=88
    test_cases = [
        (0.0, 50, "中性（0%变化）"),
        (3.0, 88, "+3%变化（明显利好）"),  # tanh(3/3) = tanh(1.0) ≈ 0.76 → 50+50*0.76=88
        (-3.0, 12, "-3%变化（明显不利）"),  # tanh(-1.0) ≈ -0.76 → 50+50*(-0.76)=12
        (6.0, 98, "+6%变化（强烈利好）"),   # tanh(6/3) = tanh(2.0) ≈ 0.96 → 50+50*0.96=98
        (-6.0, 2, "-6%变化（强烈不利）"),   # tanh(-2.0) ≈ -0.96 → 50+50*(-0.96)=2
        (100.0, 100, "极端正向"),
        (-100.0, 0, "极端负向"),
    ]

    all_passed = True
    for value, expected, desc in test_cases:
        score = directional_score(value, neutral=0.0, scale=3.0, min_score=0.0)
        # 允许±2分的误差（由于tanh的非线性）
        passed = abs(score - expected) <= 2
        status = "✅" if passed else "❌"
        print(f"{status} {desc:30s}: value={value:6.1f} → score={score:3d} (期望≈{expected})")
        if not passed:
            all_passed = False

    print()
    return all_passed


def test_symmetric_mapping():
    """测试 (score - 50) * 2 映射的对称性"""
    print("=" * 60)
    print("测试2: (score - 50) * 2 映射对称性")
    print("=" * 60)

    test_values = [0.0, 1.0, 2.0, 3.0, 5.0, 10.0]

    all_passed = True
    for value in test_values:
        # 正向
        score_pos = directional_score(value, neutral=0.0, scale=3.0, min_score=0.0)
        mapped_pos = (score_pos - 50) * 2

        # 负向
        score_neg = directional_score(-value, neutral=0.0, scale=3.0, min_score=0.0)
        mapped_neg = (score_neg - 50) * 2

        # 验证对称性：mapped_pos 应该 ≈ -mapped_neg
        symmetric = abs(mapped_pos + mapped_neg) <= 2
        status = "✅" if symmetric else "❌"

        print(f"{status} value=±{value:4.1f}: "
              f"pos_score={score_pos:3d} → mapped={mapped_pos:+4.0f}, "
              f"neg_score={score_neg:3d} → mapped={mapped_neg:+4.0f}, "
              f"对称性: {mapped_pos + mapped_neg:+.1f} (应该≈0)")

        if not symmetric:
            all_passed = False

    print()
    return all_passed


def test_fund_momentum_range():
    """测试 fund_momentum 的范围"""
    print("=" * 60)
    print("测试3: fund_momentum 范围测试")
    print("=" * 60)

    # 默认权重
    oi_weight = 0.4
    vol_weight = 0.3
    cvd_weight = 0.3

    # 测试极端情况
    test_cases = [
        # (oi_change_pct, vol_ratio, cvd_change, expected_range)
        (0.0, 1.0, 0.0, 0, "全部中性"),
        (10.0, 1.5, 0.05, 100, "全部极端正向"),
        (-10.0, 0.5, -0.05, -100, "全部极端负向"),
    ]

    all_passed = True
    for oi_change, vol_ratio, cvd_change, expected, desc in test_cases:
        oi_score = directional_score(oi_change, neutral=0.0, scale=3.0, min_score=0.0)
        vol_score = directional_score(vol_ratio, neutral=1.0, scale=0.3, min_score=0.0)
        cvd_score = directional_score(cvd_change, neutral=0.0, scale=0.02, min_score=0.0)

        fund_momentum = (
            oi_weight * ((oi_score - 50) * 2) +
            vol_weight * ((vol_score - 50) * 2) +
            cvd_weight * ((cvd_score - 50) * 2)
        )

        # 验证范围：应该在 -100 到 +100 之间
        in_range = -100 <= fund_momentum <= 100
        # 验证符号
        sign_correct = (expected >= 0 and fund_momentum >= 0) or (expected < 0 and fund_momentum < 0) or expected == 0

        passed = in_range and sign_correct
        status = "✅" if passed else "❌"

        print(f"{status} {desc:20s}: "
              f"oi_score={oi_score:3d}, vol_score={vol_score:3d}, cvd_score={cvd_score:3d} "
              f"→ fund_momentum={fund_momentum:+6.1f} (范围OK: {in_range}, 符号OK: {sign_correct})")

        if not passed:
            all_passed = False

    print()
    return all_passed


def test_f_factor_integration():
    """测试完整的F因子计算"""
    print("=" * 60)
    print("测试4: F因子完整计算")
    print("=" * 60)

    # 测试用例：设计不同场景
    test_cases = [
        # (oi, vol_ratio, cvd, price_change, slope, expected_sign, desc)
        (0.0, 1.0, 0.0, 0.0, 0.0, 0, "全部中性 → F≈0"),
        (5.0, 1.3, 0.03, 1.0, 0.01, 1, "资金强价格弱 → F>0（蓄势）"),
        (1.0, 1.1, 0.01, 8.0, 0.03, -1, "资金弱价格强 → F<0（追高）"),
        (-3.0, 0.8, -0.02, -5.0, -0.02, 0, "资金价格同步下跌 → F≈0"),
    ]

    all_passed = True
    for oi, vol_ratio, cvd, price_change, slope, expected_sign, desc in test_cases:
        F, meta = score_fund_leading(
            oi_change_pct=oi,
            vol_ratio=vol_ratio,
            cvd_change=cvd,
            price_change_pct=price_change,
            price_slope=slope
        )

        # 验证范围
        in_range = -100 <= F <= 100

        # 验证符号
        sign_correct = True
        if expected_sign > 0 and F <= 0:
            sign_correct = False
        elif expected_sign < 0 and F >= 0:
            sign_correct = False
        elif expected_sign == 0 and abs(F) > 30:  # 中性允许±30的波动
            sign_correct = False

        passed = in_range and sign_correct
        status = "✅" if passed else "❌"

        print(f"{status} {desc:30s}: F={F:+4d} "
              f"(fund_momentum={meta['fund_momentum']:+6.1f}, "
              f"price_momentum={meta['price_momentum']:+6.1f}, "
              f"leading_raw={meta['leading_raw']:+6.1f})")

        if not passed:
            all_passed = False
            if not in_range:
                print(f"   ❌ 范围错误: F={F} 超出 [-100, 100]")
            if not sign_correct:
                print(f"   ❌ 符号错误: 期望符号={expected_sign}, 实际F={F}")

    print()
    return all_passed


def test_edge_cases():
    """测试边界情况"""
    print("=" * 60)
    print("测试5: 边界情况")
    print("=" * 60)

    test_cases = [
        # 极端正向
        (100.0, 2.0, 0.1, 5.0, 0.05, "极端资金流入，温和价格上涨"),
        # 极端负向
        (-100.0, 0.5, -0.1, -5.0, -0.05, "极端资金流出，价格下跌"),
        # 资金价格极端分歧
        (100.0, 2.0, 0.1, -5.0, -0.05, "资金强烈流入但价格下跌（超强蓄势）"),
        (-100.0, 0.5, -0.1, 10.0, 0.1, "资金流出但价格暴涨（极端追高）"),
    ]

    all_passed = True
    for oi, vol_ratio, cvd, price_change, slope, desc in test_cases:
        F, meta = score_fund_leading(
            oi_change_pct=oi,
            vol_ratio=vol_ratio,
            cvd_change=cvd,
            price_change_pct=price_change,
            price_slope=slope
        )

        # 验证范围（最重要）
        in_range = -100 <= F <= 100
        status = "✅" if in_range else "❌"

        print(f"{status} {desc:50s}: F={F:+4d}")

        if not in_range:
            all_passed = False
            print(f"   ❌ 超出范围！F={F}")

    print()
    return all_passed


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("F因子数值映射验证测试")
    print("=" * 60)
    print()

    results = []

    # 运行所有测试
    results.append(("directional_score 基本行为", test_directional_score_basic()))
    results.append(("对称性映射", test_symmetric_mapping()))
    results.append(("fund_momentum 范围", test_fund_momentum_range()))
    results.append(("F因子完整计算", test_f_factor_integration()))
    results.append(("边界情况", test_edge_cases()))

    # 汇总结果
    print("=" * 60)
    print("测试汇总")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("✅ 所有测试通过！F因子的数值映射逻辑正确。")
        return 0
    else:
        print("❌ 部分测试失败，需要修复映射逻辑。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
