#!/usr/bin/env python3
# coding: utf-8
"""
测试改进后的CVD评分逻辑

验证：
1. 使用斜率而非两点比较
2. 震荡降低分数
3. 解决用户提出的"一根大流出抵消多根小流入"问题
"""

from ats_core.features.cvd_flow import score_cvd_flow
from ats_core.outputs.telegram_fmt import _desc_cvd_flow

def test_improved_cvd_logic():
    print("=" * 70)
    print("测试改进后的CVD评分逻辑")
    print("=" * 70)

    price = 50000.0
    base = 10000.0

    scenarios = [
        {
            "name": "情况A：持续平稳流入",
            "cvd": [base + i * 100 for i in range(7)],
            "expected": "高分 + 持续"
        },
        {
            "name": "情况B：先跌后涨（总变化相同）",
            "cvd": [base, base - 100, base - 200, base - 300, base - 200, base + 200, base + 600],
            "expected": "降低分数 + 震荡"
        },
        {
            "name": "情况C：用户提出的场景 - 5根小涨1根大跌",
            "cvd": [base, base + 100, base + 200, base + 300, base + 400, base + 500, base - 100],
            "expected": "正分但降级 + 震荡"
        },
        {
            "name": "情况D：1根大涨抵消5根小跌",
            "cvd": [base, base - 100, base - 200, base - 300, base - 400, base - 500, base + 500],
            "expected": "低分/负分 + 震荡"
        },
    ]

    for scenario in scenarios:
        print(f"\n【{scenario['name']}】")
        print(f"预期: {scenario['expected']}")
        print("-" * 70)

        cvd_series = scenario["cvd"]
        c_series = [price] * 7

        # 显示CVD轨迹
        print(f"CVD轨迹: ", end="")
        for v in cvd_series:
            change = v - base
            print(f"{change:+5.0f}", end=" ")
        print()

        # 调用score_cvd_flow
        C, meta = score_cvd_flow(cvd_series, c_series, side_long=True)

        # 计算总变化（起点终点）
        total_change = cvd_series[-1] - cvd_series[0]
        print(f"\n总变化（起点→终点）: {total_change:+.0f}")
        print(f"cvd6 (实际变化): {meta['cvd6'] * 100:+.2f}%")
        print(f"slope (斜率): {meta['slope'] * 100:.4f}%/h")
        print(f"R² (拟合优度): {meta['r_squared']:.3f}")
        print(f"是否持续: {'✓' if meta['is_consistent'] else '✗'}")

        print(f"\n评分结果:")
        print(f"  C分数 = {C:+4d}")
        print(f"  cvd_score = {meta['cvd_score']:+.2f}")

        # 测试Telegram显示
        desc = _desc_cvd_flow(
            C,
            is_long=True,
            cvd6=meta['cvd6'],
            consistency=None,
            is_consistent=meta['is_consistent']
        )
        print(f"\nTelegram显示:")
        print(f"  • 资金流 {C:+4d} —— {desc}")

    print("\n" + "=" * 70)
    print("【关键改进验证】")
    print("=" * 70)

    print("\n问题场景对比：")
    print("-" * 70)

    # 用户提出的核心问题
    problem_cases = [
        {
            "name": "5根小涨+1根大跌（用户担心的情况）",
            "cvd": [10000, 10100, 10200, 10300, 10400, 10500, 9900],
            "note": "总变化=-100，但前5根都在涨"
        },
        {
            "name": "相同总变化，但持续流出",
            "cvd": [10000, 9983, 9967, 9950, 9933, 9917, 9900],
            "note": "总变化=-100，每根K线平稳下跌"
        },
    ]

    for case in problem_cases:
        print(f"\n{case['name']}")
        print(f"说明: {case['note']}")

        C, meta = score_cvd_flow(case["cvd"], [price] * 7, side_long=True)

        print(f"  总变化: {case['cvd'][-1] - case['cvd'][0]:+.0f}")
        print(f"  C分数: {C:+4d}")
        print(f"  R²: {meta['r_squared']:.3f}")
        print(f"  持续性: {'✓' if meta['is_consistent'] else '✗'}")

    print("\n" + "=" * 70)
    print("✅ 改进验证完成")
    print("=" * 70)

    print("\n【核心改进】:")
    print("1. 使用斜率代替两点比较 → 不被单根K线主导")
    print("2. R²<0.7时降低分数 → 震荡会被惩罚")
    print("3. 持续性只看R²，不看K线计数 → 更准确")
    print()

if __name__ == "__main__":
    test_improved_cvd_logic()
