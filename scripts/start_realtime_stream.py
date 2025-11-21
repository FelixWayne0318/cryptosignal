#!/usr/bin/env python3
"""
V8实时数据流启动脚本

启动 V8 实时交易管道，整合 Cryptofeed → 因子计算 → 决策 → 执行。

Usage:
    python scripts/start_realtime_stream.py [--symbols BTC,ETH] [--mode simple|full]

    --symbols: 交易对列表，逗号分隔（默认：BTC,ETH）
    --mode: 运行模式
        - simple: 仅启动数据流（原始模式）
        - full: 启动完整V8管道（因子计算+信号生成）

Author: CryptoSignal
Version: v8.0.0
"""

import argparse
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_simple_mode(symbols):
    """运行简单模式（仅数据流）"""
    from cs_ext.data.cryptofeed_stream import CryptofeedStream

    # 数据缓存
    trades_buffer = {}
    orderbook_cache = {}

    def on_trade(evt):
        """写入 CVD / 成交缓存"""
        if evt.symbol not in trades_buffer:
            trades_buffer[evt.symbol] = []
        trades_buffer[evt.symbol].append({
            'ts': evt.ts,
            'price': evt.price,
            'size': evt.size,
            'side': evt.side
        })
        # 保留最近1000条
        if len(trades_buffer[evt.symbol]) > 1000:
            trades_buffer[evt.symbol] = trades_buffer[evt.symbol][-1000:]

        # 打印交易信息
        print(f"[TRADE] {evt.symbol} {evt.side} {evt.size:.4f} @ {evt.price:.2f}")

    def on_orderbook(evt):
        """写入 OBI / LDI 缓存"""
        orderbook_cache[evt.symbol] = {
            'ts': evt.ts,
            'bids': evt.bids,
            'asks': evt.asks
        }

        # 打印订单簿摘要
        if evt.bids and evt.asks:
            best_bid = evt.bids[0][0] if evt.bids else 0
            best_ask = evt.asks[0][0] if evt.asks else 0
            spread = (best_ask - best_bid) / best_bid * 10000 if best_bid > 0 else 0
            print(f"[BOOK] {evt.symbol} bid={best_bid:.2f} ask={best_ask:.2f} spread={spread:.1f}bps")

    # 转换符号格式
    cf_symbols = [f"{s.upper()}-USDT-PERP" for s in symbols]

    stream = CryptofeedStream(cf_symbols, on_trade, on_orderbook)
    print(f"[Simple Mode] Starting stream for {cf_symbols}")
    stream.run_forever()


def run_full_mode(symbols):
    """运行完整V8管道模式"""
    from ats_core.pipeline.v8_realtime_pipeline import V8RealtimePipeline, V8Signal

    # 转换符号格式
    formatted_symbols = [f"{s.upper()}USDT" for s in symbols]

    # 创建V8管道
    pipeline = V8RealtimePipeline(formatted_symbols)

    # 设置信号回调
    def on_signal(signal: V8Signal):
        direction_icon = "🟢" if signal.direction == "long" else "🔴"
        print(f"{direction_icon} [V8 Signal] {signal.symbol} {signal.direction.upper()} "
              f"strength={signal.strength:.1f} confidence={signal.confidence:.2f} "
              f"CVD_z={signal.factors.cvd_z:.2f} OBI={signal.factors.obi:.2f}")

    pipeline.set_signal_callback(on_signal)

    print(f"[Full V8 Mode] Starting pipeline for {formatted_symbols}")
    print(f"  - dry_run: {pipeline.dry_run}")
    print(f"  - auto_execute: {pipeline.auto_execute}")
    print(f"  - min_confidence: {pipeline.min_confidence}")
    print()

    # 启动管道
    import asyncio
    try:
        asyncio.run(pipeline.start())
    except KeyboardInterrupt:
        pipeline.stop()
        print("\nV8管道已停止")


def main():
    parser = argparse.ArgumentParser(description="V8实时数据流启动脚本")
    parser.add_argument(
        "--symbols",
        type=str,
        default="BTC,ETH",
        help="交易对列表，逗号分隔（默认：BTC,ETH）"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["simple", "full"],
        default="simple",
        help="运行模式：simple=仅数据流，full=完整V8管道"
    )

    args = parser.parse_args()

    # 解析交易对
    symbols = [s.strip().upper() for s in args.symbols.split(",")]

    print("=" * 60)
    print("V8 Realtime Stream")
    print("=" * 60)
    print(f"Symbols: {symbols}")
    print(f"Mode: {args.mode}")
    print("=" * 60)
    print()

    try:
        if args.mode == "simple":
            run_simple_mode(symbols)
        else:
            run_full_mode(symbols)
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
