#!/usr/bin/env python3
"""
v7.4 四步系统集成测试脚本

Purpose:
    测试四步系统在analyze_symbol中的集成效果（Dual Run模式）

Usage:
    python3 test_four_step_integration.py
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_four_step_integration():
    """测试四步系统集成"""
    print("=" * 70)
    print("v7.4 四步系统集成测试（Dual Run模式）")
    print("=" * 70)

    # 1. 导入并修改配置（临时启用four_step_system）
    from ats_core.cfg import CFG
    print("\n📝 步骤1: 临时启用四步系统配置")

    original_enabled = CFG.params.get("four_step_system", {}).get("enabled", False)
    print(f"原始enabled状态: {original_enabled}")

    # 临时启用
    if "four_step_system" not in CFG.params:
        CFG.params["four_step_system"] = {}
    CFG.params["four_step_system"]["enabled"] = True
    print(f"临时修改enabled为: True")

    # 2. 选择测试交易对
    test_symbols = ["ETHUSDT", "BTCUSDT"]

    for symbol in test_symbols:
        print("\n" + "="*70)
        print(f"🔬 测试交易对: {symbol}")
        print("="*70)

        try:
            # 3. 调用analyze_symbol
            from ats_core.pipeline.analyze_symbol import analyze_symbol

            print(f"\n📊 执行 analyze_symbol({symbol})...")
            result = analyze_symbol(symbol)

            # 4. 检查结果
            if not result.get("success", False):
                print(f"⚠️  {symbol} - analyze_symbol返回失败")
                continue

            # 5. 检查四步系统结果
            four_step_result = result.get("four_step_decision")

            if four_step_result is None:
                print(f"⚠️  {symbol} - 四步系统未执行（可能数据不足）")
                continue

            # 6. 输出对比结果
            print(f"\n{'='*70}")
            print(f"✅ {symbol} - Dual Run对比结果:")
            print(f"{'='*70}")

            # 旧系统结果
            old_signal = "LONG" if result.get("side_long", False) else "SHORT"
            old_prime = result.get("is_prime", False)
            old_strength = result.get("prime_strength", 0)

            print(f"\n【旧系统 v6.6】")
            print(f"  方向: {old_signal}")
            print(f"  是否Prime: {old_prime}")
            print(f"  Prime强度: {old_strength:.1f}")
            print(f"  加权分数: {result.get('weighted_score', 0):+.2f}")
            print(f"  置信度: {result.get('confidence', 0):.1f}")

            # 新系统结果
            decision = four_step_result.get("decision", "UNKNOWN")
            action = four_step_result.get("action", "N/A")

            print(f"\n【新系统 v7.4】")
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
            elif decision == "ERROR":
                error = four_step_result.get("error", "Unknown error")
                print(f"  错误: {error}")

            # 四步详情
            if decision in ["ACCEPT", "REJECT"]:
                print(f"\n【四步详情】")

                step1 = four_step_result.get("step1_direction", {})
                if step1:
                    print(f"  Step1 - 方向确认: {'✅ 通过' if step1.get('pass') else '❌ 拒绝'}")
                    print(f"    方向得分: {step1.get('direction_score', 0):.1f}")
                    print(f"    置信度: {step1.get('direction_confidence', 0):.2f}")
                    print(f"    BTC对齐: {step1.get('btc_alignment', 0):.2f}")
                    print(f"    最终强度: {step1.get('final_strength', 0):.1f}")
                    if step1.get('hard_veto'):
                        print(f"    ⚠️  硬veto触发")

                step2 = four_step_result.get("step2_timing", {})
                if step2:
                    print(f"  Step2 - 时机判断: {'✅ 通过' if step2.get('pass') else '❌ 拒绝'}")
                    print(f"    Enhanced F: {step2.get('enhanced_f', 0):.1f}")
                    print(f"    时机质量: {step2.get('timing_quality', 'N/A')}")
                    print(f"    最终得分: {step2.get('final_timing_score', 0):.1f}")

                step3 = four_step_result.get("step3_risk")
                if step3:
                    print(f"  Step3 - 风险管理: {'✅ 通过' if step3.get('pass') else '❌ 拒绝'}")
                    if not step3.get('pass'):
                        print(f"    拒绝原因: {step3.get('reject_reason', 'N/A')}")

                step4 = four_step_result.get("step4_quality")
                if step4:
                    print(f"  Step4 - 质量控制: {'✅ 通过' if step4.get('all_gates_pass') else '❌ 拒绝'}")
                    if not step4.get('all_gates_pass'):
                        print(f"    拒绝原因: {step4.get('reject_reason', 'N/A')}")

        except Exception as e:
            print(f"\n❌ {symbol} - 测试异常: {e}")
            import traceback
            traceback.print_exc()

    # 7. 恢复原始配置
    print("\n" + "="*70)
    print("📝 恢复原始配置")
    CFG.params["four_step_system"]["enabled"] = original_enabled
    print(f"enabled恢复为: {original_enabled}")

    print("\n" + "="*70)
    print("✅ 四步系统集成测试完成")
    print("="*70)


if __name__ == "__main__":
    test_four_step_integration()
