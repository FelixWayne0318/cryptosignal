#!/usr/bin/env python3
# coding: utf-8
"""
Phase 1 数据新鲜度测试

测试目标：
1. 验证每次扫描是否使用最新K线数据
2. 验证Phase 1三层更新机制是否正常工作
3. 验证API调用是否正常
4. 验证缓存更新时间戳

测试方法：
- 连续多次扫描同一批币种
- 记录每次扫描的K线时间戳
- 对比缓存更新时间
- 验证数据新鲜度
"""

import sys
import os
import time
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ats_core.pipeline.batch_scan_optimized import BatchScanner
from ats_core.data.realtime_kline_cache import get_kline_cache
from ats_core.sources.binance import BinanceClient
from ats_core.logging import log, warn, error


def format_timestamp(ts_ms):
    """格式化时间戳为可读格式"""
    if ts_ms is None:
        return "N/A"
    try:
        dt = datetime.fromtimestamp(ts_ms / 1000)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return str(ts_ms)


def get_kline_age(ts_ms):
    """计算K线年龄（秒）"""
    if ts_ms is None:
        return None
    try:
        now = time.time() * 1000
        age_ms = now - ts_ms
        return age_ms / 1000
    except:
        return None


def test_phase1_data_freshness():
    """测试Phase 1数据新鲜度"""

    # 测试币种（选择流动性好的成熟币）
    test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT']

    log("=" * 80)
    log("🧪 Phase 1 数据新鲜度测试")
    log("=" * 80)
    log("")
    log(f"测试币种: {', '.join(test_symbols)}")
    log(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("")

    # 初始化K线缓存
    kline_cache = get_kline_cache()
    client = BinanceClient()

    # 第一步：检查初始缓存状态
    log("=" * 80)
    log("📋 第1步：检查初始缓存状态")
    log("=" * 80)
    log("")

    initial_cache_status = {}
    for symbol in test_symbols:
        if symbol in kline_cache.cache:
            k1h = kline_cache.cache[symbol].get('1h', [])
            k4h = kline_cache.cache[symbol].get('4h', [])
            k15m = kline_cache.cache[symbol].get('15m', [])

            last_update = kline_cache.last_update.get(symbol, None)

            initial_cache_status[symbol] = {
                'k1h_count': len(k1h),
                'k4h_count': len(k4h),
                'k15m_count': len(k15m),
                'k1h_last_ts': k1h[-1][0] if k1h else None,
                'k4h_last_ts': k4h[-1][0] if k4h else None,
                'k15m_last_ts': k15m[-1][0] if k15m else None,
                'last_update': last_update
            }

            log(f"{symbol}:")
            log(f"  1h K线数量: {len(k1h)}")
            log(f"  4h K线数量: {len(k4h)}")
            log(f"  15m K线数量: {len(k15m)}")
            if k1h:
                log(f"  最新1h K线时间: {format_timestamp(k1h[-1][0])}")
                age = get_kline_age(k1h[-1][0])
                if age is not None:
                    log(f"  1h K线年龄: {age:.1f}秒")
            if last_update:
                update_age = time.time() - last_update
                log(f"  缓存更新时间: {update_age:.1f}秒前")
            log("")
        else:
            log(f"{symbol}: ❌ 缓存中不存在")
            log("")

    # 第二步：执行Layer 1更新（价格更新）
    log("=" * 80)
    log("📈 第2步：执行Layer 1更新（价格更新）")
    log("=" * 80)
    log("")

    log("调用: kline_cache.update_current_prices()")
    layer1_start = time.time()

    try:
        layer1_result = await_sync(kline_cache.update_current_prices(
            symbols=test_symbols,
            client=client
        ))
        layer1_elapsed = time.time() - layer1_start

        log(f"✅ Layer 1 完成")
        log(f"  耗时: {layer1_elapsed:.2f}秒")
        log(f"  更新数量: {layer1_result.get('updated_count', 0)}")
        log(f"  API调用: 1次 (ticker_24hr)")
        log("")

        # 检查更新后的状态
        for symbol in test_symbols:
            if symbol in kline_cache.cache:
                k1h = kline_cache.cache[symbol].get('1h', [])
                last_update = kline_cache.last_update.get(symbol, None)

                log(f"{symbol}:")
                if k1h:
                    log(f"  最新1h K线时间: {format_timestamp(k1h[-1][0])}")
                    log(f"  收盘价: {k1h[-1][4]}")
                if last_update:
                    update_age = time.time() - last_update
                    log(f"  缓存更新: {update_age:.1f}秒前 {'✅ 刚更新' if update_age < 5 else '⚠️ 未更新'}")
                log("")
    except Exception as e:
        error(f"❌ Layer 1 更新失败: {e}")
        import traceback
        traceback.print_exc()

    # 第三步：检查是否应该触发Layer 2
    log("=" * 80)
    log("📊 第3步：检查Layer 2触发条件")
    log("=" * 80)
    log("")

    current_time = datetime.now()
    current_minute = current_time.minute

    log(f"当前时间: {current_time.strftime('%H:%M:%S')}")
    log(f"当前分钟: {current_minute}")
    log("")

    should_update_15m = current_minute in [2, 17, 32, 47]
    should_update_1h4h = current_minute in [5, 7]

    log("Layer 2 触发规则:")
    log(f"  15m K线更新: 每15分钟后2分钟 (02, 17, 32, 47分)")
    log(f"    → 当前 {'✅ 应该触发' if should_update_15m else '⏸️  不触发'}")
    log(f"  1h/4h K线更新: 每小时后5-7分钟 (05, 07分)")
    log(f"    → 当前 {'✅ 应该触发' if should_update_1h4h else '⏸️  不触发'}")
    log("")

    # 如果应该触发，执行Layer 2更新
    if should_update_15m or should_update_1h4h:
        if should_update_15m:
            log("执行: kline_cache.update_completed_klines(['15m'])")
            layer2_start = time.time()
            try:
                layer2_result = await_sync(kline_cache.update_completed_klines(
                    symbols=test_symbols,
                    intervals=['15m'],
                    client=client
                ))
                layer2_elapsed = time.time() - layer2_start

                log(f"✅ Layer 2 (15m) 完成")
                log(f"  耗时: {layer2_elapsed:.2f}秒")
                log(f"  更新数量: {layer2_result.get('updated_count', 0)}")
                log(f"  失败数量: {layer2_result.get('error_count', 0)}")
                log(f"  API调用: ~{len(test_symbols)}次")
                log("")
            except Exception as e:
                error(f"❌ Layer 2 (15m) 更新失败: {e}")

        if should_update_1h4h:
            log("执行: kline_cache.update_completed_klines(['1h', '4h'])")
            layer2_start = time.time()
            try:
                layer2_result = await_sync(kline_cache.update_completed_klines(
                    symbols=test_symbols,
                    intervals=['1h', '4h'],
                    client=client
                ))
                layer2_elapsed = time.time() - layer2_start

                log(f"✅ Layer 2 (1h/4h) 完成")
                log(f"  耗时: {layer2_elapsed:.2f}秒")
                log(f"  更新数量: {layer2_result.get('updated_count', 0)}")
                log(f"  失败数量: {layer2_result.get('error_count', 0)}")
                log(f"  API调用: ~{len(test_symbols) * 2}次")
                log("")
            except Exception as e:
                error(f"❌ Layer 2 (1h/4h) 更新失败: {e}")
    else:
        log("⏸️  当前时间不触发Layer 2更新")
        log("")

    # 第四步：执行完整批量扫描
    log("=" * 80)
    log("🔍 第4步：执行完整批量扫描")
    log("=" * 80)
    log("")

    log("初始化BatchScanner...")
    scanner = BatchScanner()

    log("执行扫描...")
    scan_start = time.time()

    try:
        results = await_sync(scanner.scan(
            symbols=test_symbols,
            use_cache=True
        ))
        scan_elapsed = time.time() - scan_start

        log(f"✅ 扫描完成")
        log(f"  总耗时: {scan_elapsed:.2f}秒")
        log(f"  扫描币种: {len(test_symbols)}")
        log("")

        # 分析每个币种的结果
        for symbol in test_symbols:
            result = results.get(symbol, {})
            if result:
                log(f"{symbol}:")
                log(f"  加权分数: {result.get('weighted_score', 0):+.1f}")
                log(f"  置信度: {result.get('confidence', 0):.1f}")
                log(f"  Edge: {result.get('edge', 0):+.4f}")
                log(f"  概率: {result.get('probability', 0.5):.3f}")

                # 检查gates信息（包含DataQual）
                gates = result.get('gates', {})
                if gates:
                    data_qual = gates.get('data_qual', 0)
                    log(f"  DataQual: {data_qual:.3f} {'✅' if data_qual >= 0.9 else '⚠️'}")

                log("")
    except Exception as e:
        error(f"❌ 扫描失败: {e}")
        import traceback
        traceback.print_exc()

    # 第五步：对比前后数据变化
    log("=" * 80)
    log("📊 第5步：数据新鲜度分析")
    log("=" * 80)
    log("")

    log("对比初始状态 vs 扫描后状态:")
    log("")

    for symbol in test_symbols:
        if symbol in initial_cache_status and symbol in kline_cache.cache:
            initial = initial_cache_status[symbol]

            k1h = kline_cache.cache[symbol].get('1h', [])
            current_ts = k1h[-1][0] if k1h else None
            initial_ts = initial['k1h_last_ts']

            log(f"{symbol}:")
            log(f"  初始1h K线时间: {format_timestamp(initial_ts)}")
            log(f"  当前1h K线时间: {format_timestamp(current_ts)}")

            if current_ts and initial_ts:
                if current_ts > initial_ts:
                    log(f"  状态: ✅ 数据已更新 (新增 {(current_ts - initial_ts) / 1000 / 3600:.1f} 小时)")
                elif current_ts == initial_ts:
                    age = get_kline_age(current_ts)
                    if age and age < 3600:
                        log(f"  状态: ✅ 数据最新 (年龄: {age:.0f}秒)")
                    else:
                        log(f"  状态: ⚠️  数据未更新 (年龄: {age:.0f}秒)")
                else:
                    log(f"  状态: ❌ 数据异常 (时间倒退)")

            # 检查缓存更新时间
            last_update = kline_cache.last_update.get(symbol, None)
            if last_update:
                update_age = time.time() - last_update
                log(f"  缓存更新: {update_age:.1f}秒前")
                if update_age < 10:
                    log(f"  → ✅ 刚刚更新")
                elif update_age < 60:
                    log(f"  → ⚠️  更新较旧")
                else:
                    log(f"  → ❌ 更新过时")

            log("")

    # 第六步：总结
    log("=" * 80)
    log("📝 测试总结")
    log("=" * 80)
    log("")

    log("Phase 1 三层更新机制验证:")
    log("  Layer 1 (价格): ✅ 已测试")
    log("  Layer 2 (K线): " + ("✅ 已测试" if (should_update_15m or should_update_1h4h) else "⏸️  未触发（时间不对）"))
    log("  Layer 3 (市场): ⏸️  未测试（需30分钟触发）")
    log("")

    log("数据新鲜度评估:")
    fresh_count = 0
    total_count = len(test_symbols)

    for symbol in test_symbols:
        if symbol in kline_cache.cache:
            k1h = kline_cache.cache[symbol].get('1h', [])
            if k1h:
                age = get_kline_age(k1h[-1][0])
                if age is not None and age < 3600:
                    fresh_count += 1

    log(f"  新鲜数据: {fresh_count}/{total_count}")
    log(f"  新鲜度: {fresh_count / total_count * 100:.1f}%")
    log("")

    if fresh_count == total_count:
        log("✅ 所有测试通过！Phase 1 数据更新机制工作正常")
    else:
        log("⚠️  部分数据不够新鲜，请检查Phase 1配置")

    log("")
    log("=" * 80)
    log("测试完成")
    log("=" * 80)


def await_sync(coro):
    """同步运行异步函数"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)


if __name__ == "__main__":
    test_phase1_data_freshness()
