# coding: utf-8
"""
因子分组模块（v7.2阶段1）

设计理念：
- 减少共线性：将高度相关的因子合并
- 分工明确：核心、确认、情绪三组
- 权重稳定：3组权重比6个独立因子更稳定

分组方案：
- TC组（50%）：趋势(T) + 资金流(C) = 核心动力
- VOM组（35%）：量能(V) + 持仓(O) + 动量(M) = 确认
- B组（15%）：基差(B) = 情绪

理论依据：
1. T和C：趋势是表象，资金流是本质，二者高度相关但互补
2. V/O/M：都是"确认"因子，验证趋势的有效性
3. B：独立的情绪指标，权重最低
"""

from typing import Dict, Tuple


def calculate_grouped_score(
    T: float,
    M: float,
    C: float,
    V: float,
    O: float,
    B: float,
    params: Dict = None
) -> Tuple[float, Dict]:
    """
    计算分组加权分数（v7.2阶段1）

    分组方案：
    - TC组：趋势主导(70%) + 资金流辅助(30%)
    - VOM组：量能主导(50%) + 持仓辅助(30%) + 动量辅助(20%)
    - B组：独立

    最终权重：
    - TC组：50%
    - VOM组：35%
    - B组：15%

    Args:
        T, M, C, V, O, B: 6个A层因子分数（±100）
        params: 可选参数（用于自定义权重）

    Returns:
        (weighted_score, meta_dict)
    """
    if params is None:
        params = {}

    # === 1. TC组（趋势+资金流）===
    # T主导（70%），C辅助（30%）
    TC_T_weight = params.get("TC_T_weight", 0.70)
    TC_C_weight = params.get("TC_C_weight", 0.30)

    TC_group = TC_T_weight * T + TC_C_weight * C

    # === 2. VOM组（量能+持仓+动量）===
    # V主导（50%），O辅助（30%），M辅助（20%）
    VOM_V_weight = params.get("VOM_V_weight", 0.50)
    VOM_O_weight = params.get("VOM_O_weight", 0.30)
    VOM_M_weight = params.get("VOM_M_weight", 0.20)

    VOM_group = VOM_V_weight * V + VOM_O_weight * O + VOM_M_weight * M

    # === 3. B组（基差）===
    B_group = B

    # === 4. 最终加权 ===
    # TC组50%，VOM组35%，B组15%
    TC_weight = params.get("TC_weight", 0.50)
    VOM_weight = params.get("VOM_weight", 0.35)
    B_weight = params.get("B_weight", 0.15)

    weighted_score = TC_weight * TC_group + VOM_weight * VOM_group + B_weight * B_group

    # === 5. 元数据 ===
    meta = {
        "TC_group": round(TC_group, 2),
        "VOM_group": round(VOM_group, 2),
        "B_group": round(B_group, 2),
        "weights": {
            "TC": TC_weight,
            "VOM": VOM_weight,
            "B": B_weight
        },
        "group_details": {
            "TC": {
                "T": round(T, 1),
                "C": round(C, 1),
                "T_weight": TC_T_weight,
                "C_weight": TC_C_weight,
                "value": round(TC_group, 2)
            },
            "VOM": {
                "V": round(V, 1),
                "O": round(O, 1),
                "M": round(M, 1),
                "V_weight": VOM_V_weight,
                "O_weight": VOM_O_weight,
                "M_weight": VOM_M_weight,
                "value": round(VOM_group, 2)
            },
            "B": {
                "value": round(B, 1)
            }
        }
    }

    return weighted_score, meta


def compare_with_original(
    T: float, M: float, C: float, V: float, O: float, B: float,
    original_weights: Dict = None
) -> Dict:
    """
    对比新旧权重系统的结果

    用于测试和验证

    Args:
        T, M, C, V, O, B: 6个因子分数
        original_weights: 原始权重（v7.0）

    Returns:
        对比结果字典
    """
    # v7.0原始权重
    if original_weights is None:
        original_weights = {
            "T": 0.24,
            "M": 0.17,
            "C": 0.24,
            "V": 0.12,
            "O": 0.17,
            "B": 0.06
        }

    # 原始方法
    score_original = (
        T * original_weights["T"] +
        M * original_weights["M"] +
        C * original_weights["C"] +
        V * original_weights["V"] +
        O * original_weights["O"] +
        B * original_weights["B"]
    )

    # 新方法（分组）
    score_grouped, meta_grouped = calculate_grouped_score(T, M, C, V, O, B)

    return {
        "original_score": round(score_original, 2),
        "grouped_score": round(score_grouped, 2),
        "difference": round(score_grouped - score_original, 2),
        "original_weights": original_weights,
        "grouped_meta": meta_grouped
    }


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("因子分组测试")
    print("=" * 60)

    # 测试1：强势多头信号
    print("\n测试1：强势多头信号")
    T, M, C, V, O, B = 80, 70, 75, 60, 65, 20
    score, meta = calculate_grouped_score(T, M, C, V, O, B)
    print(f"  T={T}, M={M}, C={C}, V={V}, O={O}, B={B}")
    print(f"  TC组: {meta['TC_group']:.1f} (T×70% + C×30%)")
    print(f"  VOM组: {meta['VOM_group']:.1f} (V×50% + O×30% + M×20%)")
    print(f"  B组: {meta['B_group']:.1f}")
    print(f"  最终分数: {score:.2f}")

    # 对比原始方法
    comparison = compare_with_original(T, M, C, V, O, B)
    print(f"\n  对比原始方法:")
    print(f"    原始分数: {comparison['original_score']}")
    print(f"    分组分数: {comparison['grouped_score']}")
    print(f"    差异: {comparison['difference']}")

    # 测试2：弱势空头信号
    print("\n测试2：弱势空头信号")
    T, M, C, V, O, B = -60, -50, -55, -40, -45, -15
    score, meta = calculate_grouped_score(T, M, C, V, O, B)
    print(f"  T={T}, M={M}, C={C}, V={V}, O={O}, B={B}")
    print(f"  TC组: {meta['TC_group']:.1f}")
    print(f"  VOM组: {meta['VOM_group']:.1f}")
    print(f"  B组: {meta['B_group']:.1f}")
    print(f"  最终分数: {score:.2f}")

    comparison = compare_with_original(T, M, C, V, O, B)
    print(f"\n  对比原始方法:")
    print(f"    原始分数: {comparison['original_score']}")
    print(f"    分组分数: {comparison['grouped_score']}")
    print(f"    差异: {comparison['difference']}")

    # 测试3：震荡信号
    print("\n测试3：震荡信号")
    T, M, C, V, O, B = 10, -5, 15, 20, -10, 5
    score, meta = calculate_grouped_score(T, M, C, V, O, B)
    print(f"  T={T}, M={M}, C={C}, V={V}, O={O}, B={B}")
    print(f"  TC组: {meta['TC_group']:.1f}")
    print(f"  VOM组: {meta['VOM_group']:.1f}")
    print(f"  B组: {meta['B_group']:.1f}")
    print(f"  最终分数: {score:.2f}")

    comparison = compare_with_original(T, M, C, V, O, B)
    print(f"\n  对比原始方法:")
    print(f"    原始分数: {comparison['original_score']}")
    print(f"    分组分数: {comparison['grouped_score']}")
    print(f"    差异: {comparison['difference']}")

    print("\n" + "=" * 60)
