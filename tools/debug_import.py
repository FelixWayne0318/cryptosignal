#!/usr/bin/env python3
"""检查analyze_symbol导入路径"""
import sys

# 检查导入路径
print("Python sys.path:")
for p in sys.path:
    print(f"  {p}")

print("\n导入 analyze_symbol...")
from ats_core.pipeline.analyze_symbol import analyze_symbol

print(f"\nanalyze_symbol 函数位置:")
print(f"  模块: {analyze_symbol.__module__}")
print(f"  文件: {analyze_symbol.__code__.co_filename}")
print(f"  行号: {analyze_symbol.__code__.co_firstlineno}")

# 检查函数签名
import inspect
sig = inspect.signature(analyze_symbol)
print(f"\n函数签名: {sig}")

# 查看源代码前10行
source = inspect.getsource(analyze_symbol)
lines = source.split('\n')[:15]
print(f"\n前15行源代码:")
for i, line in enumerate(lines, 1):
    print(f"  {i}: {line}")

print("\n测试调用...")
result = analyze_symbol("BTCUSDT")
print(f"\n返回字段:")
for key in sorted(result.keys()):
    val = result[key]
    if isinstance(val, dict) and len(str(val)) > 100:
        print(f"  {key}: <dict with {len(val)} keys>")
    elif isinstance(val, (int, float, bool, str, type(None))):
        print(f"  {key}: {val}")
    else:
        print(f"  {key}: {type(val).__name__}")
