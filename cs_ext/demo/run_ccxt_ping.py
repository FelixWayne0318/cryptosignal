# cs_ext/demo/run_ccxt_ping.py
from cs_ext.api.ccxt_wrapper import CcxtExchange


def main():
    # 示例：不带 key，做公共接口测试
    ex = CcxtExchange(exchange_id="binance", enable_rate_limit=True)

    ticker = ex.fetch_ticker("BTC/USDT")
    print("[CCXT] BTC/USDT ticker:", ticker.get("last"))

    # 示例：获取最近几根 1h K 线
    klines = ex.fetch_ohlcv("BTC/USDT", timeframe="1h", limit=5)
    print("[CCXT] 最近5根1h K线（timestamp, open, high, low, close, volume）:")
    for k in klines:
        print(k)


if __name__ == "__main__":
    main()
