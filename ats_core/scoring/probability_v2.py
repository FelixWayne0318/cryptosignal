# coding: utf-8
"""
改进版概率映射 - Sigmoid方法

理论基础: Logistic Regression
P(Y=1|X) = 1 / (1 + exp(-β·X))

优势:
1. 非线性映射: edge越极端，概率变化越显著
2. 自然饱和: 自动限制在[0,1]
3. 可调温度: 适应不同市场环境
"""
import math
from typing import Tuple


def map_probability_sigmoid(
    edge: float,
    prior: float = 0.5,
    Q: float = 1.0,
    temperature: float = 3.0
) -> Tuple[float, float]:
    """
    Sigmoid概率映射（世界顶级改进版）

    Args:
        edge: 优势度 (-1.0 到 +1.0)
        prior: 先验概率 (默认0.5中性)
        Q: 质量系数 (0.6-1.0)
        temperature: 温度参数 (控制曲线陡峭度)
            - 高温(5.0): 激进，适合牛市
            - 中温(3.0): 平衡，正常市场
            - 低温(1.5): 保守，适合熊市

    Returns:
        (P_long, P_short): 做多/做空概率

    示例对比:
        edge=0.5, prior=0.5, Q=1.0
        旧版线性: P = 0.5 + 0.35*0.5*1.0 = 0.675
        新版sigmoid: P = 0.818 ✅ 更激进

        edge=0.8, prior=0.5, Q=1.0
        旧版: P = 0.5 + 0.35*0.8*1.0 = 0.78
        新版: P = 0.923 ✅ 强信号获得更高概率
    """
    # 边界检查
    edge = max(-1.0, min(1.0, edge))
    prior = max(0.05, min(0.95, prior))
    Q = max(0.6, min(1.0, Q))

    # Logit变换 (将概率空间映射到实数空间)
    # logit(p) = log(p / (1-p))
    prior_logit = math.log(prior / (1 - prior))

    # 调整logit (edge越大，调整越强，Q降低调整幅度)
    # temperature控制敏感度
    adjusted_logit = prior_logit + temperature * edge * Q

    # 逆Logit变换 (实数空间映射回概率空间)
    # p = 1 / (1 + exp(-logit))
    try:
        P = 1.0 / (1.0 + math.exp(-adjusted_logit))
    except OverflowError:
        # 处理极端值
        P = 0.999 if adjusted_logit > 0 else 0.001

    # 安全区间 [0.05, 0.95]
    P = max(0.05, min(0.95, P))

    P_long = P if edge > 0 else (1 - P)
    P_short = 1 - P_long

    return P_long, P_short


def get_adaptive_temperature(market_regime: int, volatility: float) -> float:
    """
    根据市场状态自适应调整温度参数

    Args:
        market_regime: 市场趋势 (-100到+100)
        volatility: 波动率 (日波动率, 0-0.05)

    Returns:
        temperature: 温度参数

    逻辑:
        强势市场 + 低波动 → 高温 (激进)
        震荡市场 + 高波动 → 低温 (保守)
    """
    # 基础温度
    base_temp = 3.0

    # 根据市场强度调整
    if abs(market_regime) > 60:
        # 强势市场 → 提升温度 (趋势明确，可以激进)
        regime_adj = 1.5
    elif abs(market_regime) < 30:
        # 震荡市场 → 降低温度 (不确定性高，需保守)
        regime_adj = 0.7
    else:
        regime_adj = 1.0

    # 根据波动率调整
    if volatility > 0.03:
        # 高波动 → 降低温度 (风险高，保守)
        vol_adj = 0.8
    elif volatility < 0.01:
        # 低波动 → 提升温度 (风险低，可激进)
        vol_adj = 1.2
    else:
        vol_adj = 1.0

    # 综合调整
    temperature = base_temp * regime_adj * vol_adj

    # 限制范围 [1.5, 5.0]
    return max(1.5, min(5.0, temperature))


# ========== 性能测试 ==========

if __name__ == "__main__":
    print("=" * 60)
    print("Sigmoid vs Linear 概率映射对比")
    print("=" * 60)

    # 导入旧版
    try:
        from ats_core.scoring.probability import map_probability as linear_map
    except ImportError:
        print("警告: 无法导入旧版概率映射，跳过对比测试")
        linear_map = None

    test_cases = [
        (0.2, 0.5, 1.0),   # 弱信号
        (0.5, 0.5, 1.0),   # 中等信号
        (0.8, 0.5, 1.0),   # 强信号
        (1.0, 0.5, 1.0),   # 极强信号
        (-0.5, 0.5, 1.0),  # 负信号
    ]

    for edge, prior, Q in test_cases:
        # Sigmoid映射
        p_sigmoid, _ = map_probability_sigmoid(edge, prior, Q, temperature=3.0)

        # 线性映射对比
        if linear_map:
            p_linear, _ = linear_map(edge, prior, Q)
            improvement = (p_sigmoid - p_linear) / p_linear * 100 if p_linear > 0 else 0

            print(f"\nEdge={edge:+.1f}, Prior={prior}, Q={Q}")
            print(f"  线性映射:   {p_linear:.3f}")
            print(f"  Sigmoid映射: {p_sigmoid:.3f}")
            print(f"  提升:       {improvement:+.1f}%")
        else:
            print(f"\nEdge={edge:+.1f}, Prior={prior}, Q={Q}")
            print(f"  Sigmoid映射: {p_sigmoid:.3f}")

    print("\n" + "=" * 60)
    print("自适应温度测试")
    print("=" * 60)

    scenarios = [
        (70, 0.008, "强势牛市 + 低波动"),
        (-70, 0.008, "强势熊市 + 低波动"),
        (20, 0.035, "震荡市场 + 高波动"),
        (50, 0.015, "温和趋势 + 中等波动"),
    ]

    for regime, vol, desc in scenarios:
        temp = get_adaptive_temperature(regime, vol)
        print(f"\n{desc}:")
        print(f"  Market Regime: {regime:+d}")
        print(f"  Volatility:    {vol:.3f}")
        print(f"  Temperature:   {temp:.2f}")

        # 测试edge=0.5的概率
        p_long, _ = map_probability_sigmoid(0.5, 0.5, 1.0, temp)
        print(f"  P(edge=0.5):   {p_long:.3f}")

    print("\n" + "=" * 60)
    print("✅ Sigmoid概率映射模块测试完成")
    print("=" * 60)
