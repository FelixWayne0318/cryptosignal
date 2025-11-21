# cs_ext/data/cryptofeed_stream.py
"""
Cryptofeed 数据流适配器

为 CryptoSignal 因子层提供标准化的实时数据回调接口。

Usage:
    def on_trade(evt):
        print(f"{evt.symbol} {evt.side} {evt.size} @ {evt.price}")

    def on_book(evt):
        print(f"{evt.symbol} best bid: {evt.bids[0]}")

    stream = CryptofeedStream(
        symbols=["BTC-USDT-PERP"],
        on_trade=on_trade,
        on_orderbook=on_book
    )
    stream.start()
"""

import asyncio
from decimal import Decimal
from typing import Callable, Dict, Any, List

from cryptofeed import FeedHandler
from cryptofeed.exchanges import BinanceFutures
from cryptofeed.defines import TRADES, L2_BOOK


class TradeEvent:
    def __init__(self, symbol: str, ts: float, price: float, size: float, side: str):
        self.symbol = symbol
        self.ts = ts
        self.price = price
        self.size = size
        self.side = side  # 'buy' 或 'sell'


class OrderBookEvent:
    def __init__(self, symbol: str, ts: float, bids: List[List[float]], asks: List[List[float]]):
        self.symbol = symbol
        self.ts = ts
        self.bids = bids  # [[price, size], ...]
        self.asks = asks


class CryptofeedStream:
    """
    统一封装 Cryptofeed，为 CryptoSignal 因子层提供标准化数据回调。
    """

    def __init__(
        self,
        symbols: List[str],
        on_trade: Callable[[TradeEvent], None],
        on_orderbook: Callable[[OrderBookEvent], None],
    ):
        self.symbols = symbols
        self.on_trade = on_trade
        self.on_orderbook = on_orderbook
        self._fh = FeedHandler()

    async def _trade_callback(self, feed: str, symbol: str, order_id: str, timestamp: float,
                              side: str, amount: Decimal, price: Decimal, receipt_timestamp: float):
        evt = TradeEvent(
            symbol=symbol,
            ts=timestamp,
            price=float(price),
            size=float(amount),
            side=side.lower()
        )
        self.on_trade(evt)

    async def _l2_book_callback(self, feed: str, symbol: str, book: Dict[str, Any], timestamp: float, receipt_timestamp: float):
        bids = [[float(p), float(s)] for p, s in book["bid"].items()]
        asks = [[float(p), float(s)] for p, s in book["ask"].items()]
        evt = OrderBookEvent(
            symbol=symbol,
            ts=timestamp,
            bids=bids,
            asks=asks,
        )
        self.on_orderbook(evt)

    def start(self):
        """
        启动异步事件循环。
        """
        self._fh.add_feed(
            BinanceFutures(
                channels=[TRADES, L2_BOOK],
                symbols=self.symbols,
                callbacks={
                    TRADES: self._trade_callback,
                    L2_BOOK: self._l2_book_callback,
                },
            )
        )
        self._fh.run()
