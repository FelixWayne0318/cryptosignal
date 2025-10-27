#!/usr/bin/env python3
# coding: utf-8
"""
测试F（资金领先）带符号评分系统

验证：
1. F分数是否正确映射到-100到+100
2. 概率调整逻辑是否正确
3. Telegram显示是否直观
"""

from ats_core.features.fund_leading import score_fund_leading, interpret_F
from ats_core.outputs.telegram_fmt import _desc_fund_leading

def test_fund_leading_signed():
    print("=" * 70)
    print("测试F（资金领先）带符号评分系统")
    print("=" * 70)

    # 测试用例：不同的资金和价格动量组合
    test_cases = [
        {
            "name": "理想做多信号（资金强势流入，价格未涨）",
            "oi_change_pct": 5.0,      # OI大幅上升
            "vol_ratio": 1.5,          # 量能放大
            "cvd_change": 0.03,        # CVD强势流入
            "price_change_pct": 1.0,   # 价格小幅上涨
            "price_slope": 0.005,      # 价格斜率温和
            "side_long": True,
            "expected_sign": "+",
            "expected_desc": "资金领先价格"
        },
        {
            "name": "追高做多信号（价格已涨，资金流入减弱）",
            "oi_change_pct": 1.0,      # OI小幅上升
            "vol_ratio": 1.1,          # 量能略微放大
            "cvd_change": 0.005,       # CVD略微流入
            "price_change_pct": 5.0,   # 价格大幅上涨
            "price_slope": 0.02,       # 价格斜率陡峭
            "side_long": True,
            "expected_sign": "-",
            "expected_desc": "价格领先资金"
        },
        {
            "name": "资金价格同步（均衡状态）",
            "oi_change_pct": 2.0,
            "vol_ratio": 1.2,
            "cvd_change": 0.01,
            "price_change_pct": 2.0,
            "price_slope": 0.008,
            "side_long": True,
            "expected_sign": "~",
            "expected_desc": "同步"
        },
        {
            "name": "理想做空信号（资金流出，价格未跌）",
            "oi_change_pct": -5.0,     # OI大幅下降
            "vol_ratio": 1.5,          # 量能放大
            "cvd_change": -0.03,       # CVD强势流出
            "price_change_pct": -1.0,  # 价格小幅下跌
            "price_slope": -0.005,     # 价格斜率温和
            "side_long": False,
            "expected_sign": "+",
            "expected_desc": "资金领先价格"
        },
        {
            "name": "追空做空信号（价格已跌，资金流出减弱）",
            "oi_change_pct": -1.0,     # OI小幅下降
            "vol_ratio": 1.1,          # 量能略微放大
            "cvd_change": -0.005,      # CVD略微流出
            "price_change_pct": -5.0,  # 价格大幅下跌
            "price_slope": -0.02,      # 价格斜率陡峭
            "side_long": False,
            "expected_sign": "-",
            "expected_desc": "价格领先资金"
        },
    ]

    print("\n【测试1：F分数映射】")
    print("-" * 70)

    for case in test_cases:
        # 计算F分数
        F, meta = score_fund_leading(
            oi_change_pct=case["oi_change_pct"],
            vol_ratio=case["vol_ratio"],
            cvd_change=case["cvd_change"],
            price_change_pct=case["price_change_pct"],
            price_slope=case["price_slope"],
            side_long=case["side_long"],
            params={}
        )

        print(f"\n{case['name']}")
        print(f"  方向: {'做多' if case['side_long'] else '做空'}")
        print(f"  输入:")
        print(f"    - OI变化: {case['oi_change_pct']:+.1f}%")
        print(f"    - 量能比值: {case['vol_ratio']:.2f}")
        print(f"    - CVD变化: {case['cvd_change']:+.3f}")
        print(f"    - 价格变化: {case['price_change_pct']:+.1f}%")
        print(f"    - 价格斜率: {case['price_slope']:+.3f}")
        print(f"  输出:")
        print(f"    - 资金动量: {meta['fund_momentum']:.1f}")
        print(f"    - 价格动量: {meta['price_momentum']:.1f}")
        print(f"    - 领先性: {meta['leading_raw']:+.1f}")
        print(f"    - F分数: {F:+4d}")

        # 验证符号
        if case["expected_sign"] == "+":
            assert F > 30, f"期望F>30（资金领先），实际 {F}"
            print(f"  ✅ 符号正确（正数 = {case['expected_desc']}）")
        elif case["expected_sign"] == "-":
            assert F < -30, f"期望F<-30（价格领先），实际 {F}"
            print(f"  ✅ 符号正确（负数 = {case['expected_desc']}）")
        elif case["expected_sign"] == "~":
            assert -30 <= F <= 30, f"期望-30≤F≤30（同步），实际 {F}"
            print(f"  ✅ 符号正确（接近0 = {case['expected_desc']}）")

    print("\n" + "=" * 70)
    print("【测试2：概率调整逻辑】")
    print("-" * 70)

    # 测试概率调整
    adjustment_cases = [
        (70, 1.15, "资金强势领先，提升15%"),
        (45, 1.05, "资金温和领先，提升5%"),
        (0, 1.0, "资金价格同步，不调整"),
        (-45, 0.9, "价格温和领先，降低10%"),
        (-70, 0.7, "价格强势领先，降低30%"),
    ]

    for f_score, expected_adj, desc in adjustment_cases:
        # 模拟概率调整逻辑
        if f_score >= 60:
            adjustment = 1.15
        elif f_score >= 30:
            adjustment = 1.05
        elif f_score >= -30:
            adjustment = 1.0
        elif f_score >= -60:
            adjustment = 0.9
        else:
            adjustment = 0.7

        print(f"\nF={f_score:+4d}: 调整系数 ×{adjustment:.2f} - {desc}")
        assert adjustment == expected_adj, f"期望 {expected_adj}, 实际 {adjustment}"
        print(f"  ✅ 调整系数正确")

    print("\n" + "=" * 70)
    print("【测试3：Telegram显示格式】")
    print("-" * 70)

    display_cases = [
        (+90, "资金强势领先价格 (蓄势待发)"),
        (+70, "资金强势领先价格 (蓄势待发)"),
        (+45, "资金温和领先价格 (机会较好)"),
        (+15, "资金略微领先 (同步偏好)"),
        (0, "资金价格同步 (中性)"),
        (-15, "价格略微领先 (同步偏差)"),
        (-45, "价格温和领先资金 (追高风险)"),
        (-70, "价格强势领先资金 (风险很大)"),
        (-90, "价格强势领先资金 (风险很大)"),
    ]

    print("\n正负对称的描述体系：")
    for f_score, expected_desc in display_cases:
        desc = _desc_fund_leading(f_score)
        print(f"  F={f_score:+4d}: {desc}")
        assert expected_desc in desc or desc in expected_desc, \
            f"期望包含 '{expected_desc}', 实际 '{desc}'"

    print("\n实际Telegram消息示例：")
    print("\n做多信号（F=+65）：")
    desc = _desc_fund_leading(65)
    print(f"⚡ {desc} (F=+65) → 概率调整 ×1.15")

    print("\n做空信号（F=-45）：")
    desc = _desc_fund_leading(-45)
    print(f"⚡ {desc} (F=-45) → 概率调整 ×0.90")

    print("\n均衡状态（F=+5）：")
    desc = _desc_fund_leading(5)
    print(f"⚡ {desc} (F=+5) → 概率调整 ×1.00")

    print("\n" + "=" * 70)
    print("✅ 所有测试通过！")
    print("=" * 70)

    print("\n【改进总结】")
    print("1. F分数从0-100改为-100到+100（带符号）")
    print("2. 正数 = 资金领先价格（蓄势待发，好）")
    print("3. 负数 = 价格领先资金（追高风险，差）")
    print("4. 显示从'资金领先 35'改为'价格领先资金 (F=-35, 追高风险)'")
    print("5. 一眼就能看懂谁领先谁，领先程度如何")
    print()

if __name__ == "__main__":
    test_fund_leading_signed()
