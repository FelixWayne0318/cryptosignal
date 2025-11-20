# coding: utf-8
"""
DataFeed - Binance WebSocket实时数据接入

职责：
- 连接Binance WebSocket获取实时K线数据
- 维护1m K线缓冲区用于回看计算
- 提供价格更新回调
- 自动重连机制

数据流：
- WebSocket → 1m Kline → Buffer → Callback

Version: v1.0.0
Standard: SYSTEM_ENHANCEMENT_STANDARD.md v3.3.0
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional
from collections import deque

import websockets
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)


class DataFeed:
    """
    Binance WebSocket实时数据源

    配置从config/params.json的paper_trading.data_feed读取
    """

    def __init__(self, config: Dict[str, Any], symbols: List[str]):
        """
        初始化DataFeed

        Args:
            config: 数据源配置（paper_trading.data_feed）
            symbols: 交易对列表
        """
        # 配置参数
        self.source = config.get("source", "binance_mainnet")
        self.reconnect_delay = config.get("reconnect_delay", 5)
        self.buffer_size = config.get("buffer_size", 1000)
        self.kline_lookback_bars = config.get("kline_lookback_bars", 300)

        # 符号列表（转小写用于WebSocket）
        self.symbols = [s.lower() for s in symbols]

        # K线缓冲区 {symbol: deque of klines}
        self.kline_buffers: Dict[str, deque] = {
            s.upper(): deque(maxlen=self.buffer_size)
            for s in self.symbols
        }

        # 最新价格缓存 {symbol: price}
        self.last_prices: Dict[str, float] = {}

        # 回调函数
        self._on_kline_callback: Optional[Callable] = None
        self._on_price_callback: Optional[Callable] = None

        # 连接状态
        self._running = False
        self._ws = None
        self._reconnect_count = 0

        logger.info(
            f"DataFeed初始化: source={self.source}, "
            f"symbols={symbols}, buffer_size={self.buffer_size}"
        )

    def set_callbacks(
        self,
        on_kline: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        on_price: Optional[Callable[[str, float, int], None]] = None
    ) -> None:
        """
        设置回调函数

        Args:
            on_kline: K线完成回调 (symbol, kline_data) -> None
            on_price: 价格更新回调 (symbol, price, timestamp) -> None
        """
        self._on_kline_callback = on_kline
        self._on_price_callback = on_price

    async def start(self) -> None:
        """启动数据源连接"""
        self._running = True

        while self._running:
            try:
                await self._connect_and_subscribe()
            except ConnectionClosed as e:
                if self._running:
                    self._reconnect_count += 1
                    logger.warning(
                        f"WebSocket连接关闭: {e}, "
                        f"第{self._reconnect_count}次重连，"
                        f"{self.reconnect_delay}秒后重试"
                    )
                    await asyncio.sleep(self.reconnect_delay)
            except Exception as e:
                if self._running:
                    self._reconnect_count += 1
                    logger.error(
                        f"WebSocket异常: {e}, "
                        f"第{self._reconnect_count}次重连，"
                        f"{self.reconnect_delay}秒后重试"
                    )
                    await asyncio.sleep(self.reconnect_delay)

    async def stop(self) -> None:
        """停止数据源连接"""
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None
        logger.info("DataFeed已停止")

    def get_klines(self, symbol: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取K线历史数据

        Args:
            symbol: 交易对
            limit: 返回数量限制（默认全部）

        Returns:
            K线数据列表（从旧到新）
        """
        symbol = symbol.upper()
        if symbol not in self.kline_buffers:
            return []

        buffer = self.kline_buffers[symbol]
        klines = list(buffer)

        if limit:
            klines = klines[-limit:]

        return klines

    def get_last_price(self, symbol: str) -> Optional[float]:
        """
        获取最新价格

        Args:
            symbol: 交易对

        Returns:
            最新价格或None
        """
        return self.last_prices.get(symbol.upper())

    async def _connect_and_subscribe(self) -> None:
        """连接WebSocket并订阅数据流"""
        # 构建WebSocket URL
        streams = [f"{s}@kline_1m" for s in self.symbols]
        stream_name = "/".join(streams)

        if self.source == "binance_mainnet":
            ws_url = f"wss://stream.binance.com:9443/stream?streams={stream_name}"
        else:
            # 默认使用mainnet
            ws_url = f"wss://stream.binance.com:9443/stream?streams={stream_name}"

        logger.info(f"连接WebSocket: {ws_url}")

        async with websockets.connect(ws_url, ping_interval=20) as ws:
            self._ws = ws
            self._reconnect_count = 0
            logger.info("WebSocket连接成功")

            async for message in ws:
                if not self._running:
                    break
                await self._handle_message(message)

    async def _handle_message(self, message: str) -> None:
        """
        处理WebSocket消息

        Args:
            message: 原始JSON消息
        """
        try:
            data = json.loads(message)

            # Binance stream format: {"stream": "...", "data": {...}}
            if "data" in data:
                stream_data = data["data"]
                event_type = stream_data.get("e")

                if event_type == "kline":
                    await self._handle_kline(stream_data)

        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败: {e}")
        except Exception as e:
            logger.error(f"消息处理异常: {e}")

    async def _handle_kline(self, data: Dict[str, Any]) -> None:
        """
        处理K线数据

        Args:
            data: K线事件数据
        """
        symbol = data["s"]  # BNBUSDT
        kline = data["k"]

        # 提取K线数据
        kline_data = {
            "open_time": kline["t"],
            "open": float(kline["o"]),
            "high": float(kline["h"]),
            "low": float(kline["l"]),
            "close": float(kline["c"]),
            "volume": float(kline["v"]),
            "close_time": kline["T"],
            "quote_volume": float(kline["q"]),
            "trades": kline["n"],
            "is_closed": kline["x"],
        }

        # 更新最新价格
        current_price = kline_data["close"]
        self.last_prices[symbol] = current_price

        # 价格回调
        if self._on_price_callback:
            timestamp = int(time.time() * 1000)
            self._on_price_callback(symbol, current_price, timestamp)

        # K线完成时更新缓冲区
        if kline_data["is_closed"]:
            buffer = self.kline_buffers.get(symbol)
            if buffer is not None:
                # 避免重复添加
                if not buffer or buffer[-1]["open_time"] != kline_data["open_time"]:
                    buffer.append(kline_data)
                    logger.debug(
                        f"K线完成: {symbol} "
                        f"O={kline_data['open']:.2f} "
                        f"H={kline_data['high']:.2f} "
                        f"L={kline_data['low']:.2f} "
                        f"C={kline_data['close']:.2f}"
                    )

                    # K线完成回调
                    if self._on_kline_callback:
                        self._on_kline_callback(symbol, kline_data)

    async def preload_history(self, interval: str = "1m") -> None:
        """
        预加载历史K线数据

        从REST API获取历史数据填充缓冲区

        Args:
            interval: K线间隔（默认1m）
        """
        import aiohttp

        base_url = "https://api.binance.com/api/v3/klines"

        for symbol in self.symbols:
            symbol_upper = symbol.upper()

            try:
                params = {
                    "symbol": symbol_upper,
                    "interval": interval,
                    "limit": self.kline_lookback_bars
                }

                async with aiohttp.ClientSession() as session:
                    async with session.get(base_url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()

                            buffer = self.kline_buffers[symbol_upper]
                            for item in data:
                                kline_data = {
                                    "open_time": item[0],
                                    "open": float(item[1]),
                                    "high": float(item[2]),
                                    "low": float(item[3]),
                                    "close": float(item[4]),
                                    "volume": float(item[5]),
                                    "close_time": item[6],
                                    "quote_volume": float(item[7]),
                                    "trades": item[8],
                                    "is_closed": True,
                                }
                                buffer.append(kline_data)

                            # 更新最新价格
                            if buffer:
                                self.last_prices[symbol_upper] = buffer[-1]["close"]

                            logger.info(
                                f"预加载历史数据: {symbol_upper} "
                                f"{len(buffer)}条K线"
                            )
                        else:
                            logger.error(
                                f"获取历史数据失败: {symbol_upper} "
                                f"status={response.status}"
                            )

            except Exception as e:
                logger.error(f"预加载历史数据异常: {symbol_upper} {e}")

    def get_buffer_status(self) -> Dict[str, int]:
        """
        获取缓冲区状态

        Returns:
            {symbol: kline_count}
        """
        return {
            symbol: len(buffer)
            for symbol, buffer in self.kline_buffers.items()
        }


class MockDataFeed(DataFeed):
    """
    模拟数据源（用于测试）

    不连接真实WebSocket，而是从本地数据生成
    """

    def __init__(self, config: Dict[str, Any], symbols: List[str]):
        super().__init__(config, symbols)
        self._mock_data: Dict[str, List[Dict]] = {}
        self._mock_index: Dict[str, int] = {}

    def load_mock_data(self, symbol: str, klines: List[Dict[str, Any]]) -> None:
        """
        加载模拟数据

        Args:
            symbol: 交易对
            klines: K线数据列表
        """
        symbol = symbol.upper()
        self._mock_data[symbol] = klines
        self._mock_index[symbol] = 0
        logger.info(f"加载模拟数据: {symbol} {len(klines)}条")

    async def start(self) -> None:
        """启动模拟数据流"""
        self._running = True
        logger.info("MockDataFeed启动")

        while self._running:
            for symbol, klines in self._mock_data.items():
                idx = self._mock_index.get(symbol, 0)
                if idx < len(klines):
                    kline = klines[idx]

                    # 更新缓冲区
                    self.kline_buffers[symbol].append(kline)
                    self.last_prices[symbol] = kline["close"]

                    # 触发回调
                    if self._on_price_callback:
                        self._on_price_callback(
                            symbol, kline["close"], kline["close_time"]
                        )

                    if self._on_kline_callback:
                        self._on_kline_callback(symbol, kline)

                    self._mock_index[symbol] = idx + 1
                else:
                    # 数据播放完毕
                    self._running = False
                    break

            # 模拟1分钟间隔（实际测试时可以加速）
            await asyncio.sleep(0.1)

        logger.info("MockDataFeed数据播放完毕")
