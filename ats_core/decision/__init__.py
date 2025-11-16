"""
v7.4 四步分层决策系统

Purpose:
    实现革命性的四步决策架构：不仅给方向，更给具体价格

Modules:
    - step1_direction: 方向确认层（A层因子 + I因子 + BTC对齐 + 硬veto）
    - step2_timing: 时机判断层（Enhanced F v2修正版）
    - step3_risk: 风险管理层（Entry/SL/TP价格计算）
    - step4_quality: 质量控制层（四道闸门验证）
    - four_step_system: 主入口函数

Author: Claude Code (based on Expert Implementation Plan)
Version: v7.4.0
Created: 2025-11-16
"""

__version__ = "7.4.0"
__all__ = [
    "step1_direction_confirmation",
    "step2_timing_judgment",
    "step3_risk_management",
    "step4_quality_control",
    "run_four_step_decision"
]
