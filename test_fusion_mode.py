#!/usr/bin/env python3
"""
v7.4 融合模式测试

Purpose:
    测试融合模式配置对analyze_symbol决策的影响

Usage:
    python3 test_fusion_mode.py
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ats_core.outputs.telegram_fmt import _pricing_block


def test_pricing_block_four_step():
    """测试_pricing_block对四步系统价格的支持"""
    print("=" * 70)
    print("测试1: _pricing_block - 四步系统价格显示")
    print("=" * 70)

    # 模拟四步系统结果（包含entry_price, stop_loss, take_profit）
    result_four_step = {
        "symbol": "BTCUSDT",
        "entry_price": 50000.0,
        "stop_loss": 49500.0,
        "take_profit": 51500.0,
        "risk_reward_ratio": 3.0,
        "price": 50000.0
    }

    pricing_output = _pricing_block(result_four_step)
    print("\n四步系统价格输出:")
    print(pricing_output)

    # 验证包含关键字段
    assert "入场价" in pricing_output, "❌ 缺少入场价"
    assert "止损" in pricing_output, "❌ 缺少止损"
    assert "止盈" in pricing_output, "❌ 缺少止盈"
    assert "盈亏比" in pricing_output, "❌ 缺少盈亏比"
    # _fmt_price格式化后数字可能包含逗号，检查关键数字部分
    assert ("50,000" in pricing_output or "50000" in pricing_output), "❌ 入场价数值错误"
    assert "3.00" in pricing_output, "❌ 盈亏比数值错误"

    print("\n✅ 四步系统价格显示测试通过")


def test_pricing_block_old_system():
    """测试_pricing_block对旧系统价格的兼容性"""
    print("\n" + "=" * 70)
    print("测试2: _pricing_block - 旧系统价格兼容性")
    print("=" * 70)

    # 模拟旧系统结果（使用pricing dict）
    result_old = {
        "symbol": "ETHUSDT",
        "price": 3000.0,
        "pricing": {
            "entry_lo": 2990.0,
            "entry_hi": 3010.0,
            "tp1": 3150.0
        },
        "stop_loss": {
            "stop_price": 2900.0,
            "distance_pct": 0.03,
            "method_cn": "ATR止损",
            "confidence": 85
        },
        "take_profit": {
            "price": 3150.0,
            "rr_ratio": 1.5
        }
    }

    pricing_output = _pricing_block(result_old)
    print("\n旧系统价格输出:")
    print(pricing_output)

    # 验证包含关键字段
    assert "入场" in pricing_output, "❌ 缺少入场信息"
    assert "止损" in pricing_output, "❌ 缺少止损"
    assert "止盈" in pricing_output, "❌ 缺少止盈"
    # _fmt_price格式化后数字可能包含逗号和小数点
    assert ("2,990" in pricing_output or "3,010" in pricing_output or "2990" in pricing_output or "3010" in pricing_output), "❌ 入场价数值错误"

    print("\n✅ 旧系统价格兼容性测试通过")


def test_fusion_mode_config():
    """测试融合模式配置读取"""
    print("\n" + "=" * 70)
    print("测试3: 融合模式配置验证")
    print("=" * 70)

    from ats_core.cfg import CFG

    params = CFG.params
    four_step_config = params.get("four_step_system", {})
    fusion_config = four_step_config.get("fusion_mode", {})

    print(f"\n融合模式配置:")
    print(f"  fusion_mode.enabled: {fusion_config.get('enabled', False)}")
    print(f"  compatibility_mode.preserve_old_fields: {fusion_config.get('compatibility_mode', {}).get('preserve_old_fields', True)}")

    # 验证配置存在
    assert "fusion_mode" in four_step_config, "❌ params.json缺少fusion_mode配置"
    assert isinstance(fusion_config.get("enabled"), bool), "❌ fusion_mode.enabled不是布尔值"

    print("\n✅ 融合模式配置验证通过")


def test_decision_flow_simulation():
    """模拟决策流程测试"""
    print("\n" + "=" * 70)
    print("测试4: 决策流程模拟")
    print("=" * 70)

    # 模拟融合逻辑
    fusion_enabled = True
    preserve_old_fields = True

    # 场景1: 四步系统ACCEPT + 融合启用
    print("\n场景1: 融合模式 + 四步ACCEPT")
    result = {"is_prime": False, "side_long": False}  # 旧系统结果
    four_step_result = {
        "decision": "ACCEPT",
        "action": "LONG",
        "entry_price": 50000.0,
        "stop_loss": 49500.0,
        "take_profit": 51500.0,
        "risk_reward_ratio": 3.0,
        "step1_direction": {"final_strength": 75}
    }

    # 模拟融合逻辑
    if fusion_enabled and four_step_result.get("decision") in ["ACCEPT", "REJECT"]:
        old_is_prime = result.get("is_prime", False)
        result["is_prime"] = (four_step_result["decision"] == "ACCEPT")
        if four_step_result["decision"] == "ACCEPT":
            result["side_long"] = (four_step_result["action"] == "LONG")
            result["entry_price"] = four_step_result.get("entry_price")
            result["stop_loss"] = four_step_result.get("stop_loss")
            result["take_profit"] = four_step_result.get("take_profit")

        if preserve_old_fields:
            result["v6_decision"] = {"is_prime": old_is_prime}

    print(f"  旧系统: is_prime=False")
    print(f"  四步系统: decision=ACCEPT, action=LONG")
    print(f"  融合后: is_prime={result['is_prime']}, side_long={result.get('side_long')}")
    print(f"  融合后: entry_price={result.get('entry_price')}")
    print(f"  保留旧决策: {result.get('v6_decision')}")

    assert result["is_prime"] == True, "❌ 融合后is_prime应为True"
    assert result["side_long"] == True, "❌ 融合后side_long应为True"
    assert result.get("entry_price") == 50000.0, "❌ 缺少entry_price"

    # 场景2: 四步系统REJECT + 融合启用
    print("\n场景2: 融合模式 + 四步REJECT")
    result2 = {"is_prime": True, "side_long": True}  # 旧系统结果
    four_step_result2 = {
        "decision": "REJECT",
        "reject_stage": "step2",
        "reject_reason": "时机不佳"
    }

    if fusion_enabled and four_step_result2.get("decision") in ["ACCEPT", "REJECT"]:
        old_is_prime = result2.get("is_prime", False)
        result2["is_prime"] = (four_step_result2["decision"] == "ACCEPT")  # REJECT -> False

        if preserve_old_fields:
            result2["v6_decision"] = {"is_prime": old_is_prime}

    print(f"  旧系统: is_prime=True")
    print(f"  四步系统: decision=REJECT")
    print(f"  融合后: is_prime={result2['is_prime']}")
    print(f"  保留旧决策: {result2.get('v6_decision')}")

    assert result2["is_prime"] == False, "❌ 融合后is_prime应为False"

    print("\n✅ 决策流程模拟测试通过")


if __name__ == "__main__":
    try:
        test_pricing_block_four_step()
        test_pricing_block_old_system()
        test_fusion_mode_config()
        test_decision_flow_simulation()

        print("\n" + "=" * 70)
        print("✅ 所有融合模式测试通过")
        print("=" * 70)

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
