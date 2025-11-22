# cs_ext/demo/run_cryptofeed_demo.py
from ats_core.env.bootstrap import bootstrap_env

bootstrap_env()

from cs_ext.data.cryptofeed_stream import CryptofeedStream, TradeEvent, OrderBookEvent


def on_trade(evt: TradeEvent):
    print(f"[TRADE] {evt}")


def on_orderbook(evt: OrderBookEvent):
    print(f"[L2_BOOK] {evt.symbol} ts={evt.ts} bids={len(evt.bids)} asks={len(evt.asks)}")


def main():
    # 先只测 BTC，避免一次订阅太多
    symbols = ["BTC-USDT-PERP"]
    stream = CryptofeedStream(symbols=symbols, on_trade=on_trade, on_orderbook=on_orderbook)
    stream.run_forever()


if __name__ == "__main__":
    main()
