#!/usr/bin/env python3
"""
V8实时数据流启动脚本

启动 V8 实时交易管道，整合 Cryptofeed → 因子计算 → 决策 → 执行。

Usage:
    python scripts/start_realtime_stream.py [--symbols BTC,ETH] [--mode simple|full]
    python scripts/start_realtime_stream.py --all-symbols --mode full  # 全市场扫描

    --symbols: 交易对列表，逗号分隔（默认：BTC,ETH）
    --all-symbols: 动态加载全市场高流动性币种（从CCXT获取）
    --mode: 运行模式
        - simple: 仅启动数据流（原始模式）
        - full: 启动完整V8管道（因子计算+信号生成）
    --interval: 扫描间隔秒数（默认300）

Author: CryptoSignal
Version: v8.0.1
"""

import argparse
import sys
import os
import asyncio

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ats_core.config.threshold_config import get_thresholds


async def load_dynamic_symbols():
    """
    从CCXT动态加载高流动性USDT永续合约币种

    Returns:
        List[str]: 币种列表（如['BTC', 'ETH', 'SOL', ...]）
    """
    try:
        import ccxt.async_support as ccxt

        # 从配置加载参数
        config = get_thresholds()
        v8_config = config.get_all().get("v8_integration", {})
        scanner_cfg = v8_config.get("scanner", {})

        min_volume = scanner_cfg.get("min_volume_usdt", 3000000)
        max_symbols = scanner_cfg.get("max_symbols", None)
        excluded_symbols = set(scanner_cfg.get("excluded_symbols", []))

        print(f"[V8] 从CCXT动态加载币种...")
        print(f"     最小成交额: {min_volume/1000000:.1f}M USDT")
        if excluded_symbols:
            print(f"     排除币种: {len(excluded_symbols)}个 (Cryptofeed不支持)")

        # 创建CCXT客户端
        exchange = ccxt.binanceusdm({
            'enableRateLimit': True,
        })

        try:
            # 获取市场信息
            markets = await exchange.load_markets()

            # 获取24h行情
            tickers = await exchange.fetch_tickers()

            # 筛选USDT永续合约
            symbols = []
            for symbol, ticker in tickers.items():
                if not symbol.endswith(':USDT'):
                    continue

                market = markets.get(symbol)
                if not market:
                    continue

                # 检查是否为永续合约
                if market.get('type') != 'swap' or market.get('settle') != 'USDT':
                    continue

                # 检查流动性
                quote_volume = ticker.get('quoteVolume', 0) or 0
                if quote_volume < min_volume:
                    continue

                # 提取基础币种名称（如 BTC/USDT:USDT → BTC）
                base = symbol.split('/')[0]

                # 过滤Cryptofeed不支持的币种
                if base in excluded_symbols:
                    continue

                symbols.append((base, quote_volume))

            # 按成交额排序
            symbols.sort(key=lambda x: x[1], reverse=True)

            # 提取币种名称
            result = [s[0] for s in symbols]

            # 限制最大数量
            if max_symbols and len(result) > max_symbols:
                result = result[:max_symbols]

            print(f"[V8] 筛选出 {len(result)} 个高流动性币种 (已排除{len(excluded_symbols)}个不支持币种)")
            if len(result) > 0:
                print(f"     Top 5: {', '.join(result[:5])}")

            return result

        finally:
            await exchange.close()

    except ImportError:
        print("[V8] 错误: CCXT未安装，请运行 pip install ccxt")
        return ["BTC", "ETH"]
    except Exception as e:
        print(f"[V8] 动态加载币种失败: {e}")
        print("[V8] 使用默认币种: BTC, ETH")
        return ["BTC", "ETH"]


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
        "--all-symbols",
        action="store_true",
        help="动态加载全市场高流动性币种（覆盖--symbols）"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["simple", "full"],
        default="simple",
        help="运行模式：simple=仅数据流，full=完整V8管道"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="扫描间隔秒数（默认300）"
    )

    args = parser.parse_args()

    # 解析交易对
    if args.all_symbols:
        # 动态加载全市场币种
        symbols = asyncio.run(load_dynamic_symbols())
    else:
        symbols = [s.strip().upper() for s in args.symbols.split(",")]

    print("=" * 60)
    print("V8 Realtime Stream v8.0.1")
    print("=" * 60)
    print(f"Symbols: {len(symbols)}个 ({', '.join(symbols[:5])}{'...' if len(symbols) > 5 else ''})")
    print(f"Mode: {args.mode}")
    print(f"Interval: {args.interval}s")
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
