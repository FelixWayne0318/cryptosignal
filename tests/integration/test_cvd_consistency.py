#!/usr/bin/env python3
# coding: utf-8
"""
测试CVD持续性问题

验证：
1. 当前两点比较法的局限性
2. 持续流入 vs 突然流入 的区别
3. 改进方案：斜率+一致性
"""

import math

def current_method(cvd_series, price):
    """当前方法：两点比较"""
    cvd6 = (cvd_series[-1] - cvd_series[-7]) / price
    return cvd6

def improved_method(cvd_series, price):
    """改进方法：斜率+一致性"""
    # 1. 总变化（和当前方法一样）
    cvd_change = cvd_series[-1] - cvd_series[-7]
    cvd6 = cvd_change / price

    # 2. 计算斜率（线性回归）
    n = len(cvd_series)
    x_mean = (n - 1) / 2
    y_mean = sum(cvd_series) / n

    numerator = sum((i - x_mean) * (cvd_series[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    slope = numerator / denominator if denominator > 0 else 0
    slope_normalized = slope / price  # 归一化到价格

    # 3. 计算一致性（上涨K线占比）
    up_count = sum(1 for i in range(1, n) if cvd_series[i] > cvd_series[i-1])
    consistency = up_count / (n - 1)

    # 4. 计算R²（拟合优度）
    y_pred = [slope * i + (y_mean - slope * x_mean) for i in range(n)]
    ss_res = sum((cvd_series[i] - y_pred[i]) ** 2 for i in range(n))
    ss_tot = sum((cvd_series[i] - y_mean) ** 2 for i in range(n))
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    return {
        "cvd6": cvd6,
        "slope": slope_normalized,
        "consistency": consistency,
        "r_squared": r_squared,
        "is_consistent": consistency >= 0.6 and r_squared >= 0.7
    }

def test_scenarios():
    print("=" * 70)
    print("CVD持续性测试")
    print("=" * 70)

    price = 50000.0
    base = 10000.0

    scenarios = [
        {
            "name": "情况A：持续平稳流入（理想情况）",
            "cvd": [base + i * 100 for i in range(7)],  # 稳步上涨
            "expected": "持续流入 ✅"
        },
        {
            "name": "情况B：先跌后涨（总变化相同）",
            "cvd": [base, base - 100, base - 200, base - 300, base - 200, base + 200, base + 600],
            "expected": "不持续 ⚠️"
        },
        {
            "name": "情况C：前期流入，后期平稳",
            "cvd": [base, base + 200, base + 400, base + 600, base + 600, base + 600, base + 600],
            "expected": "流入已停止 ⚠️"
        },
        {
            "name": "情况D：后期加速流入",
            "cvd": [base, base + 50, base + 100, base + 200, base + 350, base + 550, base + 850],
            "expected": "加速流入 ✅"
        },
        {
            "name": "情况E：持续流出",
            "cvd": [base - i * 100 for i in range(7)],  # 稳步下跌
            "expected": "持续流出 ✅"
        },
        {
            "name": "情况F：震荡（上下波动）",
            "cvd": [base, base + 100, base - 50, base + 150, base - 100, base + 200, base + 100],
            "expected": "震荡不稳 ⚠️"
        },
    ]

    for scenario in scenarios:
        print(f"\n【{scenario['name']}】")
        print(f"预期: {scenario['expected']}")
        print("-" * 70)

        cvd = scenario["cvd"]

        # 显示CVD变化轨迹
        print(f"CVD轨迹: ", end="")
        for i, v in enumerate(cvd):
            change = v - base
            print(f"{change:+5.0f}", end=" ")
        print()

        # 当前方法
        cvd6_old = current_method(cvd, price)
        print(f"\n当前方法（两点比较）:")
        print(f"  cvd6 = {cvd6_old * 100:+.2f}%")

        # 改进方法
        result = improved_method(cvd, price)
        print(f"\n改进方法（斜率+一致性）:")
        print(f"  cvd6 = {result['cvd6'] * 100:+.2f}%  （总变化）")
        print(f"  斜率 = {result['slope'] * 100:.4f}%  （每小时平均变化）")
        print(f"  一致性 = {result['consistency'] * 100:.1f}%  （上涨K线占比）")
        print(f"  R² = {result['r_squared']:.3f}  （线性拟合优度，越接近1越稳定）")
        print(f"  判断: {'持续性强 ✅' if result['is_consistent'] else '持续性弱 ⚠️'}")

    print("\n" + "=" * 70)
    print("结论")
    print("=" * 70)
    print("1. 当前方法只看起点和终点，不看中间过程")
    print("2. 无法区分'持续流入'和'先出后入'")
    print("3. 改进方案：")
    print("   - 斜率：反映平均变化速度")
    print("   - 一致性：反映方向的稳定性（上涨K线占比）")
    print("   - R²：反映趋势的线性度（是否平稳）")
    print("4. 建议组合判断：")
    print("   - 一致性 >= 60% + R² >= 0.7 = 持续性强")
    print("   - 否则标注为'不持续'或'震荡'")
    print()

if __name__ == "__main__":
    test_scenarios()
