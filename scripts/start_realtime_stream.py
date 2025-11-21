#!/usr/bin/env python3
"""
实时数据流启动脚本

启动 Cryptofeed WebSocket 数据流，为因子系统提供实时数据。

Usage:
    python scripts/start_realtime_stream.py

Author: CryptoSignal
Version: v0.1.0
"""

from cs_ext.data.cryptofeed_stream import CryptofeedStream

# 数据缓存
trades_buffer = {}
orderbook_cache = {}


def on_trade(evt):
    """写入 CVD / 成交缓存"""
    if evt.symbol not in trades_buffer:
        trades_buffer[evt.symbol] = []
    trades_buffer[evt.symbol].append({
        'ts': evt.ts,
        'price': evt.price,
        'size': evt.size,
        'side': evt.side
    })
    # 保留最近1000条
    if len(trades_buffer[evt.symbol]) > 1000:
        trades_buffer[evt.symbol] = trades_buffer[evt.symbol][-1000:]


def on_orderbook(evt):
    """写入 OBI / LDI 缓存"""
    orderbook_cache[evt.symbol] = {
        'ts': evt.ts,
        'bids': evt.bids,
        'asks': evt.asks
    }


def start_realtime_data():
    symbols = ["BTC-USDT-PERP", "ETH-USDT-PERP"]
    stream = CryptofeedStream(symbols, on_trade, on_orderbook)
    print(f"Starting stream for {symbols}")
    stream.start()


if __name__ == "__main__":
    start_realtime_data()
