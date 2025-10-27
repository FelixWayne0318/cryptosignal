#!/usr/bin/env python3
# coding: utf-8
"""
测试WebSocket优化批量扫描

使用方法:
    python scripts/test_optimized_scan.py
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ats_core.pipeline.batch_scan_optimized import run_optimized_scan, benchmark_comparison


async def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║        WebSocket批量扫描优化测试                              ║
╚══════════════════════════════════════════════════════════════╝

选择测试模式:
1. 快速测试（20个币种）
2. 完整扫描（所有币种）
3. 性能对比（当前REST vs WebSocket缓存）
    """)

    choice = input("请选择 (1/2/3): ").strip()

    if choice == '1':
        print("\n🚀 开始快速测试（20个币种）...\n")
        await run_optimized_scan(min_score=70, max_symbols=20)

    elif choice == '2':
        print("\n🚀 开始完整扫描（所有币种）...\n")
        await run_optimized_scan(min_score=75)

    elif choice == '3':
        print("\n🚀 开始性能对比测试...\n")
        await benchmark_comparison(test_symbols=20)

    else:
        print("❌ 无效选择")
        return

    print("\n✅ 测试完成！\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  测试中断")
    except Exception as e:
        print(f"\n\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
