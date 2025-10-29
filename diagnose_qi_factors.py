#!/usr/bin/env python
# coding: utf-8
"""
Q和I因子诊断脚本

检查数据获取和传递的每个环节，定位Q/I因子返回0的原因。
"""
import asyncio
from ats_core.pipeline.batch_scan_optimized import OptimizedBatchScanner

async def diagnose_qi_factors():
    """诊断Q和I因子数据流"""
    print("\n" + "=" * 80)
    print("Q和I因子诊断")
    print("=" * 80)

    scanner = OptimizedBatchScanner()

    # ========== 阶段1：初始化 ==========
    print("\n【阶段1：初始化扫描器】")
    await scanner.initialize()

    # 检查清算数据缓存
    print("\n【阶段2：检查清算数据缓存（Q因子）】")
    if hasattr(scanner, 'liquidation_cache'):
        total_symbols = len(scanner.liquidation_cache)
        non_empty = sum(1 for v in scanner.liquidation_cache.values() if v and len(v) > 0)
        print(f"  清算缓存中的币种数: {total_symbols}")
        print(f"  有清算数据的币种: {non_empty}/{total_symbols}")

        # 显示前3个币种的清算数据
        for i, (symbol, liquidations) in enumerate(list(scanner.liquidation_cache.items())[:3]):
            print(f"\n  [{symbol}]")
            print(f"    清算数据条数: {len(liquidations) if liquidations else 0}")
            if liquidations and len(liquidations) > 0:
                print(f"    示例数据: {liquidations[0]}")
                # 统计多空
                long_count = sum(1 for l in liquidations if l.get('side') == 'long')
                short_count = sum(1 for l in liquidations if l.get('side') == 'short')
                print(f"    多单清算: {long_count}, 空单清算: {short_count}")
    else:
        print("  ❌ 未找到liquidation_cache属性")

    # 检查BTC/ETH K线缓存
    print("\n【阶段3：检查BTC/ETH K线缓存（I因子）】")
    if hasattr(scanner, 'btc_klines'):
        print(f"  BTC K线数量: {len(scanner.btc_klines) if scanner.btc_klines else 0}根")
        if scanner.btc_klines and len(scanner.btc_klines) > 0:
            print(f"  BTC示例K线: {scanner.btc_klines[0][:5]}...")  # 前5个字段
    else:
        print("  ❌ 未找到btc_klines属性")

    if hasattr(scanner, 'eth_klines'):
        print(f"  ETH K线数量: {len(scanner.eth_klines) if scanner.eth_klines else 0}根")
        if scanner.eth_klines and len(scanner.eth_klines) > 0:
            print(f"  ETH示例K线: {scanner.eth_klines[0][:5]}...")
    else:
        print("  ❌ 未找到eth_klines属性")

    # ========== 阶段4：扫描BTCUSDT ==========
    print("\n【阶段4：扫描BTCUSDT并检查Q/I因子】")
    results = await scanner.scan()

    if not results:
        print("  ❌ 扫描失败，无结果")
        return

    # 找到BTCUSDT的结果
    btc_result = None
    for r in results:
        if r.get('symbol') == 'BTCUSDT':
            btc_result = r
            break

    if not btc_result:
        print("  ❌ 未找到BTCUSDT的分析结果")
        return

    # 提取Q和I因子
    scores = btc_result.get('scores', {})
    scores_meta = btc_result.get('scores_meta', {})

    Q = scores.get('Q', 0)
    I = scores.get('I', 0)
    Q_meta = scores_meta.get('Q', {})
    I_meta = scores_meta.get('I', {})

    print(f"\n  BTCUSDT分析结果:")
    print(f"    Q因子分数: {Q:+.1f}/100")
    print(f"    Q因子元数据: {Q_meta}")

    print(f"\n    I因子分数: {I:+.1f}/100")
    print(f"    I因子元数据: {I_meta}")

    # ========== 阶段5：诊断结论 ==========
    print("\n【阶段5：诊断结论】")

    # Q因子诊断
    if Q == 0:
        if 'note' in Q_meta:
            if '无清算数据' in Q_meta['note']:
                print("\n  🔴 Q因子问题：清算数据未传递到分析函数")
                print("     可能原因：")
                print("     1. liquidation_cache中BTCUSDT的数据为空")
                print("     2. 清算数据获取失败")
                print("     3. scan()方法未正确传递liquidations参数")
            else:
                print(f"\n  ⚠️  Q因子返回0，原因: {Q_meta['note']}")
        elif 'error' in Q_meta:
            print(f"\n  🔴 Q因子计算失败: {Q_meta['error']}")
        else:
            print("\n  ⚠️  Q因子返回0，但无错误信息（可能清算平衡）")
    else:
        print(f"\n  ✅ Q因子正常工作: {Q:+.1f}/100")

    # I因子诊断
    if I == 0:
        if 'note' in I_meta:
            if '缺少BTC/ETH' in I_meta['note']:
                print("\n  🔴 I因子问题：BTC/ETH K线未传递到分析函数")
                print("     可能原因：")
                print("     1. btc_klines或eth_klines为空")
                print("     2. K线获取失败")
                print("     3. scan()方法未正确传递btc/eth_klines参数")
            elif '数据不足' in I_meta['note']:
                print(f"\n  ⚠️  I因子数据不足: {I_meta['note']}")
            else:
                print(f"\n  ⚠️  I因子返回0，原因: {I_meta['note']}")
        elif 'error' in I_meta:
            print(f"\n  🔴 I因子计算失败: {I_meta['error']}")
        else:
            print("\n  ⚠️  I因子返回0，但无错误信息（可能与BTC/ETH完全相关）")
    else:
        print(f"\n  ✅ I因子正常工作: {I:+.1f}/100")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(diagnose_qi_factors())
