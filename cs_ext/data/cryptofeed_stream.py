"""
Cryptofeed 数据流适配器

封装 Cryptofeed WebSocket 数据流，输出统一格式供 CryptoSignal 因子系统使用。

Features:
    - L2/L3 订单簿数据
    - 逐笔成交 (Trades)
    - 资金费率 (Funding)
    - 清算数据 (Liquidations)
    - Open Interest

Usage:
    from cs_ext.data.cryptofeed_stream import CryptoFeedStream

    stream = CryptoFeedStream(config_path="cs_ext/config/cryptofeed_config.yml")
    stream.start()

Author: Claude Code
Version: v0.1.0
Created: 2025-11-21
"""

import asyncio
import logging
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime
from collections import defaultdict

# 延迟导入cryptofeed，允许在未安装时导入模块
try:
    from cryptofeed import FeedHandler
    from cryptofeed.defines import (
        TRADES, L2_BOOK, L3_BOOK, TICKER, FUNDING, LIQUIDATIONS, OPEN_INTEREST
    )
    from cryptofeed.exchanges import (
        Binance, BinanceFutures, OKX, Bybit
    )
    CRYPTOFEED_AVAILABLE = True
except ImportError:
    CRYPTOFEED_AVAILABLE = False
    FeedHandler = None

logger = logging.getLogger(__name__)


class CryptoFeedStream:
    """
    Cryptofeed 数据流管理器

    将 Cryptofeed 的 WebSocket 数据转换为 CryptoSignal 统一格式
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化数据流管理器

        Args:
            config: 配置字典，包含交易所、交易对、数据类型等
        """
        if not CRYPTOFEED_AVAILABLE:
            raise ImportError(
                "Cryptofeed 未安装。请运行: pip install cryptofeed\n"
                "或者: pip install -e externals/cryptofeed"
            )

        self.config = config or self._default_config()
        self.feed_handler = FeedHandler()

        # 数据缓存
        self.orderbook_cache: Dict[str, Dict] = defaultdict(dict)
        self.trades_cache: Dict[str, List] = defaultdict(list)
        self.funding_cache: Dict[str, Dict] = {}
        self.oi_cache: Dict[str, float] = {}

        # 回调函数
        self.callbacks: Dict[str, List[Callable]] = defaultdict(list)

        # 状态
        self._running = False

    def _default_config(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            "exchanges": ["BINANCE_FUTURES"],
            "symbols": ["BTC-USDT-PERP", "ETH-USDT-PERP"],
            "channels": ["trades", "l2_book", "funding", "open_interest"],
            "book_depth": 20,
            "max_trades_cache": 1000
        }

    def _get_exchange_class(self, exchange_name: str):
        """获取交易所类"""
        exchange_map = {
            "BINANCE": Binance,
            "BINANCE_FUTURES": BinanceFutures,
            "OKX": OKX,
            "BYBIT": Bybit
        }
        return exchange_map.get(exchange_name.upper())

    # ========== 数据处理回调 ==========

    async def _handle_trade(self, trade, receipt_timestamp):
        """处理逐笔成交"""
        symbol = trade.symbol
        trade_data = {
            "timestamp": trade.timestamp,
            "receipt_timestamp": receipt_timestamp,
            "symbol": symbol,
            "side": trade.side,
            "price": float(trade.price),
            "amount": float(trade.amount),
            "id": trade.id
        }

        # 缓存
        self.trades_cache[symbol].append(trade_data)
        max_cache = self.config.get("max_trades_cache", 1000)
        if len(self.trades_cache[symbol]) > max_cache:
            self.trades_cache[symbol] = self.trades_cache[symbol][-max_cache:]

        # 触发回调
        for callback in self.callbacks.get("trade", []):
            try:
                await self._maybe_await(callback(trade_data))
            except Exception as e:
                logger.error(f"Trade callback error: {e}")

    async def _handle_book(self, book, receipt_timestamp):
        """处理订单簿更新"""
        symbol = book.symbol
        book_data = {
            "timestamp": book.timestamp,
            "receipt_timestamp": receipt_timestamp,
            "symbol": symbol,
            "bids": [(float(p), float(s)) for p, s in list(book.book.bids.items())[:self.config.get("book_depth", 20)]],
            "asks": [(float(p), float(s)) for p, s in list(book.book.asks.items())[:self.config.get("book_depth", 20)]]
        }

        self.orderbook_cache[symbol] = book_data

        # 触发回调
        for callback in self.callbacks.get("book", []):
            try:
                await self._maybe_await(callback(book_data))
            except Exception as e:
                logger.error(f"Book callback error: {e}")

    async def _handle_funding(self, funding, receipt_timestamp):
        """处理资金费率"""
        symbol = funding.symbol
        funding_data = {
            "timestamp": funding.timestamp,
            "receipt_timestamp": receipt_timestamp,
            "symbol": symbol,
            "rate": float(funding.rate),
            "predicted_rate": float(funding.predicted_rate) if funding.predicted_rate else None
        }

        self.funding_cache[symbol] = funding_data

        # 触发回调
        for callback in self.callbacks.get("funding", []):
            try:
                await self._maybe_await(callback(funding_data))
            except Exception as e:
                logger.error(f"Funding callback error: {e}")

    async def _handle_oi(self, oi, receipt_timestamp):
        """处理持仓量"""
        symbol = oi.symbol
        oi_data = {
            "timestamp": oi.timestamp,
            "receipt_timestamp": receipt_timestamp,
            "symbol": symbol,
            "open_interest": float(oi.open_interest)
        }

        self.oi_cache[symbol] = oi_data.get("open_interest", 0)

        # 触发回调
        for callback in self.callbacks.get("oi", []):
            try:
                await self._maybe_await(callback(oi_data))
            except Exception as e:
                logger.error(f"OI callback error: {e}")

    async def _maybe_await(self, result):
        """如果是协程则await"""
        if asyncio.iscoroutine(result):
            return await result
        return result

    # ========== 公共接口 ==========

    def add_callback(self, data_type: str, callback: Callable):
        """
        添加数据回调

        Args:
            data_type: 数据类型 ('trade', 'book', 'funding', 'oi')
            callback: 回调函数
        """
        self.callbacks[data_type].append(callback)

    def setup_feeds(self):
        """根据配置设置数据源"""
        exchanges = self.config.get("exchanges", [])
        symbols = self.config.get("symbols", [])
        channels = self.config.get("channels", [])

        for exchange_name in exchanges:
            exchange_class = self._get_exchange_class(exchange_name)
            if not exchange_class:
                logger.warning(f"Unknown exchange: {exchange_name}")
                continue

            # 构建回调映射
            callbacks_map = {}
            if "trades" in channels:
                callbacks_map[TRADES] = self._handle_trade
            if "l2_book" in channels:
                callbacks_map[L2_BOOK] = self._handle_book
            if "funding" in channels:
                callbacks_map[FUNDING] = self._handle_funding
            if "open_interest" in channels:
                callbacks_map[OPEN_INTEREST] = self._handle_oi

            # 添加交易所
            self.feed_handler.add_feed(
                exchange_class(
                    symbols=symbols,
                    channels=list(callbacks_map.keys()),
                    callbacks=callbacks_map
                )
            )

            logger.info(f"Added feed: {exchange_name} with {len(symbols)} symbols")

    def start(self):
        """启动数据流（阻塞）"""
        self.setup_feeds()
        self._running = True
        logger.info("Starting CryptoFeed stream...")
        self.feed_handler.run()

    async def start_async(self):
        """异步启动数据流"""
        self.setup_feeds()
        self._running = True
        logger.info("Starting CryptoFeed stream (async)...")
        await self.feed_handler.run_async()

    def stop(self):
        """停止数据流"""
        self._running = False
        self.feed_handler.stop()
        logger.info("CryptoFeed stream stopped")

    # ========== 数据获取接口（供因子系统使用）==========

    def get_orderbook(self, symbol: str) -> Optional[Dict]:
        """
        获取指定交易对的订单簿

        Returns:
            {
                "bids": [(price, size), ...],
                "asks": [(price, size), ...],
                "timestamp": float
            }
        """
        return self.orderbook_cache.get(symbol)

    def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """
        获取最近的逐笔成交

        Returns:
            [{"price": float, "amount": float, "side": str, "timestamp": float}, ...]
        """
        trades = self.trades_cache.get(symbol, [])
        return trades[-limit:] if trades else []

    def get_funding_rate(self, symbol: str) -> Optional[Dict]:
        """获取资金费率"""
        return self.funding_cache.get(symbol)

    def get_open_interest(self, symbol: str) -> float:
        """获取持仓量"""
        return self.oi_cache.get(symbol, 0.0)

    def calculate_cvd(self, symbol: str, window: int = 100) -> float:
        """
        计算CVD (Cumulative Volume Delta)

        基于逐笔成交计算买卖差额

        Args:
            symbol: 交易对
            window: 计算窗口

        Returns:
            CVD值（正=买盘主导，负=卖盘主导）
        """
        trades = self.get_recent_trades(symbol, window)
        if not trades:
            return 0.0

        cvd = 0.0
        for trade in trades:
            if trade["side"].lower() == "buy":
                cvd += trade["amount"]
            else:
                cvd -= trade["amount"]

        return cvd

    def calculate_obi(self, symbol: str) -> float:
        """
        计算OBI (Order Book Imbalance)

        OBI = (bid_volume - ask_volume) / (bid_volume + ask_volume)

        Returns:
            OBI值 [-1, 1]
        """
        book = self.get_orderbook(symbol)
        if not book:
            return 0.0

        bid_volume = sum(size for _, size in book.get("bids", []))
        ask_volume = sum(size for _, size in book.get("asks", []))

        total = bid_volume + ask_volume
        if total == 0:
            return 0.0

        return (bid_volume - ask_volume) / total


# ========== 便捷函数 ==========

def create_stream_from_yaml(config_path: str) -> CryptoFeedStream:
    """从YAML配置文件创建数据流"""
    import yaml
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return CryptoFeedStream(config)


# ========== 示例用法 ==========

if __name__ == "__main__":
    # 示例：启动数据流
    logging.basicConfig(level=logging.INFO)

    config = {
        "exchanges": ["BINANCE_FUTURES"],
        "symbols": ["BTC-USDT-PERP"],
        "channels": ["trades", "l2_book"],
        "book_depth": 10
    }

    stream = CryptoFeedStream(config)

    # 添加回调
    def on_trade(trade):
        print(f"Trade: {trade['symbol']} {trade['side']} {trade['price']} x {trade['amount']}")

    stream.add_callback("trade", on_trade)

    print("Starting stream... Press Ctrl+C to stop")
    try:
        stream.start()
    except KeyboardInterrupt:
        stream.stop()
