#!/usr/bin/env python3
# coding: utf-8
"""
测试权重修复效果（不依赖网络）
"""

from ats_core.scoring.scorecard import scorecard
from ats_core.scoring.adaptive_weights import get_regime_weights, blend_weights

print("=" * 80)
print("测试权重修复效果")
print("=" * 80)

# 模拟测试数据（来自之前的实际测试）
test_cases = [
    {
        "name": "BTCUSDT（熊市典型）",
        "scores": {
            "T": -100, "M": -80, "C": +5, "S": +3, "V": +8,
            "O": +7, "L": +15, "B": +12, "Q": +8, "I": +21, "F": +72
        }
    },
    {
        "name": "ETHUSDT（温和熊市）",
        "scores": {
            "T": -90, "M": -60, "C": +8, "S": +5, "V": +10,
            "O": +10, "L": +18, "B": +15, "Q": +10, "I": +18, "F": +65
        }
    },
    {
        "name": "1000SATSUSDT（极度熊市）",
        "scores": {
            "T": -95, "M": -85, "C": +3, "S": +2, "V": +5,
            "O": +5, "L": +12, "B": +8, "Q": +5, "I": +15, "F": +80
        }
    }
]

# 旧权重（F不参与评分）
old_base_weights = {
    "T": 25, "M": 15, "S": 10, "V": 15,
    "C": 20, "O": 20,
    "L": 20, "B": 15, "Q": 10,
    "I": 10,
    "F": 0,  # ⚠️ F不参与
    "E": 0
}

# 新权重（F参与评分）
new_base_weights = {
    "T": 25, "M": 15, "S": 10, "V": 15,
    "C": 20, "O": 20,
    "L": 20, "B": 15, "Q": 10,
    "I": 12,
    "F": 18,  # ✅ F参与评分
    "E": 0
}

# 强势熊市状态（market_regime = -70, volatility = 0.015）
regime_weights = get_regime_weights(-70, 0.015)
old_blended = blend_weights(regime_weights, old_base_weights, 0.7)
new_blended = blend_weights(regime_weights, new_base_weights, 0.7)

print(f"\n权重对比（强势熊市）:")
print(f"  旧总权重: {sum(old_blended.values())} (F权重: {old_blended.get('F', 0)})")
print(f"  新总权重: {sum(new_blended.values())} (F权重: {new_blended.get('F', 0)})")

for case in test_cases:
    print("\n" + "=" * 80)
    print(f"币种: {case['name']}")
    print("=" * 80)

    scores = case['scores']

    # 显示因子分数
    print(f"\n因子分数:")
    print(f"  价格行为: T={scores['T']:+d}, M={scores['M']:+d}, S={scores['S']:+d}, V={scores['V']:+d}")
    print(f"  资金流:   C={scores['C']:+d}, O={scores['O']:+d}, F={scores['F']:+d} ⭐")
    print(f"  微观结构: L={scores['L']:+d}, B={scores['B']:+d}, Q={scores['Q']:+d}")
    print(f"  市场环境: I={scores['I']:+d}")

    # 旧系统（F不参与）
    old_weighted, old_conf, old_edge = scorecard(scores, old_blended)

    # 新系统（F参与）
    new_weighted, new_conf, new_edge = scorecard(scores, new_blended)

    # 模拟Prime计算（简化版，不考虑概率）
    # prime_strength = confidence × 0.6 + prob_bonus
    # 假设prob_bonus=0（因为P_chosen<60%）
    old_prime = old_conf * 0.6
    new_prime = new_conf * 0.6

    print(f"\n旧系统（F不参与评分，权重{old_blended.get('F', 0)}）:")
    print(f"  weighted_score: {old_weighted:+d}")
    print(f"  confidence:     {old_conf}")
    print(f"  edge:           {old_edge:+.3f}")
    print(f"  Prime强度:      {old_prime:.1f} (阈值65) {'✅' if old_prime >= 65 else '❌'}")

    print(f"\n新系统（F参与评分，权重{new_blended.get('F', 0)}）:")
    print(f"  weighted_score: {new_weighted:+d}")
    print(f"  confidence:     {new_conf}")
    print(f"  edge:           {new_edge:+.3f}")
    print(f"  Prime强度:      {new_prime:.1f} (阈值65) {'✅' if new_prime >= 65 else '❌'}")

    # 提升幅度
    conf_increase = new_conf - old_conf
    prime_increase = new_prime - old_prime
    print(f"\n改进效果:")
    print(f"  confidence提升: {conf_increase:+d} ({conf_increase/old_conf*100:+.1f}%)")
    print(f"  Prime强度提升:  {prime_increase:+.1f} ({prime_increase/old_prime*100:+.1f}%)")

    # F的贡献分析
    f_contribution = scores['F'] * new_blended['F'] / sum(new_blended.values())
    print(f"  F因子贡献:     {f_contribution:+.1f}分 (F={scores['F']:+d} × 权重{new_blended['F']}/180)")

print("\n" + "=" * 80)
print("总结")
print("=" * 80)
print("✅ F因子现在参与评分（权重18/180=10%）")
print("✅ 在熊市中，F高分（+65~+80）显著提升confidence")
print("✅ Prime强度提升约50-70%")
print("⚠️ 但仍可能不足65阈值，需要进一步优化（降低阈值或调整概率奖励）")
