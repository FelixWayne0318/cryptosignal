# coding: utf-8
"""
币安异步客户端（REST + WebSocket）

特性:
- REST API: 用于初始化历史数据
- WebSocket: 用于实时数据更新
- 与RealtimeKlineCache无缝集成
- 支持异步并发操作

使用场景:
- 批量市场扫描
- 实时K线监控
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional, Callable
from ats_core.logging import log, warn, error
from ats_core.data.binance_websocket_client import BinanceWebSocketClient


class BinanceAsyncClient:
    """
    币安异步客户端（完整版）

    功能:
    1. REST API: 获取历史K线、持仓量、资金费率等
    2. WebSocket: 实时K线数据推送
    3. 自动管理连接和会话

    示例:
        async with BinanceAsyncClient() as client:
            # REST: 获取历史K线
            klines = await client.get_klines('BTCUSDT', '1h', limit=300)

            # WebSocket: 订阅实时K线
            await client.subscribe_kline(
                symbol='BTCUSDT',
                interval='1h',
                callback=lambda data: print(data)
            )

            # 等待WebSocket消息
            await asyncio.sleep(60)
    """

    # 币安REST API地址
    BASE_URL = "https://fapi.binance.com"

    def __init__(self):
        """初始化异步客户端"""
        # HTTP会话
        self.session: Optional[aiohttp.ClientSession] = None

        # WebSocket客户端
        self.ws_client: Optional[BinanceWebSocketClient] = None

        # 是否已启动
        self.started = False

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.close()

    async def start(self):
        """启动客户端"""
        if self.started:
            return

        # 创建HTTP会话
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )

        # 创建WebSocket客户端
        self.ws_client = BinanceWebSocketClient()

        self.started = True
        log("✅ 币安异步客户端已启动")

    async def close(self):
        """关闭客户端"""
        if not self.started:
            return

        # 关闭HTTP会话
        if self.session:
            await self.session.close()
            self.session = None

        # 关闭WebSocket客户端
        if self.ws_client:
            await self.ws_client.stop()
            self.ws_client = None

        self.started = False
        log("✅ 币安异步客户端已关闭")

    # ============ REST API 方法 ============

    async def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 300
    ) -> List:
        """
        获取K线数据（REST API）

        Args:
            symbol: 币种（如 BTCUSDT）
            interval: 周期（如 1h, 5m, 15m）
            limit: 数量（最大1500）

        Returns:
            K线列表，格式: [[open_time, open, high, low, close, volume, ...], ...]
        """
        if not self.session:
            raise RuntimeError("客户端未启动，请先调用 start() 或使用 async with")

        symbol = symbol.upper()
        url = f"{self.BASE_URL}/fapi/v1/klines"

        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": min(limit, 1500)
        }

        try:
            async with self.session.get(url, params=params) as resp:
                resp.raise_for_status()
                data = await resp.json()

                # 检查是否有错误
                if isinstance(data, dict) and 'code' in data:
                    error(f"❌ API错误 {symbol}: {data.get('msg', 'Unknown error')}")
                    return []

                return data

        except aiohttp.ClientError as e:
            error(f"❌ 请求失败 {symbol}: {e}")
            return []
        except Exception as e:
            error(f"❌ 未知错误 {symbol}: {e}")
            return []

    async def get_open_interest_hist(
        self,
        symbol: str,
        period: str = "1h",
        limit: int = 200
    ) -> List[Dict]:
        """
        获取持仓量历史（REST API）

        Args:
            symbol: 币种
            period: 周期（5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d）
            limit: 数量（最大500）

        Returns:
            持仓量列表，格式: [{"symbol": "BTCUSDT", "sumOpenInterest": "123.45", "timestamp": 1638747600000}, ...]
        """
        if not self.session:
            raise RuntimeError("客户端未启动")

        symbol = symbol.upper()
        url = f"{self.BASE_URL}/futures/data/openInterestHist"

        params = {
            "symbol": symbol,
            "period": period,
            "limit": min(limit, 500)
        }

        try:
            async with self.session.get(url, params=params) as resp:
                resp.raise_for_status()
                data = await resp.json()

                if isinstance(data, dict) and 'code' in data:
                    error(f"❌ API错误 {symbol}: {data.get('msg', 'Unknown error')}")
                    return []

                return data

        except Exception as e:
            error(f"❌ 获取持仓量失败 {symbol}: {e}")
            return []

    async def get_funding_rate(
        self,
        symbol: str,
        limit: int = 100
    ) -> List[Dict]:
        """
        获取资金费率历史（REST API）

        Args:
            symbol: 币种
            limit: 数量（最大1000）

        Returns:
            资金费率列表，格式: [{"symbol": "BTCUSDT", "fundingRate": "0.0001", "fundingTime": 1638748800000}, ...]
        """
        if not self.session:
            raise RuntimeError("客户端未启动")

        symbol = symbol.upper()
        url = f"{self.BASE_URL}/fapi/v1/fundingRate"

        params = {
            "symbol": symbol,
            "limit": min(limit, 1000)
        }

        try:
            async with self.session.get(url, params=params) as resp:
                resp.raise_for_status()
                data = await resp.json()

                if isinstance(data, dict) and 'code' in data:
                    error(f"❌ API错误 {symbol}: {data.get('msg', 'Unknown error')}")
                    return []

                return data

        except Exception as e:
            error(f"❌ 获取资金费率失败 {symbol}: {e}")
            return []

    async def get_ticker_24h(self, symbol: Optional[str] = None) -> Dict:
        """
        获取24小时统计（REST API）

        Args:
            symbol: 币种（如果为None，返回所有币种）

        Returns:
            统计数据
        """
        if not self.session:
            raise RuntimeError("客户端未启动")

        url = f"{self.BASE_URL}/fapi/v1/ticker/24hr"

        params = {}
        if symbol:
            params['symbol'] = symbol.upper()

        try:
            async with self.session.get(url, params=params) as resp:
                resp.raise_for_status()
                return await resp.json()

        except Exception as e:
            error(f"❌ 获取24h统计失败: {e}")
            return {}

    # ============ WebSocket 方法 ============

    async def subscribe_kline(
        self,
        symbol: str,
        interval: str,
        callback: Callable[[Dict], None]
    ):
        """
        订阅K线数据流（WebSocket）

        Args:
            symbol: 币种（如 BTCUSDT）
            interval: 周期（如 1h, 5m, 15m）
            callback: 数据回调函数，接收K线数据

        回调数据格式:
        {
            "e": "kline",
            "E": 1638747660000,
            "s": "BTCUSDT",
            "k": {
                "t": 1638747600000,  # 开盘时间
                "T": 1638751199999,  # 收盘时间
                "s": "BTCUSDT",
                "i": "1h",           # 周期
                "o": "49000.0",      # 开盘价
                "h": "49500.0",      # 最高价
                "l": "48800.0",      # 最低价
                "c": "49200.0",      # 收盘价
                "v": "1000.5",       # 成交量
                "x": false,          # 是否完成（true=K线已完成）
                ...
            }
        }
        """
        if not self.ws_client:
            raise RuntimeError("WebSocket客户端未启动")

        # 如果WebSocket还未启动，先启动
        if not self.ws_client.running:
            await self.ws_client.start()

        # 订阅K线流
        await self.ws_client.subscribe_kline(symbol, interval, callback)

    async def unsubscribe_kline(self, symbol: str, interval: str):
        """
        取消订阅K线数据流

        Args:
            symbol: 币种
            interval: 周期
        """
        if not self.ws_client:
            return

        await self.ws_client.unsubscribe_kline(symbol, interval)

    def get_websocket_stats(self) -> Dict:
        """获取WebSocket统计信息"""
        if not self.ws_client:
            return {'error': 'WebSocket未启动'}

        return self.ws_client.get_stats()


# ============ 便捷函数 ============

async def create_binance_client() -> BinanceAsyncClient:
    """
    创建并启动币安异步客户端

    Returns:
        已启动的客户端实例

    使用示例:
        client = await create_binance_client()
        klines = await client.get_klines('BTCUSDT', '1h')
        await client.close()
    """
    client = BinanceAsyncClient()
    await client.start()
    return client
