"""
v7.4 Step1: 方向确认层 - Direction Confirmation Layer

Purpose:
    基于A层因子、I因子独立性、BTC对齐度，确认交易方向并计算置信度

Key Corrections (vs v1.0):
    1. I因子语义修正：I∈[0,100]，高值=独立(低Beta)，低值=跟随BTC(高Beta)
    2. 硬veto规则：高Beta币 + 强BTC趋势 + 反向 → 直接拒绝（防作死）
    3. BTC对齐系数：考虑独立性的动态调整

Implementation:
    - calculate_direction_confidence_v2(): I因子 → 置信度映射（修正版）
    - calculate_btc_alignment_v2(): BTC方向对齐系数
    - check_hard_veto(): 硬veto规则检查
    - step1_direction_confirmation(): 主入口函数

Author: Claude Code (based on Expert Plan)
Version: v7.4.2
Created: 2025-11-16
"""

from typing import Dict, Any, Optional
from ats_core.logging import log, warn


def calculate_direction_confidence_v2(
    direction_score: float,
    I_score: float,
    params: Dict[str, Any]
) -> float:
    """
    计算方向置信度（基于I因子独立性，修正版）

    Key Correction:
        v1.0错误: 假设I∈[-100,100]，I>0=独立
        v2.0正确: I∈[0,100]，高值=独立(低Beta)，低值=跟随BTC(高Beta)

    Mapping Logic (修正后):
        I < 15  (高Beta，严重跟随BTC)  → confidence ∈ [0.60, 0.70]
        I < 30  (中度跟随BTC)          → confidence ∈ [0.70, 0.85]
        I < 50  (轻度跟随BTC)          → confidence ∈ [0.85, 0.95]
        I >= 50 (独立行情)             → confidence ∈ [0.95, 1.00]

    Args:
        direction_score: A层方向得分（-100到+100）
        I_score: I因子独立性得分（0到100，高值=独立）
        params: 配置参数

    Returns:
        confidence: 方向置信度（0.50到1.00）
    """
    # 从配置读取阈值（零硬编码）
    step1_cfg = params.get("four_step_system", {}).get("step1_direction", {})
    I_thresholds = step1_cfg.get("I_thresholds", {})

    high_beta = I_thresholds.get("high_beta", 15)      # 默认15
    moderate_beta = I_thresholds.get("moderate_beta", 30)  # 默认30
    low_beta = I_thresholds.get("low_beta", 50)        # 默认50

    confidence_cfg = step1_cfg.get("confidence", {})
    floor = confidence_cfg.get("floor", 0.50)
    ceiling = confidence_cfg.get("ceiling", 1.00)

    # v7.4.2新增：从配置读取置信度映射曲线参数（消除硬编码）
    mapping = confidence_cfg.get("mapping", {})
    high_beta_base = mapping.get("high_beta_base", 0.60)
    high_beta_range = mapping.get("high_beta_range", 0.10)
    moderate_beta_base = mapping.get("moderate_beta_base", 0.70)
    moderate_beta_range = mapping.get("moderate_beta_range", 0.15)
    low_beta_base = mapping.get("low_beta_base", 0.85)
    low_beta_range = mapping.get("low_beta_range", 0.10)
    independent_base = mapping.get("independent_base", 0.95)
    independent_range = mapping.get("independent_range", 0.05)

    # 分段计算置信度（v2.0修正版 + v7.4.2配置化）
    if I_score < high_beta:
        # 高Beta（严重跟随BTC）→ 置信度低
        # I=0 → high_beta_base, I=high_beta → high_beta_base + high_beta_range
        confidence = high_beta_base + (I_score / high_beta) * high_beta_range

    elif I_score < moderate_beta:
        # 中度跟随BTC
        # I=high_beta → moderate_beta_base, I=moderate_beta → moderate_beta_base + moderate_beta_range
        progress = (I_score - high_beta) / (moderate_beta - high_beta)
        confidence = moderate_beta_base + progress * moderate_beta_range

    elif I_score < low_beta:
        # 轻度跟随BTC
        # I=moderate_beta → low_beta_base, I=low_beta → low_beta_base + low_beta_range
        progress = (I_score - moderate_beta) / (low_beta - moderate_beta)
        confidence = low_beta_base + progress * low_beta_range

    else:
        # 独立行情（I >= low_beta）
        # I=low_beta → independent_base, I=100 → independent_base + independent_range
        progress = (I_score - low_beta) / (100.0 - low_beta)
        confidence = independent_base + progress * independent_range

    # 截断到[floor, ceiling]范围
    confidence = max(floor, min(ceiling, confidence))

    return confidence


def calculate_btc_alignment_v2(
    direction_score: float,
    btc_direction_score: float,
    I_score: float,
    params: Dict[str, Any]
) -> float:
    """
    计算BTC方向对齐系数（v2版本，考虑独立性）

    Logic:
        - 同向: alignment = 0.90 + independence_factor * 0.10  (0.90-1.00)
        - 反向: alignment = 0.70 + independence_factor * 0.25  (0.70-0.95)

        independence_factor = I_score / 100.0

        含义: 独立性越高，反向时惩罚越小

    Args:
        direction_score: 本币方向得分
        btc_direction_score: BTC方向得分
        I_score: I因子独立性得分
        params: 配置参数

    Returns:
        alignment: BTC对齐系数（0.70到1.00）
    """
    # 从配置读取参数
    step1_cfg = params.get("four_step_system", {}).get("step1_direction", {})
    btc_cfg = step1_cfg.get("btc_alignment", {})

    same_dir_base = btc_cfg.get("same_direction_base", 0.90)
    same_dir_bonus = btc_cfg.get("same_direction_bonus", 0.10)
    opposite_dir_base = btc_cfg.get("opposite_direction_base", 0.70)
    opposite_dir_bonus = btc_cfg.get("opposite_direction_bonus", 0.25)

    # 计算独立性因子（0-1）
    independence_factor = I_score / 100.0

    # 判断是否同向
    same_direction = (direction_score * btc_direction_score) > 0

    if same_direction:
        # 同向：基础对齐度高
        alignment = same_dir_base + independence_factor * same_dir_bonus
    else:
        # 反向：基础对齐度低，但独立性高的币惩罚减小
        alignment = opposite_dir_base + independence_factor * opposite_dir_bonus

    # 限制在合理范围
    alignment = max(0.70, min(1.00, alignment))

    return alignment


def check_hard_veto(
    direction_score: float,
    btc_direction_score: float,
    btc_trend_strength: float,
    I_score: float,
    params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    检查硬veto规则：高Beta币 vs 强BTC趋势 - 防作死底线

    Hard Veto Condition:
        1. I_score < high_beta_threshold (高Beta，严重跟随BTC)
        2. abs(btc_trend_strength) > strong_btc_threshold (BTC趋势很强)
        3. direction_score * btc_direction_score < 0 (本币方向与BTC相反)

        三者同时满足 → 硬veto，直接拒绝

    Rationale:
        高Beta币在强BTC趋势下逆势操作，风险极高，必须拒绝

    Args:
        direction_score: 本币方向得分
        btc_direction_score: BTC方向得分
        btc_trend_strength: BTC趋势强度（abs值）
        I_score: I因子独立性得分
        params: 配置参数

    Returns:
        dict: {
            "hard_veto": bool,         # 是否触发硬veto
            "veto_reason": str or None # veto原因
        }
    """
    # 从配置读取硬veto参数
    step1_cfg = params.get("four_step_system", {}).get("step1_direction", {})
    veto_cfg = step1_cfg.get("hard_veto", {})

    enabled = veto_cfg.get("enabled", True)
    high_beta_threshold = veto_cfg.get("high_beta_threshold", 30)
    strong_btc_threshold = veto_cfg.get("strong_btc_threshold", 70.0)

    # 如果未启用，直接返回
    if not enabled:
        return {"hard_veto": False, "veto_reason": None}

    # 检查三个条件
    is_high_beta = I_score < high_beta_threshold
    is_strong_btc = abs(btc_trend_strength) > strong_btc_threshold
    is_opposite = (direction_score * btc_direction_score) < 0

    # 三者同时满足 → 硬veto
    if is_high_beta and is_strong_btc and is_opposite:
        veto_reason = (
            f"High Beta coin (I={I_score:.0f} < {high_beta_threshold}) "
            f"vs strong BTC trend (|T_BTC|={abs(btc_trend_strength):.0f} > {strong_btc_threshold}) "
            f"in opposite direction - Hard Veto"
        )

        warn(f"🚫 {veto_reason}")

        return {
            "hard_veto": True,
            "veto_reason": veto_reason
        }

    return {"hard_veto": False, "veto_reason": None}


def step1_direction_confirmation(
    factor_scores: Dict[str, float],
    btc_factor_scores: Dict[str, float],
    params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Step1主函数：方向确认层

    Pipeline:
        1. 计算A层方向得分（加权平均）
        2. 基于I因子计算方向置信度（v2修正版）
        3. 基于BTC对齐计算对齐系数（v2版本）
        4. 检查硬veto规则（防作死）
        5. 计算最终强度 = direction_strength * confidence * alignment
        6. 判断是否通过（final_strength >= min_final_strength）

    Args:
        factor_scores: 本币因子得分 {"T": float, "M": float, ...}
        btc_factor_scores: BTC因子得分 {"T": float, ...}
        params: 配置参数

    Returns:
        dict: {
            "pass": bool,                    # 是否通过Step1
            "direction_score": float,        # A层方向得分
            "direction_strength": float,     # abs(direction_score)
            "direction_confidence": float,   # I因子置信度
            "btc_alignment": float,          # BTC对齐系数
            "final_strength": float,         # 最终强度
            "hard_veto": bool,               # 是否触发硬veto
            "reject_reason": str or None,    # 拒绝原因
            "metadata": dict                 # 详细元数据
        }
    """
    # 获取配置
    step1_cfg = params.get("four_step_system", {}).get("step1_direction", {})
    weights = step1_cfg.get("weights", {})
    min_final_strength = step1_cfg.get("min_final_strength", 20.0)

    # 1. 计算A层方向得分（加权平均）
    # 过滤掉配置中的注释字段（以"_"开头的键）
    numeric_weights = {k: v for k, v in weights.items() if not k.startswith("_") and isinstance(v, (int, float))}

    direction_score = (
        factor_scores.get("T", 0.0) * numeric_weights.get("T", 0.23) +
        factor_scores.get("M", 0.0) * numeric_weights.get("M", 0.10) +
        factor_scores.get("C", 0.0) * numeric_weights.get("C", 0.26) +
        factor_scores.get("V", 0.0) * numeric_weights.get("V", 0.11) +
        factor_scores.get("O", 0.0) * numeric_weights.get("O", 0.20) +
        factor_scores.get("B", 0.0) * numeric_weights.get("B", 0.10)
    )

    # 归一化（如果权重总和不为1）
    weight_sum = sum(numeric_weights.values())
    if weight_sum > 0 and abs(weight_sum - 1.0) > 0.01:
        direction_score = direction_score / weight_sum

    direction_strength = abs(direction_score)

    # 获取I因子和BTC因子
    I_score = factor_scores.get("I", 50.0)  # 默认中性
    btc_direction_score = btc_factor_scores.get("T", 0.0)
    btc_trend_strength = abs(btc_direction_score)

    # 2. 检查硬veto（优先级最高）
    veto_result = check_hard_veto(
        direction_score,
        btc_direction_score,
        btc_trend_strength,
        I_score,
        params
    )

    if veto_result["hard_veto"]:
        return {
            "pass": False,
            "direction_score": direction_score,
            "direction_strength": direction_strength,
            "direction_confidence": 0.0,
            "btc_alignment": 0.0,
            "final_strength": 0.0,
            "hard_veto": True,
            "reject_reason": veto_result["veto_reason"],
            "metadata": {
                "I_score": I_score,
                "btc_direction_score": btc_direction_score,
                "btc_trend_strength": btc_trend_strength
            }
        }

    # 3. 计算方向置信度（v2修正版）
    direction_confidence = calculate_direction_confidence_v2(
        direction_score,
        I_score,
        params
    )

    # 4. 计算BTC对齐系数（v2版本）
    btc_alignment = calculate_btc_alignment_v2(
        direction_score,
        btc_direction_score,
        I_score,
        params
    )

    # 5. 计算最终强度
    final_strength = direction_strength * direction_confidence * btc_alignment

    # 6. 判断是否通过
    pass_step1 = final_strength >= min_final_strength

    reject_reason = None
    if not pass_step1:
        reject_reason = (
            f"Final strength insufficient: {final_strength:.1f} < {min_final_strength}"
        )

    # 返回完整结果
    return {
        "pass": pass_step1,
        "direction_score": direction_score,
        "direction_strength": direction_strength,
        "direction_confidence": direction_confidence,
        "btc_alignment": btc_alignment,
        "final_strength": final_strength,
        "hard_veto": False,
        "reject_reason": reject_reason,
        "metadata": {
            "I_score": I_score,
            "btc_direction_score": btc_direction_score,
            "btc_trend_strength": btc_trend_strength,
            "weights": weights,
            "min_final_strength": min_final_strength
        }
    }


# ============ 测试用例 ============

if __name__ == "__main__":
    """
    测试Step1方向确认层

    Usage:
        python3 -m ats_core.decision.step1_direction
    """
    print("="*70)
    print("v7.4 Step1: 方向确认层测试")
    print("="*70)

    # 模拟配置
    test_params = {
        "four_step_system": {
            "step1_direction": {
                "min_final_strength": 20.0,
                "weights": {
                    "T": 0.23, "M": 0.10, "C": 0.26,
                    "V": 0.11, "O": 0.20, "B": 0.10
                },
                "I_thresholds": {
                    "high_beta": 15,
                    "moderate_beta": 30,
                    "low_beta": 50,
                    "independent": 85
                },
                "btc_alignment": {
                    "strong_trend_threshold": 70.0,
                    "same_direction_base": 0.90,
                    "same_direction_bonus": 0.10,
                    "opposite_direction_base": 0.70,
                    "opposite_direction_bonus": 0.25
                },
                "hard_veto": {
                    "enabled": True,
                    "high_beta_threshold": 30,
                    "strong_btc_threshold": 70.0
                },
                "confidence": {
                    "floor": 0.50,
                    "ceiling": 1.00
                }
            }
        }
    }

    # 测试用例1：高独立性 + 同向BTC
    print("\n📊 测试用例1：高独立性币(I=90) + 同向BTC(T_BTC=80)")
    result1 = step1_direction_confirmation(
        factor_scores={"T": 70, "M": 20, "C": 85, "V": 60, "O": 75, "B": 65, "I": 90},
        btc_factor_scores={"T": 80},
        params=test_params
    )
    print(f"   通过: {result1['pass']}")
    print(f"   方向得分: {result1['direction_score']:.1f}")
    print(f"   置信度: {result1['direction_confidence']:.2f}")
    print(f"   BTC对齐: {result1['btc_alignment']:.2f}")
    print(f"   最终强度: {result1['final_strength']:.1f}")

    # 测试用例2：高Beta币 + 强BTC趋势 + 反向 → 硬veto
    print("\n🚫 测试用例2：高Beta币(I=20) + 强BTC趋势(T_BTC=85) + 反向")
    result2 = step1_direction_confirmation(
        factor_scores={"T": 60, "M": 15, "C": 70, "V": 50, "O": 65, "B": 55, "I": 20},
        btc_factor_scores={"T": -85},
        params=test_params
    )
    print(f"   通过: {result2['pass']}")
    print(f"   硬veto: {result2['hard_veto']}")
    print(f"   拒绝原因: {result2['reject_reason']}")

    # 测试用例3：中等独立性 + 反向BTC
    print("\n⚠️  测试用例3：中等独立性(I=45) + 反向BTC(T_BTC=-60)")
    result3 = step1_direction_confirmation(
        factor_scores={"T": 50, "M": 10, "C": 60, "V": 45, "O": 55, "B": 50, "I": 45},
        btc_factor_scores={"T": -60},
        params=test_params
    )
    print(f"   通过: {result3['pass']}")
    print(f"   方向得分: {result3['direction_score']:.1f}")
    print(f"   置信度: {result3['direction_confidence']:.2f}")
    print(f"   BTC对齐: {result3['btc_alignment']:.2f}")
    print(f"   最终强度: {result3['final_strength']:.1f}")

    print("\n" + "="*70)
    print("✅ Step1测试完成")
    print("="*70)
