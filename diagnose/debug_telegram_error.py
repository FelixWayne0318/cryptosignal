#!/usr/bin/env python3
"""
诊断脚本：定位UNIUSDT Telegram发送失败的具体错误行

用法：
    python3 debug_telegram_error.py

功能：
    1. 模拟UNIUSDT数据调用render_trade_v72
    2. 捕获'str' object has no attribute 'get'错误
    3. 打印详细traceback和错误行号
    4. 输出所有可疑的v72_enhancements字段类型
"""

import sys
import traceback
from pathlib import Path

# 确保导入路径正确
sys.path.insert(0, str(Path(__file__).parent))

def test_telegram_rendering():
    """测试Telegram渲染函数，捕获详细错误"""

    print("=" * 80)
    print("🔍 Telegram错误诊断脚本 - v7.2.16+")
    print("=" * 80)

    try:
        from ats_core.outputs.telegram_fmt import render_trade_v72
        print("✅ 成功导入 render_trade_v72")
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        traceback.print_exc()
        return

    # 模拟UNIUSDT信号数据
    # 关键：模拟可能导致'str' object has no attribute 'get'的数据
    test_signal = {
        "symbol": "UNIUSDT",
        "side_long": True,
        "confidence": 55.0,
        "confidence_adjusted": 55.0,
        "prime_strength": 60,
        "prime_prob": 0.65,
        "edge": 0.25,
        "scores": {
            "T": 45,
            "C": 55,
            "V": 50,
            "M": 60,
            "D": 40,
            "L": 55,
        },
        "v72_enhancements": {
            # 测试1: 正常字典
            "I_meta": {
                "beta_btc": 0.75,
                "beta_eth": 0.82,
            },
            "independence_market_analysis": {
                "market_regime": -35.0,
                "alignment": "逆势",
            },
            "group_scores": {
                "TC": 50,
                "MV": 55,
            },
            "gates": {
                "details": [
                    {"gate": "gate1", "status": "pass"},
                ]
            },
        }
    }

    print("\n📊 测试数据1: 正常字典结构")
    print("-" * 80)
    try:
        result = render_trade_v72(test_signal)
        print("✅ 测试1通过: 正常字典渲染成功")
        print(f"消息长度: {len(result)} 字符")
    except Exception as e:
        print(f"❌ 测试1失败: {e}")
        print("\n完整Traceback:")
        traceback.print_exc()
        print("\n" + "=" * 80)
        return

    # 测试2: 模拟字符串值（可能的错误来源）
    test_signal_bad = {
        "symbol": "UNIUSDT",
        "side_long": True,
        "confidence": 55.0,
        "confidence_adjusted": 55.0,
        "prime_strength": 60,
        "prime_prob": 0.65,
        "edge": 0.25,
        "scores": "invalid_string",  # ⚠️ 可疑：字符串而非字典
        "v72_enhancements": {
            "I_meta": "invalid_string",  # ⚠️ 可疑
            "independence_market_analysis": "invalid_string",  # ⚠️ 可疑
            "group_scores": "invalid_string",  # ⚠️ 可疑
            "gates": "invalid_string",  # ⚠️ 可疑
        }
    }

    print("\n📊 测试数据2: 字符串值（模拟问题数据）")
    print("-" * 80)
    try:
        result = render_trade_v72(test_signal_bad)
        print("✅ 测试2通过: 字符串值渲染成功（已修复）")
        print(f"消息长度: {len(result)} 字符")
    except AttributeError as e:
        print(f"❌ 测试2失败: {e}")
        print("\n⚠️ 发现'str' object has no attribute 'get'错误！")
        print("\n完整Traceback:")
        traceback.print_exc()
        print("\n" + "=" * 80)

        # 提取错误行号
        tb = sys.exc_info()[2]
        while tb.tb_next:
            tb = tb.tb_next
        frame = tb.tb_frame
        print(f"\n🎯 错误发生在: {frame.f_code.co_filename}:{tb.tb_lineno}")
        print(f"函数名: {frame.f_code.co_name}")
        print(f"局部变量: {list(frame.f_locals.keys())}")
        return
    except Exception as e:
        print(f"❌ 测试2失败（其他错误）: {e}")
        traceback.print_exc()
        return

    print("\n" + "=" * 80)
    print("✅ 所有测试通过！v7.2.16修复有效")
    print("=" * 80)

if __name__ == "__main__":
    test_telegram_rendering()
