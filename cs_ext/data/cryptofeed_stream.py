# cs_ext/data/cryptofeed_stream.py
import asyncio
from decimal import Decimal
from typing import Callable, Dict, Any, List, Optional

from cryptofeed import FeedHandler
from cryptofeed.exchanges import BinanceFutures
from cryptofeed.defines import TRADES, L2_BOOK


class TradeEvent:
    """
    统一的成交事件结构，用于 CVD / 成交驱动因子。
    """
    def __init__(self, symbol: str, ts: float, price: float, size: float, side: str):
        self.symbol = symbol            # 交易对，如 BTC-USDT-PERP
        self.ts = ts                    # 交易所时间戳（秒）
        self.price = price
        self.size = size
        self.side = side.lower()        # 'buy' or 'sell'

    def __repr__(self) -> str:
        return (
            f"TradeEvent(symbol={self.symbol}, ts={self.ts}, "
            f"price={self.price}, size={self.size}, side={self.side})"
        )


class OrderBookEvent:
    """
    统一的订单簿事件结构，用于 OBI / LDI / 流动性因子。
    """
    def __init__(self, symbol: str, ts: float, bids: List[List[float]], asks: List[List[float]]):
        self.symbol = symbol
        self.ts = ts
        # 约定 bids/asks 排序由上层因子模块决定，这里按常规排序
        self.bids = bids  # [[price, size], ...]
        self.asks = asks

    def __repr__(self) -> str:
        return (
            f"OrderBookEvent(symbol={self.symbol}, ts={self.ts}, "
            f"bids_len={len(self.bids)}, asks_len={len(self.asks)})"
        )


class CryptofeedStream:
    """
    使用 Cryptofeed 订阅 Binance USDT-M 行情，为 CryptoSignal 提供统一数据回调。

    用法示例：
        def on_trade(evt: TradeEvent):
            # 写入 CVD 缓存 / 队列
            pass

        def on_orderbook(evt: OrderBookEvent):
            # 写入 OBI / LDI 缓存 / 队列
            pass

        stream = CryptofeedStream(symbols=["BTC-USDT-PERP"], on_trade=on_trade, on_orderbook=on_orderbook)
        stream.run_forever()
    """

    def __init__(
        self,
        symbols: List[str],
        on_trade: Optional[Callable[[TradeEvent], None]] = None,
        on_orderbook: Optional[Callable[[OrderBookEvent], None]] = None,
        max_depth: int = 50,
    ):
        self.symbols = symbols
        self.on_trade = on_trade
        self.on_orderbook = on_orderbook
        self.max_depth = max_depth

        self._fh = FeedHandler()

    async def _trade_callback(self, trade, receipt_timestamp: float):
        """
        新版 cryptofeed 回调签名：(trade_obj, receipt_timestamp)
        """
        if not self.on_trade:
            return

        evt = TradeEvent(
            symbol=trade.symbol,
            ts=trade.timestamp,
            price=float(trade.price),
            size=float(trade.amount),
            side=trade.side.lower(),
        )
        try:
            self.on_trade(evt)
        except Exception as e:
            # 防止单个回调异常导致整体中断
            print(f"[CryptofeedStream] on_trade error: {e} for event {evt}")

    async def _l2_book_callback(self, book, receipt_timestamp: float):
        """
        新版 cryptofeed 回调签名：(book_obj, receipt_timestamp)
        """
        if not self.on_orderbook:
            return

        # 新版 book 对象有 .book.bids 和 .book.asks
        bids_raw = book.book.bids
        asks_raw = book.book.asks

        # bids/asks 是 SortedDict {price: size}
        bids = [[float(p), float(s)] for p, s in bids_raw.items()]
        asks = [[float(p), float(s)] for p, s in asks_raw.items()]

        # 按价格排序：bids 从高到低，asks 从低到高
        bids.sort(key=lambda x: x[0], reverse=True)
        asks.sort(key=lambda x: x[0])

        if self.max_depth and self.max_depth > 0:
            bids = bids[: self.max_depth]
            asks = asks[: self.max_depth]

        evt = OrderBookEvent(
            symbol=book.symbol,
            ts=book.timestamp,
            bids=bids,
            asks=asks,
        )
        try:
            self.on_orderbook(evt)
        except Exception as e:
            print(f"[CryptofeedStream] on_orderbook error: {e} for event {evt}")

    def run_forever(self):
        """
        阻塞式启动事件循环。适合独立进程或专用线程使用。
        """
        channels = [TRADES, L2_BOOK]

        self._fh.add_feed(
            BinanceFutures(
                channels=channels,
                symbols=self.symbols,
                callbacks={
                    TRADES: self._trade_callback,
                    L2_BOOK: self._l2_book_callback,
                },
            )
        )

        # Python 3.10+ 兼容：确保有事件循环
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        self._fh.run()

    def run_in_background(self):
        """
        把 Cryptofeed 跑在独立异步任务中（如果你的主程序已有 asyncio loop，可以用此方式）。
        """
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._run_async())
        except RuntimeError:
            # Python 3.10+ 兼容：没有运行中的事件循环时创建新的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.create_task(self._run_async())

    async def _run_async(self):
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
        await self._fh.start()
