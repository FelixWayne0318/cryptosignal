#!/bin/bash
# 简化的Q/I因子诊断脚本

echo "=================================="
echo "Q/I因子快速诊断"
echo "=================================="
echo ""

cd /home/user/cryptosignal

PYTHONPATH=/home/user/cryptosignal python3 << 'EOF'
import asyncio
from ats_core.pipeline.batch_scan_optimized import OptimizedBatchScanner

async def diagnose():
    scanner = OptimizedBatchScanner()

    print("🔍 开始初始化扫描器...")
    print("=" * 60)

    try:
        await scanner.initialize()
    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        return

    print("\n" + "=" * 60)
    print("📊 诊断结果")
    print("=" * 60)

    # 检查清算数据缓存
    print("\n【Q因子 - 清算数据】")
    total_symbols = len(scanner.liquidation_cache)
    non_empty = sum(1 for v in scanner.liquidation_cache.values() if v and len(v) > 0)

    print(f"  总币种数: {total_symbols}")
    print(f"  有清算数据: {non_empty}/{total_symbols}")

    if total_symbols > 0:
        success_rate = (non_empty / total_symbols) * 100
        print(f"  成功率: {success_rate:.1f}%")

        if success_rate == 0:
            print("\n  ❌ 所有币种的清算数据获取失败！")
            print("     可能原因：")
            print("     1. API权限不足（无清算数据权限）")
            print("     2. 网络超时")
            print("     3. API限流")
        elif success_rate < 50:
            print("\n  ⚠️  清算数据获取成功率偏低")
        else:
            print("\n  ✅ 清算数据获取正常")

            # 显示示例
            for symbol, liq in list(scanner.liquidation_cache.items())[:2]:
                if liq and len(liq) > 0:
                    long_count = sum(1 for l in liq if l.get('side') == 'long')
                    short_count = sum(1 for l in liq if l.get('side') == 'short')
                    print(f"\n  示例 - {symbol}:")
                    print(f"    清算记录: {len(liq)}条")
                    print(f"    多单清算: {long_count}, 空单清算: {short_count}")

    # 检查BTC/ETH K线
    print("\n【I因子 - BTC/ETH K线】")
    print(f"  BTC K线: {len(scanner.btc_klines)}根")
    print(f"  ETH K线: {len(scanner.eth_klines)}根")

    if len(scanner.btc_klines) == 0:
        print("\n  ❌ BTC K线获取失败！")
        print("     可能原因：网络问题、API超时")
    elif len(scanner.btc_klines) < 48:
        print(f"\n  ⚠️  BTC K线数据不足（需要48根，实际{len(scanner.btc_klines)}根）")
    else:
        print("\n  ✅ BTC K线获取正常")

    if len(scanner.eth_klines) == 0:
        print("\n  ❌ ETH K线获取失败！")
    elif len(scanner.eth_klines) < 48:
        print(f"\n  ⚠️  ETH K线数据不足（需要48根，实际{len(scanner.eth_klines)}根）")
    else:
        print("\n  ✅ ETH K线获取正常")

    # 总结
    print("\n" + "=" * 60)
    print("💡 总结")
    print("=" * 60)

    q_ok = non_empty > 0
    i_ok = len(scanner.btc_klines) >= 48 and len(scanner.eth_klines) >= 48

    if q_ok and i_ok:
        print("\n✅ Q和I因子数据获取正常，应该可以计算非零值")
        print("   如果仍然返回0，请查看元数据获取失败原因")
    elif not q_ok and not i_ok:
        print("\n❌ Q和I因子数据都获取失败")
        print("   这就是Q=0, I=0的根本原因！")
    elif not q_ok:
        print("\n⚠️  只有Q因子数据获取失败（清算数据）")
        print("   这会导致Q=0")
    elif not i_ok:
        print("\n⚠️  只有I因子数据获取失败（BTC/ETH K线）")
        print("   这会导致I=0")

    print("\n" + "=" * 60)

try:
    asyncio.run(diagnose())
except KeyboardInterrupt:
    print("\n\n已取消")
except Exception as e:
    print(f"\n❌ 诊断过程出错: {e}")
    import traceback
    traceback.print_exc()
EOF
