# coding: utf-8
"""
测试 F 维度显示（使用模拟数据）
"""
import sys
sys.path.insert(0, "/home/user/cryptosignal")

from ats_core.outputs.telegram_fmt import render_signal

# 模拟一个有真实 leading_raw 的结果
mock_result = {
    "symbol": "ETHUSDT",
    "price": 3250.50,
    "side": "long",
    "probability": 0.54,
    "ttl_h": 8,

    # 七维分数
    "T": 67,
    "S": 55,
    "V": 48,
    "A": 52,
    "O": 45,
    "E": 60,
    "F": 0,  # 极低分数

    # F 的元数据（包含真实 leading_raw）
    "scores_meta": {
        "F": {
            "fund_momentum": 17.9,
            "price_momentum": 80.2,
            "leading_raw": -62.3  # 价格远远领先资金
        }
    }
}

print("="*80)
print("测试 F 维度显示（价格领先场景）")
print("="*80)
print(f"\n模拟数据：")
print(f"  F 分数: {mock_result['F']}")
print(f"  资金动量: {mock_result['scores_meta']['F']['fund_momentum']:.1f}")
print(f"  价格动量: {mock_result['scores_meta']['F']['price_momentum']:.1f}")
print(f"  领先性: {mock_result['scores_meta']['F']['leading_raw']:.1f}")
print("\n" + "="*80)
print("Telegram 消息预览：")
print("="*80)
print()
print(render_signal(mock_result, is_watch=False))
print()

# 测试资金领先场景
mock_result_good = {
    "symbol": "BTCUSDT",
    "price": 98500.00,
    "side": "long",
    "probability": 0.72,
    "ttl_h": 8,

    # 七维分数
    "T": 55,
    "S": 65,
    "V": 72,
    "A": 68,
    "O": 75,
    "E": 60,
    "F": 78,  # 高分

    # F 的元数据（资金领先）
    "scores_meta": {
        "F": {
            "fund_momentum": 75.5,
            "price_momentum": 30.2,
            "leading_raw": 45.3  # 资金领先价格
        }
    }
}

print("\n" + "="*80)
print("测试 F 维度显示（资金领先场景）")
print("="*80)
print(f"\n模拟数据：")
print(f"  F 分数: {mock_result_good['F']}")
print(f"  资金动量: {mock_result_good['scores_meta']['F']['fund_momentum']:.1f}")
print(f"  价格动量: {mock_result_good['scores_meta']['F']['price_momentum']:.1f}")
print(f"  领先性: {mock_result_good['scores_meta']['F']['leading_raw']:.1f}")
print("\n" + "="*80)
print("Telegram 消息预览：")
print("="*80)
print()
print(render_signal(mock_result_good, is_watch=False))
