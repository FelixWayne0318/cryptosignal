#!/usr/bin/env python3
# coding: utf-8
"""
测试±100对称评分系统（不依赖网络）
"""
import sys
sys.path.insert(0, '/home/user/cryptosignal')

from ats_core.features.scoring_utils import directional_score_symmetric
from ats_core.features.cvd_flow import score_cvd_flow
from ats_core.features.momentum import score_momentum
from ats_core.features.trend import score_trend
from ats_core.features.volume import score_volume
from ats_core.features.fund_leading import score_fund_leading, calculate_F_adjustment
import math

def test_symmetric_scoring_function():
    """测试基础对称评分函数"""
    print("=" * 60)
    print("测试1：对称评分函数 directional_score_symmetric")
    print("=" * 60)

    test_cases = [
        # (value, neutral, scale, expected_range, description)
        (1.0, 0.0, 1.0, (50, 80), "正值应返回正分"),
        (-1.0, 0.0, 1.0, (-80, -50), "负值应返回负分"),
        (0.0, 0.0, 1.0, (-10, 10), "中性值应接近0"),
        (1.5, 1.0, 0.5, (50, 90), "超过中性应为正"),
        (0.5, 1.0, 0.5, (-90, -50), "低于中性应为负"),
    ]

    passed = 0
    for value, neutral, scale, (low, high), desc in test_cases:
        score = directional_score_symmetric(value, neutral, scale)
        if low <= score <= high:
            print(f"✅ {desc}: value={value}, score={score}")
            passed += 1
        else:
            print(f"❌ {desc}: value={value}, score={score}, expected [{low}, {high}]")

    print(f"\n通过: {passed}/{len(test_cases)}\n")
    return passed == len(test_cases)

def test_dimension_ranges():
    """测试各维度返回±100范围"""
    print("=" * 60)
    print("测试2：各维度±100范围验证")
    print("=" * 60)

    # 构造合成数据
    n = 100
    c = [100.0 + i * 0.1 for i in range(n)]  # 上升趋势
    h = [x + 1.0 for x in c]
    l = [x - 1.0 for x in c]
    vol = [1000.0 + i * 10 for i in range(n)]
    cvd = [i * 5.0 for i in range(n)]

    results = []

    # T - Trend
    try:
        from ats_core.features.ta_core import ema
        c4 = ema([c[-1]], 1)[0]
        T, T_meta = score_trend(h, l, c, c4, {})
        results.append(("T(趋势)", T, -100 <= T <= 100))
    except Exception as e:
        results.append(("T(趋势)", None, False, str(e)))

    # M - Momentum
    try:
        M, M_meta = score_momentum(c, {})
        results.append(("M(动量)", M, -100 <= M <= 100))
    except Exception as e:
        results.append(("M(动量)", None, False, str(e)))

    # C - CVD Flow
    try:
        C, C_meta = score_cvd_flow(cvd, c, {})
        results.append(("C(资金流)", C, -100 <= C <= 100))
    except Exception as e:
        results.append(("C(资金流)", None, False, str(e)))

    # V - Volume
    try:
        V, V_meta = score_volume(vol, {})
        results.append(("V(量能)", V, -100 <= V <= 100))
    except Exception as e:
        results.append(("V(量能)", None, False, str(e)))

    # F - Fund Leading
    try:
        # 构造F维度所需参数
        oi_change_pct = 5.0  # OI上升5%
        vol_ratio = 1.3  # 量能比值
        cvd_change = 0.02  # CVD变化
        price_change_pct = 2.0  # 价格上升2%
        price_slope = 0.5  # 价格斜率

        F, F_meta = score_fund_leading(
            oi_change_pct, vol_ratio, cvd_change,
            price_change_pct, price_slope, {}
        )
        results.append(("F(资金领先)", F, -100 <= F <= 100))
    except Exception as e:
        results.append(("F(资金领先)", None, False, str(e)))

    passed = 0
    for item in results:
        if len(item) == 3:
            name, score, valid = item
            if valid and score is not None:
                print(f"✅ {name}: {score:+4d} (范围正确)")
                passed += 1
            else:
                print(f"❌ {name}: {score} (范围错误)")
        else:
            name, score, valid, error = item
            print(f"❌ {name}: 错误 - {error}")

    print(f"\n通过: {passed}/{len(results)}\n")
    return passed == len(results)

def test_F_adjustment_continuous():
    """测试F连续调节函数"""
    print("=" * 60)
    print("测试3：F连续调节函数")
    print("=" * 60)

    test_points = [
        (-100, 0.75, "极度看空"),
        (-80, 0.77, "强烈看空"),
        (-50, 0.85, "看空"),
        (-20, 0.94, "略看空"),
        (0, 1.00, "中性"),
        (20, 1.06, "略看多"),
        (50, 1.15, "看多"),
        (80, 1.23, "强烈看多"),
        (100, 1.25, "极度看多"),
    ]

    print(f"{'F分数':<10} {'调节系数':<12} {'说明':<20} {'连续性':<10}")
    print("-" * 60)

    passed = 0
    prev_F = None
    prev_adj = None
    for F, expected, desc in test_points:
        adj = calculate_F_adjustment(F)

        # 检查范围
        valid_range = 0.75 <= adj <= 1.25

        # 检查连续性（tanh函数是数学上连续的）
        # 验证斜率是否合理：相邻点的变化率应该与F的步长成比例
        continuous = True
        if prev_adj is not None and prev_F is not None:
            F_step = abs(F - prev_F)
            adj_diff = abs(adj - prev_adj)
            # tanh导数最大值为1，所以调节系数变化率应该 < 0.25 * F_step / 40
            max_expected_diff = 0.25 * F_step / 40 * 1.5  # 留一些容差
            continuous = adj_diff <= max_expected_diff

        status = "✅" if valid_range and continuous else "❌"
        cont_str = "连续" if continuous else "不连续"

        print(f"{F:<10} {adj:<12.2f} {desc:<20} {cont_str:<10} {status}")

        if valid_range and continuous:
            passed += 1

        prev_F = F
        prev_adj = adj

    print(f"\n通过: {passed}/{len(test_points)}\n")
    return passed == len(test_points)

def test_direction_auto_determination():
    """测试方向自动判定"""
    print("=" * 60)
    print("测试4：方向自动判定（正分=做多，负分=做空）")
    print("=" * 60)

    # 模拟上升趋势数据
    n = 100
    c_up = [100.0 + i * 0.5 for i in range(n)]  # 强上升

    # 模拟下降趋势数据
    c_down = [200.0 - i * 0.5 for i in range(n)]  # 强下降

    results = []

    # 测试动量维度
    try:
        M_up, _ = score_momentum(c_up, {})
        M_down, _ = score_momentum(c_down, {})

        up_positive = M_up > 0
        down_negative = M_down < 0

        if up_positive and down_negative:
            print(f"✅ M(动量)：上升趋势={M_up:+d}, 下降趋势={M_down:+d}")
            results.append(True)
        else:
            print(f"❌ M(动量)：上升={M_up:+d}, 下降={M_down:+d} (方向错误)")
            results.append(False)
    except Exception as e:
        print(f"❌ M(动量) 错误: {e}")
        results.append(False)

    # 测试资金流维度
    try:
        cvd_up = [i * 10.0 for i in range(n)]
        cvd_down = [-i * 10.0 for i in range(n)]

        C_up, _ = score_cvd_flow(cvd_up, c_up, {})
        C_down, _ = score_cvd_flow(cvd_down, c_down, {})

        up_positive = C_up > 0
        down_negative = C_down < 0

        if up_positive and down_negative:
            print(f"✅ C(资金流)：净流入={C_up:+d}, 净流出={C_down:+d}")
            results.append(True)
        else:
            print(f"❌ C(资金流)：流入={C_up:+d}, 流出={C_down:+d} (方向错误)")
            results.append(False)
    except Exception as e:
        print(f"❌ C(资金流) 错误: {e}")
        results.append(False)

    passed = sum(results)
    print(f"\n通过: {passed}/{len(results)}\n")
    return passed == len(results)

if __name__ == "__main__":
    print("\n")
    print("=" * 60)
    print("±100对称评分系统单元测试")
    print("=" * 60)
    print()

    all_passed = []

    all_passed.append(test_symmetric_scoring_function())
    all_passed.append(test_dimension_ranges())
    all_passed.append(test_F_adjustment_continuous())
    all_passed.append(test_direction_auto_determination())

    print("=" * 60)
    print("测试总结")
    print("=" * 60)

    total = len(all_passed)
    passed = sum(all_passed)

    if passed == total:
        print(f"✅ 全部通过 ({passed}/{total})")
        print("\n✅ ±100对称评分系统实现正确！")
        sys.exit(0)
    else:
        print(f"❌ 部分失败 ({passed}/{total})")
        sys.exit(1)
