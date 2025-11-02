# coding: utf-8
"""
自适应权重系统 - Regime-Dependent

根据市场状态动态调整因子权重

理论基础: Adaptive Asset Allocation
不同市场regime下，因子有效性不同

⚠️ 重要修改 (v2.0):
- F/I 因子已从评分权重中移除（按newstandards/MODULATORS.md规范）
- F/I 仅用于调节温度/成本/门槛，不参与方向性评分
- 总计9个方向性因子: T/M/S/V/C/O/L/B/Q
"""
from typing import Dict


def get_regime_weights(market_regime: int, volatility: float) -> Dict[str, float]:
    """
    根据市场状态返回最优权重配置（9维方向因子系统）

    Args:
        market_regime: 市场趋势 (-100到+100)
        volatility: 波动率 (日波动率, 0-0.05)

    Returns:
        权重字典 {T: 20.0, M: 12.0, ...} (总权重100%)

    状态分类:
        强势趋势 (|regime| > 60): 趋势为王
        震荡市场 (|regime| < 30): 结构和资金重要
        高波动 (vol > 0.03): 量价协同重要
        低波动 (vol < 0.01): 微观结构细节重要

    因子架构 (v2.0):
        Layer A: 方向因子 - T(趋势), M(动量), S(结构), V(量能), C(CVD), O(OI), Q(清算), L(流动性), B(基差)
        Layer B: 调节器 - F(资金拥挤), I(独立性) [不参与评分！仅调节Teff/cost/门槛]
    """
    # ========== 趋势状态 ==========
    if abs(market_regime) > 60:
        # 强势趋势 (牛市或熊市)
        # 策略: 趋势为王，跟随主趋势
        return {
            # Layer A: 方向因子 (趋势主导)
            "T": 24.0,  # 趋势 ↑ (13.9→24.0, 补回F/I的权重)
            "M": 13.0,  # 动量 ↑ (8.3→13.0)
            "S": 3.0,   # 结构 ↓ (5.6→3.0, 趋势市结构不重要)
            "V": 6.0,   # 量能 ↓ (8.3→6.0)
            # Layer A: 资金流
            "C": 10.0,  # CVD ↓ (11.1→10.0)
            "O": 10.0,  # 持仓 ↓ (11.1→10.0)
            # Layer A: 微观结构
            "L": 10.0,  # 流动性
            "B": 14.0,  # 基差 ↑ (8.3→14.0, 趋势市基差重要)
            "Q": 10.0,  # 清算 ↑ (5.6→10.0)
        }  # 总计: 100.0% (F/I已移除，权重重新分配)

    elif abs(market_regime) < 30:
        # 震荡市场 (横盘)
        # 策略: 结构和资金流重要，趋势不可靠
        return {
            # Layer A: 方向因子 (趋势不可靠)
            "T": 9.0,   # 趋势 ↓ (13.9→9.0, 震荡时趋势不可靠)
            "M": 6.0,   # 动量 ↓ (8.3→6.0)
            "S": 11.0,  # 结构 ↑ (5.6→11.0, 支撑阻力重要)
            "V": 7.0,   # 量能 ↓ (8.3→7.0)
            # Layer A: 资金流 (震荡时最重要)
            "C": 17.0,  # CVD ↑ (11.1→17.0, 补回F权重)
            "O": 17.0,  # 持仓 ↑ (11.1→17.0)
            # Layer A: 微观结构
            "L": 16.0,  # 流动性 ↑ (11.1→16.0, 震荡时流动性关键)
            "B": 12.0,  # 基差 ↑ (8.3→12.0)
            "Q": 5.0,   # 清算 ↓ (5.6→5.0)
        }  # 总计: 100.0% (F/I已移除)

    # ========== 波动率状态 ==========
    elif volatility > 0.03:
        # 高波动市场
        # 策略: 量价协同，风控优先
        return {
            # Layer A: 方向因子
            "T": 12.0,  # 趋势 ↓ (高波动时趋势易反转)
            "M": 12.0,  # 动量 ↑ (8.3→12.0)
            "S": 8.0,   # 结构 ↑ (5.6→8.0)
            "V": 8.0,   # 量能 ↓ (8.3→8.0)
            # Layer A: 资金流 (高波动时关键)
            "C": 15.0,  # CVD ↑ (11.1→15.0)
            "O": 17.0,  # 持仓 ↑ (11.1→17.0, OI波动显著)
            # Layer A: 微观结构
            "L": 12.0,  # 流动性 ↑ (11.1→12.0)
            "B": 7.0,   # 基差 ↓ (8.3→7.0, 高波动基差不稳定)
            "Q": 9.0,   # 清算 ↑ (5.6→9.0, 清算风险高)
        }  # 总计: 100.0% (F/I已移除)

    elif volatility < 0.01:
        # 低波动市场
        # 策略: 微观结构细节，捕捉小波动
        return {
            # Layer A: 方向因子
            "T": 22.0,  # 趋势 ↑ (13.9→22.0, 低波动时趋势稳定，补回F/I权重)
            "M": 8.0,   # 动量 ↓ (8.3→8.0)
            "S": 5.0,   # 结构 ↓ (5.6→5.0)
            "V": 10.0,  # 量能 ↑ (8.3→10.0)
            # Layer A: 资金流
            "C": 12.0,  # CVD ↑ (11.1→12.0)
            "O": 12.0,  # 持仓 ↑ (11.1→12.0)
            # Layer A: 微观结构 (低波动细节重要)
            "L": 15.0,  # 流动性 ↑ (11.1→15.0, 流动性细节)
            "B": 11.0,  # 基差 ↑ (8.3→11.0)
            "Q": 5.0,   # 清算 ↓ (5.6→5.0)
        }  # 总计: 100.0% (F/I已移除)

    else:
        # 正常市场 (默认权重，按newstandards基线: T18/M12/S10/V10/C18/O18/Q4)
        # 9个方向因子总计100%，F/I已移除
        return {
            # Layer A: 方向因子 (标准配置)
            "T": 18.0,  # 趋势 ↑ (13.9→18.0, 补回F的10%)
            "M": 12.0,  # 动量 ↑ (8.3→12.0)
            "S": 10.0,  # 结构 ↑ (5.6→10.0)
            "V": 10.0,  # 量能 ↑ (8.3→10.0)
            # Layer A: 资金流
            "C": 18.0,  # CVD ↑ (11.1→18.0)
            "O": 18.0,  # 持仓 ↑ (11.1→18.0)
            # Layer A: 微观结构
            "L": 8.0,   # 流动性 ↓ (11.1→8.0)
            "B": 2.0,   # 基差 ↓ (8.3→2.0)
            "Q": 4.0,   # 清算 ↓ (5.6→4.0)
        }  # 总计: 100.0% (符合newstandards基线配置)


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

    # 只处理因子权重，跳过注释字段（以_开头的字段）
    for dim in base_weights.keys():
        if dim.startswith('_'):
            continue  # 跳过注释字段

        base_w = base_weights.get(dim, 0)
        regime_w = regime_weights.get(dim, base_w)

        # 确保权重是数值类型
        if not isinstance(base_w, (int, float)) or not isinstance(regime_w, (int, float)):
            continue  # 跳过非数值字段

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
        # Layer A: 方向因子 (v2.0 - F/I已移除)
        "T": 18.0, "M": 12.0, "S": 10.0, "V": 10.0,
        "C": 18.0, "O": 18.0,
        "L": 8.0, "B": 2.0, "Q": 4.0,
    }  # 总计: 100.0% (9个方向因子)

    for regime, vol, desc in scenarios:
        print(f"\n{desc}")
        print(f"  Market Regime: {regime:+d}")
        print(f"  Volatility:    {vol:.3f}")

        # 获取regime权重
        regime_w = get_regime_weights(regime, vol)

        # 平滑混合
        final_w = blend_weights(regime_w, base_weights, blend_ratio=0.7)

        print("  权重调整:")
        for dim in ["T", "M", "S", "V", "C", "O", "L", "B", "Q"]:
            base = base_weights.get(dim, 0)
            final = final_w.get(dim, 0)
            change = final - base
            marker = "↑" if change > 0 else "↓" if change < 0 else "-"
            print(f"    {dim}: {base:4.1f} → {final:4.1f} ({change:+4.1f}) {marker}")

        print(f"  总权重: {sum(final_w.values()):.1f}")
        print(f"  注: F/I已移除，仅用于调节Teff/cost/门槛")

    print("\n" + "=" * 60)
    print("✅ 自适应权重模块测试完成")
    print("=" * 60)
