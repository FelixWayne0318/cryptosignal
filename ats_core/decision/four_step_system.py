"""
v7.4 四步分层决策系统 - 主入口函数

Purpose:
    串联四步决策流程，从方向确认到质量控制，生成最终决策

Architecture:
    Step1: 方向确认层 → direction_score, confidence, btc_alignment
    Step2: 时机判断层 → enhanced_f, timing_quality
    Step3: 风险管理层 → entry_price, stop_loss, take_profit
    Step4: 质量控制层 → final gates检查

Phase 2 Implementation (阶段2):
    ✅ Step1 + Step2核心逻辑（阶段1完成）
    ✅ Step3 + Step4完整实现（阶段2完成）

Author: Claude Code (based on Expert Plan)
Version: v7.4.4 (Phase 2 + TrendStage)
Created: 2025-11-16
Updated: 2025-11-20
"""

from typing import Dict, Any, List, Optional
from ats_core.logging import log, warn

# 导入所有四步
from ats_core.decision.step1_direction import step1_direction_confirmation
from ats_core.decision.step2_timing import step2_timing_judgment
from ats_core.decision.step3_risk import step3_risk_management
from ats_core.decision.step4_quality import step4_quality_control


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
        params=params,
        symbol=symbol  # v7.4.4: 传递symbol用于BTC特殊处理
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
    # v7.4.3: L因子不再用于Step2时机惩罚，仅用于Step3止损宽度调整
    log(f"⏰ Step2: 时机判断...")
    step2_result = step2_timing_judgment(
        factor_scores_series=factor_scores_series,
        klines=klines,
        s_factor_meta=s_factor_meta,
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


def run_four_step_decision(
    symbol: str,
    klines: List[Dict[str, Any]],
    factor_scores: Dict[str, float],
    factor_scores_series: List[Dict[str, float]],
    btc_factor_scores: Dict[str, float],
    s_factor_meta: Dict[str, Any],
    l_factor_meta: Optional[Dict[str, Any]],
    l_score: float,
    params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    四步系统完整主入口（阶段2：Step1+2+3+4）

    Pipeline:
        Step1: 方向确认 → pass → 继续
                        → fail → REJECT
        Step2: 时机判断 → pass → 继续
                        → fail → REJECT
        Step3: 风险管理 → pass → 继续（生成Entry/SL/TP）
                        → fail → REJECT
        Step4: 质量控制 → pass → ACCEPT
                        → fail → REJECT

    Args:
        symbol: 交易对符号
        klines: 1小时K线数据（至少24根）
        factor_scores: 当前因子得分
        factor_scores_series: 历史因子得分序列（7个时间点）
        btc_factor_scores: BTC因子得分
        s_factor_meta: S因子元数据（包含zigzag_points）
        l_factor_meta: L因子元数据（包含obi_value等）
        l_score: L因子流动性得分
        params: 配置参数

    Returns:
        dict: {
            "symbol": str,
            "decision": "ACCEPT" / "REJECT",
            "action": "LONG" / "SHORT" / None,
            "reject_stage": str | None,     # "step1" / "step2" / "step3" / "step4"
            "reject_reason": str | None,

            # 四步结果
            "step1_direction": dict,
            "step2_timing": dict,
            "step3_risk": dict | None,
            "step4_quality": dict | None,

            # 交易建议（仅ACCEPT时有效）
            "entry_price": float | None,
            "stop_loss": float | None,
            "take_profit": float | None,
            "risk_pct": float | None,
            "reward_pct": float | None,
            "risk_reward_ratio": float | None,

            "factor_scores": dict,
            "phase": str                    # "phase2_complete"
        }
    """
    log(f"🚀 四步系统(Phase 2 Complete) - {symbol}")

    # ---- Step1: 方向确认层 ----
    log(f"📍 Step1: 方向确认...")
    step1_result = step1_direction_confirmation(
        factor_scores=factor_scores,
        btc_factor_scores=btc_factor_scores,
        params=params,
        symbol=symbol  # v7.4.4: 传递symbol用于BTC特殊处理
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
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "risk_pct": None,
            "reward_pct": None,
            "risk_reward_ratio": None,
            "factor_scores": factor_scores,
            "phase": "phase2_complete"
        }

    # Step1通过
    log(f"✅ {symbol} - Step1通过: "
        f"方向={step1_result['direction_score']:.1f}, "
        f"置信度={step1_result['direction_confidence']:.2f}, "
        f"BTC对齐={step1_result['btc_alignment']:.2f}, "
        f"最终强度={step1_result['final_strength']:.1f}")

    # ---- Step2: 时机判断层 ----
    # v7.4.3: L因子不再用于Step2时机惩罚，仅用于Step3止损宽度调整
    log(f"⏰ Step2: 时机判断...")
    step2_result = step2_timing_judgment(
        factor_scores_series=factor_scores_series,
        klines=klines,
        s_factor_meta=s_factor_meta,
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
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "risk_pct": None,
            "reward_pct": None,
            "risk_reward_ratio": None,
            "factor_scores": factor_scores,
            "phase": "phase2_complete"
        }

    # Step2通过
    # v7.4.4: 添加TrendStage相关信息和direction_sign观测
    enhanced_f_final = step2_result.get('enhanced_f_final', step2_result.get('final_timing_score', 0))
    trend_stage = step2_result.get('trend_stage', 'unknown')

    # 提取direction_sign用于观测
    step2_metadata = step2_result.get('metadata', {})
    step2_direction_sign = step2_metadata.get('direction_sign', 0)
    step1_direction_sign = 1 if step1_result['direction_score'] > 0 else -1

    # 观测记录：direction_sign来源对齐问题（暂不改判定，只观测）
    direction_sign_mismatch = step2_direction_sign != step1_direction_sign
    if direction_sign_mismatch and step2_direction_sign != 0:
        warn(f"⚠️  {symbol} - direction_sign不一致: Step1={step1_direction_sign}, Step2(T)={step2_direction_sign}")

    log(f"✅ {symbol} - Step2通过: "
        f"Enhanced_F={step2_result['enhanced_f']:.1f}, "
        f"final={enhanced_f_final:.1f}, "
        f"stage={trend_stage}, "
        f"时机质量={step2_result['timing_quality']}")

    # ---- Step3: 风险管理层 ----
    log(f"💰 Step3: 风险管理...")
    step3_result = step3_risk_management(
        symbol=symbol,
        klines=klines,
        s_factor_meta=s_factor_meta,
        l_factor_meta=l_factor_meta,
        l_score=l_score,
        direction_score=step1_result["direction_score"],
        enhanced_f=step2_result["enhanced_f"],
        params=params
    )

    if not step3_result["pass"]:
        # Step3未通过，拒绝
        decision = "REJECT"
        reject_stage = "step3"
        reject_reason = step3_result["reject_reason"]

        log(f"❌ {symbol} - Step3拒绝: {reject_reason}")

        return {
            "symbol": symbol,
            "decision": decision,
            "action": None,
            "reject_stage": reject_stage,
            "reject_reason": reject_reason,
            "step1_direction": step1_result,
            "step2_timing": step2_result,
            "step3_risk": step3_result,
            "step4_quality": None,
            "entry_price": step3_result["entry_price"],
            "stop_loss": step3_result["stop_loss"],
            "take_profit": step3_result["take_profit"],
            "risk_pct": step3_result["risk_pct"],
            "reward_pct": step3_result["reward_pct"],
            "risk_reward_ratio": step3_result["risk_reward_ratio"],
            "factor_scores": factor_scores,
            "phase": "phase2_complete"
        }

    # Step3通过
    log(f"✅ {symbol} - Step3通过: "
        f"Entry={step3_result['entry_price']:.6f}, "
        f"SL={step3_result['stop_loss']:.6f}, "
        f"TP={step3_result['take_profit']:.6f}, "
        f"RR={step3_result['risk_reward_ratio']:.2f}")

    # ---- Step4: 质量控制层 ----
    log(f"🔍 Step4: 质量控制...")
    step4_result = step4_quality_control(
        symbol=symbol,
        klines=klines,
        factor_scores=factor_scores,
        prime_strength=step1_result["final_strength"],
        step1_result=step1_result,
        step2_result=step2_result,
        step3_result=step3_result,
        params=params
    )

    if not step4_result["all_gates_pass"]:
        # Step4未通过，拒绝
        decision = "REJECT"
        reject_stage = "step4"
        reject_reason = step4_result["reject_reason"]

        log(f"❌ {symbol} - Step4拒绝: {reject_reason}")

        return {
            "symbol": symbol,
            "decision": decision,
            "action": None,
            "reject_stage": reject_stage,
            "reject_reason": reject_reason,
            "step1_direction": step1_result,
            "step2_timing": step2_result,
            "step3_risk": step3_result,
            "step4_quality": step4_result,
            "entry_price": step3_result["entry_price"],
            "stop_loss": step3_result["stop_loss"],
            "take_profit": step3_result["take_profit"],
            "risk_pct": step3_result["risk_pct"],
            "reward_pct": step3_result["reward_pct"],
            "risk_reward_ratio": step3_result["risk_reward_ratio"],
            "factor_scores": factor_scores,
            "phase": "phase2_complete"
        }

    # ---- 全部通过：ACCEPT ----
    action = "LONG" if step1_result["direction_score"] > 0 else "SHORT"

    log(f"🎉 {symbol} - 四步系统全部通过！")
    log(f"   方向: {action}")
    log(f"   入场: {step3_result['entry_price']:.6f}")
    log(f"   止损: {step3_result['stop_loss']:.6f}")
    log(f"   止盈: {step3_result['take_profit']:.6f}")
    log(f"   赔率: {step3_result['risk_reward_ratio']:.2f}:1")

    return {
        "symbol": symbol,
        "decision": "ACCEPT",
        "action": action,
        "reject_stage": None,
        "reject_reason": None,
        "step1_direction": step1_result,
        "step2_timing": step2_result,
        "step3_risk": step3_result,
        "step4_quality": step4_result,
        "entry_price": step3_result["entry_price"],
        "stop_loss": step3_result["stop_loss"],
        "take_profit": step3_result["take_profit"],
        "risk_pct": step3_result["risk_pct"],
        "reward_pct": step3_result["reward_pct"],
        "risk_reward_ratio": step3_result["risk_reward_ratio"],
        "factor_scores": factor_scores,
        "phase": "phase2_complete"
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
                    "T": 0.23,
                    "M": 0.10,
                    "C": 0.26,
                    "V": 0.11,
                    "O": 0.20,
                    "B": 0.10
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

    # ======== Phase 2 Complete测试 ========

    print("\n\n" + "="*70)
    print("v7.4 四步系统完整测试（Phase 2: Step1+2+3+4）")
    print("="*70)

    # 补充L因子元数据（用于Step3）
    l_meta_complete = {
        "obi_value": 0.3,
        "best_bid": 102.0,
        "best_ask": 102.1
    }

    # 测试场景4：完美信号（四步全通过）
    print("\n📊 测试场景4：完美信号（四步全通过）")
    print("-" * 70)

    result4 = run_four_step_decision(
        symbol="ETHUSDT",
        klines=klines_perfect,
        factor_scores=factor_scores_perfect,
        factor_scores_series=factor_series_perfect,
        btc_factor_scores={"T": 75},
        s_factor_meta={"theta": 0.75, "timing": 0.9, "zigzag_points": [
            {"type": "L", "price": 100.5, "dt": 3},
            {"type": "H", "price": 103.5, "dt": 1}
        ]},
        l_factor_meta=l_meta_complete,
        l_score=80.0,
        params=test_params
    )

    print(f"\n结果: {result4['decision']} - {result4.get('action', 'N/A')}")
    if result4['decision'] == "ACCEPT":
        print(f"✅ 入场: {result4['entry_price']:.6f}")
        print(f"✅ 止损: {result4['stop_loss']:.6f}")
        print(f"✅ 止盈: {result4['take_profit']:.6f}")
        print(f"✅ 赔率: {result4['risk_reward_ratio']:.2f}:1")
    else:
        print(f"拒绝阶段: {result4['reject_stage']}")
        print(f"拒绝原因: {result4['reject_reason']}")

    # 测试场景5：Step3被拒（赔率不足）
    print("\n\n📊 测试场景5：Step3被拒（高波动导致赔率不足）")
    print("-" * 70)

    # 高波动K线
    klines_high_vol = []
    for i in range(24):
        klines_high_vol.append({
            "open_time": 1700000000000 + i * 3600000,
            "open": 100.0,
            "high": 100.0 + 5.0,
            "low": 100.0 - 5.0,
            "close": 100.0,
            "volume": 100_000.0,
            "atr": 8.0  # 大ATR
        })

    result5 = run_four_step_decision(
        symbol="VOLATILUSDT",
        klines=klines_high_vol,
        factor_scores=factor_scores_perfect,
        factor_scores_series=factor_series_perfect,
        btc_factor_scores={"T": 60},
        s_factor_meta={"theta": 0.60, "timing": 0.7, "zigzag_points": [
            {"type": "L", "price": 95.0, "dt": 3},
            {"type": "H", "price": 105.0, "dt": 1}
        ]},
        l_factor_meta=l_meta_complete,
        l_score=40.0,
        params=test_params
    )

    print(f"\n结果: {result5['decision']}")
    print(f"拒绝阶段: {result5['reject_stage']}")
    print(f"拒绝原因: {result5['reject_reason']}")

    # 测试场景6：Step4被拒（成交量不足）
    print("\n\n📊 测试场景6：Step4被拒（成交量不足）")
    print("-" * 70)

    # 低成交量K线
    klines_low_vol = []
    for i in range(24):
        klines_low_vol.append({
            "open_time": 1700000000000 + i * 3600000,
            "open": 100.0 + i * 0.1,
            "high": 100.0 + i * 0.1 + 0.5,
            "low": 100.0 + i * 0.1 - 0.5,
            "close": 100.0 + i * 0.1 + 0.2,
            "volume": 10_000.0,  # 24h = 240K < 1M
            "atr": 0.5
        })

    result6 = run_four_step_decision(
        symbol="LOWVOLUSDT",
        klines=klines_low_vol,
        factor_scores=factor_scores_perfect,
        factor_scores_series=factor_series_perfect,
        btc_factor_scores={"T": 70},
        s_factor_meta={"theta": 0.70, "timing": 0.8, "zigzag_points": [
            {"type": "L", "price": 100.0, "dt": 2},
            {"type": "H", "price": 103.0, "dt": 1}
        ]},
        l_factor_meta=l_meta_complete,
        l_score=60.0,
        params=test_params
    )

    print(f"\n结果: {result6['decision']}")
    print(f"拒绝阶段: {result6['reject_stage']}")
    print(f"拒绝原因: {result6['reject_reason']}")

    print("\n" + "="*70)
    print("✅ 四步系统Phase 2完整测试完成")
    print("="*70)
