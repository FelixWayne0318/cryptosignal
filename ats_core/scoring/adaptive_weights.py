# coding: utf-8
"""
自适应权重系统 - Regime-Dependent

根据市场状态动态调整因子权重

理论基础: Adaptive Asset Allocation
不同市场regime下，因子有效性不同
"""
from typing import Dict


def get_regime_weights(market_regime: int, volatility: float) -> Dict[str, int]:
    """
    根据市场状态返回最优权重配置（10维因子系统）

    Args:
        market_regime: 市场趋势 (-100到+100)
        volatility: 波动率 (日波动率, 0-0.05)

    Returns:
        权重字典 {T: 35, M: 20, ...} (总权重160分)

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
            "T": 35,   # 趋势 ↑ (25→35)
            "M": 20,   # 动量 ↑ (15→20)
            "S": 5,    # 结构 ↓ (10→5, 趋势市结构不重要)
            "V": 10,   # 量能 ↓ (15→10)
            # Layer 2: 资金流
            "C": 15,   # CVD ↓ (20→15)
            "O": 15,   # 持仓 ↓ (20→15)
            "F": 18,   # 资金领先 ↑ (0→18, 参与评分)
            # Layer 3: 微观结构
            "L": 15,   # 流动性 (新增)
            "B": 20,   # 基差 (新增, 趋势市基差重要)
            "Q": 15,   # 清算 (新增)
            # Layer 4: 市场环境
            "I": 12,   # 独立性 (新增)
        }  # 总计: 180分

    elif abs(market_regime) < 30:
        # 震荡市场 (横盘)
        # 策略: 结构和资金流重要，趋势不可靠
        return {
            # Layer 1: 价格行为 (趋势不可靠)
            "T": 15,   # 趋势 ↓ (25→15, 震荡时趋势不可靠)
            "M": 10,   # 动量 ↓ (15→10)
            "S": 15,   # 结构 ↑ (10→15, 支撑阻力重要)
            "V": 12,   # 量能 ↓ (15→12)
            # Layer 2: 资金流 (震荡时最重要)
            "C": 25,   # CVD ↑ (20→25)
            "O": 25,   # 持仓 ↑ (20→25)
            "F": 20,   # 资金领先 ↑ (0→20, 领先性关键)
            # Layer 3: 微观结构
            "L": 22,   # 流动性 (新增, 震荡时流动性关键)
            "B": 18,   # 基差 (新增)
            "Q": 8,    # 清算 (新增)
            # Layer 4: 市场环境
            "I": 10,   # 独立性 (新增)
        }  # 总计: 180分

    # ========== 波动率状态 ==========
    elif volatility > 0.03:
        # 高波动市场
        # 策略: 量价协同，风控优先
        return {
            # Layer 1: 价格行为
            "T": 20,   # 趋势 ↓ (高波动时趋势易反转)
            "M": 18,   # 动量 ↑ (15→18)
            "S": 12,   # 结构 ↑ (10→12)
            "V": 12,   # 量能 ↓ (15→12)
            # Layer 2: 资金流 (高波动时关键)
            "C": 22,   # CVD ↑ (20→22)
            "O": 25,   # 持仓 ↑ (20→25, OI波动显著)
            "F": 12,   # 资金领先 (0→12, 高波动时领先性部分失效)
            # Layer 3: 微观结构
            "L": 18,   # 流动性 (新增)
            "B": 12,   # 基差 (新增, 高波动基差不稳定)
            "Q": 15,   # 清算 (新增, 清算风险高)
            # Layer 4: 市场环境
            "I": 14,   # 独立性 (新增)
        }  # 总计: 180分

    elif volatility < 0.01:
        # 低波动市场
        # 策略: 微观结构细节，捕捉小波动
        return {
            # Layer 1: 价格行为
            "T": 30,   # 趋势 ↑ (25→30, 低波动时趋势稳定)
            "M": 12,   # 动量 ↓ (15→12)
            "S": 8,    # 结构 ↓ (10→8)
            "V": 15,   # 量能 = (15→15)
            # Layer 2: 资金流
            "C": 18,   # CVD ↓ (20→18)
            "O": 18,   # 持仓 ↓ (20→18)
            "F": 16,   # 资金领先 (0→16)
            # Layer 3: 微观结构 (低波动细节重要)
            "L": 22,   # 流动性 (新增, 流动性细节)
            "B": 18,   # 基差 (新增)
            "Q": 8,    # 清算 (新增)
            # Layer 4: 市场环境
            "I": 15,   # 独立性 (新增)
        }  # 总计: 180分

    else:
        # 正常市场 (默认权重，匹配base_weights + F)
        return {
            # Layer 1: 价格行为
            "T": 25, "M": 15, "S": 10, "V": 15,
            # Layer 2: 资金流
            "C": 20, "O": 20, "F": 18,
            # Layer 3: 微观结构
            "L": 20, "B": 15, "Q": 10,
            # Layer 4: 市场环境
            "I": 12,
        }  # 总计: 180分


def blend_weights(
    regime_weights: Dict[str, int],
    base_weights: Dict[str, int],
    blend_ratio: float = 0.7
) -> Dict[str, int]:
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

    注意: 总权重目标为180（10+1因子系统）
    """
    blended = {}

    for dim in base_weights.keys():
        base_w = base_weights.get(dim, 0)
        regime_w = regime_weights.get(dim, base_w)

        # 线性插值
        blended[dim] = int(round(
            blend_ratio * regime_w + (1 - blend_ratio) * base_w
        ))

    # 确保总权重=180 (10+1因子系统: 10个评分因子 + F调节器现在也参与评分)
    total = sum(blended.values())
    target_weight = 180
    if total != target_weight:
        # 调整最大权重维度
        max_dim = max(blended, key=blended.get)
        blended[max_dim] += (target_weight - total)

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
        "T": 25, "M": 15, "S": 10, "V": 15,
        # Layer 2: 资金流
        "C": 20, "O": 20, "F": 18,
        # Layer 3: 微观结构
        "L": 20, "B": 15, "Q": 10,
        # Layer 4: 市场环境
        "I": 12,
    }  # 总计: 180分

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
            print(f"    {dim}: {base:2d} → {final:2d} ({change:+2d}) {marker}")

        print(f"  总权重: {sum(final_w.values())}")

    print("\n" + "=" * 60)
    print("✅ 自适应权重模块测试完成")
    print("=" * 60)
