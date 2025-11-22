#!/usr/bin/env python3
"""
Cryptofeed 诊断脚本 - 全面检测事件循环和连接问题
"""

import sys
import asyncio
import inspect

print("=" * 60)
print("Cryptofeed 诊断脚本")
print("=" * 60)

# 1. Python 环境检查
print("\n[1] Python 环境")
print(f"  Python 版本: {sys.version}")
print(f"  平台: {sys.platform}")

# 2. 检查关键依赖
print("\n[2] 依赖包版本")
try:
    import cryptofeed
    version = getattr(cryptofeed, '__version__', 'unknown')
    print(f"  cryptofeed: {version}")
except Exception as e:
    print(f"  cryptofeed: 导入失败 - {e}")
    sys.exit(1)

try:
    import uvloop
    print(f"  uvloop: {uvloop.__version__}")
except ImportError:
    print(f"  uvloop: 未安装")

try:
    import nest_asyncio
    print(f"  nest_asyncio: 已安装")
except ImportError:
    print(f"  nest_asyncio: 未安装")

# 3. 检查 Cryptofeed Feed 类的 start 方法签名
print("\n[3] Feed.start() 方法签名检查")
try:
    from cryptofeed.feed import Feed
    start_sig = inspect.signature(Feed.start)
    print(f"  Feed.start 签名: {start_sig}")

    # 获取参数列表
    params = list(start_sig.parameters.keys())
    print(f"  参数列表: {params}")

    # 检查是否需要 loop 参数
    if 'loop' in params:
        print(f"  ⚠️  需要 loop 参数")
    else:
        print(f"  ✅ 不需要 loop 参数")
except Exception as e:
    print(f"  检查失败: {e}")

# 4. 检查 FeedHandler 的方法
print("\n[4] FeedHandler 方法检查")
try:
    from cryptofeed import FeedHandler
    fh = FeedHandler()

    # 列出所有公开方法
    methods = [m for m in dir(fh) if not m.startswith('_') and callable(getattr(fh, m))]
    print(f"  可用方法: {', '.join(methods)}")

    # 检查 run 方法签名
    if hasattr(fh, 'run'):
        run_sig = inspect.signature(fh.run)
        print(f"  FeedHandler.run 签名: {run_sig}")
except Exception as e:
    print(f"  检查失败: {e}")

# 5. 检查 BinanceFutures 交易所
print("\n[5] BinanceFutures 交易所检查")
try:
    from cryptofeed.exchanges import BinanceFutures

    # 检查支持的币种数量
    exchange = BinanceFutures(config={'log': {'disabled': True}})
    symbols = exchange.symbols()
    print(f"  支持的币种数量: {len(symbols)}")
    print(f"  示例币种: {list(symbols)[:5]}")
except Exception as e:
    print(f"  检查失败: {e}")

# 6. 事件循环测试
print("\n[6] 事件循环测试")

async def test_event_loop():
    """测试基本的异步功能"""
    print("  测试 asyncio.sleep...")
    await asyncio.sleep(0.1)
    print("  ✅ asyncio.sleep 正常")

    # 获取当前事件循环
    try:
        loop = asyncio.get_event_loop()
        print(f"  当前事件循环类型: {type(loop).__name__}")
    except Exception as e:
        print(f"  获取事件循环失败: {e}")

    return True

try:
    result = asyncio.run(test_event_loop())
    print("  ✅ 事件循环测试通过")
except Exception as e:
    print(f"  ❌ 事件循环测试失败: {e}")

# 7. Cryptofeed 简单连接测试
print("\n[7] Cryptofeed 连接测试（5秒超时）")

async def test_cryptofeed_connection():
    """测试 Cryptofeed 连接"""
    from cryptofeed import FeedHandler
    from cryptofeed.exchanges import BinanceFutures
    from cryptofeed.defines import TRADES

    received_data = []

    async def trade_callback(trade, receipt_timestamp):
        received_data.append(trade)
        print(f"  收到数据: {trade.symbol} @ {trade.price}")

    fh = FeedHandler()

    # 只订阅一个币种
    feed = BinanceFutures(
        channels=[TRADES],
        symbols=['BTC-USDT-PERP'],
        callbacks={TRADES: trade_callback},
    )
    fh.add_feed(feed)

    print("  正在启动 Feed...")

    # 检查 feed.start 的签名来决定如何调用
    start_sig = inspect.signature(feed.start)
    params = list(start_sig.parameters.keys())

    try:
        loop = asyncio.get_event_loop()

        if 'loop' in params:
            print(f"  使用 feed.start(loop)（同步方法）...")
            feed.start(loop)
        else:
            print(f"  使用 feed.start()（同步方法）...")
            feed.start()

        print("  ✅ Feed.start() 成功")

        # 等待数据（最多5秒）
        for i in range(50):
            await asyncio.sleep(0.1)
            if received_data:
                break

        if received_data:
            print(f"  ✅ 收到 {len(received_data)} 条数据")
        else:
            print(f"  ⚠️  5秒内未收到数据（可能是网络问题）")

        # 停止
        await feed.stop()
        print("  ✅ Feed.stop() 成功")

    except TypeError as e:
        print(f"  ❌ TypeError: {e}")
        print(f"  这表明 Feed.start() 的调用方式不正确")
        raise
    except Exception as e:
        print(f"  ❌ 连接失败: {type(e).__name__}: {e}")
        raise

try:
    asyncio.run(test_cryptofeed_connection())
    print("  ✅ Cryptofeed 连接测试通过")
except Exception as e:
    print(f"  ❌ Cryptofeed 连接测试失败")
    import traceback
    traceback.print_exc()

# 8. 检查 CryptoSignal 模块
print("\n[8] CryptoSignal 模块检查")
try:
    from cs_ext.data.cryptofeed_stream import CryptofeedStream
    print("  ✅ CryptofeedStream 导入成功")

    # 检查 _run_async 方法
    if hasattr(CryptofeedStream, '_run_async'):
        sig = inspect.signature(CryptofeedStream._run_async)
        print(f"  _run_async 签名: {sig}")
except Exception as e:
    print(f"  ❌ 导入失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)
