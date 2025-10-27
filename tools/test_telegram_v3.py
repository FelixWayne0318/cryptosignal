#!/usr/bin/env python3
# coding: utf-8
"""
测试v3系统Telegram发送功能
"""

import os
import sys

# 检查Telegram配置
def check_telegram_config():
    """检查Telegram配置是否完整"""
    token = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("ATS_TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("ATS_TELEGRAM_CHAT_ID")

    print("=" * 60)
    print("Telegram配置检查")
    print("=" * 60)

    if token:
        print(f"✅ TELEGRAM_BOT_TOKEN: {token[:10]}...{token[-4:]}")
    else:
        print("❌ TELEGRAM_BOT_TOKEN: 未设置")

    if chat_id:
        print(f"✅ TELEGRAM_CHAT_ID: {chat_id}")
    else:
        print("❌ TELEGRAM_CHAT_ID: 未设置")

    print("=" * 60)

    return bool(token and chat_id)


def send_test_signal():
    """发送测试信号"""
    from ats_core.outputs.telegram_fmt import render_trade
    from ats_core.outputs.publisher import telegram_send

    # 构造测试信号
    test_result = {
        "symbol": "BTCUSDT",
        "price": 68500.00,
        "side": "long",
        "probability": 0.72,
        "T": 65,
        "M": 55,
        "S": 50,
        "V": 60,
        "C": 70,
        "O": 45,
        "E": 40,
        "F": 15,
        "scores_meta": {
            "T": {"Tm": 1},
            "M": {"slope_now": 0.5},
            "C": {"cvd6": 0.023, "is_consistent": True},
            "O": {"oi24h_pct": 8.5},
            "E": {"chop": 35}
        },
        "publish": {
            "prime": True,
            "side": "long",
            "ttl_h": 8
        },
        "pricing": {
            "entry_lo": 68000,
            "entry_hi": 69000,
            "sl": 66500,
            "tp1": 71000,
            "tp2": 73500
        },
        "ttl_h": 8,
        "note": "v3系统测试信号 - 10+1维因子体系"
    }

    # 格式化消息
    html = render_trade(test_result)

    print("\n" + "=" * 60)
    print("准备发送的消息:")
    print("=" * 60)
    print(html)
    print("=" * 60)

    # 发送到Telegram
    try:
        telegram_send(html)
        print("\n✅ 测试信号已成功发送到Telegram!")
        return True
    except Exception as e:
        print(f"\n❌ 发送失败: {e}")
        return False


if __name__ == "__main__":
    print("\n🚀 v3系统 - Telegram发送功能测试\n")

    # 检查配置
    if not check_telegram_config():
        print("\n⚠️  请先配置Telegram Bot Token和Chat ID")
        print("\n配置方法:")
        print("  1. 创建Telegram Bot (找 @BotFather)")
        print("  2. 获取Bot Token")
        print("  3. 将Bot添加到群组，获取Chat ID")
        print("  4. 设置环境变量:")
        print("     export TELEGRAM_BOT_TOKEN=\"你的Token\"")
        print("     export TELEGRAM_CHAT_ID=\"你的Chat ID\"")
        print("\n或运行配置脚本:")
        print("  bash setup_telegram.sh")
        sys.exit(1)

    # 发送测试信号
    print("\n开始发送测试信号...\n")
    success = send_test_signal()

    if success:
        print("\n🎉 v3系统Telegram发送功能正常!")
        print("\n下一步:")
        print("  1. 运行批量扫描: python3 -m ats_core.pipeline.batch_scan")
        print("  2. 或使用v3分析: from ats_core.pipeline.analyze_symbol_v3 import analyze_symbol_v3")
    else:
        print("\n请检查Telegram配置是否正确")
        sys.exit(1)
