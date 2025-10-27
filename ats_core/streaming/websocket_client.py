# coding: utf-8
"""
WebSocket实时数据流客户端（框架）

功能：
1. Binance WebSocket流订阅
2. 实时K线、订单簿、交易流
3. 自动重连机制
4. 数据缓冲和回调

使用方法：
    from ats_core.streaming.websocket_client import WebSocketClient

    client = WebSocketClient()
    client.subscribe_kline("BTCUSDT", "1m", on_kline_update)
    client.subscribe_orderbook("BTCUSDT", on_orderbook_update)
    client.start()

注意：
- 本地环境无法直接测试Binance WebSocket
- 需要在服务器上启用
- 提供完整框架，用户可以根据需要定制
"""

from __future__ import annotations
import json
import time
import threading
from typing import Callable, Dict, Any, Optional, List
from collections import deque


class WebSocketClient:
    """
    Binance WebSocket客户端（框架实现）

    特性：
    - 多流订阅
    - 自动重连
    - 心跳检测
    - 线程安全

    TODO（服务器上实现）：
    - 安装websocket-client: pip install websocket-client
    - 实现_connect()方法
    - 实现_send()方法
    - 配置重连策略
    """

    def __init__(
        self,
        base_url: str = "wss://fstream.binance.com",
        reconnect_interval: int = 5,
        buffer_size: int = 1000
    ):
        """
        Args:
            base_url: WebSocket服务器地址
            reconnect_interval: 重连间隔（秒）
            buffer_size: 数据缓冲区大小
        """
        self.base_url = base_url
        self.reconnect_interval = reconnect_interval
        self.buffer_size = buffer_size

        # 订阅管理
        self.subscriptions: Dict[str, Dict[str, Any]] = {}

        # 数据缓冲
        self.kline_buffer: Dict[str, deque] = {}
        self.orderbook_buffer: Dict[str, deque] = {}
        self.trade_buffer: Dict[str, deque] = {}

        # 状态
        self.connected = False
        self.running = False

        # 线程
        self.ws_thread: Optional[threading.Thread] = None
        self.callback_thread: Optional[threading.Thread] = None

        print("[WebSocket] 客户端初始化完成")
        print("[WebSocket] ⚠️ 注意：需要在服务器上安装 websocket-client 库")
        print("[WebSocket] ⚠️ 安装命令: pip install websocket-client")

    def subscribe_kline(
        self,
        symbol: str,
        interval: str,
        callback: Callable[[Dict], None]
    ) -> None:
        """
        订阅实时K线

        Args:
            symbol: 交易对（如 BTCUSDT）
            interval: K线周期（1m, 5m, 15m, 1h等）
            callback: 回调函数 (kline_data) -> None

        K线数据格式：
        {
            'symbol': 'BTCUSDT',
            'interval': '1m',
            'open': 50000.0,
            'high': 50100.0,
            'low': 49900.0,
            'close': 50050.0,
            'volume': 100.5,
            'close_time': 1234567890000
        }
        """
        stream_name = f"{symbol.lower()}@kline_{interval}"

        self.subscriptions[stream_name] = {
            'type': 'kline',
            'symbol': symbol,
            'interval': interval,
            'callback': callback
        }

        # 初始化缓冲区
        if symbol not in self.kline_buffer:
            self.kline_buffer[symbol] = deque(maxlen=self.buffer_size)

        print(f"[WebSocket] 订阅K线: {symbol} {interval}")

    def subscribe_orderbook(
        self,
        symbol: str,
        callback: Callable[[Dict], None],
        depth: int = 20
    ) -> None:
        """
        订阅实时订单簿

        Args:
            symbol: 交易对
            callback: 回调函数 (orderbook_data) -> None
            depth: 深度档位（5, 10, 20）

        订单簿数据格式：
        {
            'symbol': 'BTCUSDT',
            'bids': [[price, qty], ...],
            'asks': [[price, qty], ...],
            'timestamp': 1234567890000
        }
        """
        stream_name = f"{symbol.lower()}@depth{depth}"

        self.subscriptions[stream_name] = {
            'type': 'orderbook',
            'symbol': symbol,
            'depth': depth,
            'callback': callback
        }

        # 初始化缓冲区
        if symbol not in self.orderbook_buffer:
            self.orderbook_buffer[symbol] = deque(maxlen=100)  # 订单簿缓冲较小

        print(f"[WebSocket] 订阅订单簿: {symbol} (深度{depth})")

    def subscribe_trades(
        self,
        symbol: str,
        callback: Callable[[Dict], None]
    ) -> None:
        """
        订阅实时成交流

        Args:
            symbol: 交易对
            callback: 回调函数 (trade_data) -> None

        成交数据格式：
        {
            'symbol': 'BTCUSDT',
            'price': 50000.0,
            'qty': 0.5,
            'time': 1234567890000,
            'is_buyer_maker': True
        }
        """
        stream_name = f"{symbol.lower()}@trade"

        self.subscriptions[stream_name] = {
            'type': 'trade',
            'symbol': symbol,
            'callback': callback
        }

        # 初始化缓冲区
        if symbol not in self.trade_buffer:
            self.trade_buffer[symbol] = deque(maxlen=self.buffer_size)

        print(f"[WebSocket] 订阅成交流: {symbol}")

    def start(self) -> None:
        """
        启动WebSocket客户端

        TODO（服务器实现）：
        1. 导入websocket-client库
        2. 连接Binance WebSocket
        3. 启动接收线程
        4. 启动回调处理线程
        """
        if self.running:
            print("[WebSocket] 客户端已在运行")
            return

        self.running = True

        print("[WebSocket] 启动客户端...")
        print("[WebSocket] ⚠️ 当前为模拟模式")
        print("[WebSocket] ⚠️ 服务器部署时需要实现以下方法：")
        print("[WebSocket]    1. _connect() - 建立WebSocket连接")
        print("[WebSocket]    2. _receive_loop() - 接收数据循环")
        print("[WebSocket]    3. _process_message() - 处理消息")
        print("[WebSocket]    4. _reconnect() - 重连机制")

        # 模拟模式：打印订阅信息
        print(f"[WebSocket] 当前订阅流: {len(self.subscriptions)} 个")
        for stream_name, sub_info in self.subscriptions.items():
            print(f"  - {stream_name} ({sub_info['type']})")

    def stop(self) -> None:
        """停止WebSocket客户端"""
        print("[WebSocket] 停止客户端...")
        self.running = False
        self.connected = False

    def get_latest_kline(self, symbol: str, count: int = 1) -> List[Dict]:
        """
        获取最新K线数据（从缓冲区）

        Args:
            symbol: 交易对
            count: 获取数量

        Returns:
            K线数据列表
        """
        if symbol not in self.kline_buffer:
            return []

        buffer = self.kline_buffer[symbol]
        return list(buffer)[-count:]

    def get_latest_orderbook(self, symbol: str) -> Optional[Dict]:
        """获取最新订单簿"""
        if symbol not in self.orderbook_buffer:
            return None

        buffer = self.orderbook_buffer[symbol]
        return buffer[-1] if buffer else None

    def is_connected(self) -> bool:
        """检查连接状态"""
        return self.connected

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'connected': self.connected,
            'running': self.running,
            'subscriptions': len(self.subscriptions),
            'kline_symbols': len(self.kline_buffer),
            'orderbook_symbols': len(self.orderbook_buffer),
            'trade_symbols': len(self.trade_buffer)
        }


# ========== 便捷函数 ==========

_global_client: Optional[WebSocketClient] = None


def get_websocket_client() -> WebSocketClient:
    """获取全局WebSocket客户端（单例）"""
    global _global_client

    if _global_client is None:
        _global_client = WebSocketClient()

    return _global_client


# ========== 测试代码 ==========

if __name__ == "__main__":
    print("=" * 70)
    print("WebSocket实时数据流框架测试")
    print("=" * 70)

    # 定义回调函数
    def on_kline(data: Dict):
        print(f"[K线更新] {data['symbol']} {data['interval']}: "
              f"C={data['close']}, V={data['volume']}")

    def on_orderbook(data: Dict):
        print(f"[订单簿更新] {data['symbol']}: "
              f"最佳买={data['bids'][0] if data['bids'] else 'N/A'}, "
              f"最佳卖={data['asks'][0] if data['asks'] else 'N/A'}")

    def on_trade(data: Dict):
        print(f"[成交] {data['symbol']}: "
              f"价格={data['price']}, 数量={data['qty']}")

    # 创建客户端
    client = WebSocketClient()

    # 订阅流
    client.subscribe_kline("BTCUSDT", "1m", on_kline)
    client.subscribe_kline("ETHUSDT", "1m", on_kline)
    client.subscribe_orderbook("BTCUSDT", on_orderbook)
    client.subscribe_trades("BTCUSDT", on_trade)

    # 启动（模拟模式）
    client.start()

    # 显示统计
    print(f"\n统计信息: {client.get_stats()}")

    # 停止
    print("\n按Ctrl+C停止...")
    try:
        time.sleep(5)
    except KeyboardInterrupt:
        pass

    client.stop()

    print("\n" + "=" * 70)
    print("✅ WebSocket框架测试完成")
    print("=" * 70)
    print("\n📌 服务器部署步骤：")
    print("1. pip install websocket-client")
    print("2. 实现_connect()等方法")
    print("3. 配置Binance API密钥")
    print("4. 启动client.start()")
