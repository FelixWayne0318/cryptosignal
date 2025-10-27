#!/usr/bin/env python3
# coding: utf-8
"""
测试CVD持续性实现

验证：
1. score_cvd_flow函数是否正确计算持续性
2. telegram_fmt是否正确显示持续性
"""

from ats_core.features.cvd_flow import score_cvd_flow
from ats_core.outputs.telegram_fmt import _desc_cvd_flow

def test_cvd_consistency_implementation():
    print("=" * 70)
    print("测试CVD持续性实现")
    print("=" * 70)

    price = 50000.0
    base = 10000.0

    scenarios = [
        {
            "name": "情况A：持续平稳流入（理想）",
            "cvd": [base + i * 100 for i in range(7)],
            "expected_consistent": True
        },
        {
            "name": "情况B：先跌后涨（不持续）",
            "cvd": [base, base - 100, base - 200, base - 300, base - 200, base + 200, base + 600],
            "expected_consistent": False
        },
        {
            "name": "情况C：前期流入，后期平稳（不持续）",
            "cvd": [base, base + 200, base + 400, base + 600, base + 600, base + 600, base + 600],
            "expected_consistent": False
        },
        {
            "name": "情况D：后期加速流入（持续）",
            "cvd": [base, base + 50, base + 100, base + 200, base + 350, base + 550, base + 850],
            "expected_consistent": True
        },
    ]

    for scenario in scenarios:
        print(f"\n【{scenario['name']}】")
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

        print(f"\n评分结果:")
        print(f"  C分数 = {C:+4d}")
        print(f"  cvd6 = {meta['cvd6'] * 100:+.2f}%")
        print(f"  一致性 = {meta['consistency'] * 100:.1f}%")
        print(f"  R² = {meta['r_squared']:.3f}")
        print(f"  是否持续 = {'✓' if meta['is_consistent'] else '✗'}")

        # 验证持续性判断
        expected = scenario['expected_consistent']
        actual = meta['is_consistent']
        if expected == actual:
            print(f"  ✅ 持续性判断正确（期望={expected}, 实际={actual}）")
        else:
            print(f"  ❌ 持续性判断错误（期望={expected}, 实际={actual}）")

        # 测试Telegram显示
        desc = _desc_cvd_flow(
            C,
            is_long=True,
            cvd6=meta['cvd6'],
            consistency=meta['consistency'],
            is_consistent=meta['is_consistent']
        )
        print(f"\nTelegram显示:")
        print(f"  {desc}")

    print("\n" + "=" * 70)
    print("✅ 测试完成")
    print("=" * 70)

    print("\n【显示效果对比】")
    print("-" * 70)

    # 模拟几种典型情况
    test_displays = [
        {
            "name": "持续流入",
            "C": 85,
            "cvd6": 0.023,
            "consistency": 1.0,
            "is_consistent": True
        },
        {
            "name": "震荡流入",
            "C": 85,
            "cvd6": 0.023,
            "consistency": 0.5,
            "is_consistent": False
        },
        {
            "name": "持续流出",
            "C": -85,
            "cvd6": -0.023,
            "consistency": 0.0,
            "is_consistent": False  # 流出方向需要低一致性
        },
    ]

    for case in test_displays:
        desc = _desc_cvd_flow(
            case["C"],
            is_long=True,
            cvd6=case["cvd6"],
            consistency=case["consistency"],
            is_consistent=case["is_consistent"]
        )
        print(f"\n{case['name']}:")
        print(f"  • 资金流 {case['C']:+4d} —— {desc}")

    print()

if __name__ == "__main__":
    test_cvd_consistency_implementation()
