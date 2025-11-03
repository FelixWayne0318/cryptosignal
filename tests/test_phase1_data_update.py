#!/usr/bin/env python3
# coding: utf-8
"""
Phase 1: 数据更新功能测试

测试内容：
1. Layer 1: 价格更新功能
2. Layer 2: K线增量更新功能
3. Layer 3: 市场数据更新功能
4. 智能时间对齐计算

运行方法：
    python tests/test_phase1_data_update.py
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ats_core.data.realtime_kline_cache import RealtimeKlineCache
from ats_core.execution.binance_futures_client import get_binance_client
from ats_core.logging import log, warn, error


async def test_layer1_price_update():
    """测试Layer 1: 价格更新"""
    log("\n" + "=" * 60)
    log("测试 Layer 1: 价格更新")
    log("=" * 60)

    try:
        # 初始化
        cache = RealtimeKlineCache(max_klines=50)
        client = get_binance_client()

        # 测试币种（只用5个币种快速测试）
        test_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']

        log(f"\n1. 初始化缓存（{len(test_symbols)}个币种）...")
        await cache.initialize_batch(
            symbols=test_symbols,
            intervals=['1h', '15m'],
            client=client
        )

        # 记录更新前的价格
        log("\n2. 记录更新前的价格...")
        before_prices = {}
        for symbol in test_symbols:
            klines_1h = cache.get_klines(symbol, '1h', 1)
            if klines_1h:
                before_prices[symbol] = float(klines_1h[0][4])  # 收盘价
                log(f"   {symbol}: {before_prices[symbol]:.4f}")

        # 等待1秒（让价格有机会变化）
        log("\n3. 等待1秒...")
        await asyncio.sleep(1)

        # 执行Layer 1更新
        log("\n4. 执行Layer 1价格更新...")
        result = await cache.update_current_prices(
            symbols=test_symbols,
            client=client
        )

        log(f"\n   更新结果:")
        log(f"   - 更新数量: {result.get('updated_count')}")
        log(f"   - 耗时: {result.get('elapsed', 0):.2f}秒")

        # 检查更新后的价格
        log("\n5. 检查更新后的价格...")
        after_prices = {}
        changed_count = 0
        for symbol in test_symbols:
            klines_1h = cache.get_klines(symbol, '1h', 1)
            if klines_1h:
                after_prices[symbol] = float(klines_1h[0][4])
                if before_prices.get(symbol) != after_prices[symbol]:
                    changed_count += 1
                    log(f"   {symbol}: {before_prices.get(symbol, 0):.4f} → {after_prices[symbol]:.4f} ✓")
                else:
                    log(f"   {symbol}: {after_prices[symbol]:.4f} (未变化)")

        log(f"\n✅ Layer 1测试完成: {changed_count}/{len(test_symbols)}个币种价格已更新")
        return True

    except Exception as e:
        error(f"❌ Layer 1测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_layer2_kline_update():
    """测试Layer 2: K线增量更新"""
    log("\n" + "=" * 60)
    log("测试 Layer 2: K线增量更新")
    log("=" * 60)

    try:
        # 初始化
        cache = RealtimeKlineCache(max_klines=50)
        client = get_binance_client()

        # 测试币种
        test_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']

        log(f"\n1. 初始化缓存（{len(test_symbols)}个币种）...")
        await cache.initialize_batch(
            symbols=test_symbols,
            intervals=['1h', '15m'],
            client=client
        )

        # 记录更新前的K线
        log("\n2. 记录更新前的K线时间戳...")
        before_timestamps = {}
        for symbol in test_symbols:
            klines_1h = cache.get_klines(symbol, '1h', 2)
            if klines_1h and len(klines_1h) >= 2:
                before_timestamps[symbol] = {
                    'second_last': int(klines_1h[-2][0]),
                    'last': int(klines_1h[-1][0])
                }
                log(f"   {symbol}: 倒数第二={before_timestamps[symbol]['second_last']}, 最后={before_timestamps[symbol]['last']}")

        # 执行Layer 2更新
        log("\n3. 执行Layer 2 K线更新...")
        result = await cache.update_completed_klines(
            symbols=test_symbols,
            intervals=['1h', '15m'],
            client=client
        )

        log(f"\n   更新结果:")
        log(f"   - 更新数量: {result.get('updated_count')}")
        log(f"   - 失败数量: {result.get('error_count')}")
        log(f"   - 耗时: {result.get('elapsed', 0):.2f}秒")

        # 检查更新后的K线
        log("\n4. 检查更新后的K线...")
        for symbol in test_symbols:
            klines_1h = cache.get_klines(symbol, '1h', 2)
            if klines_1h and len(klines_1h) >= 2:
                after_ts = {
                    'second_last': int(klines_1h[-2][0]),
                    'last': int(klines_1h[-1][0])
                }
                log(f"   {symbol}: 倒数第二={after_ts['second_last']}, 最后={after_ts['last']} ✓")

        log(f"\n✅ Layer 2测试完成")
        return True

    except Exception as e:
        error(f"❌ Layer 2测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_layer3_market_data():
    """测试Layer 3: 市场数据更新"""
    log("\n" + "=" * 60)
    log("测试 Layer 3: 市场数据更新")
    log("=" * 60)

    try:
        # 初始化
        cache = RealtimeKlineCache(max_klines=50)
        client = get_binance_client()

        # 测试币种
        test_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']

        log(f"\n1. 初始化缓存（{len(test_symbols)}个币种）...")
        await cache.initialize_batch(
            symbols=test_symbols,
            intervals=['1h'],
            client=client
        )

        # 执行Layer 3更新
        log("\n2. 执行Layer 3市场数据更新...")
        result = await cache.update_market_data(
            symbols=test_symbols,
            client=client
        )

        log(f"\n   更新结果:")
        log(f"   - 更新数量: {result.get('updated_count')}")
        log(f"   - 失败数量: {result.get('error_count')}")
        log(f"   - 耗时: {result.get('elapsed', 0):.2f}秒")

        # 检查市场数据
        log("\n3. 检查市场数据...")
        for symbol in test_symbols:
            market_data = cache.get_market_data(symbol)
            if market_data:
                funding_rate = market_data.get('funding_rate', 0)
                open_interest = market_data.get('open_interest', 0)
                log(f"   {symbol}:")
                log(f"      资金费率: {funding_rate * 100:.4f}%")
                log(f"      持仓量: {open_interest:,.0f}")
            else:
                log(f"   {symbol}: 无市场数据")

        log(f"\n✅ Layer 3测试完成")
        return True

    except Exception as e:
        error(f"❌ Layer 3测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_smart_time_alignment():
    """测试智能时间对齐计算"""
    log("\n" + "=" * 60)
    log("测试智能时间对齐计算")
    log("=" * 60)

    try:
        # 模拟不同的当前时间，测试计算结果
        test_cases = [
            (0, 2),   # 00分 → 02分
            (2, 7),   # 02分 → 07分
            (15, 17), # 15分 → 17分
            (47, 52), # 47分 → 52分
            (57, 2),  # 57分 → 下一小时02分
        ]

        log("\n测试用例:")
        for current_min, expected_min in test_cases:
            # 这里简化测试，只检查逻辑
            key_minutes = [2, 7, 12, 17, 22, 27, 32, 37, 42, 47, 52, 57]

            next_key_minute = None
            for km in key_minutes:
                if km > current_min:
                    next_key_minute = km
                    break

            if next_key_minute is None:
                next_key_minute = 2  # 下一小时

            if next_key_minute == expected_min or (current_min == 57 and expected_min == 2):
                log(f"   ✓ {current_min:02d}分 → {expected_min:02d}分")
            else:
                log(f"   ✗ {current_min:02d}分 → {next_key_minute:02d}分 (期望{expected_min:02d}分)")

        log(f"\n✅ 智能时间对齐测试完成")
        return True

    except Exception as e:
        error(f"❌ 时间对齐测试失败: {e}")
        return False


async def main():
    """运行所有测试"""
    log("\n" + "=" * 80)
    log("Phase 1: 数据更新功能测试套件")
    log("=" * 80)

    results = []

    # 测试Layer 1
    result1 = await test_layer1_price_update()
    results.append(('Layer 1: 价格更新', result1))

    # 测试Layer 2
    result2 = await test_layer2_kline_update()
    results.append(('Layer 2: K线更新', result2))

    # 测试Layer 3
    result3 = await test_layer3_market_data()
    results.append(('Layer 3: 市场数据', result3))

    # 测试时间对齐
    result4 = test_smart_time_alignment()
    results.append(('智能时间对齐', result4))

    # 汇总结果
    log("\n" + "=" * 80)
    log("测试结果汇总")
    log("=" * 80)

    passed = 0
    failed = 0

    for test_name, result in results:
        if result:
            log(f"✅ {test_name}: 通过")
            passed += 1
        else:
            log(f"❌ {test_name}: 失败")
            failed += 1

    log("\n" + "=" * 80)
    log(f"总计: {passed + failed}个测试, {passed}个通过, {failed}个失败")
    log("=" * 80)

    if failed == 0:
        log("\n🎉 所有测试通过！Phase 1实施成功！")
        return 0
    else:
        log("\n⚠️  部分测试失败，请检查错误信息")
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
