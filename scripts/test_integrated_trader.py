#!/usr/bin/env python3
# coding: utf-8
"""
测试集成WebSocket优化的自动交易系统

使用方法:
    python scripts/test_integrated_trader.py
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ats_core.execution.auto_trader import AutoTrader


async def test_optimized_trader():
    """测试WebSocket优化的自动交易系统"""

    print("""
╔══════════════════════════════════════════════════════════════╗
║     集成WebSocket优化的自动交易系统测试                       ║
╚══════════════════════════════════════════════════════════════╝

功能:
✅ WebSocket批量扫描（17倍提速）
✅ 自动信号执行
✅ 动态仓位管理
✅ 关键事件通知

初始化需要约2-3分钟（一次性预热）
后续每次扫描仅需5秒！
    """)

    input("按Enter开始测试...")

    # 创建自动交易器（默认启用WebSocket优化）
    trader = AutoTrader(use_optimized_scan=True)

    try:
        # 初始化（包含WebSocket K线缓存预热）
        print("\n" + "="*60)
        print("开始初始化（约2-3分钟）...")
        print("="*60)

        await trader.initialize()

        # 查看当前状态
        print("\n" + "="*60)
        print("初始化完成！现在开始测试扫描...")
        print("="*60)

        await trader.print_status()

        # 单次扫描测试
        print("\n" + "="*60)
        print("执行单次扫描（应该约5秒）...")
        print("="*60)

        await trader.scan_and_execute(min_score=75)

        # 再次查看状态
        await trader.print_status()

        print("\n" + "="*60)
        print("测试完成！")
        print("="*60)
        print("""
后续使用:

1. 定时扫描（生产推荐）:
   await trader.start_periodic_scan(interval_minutes=60, min_score=75)

2. 手动触发扫描:
   await trader.scan_and_execute(min_score=75)

3. 查看状态:
   await trader.print_status()

4. 紧急平仓:
   await trader.close_all_positions()
        """)

    except KeyboardInterrupt:
        print("\n\n⚠️  测试中断")

    except Exception as e:
        print(f"\n\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\n关闭交易器...")
        await trader.stop()


async def test_performance_comparison():
    """性能对比测试：优化 vs 标准"""

    print("""
╔══════════════════════════════════════════════════════════════╗
║          性能对比测试: WebSocket优化 vs REST标准              ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # 测试优化版本
    print("\n1️⃣  测试WebSocket优化版本...\n")
    trader_optimized = AutoTrader(use_optimized_scan=True)

    try:
        await trader_optimized.initialize()

        import time
        start = time.time()
        await trader_optimized.scan_and_execute(min_score=75)
        optimized_time = time.time() - start

        print(f"\n✅ WebSocket优化版本耗时: {optimized_time:.1f}秒")

        await trader_optimized.stop()

    except Exception as e:
        print(f"❌ 优化版本测试失败: {e}")
        return

    # 测试标准版本
    print("\n2️⃣  测试REST标准版本...\n")
    trader_standard = AutoTrader(use_optimized_scan=False)

    try:
        await trader_standard.initialize()

        import time
        start = time.time()
        await trader_standard.scan_and_execute(min_score=75)
        standard_time = time.time() - start

        print(f"\n✅ REST标准版本耗时: {standard_time:.1f}秒")

        await trader_standard.stop()

    except Exception as e:
        print(f"❌ 标准版本测试失败: {e}")
        return

    # 对比结果
    print("\n" + "="*60)
    print("📊 性能对比结果")
    print("="*60)
    print(f"WebSocket优化: {optimized_time:.1f}秒")
    print(f"REST标准: {standard_time:.1f}秒")

    if standard_time > optimized_time:
        speedup = standard_time / optimized_time
        print(f"\n⚡ 性能提升: {speedup:.1f}x 🚀")
    print("="*60)


async def main():
    print("""
选择测试模式:
1. 完整功能测试（推荐，包含预热）
2. 性能对比测试（WebSocket vs REST）
3. 快速验证（仅测试初始化）
    """)

    choice = input("请选择 (1/2/3): ").strip()

    if choice == '1':
        await test_optimized_trader()

    elif choice == '2':
        await test_performance_comparison()

    elif choice == '3':
        print("\n🚀 快速验证测试...\n")
        trader = AutoTrader(use_optimized_scan=True)
        try:
            await trader.initialize()
            print("\n✅ 初始化成功！系统就绪。")
            await trader.print_status()
        finally:
            await trader.stop()

    else:
        print("❌ 无效选择")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  测试中断")
    except Exception as e:
        print(f"\n\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
