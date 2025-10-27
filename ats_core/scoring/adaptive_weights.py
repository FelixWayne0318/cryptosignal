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
    根据市场状态返回最优权重配置

    Args:
        market_regime: 市场趋势 (-100到+100)
        volatility: 波动率 (日波动率, 0-0.05)

    Returns:
        权重字典 {T: 30, M: 10, ...}

    状态分类:
        强势趋势 (|regime| > 60): 趋势为王
        震荡市场 (|regime| < 30): 结构和资金重要
        高波动 (vol > 0.03): 量价协同重要
        低波动 (vol < 0.01): 微观结构细节重要
    """
    # ========== 趋势状态 ==========
    if abs(market_regime) > 60:
        # 强势趋势 (牛市或熊市)
        # 策略: 趋势为王，跟随主趋势
        return {
            "T": 40,   # 趋势 ↑ (30→40)
            "M": 10,   # 动量 ↑ (5→10)
            "C": 15,   # 资金 ↓ (17→15)
            "O": 15,   # 持仓 ↓ (18→15)
            "V": 10,   # 量能 ↓ (20→10)
            "F": 8,    # 资金领先 ↑ (7→8)
            "S": 1,    # 结构 - (保持)
            "E": 1     # 环境 ↓ (2→1)
        }

    elif abs(market_regime) < 30:
        # 震荡市场 (横盘)
        # 策略: 结构和资金流重要，趋势不可靠
        return {
            "T": 20,   # 趋势 ↓ (30→20, 震荡时趋势不可靠)
            "M": 5,    # 动量 - (保持)
            "C": 20,   # 资金 ↑ (17→20, 震荡时资金流更重要)
            "O": 20,   # 持仓 ↑ (18→20)
            "V": 15,   # 量能 ↓ (20→15)
            "F": 10,   # 资金领先 ↑ (7→10, 震荡时领先性关键)
            "S": 5,    # 结构 ↑ (1→5, 震荡时支撑阻力重要)
            "E": 5     # 环境 ↑ (2→5, 震荡时空间判断重要)
        }

    # ========== 波动率状态 ==========
    elif volatility > 0.03:
        # 高波动市场
        # 策略: 量价协同，风控优先
        return {
            "T": 25,   # 趋势 ↓ (高波动时趋势易反转)
            "M": 8,    # 动量 ↑
            "C": 18,   # 资金 ↑
            "O": 22,   # 持仓 ↑ (高波动时OI变化显著)
            "V": 15,   # 量能 ↓ (高波动时量能不稳定)
            "F": 5,    # 资金领先 ↓ (高波动时领先性失效)
            "S": 3,    # 结构 ↑
            "E": 4     # 环境 ↑ (高波动需关注空间)
        }

    elif volatility < 0.01:
        # 低波动市场
        # 策略: 微观结构细节，捕捉小波动
        return {
            "T": 35,   # 趋势 ↑ (低波动时趋势稳定)
            "M": 5,    # 动量 - (低波动时动量不明显)
            "C": 15,   # 资金 ↓
            "O": 15,   # 持仓 ↓
            "V": 18,   # 量能 ↓ (低波动时量能相对重要)
            "F": 8,    # 资金领先 ↑
            "S": 2,    # 结构 ↑
            "E": 2     # 环境 -
        }

    else:
        # 正常市场 (默认权重)
        return {
            "T": 30,
            "C": 17,
            "O": 18,
            "V": 20,
            "M": 5,
            "F": 7,
            "S": 1,
            "E": 2
        }


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
    """
    blended = {}

    for dim in base_weights.keys():
        base_w = base_weights.get(dim, 0)
        regime_w = regime_weights.get(dim, base_w)

        # 线性插值
        blended[dim] = int(round(
            blend_ratio * regime_w + (1 - blend_ratio) * base_w
        ))

    # 确保总权重=100
    total = sum(blended.values())
    if total != 100:
        # 调整最大权重维度
        max_dim = max(blended, key=blended.get)
        blended[max_dim] += (100 - total)

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
        "T": 30, "C": 17, "O": 18, "V": 20,
        "M": 5, "F": 7, "S": 1, "E": 2
    }

    for regime, vol, desc in scenarios:
        print(f"\n{desc}")
        print(f"  Market Regime: {regime:+d}")
        print(f"  Volatility:    {vol:.3f}")

        # 获取regime权重
        regime_w = get_regime_weights(regime, vol)

        # 平滑混合
        final_w = blend_weights(regime_w, base_weights, blend_ratio=0.7)

        print("  权重调整:")
        for dim in ["T", "M", "C", "V", "O", "F", "S", "E"]:
            base = base_weights[dim]
            final = final_w[dim]
            change = final - base
            marker = "↑" if change > 0 else "↓" if change < 0 else "-"
            print(f"    {dim}: {base:2d} → {final:2d} ({change:+2d}) {marker}")

        print(f"  总权重: {sum(final_w.values())}")

    print("\n" + "=" * 60)
    print("✅ 自适应权重模块测试完成")
    print("=" * 60)
