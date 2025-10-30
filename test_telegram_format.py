#!/usr/bin/env python3
# coding: utf-8
"""
测试电报消息格式（v5.0增强版）

新格式：T趋势: -100 (-13.9%)，强势下跌趋势
"""

import sys
sys.path.insert(0, '/home/user/cryptosignal')

from ats_core.scoring.scorecard import (
    scorecard,
    get_factor_contributions,
    format_factor_for_telegram
)

def test_telegram_format():
    """
    测试电报消息格式
    """
    print("=" * 80)
    print("【电报消息格式测试 - v5.0增强版】")
    print("=" * 80)
    print()

    # 测试数据：熊市场景（来自Vultr服务器实际测试）
    test_scores = {
        "T": -100,
        "M": -80,
        "S": +3,
        "V": +8,
        "C": +5,
        "O": +7,
        "F": +72,
        "L": +15,
        "B": +12,
        "Q": +8,
        "I": +21,
        "E": 0
    }

    # 基础权重（总权重=180）
    base_weights = {
        "T": 25, "M": 15, "S": 10, "V": 15,
        "C": 20, "O": 20, "F": 18,
        "L": 20, "B": 15, "Q": 10,
        "I": 12,
        "E": 0
    }

    # 获取因子贡献
    contributions = get_factor_contributions(test_scores, base_weights)

    print("【测试场景】BTCUSDT 熊市趋势")
    print()
    print("=" * 80)
    print("【电报消息格式示例】")
    print("=" * 80)
    print()
    print("📊 BTCUSDT 信号详情")
    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🔍 主要因子分析：")
    print()

    # 显示主要因子（按贡献值排序）
    main_factors = ["T", "M", "F", "C", "O"]

    for factor in main_factors:
        if factor in contributions:
            info = contributions[factor]
            score = info["score"]
            contrib = info["contribution"]

            # 使用新格式
            msg = format_factor_for_telegram(factor, score, contrib, include_description=True)
            print(f"  {msg}")

    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📈 微观结构：")
    print()

    micro_factors = ["L", "B", "Q", "I"]

    for factor in micro_factors:
        if factor in contributions:
            info = contributions[factor]
            score = info["score"]
            contrib = info["contribution"]

            # 微观结构因子可以不显示描述（更简洁）
            msg = format_factor_for_telegram(factor, score, contrib, include_description=False)
            print(f"  {msg}")

    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # 总分和方向
    weighted_score = contributions["weighted_score"]
    confidence = contributions["confidence"]

    direction_emoji = "🔻" if weighted_score < 0 else "🚀" if weighted_score > 0 else "➡️"
    direction_text = "看空" if weighted_score < 0 else "看多" if weighted_score > 0 else "中性"

    print(f"📊 综合评分：{weighted_score:+d}")
    print(f"🎯 信号方向：{direction_text} {direction_emoji}")
    print(f"💪 置信度：{confidence}")
    print()
    print("=" * 80)
    print()

    # 测试不同场景
    print("【其他场景测试】")
    print("-" * 80)
    print()

    # 场景2：强势上涨
    print("场景2: 强势上涨")
    bull_scores = {
        "T": +95,
        "M": +85,
        "C": +60,
        "O": +40,
        "F": +80,
        "L": +50,
        "B": +25,
        "Q": +15,
        "I": +10,
        "S": +30,
        "V": +70,
        "E": 0
    }

    bull_contributions = get_factor_contributions(bull_scores, base_weights)

    for factor in ["T", "M", "F"]:
        if factor in bull_contributions:
            info = bull_contributions[factor]
            score = info["score"]
            contrib = info["contribution"]
            msg = format_factor_for_telegram(factor, score, contrib)
            print(f"  {msg}")

    bull_score = bull_contributions["weighted_score"]
    print(f"  → 总分: {bull_score:+d} (看多 🚀)")
    print()

    # 场景3：震荡行情
    print("场景3: 震荡行情")
    neutral_scores = {
        "T": +5,
        "M": -8,
        "C": +12,
        "O": -3,
        "F": +15,
        "L": +20,
        "B": -5,
        "Q": +3,
        "I": -2,
        "S": +8,
        "V": +10,
        "E": 0
    }

    neutral_contributions = get_factor_contributions(neutral_scores, base_weights)

    for factor in ["T", "M", "F"]:
        if factor in neutral_contributions:
            info = neutral_contributions[factor]
            score = info["score"]
            contrib = info["contribution"]
            msg = format_factor_for_telegram(factor, score, contrib)
            print(f"  {msg}")

    neutral_score = neutral_contributions["weighted_score"]
    print(f"  → 总分: {neutral_score:+d} (震荡 ➡️)")
    print()

    print("=" * 80)
    print()

    # 分析优势
    print("【新格式优势】")
    print("✓ 直接显示贡献百分比（带符号），清晰明了")
    print("✓ 简要描述方便理解，不需要看分数就知道含义")
    print("✓ 格式统一：因子名 + 分数 + 贡献 + 描述")
    print("✓ 适合电报消息显示，既简洁又信息丰富")
    print()

    return contributions


if __name__ == "__main__":
    test_telegram_format()
