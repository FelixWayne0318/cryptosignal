#!/usr/bin/env python3
"""
V8 架构服务器连通性测试

测试所有组件：
1. Cryptofeed - WebSocket 数据流
2. CCXT - REST API 调用
3. Cryptostore - 数据落盘
4. Freqtrade - 策略导入
5. Hummingbot - 执行器

Usage:
    python -m cs_ext.demo.test_v8_connectivity
"""

import sys
import time
import asyncio
from datetime import datetime

# 环境引导
from ats_core.env.bootstrap import bootstrap_env
bootstrap_env()


def test_ccxt():
    """测试 CCXT API 连通性"""
    print("\n" + "="*50)
    print("🔍 测试 CCXT API 连通性")
    print("="*50)

    try:
        from cs_ext.api.ccxt_wrapper import CcxtExchange

        # 测试 Binance 现货
        ex = CcxtExchange(exchange_id="binance", enable_rate_limit=True)
        ticker = ex.fetch_ticker("BTC/USDT")
        print(f"[OK] Binance 现货 BTC/USDT: ${ticker.get('last', 'N/A')}")

        # 测试获取 K 线
        klines = ex.fetch_ohlcv("BTC/USDT", timeframe="1h", limit=3)
        print(f"[OK] 获取 K 线成功，最新收盘价: {klines[-1][4] if klines else 'N/A'}")

        # 测试 Binance USDT-M 合约
        try:
            ex_futures = CcxtExchange(exchange_id="binanceusdm", enable_rate_limit=True)
            ticker_futures = ex_futures.fetch_ticker("BTC/USDT")
            print(f"[OK] Binance 合约 BTC/USDT: ${ticker_futures.get('last', 'N/A')}")
        except Exception as e:
            print(f"[WARN] Binance 合约测试失败: {e}")

        return True
    except Exception as e:
        print(f"[FAIL] CCXT 测试失败: {e}")
        return False


def test_cryptofeed():
    """测试 Cryptofeed WebSocket 连通性"""
    print("\n" + "="*50)
    print("🔍 测试 Cryptofeed WebSocket 连通性")
    print("="*50)

    try:
        from cs_ext.data.cryptofeed_stream import CryptofeedStream, TradeEvent, OrderBookEvent

        received_data = {"trade": False, "book": False}

        def on_trade(evt: TradeEvent):
            if not received_data["trade"]:
                print(f"[OK] 收到交易数据: {evt.symbol} {evt.side} {evt.size} @ {evt.price}")
                received_data["trade"] = True

        def on_book(evt: OrderBookEvent):
            if not received_data["book"]:
                best_bid = evt.bids[0] if evt.bids else [0, 0]
                best_ask = evt.asks[0] if evt.asks else [0, 0]
                print(f"[OK] 收到订单簿: {evt.symbol} bid={best_bid[0]} ask={best_ask[0]}")
                received_data["book"] = True

        print("连接 Binance Futures WebSocket (等待5秒)...")

        # 使用线程运行，设置超时
        import threading

        stream = CryptofeedStream(
            symbols=["BTC-USDT-PERP"],
            on_trade=on_trade,
            on_orderbook=on_book
        )

        thread = threading.Thread(target=stream.run_forever, daemon=True)
        thread.start()

        # 等待数据
        timeout = 5
        start = time.time()
        while time.time() - start < timeout:
            if received_data["trade"] and received_data["book"]:
                break
            time.sleep(0.1)

        if received_data["trade"] or received_data["book"]:
            print("[OK] Cryptofeed 连接成功")
            return True
        else:
            print("[WARN] Cryptofeed 超时，未收到数据（可能是网络限制）")
            return False

    except Exception as e:
        print(f"[FAIL] Cryptofeed 测试失败: {e}")
        return False


def test_cryptostore():
    """测试 Cryptostore 数据落盘"""
    print("\n" + "="*50)
    print("🔍 测试 Cryptostore 数据落盘")
    print("="*50)

    try:
        from cs_ext.storage.cryptostore_adapter import CryptostoreAdapter
        import os

        adapter = CryptostoreAdapter()

        # 测试存储交易数据
        ts = time.time()
        adapter.store_trade(
            ts=ts,
            symbol="BTC-USDT",
            price=50000.0,
            size=0.1,
            side="buy"
        )
        print("[OK] 交易数据存储成功")

        # 测试存储信号数据
        adapter.store_signal(
            ts=ts,
            symbol="BTC-USDT",
            direction="long",
            strength=85.5,
            probability=0.72,
            extra={"source": "test"}
        )
        print("[OK] 信号数据存储成功")

        # 验证文件存在
        date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        trade_file = f"data/storage/{date_str}/trade.jsonl"
        signal_file = f"data/storage/{date_str}/signal.jsonl"

        if os.path.exists(trade_file):
            print(f"[OK] 交易文件已创建: {trade_file}")
        if os.path.exists(signal_file):
            print(f"[OK] 信号文件已创建: {signal_file}")

        return True
    except Exception as e:
        print(f"[FAIL] Cryptostore 测试失败: {e}")
        return False


def test_freqtrade():
    """测试 Freqtrade 策略导入"""
    print("\n" + "="*50)
    print("🔍 测试 Freqtrade 策略导入")
    print("="*50)

    try:
        from freqtrade.strategy.interface import IStrategy
        from cs_ext.backtest.freqtrade_bridge import CryptoSignalStrategy

        # 验证类继承
        assert issubclass(CryptoSignalStrategy, IStrategy)
        print("[OK] CryptoSignalStrategy 正确继承 IStrategy")

        # 检查必要方法
        required_methods = [
            'populate_indicators',
            'populate_entry_trend',
            'populate_exit_trend'
        ]
        for method in required_methods:
            assert hasattr(CryptoSignalStrategy, method)
            print(f"[OK] 方法存在: {method}")

        return True
    except Exception as e:
        print(f"[FAIL] Freqtrade 测试失败: {e}")
        return False


def test_hummingbot():
    """测试 Hummingbot 执行器"""
    print("\n" + "="*50)
    print("🔍 测试 Hummingbot 执行器")
    print("="*50)

    try:
        from cs_ext.execution.hummingbot_bridge import HummingbotExecutor, ExecutionSignal

        # 创建执行器
        executor = HummingbotExecutor(poll_interval=0.1)
        print("[OK] HummingbotExecutor 创建成功")

        # 创建测试信号
        signal = ExecutionSignal(
            exchange="binance_perpetual",
            symbol="BTC-USDT",
            side="buy",
            quantity=0.001,
            signal_id="test_001",
            order_type="market"
        )
        print(f"[OK] ExecutionSignal 创建成功: {signal}")

        # 测试提交信号（不启动执行线程）
        executor.submit_signal(signal)
        print("[OK] 信号提交成功")

        # 注意：实际下单需要配置 connector
        print("[INFO] 实际下单需要配置 Hummingbot connector")

        return True
    except Exception as e:
        print(f"[FAIL] Hummingbot 测试失败: {e}")
        return False


def main():
    print("="*50)
    print("🚀 CryptoSignal V8 服务器连通性测试")
    print(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)

    results = {}

    # 运行所有测试
    results["CCXT"] = test_ccxt()
    results["Cryptofeed"] = test_cryptofeed()
    results["Cryptostore"] = test_cryptostore()
    results["Freqtrade"] = test_freqtrade()
    results["Hummingbot"] = test_hummingbot()

    # 汇总结果
    print("\n" + "="*50)
    print("📊 测试结果汇总")
    print("="*50)

    all_passed = True
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print("="*50)
    if all_passed:
        print("🎉 所有组件测试通过！V8 架构就绪。")
    else:
        print("⚠️  部分组件测试失败，请检查配置。")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
