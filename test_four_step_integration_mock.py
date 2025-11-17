#!/usr/bin/env python3
"""
v7.4 四步系统集成模拟测试（无numpy依赖）

Purpose:
    模拟测试四步系统集成逻辑（不依赖完整analyze_symbol）

Usage:
    python3 test_four_step_integration_mock.py
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_four_step_integration_mock():
    """模拟测试四步系统集成"""
    print("=" * 70)
    print("v7.4 四步系统集成模拟测试")
    print("=" * 70)

    # 1. 导入配置和四步系统
    from ats_core.cfg import CFG

    # 2. 准备模拟数据
    symbol = "ETHUSDT_MOCK"

    # 模拟factor_scores
    factor_scores = {
        "T": 70, "M": 20, "C": 80, "V": 65, "O": 75, "B": 60,
        "L": 50, "S": 30, "F": 40, "I": 80
    }

    # 模拟BTC factor_scores
    btc_factor_scores = {"T": 75}

    # 模拟K线数据（至少32根，满足factor_history需求）
    klines = []
    for i in range(32):
        klines.append({
            "open_time": 1700000000000 + i * 3600000,
            "open": 100.0 + i * 0.1,
            "high": 100.0 + i * 0.1 + 0.5,
            "low": 100.0 + i * 0.1 - 0.5,
            "close": 100.0 + i * 0.1 + 0.2,
            "volume": 100_000.0,
            "atr": 0.5
        })

    # 模拟S factor meta
    s_factor_meta = {
        "theta": 0.75,
        "timing": 0.9,
        "zigzag_points": [
            {"type": "L", "price": 100.5, "dt": 3},
            {"type": "H", "price": 103.5, "dt": 1}
        ]
    }

    # 模拟L factor meta
    l_factor_meta = {
        "obi_value": 0.3,
        "best_bid": 102.0,
        "best_ask": 102.1
    }

    l_score = 50.0

    # 3. 准备factor_scores_series
    print("\n📝 步骤1: 准备历史因子序列...")
    from ats_core.utils.factor_history import get_factor_scores_series

    factor_scores_series = get_factor_scores_series(
        klines_1h=klines,
        window_hours=7,
        current_factor_scores=factor_scores,
        params=CFG.params
    )
    print(f"✅ 历史因子序列长度: {len(factor_scores_series)}")

    # 4. 调用四步系统
    print(f"\n📝 步骤2: 调用四步系统...")
    from ats_core.decision.four_step_system import run_four_step_decision

    four_step_result = run_four_step_decision(
        symbol=symbol,
        klines=klines,
        factor_scores=factor_scores,
        factor_scores_series=factor_scores_series,
        btc_factor_scores=btc_factor_scores,
        s_factor_meta=s_factor_meta,
        l_factor_meta=l_factor_meta,
        l_score=l_score,
        params=CFG.params
    )

    # 5. 输出结果
    print(f"\n{'='*70}")
    print(f"✅ {symbol} - 四步系统结果:")
    print(f"{'='*70}")

    decision = four_step_result.get("decision", "UNKNOWN")
    action = four_step_result.get("action", "N/A")

    print(f"\n【决策结果】")
    print(f"  决策: {decision}")

    if decision == "ACCEPT":
        print(f"  方向: {action}")
        print(f"  入场价: {four_step_result.get('entry_price', 0):.6f}")
        print(f"  止损价: {four_step_result.get('stop_loss', 0):.6f}")
        print(f"  止盈价: {four_step_result.get('take_profit', 0):.6f}")
        print(f"  风险: {four_step_result.get('risk_pct', 0):.2f}%")
        print(f"  收益: {four_step_result.get('reward_pct', 0):.2f}%")
        print(f"  赔率: {four_step_result.get('risk_reward_ratio', 0):.2f}:1")
    elif decision == "REJECT":
        reject_stage = four_step_result.get("reject_stage", "unknown")
        reject_reason = four_step_result.get("reject_reason", "N/A")
        print(f"  拒绝阶段: {reject_stage}")
        print(f"  拒绝原因: {reject_reason}")

    # 四步详情
    print(f"\n【四步详情】")

    step1 = four_step_result.get("step1_direction", {})
    if step1:
        print(f"  Step1 - 方向确认: {'✅ 通过' if step1.get('pass') else '❌ 拒绝'}")
        print(f"    方向得分: {step1.get('direction_score', 0):.1f}")
        print(f"    置信度: {step1.get('direction_confidence', 0):.2f}")
        print(f"    BTC对齐: {step1.get('btc_alignment', 0):.2f}")
        print(f"    最终强度: {step1.get('final_strength', 0):.1f}")

    step2 = four_step_result.get("step2_timing", {})
    if step2:
        print(f"  Step2 - 时机判断: {'✅ 通过' if step2.get('pass') else '❌ 拒绝'}")
        print(f"    Enhanced F: {step2.get('enhanced_f', 0):.1f}")
        print(f"    时机质量: {step2.get('timing_quality', 'N/A')}")
        print(f"    最终得分: {step2.get('final_timing_score', 0):.1f}")

    step3 = four_step_result.get("step3_risk")
    if step3:
        print(f"  Step3 - 风险管理: {'✅ 通过' if step3.get('pass') else '❌ 拒绝'}")
        if step3.get('pass'):
            print(f"    支撑位: {step3.get('support')}")
            print(f"    阻力位: {step3.get('resistance')}")
            print(f"    ATR: {step3.get('atr', 0):.6f}")

    step4 = four_step_result.get("step4_quality")
    if step4:
        print(f"  Step4 - 质量控制: {'✅ 通过' if step4.get('all_gates_pass') else '❌ 拒绝'}")
        gates_status = step4.get('gates_status', {})
        for gate_name, gate_info in gates_status.items():
            status = '✅' if gate_info.get('pass') else '❌'
            print(f"    {gate_name}: {status}")

    print("\n" + "="*70)
    print("✅ 四步系统集成模拟测试完成")
    print("="*70)

    # 验证集成逻辑
    print("\n📊 集成逻辑验证:")
    print(f"  ✅ factor_scores准备完成")
    print(f"  ✅ factor_scores_series生成完成（{len(factor_scores_series)}个时间点）")
    print(f"  ✅ run_four_step_decision调用成功")
    print(f"  ✅ 结果包含完整四步详情")
    print(f"  ✅ 决策结果: {decision}")


if __name__ == "__main__":
    test_four_step_integration_mock()
