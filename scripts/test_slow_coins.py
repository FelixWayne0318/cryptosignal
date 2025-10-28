#!/usr/bin/env python3
# coding: utf-8
"""
测试慢速币种的性能分析
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ats_core.pipeline.batch_scan_optimized import OptimizedBatchScanner
from ats_core.logging import log

async def test_slow_coins():
    """测试特定慢速币种"""

    # 从之前日志中发现的慢速币种
    slow_symbols = [
        'DEGOUSDT',    # 33.1秒
        'PAXGUSDT',    # 25.6秒
        '42USDT',      # 16.9秒（超新币）
        'EVAAUSDT',    # 16.7秒
        'HUSDT',       # 16.7秒
        'BNBUSDT',     # 31秒
        'ZECUSDT',     # 31秒
        'DOGEUSDT',    # 41秒
        'LINKUSDT',    # 12秒
        '1000PEPEUSDT' # 35秒
    ]

    log("=" * 60)
    log("🔍 慢速币种性能分析测试")
    log("=" * 60)
    log(f"测试币种: {len(slow_symbols)} 个")
    log(f"币种列表: {', '.join(slow_symbols)}")
    log("=" * 60)

    scanner = OptimizedBatchScanner()

    # 初始化（只初始化这些币种）
    log("\n⏳ 初始化扫描器...")
    await scanner.initialize()

    log("\n✅ 初始化完成，开始分析慢速币种...\n")

    # 手动测试每个币种
    import time
    from ats_core.pipeline.analyze_symbol import analyze_symbol_with_preloaded_klines

    for symbol in slow_symbols:
        log("=" * 60)
        log(f"🔍 测试 {symbol}")
        log("=" * 60)

        try:
            # 获取K线
            k1h = scanner.kline_cache.get_klines(symbol, '1h', 300)
            k4h = scanner.kline_cache.get_klines(symbol, '4h', 200)

            if not k1h or not k4h:
                log(f"⚠️  {symbol}: K线数据不足，跳过")
                continue

            log(f"K线数据: 1h={len(k1h)}根, 4h={len(k4h)}根")

            # 分析
            start = time.time()
            result = analyze_symbol_with_preloaded_klines(
                symbol=symbol,
                k1h=k1h,
                k4h=k4h
            )
            elapsed = time.time() - start

            log(f"总耗时: {elapsed:.1f}秒")

            # 打印性能详情
            perf = result.get('perf', {})
            if perf:
                log("\n性能详情:")
                for step, t in sorted(perf.items(), key=lambda x: -x[1]):
                    log(f"  {step}: {t:.3f}秒")

            # 打印慢速步骤
            slow_steps = {k: v for k, v in perf.items() if v > 1.0}
            if slow_steps:
                log("\n⚠️  慢速步骤（>1秒）:")
                for step, t in sorted(slow_steps.items(), key=lambda x: -x[1]):
                    log(f"  - {step}: {t:.1f}秒")

            log("")

        except Exception as e:
            log(f"❌ {symbol} 分析失败: {e}")
            import traceback
            traceback.print_exc()

    # 清理
    await scanner.close()
    log("\n✅ 测试完成")

if __name__ == '__main__':
    asyncio.run(test_slow_coins())
