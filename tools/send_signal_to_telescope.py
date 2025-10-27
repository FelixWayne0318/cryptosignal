#!/usr/bin/env python3
# coding: utf-8
"""
发送信号到链上望远镜群组
使用 telegram_fmt.py 标准样式
"""

import os
import sys

# 设置Telegram配置（链上望远镜）
os.environ["TELEGRAM_BOT_TOKEN"] = "7545580872:AAF7HzkHA4LRQUiOZngUgL39epuGVeEta70"
os.environ["TELEGRAM_CHAT_ID"] = "-1003142003085"

def send_analysis(symbol: str, use_v3: bool = False):
    """
    分析币种并发送到Telegram

    Args:
        symbol: 交易对符号（如BTCUSDT）
        use_v3: 是否使用v3分析器（默认False，使用v2）
    """
    from ats_core.outputs.telegram_fmt import render_trade, render_watch
    from ats_core.outputs.publisher import telegram_send

    try:
        if use_v3:
            # 使用v3系统（需要API密钥）
            from ats_core.pipeline.analyze_symbol_v3 import analyze_symbol_v3
            print(f"🔍 使用v3系统分析 {symbol}...")
            result = analyze_symbol_v3(symbol)
        else:
            # 使用v2系统（无需API密钥）
            from ats_core.pipeline.analyze_symbol import analyze_symbol
            print(f"🔍 使用v2系统分析 {symbol}...")
            result = analyze_symbol(symbol)

        # 检查是否有错误
        if "error" in result:
            print(f"❌ 分析失败: {result['error']}")
            return False

        # 判断信号类型
        pub = result.get("publish", {})
        is_prime = pub.get("prime", False)

        # 格式化消息（使用telegram_fmt.py样式）
        if is_prime:
            message = render_trade(result)
            signal_type = "Prime交易信号"
        else:
            message = render_watch(result)
            signal_type = "Watch观察信号"

        print(f"\n{'=' * 60}")
        print(f"📊 {signal_type}")
        print(f"{'=' * 60}")
        print(message)
        print(f"{'=' * 60}\n")

        # 发送到Telegram
        print(f"📤 发送到【链上望远镜】群组...")
        telegram_send(message)
        print(f"✅ 发送成功！")

        return True

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def batch_scan_and_send(max_symbols: int = 10, use_v3: bool = False):
    """
    批量扫描并发送信号

    Args:
        max_symbols: 最多分析多少个币种
        use_v3: 是否使用v3分析器
    """
    import asyncio
    from ats_core.pipeline.market_wide_scanner import MarketWideScanner
    from ats_core.outputs.telegram_fmt import render_trade, render_watch
    from ats_core.outputs.publisher import telegram_send
    import time

    async def scan():
        scanner = MarketWideScanner(
            min_quote_volume=3_000_000,
            use_websocket_cache=False
        )
        await scanner.initialize()
        symbols = scanner.get_symbols()[:max_symbols]

        print(f"🚀 开始批量扫描: {len(symbols)} 个币种")
        print(f"   目标群组: 链上望远镜 (-1003142003085)")
        print(f"   分析系统: {'v3 (10+1维)' if use_v3 else 'v2 (8维)'}")
        print(f"   消息样式: telegram_fmt.py 标准模板\n")

        success_count = 0
        error_count = 0

        for i, symbol in enumerate(symbols, 1):
            print(f"\n[{i}/{len(symbols)}] 分析 {symbol}...")

            if send_analysis(symbol, use_v3):
                success_count += 1
            else:
                error_count += 1

            # 限流：每个币种间隔1秒
            if i < len(symbols):
                time.sleep(1)

        print(f"\n{'=' * 60}")
        print(f"📊 扫描完成统计")
        print(f"{'=' * 60}")
        print(f"✅ 成功: {success_count}")
        print(f"❌ 失败: {error_count}")
        print(f"📊 总计: {len(symbols)}")
        print(f"{'=' * 60}\n")

    asyncio.run(scan())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="发送信号到链上望远镜群组")
    parser.add_argument("symbol", nargs="?", help="交易对符号（如BTCUSDT）")
    parser.add_argument("--batch", action="store_true", help="批量扫描模式")
    parser.add_argument("--max", type=int, default=10, help="批量模式最多分析币种数")
    parser.add_argument("--v3", action="store_true", help="使用v3分析器（需要API密钥）")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("🔭 链上望远镜 - 信号发送系统")
    print("=" * 60)
    print("群组ID: -1003142003085")
    print("Bot: @analysis_token_bot")
    print("样式: telegram_fmt.py 标准模板")
    print("=" * 60 + "\n")

    if args.batch:
        # 批量扫描模式
        batch_scan_and_send(max_symbols=args.max, use_v3=args.v3)
    elif args.symbol:
        # 单币种模式
        send_analysis(args.symbol.upper(), use_v3=args.v3)
    else:
        # 显示帮助
        print("使用方法:")
        print("\n1. 发送单个币种分析:")
        print("   python3 tools/send_signal_to_telescope.py BTCUSDT")
        print("\n2. 批量扫描并发送（v2系统，无需API）:")
        print("   python3 tools/send_signal_to_telescope.py --batch --max 20")
        print("\n3. 使用v3系统（需要Binance API密钥）:")
        print("   python3 tools/send_signal_to_telescope.py BTCUSDT --v3")
        print("\n4. v3批量扫描:")
        print("   python3 tools/send_signal_to_telescope.py --batch --max 20 --v3")
        print()
