"""
v7.4 四步分层决策系统 - 主入口函数

Purpose:
    串联四步决策流程，从方向确认到质量控制，生成最终决策

Architecture:
    Step1: 方向确认层 → direction_score, confidence, btc_alignment
    Step2: 时机判断层 → enhanced_f, timing_quality
    Step3: 风险管理层 → entry_price, stop_loss, take_profit（阶段2实现）
    Step4: 质量控制层 → final gates检查（阶段2实现）

Phase 1 Implementation (阶段1):
    ✅ Step1 + Step2核心逻辑
    ⏸️  Step3 + Step4（阶段2实施）

Author: Claude Code (based on Expert Plan)
Version: v7.4.0 (Phase 1)
Created: 2025-11-16
"""

from typing import Dict, Any, List, Optional
from ats_core.logging import log, warn

# Phase 1: 导入Step1和Step2
from ats_core.decision.step1_direction import step1_direction_confirmation
from ats_core.decision.step2_timing import step2_timing_judgment


def run_four_step_decision_phase1(
    symbol: str,
    factor_scores: Dict[str, float],
    factor_scores_series: List[Dict[str, float]],
    btc_factor_scores: Dict[str, float],
    klines: List[Dict[str, Any]],
    s_factor_meta: Dict[str, Any],
    l_score: float,
    params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    四步系统主入口（阶段1：仅Step1+2）

    Pipeline:
        Step1: 方向确认 → 检查方向、置信度、BTC对齐、硬veto
        Step2: 时机判断 → 计算Enhanced F v2，判断时机质量
        Step3: 风险管理 → （阶段2实现）
        Step4: 质量控制 → （阶段2实现）

    Args:
        symbol: 交易对符号
        factor_scores: 当前因子得分 {"T": float, "M": float, ...}
        factor_scores_series: 历史因子得分序列（7个时间点）
        btc_factor_scores: BTC因子得分 {"T": float}
        klines: 1小时K线数据
        s_factor_meta: S因子元数据（包含theta、zigzag_points等）
        l_score: L因子流动性得分
        params: 配置参数

    Returns:
        dict: {
            "symbol": str,
            "decision": "ACCEPT" / "REJECT" / "PENDING_STEP3",
            "action": "LONG" / "SHORT" / None,
            "step1_direction": dict,  # Step1输出
            "step2_timing": dict,     # Step2输出
            "step3_risk": None,       # 阶段2实现
            "step4_quality": None,    # 阶段2实现
            "factor_scores": dict,
            "phase": str              # "phase1_step1_step2"
        }
    """
    log(f"🚀 四步系统(Phase 1) - {symbol}")

    # ---- Step1: 方向确认层 ----
    log(f"📍 Step1: 方向确认...")
    step1_result = step1_direction_confirmation(
        factor_scores=factor_scores,
        btc_factor_scores=btc_factor_scores,
        params=params
    )

    if not step1_result["pass"]:
        # Step1未通过，直接拒绝
        decision = "REJECT"
        reject_stage = "step1"
        reject_reason = step1_result["reject_reason"]

        if step1_result.get("hard_veto", False):
            warn(f"🚫 {symbol} - Step1硬veto: {reject_reason}")
        else:
            log(f"❌ {symbol} - Step1拒绝: {reject_reason}")

        return {
            "symbol": symbol,
            "decision": decision,
            "action": None,
            "reject_stage": reject_stage,
            "reject_reason": reject_reason,
            "step1_direction": step1_result,
            "step2_timing": None,
            "step3_risk": None,
            "step4_quality": None,
            "factor_scores": factor_scores,
            "phase": "phase1_step1_step2"
        }

    # Step1通过
    log(f"✅ {symbol} - Step1通过: "
        f"方向={step1_result['direction_score']:.1f}, "
        f"置信度={step1_result['direction_confidence']:.2f}, "
        f"BTC对齐={step1_result['btc_alignment']:.2f}, "
        f"最终强度={step1_result['final_strength']:.1f}")

    # ---- Step2: 时机判断层 ----
    log(f"⏰ Step2: 时机判断...")
    step2_result = step2_timing_judgment(
        factor_scores_series=factor_scores_series,
        klines=klines,
        s_factor_meta=s_factor_meta,
        l_score=l_score,
        params=params
    )

    if not step2_result["pass"]:
        # Step2未通过，拒绝
        decision = "REJECT"
        reject_stage = "step2"
        reject_reason = step2_result["reject_reason"]

        log(f"❌ {symbol} - Step2拒绝: {reject_reason}")

        return {
            "symbol": symbol,
            "decision": decision,
            "action": None,
            "reject_stage": reject_stage,
            "reject_reason": reject_reason,
            "step1_direction": step1_result,
            "step2_timing": step2_result,
            "step3_risk": None,
            "step4_quality": None,
            "factor_scores": factor_scores,
            "phase": "phase1_step1_step2"
        }

    # Step2通过
    log(f"✅ {symbol} - Step2通过: "
        f"Enhanced_F={step2_result['enhanced_f']:.1f}, "
        f"时机质量={step2_result['timing_quality']}, "
        f"最终得分={step2_result['final_timing_score']:.1f}")

    # ---- Phase 1完成：Step1+2都通过 ----
    # 确定交易方向
    action = "LONG" if step1_result["direction_score"] > 0 else "SHORT"

    log(f"🎯 {symbol} - Phase 1完成: 方向={action}, 等待Step3+4实现")

    return {
        "symbol": symbol,
        "decision": "PENDING_STEP3",  # 等待阶段2实现Step3+4
        "action": action,
        "reject_stage": None,
        "reject_reason": None,
        "step1_direction": step1_result,
        "step2_timing": step2_result,
        "step3_risk": None,  # 阶段2实现
        "step4_quality": None,  # 阶段2实现
        "factor_scores": factor_scores,
        "phase": "phase1_step1_step2",
        "phase_note": "Step1+2通过，等待Step3+4实现（阶段2）"
    }


# ============ 测试用例 ============

if __name__ == "__main__":
    """
    测试四步系统主入口（Phase 1）

    Usage:
        python3 -m ats_core.decision.four_step_system
    """
    print("="*70)
    print("v7.4 四步系统主入口测试（Phase 1: Step1+2）")
    print("="*70)

    # 模拟配置
    from ats_core.cfg import CFG
    test_params = CFG.params

    # 确保四步系统配置存在
    if "four_step_system" not in test_params:
        test_params["four_step_system"] = {
            "enabled": True,
            "step1_direction": {
                "min_final_strength": 20.0,
                "weights": {
                    "T": 0.23, "M": 0.10, "C": 0.26,
                    "V": 0.11, "O": 0.20, "B": 0.10
                },
                "I_thresholds": {
                    "high_beta": 15,
                    "moderate_beta": 30,
                    "low_beta": 50
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
            },
            "step2_timing": {
                "enhanced_f": {
                    "scale": 20.0,
                    "min_threshold": 30.0,
                    "flow_weights": {
                        "C": 0.40,
                        "O": 0.30,
                        "V": 0.20,
                        "B": 0.10
                    },
                    "lookback_hours": 6
                },
                "timing_quality": {
                    "excellent": 80,
                    "good": 60,
                    "fair": 30
                },
                "S_factor": {
                    "theta_threshold": 0.65,
                    "timing_boost": 10
                },
                "L_factor": {
                    "liquidity_min": 30,
                    "timing_penalty": 15
                }
            }
        }

    # 测试场景1：完美信号（Step1+2都通过）
    print("\n📊 测试场景1：完美信号（高独立性+强吸筹）")
    print("-" * 70)

    factor_scores_perfect = {
        "T": 70, "M": 20, "C": 85, "V": 75, "O": 80, "B": 70, "I": 85
    }

    factor_series_perfect = [
        {"C": 60+i*5, "O": 55+i*5, "V": 50+i*5, "B": 45+i*5}
        for i in range(7)
    ]

    klines_perfect = [
        {"close": 100 + i * 0.2} for i in range(7)
    ]

    result1 = run_four_step_decision_phase1(
        symbol="ETHUSDT",
        factor_scores=factor_scores_perfect,
        factor_scores_series=factor_series_perfect,
        btc_factor_scores={"T": 75},
        klines=klines_perfect,
        s_factor_meta={"theta": 0.75, "timing": 0.9, "zigzag_points": []},
        l_score=80.0,
        params=test_params
    )

    print(f"\n结果: {result1['decision']} - {result1['action']}")
    print(f"Step1: {result1['step1_direction']['pass']}")
    print(f"Step2: {result1['step2_timing']['pass']}")

    # 测试场景2：硬veto（高Beta + 强BTC + 反向）
    print("\n\n🚫 测试场景2：硬veto（高Beta + 强BTC + 反向）")
    print("-" * 70)

    factor_scores_veto = {
        "T": 60, "M": 15, "C": 70, "V": 50, "O": 65, "B": 55, "I": 20
    }

    result2 = run_four_step_decision_phase1(
        symbol="LINKUSDT",
        factor_scores=factor_scores_veto,
        factor_scores_series=factor_series_perfect,
        btc_factor_scores={"T": -85},
        klines=klines_perfect,
        s_factor_meta={"theta": 0.60, "timing": 0.7, "zigzag_points": []},
        l_score=50.0,
        params=test_params
    )

    print(f"\n结果: {result2['decision']}")
    print(f"拒绝阶段: {result2['reject_stage']}")
    print(f"拒绝原因: {result2['reject_reason']}")

    # 测试场景3：追涨被拒（Step2拒绝）
    print("\n\n❌ 测试场景3：追涨被拒（Step2时机不佳）")
    print("-" * 70)

    factor_scores_chase = {
        "T": 50, "M": 10, "C": 60, "V": 45, "O": 55, "B": 50, "I": 60
    }

    factor_series_chase = [
        {"C": 50-i*3, "O": 45-i*3, "V": 40-i*3, "B": 35-i*3}
        for i in range(7)
    ]

    klines_rally = [
        {"close": 100 * (1 + i * 0.04)} for i in range(7)
    ]

    result3 = run_four_step_decision_phase1(
        symbol="SOLUSDT",
        factor_scores=factor_scores_chase,
        factor_scores_series=factor_series_chase,
        btc_factor_scores={"T": 60},
        klines=klines_rally,
        s_factor_meta={"theta": 0.40, "timing": 0.3, "zigzag_points": []},
        l_score=30.0,
        params=test_params
    )

    print(f"\n结果: {result3['decision']}")
    print(f"拒绝阶段: {result3['reject_stage']}")
    print(f"拒绝原因: {result3['reject_reason']}")

    print("\n" + "="*70)
    print("✅ 四步系统Phase 1测试完成")
    print("="*70)
