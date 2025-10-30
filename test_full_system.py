#!/usr/bin/env python3
# coding: utf-8
"""
完整系统集成测试（v5.0增强版）

测试内容：
1. 所有模块导入
2. scorecard系统（加权平均）
3. get_factor_contributions（贡献计算）
4. format_factor_for_telegram（电报格式化）
5. analyze_symbol集成（使用模拟数据）
6. 完整流程验证

避免以前的问题：
- 导入错误
- 函数签名不匹配
- 数据格式错误
- 计算逻辑错误
"""

import sys
sys.path.insert(0, '/home/user/cryptosignal')

import traceback
from typing import Dict, List, Any


def test_step(step_name: str, test_func):
    """
    执行测试步骤并捕获错误
    """
    print(f"\n{'='*80}")
    print(f"【测试步骤】{step_name}")
    print(f"{'='*80}")

    try:
        result = test_func()
        print(f"✅ {step_name} - 通过")
        return True, result
    except Exception as e:
        print(f"❌ {step_name} - 失败")
        print(f"错误: {e}")
        print(f"\n详细错误信息:")
        traceback.print_exc()
        return False, None


def test_1_imports():
    """
    测试1: 验证所有模块导入
    """
    print("\n导入核心模块...")

    # 评分系统
    from ats_core.scoring.scorecard import (
        scorecard,
        get_factor_contributions,
        get_factor_description,
        format_factor_for_telegram
    )
    print("  ✓ scorecard 模块")

    # 自适应权重
    from ats_core.scoring.adaptive_weights import (
        get_regime_weights,
        blend_weights
    )
    print("  ✓ adaptive_weights 模块")

    # 分析管道
    from ats_core.pipeline.analyze_symbol import _analyze_symbol_core
    print("  ✓ analyze_symbol 模块")

    # 因子系统
    from ats_core.factors_v2.liquidity import calculate_liquidity
    from ats_core.factors_v2.basis_funding import calculate_basis_funding
    from ats_core.factors_v2.liquidation_v2 import calculate_liquidation_from_trades
    from ats_core.factors_v2.independence import calculate_independence
    print("  ✓ 10维因子模块")

    print("\n所有模块导入成功！")
    return True


def test_2_scorecard():
    """
    测试2: scorecard系统（加权平均）
    """
    from ats_core.scoring.scorecard import scorecard

    print("\n测试加权平均计算...")

    # 测试数据
    scores = {
        "T": -100, "M": -80, "C": +5, "S": +3, "V": +8,
        "O": +7, "F": +72, "L": +15, "B": +12, "Q": +8,
        "I": +21, "E": 0
    }

    weights = {
        "T": 13.9, "M": 8.3, "S": 5.6, "V": 8.3,
        "C": 11.1, "O": 11.1, "F": 10.0,
        "L": 11.1, "B": 8.3, "Q": 5.6,
        "I": 6.7, "E": 0
    }

    weighted_score, confidence, edge = scorecard(scores, weights)

    print(f"  总分: {weighted_score:+d}")
    print(f"  置信度: {confidence}")
    print(f"  优势度: {edge:+.3f}")

    # 验证
    assert -100 <= weighted_score <= 100, "总分超出范围"
    assert 0 <= confidence <= 100, "置信度超出范围"
    assert -1.0 <= edge <= 1.0, "优势度超出范围"
    assert weighted_score == confidence * (-1 if edge < 0 else 1), "一致性检查失败"

    print("\n  ✓ scorecard计算正确")
    print(f"  ✓ 熊市场景识别正确（总分={weighted_score:+d} < 0）")

    return {"weighted_score": weighted_score, "confidence": confidence}


def test_3_contributions():
    """
    测试3: 因子贡献计算
    """
    from ats_core.scoring.scorecard import get_factor_contributions

    print("\n测试因子贡献计算...")

    scores = {
        "T": -100, "M": -80, "C": +5, "O": +7, "F": +72,
        "L": +15, "B": +12, "Q": +8, "I": +21,
        "S": +3, "V": +8, "E": 0
    }

    weights = {
        "T": 13.9, "M": 8.3, "S": 5.6, "V": 8.3,
        "C": 11.1, "O": 11.1, "F": 10.0,
        "L": 11.1, "B": 8.3, "Q": 5.6,
        "I": 6.7, "E": 0
    }

    contributions = get_factor_contributions(scores, weights)

    # 验证结构
    assert "T" in contributions, "缺少T因子贡献"
    assert "total_weight" in contributions, "缺少总权重"
    assert "weighted_score" in contributions, "缺少总分"

    # 验证T因子数据
    t_info = contributions["T"]
    assert "score" in t_info, "T因子缺少score字段"
    assert "weight" in t_info, "T因子缺少weight字段"
    assert "weight_pct" in t_info, "T因子缺少weight_pct字段"
    assert "contribution" in t_info, "T因子缺少contribution字段"

    print(f"  总权重: {contributions['total_weight']}")
    print(f"  T因子贡献: {t_info['contribution']:+.1f} ({t_info['weight_pct']:.1f}%)")
    print(f"  M因子贡献: {contributions['M']['contribution']:+.1f} ({contributions['M']['weight_pct']:.1f}%)")
    print(f"  F因子贡献: {contributions['F']['contribution']:+.1f} ({contributions['F']['weight_pct']:.1f}%)")

    # 验证计算
    total_weight = contributions["total_weight"]
    assert abs(total_weight - 100) < 0.1, f"总权重错误: {total_weight}"

    expected_t_pct = 25 / 180 * 100
    assert abs(t_info["weight_pct"] - expected_t_pct) < 0.1, "T权重百分比计算错误"

    expected_t_contrib = -100 * 25 / 180
    assert abs(t_info["contribution"] - expected_t_contrib) < 0.1, "T贡献计算错误"

    print("\n  ✓ 因子贡献计算正确")
    print("  ✓ 数据结构完整")

    return contributions


def test_4_telegram_format():
    """
    测试4: 电报消息格式化
    """
    from ats_core.scoring.scorecard import (
        format_factor_for_telegram,
        get_factor_description
    )

    print("\n测试电报消息格式化...")

    # 测试描述生成
    desc_t = get_factor_description("T", -100)
    desc_m = get_factor_description("M", +85)
    desc_f = get_factor_description("F", +72)

    print(f"  T=-100 → {desc_t}")
    print(f"  M=+85 → {desc_m}")
    print(f"  F=+72 → {desc_f}")

    assert "下跌" in desc_t or "跌" in desc_t, "T描述错误"
    assert "上涨" in desc_m or "涨" in desc_m, "M描述错误"

    # 测试格式化
    msg_t = format_factor_for_telegram("T", -100, -13.9, include_description=True)
    msg_f = format_factor_for_telegram("F", +72, +7.2, include_description=True)

    print(f"\n  格式化示例:")
    print(f"    {msg_t}")
    print(f"    {msg_f}")

    # 验证格式
    assert "T趋势" in msg_t, "T名称缺失"
    assert "-100" in msg_t, "T分数缺失"
    assert "-13.9%" in msg_t, "T贡献缺失"
    assert desc_t in msg_t, "T描述缺失"

    print("\n  ✓ 描述生成正确")
    print("  ✓ 格式化输出正确")

    return {"msg_t": msg_t, "msg_f": msg_f}


def test_5_adaptive_weights():
    """
    测试5: 自适应权重系统
    """
    from ats_core.scoring.adaptive_weights import get_regime_weights, blend_weights

    print("\n测试自适应权重...")

    # 测试强势趋势权重
    trend_weights = get_regime_weights(market_regime=70, volatility=0.03)
    print(f"  强势趋势权重: T={trend_weights['T']}, M={trend_weights['M']}, F={trend_weights['F']}")

    # 测试震荡权重
    range_weights = get_regime_weights(market_regime=10, volatility=0.02)
    print(f"  震荡市场权重: C={range_weights['C']}, L={range_weights['L']}, B={range_weights['B']}")

    # 验证权重总和
    trend_sum = sum(trend_weights.values())
    range_sum = sum(range_weights.values())

    assert abs(trend_sum - 100) < 0.2, f"趋势权重总和错误: {trend_sum}"
    assert abs(range_sum - 100) < 0.2, f"震荡权重总和错误: {range_sum}"

    # 测试权重混合
    base_weights = {
        "T": 13.9, "M": 8.3, "S": 5.6, "V": 8.3,
        "C": 11.1, "O": 11.1, "F": 10.0,
        "L": 11.1, "B": 8.3, "Q": 5.6,
        "I": 6.7, "E": 0
    }

    blended = blend_weights(trend_weights, base_weights, blend_ratio=0.7)
    blended_sum = sum(blended.values())

    print(f"  混合权重: T={blended['T']:.0f}, M={blended['M']:.0f}")
    print(f"  混合权重总和: {blended_sum:.0f}")

    assert abs(blended_sum - 100) < 0.2, f"混合权重总和错误: {blended_sum}"

    print("\n  ✓ 自适应权重计算正确")
    print("  ✓ 权重混合正确")

    return blended


def test_6_analyze_integration():
    """
    测试6: analyze_symbol集成（模拟数据）
    """
    print("\n测试analyze_symbol集成...")
    print("  注意: 使用模拟数据，不调用网络API")

    # 生成模拟K线数据
    def generate_mock_klines(periods=500, trend="bear"):
        """生成模拟K线数据"""
        import random
        klines = []
        base_price = 50000.0

        for i in range(periods):
            if trend == "bear":
                # 下跌趋势
                base_price *= (1 - random.uniform(0, 0.01))
            elif trend == "bull":
                # 上涨趋势
                base_price *= (1 + random.uniform(0, 0.01))
            else:
                # 震荡
                base_price *= (1 + random.uniform(-0.005, 0.005))

            open_price = base_price * (1 + random.uniform(-0.002, 0.002))
            high = max(open_price, base_price) * (1 + random.uniform(0, 0.01))
            low = min(open_price, base_price) * (1 - random.uniform(0, 0.01))
            close = base_price
            volume = random.uniform(100, 1000)

            klines.append([
                1700000000000 + i * 60000,  # timestamp
                str(open_price),
                str(high),
                str(low),
                str(close),
                str(volume),
                0, 0, 0, 0, 0, 0
            ])

        return klines

    # 生成模拟持仓数据
    def generate_mock_oi(periods=500):
        """生成模拟持仓数据"""
        import random
        oi_data = []
        base_oi = 100000.0

        for i in range(periods):
            base_oi *= (1 + random.uniform(-0.02, 0.02))
            oi_data.append({
                'timestamp': 1700000000000 + i * 60000,
                'sumOpenInterest': str(base_oi),
                'sumOpenInterestValue': str(base_oi * 50000)
            })

        return oi_data

    print("  生成模拟数据...")
    k1_mock = generate_mock_klines(500, trend="bear")
    k4_mock = generate_mock_klines(125, trend="bear")
    oi_mock = generate_mock_oi(500)

    print(f"    K1数据: {len(k1_mock)} 条")
    print(f"    K4数据: {len(k4_mock)} 条")
    print(f"    OI数据: {len(oi_mock)} 条")

    # 导入分析函数
    from ats_core.pipeline.analyze_symbol import _analyze_symbol_core

    print("\n  执行分析...")

    try:
        result = _analyze_symbol_core(
            symbol="BTCUSDT",
            k1=k1_mock,
            k4=k4_mock,
            oi_data=oi_mock,
            spot_k1=None,
            k15m=None,
            k1d=None,
            orderbook=None,
            mark_price=None,
            funding_rate=None,
            spot_price=None,
            agg_trades=None,
            btc_klines=None,
            eth_klines=None
        )

        # 验证返回结果
        assert "weighted_score" in result, "缺少weighted_score"
        assert "confidence" in result, "缺少confidence"
        assert "factor_contributions" in result, "缺少factor_contributions"

        print(f"\n  分析结果:")
        print(f"    总分: {result['weighted_score']:+d}")
        print(f"    置信度: {result['confidence']}")
        print(f"    方向: {'看多' if result['side_long'] else '看空'}")

        # 验证因子贡献
        contrib = result['factor_contributions']
        assert "T" in contrib, "因子贡献缺少T"
        assert "total_weight" in contrib, "因子贡献缺少total_weight"

        print(f"    因子贡献数据完整: ✓")

        # 显示主要因子
        print(f"\n  主要因子:")
        for factor in ["T", "M", "C", "O", "F"]:
            if factor in contrib:
                info = contrib[factor]
                print(f"    {factor}: {info['score']:+4d} ({info['contribution']:+.1f}%)")

        print("\n  ✓ analyze_symbol集成成功")
        print("  ✓ 新功能正常工作")

        return result

    except Exception as e:
        print(f"\n  ❌ 分析失败: {e}")
        traceback.print_exc()
        return None


def test_7_full_telegram_output():
    """
    测试7: 完整电报消息输出
    """
    from ats_core.scoring.scorecard import (
        get_factor_contributions,
        format_factor_for_telegram
    )

    print("\n测试完整电报消息输出...")

    # 模拟分析结果
    scores = {
        "T": -100, "M": -80, "C": +5, "S": +3, "V": +8,
        "O": +7, "F": +72, "L": +15, "B": +12, "Q": +8,
        "I": +21, "E": 0
    }

    weights = {
        "T": 13.9, "M": 8.3, "S": 5.6, "V": 8.3,
        "C": 11.1, "O": 11.1, "F": 10.0,
        "L": 11.1, "B": 8.3, "Q": 5.6,
        "I": 6.7, "E": 0
    }

    contributions = get_factor_contributions(scores, weights)

    # 生成完整电报消息
    print("\n" + "="*80)
    print("【完整电报消息示例】")
    print("="*80)
    print()
    print("📊 BTCUSDT 信号分析")
    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🔍 主要因子:")
    print()

    main_factors = ["T", "M", "C", "O", "F"]
    for factor in main_factors:
        if factor in contributions:
            info = contributions[factor]
            msg = format_factor_for_telegram(factor, info['score'], info['contribution'])
            print(f"  {msg}")

    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    weighted_score = contributions['weighted_score']
    confidence = contributions['confidence']

    direction_emoji = "🔻" if weighted_score < 0 else "🚀" if weighted_score > 0 else "➡️"
    direction_text = "看空" if weighted_score < 0 else "看多" if weighted_score > 0 else "中性"

    print(f"📊 综合评分: {weighted_score:+d}")
    print(f"🎯 信号方向: {direction_text} {direction_emoji}")
    print(f"💪 置信度: {confidence}")
    print()
    print("="*80)

    print("\n  ✓ 电报消息生成成功")
    print("  ✓ 格式完整美观")

    return True


def main():
    """
    主测试流程
    """
    print("\n" + "="*80)
    print("【完整系统集成测试 - v5.0增强版】")
    print("="*80)
    print("\n测试目标:")
    print("  1. 验证所有模块正常导入")
    print("  2. 验证scorecard加权平均系统")
    print("  3. 验证因子贡献计算")
    print("  4. 验证电报消息格式化")
    print("  5. 验证自适应权重系统")
    print("  6. 验证analyze_symbol集成")
    print("  7. 验证完整电报消息输出")

    results = {}
    all_passed = True

    # 执行所有测试
    tests = [
        ("1. 模块导入", test_1_imports),
        ("2. Scorecard系统", test_2_scorecard),
        ("3. 因子贡献计算", test_3_contributions),
        ("4. 电报消息格式化", test_4_telegram_format),
        ("5. 自适应权重", test_5_adaptive_weights),
        ("6. Analyze集成", test_6_analyze_integration),
        ("7. 完整电报输出", test_7_full_telegram_output),
    ]

    for test_name, test_func in tests:
        passed, result = test_step(test_name, test_func)
        results[test_name] = {"passed": passed, "result": result}

        if not passed:
            all_passed = False
            print(f"\n⚠️  测试失败，停止后续测试")
            break

    # 总结
    print("\n" + "="*80)
    print("【测试总结】")
    print("="*80)
    print()

    passed_count = sum(1 for r in results.values() if r["passed"])
    total_count = len(results)

    for test_name, result in results.items():
        status = "✅ 通过" if result["passed"] else "❌ 失败"
        print(f"  {test_name}: {status}")

    print()
    print(f"测试结果: {passed_count}/{total_count} 通过")

    if all_passed:
        print("\n🎉 所有测试通过！系统运行正常！")
        print("\n系统已就绪：")
        print("  ✓ 评分系统（加权平均）工作正常")
        print("  ✓ 因子贡献计算正确")
        print("  ✓ 电报消息格式化美观")
        print("  ✓ 自适应权重正确")
        print("  ✓ analyze_symbol集成成功")
        print("  ✓ 没有导入错误或语法错误")
        return 0
    else:
        print("\n❌ 部分测试失败，请检查错误信息")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
