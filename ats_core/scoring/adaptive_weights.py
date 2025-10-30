# coding: utf-8
"""
自适应权重系统 - Regime-Dependent

根据市场状态动态调整因子权重

理论基础: Adaptive Asset Allocation
不同市场regime下，因子有效性不同
"""
from typing import Dict


def get_regime_weights(market_regime: int, volatility: float) -> Dict[str, float]:
    """
    根据市场状态返回最优权重配置（10维因子系统）

    Args:
        market_regime: 市场趋势 (-100到+100)
        volatility: 波动率 (日波动率, 0-0.05)

    Returns:
        权重字典 {T: 19.4, M: 11.1, ...} (总权重100%)

    状态分类:
        强势趋势 (|regime| > 60): 趋势为王
        震荡市场 (|regime| < 30): 结构和资金重要
        高波动 (vol > 0.03): 量价协同重要
        低波动 (vol < 0.01): 微观结构细节重要

    因子架构:
        Layer 1: 价格行为层 - T(趋势), M(动量), S(结构), V(量能)
        Layer 2: 资金流层 - C(CVD), O(OI), F(资金领先)
        Layer 3: 微观结构层 - L(流动性), B(基差), Q(清算)
        Layer 4: 市场环境层 - I(独立性)
    """
    # ========== 趋势状态 ==========
    if abs(market_regime) > 60:
        # 强势趋势 (牛市或熊市)
        # 策略: 趋势为王，跟随主趋势
        return {
            # Layer 1: 价格行为 (趋势主导)
            "T": 19.4,  # 趋势 ↑ (13.9→19.4)
            "M": 11.1,  # 动量 ↑ (8.3→11.1)
            "S": 2.8,   # 结构 ↓ (5.6→2.8, 趋势市结构不重要)
            "V": 5.6,   # 量能 ↓ (8.3→5.6)
            # Layer 2: 资金流
            "C": 8.3,   # CVD ↓ (11.1→8.3)
            "O": 8.3,   # 持仓 ↓ (11.1→8.3)
            "F": 10.0,  # 资金领先 (参与评分)
            # Layer 3: 微观结构
            "L": 8.3,   # 流动性
            "B": 11.1,  # 基差 (趋势市基差重要)
            "Q": 8.3,   # 清算
            # Layer 4: 市场环境
            "I": 6.7,   # 独立性
        }  # 总计: 99.9% ≈ 100%

    elif abs(market_regime) < 30:
        # 震荡市场 (横盘)
        # 策略: 结构和资金流重要，趋势不可靠
        return {
            # Layer 1: 价格行为 (趋势不可靠)
            "T": 8.3,   # 趋势 ↓ (13.9→8.3, 震荡时趋势不可靠)
            "M": 5.6,   # 动量 ↓ (8.3→5.6)
            "S": 8.3,   # 结构 ↑ (5.6→8.3, 支撑阻力重要)
            "V": 6.7,   # 量能 ↓ (8.3→6.7)
            # Layer 2: 资金流 (震荡时最重要)
            "C": 13.9,  # CVD ↑ (11.1→13.9)
            "O": 13.9,  # 持仓 ↑ (11.1→13.9)
            "F": 11.1,  # 资金领先 ↑ (10.0→11.1, 领先性关键)
            # Layer 3: 微观结构
            "L": 12.2,  # 流动性 (震荡时流动性关键)
            "B": 10.0,  # 基差
            "Q": 4.4,   # 清算
            # Layer 4: 市场环境
            "I": 5.6,   # 独立性
        }  # 总计: 100.0%

    # ========== 波动率状态 ==========
    elif volatility > 0.03:
        # 高波动市场
        # 策略: 量价协同，风控优先
        return {
            # Layer 1: 价格行为
            "T": 11.1,  # 趋势 ↓ (高波动时趋势易反转)
            "M": 10.0,  # 动量 ↑ (8.3→10.0)
            "S": 6.7,   # 结构 ↑ (5.6→6.7)
            "V": 6.7,   # 量能 ↓ (8.3→6.7)
            # Layer 2: 资金流 (高波动时关键)
            "C": 12.2,  # CVD ↑ (11.1→12.2)
            "O": 13.9,  # 持仓 ↑ (11.1→13.9, OI波动显著)
            "F": 6.7,   # 资金领先 (10.0→6.7, 高波动时领先性部分失效)
            # Layer 3: 微观结构
            "L": 10.0,  # 流动性
            "B": 6.7,   # 基差 (高波动基差不稳定)
            "Q": 8.3,   # 清算 (清算风险高)
            # Layer 4: 市场环境
            "I": 7.8,   # 独立性
        }  # 总计: 100.1% ≈ 100%

    elif volatility < 0.01:
        # 低波动市场
        # 策略: 微观结构细节，捕捉小波动
        return {
            # Layer 1: 价格行为
            "T": 16.7,  # 趋势 ↑ (13.9→16.7, 低波动时趋势稳定)
            "M": 6.7,   # 动量 ↓ (8.3→6.7)
            "S": 4.4,   # 结构 ↓ (5.6→4.4)
            "V": 8.3,   # 量能 = (8.3→8.3)
            # Layer 2: 资金流
            "C": 10.0,  # CVD ↓ (11.1→10.0)
            "O": 10.0,  # 持仓 ↓ (11.1→10.0)
            "F": 8.9,   # 资金领先 (10.0→8.9)
            # Layer 3: 微观结构 (低波动细节重要)
            "L": 12.2,  # 流动性 (流动性细节)
            "B": 10.0,  # 基差
            "Q": 4.4,   # 清算
            # Layer 4: 市场环境
            "I": 8.3,   # 独立性
        }  # 总计: 99.9% ≈ 100%

    else:
        # 正常市场 (默认权重，匹配base_weights + F)
        return {
            # Layer 1: 价格行为
            "T": 13.9, "M": 8.3, "S": 5.6, "V": 8.3,
            # Layer 2: 资金流
            "C": 11.1, "O": 11.1, "F": 10.0,
            # Layer 3: 微观结构
            "L": 11.1, "B": 8.3, "Q": 5.6,
            # Layer 4: 市场环境
            "I": 6.7,
        }  # 总计: 100.0%


def blend_weights(
    regime_weights: Dict[str, float],
    base_weights: Dict[str, float],
    blend_ratio: float = 0.7
) -> Dict[str, float]:
    """
    平滑混合regime权重和基础权重

    Args:
        regime_weights: 状态依赖权重
        base_weights: 基础权重
        blend_ratio: 混合比例 (0-1)
            0 = 完全使用base_weights
            1 = 完全使用regime_weights
            0.7 = 70%regime + 30%base (推荐)

    Returns:
        混合后的权重

    目的: 避免权重跳变过于剧烈

    注意: 总权重目标为100%
    """
    blended = {}

    for dim in base_weights.keys():
        base_w = base_weights.get(dim, 0)
        regime_w = regime_weights.get(dim, base_w)

        # 线性插值
        blended[dim] = round(
            blend_ratio * regime_w + (1 - blend_ratio) * base_w,
            1  # 保留1位小数
        )

    # 确保总权重=100% (10+1因子系统)
    total = sum(blended.values())
    target_weight = 100.0

    if abs(total - target_weight) > 0.1:
        # 按比例归一化所有维度（避免单个维度权重异常）
        scale_factor = target_weight / total if total > 0 else 1.0
        for dim in blended:
            blended[dim] = round(blended[dim] * scale_factor, 1)

        # 修正舍入误差：调整最大权重维度
        actual_total = sum(blended.values())
        if abs(actual_total - target_weight) > 0.1:
            max_dim = max(blended, key=blended.get)
            adjustment = target_weight - actual_total
            blended[max_dim] = round(blended[max_dim] + adjustment, 1)

            # 安全检查：确保权重合理（0-100范围）
            if blended[max_dim] < 0 or blended[max_dim] > 100:
                raise ValueError(
                    f"权重归一化失败：{max_dim}={blended[max_dim]} 超出合理范围[0,100]。"
                    f"blend_ratio={blend_ratio}, total={total}, target={target_weight}"
                )

    return blended


# ========== 测试 ==========

if __name__ == "__main__":
    print("=" * 60)
    print("Regime-Dependent Weights 测试")
    print("=" * 60)

    scenarios = [
        (70, 0.015, "强势牛市 + 正常波动"),
        (-70, 0.015, "强势熊市 + 正常波动"),
        (20, 0.008, "震荡市场 + 低波动"),
        (50, 0.035, "温和趋势 + 高波动"),
        (0, 0.015, "完全震荡 + 正常波动"),
    ]

    base_weights = {
        # Layer 1: 价格行为
        "T": 13.9, "M": 8.3, "S": 5.6, "V": 8.3,
        # Layer 2: 资金流
        "C": 11.1, "O": 11.1, "F": 10.0,
        # Layer 3: 微观结构
        "L": 11.1, "B": 8.3, "Q": 5.6,
        # Layer 4: 市场环境
        "I": 6.7,
    }  # 总计: 100.0%

    for regime, vol, desc in scenarios:
        print(f"\n{desc}")
        print(f"  Market Regime: {regime:+d}")
        print(f"  Volatility:    {vol:.3f}")

        # 获取regime权重
        regime_w = get_regime_weights(regime, vol)

        # 平滑混合
        final_w = blend_weights(regime_w, base_weights, blend_ratio=0.7)

        print("  权重调整:")
        for dim in ["T", "M", "C", "V", "O", "F", "S", "L", "B", "Q", "I"]:
            base = base_weights.get(dim, 0)
            final = final_w.get(dim, 0)
            change = final - base
            marker = "↑" if change > 0 else "↓" if change < 0 else "-"
            print(f"    {dim}: {base:4.1f} → {final:4.1f} ({change:+4.1f}) {marker}")

        print(f"  总权重: {sum(final_w.values()):.1f}")

    print("\n" + "=" * 60)
    print("✅ 自适应权重模块测试完成")
    print("=" * 60)
