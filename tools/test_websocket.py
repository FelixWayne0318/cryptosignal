#!/usr/bin/env python3
# coding: utf-8
"""
WebSocket测试脚本

测试币安WebSocket连接是否正常工作

使用方法:
    python3 tools/test_websocket.py

预期输出:
    - WebSocket连接成功
    - 接收到BTCUSDT和ETHUSDT的K线数据
    - 每60秒显示一次统计信息
"""

import os
import sys
import asyncio

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ats_core.data.binance_websocket_client import BinanceWebSocketClient
from ats_core.logging import log


# 测试回调函数
def on_btc_kline(data):
    """BTCUSDT K线回调"""
    kline = data.get('k', {})
    symbol = data.get('s', 'Unknown')
    interval = kline.get('i', 'Unknown')
    close = kline.get('c', 'Unknown')
    is_closed = kline.get('x', False)

    if is_closed:
        log(f"✅ {symbol} {interval} K线完成: close={close}")
    else:
        log(f"📊 {symbol} {interval} K线更新: close={close}")


def on_eth_kline(data):
    """ETHUSDT K线回调"""
    kline = data.get('k', {})
    symbol = data.get('s', 'Unknown')
    interval = kline.get('i', 'Unknown')
    close = kline.get('c', 'Unknown')
    is_closed = kline.get('x', False)

    if is_closed:
        log(f"✅ {symbol} {interval} K线完成: close={close}")
    else:
        log(f"📊 {symbol} {interval} K线更新: close={close}")


async def main():
    """主测试函数"""
    log("=" * 60)
    log("🧪 WebSocket测试开始")
    log("=" * 60)

    # 创建WebSocket客户端
    client = BinanceWebSocketClient()

    # 启动客户端
    await client.start()

    # 等待1秒（确保连接已建立）
    await asyncio.sleep(1)

    # 订阅BTCUSDT 1h K线
    log("📡 订阅 BTCUSDT@kline_1h...")
    await client.subscribe_kline(
        symbol='BTCUSDT',
        interval='1h',
        callback=on_btc_kline
    )

    # 订阅ETHUSDT 1h K线
    log("📡 订阅 ETHUSDT@kline_1h...")
    await client.subscribe_kline(
        symbol='ETHUSDT',
        interval='1h',
        callback=on_eth_kline
    )

    log("=" * 60)
    log("✅ 订阅完成，开始接收数据...")
    log("=" * 60)
    log("   提示：")
    log("   - K线更新会实时显示")
    log("   - 每60秒显示一次统计信息")
    log("   - 按Ctrl+C停止测试")
    log("=" * 60)

    # 运行60秒，每10秒显示一次统计
    try:
        for i in range(6):
            await asyncio.sleep(10)

            # 显示统计
            stats = client.get_stats()
            log("=" * 60)
            log(f"📊 统计信息 (第{(i+1)*10}秒)")
            log("=" * 60)
            log(f"   连接状态: {'✅ 已连接' if stats['connected'] else '❌ 未连接'}")
            log(f"   订阅流数: {stats['active_streams']}")
            log(f"   接收消息: {stats['messages_received']}")
            log(f"   重连次数: {stats['reconnect_count']}")
            log(f"   运行时间: {stats['uptime_seconds']}秒")
            if stats['last_message_age'] is not None:
                log(f"   最后消息: {stats['last_message_age']}秒前")
            log("=" * 60)

        log("=" * 60)
        log("✅ 测试完成！")
        log("=" * 60)

    except KeyboardInterrupt:
        log("⚠️  测试被中断")

    finally:
        # 停止客户端
        await client.stop()

    log("=" * 60)
    log("✅ 测试结束")
    log("=" * 60)


if __name__ == '__main__':
    asyncio.run(main())
