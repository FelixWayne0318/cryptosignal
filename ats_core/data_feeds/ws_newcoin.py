# coding: utf-8
"""
新币WebSocket数据流模块 (Phase 2 - NEWCOIN_SPEC.md § 2, § 7)

提供新币专用的WS实时数据订阅：
1. 多粒度K线实时流（1m/5m/15m）
2. 组合流管理（降低单连接压力）
3. 指数回退重连机制
4. 心跳监控与DataQual降级

Phase 2范围:
- ✅ kline_1m/5m/15m订阅
- ✅ 基础重连机制
- ✅ 心跳监控

Phase 4扩展（待实现）:
- ⏸️ aggTrade流（计算speed/agg_buy）
- ⏸️ depth@100ms流（计算OBI）
- ⏸️ markPrice@1s流
- ⏸️ REST深度快照对账

符合规范：newstandards/NEWCOIN_SPEC.md § 2, § 7
"""

from __future__ import annotations
import asyncio
import json
import time
from typing import Dict, List, Optional, Callable, Any
from collections import deque

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    # 如果websockets未安装，提供fallback警告

from ats_core.logging import log, warn, error


# Binance WebSocket端点
WS_BASE = "wss://fstream.binance.com"


class ExponentialBackoff:
    """
    指数回退重连策略

    符合规范：NEWCOIN_SPEC.md § 7 - 指数退避+抖动
    """

    def __init__(self, base_delay: float = 1.0, max_delay: float = 60.0, jitter: float = 0.1):
        """
        Args:
            base_delay: 基础延迟（秒）
            max_delay: 最大延迟（秒）
            jitter: 抖动比例（0-1）
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.retry_count = 0

    def get_delay(self) -> float:
        """计算下次重连延迟（指数回退 + 随机抖动）"""
        import random

        # 指数回退: delay = base * 2^retry_count
        delay = min(self.base_delay * (2 ** self.retry_count), self.max_delay)

        # 添加随机抖动: ±jitter%
        jitter_amount = delay * self.jitter * (random.random() * 2 - 1)
        delay += jitter_amount

        return max(0.1, delay)  # 最小0.1秒

    def on_success(self):
        """连接成功，重置计数"""
        self.retry_count = 0

    def on_failure(self):
        """连接失败，增加计数"""
        self.retry_count += 1


class NewCoinWSFeed:
    """
    新币WebSocket数据流管理器

    功能:
    1. 订阅多粒度K线（1m/5m/15m）
    2. 本地K线缓存（内存中维护最近N根）
    3. 心跳监控与自动重连
    4. DataQual动态降级（心跳缺失时）

    示例:
        feed = NewCoinWSFeed("BTCUSDT")
        await feed.start()
        # 获取最新K线
        k1m = feed.get_klines("1m")
    """

    def __init__(
        self,
        symbol: str,
        cache_size: int = 500,
        heartbeat_interval: float = 30.0,
        heartbeat_timeout: float = 60.0,
    ):
        """
        Args:
            symbol: 交易对符号（如 "BTCUSDT"）
            cache_size: 每个粒度缓存的K线数量
            heartbeat_interval: 心跳检查间隔（秒）
            heartbeat_timeout: 心跳超时阈值（秒）
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError("websockets库未安装，请运行: pip install websockets")

        self.symbol = symbol.upper()
        self.cache_size = cache_size
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout

        # K线缓存（每个粒度一个deque）
        self.klines_cache: Dict[str, deque] = {
            "1m": deque(maxlen=cache_size),
            "5m": deque(maxlen=cache_size),
            "15m": deque(maxlen=cache_size),
        }

        # WS连接（每个流一个连接，Phase 2简化版）
        self.connections: Dict[str, Any] = {}

        # 重连策略
        self.backoff = ExponentialBackoff(base_delay=1.0, max_delay=60.0, jitter=0.1)

        # 心跳状态
        self.last_message_time: Dict[str, float] = {}
        self.data_quality = 1.0  # 0.0-1.0，心跳缺失时降级

        # 运行状态
        self.running = False
        self.tasks: List[asyncio.Task] = []

    async def start(self):
        """启动WS订阅和心跳监控"""
        if self.running:
            warn(f"{self.symbol} WS已在运行")
            return

        self.running = True
        log(f"启动 {self.symbol} WS数据流（1m/5m/15m）")

        # 启动各个流的订阅任务
        for interval in ["1m", "5m", "15m"]:
            task = asyncio.create_task(self._subscribe_kline(interval))
            self.tasks.append(task)

        # 启动心跳监控任务
        heartbeat_task = asyncio.create_task(self._heartbeat_monitor())
        self.tasks.append(heartbeat_task)

    async def stop(self):
        """停止所有WS连接和任务"""
        self.running = False
        log(f"停止 {self.symbol} WS数据流")

        # 关闭所有连接
        for interval, ws in self.connections.items():
            try:
                await ws.close()
            except Exception as e:
                warn(f"关闭{interval} WS连接失败: {e}")

        # 取消所有任务
        for task in self.tasks:
            task.cancel()

        # 等待任务完成
        await asyncio.gather(*self.tasks, return_exceptions=True)

    async def _subscribe_kline(self, interval: str):
        """
        订阅K线流（带自动重连）

        Args:
            interval: K线间隔（1m/5m/15m）
        """
        stream_name = f"{self.symbol.lower()}@kline_{interval}"
        url = f"{WS_BASE}/ws/{stream_name}"

        while self.running:
            try:
                log(f"连接 {stream_name}")
                async with websockets.connect(url) as ws:
                    self.connections[interval] = ws
                    self.backoff.on_success()  # 连接成功，重置重试计数

                    # 持续接收消息
                    async for message in ws:
                        if not self.running:
                            break

                        try:
                            data = json.loads(message)
                            await self._handle_kline_message(interval, data)
                            self.last_message_time[interval] = time.time()

                        except Exception as e:
                            error(f"处理{stream_name}消息失败: {e}")

            except Exception as e:
                self.backoff.on_failure()
                delay = self.backoff.get_delay()
                warn(f"{stream_name} 连接失败: {e}，{delay:.1f}秒后重连（尝试#{self.backoff.retry_count}）")

                if self.running:
                    await asyncio.sleep(delay)

    async def _handle_kline_message(self, interval: str, data: Dict[str, Any]):
        """
        处理K线消息并更新本地缓存

        Binance K线消息格式:
        {
            "e": "kline",
            "E": 1638747660000,  # 事件时间
            "s": "BTCUSDT",
            "k": {
                "t": 1638747600000,  # K线开始时间
                "T": 1638747659999,  # K线结束时间
                "s": "BTCUSDT",
                "i": "1m",
                "f": 123456,  # 第一笔成交ID
                "L": 123457,  # 最后一笔成交ID
                "o": "50000.00",  # 开盘价
                "c": "50100.00",  # 收盘价
                "h": "50200.00",  # 最高价
                "l": "49900.00",  # 最低价
                "v": "100.5",     # 成交量
                "n": 1000,        # 成交笔数
                "x": false,       # 该K线是否完成
                "q": "5010000.00", # 成交额
                "V": "50.2",      # 主动买入成交量
                "Q": "2505000.00", # 主动买入成交额
            }
        }
        """
        if data.get("e") != "kline":
            return

        k = data.get("k", {})

        # 只处理已完成的K线（x=true）
        if not k.get("x"):
            return

        # 转换为标准K线格式（与REST API一致）
        # [openTime, open, high, low, close, volume, closeTime,
        #  quoteVolume, trades, takerBuyBaseVolume, takerBuyQuoteVolume, ignore]
        kline = [
            k["t"],  # openTime
            k["o"],  # open
            k["h"],  # high
            k["l"],  # low
            k["c"],  # close
            k["v"],  # volume
            k["T"],  # closeTime
            k["q"],  # quoteVolume
            k["n"],  # trades
            k["V"],  # takerBuyBaseVolume
            k["Q"],  # takerBuyQuoteVolume
            "0",     # ignore
        ]

        # 添加到缓存（deque自动维护最大长度）
        self.klines_cache[interval].append(kline)

    async def _heartbeat_monitor(self):
        """
        心跳监控任务

        检查各个流的消息接收情况，超时则降低DataQual

        符合规范：NEWCOIN_SPEC.md § 7 - 心跳缺失 → DataQual降级
        """
        while self.running:
            await asyncio.sleep(self.heartbeat_interval)

            current_time = time.time()
            missing_count = 0

            for interval in ["1m", "5m", "15m"]:
                last_time = self.last_message_time.get(interval, 0)
                if last_time == 0:
                    continue  # 尚未收到第一条消息

                time_since_last = current_time - last_time

                if time_since_last > self.heartbeat_timeout:
                    warn(f"{self.symbol} {interval} 心跳超时（{time_since_last:.1f}s）")
                    missing_count += 1

            # 根据缺失流数量降低DataQual
            # 3个流都正常: DataQual = 1.0
            # 缺失1个: 0.8
            # 缺失2个: 0.5
            # 缺失3个: 0.2
            if missing_count == 0:
                self.data_quality = 1.0
            elif missing_count == 1:
                self.data_quality = 0.8
            elif missing_count == 2:
                self.data_quality = 0.5
            else:
                self.data_quality = 0.2

    def get_klines(self, interval: str) -> List[list]:
        """
        获取指定粒度的K线缓存

        Args:
            interval: K线间隔（1m/5m/15m）

        Returns:
            K线列表（按时间升序）
        """
        return list(self.klines_cache.get(interval, []))

    def get_data_quality(self) -> float:
        """
        获取当前数据质量（0.0-1.0）

        基于心跳监控动态调整
        """
        return self.data_quality


# ============ 工具函数 ============

async def test_newcoin_ws(symbol: str, duration: int = 60):
    """
    测试新币WS订阅（运行指定时长）

    Args:
        symbol: 交易对符号
        duration: 运行时长（秒）
    """
    feed = NewCoinWSFeed(symbol)

    try:
        await feed.start()
        log(f"WS测试运行{duration}秒...")

        await asyncio.sleep(duration)

        # 输出缓存状态
        for interval in ["1m", "5m", "15m"]:
            klines = feed.get_klines(interval)
            log(f"{symbol} {interval}: {len(klines)}根K线")

        log(f"DataQual: {feed.get_data_quality():.2f}")

    finally:
        await feed.stop()


# ============ 主函数（测试用） ============

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python ws_newcoin.py SYMBOL [DURATION]")
        print("示例: python ws_newcoin.py BTCUSDT 60")
        sys.exit(1)

    symbol = sys.argv[1]
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60

    asyncio.run(test_newcoin_ws(symbol, duration))
