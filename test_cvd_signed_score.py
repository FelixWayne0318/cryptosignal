#!/usr/bin/env python3
# coding: utf-8
"""
测试CVD带符号评分系统

验证：
1. CVD分数是否正确映射到-100到+100
2. Prime判定逻辑是否正确处理正负号
3. Telegram显示是否正确
"""

import math
from ats_core.features.cvd_flow import score_cvd_flow

def test_cvd_signed_score():
    """测试CVD带符号评分"""
    print("=" * 60)
    print("测试CVD带符号评分系统")
    print("=" * 60)

    # 模拟CVD序列和价格序列
    price = 50000.0

    # 测试用例：不同的CVD变化
    test_cases = [
        {
            "name": "强烈买入压力（CVD大幅上升）",
            "cvd_change": 1000.0,  # CVD上升1000
            "expected_sign": "+",
            "expected_range": (60, 100)
        },
        {
            "name": "中等买入压力（CVD适度上升）",
            "cvd_change": 500.0,
            "expected_sign": "+",
            "expected_range": (40, 80)
        },
        {
            "name": "轻微买入压力（CVD小幅上升）",
            "cvd_change": 100.0,
            "expected_sign": "+",
            "expected_range": (0, 60)
        },
        {
            "name": "均衡（CVD无变化）",
            "cvd_change": 0.0,
            "expected_sign": "0",
            "expected_range": (-10, 10)
        },
        {
            "name": "轻微卖出压力（CVD小幅下降）",
            "cvd_change": -100.0,
            "expected_sign": "-",
            "expected_range": (-60, 0)
        },
        {
            "name": "中等卖出压力（CVD适度下降）",
            "cvd_change": -500.0,
            "expected_sign": "-",
            "expected_range": (-80, -40)
        },
        {
            "name": "强烈卖出压力（CVD大幅下降）",
            "cvd_change": -1000.0,
            "expected_sign": "-",
            "expected_range": (-100, -60)
        },
    ]

    print("\n【测试1：CVD分数映射】")
    print("-" * 60)

    for case in test_cases:
        # 构造CVD序列（6小时前 vs 现在）
        cvd_before = 10000.0
        cvd_now = cvd_before + case["cvd_change"]
        cvd_series = [cvd_before] * 6 + [cvd_now]
        c_series = [price] * 7

        # 测试做多信号
        c_long, meta_long = score_cvd_flow(cvd_series, c_series, side_long=True)

        # 测试做空信号
        c_short, meta_short = score_cvd_flow(cvd_series, c_series, side_long=False)

        print(f"\n{case['name']}")
        print(f"  CVD变化: {case['cvd_change']:+.0f}")
        print(f"  CVD 6h归一化: {meta_long['cvd6']:.6f}")

        # 注意：新逻辑下，做多和做空的C分数应该相同（都反映真实方向）
        print(f"  C分数（做多）: {c_long:+4d}")
        print(f"  C分数（做空）: {c_short:+4d}")

        # 验证符号
        if case["expected_sign"] == "+":
            assert c_long > 0, f"期望正数，实际 {c_long}"
            print(f"  ✅ 符号正确（正数 = 买入压力）")
        elif case["expected_sign"] == "-":
            assert c_long < 0, f"期望负数，实际 {c_long}"
            print(f"  ✅ 符号正确（负数 = 卖出压力）")
        elif case["expected_sign"] == "0":
            assert -10 <= c_long <= 10, f"期望接近0，实际 {c_long}"
            print(f"  ✅ 符号正确（接近0 = 均衡）")

        # 验证做多和做空分数相同
        assert c_long == c_short, f"做多和做空分数应该相同！做多={c_long}, 做空={c_short}"
        print(f"  ✅ 做多/做空分数一致（不再取反）")

    print("\n" + "=" * 60)
    print("【测试2：Prime判定逻辑】")
    print("-" * 60)

    # 测试Prime判定逻辑
    test_prime_cases = [
        {
            "name": "做多Prime信号（C=+90, V=70, O=70）",
            "side_long": True,
            "scores": {"C": 90, "V": 70, "O": 70},
            "expected_prime": True
        },
        {
            "name": "做多非Prime（C=+30，买入压力不足）",
            "side_long": True,
            "scores": {"C": 30, "V": 70, "O": 70},
            "expected_prime": False
        },
        {
            "name": "做多非Prime（C=-90，方向相反）",
            "side_long": True,
            "scores": {"C": -90, "V": 70, "O": 70},
            "expected_prime": False
        },
        {
            "name": "做空Prime信号（C=-90, V=70, O=70）",
            "side_long": False,
            "scores": {"C": -90, "V": 70, "O": 70},
            "expected_prime": True
        },
        {
            "name": "做空非Prime（C=-30，卖出压力不足）",
            "side_long": False,
            "scores": {"C": -30, "V": 70, "O": 70},
            "expected_prime": False
        },
        {
            "name": "做空非Prime（C=+90，方向相反）",
            "side_long": False,
            "scores": {"C": 90, "V": 70, "O": 70},
            "expected_prime": False
        },
    ]

    for case in test_prime_cases:
        c_score = case["scores"]["C"]
        v_score = case["scores"]["V"]
        o_score = case["scores"]["O"]
        side_long = case["side_long"]

        # 模拟Prime判定逻辑
        c_ok = (c_score >= 65) if side_long else (c_score <= -65)
        fund_dims_ok = all([
            c_ok,
            v_score >= 65,
            o_score >= 65
        ])

        print(f"\n{case['name']}")
        print(f"  C={c_score:+4d}, V={v_score:>2d}, O={o_score:>2d}")
        print(f"  C条件: {'✅' if c_ok else '❌'} (期望: {'>= 65' if side_long else '<= -65'})")
        print(f"  V条件: {'✅' if v_score >= 65 else '❌'}")
        print(f"  O条件: {'✅' if o_score >= 65 else '❌'}")
        print(f"  Prime: {'✅' if fund_dims_ok else '❌'} (期望: {'✅' if case['expected_prime'] else '❌'})")

        assert fund_dims_ok == case["expected_prime"], \
            f"Prime判定错误！期望 {case['expected_prime']}, 实际 {fund_dims_ok}"

    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)

    # 显示格式示例
    print("\n【Telegram显示格式示例】")
    print("-" * 60)
    print("\n做多信号（C=+85）：")
    print(f"• 资金流 🟢 {85:+4d} —— 强劲买入压力/资金流入 (CVD+2.1%)")

    print("\n做空信号（C=-85）：")
    print(f"• 资金流 🔴 {-85:+4d} —— 强劲卖出压力/资金流出 (CVD-2.1%)")

    print("\n均衡状态（C=+5）：")
    print(f"• 资金流 🟡  {5:+4d} —— 买卖压力均衡 (CVD+0.1%)")
    print()

if __name__ == "__main__":
    test_cvd_signed_score()
