#!/usr/bin/env python3
# coding: utf-8
"""
debug_scan: 调试版扫描工具 - 显示详细错误信息
"""
import os
import sys

os.environ.setdefault("ATS_FMT_SHOW_ZERO", "1")
os.environ.setdefault("ATS_FMT_FULL", "1")

from ats_core.pipeline.analyze_symbol import analyze_symbol

# 测试单个币种
symbol = "BTCUSDT"

print(f"正在分析 {symbol}...")
print("="*60)

try:
    result = analyze_symbol(symbol)
    print(f"✅ 分析成功！")
    print(f"   Symbol: {result.get('symbol', 'N/A')}")
    print(f"   Side: {result.get('side', 'N/A')}")
    print(f"   Probability: {result.get('probability', 0):.2%}")
    print(f"   Scores: {result.get('scores', {})}")

    pub = result.get("publish") or {}
    print(f"   Is Prime: {pub.get('prime', False)}")
    print(f"   Is Watch: {pub.get('watch', False)}")

except Exception as e:
    print(f"❌ 分析失败！")
    print(f"   错误类型: {type(e).__name__}")
    print(f"   错误信息: {e}")

    # 打印完整的错误堆栈
    import traceback
    print("\n完整错误堆栈：")
    traceback.print_exc()
